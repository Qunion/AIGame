import pygame
import os
from settings import *

class AssetManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.default_font = None
        self.load_assets()
        self.load_font()

    def load_assets(self):
        print("Loading assets...")
        # Load images
        for key, filename in IMAGE_FILES.items():
            path = os.path.join(IMAGE_FOLDER, filename)
            try:
                image = pygame.image.load(path)
                # Convert alpha for better performance, except for maybe floor/wall
                if image.get_alpha() is None and key not in ['wall', 'floor']:
                     image = image.convert()
                else:
                     image = image.convert_alpha()

                # Resize if needed (example for items)
                if 'item' in key or 'food' in key or 'weapon' in key:
                     image = pygame.transform.scale(image, ITEM_IMAGE_SIZE)
                elif 'monster' in key:
                     image = pygame.transform.scale(image, MONSTER_IMAGE_SIZE)
                elif key == 'player':
                     image = pygame.transform.scale(image, PLAYER_IMAGE_SIZE)
                elif key == 'ui_hunger':
                     image = pygame.transform.scale(image, (UI_ICON_SIZE, UI_ICON_SIZE))
                elif key == 'ui_match':
                     image = pygame.transform.scale(image, (UI_MATCH_WIDTH, UI_MATCH_HEIGHT))


                self.images[key] = image
                print(f"Loaded image: {filename}")
            except pygame.error as e:
                print(f"Error loading image {filename}: {e}")
                # Provide a fallback surface
                size = TILE_SIZE
                if 'item' in key or 'food' in key or 'weapon' in key: size = ITEM_IMAGE_SIZE[0]
                elif 'monster' in key: size = MONSTER_IMAGE_SIZE[0]
                elif key == 'player': size = PLAYER_IMAGE_SIZE[0]
                elif key == 'ui_hunger': size = UI_ICON_SIZE
                elif key == 'ui_match': size = UI_MATCH_WIDTH

                fallback_surf = pygame.Surface((size, size) if key != 'ui_match' else (UI_MATCH_WIDTH, UI_MATCH_HEIGHT)).convert()

                color = GREY # Default fallback
                if key == 'wall': color = DARKGREY
                elif key == 'floor': color = LIGHTGREY
                elif key == 'player': color = WHITE
                elif 'monster' in key: color = RED
                elif 'item' in key: color = YELLOW
                elif 'food' in key: color = GREEN
                elif 'weapon' in key: color = BLUE

                fallback_surf.fill(color)
                self.images[key] = fallback_surf


        # Load sounds
        if pygame.mixer.get_init(): # Check if mixer initialized
            for key, filename in SOUND_FILES.items():
                path = os.path.join(SOUND_FOLDER, filename)
                try:
                    # For background music, load differently if needed (streaming)
                    if key == 'background':
                        # pygame.mixer.music.load(path) # Loaded in main typically
                        pass # Just note it exists, load later
                    else:
                        sound = pygame.mixer.Sound(path)
                        self.sounds[key] = sound
                        print(f"Loaded sound: {filename}")
                except pygame.error as e:
                    print(f"Error loading sound {filename}: {e}")
                    self.sounds[key] = None # Indicate sound failed to load
        else:
            print("Pygame mixer not initialized. Skipping sound loading.")

    def load_font(self):
         try:
             self.default_font = pygame.font.Font(FONT_NAME, UI_FONT_SIZE)
             print(f"Loaded font: {FONT_NAME}")
         except IOError:
              print(f"Could not find font {FONT_NAME}, using default.")
              self.default_font = pygame.font.Font(None, UI_FONT_SIZE) # Pygame's default

    def get_image(self, key):
        return self.images.get(key) # Returns None if key doesn't exist

    def get_sound(self, key):
        return self.sounds.get(key) # Returns None if key doesn't exist or failed load

    def play_sound(self, key, loops=0, volume=1.0):
        sound = self.get_sound(key)
        if sound and pygame.mixer.get_init():
            sound.set_volume(volume)
            sound.play(loops=loops)

    def play_music(self, key, loops=-1, volume=0.5):
         if pygame.mixer.get_init():
              path = os.path.join(SOUND_FOLDER, SOUND_FILES.get(key))
              if os.path.exists(path):
                   try:
                       pygame.mixer.music.load(path)
                       pygame.mixer.music.set_volume(volume)
                       pygame.mixer.music.play(loops=loops)
                       print(f"Playing music: {SOUND_FILES.get(key)}")
                   except pygame.error as e:
                       print(f"Error playing music {SOUND_FILES.get(key)}: {e}")
              else:
                   print(f"Music file not found: {path}")

    def stop_music(self):
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() # Release the file

    def get_font(self, size=UI_FONT_SIZE):
         # Allow getting font in different sizes if needed easily
         try:
             return pygame.font.Font(FONT_NAME, size)
         except IOError:
              return pygame.font.Font(None, size)