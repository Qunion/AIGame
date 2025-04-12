import pygame
import os

# --- Core Settings ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
WINDOW_TITLE = "增强版贪吃蛇" # Changed to Chinese
FPS = 60 # Target frames per second

# --- Grid & Canvas ---
# Canvas grid dimensions match the screen aspect ratio better
CANVAS_GRID_WIDTH = 71
CANVAS_GRID_HEIGHT = 40

# Calculate GRID_SIZE to fit the canvas onto the screen
# Use the dimension that restricts the size the most
GRID_SIZE_W = SCREEN_WIDTH // CANVAS_GRID_WIDTH
GRID_SIZE_H = SCREEN_HEIGHT // CANVAS_GRID_HEIGHT
GRID_SIZE = min(GRID_SIZE_W, GRID_SIZE_H) # Use the smaller size to ensure fit (likely 27)

# Canvas size in pixels is now the same as the grid dimensions * GRID_SIZE
# This might not perfectly match SCREEN_WIDTH/HEIGHT if GRID_SIZE caused rounding.
# We'll draw centered or with black bars if needed, handled in drawing.
CANVAS_WIDTH_PX = CANVAS_GRID_WIDTH * GRID_SIZE
CANVAS_HEIGHT_PX = CANVAS_GRID_HEIGHT * GRID_SIZE

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
YELLOW = (255, 255, 0)
DARK_YELLOW = (200, 200, 0) # Base snake color
GREY = (128, 128, 128)
# Adjusted alpha slightly for potentially smaller grid lines
GRID_COLOR = (200, 200, 200, 80) # Light grey with transparency

# --- Game Mechanics - TUNABLE PARAMETERS ---
INITIAL_SNAKE_LENGTH = 3
# Adjusted base speed: Since grid size is halved, double steps/sec for same visual speed
BASE_SNAKE_SPEED_PPS = 10.0 # Grids per second at the start 【调试编辑】<- Adjusted
ACCELERATION_FACTOR = 1.5 # Multiplier when Shift is pressed (50% increase) 【调试编辑】
SPLIT_MIN_LENGTH = 2
CORPSE_LIFESPAN_SECONDS = 43 # 【调试编辑】
CORPSE_FLICKER_START_OFFSET = 30 # 【调试编辑】
CORPSE_Flicker_DURATION_SECONDS = 3 # 【调试编辑】
CORPSE_FADE_DURATION_SECONDS = 10 # 【调试编辑】
REWIND_SECONDS = 10       # 【调试编辑】
GRADUAL_HEAT_INTERVAL_SECONDS = 10 # 【调试编辑】
GRADUAL_HEAT_INCREASE_PERCENT = 0.02 # 【调试编辑】
FRENZY_INTERVAL_SECONDS = 60 # 【调试编辑】
FRENZY_DURATION_SECONDS = 10   # 【调试编辑】
FRENZY_PEAK_BONUS_PERCENT = 0.20 # 【调试编辑】
FRENZY_RAMP_UP_SECONDS = 2     # 【调试编辑】
FRENZY_RAMP_DOWN_SECONDS = 2   # 【调试编辑】
FRUIT_SPAWN_INTERVAL_SECONDS = 5 # 【调试编辑】
MAX_FRUITS = 10            # 【调试编辑】
HEALTHY_FRUIT_DURATION_SECONDS = 30 # 【调试编辑】
BOMB_FRUIT_DURATION_SECONDS = 30    # 【调试编辑】
PINKY_SPAWN_LENGTH = 10    # 【调试编辑】
GHOST_BASE_SPEED_FACTOR = 0.5 # 【调试编辑】<- Relative speed remains same %
GHOST_TARGET_UPDATE_INTERVAL_MS = 500 # 【调试编辑】
PINKY_PREDICTION_DISTANCE = 4 # 【调试编辑】
GHOST_WARNING_DISTANCE_GRIDS = 3 # 【调试编辑】
SNAKE_ALPHA_DECREASE_PER_SEGMENT = 0.02 # 【调试编辑】
MERGE_IMMUNITY_SECONDS = 0.15 # Small delay after split before corpse can be merged 【调试编辑】 <- New setting for split/merge fix


# --- Asset Paths ---
ASSET_DIR = os.path.join(os.path.dirname(__file__), 'assets')
IMG_DIR = os.path.join(ASSET_DIR, 'images')
SOUND_DIR = os.path.join(ASSET_DIR, 'sounds')

# --- Game States ---
STATE_PLAYING = 0
STATE_GAME_OVER = 1
STATE_PAUSED = 2

# --- 帮助函数 ---
def scale_image(image, size):
    """缩放 Pygame 表面。"""
    # 确保尺寸至少是 1x1
    safe_size = max(1, size)
    try:
        return pygame.transform.scale(image, (safe_size, safe_size))
    except Exception as e:
        print(f"缩放图像时出错: {e}")
        # 返回一个占位符或原始图像
        return image # 或者返回一个小的占位符表面

def load_image(filename, size=None, use_alpha=True):
    """
    加载图像，如果提供了 size 则缩放，并处理错误。
    size=None 表示不缩放。
    """
    path = os.path.join(IMG_DIR, filename)
    # effective_size = size if size is not None else GRID_SIZE # <--- 旧的错误逻辑
    effective_size = size # <--- 修正：只有在 size 被指定时才使用它

    try:
        image = pygame.image.load(path)
        if use_alpha:
            image = image.convert_alpha() # 使用透明通道
        else:
            image = image.convert() # 不使用透明通道（例如背景图）

        # --- 修正：仅当提供了有效的 size 参数时才缩放 ---
        if effective_size is not None and isinstance(effective_size, int) and effective_size > 0:
            image = scale_image(image, effective_size)
        # ----------------------------------------------------

        return image
    except pygame.error as e:
        print(f"警告：无法加载图像 '{filename}': {e}")
        # 如果加载失败，创建一个占位符表面
        placeholder_size = effective_size if (effective_size is not None and effective_size > 0) else 10 # 备用尺寸
        placeholder = pygame.Surface((placeholder_size, placeholder_size))
        placeholder.fill(RED) # 填充红色表示错误
        if placeholder.get_width() > 1 and placeholder.get_height() > 1:
            pygame.draw.line(placeholder, BLACK, (0,0), (placeholder.get_width()-1, placeholder.get_height()-1), 1)
            pygame.draw.line(placeholder, BLACK, (0, placeholder.get_height()-1), (placeholder.get_width()-1, 0), 1)
        return placeholder
    except FileNotFoundError:
        print(f"警告：图像文件未找到 '{filename}'")
        # 如果文件未找到，创建另一个占位符
        placeholder_size = effective_size if (effective_size is not None and effective_size > 0) else 10
        placeholder = pygame.Surface((placeholder_size, placeholder_size))
        placeholder.fill(BLUE) # 填充蓝色表示文件缺失
        if placeholder.get_width() > 1 and placeholder.get_height() > 1:
             pygame.draw.line(placeholder, WHITE, (0,0), (placeholder.get_width()-1, placeholder.get_height()-1), 1)
             pygame.draw.line(placeholder, WHITE, (0, placeholder.get_height()-1), (placeholder.get_width()-1, 0), 1)
        return placeholder


def load_sound(filename):
    """Loads a sound and handles errors."""
    path = os.path.join(SOUND_DIR, filename)
    if not pygame.mixer or not pygame.mixer.get_init():
        print("Warning: Mixer module not initialized. Cannot load sound.")
        return None
    try:
        sound = pygame.mixer.Sound(path)
        return sound
    except pygame.error as e:
        print(f"Warning: Could not load sound '{filename}': {e}")
        return None
    except FileNotFoundError:
        print(f"Warning: Sound file not found '{filename}'")
        return None

def load_music(filename):
    """Loads background music."""
    path = os.path.join(SOUND_DIR, filename)
    if not pygame.mixer or not pygame.mixer.get_init():
        print("Warning: Mixer module not initialized. Cannot load music.")
        return False
    try:
        pygame.mixer.music.load(path)
        return True
    except pygame.error as e:
        print(f"Warning: Could not load music '{filename}': {e}")
        return False
    except FileNotFoundError:
        print(f"Warning: Music file not found '{filename}'")
        return False

# --- 字体 ---
# 指定常见中文字体的名称或路径 (根据你的系统调整)
# 确保这些字体文件存在于系统或脚本目录中
PRIMARY_FONT_NAME = "simhei.ttf" # 尝试 黑体
FALLBACK_FONT_NAME = "msyh.ttc" # 尝试 微软雅黑

def get_font(size):
    """尝试加载指定的中文字体，失败则使用 Pygame 默认字体。"""
    # 优先尝试系统字体名称
    try:
        font = pygame.font.SysFont(PRIMARY_FONT_NAME, size)
        # print(f"已加载系统字体: {PRIMARY_FONT_NAME}") # 调试信息
        return font
    except:
        try:
            font = pygame.font.SysFont(FALLBACK_FONT_NAME, size)
            # print(f"已加载系统字体: {FALLBACK_FONT_NAME}") # 调试信息
            return font
        except:
            # 如果系统字体加载失败，尝试从文件加载
            try:
                # 假设字体文件在脚本相同目录下
                font_path = os.path.join(os.path.dirname(__file__), PRIMARY_FONT_NAME)
                if os.path.exists(font_path):
                    font = pygame.font.Font(font_path, size)
                    # print(f"已加载字体文件: {font_path}") # 调试信息
                    return font
                else:
                     # 尝试备用字体文件
                     font_path = os.path.join(os.path.dirname(__file__), FALLBACK_FONT_NAME)
                     if os.path.exists(font_path):
                          font = pygame.font.Font(font_path, size)
                          # print(f"已加载字体文件: {font_path}") # 调试信息
                          return font
            except Exception as e1:
                print(f"无法从文件加载字体 ({PRIMARY_FONT_NAME}, {FALLBACK_FONT_NAME}): {e1}")
                pass # 继续使用最终后备方案

            # 最终后备：Pygame 默认字体
            print(f"警告：无法加载指定的中文字体。将使用默认字体，中文字符可能无法正确显示。")
            try:
                return pygame.font.Font(None, size + 4) # 默认字体可能需要调整大小
            except Exception as e_default:
                 print(f"加载 Pygame 默认字体时也出错: {e_default}")
                 # 极特殊情况：返回 None 或引发异常
                 return None # 或者 raise Exception("无法加载任何字体")

# ... (方向向量等保持不变) ...
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)