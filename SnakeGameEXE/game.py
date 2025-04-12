import pygame
import sys
import time
import random
from collections import deque
from settings import *
from sprites import Snake, Fruit, Corpse, Blinky, Pinky, Particle # Import necessary classes

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init() # Initialize the mixer
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font_small = get_font(24)
        self.font_large = get_font(64)
        self.font_medium = get_font(36)
        self.is_running = True
        self.game_state = STATE_PLAYING
        self.last_game_over_reason = ""
        self.rewind_available = True

        # Load assets
        self.load_assets()

        # Game specific variables
        self.start_time = time.time()
        self.game_timer = 0 # Elapsed game time in seconds
        self.last_move_time = 0
        self.last_fruit_spawn_time = 0
        self.last_gradual_heat_time = 0
        self.last_frenzy_start_time = -FRENZY_INTERVAL_SECONDS # Allow first frenzy sooner
        self.frenzy_active = False
        self.pinky_spawned = False

        # Rewind state storage (list of snapshots)
        self.history = deque(maxlen=int(REWIND_SECONDS * FPS / 2)) # Store state roughly every 0.5s worth of frames
        self.frames_since_last_snapshot = 0

        # Sound control for warning
        self.ghost_warning_playing = False
        self.last_ghost_warning_time = 0


        # Initialize game objects
        self.all_sprites = pygame.sprite.Group() # Optional: Use groups if preferred
        self.snake = None
        self.fruits = []
        self.corpses = []
        self.ghosts = []
        self.particles = []

        self.camera_offset_x = 0
        self.camera_offset_y = 0

    def load_assets(self):
        self.images = {
            'background': load_image('background.png', size=None, use_alpha=False), # Load bg without scaling initially
            # Sprite images are loaded within their respective classes
        }
        # Scale background to screen size or ensure it tiles
        if self.images['background']:
             # Option 1: Scale to fit screen (might distort if aspect ratio differs)
             # self.images['background'] = pygame.transform.scale(self.images['background'], (SCREEN_WIDTH, SCREEN_HEIGHT))
             # Option 2: Assume it's large enough or tile it (drawing logic handles tiling)
             pass # Keep original size for now

        self.sounds = {
            'pickup_normal': load_sound('pickup_normal.wav'),
            'pickup_healthy': load_sound('pickup_healthy.wav'),
            'pickup_bomb': load_sound('pickup_bomb.wav'),
            'split': load_sound('split.wav'),
            'merge': load_sound('merge.wav'),
            'death': load_sound('death.wav'),
            'rewind': load_sound('rewind.wav'),
            'ghost_warning': load_sound('ghost_warning.wav')
        }
        # Load and play BGM
        if load_music('bgm.ogg'):
            pygame.mixer.music.play(loops=-1) # Loop indefinitely
            pygame.mixer.music.set_volume(0.3) # Adjust volume (0.0 to 1.0)


    def play_sound(self, sound_name):
        sound = self.sounds.get(sound_name)
        if sound:
            sound.play()

    def try_play_sound(self, sound_name, unique=False, cooldown=1000):
        """Plays sound, optionally ensuring it doesn't spam."""
        sound = self.sounds.get(sound_name)
        if sound:
            if unique:
                 now = pygame.time.get_ticks()
                 if sound_name == 'ghost_warning':
                     if not self.ghost_warning_playing or now - self.last_ghost_warning_time > cooldown:
                         sound.play()
                         self.ghost_warning_playing = True
                         self.last_ghost_warning_time = now
                 # Add other unique sounds here if needed
            else:
                 sound.play()
        # Reset warning flag if player moves away (handled implicitly by distance check in ghost update)
        # Or add explicit reset logic if needed


    def reset_game(self):
        print("Resetting game...")
        # Clear lists and groups
        self.all_sprites.empty()
        self.fruits.clear()
        self.corpses.clear()
        self.ghosts.clear()
        self.particles.clear()
        self.history.clear() # Clear rewind history

        # Re-initialize game state
        self.snake = Snake(self)
        # Spawn initial fruit(s)
        self.spawn_fruit(count=2, force_special=True)

        # Spawn Blinky
        self.ghosts.append(Blinky(self))

        self.start_time = time.time()
        self.game_timer = 0
        self.last_move_time = 0
        self.last_fruit_spawn_time = time.time() # Reset spawn timer
        self.last_gradual_heat_time = time.time()
        self.last_frenzy_start_time = time.time() # Reset frenzy timer
        self.frenzy_active = False
        self.pinky_spawned = False
        self.rewind_available = True # Reset rewind availability
        self.last_game_over_reason = ""
        self.frames_since_last_snapshot = 0
        self.ghost_warning_playing = False # Reset warning sound flag

        self.game_state = STATE_PLAYING
        print("Game reset complete.")

    def get_current_speed(self):
        """Calculates the snake's current speed in grids per second."""
        # 1. Base Speed
        current_speed = BASE_SNAKE_SPEED_PPS

        # 2. Gradual Heat Bonus
        time_elapsed = self.game_timer
        heat_bonus = 1.0 + (GRADUAL_HEAT_INCREASE_PERCENT * (time_elapsed // GRADUAL_HEAT_INTERVAL_SECONDS))
        current_speed *= heat_bonus

        # 3. Frenzy Bonus
        frenzy_bonus = 1.0
        time_since_frenzy_start = time.time() - self.last_frenzy_start_time
        if self.frenzy_active:
            if time_since_frenzy_start < FRENZY_RAMP_UP_SECONDS:
                # Ramp up
                frenzy_bonus = 1.0 + FRENZY_PEAK_BONUS_PERCENT * (time_since_frenzy_start / FRENZY_RAMP_UP_SECONDS)
            elif time_since_frenzy_start < FRENZY_DURATION_SECONDS - FRENZY_RAMP_DOWN_SECONDS:
                # Peak
                frenzy_bonus = 1.0 + FRENZY_PEAK_BONUS_PERCENT
            elif time_since_frenzy_start < FRENZY_DURATION_SECONDS:
                 # Ramp down
                 time_left = FRENZY_DURATION_SECONDS - time_since_frenzy_start
                 frenzy_bonus = 1.0 + FRENZY_PEAK_BONUS_PERCENT * (time_left / FRENZY_RAMP_DOWN_SECONDS)
            else:
                # Frenzy ended
                self.frenzy_active = False
        current_speed *= frenzy_bonus

        # 4. Acceleration Button Bonus
        if self.snake.is_accelerating:
             current_speed *= ACCELERATION_FACTOR

        return current_speed

    def check_frenzy_state(self):
        """Checks if frenzy should start or end."""
        now = time.time()
        if not self.frenzy_active and (now - self.last_frenzy_start_time >= FRENZY_INTERVAL_SECONDS):
             self.frenzy_active = True
             self.last_frenzy_start_time = now
             print("FRENZY START!")
        elif self.frenzy_active and (now - self.last_frenzy_start_time >= FRENZY_DURATION_SECONDS):
             self.frenzy_active = False
             # last_frenzy_start_time remains the time it *actually* started for interval calculation
             print("FRENZY END!")


    def spawn_fruit(self, count=1, force_special=False):
        spawned_count = 0
        attempts = 0 # Prevent infinite loop if canvas is full
        max_attempts = (CANVAS_GRID_WIDTH * CANVAS_GRID_HEIGHT) * 2

        while spawned_count < count and len(self.fruits) < MAX_FRUITS and attempts < max_attempts:
            attempts += 1
            pos = (random.randint(0, CANVAS_GRID_WIDTH - 1),
                   random.randint(0, CANVAS_GRID_HEIGHT - 1))

            # Check if position is occupied by snake, other fruits, ghosts, or corpses
            occupied = False
            if self.snake and pos in self.snake.body:
                occupied = True
            if any(f.position == pos for f in self.fruits):
                occupied = True
            if any(g.grid_pos == pos for g in self.ghosts):
                 occupied = True
            if any(pos in c.segments for c in self.corpses):
                 occupied = True

            if not occupied:
                # Determine fruit type
                fruit_type = 'normal'
                lifespan = None
                img_name = 'fruit_normal.png'
                pickup_sound = 'pickup_normal'

                # Logic for special fruit spawning
                is_special = False
                if force_special and spawned_count == 0: # Ensure at least one special if forced
                    is_special = True
                elif random.random() < 0.3: # 30% chance for special otherwise
                    is_special = True

                if is_special:
                    choice = random.choice(['healthy', 'bomb'])
                    if choice == 'healthy':
                        fruit_type = 'healthy'
                        lifespan = HEALTHY_FRUIT_DURATION_SECONDS
                        img_name = 'fruit_healthy.png'
                        pickup_sound = 'pickup_healthy'
                    else: # Bomb
                         fruit_type = 'bomb'
                         lifespan = BOMB_FRUIT_DURATION_SECONDS
                         img_name = 'fruit_bomb.png'
                         pickup_sound = 'pickup_bomb' # Sound played on death though

                image = load_image(img_name, GRID_SIZE)
                self.fruits.append(Fruit(self, pos, fruit_type, image, lifespan))
                spawned_count += 1
                # print(f"Spawned {fruit_type} fruit at {pos}")


    def update_camera(self):
        """Centers the camera on the snake head, clamped to canvas boundaries."""
        head_x, head_y = self.snake.get_head_position()
        target_cam_x = head_x * GRID_SIZE - SCREEN_WIDTH / 2 + GRID_SIZE / 2
        target_cam_y = head_y * GRID_SIZE - SCREEN_HEIGHT / 2 + GRID_SIZE / 2

        # Clamp camera position to stay within canvas bounds
        max_cam_x = CANVAS_WIDTH_PX - SCREEN_WIDTH
        max_cam_y = CANVAS_HEIGHT_PX - SCREEN_HEIGHT

        self.camera_offset_x = max(0, min(target_cam_x, max_cam_x))
        self.camera_offset_y = max(0, min(target_cam_y, max_cam_y))


    def trigger_game_over(self, reason="unknown"):
         if self.game_state != STATE_GAME_OVER:
             print(f"Game Over! Reason: {reason}")
             self.last_game_over_reason = reason
             self.game_state = STATE_GAME_OVER
             self.snake.alive = False
             if reason == "bomb_collision":
                  self.play_sound('pickup_bomb') # Play bomb sound on collision
             else:
                  self.play_sound('death')


    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            if event.type == pygame.KEYDOWN:
                if self.game_state == STATE_PLAYING:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.snake.change_direction(UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.snake.change_direction(DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.snake.change_direction(LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.snake.change_direction(RIGHT)
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        self.snake.is_accelerating = True
                    elif event.key == pygame.K_SPACE:
                        new_corpse, success = self.snake.split()
                        if success:
                            self.corpses.append(new_corpse)
                    elif event.key == pygame.K_ESCAPE: # Optional: Pause Key
                         # self.game_state = STATE_PAUSED
                         self.is_running = False # Simple quit on escape for now
                elif self.game_state == STATE_GAME_OVER:
                    if event.key == pygame.K_r: # Check for 'R' key press for Replay
                        self.reset_game()
                    if event.key == pygame.K_t and self.rewind_available : # Check for 'T' key press for Rewind
                        self.attempt_rewind()


            if event.type == pygame.KEYUP:
                 if self.game_state == STATE_PLAYING:
                     if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                         self.snake.is_accelerating = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                 if self.game_state == STATE_GAME_OVER:
                      self.check_game_over_button_clicks(event.pos)


    def update(self, dt):
        if self.game_state != STATE_PLAYING:
            return # Don't update game logic if not playing

        # Update game timer
        self.game_timer = time.time() - self.start_time

        # Check and update frenzy state
        self.check_frenzy_state()

        # --- Snake Movement Timing ---
        speed = self.get_current_speed()
        if speed <= 0: return # Avoid division by zero or no movement
        move_interval = 1.0 / speed # Time in seconds between moves
        current_time = time.time()
        if current_time - self.last_move_time >= move_interval:
             self.snake.update() # Move snake one grid step
             self.last_move_time = current_time
             # Check for collisions after snake has potentially moved into a new cell
             self.check_fruit_collisions()
             self.check_corpse_merge()
             self.check_ghost_collisions() # Check collision with ghosts *after* moving

        # Check Pinky spawn condition
        if not self.pinky_spawned and self.snake.length >= PINKY_SPAWN_LENGTH:
            self.ghosts.append(Pinky(self))
            self.pinky_spawned = True
            print("Pinky has spawned!")

        # Update Ghosts
        for ghost in self.ghosts:
             ghost.update(dt, self.snake.body) # Pass delta time and snake body

        # Update Fruits (check lifespan)
        self.fruits[:] = [f for f in self.fruits if f.update()] # Keep active fruits

        # Update Corpses (flicker, fade, disappear)
        self.corpses[:] = [c for c in self.corpses if c.update()] # Keep active corpses

        # Update Particles
        self.particles[:] = [p for p in self.particles if p.update(dt)] # Keep active particles

        # Fruit Spawning Logic
        now = time.time()
        if now - self.last_fruit_spawn_time > FRUIT_SPAWN_INTERVAL_SECONDS:
            self.spawn_fruit()
            self.last_fruit_spawn_time = now
        # Force spawn if count is zero
        if len(self.fruits) == 0:
            self.spawn_fruit(count=2, force_special=True)
            self.last_fruit_spawn_time = now # Reset timer after force spawn


        # Update Camera based on snake head
        self.update_camera()

        # --- Rewind Snapshot ---
        self.frames_since_last_snapshot += 1
        # Store state less frequently than every frame for performance/memory
        snapshot_interval_frames = int(FPS * 0.25) # Snapshot every 0.25 seconds approx
        if self.frames_since_last_snapshot >= snapshot_interval_frames:
            self.save_state_for_rewind()
            self.frames_since_last_snapshot = 0


    def check_fruit_collisions(self):
        head_pos = self.snake.get_head_position()
        eaten_fruit_index = -1
        for i, fruit in enumerate(self.fruits):
            if fruit.position == head_pos:
                eaten_fruit_index = i
                # Apply effect
                if fruit.type == 'normal':
                    self.snake.grow(1)
                    self.play_sound('pickup_normal')
                elif fruit.type == 'healthy':
                    self.snake.grow(2) # Extra growth
                    self.play_sound('pickup_healthy')
                elif fruit.type == 'bomb':
                     self.trigger_game_over("bomb_collision")
                     # Sound is played in trigger_game_over
                break # Eat only one fruit per step

        if eaten_fruit_index != -1:
            del self.fruits[eaten_fruit_index]


    def check_ghost_collisions(self):
        if not self.snake.alive: return
        head_pos = self.snake.get_head_position()
        for ghost in self.ghosts:
            # Check if snake head occupies the same grid cell as the ghost
            if ghost.grid_pos == head_pos:
                 self.trigger_game_over(f"{ghost.type}_collision")
                 break # Game over, no need to check other ghosts


    def check_corpse_merge(self):
         if not self.snake.alive: return
         head_pos = self.snake.get_head_position()
         merged = False
         corpse_to_remove = None

         for i, corpse in enumerate(self.corpses):
             if not corpse.segments: continue # Skip empty corpses if possible

             first_seg, last_seg = corpse.get_end_points()

             if head_pos == first_seg or head_pos == last_seg:
                 print("Merge triggered!")
                 corpse_to_remove = i
                 merge_at_first = (head_pos == first_seg)

                 # Combine segments
                 if merge_at_first:
                      # Snake head hits corpse start. New body = snake body + corpse segments
                      new_body_list = list(self.snake.body) + list(corpse.segments)
                      # New head position is the end of the corpse
                      new_head_pos = last_seg
                      # New direction: from corpse's second-to-last towards last
                      if len(corpse.segments) > 1:
                           p_last_x, p_last_y = corpse.segments[-2]
                           last_x, last_y = corpse.segments[-1]
                           new_direction = (last_x - p_last_x, last_y - p_last_y)
                      else: # Corpse was single segment, maintain snake's direction? Risky. Reverse?
                          new_direction = self.snake.direction # Keep current direction maybe?

                 else: # Snake head hits corpse end. New body = corpse segments + snake body
                       new_body_list = list(corpse.segments) + list(self.snake.body)
                       # New head position is the start of the corpse
                       new_head_pos = first_seg
                       # New direction: from corpse's second towards first
                       if len(corpse.segments) > 1:
                            first_x, first_y = corpse.segments[0]
                            sec_x, sec_y = corpse.segments[1]
                            new_direction = (first_x - sec_x, first_y - sec_y) # Move towards the first segment
                       else: # Corpse was single segment
                            new_direction = self.snake.direction # Keep current direction


                 # Update snake
                 self.snake.body = deque(new_body_list)
                 self.snake.length = len(self.snake.body)
                 # Directly set the head position (overrides normal movement for this step)
                 self.snake.body[-1] = new_head_pos # Ensure the last element IS the new head pos
                 self.snake.direction = new_direction
                 self.snake.new_direction = new_direction # Sync buffered direction
                 self.snake.update_head_image()

                 self.play_sound('merge')
                 merged = True
                 break # Merge with only one corpse per step

         if corpse_to_remove is not None:
              del self.corpses[corpse_to_remove]


    def add_particles(self, grid_pos, count, color):
         """Adds particles originating from a grid cell."""
         pixel_pos = (grid_pos[0] * GRID_SIZE + GRID_SIZE // 2,
                      grid_pos[1] * GRID_SIZE + GRID_SIZE // 2)
         for _ in range(count):
              self.particles.append(Particle(self, pixel_pos, color))

    def draw_grid(self, surface):
        """Draws the semi-transparent grid over the visible area."""
        # Use camera offset to draw only the visible portion of the infinite grid
        start_col = int(self.camera_offset_x // GRID_SIZE)
        end_col = int((self.camera_offset_x + SCREEN_WIDTH) // GRID_SIZE) + 1
        start_row = int(self.camera_offset_y // GRID_SIZE)
        end_row = int((self.camera_offset_y + SCREEN_HEIGHT) // GRID_SIZE) + 1

        # Create a surface for the grid lines with alpha
        grid_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        grid_surface.fill((0,0,0,0)) # Transparent background

        for col in range(start_col, end_col + 1):
            x = col * GRID_SIZE - self.camera_offset_x
            if 0 <= x <= SCREEN_WIDTH:
                pygame.draw.line(grid_surface, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
        for row in range(start_row, end_row + 1):
            y = row * GRID_SIZE - self.camera_offset_y
            if 0 <= y <= SCREEN_HEIGHT:
                pygame.draw.line(grid_surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

        surface.blit(grid_surface, (0, 0))

    def draw_background(self, surface):
         """Draws the background, tiling if necessary."""
         bg_image = self.images.get('background')
         if not bg_image:
             surface.fill(BLACK) # Fallback color
             return

         bg_width = bg_image.get_width()
         bg_height = bg_image.get_height()

         # Calculate how many tiles are needed based on camera view
         # We need to draw sections of the background offset by the camera view
         # relative to the top-left of the potentially huge background image.

         # Find top-left corner of the background piece to draw on screen
         start_x = self.camera_offset_x % bg_width
         start_y = self.camera_offset_y % bg_height

         # Draw tiles covering the screen
         for x in range(-int(start_x), SCREEN_WIDTH, bg_width):
             for y in range(-int(start_y), SCREEN_HEIGHT, bg_height):
                 surface.blit(bg_image, (x, y))


    def draw_ui(self, surface):
        # Game Timer
        mins, secs = divmod(int(self.game_timer), 60)
        timer_text = f"时长: {mins:01d}:{secs:02d}"
        timer_surf = self.font_small.render(timer_text, True, WHITE)
        surface.blit(timer_surf, (10, 10))

        # Snake Length
        length_text = f"长度: {self.snake.length}"
        length_surf = self.font_small.render(length_text, True, WHITE)
        length_rect = length_surf.get_rect(topright=(SCREEN_WIDTH - 10, 10))
        surface.blit(length_surf, length_rect)

        # Split Button Indicator (Optional)
        split_color = WHITE if self.snake.split_available else GREY
        split_text = "分裂[空格]"
        split_surf = self.font_small.render(split_text, True, split_color)
        split_rect = split_surf.get_rect(bottomleft=(10, SCREEN_HEIGHT - 10))
        surface.blit(split_surf, split_rect)


    def draw_game_over_screen(self, surface):
        # Dim the background slightly
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # Semi-transparent black overlay
        surface.blit(overlay, (0, 0))

        # --- Texts ---
        title_surf = self.font_large.render("游戏结算", True, RED)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        surface.blit(title_surf, title_rect)

        score_text = f"最终长度: {self.snake.length}"
        score_surf = self.font_medium.render(score_text, True, WHITE)
        score_rect = score_surf.get_rect(center=(SCREEN_WIDTH // 2, title_rect.bottom + 50))
        surface.blit(score_surf, score_rect)

        # --- Buttons ---
        button_width = 250
        button_height = 60
        button_spacing = 30
        base_y = score_rect.bottom + 80

        # Replay Button
        self.replay_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - button_width - button_spacing // 2, base_y, button_width, button_height)
        pygame.draw.rect(surface, GREEN, self.replay_button_rect, border_radius=10)
        replay_text_surf = self.font_medium.render("重玩 (R)", True, BLACK)
        replay_text_rect = replay_text_surf.get_rect(center=self.replay_button_rect.center)
        surface.blit(replay_text_surf, replay_text_rect)

        # Rewind Button
        rewind_button_color = BLUE if self.rewind_available else GREY
        self.rewind_button_rect = pygame.Rect(SCREEN_WIDTH // 2 + button_spacing // 2, base_y, button_width, button_height)
        pygame.draw.rect(surface, rewind_button_color, self.rewind_button_rect, border_radius=10)
        rewind_text = "时光倒流 (T)" if self.rewind_available else "时光倒流 (已用)"
        rewind_text_surf = self.font_medium.render(rewind_text, True, BLACK)
        rewind_text_rect = rewind_text_surf.get_rect(center=self.rewind_button_rect.center)
        surface.blit(rewind_text_surf, rewind_text_rect)


    def check_game_over_button_clicks(self, mouse_pos):
         if self.replay_button_rect.collidepoint(mouse_pos):
             self.reset_game()
         elif self.rewind_button_rect.collidepoint(mouse_pos) and self.rewind_available:
             self.attempt_rewind()


    def draw(self):
        # Drawing order is important for layers
        # 1. Background
        self.draw_background(self.screen)

        # 2. Grid (Drawn on top of background)
        self.draw_grid(self.screen)

        # 3. Game Objects (Fruits, Corpses, Ghosts, Snake) - Apply camera offset
        cam_offset = (self.camera_offset_x, self.camera_offset_y)
        for fruit in self.fruits:
            fruit.draw(self.screen, cam_offset)
        for corpse in self.corpses:
             corpse.draw(self.screen, cam_offset)
        if self.snake: # Check if snake exists (it might not briefly during reset)
            self.snake.draw(self.screen, cam_offset) # Draw snake last so it's on top of its tail etc.
        for ghost in self.ghosts:
            ghost.draw(self.screen, cam_offset)
        for particle in self.particles:
             particle.draw(self.screen, cam_offset)


        # 4. UI (Score, Timer) - Drawn over everything, no offset
        if self.snake: # Draw UI only if snake exists
            self.draw_ui(self.screen)

        # 5. Game Over Screen (If applicable)
        if self.game_state == STATE_GAME_OVER:
            self.draw_game_over_screen(self.screen)

        # Update the display
        pygame.display.flip()


    def save_state_for_rewind(self):
        """Saves the current game state for potential rewind."""
        if not self.snake: return # Don't save if snake doesn't exist

        state = {
            'time': self.game_timer,
            'snake_body': self.snake.body.copy(), # Need copies!
            'snake_length': self.snake.length,
            'snake_direction': self.snake.direction,
            'snake_new_direction': self.snake.new_direction,
            'fruits': [(f.position, f.type, f.lifespan, f.creation_time) for f in self.fruits], # Store necessary info
            'corpses': [{'segments': c.segments.copy(), 'creation_time': c.creation_time} for c in self.corpses], # Store necessary info
            'ghosts': [{'pos': g.grid_pos, 'pixel_pos': list(g.pixel_pos), 'type': g.type, 'target': g.target_grid_pos} for g in self.ghosts], # Store pos & type
            'pinky_spawned': self.pinky_spawned,
            'frenzy_active': self.frenzy_active,
            'last_frenzy_start_time': self.last_frenzy_start_time,
            # Note: Camera offset is derived, no need to store. Speed is derived.
        }
        self.history.append(state)
        # print(f"Saved state. History size: {len(self.history)}")


    def attempt_rewind(self):
         if not self.rewind_available:
             print("Rewind not available.")
             return
         if not self.history:
              print("No history to rewind to.")
              return

         print("Attempting rewind...")
         try:
             # The most recent state in 'history' is the one from ~0.25s ago.
             # We want the state from REWIND_SECONDS ago.
             # Find the snapshot closest to (current_time - REWIND_SECONDS)
             target_time = self.game_timer - REWIND_SECONDS
             best_snapshot = None
             min_diff = float('inf')

             for snapshot in reversed(self.history): # Search backwards for efficiency
                 time_diff = abs(snapshot['time'] - target_time)
                 if time_diff < min_diff:
                     min_diff = time_diff
                     best_snapshot = snapshot
                 # Optimization: if we go too far back past the target time, stop searching
                 if snapshot['time'] < target_time - 2: # Allow some buffer
                     break

             if best_snapshot:
                  self.restore_state_from_rewind(best_snapshot)
                  self.rewind_available = False # Used the rewind
                  self.play_sound('rewind')
                  # Clear future history after rewind? Yes, like undo.
                  # Find index of restored state and clear everything after it.
                  # This is complex with deque. Simpler: Clear entire history after restore.
                  self.history.clear()
                  self.frames_since_last_snapshot = 0 # Reset snapshot counter
                  print("Rewind successful!")
             else:
                  print("Could not find suitable rewind point in history.")

         except Exception as e:
              print(f"Error during rewind: {e}")
              # Optionally try to reset or handle gracefully


    def restore_state_from_rewind(self, state):
        """Restores the game state from a saved snapshot."""
        self.game_timer = state['time']
        # self.start_time needs adjustment: self.start_time = time.time() - self.game_timer

        # Restore Snake
        self.snake.body = state['snake_body'].copy()
        self.snake.length = state['snake_length']
        self.snake.direction = state['snake_direction']
        self.snake.new_direction = state['snake_new_direction']
        self.snake.alive = True # Make sure snake is alive after rewind
        self.snake.update_head_image()

        # Restore Fruits
        self.fruits.clear()
        now = time.time()
        for pos, f_type, lifespan, creation_time in state['fruits']:
             # Check if fruit should still exist based on restored time vs lifespan
             if lifespan is None or (self.game_timer - (creation_time - (time.time() - self.game_timer)) < lifespan): # Estimate original game time of creation
                img_name = f'fruit_{f_type}.png'
                image = load_image(img_name, GRID_SIZE)
                restored_fruit = Fruit(self, pos, f_type, image, lifespan)
                restored_fruit.creation_time = creation_time # Restore original creation time
                self.fruits.append(restored_fruit)


        # Restore Corpses
        self.corpses.clear()
        for c_data in state['corpses']:
             # Check if corpse should still exist
             corpse_age = self.game_timer - (c_data['creation_time'] - (time.time() - self.game_timer))
             if corpse_age < CORPSE_LIFESPAN_SECONDS:
                 restored_corpse = Corpse(self, c_data['segments'].copy())
                 restored_corpse.creation_time = c_data['creation_time'] # Restore original time
                 # Recalculate flicker/fade based on restored time
                 restored_corpse.flicker_start_time = restored_corpse.creation_time + CORPSE_FLICKER_START_OFFSET
                 restored_corpse.flicker_end_time = restored_corpse.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS
                 restored_corpse.fade_start_time = restored_corpse.flicker_end_time
                 restored_corpse.fade_end_time = restored_corpse.fade_start_time + CORPSE_FADE_DURATION_SECONDS
                 self.corpses.append(restored_corpse)

        # Restore Ghosts
        self.ghosts.clear()
        self.pinky_spawned = state['pinky_spawned']
        for g_data in state['ghosts']:
            if g_data['type'] == 'Blinky':
                ghost = Blinky(self)
            elif g_data['type'] == 'Pinky':
                 ghost = Pinky(self)
            else: continue # Should not happen
            ghost.grid_pos = g_data['pos']
            ghost.pixel_pos = list(g_data['pixel_pos']) # Restore pixel pos too for smoothness
            ghost.target_grid_pos = g_data['target']
            self.ghosts.append(ghost)


        # Restore Frenzy State (Might be slightly off due to snapshot timing)
        self.frenzy_active = state['frenzy_active']
        self.last_frenzy_start_time = state['last_frenzy_start_time']


        # Reset timers that depend on current time
        self.last_move_time = time.time() # Prevent immediate move after rewind
        self.last_fruit_spawn_time = time.time() # Reset spawn timer


        # Crucially, change game state back to playing
        self.game_state = STATE_PLAYING


    def run(self):
        self.reset_game() # Start a new game when run is called

        while self.is_running:
            # Delta time calculation for frame-independent movement/updates
            dt = self.clock.tick(FPS) / 1000.0 # Time since last frame in seconds

            self.handle_input()
            if self.game_state == STATE_PLAYING:
                self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()