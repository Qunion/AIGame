import pygame
import sys
import time
import random
from collections import deque
from settings import * # 导入设置
from sprites import Snake, Fruit, Corpse, Blinky, Pinky, Particle # 导入精灵类

snake_body_without_head2 = None

class Game:
    def __init__(self):
        pygame.init()
        # --- 修正：为加速音效预留通道 ---
        pygame.mixer.set_reserved(1) # 预留通道 0
        # ------------------------------
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font_small = get_font(24)
        self.font_large = get_font(64)
        self.font_medium = get_font(36)
        self.is_running = True
        self.game_state = STATE_PLAYING
        self.last_game_over_reason = ""
        self.rewind_available = True

        try: pygame.key.stop_text_input()
        except: pass # 忽略可能的错误

        self.load_assets()

        self.start_time = time.time()
        self.game_timer = 0
        self.last_move_time = 0
        self.last_fruit_spawn_time = 0
        self.last_gradual_heat_time = 0
        self.last_frenzy_start_time = -FRENZY_INTERVAL_SECONDS
        self.frenzy_active = False
        self.pinky_spawned = False

        self.history = deque(maxlen=int(REWIND_SECONDS * FPS * 0.5))
        self.frames_since_last_snapshot = 0

        self.ghost_warning_playing = False
        self.last_ghost_warning_time = 0
        # --- 修正：获取预留的通道 ---
        self.speedup_channel = pygame.mixer.Channel(0) # 获取预留的通道 0
        if not self.speedup_channel:
             print("严重错误：无法获取预留的音频通道 0！加速音效将无法播放。")
        # -------------------------

        self.all_sprites = pygame.sprite.Group()
        self.snake = None
        self.fruits = []
        self.corpses = []
        self.ghosts = []
        self.particles = []

        self.draw_offset_x = (SCREEN_WIDTH - CANVAS_WIDTH_PX) // 2
        self.draw_offset_y = (SCREEN_HEIGHT - CANVAS_HEIGHT_PX) // 2
        # snake_body_list2 = list(self.snake.body)


    def load_assets(self):
        """加载游戏所需的图像和声音资源。"""
        self.images = {
            # 背景图加载时不指定 size，由 load_image 决定不缩放
            'background': load_image('background.png', use_alpha=False),
        }
        self.sounds = {
            'pickup_normal': load_sound('pickup_normal.wav'),
            'pickup_healthy': load_sound('pickup_healthy.wav'),
            'pickup_bomb': load_sound('pickup_bomb.wav'),
            'split': load_sound('split.wav'),
            'merge': load_sound('merge.wav'),
            'death': load_sound('death.wav'),
            'rewind': load_sound('rewind.wav'),
            'ghost_warning': load_sound('ghost_warning.wav'),
            # 在 Game.load_assets 方法内的 self.sounds 字典中添加
            'pickup_super': load_sound('pickup_super.wav'), # 加载新音效
            'speedup': load_sound('speedup.wav')

        }
        # 检查加速音效是否加载成功
        if not self.sounds['speedup']:
            print("警告：未能加载 speedup.wav 文件。加速音效将不可用。")

        # 加载并播放背景音乐
        if load_music('bgm.ogg'):
            pygame.mixer.music.play(loops=-1)
            pygame.mixer.music.set_volume(0.3)
        else:
            print("警告：未能加载背景音乐 bgm.ogg。")

    # ... (play_sound, try_play_sound, reset_game, get_current_speed, check_frenzy_state, spawn_fruit, trigger_game_over 方法保持不变) ...
    def play_sound(self, sound_name):
        """播放指定名称的音效。"""
        sound = self.sounds.get(sound_name)
        if sound:
            # 尝试在非预留通道上播放短音效
            ch = pygame.mixer.find_channel() # 查找一个非预留的空闲通道
            if ch:
                ch.play(sound)
            else:
                # 如果找不到非预留通道，就不播放？或者在任意频道播放？
                # 决定：在任意频道播放，可能会覆盖，但总比不响好
                sound.play()
                # print(f"警告：没有空闲的非预留通道，在任意频道播放 {sound_name}")

    def try_play_sound(self, sound_name, unique=False, cooldown=1000):
        """尝试播放音效，可选地确保它不会过于频繁地播放。"""
        sound = self.sounds.get(sound_name)
        if sound:
            now = pygame.time.get_ticks()
            if unique:
                 if sound_name == 'ghost_warning':
                     if not self.ghost_warning_playing or now - self.last_ghost_warning_time > cooldown:
                         ch = pygame.mixer.find_channel() # 优先非预留通道
                         if ch: ch.play(sound)
                         else: sound.play()
                         self.ghost_warning_playing = True
                         self.last_ghost_warning_time = now
                 # 在这里可以为其他unique声音添加逻辑
            else:
                 ch = pygame.mixer.find_channel()
                 if ch: ch.play(sound)
                 else: sound.play()

            # 重置警告标志
            if self.ghost_warning_playing and now - self.last_ghost_warning_time > cooldown * 2:
                 self.ghost_warning_playing = False


    def reset_game(self):
        """重置游戏状态到初始设置，开始新的一局。"""
        print("重置游戏中...")
        # 确保停止预留通道的声音
        if self.speedup_channel:
            self.speedup_channel.stop()

        # 清理工作... (省略重复代码)
        self.all_sprites.empty()
        self.fruits.clear()
        self.corpses.clear()
        self.ghosts.clear()
        self.particles.clear()
        self.history.clear()

        self.snake = Snake(self)
        
        # --- 修改：使用新的初始果实数量设置 ---
        # 确保初始数量至少为 1，并且如果数量大于等于2，强制生成一个特殊果实
        initial_count = max(1, INITIAL_FRUIT_COUNT) # 保证至少有1个
        force_special_on_init = initial_count >= 2 # 如果初始数量大于等于2，则强制特殊
        self.spawn_fruit(count=initial_count, force_special=force_special_on_init)
        # ------------------------------------

        self.ghosts.append(Blinky(self))

        # 重置状态... (省略重复代码)
        self.start_time = time.time()
        self.game_timer = 0
        self.last_move_time = 0
        self.last_fruit_spawn_time = time.time()
        self.last_gradual_heat_time = time.time()
        self.last_frenzy_start_time = time.time() # 重置狂热计时器
        self.frenzy_active = False
        self.pinky_spawned = False
        self.rewind_available = True
        self.last_game_over_reason = ""
        self.frames_since_last_snapshot = 0
        self.ghost_warning_playing = False
        if self.snake: self.snake.is_accelerating = False

        self.game_state = STATE_PLAYING
        print("游戏重置完成.")


    def get_current_speed(self):
        """计算蛇当前的移动速度（格子/秒）。"""
        current_speed = BASE_SNAKE_SPEED_PPS
        time_elapsed = self.game_timer
        heat_intervals = time_elapsed // GRADUAL_HEAT_INTERVAL_SECONDS
        heat_bonus_multiplier = 1.0 + (GRADUAL_HEAT_INCREASE_PERCENT * heat_intervals)
        current_speed *= heat_bonus_multiplier

        frenzy_bonus_multiplier = 1.0
        if self.frenzy_active:
            time_since_frenzy_start = time.time() - self.last_frenzy_start_time
            if time_since_frenzy_start < FRENZY_RAMP_UP_SECONDS:
                progress = time_since_frenzy_start / FRENZY_RAMP_UP_SECONDS
                frenzy_bonus_multiplier = 1.0 + FRENZY_PEAK_BONUS_PERCENT * progress
            elif time_since_frenzy_start < FRENZY_DURATION_SECONDS - FRENZY_RAMP_DOWN_SECONDS:
                frenzy_bonus_multiplier = 1.0 + FRENZY_PEAK_BONUS_PERCENT
            elif time_since_frenzy_start < FRENZY_DURATION_SECONDS:
                 time_left_in_ramp_down = FRENZY_DURATION_SECONDS - time_since_frenzy_start
                 # 确保 FRENZY_RAMP_DOWN_SECONDS 不为零
                 ramp_down_duration = FRENZY_RAMP_DOWN_SECONDS if FRENZY_RAMP_DOWN_SECONDS > 0 else 1
                 progress = max(0, time_left_in_ramp_down / ramp_down_duration) # 保证 progress 不小于 0
                 frenzy_bonus_multiplier = 1.0 + FRENZY_PEAK_BONUS_PERCENT * progress
            # 狂热结束由 check_frenzy_state 处理状态切换

        current_speed *= frenzy_bonus_multiplier

        if self.snake and self.snake.is_accelerating:
             current_speed *= ACCELERATION_FACTOR

        return max(0.1, current_speed) # 限制最小速度


    def check_frenzy_state(self):
        """检查并更新狂热状态。"""
        now = time.time()
        if not self.frenzy_active and (now - self.last_frenzy_start_time >= FRENZY_INTERVAL_SECONDS):
             self.frenzy_active = True
             self.last_frenzy_start_time = now
             print("狂热时刻开始!")
        elif self.frenzy_active and (now - self.last_frenzy_start_time >= FRENZY_DURATION_SECONDS):
             self.frenzy_active = False
             print("狂热时刻结束!")

        # 在 Game 类中
    def spawn_fruit(self, count=1, force_special=False):
        """在画布上生成指定数量的果实，加入超级增长果实。"""
        spawned_count = 0
        attempts = 0
        max_attempts = CANVAS_GRID_WIDTH * CANVAS_GRID_HEIGHT

        current_occupancies = set()
        if self.snake: current_occupancies.update(self.snake.body)
        current_occupancies.update(f.position for f in self.fruits)
        current_occupancies.update(g.grid_pos for g in self.ghosts)
        for c in self.corpses: current_occupancies.update(c.segments)

        while spawned_count < count and len(self.fruits) < MAX_FRUITS and attempts < max_attempts:
            attempts += 1
            pos = (random.randint(0, CANVAS_GRID_WIDTH - 1),
                   random.randint(0, CANVAS_GRID_HEIGHT - 1))

            if pos not in current_occupancies:
                fruit_type = 'normal'
                lifespan = None
                img_name = 'fruit_normal.png'
                pickup_sound = 'pickup_normal' # 默认普通音效

                is_special = False
                if force_special and spawned_count == 0: is_special = True
                elif random.random() < SPECIAL_FRUIT_OVERALL_CHANCE: # --- 可以微调生成特殊果实的整体概率 ---
                    is_special = True

                if is_special:
                    # --- 修改：在特殊果实中选择类型 ---
                    rand_num = random.random() # 生成一个 0到1 的随机数
                    if rand_num < SUPER_GROWTH_FRUIT_SPAWN_CHANCE: # 按概率生成超级增长果实
                        fruit_type = 'super_growth'
                        lifespan = SUPER_GROWTH_FRUIT_DURATION_SECONDS
                        img_name = FRUIT_SUPER_GROWTH_IMG # 使用 settings.py 中定义的文件名
                        pickup_sound = 'pickup_super' # 假设有这个音效
                        print(f"生成了 超级增长 果实于 {pos}") # 调试信息
                    elif rand_num < SUPER_GROWTH_FRUIT_SPAWN_CHANCE + HEALTHY_FRUIT_SPAWN_CHANCE: # 超级果实+健康果实的区间
                        fruit_type = 'healthy'
                        lifespan = HEALTHY_FRUIT_DURATION_SECONDS
                        img_name = 'fruit_healthy.png'
                        pickup_sound = 'pickup_healthy'
                    else: # 剩余概率生成炸弹
                         fruit_type = 'bomb'
                         lifespan = BOMB_FRUIT_DURATION_SECONDS
                         img_name = 'fruit_bomb.png'
                         pickup_sound = 'pickup_bomb' # 炸弹音效在碰撞时处理
                    # --- 修改结束 ---

                # 创建果实对象
                new_fruit = Fruit(self, pos, fruit_type, img_name, lifespan)
                self.fruits.append(new_fruit)
                current_occupancies.add(pos)
                spawned_count += 1

    def trigger_game_over(self, reason="未知原因"):
         """触发游戏结束状态。"""
         if self.game_state != STATE_GAME_OVER:
             print(f"游戏结束! 原因: {reason}")
             self.last_game_over_reason = reason
             self.game_state = STATE_GAME_OVER
             if self.snake:
                 self.snake.alive = False
                 self.snake.is_accelerating = False
             # 停止加速音效
             if self.speedup_channel:
                 self.speedup_channel.stop() # <--- 确保停止

             if reason == "炸弹果实":
                  self.play_sound('pickup_bomb')
             else:
                  self.play_sound('death')


    def handle_input(self):
        """处理玩家的输入事件。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.is_running = False
            if event.type == pygame.KEYDOWN:
                if self.game_state == STATE_PLAYING and self.snake:
                    if event.key == pygame.K_UP or event.key == pygame.K_w: self.snake.change_direction(UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s: self.snake.change_direction(DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a: self.snake.change_direction(LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d: self.snake.change_direction(RIGHT)
                    # --- 修正：加速音效处理 ---
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        if not self.snake.is_accelerating:
                            self.snake.is_accelerating = True
                            # 检查通道和音效是否存在
                            if self.speedup_channel and self.sounds['speedup']:
                                try:
                                    # print("播放加速音效...") # 调试信息
                                    self.speedup_channel.play(self.sounds['speedup'], loops=-1)
                                except pygame.error as e:
                                     print(f"播放加速音效失败: {e}") # 打印错误
                            elif not self.sounds['speedup']:
                                 print("加速音效未加载。")
                            elif not self.speedup_channel:
                                 print("加速音频通道无效。")
                    # -------------------------
                    elif event.key == pygame.K_SPACE:
                        if self.snake.split_available:
                            new_corpse, success = self.snake.split()
                            if success: self.corpses.append(new_corpse)
                    elif event.key == pygame.K_ESCAPE: self.is_running = False
                elif self.game_state == STATE_GAME_OVER:
                    if event.key == pygame.K_r: self.reset_game()
                    if event.key == pygame.K_t and self.rewind_available: self.attempt_rewind()
            if event.type == pygame.KEYUP:
                 if self.game_state == STATE_PLAYING and self.snake:
                     # --- 修正：停止加速音效 ---
                     if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                         if self.snake.is_accelerating: # 仅当之前在加速时才停止
                             self.snake.is_accelerating = False
                             if self.speedup_channel:
                                #  print("停止加速音效...") # 调试信息
                                 self.speedup_channel.stop()
                     # -------------------------
            if event.type == pygame.MOUSEBUTTONDOWN:
                 if self.game_state == STATE_GAME_OVER:
                      self.check_game_over_button_clicks(event.pos)

    # ... (update, check_fruit_collisions, check_ghost_collisions, check_corpse_merge, add_particles 方法保持不变) ...
    def update(self, dt):
        """更新游戏逻辑状态（每帧调用）。"""
        if self.game_state != STATE_PLAYING:
            self.particles[:] = [p for p in self.particles if p.update(dt)]
            return

        self.game_timer = time.time() - self.start_time
        self.check_frenzy_state()

        # 蛇移动
        speed = self.get_current_speed()
        move_interval = 1.0 / speed if speed > 0 else float('inf') # 防止除零
        current_time = time.time()
        moved_this_frame = False
        if current_time - self.last_move_time >= move_interval:
             if self.snake:
                 snake_body_list2 = list(self.snake.body)
                 global snake_body_without_head2
                 snake_body_without_head2 = snake_body_list2[:1]
                 self.snake.update()
                 self.last_move_time = current_time
                 moved_this_frame = True

        # 碰撞检测
        if moved_this_frame and self.snake and self.snake.alive:
             self.check_fruit_collisions()
             self.check_corpse_merge()
             self.check_ghost_collisions()

        # Pinky 生成
        if not self.pinky_spawned and self.snake and self.snake.length >= PINKY_SPAWN_LENGTH:
            self.ghosts.append(Pinky(self))
            self.pinky_spawned = True
            print("Pinky 已生成!")

        # 更新其他元素
        snake_body_for_ghosts = self.snake.body if self.snake else deque()
        for ghost in self.ghosts: ghost.update(dt, snake_body_for_ghosts)
        self.fruits[:] = [f for f in self.fruits if f.update()]
        self.corpses[:] = [c for c in self.corpses if c.update()]
        self.particles[:] = [p for p in self.particles if p.update(dt)]

        # 果实生成
        now = time.time()
        if now - self.last_fruit_spawn_time > FRUIT_SPAWN_INTERVAL_SECONDS:
            self.spawn_fruit()
            self.last_fruit_spawn_time = now
        if len(self.fruits) == 0:
            self.spawn_fruit(count=2, force_special=True)
            self.last_fruit_spawn_time = now

        # 时光倒流快照
        self.frames_since_last_snapshot += 1
        snapshot_interval_frames = int(FPS / 4) # 快照频率调整为每秒4次
        if self.frames_since_last_snapshot >= snapshot_interval_frames:
            self.save_state_for_rewind()
            self.frames_since_last_snapshot = 0

        # 在 Game 类中
    def check_fruit_collisions(self):
        """检查蛇头是否与果实发生碰撞，加入超级增长果实的处理。"""
        if not self.snake or not self.snake.alive: return
        head_pos = self.snake.get_head_position()
        eaten_fruit_index = -1

        for i, fruit in enumerate(self.fruits):
            if fruit.position == head_pos:
                eaten_fruit_index = i
                # --- 修改：增加新果实类型的处理 ---
                if fruit.type == 'normal':
                    self.snake.grow(1)
                    self.play_sound('pickup_normal')
                elif fruit.type == 'healthy':
                    self.snake.grow(2)
                    self.play_sound('pickup_healthy')
                elif fruit.type == 'super_growth': # <--- 新增类型判断
                    self.snake.grow(SUPER_GROWTH_FRUIT_LENGTH_BONUS) # 使用 settings 中的参数
                    self.play_sound('pickup_super') # 播放新音效 (如果已添加)
                elif fruit.type == 'bomb':
                     self.trigger_game_over("炸弹果实") # 游戏结束
                # --- 修改结束 ---
                break # 每步只吃一个

        if eaten_fruit_index != -1 and eaten_fruit_index < len(self.fruits):
            del self.fruits[eaten_fruit_index]

# ===============================================
    # ======= 修正后的 check_ghost_collisions =======
    # ===============================================
    def check_ghost_collisions(self):
        """检查蛇的任何部分（头或身体）是否与鬼魂发生碰撞。"""
        if not self.snake or not self.snake.alive: return # 如果蛇不存在或死亡，则不检查

        # 使用集合进行更高效的查找（如果蛇很长）
        snake_segments_set = set(self.snake.body)

        # 遍历每一个鬼魂
        for ghost in self.ghosts:
            # 检查鬼魂的当前格子位置是否存在于蛇的身体段集合中
            if ghost.grid_pos in snake_segments_set:
                 # 触发游戏结束，原因包含鬼魂类型
                 self.trigger_game_over(f"撞到 {ghost.type}")
                 # 只需要检测到一次碰撞即可结束游戏，立即返回
                 return
    # ===============================================
    # ===============================================

    # 在 Game 类中找到 check_corpse_merge 方法
    def check_corpse_merge(self):
         """检查蛇头是否与尸体的端点接触以触发融合。修正头部重置和方向逻辑，并修复 deque 切片错误。"""
         if not self.snake or not self.snake.alive: return
         head_pos = self.snake.get_head_position()
         corpse_to_remove_index = -1
         current_time = time.time()

         for i, corpse in enumerate(self.corpses):
             # 免疫时间检查
             if current_time - corpse.creation_time < MERGE_IMMUNITY_SECONDS: continue
             if not corpse.segments: continue

             first_seg, last_seg = corpse.get_end_points()
             if first_seg is None: continue # 无效尸体

             # --- 1. 判断接触点和非接触点 ---
             contact_point = None
             non_contact_end = None
             merge_at_first = False
            #  snake_body_Final_Tail = None
             

             if head_pos == first_seg:
                 contact_point = first_seg
                 non_contact_end = last_seg
                 merge_at_first = True
                 print(f"融合触发! 蛇头 {head_pos} 接触尸体首段 {contact_point}")
             elif head_pos == last_seg:
                 contact_point = last_seg
                 non_contact_end = first_seg
                 merge_at_first = False
                 print(f"融合触发! 蛇头 {head_pos} 接触尸体末段 {contact_point}")

             # --- 2. 如果触发了融合 ---
             if contact_point is not None:
                 corpse_to_remove_index = i

                 # --- 3. 拼接身体，确保非接触端是新头 ---
                 new_body_list = []
                 original_corpse_list = list(corpse.segments)

                 # -------->>>  修改点 1 开始 <<<-----------
                 # 先将 deque 转换为 list，再进行切片
                 snake_body_list = list(self.snake.body)
                 snake_body_list2 = list(self.snake.body)
                 
                #  self.body.appendleft((segment_x, segment_y))
                

                #  snake_body_Final_Tail = []
                # #  snake_body_Final_Tail2 = list(deque())[-1] 
                #  snake_body_Final_Tail = [[snake_body_list2[-1]]]
                #  snake_segments_set = set(tuple(segment) for segment in snake_body_Final_Tail)
                #  corpse_segments2 = deque(list(self.snake.body)[-1]) 


                #  print("测试它是个啥！！！：：："+str(snake_body_Final_Tail[0]))
                 
                #  print("测试它是个啥！！！：：："+{corpse_segments2})

                #  print("snake_body_Final_Tail")
                 snake_body_without_head = snake_body_list[:-1] if snake_body_list else []
                 # -------->>>  修改点 1 结束 <<<-----------
                 snake_body_without_head3 = snake_body_list[:1]
                 print(f"测测他是啥{snake_body_without_head2}")


                 if merge_at_first: # 蛇头接触尸体首段
                     # -------->>>  修改点 2 开始 <<<-----------
                     # 使用转换后的列表进行拼接
                     new_body_list = snake_body_without_head + original_corpse_list
                    #  new_body_list = snake_body_without_head + original_corpse_list+ snake_body_Final_Tail
                     # -------->>>  修改点 2 结束 <<<-----------
                     print(f"融合方式：蛇头接触首段。拼接前蛇身: {snake_body_without_head}, 尸体: {original_corpse_list}, 尾巴: {snake_body_without_head2}")
                 else: # 蛇头接触尸体末段
                     original_corpse_list.reverse() # 反转尸体段
                     # -------->>>  修改点 3 开始 <<<-----------
                     # 使用转换后的列表进行拼接
                     new_body_list = snake_body_without_head + original_corpse_list
                    #  new_body_list = snake_body_without_head + original_corpse_list+ snake_body_Final_Tail
                     # -------->>>  修改点 3 结束 <<<-----------
                     print(f"融合方式：蛇头接触末段。拼接前蛇身: {snake_body_without_head}, 反转后尸体: {original_corpse_list}, 尾巴: {snake_body_without_head2}")

                 # 安全检查
                 if not new_body_list:
                      print("错误：融合后身体列表为空！")
                      continue

                 # --- 4. 计算新方向 ---
                 new_direction = None
                 # 方向计算基于 original_corpse_list (如果接触末段，它已经被反转)
                 # 确保 non_contact_end 是有效的
                 if non_contact_end and len(original_corpse_list) > 1:
                     # 方向: 倒数第二段 -> 非接触端 (即新头)
                     prev_to_non_contact = original_corpse_list[-2]
                     new_direction = (non_contact_end[0] - prev_to_non_contact[0],
                                      non_contact_end[1] - prev_to_non_contact[1])
                     print(f"计算新方向: 从 {prev_to_non_contact} -> {non_contact_end} = {new_direction}")
                 # else: (如果无法计算，则使用备用逻辑)
                
                
                #  补上丢失的一格！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
                 new_body_list = snake_body_without_head2 + new_body_list
                 print(f"再次融合！：{new_body_list} ，尾巴: {snake_body_without_head2}")

                #  if merge_at_first: # 蛇头接触尸体首段
                #     new_body_list = snake_body_without_head2 + new_body_list
                #     print(f"再次融合！：{new_body_list} ，尾巴: {snake_body_without_head2}")
                #  else:
                #     new_body_list = snake_body_without_head2 + new_body_list
                #     # new_body_list = new_body_list + snake_body_without_head2
                #     print(f"再次融合！：{new_body_list} ，尾巴: {snake_body_without_head2}")


                 if new_direction is None or new_direction == (0,0):
                      print(f"警告：无法根据尸体计算有效方向，保持融合前方向 {self.snake.last_move_direction}")
                      new_direction = self.snake.last_move_direction
                      if new_direction == (0,0): new_direction = random.choice([UP, DOWN, LEFT, RIGHT])


                 # --- 5. 强制更新蛇的状态 ---
                 self.snake.body = deque(new_body_list)
                 self.snake.length = len(self.snake.body)
                 self.snake.direction = new_direction
                 self.snake.new_direction = new_direction
                 self.snake.last_move_direction = new_direction
                 self.snake.update_head_image()

                 print(f"融合后蛇身: {list(self.snake.body)}")
                 print(f"融合后头部应为: {non_contact_end}")
                 print(f"融合后最终方向: D={self.snake.direction}, NewD={self.snake.new_direction}, LastMoveD={self.snake.last_move_direction}")

                 # 播放效果
                 self.play_sound('merge')
                 self.add_particles(contact_point, 15, GREEN)

                 break # 处理完一次融合即退出循环

         # 移除被融合的尸体
         if corpse_to_remove_index != -1:
              if corpse_to_remove_index < len(self.corpses):
                   del self.corpses[corpse_to_remove_index]

    def add_particles(self, grid_pos, count, color):
         """在指定的格子位置生成粒子效果。"""
         pixel_pos = (grid_pos[0] * GRID_SIZE + GRID_SIZE // 2 + self.draw_offset_x,
                      grid_pos[1] * GRID_SIZE + GRID_SIZE // 2 + self.draw_offset_y)
         for _ in range(count):
              self.particles.append(Particle(self, pixel_pos, color))


    # --- 修正：背景图绘制逻辑 ---
    def draw_background(self, surface):
         """在画布区域内绘制（可能是平铺的）背景图。"""
         bg_image = self.images.get('background')
         canvas_rect = pygame.Rect(self.draw_offset_x, self.draw_offset_y, CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX)

         if not bg_image:
             pygame.draw.rect(surface, BLACK, canvas_rect)
             return

         bg_width = bg_image.get_width()
         bg_height = bg_image.get_height()

         if bg_width <= 0 or bg_height <= 0:
             pygame.draw.rect(surface, BLACK, canvas_rect)
             return

         # 直接在主 surface 的画布区域绘制背景
         # 如果背景图小于画布，则平铺；如果大于等于画布，则只绘制左上角部分
         try:
             # 平铺逻辑
             for x in range(self.draw_offset_x, self.draw_offset_x + CANVAS_WIDTH_PX, bg_width):
                 for y in range(self.draw_offset_y, self.draw_offset_y + CANVAS_HEIGHT_PX, bg_height):
                     # 计算绘制区域，确保不超出画布边界
                     draw_area = pygame.Rect(x, y, bg_width, bg_height)
                     # clip_rect 用于从 bg_image 中取出需要绘制的部分
                     clip_rect = pygame.Rect(0, 0,
                                             min(bg_width, self.draw_offset_x + CANVAS_WIDTH_PX - x),
                                             min(bg_height, self.draw_offset_y + CANVAS_HEIGHT_PX - y))
                     # 确保 clip_rect 的宽高有效
                     if clip_rect.width > 0 and clip_rect.height > 0:
                          surface.blit(bg_image, draw_area.topleft, clip_rect)

         except Exception as e:
              print(f"绘制背景时出错: {e}")
              pygame.draw.rect(surface, BLACK, canvas_rect) # 出错时填充黑色
    # --- 背景绘制修正结束 ---

    # ... (draw_grid, draw_ui, draw_game_over_screen, check_game_over_button_clicks, draw 方法主体保持不变) ...
    def draw_grid(self, surface):
        """在活动画布区域绘制网格线。"""
        grid_surface = pygame.Surface((CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX), pygame.SRCALPHA)
        grid_surface.fill((0,0,0,0))
        for col in range(CANVAS_GRID_WIDTH + 1):
            x = col * GRID_SIZE
            pygame.draw.line(grid_surface, GRID_COLOR, (x, 0), (x, CANVAS_HEIGHT_PX), 1)
        for row in range(CANVAS_GRID_HEIGHT + 1):
            y = row * GRID_SIZE
            pygame.draw.line(grid_surface, GRID_COLOR, (0, y), (CANVAS_WIDTH_PX, y), 1)
        surface.blit(grid_surface, (self.draw_offset_x, self.draw_offset_y))

    def draw_ui(self, surface):
        """绘制用户界面元素。"""
        # --- 获取字体 ---
        # 使用中等字体来显示操作提示，会比小的 timer/length 字体大
        font_action_prompt = self.font_medium # 例如使用 36号字体

        mins, secs = divmod(int(self.game_timer), 60)
        timer_text = f"时长: {mins:01d}:{secs:02d}"
        timer_surf = self.font_medium.render(timer_text, True, WHITE)
        surface.blit(timer_surf, (10 + self.draw_offset_x, 10 + self.draw_offset_y))

        length = self.snake.length if self.snake else 0
        length_text = f"长度: {length}"
        length_surf = self.font_medium.render(length_text, True, WHITE)
        length_rect = length_surf.get_rect(topright=(self.draw_offset_x + CANVAS_WIDTH_PX - 10, 10 + self.draw_offset_y))
        surface.blit(length_surf, length_rect)

        # --- 修改：操作提示 (左下角) ---
        # 1. 绘制分裂提示 (使用中等字体)
        split_available = self.snake.split_available if self.snake else False
        split_color = WHITE if split_available else GREY
        split_text = "分裂 [空格]" # 稍微调整下格式
        split_surf = font_action_prompt.render(split_text, True, split_color)
        # 获取分裂文本的高度，用于定位加速文本
        split_text_height = split_surf.get_height()
        # 定位分裂文本在左下角
        split_rect = split_surf.get_rect(bottomleft=(10 + self.draw_offset_x, self.draw_offset_y + CANVAS_HEIGHT_PX - 10))
        surface.blit(split_surf, split_rect)

        # 2. 绘制加速提示 (在分裂提示上方)
        # 加速提示通常一直显示，颜色可以固定为白色，或者根据是否按下 Shift 变化？(暂时固定白色)
        accelerate_color = WHITE
        accelerate_text = "加速 [Shift]"
        accelerate_surf = font_action_prompt.render(accelerate_text, True, accelerate_color)
        # 定位加速文本，使其底部与分裂文本的顶部对齐，并留一点间距
        accelerate_rect = accelerate_surf.get_rect(bottomleft=(split_rect.left, split_rect.top - 5)) # 5 是间距像素
        surface.blit(accelerate_surf, accelerate_rect)
        # --- 操作提示修改结束 ---

    def draw_game_over_screen(self, surface):
        """绘制游戏结束结算界面。"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

        title_surf = self.font_large.render("游戏结算", True, RED)
        title_rect = title_surf.get_rect(center=(center_x, center_y - 150))
        surface.blit(title_surf, title_rect)

        score_length = self.snake.length if self.snake else 0
        score_text = f"最终长度: {score_length}"
        score_surf = self.font_medium.render(score_text, True, WHITE)
        score_rect = score_surf.get_rect(center=(center_x, title_rect.bottom + 60))
        surface.blit(score_surf, score_rect)

        button_width, button_height, button_spacing = 250, 60, 30
        base_y = score_rect.bottom + 80

        # 重玩按钮
        self.replay_button_rect = pygame.Rect(0, 0, button_width, button_height)
        self.replay_button_rect.midtop = (center_x - button_width/2 - button_spacing/2, base_y)
        pygame.draw.rect(surface, GREEN, self.replay_button_rect, border_radius=10)
        replay_text_surf = self.font_medium.render("重玩 (R)", True, BLACK)
        replay_text_rect = replay_text_surf.get_rect(center=self.replay_button_rect.center)
        surface.blit(replay_text_surf, replay_text_rect)

        # 时光倒流按钮
        rewind_button_color = BRIGHT_YELLOW if self.rewind_available else GREY
        self.rewind_button_rect = pygame.Rect(0, 0, button_width, button_height)
        self.rewind_button_rect.midtop = (center_x + button_width/2 + button_spacing/2, base_y)
        pygame.draw.rect(surface, rewind_button_color, self.rewind_button_rect, border_radius=10)
        rewind_text = "时光倒流 (T)" if self.rewind_available else "时光倒流 (已用)"
        rewind_text_surf = self.font_medium.render(rewind_text, True, BLACK)
        rewind_text_rect = rewind_text_surf.get_rect(center=self.rewind_button_rect.center)
        surface.blit(rewind_text_surf, rewind_text_rect)


    def check_game_over_button_clicks(self, mouse_pos):
         """检查鼠标点击是否在游戏结束界面的按钮上。"""
         if hasattr(self, 'replay_button_rect') and self.replay_button_rect.collidepoint(mouse_pos):
             self.reset_game()
         elif hasattr(self, 'rewind_button_rect') and self.rewind_button_rect.collidepoint(mouse_pos) and self.rewind_available:
             self.attempt_rewind()


    def draw(self):
        """绘制游戏的所有可见元素。"""
        self.screen.fill(BLACK)
        self.draw_background(self.screen) # 绘制背景
        self.draw_grid(self.screen)       # 绘制网格

        # 在画布子表面上绘制游戏对象
        try:
             canvas_rect = pygame.Rect(self.draw_offset_x, self.draw_offset_y, CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX)
             canvas_surface = self.screen.subsurface(canvas_rect)
             for fruit in self.fruits: fruit.draw(canvas_surface)
             for corpse in self.corpses: corpse.draw(canvas_surface)
             if self.snake: self.snake.draw(canvas_surface)
             for ghost in self.ghosts: ghost.draw(canvas_surface)
        except ValueError as e:
            # print(f"创建画布子表面失败: {e}") # 减少打印
            # 如果子表面创建失败，尝试直接在屏幕上绘制（可能超出边界）
             canvas_rect = pygame.Rect(self.draw_offset_x, self.draw_offset_y, CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX)
             pygame.draw.rect(self.screen, GREY, canvas_rect, 1) # 画个框提示区域

        # 在主屏幕上绘制粒子
        for particle in self.particles: particle.draw(self.screen)

        # 绘制 UI 和 游戏结束界面
        self.draw_ui(self.screen)
        if self.game_state == STATE_GAME_OVER:
            self.draw_game_over_screen(self.screen)

        pygame.display.flip() # 更新屏幕

    # ... (save_state_for_rewind, attempt_rewind, restore_state_from_rewind 方法保持不变) ...
    def save_state_for_rewind(self):
        """保存当前游戏状态，用于可能的时光倒流。"""
        if not self.snake: return
        current_game_time = self.game_timer
        state = {
            'time': current_game_time,
            'snake_body': self.snake.body.copy(),
            'snake_length': self.snake.length,
            'snake_direction': self.snake.direction,
            'snake_new_direction': self.snake.new_direction,
            'snake_is_accelerating': self.snake.is_accelerating,
            'fruits': [(f.position, f.type, f.lifespan, f.creation_time - self.start_time) for f in self.fruits],
            'corpses': [{'segments': c.segments.copy(), 'creation_game_time': c.creation_time - self.start_time} for c in self.corpses],
            'ghosts': [{'pos': g.grid_pos, 'pixel_pos': list(g.pixel_pos), 'type': g.type, 'target': g.target_grid_pos} for g in self.ghosts],
            'pinky_spawned': self.pinky_spawned,
            'frenzy_active': self.frenzy_active,
            'last_frenzy_start_time': self.last_frenzy_start_time,
        }
        self.history.append(state)

    def attempt_rewind(self):
         """尝试执行时光倒流操作。"""
         if not self.rewind_available: print("时光倒流不可用."); return
         if not self.history: print("没有历史记录可供倒流."); return
         print("尝试时光倒流...")
         try:
             target_game_time = self.game_timer - REWIND_SECONDS
             best_snapshot = None
             for snapshot in reversed(self.history):
                 if snapshot['time'] <= target_game_time:
                     best_snapshot = snapshot; break
             if not best_snapshot and self.history:
                 best_snapshot = self.history[0]; print("历史记录不足，回溯到最早状态。")

             if best_snapshot:
                  self.restore_state_from_rewind(best_snapshot)
                  self.rewind_available = False
                  self.play_sound('rewind')
                  self.history.clear()
                  self.frames_since_last_snapshot = 0
                  print("时光倒流成功!")
             else: print("在历史记录中找不到合适的回溯点.")
         except Exception as e: print(f"时光倒流时发生错误: {e}")

    def restore_state_from_rewind(self, state):
        """根据保存的状态快照恢复游戏。"""
        restored_game_time = state['time']
        print(f"恢复到游戏时间: {restored_game_time:.2f} 秒")
        self.start_time = time.time() - restored_game_time
        self.game_timer = restored_game_time

        if self.speedup_channel: self.speedup_channel.stop()

        # 恢复蛇
        if not self.snake: self.snake = Snake(self)
        self.snake.body = state['snake_body'].copy()
        self.snake.length = state['snake_length']
        self.snake.direction = state['snake_direction']
        self.snake.new_direction = state['snake_new_direction']
        self.snake.alive = True
        self.snake.is_accelerating = state['snake_is_accelerating']
        self.snake.update_head_image()

        # 恢复果实
        self.fruits.clear()
        for pos, f_type_name, lifespan, creation_game_time in state['fruits']:
             img_name = f'fruit_{f_type_name}.png'
             should_exist = True
             if lifespan is not None and restored_game_time - creation_game_time > lifespan:
                  should_exist = False
             if should_exist:
                 restored_fruit = Fruit(self, pos, f_type_name, img_name, lifespan)
                 restored_fruit.creation_time = self.start_time + creation_game_time
                 self.fruits.append(restored_fruit)

        # 恢复尸体
        self.corpses.clear()
        for c_data in state['corpses']:
             creation_game_time = c_data['creation_game_time']
             corpse_age = restored_game_time - creation_game_time
             if corpse_age < CORPSE_LIFESPAN_SECONDS:
                 restored_corpse = Corpse(self, c_data['segments'].copy())
                 restored_corpse.creation_time = self.start_time + creation_game_time
                 # 重算时间点
                 restored_corpse.flicker_start_time = restored_corpse.creation_time + CORPSE_FLICKER_START_OFFSET
                 restored_corpse.flicker_end_time = restored_corpse.flicker_start_time + CORPSE_Flicker_DURATION_SECONDS
                 restored_corpse.fade_start_time = restored_corpse.flicker_end_time
                 restored_corpse.fade_end_time = restored_corpse.fade_start_time + CORPSE_FADE_DURATION_SECONDS
                 if time.time() < restored_corpse.fade_end_time: # 用当前墙上时间判断是否还应存在
                     self.corpses.append(restored_corpse)


        # 恢复鬼魂
        self.ghosts.clear()
        self.pinky_spawned = state['pinky_spawned']
        for g_data in state['ghosts']:
            ghost = None
            if g_data['type'] == 'Blinky': ghost = Blinky(self)
            elif g_data['type'] == 'Pinky': ghost = Pinky(self)
            if ghost:
                ghost.grid_pos = g_data['pos']
                ghost.pixel_pos = list(g_data['pixel_pos'])
                ghost.target_grid_pos = g_data['target']
                ghost.last_target_update = 0
                self.ghosts.append(ghost)

        # 恢复狂热
        self.frenzy_active = state['frenzy_active']
        self.last_frenzy_start_time = state['last_frenzy_start_time']

        # 重置计时器
        self.last_move_time = time.time()
        self.last_fruit_spawn_time = time.time()
        self.last_gradual_heat_time = time.time()

        # 重启加速音效（如果需要）
        if self.snake.is_accelerating and self.speedup_channel and self.sounds['speedup']:
            try: self.speedup_channel.play(self.sounds['speedup'], loops=-1)
            except pygame.error as e: print(f"恢复时播放加速音效失败: {e}")

        self.game_state = STATE_PLAYING


    def run(self):
        """游戏主循环。"""
        try:
            self.reset_game()
            while self.is_running:
                dt = self.clock.tick(FPS) / 1000.0
                dt = min(dt, 0.1)
                self.handle_input()
                if self.game_state == STATE_PLAYING:
                    self.update(dt)
                self.draw()
        finally:
            print("游戏退出，停止音频...")
            pygame.mixer.music.stop()
            pygame.mixer.stop()
            print("卸载 Pygame...")
            pygame.quit()
            print("Pygame 已卸载。")

# ... (main.py 不需要修改) ...