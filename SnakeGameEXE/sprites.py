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
        self.direction = random.choice([UP, DOWN, LEFT, RIGHT])
        self.new_direction = self.direction
        self.length = INITIAL_SNAKE_LENGTH
        self.is_accelerating = False
        self.alive = True
        self.split_available = True

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
        start_x = CANVAS_GRID_WIDTH // 2
        start_y = CANVAS_GRID_HEIGHT // 2
        for i in range(self.length):
            segment_x = start_x - self.direction[0] * i
            segment_y = start_y - self.direction[1] * i
            segment_x = max(0, min(CANVAS_GRID_WIDTH - 1, segment_x))
            segment_y = max(0, min(CANVAS_GRID_HEIGHT - 1, segment_y))
            self.body.appendleft((segment_x, segment_y))

        self.update_head_image() # 调用旋转方法

    # --------->>> 定义 get_head_position 方法 <<<---------
    def get_head_position(self):
        """获取蛇头的格子坐标。"""
        # 检查蛇身是否存在且不为空
        if hasattr(self, 'body') and self.body:
            return self.body[-1] # 蛇头是队列的最后一个元素
        else:
            # 如果蛇身不存在或为空，返回一个默认值或记录错误
            # print("错误：尝试获取空蛇或不存在的蛇的头部位置。")
            # 根据游戏逻辑，可能需要返回中心点或引发异常
            return (CANVAS_GRID_WIDTH // 2, CANVAS_GRID_HEIGHT // 2) # 返回画布中心作为备用
    # --------->>> get_head_position 方法定义结束 <<<---------


    def update_head_image(self):
        """根据当前方向旋转蛇头图像。"""
        angle = 0
        # 确保 self.direction 是有效的方向元组
        if isinstance(self.direction, tuple) and len(self.direction) == 2:
            if self.direction == UP: angle = 0
            elif self.direction == DOWN: angle = 180
            elif self.direction == LEFT: angle = 90
            elif self.direction == RIGHT: angle = -90
        else:
            print(f"警告：无效的蛇方向值 {self.direction}，无法确定旋转角度。")
            # 可以设置一个默认角度或不旋转

        if hasattr(self, 'head_image_orig') and self.head_image_orig:
            try:
                self.head_image = pygame.transform.rotate(self.head_image_orig, angle)
            except Exception as e:
                print(f"旋转蛇头图像时出错: {e}")
                if not hasattr(self, 'head_image') or not self.head_image:
                     self.head_image = self.head_image_orig # 使用原始图像作为备用
        else:
            print("警告：蛇头原始图像不存在，无法旋转。")
            if not hasattr(self, 'head_image') or not self.head_image:
                 self.head_image = pygame.Surface((self.grid_size, self.grid_size)); self.head_image.fill(self.color)


    def grow(self, amount=1):
        """增加蛇的目标长度。"""
        self.length += amount


    def change_direction(self, new_dir):
        """
        尝试改变蛇的移动方向（缓冲）。
        只有当新方向不是当前实际移动方向的反方向时才接受。
        """
        # 使用 self.direction (当前实际移动方向) 来判断是否为反方向
        if (new_dir[0] != -self.direction[0] or \
            new_dir[1] != -self.direction[1]):
           self.new_direction = new_dir # 更新缓冲方向


    def update(self):
        """更新蛇的状态（处理方向缓冲、移动、移除尾巴）。"""
        # 1. 应用缓冲的方向（如果有效）
        # 同样使用 self.direction 判断反方向
        if (self.new_direction[0] != -self.direction[0] or \
            self.new_direction[1] != -self.direction[1]):
             self.direction = self.new_direction # 更新实际移动方向
             self.update_head_image() # 方向改变，更新蛇头图像

        # 2. 计算新头位置
        head_x, head_y = self.get_head_position() # <-- 调用 get_head_position
        move_x, move_y = self.direction
        new_head = (head_x + move_x, head_y + move_y)

        # 3. 碰撞检测（由 Game 类在蛇移动后调用）
        #   这里只负责移动逻辑，碰撞检测在 Game.update 中进行更合适，
        #   因为它需要检查与其他对象（果实、鬼魂、尸体）的交互。
        #   但内部的 check_collisions 需要保留用于检测边界和自撞。
        self.check_collisions(new_head) # 检测边界和自撞，可能会设置 self.alive=False

        # 4. 如果存活，执行移动
        if self.alive:
            self.body.append(new_head) # 添加新头
            # 检查是否需要移除尾巴
            if len(self.body) > self.length:
                self.body.popleft()
        else:
            # 如果死亡，可以选择是否在死亡的那一帧移除导致碰撞的头？
            # 当前逻辑是不移除，游戏结束画面会显示碰撞状态。
            pass

        # 5. 更新分裂可用状态
        self.split_available = self.length >= SPLIT_MIN_LENGTH


    def check_collisions(self, new_head):
        """仅检查新头位置是否撞墙或撞自身。"""
        head_x, head_y = new_head

        # 1. 撞墙
        if not (0 <= head_x < CANVAS_GRID_WIDTH and 0 <= head_y < CANVAS_GRID_HEIGHT):
            self.alive = False
            self.game.trigger_game_over("撞墙")
            return # 已死亡，无需后续检查

        # 2. 撞自身
        check_body = list(self.body)
        if len(self.body) >= self.length: # 只有当蛇身达到目标长度时，尾巴才会被移除
             check_body = check_body[1:]
        if new_head in check_body:
             self.alive = False
             self.game.trigger_game_over("撞到自己")
             return


    def draw(self, surface, camera_offset=(0, 0)): # camera_offset 参数保留但未使用
        """绘制蛇的身体和头部。"""
        offset_x, offset_y = 0, 0 # 因为画布等于屏幕，偏移为0
        num_segments = len(self.body)

        # 绘制身体段（从尾到头绘制，除了最后一个）
        for i in range(num_segments - 1):
            segment = self.body[i]
            seg_x, seg_y = segment
            pixel_x = seg_x * self.grid_size + offset_x
            pixel_y = seg_y * self.grid_size + offset_y

            alpha = max(0, 255 * (1 - (num_segments - 1 - i) * SNAKE_ALPHA_DECREASE_PER_SEGMENT))

            if self.body_image: # 确保身体图像已加载
                # 优化：仅在需要透明度时复制和设置 alpha
                if alpha < 254:
                    try:
                        body_copy = self.body_image.copy()
                        body_copy.set_alpha(int(alpha))
                        surface.blit(body_copy, (pixel_x, pixel_y))
                    except Exception as e:
                         print(f"绘制蛇身段时出错: {e}")
                         pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size)) # 绘制备用方块
                else: # 完全不透明
                    surface.blit(self.body_image, (pixel_x, pixel_y))
            else: # 如果身体图像未加载
                 pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size))

        # 绘制头部（最后一个元素）
        if num_segments > 0:
             head = self.body[-1]
             head_x, head_y = head
             pixel_x = head_x * self.grid_size + offset_x
             pixel_y = head_y * self.grid_size + offset_y
             if hasattr(self, 'head_image') and self.head_image:
                 surface.blit(self.head_image, (pixel_x, pixel_y))
             else: # 如果头部图像未加载或无效
                 pygame.draw.rect(surface, self.color, (pixel_x, pixel_y, self.grid_size, self.grid_size))


        # 绘制速度线 (如果正在加速)
        if self.is_accelerating and self.alive:
            head_x, head_y = self.get_head_position()
            center_x = head_x * self.grid_size + self.grid_size // 2 + offset_x
            center_y = head_y * self.grid_size + self.grid_size // 2 + offset_y
            num_lines = 5
            line_length = self.grid_size * 1.2
            line_speed_offset = self.grid_size * 0.6

            back_dir_x, back_dir_y = -self.direction[0], -self.direction[1]
            perp_dir_x, perp_dir_y = -back_dir_y, back_dir_x # 垂直方向

            for i in range(num_lines):
                spread_factor = (i - num_lines // 2) * 0.3
                start_x = center_x + back_dir_x * line_speed_offset + perp_dir_x * spread_factor * self.grid_size
                start_y = center_y + back_dir_y * line_speed_offset + perp_dir_y * spread_factor * self.grid_size
                end_x = start_x + back_dir_x * line_length
                end_y = start_y + back_dir_y * line_length
                pygame.draw.line(surface, WHITE, (start_x, start_y), (end_x, end_y), 1)


    def split(self):
        """执行分裂操作。"""
        if not self.split_available:
            return None, None

        split_index = len(self.body) // 2
        # 确保分裂后两部分都有内容 (至少长度为2才能分)
        if split_index == 0 or split_index == len(self.body):
             print("警告：蛇太短无法分裂。")
             return None, None

        corpse_segments = deque(list(self.body)[split_index:])
        new_snake_body = deque(list(self.body)[:split_index])

        # --- 计算新蛇的方向 (基于尾部变头) ---
        new_direction = (0, 0)
        if new_snake_body: # 确保新蛇身体不为空
            new_head_pos = new_snake_body[-1] # 新头是原尾巴段的最后一节
            if len(new_snake_body) > 1:
                # 方向：倒数第二节指向新头
                prev_segment_pos = new_snake_body[-2]
                new_direction = (new_head_pos[0] - prev_segment_pos[0],
                                 new_head_pos[1] - prev_segment_pos[1])
            elif corpse_segments: # 新蛇只有一节，尝试远离尸体
                 corpse_start_pos = corpse_segments[0]
                 new_direction = (new_head_pos[0] - corpse_start_pos[0],
                                  new_head_pos[1] - corpse_start_pos[1])
                 # 如果紧挨着，使用分裂前的方向作为备用
                 if new_direction == (0,0): new_direction = self.direction
            else: # 无法确定方向，保持原方向
                 new_direction = self.direction

            # 最终检查零向量
            if new_direction == (0,0):
                print("警告：分裂后计算方向为零向量，随机选择方向。")
                valid_dirs = [d for d in [UP, DOWN, LEFT, RIGHT] if d != self.direction and d != (-self.direction[0], -self.direction[1])]
                new_direction = random.choice(valid_dirs) if valid_dirs else RIGHT
        else:
             print("错误：分裂逻辑中 new_snake_body 意外为空。")
             return None, None
        # --- 方向计算结束 ---

        # 更新当前蛇对象的状态
        self.body = new_snake_body
        self.length = len(self.body)
        self.direction = new_direction
        self.new_direction = new_direction # 同步缓冲方向
        self.update_head_image()

        # 创建尸体对象
        corpse = Corpse(self.game, corpse_segments)

        # 播放效果
        self.game.play_sound('split')
        if corpse.segments:
            self.game.add_particles(corpse.segments[0], 10, RED)

        print(f"分裂完成: 新蛇身体: {list(self.body)}, 新方向: {self.direction}")
        return corpse, True


# --- 尸体 类 ---
class Corpse:
    def __init__(self, game, segments):
        self.game = game
        self.segments = segments
        self.grid_size = GRID_SIZE
        self.image = load_image('corpse.png', size=self.grid_size)
        if not self.image:
             print("错误：未能加载 corpse.png")
             self.image = pygame.Surface((self.grid_size, self.grid_size)); self.image.fill(GREY)
        self.creation_time = time.time()
        self.lifespan = CORPSE_LIFESPAN_SECONDS
        self.flicker_start_time = self.creation_time + CORPSE_FLICKER_START_OFFSET
        self.flicker_end_time = self.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS
        self.fade_start_time = self.flicker_end_time
        self.fade_end_time = self.fade_start_time + CORPSE_FADE_DURATION_SECONDS
        self.visible = True
        self.is_fading = False
        self.flicker_on = True
        self.last_flicker_toggle = 0
        self.flicker_interval = 150

    def update(self):
        current_time = time.time()
        if current_time > self.fade_end_time: return False
        self.is_fading = current_time > self.fade_start_time
        if self.flicker_start_time <= current_time < self.flicker_end_time:
            now_ms = pygame.time.get_ticks()
            if now_ms - self.last_flicker_toggle > self.flicker_interval:
                self.flicker_on = not self.flicker_on
                self.last_flicker_toggle = now_ms
            self.visible = self.flicker_on
        elif self.is_fading: self.visible = True
        else: self.visible = True
        return True

    def draw(self, surface, camera_offset=(0, 0)):
        if not self.visible: return
        offset_x, offset_y = 0, 0
        alpha = 255
        if self.is_fading:
             fade_duration = CORPSE_FADE_DURATION_SECONDS
             if fade_duration <= 0: fade_duration = 1
             fade_progress = (time.time() - self.fade_start_time) / fade_duration
             alpha = max(0, 255 * (1 - fade_progress))

        img_to_draw = self.image
        if alpha < 254:
            try:
                img_to_draw = self.image.copy()
                img_to_draw.set_alpha(int(alpha))
            except Exception as e: img_to_draw = self.image

        for seg_x, seg_y in self.segments:
            pixel_x = seg_x * self.grid_size + offset_x
            pixel_y = seg_y * self.grid_size + offset_y
            if img_to_draw: surface.blit(img_to_draw, (pixel_x, pixel_y))
            else: pygame.draw.rect(surface, GREY, (pixel_x, pixel_y, self.grid_size, self.grid_size), 1)

    def get_end_points(self):
        if not self.segments: return None, None
        try: return self.segments[0], self.segments[-1]
        except IndexError: return None, None

# --- 果实 基类 ---
class Fruit:
    def __init__(self, game, position, fruit_type, image_name, lifespan=None):
        self.game = game
        self.position = position
        self.type = fruit_type
        self.grid_size = GRID_SIZE
        self.image = load_image(image_name, size=self.grid_size)
        if not self.image:
             print(f"错误：未能加载 {image_name}")
             self.image = pygame.Surface((self.grid_size, self.grid_size))
             if self.type == 'healthy': self.image.fill(GREEN)
             elif self.type == 'bomb': self.image.fill(RED)
             else: self.image.fill(WHITE)
        self.lifespan = lifespan
        self.creation_time = time.time()
        self.is_special = fruit_type != 'normal'

    def update(self):
        if self.lifespan is not None and time.time() - self.creation_time > self.lifespan:
            return False
        return True

    def draw(self, surface, camera_offset=(0, 0)):
        offset_x, offset_y = 0, 0
        pixel_x = self.position[0] * self.grid_size + offset_x
        pixel_y = self.position[1] * self.grid_size + offset_y
        if self.image: surface.blit(self.image, (pixel_x, pixel_y))

# --- 鬼魂 基类 ---
class Ghost:
    def __init__(self, game, start_pos, image_name, speed_factor):
        self.game = game
        self.grid_pos = start_pos
        self.pixel_pos = [start_pos[0] * GRID_SIZE, start_pos[1] * GRID_SIZE]
        self.grid_size = GRID_SIZE
        self.image = load_image(image_name, size=self.grid_size)
        if not self.image:
             print(f"错误：未能加载 {image_name}")
             self.image = pygame.Surface((self.grid_size, self.grid_size))
             if 'blinky' in image_name: self.image.fill(RED)
             elif 'pinky' in image_name: self.image.fill((255,182,193))
             else: self.image.fill(BLUE)
        self.speed_factor = speed_factor
        self.target_grid_pos = start_pos
        self.last_target_update = 0
        self.current_path = []
        self.move_direction = (0, 0)

    def get_speed(self):
        return BASE_SNAKE_SPEED_PPS * self.speed_factor * self.grid_size

    def update_target(self, snake_body): pass

    def update(self, dt, snake_body):
        current_time_ms = pygame.time.get_ticks()
        if current_time_ms - self.last_target_update > GHOST_TARGET_UPDATE_INTERVAL_MS:
            if snake_body: self.update_target(snake_body)
            self.last_target_update = current_time_ms
            if self.target_grid_pos and self.target_grid_pos != self.grid_pos:
                dx = self.target_grid_pos[0] - self.grid_pos[0]; dy = self.target_grid_pos[1] - self.grid_pos[1]
                if abs(dx) > abs(dy): self.move_direction = (1 if dx > 0 else -1, 0)
                elif abs(dy) > abs(dx): self.move_direction = (0, 1 if dy > 0 else -1)
                elif dx != 0: self.move_direction = (1 if dx > 0 else -1, 0)
                elif dy != 0: self.move_direction = (0, 1 if dy > 0 else -1)
                else: self.move_direction = (0, 0)
            else: self.move_direction = (0, 0)

        speed_pixels_per_sec = self.get_speed()
        move_dist = speed_pixels_per_sec * dt
        target_center_px = (self.target_grid_pos[0] * self.grid_size + self.grid_size / 2, self.target_grid_pos[1] * self.grid_size + self.grid_size / 2)
        current_center_px = (self.pixel_pos[0] + self.grid_size / 2, self.pixel_pos[1] + self.grid_size / 2)
        delta_px = target_center_px[0] - current_center_px[0]; delta_py = target_center_px[1] - current_center_px[1]
        dist_to_target = (delta_px**2 + delta_py**2)**0.5

        if dist_to_target > 1:
            norm_dx = delta_px / dist_to_target; norm_dy = delta_py / dist_to_target
            self.pixel_pos[0] += norm_dx * move_dist; self.pixel_pos[1] += norm_dy * move_dist
            new_grid_x = int(self.pixel_pos[0] // self.grid_size); new_grid_y = int(self.pixel_pos[1] // self.grid_size)
            new_grid_x = max(0, min(CANVAS_GRID_WIDTH - 1, new_grid_x)); new_grid_y = max(0, min(CANVAS_GRID_HEIGHT - 1, new_grid_y))
            self.grid_pos = (new_grid_x, new_grid_y)

        if snake_body:
             head_pos = snake_body[-1]
             dist_sq = (head_pos[0] - self.grid_pos[0])**2 + (head_pos[1] - self.grid_pos[1])**2
             if dist_sq <= GHOST_WARNING_DISTANCE_GRIDS**2: self.game.try_play_sound('ghost_warning', unique=True)

    def draw(self, surface, camera_offset=(0, 0)):
        offset_x, offset_y = 0, 0
        draw_x = self.pixel_pos[0] + offset_x; draw_y = self.pixel_pos[1] + offset_y
        if self.image: surface.blit(self.image, (draw_x, draw_y))

# --- Blinky ---
class Blinky(Ghost):
    def __init__(self, game):
        start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
        super().__init__(game, start_pos, 'ghost_blinky.png', GHOST_BASE_SPEED_FACTOR)
        self.type = "Blinky"
    def update_target(self, snake_body):
        if not snake_body: return
        mid_index = len(snake_body) // 2
        if 0 <= mid_index < len(snake_body): self.target_grid_pos = snake_body[mid_index]
        elif snake_body: self.target_grid_pos = snake_body[-1]

# --- Pinky ---
class Pinky(Ghost):
    def __init__(self, game):
        spawn_ok = False; start_pos = (0,0); attempts = 0; max_attempts = 100
        while not spawn_ok and attempts < max_attempts:
            attempts += 1
            start_pos = (random.randint(0, CANVAS_GRID_WIDTH - 1), random.randint(0, CANVAS_GRID_HEIGHT - 1))
            if game.snake is None or not hasattr(game.snake, 'body') or start_pos not in game.snake.body: spawn_ok = True
        if not spawn_ok: start_pos = (0,0); print("警告：未能为 Pinky 找到清晰的生成点，生成在 (0,0)")
        super().__init__(game, start_pos, 'ghost_pinky.png', GHOST_BASE_SPEED_FACTOR)
        self.type = "Pinky"
    def update_target(self, snake_body):
        if not snake_body: return
        head_pos = snake_body[-1]
        if self.game.snake: head_dir = self.game.snake.direction
        else: head_dir = RIGHT
        target_x = head_pos[0] + head_dir[0] * PINKY_PREDICTION_DISTANCE; target_y = head_pos[1] + head_dir[1] * PINKY_PREDICTION_DISTANCE
        target_x = max(0, min(CANVAS_GRID_WIDTH - 1, target_x)); target_y = max(0, min(CANVAS_GRID_HEIGHT - 1, target_y))
        self.target_grid_pos = (target_x, target_y)

# --- 粒子 类 ---
class Particle:
    def __init__(self, game, pos_px, color, size_range=(1, 3), vel_range=(-1.5, 1.5), lifespan_ms=400):
        self.game = game; self.x, self.y = pos_px; self.color = color
        self.size = random.uniform(size_range[0], size_range[1])
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
        offset_x, offset_y = 0, 0
        draw_x = int(self.x + offset_x); draw_y = int(self.y + offset_y); radius = max(1, int(self.size))
        try:
            particle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (*self.color, int(self.alpha)), (radius, radius), radius)
            surface.blit(particle_surf, (draw_x - radius, draw_y - radius))
        except Exception as e: pass