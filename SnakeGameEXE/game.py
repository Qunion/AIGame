import pygame
import sys
import time
import random
from collections import deque
from settings import * # 导入更新后的设置
from sprites import Snake, Fruit, Corpse, Blinky, Pinky, Particle # 导入精灵类

class Game:
    def __init__(self):
        # 初始化 Pygame 模块
        pygame.init()
        pygame.mixer.init() # 初始化音频混合器

        # 创建游戏窗口
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE) # 设置窗口标题
        self.clock = pygame.time.Clock() # 创建时钟对象，用于控制帧率

        # 加载字体 (使用更新后的 get_font 函数)
        self.font_small = get_font(24)
        self.font_large = get_font(64)
        self.font_medium = get_font(36)

        # 游戏状态变量
        self.is_running = True # 游戏主循环标志
        self.game_state = STATE_PLAYING # 当前游戏状态 (玩、结束、暂停等)
        self.last_game_over_reason = "" # 上次游戏结束的原因
        self.rewind_available = True # 时光倒流是否可用

        # 尝试禁用系统文本输入处理 (效果有限)
        try:
             pygame.key.stop_text_input()
             print("尝试停止文本输入...")
        except Exception as e:
             print(f"无法停止文本输入 (可能正常): {e}")

        # 加载游戏资源 (图像、声音)
        self.load_assets()

        # 游戏逻辑相关变量
        self.start_time = time.time() # 游戏开始的墙上时间
        self.game_timer = 0 # 游戏内计时器 (秒)
        self.last_move_time = 0 # 上次蛇移动的时间 (用于控制速度)
        self.last_fruit_spawn_time = 0 # 上次生成果实的时间
        self.last_gradual_heat_time = 0 # 上次速度加热的时间
        self.last_frenzy_start_time = -FRENZY_INTERVAL_SECONDS # 上次狂热开始时间 (初始化为负，使第一次狂热能较早触发)
        self.frenzy_active = False # 当前是否处于狂热状态
        self.pinky_spawned = False # Pinky 鬼魂是否已生成

        # 时光倒流历史记录 (使用双端队列，限制最大长度)
        # maxlen 大约是 REWIND_SECONDS 秒内，每 0.5 秒记录一次状态所对应的帧数
        self.history = deque(maxlen=int(REWIND_SECONDS * FPS * 0.5)) # 调整快照频率 (例如改为每秒4次)
        self.frames_since_last_snapshot = 0 # 自上次快照以来的帧数

        # 音效控制相关变量
        self.ghost_warning_playing = False # 鬼魂警告音效是否正在播放 (用于冷却)
        self.last_ghost_warning_time = 0 # 上次播放警告音效的时间
        self.speedup_channel = None # 用于播放加速音效的专属频道

        # 游戏对象列表/组
        self.all_sprites = pygame.sprite.Group() # Pygame 的精灵组 (可选使用)
        self.snake = None # 蛇对象
        self.fruits = [] # 果实列表
        self.corpses = [] # 尸体列表
        self.ghosts = [] # 鬼魂列表
        self.particles = [] # 粒子列表

        # 因为画布现在等于屏幕大小，相机偏移不再需要
        # self.camera_offset_x = 0
        # self.camera_offset_y = 0

        # 计算绘制区域的偏移量，用于将画布居中显示 (如果画布像素尺寸小于屏幕尺寸)
        self.draw_offset_x = (SCREEN_WIDTH - CANVAS_WIDTH_PX) // 2
        self.draw_offset_y = (SCREEN_HEIGHT - CANVAS_HEIGHT_PX) // 2

    def load_assets(self):
        """加载游戏所需的图像和声音资源。"""
        self.images = {
            # 背景图加载，但绘制方式改变 (在画布区域内平铺)
            'background': load_image('background.png', size=None, use_alpha=False),
        }
        # 精灵的图像在其各自的类中加载

        self.sounds = {
            'pickup_normal': load_sound('pickup_normal.wav'),
            'pickup_healthy': load_sound('pickup_healthy.wav'),
            'pickup_bomb': load_sound('pickup_bomb.wav'),
            'split': load_sound('split.wav'),
            'merge': load_sound('merge.wav'),
            'death': load_sound('death.wav'),
            'rewind': load_sound('rewind.wav'),
            'ghost_warning': load_sound('ghost_warning.wav'),
            'speedup': load_sound('speedup.wav') # 加载加速音效
        }

        # 为加速音效寻找一个专用频道，以便循环播放和停止
        self.speedup_channel = pygame.mixer.find_channel() # 尝试获取一个空闲频道
        if not self.speedup_channel:
            # 如果没有空闲频道，尝试强制获取一个 (可能会覆盖其他音效)
            self.speedup_channel = pygame.mixer.find_channel(True)
            if not self.speedup_channel:
                 print("警告：无法为加速音效找到可用的混音器频道。")
            else:
                 print("警告：强制获取了一个混音器频道用于加速音效。")

        # 加载并播放背景音乐
        if load_music('bgm.ogg'):
            pygame.mixer.music.play(loops=-1) # 无限循环播放
            pygame.mixer.music.set_volume(0.3) # 设置音量 (0.0 到 1.0)

    def play_sound(self, sound_name):
        """播放指定名称的音效。"""
        sound = self.sounds.get(sound_name)
        if sound:
            # 查找一个空闲频道播放，避免打断其他重要音效 (如果可能)
            ch = pygame.mixer.find_channel()
            if ch:
                ch.play(sound)
            else:
                # 如果没有空闲频道，就直接播放 (可能会在默认频道上播放)
                sound.play()
                # print(f"警告：没有空闲频道，在默认频道播放 {sound_name}")

    def try_play_sound(self, sound_name, unique=False, cooldown=1000):
        """
        尝试播放音效，可选地确保它不会过于频繁地播放（用于警告音等）。
        unique=True: 启用冷却机制。
        cooldown: 冷却时间（毫秒）。
        """
        sound = self.sounds.get(sound_name)
        if sound:
            if unique:
                 now = pygame.time.get_ticks() # 获取当前游戏时间 (毫秒)
                 # 特殊处理鬼魂警告音效
                 if sound_name == 'ghost_warning':
                     # 检查是否不在播放状态，或者冷却时间已过
                     if not self.ghost_warning_playing or now - self.last_ghost_warning_time > cooldown:
                         ch = pygame.mixer.find_channel() # 找个频道播放
                         if ch: ch.play(sound)
                         else: sound.play()
                         self.ghost_warning_playing = True # 标记为正在播放
                         self.last_ghost_warning_time = now # 记录播放时间
                 # 如果需要，可以为其他 unique 音效添加类似逻辑
            else:
                 # 非 unique 音效直接播放
                 ch = pygame.mixer.find_channel()
                 if ch: ch.play(sound)
                 else: sound.play()

            # 重置警告音效播放标志的逻辑可以放在鬼魂远离时，或者简单地在一段时间后重置
            if self.ghost_warning_playing and now - self.last_ghost_warning_time > cooldown * 2: # 例如 2 倍冷却时间后
                 self.ghost_warning_playing = False # 允许再次触发

    def reset_game(self):
        """重置游戏状态到初始设置，开始新的一局。"""
        print("重置游戏中...") # 中文提示
        # 停止可能正在循环的音效
        if self.speedup_channel: self.speedup_channel.stop()

        # 清空游戏对象列表和组
        self.all_sprites.empty()
        self.fruits.clear()
        self.corpses.clear()
        self.ghosts.clear()
        self.particles.clear()
        self.history.clear() # 清除时光倒流历史

        # 重新创建蛇对象
        self.snake = Snake(self)
        # 生成初始果实
        self.spawn_fruit(count=2, force_special=True)
        # 生成 Blinky 鬼魂
        self.ghosts.append(Blinky(self))

        # 重置计时器和状态标志
        self.start_time = time.time()
        self.game_timer = 0
        self.last_move_time = 0
        self.last_fruit_spawn_time = time.time() # 重置生成计时器
        self.last_gradual_heat_time = time.time()
        self.last_frenzy_start_time = time.time() # 重置狂热计时器
        self.frenzy_active = False
        self.pinky_spawned = False
        self.rewind_available = True # 重置时光倒流可用性
        self.last_game_over_reason = ""
        self.frames_since_last_snapshot = 0
        self.ghost_warning_playing = False # 重置警告音效标志
        if self.snake: self.snake.is_accelerating = False # 确保加速状态关闭

        self.game_state = STATE_PLAYING # 设置游戏状态为进行中
        print("游戏重置完成.") # 中文提示

    def get_current_speed(self):
        """计算蛇当前的移动速度（格子/秒）。"""
        # 1. 基础速度
        current_speed = BASE_SNAKE_SPEED_PPS

        # 2. 逐渐燥热加成
        time_elapsed = self.game_timer # 获取游戏内已进行时间
        # 计算有多少个加热间隔过去了
        heat_intervals = time_elapsed // GRADUAL_HEAT_INTERVAL_SECONDS
        # 计算加热带来的速度乘数
        heat_bonus_multiplier = 1.0 + (GRADUAL_HEAT_INCREASE_PERCENT * heat_intervals)
        current_speed *= heat_bonus_multiplier

        # 3. 狂热时刻加成
        frenzy_bonus_multiplier = 1.0 # 默认无加成
        # 检查狂热状态和时间，应用速度曲线
        if self.frenzy_active:
            time_since_frenzy_start = time.time() - self.last_frenzy_start_time
            if time_since_frenzy_start < FRENZY_RAMP_UP_SECONDS:
                # 速度线性提升阶段
                progress = time_since_frenzy_start / FRENZY_RAMP_UP_SECONDS
                frenzy_bonus_multiplier = 1.0 + FRENZY_PEAK_BONUS_PERCENT * progress
            elif time_since_frenzy_start < FRENZY_DURATION_SECONDS - FRENZY_RAMP_DOWN_SECONDS:
                # 速度保持峰值阶段
                frenzy_bonus_multiplier = 1.0 + FRENZY_PEAK_BONUS_PERCENT
            elif time_since_frenzy_start < FRENZY_DURATION_SECONDS:
                 # 速度线性回落阶段
                 time_left_in_ramp_down = FRENZY_DURATION_SECONDS - time_since_frenzy_start
                 progress = time_left_in_ramp_down / FRENZY_RAMP_DOWN_SECONDS
                 frenzy_bonus_multiplier = 1.0 + FRENZY_PEAK_BONUS_PERCENT * progress
            # else: 狂热时间已过，在 check_frenzy_state 中处理状态切换

        current_speed *= frenzy_bonus_multiplier

        # 4. 加速按钮加成
        if self.snake and self.snake.is_accelerating: # 检查蛇是否存在且正在加速
             current_speed *= ACCELERATION_FACTOR

        # 返回最终计算出的速度
        return max(0.1, current_speed) # 确保速度不会低于一个很小的值，防止 move_interval 无穷大

    # --------->>> 定义 check_frenzy_state 方法 <<<---------
    def check_frenzy_state(self):
        """检查并更新狂热状态。"""
        now = time.time()
        # 检查是否应该开始狂热
        if not self.frenzy_active and (now - self.last_frenzy_start_time >= FRENZY_INTERVAL_SECONDS):
             self.frenzy_active = True
             self.last_frenzy_start_time = now # 更新狂热开始时间
             print("狂热时刻开始!") # 中文提示
        # 检查是否应该结束狂热
        elif self.frenzy_active and (now - self.last_frenzy_start_time >= FRENZY_DURATION_SECONDS):
             self.frenzy_active = False
             # last_frenzy_start_time 保持不变，用于计算下一次狂热的间隔
             print("狂热时刻结束!") # 中文提示
    # --------->>> check_frenzy_state 方法定义结束 <<<---------

    def spawn_fruit(self, count=1, force_special=False):
        """在画布上生成指定数量的果实。"""
        spawned_count = 0
        attempts = 0
        # 最大尝试次数，避免画布满时死循环
        max_attempts = CANVAS_GRID_WIDTH * CANVAS_GRID_HEIGHT

        # 创建当前所有被占据格子的集合，提高查找效率
        current_occupancies = set()
        if self.snake: current_occupancies.update(self.snake.body)
        current_occupancies.update(f.position for f in self.fruits)
        current_occupancies.update(g.grid_pos for g in self.ghosts)
        for c in self.corpses: current_occupancies.update(c.segments)

        while spawned_count < count and len(self.fruits) < MAX_FRUITS and attempts < max_attempts:
            attempts += 1
            # 随机选择一个生成位置
            pos = (random.randint(0, CANVAS_GRID_WIDTH - 1),
                   random.randint(0, CANVAS_GRID_HEIGHT - 1))

            # 检查该位置是否已被占据
            if pos not in current_occupancies:
                # 确定果实类型
                fruit_type = 'normal'
                lifespan = None
                img_name = 'fruit_normal.png'

                # 特殊果实生成逻辑
                is_special = False
                # 如果强制生成特殊果实且这是第一个生成的，则必定是特殊
                if force_special and spawned_count == 0:
                    is_special = True
                # 否则按概率生成特殊果实
                elif random.random() < 0.3: # 例如 30% 概率
                    is_special = True

                if is_special:
                    # 在特殊果实中随机选择一种
                    choice = random.choice(['healthy', 'bomb'])
                    if choice == 'healthy':
                        fruit_type = 'healthy'
                        lifespan = HEALTHY_FRUIT_DURATION_SECONDS
                        img_name = 'fruit_healthy.png'
                    else: # 炸弹果实
                         fruit_type = 'bomb'
                         lifespan = BOMB_FRUIT_DURATION_SECONDS
                         img_name = 'fruit_bomb.png'

                # 创建果实对象（传递图像文件名）并添加到列表
                new_fruit = Fruit(self, pos, fruit_type, img_name, lifespan)
                self.fruits.append(new_fruit)
                # 更新已占据位置集合
                current_occupancies.add(pos)
                spawned_count += 1
                # print(f"生成了 {fruit_type} 果实于 {pos}") # 调试信息


    def trigger_game_over(self, reason="未知原因"): # 默认原因使用中文
         """触发游戏结束状态。"""
         # 确保只触发一次游戏结束
         if self.game_state != STATE_GAME_OVER:
             print(f"游戏结束! 原因: {reason}") # 中文提示
             self.last_game_over_reason = reason
             self.game_state = STATE_GAME_OVER # 切换游戏状态
             # 停止蛇的活动
             if self.snake: # 检查蛇对象是否存在
                 self.snake.alive = False
                 self.snake.is_accelerating = False # 停止加速状态
             # 停止可能在播放的加速音效
             if self.speedup_channel: self.speedup_channel.stop()

             # 根据死亡原因播放不同音效
             if reason == "炸弹果实": # 匹配中文原因
                  self.play_sound('pickup_bomb') # 碰到炸弹的音效
             else:
                  self.play_sound('death') # 其他死亡原因的音效


    def handle_input(self):
        """处理玩家的输入事件（键盘、鼠标等）。"""
        for event in pygame.event.get():
            # 处理退出事件
            if event.type == pygame.QUIT:
                self.is_running = False

            # 处理键盘按下事件
            if event.type == pygame.KEYDOWN:
                # 在游戏进行中状态下的按键处理
                if self.game_state == STATE_PLAYING and self.snake: # 确保蛇存在
                    # 方向键控制
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.snake.change_direction(UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.snake.change_direction(DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.snake.change_direction(LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.snake.change_direction(RIGHT)

                    # 加速功能键 (Shift)
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        if not self.snake.is_accelerating: # 避免重复触发
                            self.snake.is_accelerating = True
                            # 播放循环加速音效
                            if self.speedup_channel and self.sounds['speedup']:
                                self.speedup_channel.play(self.sounds['speedup'], loops=-1)

                    # 分裂功能键 (空格)
                    elif event.key == pygame.K_SPACE:
                        if self.snake.split_available: # 检查是否满足分裂条件
                            new_corpse, success = self.snake.split() # 尝试分裂
                            if success: # 如果分裂成功
                                self.corpses.append(new_corpse) # 添加新生成的尸体

                    # 退出键 (Escape)
                    elif event.key == pygame.K_ESCAPE:
                         self.is_running = False # 按 Esc 退出游戏

                # 在游戏结束状态下的按键处理
                elif self.game_state == STATE_GAME_OVER:
                    # 重新开始 (R键)
                    if event.key == pygame.K_r:
                        self.reset_game()
                    # 时光倒流 (T键)，且功能可用
                    if event.key == pygame.K_t and self.rewind_available :
                        self.attempt_rewind()

            # 处理键盘松开事件
            if event.type == pygame.KEYUP:
                 # 在游戏进行中状态下的按键处理
                 if self.game_state == STATE_PLAYING and self.snake:
                     # 停止加速 (松开 Shift)
                     if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                         self.snake.is_accelerating = False
                         # 停止加速音效
                         if self.speedup_channel:
                             self.speedup_channel.stop()

            # 处理鼠标点击事件 (用于游戏结束界面的按钮)
            if event.type == pygame.MOUSEBUTTONDOWN:
                 if self.game_state == STATE_GAME_OVER:
                      # 检查点击位置是否在按钮区域内
                      self.check_game_over_button_clicks(event.pos)


    def update(self, dt):
        """更新游戏逻辑状态（每帧调用）。"""
        # 如果游戏不在进行中，则不更新主要逻辑 (但可能更新粒子等效果)
        if self.game_state != STATE_PLAYING:
            # 更新粒子效果
            self.particles[:] = [p for p in self.particles if p.update(dt)]
            return

        # 更新游戏内计时器
        self.game_timer = time.time() - self.start_time

        # ---->>> 调用 check_frenzy_state <<<----
        # 检查并更新狂热状态
        self.check_frenzy_state()
        # ---->>> 调用结束 <<<----


        # --- 蛇的移动计时和逻辑 ---
        speed = self.get_current_speed() # 获取当前计算出的速度
        if speed <= 0: return # 避免速度为零或负数
        move_interval = 1.0 / speed # 计算移动一格所需的时间间隔
        current_time = time.time() # 获取当前墙上时间

        moved_this_frame = False # 标记本帧蛇是否移动了
        # 检查是否到达移动时间
        if current_time - self.last_move_time >= move_interval:
             if self.snake: # 确保蛇对象存在
                 self.snake.update() # 更新蛇的位置和状态
                 self.last_move_time = current_time # 更新上次移动时间
                 moved_this_frame = True # 标记已移动

        # --- 碰撞检测 (在蛇移动之后进行) ---
        # 仅在蛇移动了且仍然存活时进行碰撞检测
        if moved_this_frame and self.snake and self.snake.alive:
             self.check_fruit_collisions() # 检测与果实的碰撞
             self.check_corpse_merge()     # 检测与尸体的融合
             self.check_ghost_collisions() # 检测与鬼魂的碰撞

        # --- Pinky 生成逻辑 ---
        # 检查是否达到生成条件且尚未生成
        if not self.pinky_spawned and self.snake and self.snake.length >= PINKY_SPAWN_LENGTH:
            self.ghosts.append(Pinky(self)) # 创建 Pinky 对象并添加到列表
            self.pinky_spawned = True # 标记已生成
            print("Pinky 已生成!") # 中文提示

        # --- 更新其他游戏元素 ---
        # 更新鬼魂状态 (传递当前蛇身用于目标计算)
        snake_body_for_ghosts = self.snake.body if self.snake else deque() # 获取蛇身，如果蛇不存在则为空队列
        for ghost in self.ghosts:
             ghost.update(dt, snake_body_for_ghosts) # 更新每个鬼魂

        # 更新果实状态 (检查生命周期)，并移除过期的果实
        self.fruits[:] = [f for f in self.fruits if f.update()]

        # 更新尸体状态 (闪烁、淡出)，并移除消失的尸体
        self.corpses[:] = [c for c in self.corpses if c.update()]

        # 更新粒子状态，并移除生命周期结束的粒子
        self.particles[:] = [p for p in self.particles if p.update(dt)]

        # --- 果实生成逻辑 ---
        now = time.time()
        # 按时间间隔生成普通果实
        if now - self.last_fruit_spawn_time > FRUIT_SPAWN_INTERVAL_SECONDS:
            self.spawn_fruit() # 调用生成函数
            self.last_fruit_spawn_time = now # 更新上次生成时间
        # 如果场上没有果实，则强制生成两个（包含特殊果实）
        if len(self.fruits) == 0:
            self.spawn_fruit(count=2, force_special=True)
            self.last_fruit_spawn_time = now # 重置生成计时器


        # --- 时光倒流状态快照 ---
        self.frames_since_last_snapshot += 1
        # 设置快照频率 (例如每秒4次)
        snapshot_interval_frames = int(FPS / 4)
        if self.frames_since_last_snapshot >= snapshot_interval_frames:
            self.save_state_for_rewind() # 保存当前状态
            self.frames_since_last_snapshot = 0 # 重置计数器


    def check_fruit_collisions(self):
        """检查蛇头是否与果实发生碰撞。"""
        # 确保蛇存在且存活
        if not self.snake or not self.snake.alive: return
        head_pos = self.snake.get_head_position() # 获取蛇头位置
        eaten_fruit_index = -1 # 标记被吃掉果实的索引

        # 遍历所有果实
        for i, fruit in enumerate(self.fruits):
            if fruit.position == head_pos: # 如果蛇头位置与果实位置重合
                eaten_fruit_index = i # 记录索引
                # 根据果实类型执行效果
                if fruit.type == 'normal':
                    self.snake.grow(1) # 普通果实长度+1
                    self.play_sound('pickup_normal')
                elif fruit.type == 'healthy':
                    self.snake.grow(2) # 健康果实长度+2
                    self.play_sound('pickup_healthy')
                elif fruit.type == 'bomb':
                     self.trigger_game_over("炸弹果实") # 碰到炸弹游戏结束 (使用中文原因)
                break # 每步只吃一个果实

        # 如果吃到了果实，则从列表中移除
        if eaten_fruit_index != -1:
            # 安全地删除元素
            if eaten_fruit_index < len(self.fruits):
                del self.fruits[eaten_fruit_index]


    def check_ghost_collisions(self):
        """检查蛇头是否与鬼魂发生碰撞。"""
        if not self.snake or not self.snake.alive: return
        head_pos = self.snake.get_head_position()
        # 遍历所有鬼魂
        for ghost in self.ghosts:
            # 检查蛇头格子是否与鬼魂格子重合
            if ghost.grid_pos == head_pos:
                 # 触发游戏结束，原因包含鬼魂类型
                 self.trigger_game_over(f"撞到 {ghost.type}") # 中文原因
                 break # 游戏结束，无需再检查其他鬼魂


    def check_corpse_merge(self):
         """检查蛇头是否与尸体的端点接触以触发融合。"""
         if not self.snake or not self.snake.alive: return
         head_pos = self.snake.get_head_position()
         corpse_to_remove_index = -1 # 标记要移除的尸体索引

         current_time = time.time() # 获取当前时间用于免疫检查

         # 遍历所有尸体
         for i, corpse in enumerate(self.corpses):
             # *** 分裂/融合 Bug 修复 ***
             # 检查尸体是否刚被创建（给予短暂的免疫时间）
             if current_time - corpse.creation_time < MERGE_IMMUNITY_SECONDS:
                  continue # 跳过对此新尸体的融合检查

             # 确保尸体段存在
             if not corpse.segments: continue

             # 获取尸体的两个端点
             first_seg, last_seg = corpse.get_end_points()

             # 检查蛇头是否碰到任一端点
             if head_pos == first_seg or head_pos == last_seg:
                 print("融合触发!") # 中文提示
                 corpse_to_remove_index = i # 记录要移除的尸体索引
                 merge_at_first = (head_pos == first_seg) # 判断是在哪一端触发的融合

                 # --- 执行融合逻辑 ---
                 if merge_at_first:
                      # 蛇头碰到尸体起点：新身体 = 蛇身 + 尸体段
                      new_body_list = list(self.snake.body) + list(corpse.segments)
                      # 新蛇头位置变为尸体的终点
                      # new_head_pos = last_seg # (这行不需要，由列表拼接自动完成)
                      # 计算新方向：从尸体倒数第二段指向最后一段
                      if len(corpse.segments) > 1:
                           p_last_x, p_last_y = corpse.segments[-2]
                           last_x, last_y = corpse.segments[-1]
                           new_direction = (last_x - p_last_x, last_y - p_last_y)
                      else: # 如果尸体只有一段，保持蛇原方向？
                          new_direction = self.snake.direction
                 else: # 蛇头碰到尸体终点：新身体 = 尸体段 + 蛇身
                       new_body_list = list(corpse.segments) + list(self.snake.body)
                       # 新蛇头位置变为尸体的起点
                       # new_head_pos = first_seg # (这行不需要)
                       # 计算新方向：从尸体第二段指向第一段 (注意方向！)
                       if len(corpse.segments) > 1:
                            first_x, first_y = corpse.segments[0]
                            sec_x, sec_y = corpse.segments[1]
                            new_direction = (first_x - sec_x, first_y - sec_y) # 指向第一段
                       else: # 如果尸体只有一段
                            new_direction = self.snake.direction

                 # --- 更新蛇的状态 ---
                 self.snake.body = deque(new_body_list) # 更新蛇身队列
                 self.snake.length = len(self.snake.body) # 更新长度
                 # 新蛇头已经是队列的最后一个元素
                 self.snake.direction = new_direction # 设置新的移动方向
                 self.snake.new_direction = new_direction # 同步缓冲方向
                 self.snake.update_head_image() # 更新蛇头图像以匹配新方向

                 # 播放融合音效和粒子效果
                 self.play_sound('merge')
                 self.add_particles(head_pos, 15, GREEN) # 在融合点添加绿色粒子

                 break # 每帧只处理一次融合

         # 如果发生了融合，移除被融合的尸体
         if corpse_to_remove_index != -1:
              if corpse_to_remove_index < len(self.corpses):
                   del self.corpses[corpse_to_remove_index]


    def add_particles(self, grid_pos, count, color):
         """在指定的格子位置生成粒子效果。"""
         # 计算粒子生成的中心像素坐标 (考虑画布偏移)
         pixel_pos = (grid_pos[0] * GRID_SIZE + GRID_SIZE // 2 + self.draw_offset_x,
                      grid_pos[1] * GRID_SIZE + GRID_SIZE // 2 + self.draw_offset_y)
         # 生成指定数量的粒子
         for _ in range(count):
              self.particles.append(Particle(self, pixel_pos, color)) # 添加到粒子列表


    def draw_grid(self, surface):
        """在活动画布区域绘制网格线。"""
        # 创建一个与画布大小相同、支持透明度的表面用于绘制网格
        grid_surface = pygame.Surface((CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX), pygame.SRCALPHA)
        grid_surface.fill((0,0,0,0)) # 填充透明背景

        # 绘制垂直线
        for col in range(CANVAS_GRID_WIDTH + 1):
            x = col * GRID_SIZE
            pygame.draw.line(grid_surface, GRID_COLOR, (x, 0), (x, CANVAS_HEIGHT_PX), 1) # 线宽为1
        # 绘制水平线
        for row in range(CANVAS_GRID_HEIGHT + 1):
            y = row * GRID_SIZE
            pygame.draw.line(grid_surface, GRID_COLOR, (0, y), (CANVAS_WIDTH_PX, y), 1)

        # 将绘制好的网格表面一次性blit到主屏幕的画布区域
        surface.blit(grid_surface, (self.draw_offset_x, self.draw_offset_y))

    def draw_background(self, surface):
         """在画布区域内绘制平铺的背景图。"""
         bg_image = self.images.get('background')
         # 获取画布区域的 Rect 对象
         canvas_rect = pygame.Rect(self.draw_offset_x, self.draw_offset_y, CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX)

         # 如果背景图无效，用纯色填充画布区域
         if not bg_image:
             pygame.draw.rect(surface, BLACK, canvas_rect)
             return

         bg_width = bg_image.get_width()
         bg_height = bg_image.get_height()

         # 确保背景图尺寸有效，防止除以零
         if bg_width <= 0 or bg_height <= 0:
             pygame.draw.rect(surface, BLACK, canvas_rect) # 尺寸无效也用纯色填充
             return

         # 创建画布区域的子表面，以便在其上平铺背景
         # 使用 try-except 块处理可能的子表面创建错误 (例如 Rect 无效)
         try:
             canvas_surface = surface.subsurface(canvas_rect)
             # 在子表面上平铺背景图
             for x in range(0, CANVAS_WIDTH_PX, bg_width):
                 for y in range(0, CANVAS_HEIGHT_PX, bg_height):
                     canvas_surface.blit(bg_image, (x, y))
         except ValueError as e:
              print(f"创建子表面失败: {e}. 使用纯色背景填充。")
              pygame.draw.rect(surface, BLACK, canvas_rect)


    def draw_ui(self, surface):
        """绘制用户界面元素（计时器、长度、提示等）。"""
        # UI元素绘制在主屏幕上，但位置可能相对于画布区域

        # 游戏计时器 (在画布左上角)
        mins, secs = divmod(int(self.game_timer), 60) # 计算分钟和秒
        timer_text = f"时长: {mins:01d}:{secs:02d}" # 中文标签
        timer_surf = self.font_small.render(timer_text, True, WHITE) # 渲染文本
        # 位置考虑画布偏移
        surface.blit(timer_surf, (10 + self.draw_offset_x, 10 + self.draw_offset_y))

        # 蛇的长度 (在画布右上角)
        length = self.snake.length if self.snake else 0 # 获取长度，处理蛇不存在的情况
        length_text = f"长度: {length}" # 中文标签
        length_surf = self.font_small.render(length_text, True, WHITE)
        # 位置相对于画布右上角
        length_rect = length_surf.get_rect(topright=(self.draw_offset_x + CANVAS_WIDTH_PX - 10, 10 + self.draw_offset_y))
        surface.blit(length_surf, length_rect)

        # 分裂按钮状态提示 (在画布左下角)
        split_available = self.snake.split_available if self.snake else False # 获取状态
        split_color = WHITE if split_available else GREY # 根据状态选择颜色
        split_text = "分裂[空格]" # 中文标签
        split_surf = self.font_small.render(split_text, True, split_color)
        # 位置相对于画布左下角
        split_rect = split_surf.get_rect(bottomleft=(10 + self.draw_offset_x, self.draw_offset_y + CANVAS_HEIGHT_PX - 10))
        surface.blit(split_surf, split_rect)

    def draw_game_over_screen(self, surface):
        """绘制游戏结束结算界面。"""
        # 绘制半透明黑色遮罩层，覆盖整个屏幕
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # 黑色，180/255 的透明度
        surface.blit(overlay, (0, 0))

        # 计算屏幕中心点
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2

        # 显示标题 "游戏结算" (中文)
        title_surf = self.font_large.render("游戏结算", True, RED)
        title_rect = title_surf.get_rect(center=(center_x, center_y - 150)) # 调整垂直位置
        surface.blit(title_surf, title_rect)

        # 显示最终长度
        score_length = self.snake.length if self.snake else 0 # 获取最终长度
        score_text = f"最终长度: {score_length}" # 中文
        score_surf = self.font_medium.render(score_text, True, WHITE)
        score_rect = score_surf.get_rect(center=(center_x, title_rect.bottom + 60)) # 在标题下方
        surface.blit(score_surf, score_rect)

        # --- 绘制按钮 ---
        button_width = 250
        button_height = 60
        button_spacing = 30
        base_y = score_rect.bottom + 80 # 按钮基准垂直位置

        # 重玩按钮 (绿色)
        self.replay_button_rect = pygame.Rect(0, 0, button_width, button_height)
        self.replay_button_rect.midtop = (center_x - button_width/2 - button_spacing/2, base_y) # 定位按钮
        pygame.draw.rect(surface, GREEN, self.replay_button_rect, border_radius=10) # 绘制圆角矩形
        replay_text_surf = self.font_medium.render("重玩 (R)", True, BLACK) # 中文标签
        replay_text_rect = replay_text_surf.get_rect(center=self.replay_button_rect.center) # 文本居中
        surface.blit(replay_text_surf, replay_text_rect)

        # 时光倒流按钮 (蓝色或灰色)
        rewind_button_color = BLUE if self.rewind_available else GREY # 根据是否可用选择颜色
        self.rewind_button_rect = pygame.Rect(0, 0, button_width, button_height)
        self.rewind_button_rect.midtop = (center_x + button_width/2 + button_spacing/2, base_y) # 定位按钮
        pygame.draw.rect(surface, rewind_button_color, self.rewind_button_rect, border_radius=10)
        rewind_text = "时光倒流 (T)" if self.rewind_available else "时光倒流 (已用)" # 中文标签
        rewind_text_surf = self.font_medium.render(rewind_text, True, BLACK)
        rewind_text_rect = rewind_text_surf.get_rect(center=self.rewind_button_rect.center)
        surface.blit(rewind_text_surf, rewind_text_rect)


    def check_game_over_button_clicks(self, mouse_pos):
         """检查鼠标点击是否在游戏结束界面的按钮上。"""
         # 使用屏幕坐标进行碰撞检测
         if hasattr(self, 'replay_button_rect') and self.replay_button_rect.collidepoint(mouse_pos):
             self.reset_game() # 点击重玩按钮
         elif hasattr(self, 'rewind_button_rect') and self.rewind_button_rect.collidepoint(mouse_pos) and self.rewind_available:
             self.attempt_rewind() # 点击时光倒流按钮 (如果可用)


    def draw(self):
        """绘制游戏的所有可见元素（主绘制循环）。"""
        # 1. 填充屏幕背景色 (防止画布外的区域闪烁)
        self.screen.fill(BLACK)

        # 2. 在画布区域绘制背景图
        self.draw_background(self.screen)

        # 3. 在画布区域绘制网格
        self.draw_grid(self.screen)

        # 4. 在画布区域绘制游戏对象 (果实、尸体、蛇、鬼魂)
        #    使用子表面可以确保绘制内容被限制在画布区域内
        try:
             canvas_surface = self.screen.subsurface(pygame.Rect(self.draw_offset_x, self.draw_offset_y, CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX))

             # 调用各对象的 draw 方法，将子表面传递给它们
             for fruit in self.fruits:
                 fruit.draw(canvas_surface) # 现在 draw 方法只接收 surface 参数
             for corpse in self.corpses:
                  corpse.draw(canvas_surface)
             if self.snake:
                 self.snake.draw(canvas_surface)
             for ghost in self.ghosts:
                 ghost.draw(canvas_surface)
        except ValueError as e:
            print(f"创建画布子表面失败，无法绘制游戏对象: {e}")


        # 5. 在主屏幕上绘制粒子效果 (粒子坐标是相对于主屏幕的)
        for particle in self.particles:
             particle.draw(self.screen) # 直接在主屏幕上绘制

        # 6. 绘制 UI 元素 (计时器、长度等，位置已考虑偏移)
        self.draw_ui(self.screen)

        # 7. 如果游戏结束，绘制结算界面 (覆盖在所有元素之上)
        if self.game_state == STATE_GAME_OVER:
            self.draw_game_over_screen(self.screen)

        # 8. 更新整个屏幕显示
        pygame.display.flip()


    def save_state_for_rewind(self):
        """保存当前游戏状态，用于可能的时光倒流。"""
        if not self.snake: return # 如果蛇不存在，不保存状态

        # 为了更准确地恢复计时果实和尸体，保存创建时的游戏计时器时间
        current_game_time = self.game_timer

        # 存储必要的状态信息
        state = {
            'time': current_game_time, # 保存当前游戏时间
            'snake_body': self.snake.body.copy(), # 复制蛇身队列
            'snake_length': self.snake.length,
            'snake_direction': self.snake.direction,
            'snake_new_direction': self.snake.new_direction,
            'snake_is_accelerating': self.snake.is_accelerating, # 保存加速状态
            # 保存果实信息 (位置, 类型名, 生命周期, 创建时的游戏时间)
            'fruits': [(f.position, f.type, f.lifespan,
                        f.creation_time - self.start_time) # 保存相对游戏开始的时间戳
                       for f in self.fruits],
            # 保存尸体信息 (段队列, 创建时的游戏时间)
            'corpses': [{'segments': c.segments.copy(),
                         'creation_game_time': c.creation_time - self.start_time} # 保存相对游戏开始的时间戳
                        for c in self.corpses],
            # 保存鬼魂信息 (位置, 像素位置, 类型名, 目标位置)
            'ghosts': [{'pos': g.grid_pos, 'pixel_pos': list(g.pixel_pos), 'type': g.type, 'target': g.target_grid_pos}
                       for g in self.ghosts],
            'pinky_spawned': self.pinky_spawned, # 保存 Pinky 生成状态
            'frenzy_active': self.frenzy_active, # 保存狂热状态
            'last_frenzy_start_time': self.last_frenzy_start_time, # 保存上次狂热开始的墙上时间
        }
        self.history.append(state) # 添加到历史记录队列


    def attempt_rewind(self):
         """尝试执行时光倒流操作。"""
         if not self.rewind_available:
             print("时光倒流不可用.") # 中文提示
             return
         if not self.history:
              print("没有历史记录可供倒流.") # 中文提示
              return

         print("尝试时光倒流...") # 中文提示
         try:
             # 计算目标回溯到的游戏时间点
             target_game_time = self.game_timer - REWIND_SECONDS
             best_snapshot = None

             # 从最近的快照开始向前查找，找到第一个时间点小于等于目标时间的快照
             for snapshot in reversed(self.history):
                 if snapshot['time'] <= target_game_time:
                     best_snapshot = snapshot
                     break # 找到了最接近且不晚于目标时间的快照

             # 如果所有快照都比目标时间晚（例如游戏刚开始不久），则回溯到最早的快照
             if not best_snapshot and self.history:
                 best_snapshot = self.history[0]
                 print("历史记录不足，回溯到最早状态。") # 中文提示

             # 如果找到了合适的快照
             if best_snapshot:
                  self.restore_state_from_rewind(best_snapshot) # 恢复状态
                  self.rewind_available = False # 标记时光倒流已使用
                  self.play_sound('rewind') # 播放音效
                  self.history.clear() # 清空历史记录 (时光倒流后不能再倒流)
                  self.frames_since_last_snapshot = 0 # 重置快照计数
                  print("时光倒流成功!") # 中文提示
             else:
                  # 这种情况理论上不应该发生，因为如果 history 非空，总能找到一个 best_snapshot
                  print("在历史记录中找不到合适的回溯点.") # 中文提示

         except Exception as e:
              print(f"时光倒流时发生错误: {e}") # 中文提示
              # 可以考虑添加更详细的错误处理或日志记录


    def restore_state_from_rewind(self, state):
        """根据保存的状态快照恢复游戏。"""
        restored_game_time = state['time'] # 获取快照记录的游戏时间
        print(f"恢复到游戏时间: {restored_game_time:.2f} 秒")

        # 调整游戏开始时间，使当前 game_timer 与恢复的时间匹配
        self.start_time = time.time() - restored_game_time
        self.game_timer = restored_game_time # 直接设置游戏计时器

        # 停止可能正在播放的循环音效
        if self.speedup_channel: self.speedup_channel.stop()

        # --- 恢复蛇的状态 ---
        if not self.snake: self.snake = Snake(self) # 如果蛇不存在，重新创建
        self.snake.body = state['snake_body'].copy()
        self.snake.length = state['snake_length']
        self.snake.direction = state['snake_direction']
        self.snake.new_direction = state['snake_new_direction']
        self.snake.alive = True # 关键：让蛇复活
        self.snake.is_accelerating = state['snake_is_accelerating'] # 恢复加速状态
        self.snake.update_head_image() # 更新蛇头方向

        # --- 恢复果实的状态 ---
        self.fruits.clear()
        for pos, f_type_name, lifespan, creation_game_time in state['fruits']:
             img_name = f'fruit_{f_type_name}.png' # 重构图像文件名
             # 检查果实是否在恢复的时间点仍然有效
             should_exist = True
             if lifespan is not None:
                  # 如果 (恢复的游戏时间 - 果实创建的游戏时间) > 生命周期，则已过期
                  if restored_game_time - creation_game_time > lifespan:
                       should_exist = False

             if should_exist:
                 # 创建果实对象
                 restored_fruit = Fruit(self, pos, f_type_name, img_name, lifespan)
                 # 设置其创建时间 (相对于调整后的 start_time)
                 restored_fruit.creation_time = self.start_time + creation_game_time
                 self.fruits.append(restored_fruit)

        # --- 恢复尸体的状态 ---
        self.corpses.clear()
        for c_data in state['corpses']:
             creation_game_time = c_data['creation_game_time']
             # 检查尸体在恢复的时间点是否仍然有效
             corpse_age = restored_game_time - creation_game_time
             if corpse_age < CORPSE_LIFESPAN_SECONDS: # 检查总生命周期
                 # 创建尸体对象
                 restored_corpse = Corpse(self, c_data['segments'].copy())
                 # 恢复其原始创建时间 (相对于调整后的 start_time)
                 restored_corpse.creation_time = self.start_time + creation_game_time
                 # 重新计算闪烁和淡出时间点
                 restored_corpse.flicker_start_time = restored_corpse.creation_time + CORPSE_FLICKER_START_OFFSET
                 restored_corpse.flicker_end_time = restored_corpse.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS
                 restored_corpse.fade_start_time = restored_corpse.flicker_end_time
                 restored_corpse.fade_end_time = restored_corpse.fade_start_time + CORPSE_FADE_DURATION_SECONDS
                 # 再次确认，根据当前墙上时间，它是否真的还没消失
                 if time.time() < restored_corpse.fade_end_time:
                     self.corpses.append(restored_corpse)


        # --- 恢复鬼魂的状态 ---
        self.ghosts.clear()
        self.pinky_spawned = state['pinky_spawned'] # 恢复 Pinky 生成状态
        for g_data in state['ghosts']:
            ghost = None # 初始化鬼魂变量
            # 根据类型重新创建鬼魂对象
            if g_data['type'] == 'Blinky':
                ghost = Blinky(self)
            elif g_data['type'] == 'Pinky':
                 ghost = Pinky(self)

            if ghost: # 如果成功创建
                ghost.grid_pos = g_data['pos'] # 恢复格子位置
                ghost.pixel_pos = list(g_data['pixel_pos']) # 恢复像素位置
                ghost.target_grid_pos = g_data['target'] # 恢复目标位置
                ghost.last_target_update = 0 # 重置目标更新计时器，强制下次更新
                self.ghosts.append(ghost) # 添加到列表

        # --- 恢复狂热状态 ---
        self.frenzy_active = state['frenzy_active']
        self.last_frenzy_start_time = state['last_frenzy_start_time'] # 恢复上次开始的墙上时间

        # --- 重置依赖当前时间的计时器 ---
        self.last_move_time = time.time() # 防止恢复后立即移动
        # 重置果实生成计时器，避免恢复后立即生成大量果实
        self.last_fruit_spawn_time = time.time()
        # 重置逐渐加热计时器？可以考虑也恢复，或者重置
        self.last_gradual_heat_time = time.time() # 简单重置

        # 如果恢复时蛇处于加速状态，重新播放加速音效
        if self.snake.is_accelerating and self.speedup_channel and self.sounds['speedup']:
            self.speedup_channel.play(self.sounds['speedup'], loops=-1)

        # --- 设置游戏状态为进行中 ---
        self.game_state = STATE_PLAYING


    def run(self):
        """游戏主循环。"""
        try: # 使用 try...finally 确保 pygame.quit() 被调用
            self.reset_game() # 初始化游戏

            while self.is_running:
                # 计算自上一帧以来的时间差 (秒)
                dt = self.clock.tick(FPS) / 1000.0
                # 限制 dt 的最大值，防止游戏卡顿时导致物体瞬间移动过远
                dt = min(dt, 0.1) # 例如，最大允许 100ms 的时间差

                # 处理输入
                self.handle_input()

                # 更新游戏逻辑 (仅在游戏进行中状态下)
                if self.game_state == STATE_PLAYING:
                    self.update(dt)

                # 绘制游戏画面 (所有状态下都需要绘制)
                self.draw()

        finally: # 无论如何退出循环，都执行清理操作
            # 停止所有音效和音乐
            print("游戏退出，停止音频...")
            pygame.mixer.music.stop()
            pygame.mixer.stop() # 停止所有频道的声音

            # 卸载 Pygame 模块
            print("卸载 Pygame...")
            pygame.quit()
            print("Pygame 已卸载。")
            # 退出 Python 程序
            # sys.exit() # 通常不需要显式调用 sys.exit()，程序结束即可