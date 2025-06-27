import pygame
from config import COLORS, SCREEN_WIDTH

class HUD:
    """负责绘制战斗界面的信息显示（Heads-Up Display）"""

    def __init__(self, font):
        self.font = font

    def draw(self, screen, player_machine, ai_machine):
        """绘制所有HUD元素"""
        # 绘制玩家血条
        if player_machine:
            self._draw_hp_bar(screen, 20, 20, 400, 30, "玩家", player_machine, COLORS["player_hp"])
        
        # 绘制AI血条
        if ai_machine:
            self._draw_hp_bar(screen, SCREEN_WIDTH - 420, 20, 400, 30, "AI对手", ai_machine, COLORS["ai_hp"])

    def _draw_hp_bar(self, screen, x, y, width, height, label, machine, color):
        # 计算HP比例
        ratio = 0
        core_part = machine.get_core_part()
        if core_part:
            ratio = core_part.hp / core_part.definition['hp']

        # 绘制背景
        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, COLORS["hp_bg"], bg_rect, border_radius=5)

        # 绘制当前血量
        hp_width = int(width * ratio)
        hp_rect = pygame.Rect(x, y, hp_width, height)
        pygame.draw.rect(screen, color, hp_rect, border_radius=5)
        
        # 绘制标签文本
        text_surface = self.font.render(f"{label}: {int(ratio*100)}%", True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=bg_rect.center)
        screen.blit(text_surface, text_rect)