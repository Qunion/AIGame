import pygame
import sys
import random
import os
import pickle
import noise # 确保导入 noise 库
from markers import Marker

from settings import *           # 导入所有设置常量
from assets import AssetManager  # 导入资源管理器
from maze import Maze, Tile      # 导入迷宫和瓦片类
from player import Player        # 导入玩家类
from items import MatchItem, FoodItem, WeaponItem # 导入物品类
from monster import Monster      # 导入怪物类
from lighting import Lighting    # 导入光照和视野类
from camera import Camera        # 导入摄像机类
# 导入 UI 绘制函数
from ui import draw_player_hud, draw_game_over_screen, draw_win_screen, draw_pause_screen, draw_text
# 导入存档/读档函数
from save_load import save_game, load_game, capture_game_state, restore_game_state
from typing import Tuple # 导入需要用到的类型提示


class Game:
    """游戏主类，管理游戏循环、状态和对象。"""
    def __init__(self):
        """初始化 Pygame、窗口、时钟和资源管理器。"""
        pygame.init()
        # 优先初始化混音器，使用推荐参数
        try:
             pygame.mixer.pre_init(44100, -16, 2, 512) # 频率, 格式(16位有符号), 声道数, 缓冲区大小
             pygame.mixer.init()
             print("Pygame 混音器初始化成功。")
        except pygame.error as e:
             print(f"初始化 Pygame 混音器时出错: {e}。音效将被禁用。")

        # 创建游戏窗口
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_TITLE) # 设置窗口标题
        self.clock = pygame.time.Clock() # 创建时钟对象，用于控制帧率
        self.running = True        # 游戏主循环运行标志
        self.paused = False        # 游戏暂停标志
        self.game_over = False     # 游戏结束标志
        self.game_won = False      # 游戏胜利标志
        self.asset_manager = AssetManager() # 创建并初始化资源管理器（加载资源）
        self.dt = 0.0 # 初始化时间增量

    def setup_new_game(self):
        """初始化新游戏的所有对象和状态。"""
        print("正在设置新游戏...")
        # 使用 LayeredUpdates 可以更好地控制精灵绘制顺序（基于 _layer 属性）
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.walls = pygame.sprite.Group()       # 存储墙体精灵（当前未使用，迷宫直接绘制）
        self.items = pygame.sprite.Group()       # 存储地面上的物品精灵
        self.monsters = pygame.sprite.Group()    # 存储怪物精灵
        self.markers_placed = pygame.sprite.Group() # 新增：存储已放置标记物的组

        # 创建迷宫实例 (会自动生成迷宫)
        self.maze = Maze(self, GRID_WIDTH, GRID_HEIGHT)

        # 确保玩家起始位置有效
        if self.maze.player_start_pos is None:
             print("错误：无法从迷宫确定玩家起始位置。")
             self.running = False # 发生严重错误，停止游戏
             return
        # 创建玩家实例
        self.player = Player(self, self.maze.player_start_pos)

        # 创建摄像机实例
        self.camera = Camera(WIDTH, HEIGHT)
        # 创建光照/视野系统实例
        self.lighting = Lighting(self)

        # --- 在迷宫中放置物品 ---
        placed_tiles = set() # 记录已放置物品或玩家/出口的瓦片坐标，避免重叠
        # 将玩家起始瓦片加入已占用集合
        player_tile = (int(self.player.pos.x // TILE_SIZE), int(self.player.pos.y // TILE_SIZE))
        placed_tiles.add(player_tile)
        # 将出口瓦片加入已占用集合
        if self.maze.exit_pos: placed_tiles.add(self.maze.exit_pos)

        # 定义一个辅助函数来获取一个随机的、未被占用的地面瓦片的世界坐标
        def get_spawn_pos() -> Tuple[float, float]:
            attempts = 0
            while attempts < GRID_WIDTH * GRID_HEIGHT: # 避免死循环
                # --- 修改开始 ---
                # 从迷宫获取 瓦片坐标 和 世界坐标
                # 使用 _ 来忽略我们暂时不需要的瓦片坐标（但我们马上会用到）
                # tile_coords, pos_world = self.maze.get_random_floor_tile()
                # 或者更清晰地命名：
                found_tile_coords, found_pos_world = self.maze.get_random_floor_tile()

                # 将瓦片坐标用于检查是否已占用
                # pos_tile = (int(pos_world[0] // TILE_SIZE), int(pos_world[1] // TILE_SIZE)) # <--- 旧的错误行
                pos_tile = found_tile_coords # <--- 直接使用返回的瓦片坐标

                # 检查该瓦片是否已被占用
                if pos_tile not in placed_tiles:
                    placed_tiles.add(pos_tile) # 标记为已占用
                    return found_pos_world # 返回可用的世界坐标
                # --- 修改结束 ---
                attempts += 1
            # 如果尝试了很多次都找不到空位（理论上不应发生）
            print("警告：找不到合适的空闲位置来放置物品！")
            # 返回一个默认位置或地图中心？这里返回(0,0)可能导致问题，返回第一个随机位置
            return self.maze.get_random_floor_tile()


        print("正在放置物品...")
        # 放置火柴
        for _ in range(MATCH_SPAWN_COUNT): MatchItem(self, get_spawn_pos())
        # 放置面包
        for _ in range(FOOD_BREAD_COUNT): FoodItem(self, get_spawn_pos(), 'bread')
        # 放置肉
        for _ in range(FOOD_MEAT_COUNT): FoodItem(self, get_spawn_pos(), 'meat')
        # 放置武器
        WeaponItem(self, get_spawn_pos(), 'broken') # 放置断剑
        WeaponItem(self, get_spawn_pos(), 'good')   # 放置好剑

        # --- 在迷宫中放置怪物 ---
        print("正在放置怪物...")
        # 创建怪物索引和区域索引列表，并打乱顺序，实现随机分配
        monster_indices = list(range(MONSTER_COUNT))
        random.shuffle(monster_indices)
        zone_indices = list(range(len(MONSTER_SPAWN_ZONES)))
        random.shuffle(zone_indices)

        # 遍历每个怪物，分配到随机区域的随机位置
        for i in range(MONSTER_COUNT):
             zone_idx = zone_indices[i] # 获取随机选择的区域索引
             monster_idx = monster_indices[i] # 获取随机选择的怪物索引
             zone = MONSTER_SPAWN_ZONES[zone_idx] # 获取区域范围 (网格坐标)
             name = MONSTER_NAMES[monster_idx]    # 获取怪物名称
             m_type = MONSTER_TYPES[monster_idx]  # 获取怪物类型

             # 在指定区域内寻找一个随机的、未被占用的地面瓦片
             attempts = 0
             max_zone_attempts = (zone[2] - zone[0]) * (zone[3] - zone[1]) * 2 # 区域内尝试次数
             while attempts < max_zone_attempts:
                 # 在区域内随机选择一个瓦片坐标
                 x = random.randint(zone[0], zone[2] - 1)
                 y = random.randint(zone[1], zone[3] - 1)
                 # 检查是否是地面且未被占用
                 if not self.maze.is_wall(x, y) and (x, y) not in placed_tiles:
                      # 计算世界坐标中心点
                      pos_world = (x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2)
                      # 创建怪物实例
                      Monster(self, pos_world, name, m_type)
                      placed_tiles.add((x, y)) # 标记瓦片为已占用
                      print(f"已放置 {name} ({m_type}) 在区域 {zone_idx} 的坐标 {(x, y)}")
                      break # 成功放置，跳出内部循环
                 attempts += 1
             else: # 如果在区域内尝试多次仍未找到位置
                  print(f"警告: 未能在区域 {zone_idx} 为 {name} 找到合适位置。将在随机位置放置。")
                  # 后备方案：在地图上随机找一个空位
                  Monster(self, get_spawn_pos(), name, m_type)

        # 初始化光照/视野系统
        self.lighting.update(self.player)

        # 播放背景音乐
        self.asset_manager.play_music('background')

        # 重置游戏状态标志
        self.game_over = False
        self.game_won = False
        self.paused = False # 确保新游戏不是暂停状态

    def try_load_game(self) -> bool:
        """尝试从文件加载游戏状态。"""
        print(f"尝试从 {SAVE_FILE} 加载游戏...")
        saved_state = load_game() # 调用加载函数
        if saved_state:
            # --- 加载成功，需要重建游戏对象 ---
            # 必须先初始化基本的游戏结构（精灵组等）
            self.all_sprites = pygame.sprite.LayeredUpdates()
            self.walls = pygame.sprite.Group()
            self.items = pygame.sprite.Group()
            self.monsters = pygame.sprite.Group()
            self.markers_placed = pygame.sprite.Group() # 新增：初始化组
            # 创建临时的迷宫和玩家对象，restore_game_state 会填充它们
            # 注意：这里传递 self (Game 实例) 给 Maze 和 Player
            self.maze = Maze(self, GRID_WIDTH, GRID_HEIGHT) # Maze 会生成，但会被覆盖
            # 玩家需要一个初始位置，即使是临时的
            temp_start_pos = (GRID_WIDTH // 2 * TILE_SIZE, GRID_HEIGHT // 2 * TILE_SIZE)
            self.player = Player(self, temp_start_pos)
            self.camera = Camera(WIDTH, HEIGHT)
            self.lighting = Lighting(self)

            # 调用恢复函数，用加载的数据填充游戏对象
            if restore_game_state(self, saved_state):
                print("游戏状态加载并恢复成功。")
                self.asset_manager.play_music('background') # 重新播放背景音乐
                self.game_over = False # 重置状态标志
                self.game_won = False
                self.paused = False
                return True # 返回加载成功
            else:
                print("恢复游戏状态失败，将开始新游戏。")
                # 如果恢复失败（例如存档损坏），则不返回 True，让 run() 方法调用 setup_new_game()
        return False # 没有找到存档文件或加载/恢复失败

    def run(self):
        """游戏主循环。"""
        # 尝试加载游戏，如果失败则设置新游戏
        if not self.try_load_game():
            self.setup_new_game()

        # 主循环开始
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0 # 获取自上一帧以来的时间（秒）
            self.events() # 处理事件
            # 只有在非暂停、非游戏结束、非胜利状态下才更新游戏逻辑
            if not self.paused and not self.game_over and not self.game_won:
                self.update() # 更新游戏状态
            self.draw()   # 绘制游戏画面

        # 游戏主循环结束 (running 变为 False)
        # 如果是正常退出（非胜利非结束），且设置了退出时存档
        if SAVE_ON_EXIT and not self.game_won and not self.game_over:
            self.save_game_state() # 保存游戏状态
        pygame.quit() # 卸载 Pygame 模块
        sys.exit()    # 退出程序

    def events(self):
        """处理所有游戏事件（输入、关闭窗口等）。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT: # 点击关闭按钮
                self.running = False
            elif event.type == pygame.KEYDOWN: # 按下键盘按键
                if event.key == pygame.K_ESCAPE: # 按下 ESC 键
                    self.running = False
                elif event.key == pygame.K_f:
                    # --- 修改：区分暂停和放置标记物 ---
                    if self.game_over or self.game_won: # 如果游戏结束，空格无效
                         pass
                    elif self.paused: # 如果是暂停状态，空格取消暂停
                        self.paused = False
                        pygame.mixer.music.unpause()
                        print("游戏已恢复")
                    # else: # 如果非暂停状态，空格尝试放置标记物，然后才切换暂停
                    #     if hasattr(self, 'player'):
                    #         placed = self.player.try_place_marker()
                    elif hasattr(self, 'player') and not self.paused and not self.game_over and not self.game_won:
                         self.player.try_place_marker()
                elif event.key == pygame.K_SPACE: # 按下空格键
                    if not self.game_over and not self.game_won: # 结束后不能暂停
                        self.paused = not self.paused # 切换暂停状态
                        if self.paused:
                            pygame.mixer.music.pause() # 暂停音乐
                            print("游戏已暂停")
                        else:
                            pygame.mixer.music.unpause() # 取消暂停音乐
                            print("游戏已恢复")
                # 如果游戏已结束或胜利
                if self.game_over or self.game_won:
                    if event.key == pygame.K_r: # 按下 R 键 (重新开始)
                         self.setup_new_game() # 重新设置新游戏
                    if event.key == pygame.K_q: # 按下 Q 键 (退出)
                         self.running = False
                # --- 调试用按键 (可选) ---
                # if event.key == pygame.K_h: # 恢复饱食度
                #     if hasattr(self, 'player'): self.player.add_hunger(50)
                # if event.key == pygame.K_m: # 添加火柴
                #     if hasattr(self, 'player'): self.player.add_match()
                # if event.key == pygame.K_g: # 无敌模式开关 (需要实现对应逻辑)
                #     pass
                # if event.key == pygame.K_k: # 击杀最近的怪物 (需要实现)
                #      pass
                # if event.key == pygame.K_l: # 开关照亮墙壁
                #      if hasattr(self, 'lighting'):
                #           self.lighting.light_walls = not self.lighting.light_walls
                #           print(f"照亮墙壁: {self.lighting.light_walls}")


    def update(self):
        """更新所有游戏对象的状态。"""
        # 调用 all_sprites 组中所有精灵的 update 方法
        # 更新精灵组 (Player, Monster, Decoration 都会调用 update)
        # (Player 和 Monster 会在这里更新自己的状态、移动等)
        self.all_sprites.update(self.dt)
        # 更新摄像机，让其跟随玩家
        self.camera.update(self.player)
        # 更新光照/视野系统
        self.lighting.update(self.player)

        # 在玩家更新后检查其是否死亡
        if self.player.is_dead:
            self.game_over = True # 设置游戏结束标志

    def draw(self):
        """绘制所有游戏内容到屏幕上。"""
        self.screen.fill(BLACK) # 用黑色填充背景 (对于完全黑暗的区域)

        # 绘制迷宫 (会根据光照和记忆状态绘制)(包括不同地形的地板和墙壁)
        self.maze.draw(self.screen, self.camera, self.lighting)

        # 绘制所有精灵 (物品、玩家、怪物) (按图层顺序: Decoration -> Item -> Player/Monster)
        # LayeredUpdates 会自动按 _layer 属性排序绘制——会处理图层顺序
        for sprite in self.all_sprites:
             # --- 优化：只绘制在视野内的精灵 ---
             sprite_tile_x = int(sprite.pos.x // TILE_SIZE)
             sprite_tile_y = int(sprite.pos.y // TILE_SIZE)
             # 获取精灵所在瓦片的亮度
             brightness = self.lighting.get_tile_brightness(sprite_tile_x, sprite_tile_y)

             # 设置一个亮度阈值，太暗就不绘制精灵 (例如记忆中很模糊的地方)
             # 0.1 大约对应非常暗淡的记忆边缘
             # 如果想让记忆中的物品/怪物也可见，可以降低阈值或始终绘制记忆中的
             # if pos in self.lighting.visible_tiles or pos in self.lighting.memory_tiles:
             if brightness > 0.05: # 稍微可见就绘制
                 # 可以选择根据亮度调整精灵图像的透明度或颜色 (较复杂)
                 # img_copy = sprite.image.copy()
                 # alpha = int(brightness * 255)
                 # img_copy.set_alpha(alpha)
                 # self.screen.blit(img_copy, self.camera.apply(sprite))

                 # 简单方式：只要亮度大于阈值，就正常绘制精灵
                 self.screen.blit(sprite.image, self.camera.apply(sprite))

        # --- 绘制可选的整体黑暗遮罩 (如果 Lighting 类实现了 draw_darkness) ---
        # self.lighting.draw_darkness(self.screen, self.camera, self.player)

        # --- 绘制 HUD (始终在最上层，不受相机影响) ---
        draw_player_hud(self.screen, self.player, self.asset_manager)

        # --- 根据游戏状态绘制 游戏结束 / 胜利 / 暂停 画面 ---
        if self.game_over:
            draw_game_over_screen(self.screen, self.player.death_reason, self.asset_manager)
        elif self.game_won:
            draw_win_screen(self.screen, self.asset_manager)
        elif self.paused:
            # 修改调用以反映暂停键是 P
            # draw_pause_screen(self.screen, self.asset_manager) # 旧调用
            self.draw_pause_screen_custom() # 使用自定义绘制，提示用 P

        # --- 绘制 FPS (可选的调试信息) ---
        # draw_text(self.screen, f"FPS: {self.clock.get_fps():.2f}", 18, 10, 10, YELLOW, align="topleft")

        # 更新整个屏幕显示
        pygame.display.flip()

    # --- 新增：自定义暂停界面绘制 ---
    def draw_pause_screen_custom(self):
        """绘制游戏暂停画面。"""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((50, 50, 50, 180))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "游戏暂停", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
        draw_text(self.screen, "按 空格 键继续", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")

    def win_game(self):
        """处理游戏胜利逻辑。"""
        # 确保只触发一次胜利
        if not self.game_won and not self.game_over:
             print("玩家到达出口！你赢了！")
             self.game_won = True # 设置胜利标志
             self.asset_manager.play_sound('win') # 播放胜利音效
             self.asset_manager.stop_music()     # 停止背景音乐
             # 可选：游戏胜利后删除存档文件
             if os.path.exists(SAVE_FILE):
                  try:
                       os.remove(SAVE_FILE)
                       print(f"存档文件 {SAVE_FILE} 已删除。")
                  except OSError as e:
                       print(f"删除存档文件时出错: {e}")

    def save_game_state(self):
        """捕获当前游戏状态并保存到文件。"""
        print("正在保存游戏状态...")
        state = capture_game_state(self) # 获取状态字典
        save_game(state) # 调用保存函数

# --- 主程序入口 ---
if __name__ == '__main__':
    game = Game() # 创建游戏实例
    game.run()    # 开始游戏主循环