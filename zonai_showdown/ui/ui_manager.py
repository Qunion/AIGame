import pygame
import time
from .button import Button
from config import *
from .hud import HUD

class UIManager:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("SimHei", 24)
        self.title_font = pygame.font.SysFont("SimHei", 48)
        self.feedback_font = pygame.font.SysFont("SimHei", 32)
        
        self.build_area_rect = pygame.Rect(0, 0, SCREEN_WIDTH - 250, SCREEN_HEIGHT)
        self.shop_rect = pygame.Rect(SCREEN_WIDTH - 250, 0, 250, SCREEN_HEIGHT)

        self.buttons = {
            "start_combat": Button(self.shop_rect.x + 25, 550, 200, 50, "开始战斗", self.font),
            "reset_assembly": Button(self.shop_rect.x + 25, 620, 200, 50, "返回设计", self.font),
        }
        self.device_buttons = self._create_device_buttons()
        self.hud = HUD(self.font)
        self.buttons["reset_assembly"].visible = False
        
        # 反馈信息相关
        self.feedback_text = ""
        self.feedback_end_time = 0

    def show_feedback(self, text, duration_seconds):
        """显示一条临时反馈信息"""
        self.feedback_text = text
        self.feedback_end_time = time.time() + duration_seconds

    def _create_device_buttons(self):
        buttons = {}; y_offset = 50
        order = ["钢条"] + [name for name in DEVICE_DEFINITIONS if name != "钢条"]
        for name in order:
            buttons[name] = Button(self.shop_rect.x + 25, y_offset, 200, 40, name, self.font)
            y_offset += 50
        return buttons

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1: return None
        for name, button in self.buttons.items():
            if button.visible and button.is_clicked(event.pos): return name
        if self.game.game_state == GameState.ASSEMBLY:
            for name, button in self.device_buttons.items():
                if button.is_clicked(event.pos): return {"select_device": name}
        return None

    def draw(self, screen, game):
        pygame.draw.rect(screen, COLORS["ui_background"], self.shop_rect)
        if game.game_state == GameState.ASSEMBLY: self._draw_assembly_ui(screen)
        elif game.game_state == GameState.COMBAT: self.hud.draw(screen, game.player_machine, game.ai_machine)
        elif game.game_state == GameState.END_SCREEN: self._draw_end_screen(screen, game.winner)
        self._draw_feedback(screen)
    
    def _draw_feedback(self, screen):
        """绘制反馈信息"""
        if time.time() < self.feedback_end_time:
            text_surface = self.feedback_font.render(self.feedback_text, True, (255, 200, 0))
            # 显示在建造区域中央
            text_rect = text_surface.get_rect(center=(self.build_area_rect.centerx, 50))
            screen.blit(text_surface, text_rect)

    def _draw_assembly_ui(self, screen):
        self.buttons["start_combat"].visible = True
        self.buttons["reset_assembly"].visible = False
        title = self.font.render("装置商店", True, COLORS["text"])
        screen.blit(title, (self.shop_rect.x + 60, 15))
        for button in self.device_buttons.values(): button.draw(screen)
        self.buttons["start_combat"].draw(screen)

    def _draw_end_screen(self, screen, winner):
        self.buttons["start_combat"].visible = False; self.buttons["reset_assembly"].visible = True
        self.buttons["reset_assembly"].rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100)
        text, color = ("胜利！", (0,255,150)) if winner == "player" else (("失败", (255,0,100)) if winner == "ai" else ("平局", (150,150,150)))
        text_surface = self.title_font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
        screen.blit(text_surface, text_rect); self.buttons["reset_assembly"].draw(screen)

    def draw_grid(self, screen):
        for x in range(0, self.build_area_rect.width, 50): pygame.draw.line(screen, COLORS["grid"], (x, 0), (x, self.build_area_rect.height))
        for y in range(0, self.build_area_rect.height, 50): pygame.draw.line(screen, COLORS["grid"], (0, y), (self.build_area_rect.width, y))

    def is_in_build_area(self, pos): return self.build_area_rect.collidepoint(pos)

    def draw_ghost_device(self, screen, device_type, angle_deg, screen_pos):
        if not self.is_in_build_area(screen_pos): return
        definition = DEVICE_DEFINITIONS[device_type]; color = (*definition['color'], 128)
        info = definition['shape_info']
        if info['type'] == 'box':
            w, h = info['size']; surface = pygame.Surface((w,h), pygame.SRCALPHA); surface.fill(color)
            rotated_surface = pygame.transform.rotate(surface, angle_deg)
            rect = rotated_surface.get_rect(center=screen_pos)
            screen.blit(rotated_surface, rect)
        elif info['type'] == 'circle':
            radius = info['radius']; surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(surface, color, (radius, radius), radius)
            screen.blit(surface, (screen_pos[0] - radius, screen_pos[1] - radius))