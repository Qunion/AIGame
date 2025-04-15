import pygame
import math
from settings import *
from typing import TYPE_CHECKING, Set, Tuple, Dict

if TYPE_CHECKING:
    from main import Game
from player import Player
from camera import Camera

class Lighting:
    """管理游戏中的光照效果、视野计算和战争迷雾（记忆）系统。"""
    def __init__(self, game: 'Game'):
        self.game = game # 游戏主对象的引用
        # 存储当前帧可见的瓦片坐标集合 {(x, y), ...}
        self.visible_tiles: Set[Tuple[int, int]] = set()
        # 存储被探索过的瓦片记忆信息
        # 格式: {(x, y): (timestamp, initial_brightness), ...}
        # timestamp 是最后一次看到该瓦片的时间戳 (毫秒)
        # initial_brightness 是刚进入记忆状态时的亮度 (通常是 FOW_MEMORY_BRIGHTNESS)
        self.memory_tiles: Dict[Tuple[int, int], Tuple[float, float]] = {}
        self.light_walls: bool = FOV_LIGHT_WALLS # 是否照亮墙壁本身
        self.num_rays: int = FOV_NUM_RAYS # 视野计算使用的光线数量
        # 用于绘制整体黑暗效果的表面 (可选的高级效果)
        # self.fov_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()

    def calculate_fov(self, player: 'Player'):
        """使用射线投射算法计算玩家当前的可见瓦片范围。"""
        self.visible_tiles.clear() # 每帧开始时清空可见集合
        # 获取玩家中心点和所在的瓦片坐标
        player_tile_x = int(player.pos.x // TILE_SIZE)
        player_tile_y = int(player.pos.y // TILE_SIZE)
        cx, cy = player.pos.x, player.pos.y # 光源中心 (玩家中心)

        # 获取当前火柴数量和状态
        current_match_count = player.get_total_match_count()
        remaining_frames = player.get_current_match_remaining_frames()

        # 如果没有火柴或火柴已烧尽，则没有视野
        if current_match_count == 0 or remaining_frames <= 0:
             # 确保玩家脚下的格子仍然在"可见"范围内（亮度为0），这样地图不会完全消失
             self.visible_tiles.add((player_tile_x, player_tile_y))
             return

        # 根据火柴数量决定基础照明半径
        radius_px = MATCH_RADIUS_LARGE_PX if current_match_count >= MATCH_COUNT_THRESHOLD_RADIUS else MATCH_RADIUS_SMALL_PX
        # 检查火柴魔法是否激活 (当前未使用)
        magic_active = player.has_magic_match_active()

        # 玩家脚下的瓦片总是可见的
        self.visible_tiles.add((player_tile_x, player_tile_y))

        # --- 射线投射 ---
        # 从玩家位置向四周发射光线
        for i in range(self.num_rays):
            angle = (i / self.num_rays) * 2 * math.pi # 计算当前光线的角度
            dx = math.cos(angle) # 光线方向的 x 分量
            dy = math.sin(angle) # 光线方向的 y 分量

            # 沿光线方向步进，检查每个经过的瓦片
            for step in range(int(radius_px)): # 步进距离最远为半径
                # 计算当前步进点在世界坐标中的位置
                x = cx + dx * step
                y = cy + dy * step
                # 将世界坐标转换为瓦片坐标
                tile_x = int(x // TILE_SIZE)
                tile_y = int(y // TILE_SIZE)

                # 检查瓦片坐标是否在地图边界内
                if not (0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT):
                    break # 光线超出地图范围，停止这条光线

                # 将当前瓦片添加到可见集合
                self.visible_tiles.add((tile_x, tile_y))

                # 检查是否撞到墙壁 (除非魔法激活)
                if not magic_active and self.game.maze.is_wall(tile_x, tile_y):
                    # 如果设置了照亮墙壁本身
                    if self.light_walls:
                        # 将墙壁瓦片也加入可见集合
                        self.visible_tiles.add((tile_x, tile_y))
                    break # 光线被墙壁阻挡，停止这条光线

    def update_memory(self):
        """更新战争迷雾（记忆）信息，将新看到的瓦片加入记忆，并处理旧记忆的遗忘。"""
        current_time = pygame.time.get_ticks() # 获取当前时间戳 (毫秒)

        # 将当前可见的瓦片添加到记忆中，或更新其时间戳
        for tile_pos in self.visible_tiles:
            # 即使瓦片已在记忆中，也更新时间戳，表示最近刚看到
            # 存储进入记忆时的基础亮度
            self.memory_tiles[tile_pos] = (current_time, FOW_MEMORY_BRIGHTNESS)

        # 检查并移除过期的记忆瓦片
        to_remove = [] # 存储需要移除的瓦片坐标
        for pos, (timestamp, initial_brightness) in self.memory_tiles.items():
            # 只处理当前不可见的记忆瓦片
            if pos not in self.visible_tiles:
                age_ms = current_time - timestamp # 计算记忆经过的时间 (毫秒)
                # FOW_FORGET_TIME_FRAMES 需要转换为毫秒进行比较
                if age_ms >= FOW_FORGET_TIME_FRAMES * (1000 / FPS):
                    to_remove.append(pos) # 超过遗忘时间，标记为待移除
                # 亮度的衰减逻辑在 get_tile_brightness 中处理

        # 从记忆字典中移除过期的瓦片
        for pos in to_remove:
            if pos in self.memory_tiles: # 再次检查以防万一
                 del self.memory_tiles[pos]


    def get_tile_brightness(self, x: int, y: int) -> float:
        """获取指定瓦片的亮度值 (0.0 到 1.0)，考虑当前光照和记忆效果。"""
        pos = (x, y)
        current_time = pygame.time.get_ticks() # 当前时间戳 (毫秒)
        player = self.game.player

        # 1. 检查瓦片是否当前可见
        if pos in self.visible_tiles:
            # 获取当前火柴状态
            total_remaining_frames  = player.get_total_remaining_burn_frames()  
            total_frames = MATCH_BURN_TIME_FRAMES

            # 如果没有光（火柴烧尽），亮度为 0
            if total_remaining_frames  <= 0:
                # 特例：如果玩家脚下瓦片是唯一可见的，给个极低亮度避免全黑？
                # if pos == (int(player.pos.x // TILE_SIZE), int(player.pos.y // TILE_SIZE)):
                #     return 0.01
                return 0.0

            # 计算基础亮度 (根据火柴剩余时间)
            base_brightness = 1.0

            # if len(Player.matches) <= 1:
            # 查找第一个满足的低亮度阈值
            for i in range(len(MATCH_LOW_THRESHOLDS_FRAMES)):
                if total_remaining_frames  <= MATCH_LOW_THRESHOLDS_FRAMES[i]:
                    base_brightness = MATCH_LOW_BRIGHTNESS[i]
                    break # 使用第一个达到的阈值对应的亮度

            # 计算从光源中心到瓦片中心的距离
            dist_sq = (player.pos.x - (x * TILE_SIZE + TILE_SIZE / 2))**2 + \
                      (player.pos.y - (y * TILE_SIZE + TILE_SIZE / 2))**2
            # 获取当前光源的最大半径
            max_radius = MATCH_RADIUS_LARGE_PX if player.get_total_match_count() >= MATCH_COUNT_THRESHOLD_RADIUS else MATCH_RADIUS_SMALL_PX

            # 如果最大半径为0（理论上不应发生），距离比例为0
            dist_ratio = min(1.0, math.sqrt(dist_sq) / max_radius) if max_radius > 0 else 0

            # --- 应用光照梯度效果 ---
            # 计算亮度需要减少的总量 (1.0 - base_brightness)
            total_brightness_reduction = 1.0 - base_brightness
            # 根据距离比例和 LIGHT_GRADIENT_STOPS 计算当前距离应该应用的亮度减少比例 (gradient_multiplier)
            gradient_multiplier = 0.0 # 0 表示不减少，1 表示完全减少
            last_radius_ratio = 0.0
            last_reduction_ratio = 0.0
            for radius_ratio_thresh, reduction_ratio_thresh in LIGHT_GRADIENT_STOPS:
                 if dist_ratio <= radius_ratio_thresh:
                      # 在当前段内进行线性插值
                      segment_range = radius_ratio_thresh - last_radius_ratio
                      reduction_range = reduction_ratio_thresh - last_reduction_ratio
                      # 处理分母为零的情况
                      if segment_range > 0:
                           ratio_in_segment = (dist_ratio - last_radius_ratio) / segment_range
                           gradient_multiplier = last_reduction_ratio + ratio_in_segment * reduction_range
                      else: # 如果段范围为0（例如只有一个点），直接使用该点的减少比例
                           gradient_multiplier = reduction_ratio_thresh
                      break # 找到所在区间后停止
                 last_radius_ratio = radius_ratio_thresh
                 last_reduction_ratio = reduction_ratio_thresh
            else: # 如果距离超过了所有定义的梯度停止点（理论上在半径内不应发生）
                 gradient_multiplier = 1.0 # 应用完全的亮度减少

            # 计算最终亮度：基础亮度 - (总减少量 * 梯度减少比例)
            # 或者：最终亮度 = 1.0 - (总减少量 * 梯度减少比例) ? 不对
            # 正确逻辑： 最终亮度 = 基础亮度 + (1.0 - 基础亮度) * (1.0 - gradient_multiplier)
            # 这样当 gradient_multiplier=0 时, 亮度=基础; gradient_multiplier=1 时, 亮度 = 基础 + (1-基础)*0 = 基础? 也不对
            # 应该是：最终亮度 = 1.0 - 亮度减少量 * 梯度比例
            final_brightness = 1.0 - total_brightness_reduction * gradient_multiplier # 这个似乎合理

            # 确保亮度在 0.0 到 1.0 之间
            return max(0.0, min(1.0, final_brightness))


        # 2. 如果瓦片不在当前视野，检查是否在记忆中
        elif pos in self.memory_tiles:
            timestamp, initial_brightness = self.memory_tiles[pos]
            age_ms = current_time - timestamp # 记忆经过的时间 (毫秒)
            # 将毫秒转换为帧数，用于与设置中的帧数比较
            age_frames = age_ms / (1000 / FPS)

            # 检查玩家当前火柴是否过低，如果过低则暂时隐藏记忆效果
            if player.get_total_remaining_burn_frames() < MATCH_MEMORY_FADE_THRESHOLD_FRAMES:
                 return 0.0 # 临时隐藏记忆

            # 计算记忆亮度衰减
            current_mem_brightness = initial_brightness # 从进入记忆时的亮度开始
            # 查找适用的最暗的衰减级别
            for i in range(len(FOW_DECAY_TIMES_FRAMES)):
                 if age_frames >= FOW_DECAY_TIMES_FRAMES[i]:
                      current_mem_brightness = FOW_DECAY_BRIGHTNESS[i]
                      # 注意：这里没有 break，所以会应用最后一个满足条件的（最暗的）亮度级别

            # 再次检查是否已完全遗忘 (时间超过最大遗忘时间)
            if age_frames >= FOW_FORGET_TIME_FRAMES:
                return 0.0

            # 返回计算出的记忆亮度
            return max(0.0, min(1.0, current_mem_brightness)) # 限制在 0.0 到 1.0


        # 3. 如果瓦片既不可见也不在记忆中，亮度为 0
        else:
            return 0.0

    def draw_darkness(self, surface: pygame.Surface, camera: 'Camera', player: 'Player'):
        """(可选实现) 绘制一个覆盖全屏的黑暗层，模拟光照衰减。
           这是一种替代或补充瓦片亮度控制的方法。
           当前实现依赖于 get_tile_brightness 来控制每个瓦片的 alpha。
           如果需要更平滑的圆形光照，可以在这里绘制。
        """
        # 简单的实现：依赖瓦片自身的 alpha 透明度，这里什么都不做
        pass

        # --- 复杂实现示例：绘制渐变黑暗遮罩 ---
        # self.fov_surface.fill((0, 0, 0, 255)) # 从完全黑暗开始

        # # 获取当前光照参数
        # remaining_frames = player.get_current_match_remaining_frames()
        # if remaining_frames <= 0:
        #      surface.blit(self.fov_surface, (0,0)) # 如果没光，直接全黑
        #      return

        # max_radius = MATCH_RADIUS_LARGE_PX if player.get_total_match_count() >= MATCH_COUNT_THRESHOLD_RADIUS else MATCH_RADIUS_SMALL_PX
        # base_brightness = 1.0
        # for i in range(len(MATCH_LOW_THRESHOLDS_FRAMES)):
        #      if remaining_frames <= MATCH_LOW_THRESHOLDS_FRAMES[i]:
        #           base_brightness = MATCH_LOW_BRIGHTNESS[i]
        #           break

        # # 获取玩家在屏幕上的坐标
        # player_screen_pos = camera.apply_sprite(player).center

        # # 计算最大黑暗度 (alpha)
        # max_darkness_alpha = int((1.0 - base_brightness) * 255 * 0.8) # *0.8 让最暗处也稍微有点透

        # # 绘制从外到内的渐变圆
        # num_gradient_steps = 30 # 步数越多越平滑
        # for i in range(num_gradient_steps, -1, -1):
        #     dist_ratio = i / num_gradient_steps # 当前圆的半径比例 (0 到 1)
        #     current_radius = int(dist_ratio * max_radius)

        #     if current_radius <= 0: continue

        #     # 计算此半径比例对应的黑暗度比例 (gradient_multiplier)
        #     gradient_multiplier = 0.0
        #     # ... (此处省略根据 LIGHT_GRADIENT_STOPS 计算 gradient_multiplier 的逻辑) ...

        #     # 计算当前圆的 alpha 值 (越往外越不透明)
        #     current_alpha = int(gradient_multiplier * max_darkness_alpha)
        #     current_alpha = max(0, min(255, current_alpha))

        #     # 在 fov_surface 上绘制一个有透明度的黑色圆
        #     pygame.draw.circle(self.fov_surface, (0, 0, 0, current_alpha), player_screen_pos, current_radius)

        # # 最后将带有透明渐变圆的 fov_surface 绘制到主屏幕上
        # surface.blit(self.fov_surface, (0, 0))


    def update(self, player: 'Player'):
        """每帧更新光照系统：计算视野并更新记忆。"""
        self.calculate_fov(player)
        self.update_memory()