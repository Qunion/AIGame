import pygame
import sys
import time
import random
from collections import deque
from settings import * # 导入设置
from sprites import Snake, Fruit, Corpse, Blinky, Pinky, Particle # 导入精灵类

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
        self.spawn_fruit(count=2, force_special=True)
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

    def spawn_fruit(self, count=1, force_special=False):
        """在画布上生成指定数量的果实。"""
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

                is_special = False
                if force_special and spawned_count == 0: is_special = True
                elif random.random() < 0.3: is_special = True

                if is_special:
                    choice = random.choice(['healthy', 'bomb'])
                    if choice == 'healthy':
                        fruit_type = 'healthy'; lifespan = HEALTHY_FRUIT_DURATION_SECONDS; img_name = 'fruit_healthy.png'
                    else:
                         fruit_type = 'bomb'; lifespan = BOMB_FRUIT_DURATION_SECONDS; img_name = 'fruit_bomb.png'

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
                                    print("播放加速音效...") # 调试信息
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
                                 print("停止加速音效...") # 调试信息
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

    def check_fruit_collisions(self):
        """检查蛇头是否与果实发生碰撞。"""
        if not self.snake or not self.snake.alive: return
        head_pos = self.snake.get_head_position()
        eaten_fruit_index = -1
        for i, fruit in enumerate(self.fruits):
            if fruit.position == head_pos:
                eaten_fruit_index = i
                if fruit.type == 'normal': self.snake.grow(1); self.play_sound('pickup_normal')
                elif fruit.type == 'healthy': self.snake.grow(2); self.play_sound('pickup_healthy')
                elif fruit.type == 'bomb': self.trigger_game_over("炸弹果实")
                break
        if eaten_fruit_index != -1:
            if eaten_fruit_index < len(self.fruits): del self.fruits[eaten_fruit_index]

    def check_ghost_collisions(self):
        """检查蛇头是否与鬼魂发生碰撞。"""
        if not self.snake or not self.snake.alive: return
        head_pos = self.snake.get_head_position()
        for ghost in self.ghosts:
            if ghost.grid_pos == head_pos:
                 self.trigger_game_over(f"撞到 {ghost.type}")
                 break

    def check_corpse_merge(self):
         """检查蛇头是否与尸体的端点接触以触发融合。"""
         if not self.snake or not self.snake.alive: return
         head_pos = self.snake.get_head_position()
         corpse_to_remove_index = -1
         current_time = time.time()

         for i, corpse in enumerate(self.corpses):
             # 免疫检查
             if current_time - corpse.creation_time < MERGE_IMMUNITY_SECONDS: continue
             if not corpse.segments: continue

             first_seg, last_seg = corpse.get_end_points()
             if first_seg is None: continue # 如果端点无效则跳过

             if head_pos == first_seg or head_pos == last_seg:
                 print(f"融合触发! 蛇头: {head_pos}, 尸体端点: {first_seg}, {last_seg}") # 调试信息
                 corpse_to_remove_index = i
                 merge_at_first = (head_pos == first_seg)

                 # 融合逻辑 (与上次相同)
                 if merge_at_first:
                      new_body_list = list(self.snake.body) + list(corpse.segments)
                      if len(corpse.segments) > 1:
                           p_last_x, p_last_y = corpse.segments[-2]; last_x, last_y = corpse.segments[-1]
                           new_direction = (last_x - p_last_x, last_y - p_last_y)
                      else: new_direction = self.snake.direction
                 else:
                       new_body_list = list(corpse.segments) + list(self.snake.body)
                       if len(corpse.segments) > 1:
                            first_x, first_y = corpse.segments[0]; sec_x, sec_y = corpse.segments[1]
                            new_direction = (first_x - sec_x, first_y - sec_y)
                       else: new_direction = self.snake.direction

                 # 更新蛇状态
                 self.snake.body = deque(new_body_list)
                 self.snake.length = len(self.snake.body)
                 self.snake.direction = new_direction
                 self.snake.new_direction = new_direction
                 self.snake.update_head_image()

                 self.play_sound('merge')
                 self.add_particles(head_pos, 15, GREEN)
                 break # 处理完一次融合即退出循环

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
        mins, secs = divmod(int(self.game_timer), 60)
        timer_text = f"时长: {mins:01d}:{secs:02d}"
        timer_surf = self.font_small.render(timer_text, True, WHITE)
        surface.blit(timer_surf, (10 + self.draw_offset_x, 10 + self.draw_offset_y))

        length = self.snake.length if self.snake else 0
        length_text = f"长度: {length}"
        length_surf = self.font_small.render(length_text, True, WHITE)
        length_rect = length_surf.get_rect(topright=(self.draw_offset_x + CANVAS_WIDTH_PX - 10, 10 + self.draw_offset_y))
        surface.blit(length_surf, length_rect)

        split_available = self.snake.split_available if self.snake else False
        split_color = WHITE if split_available else GREY
        split_text = "分裂[空格]"
        split_surf = self.font_small.render(split_text, True, split_color)
        split_rect = split_surf.get_rect(bottomleft=(10 + self.draw_offset_x, self.draw_offset_y + CANVAS_HEIGHT_PX - 10))
        surface.blit(split_surf, split_rect)

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
        rewind_button_color = BLUE if self.rewind_available else GREY
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