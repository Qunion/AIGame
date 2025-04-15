import pygame
import random
from settings import *
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

class Tile:
    def __init__(self, x, y, is_wall):
        self.x = x
        self.y = y
        self.is_wall = is_wall
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        # FoW related attributes will be managed by Lighting class

class Maze:
    def __init__(self, game, width, height):
        self.game = game
        self.width = width
        self.height = height
        self.grid_cells = [[Tile(x, y, True) for y in range(height)] for x in range(width)] # Start all as walls
        self.exit_pos = None
        self.player_start_pos = None
        self._generate_maze()
        self._add_loops(int(width * height * 0.05)) # Remove 5% of walls randomly for loops
        self.pathfinding_grid_matrix = self._create_pathfinding_matrix()
        self.pathfinding_grid = Grid(matrix=self.pathfinding_grid_matrix)
        self.finder = AStarFinder()
        self.place_exit()
        self.player_start_pos = self.get_random_floor_tile()


    def _is_valid(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def _generate_maze(self):
        print("Generating maze...")
        start_x, start_y = random.randint(0, self.width // 2 - 1) * 2 + 1, random.randint(0, self.height // 2 - 1) * 2 + 1
        self.grid_cells[start_x][start_y].is_wall = False
        stack = [(start_x, start_y)]
        visited = set([(start_x, start_y)])

        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
                nx, ny = cx + dx, cy + dy
                if self._is_valid(nx, ny) and self.grid_cells[nx][ny].is_wall:
                     # Check if neighbor is within bounds and is a wall that hasn't been visited indirectly
                    wall_x, wall_y = cx + dx // 2, cy + dy // 2
                    if self._is_valid(wall_x, wall_y): # Ensure wall is valid
                         neighbors.append((nx, ny, wall_x, wall_y))

            if neighbors:
                nx, ny, wall_x, wall_y = random.choice(neighbors)
                if (nx, ny) not in visited:
                    self.grid_cells[nx][ny].is_wall = False
                    self.grid_cells[wall_x][wall_y].is_wall = False
                    visited.add((nx, ny))
                    stack.append((nx, ny))
                else:
                    # This case should ideally not happen often in standard DFS maze gen
                    # If neighbor was visited, try another neighbor
                    # If all neighbors visited, pop from stack (handled below)
                    pass # Just continue loop to potentially pop

            else:
                stack.pop()
        print("Maze generation complete.")


    def _add_loops(self, num_loops):
        print(f"Adding {num_loops} loops...")
        added = 0
        attempts = 0
        max_attempts = num_loops * 10 # Prevent infinite loop if finding walls is hard

        while added < num_loops and attempts < max_attempts:
             attempts += 1
             x = random.randint(1, self.width - 2)
             y = random.randint(1, self.height - 2)

             # Check if it's an internal wall candidate
             if self.grid_cells[x][y].is_wall:
                 # Check if removing it connects two separate passages
                 is_horizontal_wall = (not self.grid_cells[x-1][y].is_wall and not self.grid_cells[x+1][y].is_wall) and \
                                      (self.grid_cells[x][y-1].is_wall and self.grid_cells[x][y+1].is_wall)
                 is_vertical_wall = (self.grid_cells[x-1][y].is_wall and self.grid_cells[x+1][y].is_wall) and \
                                    (not self.grid_cells[x][y-1].is_wall and not self.grid_cells[x][y+1].is_wall)

                 if is_horizontal_wall or is_vertical_wall:
                      self.grid_cells[x][y].is_wall = False
                      added += 1
        print(f"Added {added} loops.")


    def is_wall(self, x, y):
        if not self._is_valid(x, y):
            return True # Treat out of bounds as wall
        return self.grid_cells[x][y].is_wall

    def get_tile(self, x, y):
         if not self._is_valid(x, y):
             return None
         return self.grid_cells[x][y]

    def draw(self, surface, camera, lighting):
        cam_rect = camera.get_view_rect()
        # Determine visible tile range based on camera view
        start_col = max(0, cam_rect.left // TILE_SIZE)
        end_col = min(self.width, (cam_rect.right + TILE_SIZE -1) // TILE_SIZE)
        start_row = max(0, cam_rect.top // TILE_SIZE)
        end_row = min(self.height, (cam_rect.bottom + TILE_SIZE -1)// TILE_SIZE)

        wall_img = self.game.asset_manager.get_image('wall')
        floor_img = self.game.asset_manager.get_image('floor')
        exit_img = self.game.asset_manager.get_image('exit')

        for x in range(start_col, end_col):
            for y in range(start_row, end_row):
                tile = self.grid_cells[x][y]
                screen_pos = camera.apply(tile) # Get screen position via camera

                brightness = lighting.get_tile_brightness(x, y)

                if brightness > 0: # If visible or in memory
                    is_currently_visible = (x, y) in lighting.visible_tiles

                    if tile.is_wall:
                         if lighting.light_walls or is_currently_visible: # Only draw walls if lit or currently visible
                             img = wall_img
                         else:
                              continue # Don't draw walls that are only in memory unless light_walls is True
                    else: # Floor
                         img = floor_img
                         if (x, y) == self.exit_pos and exit_img:
                              img = exit_img # Draw exit image on floor tile

                    if img:
                        # Apply brightness / memory alpha
                        temp_surf = img.copy()
                        alpha = int(brightness * 255)

                        # Use alpha for memory, potentially tint for current light level?
                        # Simple approach: use alpha for both memory and current light dimming
                        temp_surf.set_alpha(alpha)
                        surface.blit(temp_surf, screen_pos.topleft)

                # Optional: Draw black rect for absolutely unseen areas within view?
                # else:
                #     pygame.draw.rect(surface, BLACK, (screen_pos.x, screen_pos.y, TILE_SIZE, TILE_SIZE))


    def get_random_floor_tile(self):
        while True:
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            if not self.grid_cells[x][y].is_wall:
                # Return center of the tile in world coordinates
                return (x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2)

    def place_exit(self):
         edge_tiles = []
         for x in range(self.width):
              if not self.grid_cells[x][0].is_wall: edge_tiles.append((x, 0))
              if not self.grid_cells[x][self.height - 1].is_wall: edge_tiles.append((x, self.height - 1))
         for y in range(1, self.height - 1):
              if not self.grid_cells[0][y].is_wall: edge_tiles.append((0, y))
              if not self.grid_cells[self.width - 1][y].is_wall: edge_tiles.append((self.width - 1, y))

         if edge_tiles:
             self.exit_pos = random.choice(edge_tiles)
             print(f"Exit placed at: {self.exit_pos}")
         else:
              print("WARNING: Could not find valid edge tile for exit! Placing randomly.")
              # Fallback: place randomly on any floor tile if edge placement fails
              random_pos_world = self.get_random_floor_tile()
              self.exit_pos = (int(random_pos_world[0] // TILE_SIZE), int(random_pos_world[1] // TILE_SIZE))


    def get_exit_rect(self):
        if self.exit_pos:
            return pygame.Rect(self.exit_pos[0] * TILE_SIZE, self.exit_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        return None

    def _create_pathfinding_matrix(self):
        # 0 = wall, 1 = floor (walkable) for pathfinding lib
        matrix = [[1 if not self.grid_cells[x][y].is_wall else 0 for y in range(self.height)] for x in range(self.width)]
        return matrix

    def update_pathfinding_grid(self):
         # In case walls change dynamically (not in this design, but good practice)
         # self.pathfinding_grid_matrix = self._create_pathfinding_matrix()
         self.pathfinding_grid = Grid(matrix=self.pathfinding_grid_matrix)

    def find_path(self, start_pos_world, end_pos_world):
        start_tile = (int(start_pos_world.x // TILE_SIZE), int(start_pos_world.y // TILE_SIZE))
        end_tile = (int(end_pos_world.x // TILE_SIZE), int(end_pos_world.y // TILE_SIZE))

        # Ensure start and end are valid grid coordinates and walkable
        start_node = self.pathfinding_grid.node(start_tile[0], start_tile[1])
        end_node = self.pathfinding_grid.node(end_tile[0], end_tile[1])

        # Check if nodes are walkable (pathfinding lib uses 0 for wall, 1 for floor)
        if not start_node or not self.pathfinding_grid_matrix[start_node.y][start_node.x]:
            # print(f"Start node {start_tile} is invalid or a wall.")
            return None, float('inf')
        if not end_node or not self.pathfinding_grid_matrix[end_node.y][end_node.x]:
             # Allow targeting walls for prediction, but path may fail later
             # print(f"End node {end_tile} is invalid or a wall.")
             # Return something to indicate target is bad? Or let finder handle it.
             pass


        self.pathfinding_grid.cleanup() # Important before finding a new path
        try:
            path, runs = self.finder.find_path(start_node, end_node, self.pathfinding_grid)
            # Convert path back to world coordinates (center of tiles)
            world_path = [( (node.x * TILE_SIZE + TILE_SIZE // 2), (node.y * TILE_SIZE + TILE_SIZE // 2) ) for node in path]
            # print(f"Path found from {start_tile} to {end_tile}: {len(path)} steps")
            return world_path, len(path) # Return path and length (distance)
        except Exception as e:
             # Handles cases like target unreachable etc. Pathfinding lib might raise errors.
             # print(f"Pathfinding error from {start_tile} to {end_tile}: {e}")
             return None, float('inf')