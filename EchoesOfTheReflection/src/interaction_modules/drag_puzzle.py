# src/interaction_modules/drag_puzzle.py
import pygame
from src.settings import Settings
from src.image_renderer import ImageRenderer
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
        self.settings = image_renderer.settings

        self.puzzle_config = config.get("puzzle_config", {})
        self.rows = self.puzzle_config.get("rows", 3)
        self.cols = self.puzzle_config.get("cols", 3)
        self.artistic_cut = self.puzzle_config.get("artistic_cut", False)
        self.initial_scatter_range = self.puzzle_config.get("initial_scatter_range", 0.2)

        # 拼图碎片列表
        self.pieces = [] # List of PuzzlePiece objects
        self._create_puzzle_pieces()

        self._dragging_piece = None # 当前正在拖拽的碎片
        self._drag_offset = (0, 0) # 拖拽时的鼠标偏移

        # 拼图完成状态
        self._is_completed = False

        # 跟踪已触发的叙事事件
        self._triggered_narrative_events = set()

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

        # TODO: 实现艺术化切割或简单网格切割，获取每个碎片的 Surface
        # 对于简单网格切割:
        piece_surfaces = []
        for r in range(self.rows):
            for c in range(self.cols):
                piece_rect = pygame.Rect(c * piece_width, r * piece_height, piece_width, piece_height)
                piece_surface = source_surface.subsurface(piece_rect)
                piece_surfaces.append(piece_surface)

        # TODO: 根据 config 中的 pieces 定义（如果存在）来创建 PuzzlePiece 对象
        # 否则，使用默认的网格索引和位置
        self.pieces = []
        all_correct_positions = [] # 存储所有正确位置的屏幕坐标
        for r in range(self.rows):
            for c in range(self.cols):
                piece_index = r * self.cols + c
                piece_surface = piece_surfaces[piece_index]

                # 计算正确位置 (相对于图片显示区域左上角的像素坐标)
                correct_pos_local = (c * piece_width, r * piece_height)
                # 示例：将本地坐标存储在 PuzzlePiece 对象中

                self.pieces.append(PuzzlePiece(piece_index, piece_surface, correct_pos_local, (r, c)))

        # 计算碎片的初始随机散开位置 (在图片显示区域范围内)
        # TODO: 将正确位置转换为屏幕坐标，然后在其周围随机偏移
        image_display_rect = self.image_renderer.image_display_rect # 需要当前的显示区域
        scatter_width = image_display_rect.width * self.initial_scatter_range
        scatter_height = image_display_rect.height * self.initial_scatter_range

        for piece in self.pieces:
            # 示例：将正确位置 (相对于图片区域的像素坐标) 转换为屏幕坐标
            correct_screen_pos = (
                image_display_rect.left + piece.correct_pos_local[0],
                image_display_rect.top + piece.correct_pos_local[1]
            )
            # 在正确位置周围随机偏移
            initial_pos_screen = (
                correct_screen_pos[0] + random.uniform(-scatter_width, scatter_width),
                correct_screen_pos[1] + random.uniform(-scatter_height, scatter_height)
            )
            piece.set_position(initial_pos_screen) # 设置碎片在屏幕上的初始位置
            piece.set_locked(False) # 初始为可拖拽状态

        # 打乱碎片的绘制顺序，增加随机感
        random.shuffle(self.pieces)

    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            mouse_pos = event.pos
            # 检查是否点击到任何一个未锁定（可拖拽）的碎片
            for piece in reversed(self.pieces): # 从后往前检查，确保点击到最上面的碎片
                if not piece.is_locked() and piece.rect.collidepoint(mouse_pos):
                    self._dragging_piece = piece
                    self._drag_offset = (mouse_pos[0] - piece.rect.left, mouse_pos[1] - piece.rect.top)
                    # 将被拖拽的碎片放到列表末尾，使其绘制在最上层
                    self.pieces.remove(piece)
                    self.pieces.append(piece)

                    # 触发第一次拖拽叙事 (如果配置了)
                    if self._dragging_piece and "on_drag_first_piece" in self.config.get("narrative_triggers", {}) and "on_drag_first_piece" not in self._triggered_narrative_events:
                        pass # 在 update 中统一返回叙事事件

                    # TODO: 播放拾起音效 sfx_puzzle_pickup
                    # self.audio_manager.play_sfx("sfx_puzzle_pickup")

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
                    # self.audio_manager.play_sfx("sfx_puzzle_snap")
                else:
                     # TODO: 播放放下音效 sfx_puzzle_drop
                     pass # self.audio_manager.play_sfx("sfx_puzzle_drop")

                self._dragging_piece = None # 停止拖拽

        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._dragging_piece:
                mouse_pos = event.pos
                # 更新碎片位置，考虑拖拽偏移
                new_x = mouse_pos[0] - self._drag_offset[0]
                new_y = mouse_pos[1] - self._drag_offset[1]
                self._dragging_piece.set_position((new_x, new_y))

                # TODO: 播放拖拽音效 sfx_puzzle_dragging_looping (循环音效)
                # if not self.audio_manager.is_sfx_playing("sfx_puzzle_dragging_looping"): # 避免重复播放
                #     self.audio_manager.play_sfx("sfx_puzzle_dragging_looping", loop=True)

        # TODO: 鼠标移动停止时，停止拖拽音效


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
            print(f"Drag Puzzle for {self.config['file']} Completed!")
            # TODO: 播放拼图完成音效 sfx_puzzle_complete
            # self.audio_manager.play_sfx("sfx_puzzle_complete")
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
        # 这个判断需要在 handle_event 中标记，并在 update 中检查和返回
        # 示例 (伪代码):
        # if self._just_started_dragging_first_time:
        #    event_id = "on_drag_first_piece"
        #    if event_id in config_triggers and event_id not in self._triggered_narrative_events:
        #         triggered[event_id] = config_triggers[event_id]
        #         self._triggered_narrative_events.add(event_id)
        #    self._just_started_dragging_first_time = False


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

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     return {
    #         "piece_positions": {piece.id: piece.rect.topleft for piece in self.pieces},
    #         "piece_locked_status": {piece.id: piece.is_locked() for piece in self.pieces},
    #         "triggered_narrative_events": list(self._triggered_narrative_events)
    #     }

    # def load_state(self, state_data):
    #     # 重新创建碎片，然后根据保存的状态设置位置和锁定状态
    #     self._create_puzzle_pieces() # 先创建碎片
    #     for piece in self.pieces:
    #          if str(piece.id) in state_data["piece_positions"]: # 保存的键可能是字符串
    #              piece.set_position(tuple(state_data["piece_positions"][str(piece.id)]))
    #          if str(piece.id) in state_data["piece_locked_status"]:
    #              piece.set_locked(state_data["piece_locked_status"][str(piece.id)])
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._is_completed = all(piece.is_locked() for piece in self.pieces) # 重新计算完成状态