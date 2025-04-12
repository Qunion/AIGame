import pygame
import random
import time
from settings import *
from collections import deque
# Optional: Import pathfinding library if you use one
# from pathfinding.core.grid import Grid
# from pathfinding.finder.a_star import AStarFinder

# --- Snake Class ---
class Snake:
    def __init__(self, game):
        self.game = game
        self.grid_size = GRID_SIZE
        self.color = DARK_YELLOW
        self.body = deque() # Using deque for efficient pop/append from both ends
        self.direction = random.choice([UP, DOWN, LEFT, RIGHT])
        self.new_direction = self.direction
        self.length = INITIAL_SNAKE_LENGTH
        self.is_accelerating = False
        self.alive = True
        self.split_available = True # Can the snake split?

        # Load images
        self.head_image_orig = load_image('snake_head.png', self.grid_size)
        self.body_image = load_image('snake_body.png', self.grid_size)
        self.head_image = self.head_image_orig # Current head image (changes with rotation)

        # Initial position (center of the canvas)
        start_x = CANVAS_GRID_WIDTH // 2
        start_y = CANVAS_GRID_HEIGHT // 2
        for i in range(self.length):
            # Place initial segments behind the head based on initial direction
            segment_x = start_x - self.direction[0] * i
            segment_y = start_y - self.direction[1] * i
            self.body.appendleft((segment_x, segment_y)) # Add to the front (tail)

        self.update_head_image() # Rotate head initially

    def get_head_position(self):
        return self.body[-1] # Head is the last element

    def update(self):
        # Only change direction if it's not the opposite
        if self.new_direction[0] != -self.direction[0] or self.new_direction[1] != -self.direction[1]:
             self.direction = self.new_direction
             self.update_head_image() # Rotate head image when direction changes

        head_x, head_y = self.get_head_position()
        move_x, move_y = self.direction
        new_head = (head_x + move_x, head_y + move_y)

        # Check collisions before moving
        self.check_collisions(new_head)

        if self.alive:
            self.body.append(new_head) # Add new head

            # Remove tail if not growing
            if len(self.body) > self.length:
                self.body.popleft() # Remove tail segment

        # Update split availability
        self.split_available = self.length >= SPLIT_MIN_LENGTH


    def update_head_image(self):
        """Rotates the head image based on the current direction."""
        angle = 0
        if self.direction == UP:
            angle = 0
        elif self.direction == DOWN:
            angle = 180
        elif self.direction == LEFT:
            angle = 90
        elif self.direction == RIGHT:
            angle = -90
        self.head_image = pygame.transform.rotate(self.head_image_orig, angle)


    def grow(self, amount=1):
        self.length += amount

    def change_direction(self, new_dir):
        # Buffer the direction change to prevent 180 degree turns in one step
        # Only accept if it's not the direct opposite of the current direction
        if (new_dir[0] != -self.direction[0] or new_dir[1] != -self.direction[1]):
           self.new_direction = new_dir


    def check_collisions(self, new_head):
        head_x, head_y = new_head

        # 1. Canvas Boundaries
        if not (0 <= head_x < CANVAS_GRID_WIDTH and 0 <= head_y < CANVAS_GRID_HEIGHT):
            self.alive = False
            self.game.trigger_game_over("wall_collision")
            return

        # 2. Self Collision (check against all segments except the potential new head)
        # Check against body segments excluding the tail if it's about to be removed
        check_body = list(self.body)
        if len(self.body) >= self.length: # If not growing, tail will pop
             check_body = check_body[1:]
        if new_head in check_body:
             self.alive = False
             self.game.trigger_game_over("self_collision")
             return

        # 3. Ghost Collision (checked in main game loop)
        # 4. Bomb Fruit Collision (checked in main game loop)
        # 5. Corpse Collision for Merge (checked in main game loop)


    def draw(self, surface, camera_offset):
        offset_x, offset_y = camera_offset

        # Draw body segments with gradient alpha
        num_segments = len(self.body)
        for i, segment in enumerate(self.body):
            seg_x, seg_y = segment
            pixel_x = seg_x * self.grid_size - offset_x
            pixel_y = seg_y * self.grid_size - offset_y

            # Check if segment is within screen bounds before drawing
            if -self.grid_size < pixel_x < SCREEN_WIDTH and -self.grid_size < pixel_y < SCREEN_HEIGHT:
                if i == num_segments - 1: # Head segment
                    surface.blit(self.head_image, (pixel_x, pixel_y))
                else: # Body segment
                    alpha = max(0, 255 * (1 - (num_segments - 1 - i) * SNAKE_ALPHA_DECREASE_PER_SEGMENT))
                    body_copy = self.body_image.copy()
                    body_copy.set_alpha(int(alpha))
                    surface.blit(body_copy, (pixel_x, pixel_y))

        # --- Draw Speed Lines (if accelerating) ---
        if self.is_accelerating and self.alive:
            head_x, head_y = self.get_head_position()
            pixel_x = head_x * self.grid_size - offset_x + self.grid_size // 2
            pixel_y = head_y * self.grid_size - offset_y + self.grid_size // 2
            num_lines = 5
            line_length = self.grid_size * 1.5
            line_speed_offset = self.grid_size * 0.8 # How far back lines start

            # Calculate backward direction
            back_dir_x, back_dir_y = -self.direction[0], -self.direction[1]
            # Calculate perpendicular directions for spread
            perp_dir_x, perp_dir_y = -back_dir_y, back_dir_x

            for i in range(num_lines):
                spread_factor = (i - num_lines // 2) * 0.3 # Adjust spread
                start_x = pixel_x + back_dir_x * line_speed_offset + perp_dir_x * spread_factor * self.grid_size
                start_y = pixel_y + back_dir_y * line_speed_offset + perp_dir_y * spread_factor * self.grid_size
                end_x = start_x + back_dir_x * line_length
                end_y = start_y + back_dir_y * line_length

                # Check if line is roughly on screen
                if -line_length < start_x < SCREEN_WIDTH + line_length and -line_length < start_y < SCREEN_HEIGHT + line_length:
                   pygame.draw.line(surface, WHITE, (start_x, start_y), (end_x, end_y), 2)

    def split(self):
        if not self.split_available:
            return None, None # Cannot split

        split_index = len(self.body) // 2 # Integer division, head part gets more if odd

        corpse_segments = deque(list(self.body)[split_index:]) # Head part becomes corpse
        new_snake_body = deque(list(self.body)[:split_index])   # Tail part becomes new snake

        if not new_snake_body: # Cannot split if tail part is empty
            return None, None

        # Create Corpse
        corpse = Corpse(self.game, corpse_segments)

        # Modify current snake (becomes the tail part)
        self.body = new_snake_body
        self.length = len(self.body)

        # Determine new direction for the 'new' snake (original object)
        # It should move away from the split point (towards the original tail)
        if len(self.body) > 1:
            # Direction from second-to-last segment towards the last (new head)
            p_tail_x, p_tail_y = self.body[-2] # Penultimate tail segment
            tail_x, tail_y = self.body[-1]   # Actual new head (last segment of tail part)
            self.direction = (tail_x - p_tail_x, tail_y - p_tail_y)
        elif len(self.body) == 1:
             # If only one segment left, needs a direction. Use opposite of corpse's first move?
             # Let's try moving opposite to the original direction before split
             self.direction = (-self.direction[0], -self.direction[1]) # Reverse original direction
        self.new_direction = self.direction # Sync buffered direction
        self.update_head_image()

        self.game.play_sound('split')
        self.game.add_particles(corpse.segments[0], 15, RED) # Particles at split point

        return corpse, True # Return the created corpse object and success


# --- Corpse Class ---
class Corpse:
    def __init__(self, game, segments):
        self.game = game
        self.segments = segments # deque of (x, y) tuples
        self.grid_size = GRID_SIZE
        self.image = load_image('corpse.png', self.grid_size)
        self.creation_time = time.time()
        self.lifespan = CORPSE_LIFESPAN_SECONDS
        self.flicker_start_time = self.creation_time + CORPSE_FLICKER_START_OFFSET
        self.flicker_end_time = self.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS
        self.fade_start_time = self.flicker_end_time
        self.fade_end_time = self.fade_start_time + CORPSE_FADE_DURATION_SECONDS
        self.visible = True
        self.is_fading = False
        self.flicker_on = True
        self.last_flicker_toggle = 0
        self.flicker_interval = 150 # milliseconds

    def update(self):
        current_time = time.time()
        if current_time > self.fade_end_time:
            return False # Signal to remove this corpse

        self.is_fading = current_time > self.fade_start_time

        if self.flicker_start_time <= current_time < self.flicker_end_time:
            now_ms = pygame.time.get_ticks()
            if now_ms - self.last_flicker_toggle > self.flicker_interval:
                self.flicker_on = not self.flicker_on
                self.last_flicker_toggle = now_ms
            self.visible = self.flicker_on
        elif self.is_fading:
            self.visible = True # Ensure visible for fade calculation
        else:
            self.visible = True # Visible before flicker/fade

        return True # Still active

    def draw(self, surface, camera_offset):
        if not self.visible:
            return

        offset_x, offset_y = camera_offset
        alpha = 255

        if self.is_fading:
             fade_progress = (time.time() - self.fade_start_time) / CORPSE_FADE_DURATION_SECONDS
             alpha = max(0, 255 * (1 - fade_progress))

        img_copy = self.image.copy()
        img_copy.set_alpha(int(alpha))

        for seg_x, seg_y in self.segments:
            pixel_x = seg_x * self.grid_size - offset_x
            pixel_y = seg_y * self.grid_size - offset_y
            # Check if segment is within screen bounds before drawing
            if -self.grid_size < pixel_x < SCREEN_WIDTH and -self.grid_size < pixel_y < SCREEN_HEIGHT:
                surface.blit(img_copy, (pixel_x, pixel_y))

    def get_end_points(self):
        """Returns the grid coordinates of the two ends of the corpse."""
        if not self.segments:
            return None, None
        return self.segments[0], self.segments[-1]


# --- Fruit Base Class ---
class Fruit:
    def __init__(self, game, position, fruit_type, image, lifespan=None):
        self.game = game
        self.position = position
        self.type = fruit_type
        self.grid_size = GRID_SIZE
        self.image = image
        self.lifespan = lifespan # In seconds, None means infinite
        self.creation_time = time.time()
        self.is_special = fruit_type != 'normal'

    def update(self):
        if self.lifespan is not None:
            if time.time() - self.creation_time > self.lifespan:
                return False # Signal to remove this fruit
        return True # Still active

    def draw(self, surface, camera_offset):
        offset_x, offset_y = camera_offset
        pixel_x = self.position[0] * self.grid_size - offset_x
        pixel_y = self.position[1] * self.grid_size - offset_y

        # Check if fruit is within screen bounds before drawing
        if -self.grid_size < pixel_x < SCREEN_WIDTH and -self.grid_size < pixel_y < SCREEN_HEIGHT:
           surface.blit(self.image, (pixel_x, pixel_y))

# --- Specific Fruit Types (mostly handled by parameters in __init__) ---
# We can create subclasses if more distinct behavior is needed later.

# --- Ghost Base Class ---
class Ghost:
    def __init__(self, game, start_pos, image, speed_factor):
        self.game = game
        self.grid_pos = start_pos
        self.pixel_pos = [start_pos[0] * GRID_SIZE, start_pos[1] * GRID_SIZE]
        self.grid_size = GRID_SIZE
        self.image = image
        self.speed_factor = speed_factor # Relative to snake's BASE speed
        self.target_grid_pos = start_pos # Target grid cell
        self.last_target_update = 0
        self.current_path = [] # For A* pathfinding (optional)
        # Simple movement: Direction towards target
        self.move_direction = (0, 0) # (dx, dy) in grid units per move

    def get_speed(self):
        # Ghosts move relative to BASE snake speed, ignoring frenzy/heat/boost
        return BASE_SNAKE_SPEED_PPS * self.speed_factor * self.grid_size # Speed in pixels per second

    def update_target(self, snake_body):
        # This method will be overridden by subclasses (Blinky, Pinky)
        pass

    def update(self, dt, snake_body):
        current_time_ms = pygame.time.get_ticks()

        # Periodically update the target
        if current_time_ms - self.last_target_update > GHOST_TARGET_UPDATE_INTERVAL_MS:
            self.update_target(snake_body)
            self.last_target_update = current_time_ms
            # --- Simple Pathfinding: Move one step towards target ---
            if self.target_grid_pos:
                dx = self.target_grid_pos[0] - self.grid_pos[0]
                dy = self.target_grid_pos[1] - self.grid_pos[1]

                # Choose dominant direction
                if abs(dx) > abs(dy):
                    self.move_direction = (1 if dx > 0 else -1 if dx < 0 else 0, 0)
                elif abs(dy) > abs(dx):
                     self.move_direction = (0, 1 if dy > 0 else -1 if dy < 0 else 0)
                elif dx != 0: # If equal distance, prefer horizontal or vertical randomly? Or prioritize one? Let's prefer horizontal.
                    self.move_direction = (1 if dx > 0 else -1, 0)
                elif dy != 0:
                    self.move_direction = (0, 1 if dy > 0 else -1)
                else:
                    self.move_direction = (0,0) # Reached target (or target is current pos)
            else:
                self.move_direction = (0,0)

            # --- A* Pathfinding (More Complex - Requires pathfinding lib/implementation) ---
            # self.find_path(snake_body) # Pass obstacles if needed


        # --- Move the ghost ---
        speed_pixels_per_sec = self.get_speed()
        move_dist = speed_pixels_per_sec * dt # Pixels to move this frame

        # Calculate desired pixel position based on moving towards the next grid cell
        target_pixel_x = self.grid_pos[0] * self.grid_size
        target_pixel_y = self.grid_pos[1] * self.grid_size

        # If we have a direction, aim for the center of the *next* grid cell in that direction
        if self.move_direction != (0, 0):
            next_grid_x = self.grid_pos[0] + self.move_direction[0]
            next_grid_y = self.grid_pos[1] + self.move_direction[1]
            target_pixel_x = next_grid_x * self.grid_size
            target_pixel_y = next_grid_y * self.grid_size

        # Move towards the target pixel position
        delta_px = target_pixel_x - self.pixel_pos[0]
        delta_py = target_pixel_y - self.pixel_pos[1]
        dist_to_target = (delta_px**2 + delta_py**2)**0.5

        if dist_to_target > 0:
            # Normalize direction vector
            norm_dx = delta_px / dist_to_target
            norm_dy = delta_py / dist_to_target

            # Move, but don't overshoot the target pixel position for this step
            move_amount = min(move_dist, dist_to_target)
            self.pixel_pos[0] += norm_dx * move_amount
            self.pixel_pos[1] += norm_dy * move_amount


        # Update grid position based on pixel position (center of ghost)
        new_grid_x = int((self.pixel_pos[0] + self.grid_size / 2) // self.grid_size)
        new_grid_y = int((self.pixel_pos[1] + self.grid_size / 2) // self.grid_size)

        # Prevent moving outside canvas (should ideally not happen with A* or proper targetting)
        new_grid_x = max(0, min(CANVAS_GRID_WIDTH - 1, new_grid_x))
        new_grid_y = max(0, min(CANVAS_GRID_HEIGHT - 1, new_grid_y))

        # Check for collisions with obstacles before finalizing grid position (optional, A* handles this better)
        # Simplistic check: If the target grid cell is an obstacle, maybe don't move?
        # Needs a representation of obstacles (e.g., snake body, corpses)

        self.grid_pos = (new_grid_x, new_grid_y)


        # --- Ghost Warning Sound ---
        head_pos = snake_body[-1]
        dist_sq = (head_pos[0] - self.grid_pos[0])**2 + (head_pos[1] - self.grid_pos[1])**2
        if dist_sq <= GHOST_WARNING_DISTANCE_GRIDS**2:
             self.game.try_play_sound('ghost_warning', unique=True) # Play once per encounter maybe


    def draw(self, surface, camera_offset):
        offset_x, offset_y = camera_offset
        # Use pixel_pos for smooth movement drawing
        draw_x = self.pixel_pos[0] - offset_x
        draw_y = self.pixel_pos[1] - offset_y

        # Check if ghost is within screen bounds before drawing
        if -self.grid_size < draw_x < SCREEN_WIDTH and -self.grid_size < draw_y < SCREEN_HEIGHT:
            surface.blit(self.image, (draw_x, draw_y))

    # --- A* Pathfinding Placeholder ---
    # def find_path(self, snake_body):
    #     # Requires a grid representation with obstacles (walls, snake body, corpses)
    #     # Example using python-pathfinding library (install with pip install pathfinding)
    #     try:
    #         # 1. Create matrix (0=walkable, 1=obstacle)
    #         matrix = [[0 for _ in range(CANVAS_GRID_WIDTH)] for _ in range(CANVAS_GRID_HEIGHT)]
    #         # Mark snake body as obstacles (excluding head maybe?)
    #         for seg_x, seg_y in snake_body:
    #              if 0 <= seg_y < CANVAS_GRID_HEIGHT and 0 <= seg_x < CANVAS_GRID_WIDTH:
    #                 matrix[seg_y][seg_x] = 1
    #         # Mark corpses as obstacles
    #         for corpse in self.game.corpses:
    #             for seg_x, seg_y in corpse.segments:
    #                  if 0 <= seg_y < CANVAS_GRID_HEIGHT and 0 <= seg_x < CANVAS_GRID_WIDTH:
    #                     matrix[seg_y][seg_x] = 1

    #         grid = Grid(matrix=matrix)
    #         start = grid.node(self.grid_pos[0], self.grid_pos[1])
    #         end = grid.node(self.target_grid_pos[0], self.target_grid_pos[1])
    #         finder = AStarFinder() # Or DiagonalMovement.never if only orthogonal moves
    #         path, runs = finder.find_path(start, end, grid)
    #         self.current_path = path[1:] # Store path excluding current pos
    #         # print(f"Path found: {path}") # Debugging
    #         if self.current_path:
    #             next_step = self.current_path[0]
    #             self.move_direction = (next_step.x - self.grid_pos[0], next_step.y - self.grid_pos[1])
    #         else:
    #              self.move_direction = (0,0) # No path found or already at target

    #     except Exception as e:
    #         print(f"Pathfinding error: {e}")
    #         # Fallback to simple direct movement if A* fails
    #         dx = self.target_grid_pos[0] - self.grid_pos[0]
    #         dy = self.target_grid_pos[1] - self.grid_pos[1]
    #         # ... (rest of simple pathfinding logic) ...


# --- Blinky (Red Ghost) ---
class Blinky(Ghost):
    def __init__(self, game):
        start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
        image = load_image('ghost_blinky.png', GRID_SIZE)
        super().__init__(game, start_pos, image, GHOST_BASE_SPEED_FACTOR)
        self.type = "Blinky"

    def update_target(self, snake_body):
        if not snake_body: return
        # Target the middle segment of the snake
        mid_index = len(snake_body) // 2
        self.target_grid_pos = snake_body[mid_index]

# --- Pinky (Pink Ghost) ---
class Pinky(Ghost):
    def __init__(self, game):
        # Spawn at a random location, maybe try not to spawn directly on snake
        spawn_ok = False
        while not spawn_ok:
            start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
            if start_pos not in game.snake.body: # Simple check
                 spawn_ok = True

        image = load_image('ghost_pinky.png', GRID_SIZE)
        super().__init__(game, start_pos, image, GHOST_BASE_SPEED_FACTOR)
        self.type = "Pinky"

    def update_target(self, snake_body):
        if not snake_body: return
        head_pos = snake_body[-1]
        head_dir = self.game.snake.direction # Get snake's current direction

        # Calculate target 4 steps ahead
        target_x = head_pos[0] + head_dir[0] * PINKY_PREDICTION_DISTANCE
        target_y = head_pos[1] + head_dir[1] * PINKY_PREDICTION_DISTANCE

        # Clamp target to canvas boundaries
        target_x = max(0, min(CANVAS_GRID_WIDTH - 1, target_x))
        target_y = max(0, min(CANVAS_GRID_HEIGHT - 1, target_y))

        self.target_grid_pos = (target_x, target_y)

# --- Particle Class (for effects) ---
class Particle:
    def __init__(self, game, pos_px, color, size_range=(2, 5), vel_range=(-2, 2), lifespan_ms=500):
        self.game = game
        self.x, self.y = pos_px
        self.color = color
        self.size = random.uniform(size_range[0], size_range[1])
        self.vx = random.uniform(vel_range[0], vel_range[1]) * 60 # Adjust velocity based on FPS assumption
        self.vy = random.uniform(vel_range[0], vel_range[1]) * 60
        self.creation_time = pygame.time.get_ticks()
        self.lifespan = lifespan_ms
        self.alpha = 255

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 0.1 * 60 * dt # Simple gravity effect

        elapsed = pygame.time.get_ticks() - self.creation_time
        if elapsed > self.lifespan:
            return False # Signal removal

        # Fade out
        self.alpha = max(0, 255 * (1 - (elapsed / self.lifespan)))
        return True

    def draw(self, surface, camera_offset):
        if self.alpha <= 0: return

        offset_x, offset_y = camera_offset
        draw_x = int(self.x - offset_x)
        draw_y = int(self.y - offset_y)

        # Simple circle particle
        temp_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(temp_surface, (*self.color, int(self.alpha)), (int(self.size), int(self.size)), int(self.size))
        surface.blit(temp_surface, (draw_x - self.size, draw_y - self.size))

        # Alternative: Rect particle
        # rect = pygame.Rect(draw_x - self.size/2, draw_y - self.size/2, self.size, self.size)
        # Draw with alpha - need a surface if using basic shapes
        # s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        # s.fill((*self.color, int(self.alpha)))
        # surface.blit(s, rect.topleft)