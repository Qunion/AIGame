import pygame
from settings import *
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    # 避免循环导入，仅用于类型注解
    from player import Player
    from maze import Tile

class Camera:
    """管理游戏世界的视口（可见区域）。"""
    def __init__(self, width_pixels: int, height_pixels: int):
        # camera_rect 的 topleft 存储了绘制世界时需要应用的偏移量
        # 它的 width 和 height 就是屏幕的宽高
        self.camera_rect = pygame.Rect(0, 0, width_pixels, height_pixels)
        self.width = width_pixels   # 摄像机视口宽度（等于屏幕宽度）
        self.height = height_pixels # 摄像机视口高度（等于屏幕高度）

    def apply(self, entity_or_rect: Union[pygame.sprite.Sprite, pygame.Rect, 'Tile']) -> pygame.Rect:
        """将摄像机偏移应用到实体（精灵、矩形或瓦片）上，返回其在屏幕上的绘制矩形。"""
        if isinstance(entity_or_rect, pygame.Rect):
            # 如果是 Rect 对象，直接移动
            return entity_or_rect.move(self.camera_rect.topleft)
        else: # 否则假设它是一个包含 rect 属性的对象 (如 Sprite 或 Tile)
            return entity_or_rect.rect.move(self.camera_rect.topleft)

    def apply_sprite(self, sprite: pygame.sprite.Sprite) -> pygame.Rect:
        """更明确地为 Sprite 应用摄像机偏移。"""
        return sprite.rect.move(self.camera_rect.topleft)

    def update(self, target: Union[pygame.sprite.Sprite, 'Player']):
        """更新摄像机位置，使其中心对准目标（通常是玩家）。"""
        # 目标的世界坐标中心 target.rect.centerx, target.rect.centery
        # 我们希望这个点显示在屏幕中心 (WIDTH / 2, HEIGHT / 2)
        # camera_rect 的 topleft 应该是多少？
        # screen_x = world_x + camera_x => camera_x = screen_x - world_x
        # screen_y = world_y + camera_y => camera_y = screen_y - world_y
        x = -target.rect.centerx + int(WIDTH / 2)
        y = -target.rect.centery + int(HEIGHT / 2)

        # --- 限制摄像机滚动范围，防止看到地图外的区域 ---
        map_width_pixels = GRID_WIDTH * TILE_SIZE   # 地图总宽度（像素）
        map_height_pixels = GRID_HEIGHT * TILE_SIZE # 地图总高度（像素）

        # 防止摄像机向左滚动超过地图边界 (x 应该 <= 0)
        x = min(0, x)
        # 防止摄像机向上滚动超过地图边界 (y 应该 <= 0)
        y = min(0, y)
        # 防止摄像机向右滚动超过地图边界 (x 应该 >= -(地图宽 - 屏幕宽))
        x = max(-(map_width_pixels - WIDTH), x)
        # 防止摄像机向下滚动超过地图边界 (y 应该 >= -(地图高 - 屏幕高))
        y = max(-(map_height_pixels - HEIGHT), y)

        # 更新摄像机的偏移量
        self.camera_rect.topleft = (x, y)

    def get_view_rect(self) -> pygame.Rect:
        """返回摄像机在世界坐标系中的可见矩形区域。"""
        # camera_rect.left 是负的偏移量，所以世界坐标的左边界是 -camera_rect.left
        return pygame.Rect(-self.camera_rect.left, -self.camera_rect.top, self.width, self.height)