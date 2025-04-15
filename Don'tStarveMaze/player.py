import pygame
from settings import *
import math
from typing import TYPE_CHECKING, List, Dict, Optional
from typing import Tuple # 导入需要用到的类型提示

if TYPE_CHECKING:
    from main import Game
    from items import WeaponItem
    from monster import Monster
    from items import Item

class Player(pygame.sprite.Sprite):
    """代表玩家角色。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float]):
        self._layer = PLAYER_LAYER # 设置精灵图层
        self.groups = game.all_sprites # 将玩家添加到 all_sprites 组
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game # 游戏主对象的引用

        # 加载玩家图片，处理加载失败的情况
        self.image_orig = game.asset_manager.get_image('player')
        if self.image_orig is None: # 备用图像
             self.image_orig = pygame.Surface(PLAYER_IMAGE_SIZE, pygame.SRCALPHA).convert_alpha()
             self.image_orig.fill((0,0,0,0)) # 透明背景
             pygame.draw.circle(self.image_orig, WHITE, (PLAYER_RADIUS_PX, PLAYER_RADIUS_PX), PLAYER_RADIUS_PX) # 画一个白色圆圈
        self.image = self.image_orig.copy() # 当前显示的图像
        self.rect = self.image.get_rect()   # 图像的矩形
        self.hit_rect = PLAYER_HIT_RECT.copy() # 用于碰撞检测的矩形
        self.pos = pygame.Vector2(pos)      # 玩家中心位置 (世界坐标)
        self.vel = pygame.Vector2(0, 0)     # 玩家速度向量
        self.rect.center = self.pos         # 初始化图像矩形位置
        self.hit_rect.center = self.rect.center # 初始化碰撞矩形位置

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

        # --- 移动与速度 ---
        self.base_speed: float = PLAYER_SPEED # 基础移动速度 (像素/帧)
        self.current_speed: float = self.base_speed # 当前移动速度
        self.speed_boost_factor: float = 1.0 # 速度加成因子
        self.speed_boost_timer: float = 0 # 加速效果剩余时间 (帧)

        # --- 状态计时器 ---
        self.hunger_decay_timer: float = 0 # 饱食度衰减计时器 (帧)
        self.hunger_warn_timer: float = 0  # 饥饿警告音效计时器 (帧)
        self.match_out_timer: float = 0    # 火柴耗尽后的死亡计时器 (帧)
        self.is_dead: bool = False         # 标记玩家是否死亡
        self.death_reason: str = ""        # 玩家死亡原因

        # 火柴魔法效果计时器 (当前未使用)
        self.magic_match_timer: float = 0

    def get_input(self):
        """处理玩家输入，更新速度向量。"""
        self.vel = pygame.Vector2(0, 0) # 每帧重置速度
        keys = pygame.key.get_pressed() # 获取当前按下的按键

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

    def move(self, dt: float):
        """根据速度移动玩家，并处理碰撞。 dt 未在此函数中使用，因为速度是像素/帧。"""
        if self.vel.length_squared() > 0: # 仅在有速度时移动和检测碰撞
            new_pos = self.pos + self.vel # 计算潜在的新位置
            self.check_collisions(new_pos) # 检查碰撞并更新实际位置 self.pos
            # 播放脚步声 (可以限制频率避免太吵)
            # if random.random() < 0.1: self.game.asset_manager.play_sound('step')
        # 更新 sprite 的 rect 位置
        self.rect.center = self.pos
        self.hit_rect.center = self.rect.center

    def check_collisions(self, potential_pos: pygame.Vector2):
        """检查玩家在潜在新位置是否与墙壁、物品、怪物或出口碰撞，并更新实际位置。"""

        # --- 墙壁碰撞检测 (分开处理 x 和 y 轴，允许贴墙滑动) ---
        new_pos_x = pygame.Vector2(potential_pos.x, self.pos.y)
        new_pos_y = pygame.Vector2(self.pos.x, potential_pos.y)

        # 检查 X 轴移动
        potential_hit_rect_x = self.hit_rect.copy()
        potential_hit_rect_x.centerx = new_pos_x.x
        collision_x = False
        # 获取可能碰撞的瓦片范围
        tile_range_x = range(int(potential_hit_rect_x.left // TILE_SIZE), int(potential_hit_rect_x.right // TILE_SIZE) + 1)
        tile_range_y = range(int(potential_hit_rect_x.top // TILE_SIZE), int(potential_hit_rect_x.bottom // TILE_SIZE) + 1)
        for x in tile_range_x:
            for y in tile_range_y:
                 if self.game.maze.is_wall(x, y): # 如果是墙
                      wall_tile_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                      if potential_hit_rect_x.colliderect(wall_tile_rect): # 发生碰撞
                           collision_x = True
                           # 碰撞后将玩家位置吸附到墙边
                           if self.vel.x > 0: #向右移动撞墙
                               self.pos.x = wall_tile_rect.left - self.hit_rect.width / 2
                           elif self.vel.x < 0: # 向左移动撞墙
                               self.pos.x = wall_tile_rect.right + self.hit_rect.width / 2
                           self.vel.x = 0 # X 轴速度清零
                           potential_hit_rect_x.centerx = self.pos.x # 更新X轴的hit_rect位置
                           break # 停止内层循环
            if collision_x: break # 停止外层循环

        if not collision_x:
             self.pos.x = new_pos_x.x # 没有碰撞则更新 X 坐标

        # 检查 Y 轴移动
        potential_hit_rect_y = self.hit_rect.copy()
        potential_hit_rect_y.centery = new_pos_y.y
        potential_hit_rect_y.centerx = self.pos.x # 使用更新后的 X 坐标
        collision_y = False
        # 更新可能碰撞的瓦片范围 (X轴位置可能已改变)
        tile_range_x = range(int(potential_hit_rect_y.left // TILE_SIZE), int(potential_hit_rect_y.right // TILE_SIZE) + 1)
        tile_range_y = range(int(potential_hit_rect_y.top // TILE_SIZE), int(potential_hit_rect_y.bottom // TILE_SIZE) + 1)
        for x in tile_range_x:
            for y in tile_range_y:
                 if self.game.maze.is_wall(x, y):
                      wall_tile_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                      if potential_hit_rect_y.colliderect(wall_tile_rect):
                           collision_y = True
                           # 碰撞后将玩家位置吸附到墙边
                           if self.vel.y > 0: # 向下移动撞墙
                               self.pos.y = wall_tile_rect.top - self.hit_rect.height / 2
                           elif self.vel.y < 0: # 向上移动撞墙
                               self.pos.y = wall_tile_rect.bottom + self.hit_rect.height / 2
                           self.vel.y = 0 # Y 轴速度清零
                           potential_hit_rect_y.centery = self.pos.y # 更新Y轴的hit_rect位置
                           break
            if collision_y: break

        if not collision_y:
             self.pos.y = new_pos_y.y # 没有碰撞则更新 Y 坐标

        # 最终更新所有 rect 的位置
        self.rect.center = self.pos
        self.hit_rect.center = self.rect.center


        # --- 物品碰撞检测 ---
        # 使用 spritecollide 检测玩家和 items 组中的精灵碰撞
        # False 表示不删除碰撞的物品精灵 (让物品自己处理)
        # pygame.sprite.collide_rect_ratio(0.8) 使用缩小一点的矩形进行碰撞判断，感觉更精确
        items_hit = pygame.sprite.spritecollide(self, self.game.items, False, pygame.sprite.collide_rect_ratio(0.8))
        for item in items_hit:
            if isinstance(item, Item): # 确保是 Item 类型的对象
                 if item.interact(self): # 调用物品的 interact 方法
                    if SAVE_ON_PICKUP: # 如果设置了拾取时存档
                        self.game.save_game_state() # 执行存档

        # --- 怪物碰撞检测 ---
        monsters_hit = pygame.sprite.spritecollide(self, self.game.monsters, False, pygame.sprite.collide_rect_ratio(0.7))
        for monster in monsters_hit:
            if not self.is_dead and isinstance(monster, Monster): # 确保玩家还活着且对象是怪物
                self.handle_monster_collision(monster) # 处理与怪物的碰撞

        # --- 出口碰撞检测 ---
        exit_rect = self.game.maze.get_exit_rect() # 获取出口的矩形区域
        if exit_rect and self.hit_rect.colliderect(exit_rect): # 如果存在出口且玩家碰撞到
             self.game.win_game() # 调用游戏胜利逻辑


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

    def update(self, dt: float):
        """每帧更新玩家状态。"""
        if self.is_dead: # 如果玩家已死亡，则不进行任何更新
            return

        self.get_input() # 处理输入
        self.move(dt)    # 处理移动和碰撞

        # 更新状态计时器和属性
        self.update_hunger(dt)
        self.update_matches(dt)
        self.update_speed_boost(dt)
        self.update_magic_match(dt)

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

    def update_hunger(self, dt: float):
        """更新饱食度。"""
        self.hunger_decay_timer += dt * FPS # 累加计时器 (帧)
        if self.hunger_decay_timer >= PLAYER_HUNGER_DECAY_INTERVAL:
            self.hunger_decay_timer = 0 # 重置计时器
            self.hunger = max(0, self.hunger - PLAYER_HUNGER_DECAY_RATE) # 减少饱食度，但不低于0
            # print(f"饱食度: {self.hunger}") # 调试信息

    def update_matches(self, dt: float):
        """更新当前燃烧的火柴状态。"""
        if self.current_match_index != -1 and self.current_match_index < len(self.matches):
            # 减少当前燃烧火柴的剩余时间
            self.matches[self.current_match_index] -= dt * FPS
            if self.matches[self.current_match_index] <= 0: # 如果这根火柴烧完了
                print("一根火柴烧尽了!")
                # 移除烧尽的火柴 (位于列表的最右边，即索引最高的位置)
                self.matches.pop(self.current_match_index)
                # 更新当前燃烧火柴的索引为新的最右边那个
                self.current_match_index = len(self.matches) - 1
                if self.current_match_index == -1: # 如果所有火柴都烧完了
                    print("所有火柴都烧尽了!")
                    # 停止燃烧音效 (如果正在播放)
                    # 需要找到播放燃烧音效的channel并停止，或者直接停止所有该音效
                    # self.game.asset_manager.stop_sound('match_burn') # 假设有 stop_sound 方法
                    # 或者停止音乐模块？不合适。需要精确控制循环音效。
                    # 简单处理：在 add_match 时才播放循环音效，耗尽时不主动停止，让它自然结束？
                    # 更好的方法：记录播放 channel
                    pass
                else:
                    # 如果换了新火柴，确保燃烧音效在播放
                    # self.game.asset_manager.play_sound('match_burn', loops=-1)
                    pass

    def update_speed_boost(self, dt: float):
        """更新速度加成效果的持续时间。"""
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt * FPS # 减少剩余时间 (帧)
            if self.speed_boost_timer <= 0:
                self.speed_boost_timer = 0 # 时间耗尽
                self.speed_boost_factor = 1.0 # 恢复速度因子
                self.current_speed = self.base_speed # 恢复基础速度
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


    def add_weapon(self, weapon_item: 'WeaponItem'):
        """将拾取的武器添加到玩家库存。"""
        # 按获取顺序添加到列表末尾
        self.inventory['weapons'].append(weapon_item)
        print(f"拾取到武器: {weapon_item.weapon_type}, 可用次数: {weapon_item.uses}。当前武器数量: {len(self.inventory['weapons'])}")

    def apply_speed_boost(self, factor: float, duration_frames: float):
        """应用速度加成效果。"""
        self.speed_boost_factor = factor
        self.speed_boost_timer = duration_frames
        self.current_speed = self.base_speed * self.speed_boost_factor # 更新当前速度
        print(f"获得速度加成！当前速度: {self.current_speed / TILE_SIZE * FPS:.1f} 米/秒")

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