# ui_elements.py
# 存放可重用的UI元素类，如按钮、提示信息等

import pygame
import settings
import time # 用于计时

# TODO: Button 类尚未实现，如果图库图标使用Button，需要在这里实现完整的Button类
# class Button(pygame.sprite.Sprite):
#     def __init__(self, image, position, anchor='topleft'):
#         super().__init__()
#         self.image = image
#         self.rect = self.image.get_rect(**{anchor: position})
#         self._callback = None # 点击事件回调函数

#     def set_callback(self, callback):
#         self._callback = callback

#     def handle_event(self, event):
#         if event.type == pygame.MOUSEBUTTONDOWN:
#             if event.button == 1 and self.rect.collidepoint(event.pos):
#                 if self._callback:
#                     self._callback() # 执行回调函数
#                 return True # 事件被消耗
#         return False # 事件未被处理

#     def draw(self, surface):
#         surface.blit(self.image, self.rect)

class PopupText(pygame.sprite.Sprite):
    def __init__(self, text, color, duration_seconds, position=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2)):
        """
        初始化一个弹出文字提示

        Args:
            text (str): 要显示的文字
            color (tuple): 文字颜色 (RGB)
            duration_seconds (float): 文字显示持续时间 (秒)
            position (tuple): 文字显示的中心位置 (像素)
        """
        super().__init__()
        # TODO: 字体初始化可以放在 Game 类中并传递进来，避免重复加载
        self.font = pygame.font.Font(None, 48) # 示例字体和大小
        self.text_surface = None # 初始时没有文字表面
        self.rect = None # 初始时没有Rect

        self.duration = duration_seconds
        self.start_time = 0 # 记录开始显示的时间戳
        self.is_active = False # 是否正在显示


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
         self.font = pygame.font.Font(None, 48) # 确保字体已加载 (可以优化到初始化或Game类中)
         self.text_surface = self.font.render(text, True, color)
         self.rect = self.text_surface.get_rect(center=position)

         self.duration = duration_seconds
         self.start_time = time.time() # 记录当前时间作为开始时间
         self.is_active = True # 激活显示
         print(f"显示提示: \"{text}\"") # 调试信息