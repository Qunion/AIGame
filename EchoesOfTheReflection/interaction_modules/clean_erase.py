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
        self._last_hit_unerasable_time = 0 # 上次碰到不可擦区域的时间

        # TODO: 加载笔刷纹理 (可选，如果笔刷是纹理)
        # self.brush_texture = self.image_renderer.get_effect_texture("erase_brush") # 示例

        # TODO: 创建不可擦除区域的 Pygame Rect/Shape 对象 (需要在加载或resize时根据配置转换坐标)
        self.unerasable_display_areas = [] # List of Pygame Rects or other shape objects in screen coordinates


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


    def _update_unerasable_display_areas(self, image_display_rect: pygame.Rect):
        """根据当前图片显示区域，计算不可擦除区域在屏幕上的显示形状"""
        self.unerasable_display_areas = []
        if image_display_rect.size == (0, 0):
             return # 图片显示区域无效

        for area_config in self.unerasable_areas_config:
             area_type = area_config.get("type")
             # TODO: 根据 area_type 将 config 中的坐标转换为屏幕坐标或相对于图片显示区域的坐标
             if area_type == "rect":
                 # 假设 config 中的 rect 是相对于原始图片尺寸的比例或像素坐标
                 # screen_rect = self.image_renderer.get_screen_rect_from_original(area_config["x"], area_config["y"], area_config["width"], area_config["height"])
                 # self.unerasable_display_areas.append(screen_rect)
                 pass # 待实现具体的坐标转换和 Rect/Shape 创建
             # TODO: 支持 circle, polygon 等其他形状


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        self._ensure_mask_surface(image_display_rect) # 确保蒙版Surface已准备好
        self._update_unerasable_display_areas(image_display_rect) # 确保不可擦除区域位置已更新


        mouse_pos = event.pos # 屏幕坐标

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            if image_display_rect.collidepoint(mouse_pos):
                self._is_erasing = True
                # 触发开始擦拭叙事 (只触发一次)
                if "on_start_erase" in self.config.get("narrative_triggers", {}) and "on_start_erase" not in self._triggered_narrative_events:
                    # 返回触发的事件，让 GameManager 启动叙事
                    pass # 在 update 中统一返回叙事事件

                # TODO: 播放开始擦拭音效 (sfx_erase_looping)，设置为循环播放
                # self.audio_manager.play_sfx("sfx_erase_looping", loop=-1)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: # 左键抬起
            self._is_erasing = False
            # TODO: 停止循环擦拭音效
            # self.audio_manager.stop_sfx("sfx_erase_looping")


        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._is_erasing and image_display_rect.collidepoint(mouse_pos):
                # 将鼠标位置转换为相对于图片显示区域左上角的坐标
                relative_pos = (mouse_pos[0] - image_display_rect.left, mouse_pos[1] - image_display_rect.top)

                # TODO: 检查是否在不可擦除区域
                is_in_unerasable = False
                # for area in self.unerasable_display_areas: # 遍历屏幕坐标下的不可擦除区域形状
                #     if area.collidepoint(mouse_pos): # 或者更通用的碰撞检测方法
                #         is_in_unerasable = True
                #         break

                if not is_in_unerasable:
                    # 在 mask_alpha_surface 上绘制透明笔刷
                    # 笔刷中心位置是 relative_pos
                    brush_rect_local = pygame.Rect(0, 0, self.erase_brush_size, self.erase_brush_size)
                    brush_rect_local.center = relative_pos

                    # TODO: 实现高效的擦除绘制逻辑，修改 mask_alpha_surface 的 alpha 值
                    # 使用 Surface.blit with special_flags (BLEND_RGBA_MULT 或 BLEND_RGBA_MIN)
                    # 或者直接操作像素数组 (较慢)
                    # 可以绘制一个带有透明度的圆圈 Surface，然后 blit 到 mask_alpha_surface
                    # brush_alpha = 20 # 每次绘制减少的alpha值，模拟擦拭力度
                    # erase_surface = pygame.Surface(brush_rect_local.size, pygame.SRCALPHA)
                    # pygame.draw.circle(erase_surface, (255, 255, 255, brush_alpha), (self.erase_brush_size//2, self.erase_brush_size//2), self.erase_brush_size//2)
                    # self.mask_alpha_surface.blit(erase_surface, brush_rect_local.topleft, special_flags=pygame.BLEND_RGBA_MIN) # MIN 模式可以模拟alpha减少

                    # 或者使用 numpy 直接操作像素 (需要 Surface 是 format_alpha)
                    # if self.mask_alpha_surface.get_flags() & pygame.SRCALPHA:
                    #    pixels = pygame.surfarray.pixels_alpha(self.mask_alpha_surface)
                    #    x_start, y_start = brush_rect_local.topleft
                    #    x_end, y_end = brush_rect_local.bottomright
                    #    x_start = max(0, x_start)
                    #    y_start = max(0, y_start)
                    #    x_end = min(self.mask_alpha_surface.get_width(), x_end)
                    #    y_end = min(self.mask_alpha_surface.get_height(), y_end)
                    #    # 在笔刷区域内减少alpha值 (复杂的圆圈形状判断)
                    #    # pixels[x_start:x_end, y_start:y_end] = np.maximum(0, pixels[x_start:x_end, y_start:y_end] - brush_alpha)
                    #    del pixels # 解锁像素数组

                    pass # 待实现具体的擦除绘制逻辑

                    # TODO: 触发擦拭视觉反馈 (例如粒子效果)
                    # self.image_renderer.trigger_effect("erase_particles", mouse_pos) # 示例粒子效果


                else: # 在不可擦除区域
                     # TODO: 触发遇到不可擦除区域的叙事和反馈
                     current_time = time.time()
                     # 防洪处理，避免频繁触发音效和叙事
                     if current_time - self._last_hit_unerasable_time > 0.5: # 0.5秒内只触发一次
                         print("碰到不可擦区域！")
                         if "on_hit_unerasable" in self.config.get("narrative_triggers", {}):
                             # 返回触发的事件，让 GameManager 启动叙事
                             pass # 在 update 中统一返回叙事事件
                             self._just_hit_unerasable_this_frame = True # 标记给 update 检查

                         # TODO: 播放不可擦音效
                         # self.audio_manager.play_sfx("sfx_unerasable_hit") # 示例音效

                         # TODO: 改变笔刷视觉 (可选)

                         self._last_hit_unerasable_time = current_time # 更新时间戳


    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新清洁擦除状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        if self._is_completed:
            return True, {}

        self._ensure_mask_surface(image_display_rect) # 确保蒙版Surface已准备好
        self._update_unerasable_display_areas(image_display_rect) # 确保不可擦除区域位置已更新

        # 计算擦除进度
        # TODO: 实现一个方法来计算 mask_alpha_surface 中 alpha 值小于某个阈值的像素比例
        # 这是一个性能敏感的操作，可能需要优化或使用不同的方法 (例如，使用 numpy)
        if self.mask_alpha_surface:
             # 示例计算：计算完全透明的像素比例 (alpha == 0)
             # pixels = pygame.surfarray.pixels_alpha(self.mask_alpha_surface) # 需要 surface 是 format_alpha
             # total_pixels = pixels.size
             # fully_transparent_pixels = np.sum(pixels == 0)
             # erase_progress = fully_transparent_pixels / total_pixels # 示例，实际可能需要 alpha < 某个阈值
             # del pixels # 解锁像素数组
             erase_progress = 0.0 # 占位，待实现计算方法
             self.erase_progress = erase_progress # 更新进度变量
        else:
             self.erase_progress = 0.0


        # TODO: 触发进度相关的叙事事件 (例如，on_erase_progress_XX)
        narrative_events = self._check_and_trigger_narrative_events()

        # 检查是否完成
        if self.erase_progress >= self.erase_threshold:
             self._is_completed = True
             print(f"Clean Erase for {self.config.get('file', self.config.get('description', 'current image'))} Completed! Progress: {self.erase_progress}")
             # 在这里触发 on_complete 叙事事件 (如果有)
             complete_narrative = self._check_and_trigger_narrative_events(check_complete=True) # 检查完成事件

             # 如果是混合玩法的 Clean Erase，可能还需要触发 on_complete_erase 事件 (Stage 3.2, 5.1)
             if self.config.get("type") in [self.settings.INTERACTION_HYBRID_ERASE_THEN_CLICK, self.settings.INTERACTION_CLEAN_ERASE_HINT]:
                  erase_complete_narrative = self._check_and_trigger_narrative_events(check_erase_complete=True)
                  narrative_events = {**narrative_events, **complete_narrative, **erase_complete_narrative} # 合并所有触发的事件
             else:
                  narrative_events = {**narrative_events, **complete_narrative} # 合并触发的事件

             return True, narrative_events # 返回完成状态和触发的叙事事件


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

    # TODO: 实现初始化不可擦区域在蒙版上的方法 (_init_unerasable_areas_on_mask)
    # TODO: 实现根据新尺寸更新不可擦区域Rects的方法 (_update_unerasable_display_areas)

    # 在窗口resize时，可能需要重新创建 mask_alpha_surface 和更新不可擦区域位置
    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
         """处理窗口大小改变事件，重新创建蒙版Surface并更新不可擦区域位置"""
         self.mask_alpha_surface = None # 强制重新创建蒙版Surface
         self._ensure_mask_surface(image_display_rect) # 确保创建新的蒙版Surface
         self._update_unerasable_display_areas(image_display_rect) # 更新不可擦区域位置

         # TODO: 如果保存了 mask_alpha_surface 的状态，需要在 resize 后重新绘制到新的 Surface 上


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
        # _just_hit_unerasable_this_frame 标志需要在 handle_event 中设置
        # if hasattr(self, '_just_hit_unerasable_this_frame') and self._just_hit_unerasable_this_frame:
        #    event_id = "on_hit_unerasable"
        #    if event_id in config_triggers: # 每次触发，不添加到 _triggered_narrative_events
        #        triggered[event_id] = config_triggers[event_id]
        #    self._just_hit_unerasable_this_frame = False


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
    #     # self._ensure_mask_surface(image_display_rect) # 创建空白或初始状态的Surface
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