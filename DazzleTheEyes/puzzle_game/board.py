# board.py
# 管理拼盘的状态、碎片布局、交换、完成检测及动态填充

import pygame
import settings
import random # 用于随机打乱碎片
from piece import Piece # 导入Piece类
# from image_manager import ImageManager # 后续需要导入 ImageManager

class Board:
    def __init__(self, image_manager):
        """
        初始化拼盘

        Args:
            image_manager (ImageManager): 图像管理器实例
        """
        self.image_manager = image_manager
        # 存储拼盘中的碎片，使用二维列表表示物理网格 (16x9)
        # 列表中的元素将是 Piece 对象或 None (表示空槽位)
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]

        # 获取初始碎片并填充到拼盘
        self.fill_initial_pieces()

        # 选中的碎片 (用于点击交换)
        self.selected_piece = None

        # 正在拖拽的碎片 (用于拖拽交换)
        self.dragging_piece = None
        self.drag_start_grid_pos = None # 拖拽开始时碎片所在的网格位置
        self.last_processed_grid_pos = None # 拖拽过程中上一次处理的网格位置

        # 用于管理所有 Piece Sprite 的 Group (如果需要)
        # self.all_pieces_group = pygame.sprite.Group()


    def fill_initial_pieces(self):
        """根据settings填充初始碎片并随机打乱"""
        initial_pieces = self.image_manager.get_initial_pieces_for_board()

        # 确保获取到的碎片数量符合预期
        if len(initial_pieces) != settings.EXPECTED_INITIAL_PIECE_COUNT:
             print(f"错误: 获取的初始碎片数量 {len(initial_pieces)} 与预期 {settings.EXPECTED_INITIAL_PIECE_COUNT} 不符，无法填充拼盘。")
             return # 碎片数量不匹配，停止填充

        print(f"获取了 {len(initial_pieces)} 个初始碎片，开始填充拼盘。") # 调试信息

        # 生成所有网格位置的列表
        all_grid_positions = [(r, c) for r in range(settings.BOARD_ROWS) for c in range(settings.BOARD_COLS)]
        # 随机打乱位置列表
        random.shuffle(all_grid_positions)

        # 将每个碎片放置到一个随机的网格位置上
        for i, piece in enumerate(initial_pieces):
            # 获取一个随机的网格位置
            r, c = all_grid_positions[i]

            # 将碎片放到网格中
            self.grid[r][c] = piece
            # 更新碎片自身的当前网格位置和屏幕位置
            piece.set_grid_position(r, c)

            # self.all_pieces_group.add(piece) # 如果使用Sprite Group


    def swap_pieces(self, pos1_grid, pos2_grid):
        """
        交换两个网格位置上的碎片

        Args:
            pos1_grid (tuple): 第一个碎片的网格坐标 (row, col)
            pos2_grid (tuple): 第二个碎片的网格坐标 (row, col)
        """
        r1, c1 = pos1_grid
        r2, c2 = pos2_grid

        # 确保坐标有效且在板子上
        if not (0 <= r1 < settings.BOARD_ROWS and 0 <= c1 < settings.BOARD_COLS and
                0 <= r2 < settings.BOARD_ROWS and 0 <= c2 < settings.BOARD_COLS):
            print(f"警告: 无效的网格位置 ({r1},{c1}) 或 ({r2},{c2})，无法交换。")
            return

        piece1 = self.grid[r1][c1]
        piece2 = self.grid[r2][c2]

        # 在网格中交换
        self.grid[r1][c1] = piece2
        self.grid[r2][c2] = piece1

        # 更新碎片自身的网格位置属性
        if piece1:
            piece1.set_grid_position(r2, c2)
        if piece2:
            piece2.set_grid_position(r1, c1)

        print(f"交换了碎片位置: ({r1},{c1}) 与 ({r2},{c2})") # 调试信息


    # def handle_click(self, grid_pos): ... (从骨架复制过来，暂时未实现功能)
    # def start_drag(self, piece, grid_pos): ...
    # def process_drag_motion(self, current_mouse_grid_pos): ...
    # def stop_drag(self): ...
    # def check_and_process_completion(self): ...
    # def check_completion(self): ...
    # def remove_completed_pieces(self, completed_image_id): ...
    # def fall_down_pieces(self): ...
    # def fill_new_pieces(self): ...


    def draw(self, surface):
        """在指定的surface上绘制拼盘中的所有碎片"""
        # 遍历 self.grid，对于每个非 None 的 Piece 对象，调用其 draw 方法
        for r in range(settings.BOARD_ROWS):
            for c in range(settings.BOARD_COLS):
                piece = self.grid[r][c]
                if piece:
                    piece.draw(surface)

        # TODO: 绘制选中碎片的特殊效果 (如果 self.selected_piece 不是 None)
        # TODO: 绘制正在拖拽碎片的特殊效果 (如果 self.dragging_piece 不是 None)

    # def update(self, dt):
    #      """更新Board的状态，例如处理碎片下落动画"""
    #      # if self.all_pieces_group: # 如果使用Sprite Group
    #      #      self.all_pieces_group.update(dt)
    #      pass # TODO: 实现Board的update逻辑，特别是碎片下落