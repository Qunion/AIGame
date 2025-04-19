# src/interaction_modules/clean_erase.py
import pygame
from src.settings import Settings
from src.image_renderer import ImageRenderer
import os

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
        self.settings = image_renderer.settings
        self.screen = screen # 需要主屏幕尺寸来创建RenderTexture

        # 从config中加载蒙版和不可擦除区域信息
        mask_texture_path = os.path.join(self.settings.MASK_DIR, config.get("mask_texture", "default_mask.png")) # 默认蒙版
        # TODO: 加载蒙版纹理，并缩放到图片的实际显示尺寸
        # self.mask_surface = pygame.image.load(mask_texture_path).convert_alpha() # 原始蒙版纹理
        # self.scaled_mask_surface = None # 缩放到图片显示尺寸的蒙版

        self.unerasable_areas_config = config.get("unerasable_areas", []) # 不可擦除区域配置

        # 用于模拟 Render Texture 的 Surface
        # 我们需要一个 Surface 来表示蒙版的透明度，初始为不透明，擦拭时修改alpha
        # 这个 Surface 需要和图片实际显示区域一样大
        self.mask_alpha_surface = None # 这是一个与图片显示区域同尺寸的 Surface，用来控制alpha
        self.erase_brush_size = 40 # 擦拭笔刷大小 (像素)
        self._is_erasing = False # 标记是否正在擦拭

        # 擦除进度
        self.erase_progress = 0.0
        self.erase_threshold = config.get("erase_threshold", 0.95) # 完成阈值

        # 跟踪已触发的叙事事件
        self._triggered_narrative_events = set()

        # 标记是否已完成
        self._is_completed = False

        # TODO: 初始化与擦除相关的视觉或音频反馈
        self._init_visual_elements()

    def _init_visual_elements(self):
        """初始化擦除相关的视觉元素"""
        # 创建用于模拟 Render Texture 的 Surface
        # 这个 Surface 的 alpha 通道将用来控制蒙版的透明度
        # 它的尺寸应该和图片实际显示区域一样大 (self.image_renderer.image_display_rect.size)
        # 但在 __init__ 时图片可能还没加载，所以需要在 update 或 handle_event 中根据 image_display_rect 初始化

        # TODO: 加载笔刷纹理
        # self.brush_texture = self.image_renderer.effect_textures.get("erase_brush") # 示例

        # TODO: 创建不可擦除区域的 Pygame Rect/Shape 对象 (需要在加载时根据配置转换坐标)
        self.unerasable_rects = [] # 示例只用Rect
        # for area_config in self.unerasable_areas_config:
        #     if area_config["type"] == "rect":
        #         # 将配置坐标转换为屏幕坐标或相对于图片显示区域的坐标
        #         # screen_rect = self.image_renderer.get_screen_rect_from_original(...)
        #         self.unerasable_rects.append(pygame.Rect(...))

    def _ensure_mask_surface(self, image_display_rect: pygame.Rect):
        """确保 mask_alpha_surface 已初始化并与图片显示区域尺寸匹配"""
        if self.mask_alpha_surface is None or self.mask_alpha_surface.get_size() != image_display_rect.size:
            print(f"初始化/重塑 mask_alpha_surface 为尺寸: {image_display_rect.size}")
            self.mask_alpha_surface = pygame.Surface(image_display_rect.size, pygame.SRCALPHA) # 带alpha通道
            self.mask_alpha_surface.fill((255, 255, 255, 255)) # 初始为完全不透明 (白色，alpha=255)

            # TODO: 根据配置，绘制初始蒙版纹理到 mask_alpha_surface 上，而不是纯白色
            # if self.scaled_mask_surface is None or self.scaled_mask_surface.get_size() != image_display_rect.size:
            #     mask_path = os.path.join(self.settings.MASK_DIR, self.config.get("mask_texture", "default_mask.png"))
            #     try:
            #          original_mask = pygame.image.load(mask_path).convert_alpha()
            #          self.scaled_mask_surface = pygame.transform.scale(original_mask, image_display_rect.size)
            #     except pygame.error as e:
            #          print(f"警告：无法加载或缩放蒙版纹理 {mask_path}: {e}")
            #          self.scaled_mask_surface = None # 加载失败

            # if self.scaled_mask_surface:
            #      self.mask_alpha_surface.blit(self.scaled_mask_surface, (0,0))
            # else:
            #      self.mask_alpha_surface.fill((255, 255, 255, 255)) # 使用纯白色作为 fallback

            # TODO: 根据不可擦除区域配置，初始化这些区域的alpha，使其保持不透明
            # self._init_unerasable_areas_on_mask()

        # TODO: 更新不可擦除区域的 Pygame Rect/Shape 对象，以适应新的图片显示区域尺寸
        # self._update_unerasable_area_rects(image_display_rect)


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """处理来自InputHandler的事件"""
        if self._is_completed:
            return

        self._ensure_mask_surface(image_display_rect) # 确保蒙版Surface已准备好

        mouse_pos = event.pos # 屏幕坐标

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键按下
            if image_display_rect.collidepoint(mouse_pos):
                self._is_erasing = True
                # 触发开始擦拭叙事 (只触发一次)
                if "on_start_erase" in self.config.get("narrative_triggers", {}) and "on_start_erase" not in self._triggered_narrative_events:
                    # 返回触发的事件，让 GameManager 启动叙事
                    pass # 在 update 中统一返回叙事事件

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: # 左键抬起
            self._is_erasing = False

        elif event.type == pygame.MOUSEMOTION: # 鼠标移动
            if self._is_erasing and image_display_rect.collidepoint(mouse_pos):
                # 将鼠标位置转换为相对于图片显示区域的坐标
                relative_pos = (mouse_pos[0] - image_display_rect.left, mouse_pos[1] - image_display_rect.top)

                # TODO: 检查是否在不可擦除区域
                is_in_unerasable = False
                # for unerasable_rect in self.unerasable_rects: # 示例只用Rect
                #     if unerasable_rect.collidepoint(relative_pos): # 注意这里的坐标系
                #         is_in_unerasable = True
                #         break

                if not is_in_unerasable:
                    # 在 mask_alpha_surface 上绘制透明笔刷
                    # 模拟 Render Texture 的绘制，用 SRCALPHA 混合模式
                    # 笔刷中心位置是 relative_pos
                    brush_rect = pygame.Rect(0, 0, self.erase_brush_size, self.erase_brush_size)
                    brush_rect.center = relative_pos

                    # TODO: 绘制一个透明圆圈或笔刷纹理到 self.mask_alpha_surface 上
                    # 需要设置 blit 的 special_flags=pygame.BLEND_RGBA_MULT 或其他模式来模拟擦除效果
                    # Pygame 的 Surface blit 模拟 Render Texture 擦除比较复杂，可能需要修改 Surface 的像素 alpha 值
                    # 或者使用更高级的渲染方式（如 moderngl 等库）
                    # 简化的方案是在一个 Surface 上绘制黑色（或透明），然后用它来和蒙版 Surface 叠加，控制最终透明度
                    # 或者直接操作像素数组 (性能可能不高)

                    # 示例：绘制一个黑色圆圈到临时的擦除Surfac上，然后用它更新mask_alpha_surface
                    erase_brush_surface = pygame.Surface((self.erase_brush_size, self.erase_brush_size), pygame.SRCALPHA)
                    pygame.draw.circle(erase_brush_surface, (0, 0, 0, 255), (self.erase_brush_size//2, self.erase_brush_size//2), self.erase_brush_size//2)
                    # 将黑色圆圈的alpha通道应用到mask_alpha_surface上对应的区域
                    # 这里的alpha混合逻辑需要仔细实现
                    # self.mask_alpha_surface.blit(erase_brush_surface, brush_rect.topleft, special_flags=pygame.BLEND_RGBA_MULT) # SRCALPHA 模拟

                    # 更简单的模拟：直接将笔刷区域的 alpha 设为0
                    # 这是一个性能较低的方法，特别是笔刷大或屏幕大时
                    # rect_to_clear = brush_rect.clamp(self.mask_alpha_surface.get_rect())
                    # for x in range(rect_to_clear.left, rect_to_clear.right):
                    #     for y in range(rect_to_clear.top, rect_to_clear.bottom):
                    #         if (x - brush_rect.centerx)**2 + (y - brush_rect.centery)**2 <= (self.erase_brush_size//2)**2:
                    #             self.mask_alpha_surface.set_at((x, y), (0, 0, 0, 0)) # 设置为完全透明

                    # TODO: 实现一个高效的擦除绘制逻辑，可能需要自定义Shader或利用硬件加速特性
                    # 暂时留空具体的绘制实现

                    # TODO: 触发擦拭音效和视觉反馈
                    # self.audio_manager.play_sfx("sfx_erase_looping") # 循环音效
                    # self.image_renderer.trigger_effect("erase_particles", mouse_pos) # 示例粒子效果

                else: # 在不可擦除区域
                     # TODO: 触发遇到不可擦除区域的叙事和反馈
                     if "on_hit_unerasable" in self.config.get("narrative_triggers", {}):
                         # 返回触发的事件，让 GameManager 启动叙事
                         pass # 在 update 中统一返回叙事事件
                     # TODO: 播放不可擦音效，改变笔刷视觉等

    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """
        更新清洁擦除状态。
        返回 (是否完成当前图片互动, 触发的叙事事件字典)。
        """
        if self._is_completed:
            return True, {}

        self._ensure_mask_surface(image_display_rect) # 确保蒙版Surface已准备好

        # 计算擦除进度
        # TODO: 需要一个方法来计算 mask_alpha_surface 中 alpha 值小于某个阈值的像素比例
        # 这是一个性能敏感的操作，可能需要优化或使用不同的方法
        # erase_progress = self._calculate_erase_progress() # 示例
        erase_progress = 0.0 # 占位，待实现计算方法
        self.erase_progress = erase_progress # 更新进度变量

        # TODO: 触发进度相关的叙事事件 (例如，on_erase_progress_XX)
        narrative_events = self._check_and_trigger_narrative_events()


        # 检查是否完成
        if self.erase_progress >= self.erase_threshold:
             self._is_completed = True
             print(f"Clean Erase for {self.config['file']} Completed! Progress: {self.erase_progress}")
             # 在这里触发 on_complete 叙事事件 (如果有)
             complete_narrative = self._check_and_trigger_narrative_events(check_complete=True) # 检查完成事件
             return True, {**narrative_events, **complete_narrative} # 返回所有触发的事件

        return False, narrative_events # 未完成

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制清洁擦除模块的视觉元素（主要是蒙版）"""
        # 在图片显示区域上方绘制 mask_alpha_surface
        if self.mask_alpha_surface:
             screen.blit(self.mask_alpha_surface, image_display_rect.topleft)

        # TODO: 绘制不可擦除区域的视觉提示 (可选，如果设计需要)
        # for unerasable_rect in self.unerasable_rects:
        #     pygame.draw.rect(screen, (255, 0, 0, 100), unerasable_rect, 2) # 示例：绘制一个红色半透明框

        # TODO: 绘制笔刷的视觉反馈 (例如，笔刷光标)
        # mouse_pos = pygame.mouse.get_pos()
        # if self._is_erasing and image_display_rect.collidepoint(mouse_pos):
        #     brush_visual_rect = pygame.Rect(0, 0, self.erase_brush_size, self.erase_brush_size)
        #     brush_visual_rect.center = mouse_pos
        #     pygame.draw.circle(screen, (255, 255, 255, 150), brush_visual_rect.center, self.erase_brush_size//2, 2) # 示例：绘制白色圆圈边框


    # TODO: 实现计算擦除进度的方法 (_calculate_erase_progress)
    # 它需要遍历 mask_alpha_surface 的像素，计算 alpha < 某个阈值的比例

    # TODO: 实现初始化不可擦区域在蒙版上的方法 (_init_unerasable_areas_on_mask)
    # TODO: 实现根据新尺寸更新不可擦区域Rects的方法 (_update_unerasable_area_rects)

    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
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
        # 这个判断应该在 handle_event 中做更精确的碰撞检测时触发，并标记一个状态，然后在 update 中检查状态并触发叙事
        # 示例 (伪代码):
        # if self._just_hit_unerasable_this_frame: # 在 handle_event 中标记的状态
        #    event_id = "on_hit_unerasable"
        #    if event_id in config_triggers and event_id not in self._triggered_narrative_events: # 每次触发
        #        triggered[event_id] = config_triggers[event_id]
        #        # 不添加到 _triggered_narrative_events 集合，允许重复触发
        #    self._just_hit_unerasable_this_frame = False

        # 检查进度触发 (on_erase_progress_XX)
        # 示例:
        # if self.erase_progress >= 0.3 and "on_erase_progress_30" in config_triggers:
        #     event_id = "on_erase_progress_30"
        #     if event_id not in self._triggered_narrative_events:
        #          triggered[event_id] = config_triggers[event_id]
        #          self._triggered_narrative_events.add(event_id)
        # TODO: 检查所有进度触发点

        # 检查 on_complete (互动完成)
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        # 检查 on_complete_erase (擦除完成，只在混合玩法 Stage 3.2 触发)
        # 这个需要 GameManager 根据互动类型调用，或者 CleanErase 本身根据 config 类型判断
        # 示例 (在 Stage 3.2 的 CleanErase 实例中):
        # if self._is_completed and self.config["type"] == self.settings.INTERACTION_HYBRID_ERASE_THEN_CLICK and "on_complete_erase" in config_triggers:
        #      event_id = "on_complete_erase"
        #      if event_id not in self._triggered_narrative_events:
        #          triggered[event_id] = config_triggers[event_id]
        #          self._triggered_narrative_events.add(event_id)


        return triggered

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     # 需要保存 mask_alpha_surface 的状态，这比较复杂，可能需要保存其像素数据或一个简化表示
    #     # 或者只保存 erase_progress 和已触发事件，加载时根据进度近似恢复蒙版状态 (精度损失)
    #     return {
    #          "erase_progress": self.erase_progress,
    #          "triggered_narrative_events": list(self._triggered_narrative_events)
    #          # "mask_alpha_data": self._get_mask_alpha_data() # 示例，复杂
    #     }
    # def load_state(self, state_data):
    #     self.erase_progress = state_data["erase_progress"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._is_completed = self.erase_progress >= self.erase_threshold # 重新计算完成状态
    #     # TODO: 根据加载的进度或数据恢复 mask_alpha_surface 的状态
    #     # self._load_mask_alpha_data(state_data["mask_alpha_data"])