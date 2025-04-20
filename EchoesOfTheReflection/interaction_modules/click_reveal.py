# interaction_modules/click_reveal.py
import pygame
# 导入自定义模块 - 它们现在位于根目录
from settings import Settings
from image_renderer import ImageRenderer
from audio_manager import AudioManager # 需要AudioManager来播放音效


class ClickReveal:
    """
    处理Click Reveal玩法逻辑。
    玩家点击预设的区域，图片逐渐显现。
    """

    def __init__(self, config: dict, image_renderer: ImageRenderer):
        """
        初始化点击显现模块。
        config: 来自image_config.json的当前图片配置。
        image_renderer: 用于图片显示和效果控制的ImageRenderer实例。
        """
        self.config = config
        self.image_renderer = image_renderer
        self.settings: Settings = image_renderer.settings # 获取settings实例
        self.audio_manager: AudioManager = self.settings.game_manager.audio_manager # 从settings获取GameManager，再获取AudioManager

        # 从config中加载点击点信息
        # click_points 存储的是原始图片中的像素坐标 [x, y]
        self.click_points_config = config.get("click_points", [])
        # 记录每个点击点是否已被激活 {point_id: True/False}
        self.activated_points = {point["id"]: False for point in self.click_points_config}

        # 显影进度控制
        self.reveal_progress = 0.0
        self.reveal_progress_per_click = config.get("reveal_progress_per_click", 0.25) # 每次点击增加的进度比例

        # 跟踪已触发的叙事事件，避免重复触发
        self._triggered_narrative_events = set()

        # 标记是否已完成所有点击
        self._is_completed = False

        # TODO: 初始化与点击点相关的视觉效果（例如，点击点的高亮表面或Rects）
        self._init_visual_elements()


    def _init_visual_elements(self):
        """初始化点击点的视觉表示"""
        # 例如，为每个点击点创建一个 Rect，用于绘制高亮效果和碰撞检测
        # 这些Rect的位置需要根据 ImageRenderer 的 image_display_rect 动态计算
        self.click_point_display_rects = {} # {point_id: Pygame.Rect}
        self.click_point_highlight_surface = None # TODO: 加载点击点的高亮图片资源

        # TODO: 加载点击点高亮图片 (例如，一个小光点或圆圈)
        # highlight_image_path = self.settings.EFFECTS_DIR + "click_highlight.png" # 示例资源路径
        # if os.path.exists(highlight_image_path):
        #     try:
        #          self.click_point_highlight_surface = pygame.image.load(highlight_image_path).convert_alpha()
        #     except pygame.error as e:
        #          print(f"警告：无法加载点击点高亮图片 {highlight_image_path}: {e}")

        # 初始计算一次点击点的显示Rects (在 resize 或 load_image 后需要重新计算)
        # self._calculate_point_display_rects(self.image_renderer.image_display_rect)


    def _calculate_point_display_rects(self, image_display_rect: pygame.Rect):
        """根据当前图片显示区域，计算点击点在屏幕上的显示矩形"""
        self.click_point_display_rects = {}
        highlight_size = 40 # TODO: 点击点视觉表示的尺寸 (像素)

        for point_config in self.click_points_config:
            point_id = point_config["id"]
            original_x = point_config["x"]
            original_y = point_config["y"]

            # 将原始图片坐标转换为屏幕坐标
            screen_pos = self.image_renderer.get_screen_coords_from_original(original_x, original_y)

            # 创建一个以屏幕坐标为中心的矩形作为点击区域和绘制区域
            point_rect = pygame.Rect(0, 0, highlight_size, highlight_size)
            point_rect.center = screen_pos

            self.click_point_display_rects[point_id] = point_rect


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed: # 如果已完成，不再处理点击事件
            return

        # 确保点击点显示Rects已计算 (在窗口resize或图片加载后需要)
        if not self.click_point_display_rects:
            self._calculate_point_display_rects(image_display_rect)


        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键点击
            mouse_pos = event.pos # 屏幕坐标

            # 检查点击是否在图片的显示区域内 (可选，如果点击点只在图片内)
            # if image_display_rect.collidepoint(mouse_pos):

            for point_config in self.click_points_config:
                point_id = point_config["id"]
                # 检查点击是否在当前点击点区域内 (使用计算好的显示Rect进行碰撞检测)
                if not self.activated_points[point_id]:
                    point_display_rect = self.click_point_display_rects.get(point_id)
                    if point_display_rect and point_display_rect.collidepoint(mouse_pos):
                        self.activated_points[point_id] = True
                        self._on_point_activated(point_id)
                        break # 一次点击只激活一个点

    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新点击显现状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        if self._is_completed:
            return True, {} # 已完成，不再更新

        # 确保点击点显示Rects已计算 (在窗口resize或图片加载后需要)
        if not self.click_point_display_rects:
            self._calculate_point_display_rects(image_display_rect)


        # 根据已激活的点击点数量更新显影进度
        activated_count = sum(self.activated_points.values())
        total_points = len(self.click_points_config)

        # 根据点击点数量直接设置进度
        if total_points > 0:
             target_progress = activated_count / total_points
        else:
             target_progress = 1.0 # 没有点击点则直接完成

        # 更新显影进度
        self.reveal_progress = target_progress

        # 通知 ImageRenderer 更新显影效果
        self.image_renderer.update_effect("blur_reveal", self.reveal_progress) # TODO: ImageRenderer需要实现一个通用的显影效果更新


        # 检查是否所有点击点都已激活
        if activated_count == total_points and total_points > 0:
             self._is_completed = True
             print(f"Click Reveal for {self.config.get('file', self.config.get('description', 'current image'))} Completed!")
             # 在这里触发 on_all_clicked 和 on_complete 叙事事件
             narrative_events = self._check_and_trigger_narrative_events(check_complete=True) # 检查所有触发器，包括 complete
             return True, narrative_events # 返回完成状态和触发的叙事事件
        elif total_points == 0: # 没有点击点也视为完成
             self._is_completed = True
             complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
             return True, complete_narrative

        # 检查是否触发了其他进度相关的叙事事件
        narrative_events = self._check_and_trigger_narrative_events()

        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制点击显现模块的视觉元素（例如，未激活点击点的高亮）"""
        if self._is_completed:
             # 完成后可能绘制最终状态或无 thing
             # 最终显现效果由 ImageRenderer 绘制
             return

        # 绘制未激活点击点的高亮提示
        # 确保点击点显示Rects已计算
        if not self.click_point_display_rects:
            self._calculate_point_display_rects(image_display_rect)


        for point_config in self.click_points_config:
            point_id = point_config["id"]
            if not self.activated_points[point_id]:
                point_display_rect = self.click_point_display_rects.get(point_id)
                if point_display_rect:
                    # TODO: 绘制高亮圆圈或图标
                    # if self.click_point_highlight_surface:
                    #     screen.blit(self.click_point_highlight_surface, point_display_rect.topleft)
                    # else:
                    # 简单示例：绘制一个白点或圆圈
                    pygame.draw.circle(screen, self.settings.WHITE, point_display_rect.center, 10) # 绘制一个白色圆圈


    def _on_point_activated(self, point_id):
        """处理单个点击点被激活后的逻辑"""
        print(f"点击点 {point_id} 被激活")
        # 增加显影进度 (由 update 方法根据 activated_points 统一计算)

        # 触发点击反馈特效和音效
        # TODO: 触发点击反馈特效
        # if self.settings.CLICK_FEEDBACK_EFFECT_ID: # 示例通用点击反馈特效ID
        #     self.image_renderer.trigger_effect(self.settings.CLICK_FEEDBACK_EFFECT_ID, self.click_point_display_rects.get(point_id).center) # 传递位置

        # 播放点击音效
        if self.audio_manager:
            self.audio_manager.play_sfx("sfx_click") # 示例通用点击音效ID

        # 检查是否触发了点击相关的叙事事件 (这个检查统一放在 update 里处理)


    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
        """检查当前状态是否触发了叙事事件，并返回未触发过的事件字典"""
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 OnClickAny (点击任意点) - 第一次点击任意点后触发
        if sum(self.activated_points.values()) == 1 and "on_click_any" in config_triggers: # 只有激活点数量从0变为1时触发
            event_id = "on_click_any"
            if event_id not in self._triggered_narrative_events:
                triggered[event_id] = config_triggers[event_id]
                self._triggered_narrative_events.add(event_id)

        # 检查 OnClickSpecificPoint (点击特定点) - 每次点击一个特定点后触发 (如果配置了)
        # 遍历所有点，检查刚刚被激活的点
        # 需要一种方式判断点是否是“刚刚”被激活
        # 可以在 _on_point_activated 中设置一个标志，然后在 update 中检查并清除
        # 或者在 _check_and_trigger_narrative_events 中，将已检查的特定点击事件也添加到 _triggered_narrative_events
        for point_id, is_activated in self.activated_points.items():
             if is_activated:
                  event_id = f"on_click_point_{point_id}"
                  if event_id in config_triggers and event_id not in self._triggered_narrative_events:
                       triggered[event_id] = config_triggers[event_id]
                       self._triggered_narrative_events.add(event_id)


        # 检查 OnAllClicked (所有点都已点击) - 只有当所有点都被激活时触发一次
        if all(self.activated_points.values()) and len(self.activated_points) > 0 and "on_all_clicked" in config_triggers:
            event_id = "on_all_clicked"
            if event_id not in self._triggered_narrative_events:
                triggered[event_id] = config_triggers[event_id]
                self._triggered_narrative_events.add(event_id)

        # 检查 OnComplete (互动完成) - 这个通常在 GameManager._on_interaction_complete 里处理
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)


        # TODO: 检查进度相关的叙事事件 (例如，on_reveal_progress_50)
        # if self.reveal_progress >= 0.5 and "on_reveal_progress_50" in config_triggers:
        #     event_id = "on_reveal_progress_50"
        #     if event_id not in self._triggered_narrative_events:
        #          triggered[event_id] = config_triggers[event_id]
        #          self._triggered_narrative_events.add(event_id)


        return triggered

    # 在窗口resize时，需要重新计算点击点在屏幕上的显示位置
    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
         """处理窗口大小改变事件，重新计算点击点位置"""
         self._calculate_point_display_rects(image_display_rect)


    # TODO: 添加保存和加载模块状态的方法 (用于保存游戏进度)
    # def get_state(self):
    #     return {
    #         "activated_points": self.activated_points, # 保存激活状态
    #         "reveal_progress": self.reveal_progress, # 保存进度
    #         "triggered_narrative_events": list(self._triggered_narrative_events) # 保存已触发事件
    #         # _is_completed 可以从 activated_points 计算
    #     }

    # def load_state(self, state_data, image_display_rect: pygame.Rect):
    #     self.activated_points = state_data["activated_points"]
    #     self.reveal_progress = state_data["reveal_progress"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._is_completed = all(self.activated_points.values()) if self.activated_points else True # 重新计算完成状态
    #     # 需要在加载状态后重新计算点击点位置，因为 image_display_rect 可能变了
    #     self._calculate_point_display_rects(image_display_rect)
    #     # TODO: 根据加载的进度更新视觉效果
    #     self.image_renderer.update_effect("blur_reveal", self.reveal_progress)