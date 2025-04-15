import pygame
import sys
import random
import os
import pickle
from settings import *
from assets import AssetManager
from maze import Maze, Tile
from player import Player
from items import MatchItem, FoodItem, WeaponItem
from monster import Monster
from lighting import Lighting
from camera import Camera
from ui import draw_player_hud, draw_game_over_screen, draw_win_screen, draw_pause_screen, draw_text
from save_load import save_game, load_game, capture_game_state, restore_game_state

class Game:
    def __init__(self):
        pygame.init()
        # Initialize mixer first with recommended settings
        try:
             pygame.mixer.pre_init(44100, -16, 2, 512) # freq, size, channels, buffer
             pygame.mixer.init()
             print("Pygame mixer initialized successfully.")
        except pygame.error as e:
             print(f"Error initializing pygame mixer: {e}. Sound will be disabled.")

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.game_over = False
        self.game_won = False
        self.asset_manager = AssetManager() # Load assets

    def setup_new_game(self):
        """Initializes all game objects for a new game."""
        print("Setting up new game...")
        self.all_sprites = pygame.sprite.LayeredUpdates() # Use LayeredUpdates for drawing order
        self.walls = pygame.sprite.Group() # For potential sprite-based wall collision (optional)
        self.items = pygame.sprite.Group()
        self.monsters = pygame.sprite.Group()

        self.maze = Maze(self, GRID_WIDTH, GRID_HEIGHT)

        # Ensure player start position is valid
        if self.maze.player_start_pos is None:
             print("Error: Could not determine player start position from maze.")
             self.running = False # Stop if critical error
             return
        self.player = Player(self, self.maze.player_start_pos)

        self.camera = Camera(WIDTH, HEIGHT)
        self.lighting = Lighting(self)

        # Place items
        placed_tiles = set()
        placed_tiles.add( (int(self.player.pos.x // TILE_SIZE), int(self.player.pos.y // TILE_SIZE)) )
        if self.maze.exit_pos: placed_tiles.add(self.maze.exit_pos)

        # Function to get a random empty floor tile
        def get_spawn_pos():
            while True:
                pos_world = self.maze.get_random_floor_tile()
                pos_tile = (int(pos_world[0] // TILE_SIZE), int(pos_world[1] // TILE_SIZE))
                if pos_tile not in placed_tiles:
                    placed_tiles.add(pos_tile)
                    return pos_world # Return world coordinates

        print("Placing items...")
        for _ in range(MATCH_SPAWN_COUNT): MatchItem(self, get_spawn_pos())
        for _ in range(FOOD_BREAD_COUNT): FoodItem(self, get_spawn_pos(), 'bread')
        for _ in range(FOOD_MEAT_COUNT): FoodItem(self, get_spawn_pos(), 'meat')
        WeaponItem(self, get_spawn_pos(), 'broken')
        WeaponItem(self, get_spawn_pos(), 'good')

        # Place monsters in their zones
        print("Placing monsters...")
        monster_indices = list(range(MONSTER_COUNT))
        random.shuffle(monster_indices) # Randomize which monster goes to which zone
        zone_indices = list(range(len(MONSTER_SPAWN_ZONES)))
        random.shuffle(zone_indices)

        for i in range(MONSTER_COUNT):
             zone_idx = zone_indices[i]
             monster_idx = monster_indices[i]
             zone = MONSTER_SPAWN_ZONES[zone_idx]
             name = MONSTER_NAMES[monster_idx]
             m_type = MONSTER_TYPES[monster_idx]

             # Find a random floor tile within the zone
             attempts = 0
             while attempts < 100: # Prevent infinite loop if zone is bad
                 x = random.randint(zone[0], zone[2] - 1)
                 y = random.randint(zone[1], zone[3] - 1)
                 if not self.maze.is_wall(x, y) and (x, y) not in placed_tiles:
                      pos_world = (x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2)
                      Monster(self, pos_world, name, m_type)
                      placed_tiles.add((x,y))
                      print(f"Placed {name} ({m_type}) in zone {zone_idx} at {(x,y)}")
                      break
                 attempts += 1
             else:
                  print(f"Warning: Could not place monster {name} in zone {zone_idx}. Placing randomly.")
                  Monster(self, get_spawn_pos(), name, m_type) # Fallback placement

        # Initial FoV calculation
        self.lighting.update(self.player)

        # Play background music
        self.asset_manager.play_music('background')

        self.game_over = False
        self.game_won = False

    def try_load_game(self):
        """Attempts to load a saved game state."""
        saved_state = load_game()
        if saved_state:
            # Need to initialize basic structures before restoring
            self.all_sprites = pygame.sprite.LayeredUpdates()
            self.walls = pygame.sprite.Group()
            self.items = pygame.sprite.Group()
            self.monsters = pygame.sprite.Group()
            # Create dummy maze/player first, then restore state
            self.maze = Maze(self, GRID_WIDTH, GRID_HEIGHT)
            self.player = Player(self, (0,0)) # Temp position
            self.camera = Camera(WIDTH, HEIGHT)
            self.lighting = Lighting(self)

            if restore_game_state(self, saved_state):
                print("Game loaded successfully.")
                self.asset_manager.play_music('background')
                self.game_over = False
                self.game_won = False
                return True # Load successful
            else:
                print("Failed to restore game state, starting new game.")
                # Fall through to setup_new_game if restore fails
        return False # No save file or load failed


    def run(self):
        if not self.try_load_game():
            self.setup_new_game() # Start new game if no save or load failed

        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0 # Time delta in seconds
            self.events()
            if not self.paused and not self.game_over and not self.game_won:
                self.update()
            self.draw()

        # Game loop ended
        if SAVE_ON_EXIT and not self.game_won and not self.game_over: # Only save if quitting normally mid-game
            self.save_game_state()
        pygame.quit()
        sys.exit()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    if self.paused:
                         pygame.mixer.music.pause()
                    else:
                         pygame.mixer.music.unpause()
                if self.game_over or self.game_won:
                    if event.key == pygame.K_r: # Restart
                         # Need to properly reset everything
                         self.setup_new_game()
                    if event.key == pygame.K_q: # Quit
                         self.running = False
                # --- Debug Keys (Optional) ---
                # if event.key == pygame.K_h: # Heal hunger
                #     self.player.add_hunger(50)
                # if event.key == pygame.K_m: # Add match
                #     self.player.add_match()
                # if event.key == pygame.K_g: # Toggle God Mode (no hunger/match decay?)
                #     pass
                # if event.key == pygame.K_k: # Kill nearest monster?
                #      pass
                # if event.key == pygame.K_l: # Toggle light walls
                #      self.lighting.light_walls = not self.lighting.light_walls


    def update(self):
        self.all_sprites.update(self.dt) # Calls update() on Player and Monsters
        self.camera.update(self.player)
        self.lighting.update(self.player) # Update FoV and memory

        # Check if player died during their update
        if self.player.is_dead:
            self.game_over = True

    def draw(self):
        self.screen.fill(BLACK) # Background color for unseen areas

        # Draw the maze based on lighting/FoW
        self.maze.draw(self.screen, self.camera, self.lighting)

        # Draw sprites (items, player, monsters) respecting layers and camera
        for sprite in self.all_sprites:
             # Only draw sprites if their tile is sufficiently visible?
             sprite_tile_x = int(sprite.pos.x // TILE_SIZE)
             sprite_tile_y = int(sprite.pos.y // TILE_SIZE)
             brightness = self.lighting.get_tile_brightness(sprite_tile_x, sprite_tile_y)

             if brightness > 0.1: # Only draw if reasonably lit
                 # Apply brightness to sprite image? (Optional, complex)
                 # Simple approach: Draw normally if visible enough
                 screen_pos_rect = self.camera.apply(sprite)
                 self.screen.blit(sprite.image, screen_pos_rect)

        # --- Alternative/Additional: Draw Darkness Overlay ---
        # self.lighting.draw_darkness(self.screen, self.camera, self.player)

        # Draw HUD (always on top, no camera offset)
        draw_player_hud(self.screen, self.player, self.asset_manager)

        # Draw Game Over / Win / Pause screens
        if self.game_over:
            draw_game_over_screen(self.screen, self.player.death_reason, self.asset_manager)
        elif self.game_won:
            draw_win_screen(self.screen, self.asset_manager)
        elif self.paused:
            draw_pause_screen(self.screen, self.asset_manager)

        # Display FPS (optional debug)
        draw_text(self.screen, f"FPS: {self.clock.get_fps():.2f}", 18, 10, 10, YELLOW, align="topleft")

        pygame.display.flip()

    def win_game(self):
         if not self.game_won and not self.game_over:
             print("Player reached the exit! You win!")
             self.game_won = True
             self.asset_manager.play_sound('win')
             self.asset_manager.stop_music()
             # Delete save file on win? Optional.
             if os.path.exists(SAVE_FILE):
                  try: os.remove(SAVE_FILE)
                  except OSError as e: print(f"Error deleting save file on win: {e}")


    def save_game_state(self):
         state = capture_game_state(self)
         save_game(state)

# --- Main execution ---
if __name__ == '__main__':
    game = Game()
    game.run()