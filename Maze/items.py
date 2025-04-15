import pygame
from settings import *
from typing import TYPE_CHECKING
from typing import Tuple # 导入需要用到的类型提示

if TYPE_CHECKING:
    from main import Game
    from player import Player

class Item(pygame.sprite.Sprite):
    """所有可拾取物品的基类。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float], item_type: str, image_key: str):
        self._layer = ITEM_LAYER # 设置精灵所在的图层
        # 将精灵添加到 all_sprites 和 items 组
        self.groups = game.all_sprites, game.items
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game             # 游戏主对象的引用
        self.item_type = item_type   # 物品类型 ('match', 'food', 'weapon')
        # 从资源管理器获取图片
        self.image = game.asset_manager.get_image(image_key)
        if self.image is None: # 如果图片加载失败，使用备用图像
             self.image = pygame.Surface(ITEM_IMAGE_SIZE)
             self.image.fill(YELLOW) # 用黄色方块代替
        self.rect = self.image.get_rect() # 获取图片的矩形区域
        self.pos = pygame.Vector2(pos)    # 物品的中心位置 (世界坐标)
        self.rect.center = self.pos       # 设置矩形中心点

    def interact(self, player: 'Player') -> bool:
        """当玩家接触到物品时调用。返回 True 表示交互成功。"""
        print(f"玩家与 {self.item_type} 发生交互")
        self.game.asset_manager.play_sound('pickup') # 播放拾取音效
        # 子类将覆盖此方法以实现具体效果
        self.kill() # 交互后从游戏中移除物品精灵
        return True

class MatchItem(Item):
    """代表地上的火柴物品。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float]):
        # 调用父类构造函数，指定类型和图片键名
        super().__init__(game, pos, 'match', 'match_item')

    def interact(self, player: 'Player') -> bool:
        """玩家拾取火柴。"""
        if super().interact(player): # 调用父类的 interact 处理音效和移除
            player.add_match()       # 调用玩家的方法增加火柴
            return True
        return False

class FoodItem(Item):
    """代表地上的食物物品（面包或肉）。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float], food_type: str):
        self.food_type = food_type # 'bread' 或 'meat'
        # 根据食物类型选择图片
        image_key = 'food_bread' if food_type == 'bread' else 'food_meat'
        # 调用父类构造函数
        super().__init__(game, pos, 'food', image_key)
        # 根据食物类型设置属性值
        self.hunger_value = FOOD_BREAD_VALUE if food_type == 'bread' else FOOD_MEAT_VALUE
        self.speed_boost_factor = FOOD_MEAT_SPEED_BOOST_FACTOR if food_type == 'meat' else 1.0
        self.speed_boost_duration = FOOD_MEAT_BOOST_DURATION_FRAMES if food_type == 'meat' else 0

    def interact(self, player: 'Player') -> bool:
        """玩家拾取食物。"""
        if super().interact(player): # 调用父类 interact
            player.add_hunger(self.hunger_value) # 增加玩家饱食度
            if self.food_type == 'meat': # 如果是肉，施加速效果
                player.apply_speed_boost(self.speed_boost_factor, self.speed_boost_duration)
            return True
        return False

class WeaponItem(Item):
    """代表地上的武器物品（断剑或好剑）。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float], weapon_type: str):
        self.weapon_type = weapon_type # 'broken' 或 'good'
        # 根据武器类型选择图片
        image_key = 'weapon_sword_broken' if weapon_type == 'broken' else 'weapon_sword_good'
        # 调用父类构造函数
        super().__init__(game, pos, 'weapon', image_key)
        # 根据武器类型设置使用次数
        self.uses = WEAPON_BROKEN_USES if weapon_type == 'broken' else WEAPON_GOOD_USES

    def interact(self, player: 'Player') -> bool:
        """玩家拾取武器。"""
        if super().interact(player): # 调用父类 interact
            # 将武器对象本身添加到玩家的库存中
            # 注意：此时物品精灵已被 kill()，但对象实例还在
            player.add_weapon(self)
            return True
        return False