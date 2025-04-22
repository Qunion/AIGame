# board.py
# 管理拼盘的状态、碎片布局、交换、完成检测、动态填充及动画

from ast import Return
import pygame
import settings
import random # 用于随机打乱碎片
import time # 用于计时
from piece import Piece # 导入Piece类
# from image_manager import ImageManager # image_manager 在 __init__ 中传入了
# from main import Game # Board 可能需要 Game 实例来触发状态改变 (如图片完成提示)
import utils # 导入工具函数


class Board:
    def __init__(self, image_manager, saved_grid_data=None): # <-- 新的方法签名
        """
        初始化拼盘

        Args:
            image_manager (ImageManager): 图像管理器实例
            saved_grid_data (list, optional): 从存档中加载的拼盘布局数据。如果为None，则进行初始填充。默认为None。
        """
        self.image_manager = image_manager
        # self.game = game_instance # 持有Game实例引用，用于调用Game方法

        # 存储拼盘中的碎片，使用二维列表表示物理网格 (16x9)
        # 列表中的元素将是 Piece 对象或 None (表示空槽位)
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]

        # 选中的碎片 (用于点击交换)
        self.selected_piece = None

        # 正在拖拽的碎片
        self.dragging_piece = None

        # 选中碎片的视觉反馈 Rect (直接绘制即可，不与碎片对象关联)
        self.selection_rect = None

        # Board内部状态，管理完成 -> 移除 -> 下落 -> 填充流程
        # 读档时，Board 状态应该回到 PLAYING
        self.current_board_state = settings.BOARD_STATE_PLAYING
        self._completed_image_id_pending_process = None # 完成的图片ID，等待处理
        self._completed_area_start_pos = None # 已完成区域的左上角网格位置

        # 用于管理所有 Piece Sprite 的 Group
        self.all_pieces_group = pygame.sprite.Group()
        # Group 的内容将在填充或加载拼盘时添加


        # 根据是否提供了存档数据来初始化拼盘
        if saved_grid_data is not None:
            # 从存档数据加载拼盘布局
            print("从存档加载拼盘布局...") # Debug
            self._load_grid_from_data(saved_grid_data)
        else:
            # 进行初始填充
            print("进行初始拼盘填充...") # Debug
            self.fill_initial_pieces()

        # 动画完成后的回调队列 (当下落动画完成后，需要触发填充等后续流程)
        self._animation_completion_callbacks = []

    def fill_initial_pieces(self):
        """根据settings填充初始碎片并随机打乱"""
        initial_pieces = self.image_manager.get_initial_pieces_for_board()

        # 确保获取到的碎片数量符合预期
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS
        if len(initial_pieces) != total_required_pieces:
             print(f"错误: Board: 获取的初始碎片数量 {len(initial_pieces)} 与预期 {total_required_pieces} 不符。无法填充拼盘。")
             self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
             if isinstance(self.all_pieces_group, pygame.sprite.Group):
                 self.all_pieces_group.empty()
             else:
                 print("警告: Board: self.all_pieces_group 不是 Sprite Group，无法清空。")
                 self.all_pieces_group = pygame.sprite.Group()
             return # 碎片数量不匹配，停止填充

        print(f"Board: 获取了 {len(initial_pieces)} 个初始碎片，开始填充拼盘。")

        # 生成所有网格位置的列表
        all_grid_positions = [(r, c) for r in range(settings.BOARD_ROWS) for c in range(settings.BOARD_COLS)]
        # 随机打乱位置列表
        random.shuffle(all_grid_positions)

        # 将每个碎片放置到一个随机的网格位置上，并逐个添加到 Group
        for i, piece in enumerate(initial_pieces):
            r, c = all_grid_positions[i]

            # Assign piece to grid position
            self.grid[r][c] = piece
            # Update piece's current grid position and screen position (no animation)
            piece.set_grid_position(r, c, animate=False)

            # --- **最精确定位调试、安全检查和断言：在添加到 Group 之前** ---
            # print(f"Board Debug: Piece {i+1}/{len(initial_pieces)} 准备添加到 Group.") # Debug
            # print(f"  Object Type: {type(piece)}, Is Sprite: {isinstance(piece, pygame.sprite.Sprite)}") # Debug
            # if isinstance(piece, pygame.sprite.Sprite):
            #      print(f"  Piece Info: ID {piece.original_image_id}, 原始 ({piece.original_row},{piece.original_col}), 当前 ({piece.current_grid_row},{piece.current_grid_col})") # Debug
            #      image_type = type(piece.image) if hasattr(piece, 'image') else '没有 image 属性'
            #      image_size = piece.image.get_size() if hasattr(piece, 'image') and isinstance(piece.image, pygame.Surface) else 'N/A'
            #      print(f"  Piece Image Type: {image_type}, Size: {image_size}") # Debug
            #      rect_type = type(piece.rect) if hasattr(piece, 'rect') else '没有 rect 属性'
            #      rect_pos_size = piece.rect if hasattr(piece, 'rect') else 'N/A'
            #      print(f"  Piece Rect Type: {rect_type}, Pos/Size: {rect_pos_size}") # Debug

            # --- **关键断言：强制检查 Piece 对象是否是有效的 Sprite 并有 image/rect** ---
            assert isinstance(piece, pygame.sprite.Sprite), f"致命错误: 尝试添加到 Group 的对象不是 Sprite! 类型为 {type(piece)}. Piece Info: {piece.get_original_info() if hasattr(piece, 'get_original_info') else 'N/A'}"
            assert hasattr(piece, 'image') and isinstance(piece.image, pygame.Surface), f"致命错误: 尝试添加的 Sprite 没有有效的 image 属性或不是 Surface! 类型为 {type(piece.image) if hasattr(piece, 'image') else '没有此属性'}. Piece Info: {piece.get_original_info() if hasattr(piece, 'get_original_info') else 'N/A'}"
            assert hasattr(piece, 'rect') and isinstance(piece.rect, pygame.Rect), f"致命错误: 尝试添加的 Sprite 没有有效的 rect 属性或不是 Rect! 类型为 {type(piece.rect) if hasattr(piece, 'rect') else '没有此属性'}. Piece Info: {piece.get_original_info() if hasattr(piece, 'get_original_info') else 'N/A'}"


            # --- **关键修改：回到使用 group.add(piece) 方法，并捕获异常** ---
            # Check if self.all_pieces_group is indeed a Sprite Group before adding
            if isinstance(self.all_pieces_group, pygame.sprite.Group):
                 # print(f"  Group Type: {type(self.all_pieces_group)}. Current size: {len(self.all_pieces_group)}") # Debug
                 try:
                     # Use the standard Group.add method
                     self.all_pieces_group.add(piece) # <-- Error is reported here!
                     # print(f"Board: 成功添加碎片到 Group. Group大小: {len(self.all_pieces_group)}") # Debug
                 except Exception as e:
                     # This exception handler is here just in case, but the assert should catch type issues earlier.
                     print(f"致命错误: Board: 将碎片添加到 Group 时发生异常 (在断言之后): {e}. 碎片信息: {piece.get_original_info()}.")
                     # If this happens repeatedly, the Group or the Piece creation might be fundamentally broken.
                     # Can add an exit here if needed.
                     # import sys; pygame.quit(); sys.exit()
            else:
                 print("致命错误: Board: self.all_pieces_group 不是 Sprite Group！无法添加碎片。")
                 # If this happens, the game is likely broken. Can add an exit here.
                 # import sys; pygame.quit(); sys.exit()


        print(f"Board: {len(self.all_pieces_group) if isinstance(self.all_pieces_group, pygame.sprite.Group) else 'N/A'} 个初始碎片已添加到 Group。") # Debug


    # 替换 _load_grid_from_data 方法 (回到 group.add(piece), 添加更多调试和检查)
    def _load_grid_from_data(self, saved_grid_data):
        """
        从提供的存档数据构建拼盘网格和Sprite Group。

        Args:
            saved_grid_data (list): 从存档读取的拼盘布局二维列表。
        """
        print("Board: 正在从存档数据加载网格布局...") # Debug

        # 确保存档数据尺寸匹配
        if not isinstance(saved_grid_data, list) or len(saved_grid_data) != settings.BOARD_ROWS:
             print(f"错误: Board: 存档数据行数不匹配。预期 {settings.BOARD_ROWS}，实际 {len(saved_grid_data) if isinstance(saved_grid_data, list) else '非列表'}。清空拼盘。")
             self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
             if isinstance(self.all_pieces_group, pygame.sprite.Group):
                 self.all_pieces_group.empty()
             else:
                 print("警告: Board: self.all_pieces_group 不是 Sprite Group，无法清空。")
                 self.all_pieces_group = pygame.sprite.Group()
             return # 尺寸不匹配, 加载失败

        # 清空当前的网格和 Sprite Group
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
        if isinstance(self.all_pieces_group, pygame.sprite.Group):
             self.all_pieces_group.empty()
        else:
            print("警告: Board: self.all_pieces_group 不是 Sprite Group，无法清空。正在重新初始化。")
            self.all_pieces_group = pygame.sprite.Group()


        pieces_added_count = 0 # Counter for pieces successfully added to grid and group


        for r in range(settings.BOARD_ROWS):
            if not isinstance(saved_grid_data[r], list) or len(saved_grid_data[r]) != settings.BOARD_COLS:
                 print(f"错误: Board: 存档数据第 {r} 行列数不匹配。预期 {settings.BOARD_COLS}，实际 {len(saved_grid_data[r]) if isinstance(saved_grid_data[r], list) else '非列表'}。该行加载失败。")
                 self.grid[r] = [None for _ in range(settings.BOARD_COLS)]
                 continue # 处理下一行

            for c in range(settings.BOARD_COLS):
                piece_info = saved_grid_data[r][c]
                if piece_info is not None:
                    # 如果槽位不是空的，尝试创建 Piece 对象
                    try:
                        img_id = piece_info.get('id')
                        orig_r = piece_info.get('orig_r')
                        orig_c = piece_info.get('orig_c')

                        # 验证 piece_info 数据
                        if img_id is None or orig_r is None or orig_c is None:
                             print(f"警告: Board: 存档碎片信息 ({piece_info}) 格式错误或缺失关键字段。槽位 ({r},{c}) 将为空。")
                             self.grid[r][c] = None
                             continue # Skip creating piece

                        # 从 ImageManager 获取碎片 surface
                        piece_surface = None
                        if img_id in self.image_manager.pieces_surfaces and \
                           self.image_manager.pieces_surfaces.get(img_id) is not None and \
                           (orig_r, orig_c) in self.image_manager.pieces_surfaces[img_id]:
                             piece_surface = self.image_manager.pieces_surfaces[img_id][(orig_r, orig_c)]
                             # --- **关键调试：检查获取到的 Piece Surface** ---
                             if not isinstance(piece_surface, pygame.Surface):
                                print(f"致命错误: Board: ImageManager 返回的对象不是 Surface! 图片ID {img_id}, 原始 ({orig_r},{orig_c}). 类型: {type(piece_surface)}")
                                piece_surface = None # Treat as not available

                        if piece_surface is None:
                             print(f"警告: Board: 存档碎片图片ID {img_id}, 原始 ({orig_r},{orig_c}) 的 surface 未加载在 ImageManager 中或获取失败。槽位 ({r},{c}) 将为空。")
                             self.grid[r][c] = None
                             continue # Skip creating piece


                        # 创建 Piece 对象，设置其原始信息和当前网格位置
                        piece = Piece(piece_surface, img_id, orig_r, orig_c, r, c)
                        self.grid[r][c] = piece # Assign piece to grid position


                        # 将 Piece 逐个添加到 Sprite Group
                        # --- **最精确定位调试、安全检查和断言：在添加到 Group 之前** ---
                        print(f"Board Debug: Piece ({r},{c}) from archive prepared to add to Group.") # Debug
                        print(f"  Object Type: {type(piece)}, Is Sprite: {isinstance(piece, pygame.sprite.Sprite)}") # Debug
                        if isinstance(piece, pygame.sprite.Sprite):
                            print(f"  Piece Info: ID {piece.original_image_id}, 原始 ({piece.original_row},{piece.original_col}), 当前 ({piece.current_grid_row},{piece.current_grid_col})") # Debug
                            image_type = type(piece.image) if hasattr(piece, 'image') else '没有 image 属性'
                            image_size = piece.image.get_size() if hasattr(piece, 'image') and isinstance(piece.image, pygame.Surface) else 'N/A'
                            print(f"  Piece Image Type: {image_type}, Size: {image_size}") # Debug

                            rect_type = type(piece.rect) if hasattr(piece, 'rect') else '没有 rect 属性'
                            rect_pos_size = piece.rect if hasattr(piece, 'rect') else 'N/A'
                            print(f"  Piece Rect Type: {rect_type}, Pos/Size: {rect_pos_size}") # Debug
                        else:
                            print(f"致命错误: Board: 尝试从存档添加的对象不是 Sprite，跳过添加。类型为 {type(piece)}.") # Debug
                            continue # Skip adding invalid object


                        # Check if self.all_pieces_group is indeed a Sprite Group before adding
                        if isinstance(self.all_pieces_group, pygame.sprite.Group):
                             print(f"  Group Type: {type(self.all_pieces_group)}. Current size: {len(self.all_pieces_group)}") # Debug
                             try:
                                 # --- **关键修改：回到使用 group.add(piece) 方法，并捕获异常** ---
                                 # Use the standard Group.add method
                                 self.all_pieces_group.add(piece) # <-- Error is reported here!
                                 pieces_added_count += 1
                                 # print(f"Board: 成功添加存档碎片到 Group. Group大小: {len(self.all_pieces_group)}") # Debug
                             except Exception as e:
                                 # This exception handler is here just in case, but the assert should catch type issues earlier.
                                 print(f"致命错误: Board: 将存档碎片添加到 Group 时发生异常 (在断言之后): {e}. 碎片信息: {piece_info}.")
                                 # If this happens repeatedly, the Group or the Piece creation might be fundamentally broken.
                                 # Can add an exit here if needed.
                                 # import sys; pygame.quit(); sys.exit()
                        else:
                             print("致命错误: Board: self.all_pieces_group 不是 Sprite Group！无法添加碎片。")
                             # If this happens, the game is likely broken. Can add an exit here.
                             # import sys; pygame.quit(); sys.exit()


                    except Exception as e:
                        # This catches exceptions during piece info extraction, Piece creation, or Group.add
                        print(f"错误: Board: 加载存档碎片信息 ({piece_info}) 或创建 Piece/添加到 Group 异常: {e}. 槽位 ({r},{c}) 将为空。")
                        self.grid[r][c] = None # 该槽位留空


                else:
                    # 槽位是空的 (None)，grid[r][c] 已经是 None 了，无需操作
                    pass

        print(f"Board: 从存档加载了 {pieces_added_count} 个碎片到拼盘 (成功创建Piece数量)。")

    def swap_pieces(self, pos1_grid, pos2_grid):
        """
        交换两个网格位置上的碎片。
        只会交换在 BOARD_STATE_PLAYING 状态下。

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

        # 确保坐标有效且在板子上
        if not (0 <= r1 < settings.BOARD_ROWS and 0 <= c1 < settings.BOARD_COLS and
                0 <= r2 < settings.BOARD_ROWS and 0 <= c2 < settings.BOARD_COLS):
            # print(f"警告: 无效的网格位置 ({r1},{c1}) 或 ({r2},{c2})，无法交换。")
            return False # 交换失败

        piece1 = self.grid[r1][c1]
        piece2 = self.grid[r2][c2]

        # 检查至少有一个位置不是 None，否则交换没有意义
        if piece1 is None and piece2 is None:
             # print(f"警告: 交换位置 ({r1},{c1}) 和 ({r2},{c2}) 都为空槽位，不进行交换。")
             return False # 交换失败

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

        if self.selected_piece:
             # 如果已经有选中的，先取消上一个的选中状态
             self.unselect_piece()

        self.selected_piece = piece
        # 计算选中高亮框的位置和大小，直接使用碎片的rect
        # 使用 inflate 和 topleft 计算边框位置
        border_thickness = 5 # 和 draw 中的一致
        self.selection_rect = piece.rect.inflate(border_thickness * 2, border_thickness * 2)
        self.selection_rect.topleft = (piece.rect.left - border_thickness, piece.rect.top - border_thickness)

        # print(f"选中碎片: 图片ID {piece.original_image_id}, 原始位置 ({piece.original_row},{piece.original_col}), 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def unselect_piece(self):
        """取消选中状态。"""
        self.selected_piece = None
        self.selection_rect = None # 移除选中高亮框
        # print("取消选中碎片。") # 调试信息


    def start_dragging(self, piece):
        """开始拖拽一个碎片。"""
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return # 只在PLAYING状态下允许拖拽

        self.dragging_piece = piece
        # 将正在拖拽的碎片从 Group 中移除，以便单独绘制它在最上层
        if self.dragging_piece in self.all_pieces_group:
             self.all_pieces_group.remove(self.dragging_piece)

        print(f"开始拖拽碎片: 图片ID {piece.original_image_id}, 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def stop_dragging(self):
        """停止拖拽当前碎片。"""
        if self.dragging_piece:
            # print(f"停止拖拽碎片: 图片ID {self.dragging_piece.original_image_id}, 当前位置 ({self.dragging_piece.current_grid_row},{self.dragging_piece.current_grid_col})") # 调试信息
            # 将碎片放回其当前网格位置的精确屏幕坐标 (如果拖拽时位置有偏移的话)
            current_grid_pos = (self.dragging_piece.current_grid_row, self.dragging_piece.current_grid_col)
            self.dragging_piece.set_grid_position(current_grid_pos[0], current_grid_pos[1], animate=False) # 停止拖拽瞬间归位

            # 将碎片加回 Sprite Group
            if self.dragging_piece not in self.all_pieces_group:
                 self.all_pieces_group.add(self.dragging_piece)

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

            # TODO: 可以在这里触发一个全局的游戏事件，比如播放音效，显示祝贺信息等
            # 可以通过 ImageManager 间接访问 Game 实例来调用 Game 的方法
            # if hasattr(self.image_manager.game, 'show_completion_effect'):
            #     self.image_manager.game.show_completion_effect(completed_image_id)

            return True # 有图片完成
        return False # 没有图片完成


    def check_completion(self):
        """
        检查拼盘中是否存在一个完整的 5列 x 9行 图片块。
        返回已完成的图片ID，如果没有则返回None。
        如果找到，记录完成区域的左上角位置在 self._completed_area_start_pos。
        """
        # 遍历所有可能的 5列 x 9行 图片块的左上角起始点
        # 物理板子是 9行 x 16列
        # 逻辑图片是 9行 x 5列
        # 起始行的范围: 从 0 到 BOARD_ROWS - IMAGE_LOGIC_ROWS (9 - 9 = 0)。范围是 0。所以只有 start_row = 0 是可能的。
        # 起始列的范围: 从 0 到 BOARD_COLS - IMAGE_LOGIC_COLS (16 - 5 = 11)。范围是 0 到 11。
        for start_row in range(settings.BOARD_ROWS - settings.IMAGE_LOGIC_ROWS + 1): # 范围基于新的 IMAGE_LOGIC_ROWS=9
            for start_col in range(settings.BOARD_COLS - settings.IMAGE_LOGIC_COLS + 1): # 范围基于新的 IMAGE_LOGIC_COLS=5

                # 获取该 5列 x 9行 区域左上角的碎片
                top_left_piece = self.grid[start_row][start_col]

                # 如果左上角没有碎片，或者碎片的原始位置不是逻辑上的 (0,0)，
                # 它就不可能是一个完整图片块的起始。
                # Original row/col 是碎片在逻辑上的 9x5 图片网格中的原始位置。
                if top_left_piece is None or top_left_piece.original_row != 0 or top_left_piece.original_col != 0:
                    continue # 检查下一个可能的起始位置

                # 确定要检查的目标图片ID
                target_image_id = top_left_piece.original_image_id
                is_complete = True # 假设这个区域是一个完整的图片块

                # 遍历这个 9行 x 5列 区域内的所有位置 (相对于起始点的偏移 dr, dc)
                for dr in range(settings.IMAGE_LOGIC_ROWS): # 遍历逻辑行 (0 to 8)
                    for dc in range(settings.IMAGE_LOGIC_COLS): # 遍历逻辑列 (0 to 4)
                        current_row = start_row + dr # 对应的物理行
                        current_col = start_col + dc # 对应的物理列
                        # 确保检查在板子范围内 (考虑到外层循环的范围限制，这通常为真)
                        if not (0 <= current_row < settings.BOARD_ROWS and 0 <= current_col < settings.BOARD_COLS):
                            is_complete = False # 区域超出版子范围 (不应该发生)
                            break
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
                    # 在返回图片ID之前，记录这个完成的区域的左上角位置
                    self._completed_area_start_pos = (start_row, start_col)
                    return target_image_id # 返回完成的图片ID

        return None # 遍历所有可能位置后没有找到完整的图片


    def _process_completed_picture(self):
        """
        处理已完成图片的流程状态机。
        根据 current_board_state 执行相应的步骤。
        这个方法在 Board 的 update 中被调用。
        """
        if self.current_board_state == settings.BOARD_STATE_PICTURE_COMPLETED:
            # 状态：图片已检测完成，刚进入处理流程
            print(f"Board State: PICTURE_COMPLETED -> REMOVING_PIECES for image {self._completed_image_id_pending_process}") # 调试信息
            self.current_board_state = settings.BOARD_STATE_REMOVING_PIECES
            # 移除碎片 (瞬间完成)
            self.remove_completed_pieces()
            # 移除完成后，立即切换到下落状态并启动下落动画
            self.current_board_state = settings.BOARD_STATE_PIECES_FALLING
            self.initiate_fall_down_pieces()


        elif self.current_board_state == settings.BOARD_STATE_PIECES_FALLING:
             # 状态：碎片正在下落动画中
             # 碎片下落动画的更新由 Piece 的 update 方法处理，并在 Board 的 update 中调用 group.update
             # 在 Board 的 update 方法中会检查是否所有碎片都已停止下落，并切换到 PENDING_FILL 状态
             return # 等待下落动画完成


        elif self.current_board_state == settings.BOARD_STATE_PENDING_FILL:
            # 状态：碎片下落完成，等待填充
            print("Board State: PENDING_FILL -> PLAYING (after fill)") # 调试信息
            # 填充新碎片 (瞬间完成)
            self.fill_new_pieces()

            # 清理完成图片的记录
            self._completed_image_id_pending_process = None
            self._completed_area_start_pos = None

            # 填充完成后，切换回 PLAYING 状态
            self.current_board_state = settings.BOARD_STATE_PLAYING

            # TODO: 通知 Game 或 Gallery 图库需要刷新 (Board不能直接访问Gallery，通过Game间接通知)
            if hasattr(self.image_manager.game, 'gallery'): # 检查Game实例是否有gallery属性
                print("通知 Gallery 更新列表...") # Debug
                self.image_manager.game.gallery._update_picture_list() # 直接调用更新方法



    def remove_completed_pieces(self):
        """根据记录的 _completed_area_start_pos，从拼盘中移除已完成图片的碎片"""
        if self._completed_area_start_pos is None or self._completed_image_id_pending_process is None:
             print("错误: 没有记录已完成区域或图片ID，无法移除碎片。")
             return

        start_row, start_col = self._completed_area_start_pos
        completed_image_id = self._completed_image_id_pending_process
        # print(f"Removing pieces for image {completed_image_id} starting at ({start_row},{start_col}) (9x5 area)...") # Debug

        pieces_to_remove_list = [] # 收集要移除的碎片对象

        # 遍历要移除的 9行 x 5列 区域 based on the logical image dimensions
        for dr in range(settings.IMAGE_LOGIC_ROWS): # 逻辑行 (0 to 8)
            for dc in range(settings.IMAGE_LOGIC_COLS): # 逻辑列 (0 to 4)
                r = start_row + dr # 对应的物理行
                c = start_col + dc # 对应的物理列
                # 确保坐标在板子范围内
                if 0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS:
                    piece_to_remove = self.grid[r][c]
                    # 再次检查碎片是否属于当前完成的图片 (安全检查)
                    # 检查原始行/列是否与逻辑区域的偏移匹配
                    if piece_to_remove and piece_to_remove.original_image_id == completed_image_id and \
                       piece_to_remove.original_row == dr and piece_to_remove.original_col == dc:
                         pieces_to_remove_list.append(piece_to_remove)
                         self.grid[r][c] = None # 将网格位置设为 None
                    # else:
                         # print(f"警告: 尝试移除的区域 ({r},{c}) 没有属于完成图片 {completed_image_id} 的碎片或为空。") # Debug

        # 从 Sprite Group 中移除收集到的碎片
        self.all_pieces_group.remove(*pieces_to_remove_list)
        # TODO: 可以添加一个效果，让移除的碎片消失或爆炸等 (可选)


    def initiate_fall_down_pieces(self):
        """启动碎片下落动画：计算所有碎片的最终目标位置，并标记它们为正在下落"""
        # print("启动碎片下落动画...") # Debug
        # 遍历每一列，确定每个非空碎片的最终下落位置
        for c in range(settings.BOARD_COLS): # 遍历每一列
            bottom_row_index_to_fill = settings.BOARD_ROWS - 1 # 当前列底部可以填充的行索引

            # 从底向上遍历当前列
            pieces_in_column = [] # 临时存储本列非空碎片
            for r in range(settings.BOARD_ROWS - 1, -1, -1):
                if self.grid[r][c]:
                     pieces_in_column.append(self.grid[r][c])
                     self.grid[r][c] = None # 先将原位置设为None

            # 从底向上重新放置收集到的碎片，并启动下落动画
            current_row = settings.BOARD_ROWS - 1
            for piece in pieces_in_column:
                 self.grid[current_row][c] = piece
                 # 更新碎片的网格位置并启动下落动画到新的屏幕Y坐标
                 piece.set_grid_position(current_row, c, animate=True)
                 current_row -= 1

        # 动画的实际更新由各个 Piece 的 update 方法处理，并在 Board 的 update 方法中调用 Sprite Group 的 update


    def is_any_piece_falling(self):
        """检查是否有任何碎片正在下落动画中"""
        # 遍历 Sprite Group 中的所有碎片，检查 is_falling 属性
        for piece in self.all_pieces_group:
             if piece.is_falling:
                 return True
        return False


    def fill_new_pieces(self):
        """根据填充规则，从 image_manager 获取新碎片填充顶部空位"""
        # print("触发填充新碎片...") # Debug
        # 统计有多少个空槽位需要填充 (即网格中为 None 的位置)
        empty_slots_positions = [] # 记录空槽位的位置 (从上往下，从左往右遍历获取)
        for r in range(settings.BOARD_ROWS):
            for c in range(settings.BOARD_COLS):
                if self.grid[r][c] is None:
                     empty_slots_positions.append((r, c)) # 记录空位位置

        empty_slots_count = len(empty_slots_positions)
        # print(f"检测到 {empty_slots_count} 个空槽位需要填充。") # Debug

        if empty_slots_count == 0:
             # print("没有空槽位需要填充。")
             return

        # 从 ImageManager 获取相应数量的新碎片
        new_pieces = self.image_manager.get_next_fill_pieces(empty_slots_count)
        # print(f"ImageManager 提供了 {len(new_pieces)} 个新碎片。") # Debug

        # 将新碎片放置到空槽位中
        for i, piece in enumerate(new_pieces):
             if i < len(empty_slots_positions):
                 r, c = empty_slots_positions[i]
                 self.grid[r][c] = piece
                 # 将新碎片放置到其目标网格位置 (非动画，瞬间出现)
                 piece.set_grid_position(r, c, animate=False)
                 # 将新碎片添加到 Sprite Group
                 self.all_pieces_group.add(piece)
             else:
                 print(f"警告: 有多余的新碎片 ({len(new_pieces)} 个) 但没有足够的空槽位 ({empty_slots_count} 个) 来放置。")
                 break # 没有更多空槽位了

        if len(new_pieces) < empty_slots_count:
            print(f"警告: 需要 {empty_slots_count} 个碎片，但 ImageManager 只提供了 {len(new_pieces)} 个。拼盘将会有空位。")


    def draw(self, surface):
        """在指定的surface上绘制拼盘中的所有碎片、选中效果和 debug 信息。"""
        # 绘制所有非拖拽中的碎片
        # 暂时将正在拖拽的碎片从组中移除，以便稍后将其绘制在最上层
        if self.dragging_piece and self.dragging_piece in self.all_pieces_group:
             self.all_pieces_group.remove(self.dragging_piece)

        # 绘制所有在 Group 中的 Sprite
        self.all_pieces_group.draw(surface)

        # 绘制选中碎片的特殊效果 (例如绘制边框)
        if self.selection_rect:
             # 确保高亮位置与选中碎片的矩形框同步
             if self.selected_piece:
                 border_thickness = 5
                 # 根据选中碎片的当前位置更新 selection_rect 的位置
                 self.selection_rect.topleft = (self.selected_piece.rect.left - border_thickness, self.selected_piece.rect.top - border_thickness)
             # 绘制选中边框
             pygame.draw.rect(surface, settings.HIGHLIGHT_COLOR, self.selection_rect, 5) # 绘制厚度为 5 的边框

        # 最后绘制正在拖拽的碎片，使其显示在最上层
        if self.dragging_piece:
             # 输入处理器在鼠标移动事件中更新 dragging_piece.rect 的中心位置
             self.dragging_piece.draw(surface)

        # 如果游戏中的调试标志已设置，则绘制碎片调试信息
        # 通过 ImageManager 访问游戏实例和调试字体
        if hasattr(self.image_manager.game, 'display_piece_info') and self.image_manager.game.display_piece_info:
             if hasattr(self.image_manager.game, 'font_debug') and self.image_manager.game.font_debug:
                 debug_font = self.image_manager.game.font_debug
                 # 遍历网格（或所有碎片组），在每个碎片上绘制文本
                 for piece in self.all_pieces_group: # 遍历组（如果有碎片被移除，这种方式更高效）
                     # 格式化调试文本（图片 ID、原始行、原始列）
                     debug_text = f"ID:{piece.original_image_id} R:{piece.original_row} C:{piece.original_col}"
                     # 渲染文本
                     text_surface = debug_font.render(debug_text, True, settings.DEBUG_TEXT_COLOR)
                     # 设置文本位置，例如，居中于碎片的矩形框
                     text_rect = text_surface.get_rect(center=piece.rect.center)
                     # 绘制文本
                     surface.blit(text_surface, text_rect)
                 # 如果正在拖拽的碎片处于活动状态且不在组中，也绘制其信息
                 if self.dragging_piece and self.dragging_piece not in self.all_pieces_group:
                     debug_text = f"ID:{self.dragging_piece.original_image_id} R:{self.dragging_piece.original_row} C:{self.dragging_piece.original_col}"
                     text_surface = debug_font.render(debug_text, True, settings.DEBUG_TEXT_COLOR)
                     text_rect = text_surface.get_rect(center=self.dragging_piece.rect.center)
                     surface.blit(text_surface, text_rect)

        # 绘制完成后，将正在拖拽的碎片重新添加到组中
        if self.dragging_piece and self.dragging_piece not in self.all_pieces_group:
             self.all_pieces_group.add(self.dragging_piece)


    def update(self, dt):
         """
         更新Board的状态，包括处理完成流程和碎片下落动画。

         Args:
             dt (float): 自上一帧以来的时间（秒）
         """
         # 如果 Board 状态不是 PLAYING，则调用 _process_completed_picture 处理状态机
         if self.current_board_state != settings.BOARD_STATE_PLAYING:
             self._process_completed_picture() # 处理完成流程状态机

         # 更新所有碎片的动画 (特别是正在下落的碎片)
         # 即使 Board 状态不是 FALLING，也需要更新，因为 Board 可能会在 PLAYING 状态下突然切换到 FALLING
         # 碎片 Piece 的 update 方法会根据自身的 is_falling 属性决定是否移动
         self.all_pieces_group.update(dt)

         # 如果 Board 状态是 FALLING，检查是否所有碎片都已停止下落，然后切换状态
         if self.current_board_state == settings.BOARD_STATE_PIECES_FALLING:
              if not self.is_any_piece_falling():
                   print("所有碎片下落完成。状态切换到 PENDING_FILL。") # Debug
                   self.current_board_state = settings.BOARD_STATE_PENDING_FILL # 切换状态，等待填充


    def get_piece_at_grid(self, row, col):
         """获取指定网格位置的碎片对象，或None"""
         if 0 <= row < settings.BOARD_ROWS and 0 <= col < settings.BOARD_COLS:
             return self.grid[row][col]
         return None # 坐标无效

    # 提供给 InputHandler 用于判断点击或拖拽是否在 Board 区域内
    def get_board_rect(self):
        """返回拼盘区域在屏幕上的Rect"""
        return pygame.Rect(settings.BOARD_OFFSET_X, settings.BOARD_OFFSET_Y,
                           settings.BOARD_COLS * settings.PIECE_SIZE,
                           settings.BOARD_ROWS * settings.PIECE_SIZE)

    # def _update_falling_pieces(self, dt): ... (已整合到 all_pieces_group.update)


    def get_state(self):
        """
        获取当前拼盘的碎片布局状态。

        Returns:
            list: 一个二维列表，表示拼盘的网格布局。
                  每个元素是一个字典 {'id': original_image_id, 'orig_r': original_row, 'orig_c': original_col}
                  或者 None 表示空槽位。
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

        return saved_grid