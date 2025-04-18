import pygame
from settings import *
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from main import Game

class Marker(pygame.sprite.Sprite):
    """代表玩家放置在地图上的永久标记物。"""
    def __init__(self, game: 'Game', pos_world: Tuple[float, float], marker_id: str):
        self._layer = MARKER_LAYER # 设置标记物图层
        # 加入 all_sprites 和 新的 markers_placed 组
        self.groups = game.all_sprites, game.markers_placed
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.marker_id = marker_id # 存储标记物的类型 ID

        # 获取标记物图片
        self.image = game.asset_manager.get_image(marker_id)
        # 注意：AssetManager 加载时已缩放到 MARKER_SPRITE_SIZE
        self.rect = self.image.get_rect()
        self.pos = pygame.Vector2(pos_world) # 世界坐标中心点
        self.rect.center = self.pos

    def update(self, dt: float):
        """标记物通常不需要每帧更新。"""
        pass