# src/interaction_modules/puzzle_piece.py
import pygame

class PuzzlePiece:
    """代表一个可拖拽的拼图碎片"""

    def __init__(self, piece_id, surface: pygame.Surface, correct_pos_local: tuple[int, int], grid_pos: tuple[int, int] = None):
        """
        初始化拼图碎片。
        piece_id: 碎片的唯一ID。
        surface: 碎片的Pygame Surface。
        correct_pos_local: 碎片在原始图片或其切割区域内的正确像素位置 (例如左上角)。
        grid_pos: 碎片在拼图网格中的正确行/列索引 (可选)。
        """
        self.id = piece_id
        self.surface = surface
        self.rect = self.surface.get_rect() # 用于位置和碰撞检测
        self.correct_pos_local = correct_pos_local # 在图片本地坐标系下的正确位置
        self.grid_pos = grid_pos # 在网格中的正确位置

        self._is_locked = False # 是否已锁定在正确位置

    def set_position(self, screen_pos: tuple[int, int]):
        """设置碎片在屏幕上的位置"""
        self.rect.topleft = screen_pos

    def get_position(self) -> tuple[int, int]:
        """获取碎片在屏幕上的位置"""
        return self.rect.topleft

    def set_locked(self, locked: bool):
        """设置碎片是否锁定"""
        self._is_locked = locked

    def is_locked(self) -> bool:
        """检查碎片是否锁定"""
        return self._is_locked

    def draw(self, screen: pygame.Surface):
        """在屏幕上绘制碎片"""
        screen.blit(self.surface, self.rect)
        # TODO: 绘制碎片边缘效果 (如果设计需要)
        # TODO: 绘制锁定状态的视觉反馈 (如果锁定)
        # if self._is_locked:
        #     pygame.draw.rect(screen, (0, 255, 0), self.rect, 2) # 示例：绿色边框


    # TODO: 可以添加方法来处理拖拽时的视觉效果（例如，绘制阴影）