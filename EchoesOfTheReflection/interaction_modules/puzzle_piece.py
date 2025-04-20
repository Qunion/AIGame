# interaction_modules/puzzle_piece.py
import pygame
# 导入自定义模块 - 它们现在位于根目录
from settings import Settings # 可能不需要Settings，但导入习惯保留
# from image_renderer import ImageRenderer # 拼图碎片类本身不需要ImageRenderer引用


class PuzzlePiece:
    """代表一个可拖拽的拼图碎片"""

    def __init__(self, piece_id, surface: pygame.Surface, correct_pos_local: tuple[int, int], grid_pos: tuple[int, int] = None):
        """
        初始化拼图碎片。
        piece_id: 碎片的唯一ID。
        surface: 碎片的Pygame Surface (已经根据当前显示尺寸切割好的)。
        correct_pos_local: 碎片在原始图片或其切割区域内的正确像素位置 (相对于图片显示区域的左上角)。
        grid_pos: 碎片在拼图网格中的正确行/列索引 (可选)。
        """
        self.id = piece_id
        self.surface = surface # 碎片的图像 Surface
        self.rect = self.surface.get_rect() # 用于位置和碰撞检测，其尺寸就是碎片显示尺寸
        self.correct_pos_local = correct_pos_local # 在图片显示区域本地坐标系下的正确位置 (相对于图片显示区域左上角)
        self.grid_pos = grid_pos # 在网格中的正确位置

        self._is_locked = False # 是否已锁定在正确位置

    def set_position(self, screen_pos: tuple[int, int]):
        """设置碎片在屏幕上的位置 (topleft)"""
        self.rect.topleft = screen_pos

    def get_position(self) -> tuple[int, int]:
        """获取碎片在屏幕上的位置 (topleft)"""
        return self.rect.topleft

    def set_locked(self, locked: bool):
        """设置碎片是否锁定"""
        self._is_locked = locked

    def is_locked(self) -> bool:
        """检查碎片是否锁定"""
        return self._is_locked

    def draw(self, screen: pygame.Surface):
        """在屏幕上绘制碎片"""
        if self.surface:
            screen.blit(self.surface, self.rect.topleft)
        # TODO: 绘制碎片边缘效果 (如果设计需要)
        # 例如，绘制一个边框
        # pygame.draw.rect(screen, (255, 255, 255), self.rect, 1) # 白色边框

        # TODO: 绘制锁定状态的视觉反馈 (如果锁定)
        # if self._is_locked:
        #     pygame.draw.rect(screen, (0, 255, 0), self.rect, 2) # 示例：绿色边框