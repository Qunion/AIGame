# -*- coding: utf-8 -*-
import pygame
import random
import time
from collections import deque
import sys
import os
import math
import json # For saving/loading game state like high scores

# --- 基本设置 ---
pygame.init()
pygame.font.init()

# --- 颜色定义 ---
COLOR_BLACK = (0, 0, 0)
COLOR_DARK_GRAY = (30, 30, 30)
COLOR_GRAY = (128, 128, 128)
COLOR_LIGHT_GRAY = (200, 200, 200)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_GOLD = (255, 215, 0)
COLOR_CYAN = (0, 255, 255)
COLOR_MAGENTA = (255, 0, 255)
COLOR_ORANGE = (255, 165, 0)

COLOR_NEON_BLUE = (0, 255, 255)
COLOR_NEON_PINK = (255, 0, 255)
COLOR_NEON_GREEN = (57, 255, 20)
COLOR_NEON_YELLOW = (255, 255, 0)
COLOR_NEON_ORANGE = (255, 165, 0)
COLOR_NEON_RED = (255, 0, 0)
COLOR_LIGHT_BLUE = (0, 191, 255) # 另一种蓝色

COLOR_GRID = (40, 40, 40)
COLOR_BRIGHT_GRID = (100, 100, 100)
COLOR_CLEAR_FLASH = (255, 255, 255)
COLOR_RULES_BACKGROUND = (20, 20, 40) # Dark blue/purple for rules background

# 关卡状态颜色
COLOR_LEVEL_LOCKED = COLOR_GRAY
COLOR_LEVEL_UNLOCKED = COLOR_YELLOW
COLOR_LEVEL_COMPLETED = COLOR_GREEN
COLOR_LEVEL_SELECTED_BORDER = COLOR_WHITE

# 特殊格子颜色
COLOR_KINGS_GAZE = (255, 255, 150, 100) # 淡黄色半透明
COLOR_BOMB = (139, 0, 0, 150) # 深红色半透明

# --- 字体 ---
# 尝试使用支持中文的字体
CJK_FONT_CANDIDATES = ['Microsoft YaHei', 'SimHei', 'DengXian', 'Arial Unicode MS', None] # None for default
selected_font = None
for font_name in CJK_FONT_CANDIDATES:
    try:
        if font_name:
            pygame.font.SysFont(font_name, 10) # Test if font exists
        selected_font = font_name
        print(f"使用字体: {selected_font if selected_font else '默认'}")
        break
    except:
        continue

try:
    FONT_SIZE_TINY = 16
    FONT_SIZE_SMALL = 20
    FONT_SIZE_NORMAL = 28
    FONT_SIZE_LARGE = 36
    FONT_SIZE_XLARGE = 52
    FONT_XXLARGE = 64 # For main title

    FONT_TINY = pygame.font.SysFont(selected_font, FONT_SIZE_TINY)
    FONT_SMALL = pygame.font.SysFont(selected_font, FONT_SIZE_SMALL)
    FONT_NORMAL = pygame.font.SysFont(selected_font, FONT_SIZE_NORMAL)
    FONT_LARGE = pygame.font.SysFont(selected_font, FONT_SIZE_LARGE)
    FONT_XLARGE = pygame.font.SysFont(selected_font, FONT_SIZE_XLARGE, bold=True)
    FONT_XXLARGE = pygame.font.SysFont(selected_font, FONT_XXLARGE, bold=True)
except Exception as e:
    print(f"警告: 字体加载失败 ({e})，使用默认字体。可能出现中文乱码。")
    FONT_SIZE_TINY = 16
    FONT_SIZE_SMALL = 20
    FONT_SIZE_NORMAL = 28
    FONT_SIZE_LARGE = 36
    FONT_SIZE_XLARGE = 52
    FONT_XXLARGE = 64
    FONT_TINY = pygame.font.Font(None, FONT_SIZE_TINY)
    FONT_SMALL = pygame.font.Font(None, FONT_SIZE_SMALL)
    FONT_NORMAL = pygame.font.Font(None, FONT_SIZE_NORMAL)
    FONT_LARGE = pygame.font.Font(None, FONT_SIZE_LARGE)
    FONT_XLARGE = pygame.font.Font(None, FONT_SIZE_XLARGE)
    FONT_XXLARGE = pygame.font.Font(None, FONT_XXLARGE)


# --- 日志记录器 ---
MAX_LOG_MESSAGES = 8 # Increased capacity for larger log area # 增加容量以适应更大的日志区域
log_queue = deque(maxlen=MAX_LOG_MESSAGES)
last_log_message = ""
log_repeat_count = 0
last_op_message = ""
op_sequence = ""
op_log_timer = 0

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """  # 获取资源的绝对路径,适用于开发环境和PyInstaller环境
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS  # PyInstaller创建一个临时文件夹并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
        # print(f"Running in PyInstaller temp folder: {base_path}") # Debug print  # 调试打印:在PyInstaller临时文件夹中运行
    except Exception:
        # _MEIPASS attribute not found, running in normal Python environment  # 未找到_MEIPASS属性,在普通Python环境中运行
        base_path = os.path.abspath(".")
        # print(f"Running in normal environment: {base_path}") # Debug print  # 调试打印:在普通环境中运行

    return os.path.join(base_path, relative_path)

def log_message(message, is_operation=False):
    global last_log_message, log_repeat_count, last_op_message, op_sequence, op_log_timer

    timestamp = time.strftime("%H:%M:%S", time.localtime())
    full_message = f"[{timestamp}] {message}"

    current_time = time.time()

    if is_operation:
        op_char = message # Assume message is just the operation character  # 假设消息只是操作字符
        if current_time - op_log_timer < 1.0 and last_op_message: # If last log was recent op  # 如果最后一条日志是最近的操作
            op_sequence += op_char
            if len(op_sequence) > 50: # Limit sequence length  # 限制序列长度
                 log_queue[-1] = last_op_message + op_sequence[:50] + "..."
            else:
                 log_queue[-1] = last_op_message + op_sequence
        else: # Start new operation sequence log  # 开始新的操作序列日志
             op_sequence = op_char
             last_op_message = f"[{timestamp}] 操作: "
             log_queue.append(last_op_message + op_sequence)
        op_log_timer = current_time
        last_log_message = log_queue[-1] # Update last message to combined op log  # 更新最后一条消息为组合的操作日志
    else:
        # Reset op tracking if a non-operation message comes in  # 如果收到非操作消息则重置操作跟踪
        op_sequence = ""
        last_op_message = ""
        # Avoid adding duplicate non-operation messages immediately  # 避免立即添加重复的非操作消息
        if full_message == last_log_message and log_queue:
             log_repeat_count +=1
             # Update last message with count if needed (optional)  # 如果需要,使用计数更新最后一条消息(可选)
             # log_queue[-1] = f"{full_message} (x{log_repeat_count + 1})"
        else:
             log_repeat_count = 0
             log_queue.append(full_message)
             last_log_message = full_message

    # print(full_message) # Optional debug output  # 可选的调试输出

# --- 游戏核心参数 ---
BLOCK_SIZE = 30 # Increased block size slightly
GRID_WIDTH = 10
GRID_HEIGHT = 20
NUM_LEVELS = 7

# --- 区域尺寸定义 (显著增大) ---
# 总览区域 (顶部)
OVERVIEW_AREA_HEIGHT = 120 # Increased height

# 游戏区域1 (主游戏区 - 左)
GAME_AREA1_WIDTH = GRID_WIDTH * BLOCK_SIZE # 300
GAME_AREA1_GRID_HEIGHT = GRID_HEIGHT * BLOCK_SIZE # 600
GAME_AREA1_CONTROLS_HEIGHT = 80 # Space above grid for timer/buttons
GAME_AREA1_HEIGHT = GAME_AREA1_GRID_HEIGHT + GAME_AREA1_CONTROLS_HEIGHT # Total height for Area 1

# 游戏区域2 (信息区 - 中)
GAME_AREA2_WIDTH = 300 # Increased width
GAME_AREA2_HEIGHT = GAME_AREA1_HEIGHT # Match total Area 1 height

# 日志区域 (底部)
LOG_AREA_HEIGHT = 180 # Significantly increased height

# --- 动态计算窗口尺寸 ---
def get_window_width(rules_visible):
    base_width = GAME_AREA1_WIDTH + GAME_AREA2_WIDTH
    if rules_visible:
        return base_width + RULES_AREA_WIDTH
    else:
        return base_width

WINDOW_HEIGHT = OVERVIEW_AREA_HEIGHT + GAME_AREA1_HEIGHT + LOG_AREA_HEIGHT
INITIAL_WINDOW_WIDTH = get_window_width(False) # 初始规则区隐藏

# 规则说明区域 (右侧，可隐藏)
RULES_AREA_WIDTH = 400 # Increased width
RULES_AREA_HEIGHT = WINDOW_HEIGHT # Match total window height
RULES_SCROLL_SPEED = 20  # 每次滚动的像素数
rules_scroll_y = 0  # 规则区域的滚动位置

# 各区域起始坐标 (动态计算 Y 坐标)
OVERVIEW_AREA_POS = (0, 0)
GAME_AREA1_Y = OVERVIEW_AREA_HEIGHT
GAME_AREA1_POS = (0, GAME_AREA1_Y) # Top-left of the entire Area 1 (including controls)
GAME_AREA1_GRID_POS_Y = GAME_AREA1_Y + GAME_AREA1_CONTROLS_HEIGHT # Y pos where grid actually starts
GAME_AREA2_POS = (GAME_AREA1_WIDTH, GAME_AREA1_Y)
RULES_AREA_POS = (GAME_AREA1_WIDTH + GAME_AREA2_WIDTH, 0)  # 从顶部开始
LOG_AREA_Y = OVERVIEW_AREA_HEIGHT + GAME_AREA1_HEIGHT
LOG_AREA_POS = (0, LOG_AREA_Y)

# --- 屏幕创建 (初始大小) ---
screen = pygame.display.set_mode((INITIAL_WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("多关卡俄罗斯方块 V2 - 优化布局")

# --- 背景图片加载 ---
background_image = None
background_image_original = None # Initialize to None
try:
    # --- Use resource_path to find the image ---
    image_path = resource_path("background.jpg")
    log_message(f"尝试加载背景图片于: {image_path}") # Log the path being used
    background_image_original = pygame.image.load(image_path).convert()
    log_message("背景图片加载成功。")
except FileNotFoundError:
    # This exception might still occur if --add-data failed or path is wrong
    log_message(f"错误：未找到背景图片 '{resource_path('background.jpg')}'。请确保打包时已包含该文件。")
    background_image_original = None # Ensure it's None on failure
except pygame.error as e:
    log_message(f"错误：加载背景图片时出错 - {e}")
    background_image_original = None # Ensure it's None on failure
except Exception as e: # Catch any other potential errors during path resolution or loading
    log_message(f"错误：获取资源路径或加载图片时发生未知错误 - {e}")
    background_image_original = None # Ensure it's None on failure

# --- Important Check: Ensure background_image_original is defined even after failure ---
# 重要检查：确保即使在加载失败后 background_image_original 也被定义
# This line should ideally not be needed if initialization and except blocks are correct,
# 如果初始化和异常处理块正确,这行代码理论上不需要
# but as a safeguard:
# 但作为安全保障:
if 'background_image_original' not in locals() and 'background_image_original' not in globals():
     log_message("警告: background_image_original 在加载块后仍未定义，强制设为 None。")
     background_image_original = None



# --- 按钮和UI元素 Rects (用于点击检测) ---
button_rects = {
    "level_left": None, "level_right": None, "rules_toggle": None,
    "start_pause": None, "restart": None
}
level_selector_diamond_rects = [] # 存储每个关卡菱形的Rect

# --- 方块形状定义 (保持不变) ---
SHAPES = [
    [[[1, 1, 1, 1]], [[1], [1], [1], [1]]], # I
    [[[1, 1], [1, 1]]], # O
    [[[0, 1, 0], [1, 1, 1]], [[1, 0, 0], [1, 1, 0], [1, 0, 0]], [[1, 1, 1], [0, 1, 0]], [[0, 1, 0], [1, 1, 0], [0, 1, 0]]], # T
    [[[0, 1, 1], [1, 1, 0]], [[1, 0, 0], [1, 1, 0], [0, 1, 0]]], # S
    [[[1, 1, 0], [0, 1, 1]], [[0, 1, 0], [1, 1, 0], [1, 0, 0]]], # Z
    [[[1, 0, 0], [1, 1, 1]], [[1, 1, 0], [1, 0, 0], [1, 0, 0]], [[1, 1, 1], [0, 0, 1]], [[0, 1, 0], [0, 1, 0], [1, 1, 0]]], # J
    [[[0, 0, 1], [1, 1, 1]], [[1, 0, 0], [1, 0, 0], [1, 1, 0]], [[1, 1, 1], [1, 0, 0]], [[1, 1, 0], [0, 1, 0], [0, 1, 0]]] # L
]
TETROMINO_COLORS = [COLOR_CYAN, COLOR_YELLOW, COLOR_MAGENTA, COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_ORANGE]

# --- Tetromino 类 (基本不变) ---
class Tetromino:
    def __init__(self, shape_index):
        self.shape_index = shape_index
        self.shapes = SHAPES[shape_index]
        self.rotation = 0
        self.shape = self.shapes[self.rotation]
        self.color_index = shape_index % len(TETROMINO_COLORS)
        self.color = TETROMINO_COLORS[self.color_index]
        self.grid_x = GRID_WIDTH // 2 - len(self.shape[0]) // 2
        self.grid_y = 0 # Start above the visible grid # 从可见网格上方开始

    def move(self, dx, dy):
        self.grid_x += dx
        self.grid_y += dy

    def rotate(self, clockwise=True):
        original_rotation = self.rotation
        if len(self.shapes) > 1: # Only rotate if multiple states exist # 只在有多个状态时才旋转
            if clockwise:
                self.rotation = (self.rotation + 1) % len(self.shapes)
            else:
                self.rotation = (self.rotation - 1) % len(self.shapes)
            self.shape = self.shapes[self.rotation]
        return original_rotation

    def get_block_positions(self, offset_x=0, offset_y=0):
        positions = []
        base_x = self.grid_x + offset_x
        base_y = self.grid_y + offset_y
        for r, row in enumerate(self.shape):
            for c, cell in enumerate(row):
                if cell:
                    positions.append((base_x + c, base_y + r))
        return positions

    def get_min_max_col(self):
        """获取当前形状占据的最小和最大列索引"""
        positions = self.get_block_positions()
        if not positions:
            return 0, 0
        min_col = min(p[0] for p in positions)
        max_col = max(p[0] for p in positions)
        return min_col, max_col

# --- 游戏板 ---
class Board:
    def __init__(self, width=GRID_WIDTH, height=GRID_HEIGHT):
        self.width = width
        self.height = height
        self.grid = [[0] * self.width for _ in range(self.height)]
        self.kings_gaze_cells = set() # For level 4/5 { (x,y), ... }
        self.bomb_cells = set()       # For level 6 { (x,y), ... }

    def reset(self):
        self.grid = [[0] * self.width for _ in range(self.height)]
        self.kings_gaze_cells.clear()
        self.bomb_cells.clear()

    def is_valid_position(self, tetromino, offset_x=0, offset_y=0):
        positions = tetromino.get_block_positions(offset_x, offset_y)
        for x, y in positions:
            if not (0 <= x < self.width and 0 <= y < self.height):
                return False
            # Only check grid collision for blocks inside the board height
            if y >= 0 and self.grid[y][x] != 0:
                return False
        return True

    def merge_tetromino(self, tetromino):
        color_val = tetromino.color_index + 1
        merged_coords = []
        positions = tetromino.get_block_positions()
        for x, y in positions:
            if 0 <= y < self.height and 0 <= x < self.width:
                 # Prevent merging outside bounds, though validation should prevent this
                 self.grid[y][x] = color_val
                 merged_coords.append((x,y))
        return merged_coords # 返回合并的格子坐标，用于计分

    def clear_lines(self):
        lines_cleared = 0
        cleared_indices = []
        cleared_blocks_count = 0
        new_grid = []
        for r in range(self.height - 1, -1, -1):
            row = self.grid[r]
            if all(cell != 0 for cell in row):
                lines_cleared += 1
                cleared_indices.append(r)
                cleared_blocks_count += self.width # 一整行
            else:
                new_grid.append(row)

        for _ in range(lines_cleared):
            new_grid.append([0] * self.width)

        self.grid = new_grid[::-1]
        return {'count': lines_cleared, 'indices': cleared_indices, 'blocks': cleared_blocks_count}

    def check_kings_gaze(self):
        if not self.kings_gaze_cells: return 0, 0

        filled_count = 0
        can_clear = True
        for x, y in self.kings_gaze_cells:
            if 0 <= y < self.height and 0 <= x < self.width and self.grid[y][x] != 0:
                filled_count += 1
            else:
                can_clear = False
                break # 一个没填满就不用检查了

        if can_clear and filled_count == len(self.kings_gaze_cells):
            cleared_count = 0
            for x, y in list(self.kings_gaze_cells): # Iterate over a copy
                if self.grid[y][x] != 0:
                    self.grid[y][x] = 0
                    cleared_count += 1
            self.kings_gaze_cells.clear() # Clear after activation
            return cleared_count, 100 # 固定100分
        return 0, 0

    def check_bomb_collision(self, tetromino):
        if not self.bomb_cells: return False
        positions = tetromino.get_block_positions()
        for x, y in positions:
             # Only check collision when the block is *within* the grid height
            if y >= 0 and (x, y) in self.bomb_cells:
                return True
        return False

    def add_random_gaze_cells(self, count):
        self.kings_gaze_cells.clear()
        if count <= 0: return
        # Try to place gaze cells away from the very top and bottom initially
        center_x = self.width // 2
        center_y = random.randint(self.height // 4, 3 * self.height // 4)
        start_cell = (max(0, min(self.width - 1, center_x)),
                      max(0, min(self.height - 1, center_y)))

        q = deque([start_cell])
        visited = {start_cell}
        if start_cell not in self.bomb_cells: # Avoid starting on a bomb
            self.kings_gaze_cells.add(start_cell)

        while len(self.kings_gaze_cells) < count and q:
            cx, cy = q.popleft()
            # Prioritize neighbors closer to center? Or just random? Random is simpler. # 是否优先选择更靠近中心的邻居格子？还是直接随机？随机更简单。
            neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
            random.shuffle(neighbors)

            for nx, ny in neighbors:
                if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                    visited.add((nx, ny)) # Mark visited regardless of adding
                    if len(self.kings_gaze_cells) < count:
                        # Ensure gaze cells don't overlap with bombs
                        if (nx, ny) not in self.bomb_cells:
                            self.kings_gaze_cells.add((nx, ny))
                            q.append((nx, ny))
                    else:
                        break
            if len(self.kings_gaze_cells) >= count: break

        if len(self.kings_gaze_cells) < count:
             log_message(f"警告: 未能生成全部 {count} 个凝视格子 (仅 {len(self.kings_gaze_cells)} 个).")
        else:
             log_message(f"生成 {len(self.kings_gaze_cells)} 个王的凝视格子。")

    def add_random_bombs(self, count):
        self.bomb_cells.clear()
        added = 0
        attempts = 0
        max_attempts = self.width * self.height * 5 # Increased attempts limit

        while added < count and attempts < max_attempts:
            x = random.randint(0, self.width - 1)
            # Bias bombs towards bottom 2/3, avoiding very top rows
            y = random.randint(max(3, self.height // 3), self.height - 1)

            # Check potential overlap with gaze cells and existing bombs
            potential_pos = (x, y)
            if potential_pos not in self.kings_gaze_cells and potential_pos not in self.bomb_cells:
                 self.bomb_cells.add(potential_pos)
                 added += 1
            attempts += 1

        if added < count:
            log_message(f"警告：未能生成全部 {count} 个炸弹 (仅 {added} 个)。")
        else:
            log_message(f"生成 {added} 个炸弹格子。")

    def is_top_out(self):
        """检查是否触顶 (第一行是否有方块)"""
        return any(self.grid[0][col] != 0 for col in range(self.width))

    def add_initial_blocks(self, count):
        """Carefully adds initial blocks, trying to avoid immediate game over."""
        added_count = 0
        attempts = 0
        max_attempts_per_block = 20

        target_board = self # Assume single board for this helper

        while added_count < count and attempts < count * max_attempts_per_block:
            attempts += 1
            shape_idx = random.randint(0, len(SHAPES) - 1)
            temp_tet = Tetromino(shape_idx)
            max_rot = len(temp_tet.shapes)
            temp_tet.rotation = random.randint(0, max_rot - 1)
            temp_tet.shape = temp_tet.shapes[temp_tet.rotation]

            # Try placing lower down, but check validity
            max_y = target_board.height - len(temp_tet.shape)
            min_y = target_board.height // 2 # Start dropping from halfway down
            if max_y < min_y: max_y = min_y # Ensure range is valid

            placed = False
            for y_attempt in range(max_y, min_y -1, -1): # Try from bottom up in the lower half
                 max_x = target_board.width - len(temp_tet.shape[0])
                 x_positions = list(range(max_x + 1))
                 random.shuffle(x_positions)
                 for x_attempt in x_positions:
                      temp_tet.grid_x = x_attempt
                      temp_tet.grid_y = y_attempt
                      if target_board.is_valid_position(temp_tet):
                           target_board.merge_tetromino(temp_tet)
                           added_count += 1
                           placed = True
                           break # Placed this block
                 if placed: break # Move to next block
            # If not placed after trying many positions, maybe the board is too full

        log_message(f"尝试添加 {count} 个初始方块，成功添加 {added_count} 个。")
        if target_board.is_top_out():
             log_message("警告：初始方块可能导致触顶！")
        return added_count


# --- 关卡定义 ---
LOCKED = 0
UNLOCKED = 1
COMPLETED = 2

class Level:
    def __init__(self, id, name, time_limit=180, unlock_score=100, # Default timer 180s
                 initial_blocks=0, speed_increase_factor=0.01, speed_interval=5,
                 gaze_cells=0, bomb_count=0, dual_board=False):
        self.id = id
        self.name = name
        self.time_limit = time_limit
        self.unlock_score = unlock_score
        self.initial_blocks = initial_blocks
        self.speed_increase_factor = speed_increase_factor
        self.speed_interval = speed_interval
        self.gaze_cells = gaze_cells
        self.bomb_count = bomb_count
        self.dual_board = dual_board # Level 7 Flag

# Unlock scores adjusted slightly for potentially longer games
LEVELS = [
    Level(id=1, name="关卡 1：新手上路", initial_blocks=5, unlock_score=100),
    Level(id=2, name="关卡 2：障碍挑战", initial_blocks=10, unlock_score=120),
    Level(id=3, name="关卡 3：极速狂飙", speed_increase_factor=0.03, unlock_score=150),
    Level(id=4, name="关卡 4：王的凝视 I", gaze_cells=10, unlock_score=200),
    Level(id=5, name="关卡 5：王的凝视 II", gaze_cells=15, unlock_score=300),
    Level(id=6, name="关卡 6：步步惊心", bomb_count=3, unlock_score=400),
    Level(id=7, name="关卡 7：时空穿梭", dual_board=True, unlock_score=500, time_limit=180) # Longer time for dual board?
]
NUM_LEVELS = len(LEVELS) # Ensure NUM_LEVELS matches LEVELS list

# --- 游戏状态管理 ---
SAVE_FILENAME = "tetris_multilevel_save.json"
class GameState:
    def __init__(self):
        self.level_states = [LOCKED] * NUM_LEVELS
        self.level_high_scores = [0] * NUM_LEVELS
        self.total_score = 0
        self.selected_level_index = 0
        self.rules_visible = False
        self.load_progress()
        if self.level_states[0] == LOCKED:
            self.level_states[0] = UNLOCKED

    def get_current_level_data(self):
        return LEVELS[self.selected_level_index]

    def can_select_level(self, index):
        return 0 <= index < NUM_LEVELS and self.level_states[index] != LOCKED

    def select_next_level(self):
        current_index = self.selected_level_index
        for i in range(current_index + 1, NUM_LEVELS):
            if self.can_select_level(i):
                self.selected_level_index = i
                log_message(f"切换到关卡 {i+1}")
                return True
        # Wrap around? No, stick to design doc.
        # Find first available if at end
        # for i in range(current_index):
        #     if self.can_select_level(i):
        #         self.selected_level_index = i
        #         log_message(f"切换到关卡 {i+1}")
        #         return True
        log_message("已经是最后一个可选关卡")
        return False


    def select_prev_level(self):
        current_index = self.selected_level_index
        for i in range(current_index - 1, -1, -1):
            if self.can_select_level(i):
                self.selected_level_index = i
                log_message(f"切换到关卡 {i+1}")
                return True
        # Wrap around? No.
        # Find last available if at start
        # for i in range(NUM_LEVELS - 1, current_index, -1):
        #     if self.can_select_level(i):
        #         self.selected_level_index = i
        #         log_message(f"切换到关卡 {i+1}")
        #         return True
        log_message("已经是第一个可选关卡")
        return False

    def complete_level(self, level_index, score):
        is_new_high = False
        if score > self.level_high_scores[level_index]:
            self.level_high_scores[level_index] = score
            log_message(f"关卡 {level_index+1} 新纪录: {score}!")
            is_new_high = True
        else:
            log_message(f"关卡 {level_index+1} 得分: {score} (未破纪录: {self.level_high_scores[level_index]})")


        # Mark as completed regardless of score (as per design doc, unlock based on score)
        if self.level_states[level_index] != COMPLETED:
            self.level_states[level_index] = COMPLETED
            log_message(f"关卡 {level_index+1} 已完成。")

        # Recalculate total score (sum of high scores)
        self.total_score = sum(self.level_high_scores)

        # Unlock next level if score condition met
        next_level_index = level_index + 1
        if next_level_index < NUM_LEVELS:
            current_level_data = LEVELS[level_index]
            if score >= current_level_data.unlock_score:
                if self.level_states[next_level_index] == LOCKED:
                    self.level_states[next_level_index] = UNLOCKED
                    log_message(f"恭喜！达到 {score} 分 (需 {current_level_data.unlock_score}), 解锁关卡 {next_level_index+1}！")
            else:
                 if self.level_states[next_level_index] == LOCKED:
                     log_message(f"关卡 {level_index+1} 得分 {score}，未达到解锁下一关所需分数 ({current_level_data.unlock_score})。")


        self.save_progress()
        return is_new_high

    def save_progress(self):
        try:
            data = {
                "states": self.level_states,
                "high_scores": self.level_high_scores,
                "total_score": self.total_score
            }
            with open(SAVE_FILENAME, "w") as f:
                json.dump(data, f, indent=4) # Use indent for readability
            # log_message("进度已保存。") # Avoid spamming log
        except Exception as e:
            log_message(f"错误：无法保存进度 - {e}")

    def load_progress(self):
        if not os.path.exists(SAVE_FILENAME):
             log_message("未找到存档文件，开始新游戏。")
             return

        try:
            with open(SAVE_FILENAME, "r") as f:
                data = json.load(f)
                loaded_states = data.get("states")
                loaded_scores = data.get("high_scores")

                # Basic validation
                if isinstance(loaded_states, list) and len(loaded_states) == NUM_LEVELS:
                     # Further check states are valid numbers
                     if all(isinstance(s, int) and s in [LOCKED, UNLOCKED, COMPLETED] for s in loaded_states):
                         self.level_states = loaded_states
                     else:
                         log_message("警告：存档中的关卡状态无效，重置状态。")
                         self.level_states = [UNLOCKED] + [LOCKED] * (NUM_LEVELS - 1) # Reset safely
                else:
                     log_message(f"警告：存档中的关卡状态数量 ({len(loaded_states) if loaded_states else 'N/A'}) 与当前游戏 ({NUM_LEVELS}) 不符，重置状态。")
                     self.level_states = [UNLOCKED] + [LOCKED] * (NUM_LEVELS - 1) # Reset safely

                if isinstance(loaded_scores, list) and len(loaded_scores) == NUM_LEVELS:
                     # Further check scores are numbers
                     if all(isinstance(s, (int, float)) for s in loaded_scores):
                         self.level_high_scores = [int(s) for s in loaded_scores] # Ensure ints
                     else:
                         log_message("警告：存档中的最高分包含无效数据，重置分数。")
                         self.level_high_scores = [0] * NUM_LEVELS
                else:
                     log_message(f"警告：存档中的最高分数量 ({len(loaded_scores) if loaded_scores else 'N/A'}) 与当前游戏 ({NUM_LEVELS}) 不符，重置分数。")
                     self.level_high_scores = [0] * NUM_LEVELS

                # Ensure first level is always playable
                if self.level_states[0] == LOCKED:
                     self.level_states[0] = UNLOCKED

                self.total_score = sum(self.level_high_scores) # Recalculate based on loaded high scores
                log_message("游戏进度已加载。")

        except json.JSONDecodeError:
            log_message(f"错误：无法解析存档文件 {SAVE_FILENAME}。将开始新游戏。")
            self._reset_to_default()
        except Exception as e:
            log_message(f"错误：加载进度时发生未知错误 - {e}。将开始新游戏。")
            self._reset_to_default()

    def _reset_to_default(self):
        """Resets the game state to default values."""
        self.level_states = [UNLOCKED] + [LOCKED] * (NUM_LEVELS - 1)
        self.level_high_scores = [0] * NUM_LEVELS
        self.total_score = 0
        self.selected_level_index = 0



# --- 绘制辅助函数 ---
def draw_text(surface, text, font, color, center=None, topleft=None, topright=None, bottomleft=None, bottomright=None, midleft=None, midright=None, max_width=None):
    if max_width:
         # Simple wrap if text exceeds max_width
         words = text.split(' ')
         lines = []
         current_line = ""
         for word in words:
              test_line = current_line + word + " "
              test_surf = font.render(test_line, True, color)
              if test_surf.get_width() <= max_width:
                   current_line = test_line
              else:
                   lines.append(current_line.strip())
                   current_line = word + " "
         lines.append(current_line.strip())

         rendered_lines = [font.render(line, True, color) for line in lines]
         line_height = font.get_height()
         total_height = len(rendered_lines) * line_height

         # Determine starting y position based on alignment
         start_y = 0
         if center: start_y = center[1] - total_height // 2
         elif topleft: start_y = topleft[1]
         elif topright: start_y = topright[1]
         elif bottomleft: start_y = bottomleft[1] - total_height
         elif bottomright: start_y = bottomright[1] - total_height
         elif midleft: start_y = midleft[1] - total_height // 2
         elif midright: start_y = midright[1] - total_height // 2

         blit_rects = []
         current_y = start_y
         for line_surf in rendered_lines:
              line_rect = line_surf.get_rect()
              # Determine x position based on alignment
              if center: line_rect.centerx = center[0]
              elif topleft: line_rect.left = topleft[0]
              elif topright: line_rect.right = topright[0]
              elif bottomleft: line_rect.left = bottomleft[0]
              elif bottomright: line_rect.right = bottomright[0]
              elif midleft: line_rect.left = midleft[0]
              elif midright: line_rect.right = midright[0]
              line_rect.top = current_y
              surface.blit(line_surf, line_rect)
              blit_rects.append(line_rect)
              current_y += line_height
         # Return the rect covering all lines (approximate)
         if blit_rects:
             full_rect = blit_rects[0].unionall(blit_rects[1:])
             return full_rect
         else: return pygame.Rect(0,0,0,0)


    else:
        # Original single-line drawing
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        if center: text_rect.center = center
        elif topleft: text_rect.topleft = topleft
        elif topright: text_rect.topright = topright
        elif bottomleft: text_rect.bottomleft = bottomleft
        elif bottomright: text_rect.bottomright = bottomright
        elif midleft: text_rect.midleft = midleft
        elif midright: text_rect.midright = midright
        surface.blit(text_surface, text_rect)
        return text_rect


def draw_diamond(surface, color, center_x, center_y, size, border_color=None, border_width=1, filled=True):
    half_size = size / 2
    points = [
        (center_x, center_y - half_size), (center_x + half_size, center_y),
        (center_x, center_y + half_size), (center_x - half_size, center_y)
    ]
    # Ensure points are integers for drawing
    int_points = [(int(p[0]), int(p[1])) for p in points]

    if filled:
        try: pygame.draw.polygon(surface, color, int_points)
        except ValueError: pass # Ignore potential "points must be integers" error if floats slip through

    if border_color:
        try: pygame.draw.polygon(surface, border_color, int_points, border_width)
        except ValueError: pass

    return pygame.Rect(center_x - half_size, center_y - half_size, size, size)

# --- UI 绘制函数 (大部分已在上一段代码中) ---
# Rewriting drawing functions for the new layout

def draw_block(surface, color, grid_x, grid_y, offset_x=0, offset_y=0, border=True, alpha=255, block_size=BLOCK_SIZE):
    """Draws a single block, allowing custom block_size for preview."""
    pixel_x = offset_x + grid_x * block_size
    pixel_y = offset_y + grid_y * block_size

    # Ensure color is RGB first, handle potential alpha in input
    base_color_rgb = color[:3]
    final_color_rgba = (*base_color_rgb, alpha)

    # Use SRCALPHA for transparency support
    block_surf = pygame.Surface((block_size, block_size), pygame.SRCALPHA)
    block_surf.fill(final_color_rgba)

    if border and block_size > 5: # Don't draw border if too small
        # Darker border
        border_color = tuple(max(0, c - 60) for c in base_color_rgb)
        border_color_with_alpha = (*border_color, alpha)
        pygame.draw.rect(block_surf, border_color_with_alpha, (0, 0, block_size, block_size), 1)

        # Subtle highlight on top/left edges
        highlight_color = tuple(min(255, c + 40) for c in base_color_rgb)
        highlight_color_with_alpha = (*highlight_color, alpha)
        pygame.draw.line(block_surf, highlight_color_with_alpha, (1, 1), (block_size - 2, 1)) # Top
        pygame.draw.line(block_surf, highlight_color_with_alpha, (1, 1), (1, block_size - 2)) # Left

    surface.blit(block_surf, (pixel_x, pixel_y))


def draw_tetromino(surface, tetromino, offset_x=0, offset_y=0, block_size=BLOCK_SIZE, alpha=255):
    """Draws the tetromino, allowing custom block_size and alpha."""
    if not tetromino: return
    positions = tetromino.get_block_positions()
    for x, y in positions:
        # Only draw blocks within or just above the grid area visually
        if y >= -2:
             draw_block(surface, tetromino.color, x, y, offset_x, offset_y, alpha=alpha, block_size=block_size)

def draw_board(surface, board, offset_x=0, offset_y=0):
    """Draws the fixed blocks on the board."""
    if not board: return
    for r, row in enumerate(board.grid):
        for c, cell_val in enumerate(row):
            if cell_val != 0:
                color_index = cell_val - 1
                if 0 <= color_index < len(TETROMINO_COLORS):
                    color = TETROMINO_COLORS[color_index]
                    draw_block(surface, color, c, r, offset_x, offset_y)
                else: # Fallback color for invalid index
                    draw_block(surface, COLOR_GRAY, c, r, offset_x, offset_y)


def draw_grid(surface, grid_offset_x, grid_offset_y, grid_pixel_width, grid_pixel_height):
    """Draws the game grid lines."""
    for x in range(grid_offset_x, grid_offset_x + grid_pixel_width + 1, BLOCK_SIZE):
        pygame.draw.line(surface, COLOR_GRID, (x, grid_offset_y), (x, grid_offset_y + grid_pixel_height))
    for y in range(grid_offset_y, grid_offset_y + grid_pixel_height + 1, BLOCK_SIZE):
        pygame.draw.line(surface, COLOR_GRID, (grid_offset_x, y), (grid_offset_x + grid_pixel_width, y))

def draw_drop_preview_lines(surface, tetromino, board, offset_x=0, offset_y=0):
    """Draws brighter vertical lines indicating the drop path edges."""
    if not tetromino or not board: return

    try:
        min_col, max_col = tetromino.get_min_max_col()

        line_y_start = offset_y
        line_y_end = offset_y + GRID_HEIGHT * BLOCK_SIZE

        left_line_x = offset_x + min_col * BLOCK_SIZE
        pygame.draw.line(surface, COLOR_BRIGHT_GRID, (left_line_x, line_y_start), (left_line_x, line_y_end), 2)

        right_line_x = offset_x + (max_col + 1) * BLOCK_SIZE
        pygame.draw.line(surface, COLOR_BRIGHT_GRID, (right_line_x, line_y_start), (right_line_x, line_y_end), 2)
    except Exception as e:
        # print(f"Error drawing preview lines: {e}") # Avoid console spam
        pass


def draw_clear_animation(surface, rows, progress, offset_x=0, offset_y=0):
    """Draws a flashing effect on cleared rows."""
    # Simple flash effect: solid white overlay that fades
    alpha = int(255 * math.sin(progress * math.pi)) # Fade in and out using sine wave
    if alpha < 0: alpha = 0
    flash_color = (*COLOR_CLEAR_FLASH[:3], alpha)
    flash_surface = pygame.Surface((GAME_AREA1_WIDTH, BLOCK_SIZE), pygame.SRCALPHA)
    flash_surface.fill(flash_color)

    for r in rows:
        surface.blit(flash_surface, (offset_x, offset_y + r * BLOCK_SIZE))

# --- Updated Area Drawing Functions ---

def draw_overview_area(surface, game_state):
    global button_rects, level_selector_diamond_rects
    # Full width for background/rule button positioning
    full_width = get_window_width(game_state.rules_visible)
    area_rect = pygame.Rect(OVERVIEW_AREA_POS, (full_width, OVERVIEW_AREA_HEIGHT))
    # Content should be relative to the fixed part of the window
    fixed_content_width = GAME_AREA1_WIDTH + GAME_AREA2_WIDTH

    # 1. Game Name (Smaller Font, Centered in Fixed Width)
    draw_text(surface, "多关卡俄罗斯方块", FONT_LARGE, COLOR_NEON_BLUE, # Use XLARGE instead of XXLARGE
              center=(fixed_content_width // 2, area_rect.y + 40))

    # 2. Level Selector (Positioned below title, Centered in Fixed Width)
    selector_y = area_rect.y + 90 # Lowered position
    # --- Base selector calculations on fixed_content_width ---
    selector_total_width = fixed_content_width * 0.5 # Use 50% of fixed width
    selector_center_x = fixed_content_width // 2
    level_spacing = selector_total_width / max(1, NUM_LEVELS)
    selector_start_x = selector_center_x - selector_total_width / 2 + level_spacing / 2

    # Draw connecting line (relative to fixed width calculations)
    line_start_x = selector_start_x - level_spacing / 2
    line_end_x = selector_start_x + (NUM_LEVELS - 1.5) * level_spacing
    pygame.draw.line(surface, COLOR_LIGHT_GRAY, (line_start_x, selector_y), (line_end_x, selector_y), 3) # Thicker line

    level_selector_diamond_rects = []
    for i in range(NUM_LEVELS):
        level_x = selector_start_x + i * level_spacing
        level_state = game_state.level_states[i]
        is_selected = (i == game_state.selected_level_index)

        diamond_color = COLOR_LEVEL_LOCKED
        if level_state == UNLOCKED: diamond_color = COLOR_LEVEL_UNLOCKED
        elif level_state == COMPLETED: diamond_color = COLOR_LEVEL_COMPLETED

        diamond_size = 24 # Base size
        border_color = None
        border_width = 2
        if is_selected:
            diamond_size = 36 # Larger when selected
            border_color = COLOR_LEVEL_SELECTED_BORDER
            border_width = 3

        diamond_rect = draw_diamond(surface, diamond_color, int(level_x), selector_y, diamond_size, border_color=border_color, border_width=border_width)
        level_selector_diamond_rects.append(diamond_rect)
        # Draw level number inside diamond
        text_color = COLOR_BLACK if diamond_color != COLOR_LEVEL_LOCKED else COLOR_WHITE
        num_font = FONT_SMALL if not is_selected else FONT_NORMAL
        draw_text(surface, str(i + 1), num_font, text_color, center=diamond_rect.center)

    # Arrows (Positioned relative to the fixed line ends)
    arrow_size = 30
    arrow_y = selector_y
    arrow_offset = 20 # Distance from line ends

    left_arrow_x = line_start_x - arrow_offset - arrow_size / 2
    right_arrow_x = line_end_x + arrow_offset + arrow_size / 2

    left_arrow_rect = pygame.Rect(0, 0, arrow_size, arrow_size)
    left_arrow_rect.center = (left_arrow_x, arrow_y)
    right_arrow_rect = pygame.Rect(0, 0, arrow_size, arrow_size)
    right_arrow_rect.center = (right_arrow_x, arrow_y)

    can_go_left = any(game_state.can_select_level(i) for i in range(game_state.selected_level_index))
    can_go_right = any(game_state.can_select_level(i) for i in range(game_state.selected_level_index + 1, NUM_LEVELS))

    left_arrow_color = COLOR_WHITE if can_go_left else COLOR_GRAY
    right_arrow_color = COLOR_WHITE if can_go_right else COLOR_GRAY

    # Draw filled arrows
    pygame.draw.polygon(surface, left_arrow_color, [(left_arrow_rect.right, left_arrow_rect.top), (left_arrow_rect.left, left_arrow_rect.centery), (left_arrow_rect.right, left_arrow_rect.bottom)])
    pygame.draw.polygon(surface, right_arrow_color, [(right_arrow_rect.left, right_arrow_rect.top), (right_arrow_rect.right, right_arrow_rect.centery), (right_arrow_rect.left, right_arrow_rect.bottom)])

    button_rects["level_left"] = left_arrow_rect
    button_rects["level_right"] = right_arrow_rect

    # 3. Total Score (Top Left - remains fixed)
    draw_text(surface, f"总分: {game_state.total_score}", FONT_NORMAL, COLOR_GOLD, topleft=(area_rect.x + 20, area_rect.y + 20))

    # 4. Rules Toggle Button (Top Right - relative to full width)
    rules_btn_width = 120
    rules_btn_height = 40
    rules_btn_rect = pygame.Rect(0, 0, rules_btn_width, rules_btn_height)
    # --- Position relative to the potentially changing area_rect.right ---
    rules_btn_rect.topright = (fixed_content_width - 20, area_rect.y + 20)
    btn_text = "规则 >>" if not game_state.rules_visible else "<< 规则"
    pygame.draw.rect(surface, COLOR_BLUE, rules_btn_rect, border_radius=8)
    draw_text(surface, btn_text, FONT_NORMAL, COLOR_WHITE, center=rules_btn_rect.center)
    button_rects["rules_toggle"] = rules_btn_rect


def draw_game_area1(surface, board, current_tetromino, game_timer, level_time_limit, clearing_state, game_active, is_paused, game_over_flag, level_complete_flag, current_level_data):
    """Draws Game Area 1 including controls above the grid."""
    area_rect = pygame.Rect(GAME_AREA1_POS, (GAME_AREA1_WIDTH, GAME_AREA1_HEIGHT))
    # pygame.draw.rect(surface, (50,0,0), area_rect) # Debug draw area

    # --- Controls Area (Top part of Area 1) ---
    controls_rect = pygame.Rect(area_rect.x, area_rect.y, area_rect.width, GAME_AREA1_CONTROLS_HEIGHT)
    # pygame.draw.rect(surface, (0,50,0), controls_rect) # Debug draw controls part

    # --- Timer Bar and Digital Time (Positioned together) ---
    timer_area_y = controls_rect.y + 10 # Y position for the timer stuff
    timer_bar_height = 20
    # --- Make bar shorter to leave space for text ---
    timer_bar_max_width = controls_rect.width * 0.6 # Bar uses 60% of width
    timer_bar_width = int(timer_bar_max_width)
    timer_bar_x = controls_rect.x + 20 # Left align bar with padding

    time_ratio = max(0, game_timer / level_time_limit) if level_time_limit > 0 else 0
    current_bar_width = int(timer_bar_width * time_ratio)

    # Draw Timer Bar
    timer_bar_rect = pygame.Rect(timer_bar_x, timer_area_y, timer_bar_width, timer_bar_height)
    pygame.draw.rect(surface, COLOR_DARK_GRAY, timer_bar_rect, border_radius=5)
    pygame.draw.rect(surface, COLOR_YELLOW, (timer_bar_x, timer_area_y, current_bar_width, timer_bar_height), border_radius=5)

    # Timer markers (Diamonds)
    num_segments = 3
    marker_size = timer_bar_height - 2
    for i in range(1, num_segments):
        segment_ratio = i / num_segments
        marker_x = timer_bar_x + int(timer_bar_width * segment_ratio)
        marker_color = COLOR_YELLOW if time_ratio >= segment_ratio else COLOR_GRAY
        draw_diamond(surface, marker_color, marker_x, timer_bar_rect.centery, marker_size, filled=True)

    # Digital Time (Positioned to the right of the bar)
    minutes = int(game_timer // 60)
    seconds = int(game_timer % 60)
    time_str = f"{minutes:01d}:{seconds:02d}"
    time_text_pos_x = timer_bar_rect.right + 15 # X position right of bar
    # Use midleft alignment to vertically center with the bar
    draw_text(surface, time_str, FONT_NORMAL, COLOR_WHITE, midleft=(time_text_pos_x, timer_bar_rect.centery))

    # --- Start/Pause/Restart Buttons (Positioned at the bottom of controls area) ---
    # Ensure buttons are below the timer stuff
    btn_width = 120
    btn_height = 40
    # Place buttons lower, ensuring space from timer
    btn_y = max(timer_bar_rect.bottom + 15, controls_rect.bottom - btn_height - 10)

    total_btn_width = 2 * btn_width
    gap = (controls_rect.width - total_btn_width) / 3
    start_pause_x = controls_rect.x + gap
    restart_x = start_pause_x + btn_width + gap

    start_pause_rect = pygame.Rect(start_pause_x, btn_y, btn_width, btn_height)
    restart_rect = pygame.Rect(restart_x, btn_y, btn_width, btn_height)

    # Draw buttons with appropriate text and color (Logic remains the same)
    btn_radius = 8
    if not game_active and not is_paused and not game_over_flag and not level_complete_flag: # Initial state
        pygame.draw.rect(surface, COLOR_GREEN, start_pause_rect, border_radius=btn_radius)
        draw_text(surface, "开始游戏", FONT_NORMAL, COLOR_BLACK, center=start_pause_rect.center)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, restart_rect, border_radius=btn_radius) # Dimmed restart
        draw_text(surface, "重新开始", FONT_NORMAL, COLOR_GRAY, center=restart_rect.center)
    elif is_paused:
        pygame.draw.rect(surface, COLOR_ORANGE, start_pause_rect, border_radius=btn_radius)
        draw_text(surface, "继续", FONT_NORMAL, COLOR_BLACK, center=start_pause_rect.center)
        pygame.draw.rect(surface, COLOR_RED, restart_rect, border_radius=btn_radius) # Active restart
        draw_text(surface, "重新开始", FONT_NORMAL, COLOR_BLACK, center=restart_rect.center)
    else: # Game is active and running
        pygame.draw.rect(surface, COLOR_GREEN, start_pause_rect, border_radius=btn_radius)
        draw_text(surface, "暂停", FONT_NORMAL, COLOR_BLACK, center=start_pause_rect.center)
        pygame.draw.rect(surface, COLOR_RED, restart_rect, border_radius=btn_radius) # Active restart
        draw_text(surface, "重新开始", FONT_NORMAL, COLOR_BLACK, center=restart_rect.center)

    button_rects["start_pause"] = start_pause_rect
    button_rects["restart"] = restart_rect

    # --- Actual Game Grid Area (Below controls) ---
    grid_offset_x = area_rect.x
    grid_offset_y = GAME_AREA1_GRID_POS_Y # Use the calculated grid start Y
    grid_pixel_width = GAME_AREA1_WIDTH
    grid_pixel_height = GAME_AREA1_GRID_HEIGHT

    draw_grid(surface, grid_offset_x, grid_offset_y, grid_pixel_width, grid_pixel_height)

    # Determine which board to draw (for Level 7)
    active_board = None
    if current_level_data.dual_board:
        # board is assumed to be a list [board1, board2] passed in
        if board and len(board) == 2:
            active_board = board[active_board_index] # Use the global active_board_index
        else:
             log_message("错误：双面板模式下 board 数据无效。")
             return # Avoid crashing
    else:
        active_board = board # board is the single board instance

    if not active_board: # Check if board exists before drawing on it
         # log_message("错误：无法绘制无效的游戏板。") # Avoid spam
         return

    # Draw Special Cells (Bombs, Gaze) - Background Layer
    for x, y in active_board.kings_gaze_cells:
        gaze_rect = pygame.Rect(grid_offset_x + x * BLOCK_SIZE, grid_offset_y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        gaze_surface = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
        gaze_surface.fill(COLOR_KINGS_GAZE)
        surface.blit(gaze_surface, gaze_rect.topleft)
    for x, y in active_board.bomb_cells:
        bomb_rect = pygame.Rect(grid_offset_x + x * BLOCK_SIZE, grid_offset_y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        bomb_surface = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
        bomb_surface.fill(COLOR_BOMB)
        surface.blit(bomb_surface, bomb_rect.topleft)
        draw_text(surface, "!", FONT_NORMAL, COLOR_WHITE, center=bomb_rect.center)

    # Draw Fixed Blocks
    draw_board(surface, active_board, grid_offset_x, grid_offset_y)

    # Draw Falling Piece & Preview Lines (If active state)
    if game_active and not clearing_state['active'] and current_tetromino:
        # Draw preview lines first so piece is on top
        draw_drop_preview_lines(surface, current_tetromino, active_board, grid_offset_x, grid_offset_y)
        # Draw the falling piece
        draw_tetromino(surface, current_tetromino, grid_offset_x, grid_offset_y)

    # Draw Clear Animation (If active state)
    if clearing_state['active']:
        progress = 1.0 - (clearing_state['timer'] / clearing_state['duration'])
        draw_clear_animation(surface, clearing_state['rows'], progress, grid_offset_x, grid_offset_y)


def draw_game_area2(surface, level_name, current_score, high_score, next_tetromino, score_anim_state):
    area_rect = pygame.Rect(GAME_AREA2_POS, (GAME_AREA2_WIDTH, GAME_AREA2_HEIGHT))
    # pygame.draw.rect(surface, (0,0,50), area_rect) # Debug draw area

    # Spacing things out vertically
    y_padding = 30
    current_y = area_rect.y + y_padding

    # High Score (Top)
    draw_text(surface, "本关最高", FONT_NORMAL, COLOR_LIGHT_GRAY, center=(area_rect.centerx, current_y))
    current_y += 35
    draw_text(surface, f"{high_score}", FONT_LARGE, COLOR_GOLD, center=(area_rect.centerx, current_y))
    current_y += FONT_LARGE.get_height() + y_padding + 10

    # Level Name
    # Use text wrapping if name is too long
    level_name_rect = draw_text(surface, level_name, FONT_LARGE, COLOR_NEON_BLUE, center=(area_rect.centerx, current_y), max_width=area_rect.width - 40)
    current_y += level_name_rect.height + y_padding + 20

    # Current Score
    score_color = COLOR_WHITE
    score_font = FONT_XLARGE # Make score prominent
    if score_anim_state['active']:
        # Simple blink effect
        if int(score_anim_state['timer'] * 10) % 2 == 0: score_color = COLOR_NEON_YELLOW
    draw_text(surface, "当前得分", FONT_NORMAL, COLOR_NEON_PINK, center=(area_rect.centerx, current_y))
    current_y += 40
    draw_text(surface, str(current_score), score_font, score_color, center=(area_rect.centerx, current_y))
    current_y += score_font.get_height() + y_padding + 30

    # Next Tetromino
    draw_text(surface, "下一个", FONT_LARGE, COLOR_NEON_GREEN, center=(area_rect.centerx, current_y))
    current_y += FONT_LARGE.get_height() + 20 # Space before preview box

    # Draw a box for the next piece preview
    preview_box_size = BLOCK_SIZE * 5 # Make box large enough for I piece
    preview_box_rect = pygame.Rect(0, 0, preview_box_size, preview_box_size)
    preview_box_rect.center = (area_rect.centerx, current_y + preview_box_size / 2)
    pygame.draw.rect(surface, COLOR_DARK_GRAY, preview_box_rect, border_radius=10)
    pygame.draw.rect(surface, COLOR_GRID, preview_box_rect, width=2, border_radius=10) # Border

    if next_tetromino:
        shape = next_tetromino.shape
        preview_block_size = BLOCK_SIZE # Use standard block size for consistency
        shape_pixel_width = len(shape[0]) * preview_block_size
        shape_pixel_height = len(shape) * preview_block_size

        # Center the shape within the preview box
        start_x = preview_box_rect.centerx - shape_pixel_width / 2
        start_y = preview_box_rect.centery - shape_pixel_height / 2

        # Draw preview blocks using draw_block helper
        for r, row in enumerate(shape):
            for c, cell in enumerate(row):
                if cell:
                    # Treat preview shape's top-left as (0,0) relative to start_x, start_y
                    draw_block(surface, next_tetromino.color, c, r,
                               offset_x=start_x, offset_y=start_y,
                               block_size=preview_block_size, border=True)


def draw_log_area(surface, log_messages):
    # Log area spans below Area 1 and Area 2 only
    log_area_width = GAME_AREA1_WIDTH + GAME_AREA2_WIDTH
    area_rect = pygame.Rect(LOG_AREA_POS[0], LOG_AREA_POS[1], log_area_width, LOG_AREA_HEIGHT)
    # pygame.draw.rect(surface, COLOR_DARK_GRAY, area_rect) # Background for log area

    # Draw border around log area
    pygame.draw.rect(surface, COLOR_GRID, area_rect, 1)

    log_title = "[游戏日志]"
    title_rect = draw_text(surface, log_title, FONT_NORMAL, COLOR_NEON_GREEN, topleft=(area_rect.x + 15, area_rect.y + 10))

    start_y = title_rect.bottom + 10 # Start logs below title
    line_height = FONT_SMALL.get_height() + 5 # Increased line spacing
    max_log_lines = max(1, (area_rect.bottom - start_y - 10) // line_height) # Calculate max lines based on available height
    visible_logs = list(log_messages)[-max_log_lines:] # Get the most recent logs that fit

    for i, msg in enumerate(visible_logs):
        log_y = start_y + i * line_height
        if log_y + line_height > area_rect.bottom - 5: break # Stop if next line won't fit

        # Simple wrap attempt within the log area width
        draw_text(surface, msg, FONT_SMALL, COLOR_WHITE, midleft=(area_rect.x + 20, log_y + line_height // 2), max_width=area_rect.width - 40)


# Update draw_rules_area positioning and add more detailed text
def draw_rules_area(surface, visible):
    global screen, rules_scroll_y  # 添加全局变量声明

    target_width = get_window_width(visible)
    current_width, current_height = screen.get_size()

    should_resize = False
    if visible and current_width < target_width:
         should_resize = True
    elif not visible and current_width > target_width:
         should_resize = True

    if should_resize:
         try:
             screen = pygame.display.set_mode((target_width, current_height))
             log_message(f"窗口大小调整为: {target_width}x{current_height}")
         except pygame.error as e:
             log_message(f"错误：调整窗口大小失败 - {e}")

    if not visible: 
        rules_scroll_y = 0  # 重置滚动位置
        return

    area_rect = pygame.Rect(RULES_AREA_POS, (RULES_AREA_WIDTH, RULES_AREA_HEIGHT))

    # 创建规则区域的表面
    rules_surface = pygame.Surface((RULES_AREA_WIDTH, RULES_AREA_HEIGHT), pygame.SRCALPHA)
    rules_surface.fill(COLOR_RULES_BACKGROUND)
    pygame.draw.rect(rules_surface, COLOR_GRID, (0, 0, RULES_AREA_WIDTH, RULES_AREA_HEIGHT), 1)

    rules_title = "游戏规则说明"
    title_rect = draw_text(rules_surface, rules_title, FONT_LARGE, COLOR_NEON_YELLOW, center=(RULES_AREA_WIDTH // 2, 40))

    # 定义规则文本
    rules_text = [
        "[基础操作]",
        " ← / → : 左右移动方块",
        " ↑     : 旋转方块 (顺时针)",
        " ↓     : 加速下落 (软降)",
        " 空格  : 瞬间下落 (硬降) / [关卡7] 时空切换",
        " P     : 暂停 / 继续游戏",
        " R     : (暂停/结束后) 重新开始本关",
        " ESC   : 退出游戏",
        "",
        "[通用规则]",
        "- 场地: 10格宽 x 20格高",
        "- 目标: 在限定时间内获得尽可能高的分数",
        "- 失败条件:",
        "  * 方块堆叠触顶 (新方块无法生成)",
        "  * [关卡6] 方块触碰炸弹格子",
        "  * 失败后不记录本关分数",
        "- 消除与得分:",
        "  * 填满整行即可消除该行方块",
        "  * 基础分: 每消除1个小方块得 1 分",
        "  * 额外奖励 (单次结算取最高项):",
        "    ≥ 20块: 额外 +10分",
        "    ≥ 30块: 额外 +20分",
        "    ≥ 40块: 额外 +40分",
        "  * 额外分数会以 (+N) 形式显示",
        "- 关卡进度:",
        "  * 完成关卡 (时间到) 后，若分数达到要求，则解锁下一关",
        "  * 总分 = 所有已完成关卡的最高分之和",
        "- 速度递增:",
        "  * 游戏进行中，方块下落速度会逐渐加快",
        "  * 默认: 每5秒增加 初始速度的 5%",
        "",
        "[特殊关卡机制]",
        "- 关卡 1 & 2: 初始掉落障碍方块",
        "- 关卡 3: 加速效果 x2 (每5秒 +10%)",
        "- 关卡 4 & 5: [王的凝视]",
        "  * 场地出现特定数量相连的黄色背景格",
        "  * 当所有黄格都被方块填满时，这些方块立即消除，并获得 100 分",
        "  * 消除后，黄格会重新生成",
        "- 关卡 6: [炸弹]",
        "  * 场地出现红色背景格 (炸弹)",
        "  * 正在下落的方块碰到任意炸弹格，本关立即失败",
        "- 关卡 7: [时空切换]",
        "  * 存在两个独立的游戏面板",
        "  * 按 [空格] 可将当前下落方块切换至另一面板的相同位置",
        "  * 若目标位置冲突，方块上移至最近合法位置",
        "  * 固定方块留在各自面板，两面板得分独立计算并累加",
    ]

    line_y = title_rect.bottom + 30
    line_height = FONT_SMALL.get_height() + 6
    left_margin = 20
    right_margin = RULES_AREA_WIDTH - 20
    text_width = right_margin - left_margin

    # 计算总内容高度
    total_content_height = 0
    for line in rules_text:
        if not line:
            total_content_height += line_height // 2
        else:
            text_surface = FONT_SMALL.render(line, True, COLOR_WHITE)
            total_content_height += text_surface.get_height() + 6

    # 限制滚动范围
    max_scroll = max(0, total_content_height - RULES_AREA_HEIGHT + 100)
    rules_scroll_y = max(0, min(rules_scroll_y, max_scroll))

    # 绘制规则文本
    current_y = line_y - rules_scroll_y
    for line in rules_text:
        if not line:
            current_y += line_height // 2
            continue

        color = COLOR_NEON_GREEN if line.startswith("[") else COLOR_WHITE
        text_rect = draw_text(rules_surface, line, FONT_SMALL, color, topleft=(left_margin, current_y), max_width=text_width)
        current_y += text_rect.height if text_rect.height > line_height else line_height

    # 将规则表面绘制到主表面
    surface.blit(rules_surface, area_rect)

    # 如果内容超出显示范围，绘制滚动条
    if total_content_height > RULES_AREA_HEIGHT:
        scrollbar_width = 10
        scrollbar_x = RULES_AREA_POS[0] + RULES_AREA_WIDTH - scrollbar_width - 5
        scrollbar_height = (RULES_AREA_HEIGHT / total_content_height) * RULES_AREA_HEIGHT
        scrollbar_y = RULES_AREA_POS[1] + (rules_scroll_y / total_content_height) * RULES_AREA_HEIGHT
        
        pygame.draw.rect(surface, COLOR_LIGHT_GRAY, (scrollbar_x, RULES_AREA_POS[1], scrollbar_width, RULES_AREA_HEIGHT), 1)
        pygame.draw.rect(surface, COLOR_GRAY, (scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height))

def draw_temp_score_message(surface, message, timer, max_time):
    if not message or timer <= 0: return
    fade_duration = 0.8 # Time to fade out at the end
    alpha = 255
    # Start fading only towards the end
    if timer < fade_duration:
        alpha = int(255 * (timer / fade_duration))
        alpha = max(0, min(255, alpha)) # Clamp alpha
    if alpha <= 0: return

    try:
        # Position the score message centrally above the main grid
        message_center_x = GAME_AREA1_POS[0] + GAME_AREA1_WIDTH // 2
        message_center_y = GAME_AREA1_GRID_POS_Y + 80 # Position higher up

        # Extract base score and bonus score if present
        base_msg = message
        bonus_msg = ""
        color = COLOR_GOLD # Base score color is gold

        # Improved splitting for format "+N" or "+N (+B)"
        if " (" in message and message.endswith(")"):
             parts = message.split(" (")
             base_msg = parts[0].strip() # e.g., "+10"
             bonus_part = parts[1].strip()[:-1] # e.g., "+10" (remove trailing ')')
             if bonus_part.startswith("+"):
                  bonus_msg = f"({bonus_part})" # Keep format "(+N)"
        # Else, message is just "+N"

        base_surf = FONT_XLARGE.render(base_msg, True, (*color[:3], alpha))
        base_rect = base_surf.get_rect(center=(message_center_x, message_center_y))

        # Draw base score first
        surface.blit(base_surf, base_rect)

        # Draw bonus score next to it if exists
        if bonus_msg:
             bonus_surf = FONT_LARGE.render(bonus_msg, True, (*COLOR_NEON_GREEN[:3], alpha)) # Bonus in green
             # Position bonus slightly to the right and aligned vertically
             bonus_rect = bonus_surf.get_rect(midleft=(base_rect.right + 15, base_rect.centery))
             surface.blit(bonus_surf, bonus_rect)

    except Exception as e:
         log_message(f"错误：绘制临时分数消息时出错 - {e}")


# --- 主游戏循环 ---
def main_game_loop():
    global screen, background_image, rules_scroll_y  # 添加全局变量声明

    clock = pygame.time.Clock()
    game_state = GameState()

    # --- Game Instance Variables (reset per level start) ---
    board = None # Will be Board instance or list [Board, Board] for L7
    # board2 = None # No longer needed, use board[1] if dual_board
    active_board_index = 0 # For level 7: 0 or 1
    current_tetromino = None
    next_tetromino = None
    current_level_score = 0
    game_timer = 0.0
    game_play_time = 0.0 # Tracks time within a level for speed increase
    fall_speed = 1.0 # Base speed seconds per grid cell
    fall_time = 0.0
    level_time_limit = 180 # Default, will be set by level data

    game_active = False # Is the game running (not paused, not in menu)
    is_paused = False
    game_over_flag = False
    level_complete_flag = False
    level_start_countdown = 0 # Optional: short delay before blocks fall
    new_high_score_flag = False # Flag to display new high score message

    # Animation states
    clearing_lines_state = {'active': False, 'timer': 0.0, 'rows': [], 'score_gain': 0, 'bonus_gain': 0, 'blocks_cleared': 0, 'duration': 0.3}
    score_animating_state = {'active': False, 'timer': 0.0, 'duration': 0.4}
    temp_score_msg = None
    temp_score_timer = 0.0
    TEMP_SCORE_DURATION = 2.5 # Slightly shorter duration

    # Key repeat for soft drop
    pygame.key.set_repeat(200, 35) # Faster repeat
    last_op_log_time = 0 # Throttle operation logs (handled in log_message now)

    # --- Helper function to start/reset a level ---
    def start_level(level_index):
        nonlocal board, active_board_index, current_tetromino, next_tetromino
        nonlocal current_level_score, game_timer, game_play_time, fall_speed, fall_time
        nonlocal game_active, is_paused, game_over_flag, level_complete_flag, level_time_limit
        nonlocal clearing_lines_state, score_animating_state, temp_score_msg, temp_score_timer
        nonlocal new_high_score_flag

        if not (0 <= level_index < NUM_LEVELS):
            log_message(f"错误：无效的关卡索引 {level_index}")
            return

        level_data = LEVELS[level_index]
        log_message(f"--- 开始关卡 {level_data.id}: {level_data.name} ---")
        new_high_score_flag = False # Reset flag

        # Initialize board(s)
        if level_data.dual_board:
            board = [Board(), Board()] # List containing two boards
            active_board_index = 0 # Start on board 0
            log_message("时空切换已激活！按空格切换面板。")
            # Apply initial state to BOTH boards
            for b in board:
                b.add_random_gaze_cells(level_data.gaze_cells)
                b.add_random_bombs(level_data.bomb_count)
                if level_data.initial_blocks > 0:
                    b.add_initial_blocks(level_data.initial_blocks // 2) # Split initial blocks roughly
            # Add any remainder to the first board
            if level_data.initial_blocks > 0 and level_data.initial_blocks % 2 != 0:
                 board[0].add_initial_blocks(1)
        else:
            board = Board() # Single board instance
            active_board_index = 0 # Not relevant but set to 0
            board.add_random_gaze_cells(level_data.gaze_cells)
            board.add_random_bombs(level_data.bomb_count)
            if level_data.initial_blocks > 0:
                 board.add_initial_blocks(level_data.initial_blocks)

        # Reset game variables
        current_tetromino = Tetromino(random.randint(0, len(SHAPES) - 1))
        next_tetromino = Tetromino(random.randint(0, len(SHAPES) - 1))
        # Ensure initial tetromino position is valid on the starting board
        start_board = board[0] if level_data.dual_board else board
        while not start_board.is_valid_position(current_tetromino) and current_tetromino.grid_y > -5:
             current_tetromino.move(0, -1) # Move up if initial spawn spot is blocked
        if not start_board.is_valid_position(current_tetromino):
             log_message("警告：无法在起始位置生成第一个方块！")
             # Potential early game over state, will be caught later


        current_level_score = 0
        level_time_limit = level_data.time_limit
        game_timer = level_time_limit
        game_play_time = 0.0
        fall_speed = 0.8 # Reset base fall speed (seconds per row)
        fall_time = 0.0
        game_active = False # Start paused as per requirement
        is_paused = False
        game_over_flag = False
        level_complete_flag = False

        # Reset animation/temp states
        clearing_lines_state = {'active': False, 'timer': 0.0, 'rows': [], 'score_gain': 0, 'bonus_gain': 0, 'blocks_cleared': 0, 'duration': 0.3}
        score_animating_state = {'active': False, 'timer': 0.0, 'duration': 0.4}
        temp_score_msg = None
        temp_score_timer = 0.0

        # Log level specific details
        if level_data.initial_blocks > 0: log_message(f"关卡效果：初始障碍 {level_data.initial_blocks} 个")
        if level_data.speed_increase_factor != 0.05: log_message(f"关卡效果：加速效果 x{level_data.speed_increase_factor / 0.05:.1f}")
        if level_data.gaze_cells > 0: log_message(f"关卡效果：王的凝视 {level_data.gaze_cells} 格")
        if level_data.bomb_count > 0: log_message(f"关卡效果：炸弹 {level_data.bomb_count} 个")


    # --- Main Loop ---
    running = True
    start_level(game_state.selected_level_index) # Start the initially selected level

    while running:
        delta_time = clock.tick(60) / 1000.0 # Time since last frame in seconds
        # Clamp delta_time to avoid large jumps if debugging or stalling
        delta_time = min(delta_time, 0.1)

        current_time = time.time()
        current_level_data = game_state.get_current_level_data()

        # Get the currently active board instance
        if current_level_data.dual_board:
            if isinstance(board, list) and len(board) == 2:
                current_board_instance = board[active_board_index]
            else:
                log_message("错误：双面板模式下无法获取当前面板实例！")
                # Maybe try to recover or just stop? Let's stop for safety.
                running = False
                continue
        else:
            current_board_instance = board # board is the single instance

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                log_message("请求退出。")
                break

            # --- Mouse Click Handling ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
                mouse_pos = event.pos

                # Always allow rules toggle
                if button_rects["rules_toggle"] and button_rects["rules_toggle"].collidepoint(mouse_pos):
                    game_state.rules_visible = not game_state.rules_visible
                    log_message("切换规则说明显示。")
                    # Window resizing handled in draw_rules_area

                # Check other buttons only if not in clearing animation
                if not clearing_lines_state['active']:
                    # Overview Area Buttons (Level Select) - Allow even if game over/paused
                    if button_rects["level_left"] and button_rects["level_left"].collidepoint(mouse_pos):
                        if game_state.select_prev_level():
                            start_level(game_state.selected_level_index)
                    elif button_rects["level_right"] and button_rects["level_right"].collidepoint(mouse_pos):
                        if game_state.select_next_level():
                            start_level(game_state.selected_level_index)
                    # Level Diamonds Click (Allow even if game over/paused)
                    for i, rect in enumerate(level_selector_diamond_rects):
                         if rect.collidepoint(mouse_pos) and game_state.can_select_level(i) and i != game_state.selected_level_index:
                             game_state.selected_level_index = i
                             log_message(f"直接选择关卡 {i+1}")
                             start_level(i)
                             break # Exit loop once clicked

                    # Game Area 1 Buttons (Start/Pause/Restart) - Only if not game over/level complete
                    if not game_over_flag and not level_complete_flag:
                        if button_rects["start_pause"] and button_rects["start_pause"].collidepoint(mouse_pos):
                             if not game_active and not is_paused: # Initial Start or Resume from pause
                                 if is_paused: # Resuming
                                     is_paused = False
                                     game_active = True
                                     log_message("游戏继续。")
                                 else: # Initial start
                                     log_message("游戏开始！")
                                     game_active = True
                                     is_paused = False
                                     game_timer = current_level_data.time_limit # Ensure timer starts fresh
                                     game_play_time = 0.0
                             elif game_active and not is_paused: # Pause
                                 is_paused = True
                                 game_active = False
                                 log_message("游戏暂停。")

                        elif button_rects["restart"] and button_rects["restart"].collidepoint(mouse_pos):
                             # Allow restart if paused or running
                             if is_paused or game_active:
                                 log_message("请求重新开始当前关卡。")
                                 start_level(game_state.selected_level_index)

            # --- Keyboard Input Handling ---
            if event.type == pygame.KEYDOWN:
                # Allow quit anytime
                if event.key == pygame.K_ESCAPE:
                    running = False; break

                if game_over_flag or level_complete_flag: # Only allow restart/quit after level end
                     if event.key == pygame.K_r:
                          log_message("按键 R 重新开始。")
                          start_level(game_state.selected_level_index)
                     continue # Ignore other keys

                if is_paused: # Only allow unpause (P/Enter) or restart (R) or quit (ESC)
                    if event.key == pygame.K_p or event.key == pygame.K_RETURN:
                        is_paused = False
                        game_active = True
                        log_message("游戏继续。")
                    elif event.key == pygame.K_r:
                        log_message("按键 R 重新开始。")
                        start_level(game_state.selected_level_index)
                    continue # Ignore other keys

                # Actions only if game is active and not clearing lines
                if game_active and not clearing_lines_state['active'] and current_tetromino:
                    op_char = ''
                    moved = False # Flag to check if any movement/rotation happened

                    if event.key == pygame.K_LEFT:
                        if current_board_instance.is_valid_position(current_tetromino, offset_x=-1):
                            current_tetromino.move(-1, 0); op_char = '←'; moved = True
                    elif event.key == pygame.K_RIGHT:
                        if current_board_instance.is_valid_position(current_tetromino, offset_x=1):
                            current_tetromino.move(1, 0); op_char = '→'; moved = True
                    elif event.key == pygame.K_DOWN: # Soft drop
                        if current_board_instance.is_valid_position(current_tetromino, offset_y=1):
                            current_tetromino.move(0, 1); op_char = '↓'; moved = True
                            fall_time = 0 # Reset auto-fall timer on manual drop
                    elif event.key == pygame.K_UP: # Rotate Clockwise
                         original_rotation = current_tetromino.rotation
                         original_x, original_y = current_tetromino.grid_x, current_tetromino.grid_y
                         current_tetromino.rotate(clockwise=True)
                         op_char = '↑'; moved = True # Assume rotation happens initially

                         if not current_board_instance.is_valid_position(current_tetromino):
                              # Basic Wall Kick Logic (Try L/R 1, then 2) - Can be improved (SRS kicks are complex)
                              kick_offsets = [1, -1, 2, -2]
                              kicked = False
                              for kick in kick_offsets:
                                   if current_board_instance.is_valid_position(current_tetromino, offset_x=kick):
                                        current_tetromino.move(kick, 0)
                                        kicked = True; break
                              # Add vertical kicks? Maybe simple check for I piece near floor
                              if not kicked and current_tetromino.shape_index == 0: # Special I piece kicks
                                   if current_board_instance.is_valid_position(current_tetromino, offset_y=-1):
                                       current_tetromino.move(0,-1); kicked = True
                                   elif current_board_instance.is_valid_position(current_tetromino, offset_y=-2):
                                       current_tetromino.move(0,-2); kicked = True


                              if not kicked: # Rotation failed even with kicks
                                   # Revert rotation and position
                                   current_tetromino.rotation = original_rotation
                                   current_tetromino.shape = current_tetromino.shapes[current_tetromino.rotation]
                                   current_tetromino.grid_x = original_x
                                   current_tetromino.grid_y = original_y
                                   moved = False # Rotation ultimately failed

                    elif event.key == pygame.K_SPACE: # Hard Drop or Level 7 Switch
                        moved = True # Space always counts as an action
                        if current_level_data.dual_board:
                             # --- Level 7: Time-Space Switch ---
                             log_message("尝试时空切换...", is_operation=False)
                             inactive_board_index = 1 - active_board_index
                             inactive_board = board[inactive_board_index] # Get the other board
                             op_char = '⇋' # Switch symbol

                             # Check collision in the *other* board at current piece position
                             if inactive_board.is_valid_position(current_tetromino):
                                 active_board_index = inactive_board_index # Switch active board
                                 log_message(f"切换到面板 {active_board_index + 1}")
                             else:
                                 # Collision on switch: try moving piece up until valid on target board
                                 original_y = current_tetromino.grid_y
                                 moved_up = False
                                 # Check up to 5 cells up? More might be excessive
                                 for dy_up in range(1, 6):
                                     if inactive_board.is_valid_position(current_tetromino, offset_y=-dy_up):
                                         current_tetromino.move(0, -dy_up)
                                         active_board_index = inactive_board_index
                                         log_message(f"切换到面板 {active_board_index + 1} (向上移动 {dy_up} 格)")
                                         moved_up = True
                                         break
                                 if not moved_up:
                                     log_message("切换失败：目标位置冲突且无法上移！")
                                     op_char = '' # Indicate failure
                                     moved = False # Action failed

                        else:
                            # --- Normal Hard Drop ---
                            op_char = '░' # Hard drop symbol
                            drop_distance = 0
                            while current_board_instance.is_valid_position(current_tetromino, offset_y=1):
                                current_tetromino.move(0, 1)
                                drop_distance += 1

                            if drop_distance == 0 and not current_board_instance.is_valid_position(current_tetromino):
                                 # If hard drop immediately invalid (e.g., piece already blocked)
                                 # This shouldn't happen if logic is right, but as a failsafe:
                                 log_message("硬降失败 - 位置无效")
                                 op_char = ''
                                 moved = False
                            else:
                                 # Force lock timer to expire after hard drop
                                 fall_time = fall_speed # Trigger lock check immediately

                    # Log the operation character if an action occurred
                    if moved and op_char:
                        log_message(op_char, is_operation=True)

                    # Check for bomb collision immediately after any move/rotation
                    if moved and current_level_data.bomb_count > 0:
                         if current_board_instance.check_bomb_collision(current_tetromino):
                              game_over_flag = True
                              is_active = False
                              log_message("游戏结束 - 踩到炸弹了！")
                              # Score is not recorded on failure


        # --- Game Logic Update ---
        if not running: break

        # Update timers if game is active and not paused
        if game_active and not is_paused and not game_over_flag and not level_complete_flag:
            game_timer = max(0, game_timer - delta_time)
            game_play_time += delta_time

            # Update animation timers
            if temp_score_timer > 0:
                temp_score_timer = max(0, temp_score_timer - delta_time)
                if temp_score_timer == 0: temp_score_msg = None
            if score_animating_state['active']:
                score_animating_state['timer'] = max(0, score_animating_state['timer'] - delta_time)
                if score_animating_state['timer'] == 0: score_animating_state['active'] = False

            # Handle clearing animation state
            if clearing_lines_state['active']:
                clearing_lines_state['timer'] = max(0, clearing_lines_state['timer'] - delta_time)
                if clearing_lines_state['timer'] == 0:
                    # --- Animation Finished ---
                    clearing_lines_state['active'] = False

                    # Add score AFTER animation
                    score_to_add = clearing_lines_state['score_gain'] + clearing_lines_state['bonus_gain']
                    current_level_score += score_to_add

                    # Log score gain clearly
                    log_message(f"得分: +{clearing_lines_state['score_gain']} (消除 {clearing_lines_state['blocks_cleared']} 块)" +
                                (f" 额外 +{clearing_lines_state['bonus_gain']}" if clearing_lines_state['bonus_gain'] > 0 else ""))

                    # Trigger score number flashing animation
                    score_animating_state['active'] = True
                    score_animating_state['timer'] = score_animating_state['duration']

                    # Spawn next piece
                    current_tetromino = next_tetromino
                    next_tetromino = Tetromino(random.randint(0, len(SHAPES) - 1))

                    # Check Game Over on new piece spawn
                    if not current_board_instance.is_valid_position(current_tetromino):
                        # Try moving up slightly in case spawn point is just blocked
                        moved_up = False
                        for dy_up in range(1, 3):
                             if current_board_instance.is_valid_position(current_tetromino, offset_y=-dy_up):
                                  current_tetromino.move(0, -dy_up)
                                  moved_up = True
                                  break
                        if not moved_up:
                            game_over_flag = True
                            game_active = False
                            log_message("游戏结束 - 触顶！新方块无法放置。")
                            # Score not recorded

                # Else: Continue clearing animation, skip normal game logic below

            # --- Normal Game Flow (If not clearing lines) ---
            elif current_tetromino: # Ensure there IS a piece to control
                # Apply speed increase based on play time
                time_based_speed_multiplier = (1.0 - current_level_data.speed_increase_factor) ** math.floor(game_play_time / current_level_data.speed_interval)
                current_fall_speed_seconds = 0.8 * time_based_speed_multiplier # Base speed 0.8s/row
                current_fall_speed_seconds = max(0.05, current_fall_speed_seconds) # Minimum fall speed 0.05s/row (20 rows/sec max)

                # Log speed increase only when it changes significantly
                if abs(current_fall_speed_seconds - fall_speed) > 0.01:
                     log_message(f"速度提升: {current_fall_speed_seconds:.2f} 秒/格")
                     fall_speed = current_fall_speed_seconds

                # --- Automatic Fall & Locking ---
                fall_time += delta_time

                # Check if soft dropping (key held down)
                keys = pygame.key.get_pressed()
                soft_dropping = keys[pygame.K_DOWN]
                # Make soft drop significantly faster than normal fall
                effective_fall_speed = fall_speed / 5.0 if soft_dropping else fall_speed

                # Time to move down?
                should_fall = fall_time >= effective_fall_speed

                if should_fall:
                    fall_time %= effective_fall_speed # Keep remainder for next frame

                    # Check if piece can move down
                    if current_board_instance.is_valid_position(current_tetromino, offset_y=1):
                        current_tetromino.move(0, 1)
                        # Check for bomb collision *after* moving down
                        if current_level_data.bomb_count > 0 and current_board_instance.check_bomb_collision(current_tetromino):
                            game_over_flag = True
                            game_active = False
                            log_message("游戏结束 - 踩到炸弹了！")
                            # Score not recorded
                    else:
                        # --- Cannot move down - LOCK piece ---
                        merged_coords = current_board_instance.merge_tetromino(current_tetromino)
                        # Score is calculated based on clears, not merge count directly in this version

                        # 1. Check King's Gaze activation (Level 4/5)
                        gaze_cleared_blocks, gaze_score = 0, 0
                        if current_level_data.gaze_cells > 0:
                             gaze_cleared_blocks, gaze_score = current_board_instance.check_kings_gaze()
                             if gaze_score > 0:
                                 log_message(f"王的凝视激活！消除 {gaze_cleared_blocks} 格，获得 {gaze_score} 分！")
                                 # Regenerate gaze cells immediately after activation
                                 current_board_instance.add_random_gaze_cells(current_level_data.gaze_cells)

                        # 2. Check Line Clears
                        clear_info = current_board_instance.clear_lines()
                        lines_cleared_now = clear_info['count']
                        line_cleared_blocks = clear_info['blocks']

                        # Total blocks cleared this turn (lines + gaze)
                        total_blocks_cleared_this_turn = line_cleared_blocks + gaze_cleared_blocks

                        if total_blocks_cleared_this_turn > 0:
                             # Calculate score earned THIS TURN
                             base_score_gain = total_blocks_cleared_this_turn # 1 point per block
                             bonus_score_gain = 0
                             # Check bonus thresholds
                             if total_blocks_cleared_this_turn >= 40: bonus_score_gain = 40
                             elif total_blocks_cleared_this_turn >= 30: bonus_score_gain = 20
                             elif total_blocks_cleared_this_turn >= 20: bonus_score_gain = 10

                             # Total includes base block score, gaze score, and line clear bonus
                             turn_score_gain = base_score_gain + gaze_score + bonus_score_gain

                             # Start clearing animation, store score to be added AFTER animation
                             clearing_lines_state['active'] = True
                             clearing_lines_state['timer'] = clearing_lines_state['duration']
                             clearing_lines_state['rows'] = clear_info['indices'] # Rows for visual effect
                             clearing_lines_state['score_gain'] = base_score_gain + gaze_score # Store base + gaze
                             clearing_lines_state['bonus_gain'] = bonus_score_gain # Store bonus separately
                             clearing_lines_state['blocks_cleared'] = total_blocks_cleared_this_turn

                             # Show temp score message immediately
                             temp_score_msg = f"+{base_score_gain + gaze_score}"
                             if bonus_score_gain > 0:
                                  temp_score_msg += f" (+{bonus_score_gain})"
                             temp_score_timer = TEMP_SCORE_DURATION

                             # Next piece spawn is deferred until animation ends

                        else: # No clears, spawn next piece immediately
                            current_tetromino = next_tetromino
                            next_tetromino = Tetromino(random.randint(0, len(SHAPES) - 1))
                            # Check game over on spawn
                            if not current_board_instance.is_valid_position(current_tetromino):
                                # Try moving up slightly
                                moved_up = False
                                for dy_up in range(1, 3):
                                    if current_board_instance.is_valid_position(current_tetromino, offset_y=-dy_up):
                                        current_tetromino.move(0, -dy_up)
                                        moved_up = True
                                        break
                                if not moved_up:
                                    game_over_flag = True
                                    game_active = False
                                    log_message("游戏结束 - 触顶！新方块无法放置。")
                                    # Score not recorded

            # Check Timer Ran Out (Only if game hasn't already ended)
            if game_timer <= 0 and not game_over_flag and not level_complete_flag:
                 level_complete_flag = True
                 game_active = False
                 is_paused = False # Ensure not paused
                 log_message("时间到！关卡结束，结算分数...")
                 # Call complete_level to save score, check high score, unlock next
                 new_high_score_flag = game_state.complete_level(game_state.selected_level_index, current_level_score)


        # --- Drawing ---
        current_window_width = get_window_width(game_state.rules_visible)

        # 1. Draw Background Image (if loaded) - Only behind main areas
        screen.fill(COLOR_BLACK) # Fallback background
        # --- Check if background_image_original exists before using it ---
        if background_image_original:
            main_area_width = GAME_AREA1_WIDTH + GAME_AREA2_WIDTH
            main_area_height = WINDOW_HEIGHT # Background spans full window height behind main areas

            # Scale background only if necessary, use the original image for scaling
            if background_image is None or background_image.get_width() != main_area_width or background_image.get_height() != main_area_height:
                 try:
                     # --- Use background_image_original here ---
                     scaled_bg = pygame.transform.smoothscale(background_image_original, (main_area_width, main_area_height))
                     background_image = scaled_bg # Cache scaled version
                     log_message("背景图片已缩放。") # Add log for scaling
                 except Exception as e:
                     log_message(f"错误：无法缩放背景图片 - {e}")
                     background_image = None # Disable if scaling fails

            if background_image:
                 screen.blit(background_image, (0, 0))
        # --- If original image wasn't loaded, background_image remains None ---
        

        # 2. Draw Main Game Areas on top of background
        draw_overview_area(screen, game_state)
        # Pass board correctly (list for dual, instance for single)
        # Draw Game Area 1 (Main Play Area + Controls Above)
        draw_game_area1(screen, board, current_tetromino, game_timer, level_time_limit,
                clearing_lines_state, game_active, is_paused,
                game_over_flag, level_complete_flag, # <-- 添加这两个标志
                current_level_data)
        draw_game_area2(screen, current_level_data.name, current_level_score,
                        game_state.level_high_scores[game_state.selected_level_index],
                        next_tetromino, score_animating_state)
        draw_log_area(screen, log_queue) # Log area uses fixed width below Area1+2

        # 3. Draw Rules Area (Handles its own background and window resizing)
        draw_rules_area(screen, game_state.rules_visible)

        # 4. Draw Temp Score Message (On top of game areas)
        if temp_score_msg and temp_score_timer > 0:
            draw_temp_score_message(screen, temp_score_msg, temp_score_timer, TEMP_SCORE_DURATION)

        # 5. Draw Pause/Game Over/Level Complete Overlays (On top of everything)
        overlay_font_color = COLOR_NEON_YELLOW
        overlay_bg_alpha = 180

        if is_paused:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, overlay_bg_alpha))
            screen.blit(overlay, (0, 0))
            draw_text(screen, "游戏暂停", FONT_XLARGE, overlay_font_color, center=(current_window_width // 2, WINDOW_HEIGHT // 2 - 30))
            draw_text(screen, "按 P 或 Enter 继续 / R 重新开始", FONT_NORMAL, COLOR_WHITE, center=(current_window_width // 2, WINDOW_HEIGHT // 2 + 40))

        elif game_over_flag:
             overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, overlay_bg_alpha))
             screen.blit(overlay, (0, 0))
             draw_text(screen, "游戏失败", FONT_XLARGE, COLOR_NEON_RED, center=(current_window_width // 2, WINDOW_HEIGHT // 2 - 40))
             # Display final score even on failure? Design doc says no score recorded. Let's not show it.
             # draw_text(screen, f"最终得分: {current_level_score}", FONT_LARGE, COLOR_WHITE, center=(current_window_width // 2, WINDOW_HEIGHT // 2 + 20))
             draw_text(screen, "按 R 重新开始", FONT_NORMAL, COLOR_WHITE, center=(current_window_width // 2, WINDOW_HEIGHT // 2 + 30))

        elif level_complete_flag:
             overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, overlay_bg_alpha))
             screen.blit(overlay, (0, 0))
             draw_text(screen, "关卡完成", FONT_XLARGE, COLOR_NEON_GREEN, center=(current_window_width // 2, WINDOW_HEIGHT // 2 - 80))
             draw_text(screen, f"得分: {current_level_score}", FONT_LARGE, COLOR_WHITE, center=(current_window_width // 2, WINDOW_HEIGHT // 2 - 20))
             if new_high_score_flag:
                  draw_text(screen, "新纪录!", FONT_NORMAL, COLOR_GOLD, center=(current_window_width // 2, WINDOW_HEIGHT // 2 + 20))
             draw_text(screen, "按 箭头 选择下一关 / R 重玩本关", FONT_NORMAL, COLOR_WHITE, center=(current_window_width // 2, WINDOW_HEIGHT // 2 + 70))


        pygame.display.flip() # Update the full screen

    # --- End of Main Loop ---
    game_state.save_progress() # Save on graceful exit
    log_message("--- 游戏退出 ---")

# --- Run ---
if __name__ == '__main__':
    # Initialize log buffer before starting
    log_message("--- 游戏初始化 ---")
    main_game_loop()
    pygame.quit()
    sys.exit()