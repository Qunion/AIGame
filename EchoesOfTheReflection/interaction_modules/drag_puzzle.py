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

        # 获取要切割的原始 Surface (可能是缩放裁剪后的图片)
        source_surface = self.image_renderer.current_image
        img_width, img_height = source_surface.get_size()

        piece_width = img_width // self.cols
        piece_height = img_height // self.rows

        # 根据 config 中的 pieces 定义或默认网格来创建碎片
        pieces_config = self.puzzle_config.get("pieces") # 如果 config 中有 pieces 定义
        if pieces_config:
             # TODO: 根据更复杂的 piece config 创建碎片 (例如，Stage 5.2 由点击生成碎片)
             # For Stage 4, assume pieces config is not used, use default grid
             pass # 待实现

        # 默认简单网格切割:
        self.pieces = []
        all_correct_positions_local = [] # 存储所有正确位置的本地图片坐标 (相对于图片显示区域左上角)
        for r in range(self.rows):
            for c in range(self.cols):
                piece_index = r * self.cols + c
                piece_rect_local = pygame.Rect(c * piece_width, r * piece_height, piece_width, piece_height)
                piece_surface = source_surface.subsurface(piece_rect_local)

                correct_pos_local = (piece_rect_local.x, piece_rect_local.y) # 正确位置是其在切割前的本地坐标
                grid_pos = (r, c) # 网格位置

                self.pieces.append(puzzle_piece.PuzzlePiece(f"piece_{r}_{c}", piece_surface, correct_pos_local, grid_pos))
                all_correct_positions_local.append(correct_pos_local)


        # 计算碎片的初始随机散开位置 (在图片显示区域范围内)
        image_display_rect = self.image_renderer.image_display_rect # 需要当前的显示区域
        scatter_width = image_display_rect.width * self.initial_scatter_range
        scatter_height = image_display_rect.height * self.initial_scatter_range

        initial_positions_screen = [] # 存储打乱后的初始屏幕位置
        correct_positions_screen = [ (image_display_rect.left + pos[0], image_display_rect.top + pos[1]) for pos in all_correct_positions_local ] # 所有正确位置的屏幕坐标

        # 生成随机散开的位置
        for correct_screen_pos in correct_positions_screen:
            initial_pos_screen = (
                correct_screen_pos[0] + random.uniform(-scatter_width, scatter_width),
                correct_screen_pos[1] + random.uniform(-scatter_height, scatter_height)
            )
            initial_positions_screen.append(initial_pos_screen)

        # 将打乱后的位置赋予碎片
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
                snap_threshold = 20 # 吸附容忍度像素
                # 计算碎片的正确屏幕位置
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
                        self.audio_manager.play_sfx("sfx_puzzle_snap")
                else:
                     # TODO: 播放放下音效 sfx_puzzle_drop
                     if self.audio_manager:
                         self.audio_manager.play_sfx("sfx_puzzle_drop")

                self._dragging_piece = None # 停止拖拽

                # TODO: 停止拖拽音效 (如果使用循环音效)
                # if self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"):
                #     self.audio_manager.stop_sfx("sfx_puzzle_dragging_looping")


        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._dragging_piece:
                mouse_pos = event.pos
                # 更新碎片位置，考虑拖拽偏移
                new_x = mouse_pos[0] - self._drag_offset[0]
                new_y = mouse_pos[1] - self._drag_offset[1]
                self._dragging_piece.set_position((new_x, new_y))

                # TODO: 播放拖拽音效 sfx_puzzle_dragging_looping (循环音效)
                # if not self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"): # 避免重复播放
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
        # TODO: 绘制拖拽碎片的视觉效果 (例如，阴影或高亮)


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
        # TODO: 检查其他进度触发点


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
             # 重新计算每个碎片的正确屏幕位置 (吸附点)
             for piece in self.pieces:
                 # 将原始本地坐标转换为新的屏幕坐标
                 correct_screen_pos = (
                     image_display_rect.left + piece.correct_pos_local[0],
                     image_display_rect.top + piece.correct_pos_local[1]
                 )
                 # 如果碎片已锁定，更新其位置到新的正确屏幕位置
                 if piece.is_locked():
                     piece.set_position(correct_screen_pos)
                 # 如果碎片未锁定，它的屏幕位置需要保持相对位置或重新计算散开位置
                 # 最简单的方式是让未锁定碎片保持当前相对位置，或者重新随机散开（可能丢失进度）
                 # 保持相对位置：(当前屏幕位置 - 旧图片区域左上角) / 旧图片区域尺寸 * 新图片区域尺寸 + 新图片区域左上角
                 # TODO: 实现复杂的未锁定碎片位置更新逻辑

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     return {
    #         "piece_positions": {piece.id: piece.rect.topleft for piece in self.pieces},
    #         "piece_locked_status": {piece.id: piece.is_locked() for piece in self.pieces},
    #         "triggered_narrative_events": list(self._triggered_narrative_events),
    #         "_has_started_dragging": self._has_started_dragging,
    #     }

    # def load_state(self, state_data, image_display_rect: pygame.Rect):
    #     # 重新创建碎片 (它们的原始本地位置已确定)
    #     self._create_puzzle_pieces() # 这个方法创建了碎片，并计算了初始散开位置和正确本地位置
    #     # 现在根据保存的状态设置位置和锁定状态
    #     loaded_positions = state_data["piece_positions"]
    #     loaded_locked_status = state_data["piece_locked_status"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._has_started_dragging = state_data["_has_started_dragging"]

    #     # 创建一个字典方便通过 ID 查找碎片
    #     pieces_by_id = {piece.id: piece for piece in self.pieces}

    #     for piece_id_str, pos_list in loaded_positions.items():
    #          piece_id = int(piece_id_str) if piece_id_str.isdigit() else piece_id_str # 确保ID类型一致
    #          if piece_id in pieces_by_id:
    #              piece = pieces_by_id[piece_id]
    #              # 保存的位置是屏幕坐标，加载时直接设置
    #              piece.set_position(tuple(pos_list))

    #     for piece_id_str, locked_status in loaded_locked_status.items():
    #          piece_id = int(piece_id_str) if piece_id_str.isdigit() else piece_id_str
    #          if piece_id in pieces_by_id:
    #              pieces_by_id[piece_id].set_locked(locked_status)

    #     self._is_completed = all(piece.is_locked() for piece in self.pieces) if self.pieces else True # 重新计算完成状态
    #     # TODO: 如果 _dragging_piece 需要保存，也需要加载