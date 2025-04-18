import pygame
import math # 导入 math 进行向量运算

from settings import *
import math
from typing import TYPE_CHECKING, List, Dict, Optional, Tuple # 添加 Tuple # 导入需要用到的类型提示

if TYPE_CHECKING:
    from main import Game
from items import WeaponItem
from monster import Monster
from items import Item

# --- 辅助函数：计算点到矩形的最近点 --- (新)
def closest_point_on_rect(point: pygame.Vector2, rect: pygame.Rect) -> pygame.Vector2:
    """计算点到矩形边界上的最近点。"""
    cx = max(rect.left, min(point.x, rect.right))
    cy = max(rect.top, min(point.y, rect.bottom))
    return pygame.Vector2(cx, cy)

class Player(pygame.sprite.Sprite):
    """代表玩家角色。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float]):
        self._layer = PLAYER_LAYER # 设置精灵图层
        self.groups = game.all_sprites # 将玩家添加到 all_sprites 组
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game # 游戏主对象的引用

        self.footstep_timer: float = 0.0  # 脚步声计时器 (秒)
        self.footstep_interval: float = 0.2 # 基础脚步声间隔 (秒)

        # 加载玩家图片，处理加载失败的情况
        self.image_orig = game.asset_manager.get_image('player')
        if self.image_orig is None: # 备用图像
             self.image_orig = pygame.Surface(PLAYER_IMAGE_SIZE, pygame.SRCALPHA).convert_alpha()
             self.image_orig.fill((0,0,0,0)) # 透明背景
             pygame.draw.circle(self.image_orig, WHITE, (PLAYER_RADIUS_PX, PLAYER_RADIUS_PX), PLAYER_RADIUS_PX) # 画一个白色圆圈
        self.image = self.image_orig.copy() # 当前显示的图像
        self.rect = self.image.get_rect()   # 图像的矩形

        # self.hit_rect 不再是主要的碰撞形状，但可以保留用于其他目的或简化检测范围
        self.hit_rect = PLAYER_HIT_RECT.copy() # 用于碰撞检测的矩形
        self.pos = pygame.Vector2(pos)      # 玩家中心位置 (世界坐标)
        self.vel = pygame.Vector2(0, 0)     # 玩家速度向量
        self.rect.center = self.pos         # 初始化图像矩形位置
        self.hit_rect.center = self.rect.center # 初始化碰撞矩形位置
        # 新增：圆形碰撞半径
        self.radius = PLAYER_RADIUS_PX

        # --- 玩家状态属性 ---
        self.hunger: float = PLAYER_START_HUNGER # 当前饱食度
        # 存储每根火柴剩余燃烧时间的列表（单位：帧）
        # 新火柴添加到列表末尾，从索引 0 开始燃烧 (最先获得的先烧) -> 设计修改：从右边开始烧
        # self.matches: List[float] = []
        # for _ in range(MATCH_INITIAL_COUNT):
        #     self.add_match_legacy() # 添加初始火柴 (旧逻辑)

        # 新逻辑：火柴列表代表从左到右的显示顺序，燃烧右边的
        self.matches: List[float] = [] # 存储每根火柴剩余燃烧时间 (帧)
        self.current_match_index: int = -1 # 当前燃烧的火柴在列表中的索引 (-1 表示没有)
        for _ in range(MATCH_INITIAL_COUNT):
            self.add_match() # 添加初始火柴


        # 玩家物品栏 (当前只存武器)
        # inventory 字典存储不同类型的物品列表
        self.inventory: Dict[str, List['WeaponItem']] = {'weapons': []}

        # --- 移动与速度 (添加 is_running) ---
        self.base_speed: float = PLAYER_SPEED
        self.current_speed: float = self.base_speed
        self.speed_boost_factor: float = 1.0
        self.speed_boost_timer: float = 0
        self.is_running: bool = False # 新增：是否正在奔跑

        # --- 状态计时器 ---
        self.hunger_decay_timer: float = 0 # 饱食度衰减计时器 (帧)
        self.hunger_warn_timer: float = 0  # 饥饿警告音效计时器 (帧)
        self.match_out_timer: float = 0    # 火柴耗尽后的死亡计时器 (帧)
        self.is_dead: bool = False         # 标记玩家是否死亡
        self.death_reason: str = ""        # 玩家死亡原因

        # 火柴魔法效果计时器 (当前未使用)
        self.magic_match_timer: float = 0
        self.footstep_timer: float = 0.0
        self.footstep_interval: float = 0.3

    # --- 修改 get_input ---
    def get_input(self):
        """处理玩家输入，更新速度向量和奔跑状态。"""
        self.vel = pygame.Vector2(0, 0) # 每帧重置速度
        keys = pygame.key.get_pressed() # 获取当前按下的按键
        # 检测奔跑键
        self.is_running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        # 计算当前帧的实际移动速度 (考虑吃肉和奔跑，乘法叠加)
        run_factor = PLAYER_RUN_SPEED_MULTIPLIER if self.is_running else 1.0
        self.current_speed = self.base_speed * self.speed_boost_factor * run_factor

        # 更新速度向量 (使用 current_speed)
        # 根据按键设置水平和垂直速度
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel.x = -self.current_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel.x = self.current_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vel.y = -self.current_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vel.y = self.current_speed

        # 防止斜向移动速度过快 (向量长度修正)
        if self.vel.x != 0 and self.vel.y != 0:
            # 将速度乘以 1/sqrt(2) ≈ 0.7071
            self.vel *= 0.7071

    # --- 修改 move (现在只应用速度，碰撞单独处理) ---
    def move(self, dt: float):
        """根据速度更新玩家位置（碰撞检测移至 check_collisions）。"""
        # 直接应用速度（碰撞和滑动在 check_collisions 中处理）
        self.pos += self.vel
        # 更新 sprite 的 rect 位置 (碰撞处理后会再次更新)
        self.rect.center = self.pos
        # self.hit_rect.center = self.rect.center # hit_rect 可能不再需要频繁更新

    # --- 重写 check_collisions ---
    def check_collisions(self):
        """检查并处理玩家与墙壁、物品、怪物、出口的碰撞（圆形碰撞 + 滑动）。"""
        original_pos = self.pos.copy() # 保存原始位置以备需要
        original_vel = self.vel.copy() # 保存原始速度用于滑动计算

        # --- 墙壁碰撞检测与滑动 (圆形 vs 瓦片) ---
        # 确定需要检查的瓦片范围 (基于玩家当前位置和一点缓冲)
        check_radius_tiles = math.ceil(self.radius / TILE_SIZE) + 1 # 检查半径（格子数）
        center_tile_x = int(self.pos.x // TILE_SIZE)
        center_tile_y = int(self.pos.y // TILE_SIZE)

        collided_this_frame = False # 标记本帧是否发生碰撞

        # 迭代检查（可选，多次迭代可以处理角落碰撞更精确，但增加计算量）
        # for _ in range(2): # 迭代两次尝试解决复杂角落

        potential_collisions = [] # 存储潜在碰撞信息 (墙体rect, 碰撞点, 法线, 深度)

        for dx in range(-check_radius_tiles, check_radius_tiles + 1):
            for dy in range(-check_radius_tiles, check_radius_tiles + 1):
                check_x = center_tile_x + dx
                check_y = center_tile_y + dy
                if self.game.maze.is_wall(check_x, check_y): # 如果是墙体瓦片
                    wall_rect = pygame.Rect(check_x * TILE_SIZE, check_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    # 计算墙壁矩形上离玩家圆心最近的点
                    closest = closest_point_on_rect(self.pos, wall_rect)
                    # 计算玩家圆心到最近点的向量和距离
                    collision_vec = self.pos - closest
                    dist_sq = collision_vec.length_squared()

                    # 如果距离平方小于半径平方，则发生碰撞
                    if dist_sq < self.radius * self.radius and dist_sq > 1e-6: # 避免除零
                        dist = math.sqrt(dist_sq)
                        penetration = self.radius - dist
                        normal = collision_vec / dist # 碰撞法线 (从墙指向玩家)
                        potential_collisions.append({
                             'rect': wall_rect,
                             'closest': closest,
                             'normal': normal,
                             'penetration': penetration
                        })

        # 处理检测到的碰撞
        if potential_collisions:
             collided_this_frame = True
             # --- 位置修正 ---
             # 简单地将所有碰撞推开 (可能导致抖动)
             # 更稳健的方法是只推开最深的碰撞？或者平均推开？
             # 先尝试只推开最深的碰撞
             potential_collisions.sort(key=lambda c: c['penetration'], reverse=True)
             deepest_collision = potential_collisions[0]
             self.pos += deepest_collision['normal'] * deepest_collision['penetration']
             # print(f"Collision! Pushed back by {deepest_collision['penetration']:.2f}")

             # --- 速度修正 (向量投影滑动) ---
             collision_normal = deepest_collision['normal']
             # 计算速度在法线方向上的分量
             vel_normal_component = self.vel.dot(collision_normal)

             # 如果速度分量是冲向墙壁的 (点积 < 0)
             if vel_normal_component < 0:
                 # 移除这个冲向墙壁的分量，使得速度平行于墙面或为零
                 self.vel -= collision_normal * vel_normal_component
                 # print(f"Adjusted velocity from {original_vel} to {self.vel}")


        # --- 物品碰撞检测 (使用圆形碰撞) ---
        items_hit = pygame.sprite.spritecollide(self, self.game.items, False, pygame.sprite.collide_circle_ratio(1.0)) # 使用圆形碰撞
        for item in items_hit:
            if isinstance(item, Item): # 确保是 Item 类型的对象
                 if item.interact(self): # 调用物品的 interact 方法
                    if SAVE_ON_PICKUP: # 如果设置了拾取时存档
                        self.game.save_game_state() # 执行存档

        # --- 怪物碰撞检测 (使用圆形碰撞) ---
        monsters_hit = pygame.sprite.spritecollide(self, self.game.monsters, False, pygame.sprite.collide_circle_ratio(0.8)) # 用小一点的比例避免太敏感
        for monster in monsters_hit:
            if not self.is_dead and isinstance(monster, Monster): # 确保玩家还活着且对象是怪物
                self.handle_monster_collision(monster) # 处理与怪物的碰撞

        # --- 出口碰撞检测  (仍可使用矩形，因为出口是一个格子) ---
        exit_rect = self.game.maze.get_exit_rect() # 获取出口的矩形区域
        # 出口碰撞可以用玩家中心点是否在出口矩形内判断，更简单
        if exit_rect and exit_rect.collidepoint(self.pos):
        # 或者用圆形和矩形碰撞
        # if exit_rect and pygame.Rect(self.pos.x - self.radius, self.pos.y - self.radius, self.radius*2, self.radius*2).colliderect(exit_rect): # 粗略的圆形包围盒
             # 更精确的圆矩碰撞:
             closest_exit = closest_point_on_rect(self.pos, exit_rect)
             if (self.pos - closest_exit).length_squared() < self.radius * self.radius:
                 self.game.win_game()

        # 最终更新 rect 位置
        self.rect.center = self.pos
        # self.hit_rect.center = self.rect.center



    def handle_monster_collision(self, monster: 'Monster'):
        """处理玩家与怪物的碰撞。"""
        if self.inventory['weapons']: # 如果玩家有武器
            weapon = self.inventory['weapons'][0] # 使用获取顺序中的第一把武器
            print(f"玩家使用 {weapon.weapon_type} 剑攻击了 {monster.name}")
            monster.take_damage() # 对怪物造成伤害 (怪物自己处理是否死亡)
            weapon.uses -= 1 # 武器消耗一次使用次数
            self.game.asset_manager.play_sound('monster_die') # 播放击中音效（或者单独的武器击中音效）

            if weapon.uses <= 0: # 如果武器用完了
                 print(f"{weapon.weapon_type} 剑破碎了!")
                 self.game.asset_manager.play_sound('weapon_break') # 播放武器破碎音效
                 self.inventory['weapons'].pop(0) # 从库存中移除武器
        else: # 如果玩家没有武器
            print("玩家被怪物抓住了，而且没有武器！")
            self.die("被怪物抓住了") # 玩家死亡

    # --- 修改 update (碰撞移到 move 之后) ---
    def update(self, dt: float):
        """每帧更新玩家状态。"""
        if self.is_dead: # 如果玩家已死亡，则不进行任何更新
            return

        self.get_input() # 处理输入，更新速度和奔跑状态
        # self.move(dt)    # 旧的移动位置
        # --- 先应用速度，再检查碰撞并修正 ---
        # 1. 计算目标位置
        target_pos = self.pos + self.vel
        # 2. 尝试移动到目标位置 (暂时更新 self.pos)
        self.pos = target_pos
        # 3. 检查碰撞并修正 self.pos 和 self.vel
        self.check_collisions()
        # 4. 更新最终的 rect 位置
        self.rect.center = self.pos
        # ---------------------------------

        # 更新状态计时器和属性
        self.update_hunger(dt) # 内部需要使用 is_running
        self.update_matches(dt) # 内部需要使用 is_running
        self.update_speed_boost(dt)
        self.update_magic_match(dt) # (未使用)

        # 更新脚步声
        self.update_footsteps(dt)

        # 检查死亡条件
        if self.hunger <= 0:
            self.die("饿死了")
        # 如果没有火柴在燃烧 (index 为 -1)
        if self.current_match_index == -1 and not self.matches: # 确保列表也为空
             self.match_out_timer += dt * FPS # 累加死亡计时器 (帧)
             if self.match_out_timer >= MATCH_OUT_DEATH_TIMER_FRAMES:
                  self.die("在黑暗中迷失了")
        else: # 如果还有火柴或正在燃烧
             self.match_out_timer = 0 # 重置死亡计时器

        # 饥饿警告效果
        if self.hunger <= PLAYER_MAX_HUNGER * (PLAYER_HUNGER_WARN_THRESHOLD / 100.0):
             self.hunger_warn_timer += dt * FPS # 累加警告计时器 (帧)
             if self.hunger_warn_timer >= PLAYER_HUNGER_WARN_INTERVAL:
                  self.hunger_warn_timer = 0 # 重置计时器
                  self.game.asset_manager.play_sound('hunger_growl') # 播放咕咕叫音效
                  # 在这里添加视觉效果，例如一个短暂的波纹特效精灵
                  # print("肚子咕咕叫...") # 调试信息

    # --- 修改 update_hunger ---
    def update_hunger(self, dt: float):
        """更新饱食度，考虑奔跑消耗。"""
        self.hunger_decay_timer += dt * FPS
        if self.hunger_decay_timer >= PLAYER_HUNGER_DECAY_INTERVAL:
            self.hunger_decay_timer = 0
            # 计算消耗速率因子
            hunger_consumption_factor = PLAYER_RUN_HUNGER_MULTIPLIER if self.is_running else 1.0
            # 计算本次消耗量
            hunger_to_lose = PLAYER_HUNGER_DECAY_RATE * hunger_consumption_factor
            self.hunger = max(0, self.hunger - hunger_to_lose)

    # --- 修改 update_matches ---
    def update_matches(self, dt: float):
        """更新当前燃烧的火柴状态，考虑奔跑消耗。"""
        if self.current_match_index != -1 and self.current_match_index < len(self.matches):
            # 计算燃烧速率因子
            burn_rate_factor = PLAYER_RUN_MATCH_BURN_MULTIPLIER if self.is_running else 1.0
            # 计算本帧燃烧掉的“时间”（帧数）
            frames_to_burn = dt * FPS * burn_rate_factor
            self.matches[self.current_match_index] -= frames_to_burn

            if self.matches[self.current_match_index] <= 0:
                # ... (火柴烧尽逻辑不变) ...
                print("一根火柴烧尽了!")
                self.matches.pop(self.current_match_index)
                self.current_match_index = len(self.matches) - 1
                if self.current_match_index == -1:
                    print("所有火柴都烧尽了!")
                    pass
                else:
                    pass

    # --- 添加 update_footsteps ---
    def update_footsteps(self, dt: float):
        """更新并播放脚步声音效。"""
        is_moving = self.vel.length_squared() > 0

        if is_moving:
            self.footstep_timer += dt
            # 计算当前间隔（考虑奔跑速度因子，吃肉速度因子不影响频率）
            run_factor = PLAYER_RUN_SPEED_MULTIPLIER if self.is_running else 1.0
            # 假设速度越快，间隔越短
            current_interval = self.footstep_interval / run_factor # 加速时 run_factor > 1, 间隔变短

            if self.footstep_timer >= current_interval:
                self.game.asset_manager.play_sound('step')
                self.footstep_timer -= current_interval # 减去间隔更精确
        else:
            self.footstep_timer = 0.0 # 停止移动时重置计时器


    def update_speed_boost(self, dt: float):
        """更新速度加成效果的持续时间。"""
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt * FPS # 减少剩余时间 (帧)
            if self.speed_boost_timer <= 0:
                self.speed_boost_timer = 0 # 时间耗尽
                self.speed_boost_factor = 1.0 # 恢复速度因子
                # self.current_speed = self.base_speed # current_speed 每帧都会重新计算，这里不需要了
                print("速度加成效果结束。")

    def update_magic_match(self, dt: float):
        """更新火柴魔法效果的持续时间 (当前未使用)。"""
        if self.magic_match_timer > 0:
             self.magic_match_timer -= dt * FPS
             if self.magic_match_timer <= 0:
                  self.magic_match_timer = 0
                  print("火柴魔法效果结束。")

    def add_hunger(self, amount: int):
        """增加玩家饱食度。"""
        self.hunger = min(PLAYER_MAX_HUNGER, self.hunger + amount) # 增加饱食度，但不超过上限
        print(f"吃下食物。当前饱食度: {int(self.hunger)}/{PLAYER_MAX_HUNGER}")

    # 旧的 add_match 逻辑 (添加到列表末尾，从0开始烧)
    # def add_match_legacy(self):
    #     self.matches.append(MATCH_BURN_TIME_FRAMES)
    #     # 如果这是第一根火柴，开始燃烧
    #     if len(self.matches) == 1:
    #         self.current_match_index = 0
    #         # 播放燃烧音效 (循环)
    #         self.game.asset_manager.play_sound('match_burn', loops=-1)
    #     print(f"拾取到一根火柴。总火柴数: {len(self.matches)}")

    def add_match(self):
        """添加一根新火柴到玩家库存 (添加到左边)。"""
        # 新火柴添加到列表的最前面 (index 0)
        self.matches.insert(0, MATCH_BURN_TIME_FRAMES)
        # 如果添加前没有火柴在燃烧 (index == -1)，则新添加的这根（现在是唯一的一根，索引0）
        # 应该成为当前燃烧的火柴。但我们的燃烧逻辑是从右边(index最大)开始烧。
        # 所以，添加新火柴后，当前燃烧的火柴索引应该加 1 (因为它被往左挤了)
        if self.current_match_index != -1:
            self.current_match_index += 1
        else:
            # 如果之前没有火柴，那么现在唯一的火柴就是当前燃烧的火柴，其索引是 0
            self.current_match_index = 0
            # 开始播放燃烧音效 (循环)
            # 注意：这里需要处理停止旧循环音效的问题，如果 AssetManager 不支持的话会比较麻烦
            # 简单起见，假设 play_sound 会覆盖之前的循环
            self.game.asset_manager.play_sound('match_burn', loops=-1)

        print(f"拾取到一根火柴。总火柴数: {len(self.matches)}")

    def get_total_remaining_burn_frames(self) -> float:
        """计算所有火柴的总剩余燃烧时间（帧）。"""
        # 直接对 self.matches 列表中的所有剩余时间求和
        return sum(self.matches)

    def add_weapon(self, weapon_item: 'WeaponItem'):
        """将拾取的武器添加到玩家库存。"""
        # 按获取顺序添加到列表末尾
        self.inventory['weapons'].append(weapon_item)
        print(f"拾取到武器: {weapon_item.weapon_type}, 可用次数: {weapon_item.uses}。当前武器数量: {len(self.inventory['weapons'])}")

    def apply_speed_boost(self, factor: float, duration_frames: float):
        """应用速度加成效果。"""
        self.speed_boost_factor = factor
        self.speed_boost_timer = duration_frames
        # self.current_speed = self.base_speed * self.speed_boost_factor # current_speed 每帧重新计算
        print(f"获得速度加成！基础倍率: {self.speed_boost_factor:.1f}x")

    def get_current_match_burn_percentage(self) -> float:
        """获取当前燃烧火柴的剩余燃烧百分比 (0.0 到 1.0)。"""
        if self.current_match_index != -1 and self.current_match_index < len(self.matches):
            remaining = self.matches[self.current_match_index]
            return max(0.0, min(1.0, remaining / MATCH_BURN_TIME_FRAMES))
        return 0.0 # 没有火柴在燃烧

    def get_current_match_remaining_frames(self) -> float:
        """获取当前燃烧火柴的剩余燃烧时间 (帧)。"""
        if self.current_match_index != -1 and self.current_match_index < len(self.matches):
             return self.matches[self.current_match_index]
        return 0 # 没有火柴在燃烧

    def get_total_match_count(self) -> int:
        """获取玩家当前拥有的火柴总数。"""
        return len(self.matches)

    def has_magic_match_active(self) -> bool:
        """检查火柴魔法效果是否激活 (当前未使用)。"""
        # 示例：如果游戏中有魔法火柴物品，拾取后可以设置这个计时器
        # self.magic_match_timer = MATCH_MAGIC_DURATION_FRAMES
        return self.magic_match_timer > 0

    def die(self, reason: str):
        """处理玩家死亡。"""
        if not self.is_dead: # 防止重复触发死亡逻辑
             print(f"玩家死亡: {reason}")
             self.is_dead = True           # 标记为死亡状态
             self.death_reason = reason    # 记录死亡原因
             self.vel = pygame.Vector2(0, 0) # 停止移动
             self.game.asset_manager.play_sound('player_die') # 播放死亡音效
             self.game.asset_manager.stop_music() # 停止背景音乐
             # 可能需要停止其他循环音效，例如火柴燃烧声
             # self.game.asset_manager.stop_sound('match_burn')