# piece.py
# 定义表示单个碎片的类

import pygame
import settings

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

        self.image = image_surface
        # self.image = pygame.transform.scale(image_surface, (settings.PIECE_SIZE, settings.PIECE_SIZE)) # 假设传入的surface已经是正确尺寸的

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
             self.set_grid_position(initial_grid_row, initial_grid_col)
        else:
             # 如果初始位置未知，先创建一个空的rect，后续set_grid_position会设置
             self.rect = pygame.Rect(0, 0, settings.PIECE_SIZE, settings.PIECE_SIZE)


        # 动画相关属性 (当下落时可能需要)
        # self.is_falling = False
        # self.fall_target_y = -1 # 碎片下落的目标屏幕Y坐标

    def draw(self, surface):
        """在指定的surface上绘制碎片"""
        surface.blit(self.image, self.rect)

    # def update(self, dt):
    #     """更新碎片状态 (如下落动画)"""
    #     if self.is_falling:
    #         # 计算下一帧的位置
    #         new_y = self.rect.y + settings.FALL_SPEED_PIXELS_PER_FRAME
    #         if new_y >= self.fall_target_y:
    #             # 到达目标位置或超过，停止下落
    #             self.rect.y = self.fall_target_y
    #             self.is_falling = False
    #             # TODO: 可能需要通知 Board 碎片已到达新位置
    #         else:
    #             self.rect.y = new_y


    def set_grid_position(self, row, col):
        """设置碎片在拼盘中的新网格位置并更新其屏幕坐标"""
        self.current_grid_row = row
        self.current_grid_col = col
        self.rect.x = settings.BOARD_OFFSET_X + self.current_grid_col * settings.PIECE_SIZE
        self.rect.y = settings.BOARD_OFFSET_Y + self.current_grid_row * settings.PIECE_SIZE
        # 如果有下落动画，这里只是设置了最终位置，动画会逐步移动到这里
        # self.fall_target_y = self.rect.y # 设置下落目标Y坐标
        # self.is_falling = True # 开始下落动画