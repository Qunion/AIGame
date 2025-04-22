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
            image_surface (pygame.Surface): 碎片的图像表面 (期望尺寸为 settings.PIECE_WIDTH x settings.PIECE_HEIGHT)
            original_image_id (int): 碎片所属的原始图片ID (如 1 代表 image_1)
            original_row (int): 碎片在原始图片逻辑网格中的行索引 (0 - 图片逻辑行数-1)
            original_col (int): 碎片在原始图片逻辑网格中的列索引 (0 - 图片逻辑列数-1)
            initial_grid_row (int): 碎片在拼盘物理网格中的初始行索引 (0 - settings.BOARD_ROWS-1)。-1 表示待分配。
            initial_grid_col (int): 碎片在拼盘物理网格中的初始列索引 (0 - settings.BOARD_COLS-1)。-1 表示待分配。
        """
        # Inherit from Sprite
        super().__init__()

        # --- 关键修改：检查传入的 Surface 尺寸是否与设定的碎片宽高匹配 ---
        # 碎片Surface必须是固定尺寸，用于在Board网格中绘制
        if image_surface is None:
             print(f"致命错误: Piece: 图片ID {original_image_id} 原始位置 ({original_row},{original_col}) 的 image_surface 是 None。无法创建碎片。") # Debug
             # Create a placeholder image to prevent crashes, but mark as invalid if needed
             self.image = pygame.Surface((settings.PIECE_WIDTH, settings.PIECE_HEIGHT), pygame.SRCALPHA)
             self.image.fill((255, 0, 0, 255)) # Solid red as error visual
        elif image_surface.get_size() != (settings.PIECE_WIDTH, settings.PIECE_HEIGHT):
             print(f"警告: Piece: 图片ID {original_image_id} 原始位置 ({original_row},{original_col}) 的 image_surface 尺寸不正确 {image_surface.get_size()}，应为 {settings.PIECE_WIDTH}x{settings.PIECE_HEIGHT}。尝试缩放。") # Debug
             try:
                 # Scale the provided surface to the fixed piece size
                 self.image = pygame.transform.scale(image_surface, (settings.PIECE_WIDTH, settings.PIECE_HEIGHT)) # <-- 缩放到设定的宽高
             except pygame.error as e:
                 print(f"错误: Piece: 图片ID {original_image_id} 原始位置 ({original_row},{original_col}) 的 Surface 缩放失败: {e}. 使用原始 Surface (可能尺寸错误)。") # Debug
                 # Fallback to original surface even if size is wrong
                 self.image = image_surface
             except Exception as e:
                 print(f"错误: Piece: 图片ID {original_image_id} 原始位置 ({original_row},{original_col}) 的 Surface 缩放发生未知错误: {e}. 使用原始 Surface (可能尺寸错误)。") # Debug
                 self.image = image_surface
        else:
             # Size is correct, use the provided surface directly
             self.image = image_surface


        # 存储碎片的原始信息，用于判断是否归位
        self.original_image_id = original_image_id
        self.original_row = original_row
        self.original_col = original_col

        # 存储碎片当前在拼盘中的网格位置 (物理网格)
        self.current_grid_row = initial_grid_row
        self.current_grid_col = initial_grid_col

        # 初始化屏幕位置，如果在初始化时已知网格位置
        self.rect = self.image.get_rect() # Initialize the rect based on the image size

        if initial_grid_row != -1 and initial_grid_col != -1:
             # If initial grid position is known, set the screen position immediately
             # set_grid_position handles the screen coordinate calculation
             self.set_grid_position(initial_grid_row, initial_grid_col, animate=False) # 初始位置不动画
        else:
             # If initial position unknown, place it off-screen initially
             # The Board will call set_grid_position later to place it correctly
             self.rect.topleft = (-settings.PIECE_WIDTH, -settings.PIECE_HEIGHT) # <-- Use PIECE_WIDTH/HEIGHT for off-screen


        # 动画相关属性 (当下落时可能需要)
        self.is_falling = False
        self.fall_target_y = -1 # 碎片下落的目标屏幕Y坐标


    # 注意：如果继承自 Sprite 并使用 pygame.sprite.Group.draw() 方法，则不需要 draw 方法。
    # Group.draw() 方法会调用每个精灵的 draw 方法，但默认的 Sprite.draw 方法会执行 surface.blit(self.image, self.rect)。
    # 如果你需要为 Piece 类实现自定义绘制逻辑，则需要重写此方法。
    def draw(self, surface):
        """在指定的surface上绘制碎片"""
        surface.blit(self.image, self.rect)


    def update(self, dt):
        """更新碎片状态 (如下落动画)。Sprite Group 会调用这个方法。"""
        # Ensure dt is positive, though tick should provide positive values
        if dt < 0: dt = 0

        if self.is_falling:
            # 根据下落速度和时间差计算移动距离
            move_distance = settings.FALL_SPEED_PIXELS_PER_SECOND * dt
            new_y = self.rect.y + move_distance

            # 检查是否到达目标位置或超过
            # Compare current Y with target Y considering the fall direction
            if (settings.FALL_SPEED_PIXELS_PER_SECOND > 0 and new_y >= self.fall_target_y) or \
               (settings.FALL_SPEED_PIXELS_PER_SECOND < 0 and new_y <= self.fall_target_y):
                # Reached or passed the target Y position
                # Stop falling, snap to the exact target position
                self.rect.y = self.fall_target_y
                self.is_falling = False
                # print(f"碎片 {self.original_image_id}_{self.original_row}_{self.original_col} 停止下落到屏幕Y {self.rect.y}") # Debug stop fall
                # TODO: 可能需要通知 Board 碎片已到达新位置 (或者 Board 在 update 中检查 is_falling)
            elif settings.FALL_SPEED_PIXELS_PER_SECOND == 0:
                 # If speed is zero, it shouldn't be falling, but handle as finished just in case
                 self.rect.y = self.fall_target_y
                 self.is_falling = False
            else:
                # Continue falling downwards
                self.rect.y = new_y


    def set_grid_position(self, row, col, animate=False):
        """
        设置碎片在拼盘中的新网格位置并更新其屏幕坐标。
        可以选择是否启用下落动画。

        Args:
            row (int): 目标网格行 (物理网格)
            col (int): 目标网格列 (物理网格)
            animate (bool): 是否以动画方式移动到新位置 (目前仅支持向下动画)
        """
        # Store the new logical grid position
        self.current_grid_row = row
        self.current_grid_col = col

        # Calculate the target screen pixel position for the new grid position
        target_x = settings.BOARD_OFFSET_X + self.current_grid_col * settings.PIECE_WIDTH # <-- 使用 PIECE_WIDTH
        target_y = settings.BOARD_OFFSET_Y + self.current_grid_row * settings.PIECE_HEIGHT # <-- 使用 PIECE_HEIGHT
        # target_pos = (target_x, target_y) # Store as tuple if needed

        # Determine if animation is needed and possible (currently only supports downward animation)
        # Check if animate is requested AND the target Y is below the current Y
        if animate and target_y > self.rect.y and settings.FALL_SPEED_PIXELS_PER_SECOND > 0:
            # Start downward animation
            self.fall_target_y = target_y
            self.is_falling = True
            # The X position should snap to the target X immediately for falling animation
            self.rect.x = target_x
            # print(f"碎片 {self.original_image_id}_{self.original_row}_{self.original_col} 开始下落到 ({row},{col}) 屏幕坐标 ({target_x},{target_y})") # Debug start fall
            # The current Y position is where it starts falling FROM. update method will move it.
        else:
            # If not animating, or animating upwards/horizontally (not supported), or fall speed is zero,
            # snap the piece directly to the target screen position.
            self.rect.x = target_x
            self.rect.y = target_y
            self.is_falling = False # Stop any potential falling animation that might have been active
            self.fall_target_y = self.rect.y # Reset target Y to current Y

            # print(f"碎片 {self.original_image_id}_{self.original_row}_{self.original_col} 跳到 ({row},{col}) 屏幕坐标 ({self.rect.x},{self.rect.y})") # Debug instant set


    def get_original_info(self):
        """返回碎片的原始图片ID、行、列信息"""
        return (self.original_image_id, self.original_row, self.original_col)