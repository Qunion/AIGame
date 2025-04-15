import pygame
from settings import *
import math

class Player(pygame.sprite.Sprite):
    def __init__(self, game, pos):
        self._layer = PLAYER_LAYER
        self.groups = game.all_sprites
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.image_orig = game.asset_manager.get_image('player')
        if self.image_orig is None: # Fallback
             self.image_orig = pygame.Surface(PLAYER_IMAGE_SIZE).convert_alpha()
             self.image_orig.fill(WHITE)
             pygame.draw.circle(self.image_orig, BLUE, (PLAYER_RADIUS_PX, PLAYER_RADIUS_PX), PLAYER_RADIUS_PX)
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect()
        self.hit_rect = PLAYER_HIT_RECT.copy() # For collision
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 0)
        self.rect.center = self.pos
        self.hit_rect.center = self.rect.center

        # Stats
        self.hunger = PLAYER_START_HUNGER
        self.matches = [] # Stores remaining burn time (frames) for each match
        for _ in range(MATCH_INITIAL_COUNT):
            self.add_match() # Add initial matches
        self.current_match_index = len(self.matches) - 1 if self.matches else -1 # Start burning the rightmost one
        self.time_since_last_match_burn = 0

        self.inventory = {'weapons': []} # Store WeaponItem objects

        # Movement & Speed
        self.base_speed = PLAYER_SPEED
        self.current_speed = self.base_speed
        self.speed_boost_factor = 1.0
        self.speed_boost_timer = 0

        # State timers
        self.hunger_decay_timer = 0
        self.hunger_warn_timer = 0
        self.match_out_timer = 0 # Timer after last match burns out
        self.is_dead = False
        self.death_reason = ""

        # Magic effect timer
        self.magic_match_timer = 0


    def get_input(self):
        self.vel = pygame.Vector2(0, 0)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel.x = -self.current_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel.x = self.current_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vel.y = -self.current_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vel.y = self.current_speed

        # Prevent faster diagonal movement
        if self.vel.x != 0 and self.vel.y != 0:
            self.vel *= 0.7071 # Roughly 1/sqrt(2)

    def move(self, dt):
        if self.vel.length_squared() > 0: # Only move if velocity is non-zero
             new_pos = self.pos + self.vel # Calculate potential new position
             self.check_collisions(new_pos)
             # Play step sound (maybe throttle this)
             # if random.random() < 0.1: self.game.asset_manager.play_sound('step')


    def check_collisions(self, new_pos):
         # --- Wall Collision ---
         potential_hit_rect = self.hit_rect.copy()
         potential_hit_rect.centerx = new_pos.x
         collision_x = False
         for x in range(int(potential_hit_rect.left // TILE_SIZE), int(potential_hit_rect.right // TILE_SIZE) + 1):
             for y in range(int(potential_hit_rect.top // TILE_SIZE), int(potential_hit_rect.bottom // TILE_SIZE) + 1):
                  if self.game.maze.is_wall(x, y):
                       wall_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                       if potential_hit_rect.colliderect(wall_rect):
                            collision_x = True
                            break
             if collision_x: break

         if not collision_x:
              self.pos.x = new_pos.x

         potential_hit_rect = self.hit_rect.copy()
         potential_hit_rect.centery = new_pos.y
         potential_hit_rect.centerx = self.pos.x # Use the potentially updated x
         collision_y = False
         for x in range(int(potential_hit_rect.left // TILE_SIZE), int(potential_hit_rect.right // TILE_SIZE) + 1):
             for y in range(int(potential_hit_rect.top // TILE_SIZE), int(potential_hit_rect.bottom // TILE_SIZE) + 1):
                  if self.game.maze.is_wall(x, y):
                       wall_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                       if potential_hit_rect.colliderect(wall_rect):
                            collision_y = True
                            break
             if collision_y: break

         if not collision_y:
              self.pos.y = new_pos.y

         # Update rects after position change
         self.rect.center = self.pos
         self.hit_rect.center = self.rect.center


         # --- Item Collision ---
         items_hit = pygame.sprite.spritecollide(self, self.game.items, False, pygame.sprite.collide_rect_ratio(0.8)) # Use rect collision for items
         for item in items_hit:
              if item.interact(self): # Let item handle interaction logic
                   if SAVE_ON_PICKUP:
                        self.game.save_game_state() # Auto-save on successful pickup

         # --- Monster Collision ---
         monsters_hit = pygame.sprite.spritecollide(self, self.game.monsters, False, pygame.sprite.collide_rect_ratio(0.7))
         for monster in monsters_hit:
             if not self.is_dead:
                  self.handle_monster_collision(monster)

         # --- Exit Collision ---
         exit_rect = self.game.maze.get_exit_rect()
         if exit_rect and self.hit_rect.colliderect(exit_rect):
              self.game.win_game()


    def handle_monster_collision(self, monster):
         if self.inventory['weapons']:
             weapon = self.inventory['weapons'][0] # Use the first acquired weapon
             print(f"Player uses {weapon.weapon_type} sword on {monster.name}")
             monster.take_damage()
             weapon.uses -= 1
             if weapon.uses <= 0:
                  print(f"{weapon.weapon_type} sword broke!")
                  self.game.asset_manager.play_sound('weapon_break')
                  self.inventory['weapons'].pop(0) # Remove broken weapon
         else:
             print("Player touched by monster and has no weapon!")
             self.die("被怪物抓住了")


    def update(self, dt):
        if self.is_dead:
            return

        self.get_input()
        self.move(dt)

        # Update timers and stats
        self.update_hunger(dt)
        self.update_matches(dt)
        self.update_speed_boost(dt)
        self.update_magic_match(dt)

        # Check death conditions
        if self.hunger <= 0:
            self.die("饿死了")
        if self.current_match_index == -1: # No matches left to burn
             self.match_out_timer += dt * FPS # dt is fraction of second, need frames
             if self.match_out_timer >= MATCH_OUT_DEATH_TIMER_FRAMES:
                  self.die("在黑暗中迷失了")
        else:
             self.match_out_timer = 0 # Reset timer if player has matches

        # Hunger warning effect
        if self.hunger / PLAYER_MAX_HUNGER * 100 < PLAYER_HUNGER_WARN_THRESHOLD:
             self.hunger_warn_timer += dt * FPS
             if self.hunger_warn_timer >= PLAYER_HUNGER_WARN_INTERVAL:
                  self.hunger_warn_timer = 0
                  self.game.asset_manager.play_sound('hunger_growl')
                  # Add visual effect here if needed (e.g., spawning a short-lived effect sprite)
                  # print("Grumble...") # Placeholder


    def update_hunger(self, dt):
        self.hunger_decay_timer += dt * FPS
        if self.hunger_decay_timer >= PLAYER_HUNGER_DECAY_INTERVAL:
            self.hunger_decay_timer = 0
            self.hunger = max(0, self.hunger - PLAYER_HUNGER_DECAY_RATE)
            # print(f"Hunger: {self.hunger}")

    def update_matches(self, dt):
        if self.current_match_index != -1:
            self.matches[self.current_match_index] -= dt * FPS
            if self.matches[self.current_match_index] <= 0:
                print("A match burned out!")
                self.matches.pop(self.current_match_index)
                self.current_match_index = len(self.matches) - 1 # Move to the next one (new rightmost)
                if self.current_match_index == -1:
                    print("All matches burned out!")
                    self.game.asset_manager.play_sound('match_burn', loops=0) # Stop burning sound?
                    # Start death timer in update()

    def update_speed_boost(self, dt):
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt * FPS
            if self.speed_boost_timer <= 0:
                self.speed_boost_timer = 0
                self.speed_boost_factor = 1.0
                self.current_speed = self.base_speed
                print("Speed boost expired.")

    def update_magic_match(self, dt):
        if self.magic_match_timer > 0:
             self.magic_match_timer -= dt * FPS
             if self.magic_match_timer <= 0:
                  self.magic_match_timer = 0
                  print("Match magic expired.")


    def add_hunger(self, amount):
        self.hunger = min(PLAYER_MAX_HUNGER, self.hunger + amount)
        print(f"Ate food. Hunger: {self.hunger}/{PLAYER_MAX_HUNGER}")

    def add_match(self):
        # Add new match to the left (index 0 conceptually)
        # Since we burn from right (highest index), adding means inserting at 0 logically,
        # but our list represents right-to-left burning order. So, append and adjust index.
        self.matches.append(MATCH_BURN_TIME_FRAMES)
        # If this is the *only* match, start burning it
        if self.current_match_index == -1:
            self.current_match_index = 0
            self.game.asset_manager.play_sound('match_burn', loops=-1) # Start burning sound loop
        print(f"Picked up a match. Total matches: {len(self.matches)}")


    def add_weapon(self, weapon_item):
        # Add weapon to the end of the list (represents acquisition order)
        self.inventory['weapons'].append(weapon_item)
        print(f"Picked up weapon: {weapon_item.weapon_type}, Uses: {weapon_item.uses}. Total weapons: {len(self.inventory['weapons'])}")

    def apply_speed_boost(self, factor, duration_frames):
        self.speed_boost_factor = factor
        self.speed_boost_timer = duration_frames
        self.current_speed = self.base_speed * self.speed_boost_factor
        print(f"Speed boost applied! Speed: {self.current_speed / TILE_SIZE * FPS:.1f} m/s")

    def get_current_match_burn_percentage(self):
         if self.current_match_index != -1 and len(self.matches) > 0:
             remaining = self.matches[self.current_match_index]
             return max(0.0, min(1.0, remaining / MATCH_BURN_TIME_FRAMES))
         return 0.0

    def get_current_match_remaining_frames(self):
         if self.current_match_index != -1 and len(self.matches) > 0:
              return self.matches[self.current_match_index]
         return 0

    def get_total_match_count(self):
        return len(self.matches)

    def has_magic_match_active(self):
         # Placeholder for magic item pickup
         # Example: Add a magic match item that sets this timer
         # self.magic_match_timer = MATCH_MAGIC_DURATION_FRAMES
         return self.magic_match_timer > 0

    def die(self, reason):
        if not self.is_dead:
             print(f"Player died: {reason}")
             self.is_dead = True
             self.death_reason = reason
             self.vel = pygame.Vector2(0, 0) # Stop moving
             self.game.asset_manager.play_sound('player_die')
             self.game.asset_manager.stop_music() # Stop background music
             # Optionally, stop other looping sounds like match burning