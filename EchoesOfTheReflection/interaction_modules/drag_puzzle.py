# interaction_modules/drag_puzzle.py
import pygame
# 修正导入路径，settings 在根目录
from settings import Settings
# 修正导入路径，ImageRenderer 在根目录
from image_renderer import ImageRenderer # 导入用于坐标转换
# 修正导入路径，puzzle_piece 在 interaction_modules 子目录
from .puzzle_piece import PuzzlePiece # 导入类名
import random # 用于打乱碎片
# 导入 AudioManager 类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from audio_manager import AudioManager # AudioManager 在根目录


class DragPuzzle:
    """
    处理Drag Puzzle玩法逻辑。
    玩家拖拽图片碎片拼合。
    """

    def __init__(self, config: dict, image_renderer: ImageRenderer):
        """
        初始化拖拽拼图模块。
        config: 来自image_config.json的当前图片配置。
        image_renderer: 用于图片显示和效果控制的ImageRenderer实例。
        """
        self.config = config
        self.image_renderer = image_renderer
        self.settings = image_renderer.settings # 获取 settings 实例

        # 从 settings 获取 AudioManager 实例
        self.audio_manager: 'AudioManager' = self.settings.game_manager.audio_manager # 通过game_manager获取audio_manager


        self.puzzle_config = config.get("puzzle_config", {})
        self.rows = self.puzzle_config.get("rows", 3)
        self.cols = self.puzzle_config.get("cols", 3)
        self.artistic_cut = self.puzzle_config.get("artistic_cut", False)
        self.initial_scatter_range = self.puzzle_config.get("initial_scatter_range", 0.2)
        # 拼图碎片定义列表 (来自 config 的 puzzle_config.pieces 字段)
        # 格式示例: [{"id": "piece_0_0", "correct_pos_local": [x, y], "source_rect_original": [x, y, w, h]}, ...]
        # 如果 pieces 为空，则使用默认网格切割
        self.pieces_config = self.puzzle_config.get("pieces", [])
        # 碎片拖拽目标区域配置 (来自 config 的 puzzle_config.drop_target)
        # 格式示例: {"type": "rect", "x": 0.45, "y": 0.45, "width": 0.1, "height": 0.1, "id": "core_target"}
        self.drop_target_config = self.puzzle_config.get("drop_target") # TODO: 实现目标区域的视觉提示和吸附判断


        # 拼图碎片列表 (PuzzlePiece 对象列表)
        self.pieces: list[PuzzlePiece] = []
        # 在 __init__ 中不立即创建碎片 Surface，只存储配置，在 update 中第一次运行时根据 display_rect 创建

        self._dragging_piece: PuzzlePiece | None = None # 当前正在拖拽的碎片 (PuzzlePiece 对象)
        self._drag_offset = (0, 0) # 拖拽时的鼠标偏移 (鼠标位置 - 碎片左上角)

        # 拼图完成状态
        self._is_completed = False

        # 跟踪已触发的叙事事件
        self._triggered_narrative_events = set()

        # 标记第一次拖拽，用于触发叙事
        self._has_dragged_first_time = False

        # 标记碎片 Surface 是否已创建并初始化位置
        self._pieces_initialized = False

        # 加载或设置进度相关的叙事触发点
        self.progress_narrative_checkpoints = config.get("narrative_triggers", {}).items()
        # 过滤出进度相关的触发器 { "on_puzzle_progress_50": 50, ... }
        self._progress_checkpoints = {
            k: v for k, v in self.progress_narrative_checkpoints
            if k.startswith("on_puzzle_progress_")
        }


    def _create_puzzle_pieces(self, image_display_rect: pygame.Rect):
        """根据图片和配置创建拼图碎片 Surface 并设置初始位置"""
        if self._pieces_initialized:
            # 如果碎片已创建，这里不应该重复创建
            # resize 方法会调用这个方法，但会先清空 self.pieces 并重置 _pieces_initialized
            # print("Warning: _create_puzzle_pieces called when pieces are already initialized.")
            return

        if not self.image_renderer.current_image:
            print("错误：无法创建拼图碎片 Surface，图片未加载！")
            return

        # 获取要切割的 Surface (已缩放裁剪到显示区域尺寸)
        source_surface = self.image_renderer.current_image
        img_width, img_height = source_surface.get_size()

        self.pieces = [] # 确保列表为空

        # 遍历 config 中的 pieces 定义来创建 PuzzlePiece 对象
        # config.pieces 应该包含每个碎片的 ID 和其在原始图片中的正确像素位置 (correct_pos_local)
        # 如果 config.pieces 为空，则使用默认的网格切割和位置
        if not self.pieces_config:
            print("警告: pieces configuration missing or empty, using default grid.")
            # 默认网格切割和位置
            piece_target_width = img_width // self.cols
            piece_target_height = img_height // self.rows
            for r in range(self.rows):
                for c in range(self.cols):
                    piece_id = f"piece_{r}_{c}" # 默认ID
                    piece_rect_local = pygame.Rect(c * piece_target_width, r * piece_target_height, piece_target_width, piece_target_height)
                    # 获取碎片的 Surface (从缩放裁剪后的图片中切割)
                    piece_surface = source_surface.subsurface(piece_rect_local)
                    # 正确位置是相对于图片显示区域左上角的本地像素坐标
                    correct_pos_local = piece_rect_local.topleft
                    grid_pos = (r, c)

                    # 修正 PuzzlePiece 初始化，使用导入的类名
                    self.pieces.append(PuzzlePiece(piece_id, piece_surface, correct_pos_local, grid_pos))
        else:
            # 实现根据 config.pieces 进行艺术化切割或从指定区域获取 Surface
            # config.pieces 结构可能包含每个碎片的纹理信息或在原图上的源矩形
            # 示例: {"id": "pieceA", "source_rect_original": [x, y, w, h], "correct_pos_local": [x, y]}
            print("创建根据 pieces configuration 创建艺术化碎片...")
            for piece_cfg in self.pieces_config:
                piece_id = piece_cfg.get("id")
                if piece_id is None:
                     print(f"警告：pieces configuration 中存在没有ID的碎片配置: {piece_cfg}. 跳过。")
                     continue

                # 正确位置是相对于图片显示区域左上角的本地像素坐标
                # 确保 correct_pos_local 是一个元组 [x, y]
                correct_pos_local_list = piece_cfg.get("correct_pos_local", [0,0])
                if not isinstance(correct_pos_local_list, list) or len(correct_pos_local_list) != 2:
                    print(f"警告：碎片 {piece_id} 的 correct_pos_local 格式无效: {correct_pos_local_list}. 使用 (0,0)。")
                    correct_pos_local = (0,0)
                else:
                    correct_pos_local = tuple(correct_pos_local_list)

                piece_surface = None
                if "source_rect_original" in piece_cfg:
                     # 如果配置提供了原始图片上的源矩形
                     original_source_rect_config = piece_cfg["source_rect_original"]
                     if isinstance(original_source_rect_config, list) and len(original_source_rect_config) == 4:
                          original_source_rect = pygame.Rect(*original_source_rect_config)
                          # 将原始矩形转换为显示区域上的矩形
                          # 需要 ImageRenderer 的坐标和尺寸转换方法
                          display_source_rect = self.image_renderer.get_screen_rect_from_original(original_source_rect)
                          # 从缩放后的图片中切割 Surface
                          # 确保矩形在图片 Surface 范围内
                          if self.image_renderer.current_image and display_source_rect.colliderect(self.image_renderer.current_image.get_rect()):
                               piece_surface = self.image_renderer.current_image.subsurface(display_source_rect).copy() # 使用copy()避免subsurface的副作用
                          else:
                               print(f"警告：碎片 {piece_id} 的原始源矩形 {original_source_rect} 在显示区域外或无效。")
                               piece_surface = pygame.Surface((50,50)).convert_alpha() # 默认占位
                               piece_surface.fill((200, 100, 100)) # 示例颜色
                     else:
                          print(f"警告：碎片 {piece_id} 的 source_rect_original 格式无效: {original_source_rect_config}. 使用默认占位。")
                          piece_surface = pygame.Surface((50,50)).convert_alpha() # 默认占位
                          piece_surface.fill((200, 100, 100)) # 示例颜色

                elif "texture_file" in piece_cfg:
                     # 如果碎片是独立纹理文件
                     texture_filename = piece_cfg["texture_file"]
                     texture_path = os.path.join(self.settings.IMAGE_DIR, texture_filename) # 假设碎片纹理也放在images目录
                     if os.path.exists(texture_path):
                         try:
                              piece_surface = pygame.image.load(texture_path).convert_alpha()
                              # TODO: 缩放碎片纹理以适应其在屏幕上的预期大小 (复杂)
                              # 如果 correct_pos_local 定义了尺寸，或者 config 有单独的尺寸定义
                              # 例如: piece_size_config = piece_cfg.get("display_size") # [w, h]
                              # if piece_size_config:
                              #      display_width = int(piece_size_config[0] * self.image_renderer._scale_factor) # 示例缩放
                              #      display_height = int(piece_size_config[1] * self.image_renderer._scale_factor)
                              #      piece_surface = pygame.transform.scale(piece_surface, (display_width, display_height))
                              pass
                         except pygame.error as e:
                              print(f"警告：无法加载碎片纹理 {texture_path}: {e}")
                              piece_surface = pygame.Surface((50,50)).convert_alpha() # 默认占位
                              piece_surface.fill((100, 200, 100)) # 示例颜色
                     else:
                          print(f"警告：碎片纹理文件未找到 {texture_path}. 使用默认占位。")
                          piece_surface = pygame.Surface((50,50)).convert_alpha() # 默认占位
                          piece_surface.fill((100, 200, 100)) # 示例颜色


                else:
                     # 如果没有 source_rect 或 texture_file，创建默认占位 Surface
                     print(f"警告：碎片 {piece_id}没有定义 source_rect 或 texture_file。使用默认占位。")
                     piece_surface = pygame.Surface((50,50)).convert_alpha() # 默认占位
                     piece_surface.fill((100, 100, 200)) # 示例颜色

                if piece_surface:
                     self.pieces.append(PuzzlePiece(piece_id, piece_surface, correct_pos_local, piece_cfg.get("grid_pos")))


        # 碎片的初始位置将在 update 或 handle_event 中根据 image_display_rect 计算并设置
        # self.pieces = random.sample(self.pieces, len(self.pieces)) # 初始打乱顺序 (可选)


        self._pieces_initialized = True # 标记碎片 Surface 已创建并初始化位置


    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
        """处理窗口大小改变事件，需要重新创建/定位碎片"""
        print("DragPuzzle resize called")
        # 如果碎片已经初始化过
        if self._pieces_initialized:
             # 清空现有碎片 Surface，但保留它们的配置和状态 (位置，是否锁定)
             # 创建一个新的列表来存储旧的状态
             old_piece_states = {}
             for piece in self.pieces:
                  old_piece_states[piece.id] = {
                      # 保存位置为相对于图片显示区域的本地像素坐标，以便在新的 display_rect 下重新计算屏幕位置
                      # current_screen_pos = piece.get_position() # 屏幕坐标
                      # 将屏幕坐标转换回相对图片显示区域的坐标 (0-1) 或原始图片坐标
                      # relative_display_pos = self.image_renderer.get_relative_coords(current_screen_pos) # 如果使用相对坐标保存
                      # original_image_pos = self.image_renderer.get_image_coords(current_screen_pos[0], current_screen_pos[1]) # 如果使用原始图片坐标保存

                      # 简化的做法：只保存锁定状态
                      "is_locked": piece.is_locked(),
                      # "_has_dragged_first_time": self._has_dragged_first_time # 可以在 load_state 中一次性恢复
                  }
             self.pieces = [] # 清空 Pygame Surface

             # 重新创建碎片 Surface 并根据旧状态设置位置和锁定状态
             self._pieces_initialized = False # 重置标志
             # _create_puzzle_pieces 会根据当前的 image_display_rect 和原始图片尺寸创建碎片 Surface 并随机散开位置
             self._create_puzzle_pieces(image_display_rect) # 重新创建碎片并随机散开

             # 恢复旧的状态
             for piece in self.pieces:
                  if piece.id in old_piece_states:
                       state = old_piece_states[piece.id]
                       # 恢复锁定状态
                       piece.set_locked(state["is_locked"])
                       # TODO: 如果需要恢复精确位置，根据保存的旧位置和新的 image_display_rect 重新计算屏幕位置并设置
                       # 例如，如果保存的是相对图片显示区域的坐标 (0-1)，则：
                       # new_screen_x = image_display_rect.left + int(state["relative_pos"][0] * image_display_rect.width)
                       # new_screen_y = image_display_rect.top + int(state["relative_pos"][1] * image_display_rect.height)
                       # piece.set_position((new_screen_x, new_screen_y))

             # 恢复其他状态
             # self._triggered_narrative_events = ... # 需要在 load_state 中加载
             # self._has_dragged_first_time = ... # 需要在 load_state 中加载

             # 如果需要精确恢复位置，get_state/load_state 会处理

    # TODO: DragPuzzle 需要实现 set_pieces 和 enable_dragging 方法供 HybridInteraction 调用 (Stage 5.2)
    def set_pieces(self, pieces_surfaces_with_config: list[tuple[pygame.Surface, dict]], image_display_rect: pygame.Rect):
        """
        设置拼图模块的碎片列表 (用于混合玩法生成碎片后传递)。
        pieces_surfaces_with_config: 列表，每个元素是一个元组 (碎片Surface, 碎片配置字典)。
        image_display_rect: 当前图片显示区域。
        """
        print("DragPuzzle received pieces from HybridInteraction.")
        self.pieces = [] # 清空现有碎片
        self._pieces_initialized = False # 重置初始化标志

        if not pieces_surfaces_with_config:
            print("警告: set_pieces received empty list.")
            return

        # 创建 PuzzlePiece 实例，设置 Surface 和正确位置
        for piece_surface, piece_cfg in pieces_surfaces_with_config:
             piece_id = piece_cfg.get("id")
             # 正确位置是相对于图片显示区域左上角的本地像素坐标
             correct_pos_local_list = piece_cfg.get("correct_pos_local", [0,0])
             if not isinstance(correct_pos_local_list, list) or len(correct_pos_local_list) != 2:
                 print(f"警告：接收到的碎片配置 {piece_id} 的 correct_pos_local 格式无效: {correct_pos_local_list}. 使用 (0,0)。")
                 correct_pos_local = (0,0)
             else:
                 correct_pos_local = tuple(correct_pos_local_list)

             grid_pos = piece_cfg.get("grid_pos")

             if piece_id is not None and piece_surface: # Check if piece_id is not None
                 # Corrected: Use PuzzlePiece class name directly
                 self.pieces.append(PuzzlePiece(piece_id, piece_surface, correct_pos_local, grid_pos))
             else:
                 print(f"警告: 接收到无效的碎片配置或 Surface: {piece_cfg}")


        # 计算碎片的初始随机散开位置 (在图片显示区域范围内)
        # image_display_rect 已经是屏幕坐标 Rect
        scatter_width = image_display_rect.width * self.initial_scatter_range
        scatter_height = image_display_rect.height * self.initial_scatter_range

        initial_positions = [] # 存储初始随机位置
        for piece in self.pieces:
            # 计算碎片的正确屏幕位置 (相对于屏幕左上角)
            # correct_pos_local 是相对于图片显示区域左上角的本地像素坐标
            correct_screen_pos = (
                image_display_rect.left + piece.correct_pos_local[0],
                image_display_rect.top + piece.correct_pos_local[1]
            )
            # 在正确位置周围随机偏移
            initial_pos_screen = (
                correct_screen_pos[0] + random.uniform(-scatter_width, scatter_width),
                correct_screen_pos[1] + random.uniform(-scatter_height, scatter_height)
            )
            initial_positions.append(initial_pos_screen)

        # 打乱初始位置，然后按碎片在 self.pieces 列表中的顺序设置
        random.shuffle(initial_positions)
        for i, piece in enumerate(self.pieces):
             piece.set_position(initial_positions[i])
             piece.set_locked(False) # 初始为可拖拽状态

        # 打乱碎片的绘制顺序 (通过打乱 pieces 列表本身)
        random.shuffle(self.pieces)

        self._pieces_initialized = True # 标记碎片 Surface 已创建并初始化位置
        self._is_completed = False # 确保重置完成状态

    def enable_dragging(self):
         """启用碎片的拖拽 (如果需要分步启用拖拽)"""
         # 默认碎片就是可拖拽的 (除非 locked)
         # 如果有分步启用拖拽的需求，可以在 PuzzlePiece 中添加 is_draggable 标志，并在绘制/handle_event 中检查
         print("Dragging enabled for puzzle pieces.")
         pass # 目前不需要特殊处理


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        # 确保碎片 Surface 已创建 (如果还没有的话)
        if not self._pieces_initialized:
             self._create_puzzle_pieces(image_display_rect)
             if not self._pieces_initialized: # 如果创建失败
                  return # 无法处理事件

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            mouse_pos = event.pos
            # 检查点击是否在图片的显示区域内 (可选，如果碎片散在外面就不检查)
            # if image_display_rect.collidepoint(mouse_pos): # 示例检查
            # 检查是否点击到任何一个未锁定（可拖拽）的碎片
            # 从后往前检查，确保点击到绘制在最上面的碎片
            for piece in reversed(self.pieces):
                # 只有当碎片可见且未锁定时才检查点击
                # if not piece.is_locked() and piece.rect.collidepoint(mouse_pos):
                # 如果实现了碎片可见性控制 (例如通过 HybridInteraction)，还需要检查 piece.is_visible()
                if not piece.is_locked() and piece.rect.collidepoint(mouse_pos):
                    self._dragging_piece = piece
                    # 计算拖拽偏移 (鼠标位置 - 碎片左上角)
                    self._drag_offset = (mouse_pos[0] - piece.rect.left, mouse_pos[1] - piece.rect.top)
                    # 将被拖拽的碎片放到列表末尾，使其绘制在最上层
                    self.pieces.remove(piece)
                    self.pieces.append(piece)

                    # 触发第一次拖拽叙事 (如果配置了且尚未触发)
                    if not self._has_dragged_first_time and "on_drag_first_piece" in self.config.get("narrative_triggers", {}):
                         self._has_dragged_first_time = True
                         # 返回触发的事件，让 GameManager 启动叙事
                         pass # 在 update 中统一返回叙事事件

                    # TODO: 播放拾起音效 sfx_puzzle_pickup
                    if self.audio_manager:
                         # self.audio_manager.play_sfx("sfx_puzzle_pickup") # 示例音效ID
                         pass # 待填充实际音效ID

                    break # 只处理一个碎片


        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: # 左键抬起
            if self._dragging_piece:
                # 检查是否吸附到正确位置
                snap_threshold = self.puzzle_config.get("snap_threshold", 20) # 从config获取吸附容忍度像素

                # 计算碎片的正确屏幕位置 (相对于屏幕左上角)
                correct_screen_pos = (
                    image_display_rect.left + self._dragging_piece.correct_pos_local[0],
                    image_display_rect.top + self._dragging_piece.correct_pos_local[1]
                )
                # 检查当前位置是否接近正确位置
                if (self._dragging_piece.rect.left - correct_screen_pos[0])**2 + \
                   (self._dragging_piece.rect.top - correct_screen_pos[1])**2 <= snap_threshold**2:
                    # 吸附到位
                    self._dragging_piece.set_position(correct_screen_pos)
                    self._dragging_piece.set_locked(True) # 锁定碎片
                    # TODO: 播放吸附音效 sfx_puzzle_snap
                    if self.audio_manager:
                         # self.audio_manager.play_sfx("sfx_puzzle_snap") # 示例音效ID
                         pass # 待填充实际音效ID
                else:
                     # TODO: 播放放下音效 sfx_puzzle_drop
                     if self.audio_manager:
                          # self.audio_manager.play_sfx("sfx_puzzle_drop") # 示例音效ID
                          pass # 待填充实际音效ID


                self._dragging_piece = None # 停止拖拽


        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._dragging_piece:
                mouse_pos = event.pos
                # 更新碎片位置，考虑拖拽偏移
                new_x = mouse_pos[0] - self._drag_offset[0]
                new_y = mouse_pos[1] - self._drag_offset[1]
                self._dragging_piece.set_position((new_x, new_y))

                # TODO: 播放拖拽音效 sfx_puzzle_dragging_looping (循环音效)
                # if self.audio_manager and not self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"):
                #     self.audio_manager.play_sfx("sfx_puzzle_dragging_looping", loop=-1)

        # TODO: 鼠标移动停止时 (MOUSEBUTTONUP 或 MOUSEMOTION 速度很低时)，停止拖拽音效


    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新拖拽拼图状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        # 确保碎片 Surface 已创建
        if not self._pieces_initialized:
             self._create_puzzle_pieces(image_display_rect)
             # 如果碎片创建失败，直接标记完成避免错误
             if not self._pieces_initialized:
                 self._is_completed = True
                 return True, {}


        if self._is_completed:
            return True, {}

        # 检查所有碎片是否都已锁定 (完成拼图)
        if all(piece.is_locked() for piece in self.pieces):
            self._is_completed = True
            print(f"Drag Puzzle for {self.config.get('file', 'current image')} Completed!")
            # TODO: 播放拼图完成音效 sfx_puzzle_complete
            if self.audio_manager:
                 # self.audio_manager.play_sfx("sfx_puzzle_complete") # 示例音效ID
                 pass # 待填充实际音效ID

            # 触发 on_complete 叙事事件
            complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
            return True, complete_narrative # 返回完成状态和触发的叙事事件

        # 检查是否触发了叙事事件
        narrative_events = self._check_and_trigger_narrative_events()

        # 检查是否停止了拖拽音效
        if not self._dragging_piece and self.audio_manager and self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"):
             self.audio_manager.stop_sfx("sfx_puzzle_dragging_looping")


        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制拼图碎片"""
        # 确保碎片 Surface 已创建 before drawing
        if not self._pieces_initialized:
             # 如果碎片还没初始化，可能需要先绘制一个占位背景或提示
             return # 不绘制碎片

        # 绘制每个碎片
        for piece in self.pieces:
            piece.draw(screen)

        # TODO: 绘制吸附目标的视觉提示 (可选)
        # TODO: 绘制拖拽碎片的视觉效果 (例如，阴影或高亮)


    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
        """检查当前状态是否触发了叙事事件，并返回未触发过的事件字典"""
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 on_stage_enter (在 GameManager 中触发，这里只作为参考)

        # 检查 on_drag_first_piece (第一次拖拽任意碎片时触发)
        # 这个判断需要在 handle_event 中标记，并在 update 中检查和返回
        if self._has_dragged_first_time and "on_drag_first_piece" in config_triggers:
           event_id = "on_drag_first_piece"
           if event_id not in self._triggered_narrative_events:
                triggered[event_id] = config_triggers[event_id]
                self._triggered_narrative_events.add(event_id)


        # 检查进度触发 (on_puzzle_progress_XX)
        # 计算已锁定的碎片数量比例
        locked_count = sum(piece.is_locked() for piece in self.pieces)
        total_pieces = len(self.pieces)
        if total_pieces > 0:
            progress_percent = locked_count / total_pieces * 100
        else:
            progress_percent = 0

        # 示例检查 50% 进度触发 (从 config.narrative_triggers 中获取进度触发点)
        for trigger_key, text_ids in config_triggers.items():
            if trigger_key.startswith("on_puzzle_progress_"):
                try:
                    threshold = int(trigger_key.split("_")[-1]) # 从 key 中解析进度阈值 (例如 "on_puzzle_progress_50" -> 50)
                    if progress_percent >= threshold:
                         event_id = trigger_key
                         if event_id not in self._triggered_narrative_events:
                              triggered[event_id] = text_ids
                              self._triggered_narrative_events.add(event_id)
                except ValueError:
                    print(f"警告: 拼图进度触发器 {trigger_key} 格式无效。")


        # 检查 on_complete (互动完成)
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             # on_complete 事件只在互动模块的 is_completed 第一次为 True 时，由 GameManager._on_interaction_complete 触发
             triggered[event_id] = config_triggers[event_id]


        return triggered

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     return {
    #         # 保存每个碎片的位置 (屏幕坐标) 和锁定状态
    #         "piece_positions": {piece.id: piece.rect.topleft for piece in self.pieces},
    #         "piece_locked_status": {piece.id: piece.is_locked() for piece in self.pieces},
    #         "triggered_narrative_events": list(self._triggered_narrative_events),
    #         "_has_dragged_first_time": self._has_dragged_first_time
    #     }

    # def load_state(self, state_data, image_display_rect: pygame.Rect): # 加载时需要传递当前显示区域
    #     # 确保碎片 Surface 已创建
    #     # _create_puzzle_pieces 会根据 current_image 和 image_display_rect 计算正确位置和尺寸
    #     # 在这里，pieces_config 应该已经加载了，所以可以直接用它来创建碎片
    #     self._pieces_initialized = False # 标记未初始化，以便 _create_puzzle_pieces 重新创建
    #     self._create_puzzle_pieces(image_display_rect) # 重新创建碎片 Surface

    #     if not self.pieces: # 如果碎片创建失败，加载也失败
    #         print("警告: 加载拼图状态失败，无法重新创建碎片。")
    #         self._is_completed = True # 标记完成以避免进一步错误
    #         return

    #     # 恢复每个碎片的位置和锁定状态
    #     for piece in self.pieces:
    #          # 在保存的状态数据中查找对应的碎片
    #          piece_id_str = str(piece.id) # 保存的键可能是字符串
    #          if piece_id_str in state_data.get("piece_positions", {}):
    #              # 加载保存的位置 (屏幕坐标)，并设置给碎片
    #              piece.set_position(tuple(state_data["piece_positions"][piece_id_str]))
    #          if piece_id_str in state_data.get("piece_locked_status", {}):
    #              # 加载锁定状态
    #              piece.set_locked(state_data["piece_locked_status"][piece_id_str])

    #     # 恢复其他状态
    #     self._triggered_narrative_events = set(state_data.get("triggered_narrative_events", []))
    #     self._has_dragged_first_time = state_data.get("_has_dragged_first_time", False)

    #     # 重新计算完成状态
    #     self._is_completed = all(piece.is_locked() for piece in self.pieces) # 重新计算完成状态
    #     print(f"加载拼图状态完成。Is completed: {self._is_completed}")

    #     self._is_completed = all(piece.is_locked() for piece in self.pieces) if self.pieces else True

    # HybridInteraction 需要调用的方法，用于设置碎片 (Stage 5.2)
    def set_pieces(self, pieces: list[PuzzlePiece]):
        """设置拼图模块的碎片列表 (用于混合玩法生成碎片后传递)"""
        self.pieces = pieces
        self._pieces_initialized = True # 标记碎片已初始化
        # 碎片的位置和锁定状态需要在 HybridInteraction 中生成时设置

    def enable_dragging(self):
         """启用碎片的拖拽 (如果需要分步启用拖拽)"""
         # 默认碎片就是可拖拽的 (除非 locked)
         # 如果有分步启用拖拽的需求，可以在 PuzzlePiece 中添加 is_draggable 标志，并在绘制/handle_event 中检查
         print("Dragging enabled for puzzle pieces.")
         pass # 目前不需要特殊处理，碎片默认就是可拖拽的