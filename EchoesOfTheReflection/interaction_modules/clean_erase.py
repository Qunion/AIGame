# interaction_modules/clean_erase.py
import pygame
import os
# 修正导入路径，settings 在根目录
from settings import Settings
# 修正导入路径，ImageRenderer 在根目录
from image_renderer import ImageRenderer
# 导入 AudioManager 类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from audio_manager import AudioManager # AudioManager 在根目录

# TODO: 可以考虑一个更高效的 Render Texture 模拟或擦除实现，这里使用基础像素操作作为示例


class CleanErase:
    """
    处理Clean Erase玩法逻辑。
    玩家擦拭蒙版显现图片。
    """

    def __init__(self, config: dict, image_renderer: ImageRenderer):
        """
        初始化清洁擦除模块。
        config: 来自image_config.json的当前图片配置。
        image_renderer: 用于图片显示和效果控制的ImageRenderer实例。
        """
        self.config = config
        self.image_renderer = image_renderer
        self.settings = image_renderer.settings # 获取 settings 实例

        # 从 settings 获取 AudioManager 实例
        # self.settings.game_manager 在 GameManager 初始化 NarrativeManager 和 UIManager 后才赋值
        # 这里需要在需要时才访问 game_manager，或者确保在调用 CleanErase 的 update/handle_event 前 game_manager 已完全初始化
        # 在 __init__ 中获取是安全的，因为 HybridInteraction 在 GameManager 初始化后才创建子模块
        self.audio_manager: 'AudioManager' = self.settings.game_manager.audio_manager


        # 从config中加载蒙版和不可擦除区域信息
        self.mask_texture_filename = config.get("mask_texture", "default_mask.png") # 只存文件名，加载在_ensure_mask_surface
        self.unerasable_areas_config = config.get("unerasable_areas", []) # 不可擦除区域配置 (原始图片坐标 [x, y, w, h] 或形状+坐标)

        # 用于模拟 Render Texture 的 Surface
        # 这是一个与图片实际显示区域一样大的 Surface，用来控制蒙版的alpha
        self.mask_alpha_surface = None
        # 擦拭笔刷的视觉效果和大小
        self.erase_brush_size = config.get("brush_size", 40) # 从config获取笔刷大小
        # TODO: 加载笔刷纹理 (如果需要)
        # self.brush_texture = self.image_renderer.get_effect_texture("erase_brush.png") # 示例


        self._is_erasing = False # 标记是否正在擦拭
        self._just_hit_unerasable_this_frame = False # 标记本帧是否擦中不可擦区域（用于防洪叙事）

        # 擦除进度
        self.erase_progress = 0.0
        self.erase_threshold = config.get("erase_threshold", 0.95) # 完成阈值 (擦除比例)

        # 跟踪已触发的叙事事件
        self._triggered_narrative_events = set()

        # 标记是否已完成
        self._is_completed = False


    # CleanErase 不需要 _init_visual_elements 方法，因为它的大部分视觉元素 (蒙版) 是动态创建和绘制的

    def _ensure_mask_surface(self, image_display_rect: pygame.Rect):
        """
        确保 mask_alpha_surface 已初始化并与图片显示区域尺寸匹配。
        在 resize 或第一次绘制/处理事件时调用。
        """
        if self.mask_alpha_surface is None or self.mask_alpha_surface.get_size() != image_display_rect.size:
            print(f"初始化/重塑 mask_alpha_surface 为尺寸: {image_display_rect.size}")
            # 创建与图片显示区域同尺寸的Surface
            self.mask_alpha_surface = pygame.Surface(image_display_rect.size, pygame.SRCALPHA)

            # 绘制初始蒙版纹理到 mask_alpha_surface 上 (如果存在)
            mask_base_texture = self.image_renderer.mask_textures.get(self.mask_texture_filename)
            if mask_base_texture:
                 # 缩放蒙版纹理以适应图片显示区域尺寸
                 scaled_mask_base = pygame.transform.scale(mask_base_texture, image_display_rect.size)
                 # 使用 BLEND_RGBA_MULT 将蒙版纹理的alpha通道应用到 mask_alpha_surface
                 # 假设蒙版纹理的alpha通道表示蒙版的透明度
                 self.mask_alpha_surface.blit(scaled_mask_base, (0,0), special_flags=pygame.BLEND_RGBA_MULT)

            else:
                 # 如果没有蒙版纹理，默认填充完全不透明的颜色 (例如，用于纯色蒙版或调试)
                 self.mask_alpha_surface.fill((255, 255, 255, 255)) # 默认白色不透明


            # 根据不可擦除区域配置，在 mask_alpha_surface 上标记这些区域为不透明
            self._init_unerasable_areas_on_mask(image_display_rect)


    def _init_unerasable_areas_on_mask(self, image_display_rect: pygame.Rect):
        """
        在 mask_alpha_surface 上标记不可擦除区域为不透明。
        image_display_rect: 当前图片在屏幕上的显示区域。
        """
        if not self.mask_alpha_surface: return

        # 遍历不可擦除区域配置
        for area_config in self.unerasable_areas_config:
            area_type = area_config.get("type")
            if area_type == "rect":
                 original_x = area_config.get("x", 0)
                 original_y = area_config.get("y", 0)
                 original_width = area_config.get("width", 0)
                 original_height = area_config.get("height", 0)

                 # 将原始图片上的矩形转换为 mask_alpha_surface 上的矩形
                 # 需要 ImageRenderer 的坐标和尺寸转换方法
                 # 示例：使用 ImageRenderer 转换原始图片的左上角和尺寸到屏幕坐标
                 screen_topleft = self.image_renderer.get_screen_coords_from_original(original_x, original_y)
                 screen_size = self.image_renderer.get_screen_size_from_original(original_width, original_height)
                 # 将屏幕坐标矩形转换为相对于 mask_alpha_surface 左上角的矩形
                 mask_rect = pygame.Rect(
                     screen_topleft[0] - image_display_rect.left,
                     screen_topleft[1] - image_display_rect.top,
                     screen_size[0],
                     screen_size[1]
                 ).clamp(self.mask_alpha_surface.get_rect()) # 确保不超出蒙版范围

                 # 在 mask_alpha_surface 的这个区域内绘制一个完全不透明的矩形
                 # Pygame 的 Surface.fill 不支持 alpha 通道，但可以使用 Surface.set_alpha 或 Surface.fill with alpha
                 # 或者直接绘制到 mask_alpha_surface 的 subsurfac 并 fill 不透明颜色
                 sub_mask_surface = self.mask_alpha_surface.subsurface(mask_rect)
                 sub_mask_surface.fill((255, 255, 255, 255)) # 填充完全不透明白色

            # TODO: 实现其他形状的不可擦区域 (circle, polygon)
            elif area_type == "circle":
                 original_center_x = area_config.get("x", 0)
                 original_center_y = area_config.get("y", 0)
                 original_radius = area_config.get("radius", 0)

                 # 将原始图片上的中心坐标和半径转换为 mask_alpha_surface 上的坐标和半径
                 screen_center = self.image_renderer.get_screen_coords_from_original(original_center_x, original_center_y)
                 # 半径转换比较复杂，需要考虑缩放的各向异性，如果缩放不是均匀的。
                 # 简化：假设半径是根据宽度或高度均匀缩放的
                 screen_radius = int(original_radius * (image_display_rect.width / self.image_renderer.original_image_size[0])) # 示例按宽度缩放比例
                 # 将屏幕坐标中心转换为相对于 mask_alpha_surface 左上角的中心
                 mask_center = (
                     screen_center[0] - image_display_rect.left,
                     screen_center[1] - image_display_rect.top
                 )

                 # 在 mask_alpha_surface 的这个区域内绘制一个完全不透明的圆
                 pygame.draw.circle(self.mask_alpha_surface, (255, 255, 255, 255), mask_center, screen_radius)


            # TODO: 实现 polygon 等形状

    # 不再需要 _update_unerasable_area_display_rects 方法，碰撞检测和绘制直接使用转换后的坐标或在绘制时转换


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        # 确保蒙版Surface已准备好，特别是resize后可能需要重新创建
        self._ensure_mask_surface(image_display_rect)

        mouse_pos = event.pos # 屏幕坐标

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            if image_display_rect.collidepoint(mouse_pos):
                self._is_erasing = True
                self._just_hit_unerasable_this_frame = False # 重置标记
                # 触发开始擦拭叙事 (只触发一次) - 在 update 中检查并返回

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: # 左键抬起
            self._is_erasing = False
            # 停止擦拭循环音效 sfx_erase_looping (如果正在播放)
            if self.audio_manager and self.audio_manager.is_sfx_playing("sfx_erase_looping"):
                 self.audio_manager.stop_sfx("sfx_erase_looping")


        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._is_erasing and image_display_rect.collidepoint(mouse_pos):
                # 将鼠标位置转换为相对于图片显示区域的坐标
                relative_pos = (mouse_pos[0] - image_display_rect.left, mouse_pos[1] - image_display_rect.top)

                # 检查是否在不可擦除区域
                is_in_unerasable = False
                # 将鼠标的屏幕坐标转换为原始图片坐标进行不可擦区域碰撞检测
                original_image_mouse_pos = self.image_renderer.get_image_coords(mouse_pos[0], mouse_pos[1])

                for area_config in self.unerasable_areas_config:
                     area_type = area_config.get("type")
                     if area_type == "rect":
                          original_x = area_config.get("x", 0)
                          original_y = area_config.get("y", 0)
                          original_width = area_config.get("width", 0)
                          original_height = area_config.get("height", 0)
                          original_rect = pygame.Rect(original_x, original_y, original_width, original_height)
                          if original_rect.collidepoint(original_image_mouse_pos):
                               is_in_unerasable = True
                               self._just_hit_unerasable_this_frame = True # 标记本帧擦中了不可擦区域
                               break
                     elif area_type == "circle":
                          original_center_x = area_config.get("x", 0)
                          original_center_y = area_config.get("y", 0)
                          original_radius = area_config.get("radius", 0)
                          if (original_image_mouse_pos[0] - original_center_x)**2 + (original_image_mouse_pos[1] - original_center_y)**2 <= original_radius**2:
                               is_in_unerasable = True
                               self._just_hit_unerasable_this_frame = True
                               break
                     # TODO: 实现其他形状的碰撞检测

                if not is_in_unerasable:
                    # 在 mask_alpha_surface 上绘制透明笔刷 (降低 alpha)
                    # 笔刷中心位置是 relative_pos (相对于图片显示区域左上角)
                    brush_rect_on_mask = pygame.Rect(0, 0, self.erase_brush_size, self.erase_brush_size)
                    brush_rect_on_mask.center = relative_pos

                    # 将笔刷绘制到 mask_alpha_surface 上，模拟擦除效果 (降低 alpha)
                    # 这是一个复杂且性能敏感的实现，取决于 Pygame 版本和方法选择
                    # 使用 BLEND_RGBA_MULT 和一个黑色的笔刷纹理可以模拟擦除 (如果蒙版是白色alpha=255)
                    # 加载一个简单的黑色圆形笔刷纹理
                    # brush_surface = self.image_renderer.get_effect_texture("erase_brush.png") # 示例笔刷纹理
                    # if brush_surface:
                    #     scaled_brush = pygame.transform.scale(brush_surface, (self.erase_brush_size, self.erase_brush_size))
                    #     # 绘制时使用 BLEND_RGBA_MULT 模式
                    #     # target_rect = brush_rect_on_mask.clamp(self.mask_alpha_surface.get_rect()) # 限制绘制区域在蒙版范围内
                    #     self.mask_alpha_surface.blit(scaled_brush, brush_rect_on_mask.topleft, special_flags=pygame.BLEND_RGBA_MULT)
                    # else:
                    # 简单模拟：直接在圆形区域内降低 alpha 值
                    target_alpha_reduction = 30 # 每次移动降低的 alpha 值 # TODO: 可移动到settings
                    mask_width, mask_height = self.mask_alpha_surface.get_size()
                    # 遍历笔刷区域内的像素
                    for px in range(max(0, brush_rect_on_mask.left), min(mask_width, brush_rect_on_mask.right)):
                        for py in range(max(0, brush_rect_on_mask.top), min(mask_height, brush_rect_on_mask.bottom)):
                            # 检查像素是否在圆内 (基于笔刷中心和半径)
                            if (px - brush_rect_on_mask.centerx)**2 + (py - brush_rect_on_mask.centery)**2 <= (self.erase_brush_size//2)**2:
                                current_color = self.mask_alpha_surface.get_at((px, py))
                                # 不擦除完全不透明的像素 (不可擦区域)
                                if current_color[3] < 255:
                                     new_alpha = max(0, current_color[3] - target_alpha_reduction)
                                     self.mask_alpha_surface.set_at((px, py), (current_color[0], current_color[1], current_color[2], new_alpha))


                    # 触发擦拭音效和视觉反馈
                    if self.audio_manager and not self.audio_manager.is_sfx_playing("sfx_erase_looping"):
                        self.audio_manager.play_sfx("sfx_erase_looping", loop=-1)

                    # self.image_renderer.trigger_effect("erase_particles", mouse_pos) # 示例粒子效果


                else: # 在不可擦除区域
                     # 触发不可擦音效
                     if self.audio_manager:
                          # 检查是否已经播放了不可擦音效，避免重复触发
                          if not self.audio_manager.is_sfx_playing("sfx_unerasable_hit"):
                               self.audio_manager.play_sfx("sfx_unerasable_hit") # 示例单次音效

                     # TODO: 改变笔刷视觉等，提示不可擦拭


    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新清洁擦除状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        # 确保蒙版Surface已准备好，特别是resize后可能需要重新创建
        self._ensure_mask_surface(image_display_rect)

        if self._is_completed:
            return True, {}


        # 计算擦除进度
        # 遍历 mask_alpha_surface 的像素，计算 alpha 值小于某个阈值的像素比例
        # 这是一个性能敏感的操作，可以考虑降低计算频率，或者使用近似方法
        self.erase_progress = self._calculate_erase_progress()


        # 检查是否触发了叙事事件
        narrative_events = self._check_and_trigger_narrative_events()

        # 检查是否完成
        if self.erase_progress >= self.erase_threshold:
             self._is_completed = True
             print(f"Clean Erase for {self.config['file']} Completed! Progress: {self.erase_progress}")
             # 停止擦拭循环音效
             if self.audio_manager:
                  self.audio_manager.stop_sfx("sfx_erase_looping")

             # 检查并触发 on_complete 和 on_complete_erase (如果适用)
             complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
             return True, {**narrative_events, **complete_narrative} # 返回所有触发的事件


        # 在未完成时，如果停止了擦拭且擦拭循环音效正在播放，停止它
        if not self._is_erasing and self.audio_manager and self.audio_manager.is_sfx_playing("sfx_erase_looping"):
             self.audio_manager.stop_sfx("sfx_erase_looping")

        # 重置本帧擦中不可擦区域标记 (在检查并触发叙事后重置)
        self._just_hit_unerasable_this_frame = False


        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制清洁擦除模块的视觉元素（主要是蒙版）"""
        # 在图片显示区域上方绘制 mask_alpha_surface
        if self.mask_alpha_surface:
             screen.blit(self.mask_alpha_surface, image_display_rect.topleft)

        # TODO: 绘制不可擦除区域的视觉提示 (可选，如果设计需要)
        # 例如，绘制边框或高亮区域
        # 需要将 self.unerasable_areas_config 中的原始坐标转换为屏幕坐标进行绘制
        # for area_config in self.unerasable_areas_config:
        #     area_type = area_config.get("type")
        #     if area_type == "rect":
        #          screen_rect = pygame.Rect(
        #              *self.image_renderer.get_screen_coords_from_original(area_config["x"], area_config["y"]),
        #              *self.image_renderer.get_screen_size_from_original(area_config["width"], area_config["height"])
        #          )
        #          pygame.draw.rect(screen, (255, 0, 0, 100), screen_rect, 2) # 示例：绘制一个红色半透明框
        #     elif area_type == "circle":
        #          screen_center = self.image_renderer.get_screen_coords_from_original(area_config["x"], area_config["y"])
        #          screen_radius = int(area_config.get("radius", 0) * (image_display_rect.width / self.image_renderer.original_image_size[0])) # 示例半径转换
        #          pygame.draw.circle(screen, (255, 0, 0, 100), screen_center, screen_radius, 2) # 示例：绘制红色圆圈边框


        # TODO: 绘制笔刷的视觉反馈 (例如，笔刷光标)
        mouse_pos = pygame.mouse.get_pos()
        if self._is_erasing and image_display_rect.collidepoint(mouse_pos):
            brush_visual_rect = pygame.Rect(0, 0, self.erase_brush_size, self.erase_brush_size)
            brush_visual_rect.center = mouse_pos
            # 示例：绘制白色圆圈边框
            pygame.draw.circle(screen, (255, 255, 255, 150), brush_visual_rect.center, self.erase_brush_size//2, 2)


    def _calculate_erase_progress(self):
        """
        计算 mask_alpha_surface 中 alpha 值小于某个阈值的像素比例。
        这是一个性能敏感的操作。
        """
        if not self.mask_alpha_surface: return 0.0
        total_pixels = self.mask_alpha_surface.get_width() * self.mask_alpha_surface.get_height()
        if total_pixels == 0: return 0.0

        erased_pixels = 0
        alpha_threshold = 50 # 低于此alpha值视为已擦除

        # 使用 tostring 获取像素数据，比 set_at 遍历快，但仍然是 CPU 密集型
        # 格式必须匹配创建 Surface 时的格式，这里是 RGBA
        try:
            # 获取像素数据的 bytes 对象
            pixel_bytes = pygame.image.tostring(self.mask_alpha_surface, "RGBA")

            # 遍历像素，检查 alpha 通道
            # 每个像素 4 个字节 (R, G, B, A)，alpha 在第 4 个字节 (索引 3)
            for i in range(3, len(pixel_bytes), 4):
                 if pixel_bytes[i] < alpha_threshold:
                      erased_pixels += 1

            # 返回擦除比例
            return erased_pixels / total_pixels

        except pygame.error as e:
             print(f"警告：计算擦除进度时出错: {e}")
             return 0.0 # 发生错误返回0

    # _init_unerasable_areas_on_mask 已实现

    # 不再需要 _update_unerasable_area_display_rects 方法，碰撞检测和绘制直接使用转换后的坐标或在绘制时转换


    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
        """检查当前状态是否触发了叙事事件，并返回未触发过的事件字典"""
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 on_start_erase (只触发一次)
        # 确保在 handle_event 中设置 _is_erasing 为 True 后立即检查
        if self._is_erasing and "on_start_erase" in config_triggers: # 检查是否正在擦拭 (作为一种触发条件)
             event_id = "on_start_erase"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        # 检查 on_hit_unerasable (遇到不可擦区域，需要防洪)
        if self._just_hit_unerasable_this_frame: # 在 handle_event 中标记的状态
           event_id = "on_hit_unerasable"
           # 如果需要每次擦中都触发，则不检查 _triggered_narrative_events
           if event_id in config_triggers: # 检查配置中是否存在此触发
               # 每次触发都添加到返回列表，由 GameManager/NarrativeManager 管理是否重复播放
               triggered[event_id] = config_triggers[event_id]
           # self._just_hit_unerasable_this_frame = False # 在 update 结束时重置


        # 检查进度触发 (on_erase_progress_XX)
        # 示例进度检查点
        progress_checkpoints = {
            "on_erase_progress_30": 0.3,
            "on_erase_progress_50": 0.5,
            "on_erase_progress_70": 0.7
            # TODO: 从 config 获取或定义更多进度触发点
        }
        for event_id, threshold in progress_checkpoints.items():
             if self.erase_progress >= threshold and event_id in config_triggers:
                 if event_id not in self._triggered_narrative_events:
                      triggered[event_id] = config_triggers[event_id]
                      self._triggered_narrative_events.add(event_id)


        # 检查 on_complete (互动完成)
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             # on_complete 事件只在互动模块的 is_completed 第一次为 True 时，由 GameManager._on_interaction_complete 触发
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)


        # 检查 on_complete_erase (擦除完成，只在混合玩法 Stage 3.2 触发)
        # 这个需要 GameManager 根据互动类型调用，或者 CleanErase 本身根据 config 类型判断
        # 在 Stage 3.2 的 config 中定义 post_erase_click_points，当擦除完成后，通知 GameManager 切换到点击阶段
        # 这个逻辑应该在 update 方法检查完成时，根据 config 类型和完成状态返回一个特定的事件类型
        # 示例 (在 Stage 3.2 的 CleanErase 实例中):
        if check_complete and self.config.get("type") == self.settings.INTERACTION_HYBRID_ERASE_THEN_CLICK and "on_complete_erase" in config_triggers:
             event_id = "on_complete_erase"
             # 如果这个事件只触发一次，添加到 _triggered_narrative_events
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)


        return triggered

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     # 需要保存 mask_alpha_surface 的状态，这比较复杂，可能需要保存其像素数据或一个简化表示
    #     # 或者只保存 erase_progress 和已触发事件，加载时根据进度近似恢复蒙版状态 (精度损失)
    #     return {
    #          "erase_progress": self.erase_progress,
    #          "triggered_narrative_events": list(self._triggered_narrative_events),
    #          "_is_erasing": self._is_erasing # 保存是否正在擦拭状态
    #          # "mask_alpha_data": self._get_mask_alpha_data() # 示例，复杂
    #     }
    # def load_state(self, state_data, image_display_rect: pygame.Rect): # 加载时需要传递当前显示区域
    #     self.erase_progress = state_data["erase_progress"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._is_erasing = state_data["_is_erasing"]
    #     self._is_completed = self.erase_progress >= self.erase_threshold # 重新计算完成状态
    #     # TODO: 根据加载的进度或数据恢复 mask_alpha_surface 的状态
    #     self._ensure_mask_surface(image_display_rect) # 确保surface存在并适应新尺寸
    #     # TODO: 恢复蒙版alpha状态 based on self.erase_progress 或保存的数据
    #     # 例如，根据进度，在 mask_alpha_surface 上绘制一个透明圆或矩形模拟擦除区域
    #     pass