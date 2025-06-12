# FILENAME: utils.py

import pygame
import config

_font_cache = {}
_found_font_name = None
_searched_for_font = False

def get_font(size):
    global _found_font_name, _searched_for_font
    size = max(1, int(size))
    if not _searched_for_font:
        for name in config.FONT_NAMES:
            if name:
                try: pygame.font.SysFont(name, 12); _found_font_name = name; print(f"成功找到并使用字体: {_found_font_name}"); break
                except pygame.error: continue
        _searched_for_font = True
        if not _found_font_name: print("警告: 未找到指定字体，使用默认字体。")

    font_key = (size, _found_font_name)
    if font_key not in _font_cache:
        _font_cache[font_key] = pygame.font.SysFont(_found_font_name, size) if _found_font_name else pygame.font.Font(None, size)
    return _font_cache[font_key]

def render_text_ui(surface, text, rect, color, font_size=16, center=None):
    """
    MODIFIED: 允许传入一个可选的 center 参数来覆盖 rect.center。
    """
    font = get_font(font_size)
    text_surface = font.render(text, True, color)
    target_center = center if center else rect.center
    text_pos = text_surface.get_rect(center=target_center)
    surface.blit(text_surface, text_pos)

# --- 以下函数保持不变 ---
def render_text_in_circle(surface, text, center, radius, color):
    padding = 0.85; text_rect_size = radius * 2 * padding
    text_rect = pygame.Rect(0, 0, text_rect_size, text_rect_size); text_rect.center = center
    font_size = int(radius)
    while font_size > config.MIN_FONT_SIZE:
        font = get_font(font_size); lines = _wrap_text_for_circle(text, font, text_rect.width)
        total_height = len(lines) * font.get_linesize()
        if total_height > text_rect.height: font_size -= 1; continue
        is_within_circle = True; y_check = text_rect.top + (text_rect.height - total_height) / 2
        for line in lines:
            line_width = font.size(line)[0]; dy = abs(y_check + font.get_linesize()/2 - center[1])
            allowed_width = 2 * (radius**2 - dy**2)**0.5 if radius > dy else 0
            if line_width > allowed_width * padding: is_within_circle = False; break
            y_check += font.get_linesize()
        if is_within_circle: break
        else: font_size -= 1
    else:
        font_size = config.MIN_FONT_SIZE; font = get_font(font_size); lines = _wrap_text_for_circle(text, font, text_rect.width)
    total_height = len(lines) * font.get_linesize(); y_start = center[1] - total_height / 2
    for i, line in enumerate(lines):
        line_surface = font.render(line, True, color); x_pos = center[0] - line_surface.get_width() / 2
        y_pos = y_start + i * font.get_linesize(); surface.blit(line_surface, (x_pos, y_pos))

def _wrap_text_for_circle(text, font, max_width):
    lines = []; current_line = ""
    for char in text:
        if font.size(current_line + char)[0] < max_width: current_line += char
        else: lines.append(current_line); current_line = char
    lines.append(current_line)
    return lines

def draw_arrow(surface, color, start, end, width=3):
    if (end - start).length() < 1: return
    pygame.draw.line(surface, color, start, end, width)
    if (end - start).length() > 10:
        angle = (start - end).angle_to(pygame.Vector2(1, 0))
        p1 = end + pygame.Vector2(10, 0).rotate(angle - 30); p2 = end + pygame.Vector2(10, 0).rotate(angle + 30)
        pygame.draw.polygon(surface, color, [end, p1, p2])