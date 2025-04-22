# board.py
# 管理拼盘的状态、碎片布局、交换、完成检测、动态填充及动画

# from ast import Return # 这个导入似乎没用到，可以移除
import pygame
import settings
import random # 用于随机打乱碎片
import time # 用于计时
import os # 用于检查文件存在性
from piece import Piece # 导入Piece类
# from image_manager import ImageManager # image_manager 在 __init__ 和 ImageManager 调用中传入了
# from main import Game # Board 可能需要 Game 实例来触发状态改变 (如图片完成提示)
import utils # 导入工具函数
import image_manager # 导入 ImageManager 模块, 用于加载图片


class Board:
    def __init__(self, image_manager, saved_game_data=None): # saved_game_data 包含 Board 和 ImageManager 的存档
        """
        初始化拼盘

        Args:
            image_manager (ImageManager): 图像管理器实例
            saved_game_data (dict, optional): 从存档中加载的游戏状态数据。如果为None，则进行初始填充。默认为None。
        """
        # Check if image_manager is provided and has expected attributes
        if not hasattr(image_manager, 'get_initial_pieces_for_board') or \
           not hasattr(image_manager, 'pieces_surfaces') or \
           not hasattr(image_manager, 'game') or \
           not hasattr(image_manager, 'image_logic_dims') or \
           not hasattr(image_manager, 'set_image_state'): # Add check for set_image_state
             raise TypeError("传入的image_manager参数缺少必要的方法或属性")
        self.image_manager = image_manager
        # self.game = image_manager.game # 持有Game实例引用，通过ImageManager获取

        # 存储拼盘中的碎片，使用二维列表表示固定物理网格 (BOARD_ROWS x BOARD_COLS)
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]

        # 选中的碎片 (用于点击交换)
        self.selected_piece = None

        # 正在拖拽的碎片
        self.dragging_piece = None

        # 选中碎片的视觉反馈 Rect (直接绘制即可，不与碎片对象关联)
        self.selection_rect = None

        # Board内部状态，管理完成 -> 移除 -> 下落 -> 填充 -> 区域升级流程
        # 读档时，Board 状态应该回到 PLAYING
        self.current_board_state = settings.BOARD_STATE_PLAYING
        self._completed_image_id_pending_process = None # 完成的图片ID，等待处理
        self._completed_area_start_pos = None # 已完成区域的左上角物理网格位置
        self._upgrade_target_config = None # 区域升级：目标配置 (来自 PLAYABLE_AREA_CONFIG)

        # 用于管理所有 Piece Sprite 的 Group
        self.all_pieces_group = pygame.sprite.Group() # 正确初始化 Sprite Group

        # 动画完成后的回调队列 (目前未使用)
        # self._animation_completion_callbacks = []

        # --- 关键修改：可放置区域和背景图相关属性 ---
        self.playable_cols = 0 # 当前可放置区域的物理列数
        self.playable_rows = 0 # 当前可放置区域的物理行数
        self.playable_offset_col = 0 # 可放置区域左上角在物理拼盘网格中的列偏移
        self.playable_offset_row = 0 # 可放置区域左上角在物理拼盘网格中的行偏移
        self.background_image = None # 当前背景图 Surface
        self._current_background_name = None # 当前背景图文件名 (用于存档)
        self.unlocked_pictures_count = 0 # 已点亮图片数量 (从Game获取或存档加载)


        # 根据是否提供了存档数据来初始化拼盘
        if saved_game_data is not None and 'board_state' in saved_game_data:
            # 从存档数据加载 Board 的状态
            board_state_data = saved_game_data['board_state']
            print("Board: 从存档加载 Board 状态...") # Debug
            self._load_state_from_data(board_state_data) # 加载 Board 自身状态（包括可放置区域和背景图）
            print("Board: 从存档加载拼盘布局...") # Debug
            # _load_grid_from_data 方法内部会负责创建 Piece 并添加到 self.all_pieces_group (逐个添加)
            self._load_grid_from_data(board_state_data.get('grid_layout')) # 加载存档的物理网格布局
        else:
            # 进行初始填充
            print("Board: 进行初始拼盘填充...") # Debug
            # 初始化可放置区域和背景图为初始配置 (点亮数量 0 对应的配置)
            initial_config = settings.PLAYABLE_AREA_CONFIG.get(0)
            if initial_config is None:
                 print("致命错误: Board: settings.PLAYABLE_AREA_CONFIG 缺少点亮数量 0 的配置。无法初始化。") # Debug
                 # 触发致命错误，通知 Game 退出
                 if hasattr(self.image_manager.game, '_display_fatal_error'):
                     self.image_manager.game._display_fatal_error("配置错误: PLAYABLE_AREA_CONFIG 缺少键 0")
                     # _display_fatal_error 应该在 Game 中处理退出
                 else:
                    import sys; pygame.quit(); sys.exit()


            self._set_playable_area(initial_config['cols'], initial_config['rows'])
            self._load_background_image(initial_config['bg'])
            self.unlocked_pictures_count = 0 # 新游戏，点亮数量为 0

            # fill_initial_pieces 方法会根据初始可放置区域大小获取碎片并填充
            self.fill_initial_pieces()


        print(f"Board 初始化完成. 当前状态: {self.current_board_state}. Group大小: {len(self.all_pieces_group) if isinstance(self.all_pieces_group, pygame.sprite.Group) else 'N/A'}") # Debug


    # 新增内部方法，用于加载 Board 自身状态
    def _load_state_from_data(self, board_state_data):
        """
        从存档数据加载 Board 的状态（可放置区域、背景图、点亮数量等）。

        Args:
            board_state_data (dict): 从存档读取的 Board 状态字典。
        """
        if not board_state_data:
             print("警告: Board: 尝试从空的存档数据加载状态。")
             return

        # 加载可放置区域信息
        loaded_cols = board_state_data.get('playable_cols', 0)
        loaded_rows = board_state_data.get('playable_rows', 0)
        loaded_bg_name = board_state_data.get('background_name') # <-- 获取背景图文件名
        loaded_unlocked_count = board_state_data.get('unlocked_pictures_count', 0)

        # 验证加载的可放置区域尺寸是否有效且在物理拼盘范围内
        if loaded_cols > 0 and loaded_rows > 0 and loaded_cols <= settings.BOARD_COLS and loaded_rows <= settings.BOARD_ROWS:
             self._set_playable_area(loaded_cols, loaded_rows)
             print(f"Board: 从存档加载可放置区域: {loaded_cols}x{loaded_rows}") # Debug
        else:
             # 如果存档数据无效，使用初始可放置区域配置 (点亮数量 0 对应的配置)
             initial_config = settings.PLAYABLE_AREA_CONFIG.get(0)
             if initial_config is None:
                  print("致命错误: Board: settings.PLAYABLE_AREA_CONFIG 缺少点亮数量 0 的配置。无法恢复初始可放置区域。") # Debug
                  if hasattr(self.image_manager.game, '_display_fatal_error'):
                      self.image_manager.game._display_fatal_error("配置错误: PLAYABLE_AREA_CONFIG 缺少键 0")
                  else:
                      import sys; pygame.quit(); sys.exit()


             self._set_playable_area(initial_config['cols'], initial_config['rows'])
             print(f"Board: 存档可放置区域无效，使用初始配置: {self.playable_cols}x{self.playable_rows}") # Debug
             # Note: unlocked_pictures_count might need reset if area is reset
             loaded_unlocked_count = 0 # 如果区域无效，点亮数量也视为从 0 开始


        # 加载背景图
        if loaded_bg_name:
             self._load_background_image(loaded_bg_name)
        # else: Background will be default (based on playable area config loaded above)

        # 加载点亮图片数量
        self.unlocked_pictures_count = max(0, loaded_unlocked_count) # 确保非负数
        print(f"Board: 从存档加载点亮图片数量: {self.unlocked_pictures_count}") # Debug

        # Note: current_board_state, selected_piece, dragging_piece are not saved/loaded,
        # they are transient states and reset to PLAYING on load.


    # 新增内部方法，用于设置可放置区域尺寸和计算偏移
    def _set_playable_area(self, cols, rows):
        """
        设置当前可放置区域的尺寸，并计算其在物理拼盘中的偏移。
        Args:
            cols (int): 可放置区域的列数。
            rows (int): 可放置区域的行数。
        """
        # 确保设置的尺寸在物理拼盘范围内
        cols = min(cols, settings.BOARD_COLS)
        rows = min(rows, settings.BOARD_ROWS)

        # 确保尺寸有效且大于0
        self.playable_cols = max(1, cols)
        self.playable_rows = max(1, rows)


        # 计算可放置区域左上角在物理拼盘网格中的偏移，使其居中
        self.playable_offset_col = (settings.BOARD_COLS - self.playable_cols) // 2
        self.playable_offset_row = (settings.BOARD_ROWS - self.playable_rows) // 2

        print(f"Board: 设置可放置区域尺寸: {self.playable_cols}x{self.playable_rows}，物理偏移: ({self.playable_offset_row},{self.playable_offset_col})") # Debug


    # 新增内部方法，用于加载背景图
    def _load_background_image(self, background_name):
        """
        加载指定名称的背景图。

        Args:
            background_name (str): 背景图文件名。
        """
        if background_name is None:
             self.background_image = None
             self._current_background_name = None # Record the name loaded (None)
             print("Board: 背景图名称为 None，不加载背景图。") # Debug
             return

        background_path = os.path.join(settings.BACKGROUND_DIR, background_name)
        try:
            # 检查文件是否存在
            if not os.path.exists(background_path):
                 print(f"警告: Board: 背景图文件不存在: {background_path}") # Debug
                 self.background_image = None # 文件不存在，背景图为 None
                 self._current_background_name = None # Record the name loaded (failed)
                 return

            self.background_image = pygame.image.load(background_path).convert_alpha()
            self._current_background_name = background_name # Record the name loaded (success)
            # 背景图应与屏幕尺寸匹配 (1920x1080)
            if self.background_image.get_size() != (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT):
                 print(f"警告: Board: 背景图 {background_name} 尺寸 {self.background_image.get_size()} 与屏幕尺寸 {settings.SCREEN_WIDTH}x{settings.SCREEN_HEIGHT} 不匹配。不进行缩放。") # Debug
                 # 可以选择缩放背景图，但可能会导致扭曲或模糊
                 # self.background_image = pygame.transform.scale(self.background_image, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"错误: Board: 无法加载背景图 {background_path}: {e}") # Debug
            self.background_image = None # 加载失败，背景图为 None
            self._current_background_name = None # Record the name loaded (failed)
        except Exception as e:
            print(f"错误: Board: 加载背景图 {background_name} 时发生未知错误: {e}") # Debug
            self.background_image = None # 加载失败，背景图为 None
            self._current_background_name = None # Record the name loaded (failed)


    # 替换 fill_initial_pieces 方法 (根据初始可放置区域填充)
    def fill_initial_pieces(self):
        """根据初始可放置区域大小获取碎片并随机打乱填充到可放置区域内。"""
        # 获取初始可放置区域配置 (点亮数量为 0)
        initial_config = settings.PLAYABLE_AREA_CONFIG.get(0)
        if initial_config is None:
             print("致命错误: Board: settings.PLAYABLE_AREA_CONFIG 缺少点亮数量 0 的配置。无法进行初始填充。") # Debug
             if hasattr(self.image_manager.game, '_display_fatal_error'):
                  self.image_manager.game._display_fatal_error("配置错误: PLAYABLE_AREA_CONFIG 缺少键 0")
             else:
                  import sys; pygame.quit(); sys.exit()

        initial_playable_area_slots = initial_config['cols'] * initial_config['rows'] # 初始可放置区域的总槽位数
        print(f"Board: 初始可放置区域大小 {initial_config['cols']}x{initial_config['rows']}，总槽位 {initial_playable_area_slots}。") # Debug

        # 从 ImageManager 获取足够填满初始可放置区域的碎片数量 (或 ImageManager 当前能提供的数量)
        # ImageManager.get_initial_pieces_for_board 已经处理了只提供已加载碎片的问题
        initial_pieces = self.image_manager.get_initial_pieces_for_board(initial_playable_area_slots) # <-- 传递需要的碎片数量

        # 确保获取到的碎片数量不超过初始可放置区域槽位数
        if len(initial_pieces) > initial_playable_area_slots:
            print(f"警告: Board: ImageManager 提供的初始碎片数量 {len(initial_pieces)} 多于初始可放置区域槽位 {initial_playable_area_slots}。仅使用前 {initial_playable_area_slots} 个。") # Debug
            initial_pieces = initial_pieces[:initial_playable_area_slots]


        print(f"Board: 获取了 {len(initial_pieces)} 个初始碎片，开始填充到初始可放置区域 ({self.playable_offset_row},{self.playable_offset_col}) 起。")

        # 生成初始可放置区域内的物理网格位置列表 (从上往下，从左往右)
        initial_playable_grid_positions = []
        for r_offset in range(self.playable_rows):
            for c_offset in range(self.playable_cols):
                r = self.playable_offset_row + r_offset
                c = self.playable_offset_col + c_offset
                initial_playable_grid_positions.append((r, c))

        # 确保位置数量足够放置获取到的碎片
        if len(initial_pieces) > len(initial_playable_grid_positions):
             print(f"致命错误: Board: 获取的初始碎片数量 {len(initial_pieces)} 多于计算的可放置区域位置数量 {len(initial_playable_grid_positions)}。程序异常。") # Debug
             if hasattr(self.image_manager.game, '_display_fatal_error'):
                 self.image_manager.game._display_fatal_error("初始填充碎片数量异常。")
             else:
                  import sys; pygame.quit(); sys.exit()


        # 将每个碎片放置到初始可放置区域的一个对应顺序的网格位置上，并创建 Piece 对象
        # 这里的 initial_playable_grid_positions 是有序的，碎片是ImageManager随机打乱后给的
        # 按照 ImageManager 提供的碎片列表顺序，填充到 Board 计算出的有序位置列表
        for i, piece in enumerate(initial_pieces):
            r, c = initial_playable_grid_positions[i] # Get the next position in the playable area (ordered)

            # Assign piece to grid position
            self.grid[r][c] = piece
            # Update piece's current grid position and screen position (no animation for initial fill)
            piece.set_grid_position(r, c, animate=False)

            # --- 最精确定位调试、安全检查和断言：在添加到 Group 之前 ---
            # print(f"Board Debug: Piece {i+1}/{len(initial_pieces)} 准备添加到 Group.") # Debug
            # print(f"  Object Type: {type(piece)}, Is Sprite: {isinstance(piece, pygame.sprite.Sprite)}") # Debug
            # Get image ID safely for logging
            piece_img_id = piece.original_image_id if hasattr(piece, 'original_image_id') else 'N/A'

            # --- 关键断言：强制检查 Piece 对象是否是有效的 Sprite 并有 image/rect ---
            try:
                assert isinstance(piece, pygame.sprite.Sprite), f"致命错误: 尝试添加到 Group 的对象不是 Sprite! 类型为 {type(piece)}. Piece Info: ID {piece_img_id}"
                assert hasattr(piece, 'image') and isinstance(piece.image, pygame.Surface), f"致命错误: 尝试添加的 Sprite 没有有效的 image 属性或不是 Surface! 类型为 {type(piece.image) if hasattr(piece, 'image') else '没有此属性'}. Piece Info: ID {piece_img_id}"
                assert hasattr(piece, 'rect') and isinstance(piece.rect, pygame.Rect), f"致命错误: 尝试添加的 Sprite 没有有效的 rect 属性或不是 Rect! 类型为 {type(piece.rect) if hasattr(piece, 'rect') else '没有此属性'}. Piece Info: ID {piece_img_id}"
            except AssertionError as e:
                # Catch AssertionError and raise it with more context
                print(f"致命错误: {e}") # Print the detailed error from assertion
                if hasattr(self.image_manager.game, '_display_fatal_error'):
                     self.image_manager.game._display_fatal_error(f"碎片初始化失败:\n{e}")
                else:
                     import sys; pygame.quit(); sys.exit() # Re-raise with context


            # --- 关键修改：回到使用 group.add(piece) 方法，并捕获异常 ---
            # Check if self.all_pieces_group is indeed a Sprite Group before adding
            if isinstance(self.all_pieces_group, pygame.sprite.Group):
                 # print(f"  Group Type: {type(self.all_pieces_group)}. Current size: {len(self.all_pieces_group)}") # Debug
                 try:
                     # Use the standard Group.add method
                     self.all_pieces_group.add(piece) # <-- Error is reported here!
                     # print(f"Board: 成功添加碎片到 Group. Group大小: {len(self.all_pieces_group)}") # Debug
                 except Exception as e:
                     # Catch other exceptions during add, provide context
                     print(f"致命错误: Board: 将图片ID {piece_img_id} 的碎片添加到 Group 时发生异常 (在断言之后): {e}.") # Debug
                     if hasattr(self.image_manager.game, '_display_fatal_error'):
                          self.image_manager.game._display_fatal_error(f"添加碎片到Sprite Group失败:\n{e}")
                     else:
                         raise # Re-raise the exception

            else:
                 print("致命错误: Board: self.all_pieces_group 不是 Sprite Group！无法添加碎片。")
                 if hasattr(self.image_manager.game, '_display_fatal_error'):
                     self.image_manager.game._display_fatal_error("Sprite Group 初始化异常。")
                 else:
                     import sys; pygame.quit(); sys.exit() # Exit if Group is fundamentally broken


        print(f"Board: {len(self.all_pieces_group) if isinstance(self.all_pieces_group, pygame.sprite.Group) else 'N/A'} 个初始碎片已添加到 Group。") # Debug


    # 替换 _load_grid_from_data 方法 (回到 group.add(piece), 添加更多调试和检查)
    def _load_grid_from_data(self, grid_layout_data):
        """
        从提供的存档数据构建拼盘网格和Sprite Group。

        Args:
            grid_layout_data (list): 从存档读取的拼盘布局二维列表。
        """
        print("Board: 正在从存档数据加载物理网格布局并创建 Piece 对象...") # Debug

        # 确保存档的网格布局数据尺寸匹配当前的物理拼盘尺寸
        if not isinstance(grid_layout_data, list) or len(grid_layout_data) != settings.BOARD_ROWS:
             print(f"错误: Board: 存档数据行数不匹配当前 Board 尺寸。预期 {settings.BOARD_ROWS}，实际 {len(grid_layout_data) if isinstance(grid_layout_data, list) else '非列表'}。清空拼盘。")
             self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
             if isinstance(self.all_pieces_group, pygame.sprite.Group): self.all_pieces_group.empty()
             else: self.all_pieces_group = pygame.sprite.Group()
             return # Data mismatch, stop loading

        # 检查存档数据的列数
        if grid_layout_data and (not isinstance(grid_layout_data[0], list) or len(grid_layout_data[0]) != settings.BOARD_COLS):
             print(f"错误: Board: 存档数据第一行列数不匹配当前 Board 尺寸。预期 {settings.BOARD_COLS}，实际 {len(grid_layout_data[0]) if grid_layout_data and isinstance(grid_layout_data[0], list) else '非列表'}。清空拼盘。")
             self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
             if isinstance(self.all_pieces_group, pygame.sprite.Group): self.all_pieces_group.empty()
             else: self.all_pieces_group = pygame.sprite.Group()
             return # Data mismatch, stop loading


        # 清空当前的网格和 Sprite Group
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
        if isinstance(self.all_pieces_group, pygame.sprite.Group):
             self.all_pieces_group.empty()
        else:
            print("警告: Board: self.all_pieces_group 不是 Sprite Group，无法清空。正在重新初始化。")
            self.all_pieces_group = pygame.sprite.Group()


        pieces_added_count = 0 # Counter for pieces successfully added to grid and group


        for r in range(settings.BOARD_ROWS):
            # Ensure row data is a list and has correct number of columns
            if not isinstance(grid_layout_data[r], list) or len(grid_layout_data[r]) != settings.BOARD_COLS:
                 print(f"错误: Board: 存档数据第 {r} 行格式错误或列数不匹配。预期 {settings.BOARD_COLS} 列。跳过该行。") # Debug
                 self.grid[r] = [None for _ in range(settings.BOARD_COLS)] # Fill with None for safety
                 continue

            for c in range(settings.BOARD_COLS):
                piece_info = grid_layout_data[r][c]
                if piece_info is not None:
                    # If slot is not empty, try creating a Piece object
                    try:
                        img_id = piece_info.get('id')
                        # print(f"Board: 尝试加载图片ID {img_id} 的碎片到物理位置 ({r},{c})...") # Debug
                        orig_r = piece_info.get('orig_r')
                        orig_c = piece_info.get('orig_c')

                        # 验证 piece_info 数据
                        if img_id is None or orig_r is None or orig_c is None:
                             print(f"警告: Board: 存档碎片信息 ({piece_info}) 格式错误或缺失关键字段 (id/orig_r/orig_c)。槽位 ({r},{c}) 将为空。") # Debug
                             self.grid[r][c] = None
                             continue # Skip creating piece

                        # 从 ImageManager 获取碎片 surface
                        # 这依赖于 ImageManager 已经加载了该图片的碎片 surface (load_state会填充高优先级队列，后台加载会处理)
                        piece_surface = None
                        # Check if piece surface is available in ImageManager based on original info and loaded status
                        # Ensure img_id is a valid key in ImageManager's pieces_surfaces and the specific piece surface exists
                        if img_id in self.image_manager.pieces_surfaces and \
                           self.image_manager.pieces_surfaces.get(img_id) is not None and \
                           (orig_r, orig_c) in self.image_manager.pieces_surfaces[img_id]:
                             piece_surface = self.image_manager.pieces_surfaces[img_id][(orig_r, orig_c)]
                             # --- 关键调试：检查获取到的 Piece Surface ---
                             if not isinstance(piece_surface, pygame.Surface):
                                print(f"致命错误: Board: ImageManager 返回的对象不是 Surface! 图片ID {img_id}, 原始 ({orig_r},{orig_c}). 类型: {type(piece_surface)}") # Debug
                                piece_surface = None # Treat as not available

                        if piece_surface is None:
                             # If surface is not available, try to queue it for high-priority loading
                             # This might happen if loading was interrupted or cache incomplete
                             print(f"警告: Board: 存档碎片图片ID {img_id}, 原始 ({orig_r},{orig_c}) 的 surface 未加载在 ImageManager 中或获取失败。槽位 ({r},{c}) 将为空。加入高优先级队列。") # Debug
                             self.grid[r][c] = None # 该槽位留空
                             # Add image_id to high-priority queue if not already there (check in all_image_files to be safe)
                             if hasattr(self.image_manager, '_high_priority_load_queue') and img_id in self.image_manager.all_image_files:
                                 # Add only if not already in high priority or normal queue
                                 # Check if already in queue to avoid duplicates
                                 if img_id not in self.image_manager._high_priority_load_queue and img_id not in self.image_manager._normal_load_queue:
                                      self.image_manager._high_priority_load_queue.append(img_id)
                                      print(f"Board: 将图片ID {img_id} 加入高优先级加载队列。") # Debug
                             continue # Skip creating piece for now


                        # 创建 Piece 对象，设置其原始信息和当前网格位置
                        piece = Piece(piece_surface, img_id, orig_r, orig_c, r, c)
                        self.grid[r][c] = piece # Assign piece to grid position


                        # 将 Piece 逐个添加到 Sprite Group
                        # --- 最精确定位调试、安全检查和断言：在添加到 Group 之前 ---
                        # print(f"Board Debug: Piece ({r},{c}) from archive prepared to add to Group.") # Debug
                        # print(f"  Object Type: {type(piece)}, Is Sprite: {isinstance(piece, pygame.sprite.Sprite)}") # Debug
                        # Get image ID safely for logging (using piece object now)
                        piece_img_id = piece.original_image_id if hasattr(piece, 'original_image_id') else 'N/A'

                        # --- 关键断言：强制检查 Piece 对象是否是有效的 Sprite 并有 image/rect ---
                        try:
                            assert isinstance(piece, pygame.sprite.Sprite), f"致命错误: Board: 尝试添加到 Group 的对象不是 Sprite! 类型为 {type(piece)}. Piece Info: ID {piece_img_id}"
                            assert hasattr(piece, 'image') and isinstance(piece.image, pygame.Surface), f"致命错误: Board: 尝试添加的 Sprite 没有有效的 image 属性或不是 Surface! 类型为 {type(piece.image) if hasattr(piece, 'image') else '没有此属性'}. Piece Info: ID {piece_img_id}"
                            assert hasattr(piece, 'rect') and isinstance(piece.rect, pygame.Rect), f"致命错误: Board: 尝试添加的 Sprite 没有有效的 rect 属性或不是 Rect! 类型为 {type(piece.rect) if hasattr(piece, 'rect') else '没有此属性'}. Piece Info: ID {piece_img_id}"
                        except AssertionError as e:
                             # Catch AssertionError and raise it with more context
                             print(f"致命错误: {e}") # Print the detailed error from assertion
                             if hasattr(self.image_manager.game, '_display_fatal_error'):
                                 self.image_manager.game._display_fatal_error(f"存档加载碎片失败:\n{e}")
                             else:
                                 raise type(e)(f"{e} 发生在添加图片ID {piece_img_id} 的碎片到 Group 时 (存档加载)。") from e # Re-raise with context


                        # Check if self.all_pieces_group is indeed a Sprite Group before adding
                        if isinstance(self.all_pieces_group, pygame.sprite.Group):
                             # print(f"  Group Type: {type(self.all_pieces_group)}. Current size: {len(self.all_pieces_group)}") # Debug
                             try:
                                 # Use the standard Group.add method
                                 self.all_pieces_group.add(piece) # <-- Error might occur here!
                                 pieces_added_count += 1
                                 # print(f"Board: 成功添加存档碎片到 Group. Group大小: {len(self.all_pieces_group)}") # Debug
                             except Exception as e:
                                 # Catch other exceptions during add, provide context
                                 print(f"致命错误: Board: 将图片ID {piece_img_id} 的碎片添加到 Group 时发生异常 (在断言之后): {e}.") # Debug
                                 if hasattr(self.image_manager.game, '_display_fatal_error'):
                                     self.image_manager.game._display_fatal_error(f"添加碎片到Sprite Group失败 (存档加载):\n{e}")
                                 else:
                                     raise # Re-raise the exception

                        else:
                             print("致命错误: Board: self.all_pieces_group 不是 Sprite Group！无法添加碎片。")
                             if hasattr(self.image_manager.game, '_display_fatal_error'):
                                 self.image_manager.game._display_fatal_error("Sprite Group 初始化异常。")
                             else:
                                 import sys; pygame.quit(); sys.exit() # Exit if Group is fundamentally broken


                    except Exception as e:
                        # This catches exceptions during piece info extraction, Piece creation, or Group.add
                        # Get image ID safely from piece_info if available
                        err_img_id = piece_info.get('id') if isinstance(piece_info, dict) else 'N/A'
                        print(f"错误: Board: 加载存档碎片信息 (ID: {err_img_id}, 原始: {piece_info.get('orig_r')},{piece_info.get('orig_c')}) 或创建 Piece/添加到 Group 异常: {e}. 槽位 ({r},{c}) 将为空。") # Debug <-- 修改打印信息，安全获取id
                        self.grid[r][c] = None # 该槽位留空


                else:
                    # 槽位是空的 (None)，grid[r][c] 已经是 None 了，无需操作
                    pass

        print(f"Board: 从存档加载了 {pieces_added_count} 个碎片到拼盘 (成功创建Piece数量)。")

    def swap_pieces(self, pos1_grid, pos2_grid):
        """
        交换两个网格位置上的碎片。
        只会交换在 BOARD_STATE_PLAYING 状态下。
        只有当两个位置都在当前可放置区域内时才进行交换。

        Args:
            pos1_grid (tuple): 第一个碎片的网格坐标 (行, 列)
            pos2_grid (tuple): 第二个碎片的网格坐标 (行, 列)

        Returns:
            bool: True 如果交换成功，False 如果交换失败或当前Board状态不允许交换。
        """
        # 只有在 PLAYING 状态下才能交换碎片
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             # print("警告: Board 当前状态不允许交换碎片。") # 频繁打印可能影响性能
             return False

        r1, c1 = pos1_grid
        r2, c2 = pos2_grid

        # --- 关键修改：检查交换位置是否都在当前可放置区域内 ---
        # 获取当前可放置区域的物理 Rect
        playable_rect_grid = pygame.Rect(self.playable_offset_col, self.playable_offset_row, self.playable_cols, self.playable_rows)

        # 将网格坐标转换为可放置区域内的相对坐标，并检查是否在范围内
        # Alternatively, check if the physical grid coordinates (r, c) are contained within the playable_rect_grid
        pos1_in_playable = playable_rect_grid.collidepoint(c1, r1) # Pygame Rect collidepoint expects (x, y) -> (col, row) for grid
        pos2_in_playable = playable_rect_grid.collidepoint(c2, r2)

        # Check if both positions are within the playable area
        if not pos1_in_playable or not pos2_in_playable:
             # print(f"警告: Board: swap_pieces: 交换位置 ({r1},{c1}) 或 ({r2},{c2}) 不在可放置区域内。无法交换。") # Debug
             return False # Swap failed because one or both positions are outside the playable area


        # 确保坐标有效且在板子上 (物理范围，已在 utils 中检查过，但在 Board 层面再检查一次更安全)
        if not (0 <= r1 < settings.BOARD_ROWS and 0 <= c1 < settings.BOARD_COLS and
                0 <= r2 < settings.BOARD_ROWS and 0 <= c2 < settings.BOARD_COLS):
            # print(f"警告: Board: swap_pieces: 无效的物理网格位置 ({r1},{c1}) 或 ({r2},{c2})，无法交换。")
            return False # Swap failed

        piece1 = self.grid[r1][c1]
        piece2 = self.grid[r2][c2]

        # 检查至少有一个位置不是 None，否则交换没有意义
        if piece1 is None and piece2 is None:
             # print(f"警告: Board: swap_pieces: 交换位置 ({r1},{c1}) 和 ({r2},{c2}) 都为空槽位，不进行交换。")
             return False # Swap failed

        # 在网格中交换
        self.grid[r1][c1] = piece2
        self.grid[r2][c2] = piece1

        # 更新碎片自身的网格位置属性 (非动画方式，因为这是瞬间交换)
        if piece1:
            piece1.set_grid_position(r2, c2, animate=False)
        if piece2:
            piece2.set_grid_position(r1, c1, animate=False)

        # print(f"交换了碎片位置: ({r1},{c1}) 与 ({r2},{c2})") # 调试信息，频繁交换时打印信息太多

        # 交换成功后立即检查是否有图片完成
        self.check_and_process_completion()

        return True # 交换成功


    def select_piece(self, piece):
        """选中一个碎片 (用于点击交换模式)。"""
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return # 只在PLAYING状态下允许选中

        # --- 关键修改：检查选中的碎片是否在当前可放置区域内 ---
        piece_grid_pos = (piece.current_grid_row, piece.current_grid_col)
        # 获取当前可放置区域的物理 Rect
        playable_rect_grid = pygame.Rect(self.playable_offset_col, self.playable_offset_row, self.playable_cols, self.playable_rows)

        # 检查碎片所在的物理网格位置是否在可放置区域内
        if not playable_rect_grid.collidepoint(piece_grid_pos[1], piece_grid_pos[0]): # collidepoint expects (x, y) -> (col, row)
            # print(f"警告: Board: select_piece: 选中的碎片不在可放置区域内。忽略。") # Debug
            return # Cannot select piece outside playable area


        if self.selected_piece:
             # If a piece is already selected, unselect the previous one
             self.unselect_piece()

        self.selected_piece = piece
        # 计算选中高亮框的位置和大小，直接使用碎片的rect
        # 使用 inflate 和 topleft 计算边框位置
        border_thickness = 5 # 和 draw 中的一致
        self.selection_rect = piece.rect.inflate(border_thickness * 2, border_thickness * 2)
        # self.selection_rect.topleft = (piece.rect.left - border_thickness, piece.rect.top - border_thickness) # This is calculated in draw as well to stay in sync

        # print(f"选中碎片: 图片ID {piece.original_image_id}, 原始位置 ({piece.original_row},{piece.original_col}), 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def unselect_piece(self):
        """取消选中状态。"""
        self.selected_piece = None
        self.selection_rect = None # 移除选中高亮框
        # print("取消选中碎片。") # Debug


    def start_dragging(self, piece):
        """开始拖拽一个碎片。"""
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return # 只在PLAYING状态下允许拖拽

        # --- 关键修改：检查正在拖拽的碎片是否在当前可放置区域内 ---
        piece_grid_pos = (piece.current_grid_row, piece.current_grid_col)
        # 获取当前可放置区域的物理 Rect
        playable_rect_grid = pygame.Rect(self.playable_offset_col, self.playable_offset_row, self.playable_cols, self.playable_rows)

        # 检查碎片所在的物理网格位置是否在可放置区域内
        if not playable_rect_grid.collidepoint(piece_grid_pos[1], piece_grid_pos[0]): # collidepoint expects (x, y) -> (col, row)
            # print(f"警告: Board: start_dragging: 正在拖拽的碎片不在可放置区域内。忽略。") # Debug
            return # Cannot drag piece outside playable area


        self.dragging_piece = piece
        # 将正在拖拽的碎片从 Group 中移除，以便单独绘制它在最上层
        if self.dragging_piece in self.all_pieces_group:
             self.all_pieces_group.remove(self.dragging_piece)

        # print(f"开始拖拽碎片: 图片ID {piece.original_image_id}, 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # Debug


    def stop_dragging(self):
        """停止拖拽当前碎片。"""
        if self.dragging_piece:
            # print(f"停止拖拽碎片: 图片ID {self.dragging_piece.original_image_id}, 当前位置 ({self.dragging_piece.current_grid_row},{self.dragging_piece.current_grid_col})") # Debug
            # 将碎片放回其当前网格位置的精确屏幕坐标 (如果拖拽时位置有偏移的话)
            current_grid_pos = (self.dragging_piece.current_grid_row, self.dragging_piece.current_grid_col)
            # Note: Using animate=False here for instant snap to grid when dragging stops
            self.dragging_piece.set_grid_position(current_grid_pos[0], current_grid_pos[1], animate=False) # 停止拖拽瞬间归位

            # 将碎片加回 Sprite Group
            # Ensure the group is valid before adding
            if isinstance(self.all_pieces_group, pygame.sprite.Group) and self.dragging_piece not in self.all_pieces_group:
                 try:
                     self.all_pieces_group.add(self.dragging_piece)
                 except Exception as e:
                     print(f"致命错误: Board: 将停止拖拽的碎片添加到 Group 时发生异常: {e}.") # Debug
                     # Handle error, maybe exit or show error message

            self.dragging_piece = None


    def check_and_process_completion(self):
        """
        检查是否有图片完成，如果完成则触发处理流程。
        只在 BOARD_STATE_PLAYING 状态下执行检查。
        如果检测到完成，改变 Board 内部状态到 BOARD_STATE_PICTURE_COMPLETED。
        """
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return False # 只在PLAYING状态下检查

        completed_image_id = self.check_completion()
        if completed_image_id is not None:
            print(f"检测到图片 {completed_image_id} 完成了！触发处理流程。") # 调试信息

            # 设置 Board 内部状态为图片完成，等待处理
            self.current_board_state = settings.BOARD_STATE_PICTURE_COMPLETED
            self._completed_image_id_pending_process = completed_image_id
            # _completed_area_start_pos 已在 check_completion 中记录

            # 停止当前可能的交互 (取消选中，停止拖拽)
            self.unselect_piece()
            self.stop_dragging() # 这会把碎片归位

            # 通知 ImageManager 更新图片状态并记录完成时间 (在这里通知，因为完成了)
            self.image_manager.set_image_state(completed_image_id, 'lit')

            # === 关键修改：点亮图片数量增加 ===
            self.unlocked_pictures_count += 1
            print(f"点亮图片数量增加到: {self.unlocked_pictures_count}") # Debug

            # TODO: 可以在这里触发一个全局的游戏事件，比如播放音效，显示祝贺信息等
            # 可以通过 ImageManager 间接访问 Game 实例来调用 Game 的方法
            # if hasattr(self.image_manager.game, 'show_completion_effect'):
            #     self.image_manager.game.show_completion_effect(completed_image_id)

            return True # 有图片完成
        return False # 没有图片完成


    # 替换 check_completion 方法 (在可放置区域内检查完成，使用图片的独立逻辑尺寸)
    def check_completion(self):
        """
        检查拼盘中是否存在一个完整的 图片逻辑列数 x 图片逻辑行数 图片块。
        只在当前可放置区域内进行检查。
        返回已完成的图片ID，如果没有则返回None。
        如果找到，记录完成区域的左上角物理网格位置在 self._completed_area_start_pos。
        """
        print("Board: 检查拼盘中是否有完整的图片块...") # Debug informatio
        # 遍历所有可能的物理网格位置作为完成块的左上角
        # 这些位置必须位于当前可放置区域内
        # 物理起始行的范围: 从 self.playable_offset_row 到 self.playable_offset_row + self.playable_rows - 1
        # 物理起始列的范围: 从 self.playable_offset_col 到 self.playable_offset_col + self.playable_cols - 1
        # 但是，潜在完成块的右下角也必须在可放置区域内，这取决于图片的逻辑尺寸。

        # Get the playable area rect in physical grid coordinates
        playable_rect_grid = pygame.Rect(self.playable_offset_col, self.playable_offset_row, self.playable_cols, self.playable_rows)


        # 遍历可放置区域内的所有物理网格位置作为潜在完成块的左上角
        for start_row in range(self.playable_offset_row, self.playable_offset_row + self.playable_rows):
            for start_col in range(self.playable_offset_col, self.playable_offset_col + self.playable_cols):

                # 获取该位置的碎片
                top_left_piece = self.grid[start_row][start_col]

                # 如果左上角没有碎片，或者碎片的原始位置不是逻辑上的 (0,0)，则不可能从这里开始一个完整的图片
                if top_left_piece is None or top_left_piece.original_row != 0 or top_left_piece.original_col != 0:
                    continue # 检查下一个可能的起始位置

                # 确定要检查的目标图片ID
                target_image_id = top_left_piece.original_image_id

                # === 根据图片ID获取该图片的逻辑尺寸 ===
                if target_image_id not in self.image_manager.image_logic_dims:
                     print(f"警告: Board: check_completion: 图片ID {target_image_id} 逻辑尺寸配置缺失。跳过检查。") # Debug
                     continue # 如果图片的逻辑尺寸未知，无法检查完成

                img_logic_c, img_logic_r = self.image_manager.image_logic_dims[target_image_id] # 获取该图片的逻辑列数和行数

                # === 检查整个完成块是否完全位于当前可放置区域内 (只检查右下角是否超出) ===
                # 完成块的物理范围：从 (start_row, start_col) 到 (start_row + img_logic_r - 1, start_col + img_logic_c - 1)
                block_bottom_right_row = start_row + img_logic_r - 1
                block_bottom_right_col = start_col + img_logic_c - 1

                # Check if the bottom-right corner of the potential block is within the playable area boundaries
                if block_bottom_right_row >= self.playable_offset_row + self.playable_rows or \
                   block_bottom_right_col >= self.playable_offset_col + self.playable_cols:
                    # If the bottom-right corner is outside the playable area, this block cannot be complete within it
                    # print(f"Debug: Board: check_completion: 图片ID {target_image_id} 潜在完成块 ({start_row},{start_col}) 物理尺寸 {img_logic_r}x{img_logic_c} 右下角 ({block_bottom_right_row},{block_bottom_right_col}) 超出可放置区域。") # Debug
                    continue # Check next potential start position


                is_complete = True # 假设这个区域是一个完整的图片块

                # 遍历这个 img_logic_r 行 x img_logic_c 列 区域内的所有位置 (相对于起始点的偏移 dr, dc)
                for dr in range(img_logic_r): # 遍历逻辑行 (0 to img_logic_r - 1)
                    for dc in range(img_logic_c): # 遍历逻辑列 (0 to img_logic_c - 1)
                        current_row = start_row + dr # 对应的物理行
                        current_col = start_col + dc # 对应的物理列
                        # 确保检查在板子范围内 (应始终为真，因为我们遍历的可放置区域和块都在板子范围内)
                        # if not (0 <= current_row < settings.BOARD_ROWS and 0 <= current_col < settings.BOARD_COLS):
                        #     is_complete = False # Area extends beyond board (should not happen)
                        #     break
                        current_piece = self.grid[current_row][current_col]

                        # 检查当前位置是否有碎片
                        if current_piece is None:
                            is_complete = False
                            break # 该块不完整，跳出内层循环

                        # 检查碎片的原始信息是否与目标图片ID和预期的原始位置匹配
                        # 位于 (current_row, current_col) 的碎片应该是逻辑上原始位于 (dr, dc) 的碎片
                        if (current_piece.original_image_id != target_image_id or
                            current_piece.original_row != dr or
                            current_piece.original_col != dc):
                            is_complete = False
                            break # 信息不匹配，该块不完整，跳出内层循环

                    if not is_complete:
                        break # 如果内层循环发现不完整，跳出外层循环

                # 如果内层循环都通过，说明找到了一个完整的图片块
                if is_complete:
                    # 在返回图片ID之前，记录这个完成的区域的左上角物理网格位置
                    self._completed_area_start_pos = (start_row, start_col)
                    # print(f"Debug: Board: check_completion: 找到完成的图片ID {target_image_id} 在 ({start_row},{start_col})") # Debug
                    return target_image_id # 返回完成的图片ID

        return None # 遍历所有可能位置后没有找到完整的图片

    def _process_completed_picture(self):
        """
        处理已完成图片的流程状态机。
        根据 current_board_state 执行相应的步骤。
        这个方法在 Board 的 update 中被调用。
        """
        # print(f"Board: _process_completed_picture: 当前状态: {self.current_board_state}") # Debug - remove if too spammy

        if self.current_board_state == settings.BOARD_STATE_PICTURE_COMPLETED:
            # 状态：图片已检测完成，刚进入处理流程
            print(f"Board State: PICTURE_COMPLETED -> REMOVING_PIECES for image {self._completed_image_id_pending_process}") # 调试信息
            self.current_board_state = settings.BOARD_STATE_REMOVING_PIECES
            # 移除碎片 (瞬间完成)
            self.remove_completed_pieces()
            # 移除完成后，立即切换到下落状态并启动下落动画
            self.current_board_state = settings.BOARD_STATE_PIECES_FALLING
            self.initiate_fall_down_pieces()


        elif self.current_board_state == settings.BOARD_STATE_REMOVING_PIECES:
            # 状态：碎片正在移除动画中 (如果实现了的话)
            # print("Board State: REMOVING_PIECES - waiting for animation (if any)...") # Debug
            pass # Wait for potential removal animation


        elif self.current_board_state == settings.BOARD_STATE_PIECES_FALLING:
             # 状态：碎片正在下落动画中
             # 碎片下落动画的更新由 Piece 的 update 方法处理，并在 Board 的 update 中调用 group.update
             # 状态切换到 PENDING_FILL 在 Board.update 中检查 is_any_piece_falling() 实现
             pass # Wait for falling animation to complete


        elif self.current_board_state == settings.BOARD_STATE_PENDING_FILL:
            # 状态：碎片下落完成，等待填充或升级
            print("Board State: PENDING_FILL -> Checking for Upgrade...") # 调试信息

            # === 关键修改：检查是否需要升级可放置区域 ===
            # Add print before calling _get_next_playable_area_config
            print(f"Board: PENDING_FILL: 调用 _get_next_playable_area_config (unlocked={self.unlocked_pictures_count}, current area={self.playable_rows}x{self.playable_cols})...") # Debug
            next_upgrade_config = self._get_next_playable_area_config()
            # Add print after calling _get_next_playable_area_config
            print(f"Board: PENDING_FILL: _get_next_playable_area_config 返回: {next_upgrade_config}") # Debug

            if next_upgrade_config:
                # 需要升级
                print(f"Board State: PENDING_FILL -> UPGRADING_AREA (Next config: {next_upgrade_config})") # Debug
                self.current_board_state = settings.BOARD_STATE_UPGRADING_AREA # 切换到升级状态
                self._upgrade_target_config = next_upgrade_config # Store target config
                # 执行区域升级逻辑 (目前是瞬间完成)
                print("Board: PENDING_FILL: 进行区域升级...") # Debug
                self._upgrade_playable_area(next_upgrade_config)
                self._upgrade_target_config = None # Clear target config after use
                # 区域升级和碎片移动完成后，切换到 PLAYING 状态
                # fill_new_pieces 会在 BOARD_STATE_PLAYING 的 update 循环中被 check_and_process_completion 触发吗？
                # No, fill_new_pieces is called explicitly after the state transition completes the process.
                # Let's trigger fill *after* upgrade, and then transition to PLAYING.
                print("Board: PENDING_FILL: 区域升级完成，进行填充新区域...") # Debug
                self.fill_new_pieces() # Fill the new larger area
                print("Board: PENDING_FILL: 填充完成。切换回 PLAYING。") # Debug
                self.current_board_state = settings.BOARD_STATE_PLAYING # Final transition to PLAYING

            else:
                # 不需要升级，直接填充新碎片
                print("Board State: PENDING_FILL -> No upgrade needed. Proceeding with fill.") # Debug
                # Add print before calling fill_new_pieces
                print("Board: PENDING_FILL: 无需升级区域。进行填充。") # Debug
                self.fill_new_pieces() # Fill the empty slots in the current area
                # Add print after calling fill_new_pieces
                print("Board: PENDING_FILL: 填充完成。切换回 PLAYING。") # Debug
                # 填充完成后，切换回 PLAYING 状态
                self.current_board_state = settings.BOARD_STATE_PLAYING

            # 清理完成图片的记录 (在整个完成流程结束，状态切换到 PLAYING 之后)
            # This block should now be reached in both the upgrade and no-upgrade paths within PENDING_FILL
            if self.current_board_state == settings.BOARD_STATE_PLAYING:
                 self._completed_image_id_pending_process = None
                 self._completed_area_start_pos = None
                 # 通知 Gallery 图库需要刷新
                 if hasattr(self.image_manager.game, 'gallery'): # 检查Game实例是否有gallery属性
                     try:
                         # print("Board: 通知 Gallery 更新列表...") # Debug
                         self.image_manager.game.gallery._update_picture_list() # Update gallery list data
                     except Exception as e:
                         print(f"警告: Board: 无法通知 Gallery 更新列表: {e}") # Debug


        elif self.current_board_state == settings.BOARD_STATE_UPGRADING_AREA:
             # 状态：正在执行区域升级逻辑 (目前是瞬间完成)
             # This state handles the upgrade animation if implemented.
             # Currently, _upgrade_playable_area is called directly from PENDING_FILL,
             # so this state might not be active for long, or at all if upgrade is instant.
             # If upgrade had animation, the logic to check for animation completion
             # and transition to the next state (PENDING_FILL for fill) would be here.
             # For now, keep it simple, the transition out happens in the PENDING_FILL block after _upgrade_playable_area is called.
             pass # Wait for potential upgrade animation



    def remove_completed_pieces(self):
        """根据记录的 _completed_area_start_pos 和完成图片的逻辑尺寸，从 Board 中移除已完成图片的碎片。"""
        if self._completed_area_start_pos is None or self._completed_image_id_pending_process is None:
             print("错误: Board: remove_completed_pieces: 没有记录已完成区域或图片ID，无法移除碎片。")
             return

        start_row, start_col = self._completed_area_start_pos
        completed_image_id = self._completed_image_id_pending_process

        # === 关键修改：根据完成图片的ID获取其逻辑尺寸 ===
        if completed_image_id not in self.image_manager.image_logic_dims:
             print(f"致命错误: Board: remove_completed_pieces: 完成的图片ID {completed_image_id} 逻辑尺寸配置缺失。无法移除碎片。") # Debug
             # Reset pending completion state if cannot process
             self._completed_image_id_pending_process = None
             self._completed_area_start_pos = None
             return # Cannot remove if logic dims are unknown

        img_logic_c, img_logic_r = self.image_manager.image_logic_dims[completed_image_id] # 获取完成图片的逻辑尺寸

        print(f"Board: remove_completed_pieces: 移除图片 {completed_image_id} 在 ({start_row},{start_col}) 开始的 {img_logic_r}x{img_logic_c} 区域碎片...") # Debug

        pieces_to_remove_list = [] # 收集要移除的碎片对象

        # 遍历要移除的 img_logic_r 行 x img_logic_c 列 区域 based on the logical image dimensions
        for dr in range(img_logic_r): # 遍历逻辑行 (0 to img_logic_r - 1)
            for dc in range(img_logic_c): # 遍历逻辑列 (0 to img_logic_c - 1)
                r = start_row + dr # 对应的物理行
                c = start_col + dc # 对应的物理列
                # 确保坐标在板子范围内 (应始终为真，因为 check_completion 已经检查了范围)
                if 0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS:
                    piece_to_remove = self.grid[r][c]
                    # 再次检查碎片是否属于当前完成的图片 (安全检查)
                    # 检查原始行/列是否与逻辑区域的偏移匹配
                    if piece_to_remove and piece_to_remove.original_image_id == completed_image_id and \
                       piece_to_remove.original_row == dr and piece_to_remove.original_col == dc:
                         pieces_to_remove_list.append(piece_to_remove)
                         self.grid[r][c] = None # 将网格位置设为 None
                    # else:
                         # print(f"警告: Board: remove_completed_pieces: 尝试移除的区域 ({r},{c}) 没有属于完成图片 {completed_image_id} 的碎片或为空。") # Debug

        # 从 Sprite Group 中移除收集到的碎片
        # Ensure the group is valid before attempting remove
        if isinstance(self.all_pieces_group, pygame.sprite.Group):
            try:
                self.all_pieces_group.remove(*pieces_to_remove_list)
            except Exception as e:
                print(f"致命错误: Board: 从 Group 中移除已完成碎片时发生异常: {e}.") # Debug
                # Handle error

        # TODO: 可以添加一个效果，让移除的碎片消失或爆炸等 (可选)


    # 新增方法：检查是否满足可放置区域升级条件
    def _get_next_playable_area_config(self):
        """
        检查当前点亮图片数量是否满足下一个可放置区域升级阈值。

        Returns:
            dict or None: 如果需要升级，返回下一个区域配置字典；否则返回 None。
        """
        print(f"Board: _get_next_playable_area_config: unlocked={self.unlocked_pictures_count}, current area={self.playable_rows}x{self.playable_cols}") # Debug

        # 获取当前的可放置区域尺寸
        current_cols = self.playable_cols
        current_rows = self.playable_rows

        # 按阈值升序遍历 PLAYABLE_AREA_CONFIG
        # Ensure keys (thresholds) are sorted
        sorted_thresholds = sorted(settings.PLAYABLE_AREA_CONFIG.keys())

        # Find the threshold of the current area config
        current_config_threshold = -1 # Use -1 as a placeholder for a state below the first defined threshold (0)
        found_current_config = False
        for threshold, config in settings.PLAYABLE_AREA_CONFIG.items():
             # Check if the current area's size matches this config's size
             if config['cols'] == current_cols and config['rows'] == current_rows:
                  current_config_threshold = threshold # Found the threshold corresponding to the current area size
                  found_current_config = True
                  # print(f"Board: _get_next_playable_area_config: 找到当前区域 ({current_rows}x{current_cols}) 对应的阈值: {current_config_threshold}") # Debug
                  break # Found the current config, no need to check other thresholds


        # If current area size doesn't match any config size (shouldn't happen if initialized correctly)
        if not found_current_config:
             print(f"错误: Board: _get_next_playable_area_config: 当前区域尺寸 {self.playable_rows}x{self.playable_cols} 不匹配任何 PLAYABLE_AREA_CONFIG 配置。无法检查升级。") # Debug
             return None # Cannot determine upgrade path

        # Now, iterate through sorted thresholds again, looking for an upgrade
        print(f"Board: _get_next_playable_area_config: 遍历阈值寻找升级 (当前阈值={current_config_threshold}, 已点亮={self.unlocked_pictures_count})...") # Debug
        for threshold in sorted_thresholds:
             print(f"  检查阈值: {threshold}") # Debug
             # Only consider thresholds that are STRICTLY GREATER than the threshold of our current area
             if threshold > current_config_threshold:
                  print(f"    阈值 {threshold} 大于当前阈值 {current_config_threshold}.") # Debug
                  # Check if this threshold's unlocked picture requirement is MET or EXCEEDED
                  if threshold <= self.unlocked_pictures_count:
                       config = settings.PLAYABLE_AREA_CONFIG[threshold]
                       print(f"    阈值 {threshold} <= 已点亮数量 {self.unlocked_pictures_count}. 满足升级条件.") # Debug
                       # Check if this new config is actually larger than the current one (area size)
                       # This check is implicitly covered by "threshold > current_config_threshold" if config sizes are strictly increasing with threshold.
                       # However, configs might have the same size but different thresholds, or sizes might not be strictly monotonic.
                       # Let's explicitly check if the size is different and larger to be safe.
                       # A config is "larger" if it has more slots (cols * rows).
                       current_slots = current_cols * current_rows
                       new_slots = config['cols'] * config['rows']
                       if new_slots > current_slots:
                            # Found the *next* relevant upgrade config: smallest threshold > current, whose threshold is met, and whose area is larger.
                            print(f"    找到下一个升级目标配置: 阈值 {threshold}, 尺寸 {config['rows']}x{config['cols']}") # Debug
                            return config # Return this config as the target for upgrade
                       else:
                            print(f"    阈值 {threshold} 的配置尺寸 {config['rows']}x{config['cols']} ({new_slots} 槽位) 不大于当前尺寸 {current_rows}x{current_cols} ({current_slots} 槽位)。跳过。") # Debug
                  else:
                       print(f"    阈值 {threshold} > 已点亮数量 {self.unlocked_pictures_count}. 未满足升级条件。") # Debug
                       # Since thresholds are sorted, if this threshold is not met, no subsequent thresholds will be met either (assuming thresholds are non-decreasing)
                       # However, the user's config shows thresholds 0, 1, 3, 6, 10 which are non-decreasing.
                       # Let's keep iterating just in case there's a valid config with a higher threshold but we missed something.
                       pass # Continue checking higher thresholds if needed, though unlikely to find a met threshold


        # If the loop finishes without finding a larger config whose threshold is met
        print("Board: _get_next_playable_area_config: 未找到满足条件的下一个升级配置。") # Debug
        return None # No upgrade needed


    # 新增方法：执行可放置区域升级
    def _upgrade_playable_area(self, next_config):
        """
        执行可放置区域升级：移动现有碎片，设置新区域尺寸，加载新背景图。

        Args:
            next_config (dict): 下一个可放置区域的配置字典 {'cols', 'rows', 'bg'}。
        """
        print(f"Board: 开始区域升级到尺寸 {next_config['cols']}x{next_config['rows']}...") # Debug

        old_cols = self.playable_cols
        old_rows = self.playable_rows
        old_offset_col = self.playable_offset_col
        old_offset_row = self.playable_offset_row

        new_cols = next_config['cols']
        new_rows = next_config['rows']
        new_bg_name = next_config['bg']

        # 1. 计算新的可放置区域尺寸和偏移
        # This is already handled by _set_playable_area, but let's calculate here first
        new_offset_col = (settings.BOARD_COLS - new_cols) // 2
        new_offset_row = (settings.BOARD_ROWS - new_rows) // 2


        # 2. 移动所有现有的碎片到新区域的对应位置
        # Iterate through the old grid and move pieces if they exist
        pieces_to_move = []
        for r in range(settings.BOARD_ROWS):
             for c in range(settings.BOARD_COLS):
                  piece = self.grid[r][c]
                  if piece is not None:
                       # This piece is currently at physical grid (r, c)
                       pieces_to_move.append(piece) # Collect pieces


        # Temporarily clear the grid while moving
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]

        # Calculate new positions and place pieces in the new grid
        for piece in pieces_to_move:
             # Get piece's old physical grid position
             old_r = piece.current_grid_row
             old_c = piece.current_grid_col

             # Calculate its position relative to the OLD playable area's top-left offset
             # This is needed if the old area wasn't at (0,0) in the physical grid
             relative_old_r = old_r - old_offset_row
             relative_old_c = old_c - old_offset_col

             # Check if the piece was actually INSIDE the OLD playable area
             # Pieces outside the old area are NOT moved relative to the old area.
             # They should probably stay at their absolute physical position, or maybe moved to the edge of the new area?
             # Design says "全部已有图片保持相对位置不变，移动到左下角" - this implies only pieces *within* the old area matter for relative movement.
             # Pieces outside should perhaps be removed? Or handled differently?
             # Let's assume only pieces *inside* the old playable area are moved relative to it.
             # Pieces outside the old playable area are either removed or remain in place (and might become inside the new area).
             # Given the "all existing pieces" phrasing, perhaps *all* pieces in the grid are moved if they were within the OLD area?
             # Let's assume for simplicity now: pieces are moved IF their old position was inside the OLD playable area.
             # Any pieces outside the OLD playable area remain in place (if their position is still valid on the BOARD).

             # Let's re-read: "全部已有图片保持相对位置不变，移动到左下角" - this likely means all pieces *that are currently on the board*
             # and were located within the *previous* playable area rectangle should be shifted.
             # Pieces that were outside the previous playable area should probably stay where they are, if that position is still on the board.
             # However, the most common scenario is pieces are only ever *in* the playable area.
             # Let's assume "全部已有图片" means all pieces currently in self.all_pieces_group (which should only be pieces in the grid).
             # And "保持相对位置不变" means relative to some point. "移动到左下角" suggests aligning with the *new* area's bottom-left.

             # Let's go with the calculation: A piece at (old_r, old_c) within the OLD area
             # moves to (new_r, new_c) within the NEW area, keeping its relative position.
             # relative_to_old_top_left = (old_r - old_offset_row, old_c - old_offset_col)
             # target_new_r = new_offset_row + relative_to_old_top_left[0] # Aligning top-left
             # target_new_c = new_offset_col + relative_to_old_top_left[1] # Aligning top-left

             # To align BOTTOM-LEFT:
             # Piece's position relative to the OLD area's BOTTOM-LEFT:
             # relative_to_old_bottom_left_r = old_r - (old_offset_row + old_rows - 1) # Negative value
             # relative_to_old_bottom_left_c = old_c - old_offset_col # Positive value
             # New target position relative to the NEW area's BOTTOM-LEFT:
             # target_new_r = (new_offset_row + new_rows - 1) + relative_to_old_bottom_left_r
             # target_new_c = new_offset_col + relative_to_old_bottom_left_c

             # Substitute and simplify:
             # target_new_r = new_offset_row + new_rows - 1 + old_r - old_offset_row - old_rows + 1
             # target_new_r = new_offset_row + new_rows - old_rows + old_r - old_offset_row
             # target_new_c = new_offset_col + old_c - old_offset_col

             # This formula applies to pieces that *were* in the old playable area.
             # What about pieces *outside* the old playable area? They shouldn't move relative to the old area.
             # If a piece's old position (old_r, old_c) was outside the old playable area, it should just stay at (old_r, old_c)
             # UNLESS that position is now outside the BOARD or inside the new playable area.
             # The simplest interpretation of "全部已有图片保持相对位置不变，移动到左下角" is that *all pieces currently in the grid*
             # are conceptually part of the "puzzle block" that is being shifted.
             # Let's apply the relative shift based on the OLD playable area's top-left, BUT then shift the *entire block*
             # so that its bottom-left aligns with the NEW playable area's bottom-left.

             # Let's calculate the shift needed to align the old area's bottom-left with the new area's bottom-left
             # Old bottom-left physical grid: (old_offset_row + old_rows - 1, old_offset_col)
             # New bottom-left physical grid: (new_offset_row + new_rows - 1, new_offset_col)
             # Row shift: (new_offset_row + new_rows - 1) - (old_offset_row + old_rows - 1) = new_offset_row + new_rows - old_offset_row - old_rows
             # Col shift: new_offset_col - old_offset_col

             # Apply this shift to EVERY piece's current physical grid position (old_r, old_c)
             # New physical grid position (new_r, new_c):
             new_r = old_r + (new_offset_row + new_rows - old_offset_row - old_rows)
             new_c = old_c + (new_offset_col - old_offset_col)

             # Check if the new position is still on the board
             if 0 <= new_r < settings.BOARD_ROWS and 0 <= new_c < settings.BOARD_COLS:
                  # Place the piece at the new position in the grid
                  # Ensure the target slot is empty (should be after grid clear)
                  if self.grid[new_r][new_c] is None:
                       self.grid[new_r][new_c] = piece
                       # Update the piece's position (no animation for upgrade move)
                       piece.set_grid_position(new_r, new_c, animate=False)
                  else:
                       # This should not happen if we cleared the grid, indicates a logic error
                       print(f"致命错误: Board: _upgrade_playable_area: 尝试将碎片 {piece.original_image_id}_{piece.original_row}_{piece.original_col} 移动到 ({new_r},{new_c})，但该位置已被占用。") # Debug
                       # Handle error: maybe remove piece or exit
                       # For now, let's just print error and skip placing this piece to avoid crashing
                       pass # Piece is lost

             else:
                  # Piece moved outside the board, remove it
                  print(f"警告: Board: _upgrade_playable_area: 碎片 {piece.original_image_id}_{piece.original_row}_{piece.original_col} 从 ({old_r},{old_c}) 移动到 ({new_r},{new_c})，超出板子范围。移除。") # Debug
                  # Remove from the group if it was still there (it shouldn't be as we collected all pieces)
                  # if piece in self.all_pieces_group:
                  #      self.all_pieces_group.remove(piece)
                  # Piece is lost (not placed in grid or group)


        # 3. 设置新的可放置区域尺寸和偏移 (更新 Board 属性)
        # This must be done AFTER calculating new positions relative to the OLD offsets.
        self._set_playable_area(new_cols, new_rows)


        # 4. 加载并显示新的背景图
        self._load_background_image(new_bg_name)

        print("Board: 区域升级完成。") # Debug


    def initiate_fall_down_pieces(self):
        """启动碎片下落动画：计算所有碎片的最终目标位置，并标记它们为正在下落"""
        # print("启动碎片下落动画...") # Debug
        # 遍历每一列，确定每个非空碎片的最终下落位置
        # === 关键修改：只在当前可放置区域内处理下落 ===
        # Calculate the playable area boundaries in physical grid coordinates
        playable_row_start = self.playable_offset_row
        playable_row_end = self.playable_offset_row + self.playable_rows # Exclusive
        playable_col_start = self.playable_offset_col
        playable_col_end = self.playable_offset_col + self.playable_cols # Exclusive


        for c in range(playable_col_start, playable_col_end): # 遍历可放置区域内的列
            # bottom_row_index_to_fill 是指在当前可放置区域的这一列中，最底部的空位对应的物理行索引
            # 它从可放置区域的底行开始向上查找
            # Note: The empty slots are created by removing completed pieces.
            # Pieces *above* these empty slots within the playable area need to fall down.
            # Pieces *below* the playable area are not affected.
            # Pieces *outside* the playable area are also not affected by this fall.

            # Iterate from the bottom of the playable area upwards
            # Find pieces within this column AND within the playable rows
            pieces_in_column_within_playable_area = []
            for r in range(playable_row_end - 1, playable_row_start - 1, -1): # 从可放置区域底行向上遍历
                 if self.grid[r][c] is not None:
                     pieces_in_column_within_playable_area.append(self.grid[r][c])
                     self.grid[r][c] = None # 先将原位置设为None


            # Now, refill the column from the bottom of the playable area with the collected pieces
            current_row_to_fill = playable_row_end - 1 # Start filling from the bottom row of the playable area
            for piece in pieces_in_column_within_playable_area:
                 # Place the piece at the new physical grid position
                 self.grid[current_row_to_fill][c] = piece
                 # Update the piece's grid position and initiate fall animation to the new physical row's screen Y coordinate
                 # Piece's set_grid_position calculates the screen position based on the provided grid coordinates
                 piece.set_grid_position(current_row_to_fill, c, animate=True)
                 current_row_to_fill -= 1 # Move upwards to the next row for the next piece


        # The animation's actual update is handled by each Piece's update method, called by the Sprite Group's update in Board.update


    def is_any_piece_falling(self):
        """检查是否有任何碎片正在下落动画中"""
        # 遍历 Sprite Group 中的所有碎片，检查 is_falling 属性
        # Ensure the group is valid before iterating
        if isinstance(self.all_pieces_group, pygame.sprite.Group):
             for piece in self.all_pieces_group:
                  # Ensure the object is a Piece before accessing is_falling
                  if isinstance(piece, Piece):
                       if piece.is_falling:
                           return True
                  # else: print(f"警告: Sprite Group 中包含非 Piece 对象: {type(piece)}") # Debug invalid object

        return False


    def fill_new_pieces(self):
        """
        根据填充规则，从 image_manager 获取新碎片填充当前可放置区域内的空位。
        同时更新新进入拼盘的图片状态为 'unlit'。
        """
        print("Board: 触发填充新碎片...") # Debug
        # 统计当前可放置区域内有多少个空槽位 (即网格中为 None 的位置)
        empty_slots_positions = [] # 记录空槽位的位置 (从上往下，从左往右遍历可放置区域获取)

        # Calculate the playable area boundaries in physical grid coordinates
        playable_row_start = self.playable_offset_row
        playable_row_end = self.playable_offset_row + self.playable_rows # Exclusive
        playable_col_start = self.playable_offset_col
        playable_col_end = self.playable_offset_col + self.playable_cols # Exclusive


        # Iterate through the playable area rows and columns to find empty slots
        for r in range(playable_row_start, playable_row_end):
            for c in range(playable_col_start, playable_col_end):
                # Ensure in physical board range (should be true by definition of playable area being subset)
                # if 0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS: # Redundant check
                if self.grid[r][c] is None:
                     empty_slots_positions.append((r, c)) # Record empty slot position

        empty_slots_count = len(empty_slots_positions)
        print(f"Board: 检测到可放置区域内有 {empty_slots_count} 个空槽位需要填充。") # Debug

        if empty_slots_count == 0:
             # print("Board: 没有空槽位需要填充。") # Debug
             return

        # 从 ImageManager 获取相应数量的新碎片
        # ImageManager.get_next_fill_pieces 会根据内部消耗进度和需要的数量提供碎片
        # It will provide UP TO the requested count, depending on loaded pieces availability
        new_pieces = self.image_manager.get_next_fill_pieces(empty_slots_count)
        print(f"Board: ImageManager 提供了 {len(new_pieces)} 个新碎片用于填充。") # Debug

        # 将新碎片放置到可放置区域内的空槽位中
        # The empty_slots_positions list is already ordered top-to-bottom, left-to-right within the playable area.
        # We place the new pieces into these slots in that order.
        # The new pieces should then fall into their final positions.
        pieces_placed_count = 0
        for i, piece in enumerate(new_pieces):
             if i < len(empty_slots_positions):
                 r, c = empty_slots_positions[i] # Get an empty slot's physical grid position

                 # === 关键修改：检查新填充碎片所属图片的当前状态，如果是 'unentered' 则更新为 'unlit' ===
                 img_id = piece.original_image_id
                 current_status = self.image_manager.image_status.get(img_id, 'unentered')
                 if current_status == 'unentered':
                      print(f"Board: 碎片来自图片ID {img_id}，首次入场，更新状态为 'unlit'。") # Debug
                      self.image_manager.set_image_state(img_id, 'unlit') # 更新图片状态

                 # Set the piece's initial temporary position *above* the board
                 # This is so they can fall into their target slot
                 # Calculate the target final screen position
                 target_screen_x = settings.BOARD_OFFSET_X + c * settings.PIECE_WIDTH
                 target_screen_y = settings.BOARD_OFFSET_Y + r * settings.PIECE_HEIGHT

                 # Calculate the screen position corresponding to the *starting* grid position for fall animation
                 # Start one row above playable area's top, or row 0 if playable area starts at row 0
                 initial_r = max(0, playable_row_start - 1)
                 initial_c = c # Same column as target
                 initial_piece_screen_x = settings.BOARD_OFFSET_X + initial_c * settings.PIECE_WIDTH
                 initial_piece_screen_y = settings.BOARD_OFFSET_Y + initial_r * settings.PIECE_HEIGHT


                 # Assign piece to grid position (its final logical place)
                 self.grid[r][c] = piece
                 # Update piece's internal grid pos immediately
                 piece.current_grid_row = r
                 piece.current_grid_col = c

                 # Set the piece's rect to the *initial* screen position for animation
                 piece.rect.topleft = (initial_piece_screen_x, initial_piece_screen_y) # Start position for fall animation

                 # Tell the piece its *target* final position and start the animation
                 piece.fall_target_y = target_screen_y
                 piece.is_falling = True # Start falling animation

                 # === 将新创建的 Piece 对象添加到 Sprite Group 并启动下落动画 ===
                 # 将新碎片添加到 Sprite Group
                 if isinstance(self.all_pieces_group, pygame.sprite.Group) and piece not in self.all_pieces_group:
                     try:
                         self.all_pieces_group.add(piece) # Add to group
                     except Exception as e:
                          print(f"致命错误: Board: 将新填充的碎片添加到 Group 时发生异常: {e}.") # Debug
                          # Handle error

                 pieces_placed_count += 1
             else:
                 print(f"警告: Board: 有多余的新碎片 ({len(new_pieces)} 个) 但没有足够的空槽位 ({empty_slots_count} 个) 来放置。") # Debug
                 break # No more empty slots in the playable area


        if pieces_placed_count < empty_slots_count:
            print(f"警告: Board: 需要 {empty_slots_count} 个碎片，但 ImageManager 只提供了 {len(new_pieces)} 个。可放置区域将会有空位。") # Debug


    # 替换 draw 方法 (绘制背景图和可放置区域指示层，只绘制区域内碎片)
    def draw(self, surface):
        """在指定的surface上绘制拼盘的背景图、可放置区域指示层、碎片、选中效果和 debug 信息。"""
        # 绘制背景图 (如果存在)
        if self.background_image:
             surface.blit(self.background_image, (0, 0)) # 背景图覆盖整个屏幕


        # 绘制可放置区域的指示图层 (半透明黑色矩形)
        # === 关键修改：使用 get_playable_area_rect 获取当前可放置区域的 Rect ===
        playable_area_rect_physical = self.get_playable_area_rect()

        # 创建一个半透明 Surface 用于绘制覆盖层
        overlay_surface = pygame.Surface(playable_area_rect_physical.size, pygame.SRCALPHA)
        overlay_surface.fill(settings.PLAYABLE_AREA_OVERLAY_COLOR) # 使用设定的带透明度的颜色
        surface.blit(overlay_surface, playable_area_rect_physical.topleft) # 绘制到可放置区域的位置


        # 绘制所有非拖拽中的碎片
        # Temporarily remove the dragging piece from the group to draw it on top later
        # Ensure the group is valid before attempting remove/add
        if isinstance(self.all_pieces_group, pygame.sprite.Group):
            if self.dragging_piece and self.dragging_piece in self.all_pieces_group:
                 self.all_pieces_group.remove(self.dragging_piece)

            # === 关键修改：只绘制位于当前可放置区域内的碎片 (或与区域相交的碎片，例如下落中) ===
            # Create a temporary group containing only sprites within or intersecting the playable area rect
            playable_pieces_group = pygame.sprite.Group()
            for piece in self.all_pieces_group:
                 # Ensure it's a Piece object before accessing rect/other attributes
                 if isinstance(piece, Piece):
                      # Check if the piece's rect intersects the playable area rect
                      if piece.rect.colliderect(playable_area_rect_physical):
                          playable_pieces_group.add(piece)
                 # else: print(f"警告: Sprite Group 中包含非 Piece 对象: {type(piece)}") # Debug invalid object

            # 绘制 Group 中位于可放置区域内的所有 Sprite
            playable_pieces_group.draw(surface)


        # 绘制选中碎片的特殊效果 (例如绘制边框)
        if self.selected_piece and self.selection_rect:
             # Ensure highliight position is synced with the selected piece's rect
             # We can also check if the selected piece is still within the playable area before drawing highlight
             piece_grid_pos = (self.selected_piece.current_grid_row, self.selected_piece.current_grid_col)
             playable_rect_grid = pygame.Rect(self.playable_offset_col, self.playable_offset_row, self.playable_cols, self.playable_rows)
             if playable_rect_grid.collidepoint(piece_grid_pos[1], piece_grid_pos[0]): # collidepoint expects (x, y) -> (col, row)

                 border_thickness = 5
                 # Recalculate selection_rect position based on the selected piece's current screen position
                 self.selection_rect.topleft = (self.selected_piece.rect.left - border_thickness, self.selected_piece.rect.top - border_thickness)
                 self.selection_rect.size = (self.selected_piece.rect.width + border_thickness * 2, self.selected_piece.rect.height + border_thickness * 2)
                 # Draw the selection border
                 pygame.draw.rect(surface, settings.HIGHLIGHT_COLOR, self.selection_rect, 5) # Draw border with thickness=5


        # 最后绘制正在拖拽的碎片，使其显示在最上层
        if self.dragging_piece:
             # InputHandler updates the dragging_piece.rect.center in MOUSEMOTION
             # Ensure dragging piece is also drawn if it's within or near the playable area (optional check)
             # if self.dragging_piece.rect.colliderect(playable_area_rect_physical): # Only draw dragging if near playable area? Or always draw if dragging? Let's always draw if dragging.
             if isinstance(self.dragging_piece, Piece): # Safety check
                  self.dragging_piece.draw(surface)
             # else: print(f"警告: dragging_piece 不是 Piece 对象: {type(self.dragging_piece)}") # Debug

        # Draw debug piece info if the debug flag is set in Game
        # Through ImageManager, access Game instance and debug font
        if hasattr(self.image_manager.game, 'display_piece_info') and self.image_manager.game.display_piece_info:
             if hasattr(self.image_manager.game, 'font_debug') and self.image_manager.game.font_debug:
                 debug_font = self.image_manager.game.font_debug
                 # Iterate through the grid (or all pieces group) to draw text on each piece
                 # Only draw debug info for pieces within the playable area (or all if needed)
                 # Let's iterate through the grid for pieces that are logically placed
                 for r in range(settings.BOARD_ROWS):
                      for c in range(settings.BOARD_COLS):
                           piece = self.grid[r][c] # Get piece from grid
                           if piece and isinstance(piece, Piece): # Ensure it's a Piece
                                # Only draw debug for pieces whose grid position is within the playable area
                                if playable_area_rect_physical.collidepoint(*utils.grid_to_screen(r, c)): # Check if piece's grid position is visually within the playable area
                                     # Format the debug text (Image ID, Original Row, Original Column, Current Grid)
                                     debug_text = f"ID:{piece.original_image_id} ({piece.original_row},{piece.original_col}) [{piece.current_grid_row},{piece.current_grid_col}]"
                                     # Render the text
                                     text_surface = debug_font.render(debug_text, True, settings.DEBUG_TEXT_COLOR)
                                     # Position the text, e.g., centered on the piece's rect
                                     text_rect = text_surface.get_rect(center=piece.rect.center) # Use piece's actual rect center
                                     # Draw the text
                                     surface.blit(text_surface, text_rect)

                 # Also draw info for the dragging piece if it's active and not in the group
                 # The dragging piece's rect is updated by InputHandler
                 if self.dragging_piece and isinstance(self.dragging_piece, Piece) and self.dragging_piece not in self.all_pieces_group:
                      # We can draw debug info for the dragging piece regardless of its grid position, centered on its rect
                      debug_text = f"ID:{self.dragging_piece.original_image_id} ({self.dragging_piece.original_row},{self.dragging_piece.original_col}) [{self.dragging_piece.current_grid_row},{self.dragging_piece.current_grid_col}]"
                      text_surface = debug_font.render(debug_text, True, settings.DEBUG_TEXT_COLOR)
                      text_rect = text_surface.get_rect(center=self.dragging_piece.rect.center) # Use dragging piece's actual rect center
                      surface.blit(text_surface, text_rect)


        # Add the dragging piece back to the group after drawing
        if isinstance(self.all_pieces_group, pygame.sprite.Group):
            if self.dragging_piece and self.dragging_piece not in self.all_pieces_group:
                 try:
                     self.all_pieces_group.add(self.dragging_piece)
                 except Exception as e:
                      print(f"致命错误: Board: 将拖拽完的碎片添加到 Group 时发生异常: {e}.") # Debug
                      # Handle error


    def update(self, dt):
         """
         更新Board的状态，包括处理完成流程和碎片下落动画。

         Args:
             dt (float): 自上一帧以来的时间（秒）
         """
         # 更新所有碎片的动画 (特别是正在下落的碎片)
         # 即使 Board 状态不是 FALLING，也需要更新，因为 Board 可能会在 PLAYING 状态下突然切换到 FALLING
         # 碎片 Piece 的 update 方法会根据自身的 is_falling 属性决定是否移动
         # Ensure the group is valid before updating
         if isinstance(self.all_pieces_group, pygame.sprite.Group):
             self.all_pieces_group.update(dt) # Update all sprites in the group

         # 如果 Board 状态是 FALLING，检查是否所有碎片都已停止下落，然后切换状态
         if self.current_board_state == settings.BOARD_STATE_PIECES_FALLING:
              if not self.is_any_piece_falling():
                   print("Board: 所有碎片下落完成。状态切换到 PENDING_FILL。") # Debug
                   self.current_board_state = settings.BOARD_STATE_PENDING_FILL # 切换状态，等待填充


         # 如果 Board 状态不是 PLAYING，则调用 _process_completed_picture 处理状态机
         # Note: The transition from PIECES_FALLING to PENDING_FILL happens above.
         # The handling of PENDING_FILL and subsequent states happens here.
         if self.current_board_state in [settings.BOARD_STATE_PICTURE_COMPLETED,
                                         settings.BOARD_STATE_REMOVING_PIECES,
                                         settings.BOARD_STATE_PENDING_FILL, # Handle PENDING_FILL here
                                         settings.BOARD_STATE_UPGRADING_AREA]: # Handle UPGRADING_AREA here
              self._process_completed_picture() # 处理完成流程状态机


    def get_piece_at_grid(self, row, col):
         """获取指定物理网格位置的碎片对象，或None"""
         if 0 <= row < settings.BOARD_ROWS and 0 <= col < settings.BOARD_COLS:
             return self.grid[row][col]
         return None # 坐标无效

    # 替换 get_board_rect 方法 (返回物理拼盘的总 Rect)
    def get_board_rect(self):
        """返回物理拼盘区域在屏幕上的Rect"""
        return pygame.Rect(settings.BOARD_OFFSET_X, settings.BOARD_OFFSET_Y,
                           settings.BOARD_COLS * settings.PIECE_WIDTH, # <-- 使用 PIECE_WIDTH
                           settings.BOARD_ROWS * settings.PIECE_HEIGHT) # <-- 使用 PIECE_HEIGHT


    # 新增方法：获取当前可放置区域的物理 Rect
    def get_playable_area_rect(self):
        """返回当前可放置区域在屏幕上的Rect"""
        return pygame.Rect(
            settings.BOARD_OFFSET_X + self.playable_offset_col * settings.PIECE_WIDTH, # X 像素位置
            settings.BOARD_OFFSET_Y + self.playable_offset_row * settings.PIECE_HEIGHT, # Y 像素位置
            self.playable_cols * settings.PIECE_WIDTH, # 宽度 (像素)
            self.playable_rows * settings.PIECE_HEIGHT # 高度 (像素)
        )


    # 替换 get_state 方法 (保存可放置区域信息和背景图名)
    def get_state(self):
        """
        获取当前 Board 的状态信息。
        包括拼盘布局（物理网格）、可放置区域信息、点亮数量、背景图名。

        Returns:
            dict: 包含 Board 状态的字典。
        """
        saved_grid = []
        for r in range(settings.BOARD_ROWS):
            row_data = []
            for c in range(settings.BOARD_COLS):
                piece = self.grid[r][c]
                if piece:
                    # 保存碎片的原始信息，用于重建Piece对象
                    piece_info = {
                        'id': piece.original_image_id,
                        'orig_r': piece.original_row,
                        'orig_c': piece.original_col
                    }
                    row_data.append(piece_info)
                else:
                    row_data.append(None) # 保存 None 表示空槽位
            saved_grid.append(row_data)

        # Get current background image name (if loaded)
        # The _current_background_name attribute should store the name used to load.
        # self.current_background_name is calculated in _load_background_image

        board_state = {
            'grid_layout': saved_grid,
            'playable_cols': self.playable_cols,
            'playable_rows': self.playable_rows,
            # Offsets are calculated based on cols/rows and board size, no need to save
            # 'playable_offset_col': self.playable_offset_col,
            # 'playable_offset_row': self.playable_offset_row,
            'unlocked_pictures_count': self.unlocked_pictures_count,
            'background_name': self._current_background_name # <-- Save background name
        }

        return board_state