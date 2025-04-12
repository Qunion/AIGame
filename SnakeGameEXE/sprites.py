import pygame
import random
import time
from settings import * # 导入更新后的 GRID_SIZE 等设置
from collections import deque
# 可选：如果使用路径规划库，取消注释
# from pathfinding.core.grid import Grid
# from pathfinding.finder.a_star import AStarFinder

# --- 蛇 类 ---
class Snake:
    def __init__(self, game):
        self.game = game # 游戏对象的引用
        self.grid_size = GRID_SIZE # 使用更新后的格子大小
        self.color = DARK_YELLOW # 蛇的基础颜色
        self.body = deque() # 使用双端队列存储蛇身段，方便头尾操作
        self.direction = random.choice([UP, DOWN, LEFT, RIGHT]) # 初始随机方向
        self.new_direction = self.direction # 缓冲下一个方向，防止180度立即转向
        self.length = INITIAL_SNAKE_LENGTH # 初始长度
        self.is_accelerating = False # 是否正在加速
        self.alive = True # 蛇是否存活
        self.split_available = True # 当前是否可以执行分裂操作

        # 加载图像 - 依赖 load_image 默认使用新的 GRID_SIZE
        self.head_image_orig = load_image('snake_head.png') # 加载原始蛇头图像
        self.body_image = load_image('snake_body.png')      # 加载蛇身图像
        # 检查图像是否加载成功
        if not self.head_image_orig:
            print("错误：未能加载 snake_head.png")
            # 可以创建一个占位符
            self.head_image_orig = pygame.Surface((self.grid_size, self.grid_size))
            self.head_image_orig.fill(self.color)
        if not self.body_image:
            print("错误：未能加载 snake_body.png")
            self.body_image = pygame.Surface((self.grid_size, self.grid_size))
            self.body_image.fill(GREY)

        self.head_image = self.head_image_orig # 当前使用的蛇头图像（会根据方向旋转）

        # 初始化蛇的起始位置（画布中心）
        start_x = CANVAS_GRID_WIDTH // 2
        start_y = CANVAS_GRID_HEIGHT // 2
        for i in range(self.length):
            # 根据初始方向，在蛇头后面放置初始段
            segment_x = start_x - self.direction[0] * i
            segment_y = start_y - self.direction[1] * i
            # 确保初始段在边界内（对于非常小的网格可能需要）
            segment_x = max(0, min(CANVAS_GRID_WIDTH - 1, segment_x))
            segment_y = max(0, min(CANVAS_GRID_HEIGHT - 1, segment_y))
            self.body.appendleft((segment_x, segment_y)) # 添加到队列前端（即蛇尾）

        # *确保此方法在类中定义后再调用*
        self.update_head_image() # 根据初始方向旋转蛇头

    def get_head_position(self):
        """获取蛇头的格子坐标。"""
        if not self.body: # 防止在极少情况下body为空时出错
            return (0, 0) # 或者返回一个合理的默认值或抛出异常
        return self.body[-1] # 蛇头是队列的最后一个元素

    def update_head_image(self):
        """根据当前方向旋转蛇头图像。"""
        angle = 0
        if self.direction == UP:
            angle = 0
        elif self.direction == DOWN:
            angle = 180
        elif self.direction == LEFT:
            angle = 90
        elif self.direction == RIGHT:
            angle = -90
        # 确保 head_image_orig 存在且有效
        if hasattr(self, 'head_image_orig') and self.head_image_orig:
            try:
                self.head_image = pygame.transform.rotate(self.head_image_orig, angle)
            except Exception as e:
                print(f"旋转蛇头图像时出错: {e}")
                # 如果旋转失败，至少保证 self.head_image 有一个值
                if not hasattr(self, 'head_image'):
                     self.head_image = self.head_image_orig # 尝试使用原始图像
        else:
            print("警告：蛇头原始图像不存在，无法旋转。")
            # 确保 self.head_image 存在，即使是个占位符
            if not hasattr(self, 'head_image') or not self.head_image:
                 self.head_image = pygame.Surface((self.grid_size, self.grid_size))
                 self.head_image.fill(self.color)


    def grow(self, amount=1):
        """增加蛇的长度。"""
        self.length += amount

    def change_direction(self, new_dir):
        """
        尝试改变蛇的移动方向。
        缓冲方向改变，防止单步内发生180度转弯。
        只有当新方向不是当前方向的反方向时才接受。
        """
        current_move_dir = self.direction
        # 确保新方向不是当前移动方向的反方向
        if (new_dir[0] != -current_move_dir[0] or \
            new_dir[1] != -current_move_dir[1]):
           self.new_direction = new_dir


    def update(self):
        """更新蛇的状态（移动）。"""
        # 检查是否有缓冲的新方向，并且这个新方向不是当前实际方向的反方向
        if self.new_direction[0] != -self.direction[0] or self.new_direction[1] != -self.direction[1]:
             self.direction = self.new_direction
             self.update_head_image() # 方向改变时，更新蛇头图像

        # 获取当前蛇头位置
        head_x, head_y = self.get_head_position()
        # 计算移动向量
        move_x, move_y = self.direction
        # 计算新蛇头应该在的位置
        new_head = (head_x + move_x, head_y + move_y)

        # 在正式添加新蛇头段之前检查碰撞
        self.check_collisions(new_head) # 这个方法可能会将 self.alive 设为 False

        # 如果蛇仍然存活
        if self.alive:
            self.body.append(new_head) # 将新蛇头添加到身体队列的末尾
            # 在添加新蛇头后检查长度
            if len(self.body) > self.length:
                self.body.popleft() # 如果身体超过目标长度，移除蛇尾（队列的第一个元素）
        else:
            # 可选：如果是因为碰撞而死亡，是否不添加导致碰撞的那一节？
            # 当前逻辑是添加了，然后游戏结束画面出现。通常这样没问题。
            pass

        # 更新分裂按钮的可用状态
        self.split_available = self.length >= SPLIT_MIN_LENGTH


    def check_collisions(self, new_head):
        """检查预期的蛇头位置是否会导致碰撞。"""
        head_x, head_y = new_head

        # 1. 画布边界碰撞 (现在是 0 到 CANVAS_GRID_WIDTH/HEIGHT - 1)
        if not (0 <= head_x < CANVAS_GRID_WIDTH and 0 <= head_y < CANVAS_GRID_HEIGHT):
            self.alive = False
            self.game.trigger_game_over("撞墙") # 中文原因
            return

        # 2. 自身碰撞
        # 检查身体段，需要排除即将被移除的尾巴（如果蛇正在增长，则不排除）
        check_body = list(self.body)
        # 重要：只有当蛇身当前长度达到或超过目标长度时，尾巴才会被移除。
        if len(self.body) >= self.length:
             check_body = check_body[1:] # 排除当前的尾巴，因为它将弹出

        if new_head in check_body:
             self.alive = False
             self.game.trigger_game_over("撞到自己") # 中文原因
             return

        # 3. 鬼魂碰撞（在主游戏循环中检查）
        # 4. 炸弹果实碰撞（在主游戏循环中检查）
        # 5. 尸体融合碰撞（在主游戏循环中检查）


    def draw(self, surface, camera_offset=(0, 0)): # 相机偏移现在总是 (0,0)
        # offset_x, offset_y = camera_offset # 不再需要
        offset_x, offset_y = 0, 0

        num_segments = len(self.body)
        for i, segment in enumerate(self.body):
            seg_x, seg_y = segment
            # 直接计算像素位置
            pixel_x = seg_x * self.grid_size
            pixel_y = seg_y * self.grid_size

            # 因为画布适合屏幕，不再需要检查屏幕边界
            if i == num_segments - 1: # 蛇头段
                # 确保 head_image 存在
                if hasattr(self, 'head_image') and self.head_image:
                     surface.blit(self.head_image, (pixel_x, pixel_y))
                else: # 如果图像缺失，画一个方块作为备用
                     pygame.draw.rect(surface, self.color, (pixel_x, pixel_y, self.grid_size, self.grid_size))
            else: # 蛇身段
                alpha = max(0, 255 * (1 - (num_segments - 1 - i) * SNAKE_ALPHA_DECREASE_PER_SEGMENT))
                # 优化：仅当 alpha 不是 255 时才创建 body_copy
                if alpha < 254: # 允许微小的浮点误差
                    try:
                        body_copy = self.body_image.copy()
                        body_copy.set_alpha(int(alpha))
                        surface.blit(body_copy, (pixel_x, pixel_y))
                    except Exception as e:
                         print(f"设置蛇身透明度时出错: {e}")
                         # 绘制不透明的身体作为后备
                         if self.body_image:
                              surface.blit(self.body_image, (pixel_x, pixel_y))
                         else: # 如果身体图像也缺失，画灰色方块
                              pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size))

                else: # 完全不透明
                    if self.body_image:
                         surface.blit(self.body_image, (pixel_x, pixel_y))
                    else:
                         pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size))


        # --- 绘制速度线 (如果正在加速) ---
        if self.is_accelerating and self.alive:
            head_x, head_y = self.get_head_position()
            # 蛇头格子中心
            center_x = head_x * self.grid_size + self.grid_size // 2
            center_y = head_y * self.grid_size + self.grid_size // 2
            num_lines = 5
            # 调整线条长度/偏移量以适应较小的格子大小？让它们相对短一些。
            line_length = self.grid_size * 1.2 # 稍短的相对长度
            line_speed_offset = self.grid_size * 0.6 # 更靠近起点

            # 计算反方向和垂直方向用于散开
            back_dir_x, back_dir_y = -self.direction[0], -self.direction[1]
            perp_dir_x, perp_dir_y = -back_dir_y, back_dir_x

            for i in range(num_lines):
                spread_factor = (i - num_lines // 2) * 0.3 # 调整散开程度
                start_x = center_x + back_dir_x * line_speed_offset + perp_dir_x * spread_factor * self.grid_size
                start_y = center_y + back_dir_y * line_speed_offset + perp_dir_y * spread_factor * self.grid_size
                end_x = start_x + back_dir_x * line_length
                end_y = start_y + back_dir_y * line_length

                # 绘制线条 (不再需要屏幕边界检查)
                pygame.draw.line(surface, WHITE, (start_x, start_y), (end_x, end_y), 1) # 线条可以细一点


    def split(self):
        """执行分裂操作。"""
        if not self.split_available:
            return None, None # 如果长度不够，不能分裂

        # 计算分裂点索引
        split_index = len(self.body) // 2 # 整除，如果奇数，蛇头部分多一格

        # 分割身体队列
        corpse_segments = deque(list(self.body)[split_index:]) # 蛇头连接的部分变成尸体
        new_snake_body = deque(list(self.body)[:split_index])   # 蛇尾连接的部分变成新的蛇

        # 如果分裂后新蛇没有身体（例如长度为2时分裂），则不允许
        if not new_snake_body:
            print("警告：分裂后新蛇身体为空，分裂取消。")
            return None, None

        # 创建尸体对象，传递尸体段
        corpse = Corpse(self.game, corpse_segments)

        # 修改当前蛇对象（它变成了原来的尾巴部分）
        self.body = new_snake_body
        self.length = len(self.body) # 更新长度

        # 确定“新”蛇（即当前对象）的新方向
        # 它应该朝着远离分裂点的方向移动（即朝向原始尾巴的方向）
        if len(self.body) > 1:
            # 方向是从倒数第二段指向最后一段（新的头）
            p_tail_x, p_tail_y = self.body[-2] # 倒数第二段
            tail_x, tail_y = self.body[-1]   # 新的头（尾部段的最后一个）
            new_dir_x = tail_x - p_tail_x
            new_dir_y = tail_y - p_tail_y
            # 处理快速转向可能导致的堆叠段（例如 (5,5) 然后 (5,6)）
            # 确保方向尽可能非零
            if new_dir_x == 0 and new_dir_y == 0:
                 # 后备方案：使用尸体第一段移动方向的反方向？
                 # 这比较复杂。暂时坚持原始逻辑，假设这里不会有堆叠段。
                 print("警告：分裂后计算新方向时遇到堆叠段，可能导致方向错误。")
                 # 尝试使用尸体相对于新蛇头的反方向
                 head_x, head_y = self.body[-1]
                 corpse_start_x, corpse_start_y = corpse.segments[0]
                 fallback_dir_x = head_x - corpse_start_x
                 fallback_dir_y = head_y - corpse_start_y
                 if fallback_dir_x != 0 or fallback_dir_y != 0:
                      self.direction = (fallback_dir_x, fallback_dir_y)
                 else: # 如果还是(0,0)，随机选一个
                      self.direction = random.choice([UP, DOWN, LEFT, RIGHT])

            else:
                 self.direction = (new_dir_x, new_dir_y)

        elif len(self.body) == 1:
            # 如果只剩一个段，需要一个方向。
            # 获取尸体第一段相对于这唯一蛇段（新头）的方向
            head_x, head_y = self.body[0]
            # 确保尸体段存在
            if corpse.segments:
                 corpse_start_x, corpse_start_y = corpse.segments[0]
                 # 朝远离尸体段的方向移动
                 self.direction = (head_x - corpse_start_x, head_y - corpse_start_y)
                 # 如果计算结果是(0,0)（例如紧挨着分裂），则需要一个默认方向
                 if self.direction == (0,0):
                      self.direction = random.choice([UP, DOWN, LEFT, RIGHT]) # 随机猜一个
            else:
                 # 如果尸体段意外为空，随机给个方向
                 self.direction = random.choice([UP, DOWN, LEFT, RIGHT])


        # 同步缓冲方向并更新蛇头图像
        self.new_direction = self.direction
        self.update_head_image()

        # 播放分裂音效和粒子效果
        self.game.play_sound('split')
        # 在分裂点（尸体的起始位置）添加粒子
        if corpse.segments:
            self.game.add_particles(corpse.segments[0], 10, RED) # 粒子数量可以调整

        return corpse, True # 返回创建的尸体对象和成功标志


# --- 尸体 类 ---
class Corpse:
    def __init__(self, game, segments):
        self.game = game
        self.segments = segments # 应该是从蛇传递过来的 deque
        self.grid_size = GRID_SIZE
        # 加载图像，使用默认的 GRID_SIZE
        self.image = load_image('corpse.png')
        if not self.image: # 添加图像加载失败的检查
             print("错误：未能加载 corpse.png")
             self.image = pygame.Surface((self.grid_size, self.grid_size))
             self.image.fill(GREY)

        self.creation_time = time.time() # 精确记录创建时的墙上时间
        self.lifespan = CORPSE_LIFESPAN_SECONDS # 总生命周期
        self.flicker_start_time = self.creation_time + CORPSE_FLICKER_START_OFFSET # 开始闪烁时间
        self.flicker_end_time = self.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS # 结束闪烁时间
        self.fade_start_time = self.flicker_end_time # 开始淡出时间
        self.fade_end_time = self.fade_start_time + CORPSE_FADE_DURATION_SECONDS # 结束淡出时间（即消失时间）
        self.visible = True # 当前是否可见（用于闪烁）
        self.is_fading = False # 是否处于淡出阶段
        self.flicker_on = True # 闪烁状态切换
        self.last_flicker_toggle = 0 # 上次闪烁切换的时刻 (pygame ticks)
        self.flicker_interval = 150 # 闪烁间隔（毫秒）

    def update(self):
        """更新尸体的状态（闪烁、淡出、消失）。"""
        current_time = time.time()
        # 如果超过了最终消失时间，返回 False 表示可以移除
        if current_time > self.fade_end_time:
            return False

        # 检查是否进入淡出阶段
        self.is_fading = current_time > self.fade_start_time

        # 处理闪烁逻辑
        if self.flicker_start_time <= current_time < self.flicker_end_time:
            now_ms = pygame.time.get_ticks()
            if now_ms - self.last_flicker_toggle > self.flicker_interval:
                self.flicker_on = not self.flicker_on
                self.last_flicker_toggle = now_ms
            self.visible = self.flicker_on
        elif self.is_fading:
            self.visible = True # 确保在淡出时是可见的，以便计算 alpha
        else:
            self.visible = True # 在闪烁/淡出之前是可见的

        return True # 尸体仍然活动

    def draw(self, surface, camera_offset=(0, 0)): # 相机偏移现在总是 (0,0)
        if not self.visible:
            return # 如果不可见（闪烁关闭时），不绘制

        # offset_x, offset_y = camera_offset # 不再需要
        offset_x, offset_y = 0, 0
        alpha = 255 # 默认完全不透明

        # 如果正在淡出，计算当前的 alpha 值
        if self.is_fading:
             fade_duration = CORPSE_FADE_DURATION_SECONDS
             if fade_duration <= 0: fade_duration = 1 # 防止除以零
             # 计算淡出进度 (0.0 to 1.0)
             fade_progress = (time.time() - self.fade_start_time) / fade_duration
             # alpha 从 255 线性减到 0
             alpha = max(0, 255 * (1 - fade_progress))

        # 优化：仅当 alpha 变化时才复制图像并设置 alpha
        img_to_draw = self.image # 默认使用原始图像
        if alpha < 254: # 允许微小的浮点误差
            try:
                img_to_draw = self.image.copy()
                img_to_draw.set_alpha(int(alpha))
            except Exception as e:
                 print(f"设置尸体透明度时出错: {e}")
                 # 如果出错，就用原始图像绘制
                 img_to_draw = self.image

        # 绘制所有尸体段
        for seg_x, seg_y in self.segments:
            pixel_x = seg_x * self.grid_size
            pixel_y = seg_y * self.grid_size
            # 不再需要屏幕边界检查
            if img_to_draw: # 确保图像存在
                 surface.blit(img_to_draw, (pixel_x, pixel_y))
            else: # 备用绘制
                 pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size), 1)


    def get_end_points(self):
        """返回尸体的两个端点的格子坐标。"""
        if not self.segments:
            return None, None
        return self.segments[0], self.segments[-1]


# --- 果实 基类 ---
class Fruit:
    def __init__(self, game, position, fruit_type, image_name, lifespan=None): # 传递图像文件名而不是表面
        self.game = game
        self.position = position # 格子坐标 (x, y)
        self.type = fruit_type # 'normal', 'healthy', 'bomb'
        self.grid_size = GRID_SIZE
        # 在这里加载图像，使用默认的 GRID_SIZE
        self.image = load_image(image_name)
        if not self.image: # 添加图像加载失败的检查
             print(f"错误：未能加载 {image_name}")
             self.image = pygame.Surface((self.grid_size, self.grid_size))
             # 根据类型给占位符填色
             if self.type == 'healthy': self.image.fill(GREEN)
             elif self.type == 'bomb': self.image.fill(RED)
             else: self.image.fill(WHITE)

        self.lifespan = lifespan # 生命周期（秒），None 表示无限
        self.creation_time = time.time() # 创建时的墙上时间
        self.is_special = fruit_type != 'normal' # 是否是特殊果实

    def update(self):
        """更新果实状态（检查生命周期）。"""
        if self.lifespan is not None:
            # 如果已过生命周期，返回 False 表示可以移除
            if time.time() - self.creation_time > self.lifespan:
                return False
        return True # 果实仍然活动

    def draw(self, surface, camera_offset=(0, 0)): # 相机偏移现在总是 (0,0)
        # offset_x, offset_y = camera_offset # 不再需要
        offset_x, offset_y = 0, 0
        # 计算像素坐标
        pixel_x = self.position[0] * self.grid_size
        pixel_y = self.position[1] * self.grid_size
        # 不再需要屏幕边界检查
        if self.image: # 确保图像存在
             surface.blit(self.image, (pixel_x, pixel_y))


# --- 鬼魂 基类 ---
class Ghost:
    def __init__(self, game, start_pos, image_name, speed_factor): # 传递图像文件名
        self.game = game
        self.grid_pos = start_pos # 当前所在的格子坐标 (x, y)
        # 像素位置，用于平滑移动
        self.pixel_pos = [start_pos[0] * GRID_SIZE, start_pos[1] * GRID_SIZE]
        self.grid_size = GRID_SIZE
        # 在这里加载图像，使用默认的 GRID_SIZE
        self.image = load_image(image_name)
        if not self.image: # 添加图像加载失败的检查
             print(f"错误：未能加载 {image_name}")
             self.image = pygame.Surface((self.grid_size, self.grid_size))
             # 可以根据类型给占位符填色
             if 'blinky' in image_name: self.image.fill(RED)
             elif 'pinky' in image_name: self.image.fill((255,182,193)) # Pink color
             else: self.image.fill(BLUE) # Default color

        self.speed_factor = speed_factor # 速度系数（相对于蛇的基础速度）
        self.target_grid_pos = start_pos # 目标格子坐标
        self.last_target_update = 0 # 上次更新目标的时间 (pygame ticks)
        self.current_path = [] # 用于 A* 寻路（可选）
        self.move_direction = (0, 0) # 当前移动方向（格子单位，例如 (0, -1) 表示向上）

    def get_speed(self):
        """获取鬼魂当前的移动速度（像素/秒）。"""
        # 鬼魂速度相对于蛇的 *基础* 速度，忽略狂热/加热/加速
        return BASE_SNAKE_SPEED_PPS * self.speed_factor * self.grid_size

    def update_target(self, snake_body):
        """更新鬼魂的目标格子。由子类（Blinky, Pinky）重写。"""
        pass # 基类不实现具体目标逻辑

    def update(self, dt, snake_body):
        """更新鬼魂状态（目标、移动）。"""
        current_time_ms = pygame.time.get_ticks()

        # 定期更新目标和移动方向
        if current_time_ms - self.last_target_update > GHOST_TARGET_UPDATE_INTERVAL_MS:
            # 确保 snake_body 存在且非空再更新目标
            if snake_body:
                 self.update_target(snake_body)
            self.last_target_update = current_time_ms

            # --- 简单的寻路逻辑：朝着目标格子移动 ---
            # （如果使用 A*，这里会被 A* 的路径取代）
            if self.target_grid_pos and self.target_grid_pos != self.grid_pos:
                dx = self.target_grid_pos[0] - self.grid_pos[0]
                dy = self.target_grid_pos[1] - self.grid_pos[1]

                # 选择主要移动方向（优先移动距离较远的轴）
                if abs(dx) > abs(dy):
                    self.move_direction = (1 if dx > 0 else -1, 0)
                elif abs(dy) > abs(dx):
                    self.move_direction = (0, 1 if dy > 0 else -1)
                elif dx != 0: # 距离相等且不为零，优先水平或垂直？这里优先水平
                    self.move_direction = (1 if dx > 0 else -1, 0)
                elif dy != 0: # 距离相等且 dx 为 0，则只能垂直移动
                     self.move_direction = (0, 1 if dy > 0 else -1)
                else: # 目标就是当前位置
                     self.move_direction = (0, 0)
            else: # 没有目标或已到达目标
                self.move_direction = (0, 0)

            # --- A* 寻路（更复杂 - 需要寻路库/实现）---
            # self.find_path(snake_body) # 如果启用A*，在这里计算路径并设置 self.move_direction

        # --- 移动鬼魂（像素级移动） ---
        speed_pixels_per_sec = self.get_speed()
        move_dist = speed_pixels_per_sec * dt # 本帧应该移动的像素距离

        # 计算从当前像素位置到目标格子 *中心* 的向量
        target_center_px = (self.target_grid_pos[0] * self.grid_size + self.grid_size / 2,
                            self.target_grid_pos[1] * self.grid_size + self.grid_size / 2)
        current_center_px = (self.pixel_pos[0] + self.grid_size / 2,
                             self.pixel_pos[1] + self.grid_size / 2)

        delta_px = target_center_px[0] - current_center_px[0]
        delta_py = target_center_px[1] - current_center_px[1]
        dist_to_target = (delta_px**2 + delta_py**2)**0.5

        # 只有在距离目标较远时才移动
        if dist_to_target > 1: # 使用一个小的阈值避免抖动
            # 计算归一化方向向量
            norm_dx = delta_px / dist_to_target
            norm_dy = delta_py / dist_to_target

            # 应用移动
            self.pixel_pos[0] += norm_dx * move_dist
            self.pixel_pos[1] += norm_dy * move_dist

            # 根据移动后的像素位置（左上角）更新格子位置
            new_grid_x = int(self.pixel_pos[0] // self.grid_size)
            new_grid_y = int(self.pixel_pos[1] // self.grid_size)

            # 将格子位置限制在画布边界内
            new_grid_x = max(0, min(CANVAS_GRID_WIDTH - 1, new_grid_x))
            new_grid_y = max(0, min(CANVAS_GRID_HEIGHT - 1, new_grid_y))

            # 可以在这里添加与障碍物（蛇身、尸体）的碰撞检测，如果不用 A* 的话
            # 如果检测到碰撞，可以阻止进入该格子 (new_grid_x, new_grid_y)
            # 但简单的直接移动逻辑通常不会做这个检查

            self.grid_pos = (new_grid_x, new_grid_y)


        # --- 鬼魂警告音效 ---
        # 仅当蛇存在且有身体时才检查距离
        if snake_body:
             head_pos = snake_body[-1] # 获取蛇头位置
             # 计算鬼魂与蛇头之间的格子距离的平方
             dist_sq = (head_pos[0] - self.grid_pos[0])**2 + (head_pos[1] - self.grid_pos[1])**2
             # 如果距离小于等于警告距离的平方
             if dist_sq <= GHOST_WARNING_DISTANCE_GRIDS**2:
                 # 尝试播放警告音效（带冷却，避免重复播放）
                 self.game.try_play_sound('ghost_warning', unique=True)


    def draw(self, surface, camera_offset=(0, 0)): # 相机偏移现在总是 (0,0)
        # offset_x, offset_y = camera_offset # 不再需要
        offset_x, offset_y = 0, 0
        # 使用平滑的像素位置进行绘制
        draw_x = self.pixel_pos[0]
        draw_y = self.pixel_pos[1]
        # 不再需要屏幕边界检查
        if self.image: # 确保图像存在
             surface.blit(self.image, (draw_x, draw_y))

    # --- A* 寻路占位符 (保持注释状态) ---
    # def find_path(self, snake_body):
    #     # ... A* 实现代码 ...


# --- Blinky (红色鬼魂) ---
class Blinky(Ghost):
    def __init__(self, game):
        # 在画布内随机选择一个起始位置
        start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
        # 调用父类构造函数，传递图像文件名
        super().__init__(game, start_pos, 'ghost_blinky.png', GHOST_BASE_SPEED_FACTOR)
        self.type = "Blinky" # 鬼魂类型

    def update_target(self, snake_body):
        """Blinky 的目标是蛇身的中点。"""
        if not snake_body: return # 如果蛇不存在或身体为空，不更新目标
        # 计算蛇身中间段的索引
        mid_index = len(snake_body) // 2
        # 设置目标为该段的格子坐标
        self.target_grid_pos = snake_body[mid_index]

# --- Pinky (粉色鬼魂) ---
class Pinky(Ghost):
    def __init__(self, game):
        # 尝试在画布上找到一个不与蛇重叠的随机位置生成
        spawn_ok = False
        start_pos = (0,0) # 初始化起始位置
        attempts = 0
        max_attempts = 100 # 防止在拥挤时无限循环
        while not spawn_ok and attempts < max_attempts:
            attempts += 1
            start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
            # 检查起始位置是否在当前蛇身上（如果蛇存在）
            if game.snake is None or not hasattr(game.snake, 'body') or start_pos not in game.snake.body:
                 spawn_ok = True

        if not spawn_ok: # 如果尝试多次后仍未找到空位
            start_pos = (0,0) # 退回到角落生成
            print("警告：未能为 Pinky 找到清晰的生成点，生成在 (0,0)")

        # 调用父类构造函数，传递图像文件名
        super().__init__(game, start_pos, 'ghost_pinky.png', GHOST_BASE_SPEED_FACTOR)
        self.type = "Pinky" # 鬼魂类型

    def update_target(self, snake_body):
        """Pinky 的目标是蛇头前方一定格子数的位置。"""
        if not snake_body: return # 如果蛇不存在或为空，不更新目标
        head_pos = snake_body[-1] # 获取蛇头位置
        # 确保 game.snake 存在再访问方向
        if self.game.snake:
            head_dir = self.game.snake.direction # 获取蛇的当前移动方向
        else:
            head_dir = RIGHT # 如果蛇意外不存在，给一个默认方向

        # 计算蛇头前方 N 格的预测坐标
        target_x = head_pos[0] + head_dir[0] * PINKY_PREDICTION_DISTANCE
        target_y = head_pos[1] + head_dir[1] * PINKY_PREDICTION_DISTANCE

        # 将目标坐标限制在画布边界内
        target_x = max(0, min(CANVAS_GRID_WIDTH - 1, target_x))
        target_y = max(0, min(CANVAS_GRID_HEIGHT - 1, target_y))
        # 设置目标格子坐标
        self.target_grid_pos = (target_x, target_y)


# --- 粒子 类 (用于特效) ---
class Particle:
    def __init__(self, game, pos_px, color, size_range=(1, 3), vel_range=(-1.5, 1.5), lifespan_ms=400): # 调整了默认值以适应小格子
        self.game = game
        self.x, self.y = pos_px # 粒子的像素坐标 (float)
        self.color = color # 粒子颜色
        self.size = random.uniform(size_range[0], size_range[1]) # 随机大小
        # 随机速度 (像素/秒)
        self.vx = random.uniform(vel_range[0], vel_range[1]) * 60 # 乘以假设的FPS来得到大致的像素/秒
        self.vy = random.uniform(vel_range[0], vel_range[1]) * 60
        self.creation_time = pygame.time.get_ticks() # 创建时的游戏时钟 (毫秒)
        self.lifespan = lifespan_ms # 生命周期（毫秒）
        self.alpha = 255 # 初始透明度

    def update(self, dt):
        """更新粒子状态（位置、透明度、生命周期）。"""
        # 根据速度和时间间隔更新位置
        self.x += self.vx * dt
        self.y += self.vy * dt
        # 添加简单的重力效果
        self.vy += 0.05 * 60 * dt # 重力加速度 (像素/秒^2)

        # 检查生命周期是否结束
        elapsed = pygame.time.get_ticks() - self.creation_time
        if elapsed > self.lifespan:
            return False # 返回 False 表示可以移除

        # 计算淡出效果的 alpha 值
        self.alpha = max(0, 255 * (1 - (elapsed / self.lifespan)))
        return True # 粒子仍然活动

    def draw(self, surface, camera_offset=(0,0)): # 相机偏移现在总是 (0,0)
        # 如果粒子完全透明或尺寸过小，则不绘制
        if self.alpha <= 0 or self.size < 1: return

        # offset_x, offset_y = camera_offset # 不再需要
        offset_x, offset_y = 0, 0
        # 绘制位置（取整）
        draw_x = int(self.x)
        draw_y = int(self.y)

        # 绘制粒子（简单的圆形）
        # 确保半径至少为 1 像素
        radius = max(1, int(self.size))
        # 创建一个用于绘制带 alpha 的圆形的临时表面
        # SRCALPHA 使得表面支持像素级透明度
        try:
            particle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
             # 在临时表面上绘制圆心在 (radius, radius) 的圆
            pygame.draw.circle(particle_surf, (*self.color, int(self.alpha)), (radius, radius), radius)
             # 将临时表面绘制到主屏幕上，位置需要调整，使圆心在 (draw_x, draw_y)
            surface.blit(particle_surf, (draw_x - radius, draw_y - radius))
        except pygame.error as e:
             # 如果创建 Surface 失败 (例如半径过大或过小)，则跳过绘制
             # print(f"绘制粒子时创建表面失败: {e}")
             pass
        except ValueError as e:
             # 如果颜色值无效 (例如 alpha < 0)
             # print(f"绘制粒子时颜色值无效: {e}")
             pass