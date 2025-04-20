# interaction_modules/drag_puzzle.py
import pygame
import os # 用于加载碎片纹理
# 导入自定义模块 - 它们现在位于根目录
from settings import Settings
from image_renderer import ImageRenderer
from audio_manager import AudioManager # 需要AudioManager来播放音效
# 导入拼图碎片类 - 它在同一个子目录
from . import puzzle_piece
import random # 用于打乱碎片

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
        self.settings: Settings = image_renderer.settings
        self.audio_manager: AudioManager = self.settings.game_manager.audio_manager

        self.puzzle_config = config.get("puzzle_config", {})
        self.rows = self.puzzle_config.get("rows", 3)
        self.cols = self.puzzle_config.get("cols", 3)
        self.artistic_cut = self.puzzle_config.get("artistic_cut", False)
        self.initial_scatter_range = self.puzzle_config.get("initial_scatter_range", 0.2)

        # 拼图碎片列表
        self.pieces: list[puzzle_piece.PuzzlePiece] = [] # List of PuzzlePiece objects
        self._create_puzzle_pieces()

        self._dragging_piece: puzzle_piece.PuzzlePiece | None = None # 当前正在拖拽的碎片
        self._drag_offset = (0, 0) # 拖拽时的鼠标偏移

        # 拼图完成状态
        self._is_completed = False

        # 跟踪已触发的叙事事件
        self._triggered_narrative_events = set()

        # 跟踪第一次拖拽叙事 (只触发一次)
        self._has_started_dragging = False


    def _create_puzzle_pieces(self):
        """根据图片和配置创建拼图碎片"""
        if not self.image_renderer.current_image:
            print("错误：无法创建拼图碎片，图片未加载！")
            return

        # 获取要切割的原始 Surface (可能是缩放裁剪后的图片，这是在 ImageRenderer 中已经处理好的显示尺寸的图片)
        source_surface = self.image_renderer.current_image
        img_width, img_height = source_surface.get_size() # 这是图片的显示尺寸

        piece_width = img_width // self.cols
        piece_height = img_height // self.rows

        # 根据 config 中的 pieces 定义或默认网格来创建碎片
        pieces_config = self.puzzle_config.get("pieces") # 如果 config 中有 pieces 定义
        if pieces_config:
             # TODO: 根据更复杂的 piece config 创建碎片 (例如，Stage 5.2 由点击生成碎片)
             # For Stage 4, assume pieces config is not used, use default grid
             # 如果 pieces config 存在，它定义了碎片的 ID 和正确本地坐标
             # 需要根据这些信息从 source_surface 中截取对应的碎片 Surface
             self.pieces = []
             for piece_cfg in pieces_config:
                  piece_id = piece_cfg["id"]
                  correct_pos_local = tuple(piece_cfg["correct_pos_local"]) # 假设是本地坐标 [x, y]
                  # 根据本地坐标和碎片尺寸截取 Surface
                  piece_rect_local = pygame.Rect(correct_pos_local[0], correct_pos_local[1], piece_width, piece_height) # 假设所有碎片尺寸相同
                  piece_surface = source_surface.subsurface(piece_rect_local)
                  grid_pos = piece_cfg.get("grid_pos") # 可选的网格位置信息

                  self.pieces.append(puzzle_piece.PuzzlePiece(piece_id, piece_surface, correct_pos_local, grid_pos))

        else:
            # 默认简单网格切割:
            self.pieces = []
            for r in range(self.rows):
                for c in range(self.cols):
                    piece_index = r * self.cols + c
                    piece_rect_local = pygame.Rect(c * piece_width, r * piece_height, piece_width, piece_height)
                    piece_surface = source_surface.subsurface(piece_rect_local)

                    correct_pos_local = (piece_rect_local.x, piece_rect_local.y) # 正确位置是其在切割前的本地坐标
                    grid_pos = (r, c) # 网格位置

                    self.pieces.append(puzzle_piece.PuzzlePiece(f"piece_{r}_{c}", piece_surface, correct_pos_local, grid_pos))


        # 计算碎片的初始随机散开位置 (在图片显示区域范围内)
        image_display_rect = self.image_renderer.image_display_rect # 图片在屏幕上的显示区域
        scatter_width = image_display_rect.width * self.initial_scatter_range
        scatter_height = image_display_rect.height * self.initial_scatter_range

        initial_positions_screen = [] # 存储打乱后的初始屏幕位置

        # 遍历所有碎片，计算它们的正确屏幕位置，并生成随机散开的初始位置
        correct_positions_screen = []
        for piece in self.pieces:
            correct_screen_pos = (
                image_display_rect.left + piece.correct_pos_local[0],
                image_display_rect.top + piece.correct_pos_local[1]
            )
            correct_positions_screen.append(correct_screen_pos) # 存储正确屏幕位置

            # 生成随机散开的初始位置
            initial_pos_screen = (
                correct_screen_pos[0] + random.uniform(-scatter_width, scatter_width),
                correct_screen_pos[1] + random.uniform(-scatter_height, scatter_height)
            )
            initial_positions_screen.append(initial_pos_screen)

        # 将打乱后的初始屏幕位置赋予碎片
        random.shuffle(initial_positions_screen)
        for i, piece in enumerate(self.pieces):
             piece.set_position(initial_positions_screen[i])
             piece.set_locked(False) # 初始为可拖拽状态

        # 打乱碎片的绘制顺序，增加随机感
        random.shuffle(self.pieces)


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        mouse_pos = event.pos # 屏幕坐标

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            # 检查是否点击到任何一个未锁定（可拖拽）的碎片
            for piece in reversed(self.pieces): # 从后往前检查，确保点击到最上面的碎片
                if not piece.is_locked() and piece.rect.collidepoint(mouse_pos):
                    self._dragging_piece = piece
                    # 计算拖拽偏移：鼠标位置相对于碎片左上角的位置
                    self._drag_offset = (mouse_pos[0] - piece.rect.left, mouse_pos[1] - piece.rect.top)
                    # 将被拖拽的碎片放到列表末尾，使其绘制在最上层
                    self.pieces.remove(piece)
                    self.pieces.append(piece)

                    # 触发第一次拖拽叙事 (如果配置了)
                    if not self._has_started_dragging:
                        self._has_started_dragging = True
                        if "on_drag_first_piece" in self.config.get("narrative_triggers", {}):
                             # 返回触发的事件，让 GameManager 启动叙事
                             pass # 在 update 中统一返回叙事事件

                    # TODO: 播放拾起音效 sfx_puzzle_pickup
                    if self.audio_manager:
                        self.audio_manager.play_sfx("sfx_puzzle_pickup")

                    break # 只处理一个碎片

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: # 左键抬起
            if self._dragging_piece:
                # 检查是否吸附到正确位置
                # TODO: 吸附容忍度可以从 config 中读取
                snap_threshold = self.puzzle_config.get("snap_threshold", 20) # 吸附容忍度像素

                # 计算碎片的正确屏幕位置
                correct_screen_pos = (
                    image_display_rect.left + self._dragging_piece.correct_pos_local[0],
                    image_display_rect.top + self._dragging_piece.correct_pos_local[1]
                )
                # 检查当前位置是否接近正确位置 (使用碎片左上角进行距离判断)
                if (self._dragging_piece.rect.left - correct_screen_pos[0])**2 + \
                   (self._dragging_piece.rect.top - correct_screen_pos[1])**2 <= snap_threshold**2:
                    # 吸附到位
                    self._dragging_piece.set_position(correct_screen_pos)
                    self._dragging_piece.set_locked(True) # 锁定碎片
                    # TODO: 播放吸附音效 sfx_puzzle_snap
                    if self.audio_manager:
                        self.audio_manager.play_sfx("sfx_puzzle_snap")
                else:
                     # TODO: 播放放下音效 sfx_puzzle_drop
                     if self.audio_manager:
                         self.audio_manager.play_sfx("sfx_puzzle_drop")

                self._dragging_piece = None # 停止拖拽

                # TODO: 停止拖拽音效 (如果使用循环音效)
                # if self.audio_manager and self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"):
                #     self.audio_manager.stop_sfx("sfx_puzzle_dragging_looping")


        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._dragging_piece:
                mouse_pos = event.pos
                # 更新碎片位置，考虑拖拽偏移
                new_x = mouse_pos[0] - self._drag_offset[0]
                new_y = mouse_pos[1] - self._drag_offset[1]
                self._dragging_piece.set_position((new_x, new_y))

                # TODO: 播放拖拽音效 sfx_puzzle_dragging_looping (循环音效)
                # if self.audio_manager and not self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"): # 避免重复播放
                #     self.audio_manager.play_sfx("sfx_puzzle_dragging_looping", loop=-1)


    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新拖拽拼图状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        if self._is_completed:
            return True, {}

        # 检查所有碎片是否都已锁定 (完成拼图)
        if all(piece.is_locked() for piece in self.pieces):
            self._is_completed = True
            print(f"Drag Puzzle for {self.config.get('file', self.config.get('description', 'current image'))} Completed!")
            # TODO: 播放拼图完成音效 sfx_puzzle_complete
            if self.audio_manager:
                self.audio_manager.play_sfx("sfx_puzzle_complete")
            # 触发 on_complete 叙事事件
            complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
            return True, complete_narrative # 返回完成状态和触发的叙事事件

        # 检查是否触发了进度相关的叙事事件
        narrative_events = self._check_and_trigger_narrative_events()


        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制拼图碎片"""
        # 绘制每个碎片
        for piece in self.pieces:
            piece.draw(screen)

        # TODO: 绘制吸附目标的视觉提示 (可选)
        # 例如，在正确位置绘制一个半透明的区域或边框
        # if not self._is_completed:
        #      for piece in self.pieces:
        #          if not piece.is_locked():
        #               correct_screen_pos = (
        #                   image_display_rect.left + piece.correct_pos_local[0],
        #                   image_display_rect.top + piece.correct_pos_local[1]
        #               )
        #               target_rect = pygame.Rect(correct_screen_pos, piece.rect.size)
        #               pygame.draw.rect(screen, (255, 255, 255, 50), target_rect, 2) # 半透明白色边框

        # TODO: 绘制拖拽碎片的视觉效果 (例如，阴影或高亮)
        # if self._dragging_piece:
        #     # 在拖拽碎片的当前位置下方绘制一个半透明阴影
        #     shadow_offset = (5, 5)
        #     shadow_color = (0, 0, 0, 100) # 半透明黑色
        #     shadow_rect = self._dragging_piece.rect.copy()
        #     shadow_rect.move_ip(shadow_offset)
        #     shadow_surface = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
        #     shadow_surface.fill(shadow_color)
        #     screen.blit(shadow_surface, shadow_rect.topleft)
        #     # self._dragging_piece.draw(screen) # 绘制碎片本身，它已经在主循环的最后绘制了，因为它在 pieces 列表的末尾


    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
        """检查当前状态是否触发了叙事事件，并返回未触发过的事件字典"""
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 on_stage_enter (在 GameManager 中触发，这里只作为参考)

        # 检查 on_drag_first_piece (第一次拖拽任意碎片时触发)
        if self._has_started_dragging and "on_drag_first_piece" in config_triggers:
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

        # 示例检查 50% 进度触发
        if progress_percent >= 50 and "on_puzzle_progress_50" in config_triggers:
            event_id = "on_puzzle_progress_50"
            if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)
        # TODO: 检查其他进度触发点，例如 25%, 75% 等


        # 检查 on_complete (互动完成)
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        return triggered

    # 在窗口resize时，需要重新计算碎片在屏幕上的位置和吸附点位置
    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
         """处理窗口大小改变事件，重新计算碎片位置和吸附点"""
         if self.pieces:
             # 获取旧的图片显示区域，以便计算相对位置
             # 需要在 resize 前保存旧的 image_display_rect，或者在 GameManager 中传递旧的
             # 简化的方法：假设 resize 发生时，未锁定的碎片保持它们相对于旧图片区域的比例位置
             # 已锁定的碎片则直接更新到新的正确屏幕位置

             # 先重新计算所有碎片的正确屏幕位置 (吸附点)
             for piece in self.pieces:
                 # correct_pos_local 是相对于图片显示区域的本地坐标
                 correct_screen_pos = (
                     image_display_rect.left + piece.correct_pos_local[0],
                     image_display_rect.top + piece.correct_pos_local[1]
                 )
                 # 如果碎片已锁定，更新其位置到新的正确屏幕位置
                 if piece.is_locked():
                     piece.set_position(correct_screen_pos)
                 else:
                      # 对于未锁定的碎片，需要根据它们的旧屏幕位置和旧的图片显示区域来计算新的屏幕位置
                      # 这是一个复杂的问题，涉及到状态保存或更复杂的坐标转换
                      # 最简单的临时方案：让未锁定的碎片保持当前屏幕位置，或者重新随机散开
                      # 保持当前屏幕位置：不做任何事，缺点是如果图片区域移动，碎片位置不对
                      # 重新随机散开：调用 _create_puzzle_pieces() 会重新散开，丢失未锁定碎片的相对位置进度

                      # 更合理的方案：保存未锁定碎片的相对位置 (相对于旧图片区域)，在 resize 时根据新图片区域重新计算绝对位置
                      # 需要在 PuzzlePiece 中保存相对位置，或者在 DragPuzzle 中统一管理
                      pass # TODO: 实现复杂的未锁定碎片位置更新逻辑

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     return {
    #         "piece_positions": {str(piece.id): piece.rect.topleft for piece in self.pieces}, # 保存屏幕坐标
    #         "piece_locked_status": {str(piece.id): piece.is_locked() for piece in self.pieces},
    #         "triggered_narrative_events": list(self._triggered_narrative_events),
    #         "_has_started_dragging": self._has_started_dragging,
    #         # TODO: 如果拖拽中的碎片也需要保存，需要保存 _dragging_piece 的ID和偏移量
    #         # "_dragging_piece_id": self._dragging_piece.id if self._dragging_piece else None,
    #         # "_drag_offset": self._drag_offset
    #     }

    # def load_state(self, state_data, image_display_rect: pygame.Rect):
    #     # 重新创建碎片 (它们的原始本地位置已确定)
    #     # 需要在加载前判断是否已经创建过碎片 (例如在 __init__ 里)
    #     if not self.pieces: # 如果还没有创建碎片 (第一次加载)
    #         self._create_puzzle_pieces() # 创建碎片，并计算了初始散开位置和正确本地位置

    #     # 现在根据保存的状态设置位置和锁定状态
    #     loaded_positions = state_data.get("piece_positions", {})
    #     loaded_locked_status = state_data.get("piece_locked_status", {})
    #     self._triggered_narrative_events = set(state_data.get("triggered_narrative_events", []))
    #     self._has_started_dragging = state_data.get("_has_started_dragging", False)

    #     # 创建一个字典方便通过 ID 查找碎片
    #     pieces_by_id = {piece.id: piece for piece in self.pieces}

    #     for piece_id_str, pos_list in loaded_positions.items():
    #          # 确保 ID 类型一致，保存时转为字符串，加载时转回原始类型（这里是 int 或 str）
    #          piece_id = piece_id_str # Assuming ID is string
    #          if piece_id in pieces_by_id:
    #              piece = pieces_by_id[piece_id]
    #              # 保存的位置是屏幕坐标，加载时直接设置
    #              piece.set_position(tuple(pos_list))

    #     for piece_id_str, locked_status in loaded_locked_status.items():
    #          piece_id = piece_id_str # Assuming ID is string
    #          if piece_id in pieces_by_id:
    #              pieces_by_id[piece_id].set_locked(locked_status)

    #     self._is_completed = all(piece.is_locked() for piece in self.pieces) if self.pieces else True # 重新计算完成状态
    #     # TODO: 如果 _dragging_piece 需要保存，也需要加载并重新设置引用
    #     # dragging_piece_id = state_data.get("_dragging_piece_id")
    #     # if dragging_piece_id is not None and dragging_piece_id in pieces_by_id:
    #     #      self._dragging_piece = pieces_by_id[dragging_piece_id]
    #     #      self._drag_offset = state_data.get("_drag_offset", (0,0))

    #     # TODO: 加载状态后，可能需要重新计算所有碎片的屏幕位置，以防 image_display_rect 改变
    #     # 或者保存的是相对位置，加载时再转屏幕位置
    #     # 重新计算所有碎片的屏幕位置 (包括锁定和未锁定的)
    #     # self.resize(image_display_rect.width, image_display_rect.height, image_display_rect) # 可以调用resize方法
