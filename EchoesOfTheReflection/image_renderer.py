# image_renderer.py
import pygame
import os
# 导入自定义模块 - 现在它们位于根目录
from settings import Settings
# 导入 GameManager 类型提示，避免循环引用
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_manager import GameManager


class ImageRenderer:
    """
    负责图片的加载、缩放、裁剪、显示以及各种艺术化效果的实现。
    管理图片在屏幕上的显示位置和尺寸。
    """

    def __init__(self, screen, settings: Settings):
        """初始化图片渲染器"""
        self.screen = screen
        self.settings = settings

        # 需要 GameManager 引用以获取当前图片ID和配置，以便重新加载图片进行resize
        # GameManager 会在初始化自身后将自身实例赋值给 settings.game_manager
        self.game_manager: 'GameManager' = None # 初始为None，稍后赋值

        self.current_image_id = None # 新增：当前加载的图片的ID
        self.current_image = None # 当前加载的 Pygame Surface (已缩放裁剪到显示尺寸)
        self.original_image = None # 新增：加载的原始图片 Surface (未缩放，用于resize时重新处理)
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

        # 背景图加载 (横屏和竖屏)
        self.background_vertical = None
        self.background_horizontal = None
        self._load_backgrounds() # 加载背景图

        # 当前背景类型
        self.current_background_type = "vertical" # or "horizontal"


    def set_game_manager(self, game_manager: 'GameManager'):
        """GameManager在初始化完成后调用此方法，将自身引用传递过来"""
        self.game_manager = game_manager
        # 在这里可以获取 image_configs，因为它已经在 GameManager 中加载了
        # self.image_configs = self.game_manager.image_configs # 在加载图片时从 GameManager 获取 config 更安全


    def _load_mask_textures(self):
        """加载所有预定义的蒙版纹理"""
        # 根据 settings 中定义的蒙版文件路径加载
        mask_files = [
            "dust_mask.png",
            "fog_mask.png",
            "veil_mask.png",
            "structure_mask.png",
            "structure_overlay.png"
            # TODO: 添加其他蒙版纹理文件路径
        ]
        for file_name in mask_files:
             file_path = os.path.join(self.settings.MASK_DIR, file_name)
             if os.path.exists(file_path):
                 try:
                     self.mask_textures[file_name] = pygame.image.load(file_path).convert_alpha()
                     print(f"加载蒙版纹理成功: {file_name}")
                 except pygame.error as e:
                     print(f"警告：无法加载蒙版纹理 {file_path}: {e}")
             else:
                 print(f"警告：蒙版纹理文件未找到 {file_path}")


    # ... _load_effect_textures 方法同之前
    def _load_effect_textures(self):
         """加载所有预定义的特效纹理"""
         # 示例特效纹理文件路径
         effect_files = [
             "sparkle.png",
             "glow.png",
             # TODO: 添加其他特效纹理文件路径，如 Stage 3.2, 3.3, 4.3, 5.3, 6.1, 6.2 的特效图片
             "anomaly_flash.png",
             "puzzle_fragment_flash.png",
             "core_activation.png",
             "self_sculpt_complete.png",
             "resonance_pulse_blue.png", # 示例，可能需要多种颜色/形态
             "connection_established.png",
         ]
         for file_name in effect_files:
              file_path = os.path.join(self.settings.EFFECTS_DIR, file_name)
              if os.path.exists(file_path):
                  try:
                      self.effect_textures[file_name] = pygame.image.load(file_path).convert_alpha()
                      print(f"加载特效纹理成功: {file_name}")
                  except pygame.error as e:
                      print(f"警告：无法加载特效纹理 {file_path}: {e}")
              else:
                  print(f"警告：特效纹理文件未找到 {file_path}")


    # ... _load_backgrounds 方法同之前
    def _load_backgrounds(self):
        """加载横屏和竖屏背景图"""
        # 示例背景图文件路径 (需要在 assets/images 目录下准备这些图片)
        bg_vertical_path = os.path.join(self.settings.IMAGE_DIR, "background_vertical.png")
        bg_horizontal_path = os.path.join(self.settings.IMAGE_DIR, "background_horizontal.png")

        if os.path.exists(bg_vertical_path):
            try:
                 self.background_vertical = pygame.image.load(bg_vertical_path).convert()
                 print(f"加载竖屏背景图成功: {bg_vertical_path}")
            except pygame.error as e:
                 print(f"警告：无法加载竖屏背景图 {bg_vertical_path}: {e}")
        else:
            print(f"警告：竖屏背景图文件未找到 {bg_vertical_path}")

        if os.path.exists(bg_horizontal_path):
            try:
                 self.background_horizontal = pygame.image.load(bg_horizontal_path).convert()
                 print(f"加载横屏背景图成功: {bg_horizontal_path}")
            except pygame.error as e:
                 print(f"警告：无法加载横屏背景图 {bg_horizontal_path}: {e}")
        else:
            print(f"警告：横屏背景图文件未找到 {bg_horizontal_path}")



    def load_image(self, image_path):
        """加载指定图片，并进行缩放裁剪"""
        try:
            # 保存原始图片，用于resize
            self.original_image = pygame.image.load(image_path).convert_alpha()
            self.original_image_size = self.original_image.get_size()

            # 根据当前屏幕尺寸计算显示尺寸并缩放裁剪
            self.current_image = self._scale_and_crop_image(self.original_image, self.screen.get_size())
            self._calculate_display_rect(self.screen.get_size()) # 计算图片在屏幕上的实际显示位置和尺寸

            print(f"图片加载成功: {image_path}, 原始尺寸: {self.original_image_size}, 显示尺寸: {self.current_image.get_size()}")

            # TODO: 初始化特定于当前图片的特效或效果表面 (例如，Clean Erase 的 Render Texture 模拟)
            # 这部分逻辑可能更适合放在对应的互动模块里，由互动模块在初始化时调用ImageRenderer的方法来设置

        except pygame.error as e:
            print(f"警告：无法加载图片 {image_path}: {e}")
            self.original_image = None
            self.current_image = None
            self.original_image_size = (0, 0)
            self.image_display_rect = pygame.Rect(0, 0, 0, 0)


    # ... _scale_and_crop_image 方法同之前
    def _scale_and_crop_image(self, original_image: pygame.Surface, screen_size: tuple[int, int]) -> pygame.Surface:
        """
        根据屏幕的16:9显示区域，对原始图片进行缩放和裁剪。
        保持宽高比，将较短一边缩放到匹配目标区域的短边，裁剪长边超出部分。
        目标区域是屏幕中央的、与屏幕同高同宽的16:9区域。
        """
        original_width, original_height = original_image.get_size()
        screen_width, screen_height = screen_size

        # 目标显示区域的尺寸（与屏幕同高，16:9比例）
        target_display_height = screen_height
        target_display_width = int(screen_height * self.settings.ASPECT_RATIO)

        # 如果计算出的宽度超过屏幕宽度，则以屏幕宽度为准，重新计算高度
        if target_display_width > screen_width:
            target_display_width = screen_width
            target_display_height = int(screen_width / self.settings.ASPECT_RATIO)

        # 原始图片的宽高比
        original_aspect = original_width / original_height
        # 目标显示区域的宽高比
        target_aspect = target_display_width / target_display_height # 使用计算出的实际目标宽高比


        # 计算缩放后的原始图片尺寸（按原始比例缩放到能覆盖目标区域）
        if original_aspect > target_aspect:
            # 原始图片更宽，按目标区域高度缩放，宽度会超出
            scale_factor = target_display_height / original_height
            scaled_original_width = int(original_width * scale_factor)
            scaled_original_height = target_display_height
        else:
            # 原始图片更高或同比例，按目标区域宽度缩放，高度会超出或刚好
            scale_factor = target_display_width / original_width
            scaled_original_width = target_display_width
            scaled_original_height = int(original_height * scale_factor)

        scaled_image = pygame.transform.scale(original_image, (scaled_original_width, scaled_original_height))

        # 计算裁剪矩形 (在缩放后的原始图片上的坐标)
        crop_x = (scaled_original_width - target_display_width) // 2
        crop_y = (scaled_original_height - target_display_height) // 2
        crop_rect = pygame.Rect(crop_x, crop_y, target_display_width, target_display_height)

        # 裁剪图片
        cropped_image = scaled_image.subsurface(crop_rect)

        return cropped_image


    # ... _calculate_display_rect 方法同之前
    def _calculate_display_rect(self, screen_size: tuple[int, int]):
        """
        计算图片在屏幕上的实际显示区域（居中）。
        美图区域保持与屏幕同高同宽的16:9比例，居中显示。
        """
        screen_width, screen_height = screen_size

        # 美图显示区域的尺寸就是根据屏幕尺寸计算的16:9区域尺寸
        display_width = int(screen_height * self.settings.ASPECT_RATIO)
        display_height = screen_height

        if display_width > screen_width:
            # 如果计算出的宽度超过屏幕宽度，则以屏幕宽度为准，重新计算高度
            display_width = screen_width
            display_height = int(screen_width / self.settings.ASPECT_RATIO)

        # 居中计算位置
        pos_x = (screen_width - display_width) // 2
        pos_y = (screen_height - display_height) // 2 # 保持居中

        self.image_display_rect = pygame.Rect(
             pos_x, pos_y, display_width, display_height
        )
        # print(f"图片显示区域计算: {self.image_display_rect}") # 调试打印



    def resize(self, new_width, new_height):
        """处理窗口大小改变事件"""
        # Pygame 的 Surface 是与特定屏幕绑定的，resize时屏幕Surface会改变，需要重新加载或获取
        # screen 会在 GameManager 中重新创建并传递
        # self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE) # 这行应该在GameManager里

        # 重新计算美图显示区域
        self._calculate_display_rect((new_width, new_height))

        # 如果当前有加载的原始图片，重新进行缩放和裁剪
        if self.original_image:
             self.current_image = self._scale_and_crop_image(self.original_image, (new_width, new_height))
             print(f"窗口resize，图片重新缩放裁剪到显示尺寸: {self.current_image.get_size()}")

        # TODO: 通知 CleanErase 等模块，它们的 Render Texture 模拟 Surface 可能需要重新创建/调整尺寸
        # 这个通知应该由 GameManager 发出


    def draw_image(self, image_id):
        """绘制当前图片及其应用的效果"""
        # 绘制背景图 (根据当前屏幕尺寸和全屏状态)
        self.draw_background(self.screen.get_size())

        if self.current_image:
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

    def draw_background(self, screen_size: tuple[int, int]):
        """绘制背景图，适应屏幕尺寸"""
        screen_width, screen_height = screen_size

        # 判断当前是横屏还是竖屏模式，选择背景图
        # 如果窗口宽高比 > 1 (宽大于高)，通常是横屏
        # 如果窗口宽高比 <= 1 (高大于等于宽)，通常是竖屏
        # 游戏设计是 16:9，所以默认是横屏比例。全屏时如果屏幕是带鱼屏等，可能会是更宽的横屏。
        # 让我们简单判断当前窗口是否比 1:1 更宽，作为横竖屏判断（或者直接根据 settings 中的标志判断）
        # 根据设计，全屏时切换横屏背景，默认窗口用竖屏背景。
        # self.current_background_type 会由 GameManager 在全屏切换时设置

        if self.current_background_type == "vertical" and self.background_vertical:
             bg_image = self.background_vertical
        elif self.current_background_type == "horizontal" and self.background_horizontal:
             bg_image = self.background_horizontal
        else:
             self.screen.fill(self.settings.BLACK) # 没有背景图就用黑色填充
             return

        # 缩放背景图以填充整个屏幕
        bg_image_scaled = pygame.transform.scale(bg_image, (screen_width, screen_height))
        self.screen.blit(bg_image_scaled, (0, 0))


    def switch_background(self, bg_type):
        """切换背景图类型 (vertical/horizontal)"""
        if bg_type in ["vertical", "horizontal"]:
            self.current_background_type = bg_type
        else:
             print(f"警告：未知背景类型 {bg_type}")
        # 可以在这里触发背景切换的动画效果


    # 实现各种艺术化效果的方法 (例如，模糊、噪点、光晕叠加、结构线叠加等)
    # 这些方法会被 ImageRenderer 的 draw_image 或 apply_effect 调用
    def apply_effect(self, effect_type, params=None):
        """应用一个艺术化效果"""
        # 这是一个高级功能，Pygame 原生支持有限，可能需要模拟或额外库
        # 简单的效果可以直接修改 self.current_image 或叠加 Surface
        # 复杂的效果（如 Render Texture for blur/erase）需要更多逻辑
        print(f"TODO: 实现应用艺术化效果: {effect_type} with params {params}")
        self.current_effects[effect_type] = params # 存储当前应用的效果类型和参数

        # TODO: 根据效果类型，可能需要创建 Render Texture 或其他 Surface 来实现复杂效果
        # 例如，对于模糊效果，需要创建模糊后的Surface并在draw_image中绘制
        if effect_type == "blur":
             # 需要将当前图片进行模糊处理并存储
             # Pygame 的 transform.gaussian_blur 需要 Pygame 2.1 以上
             # 或者使用 PIL/Pillow 库进行模糊处理
             # blurred_image = pygame.transform.gaussian_blur(self.current_image, params) # params 是模糊半径/强度
             # self.effect_surfaces["blurred"] = blurred_image
             pass # 待实现具体的模糊处理


    def update_effect(self, effect_type, progress):
         """更新某个艺术化效果的进度"""
         # 例如，更新模糊强度，蒙版透明度等
         # progress 从 0.0 到 1.0
         print(f"TODO: 实现更新艺术化效果进度: {effect_type} with progress {progress}")
         if effect_type == "blur_reveal" and "blur" in self.current_effects:
            # 模糊强度从初始强度 self.current_effects["blur"]["strength"] 降到 0
            initial_strength = self.current_effects["blur"].get("strength", 50) # 获取初始强度
            current_strength = initial_strength * (1.0 - progress)
            # 更新应用的效果参数
            self.current_effects["blur"]["strength"] = current_strength
            # TODO: 重新应用模糊效果并更新 effect_surfaces["blurred"]
            # self._apply_blur_effect(current_strength)


    # def _draw_effects(self):
    #     """绘制当前应用的所有效果"""
    #     # 遍历 self.current_effects，根据效果类型调用对应的绘制逻辑
    #     if "blur" in self.current_effects and "blurred" in self.effect_surfaces:
    #         # 绘制模糊后的 Surface
    #         self.screen.blit(self.effect_surfaces["blurred"], self.image_display_rect.topleft)

    #     # TODO: 绘制其他效果，例如叠加纹理、粒子系统等


    # 坐标转换方法 (将原始图片坐标或相对坐标转换为屏幕坐标)
    # 这些方法对于互动模块将非常重要
    def get_screen_coords_from_original(self, original_x: int, original_y: int) -> tuple[int, int]:
        """将原始图片像素坐标转换为屏幕坐标"""
        if self.original_image_size == (0, 0) or self.image_display_rect.size == (0, 0) or self.original_image is None:
            print("警告：无法转换坐标，原始图片或显示区域无效。")
            return (0, 0) # 无效状态

        original_width, original_height = self.original_image_size
        display_width, display_height = self.image_display_rect.size

        original_aspect = original_width / original_height
        # 使用实际图片显示区域的比例
        display_aspect = display_width / display_height

        # 将屏幕坐标转换为相对于图片显示区域左上角的坐标
        # 首先，找到原始图片在缩放后填充显示区域时的相对位置
        # 这取决于裁剪偏移
        scaled_original_width = 0
        scaled_original_height = 0
        crop_offset_x = 0
        crop_offset_y = 0

        if original_aspect > display_aspect:
             # 原始图片更宽，按显示区域高度缩放，宽度会超出
             scale_factor = display_height / original_height
             scaled_original_width = int(original_width * scale_factor)
             scaled_original_height = display_height
             crop_offset_x = (scaled_original_width - display_width) // 2
             crop_offset_y = 0 # 高度没有裁剪偏移

        else:
             # 原始图片更高或同比例，按显示区域宽度缩放，高度会超出或刚好
             scale_factor = display_width / original_width
             scaled_original_width = display_width
             scaled_original_height = int(original_height * scale_factor)
             crop_offset_x = 0 # 宽度没有裁剪偏移
             crop_offset_y = (scaled_original_height - display_height) // 2


        # 转换原始坐标到相对于缩放后原始图片的坐标
        scaled_x = int(original_x * scale_factor)
        scaled_y = int(original_y * scale_factor)

        # 转换到相对于显示区域左上角的坐标（减去裁剪偏移）
        relative_display_x = scaled_x - crop_offset_x
        relative_display_y = scaled_y - crop_offset_y

        # 转换到屏幕坐标（加上图片显示区域的左上角位置）
        screen_x = self.image_display_rect.left + relative_display_x
        screen_y = self.image_display_rect.top + relative_display_y

        # print(f"Original ({original_x}, {original_y}) -> Scaled ({scaled_x}, {scaled_y}) -> Relative ({relative_display_x}, {relative_display_y}) -> Screen ({screen_x}, {screen_y})") # 调试打印

        return (screen_x, screen_y)


    def get_image_coords(self, screen_x: int, screen_y: int) -> tuple[int, int]:
        """将屏幕像素坐标转换回原始图片像素坐标"""
        if self.original_image_size == (0, 0) or self.image_display_rect.size == (0, 0) or self.original_image is None:
             print("警告：无法转换坐标，原始图片或显示区域无效。")
             return (0, 0) # 无效状态

        original_width, original_height = self.original_image_size
        display_width, display_height = self.image_display_rect.size

        original_aspect = original_width / original_height
        display_aspect = display_width / display_height

        # 将屏幕坐标转换为相对于图片显示区域左上角的坐标
        relative_display_x = screen_x - self.image_display_rect.left
        relative_display_y = screen_y - self.image_display_rect.top

        scaled_original_width = 0
        scaled_original_height = 0
        crop_offset_x = 0
        crop_offset_y = 0
        scale_factor = 1.0

        if original_aspect > display_aspect:
             # 原始图片更宽，按显示区域高缩放，宽度会超出
             scale_factor = display_height / original_height
             scaled_original_width = int(original_width * scale_factor)
             scaled_original_height = display_height
             crop_offset_x = (scaled_original_width - display_width) // 2
             crop_offset_y = 0

        else:
             # 原始图片更高或同比例，按显示区域宽缩放，高度会超出或刚好
             scale_factor = display_width / original_width
             scaled_original_width = display_width
             scaled_original_height = int(original_height * scale_factor)
             crop_offset_x = 0
             crop_offset_y = (scaled_original_height - display_height) // 2


        # 转换相对于显示区域的坐标到相对于缩放后原始图片的坐标（加上裁剪偏移）
        scaled_x = relative_display_x + crop_offset_x
        scaled_y = relative_display_y + crop_offset_y

        # 转换回原始图片坐标（反向缩放）
        original_x = int(scaled_x / scale_factor)
        original_y = int(scaled_y / scale_factor)

        # print(f"Screen ({screen_x}, {screen_y}) -> Relative ({relative_display_x}, {relative_display_y}) -> Scaled ({scaled_x}, {scaled_y}) -> Original ({original_x}, {original_y})") # 调试打印

        return (original_x, original_y)


    # TODO: 其他辅助方法，例如获取某个特效纹理
    # def get_effect_texture(self, effect_id):
    #     return self.effect_textures.get(effect_id)

    # TODO: 实现应用模糊效果的方法
    # def _apply_blur_effect(self, strength):
    #     """使用PIL/Pillow或其他方式对 current_image 应用模糊"""
    #     # 这是一个复杂的功能，需要导入 PIL 或使用其他图像处理库
    #     # Pygame 原生模糊 transform.gaussian_blur 在旧版本可能没有
    #     print(f"TODO: 实现模糊效果应用，强度: {strength}")
    #     pass # 待实现