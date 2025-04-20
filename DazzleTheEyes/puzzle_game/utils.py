# utils.py
# 存放通用的工具函数

import pygame
import settings

def screen_to_grid(pos):
    """
    将屏幕像素坐标转换为拼盘的网格坐标 (行, 列)

    Args:
        pos (tuple): 屏幕上的像素坐标 (x, y)

    Returns:
        tuple: 对应的网格坐标 (row, col)。如果超出拼盘范围，返回 (-1, -1)。
    """
    x, y = pos
    # 减去拼盘偏移量
    board_x = x - settings.BOARD_OFFSET_X
    board_y = y - settings.BOARD_OFFSET_Y

    # 计算网格索引 (使用int向下取整)
    col = int(board_x // settings.PIECE_SIZE)
    row = int(board_y // settings.PIECE_SIZE)

    # 添加越界检查
    if not (0 <= row < settings.BOARD_ROWS and 0 <= col < settings.BOARD_COLS):
        return (-1, -1) # 表示不在板子上

    return (row, col)

def grid_to_screen(row, col):
    """
    将拼盘的网格坐标 (行, 列) 转换为屏幕像素坐标 (x, y)，返回碎片左上角位置。

    Args:
        row (int): 网格行索引
        col (int): 网格列索引

    Returns:
        tuple: 屏幕像素坐标 (x, y)。如果网格坐标无效，可能返回无效值。
    """
    x = settings.BOARD_OFFSET_X + col * settings.PIECE_SIZE
    y = settings.BOARD_OFFSET_Y + row * settings.PIECE_SIZE
    return (x, y)

def grayscale_surface(surface):
    """
    将一个 Pygame Surface 灰度化。

    Args:
        surface (pygame.Surface): 需要灰度化的 Surface。

    Returns:
        pygame.Surface: 灰度化后的新 Surface。
    """
    # 创建一个新的 Surface，确保有 alpha 通道
    gray_surface = pygame.Surface(surface.get_size(), depth=surface.get_bitsize())
    gray_surface.fill((0, 0, 0, 0)) # 填充透明或黑色，取决于你的需求
    gray_surface = gray_surface.convert_alpha() # 确保透明度

    # 将原 Surface 绘制到新 Surface 上
    gray_surface.blit(surface, (0, 0))

    # 获取像素数组进行处理
    pixel_array = pygame.PixelArray(gray_surface)

    for x in range(surface.get_width()):
        for y in range(surface.get_height()):
            # 获取颜色 (带 alpha)
            color = gray_surface.get_at((x, y))
            # 提取 RGB
            r, g, b = color[:3]
            # 计算灰度值 (常见的加权平均法)
            gray = int(0.2989 * r + 0.5870 * g + 0.1140 * b)
            # 设置像素颜色 (保持 alpha 通道)
            pixel_array[x, y] = (gray, gray, gray, color[3] if len(color) > 3 else 255) # 兼容没有alpha的情况

    # 完成像素数组操作，返回 Surface
    pixel_array.close()
    return gray_surface

def center_rect_in_parent(rect_to_center, parent_rect):
    """
    将一个 Rect 居中于另一个 Rect。

    Args:
        rect_to_center (pygame.Rect): 需要居中的 Rect。
        parent_rect (pygame.Rect): 父级 Rect。

    Returns:
        pygame.Rect: 居中后的 Rect (会修改原对象并返回)。
    """
    rect_to_center.center = parent_rect.center
    return rect_to_center