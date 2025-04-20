# interaction_modules/click_reveal.py
import pygame
# 修正导入路径，settings 在根目录
from settings import Settings
# 修正导入路径，ImageRenderer 在根目录
from image_renderer import ImageRenderer # 导入用于坐标转换
# 导入 AudioManager 类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from audio_manager import AudioManager # AudioManager 在根目录


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
        self.settings = image_renderer.settings # 获取 settings 实例

        # 从 settings 获取 AudioManager 实例
        self.audio_manager: 'AudioManager' = self.settings.game_manager.audio_manager # 通过game_manager获取audio_manager


        # 从config中加载点击点信息
        # click_points 存储的是原始图片中的坐标 [x, y] 和 ID
        # 格式示例: [{"x": 850, "y": 520, "id": "point1", "radius": 30}, ...]
        self.click_points_config = config.get("click_points", [])
        # 记录每个点击点是否已被激活
        self.activated_points = {point["id"]: False for point in self.click_points_config}

        # 显影进度控制 (主要用于纯 Click Reveal 玩法 Stage 1)
        self.reveal_progress = 0.0
        self.reveal_progress_per_click = config.get("reveal_progress_per_click", 0.25) # 每次点击增加的进度比例

        # 跟踪已触发的叙事事件，避免重复触发
        self._triggered_narrative_events = set()

        # 标记是否已完成所有点击 (对于混合玩法，这可能只是完成步骤)
        self._is_completed = False

        # TODO: 初始化与点击点相关的视觉效果（例如，点击点的高亮表面）
        self._init_visual_elements()


    def _init_visual_elements(self):
        """初始化点击点的视觉表示 (例如加载高亮纹理)"""
        # 在这里加载点击点高亮纹理，如果它是一个图片
        # self.highlight_texture = self.image_renderer.get_effect_texture("click_highlight.png") # 示例从ImageRenderer获取特效纹理

        # Stage 3.2 的点击点是在擦除后才出现
        # Stage 5.1 的点击点是在剥离后才出现
        # Stage 5.2 的点击点 (nodes) 是初始可见的
        # Stage 6.1 的点击点 (resonance points) 是初始可见的
        # 需要根据 config 或 hybrid_type 来决定是否初始就绘制点击点


        pass # 待填充


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed: # 如果已完成，不再处理点击事件
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键点击
            mouse_pos = event.pos # 屏幕坐标

            # 检查点击是否在图片的显示区域内 (如果点击点只在图片范围内)
            # if not image_display_rect.collidepoint(mouse_pos):
            #     return

            # 将鼠标点击的屏幕坐标转换回原始图片坐标
            # ImageRenderer.get_image_coords 需要根据图片显示区域进行逆向转换
            original_image_mouse_pos = self.image_renderer.get_image_coords(mouse_pos[0], mouse_pos[1])

            for point_config in self.click_points_config:
                point_id = point_config["id"]
                # 检查点击是否在当前点击点区域内 (假设 config 中的点是原始图片像素坐标)
                # 假设点击点是圆形的，用阈值判断距离
                click_threshold_pixels = point_config.get("radius", 30) # 从config获取点击半径，默认30像素 # TODO: 可移动到settings或config

                if not self.activated_points[point_id]:
                   # 检查点击是否在以点击点原始坐标为中心，click_threshold_pixels 为半径的圆内
                   # 使用原始图片坐标进行距离计算
                   distance_sq = (original_image_mouse_pos[0] - point_config["x"])**2 + (original_image_mouse_pos[1] - point_config["y"])**2
                   if distance_sq <= click_threshold_pixels**2:

                        self.activated_points[point_id] = True
                        # 修正：传递 point_config 给 _on_point_activated
                        self._on_point_activated(point_id, point_config)
                        break # 一次点击只激活一个点

    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新点击显现状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        if self._is_completed:
            return True, {} # 已完成，不再更新

        # 根据已激活的点击点数量更新显影进度 (主要用于纯 Click Reveal 玩法 Stage 1)
        # 只有当互动类型是纯 Click Reveal 时才更新主显影进度
        if self.config.get("type") == self.settings.INTERACTION_CLICK_REVEAL:
            activated_count = sum(self.activated_points.values())
            total_points = len(self.click_points_config)

            if total_points > 0:
                 target_progress = activated_count / total_points
            else:
                 target_progress = 1.0 # 没有点击点则直接完成

            self.reveal_progress = target_progress

            # 通知 ImageRenderer 更新显影效果 (例如，更新模糊强度)
            # effect_type 可以在 config 中定义
            effect_type = self.config.get("initial_effect", {}).get("type", "blur_reveal") # 默认使用 blur_reveal
            # ImageRenderer update_effect 方法需要知道图片ID
            self.image_renderer.update_effect(effect_type, self.reveal_progress, self.config.get("id")) # 示例传递图片ID


        # 检查是否所有点击点都已激活
        # 对于纯 Click Reveal 玩法，所有点激活即完成当前图片互动
        # 对于混合玩法，所有点激活可能只是完成混合序列中的一步，需要 HybridInteraction 来协调下一步
        activated_count = sum(self.activated_points.values())
        total_points = len(self.click_points_config)

        # 检查是否所有点都已激活
        if total_points > 0 and activated_count == total_points:
            # 如果所有点已激活，标记完成状态
            if not self._is_completed: # 第一次完成时
                self._is_completed = True
                print(f"Click Reveal for {self.config.get('file', 'current image')} Completed!")

                # 检查并触发完成相关的叙事事件 (on_all_clicked, on_complete)
                narrative_events = self._check_and_trigger_narrative_events(check_complete=True)
                return True, narrative_events # 返回完成状态和触发的叙事事件

        elif total_points == 0: # 没有点击点也视为完成
             if not self._is_completed: # 第一次完成时
                 self._is_completed = True
                 print(f"Click Reveal for {self.config.get('file', 'current image')} Completed (no points).")
                 narrative_events = self._check_and_trigger_narrative_events(check_complete=True)
                 return True, narrative_events


        # 检查是否触发了其他叙事事件 (如 OnClickAny, OnClickSpecificPoint, 进度触发)
        # 这些事件可能在 update 中被触发，即使互动未完成
        narrative_events = self._check_and_trigger_narrative_events()

        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制点击显现模块的视觉元素（例如，未激活点击点的高亮）"""
        # 只有未完成时才绘制点击点提示
        if self._is_completed:
             # 完成后可能绘制最终状态或无thing
             return

        # 绘制未激活点击点的高亮提示
        for point_config in self.click_points_config:
            point_id = point_config["id"]
            if not self.activated_points[point_id]:
                # 将点击点原始坐标转换为屏幕坐标进行绘制
                point_screen_pos = self.image_renderer.get_screen_coords_from_original(point_config["x"], point_config["y"])

                # TODO: 绘制高亮圆圈或图标或特效
                # 可以在 settings 或 config 中定义点击点视觉样式
                # 例如，config.click_points 中的每个点可以有 "visual_style": {"type": "circle", "color": [255,0,0], "radius": 15}
                visual_style = point_config.get("visual_style", {"type": "circle", "color": [255,255,255], "radius": 10, "width": 0}) # 默认样式
                highlight_color = visual_style.get("color", self.settings.WHITE)
                highlight_radius = visual_style.get("radius", 10)
                highlight_width = visual_style.get("width", 0) # 0表示填充圆，>0表示圆圈边框
                highlight_type = visual_style.get("type", "circle")

                if highlight_type == "circle":
                    # 检查屏幕坐标是否有效
                    if point_screen_pos[0] is not None and point_screen_pos[1] is not None:
                         if highlight_width == 0:
                              pygame.draw.circle(screen, highlight_color, point_screen_pos, highlight_radius)
                         else:
                              pygame.draw.circle(screen, highlight_color, point_screen_pos, highlight_radius, highlight_width)
                # TODO: 实现绘制其他形状的点击点提示 (如纹理图标)
                # elif highlight_type == "icon":
                #    texture_id = visual_style.get("texture_id", "default_click_icon")
                #    icon_texture = self.image_renderer.get_effect_texture(texture_id)
                #    if icon_texture:
                #        icon_rect = icon_texture.get_rect(center=point_screen_pos)
                #        screen.blit(icon_texture, icon_rect)


    # 修正：_on_point_activated 方法接收 point_config 参数
    def _on_point_activated(self, point_id: str, point_config: dict):
        """处理单个点击点被激活后的逻辑"""
        print(f"点击点 {point_id} 被激活")
        # 增加显影进度 (Stage 1 逻辑，由 update 方法根据 activated_points 统一计算)

        # 触发点击反馈特效和音效
        # self.image_renderer.trigger_effect(self.settings.CLICK_FEEDBACK_EFFECT_ID) # TODO: 实现通用点击反馈特效
        if self.audio_manager: # 确保 audio_manager 存在
            # 播放通用点击音效，或者根据点击点ID播放特定音效
            sfx_id = point_config.get("sfx_id", "sfx_click") # 从config获取特定音效ID，默认通用点击音效
            # 如果 sfx_id 不在已加载音效中，play_sfx 会打印警告
            self.audio_manager.play_sfx(sfx_id)


        # 检查是否触发了点击相关的叙事事件
        # 这个检查统一放在 update 里通过 _check_and_trigger_narrative_events 处理

    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
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
        for point_config in self.click_points_config: # 遍历配置，而不是已激活的字典
             point_id = point_config["id"]
             if self.activated_points.get(point_id, False): # 如果这个点被激活了
                  event_id = f"on_click_point_{point_id}"
                  # 如果这个事件ID在配置中存在且尚未触发过
                  if event_id in config_triggers and event_id not in self._triggered_narrative_events:
                       triggered[event_id] = config_triggers[event_id]
                       self._triggered_narrative_events.add(event_id)

        # 检查 OnAllClicked (所有点都已点击)
        # 这个事件只在所有点第一次被激活时触发一次
        if all(self.activated_points.values()) and len(self.activated_points) > 0 and "on_all_clicked" in config_triggers:
            event_id = "on_all_clicked"
            if event_id not in self._triggered_narrative_events:
                triggered[event_id] = config_triggers[event_id]
                self._triggered_narrative_events.add(event_id)

        # 检查 OnComplete (互动完成)
        # 只有当互动模块的 _is_completed 第一次为 True 时，GameManager 才会调用此检查并触发 on_complete
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             triggered[event_id] = config_triggers[event_id]


        # TODO: 检查进度相关的叙事事件 (例如，on_reveal_progress_50)
        # 只有纯 Click Reveal 才有显影进度
        if self.config.get("type") == self.settings.INTERACTION_CLICK_REVEAL:
           # 示例检查 50% 进度触发
           # progress_checkpoints = {0.5: "on_reveal_progress_50", 0.8: "on_reveal_progress_80"} # 从config获取或settings定义
           # for threshold, event_id in progress_checkpoints.items():
           #      if self.reveal_progress >= threshold and event_id in config_triggers:
           #          if event_id not in self._triggered_narrative_events:
           #               triggered[event_id] = config_triggers[event_id]
           #               self._triggered_narrative_events.add(event_id)
           pass


        return triggered

    # TODO: 添加保存和加载模块状态的方法 (用于保存游戏进度)
    # def get_state(self):
    #     return {
    #         "activated_points": self.activated_points,
    #         "reveal_progress": self.reveal_progress, # 只对纯 Click Reveal 有效
    #         "triggered_narrative_events": list(self._triggered_narrative_events)
    #     }

    # def load_state(self, state_data, image_display_rect: pygame.Rect): # 加载时需要传递当前显示区域
    #     self.activated_points = state_data.get("activated_points", {})
    #     self.reveal_progress = state_data.get("reveal_progress", 0.0) # 提供默认值
    #     self._triggered_narrative_events = set(state_data.get("triggered_narrative_events", []))
    #     # 重新计算完成状态：如果所有点已激活，则视为完成
    #     self._is_completed = all(self.activated_points.values()) if self.activated_points else True
    #     # TODO: 根据加载的状态更新视觉效果 (调用 image_renderer 的方法)
    #     # if self.config.get("type") == self.settings.INTERACTION_CLICK_REVEAL:
    #     #    effect_type = self.config.get("initial_effect", {}).get("type", "blur_reveal")
    #     #    self.image_renderer.update_effect(effect_type, self.reveal_progress)
    #     # TODO: 确保点击点的高亮状态也恢复正确