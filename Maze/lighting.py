import pygame
import math
from settings import *

class Lighting:
    def __init__(self, game):
        self.game = game
        self.visible_tiles = set() # Tiles currently lit (x, y)
        # Memory: Stores (x, y) -> (timestamp, initial_brightness)
        self.memory_tiles = {}
        self.light_walls = FOV_LIGHT_WALLS
        self.num_rays = FOV_NUM_RAYS
        self.fov_surface = pygame.Surface((WIDTH, HEIGHT)).convert_alpha() # For darkness overlay

    def calculate_fov(self, player):
        self.visible_tiles.clear()
        player_tile_x = int(player.pos.x // TILE_SIZE)
        player_tile_y = int(player.pos.y // TILE_SIZE)
        cx, cy = player.pos.x, player.pos.y # Center of light source (player center)

        current_match_count = player.get_total_match_count()
        if current_match_count == 0: # No light if no matches burning
             return

        radius = MATCH_RADIUS_LARGE_PX if current_match_count >= MATCH_COUNT_THRESHOLD_RADIUS else MATCH_RADIUS_SMALL_PX
        magic_active = player.has_magic_match_active()

        # Always add player's own tile
        self.visible_tiles.add((player_tile_x, player_tile_y))

        # Ray Casting
        for i in range(self.num_rays):
            angle = (i / self.num_rays) * 2 * math.pi
            dx = math.cos(angle)
            dy = math.sin(angle)

            x, y = cx, cy # Start ray from player center

            for step in range(int(radius)): # Iterate steps along the ray up to radius
                x += dx
                y += dy
                tile_x = int(x // TILE_SIZE)
                tile_y = int(y // TILE_SIZE)

                # Check bounds
                if not (0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT):
                    break # Ray went out of bounds

                # Add tile to visible set
                self.visible_tiles.add((tile_x, tile_y))

                # Check for wall collision (unless magic is active)
                if not magic_active and self.game.maze.is_wall(tile_x, tile_y):
                    if self.light_walls: # If we light walls, add it and stop
                         self.visible_tiles.add((tile_x, tile_y))
                    break # Stop ray if it hits a wall

    def update_memory(self):
        current_time = pygame.time.get_ticks()
        # Add newly visible tiles to memory
        for tile_pos in self.visible_tiles:
            # Update timestamp even if already in memory, keep it fresh
             self.memory_tiles[tile_pos] = (current_time, FOW_MEMORY_BRIGHTNESS) # Store initial memory brightness

        # Decay and remove old memory tiles
        to_remove = []
        for pos, (timestamp, initial_brightness) in self.memory_tiles.items():
            if pos not in self.visible_tiles: # Only decay tiles not currently visible
                age = current_time - timestamp
                if age >= FOW_FORGET_TIME_FRAMES * 1000: # Convert frames to ms
                    to_remove.append(pos)
                # Brightness decay calculation happens in get_tile_brightness

        for pos in to_remove:
            del self.memory_tiles[pos]


    def get_tile_brightness(self, x, y):
        """Returns the brightness level (0.0 to 1.0) for a given tile."""
        pos = (x, y)
        current_time = pygame.time.get_ticks()
        player = self.game.player

        # 1. Check if currently visible
        if pos in self.visible_tiles:
            # Calculate brightness based on match status
            remaining_frames = player.get_current_match_remaining_frames()
            total_frames = MATCH_BURN_TIME_FRAMES

            if remaining_frames <= 0: # No light source
                return 0.0

            base_brightness = 1.0
            # Apply brightness reduction based on remaining time
            for i in range(len(MATCH_LOW_THRESHOLDS_FRAMES)):
                if remaining_frames <= MATCH_LOW_THRESHOLDS_FRAMES[i]:
                    base_brightness = MATCH_LOW_BRIGHTNESS[i]
                    break # Use the first threshold met

            # Apply distance gradient effect
            dist_sq = (player.pos.x - (x * TILE_SIZE + TILE_SIZE / 2))**2 + \
                      (player.pos.y - (y * TILE_SIZE + TILE_SIZE / 2))**2
            max_radius = MATCH_RADIUS_LARGE_PX if player.get_total_match_count() >= MATCH_COUNT_THRESHOLD_RADIUS else MATCH_RADIUS_SMALL_PX
            dist_ratio = min(1.0, math.sqrt(dist_sq) / max_radius) if max_radius > 0 else 0

            brightness_reduction = 1.0 - base_brightness
            gradient_multiplier = 0.0

            last_radius_ratio = 0.0
            last_reduction_ratio = 0.0
            for radius_ratio_thresh, reduction_ratio_thresh in LIGHT_GRADIENT_STOPS:
                 if dist_ratio <= radius_ratio_thresh:
                      # Linear interpolation within this segment
                      segment_dist_ratio = (dist_ratio - last_radius_ratio) / (radius_ratio_thresh - last_radius_ratio) if (radius_ratio_thresh - last_radius_ratio) > 0 else 0
                      gradient_multiplier = last_reduction_ratio + segment_dist_ratio * (reduction_ratio_thresh - last_reduction_ratio)
                      break
                 last_radius_ratio = radius_ratio_thresh
                 last_reduction_ratio = reduction_ratio_thresh
            else: # If distance is beyond the last stop (shouldn't happen if radius check done right)
                 gradient_multiplier = 1.0


            final_brightness = base_brightness + (1.0 - base_brightness) * (1.0 - gradient_multiplier) # Apply reduction based on gradient
            # final_brightness = base_brightness * (1.0 - gradient_multiplier * brightness_reduction_factor) # Alternative approach
            return max(0.0, min(1.0, final_brightness))


        # 2. Check if in memory
        elif pos in self.memory_tiles:
            timestamp, initial_brightness = self.memory_tiles[pos]
            age_ms = current_time - timestamp
            age_frames = age_ms / (1000 / FPS) # Convert ms age to frames age

            # Check if player match is too low, suppressing memory
            if player.get_current_match_remaining_frames() < MATCH_MEMORY_FADE_THRESHOLD_FRAMES:
                 return 0.0 # Temporarily hide memory

            # Calculate decay based on age
            current_mem_brightness = initial_brightness
            for i in range(len(FOW_DECAY_TIMES_FRAMES)):
                 if age_frames >= FOW_DECAY_TIMES_FRAMES[i]:
                      current_mem_brightness = FOW_DECAY_BRIGHTNESS[i]
                      # Don't break, find the latest applicable decay level
            # Linearly interpolate between decay steps? More complex, maybe not needed.

            # Check if completely forgotten
            if age_frames >= FOW_FORGET_TIME_FRAMES:
                return 0.0

            return max(0.0, min(1.0, current_mem_brightness)) # Clamp brightness


        # 3. Not visible and not in memory
        else:
            return 0.0

    def draw_darkness(self, surface, camera, player):
         """Draws the overall darkness effect, potentially replacing tile-by-tile brightness."""
         # This is an alternative/complementary way to handle overall dimming
         # Simpler approach: Just rely on get_tile_brightness for tile rendering alpha.

         # More complex: Draw a large overlay surface centered on player
         self.fov_surface.fill((0, 0, 0, 255)) # Start fully dark

         # Get current light parameters
         remaining_frames = player.get_current_match_remaining_frames()
         if remaining_frames <= 0:
              surface.blit(self.fov_surface, (0,0)) # Full darkness if no light
              return

         max_radius = MATCH_RADIUS_LARGE_PX if player.get_total_match_count() >= MATCH_COUNT_THRESHOLD_RADIUS else MATCH_RADIUS_SMALL_PX
         base_brightness = 1.0
         for i in range(len(MATCH_LOW_THRESHOLDS_FRAMES)):
              if remaining_frames <= MATCH_LOW_THRESHOLDS_FRAMES[i]:
                   base_brightness = MATCH_LOW_BRIGHTNESS[i]
                   break

         # Calculate the screen position of the player
         player_screen_pos = camera.apply_sprite(player).center

         # --- Gradient Darkness Implementation ---
         # Draw concentric circles of decreasing transparency (increasing darkness)
         # This simulates the LIGHT_GRADIENT_STOPS logic on a full surface

         max_alpha = int((1.0 - base_brightness) * 255) # Max darkness alpha

         last_radius_ratio = 0.0
         last_reduction_ratio = 0.0
         num_gradient_steps = 20 # More steps = smoother gradient

         current_full_radius = max_radius # The actual lit radius in pixels

         # Draw the gradient from outside in
         for i in range(num_gradient_steps, -1, -1):
              dist_ratio = i / num_gradient_steps # Ratio from 0 to 1

              # Find the corresponding darkness multiplier based on design
              gradient_multiplier = 0.0
              _last_r = 0.0
              _last_red = 0.0
              for r_thresh, red_thresh in LIGHT_GRADIENT_STOPS:
                   if dist_ratio <= r_thresh:
                        seg_dist_ratio = (dist_ratio - _last_r) / (r_thresh - _last_r) if (r_thresh - _last_r) > 0 else 0
                        gradient_multiplier = _last_red + seg_dist_ratio * (red_thresh - _last_red)
                        break
                   _last_r = r_thresh
                   _last_red = red_thresh
              else:
                   gradient_multiplier = 1.0 # Full reduction multiplier outside last stop

              # Calculate alpha for this circle (higher multiplier = darker)
              current_alpha = int(gradient_multiplier * max_alpha)
              current_radius = int(dist_ratio * current_full_radius)

              if current_radius > 0 and current_alpha > 0:
                  # Draw a transparent circle - erasing darkness
                  # Use SRCALPHA blend mode? Or just draw alpha circle?
                  # Let's try drawing solid color circle with alpha onto the darkness surface
                   circle_color = (0, 0, 0, 255 - int(base_brightness * (1-gradient_multiplier) * 255)) # Problematic calculation?
                   # Alternative: Calculate the needed alpha to *reveal* underlying layer
                   # Alpha = 255 means opaque overlay, 0 means transparent overlay
                   # We want overlay alpha to be high far away, low near center
                   overlay_alpha = int(gradient_multiplier * max_alpha)
                   overlay_alpha = max(0, min(255, overlay_alpha))

                   # Draw a circle with this overlay alpha on the FOV surface
                   # Need a temporary surface for the circle itself?
                   temp_circle_surf = pygame.Surface((current_radius*2, current_radius*2), pygame.SRCALPHA)
                   pygame.draw.circle(temp_circle_surf, (0, 0, 0, overlay_alpha), (current_radius, current_radius), current_radius)
                   # Blit this circle centered onto the main fov_surface, but need to erase darkness...

         # --- Simpler approach: Draw a light circle ---
         # Create a temporary surface for the light circle
         light_radius = int(max_radius)
         light_surf = pygame.Surface((light_radius * 2, light_radius * 2), pygame.SRCALPHA)
         # Draw gradient light on this surface (transparent center, opaque edges?) No, opaque center, transparent edges
         for i in range(light_radius, 0, -5): # Draw from out to in, radius i
              dist_ratio = i / light_radius
              # Calculate brightness at this radius (inverse of darkness multiplier)
              gradient_multiplier = 0.0
              _last_r = 0.0
              _last_red = 0.0
              for r_thresh, red_thresh in LIGHT_GRADIENT_STOPS:
                   if dist_ratio <= r_thresh:
                        seg_dist_ratio = (dist_ratio - _last_r) / (r_thresh - _last_r) if (r_thresh - _last_r) > 0 else 0
                        gradient_multiplier = _last_red + seg_dist_ratio * (red_thresh - _last_red)
                        break
                   _last_r = r_thresh
                   _last_red = red_thresh
              else:
                   gradient_multiplier = 1.0

              # Brightness = base * (1 - gradient_multiplier * (1-base)/base) ? Simpler:
              current_brightness = base_brightness + (1.0 - base_brightness) * (1.0 - gradient_multiplier)
              alpha = int(current_brightness * 255)
              alpha = max(0, min(255, alpha))
              pygame.draw.circle(light_surf, (255, 255, 255, alpha), (light_radius, light_radius), i)


         # Blit the light circle onto the dark surface using BLEND_RGBA_MULT ? or just draw it?
         # Draw black everywhere
         self.fov_surface.fill((0, 0, 0, 255))
         # Cut out the light circle
         light_rect = light_surf.get_rect(center=player_screen_pos)
         self.fov_surface.blit(light_surf, light_rect, special_flags=pygame.BLEND_RGBA_SUB) # Subtract light alpha from darkness


         # Finally, blit the resulting fov_surface onto the main screen
         surface.blit(self.fov_surface, (0,0))


    def update(self, player):
        self.calculate_fov(player)
        self.update_memory()