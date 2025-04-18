import pygame
import random
import noise # 导入噪声库

from settings import *
from pathfinding.core.grid import Grid # 导入寻路库的 Grid 类
from pathfinding.finder.a_star import AStarFinder # 导入 A* 寻路算法
# 导入类型提示
from typing import Optional, Tuple, List, Dict, TYPE_CHECKING, Any # 添加 Dict, Any # 导入需要用到的类型提示

# --- 添加或修改这部分 ---
if TYPE_CHECKING:
    # 这部分代码只在类型检查时执行，避免运行时循环导入
    from main import Game
    from camera import Camera
    from lighting import Lighting
# --- 结束添加/修改部分 ---

# --- Sprite for Decorations --- (新类) ---
class Decoration(pygame.sprite.Sprite):
    """代表地图上的装饰物（如杂草）的精灵。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float], image: pygame.Surface):
        self._layer = DECORATION_LAYER # 设置装饰物图层
        # 只加入 all_sprites 组，不需要其他交互组
        self.groups = game.all_sprites
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.image = image
        self.rect = self.image.get_rect()
        self.pos = pygame.Vector2(pos) # 使用瓦片中心作为位置
        self.rect.center = self.pos

# --- 修改 Tile 类 ---
class Tile:
    """代表迷宫中的一个格子。"""
    def __init__(self, x: int, y: int, is_wall: bool):
        self.x = x              # 格子的网格 x 坐标
        self.y = y              # 格子的网格 y 坐标
        self.is_wall = is_wall  # 布尔值，标记是否为墙
        # 格子的像素矩形区域
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        # FoW（战争迷雾）相关的属性将由 Lighting 类管理
        # 新增属性
        self.biome_id: int = DEFAULT_BIOME_ID # 地形 ID
        self.decoration_id: Optional[str] = None # 装饰物 ID (例如 'weed_1')

# --- 修改 Maze 类 ---
class Maze:
    """管理迷宫的生成、绘制和寻路。"""
    def __init__(self, game: 'Game', width: int, height: int):
        self.game = game        # 游戏主对象的引用
        self.width = width      # 迷宫宽度（格子数）
        self.height = height    # 迷宫高度（格子数）
        # 初始化网格，所有格子默认为墙
        self.grid_cells = [[Tile(x, y, True) for y in range(height)] for x in range(width)]
        self.exit_pos: Optional[Tuple[int, int]] = None   # 出口位置 (网格坐标)
        # self.player_start_pos: Optional[Tuple[int, int]] = None # 玩家起始位置 (世界坐标)
        self.player_start_pos: Optional[Tuple[float, float]] = None # 世界坐标

        self._generate_maze()   # 调用迷宫生成算法  # 1. 生成基本路径
        # 随机移除一些墙壁以增加循环路径，提高复杂度 (例如移除 5% 的墙)
        self._add_loops(int(width * height * 0.05)) # 2. 增加循环
        self._assign_biomes()   # 3. 分配地形区域
        self._place_decorations() # 4. 放置装饰物 (杂草)

        # 创建用于 pathfinding 库的矩阵 (0=墙, 1=路)
        self.pathfinding_grid_matrix = self._create_pathfinding_matrix()
        # 创建 pathfinding 的 Grid 对象
        self.pathfinding_grid = Grid(matrix=self.pathfinding_grid_matrix)
        # 初始化 A* 寻路器
        self.finder = AStarFinder()
        # 放置出口
        self.place_exit()  # 5. 放置出口 (现在使用加权逻辑)
        # 获取一个随机的地面格子作为玩家出生点（世界坐标）
        self.player_start_pos = self.get_random_floor_tile()[1] # get_random_floor_tile 现在返回 (tile_coords, world_coords)

    def _is_valid(self, x: int, y: int) -> bool:
        """检查给定的网格坐标是否在迷宫范围内。"""
        return 0 <= x < self.width and 0 <= y < self.height

    def _generate_maze(self):
        """使用深度优先搜索（DFS）的回溯算法生成迷宫。"""
        print("正在生成迷宫...")
        # 选择一个随机的奇数坐标作为起点 (确保在墙之间开始)
        start_x = random.randint(0, self.width // 2 - 1) * 2 + 1
        start_y = random.randint(0, self.height // 2 - 1) * 2 + 1
        self.grid_cells[start_x][start_y].is_wall = False # 将起点设为通路
        stack = [(start_x, start_y)] # 用于回溯的栈
        visited = set([(start_x, start_y)]) # 记录访问过的格子

        while stack:
            cx, cy = stack[-1] # 获取当前格子坐标
            neighbors = [] # 存储有效的邻居格子（未访问过的，隔一堵墙的）
            # 检查四个方向（上、下、左、右），每次跳两格
            for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
                nx, ny = cx + dx, cy + dy # 邻居格子坐标
                # 检查邻居是否在界内且是墙
                if self._is_valid(nx, ny) and self.grid_cells[nx][ny].is_wall:
                    # 计算邻居和当前格子之间的墙的坐标
                    wall_x, wall_y = cx + dx // 2, cy + dy // 2
                    # 确保中间的墙也在界内（虽然通常是这样）
                    if self._is_valid(wall_x, wall_y):
                        neighbors.append((nx, ny, wall_x, wall_y)) # 添加有效邻居

            if neighbors:
                # 如果有未访问的邻居，随机选择一个
                nx, ny, wall_x, wall_y = random.choice(neighbors)
                if (nx, ny) not in visited:
                    # 将邻居格子和中间的墙都设为通路
                    self.grid_cells[nx][ny].is_wall = False
                    self.grid_cells[wall_x][wall_y].is_wall = False
                    visited.add((nx, ny)) # 标记邻居为已访问
                    stack.append((nx, ny)) # 将邻居压入栈，继续探索
                else:
                    # 如果选择的邻居已被访问（理论上标准DFS不应频繁发生），尝试下一个循环
                    pass
            else:
                # 如果当前格子没有未访问的邻居，从栈中弹出，进行回溯
                stack.pop()
        print("迷宫生成完毕。")


    def _add_loops(self, num_loops: int):
        """在生成的迷宫中随机移除一些墙壁，以创建循环路径。"""
        print(f"正在添加 {num_loops} 个循环路径...")
        added = 0 # 成功添加的循环数
        attempts = 0 # 尝试次数
        max_attempts = num_loops * 10 # 设置最大尝试次数，防止死循环

        while added < num_loops and attempts < max_attempts:
            attempts += 1
            # 随机选择一个内部格子 (避开边缘)
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)

            # 检查选中的格子是否是墙
            if self.grid_cells[x][y].is_wall:
                # 检查移除这面墙是否能连接两个不同的通道
                # 条件：左右是路 && 上下是墙 (水平通道间的墙)
                is_horizontal_wall = (not self.grid_cells[x-1][y].is_wall and not self.grid_cells[x+1][y].is_wall) and \
                                     (self.grid_cells[x][y-1].is_wall and self.grid_cells[x][y+1].is_wall)
                # 条件：上下是路 && 左右是墙 (垂直通道间的墙)
                is_vertical_wall = (self.grid_cells[x-1][y].is_wall and self.grid_cells[x+1][y].is_wall) and \
                                   (not self.grid_cells[x][y-1].is_wall and not self.grid_cells[x][y+1].is_wall)

                # 如果满足任一条件，则移除这面墙
                if is_horizontal_wall or is_vertical_wall:
                     self.grid_cells[x][y].is_wall = False
                     added += 1 # 成功添加一个循环
        print(f"成功添加 {added} 个循环路径。")

    def _assign_biomes(self):
        """使用 Perlin 噪声为每个格子分配地形 ID。"""
        print("正在分配地形区域...")
        # 对每个格子计算噪声值并分配 biome_id
        for x in range(self.width):
            for y in range(self.height):
                # 使用 noise.pnoise2 生成噪声值
                # / NOISE_SCALE 控制噪声的“缩放”或频率
                # octaves 控制细节层次
                # persistence 控制高频细节的幅度
                # lacunarity 控制频率倍增
                # base 是种子，确保每次运行生成不同但内部连续的噪声
                noise_val = noise.pnoise2(x / NOISE_SCALE,
                                          y / NOISE_SCALE,
                                          octaves=NOISE_OCTAVES,
                                          persistence=NOISE_PERSISTENCE,
                                          lacunarity=NOISE_LACUNARITY,
                                          base=NOISE_SEED)

                assigned_biome = DEFAULT_BIOME_ID # 默认地形
                # 根据阈值分配地形 ID (从低到高检查)
                biome_ids_sorted = sorted(BIOME_THRESHOLDS.keys()) # 获取排序后的 biome ID
                thresholds_sorted = sorted(BIOME_THRESHOLDS.items(), key=lambda item: item[1]) # 按阈值排序

                last_biome_id = DEFAULT_BIOME_ID
                found = False
                for biome_id, threshold in thresholds_sorted:
                    if noise_val < threshold:
                        assigned_biome = biome_id
                        found = True
                        break
                    last_biome_id = biome_id # 记录最后一个检查的biome ID

                # 如果噪声值大于所有阈值，则分配最高 ID 的地形（或下一个 ID？）
                if not found:
                     # 假设 ID 是连续的，分配最后一个检查的 ID + 1？
                     # 或者直接分配 NUM_BIOMES？
                     # 确保 NUM_BIOMES 与 BIOME_THRESHOLDS 键的数量匹配
                     # 如果 BIOME_THRESHOLDS = {1: -0.1, 2: 0.2}, 那么 ID 应该是 1, 2, 3
                     # 找到最后一个阈值对应的 ID
                     if thresholds_sorted:
                         highest_threshold_id = thresholds_sorted[-1][0]
                         # 假设 ID 连续
                         if highest_threshold_id < NUM_BIOMES:
                              assigned_biome = highest_threshold_id + 1
                         else: # 如果阈值定义覆盖了所有 ID，就用最后一个
                              assigned_biome = highest_threshold_id
                     else: # 如果没有定义阈值，全部用默认
                          assigned_biome = DEFAULT_BIOME_ID


                self.grid_cells[x][y].biome_id = assigned_biome
        print("地形区域分配完毕。")

    def _place_decorations(self):
        """在地板上随机放置装饰物（如杂草）。"""
        print("正在放置装饰物...")
        if not WEED_FILES or not WEED_TYPE_WEIGHTS: # 如果没有定义杂草，直接返回
            print("未定义杂草类型，跳过放置。")
            return

        weed_types = list(WEED_TYPE_WEIGHTS.keys())
        weed_weights = list(WEED_TYPE_WEIGHTS.values())

        if not weed_types or sum(weed_weights) <= 0: # 确保有类型且权重有效
             print("杂草类型或权重无效，跳过放置。")
             return

        for x in range(self.width):
            for y in range(self.height):
                tile = self.grid_cells[x][y]
                # 只在地板上放置
                if not tile.is_wall:
                    biome_id = tile.biome_id
                    # 获取当前地形生成杂草的概率
                    spawn_chance = WEED_SPAWN_CHANCE_PER_BIOME.get(biome_id, 0)
                    # 如果随机数小于概率
                    if random.random() < spawn_chance:
                        try:
                             # 根据权重随机选择一种杂草类型
                            chosen_weed_id = random.choices(weed_types, weights=weed_weights, k=1)[0]
                            tile.decoration_id = chosen_weed_id # 记录装饰物 ID
                            # --- 创建 Decoration 精灵 ---
                            # 获取对应的图片
                            weed_image = self.game.asset_manager.get_image(chosen_weed_id)
                            if weed_image:
                                # 计算放置位置 (瓦片中心)
                                pos_world = (tile.rect.centerx, tile.rect.centery)
                                Decoration(self.game, pos_world, weed_image)
                            # --------------------------
                        except IndexError:
                             # random.choices 返回空列表的情况（理论上权重有效时不应发生）
                             print(f"警告：为坐标 {(x,y)} 选择杂草时出错。")

        print("装饰物放置完毕。")



    def is_wall(self, x: int, y: int) -> bool:
        """检查指定网格坐标是否是墙。超出边界也视为墙。"""
        if not self._is_valid(x, y):
            return True # 边界外视为墙
        return self.grid_cells[x][y].is_wall

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        """获取指定网格坐标的 Tile 对象。如果坐标无效返回 None。"""
        if not self._is_valid(x, y):
            return None
        return self.grid_cells[x][y]

    # --- 修改绘制逻辑 ---
    def draw(self, surface: pygame.Surface, camera: 'Camera', lighting: 'Lighting'):
        """绘制迷宫地图，考虑相机、光照、地形和装饰物。"""
        cam_rect = camera.get_view_rect() # 获取相机在世界坐标中的可见矩形
        # 根据相机视野确定需要绘制的瓦片范围
        start_col = max(0, int(cam_rect.left // TILE_SIZE))
        end_col = min(self.width, int((cam_rect.right + TILE_SIZE - 1) // TILE_SIZE))
        start_row = max(0, int(cam_rect.top // TILE_SIZE))
        end_row = min(self.height, int((cam_rect.bottom + TILE_SIZE - 1) // TILE_SIZE))

        # 默认图片键名 (如果获取失败)
        default_floor_key = f'{BIOME_FLOOR_BASENAME}{DEFAULT_BIOME_ID}'
        default_wall_key = f'{BIOME_WALL_BASENAME}{DEFAULT_BIOME_ID}'
        exit_img = self.game.asset_manager.get_image('exit')

        # 遍历可见范围内的瓦片
        for x in range(start_col, end_col):
            for y in range(start_row, end_row):
                tile = self.grid_cells[x][y]
                # 通过相机转换得到瓦片在屏幕上的绘制位置
                screen_pos = camera.apply(tile.rect)

                # 获取该瓦片的亮度 (0.0 到 1.0)
                brightness = lighting.get_tile_brightness(x, y)

                if brightness > 0: # 只有亮度大于0（可见或在记忆中）才绘制
                    is_currently_visible = (x, y) in lighting.visible_tiles # 是否当前被照亮

                    img_to_draw = None # 要绘制的图片
                    biome_id = tile.biome_id # 获取当前瓦片的地形 ID

                    if tile.is_wall:
                        # --- 判断墙体类型 ---
                        wall_biome_id = DEFAULT_BIOME_ID # 默认墙体类型
                        # 检查相邻地板 (优先级: 下 > 右 > 左 > 上)
                        prioritized_neighbors = [(x, y + 1), (x + 1, y), (x - 1, y), (x, y - 1)]
                        found_floor_neighbor = False
                        for nx, ny in prioritized_neighbors:
                             if self._is_valid(nx, ny):
                                 neighbor_tile = self.grid_cells[nx][ny]
                                 if not neighbor_tile.is_wall: # 如果邻居是地板
                                     wall_biome_id = neighbor_tile.biome_id # 墙体使用该地板的类型
                                     found_floor_neighbor = True
                                     break # 找到第一个地板邻居就停止

                        wall_key = f'{BIOME_WALL_BASENAME}{wall_biome_id}'
                        # ------------------
                        if lighting.light_walls or is_currently_visible:
                            img_to_draw = self.game.asset_manager.get_image(wall_key)
                            if img_to_draw is None: # 处理获取失败
                                img_to_draw = self.game.asset_manager.get_image(default_wall_key)

                    else: # 是地板
                        floor_key = f'{BIOME_FLOOR_BASENAME}{biome_id}'
                        img_to_draw = self.game.asset_manager.get_image(floor_key)
                        if img_to_draw is None: # 处理获取失败
                            img_to_draw = self.game.asset_manager.get_image(default_floor_key)

                        # 检查是否是出口
                        if (x, y) == self.exit_pos and exit_img:
                            # --- 绘制出口图片 ---
                            # 如果需要出口图片覆盖地板，在这里绘制出口图片
                            # 如果出口图片本身带透明度，效果会更好
                            # 也可以先绘制地板，再绘制出口
                            # 决定：先绘制地板，再绘制出口（如果出口图片半透明）
                            pass # 先让下面的逻辑绘制地板

                    if img_to_draw:
                        # 应用亮度/记忆效果 (通过 alpha 透明度)
                        # 创建一个临时表面来修改 alpha
                        temp_surf = img_to_draw.copy()
                        alpha = int(brightness * 255) # 将亮度映射到 0-255 的 alpha 值

                        # 设置 alpha 透明度
                        # 对于记忆区域，alpha < 255 会使其半透明
                        # 对于当前照亮区域，alpha 可以根据亮度调整（如果需要更复杂的效果）
                        # 当前实现：直接用亮度控制 alpha
                        temp_surf.set_alpha(alpha)
                        surface.blit(temp_surf, screen_pos.topleft) # 绘制到屏幕

                    # --- 绘制出口（如果地板已绘制）---
                    if not tile.is_wall and (x, y) == self.exit_pos and exit_img:
                        # 假设出口图片需要应用同样的亮度/alpha
                        exit_surf = exit_img.copy()
                        exit_alpha = int(brightness * 255)
                        exit_surf.set_alpha(exit_alpha)
                        surface.blit(exit_surf, screen_pos.topleft)

                    # --- 绘制装饰物 (在地板之上，但在精灵之下) ---
                    # 这部分逻辑移到 Decoration 精灵类中，让主循环绘制精灵

    # 修改：返回瓦片坐标和世界坐标
    def get_random_floor_tile(self) -> Tuple[Tuple[int, int], Tuple[float, float]]:
        """随机获取一个非墙壁格子的瓦片坐标和中心世界坐标。"""
        attempts = 0
        while attempts < self.width * self.height:
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            if not self.grid_cells[x][y].is_wall:
                tile_coords = (x, y)
                world_coords = (x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2)
                return tile_coords, world_coords
            attempts += 1
        # 极端情况处理
        print("错误：无法找到任何地面瓦片！")
        return (0, 0), (TILE_SIZE / 2, TILE_SIZE / 2)

    # --- 修改出口放置逻辑 ---
    def place_exit(self):
        """根据权重在不同区域（边缘、外围、中间）随机选择一个非墙壁格子作为出口。"""
        print("正在放置出口...")
        edge_tiles = []
        outer_ring_tiles = []
        middle_tiles = []

        # 遍历所有格子进行分类
        for x in range(self.width):
            for y in range(self.height):
                if not self.grid_cells[x][y].is_wall: # 只考虑非墙壁格子
                    coords = (x, y)
                    # 判断是否在边缘
                    is_edge = (x == 0 or x == self.width - 1 or y == 0 or y == self.height - 1)
                    # 判断是否在外围 (距离边缘 <= N)
                    dist_to_edge = min(x, self.width - 1 - x, y, self.height - 1 - y)
                    is_outer = (not is_edge) and (dist_to_edge <= EXIT_OUTER_RING_DISTANCE)

                    if is_edge:
                        edge_tiles.append(coords)
                    elif is_outer:
                        outer_ring_tiles.append(coords)
                    else: # 否则是中间
                        middle_tiles.append(coords)

        # 构建候选列表和权重列表
        all_candidates = []
        weights = []

        if edge_tiles:
            all_candidates.extend(edge_tiles)
            weights.extend([EXIT_ZONE_WEIGHTS['edge']] * len(edge_tiles))
        if outer_ring_tiles:
            all_candidates.extend(outer_ring_tiles)
            weights.extend([EXIT_ZONE_WEIGHTS['outer']] * len(outer_ring_tiles))
        if middle_tiles:
            all_candidates.extend(middle_tiles)
            weights.extend([EXIT_ZONE_WEIGHTS['middle']] * len(middle_tiles))

        # 进行加权随机选择
        if all_candidates:
            # 检查权重列表是否为空或总和为0
            if not weights or sum(weights) <= 0:
                print("警告：出口候选区域权重无效，将使用等概率选择。")
                self.exit_pos = random.choice(all_candidates)
            else:
                 # 使用 random.choices 进行加权选择
                 try:
                    self.exit_pos = random.choices(all_candidates, weights=weights, k=1)[0]
                    print(f"出口已根据权重放置在: {self.exit_pos}")
                 except ValueError as e:
                      print(f"警告：加权选择出口时出错 ({e})，将使用等概率选择。")
                      self.exit_pos = random.choice(all_candidates)
        else:
            # 极端情况：找不到任何非墙壁格子
            print("错误：找不到任何有效的出口位置！")
            self.exit_pos = None # 设置为 None，让游戏处理此情况


    def get_exit_rect(self) -> Optional[pygame.Rect]:
        """获取出口位置的矩形区域（世界坐标）。如果出口未设置则返回 None。"""
        if self.exit_pos:
            return pygame.Rect(self.exit_pos[0] * TILE_SIZE, self.exit_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        return None

    def _create_pathfinding_matrix(self) -> List[List[int]]:
        """为 pathfinding 库创建迷宫的矩阵表示。"""
        # 0 表示障碍物（墙），1 表示可通行（地板）
        # 注意：pathfinding库的 matrix[y][x] 访问方式
        matrix = [[1 if not self.grid_cells[x][y].is_wall else 0 for x in range(self.width)] for y in range(self.height)]
        return matrix

    def update_pathfinding_grid(self):
        """更新 pathfinding 库使用的 Grid 对象（如果迷宫结构发生变化）。"""
        # 在这个游戏中，迷宫生成后不变化，所以通常不需要调用此方法
        # 但如果未来有动态墙体，就需要更新
        # self.pathfinding_grid_matrix = self._create_pathfinding_matrix()
        self.pathfinding_grid.nodes = Grid(matrix=self.pathfinding_grid_matrix).nodes # 重建 Grid 节点
        # self.pathfinding_grid = Grid(matrix=self.pathfinding_grid_matrix) # 简单粗暴地重建 Grid 对象

    def find_path(self, start_pos_world: pygame.Vector2, end_pos_world: pygame.Vector2) -> Tuple[Optional[List[Tuple[float, float]]], float]:
        """使用 A* 算法查找从起点到终点的路径。"""
        # 将世界坐标转换为网格坐标
        start_tile = (int(start_pos_world.x // TILE_SIZE), int(start_pos_world.y // TILE_SIZE))
        end_tile = (int(end_pos_world.x // TILE_SIZE), int(end_pos_world.y // TILE_SIZE))

        # 确保起点和终点在网格范围内
        if not (self._is_valid(start_tile[0], start_tile[1]) and self._is_valid(end_tile[0], end_tile[1])):
            # print(f"寻路起点或终点 {start_tile} -> {end_tile} 超出边界")
            return None, float('inf') # 返回无路径和无限距离

        # 获取 pathfinding 库的节点对象
        # 注意：pathfinding 库使用 (x, y) 坐标顺序
        start_node = self.pathfinding_grid.node(start_tile[0], start_tile[1])
        end_node = self.pathfinding_grid.node(end_tile[0], end_tile[1])

        # 检查起点和终点节点是否有效且可通行 (值为1)
        # pathfinding 库的 matrix 是 matrix[y][x]
        if not start_node or not self.pathfinding_grid_matrix[start_node.y][start_node.x]:
            # print(f"寻路起点 {start_tile} 无效或是墙。")
            return None, float('inf')
        # 对于终点，即使是墙也尝试寻路（例如法师预测可能指向墙）
        # 寻路算法内部会处理终点不可达的情况
        if not end_node:
             # print(f"寻路终点 {end_tile} 无效。")
             return None, float('inf')
        # if not self.pathfinding_grid_matrix[end_node.y][end_node.x]:
             # print(f"警告: 寻路终点 {end_tile} 是墙。")
             # pass # 允许寻路到墙边

        self.pathfinding_grid.cleanup() # 每次寻路前清理节点状态
        try:
            # 调用 A* 寻路算法
            # path 是节点列表 [(x0, y0), (x1, y1), ...]
            path, runs = self.finder.find_path(start_node, end_node, self.pathfinding_grid)

            # 将路径节点转换回世界坐标 (每个格子的中心)
            world_path = [((node.x * TILE_SIZE + TILE_SIZE / 2), (node.y * TILE_SIZE + TILE_SIZE / 2)) for node in path]
            # print(f"找到路径: {start_tile} -> {end_tile}，长度 {len(path)} 步")
            # 返回世界坐标路径列表和路径长度（格子数）
            # 注意：路径长度包含起点，所以距离是 len(path) - 1
            distance = len(path) - 1 if path else float('inf')
            return world_path, distance

        except Exception as e:
             # 处理寻路库可能抛出的异常（例如找不到路径）
             # print(f"从 {start_tile} 到 {end_tile} 的寻路出错: {e}")
             return None, float('inf')