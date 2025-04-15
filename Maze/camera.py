import pygame
from settings import *

class Camera:
    def __init__(self, width_pixels, height_pixels):
        self.camera_rect = pygame.Rect(0, 0, width_pixels, height_pixels)
        self.width = width_pixels
        self.height = height_pixels

    def apply(self, entity_or_rect):
        """Applies camera offset to a Rect or an object with a rect attribute."""
        if isinstance(entity_or_rect, pygame.Rect):
            return entity_or_rect.move(self.camera_rect.topleft)
        else: # Assume it's a sprite-like object
            return entity_or_rect.rect.move(self.camera_rect.topleft)

    def apply_sprite(self, sprite):
         """More explicit version for sprites."""
         return sprite.rect.move(self.camera_rect.topleft)

    def update(self, target):
        """Centers the camera on the target (usually the player)."""
        # Target pos is the center, adjust camera top-left
        x = -target.rect.centerx + int(WIDTH / 2)
        y = -target.rect.centery + int(HEIGHT / 2)

        # Limit scrolling to map size
        x = min(0, x)  # Prevent camera moving left past map edge (0)
        y = min(0, y)  # Prevent camera moving up past map edge (0)
        map_width_pixels = GRID_WIDTH * TILE_SIZE
        map_height_pixels = GRID_HEIGHT * TILE_SIZE
        x = max(-(map_width_pixels - WIDTH), x) # Prevent scrolling right past map edge
        y = max(-(map_height_pixels - HEIGHT), y) # Prevent scrolling down past map edge

        self.camera_rect.topleft = (x, y)

    def get_view_rect(self):
         """Returns the rectangle representing the camera's view in world coordinates."""
         return pygame.Rect(-self.camera_rect.left, -self.camera_rect.top, self.width, self.height)