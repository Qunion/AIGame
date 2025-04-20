# interaction_modules/clean_erase.py
import pygame
import os
# 导入自定义模块 - 它们现在位于根目录
from settings import Settings
from image_renderer import ImageRenderer
from audio_manager import AudioManager # 需要AudioManager来播放音效
# import numpy as np # 可能需要 numpy 来高效处理像素数据 (可选)


class CleanErase:
    """
    处理Clean Erase玩法逻辑。
    玩家擦拭蒙版显现图片。
    """

    def __init__(self, config: dict, image_renderer: ImageRenderer, screen: pygame.Surface):
        """
        初始化清洁擦除模块。
        config: 来自image_config.json的当前图片配置。
        image_renderer: 用于图片显示和效果控制的ImageRenderer实例。
        screen: 主屏幕Surface，用于创建RenderTexture模拟。
        """
        self.config = config
        self.image_renderer = image_renderer
        self.settings: Settings = image_renderer.settings
        self.screen = screen # 主屏幕Surface，用于创建RenderTexture模拟

        self.audio_manager: AudioManager = self.settings.game_manager.audio_manager # 从settings获取GameManager，再获取AudioManager

        # 从config中加载蒙版和不可擦除区域信息
        self.mask_texture_name = config.get("mask_texture", "default_mask.png")
        self.unerasable_areas_config = config.get("unerasable_areas", []) # 不可擦除区域配置 (原始图片坐标或相对坐标)

        # 用于模拟 Render Texture 的 Surface
        # 这是一个与图片实际显示区域一样大，用于控制蒙版 alpha 的 Surface
        self.mask_alpha_surface = None # Pygame Surface with SRCALPHA
        self.erase_brush_size = config.get("brush_size", 40) # 擦拭笔刷大小 (像素)
        self._is_erasing = False # 标记是否正在擦拭

        # 擦除进度
        self.erase_progress = 0.0 # 0.0 到 1.0
        self.erase_threshold = config.get("erase_threshold", 0.95) # 完成阈值

        # 跟踪已触发的叙事事件
        self._triggered_narrative_events = set()

        # 标记是否已完成
        self._is_completed = False

        # 跟踪不可擦区域点击事件 (用于防洪或特定叙事触发)
        self._last_hit_unerasable_time = 0.0 # 上次碰到不可擦区域的时间
        self._just_hit_unerasable_this_frame = False # 标记当前帧是否碰到不可擦区域

        # TODO: 加载笔刷纹理 (可选，如果笔刷是纹理)
        # self.brush_texture = self.image_renderer.get_effect_texture("erase_brush") # 示例

        # 创建不可擦除区域的 Pygame Rect/Shape 对象 (需要在加载或resize时根据配置转换坐标)
        self.unerasable_display_areas = [] # List of Pygame Rects or other shape objects in screen coordinates
        # 在初始化时就计算一次位置，后续在resize时更新
        self._update_unerasable_display_areas(self.image_renderer.image_display_rect)


    def _ensure_mask_surface(self, image_display_rect: pygame.Rect):
        """确保 mask_alpha_surface 已初始化并与图片显示区域尺寸匹配"""
        # 只有当图片显示区域尺寸有效且 mask_alpha_surface 不存在或尺寸不匹配时才创建/重塑
        if image_display_rect.size == (0, 0):
             return # 图片显示区域无效

        if self.mask_alpha_surface is None or self.mask_alpha_surface.get_size() != image_display_rect.size:
            print(f"初始化/重塑 mask_alpha_surface 为尺寸: {image_display_rect.size}")
            self.mask_alpha_surface = pygame.Surface(image_display_rect.size, pygame.SRCALPHA) # 创建与图片显示区域同尺寸的Surface，带alpha通道

            # TODO: 绘制初始蒙版纹理到 mask_alpha_surface 上
            mask_texture = self.image_renderer.mask_textures.get(self.mask_texture_name)
            if mask_texture:
                 # 缩放蒙版纹理以适应 mask_alpha_surface 尺寸
                 scaled_mask_texture = pygame.transform.scale(mask_texture, image_display_rect.size)
                 self.mask_alpha_surface.blit(scaled_mask_texture, (0, 0))
                 print(f"绘制初始蒙版纹理 {self.mask_texture_name} 到 mask_alpha_surface")
            else:
                 # 如果蒙版纹理未加载或未指定，使用白色填充 (表示完全不透明)
                 self.mask_alpha_surface.fill((255, 255, 255, 255))
                 print("使用默认不透明蒙版填充 mask_alpha_surface")


            # TODO: 根据不可擦除区域配置，初始化这些区域在 mask_alpha_surface 上的 alpha，使其保持不透明 (alpha=255)
            # 需要将 unerasable_areas_config 中的坐标转换为相对于 mask_alpha_surface 的坐标
            # self._init_unerasable_areas_on_mask(image_display_rect.size)

            # 在重新创建蒙版Surface时，如果加载了保存的状态，需要在这里恢复蒙版内容
            # 例如，加载保存的 mask_alpha_surface 的像素数据

        # TODO: 更新不可擦除区域的 Pygame Rect/Shape 对象，以适应新的图片显示区域尺寸
        # self._update_unerasable_display_areas(image_display_rect) # 这个在handle_event和update里调用确保最新位置

    # TODO: 实现初始化不可擦区域在蒙版上的方法 (_init_unerasable_areas_on_mask)
    # 遍历 unerasable_areas_config，将对应的区域在 mask_alpha_surface 上设置为完全不透明 (alpha 255)

    def _update_unerasable_display_areas(self, image_display_rect: pygame.Rect):
        """根据当前图片显示区域，计算不可擦除区域在屏幕上的显示形状"""
        # 这个方法需要在 resize 或 _ensure_mask_surface 被调用后执行，以确保坐标正确
        self.unerasable_display_areas = []
        if image_display_rect.size == (0, 0):
             return # 图片显示区域无效

        for area_config in self.unerasable_areas_config:
             area_type = area_config.get("type")
             # TODO: 根据 area_type 将 config 中的原始图片坐标转换为屏幕坐标，并创建对应的 Pygame 形状对象
             if area_type == "rect":
                 # config 中的 rect 是原始图片像素坐标 [x, y, width, height]
                 original_x = area_config.get("x", 0)
                 original_y = area_config.get("y", 0)
                 original_width = area_config.get("width", 0)
                 original_height = area_config.get("height", 0)

                 # 将原始矩形的四个角转换为屏幕坐标，然后找到最小/最大X/Y来构建屏幕矩形
                 top_left_screen = self.image_renderer.get_screen_coords_from_original(original_x, original_y)
                 bottom_right_screen = self.image_renderer.get_screen_coords_from_original(original_x + original_width, original_y + original_height)

                 screen_rect = pygame.Rect(top_left_screen, (bottom_right_screen[0] - top_left_screen[0], bottom_right_screen[1] - top_left_screen[1]))
                 self.unerasable_display_areas.append(screen_rect)

             # TODO: 支持 circle, polygon 等其他形状的坐标转换和 Pygame 对象创建


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        # 确保蒙版Surface和不可擦除区域位置已准备好
        self._ensure_mask_surface(image_display_rect)
        # _update_unerasable_display_areas 在 update 中调用，确保每帧位置最新


        mouse_pos = event.pos # 屏幕坐标

        # 检查鼠标是否在图片显示区域内
        is_mouse_in_image_area = image_display_rect.collidepoint(mouse_pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            if is_mouse_in_image_area:
                self._is_erasing = True
                # 触发开始擦拭叙事 (只触发一次)
                if "on_start_erase" in self.config.get("narrative_triggers", {}) and "on_start_erase" not in self._triggered_narrative_events:
                    # 返回触发的事件，让 GameManager 启动叙事
                    pass # 在 update 中统一返回叙事事件 (通过 _check_and_trigger_narrative_events 检查 _is_erasing 状态)

                # TODO: 播放开始擦拭音效 (sfx_erase_looping)，设置为循环播放
                # if self.audio_manager:
                #     self.audio_manager.play_sfx("sfx_erase_looping", loop=-1)


        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: # 左键抬起
            if self._is_erasing: # 确保之前是在擦拭状态
                self._is_erasing = False
                # TODO: 停止循环擦拭音效
                # if self.audio_manager and self.audio_manager.is_sfx_playing("sfx_erase_looping"):
                #      self.audio_manager.stop_sfx("sfx_erase_looping")


        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._is_erasing and is_mouse_in_image_area:
                # 将鼠标位置转换为相对于图片显示区域左上角的坐标
                relative_pos = (mouse_pos[0] - image_display_rect.left, mouse_pos[1] - image_display_rect.top)

                # 检查是否在不可擦除区域
                is_in_unerasable = False
                for area in self.unerasable_display_areas: # 遍历屏幕坐标下的不可擦除区域形状
                    if hasattr(area, 'collidepoint') and area.collidepoint(mouse_pos): # 检查 Pygame Rect 的碰撞
                        is_in_unerasable = True
                        break
                    # TODO: 支持圆形、多边形等的碰撞检测

                if not is_in_unerasable:
                    # 在 mask_alpha_surface 上绘制透明笔刷
                    # 笔刷中心位置是 relative_pos
                    brush_center_local = relative_pos
                    brush_size_half = self.erase_brush_size // 2
                    brush_rect_to_draw = pygame.Rect(
                        brush_center_local[0] - brush_size_half,
                        brush_center_local[1] - brush_size_half,
                        self.erase_brush_size,
                        self.erase_brush_size
                    )

                    # TODO: 实现高效的擦除绘制逻辑，修改 mask_alpha_surface 的 alpha 值
                    # 最简单的 Pygame 模拟：在一个圆圈区域内设置 alpha 为 0
                    # 这是一个性能较低的方法，特别是笔刷大或屏幕大时
                    if self.mask_alpha_surface.get_flags() & pygame.SRCALPHA: # 确保 surface 有 alpha 通道
                         # 锁定像素数组进行直接修改 (更快)
                         pixels_alpha = pygame.surfarray.pixels_alpha(self.mask_alpha_surface)

                         # 计算需要修改的矩形区域，并限制在 surface 范围内
                         x_start = max(0, brush_rect_to_draw.left)
                         y_start = max(0, brush_rect_to_draw.top)
                         x_end = min(self.mask_alpha_surface.get_width(), brush_rect_to_draw.right)
                         y_end = min(self.mask_alpha_surface.get_height(), brush_rect_to_draw.bottom)

                         # 遍历矩形区域内的像素
                         for x in range(x_start, x_end):
                             for y in range(y_start, y_end):
                                 # 检查像素是否在圆圈范围内
                                 if (x - brush_center_local[0])**2 + (y - brush_center_local[1])**2 <= brush_size_half**2:
                                     # 将该像素的 alpha 值设置为 0 (完全透明)
                                     pixels_alpha[x, y] = 0 # 设置为 0

                         del pixels_alpha # 解锁像素数组

                    # TODO: 触发擦拭视觉反馈 (例如粒子效果)
                    # self.image_renderer.trigger_effect("erase_particles", mouse_pos) # 示例粒子效果


                else: # 在不可擦除区域
                     # TODO: 触发遇到不可擦除区域的叙事和反馈
                     current_time = time.time()
                     # 防洪处理，避免频繁触发音效和叙事
                     if current_time - self._last_hit_unerasable_time > 0.5: # 0.5秒内只触发一次不可擦反馈
                         print("碰到不可擦区域！")
                         # 标记给 update 检查并触发叙事
                         self._just_hit_unerasable_this_frame = True

                         # TODO: 播放不可擦音效
                         # if self.audio_manager:
                         #     self.audio_manager.play_sfx("sfx_unerasable_hit") # 示例音效

                         # TODO: 改变笔刷视觉 (可选)

                         self._last_hit_unerasable_time = current_time # 更新时间戳

            # 如果鼠标移出图片区域，也停止擦拭状态
            elif self._is_erasing and not is_mouse_in_image_area:
                 self._is_erasing = False
                 # TODO: 停止循环擦拭音效
                 # if self.audio_manager and self.audio_manager.is_sfx_playing("sfx_erase_looping"):
                 #      self.audio_manager.stop_sfx("sfx_erase_looping")


    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新清洁擦除状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        if self._is_completed:
            return True, {}

        # 确保蒙版Surface和不可擦除区域位置已准备好 (在每帧update时更新位置)
        self._ensure_mask_surface(image_display_rect)
        self._update_unerasable_display_areas(image_display_rect)


        # 计算擦除进度
        # TODO: 实现一个方法来计算 mask_alpha_surface 中 alpha 值小于某个阈值的像素比例
        # 这是一个性能敏感的操作，可能需要优化或使用不同的方法 (例如，使用 numpy)
        if self.mask_alpha_surface:
             # 示例计算：计算 alpha 小于 10 的像素比例
             if self.mask_alpha_surface.get_flags() & pygame.SRCALPHA: # 确保 surface 有 alpha 通道
                 pixels_alpha = pygame.surfarray.pixels_alpha(self.mask_alpha_surface)
                 total_pixels = pixels_alpha.size
                 # 计算 alpha 小于某个阈值 (如 10) 的像素数量
                 erased_pixels = np.sum(pixels_alpha < 10) if 'np' in sys.modules else 0 # 使用numpy如果导入了
                 self.erase_progress = erased_pixels / total_pixels if total_pixels > 0 else 0.0
                 del pixels_alpha # 解锁像素数组
             else:
                  self.erase_progress = 0.0 # 没有alpha通道，无法计算进度
        else:
             self.erase_progress = 0.0


        # TODO: 触发进度相关的叙事事件 (例如，on_erase_progress_XX)
        narrative_events = self._check_and_trigger_narrative_events()

        # 检查是否完成
        if self.erase_progress >= self.erase_threshold:
             self._is_completed = True
             print(f"Clean Erase for {self.config.get('file', self.config.get('description', 'current image'))} Completed! Progress: {self.erase_progress}")
             # 在这里触发 on_complete 叙事事件 (如果有)
             # 检查所有相关的完成触发器
             complete_narrative = self._check_and_trigger_narrative_events(check_complete=True, check_erase_complete=True)
             narrative_events = {**narrative_events, **complete_narrative} # 合并所有触发的事件

             # 停止循环擦拭音效 (以防鼠标抬起事件丢失)
             # if self.audio_manager and self.audio_manager.is_sfx_playing("sfx_erase_looping"):
             #      self.audio_manager.stop_sfx("sfx_erase_looping")


             return True, narrative_events # 返回完成状态和触发的叙事事件


        # 清除本帧的不可擦区域标记
        self._just_hit_unerasable_this_frame = False

        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制清洁擦除模块的视觉元素（主要是蒙版）"""
        # 在图片显示区域上方绘制 mask_alpha_surface
        if self.mask_alpha_surface:
             screen.blit(self.mask_alpha_surface, image_display_rect.topleft)

        # TODO: 绘制不可擦除区域的视觉提示 (可选，如果设计需要)
        # for area in self.unerasable_display_areas:
        #     if isinstance(area, pygame.Rect):
        #          pygame.draw.rect(screen, (255, 0, 0, 100), area, 2) # 示例：绘制一个红色半透明框
        #     # TODO: 绘制圆形、多边形等其他形状提示

        # TODO: 绘制笔刷的视觉反馈 (例如，笔刷光标)
        # mouse_pos = pygame.mouse.get_pos()
        # if self._is_erasing and image_display_rect.collidepoint(mouse_pos):
        #     brush_visual_rect = pygame.Rect(0, 0, self.erase_brush_size, self.erase_brush_size)
        #     brush_visual_rect.center = mouse_pos
        #     pygame.draw.circle(screen, (255, 255, 255, 150), brush_visual_rect.center, self.erase_brush_size//2, 2) # 示例：绘制白色圆圈边框


    # TODO: 实现计算擦除进度的方法 (_calculate_erase_progress)
    # 它需要遍历 mask_alpha_surface 的像素，计算 alpha < 某个阈值的比例
    # 可以使用 pygame.surfarray 或 numpy


    # 在窗口resize时，可能需要重新创建 mask_alpha_surface 和更新不可擦区域位置
    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
         """处理窗口大小改变事件，重新创建蒙版Surface并更新不可擦区域位置"""
         # 在重新创建蒙版Surface之前，保存旧蒙版的状态 (如果需要恢复擦除进度)
         # old_mask_data = self.get_state() # 示例：获取旧状态数据

         self.mask_alpha_surface = None # 强制重新创建蒙版Surface
         # 在 update 中调用 _ensure_mask_surface 和 _update_unerasable_display_areas 会根据新的 image_display_rect 自动处理
         # self._ensure_mask_surface(image_display_rect) # 确保创建新的蒙版Surface
         # self._update_unerasable_display_areas(image_display_rect) # 更新不可擦区域位置

         # TODO: 如果保存了 mask_alpha_surface 的状态，需要在 resize 后重新绘制到新的 Surface 上
         # self.load_state(old_mask_data, image_display_rect) # 示例：加载旧状态到新尺寸的Surface


    def _check_and_trigger_narrative_events(self, check_complete=False, check_erase_complete=False) -> dict:
        """检查当前状态是否触发了叙事事件，并返回未触发过的事件字典"""
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 on_start_erase (只触发一次)
        if self._is_erasing and "on_start_erase" in config_triggers: # 检查是否正在擦拭 (作为一种触发条件)
             event_id = "on_start_erase"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        # 检查 on_hit_unerasable (遇到不可擦区域，需要防洪)
        # _just_hit_unerasable_this_frame 标志在 handle_event 中设置
        if self._just_hit_unerasable_this_frame:
           event_id = "on_hit_unerasable"
           if event_id in config_triggers: # 每次触发，不添加到 _triggered_narrative_events
               triggered[event_id] = config_triggers[event_id]
           # _just_hit_unerasable_this_frame 会在 update 结束时清除


        # 检查进度触发 (on_erase_progress_XX)
        # 示例检查 30% 进度触发
        # if self.erase_progress >= 0.3 and "on_erase_progress_30" in config_triggers:
        #     event_id = "on_erase_progress_30"
        #     if event_id not in self._triggered_narrative_events:
        #          triggered[event_id] = config_triggers[event_id]
        #          self._triggered_narrative_events.add(event_id)
        # TODO: 检查所有进度触发点

        # 检查 on_complete (互动完成) - Stage 2 的最终完成
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        # 检查 on_complete_erase (擦除完成，Stage 3.2, 5.1 触发)
        if check_erase_complete and "on_complete_erase" in config_triggers:
             event_id = "on_complete_erase"
             if event_id not in self._triggered_narrative_events: # 只触发一次
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        return triggered

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     # 需要保存 mask_alpha_surface 的状态，这比较复杂，可能需要保存其像素数据或一个简化表示
    #     # 或者只保存 erase_progress 和已触发事件，加载时根据进度近似恢复蒙版状态 (精度损失)
    #     # 如果保存了 mask_alpha_surface，需要将其转换为可序列化的格式 (例如，base64编码的bytes)
    #     mask_data = None
    #     if self.mask_alpha_surface:
    #         # Example: Convert Surface to bytes (complexity depends on format)
    #         # mask_bytes = pygame.image.tostring(self.mask_alpha_surface, 'RGBA')
    #         # import base64
    #         # mask_data = base64.b64encode(mask_bytes).decode('utf-8')
    #         pass # 待实现

    #     return {
    #          "erase_progress": self.erase_progress,
    #          "triggered_narrative_events": list(self._triggered_narrative_events),
    #          # "mask_alpha_data": mask_data, # 示例
    #          # "mask_size": self.mask_alpha_surface.get_size() if self.mask_alpha_surface else (0,0)
    #     }
    # def load_state(self, state_data, image_display_rect: pygame.Rect):
    #     self.erase_progress = state_data["erase_progress"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._is_completed = self.erase_progress >= self.erase_threshold # 重新计算完成状态

    #     # 重新创建并恢复 mask_alpha_surface
    #     self._ensure_mask_surface(image_display_rect) # 创建空白或初始状态的Surface
    #     # if state_data.get("mask_alpha_data") and state_data.get("mask_size"):
    #     #      try:
    #     #          import base64
    #     #          mask_bytes = base64.b64decode(state_data["mask_alpha_data"])
    #     #          # Convert bytes back to Surface (complexity depends on format)
    #     #          loaded_surface = pygame.image.frombuffer(mask_bytes, state_data["mask_size"], 'RGBA')
    #     #          self.mask_alpha_surface = loaded_surface
    #     #      except Exception as e:
    #     #           print(f"警告：无法从保存数据加载 mask_alpha_surface: {e}")
    #     #           self.mask_alpha_surface = None # 加载失败


    #     # 需要根据加载的进度或数据恢复 mask_alpha_surface 的状态
    #     # self._load_mask_alpha_data(state_data["mask_alpha_data"])
    #     self._update_unerasable_display_areas(image_display_rect) # 更新不可擦区域位置