# src/image_renderer.py
import pygame
import os
from src.settings import Settings

class ImageRenderer:
    """
    负责图片的加载、缩放、裁剪、显示以及各种艺术化效果的实现。
    管理图片在屏幕上的显示位置和尺寸。
    """

    def __init__(self, screen, settings: Settings):
        """初始化图片渲染器"""
        self.screen = screen
        self.settings = settings
        self.current_image = None # 当前加载的 Pygame Surface
        self.original_image_size = (0, 0) # 原始图片的尺寸
        self.image_display_rect = pygame.Rect(0, 0, 0, 0) # 图片在屏幕上的实际显示区域 (Rect对象)

        # TODO: 特效系统 (需要根据设计和资源实现)
        self.current_effects = {} # {effect_type: effect_params}
        self.effect_surfaces = {} # 用于复杂特效的Surface，例如 Render Texture 模拟

        # TODO: 蒙版纹理加载 (用于清洁擦除)
        self.mask_textures = {} # {mask_id: Pygame Surface}
        self._load_mask_textures() # 加载所有需要的蒙版纹理

        # TODO: 其他艺术化资源的加载 (粒子纹理、光晕纹理等)
        self.effect_textures = {}
        self._load_effect_textures()

        # TODO: 背景图加载 (横屏和竖屏)
        self.background_vertical = None
        self.background_horizontal = None
        self._load_backgrounds() # 加载背景图

        # 当前背景类型
        self.current_background_type = "vertical" # or "horizontal"

    def _load_mask_textures(self):
        """加载所有预定义的蒙版纹理"""
        # TODO: 根据 settings 或 image_config 中定义的蒙版文件路径加载
        # 示例:
        # self.mask_textures["dust_mask.png"] = pygame.image.load(os.path.join(self.settings.MASK_DIR, "dust_mask.png")).convert_alpha()
        pass # 待填充

    def _load_effect_textures(self):
         """加载所有预定义的特效纹理"""
         # 示例:
         # self.effect_textures["sparkle"] = pygame.image.load(os.path.join(self.settings.EFFECTS_DIR, "sparkle.png")).convert_alpha()
         pass # 待填充

    def _load_backgrounds(self):
        """加载横屏和竖屏背景图"""
        # 示例:
        # self.background_vertical = pygame.image.load(os.path.join(self.settings.IMAGE_DIR, "background_vertical.png")).convert()
        # self.background_horizontal = pygame.image.load(os.path.join(self.settings.IMAGE_DIR, "background_horizontal.png")).convert()
        pass # 待填充

    def load_image(self, image_path):
        """加载指定图片，并进行缩放裁剪"""
        try:
            original_image = pygame.image.load(image_path).convert_alpha() # 加载图片
            self.original_image_size = original_image.get_size()
            self.current_image = self._scale_and_crop_image(original_image)
            self._calculate_display_rect() # 计算图片在屏幕上的显示位置和尺寸
            print(f"图片加载成功: {image_path}, 原始尺寸: {self.original_image_size}, 显示尺寸: {self.current_image.get_size()}")

            # TODO: 初始化特定于当前图片的特效或效果表面 (例如，Clean Erase 的 Render Texture 模拟)
            # 这部分逻辑可能更适合放在对应的互动模块里，然后由互动模块通知 ImageRenderer 如何绘制

        except pygame.error as e:
            print(f"警告：无法加载图片 {image_path}: {e}")
            self.current_image = None # 加载失败，设置图片为None

    def _scale_and_crop_image(self, original_image: pygame.Surface) -> pygame.Surface:
        """
        根据窗口的16:9区域，对原始图片进行缩放和裁剪。
        保持宽高比，将较短一边缩放到匹配目标区域，裁剪长边超出部分。
        """
        original_width, original_height = original_image.get_size()
        target_aspect = self.settings.IMAGE_AREA_ASPECT_RATIO

        original_aspect = original_width / original_height

        # 计算缩放后的尺寸
        if original_aspect > target_aspect:
            # 原始图片更宽，匹配高度，裁剪宽度
            scaled_height = self.screen.get_height() # 目标高度是屏幕高度 (假设美图区域占满屏幕高)
            scaled_width = int(scaled_height * original_aspect)
            scaled_image = pygame.transform.scale(original_image, (scaled_width, scaled_height))
            # 计算需要裁剪的宽度
            crop_width = scaled_width - int(self.screen.get_height() * target_aspect)
            crop_rect = pygame.Rect(crop_width // 2, 0, int(self.screen.get_height() * target_aspect), scaled_height)
            cropped_image = scaled_image.subsurface(crop_rect)

        else:
            # 原始图片更高或宽高比相同，匹配宽度，裁剪高度
            scaled_width = int(self.screen.get_height() * target_aspect) # 目标宽度根据屏幕高度和16:9比例计算
            scaled_height = int(scaled_width / original_aspect)
            scaled_image = pygame.transform.scale(original_image, (scaled_width, scaled_height))
            # 计算需要裁剪的高度
            crop_height = scaled_height - self.screen.get_height()
            crop_rect = pygame.Rect(0, crop_height // 2, scaled_width, int(self.screen.get_height())) # 这里目标高度应该也是根据屏幕高度来的
            cropped_image = scaled_image.subsurface(crop_rect)

        # 最终裁剪后的图片应该匹配屏幕的16:9区域的尺寸
        return cropped_image

    def _calculate_display_rect(self):
        """计算图片在屏幕上的实际显示区域（居中）"""
        if self.current_image:
            img_width, img_height = self.current_image.get_size()
            screen_width, screen_height = self.screen.get_size()

            # 图片区域保持16:9，且短边匹配屏幕短边（根据自适应逻辑，短边是高）
            # 所以图片显示尺寸就是屏幕高度 x 16:9 比例计算出的宽度
            display_height = screen_height
            display_width = int(screen_height * self.settings.IMAGE_AREA_ASPECT_RATIO)

            # 居中计算位置
            pos_x = (screen_width - display_width) // 2
            pos_y = (screen_height - display_height) // 2 # Stage 2/3 的文本框在底部，这里需要调整Y轴位置吗？设计文档说文本框浮在图片上不阻挡操作，UI相对美图区域。所以美图区域可能不占满全屏高。
            # 重新思考美图区域位置：如果UI相对美图区域，且文本框在底部，那么美图区域应该在屏幕上方留出文本框空间。
            # 假设美图区域占屏幕高度的大部分，底部留固定像素高度给文本框。
            # 让我们假设美图区域的高度是屏幕高度 - 文本框高度。
            # display_height = screen_height - self.settings.TEXT_BOX_HEIGHT # 示例
            # display_width = int(display_height * self.settings.IMAGE_AREA_ASPECT_RATIO)
            # pos_x = (screen_width - display_width) // 2
            # pos_y = (screen_height - display_height - self.settings.TEXT_BOX_HEIGHT) # 示例
            # TODO: 这个美图实际显示区域的计算需要根据最终的UI布局设计来确定。
            # 当前先简化为居中显示，占满屏幕高度（裁剪宽度）或宽度（留黑边高）
            # 根据"整体缩短，直到较短的一边刚好匹配放置美图的窗口"，如果窗口是16:9，美图区域也是16:9，那美图将缩放到恰好填满16:9区域，没有裁剪或黑边。
            # 如果窗口不是16:9 (例如全屏模式，但游戏区域保持16:9)，那么美图区域会居中，周围有黑边。
            # 鉴于你说了裁剪，那意味着美图区域始终是屏幕的16:9区域，美图缩放后裁剪以填充这个区域。

            # 最终确定：美图显示区域就是屏幕中央的 16:9 矩形区域，其大小根据屏幕大小和16:9比例计算。
            # 美图将被缩放后裁剪以填充这个区域。
            display_width_calculated = int(screen_height * self.settings.ASPECT_RATIO) # 屏幕高度 * 16/9
            display_height_calculated = screen_height
            if display_width_calculated > screen_width:
                 # 屏幕更窄，以宽度为准计算高度
                 display_width_calculated = screen_width
                 display_height_calculated = int(screen_width / self.settings.ASPECT_RATIO)

            self.image_display_rect = pygame.Rect(
                 (screen_width - display_width_calculated) // 2,
                 (screen_height - display_height_calculated) // 2,
                 display_width_calculated,
                 display_height_calculated
            )
            print(f"图片显示区域计算: {self.image_display_rect}")

            # 缩放并裁剪以适应最终显示区域
            self.current_image = pygame.transform.scale(self.current_image, self.image_display_rect.size)


    def resize(self, new_width, new_height):
        """处理窗口大小改变事件"""
        self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
        # 重新计算美图显示区域和缩放裁剪
        if self.current_image: # 如果当前有图片加载
             # 需要重新从原始图片加载并缩放裁剪，或者保存一个中间的缩放版本
             # 最简单的办法是保存原始图片，resize时重新加载并缩放
             # 或者，在_scale_and_crop_image中返回的Surface已经是相对于16:9区域的，resize时只需要简单scale这个Surface
             # 让我们假设 _scale_and_crop_image 返回的是一个标准16:9比例的Surface
             # 那么 resize 时只需要将其缩放到新的 display_rect 尺寸
             if self.original_image_size != (0,0): # 确保有原始图片信息
                 original_image = pygame.image.load(os.path.join(self.settings.IMAGE_DIR, self.image_configs[self.game_manager.current_image_id]["file"])).convert_alpha() # 需要 GameManager 引用或图片路径
                 self.current_image = self._scale_and_crop_image(original_image)
                 self._calculate_display_rect()
             else: # 没有图片加载时，只需要更新屏幕尺寸
                 self._calculate_display_rect() # 更新 self.image_display_rect


    def draw_image(self, image_id):
        """绘制当前图片及其应用的效果"""
        if self.current_image:
            # 绘制背景图
            self.draw_background()

            # 绘制图片本体
            # TODO: 这里需要根据当前的互动状态来决定如何绘制图片本体
            # 例如，如果是清洁擦除，需要绘制 Render Texture 模拟的表面
            # 如果是拼图，需要绘制每个碎片
            # 如果是混合玩法，需要协调绘制多个层/效果

            # 简单的示例：直接绘制缩放裁剪后的图片
            self.screen.blit(self.current_image, self.image_display_rect.topleft)

            # TODO: 绘制额外的艺术化效果层 (叠加在图片上层的效果)
            # self._draw_effects()

            # TODO: 绘制蒙版 (如果当前互动是清洁擦除)
            # if self._current_interaction_is_clean_erase():
            #     self._draw_erase_mask() # 需要 CleanErase 模块提供绘制蒙版的方法

            # TODO: 绘制拼图碎片 (如果当前互动是拼图)
            # if self._current_interaction_is_drag_puzzle():
            #     self._draw_puzzle_pieces() # 需要 DragPuzzle 模块提供绘制碎片的方法

    def draw_background(self):
        """绘制背景图"""
        # 根据当前背景类型和屏幕尺寸选择并缩放绘制背景图
        if self.current_background_type == "vertical" and self.background_vertical:
             bg_image = self.background_vertical
        elif self.current_background_type == "horizontal" and self.background_horizontal:
             bg_image = self.background_horizontal
        else:
             self.screen.fill(self.settings.BLACK) # 没有背景图就用黑色填充
             return

        # 缩放背景图以适应屏幕
        bg_image_scaled = pygame.transform.scale(bg_image, self.screen.get_size())
        self.screen.blit(bg_image_scaled, (0, 0))

    def switch_background(self, bg_type):
        """切换背景图类型 (vertical/horizontal)"""
        self.current_background_type = bg_type
        # 可以在这里触发背景切换的动画效果

    # TODO: 实现各种艺术化效果的方法 (例如，模糊、噪点、光晕叠加、结构线叠加等)
    # 这些方法会被 ImageRenderer 的 draw_image 或 apply_effect 调用
    # def apply_effect(self, effect_type, params):
    #     """应用一个艺术化效果"""
    #     self.current_effects[effect_type] = params
    #     # TODO: 根据效果类型，可能需要创建 Render Texture 或其他 Surface 来实现复杂效果

    # def _draw_effects(self):
    #     """绘制当前应用的所有效果"""
    #     # 遍历 self.current_effects，根据效果类型调用对应的绘制逻辑
    #     # 示例：
    #     # if "blur" in self.current_effects:
    #     #     self._draw_blur(self.current_effects["blur"])
    #     # if "overlay" in self.current_effects:
    #     #      self._draw_overlay(self.current_effects["overlay"])
    #     pass # 待填充

    # TODO: 其他辅助方法，例如坐标转换 (将原始图片坐标或相对坐标转换为屏幕坐标)
    # def get_screen_coords(self, relative_coords: tuple[float, float]) -> tuple[int, int]:
    #      """将相对图片区域的坐标 (0-1) 转换为屏幕坐标"""
    #      # 使用 self.image_display_rect 进行转换
    #      return (
    #          self.image_display_rect.left + int(relative_coords[0] * self.image_display_rect.width),
    #          self.image_display_rect.top + int(relative_coords[1] * self.image_display_rect.height)
    #      )

    # def get_relative_coords(self, screen_coords: tuple[int, int]) -> tuple[float, float]:
    #      """将屏幕坐标转换为相对图片区域的坐标 (0-1)"""
    #      # 使用 self.image_display_rect 进行转换
    #      return (
    #           (screen_coords[0] - self.image_display_rect.left) / self.image_display_rect.width,
    #           (screen_coords[1] - self.image_display_rect.top) / self.image_display_rect.height
    #      )

    # def get_image_coords(self, screen_coords: tuple[int, int]) -> tuple[int, int]:
    #      """将屏幕坐标转换为原始图片像素坐标"""
    #      # 需要考虑缩放和裁剪。这是一个复杂的方法。
    #      # 简化的方法是只处理相对坐标转换。如果 config 中是像素坐标，需要在加载时转换或在互动模块中处理。
    #      pass # 待填充