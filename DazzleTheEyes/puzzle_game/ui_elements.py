# ui_elements.py
# 存放可重用的UI元素类，如按钮、提示信息等

import pygame
import settings
import time # 用于计时

class Button(pygame.sprite.Sprite):
    def __init__(self, image_path, position, anchor='topleft', callback=None):
        """
        初始化一个按钮。

        Args:
            image_path (str): 按钮图片的路径。
            position (tuple): 按钮的绘制位置 (例如 (x, y) 或 (center_x, center_y))。
            anchor (str): 按钮位置的锚点，如 'topleft', 'center' 等，与 rect 的 get_rect 参数对应。
            callback (function): 点击按钮时要执行的回调函数。
        """
        super().__init__()

        try:
            self.image = pygame.image.load(image_path).convert_alpha()
        except pygame.error as e:
            print(f"警告: 无法加载按钮图片 {image_path}: {e}")
            self.image = pygame.Surface((50, 50), pygame.SRCALPHA) # 使用一个空白Surface作为占位符
            self.image.fill((255, 0, 0, 100)) # 填充红色半透明，表示加载失败

        self.rect = self.image.get_rect(**{anchor: position})
        self._callback = callback
        self._is_hovered = False # 鼠标是否悬停，用于可能的视觉反馈 (未实现)

    def handle_event(self, event):
        """处理按钮相关的事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                # TODO: 添加按钮按下音效 (可选)
                if self._callback:
                    self._callback() # 执行回调函数
                return True # 事件被消耗
        # elif event.type == pygame.MOUSEMOTION:
        #     # 检查鼠标是否悬停
        #     is_currently_hovered = self.rect.collidepoint(event.pos)
        #     if is_currently_hovered != self._is_hovered:
        #         self._is_hovered = is_currently_hovered
        #         # TODO: 切换按钮悬停状态的图像 (可选)

        return False # 事件未被处理

    def draw(self, surface):
        """绘制按钮"""
        surface.blit(self.image, self.rect)


class PopupText(pygame.sprite.Sprite):
    def __init__(self, game_instance):
        """
        初始化一个弹出文字提示管理器。

        Args:
            game_instance (Game): Game实例，用于访问字体等全局资源。
        """
        super().__init__()
        self.game = game_instance # <--- 添加这一行
        # 使用 Game 实例传递的字体，避免重复创建
        self.font = game_instance.font_tip # 假设Game实例有一个 font_tip 属性
        self.text_surface = None
        self.rect = None

        self.duration = 0
        self.start_time = 0
        self.is_active = False


    def update(self, dt):
        """更新提示状态，检查是否需要消失"""
        if self.is_active:
            if time.time() - self.start_time > self.duration:
                self.is_active = False # 超时，停止显示
                self.text_surface = None # 清除文字表面


    def draw(self, surface):
        """绘制提示文字"""
        if self.is_active and self.text_surface and self.rect:
            # 可以实现淡入淡出效果，这里只做简单的显示/隐藏
            # TODO: 实现淡入淡出动画 (可选)
            surface.blit(self.text_surface, self.rect)


    def show(self, text, color=settings.TIP_TEXT_COLOR, duration_seconds=settings.TIP_DISPLAY_DURATION, position=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2)):
         """
         更新提示内容并激活显示。

         Args:
            text (str): 要显示的文字
            color (tuple): 文字颜色 (RGB)。默认为 settings.TIP_TEXT_COLOR
            duration_seconds (float): 文字显示持续时间 (秒)。默认为 settings.TIP_DISPLAY_DURATION
            position (tuple): 文字显示的中心位置 (像素)。默认为屏幕中心
         """
         # 确保字体已加载 (这里直接使用传入的字体，应该没问题)
        #  self.font = self.game.font_tip # 确保使用Game实例中的字体
        #  self.text_surface = self.font.render(text, True, color)

         # 使用 self.game 中已经初始化好的字体来渲染文本
         if self.game and hasattr(self.game, 'font_tip') and self.game.font_tip: # 安全检查
             self.text_surface = self.game.font_tip.render(text, True, color)
         else:
              # 如果 Game 实例或字体有问题，回退到默认字体或跳过渲染
              print("警告: 无法获取 Game 实例或字体，使用默认字体渲染提示文本。")
              font_fallback = pygame.font.Font(None, settings.TIP_FONT_SIZE)
              self.text_surface = font_fallback.render(text, True, color)

         self.rect = self.text_surface.get_rect(center=position)

         self.duration = duration_seconds
         self.start_time = time.time() # 记录当前时间作为开始时间
         self.is_active = True # 激活显示
         print(f"显示提示: \"{text}\"") # 调试信息