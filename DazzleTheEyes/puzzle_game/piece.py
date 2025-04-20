# piece.py
# 定义表示单个碎片的类

import pygame
import settings
import utils # 导入utils用于坐标转换


class Piece(pygame.sprite.Sprite):
    def __init__(self, image_surface, original_image_id, original_row, original_col, initial_grid_row=-1, initial_grid_col=-1):
        """
        初始化一个碎片对象

        Args:
            image_surface (pygame.Surface): 碎片的图像表面 (期望尺寸为 settings.PIECE_SIZE x settings.PIECE_SIZE)
            original_image_id (int): 碎片所属的原始图片ID (如 1 代表 image_1)
            original_row (int): 碎片在原始图片逻辑网格中的行索引 (0 - settings.IMAGE_LOGIC_ROWS-1)
            original_col (int): 碎片在原始图片逻辑网格中的列索引 (0 - settings.IMAGE_LOGIC_COLS-1)
            initial_grid_row (int): 碎片在拼盘物理网格中的初始行索引 (0 - settings.BOARD_ROWS-1)。-1 表示待分配。
            initial_grid_col (int): 碎片在拼盘物理网格中的初始列索引 (0 - settings.BOARD_COLS-1)。-1 表示待分配。
        """
        super().__init__() # 如果继承Sprite需要调用父类初始化

        # 确保传入的 Surface 尺寸正确
        if image_surface.get_size() != (settings.PIECE_SIZE, settings.PIECE_SIZE):
             print(f"警告: 碎片 image_surface 尺寸不正确 {image_surface.get_size()}，应为 {settings.PIECE_SIZE}x{settings.PIECE_SIZE}。尝试缩放。")
             try:
                 self.image = pygame.transform.scale(image_surface, (settings.PIECE_SIZE, settings.PIECE_SIZE))
             except pygame.error as e:
                 print(f"错误: 碎片 Surface 缩放失败: {e}. 使用原始 Surface (可能尺寸错误)。")
                 self.image = image_surface # 缩放失败，使用原始 Surface
        else:
             self.image = image_surface


        # 存储碎片的原始信息，用于判断是否归位
        self.original_image_id = original_image_id
        self.original_row = original_row
        self.original_col = original_col

        # 存储碎片当前在拼盘中的网格位置
        self.current_grid_row = initial_grid_row
        self.current_grid_col = initial_grid_col

        # 初始化屏幕位置，如果在初始化时已知网格位置
        if initial_grid_row != -1 and initial_grid_col != -1:
             self.rect = self.image.get_rect()
             self.set_grid_position(initial_grid_row, initial_grid_col, animate=False) # 初始位置不动画
        else:
             # 如果初始位置未知，先创建一个位于屏幕外的 Rect，后续set_grid_position会设置
             self.rect = pygame.Rect(-settings.PIECE_SIZE, -settings.PIECE_SIZE, settings.PIECE_SIZE, settings.PIECE_SIZE)


        # 动画相关属性 (当下落时可能需要)
        self.is_falling = False
        self.fall_target_y = -1 # 碎片下落的目标屏幕Y坐标


    def draw(self, surface):
        """在指定的surface上绘制碎片"""
        surface.blit(self.image, self.rect)


    def update(self, dt):
        """更新碎片状态 (如下落动画)"""
        if self.is_falling:
            # 根据下落速度和时间差计算移动距离
            move_distance = settings.FALL_SPEED_PIXELS_PER_SECOND * dt
            new_y = self.rect.y + move_distance

            # 检查是否到达目标位置或超过
            if (settings.FALL_SPEED_PIXELS_PER_SECOND > 0 and new_y >= self.fall_target_y) or \
               (settings.FALL_SPEED_PIXELS_PER_SECOND < 0 and new_y <= self.fall_target_y) or \
               settings.FALL_SPEED_PIXELS_PER_SECOND == 0: # 如果速度为0或方向错误，也停止
                # 到达目标位置或超过，停止下落，精确设置位置
                self.rect.y = self.fall_target_y
                self.is_falling = False
                # TODO: 可能需要通知 Board 碎片已到达新位置 (或者 Board 在 update 中检查 is_falling)
            else:
                # 继续下落
                self.rect.y = new_y


    def set_grid_position(self, row, col, animate=False):
        """
        设置碎片在拼盘中的新网格位置并更新其屏幕坐标。
        可以选择是否启用下落动画。

        Args:
            row (int): 目标网格行
            col (int): 目标网格列
            animate (bool): 是否以动画方式移动到新位置 (目前仅支持向下动画)
        """
        self.current_grid_row = row
        self.current_grid_col = col

        target_x, target_y = utils.grid_to_screen(row, col)

        # 只有当目标位置在当前位置下方且启用动画时，才启动下落动画
        if animate and target_y > self.rect.y:
            self.fall_target_y = target_y
            self.is_falling = True
            # print(f"碎片 {self.original_image_id}_{self.original_row}_{self.original_col} 开始下落到 ({row},{col})") # 调试信息
            # 当前位置保持不变，update 方法会使其下落到 target_y
        else:
            # 如果不启用动画，或者向上/水平移动，则直接跳到目标位置
            self.rect.x = target_x
            self.rect.y = target_y
            self.is_falling = False # 停止任何可能的下落动画
            # print(f"碎片 {self.original_image_id}_{self.original_row}_{self.original_col} 跳到 ({row},{col})") # 调试信息


    def get_original_info(self):
        """返回碎片的原始图片ID、行、列信息"""
        return (self.original_image_id, self.original_row, self.original_col)