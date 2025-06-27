import pygame
from config import COLORS

class Button:
    """一个可复用的UI按钮类"""
    def __init__(self, x, y, width, height, text, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = COLORS["button"]
        self.hover_color = COLORS["button_hover"]
        self.text_color = COLORS["text"]
        self.is_hovered = False

    def draw(self, screen):
        # 根据是否悬停选择颜色
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=5)
        
        # 绘制文本
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def update(self, mouse_pos):
        """（可选）更新悬停状态，暂未在主循环中调用"""
        if self.rect.collidepoint(mouse_pos):
            self.is_hovered = True
        else:
            self.is_hovered = False