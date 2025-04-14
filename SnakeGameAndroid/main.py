# -*- coding: utf-8 -*-

# --- 导入必要的库 ---
import kivy
kivy.require('2.0.0') # 指定 Kivy 版本要求

import os
import random
import math
from functools import partial
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.vector import Vector
from kivy.properties import (
    NumericProperty, ListProperty, ObjectProperty,
    StringProperty, BooleanProperty, DictProperty
)
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line, Triangle, Ellipse
from kivy.core.audio import SoundLoader
from kivy.utils import get_color_from_hex, platform

# --- 可调试编辑的常量 ---
# (方便你调整游戏参数)

# -- 游戏区域 --
CANVAS_GRID_WIDTH = 71  # 画布宽度（格子数）
CANVAS_GRID_HEIGHT = 40 # 画布高度（格子数）
CELL_SIZE_DEFAULT = 64 # 默认格子像素大小 (用于加载资源，实际大小会自适应)

# -- 蛇 --
INITIAL_SNAKE_LENGTH = 3 # 初始蛇长度
SNAKE_BASE_SPEED_PPS = 5.0 # 基础速度 (格子/秒)
ACCELERATION_FACTOR = 1.5 # 加速按钮额外速度系数 (50% -> 1.5)
SPLIT_DISABLE_LENGTH = 1 # 长度小于等于此值时禁用分裂
SNAKE_BODY_TRANSPARENCY_STEP = 0.02 # 蛇身每节增加的透明度 (2%)

# -- 尸体 --
CORPSE_EXIST_DURATION = 30.0 # 尸体存在时间 (秒)
CORPSE_BLINK_DURATION = 3.0  # 尸体消失前闪烁时间 (秒)
CORPSE_FADE_DURATION = 10.0 # 尸体闪烁后到完全消失的时间 (秒)

# -- 游戏进程 --
SPEED_INCREASE_INTERVAL = 10.0 # 每隔多少秒增加速度
SPEED_INCREASE_PERCENT = 0.02 # 每次增加的速度百分比 (2%)
REWIND_SECONDS = 10.0 # 时光倒流回溯的秒数

# -- 躁动时刻 --
FRENZY_INTERVAL = 60.0 # 躁动时刻触发间隔 (秒)
FRENZY_DURATION = 10.0 # 躁动时刻持续时间 (秒)
FRENZY_SPEED_BOOST = 1.2 # 躁动时速度提升倍数 (20% -> 1.2)
FRENZY_RAMP_DURATION = 2.0 # 躁动开始/结束时速度变化时间 (秒)

# -- 果实 --
FRUIT_SPAWN_INTERVAL = 5.0 # 普通果实生成间隔 (秒)
MAX_FRUITS = 10 # 最大果实数量
FRUIT_HEALTHY_DURATION = 30.0 # 健康果实持续时间 (秒)
FRUIT_BOMB_DURATION = 30.0    # 炸弹果实持续时间 (秒)

# -- 敌人 --
GHOST_BLINKY_SPEED_FACTOR = 0.5 # Blinky 速度系数 (基础速度的 50%)
GHOST_PINKY_SPEED_FACTOR = 0.5  # Pinky 速度系数 (基础速度的 50%)
PINKY_APPEAR_LENGTH = 10       # Pinky 出现的蛇长度阈值
PINKY_PREDICTION_DISTANCE = 4  # Pinky 预测蛇头前方格子数
GHOST_UPDATE_INTERVAL = 0.5    # 鬼魂重新计算目标/路径的间隔 (秒)
GHOST_WARNING_DISTANCE = 3     # 鬼魂接近警告距离（格子）

# --- 内部常量 ---
DIRECTIONS = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}
OPPOSITE_DIRECTIONS = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
ASSETS_DIR = 'assets'
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
SOUNDS_DIR = os.path.join(ASSETS_DIR, 'sounds')

# --- 资源加载辅助函数 ---
def load_image(filename):
    """安全加载图片，处理文件不存在的情况"""
    path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(path):
        return Image(source=path, allow_stretch=True, keep_ratio=False)
    else:
        print(f"Warning: Image not found - {path}")
        # 返回一个占位符或空对象，避免崩溃
        # 这里简单返回 None，使用时需要检查
        return None

def load_sound(filename):
    """安全加载音效，处理文件不存在的情况"""
    path = os.path.join(SOUNDS_DIR, filename)
    if os.path.exists(path):
        try:
            sound = SoundLoader.load(path)
            if sound:
                return sound
            else:
                print(f"Warning: Failed to load sound - {path}")
                return None
        except Exception as e:
            print(f"Error loading sound {path}: {e}")
            return None
    else:
        print(f"Warning: Sound not found - {path}")
        return None

# --- 游戏主画布 ---
class GameCanvas(Widget):
    """负责绘制游戏背景、网格、蛇、果实、鬼魂等"""
    grid_size = NumericProperty(CELL_SIZE_DEFAULT) # 当前格子大小 (像素)
    canvas_offset_x = NumericProperty(0)
    canvas_offset_y = NumericProperty(0)
    grid_color = ListProperty(get_color_from_hex('#00000033')) # 浅色半透明网格

    # 游戏元素引用 (将在 Game 类中填充)
    snake_parts = ListProperty([]) # 蛇的所有格子坐标 [(x1, y1), (x2, y2), ...]
    fruits = DictProperty({})     # 果实 { (x,y): type, ... }
    corpses = ListProperty([])    # 尸体 [{ 'parts': [(x,y),...], 'timer': float, 'state': str }, ...]
    ghosts = DictProperty({})     # 鬼魂 { 'name': {'pos': (x,y), 'type': str}, ... }

    # 资源纹理 (预加载以提高性能)
    background_texture = ObjectProperty(None, allownone=True)
    grid_texture = ObjectProperty(None, allownone=True) # 如果用图片实现网格
    snake_head_texture = ObjectProperty(None, allownone=True)
    snake_body_texture = ObjectProperty(None, allownone=True)
    corpse_texture = ObjectProperty(None, allownone=True)
    fruit_textures = DictProperty({}) # {'normal': texture, 'healthy': texture, ...}
    ghost_textures = DictProperty({}) # {'blinky': texture, 'pinky': texture, ...}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_textures()
        # 绑定窗口大小变化事件，用于重新计算格子大小和偏移
        Window.bind(on_resize=self.update_layout)
        # 初始计算一次布局
        Clock.schedule_once(self.update_layout, 0)

    def _load_textures(self):
        """加载所有需要的图片资源为纹理"""
        bg_image = load_image('background.png')
        if bg_image:
            self.background_texture = bg_image.texture

        # 可选：加载网格图片纹理
        # grid_image = load_image('grid_overlay.png')
        # if grid_image:
        #     self.grid_texture = grid_image.texture
        #     self.grid_texture.wrap = 'repeat' # 设置为平铺

        head_image = load_image('snake_head.png')
        if head_image: self.snake_head_texture = head_image.texture

        body_image = load_image('snake_body.png')
        if body_image: self.snake_body_texture = body_image.texture

        corpse_image = load_image('corpse.png')
        if corpse_image: self.corpse_texture = corpse_image.texture

        fruit_files = {
            'normal': 'fruit_normal.png',
            'healthy': 'fruit_healthy.png',
            'bomb': 'fruit_bomb.png'
        }
        for f_type, f_name in fruit_files.items():
            img = load_image(f_name)
            if img: self.fruit_textures[f_type] = img.texture

        ghost_files = {
            'blinky': 'ghost_blinky.png',
            'pinky': 'ghost_pinky.png'
        }
        for g_type, g_name in ghost_files.items():
            img = load_image(g_name)
            if img: self.ghost_textures[g_type] = img.texture

    def update_layout(self, *args):
        """根据窗口大小调整画布和格子大小"""
        # 1. 计算格子大小 (保持画布总格子数不变)
        cell_w = Window.width / (CANVAS_GRID_WIDTH / 2) # 屏幕宽度对应画布宽度的一半
        cell_h = Window.height / (CANVAS_GRID_HEIGHT / 2) # 屏幕高度对应画布高度的一半
        self.grid_size = min(cell_w, cell_h) # 取较小值保证都能放下，并保持格子为正方形

        # 2. 计算画布在屏幕上的偏移量 (居中显示)
        # 注意：这里简化处理，默认画布中心就是屏幕中心
        # 实际需要根据蛇头位置动态调整偏移量，这部分逻辑在 draw 方法中处理
        # self.canvas_offset_x = (Window.width - CANVAS_GRID_WIDTH * self.grid_size) / 2
        # self.canvas_offset_y = (Window.height - CANVAS_GRID_HEIGHT * self.grid_size) / 2
        # print(f"Window: {Window.width}x{Window.height}, CellSize: {self.grid_size:.2f}")

        # 3. 触发重绘
        self.canvas.ask_update()

    def draw(self, snake_head_pos):
        """绘制所有游戏元素"""
        self.canvas.clear() # 清除上一帧内容

        # --- 计算视口偏移 ---
        # 目标：让蛇头尽量保持在屏幕中心
        # 1. 计算蛇头在画布坐标系中的理想屏幕中心位置 (像素)
        target_center_x_px = Window.width / 2
        target_center_y_px = Window.height / 2

        # 2. 计算蛇头当前在画布坐标系中的像素位置
        snake_head_px_x = snake_head_pos[0] * self.grid_size
        snake_head_px_y = snake_head_pos[1] * self.grid_size

        # 3. 计算需要的画布偏移量 (让蛇头像素位置对准屏幕中心)
        ideal_offset_x = target_center_x_px - snake_head_px_x
        ideal_offset_y = target_center_y_px - snake_head_px_y

        # 4. 限制画布偏移量，防止视口移出画布边界
        # 画布总像素大小
        total_canvas_width_px = CANVAS_GRID_WIDTH * self.grid_size
        total_canvas_height_px = CANVAS_GRID_HEIGHT * self.grid_size

        # 计算画布左右(上下)两边超出屏幕的部分
        overhang_x = total_canvas_width_px - Window.width
        overhang_y = total_canvas_height_px - Window.height

        # 限制偏移量范围
        # 最小偏移 (画布左/下边缘贴着屏幕左/下边缘)
        min_offset_x = -overhang_x if overhang_x > 0 else 0
        min_offset_y = -overhang_y if overhang_y > 0 else 0
        # 最大偏移 (画布右/上边缘贴着屏幕右/上边缘)
        max_offset_x = 0 if overhang_x > 0 else (Window.width - total_canvas_width_px) # 如果画布比屏幕窄，需要正偏移
        max_offset_y = 0 if overhang_y > 0 else (Window.height - total_canvas_height_px)

        # 应用限制
        self.canvas_offset_x = max(min_offset_x, min(max_offset_x, ideal_offset_x))
        self.canvas_offset_y = max(min_offset_y, min(max_offset_y, ideal_offset_y))

        # --- 开始绘制 ---
        with self.canvas:
            # 1. 绘制背景 (如果纹理存在)
            if self.background_texture:
                Color(1, 1, 1, 1) # 白色，不透明
                # 背景图绘制在整个窗口，不随画布偏移
                # (如果背景图设计为跟随画布移动，则需要加 offset)
                Rectangle(texture=self.background_texture, pos=(0, 0), size=Window.size)

            # 2. 绘制网格 (代码绘制或使用纹理)
            Color(*self.grid_color) # 设置网格颜色和透明度
            # --- 方法一：代码绘制线条 ---
            start_x = self.canvas_offset_x % self.grid_size
            start_y = self.canvas_offset_y % self.grid_size
            # 绘制垂直线
            for i in range(int(Window.width / self.grid_size) + 2):
                px = start_x + i * self.grid_size
                Line(points=[px, 0, px, Window.height], width=1)
            # 绘制水平线
            for i in range(int(Window.height / self.grid_size) + 2):
                py = start_y + i * self.grid_size
                Line(points=[0, py, Window.width, py], width=1)
            # --- 方法二：使用平铺纹理 (如果 grid_texture 存在) ---
            # if self.grid_texture:
            #     # 计算纹理坐标，使其相对于画布原点固定
            #     tex_coords_x = -self.canvas_offset_x / self.grid_texture.width
            #     tex_coords_y = -self.canvas_offset_y / self.grid_texture.height
            #     Rectangle(texture=self.grid_texture,
            #               size=Window.size, # 覆盖整个窗口
            #               pos=(0, 0),
            #               tex_coords=(tex_coords_x, tex_coords_y,
            #                           tex_coords_x + Window.width / self.grid_texture.width,
            #                           tex_coords_y + Window.height / self.grid_texture.height))


            # --- 绘制游戏元素 (需要加上画布偏移量) ---
            # 后面会在这里添加绘制蛇、果实、尸体、鬼魂的代码
            # 示例：绘制一个红色的格子在 (10, 5)
            # grid_x, grid_y = 10, 5
            # screen_x = self.canvas_offset_x + grid_x * self.grid_size
            # screen_y = self.canvas_offset_y + grid_y * self.grid_size
            # # 检查是否在屏幕范围内 (优化，避免绘制屏幕外的东西)
            # if -self.grid_size < screen_x < Window.width and -self.grid_size < screen_y < Window.height:
            #     Color(1, 0, 0, 1) # 红色
            #     Rectangle(pos=(screen_x, screen_y), size=(self.grid_size, self.grid_size))

            # 3. 绘制果实
            Color(1, 1, 1, 1) # 重置颜色为白色
            for (gx, gy), f_type in self.fruits.items():
                tex = self.fruit_textures.get(f_type)
                if tex:
                    screen_x = self.canvas_offset_x + gx * self.grid_size
                    screen_y = self.canvas_offset_y + gy * self.grid_size
                    if -self.grid_size < screen_x < Window.width and -self.grid_size < screen_y < Window.height:
                        Rectangle(texture=tex, pos=(screen_x, screen_y), size=(self.grid_size, self.grid_size))

            # 4. 绘制尸体
            if self.corpse_texture:
                for corpse_data in self.corpses:
                    alpha = 1.0
                    # 处理闪烁效果
                    if corpse_data['state'] == 'blinking':
                        # 简单的闪烁：根据时间奇偶性决定是否绘制
                        if int(corpse_data['timer'] * 10) % 2 == 0: # 每0.1秒切换一次状态
                           alpha = 0.3
                    elif corpse_data['state'] == 'fading':
                        # 线性淡出
                        alpha = max(0, 1.0 - (CORPSE_EXIST_DURATION + CORPSE_BLINK_DURATION - corpse_data['timer']) / CORPSE_FADE_DURATION)

                    if alpha > 0: # 透明度大于0才绘制
                         Color(0.5, 0.5, 0.5, alpha * 0.8) # 灰色，带一点透明度，并应用闪烁/淡出透明度
                         for px, py in corpse_data['parts']:
                             screen_x = self.canvas_offset_x + px * self.grid_size
                             screen_y = self.canvas_offset_y + py * self.grid_size
                             if -self.grid_size < screen_x < Window.width and -self.grid_size < screen_y < Window.height:
                                 Rectangle(texture=self.corpse_texture, pos=(screen_x, screen_y), size=(self.grid_size, self.grid_size))


            # 5. 绘制蛇 (需要处理渐变透明度)
            head_drawn = False
            snake_len = len(self.snake_parts)
            for i, (px, py) in enumerate(reversed(self.snake_parts)): # 从尾部开始绘制，方便计算透明度
                screen_x = self.canvas_offset_x + px * self.grid_size
                screen_y = self.canvas_offset_y + py * self.grid_size

                # 简单的视口剔除
                if -self.grid_size < screen_x < Window.width and -self.grid_size < screen_y < Window.height:
                    is_head = (i == snake_len - 1)
                    texture_to_use = self.snake_head_texture if is_head and self.snake_head_texture else self.snake_body_texture

                    if texture_to_use:
                        # 计算透明度 (从头到尾渐变)
                        # i 是从尾部开始的索引 (0 to len-1)
                        # 头部索引是 len-1, 尾部是 0
                        # 透明度从头部 (alpha=1) 到尾部递减
                        segment_index_from_head = snake_len - 1 - i
                        alpha = max(0.1, 1.0 - segment_index_from_head * SNAKE_BODY_TRANSPARENCY_STEP) # 保证最低一点透明度可见
                        Color(1, 1, 0, alpha) # 黄色基调，应用透明度

                        Rectangle(texture=texture_to_use, pos=(screen_x, screen_y), size=(self.grid_size, self.grid_size))

            # 6. 绘制鬼魂
            Color(1, 1, 1, 1) # 重置颜色
            for name, data in self.ghosts.items():
                tex = self.ghost_textures.get(data['type'])
                if tex:
                    gx, gy = data['pos']
                    screen_x = self.canvas_offset_x + gx * self.grid_size
                    screen_y = self.canvas_offset_y + gy * self.grid_size
                    if -self.grid_size < screen_x < Window.width and -self.grid_size < screen_y < Window.height:
                        Rectangle(texture=tex, pos=(screen_x, screen_y), size=(self.grid_size, self.grid_size))

            # 7. 绘制特效 (例如速度线)
            # TODO: 在这里添加特效绘制代码


# --- 游戏主逻辑类 ---
class SnakeGame(FloatLayout):
    """包含游戏画布、UI元素和游戏循环"""
    game_time = NumericProperty(0)
    snake_length = NumericProperty(0)
    game_state = StringProperty('playing') # 'playing', 'paused', 'game_over'
    can_rewind = BooleanProperty(True) # 是否还能使用时光倒流

    # 游戏元素状态
    snake = ListProperty([]) # 蛇身格子坐标 [(x, y), ...]
    direction = StringProperty('right') # 'up', 'down', 'left', 'right'
    next_direction = StringProperty('right') # 缓存下一个方向输入
    fruits = DictProperty({}) # {(x, y): type}
    corpses = ListProperty([]) # [{'parts':[(x,y),...], 'timer': float, 'state':str}, ...]
    ghosts = DictProperty({}) # {'name': {'pos':(x,y), 'type':str, 'target':(x,y), 'path':[]}, ...}

    # 计时器和状态
    time_since_last_move = NumericProperty(0)
    time_since_last_fruit = NumericProperty(0)
    time_since_last_speed_increase = NumericProperty(0)
    frenzy_timer = NumericProperty(FRENZY_INTERVAL) # 倒计时到下次躁动
    frenzy_active_timer = NumericProperty(0) # 当前躁动持续时间
    is_frenzy = BooleanProperty(False)
    is_accelerating = BooleanProperty(False) # 是否按下了加速按钮

    # 历史状态 (用于时光倒流)
    history = ListProperty([]) # [(timestamp, game_snapshot), ...]

    # 音效对象
    sounds = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_sounds()
        self.setup_ui()
        self.game_canvas = self.ids.game_canvas # 获取kv文件中定义的GameCanvas实例
        self.start_new_game()
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        Clock.schedule_interval(self.update, 1.0 / 60.0) # 启动游戏循环 (60 FPS)
        Clock.schedule_interval(self.record_history, 0.5) # 每0.5秒记录一次状态

    def _load_sounds(self):
        """加载所有音效"""
        sound_files = {
            'bgm': 'bgm.ogg',
            'pickup_normal': 'pickup_normal.wav',
            'pickup_healthy': 'pickup_healthy.wav',
            # 'pickup_bomb': 'pickup_bomb.wav', # 碰到炸弹是结束，可能用 death 音效
            'split': 'split.wav',
            'merge': 'merge.wav',
            'death': 'death.wav',
            'rewind': 'rewind.wav',
            'ghost_warning': 'ghost_warning.wav'
        }
        for name, filename in sound_files.items():
            sound = load_sound(filename)
            if sound:
                self.sounds[name] = sound
                if name == 'bgm':
                    sound.loop = True # 背景音乐循环播放

    def setup_ui(self):
        """创建并添加UI元素 (得分、时间、按钮等)"""
        # 使用 AnchorLayout 来定位 UI 元素到角落
        # Kivy Language (KV) 通常更适合定义 UI 结构，这里用代码创建作为示例

        # 顶层UI布局 (覆盖在 GameCanvas 之上)
        ui_layer = FloatLayout(size_hint=(1, 1))
        self.add_widget(ui_layer) # 添加到 SnakeGame (它本身是 FloatLayout)

        # 左上角：时长
        top_left_anchor = AnchorLayout(anchor_x='left', anchor_y='top', size_hint=(0.3, 0.1))
        self.time_label = Label(text='时长: 0:00', font_size='20sp', halign='left', valign='top', size_hint=(1, 1), padding=(10, 10))
        top_left_anchor.add_widget(self.time_label)
        ui_layer.add_widget(top_left_anchor)

        # 右上角：长度
        top_right_anchor = AnchorLayout(anchor_x='right', anchor_y='top', size_hint=(0.3, 0.1))
        self.length_label = Label(text='长度: 0', font_size='20sp', halign='right', valign='top', size_hint=(1, 1), padding=(10, 10))
        top_right_anchor.add_widget(self.length_label)
        ui_layer.add_widget(top_right_anchor)

        # 左下角：方向控制轮盘 (简化为按钮)
        # TODO: 实现一个真正的触摸滑动轮盘控件
        bottom_left_anchor = AnchorLayout(anchor_x='left', anchor_y='bottom', size_hint=(0.3, 0.3))
        dpad_grid = GridLayout(cols=3, rows=3, size_hint=(None, None), size=(150, 150), spacing=5) # 固定像素大小

        dpad_grid.add_widget(Widget()) # Top-left empty
        dpad_grid.add_widget(Button(text='↑', on_press=partial(self.set_direction, 'up')))
        dpad_grid.add_widget(Widget()) # Top-right empty

        dpad_grid.add_widget(Button(text='←', on_press=partial(self.set_direction, 'left')))
        dpad_grid.add_widget(Widget()) # Center empty
        dpad_grid.add_widget(Button(text='→', on_press=partial(self.set_direction, 'right')))

        dpad_grid.add_widget(Widget()) # Bottom-left empty
        dpad_grid.add_widget(Button(text='↓', on_press=partial(self.set_direction, 'down')))
        dpad_grid.add_widget(Widget()) # Bottom-right empty

        bottom_left_anchor.add_widget(dpad_grid)
        ui_layer.add_widget(bottom_left_anchor)


        # 右下角：功能按钮 (分裂, 加速)
        bottom_right_anchor = AnchorLayout(anchor_x='right', anchor_y='bottom', size_hint=(0.3, 0.2))
        button_box = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(220, 80), spacing=20) # 固定像素

        self.split_button = Button(text='分裂', size_hint=(1, 1), on_press=self.perform_split)
        self.accelerate_button = Button(text='加速', size_hint=(1, 1))
        # 按下加速，松开取消
        self.accelerate_button.bind(on_press=self.start_accelerate, on_release=self.stop_accelerate)

        button_box.add_widget(self.split_button)
        button_box.add_widget(self.accelerate_button)
        bottom_right_anchor.add_widget(button_box)
        ui_layer.add_widget(bottom_right_anchor)

        # 游戏结束/暂停界面 (初始隐藏)
        self.popup_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.5),
                                      pos_hint={'center_x': 0.5, 'center_y': 0.5},
                                      padding=20, spacing=10)
        # 添加一个半透明背景
        with self.popup_layout.canvas.before:
            Color(0, 0, 0, 0.7) # 半透明黑色背景
            self.popup_bg_rect = Rectangle(size=self.popup_layout.size, pos=self.popup_layout.pos)
        self.popup_layout.bind(size=self._update_popup_bg, pos=self._update_popup_bg)

        self.popup_title = Label(text='游戏结算', font_size='30sp', size_hint_y=None, height=50)
        self.popup_score = Label(text='最终长度: 0', font_size='24sp')
        self.replay_button = Button(text='重玩', size_hint_y=None, height=50, on_press=self.start_new_game)
        self.rewind_button = Button(text='时光倒流 (10s)', size_hint_y=None, height=50, on_press=self.perform_rewind)

        self.popup_layout.add_widget(self.popup_title)
        self.popup_layout.add_widget(self.popup_score)
        self.popup_layout.add_widget(self.replay_button)
        self.popup_layout.add_widget(self.rewind_button)

        # 初始不添加到界面，在需要时添加
        # self.add_widget(self.popup_layout) # 暂时不加

    def _update_popup_bg(self, instance, value):
        """Callback to update popup background size and position."""
        self.popup_bg_rect.pos = instance.pos
        self.popup_bg_rect.size = instance.size

    def show_game_over_popup(self):
        """显示游戏结束弹窗"""
        if self.popup_layout.parent: # 避免重复添加
            return
        self.popup_title.text = '游戏结算'
        self.popup_score.text = f'最终长度: {self.snake_length}'
        self.rewind_button.disabled = not self.can_rewind # 根据是否能回溯设置按钮状态
        self.add_widget(self.popup_layout)

    def hide_popup(self):
        """隐藏弹窗"""
        if self.popup_layout.parent:
            self.remove_widget(self.popup_layout)

    def start_new_game(self, *args):
        """初始化或重置游戏状态"""
        self.hide_popup() # 确保弹窗隐藏
        self.game_state = 'playing'
        self.game_time = 0
        self.can_rewind = True # 每局游戏开始时重置回溯能力

        # 初始化蛇的位置和长度
        center_x, center_y = CANVAS_GRID_WIDTH // 2, CANVAS_GRID_HEIGHT // 2
        self.snake = [(center_x - i, center_y) for i in range(INITIAL_SNAKE_LENGTH)]
        self.snake_length = INITIAL_SNAKE_LENGTH
        self.direction = 'right'
        self.next_direction = 'right'

        # 清空游戏元素
        self.fruits.clear()
        self.corpses.clear()
        self.ghosts.clear()

        # 重置计时器
        self.time_since_last_move = 0
        self.time_since_last_fruit = 0
        self.time_since_last_speed_increase = 0
        self.frenzy_timer = FRENZY_INTERVAL
        self.frenzy_active_timer = 0
        self.is_frenzy = False
        self.is_accelerating = False

        # 清空历史记录并添加初始状态
        self.history = []
        self.record_history() # 记录初始状态

        # 立即生成初始果实
        self.spawn_fruit(force_special=True) # 保证第一个是特殊
        self.spawn_fruit()

        # 重置UI显示
        self.update_ui()

        # 播放背景音乐 (如果存在且未播放)
        if 'bgm' in self.sounds and self.sounds['bgm'].state != 'play':
            self.sounds['bgm'].play()

        # 初始化鬼魂 (Blinky)
        self.spawn_ghost('blinky')
        # Pinky 在达到长度条件时生成

    def _keyboard_closed(self):
        """处理键盘关闭事件"""
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        """处理键盘按键事件"""
        key_str = keycode[1]
        if self.game_state != 'playing':
            return False # 非游戏状态不处理方向键

        if key_str == 'w' or key_str == 'up':
            self.set_direction('up')
        elif key_str == 's' or key_str == 'down':
            self.set_direction('down')
        elif key_str == 'a' or key_str == 'left':
            self.set_direction('left')
        elif key_str == 'd' or key_str == 'right':
            self.set_direction('right')
        # 添加其他按键绑定，例如空格键加速？
        # elif key_str == 'spacebar':
        #     pass # 可以绑定加速或分裂
        else:
            return False # 未处理的按键
        return True # 表示已处理该按键

    def set_direction(self, new_direction, *args):
        """设置蛇的下一个移动方向，防止180度掉头"""
        current_opposite = OPPOSITE_DIRECTIONS.get(self.direction)
        if new_direction != current_opposite:
            self.next_direction = new_direction

    def start_accelerate(self, *args):
        self.is_accelerating = True
        # TODO: 添加视觉特效（速度线）

    def stop_accelerate(self, *args):
        self.is_accelerating = False
        # TODO: 移除视觉特效

    def perform_split(self, *args):
        """执行分裂操作"""
        if self.game_state != 'playing' or self.snake_length <= SPLIT_DISABLE_LENGTH:
            return

        # 播放音效
        if 'split' in self.sounds:
            self.sounds['split'].play()

        # TODO: 添加分裂粒子效果

        split_point = self.snake_length // 2 # 向下取整

        corpse_parts = self.snake[split_point:] # 从分裂点到头部成为尸体
        new_snake_parts = self.snake[:split_point] # 从尾部到分裂点前成为新蛇

        # 创建尸体数据
        corpse_data = {
            'parts': corpse_parts,
            'timer': CORPSE_EXIST_DURATION + CORPSE_BLINK_DURATION + CORPSE_FADE_DURATION, # 总存在时间
            'state': 'normal' # 初始状态
        }
        self.corpses.append(corpse_data)

        # 更新蛇的状态
        self.snake = new_snake_parts
        self.snake_length = len(new_snake_parts)

        # 设置新蛇的移动方向 (朝向原蛇尾的反方向)
        if len(self.snake) >= 2:
            tail_end = self.snake[0]
            tail_before_end = self.snake[1]
            dx = tail_before_end[0] - tail_end[0]
            dy = tail_before_end[1] - tail_end[1]
            # 根据位移找到反方向
            for name, (vx, vy) in DIRECTIONS.items():
                if vx == -dx and vy == -dy:
                    self.direction = name
                    self.next_direction = name
                    break
        elif len(self.snake) == 1:
             # 如果分裂后只剩一格，随机一个方向或保持原方向？这里保持原方向
             pass # Direction remains the same

        self.update_ui() # 更新长度显示

    def perform_rewind(self, *args):
        """执行时光倒流"""
        if not self.can_rewind or len(self.history) < 2: # 至少需要当前和上一个状态
            return

        # 找到10秒前的状态
        target_time = self.game_time - REWIND_SECONDS
        rewind_to_state = None
        # 从最近的记录开始往前找
        for timestamp, snapshot in reversed(self.history):
            if timestamp <= target_time:
                rewind_to_state = snapshot
                break

        if rewind_to_state:
            # 播放音效
            if 'rewind' in self.sounds:
                self.sounds['rewind'].play()

            # 恢复状态
            self.restore_from_snapshot(rewind_to_state)
            self.can_rewind = False # 只能用一次
            self.game_state = 'playing' # 确保回到游戏状态
            self.hide_popup() # 隐藏可能显示的结算弹窗

            # 清除回溯点之后的所有历史记录
            self.history = [item for item in self.history if item[0] <= rewind_to_state['game_time']]
            # 立即记录当前（回溯后）的状态
            self.record_history()

            # 可能需要重新播放背景音乐（如果之前停止了）
            if 'bgm' in self.sounds and self.sounds['bgm'].state != 'play':
                self.sounds['bgm'].play()
        else:
            print("Rewind failed: No state found far back enough.")
            # 可以给用户一个提示

    def record_history(self, *args):
        """记录当前游戏状态快照"""
        if self.game_state != 'playing': # 只记录游玩时的状态
             return

        snapshot = {
            'game_time': self.game_time,
            'snake': list(self.snake), # 创建副本
            'direction': self.direction,
            'next_direction': self.next_direction,
            'fruits': dict(self.fruits), # 创建副本
            'corpses': [dict(c, parts=list(c['parts'])) for c in self.corpses], # 深拷贝
            'ghosts': {name: dict(g) for name, g in self.ghosts.items()}, # 深拷贝
            'snake_length': self.snake_length,
            'time_since_last_speed_increase': self.time_since_last_speed_increase,
            'frenzy_timer': self.frenzy_timer,
            'frenzy_active_timer': self.frenzy_active_timer,
            'is_frenzy': self.is_frenzy,
            # 注意：不记录 is_accelerating, time_since_last_move 等瞬时状态
        }
        self.history.append((self.game_time, snapshot))

        # 限制历史记录长度，防止内存无限增长 (例如只保留最近30秒)
        max_history_duration = 30.0
        if self.history:
            oldest_allowed_time = self.game_time - max_history_duration
            self.history = [item for item in self.history if item[0] >= oldest_allowed_time]

    def restore_from_snapshot(self, snapshot):
        """从快照恢复游戏状态"""
        self.game_time = snapshot['game_time']
        self.snake = snapshot['snake']
        self.direction = snapshot['direction']
        self.next_direction = snapshot['next_direction']
        self.fruits = snapshot['fruits']
        self.corpses = snapshot['corpses']
        self.ghosts = snapshot['ghosts']
        self.snake_length = snapshot['snake_length']
        self.time_since_last_speed_increase = snapshot['time_since_last_speed_increase']
        self.frenzy_timer = snapshot['frenzy_timer']
        self.frenzy_active_timer = snapshot['frenzy_active_timer']
        self.is_frenzy = snapshot['is_frenzy']

        # 重置瞬时状态
        self.time_since_last_move = 0
        self.is_accelerating = False

        self.update_ui()
        self.game_canvas.snake_parts = self.snake
        self.game_canvas.fruits = self.fruits
        self.game_canvas.corpses = self.corpses
        self.game_canvas.ghosts = self.ghosts


    def update(self, dt):
        """游戏主循环，每帧调用"""
        if self.game_state != 'playing':
            # 如果游戏结束但弹窗未显示，则显示它
            if self.game_state == 'game_over' and not self.popup_layout.parent:
                 self.show_game_over_popup()
            # 停止背景音乐？看设计需求
            # if 'bgm' in self.sounds and self.sounds['bgm'].state == 'play':
            #     self.sounds['bgm'].stop()
            return # 游戏暂停或结束，不更新逻辑

        # 更新游戏时间
        self.game_time += dt

        # 更新尸体状态和计时器
        self.update_corpses(dt)

        # 更新躁动状态
        self.update_frenzy(dt)

        # 计算当前移动速度
        current_speed = self.calculate_current_speed()
        move_interval = 1.0 / current_speed # 每隔多少秒移动一格

        # 更新移动计时器
        self.time_since_last_move += dt

        # 判断是否需要移动
        if self.time_since_last_move >= move_interval:
            self.time_since_last_move -= move_interval # 减去一个移动间隔，保留多余时间
            self.move_snake() # 执行移动逻辑

        # 更新果实生成计时器
        self.time_since_last_fruit += dt
        if self.time_since_last_fruit >= FRUIT_SPAWN_INTERVAL:
            self.time_since_last_fruit = 0
            if len(self.fruits) < MAX_FRUITS:
                self.spawn_fruit()

        # 更新速度增加计时器
        self.time_since_last_speed_increase += dt
        if self.time_since_last_speed_increase >= SPEED_INCREASE_INTERVAL:
            self.time_since_last_speed_increase = 0
            # 速度增加逻辑在 calculate_current_speed 中体现

        # 更新鬼魂 (移动、AI决策等) - 这个也应该有自己的计时器或间隔
        self.update_ghosts(dt) # dt 传进去，让鬼魂根据自己的速度移动

        # 更新UI显示
        self.update_ui()

        # 更新画布上的元素引用
        self.game_canvas.snake_parts = self.snake
        self.game_canvas.fruits = self.fruits
        self.game_canvas.corpses = self.corpses
        self.game_canvas.ghosts = self.ghosts

        # 请求重绘画布 (传入蛇头位置用于视口计算)
        if self.snake:
            self.game_canvas.draw(self.snake[-1])
        else: # 以防万一蛇没了
             self.game_canvas.draw((CANVAS_GRID_WIDTH // 2, CANVAS_GRID_HEIGHT // 2))


    def calculate_current_speed(self):
        """根据基础速度、时间加成、躁动、加速按钮计算最终速度"""
        # 1. 基础速度
        speed = SNAKE_BASE_SPEED_PPS

        # 2. 时间加成
        time_bonus = 1.0 + (SPEED_INCREASE_PERCENT * (self.game_time // SPEED_INCREASE_INTERVAL))
        speed *= time_bonus

        # 3. 躁动加成
        frenzy_boost = 1.0
        if self.is_frenzy:
            # 计算当前躁动时间点在10秒周期内的位置
            t = self.frenzy_active_timer
            if t < FRENZY_RAMP_DURATION: # 0-2秒，线性提升
                frenzy_boost = 1.0 + (FRENZY_SPEED_BOOST - 1.0) * (t / FRENZY_RAMP_DURATION)
            elif t < FRENZY_DURATION - FRENZY_RAMP_DURATION: # 2-8秒，保持最大
                frenzy_boost = FRENZY_SPEED_BOOST
            elif t < FRENZY_DURATION: # 8-10秒，线性回落
                time_left = FRENZY_DURATION - t
                frenzy_boost = 1.0 + (FRENZY_SPEED_BOOST - 1.0) * (time_left / FRENZY_RAMP_DURATION)
            else: # 正常不会到这里，以防万一
                frenzy_boost = 1.0
        speed *= frenzy_boost

        # 4. 加速按钮系数
        if self.is_accelerating:
            speed *= ACCELERATION_FACTOR

        return max(1.0, speed) # 保证最低速度

    def update_corpses(self, dt):
        """更新所有尸体的状态和计时器"""
        next_corpses = []
        for corpse in self.corpses:
            corpse['timer'] -= dt
            if corpse['timer'] <= 0:
                # 时间到，消失
                continue
            elif corpse['timer'] <= CORPSE_FADE_DURATION and corpse['state'] != 'fading':
                 corpse['state'] = 'fading' # 进入淡出状态
            elif corpse['timer'] <= CORPSE_FADE_DURATION + CORPSE_BLINK_DURATION and corpse['state'] != 'blinking' and corpse['state'] != 'fading':
                 corpse['state'] = 'blinking' # 进入闪烁状态

            next_corpses.append(corpse)
        self.corpses = next_corpses


    def update_frenzy(self, dt):
        """更新躁动状态计时器"""
        if self.is_frenzy:
            self.frenzy_active_timer += dt
            if self.frenzy_active_timer >= FRENZY_DURATION:
                # 躁动结束
                self.is_frenzy = False
                self.frenzy_active_timer = 0
                self.frenzy_timer = FRENZY_INTERVAL # 重置下次躁动间隔
        else:
            self.frenzy_timer -= dt
            if self.frenzy_timer <= 0:
                # 进入躁动
                self.is_frenzy = True
                self.frenzy_active_timer = 0
                # TODO: 触发躁动开始的视觉/音效提示？


    def move_snake(self):
        """计算蛇的下一步位置并更新状态"""
        if not self.snake: return # 蛇不存在则不移动

        # 更新实际方向
        self.direction = self.next_direction

        # 计算新蛇头位置
        head_x, head_y = self.snake[-1]
        move_x, move_y = DIRECTIONS[self.direction]
        new_head_x = head_x + move_x
        new_head_y = head_y + move_y

        # --- 碰撞检测 ---
        # 1. 撞墙检测
        if not (0 <= new_head_x < CANVAS_GRID_WIDTH and 0 <= new_head_y < CANVAS_GRID_HEIGHT):
            self.game_over("撞到墙壁！")
            return

        # 2. 撞自身检测
        # 优化：只需检查新头位置是否在旧蛇身部分（不包括旧蛇头）
        if (new_head_x, new_head_y) in self.snake[:-1]:
             self.game_over("撞到自己！")
             return

        # 3. 撞尸体检测 (非融合碰撞)
        for corpse in self.corpses:
            # 排除融合情况 (头或尾)
            if (new_head_x, new_head_y) in corpse['parts'][1:-1]: # 只检查中间部分
                self.game_over("撞到尸体！")
                return

        # 4. 撞炸弹果实检测
        if (new_head_x, new_head_y) in self.fruits and self.fruits[(new_head_x, new_head_y)] == 'bomb':
             # 播放音效?
             if 'death' in self.sounds: self.sounds['death'].play()
             self.game_over("碰到炸弹！")
             # 可以考虑移除炸弹，或者让它有个爆炸效果
             del self.fruits[(new_head_x, new_head_y)]
             return

        # 5. 撞鬼魂检测
        for name, ghost_data in self.ghosts.items():
             if (new_head_x, new_head_y) == ghost_data['pos']:
                 self.game_over(f"被{name}抓住了！")
                 return


        # --- 检查是否吃到果实或触发融合 ---
        ate_fruit = False
        merged_corpse_index = -1

        # 检查普通果实和健康果实
        fruit_type = self.fruits.get((new_head_x, new_head_y))
        if fruit_type and fruit_type != 'bomb':
            ate_fruit = True
            del self.fruits[(new_head_x, new_head_y)] # 从字典中移除果实

            # 播放音效
            sound_name = f"pickup_{fruit_type}"
            if sound_name in self.sounds:
                self.sounds[sound_name].play()

            # 增加长度
            increase = 2 if fruit_type == 'healthy' else 1
            # 长度增加逻辑在下面移动后处理

            # 如果吃完后没有果实了，立即生成两个
            if not self.fruits:
                self.spawn_fruit(force_special=True)
                self.spawn_fruit()

        # 检查是否触发融合 (撞到尸体头或尾)
        else: # 只有在没吃到果实的地方才可能融合
            for i, corpse in enumerate(self.corpses):
                 corpse_parts = corpse['parts']
                 if not corpse_parts: continue # 跳过空尸体

                 touched_end = None
                 if (new_head_x, new_head_y) == corpse_parts[0]: # 撞到尾部
                     touched_end = 'tail'
                 elif (new_head_x, new_head_y) == corpse_parts[-1]: # 撞到头部
                     touched_end = 'head'

                 if touched_end:
                     merged_corpse_index = i
                     # 播放音效
                     if 'merge' in self.sounds: self.sounds['merge'].play()

                     # --- 执行融合逻辑 ---
                     # 1. 获取尸体部分并从列表移除
                     merged_corpse = self.corpses.pop(merged_corpse_index)
                     corpse_segments = merged_corpse['parts']

                     # 2. 确定新的蛇头位置和方向
                     if touched_end == 'tail': # 撞尾融头
                         new_head_pos = corpse_segments[-1] # 新蛇头在尸体头部
                         # 新方向：尸体倒数第二格指向头部的方向
                         if len(corpse_segments) >= 2:
                             p1 = corpse_segments[-2]
                             p2 = corpse_segments[-1]
                             dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                         else: # 尸体只有一格，方向不变？或随机？保持当前方向
                             dx, dy = DIRECTIONS[self.direction]

                     else: # 撞头融尾 (touched_end == 'head')
                         new_head_pos = corpse_segments[0] # 新蛇头在尸体尾部
                         # 新方向：尸体第二格指向尾部的方向
                         if len(corpse_segments) >= 2:
                             p1 = corpse_segments[1]
                             p2 = corpse_segments[0]
                             dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                         else: # 尸体只有一格
                             dx, dy = DIRECTIONS[self.direction]

                     # 更新蛇头位置
                     new_head_x, new_head_y = new_head_pos

                     # 更新方向
                     new_dir_found = False
                     for name, (vx, vy) in DIRECTIONS.items():
                         if vx == dx and vy == dy:
                             self.direction = name
                             self.next_direction = name
                             new_dir_found = True
                             break
                     if not new_dir_found:
                          print(f"Warning: Could not determine direction after merge. dx={dx}, dy={dy}")
                          # 保留旧方向作为后备

                     # 3. 连接蛇身
                     # 如果撞尾融头，尸体需要反转再加到蛇头前面
                     if touched_end == 'tail':
                         self.snake = list(reversed(corpse_segments)) + self.snake
                     else: # 撞头融尾，尸体直接加到蛇头前面
                         self.snake = corpse_segments + self.snake

                     # 4. 更新长度
                     self.snake_length = len(self.snake)
                     # 融合后不再执行下面的常规移动添加头部的逻辑，直接跳过
                     self.update_ui()
                     # 检查 Pinky 生成条件
                     self.check_pinky_spawn()
                     return # 融合完成，结束本次移动

        # --- 更新蛇身 ---
        # 将新头添加到列表末尾
        self.snake.append((new_head_x, new_head_y))

        # 如果没有吃到果实，移除蛇尾
        if not ate_fruit:
            self.snake.pop(0)
        else:
            # 吃到了果实，长度增加
            fruit_increase = 2 if fruit_type == 'healthy' else 1
            # 因为已经加了头，所以长度直接增加 fruit_increase
            # 如果只加1，上面append已经完成了；如果加2，还需要再加一次尾巴（或不pop）
            # 为了简化，我们让吃果实的效果是“不移除尾巴”，如果健康果实则额外再复制一个尾巴
            if fruit_increase == 2 and len(self.snake) > 1:
                self.snake.insert(0, self.snake[0]) # 在尾部再加一节

            self.snake_length = len(self.snake) # 更新长度
            self.update_ui()
            # 检查 Pinky 生成条件
            self.check_pinky_spawn()


    def spawn_fruit(self, force_special=False):
        """在画布随机空位置生成一个果实"""
        if len(self.fruits) >= MAX_FRUITS and not force_special: # 强制生成特殊时忽略上限
            return

        # 查找可用位置 (不在蛇身、其他果实、尸体、鬼魂上)
        occupied_cells = set(self.snake) | set(self.fruits.keys()) | set(g['pos'] for g in self.ghosts.values())
        for corpse in self.corpses:
            occupied_cells.update(corpse['parts'])

        available_cells = []
        for x in range(CANVAS_GRID_WIDTH):
            for y in range(CANVAS_GRID_HEIGHT):
                if (x, y) not in occupied_cells:
                    available_cells.append((x, y))

        if not available_cells:
            print("Warning: No space left to spawn fruit!")
            return

        # 选择位置
        pos = random.choice(available_cells)

        # 决定果实类型
        fruit_type = 'normal'
        possible_types = ['normal', 'healthy', 'bomb']
        if force_special:
            fruit_type = random.choice(['healthy', 'bomb']) # 强制时，在特殊中选
        else:
            # 可以加权重，让普通果实概率更高
            fruit_type = random.choices(possible_types, weights=[0.7, 0.15, 0.15], k=1)[0]

        # 添加到字典
        self.fruits[pos] = fruit_type
        # TODO: 如果是限时果实 (healthy, bomb)，需要启动计时器
        # Kivy 的 Clock.schedule_once 可以用来在特定时间后移除果实


    def spawn_ghost(self, ghost_type):
        """生成指定类型的鬼魂"""
        if ghost_type in self.ghosts: # 防止重复生成同名鬼魂
             return

        # 查找出生点 (随机空位，不在蛇附近?)
        occupied_cells = set(self.snake) | set(self.fruits.keys()) | set(g['pos'] for g in self.ghosts.values())
        for corpse in self.corpses:
            occupied_cells.update(corpse['parts'])

        available_cells = []
        for x in range(CANVAS_GRID_WIDTH):
            for y in range(CANVAS_GRID_HEIGHT):
                # 简单处理：不在蛇头一定范围内出生
                head_x, head_y = self.snake[-1] if self.snake else (0,0)
                dist_sq = (x - head_x)**2 + (y - head_y)**2
                if (x, y) not in occupied_cells and dist_sq > 25: # 距离蛇头至少5格远
                    available_cells.append((x, y))

        if not available_cells:
             print(f"Warning: No space to spawn ghost {ghost_type}")
             # 可以选择强制生成在某个角落
             start_pos = (0, 0) if (0,0) not in occupied_cells else (CANVAS_GRID_WIDTH-1, CANVAS_GRID_HEIGHT-1)
        else:
             start_pos = random.choice(available_cells)

        self.ghosts[ghost_type] = {
            'pos': start_pos,
            'type': ghost_type,
            'target': None, # 目标格子
            'path': [],     # A* 路径 (如果实现)
            'move_timer': 0 # 移动计时器
        }
        print(f"Ghost {ghost_type} spawned at {start_pos}")


    def check_pinky_spawn(self):
        """检查是否达到生成 Pinky 的条件"""
        if self.snake_length >= PINKY_APPEAR_LENGTH and 'pinky' not in self.ghosts:
            self.spawn_ghost('pinky')
# -*- coding: utf-8 -*-
# --- main.py (继续) ---

# (这里省略之前已经提供的代码：导入、常量、资源加载函数、GameCanvas 类、SnakeGame 类的 __init__, _load_sounds, setup_ui, _update_popup_bg, show_game_over_popup, hide_popup, start_new_game, _keyboard_closed, _on_keyboard_down, set_direction, start_accelerate, stop_accelerate, perform_split, perform_rewind, record_history, restore_from_snapshot, update, calculate_current_speed, update_corpses, update_frenzy, move_snake [部分], spawn_fruit [部分], spawn_ghost, check_pinky_spawn, update_ghosts [部分] )
# 请将这部分代码追加到你之前的 main.py 文件末尾

    # --- (确保之前的代码都在这里) ---

    def update_ghosts(self, dt):
        """更新所有鬼魂的位置和 AI"""
        ghost_base_speed = SNAKE_BASE_SPEED_PPS # 鬼魂速度基于蛇的基础速度
        time_to_recalculate = False # 是否到了重新计算路径/目标的时间

        # 简单的计时器判断是否需要重算目标
        global_ghost_update_timer = getattr(self, '_global_ghost_update_timer', GHOST_UPDATE_INTERVAL)
        global_ghost_update_timer -= dt
        if global_ghost_update_timer <= 0:
            time_to_recalculate = True
            global_ghost_update_timer = GHOST_UPDATE_INTERVAL
        setattr(self, '_global_ghost_update_timer', global_ghost_update_timer)


        # 检查鬼魂接近警告
        ghost_is_close = False
        if self.snake:
            head_pos = self.snake[-1]
            for name, ghost in self.ghosts.items():
                # 计算鬼魂与蛇头的距离平方
                dist_sq = (ghost['pos'][0] - head_pos[0])**2 + (ghost['pos'][1] - head_pos[1])**2
                if dist_sq <= GHOST_WARNING_DISTANCE**2:
                    ghost_is_close = True
                    break # 只要有一个接近就触发

        # 播放/停止警告音
        warning_sound = self.sounds.get('ghost_warning')
        if warning_sound:
            if ghost_is_close and warning_sound.state != 'play':
                warning_sound.loop = True # 警告音循环
                warning_sound.play()
            elif not ghost_is_close and warning_sound.state == 'play':
                warning_sound.stop()


        for name, ghost in self.ghosts.items():
            # --- 更新目标 ---
            if time_to_recalculate or ghost.get('target') is None: # 使用 .get 以防 'target' 不存在
                if name == 'blinky':
                    # Blinky 目标：蛇身中点
                    if len(self.snake) > 0:
                        mid_index = len(self.snake) // 2
                        ghost['target'] = self.snake[mid_index]
                    else:
                        ghost['target'] = None # 蛇没了，原地待命？
                elif name == 'pinky':
                    # Pinky 目标：蛇头前方 4 格
                    if self.snake:
                        head_pos = self.snake[-1]
                        move_x, move_y = DIRECTIONS[self.direction]
                        target_x = head_pos[0] + move_x * PINKY_PREDICTION_DISTANCE
                        target_y = head_pos[1] + move_y * PINKY_PREDICTION_DISTANCE
                        # 检查目标是否越界
                        target_x = max(0, min(CANVAS_GRID_WIDTH - 1, target_x))
                        target_y = max(0, min(CANVAS_GRID_HEIGHT - 1, target_y))
                        ghost['target'] = (target_x, target_y)
                    else:
                        ghost['target'] = None

                # TODO: 如果实现了 A*，在这里计算路径
                # ghost['path'] = self.find_path(ghost['pos'], ghost['target'])
                # print(f"Ghost {name} target updated to: {ghost.get('target')}") # 调试信息

            # --- 移动逻辑 ---
            if ghost.get('target'):
                speed_factor = GHOST_BLINKY_SPEED_FACTOR if name == 'blinky' else GHOST_PINKY_SPEED_FACTOR
                ghost_speed = ghost_base_speed * speed_factor
                move_interval = 1.0 / ghost_speed if ghost_speed > 0 else float('inf')

                ghost['move_timer'] = ghost.get('move_timer', 0) + dt # 更新计时器
                if ghost['move_timer'] >= move_interval:
                    ghost['move_timer'] -= move_interval # 减去间隔，保留余量

                    # --- 简单的移动：直接朝目标移动一格 (无视障碍) ---
                    current_pos = ghost['pos']
                    target_pos = ghost['target']

                    dx = target_pos[0] - current_pos[0]
                    dy = target_pos[1] - current_pos[1]

                    next_pos = current_pos # 默认不动

                    # 选择主要移动方向 (x 或 y)
                    if abs(dx) > abs(dy): # X 方向优先
                        if dx > 0: next_pos = (current_pos[0] + 1, current_pos[1])
                        elif dx < 0: next_pos = (current_pos[0] - 1, current_pos[1])
                        else: # X 相同，尝试 Y
                            if dy > 0: next_pos = (current_pos[0], current_pos[1] + 1)
                            elif dy < 0: next_pos = (current_pos[0], current_pos[1] - 1)
                    else: # Y 方向优先 (或相等)
                        if dy > 0: next_pos = (current_pos[0], current_pos[1] + 1)
                        elif dy < 0: next_pos = (current_pos[0], current_pos[1] - 1)
                        else: # Y 相同，尝试 X
                            if dx > 0: next_pos = (current_pos[0] + 1, current_pos[1])
                            elif dx < 0: next_pos = (current_pos[0] - 1, current_pos[1])

                    # --- 碰撞检测 (鬼魂之间，鬼魂与尸体) ---
                    can_move = True
                    # 1. 检查是否撞墙
                    if not (0 <= next_pos[0] < CANVAS_GRID_WIDTH and 0 <= next_pos[1] < CANVAS_GRID_HEIGHT):
                        can_move = False
                        # print(f"Ghost {name} hit wall at {next_pos}")

                    # 2. 检查是否撞到其他鬼魂
                    for other_name, other_ghost in self.ghosts.items():
                        if name != other_name and next_pos == other_ghost['pos']:
                            can_move = False
                            # print(f"Ghost {name} collision with ghost {other_name} at {next_pos}")
                            break

                    # 3. 检查是否撞到尸体 (鬼魂不能穿过尸体)
                    if can_move:
                        for corpse in self.corpses:
                            if next_pos in corpse['parts']:
                                can_move = False
                                # print(f"Ghost {name} collision with corpse at {next_pos}")
                                break

                    # --- 更新位置 ---
                    if can_move:
                        ghost['pos'] = next_pos
                        # print(f"Ghost {name} moved to {next_pos}")
                    else:
                        # 如果不能朝主要方向移动，尝试次要方向 (如果之前没试过)
                        # (这里简化，暂时不实现次要方向尝试，鬼魂会被卡住)
                        # print(f"Ghost {name} blocked at {current_pos}, target {target_pos}")
                        pass

                    # --- 检查是否抓到蛇 (移动后检查) ---
                    # 注意：蛇移动时也会检查是否撞到鬼魂，这里是鬼魂移动时检查
                    if self.snake and ghost['pos'] == self.snake[-1]:
                         self.game_over(f"被{name}抓住了！")
                         return # 游戏结束，停止更新其他鬼魂


    # (A* Pathfinding - Placeholder)
    # def find_path(self, start_pos, end_pos):
    #     """使用 A* 算法查找路径 (需要实现)"""
    #     # 需要一个表示地图障碍的网格 (墙壁、尸体、其他鬼魂?)
    #     # 返回一个坐标列表 [(x1, y1), (x2, y2), ...] 或 None
    #     print("A* Pathfinding not implemented yet.")
    #     return None # 返回空路径，让鬼魂使用简单移动


    def move_snake(self):
        """计算蛇的下一步位置并更新状态 (完成版)"""
        if not self.snake: return # 蛇不存在则不移动

        # 更新实际方向
        self.direction = self.next_direction

        # 计算新蛇头位置
        head_x, head_y = self.snake[-1]
        move_x, move_y = DIRECTIONS[self.direction]
        new_head_x = head_x + move_x
        new_head_y = head_y + move_y

        # --- 碰撞检测 ---
        # 1. 撞墙检测
        if not (0 <= new_head_x < CANVAS_GRID_WIDTH and 0 <= new_head_y < CANVAS_GRID_HEIGHT):
            self.game_over("撞到墙壁！")
            return

        # 2. 撞自身检测
        if (new_head_x, new_head_y) in self.snake: # 检查整个蛇身，因为新头可能与旧尾重合（长度为1时）
             # 允许长度为2时头尾相撞（实际是追尾）
             if len(self.snake) > 2 or (new_head_x, new_head_y) != self.snake[0]:
                 self.game_over("撞到自己！")
                 return

        # 3. 撞尸体检测 (非融合碰撞)
        for corpse in self.corpses:
            # 排除融合情况 (头或尾)
            if (new_head_x, new_head_y) in corpse['parts'] and \
               (new_head_x, new_head_y) != corpse['parts'][0] and \
               (new_head_x, new_head_y) != corpse['parts'][-1]:
                self.game_over("撞到尸体中间！")
                return

        # 4. 撞炸弹果实检测
        fruit_type = self.fruits.get((new_head_x, new_head_y))
        if fruit_type == 'bomb':
             if 'death' in self.sounds: self.sounds['death'].play()
             self.game_over("碰到炸弹！")
             del self.fruits[(new_head_x, new_head_y)] # 移除炸弹
             return

        # 5. 撞鬼魂检测
        for name, ghost_data in self.ghosts.items():
             if (new_head_x, new_head_y) == ghost_data['pos']:
                 self.game_over(f"被 {name} 抓住了！")
                 return


        # --- 检查是否吃到果实或触发融合 ---
        ate_fruit = False
        merged_corpse_index = -1
        fruit_increase = 0

        # 检查普通果实和健康果实
        if fruit_type and fruit_type != 'bomb':
            ate_fruit = True
            del self.fruits[(new_head_x, new_head_y)] # 从字典中移除果实

            # 播放音效
            sound_name = f"pickup_{fruit_type}"
            if sound_name in self.sounds:
                self.sounds[sound_name].play()

            # 记录增加长度
            fruit_increase = 2 if fruit_type == 'healthy' else 1

            # 如果吃完后没有果实了，立即生成两个
            if not self.fruits:
                self.spawn_fruit(force_special=True)
                self.spawn_fruit()

        # 检查是否触发融合 (撞到尸体头或尾)
        else: # 只有在没吃到果实的地方才可能融合
            for i, corpse in enumerate(self.corpses):
                 corpse_parts = corpse['parts']
                 if not corpse_parts: continue # 跳过空尸体

                 touched_end = None
                 # 检查是否接触尸体尾部
                 if (new_head_x, new_head_y) == corpse_parts[0]:
                     touched_end = 'tail'
                 # 检查是否接触尸体头部
                 elif (new_head_x, new_head_y) == corpse_parts[-1]:
                     touched_end = 'head'

                 if touched_end:
                     merged_corpse_index = i
                     # 播放音效
                     if 'merge' in self.sounds: self.sounds['merge'].play()

                     # --- 执行融合逻辑 ---
                     # 1. 获取尸体部分并从列表移除
                     merged_corpse = self.corpses.pop(merged_corpse_index)
                     corpse_segments = merged_corpse['parts']

                     # 2. 确定新的蛇头位置和方向
                     if touched_end == 'tail': # 撞尾融头
                         new_head_pos = corpse_segments[-1] # 新蛇头在尸体头部
                         # 新方向：尸体倒数第二格指向头部的方向
                         if len(corpse_segments) >= 2:
                             p1 = corpse_segments[-2]
                             p2 = corpse_segments[-1]
                             dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                         else: # 尸体只有一格
                             dx, dy = DIRECTIONS[self.direction] # 保持原方向

                     else: # 撞头融尾 (touched_end == 'head')
                         new_head_pos = corpse_segments[0] # 新蛇头在尸体尾部
                         # 新方向：尸体第二格指向尾部的方向
                         if len(corpse_segments) >= 2:
                             p1 = corpse_segments[1]
                             p2 = corpse_segments[0]
                             dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                         else: # 尸体只有一格
                             dx, dy = DIRECTIONS[self.direction] # 保持原方向

                     # 更新蛇头位置 (注意：这里不直接修改 new_head_x/y, 而是修改最终的 snake 列表)
                     # new_head_x, new_head_y = new_head_pos # 不需要这行

                     # 更新方向
                     new_dir_found = False
                     for name, (vx, vy) in DIRECTIONS.items():
                         if vx == dx and vy == dy:
                             self.direction = name
                             self.next_direction = name
                             new_dir_found = True
                             break
                     if not new_dir_found:
                          print(f"Warning: Could not determine direction after merge. dx={dx}, dy={dy}")

                     # 3. 连接蛇身
                     if touched_end == 'tail': # 撞尾融头
                         # 新蛇 = 反转的尸体 + 旧蛇身 (除了旧头)
                         self.snake = list(reversed(corpse_segments)) + self.snake
                     else: # 撞头融尾
                         # 新蛇 = 尸体 + 旧蛇身 (除了旧头)
                         self.snake = corpse_segments + self.snake

                     # 4. 更新长度
                     self.snake_length = len(self.snake)
                     self.update_ui()
                     self.check_pinky_spawn() # 检查Pinky生成
                     # 融合后，蛇的位置已经完全更新，不需要再执行下面的添加头/移除尾操作
                     return # 结束本次移动

        # --- 更新蛇身 (常规移动或吃果实) ---
        # 将新头添加到列表末尾
        self.snake.append((new_head_x, new_head_y))

        # 根据是否吃到果实处理蛇尾和长度
        if not ate_fruit:
            self.snake.pop(0) # 没吃果实，移除尾巴
        else:
            # 吃到了果实，长度增加 fruit_increase
            # 如果增加1，上面 append 已经完成，长度自动+1
            # 如果增加2 (健康果实)，需要再增加一节 (相当于不移除尾巴)
            if fruit_increase == 1:
                pass # 长度已因 append 增加 1
            elif fruit_increase == 2:
                 # 相当于 append 了头，并且没有 pop 尾，长度净增 2
                 pass # 长度已因 append 增加 1，并且没有 pop 尾，再增 1

        # 统一更新长度变量
        self.snake_length = len(self.snake)
        self.update_ui()
        self.check_pinky_spawn() # 检查Pinky生成


    def spawn_fruit(self, force_special=False):
        """在画布随机空位置生成一个果实 (完成版)"""
        if len(self.fruits) >= MAX_FRUITS and not force_special:
            return

        occupied_cells = set(self.snake) | set(self.fruits.keys()) | set(g['pos'] for g in self.ghosts.values())
        for corpse in self.corpses:
            occupied_cells.update(corpse['parts'])

        available_cells = []
        for x in range(CANVAS_GRID_WIDTH):
            for y in range(CANVAS_GRID_HEIGHT):
                if (x, y) not in occupied_cells:
                    available_cells.append((x, y))

        if not available_cells:
            print("Warning: No space left to spawn fruit!")
            return

        pos = random.choice(available_cells)

        fruit_type = 'normal'
        possible_types = ['normal', 'healthy', 'bomb']
        if force_special:
            fruit_type = random.choice(['healthy', 'bomb'])
        else:
            fruit_type = random.choices(possible_types, weights=[0.7, 0.15, 0.15], k=1)[0]

        self.fruits[pos] = fruit_type

        # 如果是限时果实，设置移除定时器
        duration = None
        if fruit_type == 'healthy':
            duration = FRUIT_HEALTHY_DURATION
        elif fruit_type == 'bomb':
            duration = FRUIT_BOMB_DURATION

        if duration:
            # 使用 partial 传递参数给回调函数
            Clock.schedule_once(partial(self.remove_fruit, pos, fruit_type), duration)
            # print(f"Scheduled removal for {fruit_type} at {pos} in {duration}s")

    def remove_fruit(self, pos, expected_type, *args):
        """定时移除果实的回调函数"""
        # 检查果实是否还存在且类型匹配 (防止蛇先吃掉了)
        if pos in self.fruits and self.fruits[pos] == expected_type:
            del self.fruits[pos]
            # print(f"Timed fruit {expected_type} at {pos} removed.")
            # 如果移除后没有果实了，立即生成两个
            if not self.fruits:
                self.spawn_fruit(force_special=True)
                self.spawn_fruit()


    def game_over(self, reason=""):
        """处理游戏结束状态"""
        if self.game_state == 'game_over': return # 防止重复调用

        print(f"Game Over: {reason}")
        self.game_state = 'game_over'

        # 停止背景音乐和警告音
        if 'bgm' in self.sounds: self.sounds['bgm'].stop()
        if 'ghost_warning' in self.sounds: self.sounds['ghost_warning'].stop()
        # 播放死亡音效
        if 'death' in self.sounds: self.sounds['death'].play()

        # 显示结算弹窗 (由 update 循环处理)
        # self.show_game_over_popup() # 不在这里直接调用，让 update 处理

    def update_ui(self):
        """更新界面上的标签和按钮状态"""
        # 更新时长
        minutes = int(self.game_time // 60)
        seconds = int(self.game_time % 60)
        self.time_label.text = f'时长: {minutes}:{seconds:02d}'

        # 更新长度
        self.length_label.text = f'长度: {self.snake_length}'

        # 更新分裂按钮状态
        self.split_button.disabled = (self.snake_length <= SPLIT_DISABLE_LENGTH)

        # (如果实现了暂停，可以在这里更新暂停按钮文本等)

# --- Kivy App 类 ---
class SnakeApp(App):
    """应用程序主类"""
    def build(self):
        # 设置窗口标题
        self.title = '贪吃蛇 Kivy AI 版'
        # 创建并返回游戏主控件
        game = SnakeGame()
        # 在构建时调用一次 update_layout，确保初始布局正确
        Window.bind(on_load=game.ids.game_canvas.update_layout)
        return game

# --- 程序入口 ---
if __name__ == '__main__':
    # 设置窗口为横屏固定大小 (可选，Buildozer 的 orientation 设置更重要)
    # Window.size = (960, 540) # 模拟一个 16:9 的横屏尺寸
    # Window.fullscreen = 'auto' # 尝试使用全屏

    SnakeApp().run()
