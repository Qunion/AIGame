# --- START OF FILE sprites.py ---

import pygame
import random
import time
from settings import * # 导入设置
from collections import deque

# --- 蛇 类 ---
class Snake:
    def __init__(self, game):
        self.game = game
        self.grid_size = GRID_SIZE
        self.color = DARK_YELLOW
        self.body = deque()
        self.direction = random.choice([UP, DOWN, LEFT, RIGHT]) # 初始方向
        self.last_move_direction = self.direction # 记录上一帧实际移动方向
        self.new_direction = self.direction # 缓冲下一个方向
        self.length = INITIAL_SNAKE_LENGTH
        self.is_accelerating = False
        self.alive = True
        self.split_available = True
        self.current_head_angle = None # 用于优化头部旋转

        # 加载精灵图像时明确指定大小为 GRID_SIZE
        self.head_image_orig = load_image('snake_head.png', size=self.grid_size)
        self.body_image = load_image('snake_body.png', size=self.grid_size)

        # 图像加载失败检查
        if not self.head_image_orig:
            print("错误：未能加载 snake_head.png")
            self.head_image_orig = pygame.Surface((self.grid_size, self.grid_size)); self.head_image_orig.fill(self.color)
        if not self.body_image:
            print("错误：未能加载 snake_body.png")
            self.body_image = pygame.Surface((self.grid_size, self.grid_size)); self.body_image.fill(GREY)

        self.head_image = self.head_image_orig

        # 初始化蛇位置
        start_x = CANVAS_GRID_WIDTH // 2; start_y = CANVAS_GRID_HEIGHT // 2
        for i in range(self.length):
            segment_x = start_x - self.direction[0] * i; segment_y = start_y - self.direction[1] * i
            segment_x = max(0, min(CANVAS_GRID_WIDTH - 1, segment_x)); segment_y = max(0, min(CANVAS_GRID_HEIGHT - 1, segment_y))
            self.body.appendleft((segment_x, segment_y))

        self.update_head_image() # 调用旋转方法

    def get_head_position(self):
        """获取蛇头的格子坐标。"""
        if hasattr(self, 'body') and self.body:
            return self.body[-1]
        else:
            return (CANVAS_GRID_WIDTH // 2, CANVAS_GRID_HEIGHT // 2)

    def update_head_image(self):
        """根据当前实际移动方向旋转蛇头图像。"""
        direction_to_render = self.last_move_direction
        angle = 0
        if isinstance(direction_to_render, tuple) and len(direction_to_render) == 2:
            if direction_to_render == UP: angle = 0
            elif direction_to_render == DOWN: angle = 180
            elif direction_to_render == LEFT: angle = 90
            elif direction_to_render == RIGHT: angle = -90
        else: pass # 忽略无效方向

        if hasattr(self, 'head_image_orig') and self.head_image_orig:
            try:
                if self.current_head_angle != angle: # 仅当角度变化时旋转
                    self.head_image = pygame.transform.rotate(self.head_image_orig, angle)
                    self.current_head_angle = angle
            except Exception as e:
                print(f"旋转蛇头图像时出错: {e}")
                if not hasattr(self, 'head_image') or not self.head_image: self.head_image = self.head_image_orig
        else: # head_image_orig 不存在
            if not hasattr(self, 'head_image') or not self.head_image: self.head_image = pygame.Surface((self.grid_size, self.grid_size)); self.head_image.fill(self.color)

    def grow(self, amount=1):
        """增加蛇的目标长度。"""
        self.length += amount

    def change_direction(self, new_dir):
        """尝试改变蛇的移动方向（缓冲）。"""
        if (new_dir[0] != -self.last_move_direction[0] or \
            new_dir[1] != -self.last_move_direction[1]):
           self.new_direction = new_dir

    def update(self):
        """更新蛇的状态（处理方向缓冲、移动、移除尾巴）。"""
        current_direction = self.direction
        if (self.new_direction[0] != -self.last_move_direction[0] or \
            self.new_direction[1] != -self.last_move_direction[1]):
             current_direction = self.new_direction
        else: self.new_direction = current_direction # 重置无效的反向缓冲

        self.last_move_direction = current_direction
        self.direction = current_direction

        head_x, head_y = self.get_head_position()
        move_x, move_y = self.direction
        new_head = (head_x + move_x, head_y + move_y)

        self.check_collisions(new_head) # 内部碰撞检测

        if self.alive:
            self.body.append(new_head)
            if len(self.body) > self.length: self.body.popleft()
            self.update_head_image() # 更新头部图像朝向
        # else: 死亡时不移动

        self.split_available = self.length >= SPLIT_MIN_LENGTH

    def check_collisions(self, new_head):
        """仅检查新头位置是否撞墙或撞自身。"""
        head_x, head_y = new_head
        if not (0 <= head_x < CANVAS_GRID_WIDTH and 0 <= head_y < CANVAS_GRID_HEIGHT):
            self.alive = False; self.game.trigger_game_over("撞墙"); return
        check_body = list(self.body)
        if len(self.body) >= self.length: check_body = check_body[1:]
        if new_head in check_body:
             self.alive = False; self.game.trigger_game_over("撞到自己"); return

    def draw(self, surface, camera_offset=(0, 0)):
        """绘制蛇的身体和头部。"""
        offset_x, offset_y = 0, 0
        num_segments = len(self.body)
        for i in range(num_segments - 1): # 绘制身体
            segment = self.body[i]; seg_x, seg_y = segment; pixel_x = seg_x * self.grid_size + offset_x; pixel_y = seg_y * self.grid_size + offset_y
            alpha = max(0, 255 * (1 - (num_segments - 1 - i) * SNAKE_ALPHA_DECREASE_PER_SEGMENT))
            if self.body_image:
                if alpha < 254:
                    try: body_copy = self.body_image.copy(); body_copy.set_alpha(int(alpha)); surface.blit(body_copy, (pixel_x, pixel_y))
                    except Exception: pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size))
                else: surface.blit(self.body_image, (pixel_x, pixel_y))
            else: pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size))
        if num_segments > 0: # 绘制头部
             head = self.body[-1]; head_x, head_y = head; pixel_x = head_x * self.grid_size + offset_x; pixel_y = head_y * self.grid_size + offset_y
             if hasattr(self, 'head_image') and self.head_image: surface.blit(self.head_image, (pixel_x, pixel_y))
             else: pygame.draw.rect(surface, self.color, (pixel_x, pixel_y, self.grid_size, self.grid_size))
        if self.is_accelerating and self.alive: # 绘制速度线
            head_x, head_y = self.get_head_position()
            center_x = head_x * self.grid_size + self.grid_size // 2 + offset_x
            center_y = head_y * self.grid_size + self.grid_size // 2 + offset_y
            num_lines = 5; line_length = self.grid_size * 1.2; line_speed_offset = self.grid_size * 0.6
            back_dir_x, back_dir_y = -self.last_move_direction[0], -self.last_move_direction[1] # 基于上次移动方向绘制
            perp_dir_x, perp_dir_y = -back_dir_y, back_dir_x
            for i in range(num_lines):
                spread_factor = (i - num_lines // 2) * 0.3
                start_x = center_x + back_dir_x * line_speed_offset + perp_dir_x * spread_factor * self.grid_size; start_y = center_y + back_dir_y * line_speed_offset + perp_dir_y * spread_factor * self.grid_size
                end_x = start_x + back_dir_x * line_length; end_y = start_y + back_dir_y * line_length
                pygame.draw.line(surface, WHITE, (start_x, start_y), (end_x, end_y), 1)

    # ===============================================
    # ==========  修正后的 split 方法开始 ==========
    # ===============================================
    def split(self):
        """执行分裂操作，修正方向计算，使尾部变头。"""
        if not self.split_available or len(self.body) < SPLIT_MIN_LENGTH:
            return None, None

        print("-" * 10 + " 开始分裂 " + "-" * 10)
        print(f"分裂前蛇身: {list(self.body)}")
        print(f"分裂前方向: D={self.direction}, NewD={self.new_direction}, LastMoveD={self.last_move_direction}")

        split_index = len(self.body) // 2
        corpse_segments = deque(list(self.body)[split_index:]) # 头部部分成为尸体
        # print("测试它是个啥！！！：：："+{corpse_segments})

        # 1. 获取尾部段列表 (成为新蛇的部分)
        tail_part_list = list(self.body)[:split_index]

        if not tail_part_list: # 安全检查
            print("错误：分裂后尾部段为空！")
            return None, None
        print(f"获取到的尾部段 (原始顺序，尾->头): {tail_part_list}")

        # 2. *** 关键：反转列表，使原尾巴成为新头 ***
        tail_part_list.reverse()
        print(f"反转后的新蛇身体段 (新尾->新头): {tail_part_list}")

        # 3. 将反转后的列表赋给 self.body
        self.body = deque(tail_part_list)
        self.length = len(self.body) # 更新长度

        # --- 4. 重新计算新蛇的方向 ---
        new_direction = None
        if len(self.body) > 1:
            # 方向: 从倒数第二段(新蛇头的上一段)指向新的头
            new_head_pos = self.body[-1]       # 新头 (原尾巴)
            prev_segment_pos = self.body[-2]   # 新头的上一段 (原倒数第二段)
            print(f"新蛇(反转后) 头部: {new_head_pos}, 上一段: {prev_segment_pos}")
            new_direction = (new_head_pos[0] - prev_segment_pos[0],
                             new_head_pos[1] - prev_segment_pos[1])
            print(f"新计算的方向 (len>1): {new_direction}")
        elif len(self.body) == 1:
            # 单节蛇，方向是分裂前朝向尾巴的方向，即分裂前移动方向的反方向
            if hasattr(self, 'last_move_direction') and isinstance(self.last_move_direction, tuple) and len(self.last_move_direction) == 2:
                # 检查 last_move_direction 是否为 (0,0)，虽然不太可能
                if self.last_move_direction != (0,0):
                    new_direction = (-self.last_move_direction[0], -self.last_move_direction[1])
                    print(f"新计算的方向 (len=1, 反向): {new_direction} (基于 last_move_direction: {self.last_move_direction})")
                else:
                    print("警告：分裂前的 last_move_direction 为 (0,0)，无法取反，随机选择。")
                    new_direction = random.choice([d for d in [UP, DOWN, LEFT, RIGHT]]) # 随机选一个
            else:
                 print("警告：计算单节蛇方向时 last_move_direction 无效，随机选择。")
                 new_direction = random.choice([UP, DOWN, LEFT, RIGHT])

        # 最终检查方向有效性 (防止计算出零向量等问题)
        if new_direction is None or new_direction == (0,0):
            print(f"警告：最终方向计算无效({new_direction})，使用分裂前的最后移动方向作为备用。")
            new_direction = self.last_move_direction
            if new_direction == (0,0): # 如果连分裂前的方向也是(0,0)
                 print("警告：分裂前方向也为(0,0)，最终随机选择。")
                 new_direction = random.choice([UP, DOWN, LEFT, RIGHT])

        # --- 5. 更新方向状态 ---
        self.direction = new_direction
        self.new_direction = new_direction
        self.last_move_direction = new_direction # 立即更新
        self.update_head_image() # 根据新方向更新头图像

        # --- 创建尸体对象 ---
        corpse = Corpse(self.game, corpse_segments)

        # --- 播放效果 ---
        self.game.play_sound('split')
        if corpse.segments:
            self.game.add_particles(corpse.segments[0], 10, RED)

        print(f"分裂最终确定的方向: D={self.direction}, NewD={self.new_direction}, LastMoveD={self.last_move_direction}")
        print("-" * 10 + " 分裂结束 (已应用反转) " + "-" * 10)
        return corpse, True
    # ===============================================
    # ==========  修正后的 split 方法结束 ==========
    # ===============================================


# --- 尸体 类 ---
class Corpse:
    def __init__(self, game, segments):
        self.game = game; self.segments = segments; self.grid_size = GRID_SIZE
        self.image = load_image('corpse.png', size=self.grid_size)
        if not self.image: print("错误：未能加载 corpse.png"); self.image = pygame.Surface((self.grid_size, self.grid_size)); self.image.fill(GREY)
        self.creation_time = time.time(); self.lifespan = CORPSE_LIFESPAN_SECONDS
        self.flicker_start_time = self.creation_time + CORPSE_FLICKER_START_OFFSET
        self.flicker_end_time = self.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS
        self.fade_start_time = self.flicker_end_time; self.fade_end_time = self.fade_start_time + CORPSE_FADE_DURATION_SECONDS
        self.visible = True; self.is_fading = False; self.flicker_on = True; self.last_flicker_toggle = 0; self.flicker_interval = 150
    def update(self):
        current_time = time.time();
        if current_time > self.fade_end_time: return False
        self.is_fading = current_time > self.fade_start_time
        if self.flicker_start_time <= current_time < self.flicker_end_time:
            now_ms = pygame.time.get_ticks()
            if now_ms - self.last_flicker_toggle > self.flicker_interval: self.flicker_on = not self.flicker_on; self.last_flicker_toggle = now_ms
            self.visible = self.flicker_on
        elif self.is_fading: self.visible = True
        else: self.visible = True
        return True
    def draw(self, surface, camera_offset=(0, 0)):
        if not self.visible: return
        offset_x, offset_y = 0, 0; alpha = 255
        if self.is_fading:
             fade_duration = max(1, CORPSE_FADE_DURATION_SECONDS) # 防除零
             fade_progress = (time.time() - self.fade_start_time) / fade_duration; alpha = max(0, 255 * (1 - fade_progress))
        img_to_draw = self.image
        if alpha < 254:
            try: img_to_draw = self.image.copy(); img_to_draw.set_alpha(int(alpha))
            except Exception: img_to_draw = self.image
        for seg_x, seg_y in self.segments:
            pixel_x = seg_x * self.grid_size + offset_x; pixel_y = seg_y * self.grid_size + offset_y
            if img_to_draw: surface.blit(img_to_draw, (pixel_x, pixel_y))
            else: pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size), 1)
    def get_end_points(self):
        if not self.segments: return None, None
        try: return self.segments[0], self.segments[-1]
        except IndexError: return None, None

# --- 果实 基类 ---
class Fruit:
    def __init__(self, game, position, fruit_type, image_name, lifespan=None):
        self.game = game; self.position = position; self.type = fruit_type; self.grid_size = GRID_SIZE
        self.image = load_image(image_name, size=self.grid_size)
        if not self.image:
             print(f"错误：未能加载 {image_name}"); self.image = pygame.Surface((self.grid_size, self.grid_size))
             if self.type == 'healthy': self.image.fill(GREEN)
             elif self.type == 'bomb': self.image.fill(RED)
             elif self.type == 'super_growth': self.image.fill(PURPLE) # <--- 添加新类型判断
             else: self.image.fill(WHITE)
        self.lifespan = lifespan; self.creation_time = time.time(); self.is_special = fruit_type != 'normal'
    def update(self):
        if self.lifespan is not None and time.time() - self.creation_time > self.lifespan: return False
        return True
    def draw(self, surface, camera_offset=(0, 0)):
        offset_x, offset_y = 0, 0; pixel_x = self.position[0] * self.grid_size + offset_x; pixel_y = self.position[1] * self.grid_size + offset_y
        if self.image: surface.blit(self.image, (pixel_x, pixel_y))

# --- 鬼魂 基类 ---
# === ADDED/MODIFIED SECTION START: Ghost Class with A* and Debug Prints ===
try:
    from pathfinding.core.grid import Grid
    from pathfinding.finder.a_star import AStarFinder
    from pathfinding.core.diagonal_movement import DiagonalMovement
    pathfinding_available = True
except ImportError:
    print("警告：未找到 'pathfinding' 库。鬼魂将使用简单的直线移动逻辑。")
    print("请运行 'pip install pathfinding' 来安装。")
    pathfinding_available = False

class Ghost:
    def __init__(self, game, start_pos, image_name, speed_factor):
        self.game = game
        self.grid_pos = start_pos   # 当前格子坐标 (x, y)
        self.pixel_pos = [start_pos[0] * GRID_SIZE, start_pos[1] * GRID_SIZE] # 精确像素坐标 [x, y]
        self.grid_size = GRID_SIZE
        self.image = load_image(image_name, size=self.grid_size)
        if not self.image: # 图像加载失败处理
             print(f"错误：未能加载 {image_name}"); self.image = pygame.Surface((self.grid_size, self.grid_size))
             if 'blinky' in image_name: self.image.fill(RED)
             elif 'pinky' in image_name: self.image.fill((255,182,193))
             else: self.image.fill(BLUE)
        self.speed_factor = speed_factor       # 速度系数
        self.target_grid_pos = start_pos     # 目标格子坐标
        self.last_path_time = 0.0          # 上次计算路径的时间 (秒)
        self.current_path = []             # 当前计算出的路径 [(x,y), ...]
        self.move_direction = (0, 0)         # 当前帧要移动的方向 (dx, dy)
        self.type = image_name.split('_')[1].split('.')[0].capitalize() # 从文件名获取类型 (Blinky/Pinky)
        print(f"[{self.type}] 初始化于 {self.grid_pos}")

    def get_speed(self):
        """获取鬼魂当前的移动速度（像素/秒）。"""
        return BASE_SNAKE_SPEED_PPS * self.speed_factor * self.grid_size

    def update_target(self, snake_body):
        """更新鬼魂的目标格子。由子类重写。"""
        pass # 子类实现具体逻辑

    def find_path(self):
        """使用 A* 算法计算到目标点的路径。"""
        # 基础检查
        if not pathfinding_available or not self.target_grid_pos or self.grid_pos == self.target_grid_pos:
            # print(f"[{self.type}] 跳过寻路：Lib={pathfinding_available}, Target={self.target_grid_pos}, Pos={self.grid_pos}")
            if self.current_path: # 如果之前有路径，清空它
                 print(f"[{self.type}] 清空旧路径，因为已到达目标或目标无效。")
                 self.current_path = []
            return

        # print(f"[{self.type}] 开始寻路: 从 {self.grid_pos} 到 {self.target_grid_pos}")
        # 1. 创建障碍矩阵 (0=可走, 1=障碍)
        matrix = [[0 for _ in range(CANVAS_GRID_WIDTH)] for _ in range(CANVAS_GRID_HEIGHT)]
        current_target = self.target_grid_pos # 获取当前目标


        # 标记蛇身和尸体为障碍，跳过自身和目标点
        obstacles = set() # 使用集合存储障碍位置
        if self.game.snake and self.game.snake.body: obstacles.update(self.game.snake.body)
        for corpse in self.game.corpses: obstacles.update(corpse.segments)

        # --- >>> 新增：将果实位置也加入障碍物 <<< ---
        # 但要排除目标点是果实的情况吗？理论上鬼魂目标不是果实，可以不排除。
        # 排除炸弹果实？还是所有果实都避开？目前设定是所有果实都避开。
        for fruit in self.game.fruits:
             obstacles.add(fruit.position)
        # --- >>> 新增结束 <<< ---

        for obs_x, obs_y in obstacles:
            if (obs_x, obs_y) == self.grid_pos: continue # 跳过自身
            if (obs_x, obs_y) == current_target: continue # 跳过目标
            if 0 <= obs_y < CANVAS_GRID_HEIGHT and 0 <= obs_x < CANVAS_GRID_WIDTH:
                matrix[obs_y][obs_x] = 1 # 标记为障碍

        # 2. 创建 Grid 对象 (转换 matrix: 1=可走, 0=障碍)
        try:
             matrix_for_grid = [[1 if matrix[y][x] == 0 else 0 for x in range(CANVAS_GRID_WIDTH)] for y in range(CANVAS_GRID_HEIGHT)]
             grid = Grid(matrix=matrix_for_grid)

             # 检查起点和终点坐标
             start_x, start_y = self.grid_pos
             target_x = max(0, min(CANVAS_GRID_WIDTH - 1, current_target[0]))
             target_y = max(0, min(CANVAS_GRID_HEIGHT - 1, current_target[1]))

             # 确保坐标在 Grid 内部 (node 方法会检查，但提前检查更清晰)
             if not grid.inside(start_x, start_y):
                  print(f"[{self.type}] 错误: 起点 {start_x},{start_y} 超出 Grid 边界!")
                  self.current_path = []; return
             if not grid.inside(target_x, target_y):
                  print(f"[{self.type}] 错误: 目标 {target_x},{target_y} 超出 Grid 边界!")
                  self.current_path = []; return

             start_node = grid.node(start_x, start_y)
             end_node = grid.node(target_x, target_y)

             # 检查起点是否可行走
             if not start_node.walkable:
                 print(f"[{self.type}] 警告：起点 {start_node.x},{start_node.y} 在障碍物上 (matrix_for_grid={matrix_for_grid[start_y][start_x]})，寻路失败。")
                 self.current_path = []
                 return

             # 检查目标点是否可行走（理论上不会是障碍了）
             # if not end_node.walkable:
             #     print(f"[{self.type}] 提示：目标点 {end_node.x},{end_node.y} 在障碍物上。")

             # 3. 寻路
             finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
             path, runs = finder.find_path(start_node, end_node, grid)

             # 4. 处理结果
             if path and len(path) > 1: # 需要至少包含起点和下一步
                 self.current_path = [(node.x, node.y) for node in path[1:]] # 去掉起点
                #  print(f"[{self.type}] 路径找到 ({len(self.current_path)}步): {self.current_path[:5]}...")
             else:
                 fail_reason = "路径为空" if not path else "路径长度不足"
                 print(f"[{self.type}] 未找到路径 ({fail_reason}) 从 {start_node.x},{start_node.y} 到 {end_node.x},{end_node.y}")
                 self.current_path = []

        except Exception as e: # 捕获所有可能的异常
             print(f"[{self.type}] A* 寻路时发生严重错误: {e}")
             import traceback
             traceback.print_exc() # 打印详细的错误追踪信息
             self.current_path = []
    # --- A* 寻路方法结束 ---


        # 在 Ghost 类中
        # 在 Ghost 类中
    def update(self, dt, snake_body):
        """更新鬼魂状态（目标、移动）。改进格子更新和路径消耗逻辑。"""
        current_time = time.time()
        path_recalculated = False

        # --- 1. 定期更新目标和计算 A* 路径 (逻辑不变) ---
        if current_time - self.last_path_time > GHOST_TARGET_UPDATE_INTERVAL_SECONDS:
            self.last_path_time = current_time
            if snake_body: self.update_target(snake_body)
            if pathfinding_available:
                self.find_path()
                path_recalculated = True

        # --- 2. 每一帧根据当前路径确定移动方向 (逻辑不变) ---
        current_move_direction = (0,0)
        if pathfinding_available:
            if self.current_path:
                next_step = self.current_path[0]
                calculated_direction = (next_step[0] - self.grid_pos[0], next_step[1] - self.grid_pos[1])
                # print(f"[{self.type}] Update: Pos={self.grid_pos}, Path Next={next_step}, CalculatedDir={calculated_direction}")
                if calculated_direction in [(0,1), (0,-1), (1,0), (-1,0)]: current_move_direction = calculated_direction
                elif calculated_direction == (0,0): # 路径下一步是当前位置
                     print(f"[{self.type}] 警告: 路径下一步等于当前位置 {self.grid_pos}，消耗并尝试再下一步。")
                     self.current_path.pop(0)
                     if self.current_path:
                          next_step = self.current_path[0]
                          calculated_direction = (next_step[0] - self.grid_pos[0], next_step[1] - self.grid_pos[1])
                          if calculated_direction in [(0,1), (0,-1), (1,0), (-1,0)]: current_move_direction = calculated_direction; print(f"[{self.type}] 使用路径再下一步，方向: {current_move_direction}")
                          else: print(f"[{self.type}] 警告: 再下一步方向仍无效 {calculated_direction}，停止。")
                     else: print(f"[{self.type}] 路径在消耗无效步后为空，停止。")
                else: print(f"[{self.type}] 警告: 根据路径计算出无效方向 {calculated_direction}，停止。")
            # else: (无路径时保持 (0,0))
        else: # A* 不可用时的简单逻辑
             if self.target_grid_pos and self.target_grid_pos != self.grid_pos: dx = self.target_grid_pos[0] - self.grid_pos[0]; dy = self.target_grid_pos[1] - self.grid_pos[1]; current_move_direction = (1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) else (0, 1 if dy > 0 else -1) if abs(dy) > abs(dx) else (1 if dx > 0 else -1, 0) if dx != 0 else (0, 1 if dy > 0 else -1) if dy != 0 else (0,0)
             else: current_move_direction = (0, 0)
        self.move_direction = current_move_direction


        # --- 3. 移动鬼魂（像素级移动）---
        if self.move_direction != (0, 0):
            speed_pixels_per_sec = self.get_speed()
            move_dist = speed_pixels_per_sec * dt

            # --- 计算目标格子 (下一个格子) 的精确像素坐标 (左上角) ---
            next_grid_x = self.grid_pos[0] + self.move_direction[0]
            next_grid_y = self.grid_pos[1] + self.move_direction[1]
            target_pixel_pos = [next_grid_x * self.grid_size, next_grid_y * self.grid_size]

            # 计算当前像素位置到目标格子左上角的向量
            delta_px = target_pixel_pos[0] - self.pixel_pos[0]
            delta_py = target_pixel_pos[1] - self.pixel_pos[1]
            dist_to_target_pixel = (delta_px**2 + delta_py**2)**0.5

            # --- 移动逻辑：直接朝目标格子的像素坐标移动 ---
            if dist_to_target_pixel > 1: # 移动阈值
                norm_dx = delta_px / dist_to_target_pixel
                norm_dy = delta_py / dist_to_target_pixel
                actual_move = min(move_dist, dist_to_target_pixel) # 最多移动到目标格子的像素位置
                self.pixel_pos[0] += norm_dx * actual_move
                self.pixel_pos[1] += norm_dy * actual_move
                # print(f"[{self.type}] 像素移动: 方向={self.move_direction}, 距离={actual_move:.3f}, 新Pix={self.pixel_pos[0]:.2f},{self.pixel_pos[1]:.2f}, 目标Pix={target_pixel_pos[0]:.1f},{target_pixel_pos[1]:.1f}")
            else:
                # *** 到达或非常接近目标格子的像素位置 ***
                # print(f"[{self.type}] 已到达目标格子像素位置附近 {next_grid_x},{next_grid_y}")
                # --- 强制更新格子位置并消耗路径 ---
                new_pos = (next_grid_x, next_grid_y)
                if new_pos != self.grid_pos: # 确保格子位置确实改变了
                    old_grid_pos = self.grid_pos
                    self.grid_pos = new_pos # 更新格子位置
                    # print(f"[{self.type}] 格子位置更新 (到达目标像素): 从 {old_grid_pos} 到 {self.grid_pos}")

                    # 强制像素位置对齐，避免累积误差
                    self.pixel_pos = [self.grid_pos[0] * self.grid_size, self.grid_pos[1] * self.grid_size]
                    # print(f"[{self.type}] 强制像素对齐到: {self.pixel_pos}")

                    # 消耗路径
                    if pathfinding_available and self.current_path:
                        if self.grid_pos == self.current_path[0]:
                            # print(f"[{self.type}] 到达路径点 {self.current_path[0]}，消耗路径。")
                            self.current_path.pop(0)
                            if not self.current_path:
                                print(f"[{self.type}] A* 路径已完成。")
                                self.move_direction = (0,0) # 路径走完，停止
                        else: # 到达了格子，但不是路径期望的格子
                             print(f"[{self.type}] 警告：到达格子 {self.grid_pos}，但路径期望 {self.current_path[0]}！路径失效。")
                             self.current_path = []
                             self.move_direction = (0,0)
                else:
                     # 如果计算出的新格子和当前格子一样（例如，移动方向是(0,0)但仍尝试移动），则停止
                     self.move_direction = (0,0)


        # --- 4. 根据像素位置更新格子位置 (这部分现在只用于显示/边界检查，主要逻辑在上面处理) ---
        # (可以考虑移除或简化这部分，因为主要更新逻辑移到了像素移动部分)
        # new_grid_x_check = int(self.pixel_pos[0] // self.grid_size)
        # new_grid_y_check = int(self.pixel_pos[1] // self.grid_size)
        # ... (边界检查) ...


        # 触发警告音效
        if snake_body:
             head_pos = snake_body[-1]; dist_sq = (head_pos[0] - self.grid_pos[0])**2 + (head_pos[1] - self.grid_pos[1])**2
             if dist_sq <= GHOST_WARNING_DISTANCE_GRIDS**2: self.game.try_play_sound('ghost_warning', unique=True)

    def draw(self, surface, camera_offset=(0, 0)):
        """绘制鬼魂。"""
        offset_x, offset_y = 0, 0
        draw_x = self.pixel_pos[0] + offset_x
        draw_y = self.pixel_pos[1] + offset_y
        if self.image:
            surface.blit(self.image, (draw_x, draw_y))

# === ADDED/MODIFIED SECTION END: Ghost Class with A* and Debug Prints ===

# --- Blinky, Pinky, Particle 类保持不变 (确保 Pinky.update_target 中 head_pos 定义存在) ---
# ... (省略 Blinky, Pinky, Particle 的代码) ...
# --- 辅助函数：检查格子是否被占用 ---
def is_occupied(grid_pos, game):
    """检查指定格子位置是否被蛇或尸体占用。"""
    if not game: return False # 游戏对象不存在
    # 检查蛇
    if game.snake and game.snake.body and grid_pos in game.snake.body:
        return True
    # 检查尸体
    for corpse in game.corpses:
        if grid_pos in corpse.segments:
            return True
    return False

# --- Blinky (红色鬼魂) ---
class Blinky(Ghost):
    def __init__(self, game):
        # --- 修改：添加出生点检查 ---
        spawn_ok = False
        start_pos = (0,0)
        attempts = 0
        max_attempts = 100
        while not spawn_ok and attempts < max_attempts:
            attempts += 1
            start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
            # 使用辅助函数检查是否被占用
            if not is_occupied(start_pos, game):
                 spawn_ok = True
        if not spawn_ok: # Fallback
            start_pos = (0,0) # 或者选择一个已知安全的点
            print("警告：未能为 Blinky 找到清晰的生成点，生成在 (0,0)")
        # --- 修改结束 ---
        super().__init__(game, start_pos, 'ghost_blinky.png', GHOST_BASE_SPEED_FACTOR)
        # self.type = "Blinky" # type 会在父类__init__中根据文件名设置

    def update_target(self, snake_body):
        """Blinky 的目标是蛇身的中点。"""
        if not snake_body: return;
        mid_index = len(snake_body) // 2
        if 0 <= mid_index < len(snake_body): self.target_grid_pos = snake_body[mid_index]
        elif snake_body: self.target_grid_pos = snake_body[-1]

# --- Pinky (粉色鬼魂) ---
class Pinky(Ghost):
    def __init__(self, game):
        # --- 修改：使用辅助函数简化检查 ---
        spawn_ok = False
        start_pos = (0,0)
        attempts = 0
        max_attempts = 100
        while not spawn_ok and attempts < max_attempts:
            attempts += 1
            start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
            # 使用辅助函数检查
            if not is_occupied(start_pos, game):
                 spawn_ok = True
        if not spawn_ok: # Fallback
            start_pos = (0,0)
            print("警告：未能为 Pinky 找到清晰的生成点，生成在 (0,0)")
        # --- 修改结束 ---
        super().__init__(game, start_pos, 'ghost_pinky.png', GHOST_BASE_SPEED_FACTOR)
        # self.type = "Pinky"

    def update_target(self, snake_body):
        """Pinky 的目标是蛇头前方一定格子数的位置。"""
        if not snake_body: return; head_pos = snake_body[-1]
        # --- >>> 添加回这一行 <<< ---
        head_pos = snake_body[-1] # 获取蛇头位置
        # --- >>> 添加结束 <<< ---

        # 获取蛇的方向
        if self.game.snake: head_dir = self.game.snake.direction
        else: head_dir = RIGHT
        # 计算目标位置
        target_x = head_pos[0] + head_dir[0] * PINKY_PREDICTION_DISTANCE;
        target_y = head_pos[1] + head_dir[1] * PINKY_PREDICTION_DISTANCE
        # 限制目标在画布内
        target_x = max(0, min(CANVAS_GRID_WIDTH - 1, target_x));
        target_y = max(0, min(CANVAS_GRID_HEIGHT - 1, target_y));
        # 设置目标格子坐标
        self.target_grid_pos = (target_x, target_y)

# --- 粒子 类 ---
class Particle:
    def __init__(self, game, pos_px, color, size_range=(1, 3), vel_range=(-1.5, 1.5), lifespan_ms=400):
        self.game = game; self.x, self.y = pos_px; self.color = color; self.size = random.uniform(size_range[0], size_range[1])
        self.vx = random.uniform(vel_range[0], vel_range[1]) * 60; self.vy = random.uniform(vel_range[0], vel_range[1]) * 60
        self.creation_time = pygame.time.get_ticks(); self.lifespan = lifespan_ms; self.alpha = 255
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt; self.vy += 0.05 * 60 * dt
        elapsed = pygame.time.get_ticks() - self.creation_time
        if elapsed > self.lifespan: return False
        self.alpha = max(0, 255 * (1 - (elapsed / self.lifespan)))
        return True
    def draw(self, surface, camera_offset=(0,0)):
        if self.alpha <= 0 or self.size < 1: return
        offset_x, offset_y = 0, 0; draw_x = int(self.x + offset_x); draw_y = int(self.y + offset_y); radius = max(1, int(self.size))
        try: particle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA); pygame.draw.circle(particle_surf, (*self.color, int(self.alpha)), (radius, radius), radius); surface.blit(particle_surf, (draw_x - radius, draw_y - radius))
        except Exception: pass

# --- END OF FILE sprites.py ---

