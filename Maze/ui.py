import pygame
from settings import *

def draw_text(surface, text, size, x, y, color=WHITE, font_name=FONT_NAME, align="topleft"):
    font = pygame.font.Font(font_name, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "topleft":
        text_rect.topleft = (x, y)
    elif align == "topright":
        text_rect.topright = (x, y)
    elif align == "midtop":
        text_rect.midtop = (x, y)
    elif align == "center":
        text_rect.center = (x, y)
    elif align == "midbottom":
        text_rect.midbottom = (x, y)
    elif align == "bottomleft":
        text_rect.bottomleft = (x, y)
    elif align == "bottomright":
        text_rect.bottomright = (x, y)
    surface.blit(text_surface, text_rect)


def draw_player_hud(surface, player, assets):
    # --- Hunger ---
    hunger_icon = assets.get_image('ui_hunger')
    icon_rect = hunger_icon.get_rect()
    # Position left of center top
    icon_rect.top = UI_PADDING
    icon_rect.right = WIDTH // 2 - UI_PADDING
    surface.blit(hunger_icon, icon_rect)
    # Draw hunger text/bar next to it? Or just use the icon as indicator?
    # Let's add text value for clarity
    draw_text(surface, f"{int(player.hunger)}%", UI_FONT_SIZE,
              icon_rect.left - UI_PADDING, icon_rect.centery,
              color=WHITE, align="topright") # Show % next to icon

    # --- Matches ---
    match_icon = assets.get_image('ui_match')
    num_matches = player.get_total_match_count()
    current_burn_percent = player.get_current_match_burn_percentage()
    current_match_index = player.current_match_index # Index from the right (0 is rightmost burning)

    # Calculate starting x position for the leftmost match icon
    total_match_width = num_matches * UI_MATCH_WIDTH + max(0, num_matches - 1) * UI_MATCH_SPACING
    start_x = WIDTH // 2 + UI_PADDING

    for i in range(num_matches):
        match_rect = match_icon.get_rect()
        match_rect.left = start_x + i * (UI_MATCH_WIDTH + UI_MATCH_SPACING)
        match_rect.top = UI_PADDING

        # Draw base match icon
        surface.blit(match_icon, match_rect)

        # Draw progress bar overlay for the currently burning match
        # The burning match is the 'rightmost' one logically, which is index 'player.current_match_index' in the list.
        # The list represents matches from left (newest) to right (oldest/burning).
        # So, the match at index player.current_match_index needs the progress bar.
        if i == player.current_match_index:
             progress_height = int(match_rect.height * current_burn_percent)
             progress_rect_fg = pygame.Rect(match_rect.left, match_rect.top,
                                            match_rect.width, progress_height)
             progress_rect_bg = pygame.Rect(match_rect.left, match_rect.top + progress_height,
                                            match_rect.width, match_rect.height - progress_height)

             pygame.draw.rect(surface, UI_MATCH_PROGRESS_COLOR_FG, progress_rect_fg)
             pygame.draw.rect(surface, UI_MATCH_PROGRESS_COLOR_BG, progress_rect_bg)

    # --- Weapon Indicator (Optional) ---
    if player.inventory['weapons']:
         weapon = player.inventory['weapons'][0]
         weapon_key = 'weapon_sword_broken' if weapon.weapon_type == 'broken' else 'weapon_sword_good'
         weapon_img = assets.get_image(weapon_key)
         if weapon_img:
              # Scale down for HUD display
              hud_weapon_img = pygame.transform.scale(weapon_img, (UI_MATCH_WIDTH * 2, UI_MATCH_HEIGHT // 2))
              hud_weapon_rect = hud_weapon_img.get_rect()
              hud_weapon_rect.bottomright = (WIDTH - UI_PADDING, HEIGHT - UI_PADDING)
              surface.blit(hud_weapon_img, hud_weapon_rect)
              draw_text(surface, f"x{weapon.uses}", UI_FONT_SIZE,
                        hud_weapon_rect.left - 5, hud_weapon_rect.centery, align="topright")


def draw_game_over_screen(surface, reason, assets):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180)) # Semi-transparent black overlay
    surface.blit(overlay, (0, 0))
    draw_text(surface, "游戏结束", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 4, color=RED, align="center")
    draw_text(surface, reason, MESSAGE_FONT_SIZE, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
    draw_text(surface, "按 R 重新开始, 按 Q 退出", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")

def draw_win_screen(surface, assets):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 100, 0, 180)) # Semi-transparent green overlay
    surface.blit(overlay, (0, 0))
    draw_text(surface, "你成功了!", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 4, color=YELLOW, align="center")
    draw_text(surface, "你走出了饥荒迷宫!", MESSAGE_FONT_SIZE, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
    draw_text(surface, "按 R 重新开始, 按 Q 退出", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")

def draw_pause_screen(surface, assets):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((50, 50, 50, 180)) # Semi-transparent grey overlay
    surface.blit(overlay, (0, 0))
    draw_text(surface, "游戏暂停", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
    draw_text(surface, "按 空格键 继续", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")