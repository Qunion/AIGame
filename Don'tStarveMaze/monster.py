import pygame
import random
from settings import *
import math
from pathfinding.core.grid import Grid # 需要 Grid 来检查节点有效性 (虽然主要在 maze 中使用)
from pathfinding.finder.a_star import AStarFinder # A* 算法
from typing import TYPE_CHECKING, Optional, List, Tuple

if TYPE_CHECKING:
    from main import Game

class Monster(pygame.sprite.Sprite):
    """怪物基类，定义通用行为和属性。"""
    def __init__(self, game: 'Game', pos: Tuple[float, float], name: str, monster_type: str):
        self._layer = MONSTER_LAYER # 设置怪物图层
        self.groups = game.all_sprites, game.monsters # 添加到 all_sprites 和 monsters 组
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.game = game              # 游戏主对象的引用
        self.name = name              # 怪物名字 (例如 "战士哥哥")
        self.monster_type = monster_type # 怪物类型 ('warrior' 或 'mage')

        # 根据名字/类型决定使用哪个图片 (简单示例)
        # 假设名字包含"哥哥"或"姐姐"的是1号，"弟弟"或"妹妹"是2号
        img_suffix = '1' if "哥哥" in name or "姐姐" in name else '2'
        image_key = f'monster_{monster_type}_{img_suffix}'
        self.image_orig = game.asset_manager.get_image(image_key) # 加载原始图片
        if self.image_orig is None: # 处理图片加载失败
             self.image_orig = pygame.Surface(MONSTER_IMAGE_SIZE, pygame.SRCALPHA).convert_alpha()
             # 根据类型填充不同颜色的备用图像
             color = RED if 'warrior' in monster_type else BLUE
             self.image_orig.fill((0,0,0,0)) # 透明背景
             pygame.draw.rect(self.image_orig, color, self.image_orig.get_rect(), border_radius=5) # 画个圆角矩形
        self.image = self.image_orig.copy() # 当前显示的图像
        self.rect = self.image.get_rect()   # 图像矩形
        self.hit_rect = MONSTER_HIT_RECT.copy() # 碰撞矩形
        self.pos = pygame.Vector2(pos)      # 怪物中心位置 (世界坐标)
        self.vel = pygame.Vector2(0, 0)     # 怪物速度向量
        self.rect.center = pos              # 初始化图像矩形位置
        self.hit_rect.center = self.rect.center # 初始化碰撞矩形位置

        # 怪物属性
        self.speed: float = PLAYER_SPEED * MONSTER_SPEED_FACTOR # 怪物移动速度
        self.is_active: bool = False      # 是否被玩家激活（看到玩家后激活）
        self.target_pos: Optional[pygame.Vector2] = None # 追击的目标位置 (通常是玩家位置或预测位置)
        self.path: List[Tuple[float, float]] = [] # 当前寻路路径 (世界坐标列表)
        self.current_path_segment: int = 0 # 当前路径段索引
        self.last_path_find_time: float = 0 # 上次计算路径的时间戳 (毫秒)
        self.path_find_interval: float = 0.5 * FPS # 重新计算路径的间隔 (帧)

        self.health: int = 1 # 怪物生命值 (默认1点，武器正好能击杀)

    def can_see_player(self) -> bool:
        """检查怪物所在的瓦片是否被玩家的光线照亮。"""
        # 获取怪物中心点所在的瓦片坐标
        monster_tile_x = int(self.pos.x // TILE_SIZE)
        monster_tile_y = int(self.pos.y // TILE_SIZE)
        # 检查该瓦片是否在光照系统的可见集合中
        return (monster_tile_x, monster_tile_y) in self.game.lighting.visible_tiles

    def update(self, dt: float):
        """每帧更新怪物状态和行为。"""
        # 检查是否能看到玩家以更新激活状态
        if self.can_see_player():
            if not self.is_active: # 如果之前未激活
                 print(f"{self.name} 发现了玩家！正在激活！")
                 self.game.asset_manager.play_sound('monster_roar') # 播放发现玩家的吼叫声
                 self.is_active = True # 设置为激活状态
            # 持续更新目标位置为当前玩家位置（即使已激活）
            # self.target_pos = self.game.player.pos.copy() # 在 chase_player 中计算目标

        # 如果怪物已激活
        if self.is_active:
            # 计算到玩家的路径距离
            path_distance = self.get_path_distance_to_player()

            # 如果距离超过阈值，则失去目标，变为非激活状态
            if path_distance >= MONSTER_DESPAWN_DISTANCE_TILES:
                if self.is_active: # 只有在之前是激活状态才打印失活信息
                    print(f"{self.name} 跟丢了玩家 (距离: {path_distance:.0f} 格)。正在停止追击。")
                    self.is_active = False # 设置为非激活
                    self.path = []         # 清空路径
                    self.vel = pygame.Vector2(0, 0) # 停止移动
            else: # 如果距离在范围内，则继续追击
                self.chase_player(dt)
        else: # 如果未激活
             self.vel = pygame.Vector2(0, 0) # 确保怪物停止移动


        # 根据速度更新位置 (速度 chase_player 中计算)
        # 速度已经是 像素/帧，直接加即可
        self.pos += self.vel
        # 更新 sprite 的 rect 位置
        self.rect.center = self.pos
        self.hit_rect.center = self.rect.center

    def get_path_distance_to_player(self) -> float:
        """获取到玩家当前位置的路径距离（格子数量）。"""
        # 调用迷宫的寻路方法
        _, path_len = self.game.maze.find_path(self.pos, self.game.player.pos)
        # path_len 是格子数 (包含起点)，所以实际距离是 path_len 或 path_len - 1
        # 这里返回格子数，与 MONSTER_DESPAWN_DISTANCE_TILES 比较
        return path_len if path_len != float('inf') else float('inf')


    def calculate_target_position(self) -> pygame.Vector2:
        """计算怪物应该移动向的目标位置。"""
        player = self.game.player

        # 战士：直接朝玩家当前位置移动
        if self.monster_type == 'warrior':
            return player.pos.copy()

        # 法师：预测玩家前方位置
        elif self.monster_type == 'mage':
            # 获取玩家当前速度方向 (如果玩家静止，则无法预测)
            player_dir = player.vel.normalize() if player.vel.length_squared() > 0 else pygame.Vector2(0, 0)

            # 如果玩家没有移动，则直接以玩家为目标
            if player_dir.length_squared() == 0:
                return player.pos.copy()

            # 从最远预测距离开始尝试
            for steps in range(MONSTER_PREDICTION_STEPS, 0, -1):
                 predict_dist = steps * TILE_SIZE # 预测的像素距离
                 predicted_pos = player.pos + player_dir * predict_dist # 计算预测的世界坐标

                 # 检查预测位置所在的瓦片是否是通路
                 predict_tile_x = int(predicted_pos.x // TILE_SIZE)
                 predict_tile_y = int(predicted_pos.y // TILE_SIZE)

                 # 如果预测位置有效且不是墙
                 if self.game.maze._is_valid(predict_tile_x, predict_tile_y) and \
                    not self.game.maze.is_wall(predict_tile_x, predict_tile_y):
                     # print(f"法师预测玩家 {steps} 格距离的位置。")
                     return predicted_pos # 返回有效的预测位置

            # 如果所有预测位置都是墙或无效，则回退到直接以玩家为目标
            # print("法师所有预测位置均无效，改为直接追踪玩家。")
            return player.pos.copy()

        # 默认情况（如果类型未知）也直接追踪玩家
        return player.pos.copy()


    def chase_player(self, dt: float):
        """根据怪物类型计算目标，并使用寻路算法移动怪物。"""
        target_world_pos = self.calculate_target_position() # 获取要追击的目标点
        current_time = pygame.time.get_ticks() # 获取当前时间 (毫秒)

        # 判断是否需要重新计算路径
        # 条件：没有路径 / 路径已走完 / 距离上次计算超过时间间隔
        needs_recalc = False
        if not self.path or self.current_path_segment >= len(self.path):
            needs_recalc = True
        elif current_time - self.last_path_find_time > self.path_find_interval * (1000 / FPS): # 间隔是帧数，转毫秒
             needs_recalc = True
             # print(f"{self.name} 重新计算路径 (时间间隔)")


        if needs_recalc:
            # 调用迷宫寻路方法获取新路径
            new_path_nodes, _ = self.game.maze.find_path(self.pos, target_world_pos)
            if new_path_nodes and len(new_path_nodes) > 1: # 路径有效且至少包含下一步
                # world_path 是包含起点的世界坐标列表
                self.path = new_path_nodes[1:] # 获取除起点外的路径点
                self.current_path_segment = 0  # 从路径的第一个点开始
                # print(f"{self.name} 计算得到新路径，共 {len(self.path)} 步。")
            else: # 如果找不到路径或路径太短
                # print(f"{self.name} 无法找到有效路径或路径太短。")
                self.path = [] # 清空路径
                self.vel = pygame.Vector2(0, 0) # 停止移动
                # return # 停止追击逻辑？或者原地等待？当前选择原地停止

            self.last_path_find_time = current_time # 更新上次计算时间

        # 沿着当前路径移动
        if self.path and self.current_path_segment < len(self.path):
            # 获取当前路径段的目标节点世界坐标
            target_node_pos = pygame.Vector2(self.path[self.current_path_segment])
            # 计算朝向目标节点的方向向量
            direction = (target_node_pos - self.pos)

            # 检查是否足够接近当前目标节点
            # 使用速度的 1.5 倍作为阈值，避免抖动
            if direction.length_squared() < (self.speed * 1.5)**2:
                 # 到达节点，移动到下一个路径段
                 self.current_path_segment += 1
                 # 检查是否到达路径终点
                 if self.current_path_segment >= len(self.path):
                      # print(f"{self.name} 到达路径终点。")
                      self.path = [] # 清空路径，下一帧可能会重新计算
                      self.vel = pygame.Vector2(0, 0) # 暂时停止
                      return # 结束本次移动计算
                 else: # 更新目标节点为路径中的下一个点
                     target_node_pos = pygame.Vector2(self.path[self.current_path_segment])
                     # 重新计算方向向量
                     direction = (target_node_pos - self.pos)

            # 设置速度向量朝向目标节点
            if direction.length_squared() > 0: # 确保方向向量非零
                self.vel = direction.normalize() * self.speed
            else: # 如果刚好在目标点上或方向为零
                self.vel = pygame.Vector2(0, 0) # 停止

        else: # 如果没有路径或路径已完成
            self.vel = pygame.Vector2(0, 0) # 停止移动


    def take_damage(self):
        """处理怪物受到伤害。"""
        self.health -= 1 # 生命值减 1
        if self.health <= 0: # 如果生命值耗尽
            print(f"{self.name} 被击败了!")
            # 播放怪物死亡音效（如果与其他音效冲突需要处理）
            # self.game.asset_manager.play_sound('monster_die')
            # --- 新增：根据怪物类型给予玩家尸体标记物 ---
            corpse_marker_id = None
            if self.name == "法师姐姐": corpse_marker_id = 'monster_mage_corpse_1'
            elif self.name == "法师妹妹": corpse_marker_id = 'monster_mage_corpse_2'
            elif self.name == "战士哥哥": corpse_marker_id = 'monster_warrior_corpse_1'
            elif self.name == "战士弟弟": corpse_marker_id = 'monster_warrior_corpse_2'

            if corpse_marker_id:
                self.game.player.add_marker(corpse_marker_id) # 通知玩家获得标记物
            # ---------------------------------------
            self.kill() # 从所有精灵组中移除怪物