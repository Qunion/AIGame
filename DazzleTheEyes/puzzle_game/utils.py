# utils.py
# 存放通用的工具函数

import settings

def screen_to_grid(pos):
    """
    将屏幕像素坐标转换为拼盘的网格坐标 (行, 列)

    Args:
        pos (tuple): 屏幕上的像素坐标 (x, y)

    Returns:
        tuple: 对应的网格坐标 (row, col)，如果超出拼盘范围，可以添加检查
    """
    x, y = pos
    # 减去拼盘偏移量
    board_x = x - settings.BOARD_OFFSET_X
    board_y = y - settings.BOARD_OFFSET_Y

    # 计算网格索引 (使用int向下取整)
    col = int(board_x // settings.PIECE_SIZE)
    row = int(board_y // settings.PIECE_SIZE)

    # TODO: 可以添加越界检查，返回 -1,-1 或 None 表示不在板子上
    # if not (0 <= row < settings.BOARD_ROWS and 0 <= col < settings.BOARD_COLS):
    #     return (-1, -1) # 或者 None

    return (row, col)

# 其他可能的工具函数：
# def grid_to_screen(row, col): ... 将网格坐标转换为屏幕像素坐标
# def grayscale_surface(surface): ... 将一个surface灰度化
# def center_rect(rect_to_center, parent_rect): ... 将一个rect居中于另一个rect