import pygame
from settings import *

class Item(pygame.sprite.Sprite):
    def __init__(self, game, pos, item_type, image_key):
        self._layer = ITEM_LAYER
        self.groups = game.all_sprites, game.items
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.item_type = item_type
        self.image = game.asset_manager.get_image(image_key)
        if self.image is None: # Fallback if image failed load
             self.image = pygame.Surface(ITEM_IMAGE_SIZE)
             self.image.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.pos = pygame.Vector2(pos) # Center position
        self.rect.center = self.pos

    def interact(self, player):
        """Called when player touches the item. Returns True if interaction successful."""
        print(f"Player interacted with {self.item_type}")
        self.game.asset_manager.play_sound('pickup')
        # Child classes will override this
        self.kill() # Remove item from game
        return True

class MatchItem(Item):
    def __init__(self, game, pos):
        super().__init__(game, pos, 'match', 'match_item')

    def interact(self, player):
        if super().interact(player):
            player.add_match()
            return True
        return False

class FoodItem(Item):
    def __init__(self, game, pos, food_type):
        self.food_type = food_type
        image_key = 'food_bread' if food_type == 'bread' else 'food_meat'
        super().__init__(game, pos, 'food', image_key)
        self.hunger_value = FOOD_BREAD_VALUE if food_type == 'bread' else FOOD_MEAT_VALUE
        self.speed_boost_factor = FOOD_MEAT_SPEED_BOOST_FACTOR if food_type == 'meat' else 1.0
        self.speed_boost_duration = FOOD_MEAT_BOOST_DURATION_FRAMES if food_type == 'meat' else 0

    def interact(self, player):
        if super().interact(player):
            player.add_hunger(self.hunger_value)
            if self.food_type == 'meat':
                player.apply_speed_boost(self.speed_boost_factor, self.speed_boost_duration)
            return True
        return False

class WeaponItem(Item):
    def __init__(self, game, pos, weapon_type):
        self.weapon_type = weapon_type # 'broken' or 'good'
        image_key = 'weapon_sword_broken' if weapon_type == 'broken' else 'weapon_sword_good'
        super().__init__(game, pos, 'weapon', image_key)
        self.uses = WEAPON_BROKEN_USES if weapon_type == 'broken' else WEAPON_GOOD_USES

    def interact(self, player):
        if super().interact(player):
            player.add_weapon(self) # Give the weapon object itself to player
            return True
        return False