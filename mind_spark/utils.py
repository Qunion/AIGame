# FILENAME: utils.py
#
# 提供辅助函数，如文本渲染

import pygame
import config

# 缓存字体对象和已找到的字体名称以提高性能
_font_cache = {}
_found_font_name = None
_searched_for_font = False # 添加一个标志位，确保字体搜索只执行一次

def get_font(size):
    """根据大小获取或创建字体对象，并智能选择可用字体"""
    global _found_font_name, _searched_for_font
    size = int(size)

    # --- 修复逻辑 ---
    # 如果还没有搜索过字体，则执行一次搜索
    if not _searched_for_font:
        for name in config.FONT_NAMES:
            if name:  # 如果字体名不是None
                try:
                    # 使用 SysFont 来测试字体是否存在
                    pygame.font.SysFont(name, 12)
                    _found_font_name = name
                    print(f"成功找到并使用字体: {_found_font_name}")
                    break  # 找到后立刻退出循环
                except pygame.error:
                    # 字体未找到，继续尝试下一个
                    continue
        
        _searched_for_font = True # 标记为已搜索过
        if not _found_font_name:
            print("警告: 配置文件中的所有字体都未在系统中找到，将使用Pygame默认字体。")

    # 使用缓存键（字号, 字体名）来获取或创建字体对象
    font_key = (size, _found_font_name)
    if font_key not in _font_cache:
        # 如果找到了系统字体，则使用 SysFont
        if _found_font_name:
            _font_cache[font_key] = pygame.font.SysFont(_found_font_name, size)
        # 否则，使用 Pygame 的默认字体
        else:
            _font_cache[font_key] = pygame.font.Font(None, size)
            
    return _font_cache[font_key]

def render_text(surface, text, position, font_size, color=config.TEXT_COLOR):
    """在指定位置渲染居中的单行文本"""
    font = get_font(font_size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=position)
    surface.blit(text_surface, text_rect)

def calculate_font_size(radius, text):
    """根据神经元半径和文本长度动态计算字体大小"""
    if not text:
        return config.MIN_FONT_SIZE

    max_h = radius * 2 * config.MAX_FONT_SIZE_PROPORTION
    font_size = max_h / (1 + len(text) * 0.1 * config.FONT_LENGTH_ADJUST_FACTOR)

    return max(config.MIN_FONT_SIZE, int(font_size))

def draw_text_in_circle(surface, text, center, radius):
    """在圆形内部渲染文本，并处理换行（简化版）"""
    font_size = calculate_font_size(radius, text)
    font = get_font(font_size)

    max_width = radius * 2 * 0.8
    if font.size(text)[0] > max_width:
        original_text = text
        text = ""
        for char in original_text:
            if font.size(text + char + '...')[0] > max_width:
                break
            text += char
        text += '...'

    render_text(surface, text, center, font_size)

def draw_arrow(surface, color, start, end, width=3):
    """绘制一个箭头"""
    if (end - start).length() < 1: return # 避免零向量错误
    pygame.draw.line(surface, color, start, end, width)
    if (end - start).length() > 10:
        angle = (start - end).angle_to(pygame.Vector2(1, 0))
        p1 = end + pygame.Vector2(10, 0).rotate(angle - 30)
        p2 = end + pygame.Vector2(10, 0).rotate(angle + 30)
        pygame.draw.polygon(surface, color, [end, p1, p2])