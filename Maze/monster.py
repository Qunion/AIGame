import pygame
import random
from settings import *
import math
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

class Monster(pygame.sprite.Sprite):
    def __init__(self, game, pos, name, monster_type):
        self._layer = MONSTER_LAYER
        self.groups = game.all_sprites, game.monsters
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.name = name
        self.monster_type = monster_type # 'warrior' or 'mage'

        # Determine image based on name/type (simple example)
        image_key = f'monster_{monster_type}_{1 if "哥哥" in name or "姐姐" in name else 2}'
        self.image_orig = game.asset_manager.get_image(image_key)
        if self.image_orig is None: # Fallback
             self.image_orig = pygame.Surface(MONSTER_IMAGE_SIZE).convert_alpha()
             self.image_orig.fill(RED if 'warrior' in monster_type else BLUE)
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect()
        self.hit_rect = MONSTER_HIT_RECT.copy()
        self.pos = pygame.Vector2(pos) # Center position
        self.vel = pygame.Vector2(0, 0)
        self.rect.center = pos
        self.hit_rect.center = self.rect.center

        self.speed = PLAYER_SPEED * MONSTER_SPEED_FACTOR # Use base player speed factor
        self.is_active = False # Activated when seen by player
        self.target_pos = None # Player position when chasing
        self.path = [] # List of world coordinate tuples (x, y)
        self.current_path_segment = 0
        self.last_path_find_time = 0
        self.path_find_interval = 0.5 * FPS # Recalculate path every 0.5 sec if chasing

        self.health = 1 # Default health, weapons deal 1 damage

    def can_see_player(self):
         # Check if monster's tile is currently lit by player's light
         monster_tile_x = int(self.pos.x // TILE_SIZE)
         monster_tile_y = int(self.pos.y // TILE_SIZE)
         return (monster_tile_x, monster_tile_y) in self.game.lighting.visible_tiles

    def update(self, dt):
        if self.can_see_player():
            if not self.is_active:
                 print(f"{self.name} spotted the player! Activating!")
                 self.game.asset_manager.play_sound('monster_roar')
            self.is_active = True
            self.target_pos = self.game.player.pos.copy() # Update target while visible

        if self.is_active:
            path_distance = self.get_path_distance_to_player()

            if path_distance >= MONSTER_DESPAWN_DISTANCE_TILES:
                print(f"{self.name} lost the player (distance: {path_distance:.1f}). Deactivating.")
                self.is_active = False
                self.path = []
                self.vel = pygame.Vector2(0, 0)
            else:
                self.chase_player(dt)
        else:
             self.vel = pygame.Vector2(0,0) # Ensure monster stops if inactive


        # Apply movement based on velocity (set during chase logic)
        self.pos += self.vel * dt * FPS # velocity is per-frame, dt helps smooth? No, speed is per frame already.
        # self.pos += self.vel # Velocity is already calculated per frame

        self.rect.center = self.pos
        self.hit_rect.center = self.rect.center


    def get_path_distance_to_player(self):
        # Returns estimated path distance (tile count)
        _, path_len = self.game.maze.find_path(self.pos, self.game.player.pos)
        return path_len

    def calculate_target_position(self):
         """Calculates the position the monster should move towards."""
         # Warrior: Straight towards player
         if self.monster_type == 'warrior':
             return self.game.player.pos.copy()

         # Mage: Predict player position
         elif self.monster_type == 'mage':
             player = self.game.player
             player_dir = player.vel.normalize() if player.vel.length_squared() > 0 else pygame.Vector2(0, 0)

             for steps in range(MONSTER_PREDICTION_STEPS, 0, -1):
                  predict_dist = steps * TILE_SIZE
                  predicted_pos = player.pos + player_dir * predict_dist

                  # Check if predicted tile is walkable
                  predict_tile_x = int(predicted_pos.x // TILE_SIZE)
                  predict_tile_y = int(predicted_pos.y // TILE_SIZE)

                  if not self.game.maze.is_wall(predict_tile_x, predict_tile_y):
                      # print(f"Mage predicting {steps} steps ahead.")
                      return predicted_pos

             # If all predictions fail (hit wall), target player directly
             # print("Mage prediction failed, targeting player directly.")
             return player.pos.copy()

         return self.game.player.pos.copy() # Default fallback


    def chase_player(self, dt):
        self.target_pos = self.calculate_target_position()
        current_time = pygame.time.get_ticks()

        # Recalculate path periodically or if path is empty/finished
        if not self.path or current_time - self.last_path_find_time > self.path_find_interval * 1000: # interval is frames, convert to ms
            new_path, _ = self.game.maze.find_path(self.pos, self.target_pos)
            if new_path and len(new_path) > 1: # Need at least start and next step
                self.path = new_path[1:] # Remove the starting node (current pos)
                self.current_path_segment = 0
                # print(f"{self.name} found path with {len(self.path)} steps.")
            else:
                # print(f"{self.name} could not find path or path too short.")
                self.path = [] # Clear path if finding fails
                self.vel = pygame.Vector2(0, 0)
                return # Stop chasing if no path

            self.last_path_find_time = current_time

        # Move along the current path
        if self.path and self.current_path_segment < len(self.path):
            target_node_pos = pygame.Vector2(self.path[self.current_path_segment])
            direction = (target_node_pos - self.pos)

            if direction.length_squared() < (self.speed * 1.5)**2: # Close enough to target node
                 self.current_path_segment += 1
                 if self.current_path_segment >= len(self.path):
                      # print(f"{self.name} reached end of path segment.")
                      self.path = [] # Clear path, will recalculate next frame
                      self.vel = pygame.Vector2(0, 0)
                      return
                 else: # Update target node for direction calculation
                     target_node_pos = pygame.Vector2(self.path[self.current_path_segment])
                     direction = (target_node_pos - self.pos)


            # Set velocity towards the target node
            if direction.length_squared() > 0:
                self.vel = direction.normalize() * self.speed
            else:
                self.vel = pygame.Vector2(0,0) # Already at the node? Stop.

        else: # No path or finished path
            self.vel = pygame.Vector2(0, 0)


    def take_damage(self):
        self.health -= 1
        if self.health <= 0:
            print(f"{self.name} was defeated!")
            self.game.asset_manager.play_sound('monster_die')
            self.kill() # Remove monster from game