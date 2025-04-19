# src/interaction_modules/click_reveal.py
import pygame
from settings import Settings
from image_renderer import ImageRenderer # 导入用于坐标转换

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
        self.settings = image_renderer.settings # 获取设置

        # 从config中加载点击点信息
        # click_points 存储的是原始图片中的坐标或相对坐标
        self.click_points_config = config.get("click_points", [])
        # 记录每个点击点是否已被激活
        self.activated_points = {point["id"]: False for point in self.click_points_config}

        # 显影进度控制
        self.reveal_progress = 0.0
        self.reveal_progress_per_click = config.get("reveal_progress_per_click", 0.25) # 每次点击增加的进度比例

        # 跟踪已触发的叙事事件，避免重复触发
        self._triggered_narrative_events = set()

        # 标记是否已完成所有点击
        self._is_completed = False

        # TODO: 初始化与点击点相关的视觉效果（例如，点击点的高亮表面）
        self._init_visual_elements()

    def _init_visual_elements(self):
        """初始化点击点的视觉表示"""
        # 例如，为每个点击点创建一个小的 Surface 或 Rect，用于绘制高亮效果
        self.click_point_surfaces = {}
        for point_config in self.click_points_config:
             # 这里需要根据点击点是像素坐标还是相对坐标来创建Surface，并考虑缩放
             # 假设点击点配置的是相对于原始图片的像素坐标 [x, y]
             # 你需要在 ImageRenderer 中实现一个方法来将原始图片坐标转换为屏幕坐标
             # screen_pos = self.image_renderer.get_screen_coords_from_original(point_config["x"], point_config["y"])
             # self.click_point_surfaces[point_config["id"]] = self._create_highlight_surface(screen_pos) # 创建一个小的 Surface 或Rect

             # 最简单的方式是先用Rect占位，绘制时再根据实际显示区域计算位置
             self.click_point_surfaces[point_config["id"]] = pygame.Rect(0,0, 20, 20) # 占位Rect


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed: # 如果已完成，不再处理点击事件
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键点击
            mouse_pos = event.pos # 屏幕坐标

            # 检查点击是否在图片的显示区域内
            if image_display_rect.collidepoint(mouse_pos):
                # 将鼠标点击的屏幕坐标转换回原始图片坐标或相对坐标，以便与配置的点击点比较
                # relative_mouse_pos = self.image_renderer.get_relative_coords(mouse_pos) # 如果配置是相对坐标
                # 或者 original_image_mouse_pos = self.image_renderer.get_original_image_coords(mouse_pos) # 如果配置是原始像素坐标

                # 示例：假设 config 中的点击点是相对于原始图片的像素坐标
                original_image_mouse_pos = self.image_renderer.get_image_coords(mouse_pos) # 需要 ImageRenderer 实现此方法

                for point_config in self.click_points_config:
                    point_id = point_config["id"]
                    # 检查点击是否在当前点击点区域内 (假设点击点是圆形的，用阈值判断距离)
                    # 需要将 config 中的点坐标转换为实际的屏幕坐标进行碰撞检测
                    point_screen_pos = self.image_renderer.get_screen_coords_from_original(point_config["x"], point_config["y"]) # 需要 ImageRenderer 实现此方法
                    click_threshold = 30 # 点击容忍度像素

                    if not self.activated_points[point_id] and \
                       (mouse_pos[0] - point_screen_pos[0])**2 + (mouse_pos[1] - point_screen_pos[1])**2 <= click_threshold**2:

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

        # 根据已激活的点击点数量更新显影进度
        activated_count = sum(self.activated_points.values())
        total_points = len(self.click_points_config)

        # 根据点击点数量直接设置进度
        if total_points > 0:
             target_progress = activated_count / total_points
        else:
             target_progress = 1.0 # 没有点击点则直接完成

        # 可以平滑过渡进度
        # self.reveal_progress += (target_progress - self.reveal_progress) * 0.1 # 示例平滑过渡

        # 或者直接设置进度
        self.reveal_progress = target_progress

        # 通知 ImageRenderer 更新显影效果
        self.image_renderer.update_effect("blur_reveal", self.reveal_progress) # TODO: 实现一个通用的显影效果更新

        # 检查是否所有点击点都已激活
        if activated_count == total_points and total_points > 0:
             self._is_completed = True
             print(f"Click Reveal for {self.config['file']} Completed!")
             # 在这里触发 on_all_clicked 叙事事件
             narrative_events = self._check_and_trigger_narrative_events()
             return True, narrative_events # 返回完成状态和触发的叙事事件
        elif total_points == 0: # 没有点击点也视为完成
             self._is_completed = True
             return True, self._check_and_trigger_narrative_events()

        # 检查是否触发了进度相关的叙事事件
        narrative_events = self._check_and_trigger_narrative_events()

        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制点击显现模块的视觉元素（例如，未激活点击点的高亮）"""
        if self._is_completed:
             # 完成后可能绘制最终状态或无thing
             return

        # 绘制未激活点击点的高亮提示
        for point_config in self.click_points_config:
            point_id = point_config["id"]
            if not self.activated_points[point_id]:
                # 将点击点原始坐标转换为屏幕坐标进行绘制
                point_screen_pos = self.image_renderer.get_screen_coords_from_original(point_config["x"], point_config["y"]) # 需要 ImageRenderer 实现此方法
                # self._draw_highlight(screen, point_screen_pos) # 绘制高亮圆圈或图标

                # 简单示例：绘制一个白点
                pygame.draw.circle(screen, self.settings.WHITE, point_screen_pos, 10) # TODO: 替换为实际的高亮特效绘制

    def _on_point_activated(self, point_id):
        """处理单个点击点被激活后的逻辑"""
        print(f"点击点 {point_id} 被激活")
        # 增加显影进度 (由 update 方法根据 activated_points 统一计算)

        # 触发点击反馈特效和音效
        # self.image_renderer.trigger_effect(self.settings.CLICK_FEEDBACK_EFFECT_ID) # TODO: 实现通用点击反馈特效
        self.audio_manager.play_sfx("sfx_click") # 示例通用点击音效

        # 检查是否触发了点击相关的叙事事件
        # 这个检查统一放在 update 里处理，避免在事件处理函数中直接修改复杂状态和触发叙事

    def _check_and_trigger_narrative_events(self) -> dict:
        """检查当前状态是否触发了叙事事件，并返回未触发过的事件字典"""
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 OnClickAny (点击任意点)
        if sum(self.activated_points.values()) > 0 and "on_click_any" in config_triggers:
            event_id = "on_click_any"
            if event_id not in self._triggered_narrative_events:
                triggered[event_id] = config_triggers[event_id]
                self._triggered_narrative_events.add(event_id)

        # 检查 OnClickSpecificPoint (点击特定点)
        for point_id, is_activated in self.activated_points.items():
             if is_activated:
                  event_id = f"on_click_point_{point_id}"
                  if event_id in config_triggers and event_id not in self._triggered_narrative_events:
                       triggered[event_id] = config_triggers[event_id]
                       self._triggered_narrative_events.add(event_id)

        # 检查 OnAllClicked (所有点都已点击)
        if all(self.activated_points.values()) and len(self.activated_points) > 0 and "on_all_clicked" in config_triggers:
            event_id = "on_all_clicked"
            if event_id not in self._triggered_narrative_events:
                triggered[event_id] = config_triggers[event_id]
                self._triggered_narrative_events.add(event_id)

        # 检查 OnComplete (互动完成) - 这个通常在 GameManager._on_interaction_complete 里处理，但有些类型可能在模块内部触发
        if self._is_completed and "on_complete" in config_triggers:
             event_id = "on_complete"
             if event_id not in self._triggered_narrative_events:
                 # 注意：on_complete 可能包含多个文本，且在整个互动流程的最后触发
                 # GameManager._on_interaction_complete 会确保它被调用，这里也可以触发
                 # triggered[event_id] = config_triggers[event_id] # 示例
                 pass # 统一在 GameManager 中处理 on_complete

        # TODO: 检查进度相关的叙事事件 (例如，on_reveal_progress_50)
        # if self.reveal_progress >= 0.5 and "on_reveal_progress_50" in config_triggers:
        #     event_id = "on_reveal_progress_50"
        #     if event_id not in self._triggered_narrative_events:
        #          triggered[event_id] = config_triggers[event_id]
        #          self._triggered_narrative_events.add(event_id)


        return triggered

    # TODO: 添加保存和加载模块状态的方法 (用于保存游戏进度)
    # def get_state(self):
    #     return {
    #         "activated_points": self.activated_points,
    #         "reveal_progress": self.reveal_progress,
    #         "triggered_narrative_events": list(self._triggered_narrative_events)
    #     }

    # def load_state(self, state_data):
    #     self.activated_points = state_data["activated_points"]
    #     self.reveal_progress = state_data["reveal_progress"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._is_completed = all(self.activated_points.values()) if self.activated_points else True # 重新计算完成状态
    #     # TODO: 根据加载的状态更新视觉效果