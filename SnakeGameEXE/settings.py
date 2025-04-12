import pygame  # 导入 Pygame 库，用于游戏开发
import os      # 导入 os 库，用于处理文件路径

# --- 核心设置 (Core Settings) ---
SCREEN_WIDTH = 1920      # 游戏窗口宽度（像素）
SCREEN_HEIGHT = 1080     # 游戏窗口高度（像素）
WINDOW_TITLE = "增强版贪吃蛇" # 游戏窗口标题 (已改为中文)
FPS = 60                 # 游戏目标帧率 (每秒刷新次数)

# --- 网格与画布设置 (Grid & Canvas) ---
# 画布的格子尺寸，选择这个尺寸是为了更好地匹配屏幕宽高比 (71/40 ≈ 1.775, 1920/1080 ≈ 1.777)
CANVAS_GRID_WIDTH = 71   # 画布宽度（格子数）
CANVAS_GRID_HEIGHT = 40  # 画布高度（格子数）

# 计算每个格子的像素大小，以确保整个画布能适应屏幕
# 分别计算宽度和高度方向上能容纳的格子大小
GRID_SIZE_W = SCREEN_WIDTH // CANVAS_GRID_WIDTH   # 宽度方向的格子大小
GRID_SIZE_H = SCREEN_HEIGHT // CANVAS_GRID_HEIGHT # 高度方向的格子大小
# 取较小的值作为最终格子大小，保证画布内容完全可见
GRID_SIZE = min(GRID_SIZE_W, GRID_SIZE_H) # 最终使用的格子边长（像素），例如 27

# 画布的实际像素尺寸（格子数 * 每个格子的像素大小）
# 由于 GRID_SIZE 是整数，这个像素尺寸可能不完全等于 SCREEN_WIDTH/HEIGHT
# 绘图时会处理居中或黑边的问题
CANVAS_WIDTH_PX = CANVAS_GRID_WIDTH * GRID_SIZE    # 画布实际宽度（像素）
CANVAS_HEIGHT_PX = CANVAS_GRID_HEIGHT * GRID_SIZE  # 画布实际高度（像素）

# --- 颜色定义 (Colors) ---
# 使用 RGB 元组定义常用颜色
WHITE = (255, 255, 255)  # 白色
BLACK = (0, 0, 0)        # 黑色
RED = (200, 0, 0)        # 红色 (稍暗，避免刺眼)
GREEN = (0, 200, 0)      # 绿色 (稍暗)
BLUE = (0, 0, 200)       # 蓝色 (稍暗)
YELLOW = (255, 255, 0)   # 黄色
BRIGHT_YELLOW = (255, 220, 0) # 一个比较亮的黄色
DARK_YELLOW = (200, 200, 0) # 暗黄色，用作蛇的基础色
GREY = (128, 128, 128)   # 灰色
# 网格线的颜色，使用 RGBA 定义，最后一个值是 Alpha 透明度 (0-255)
# 为较小的格子调整了透明度，使其不那么显眼
GRID_COLOR = (200, 200, 200, 80) # 浅灰色，带透明度

# --- 游戏机制 - 可调参数 (Game Mechanics - TUNABLE PARAMETERS) ---
# 这些参数可以在这里方便地调整，用于测试和平衡游戏
INITIAL_SNAKE_LENGTH = 4  # 蛇的初始长度（格子数）

# --- 新增：初始果实数量 ---
INITIAL_FRUIT_COUNT = 5    # 游戏开始时生成的初始果实数量 【调试编辑】
# ------------------------

# 蛇的基础移动速度（格子/秒）
# 调整说明：因为格子大小减半，为了保持视觉速度不变，将格子移动速度加倍
BASE_SNAKE_SPEED_PPS = 7.0 # 初始速度（格子/秒） 【调试编辑】<- 已调整

# 加速功能的速度乘数
ACCELERATION_FACTOR = 2 # 按住 Shift 时的速度倍率 (1.5 表示增加 50%) 【调试编辑】

# 执行分裂操作所需的最小长度
SPLIT_MIN_LENGTH = 2

# 尸体的生命周期相关参数
CORPSE_LIFESPAN_SECONDS = 43 # 尸体总存在时间（秒）= 静态时间 + 闪烁时间 + 淡出时间 【调试编辑】
CORPSE_FLICKER_START_OFFSET = 30 # 尸体生成后多少秒开始闪烁 【调试编辑】
CORPSE_Flicker_DURATION_SECONDS = 3 # 尸体闪烁持续时间（秒） 【调试编辑】
CORPSE_FADE_DURATION_SECONDS = 10 # 尸体闪烁结束后淡出消失的持续时间（秒） 【调试编辑】

# 时光倒流功能回溯的时间长度
REWIND_SECONDS = 10       # 回溯多少秒 【调试编辑】

# “逐渐燥热”效果（速度随时间增加）的参数
GRADUAL_HEAT_INTERVAL_SECONDS = 10 # 每隔多少秒增加一次速度 【调试编辑】
GRADUAL_HEAT_INCREASE_PERCENT = 0.02 # 每次增加速度的百分比 (0.02 = 2%) 【调试编辑】

# “躁动时刻”效果的参数
FRENZY_INTERVAL_SECONDS = 60 # 每隔多少秒进入一次躁动时刻 【调试编辑】
FRENZY_DURATION_SECONDS = 10   # 每次躁动时刻持续时间（秒） 【调试编辑】
FRENZY_PEAK_BONUS_PERCENT = 0.20 # 躁动时刻达到的最大额外速度加成 (0.20 = 20%) 【调试编辑】
FRENZY_RAMP_UP_SECONDS = 2     # 达到最大加成所需时间（秒） 【调试编辑】
FRENZY_RAMP_DOWN_SECONDS = 2   # 从最大加成恢复到正常所需时间（秒） 【调试编辑】

# 果实生成相关参数
FRUIT_SPAWN_INTERVAL_SECONDS = 3 # 每隔多少秒生成一个新果实 【调试编辑】
MAX_FRUITS = 10            # 屏幕上允许存在的最大果实数量 【调试编辑】
HEALTHY_FRUIT_DURATION_SECONDS = 30 # 健康果实（绿色）的存在时间（秒） 【调试编辑】
BOMB_FRUIT_DURATION_SECONDS = 30    # 炸弹果实（红黑色）的存在时间（秒） 【调试编辑】

# 敌人（鬼魂）相关参数
PINKY_SPAWN_LENGTH = 10    # 蛇达到多长时 Pinky 鬼魂出现 【调试编辑】
GHOST_BASE_SPEED_FACTOR = 0.8 # 鬼魂的基础速度相对于蛇基础速度的倍率 (0.5 = 50%) 【调试编辑】
GHOST_TARGET_UPDATE_INTERVAL_SECONDS = 2 # 鬼魂重新计算目标位置的时间间隔（毫秒） 【调试编辑】
PINKY_PREDICTION_DISTANCE = 4 # Pinky 预测蛇头前方多少格进行拦截 【调试编辑】
GHOST_WARNING_DISTANCE_GRIDS = 2 # 鬼魂距离蛇头多少格以内触发警告音效 【调试编辑】

# 视觉效果相关参数
SNAKE_ALPHA_DECREASE_PER_SEGMENT = 0.02 # 蛇身每向后一节，透明度增加的百分比 (0.02 = 2%) 【调试编辑】
MERGE_IMMUNITY_SECONDS = 0.15 # 分裂后尸体短暂的融合免疫时间（秒），防止立即融合 【调试编辑】 <- 修复分裂融合bug的新设置


# --- 资源路径 (Asset Paths) ---
# 定义存放图像和声音资源的文件夹路径
ASSET_DIR = os.path.join(os.path.dirname(__file__), 'assets') # assets 文件夹路径 (假设与脚本在同一目录下)
IMG_DIR = os.path.join(ASSET_DIR, 'images')                   # images 子文件夹路径
SOUND_DIR = os.path.join(ASSET_DIR, 'sounds')                 # sounds 子文件夹路径

# --- 游戏状态常量 (Game States) ---
# 定义不同的游戏状态，方便管理逻辑流程
STATE_PLAYING = 0      # 游戏进行中
STATE_GAME_OVER = 1    # 游戏结束
STATE_PAUSED = 2       # 游戏暂停 (当前未使用，可扩展)

# 注意：资源加载函数 (load_image, load_sound, load_music) 和字体加载函数 (get_font)
# 以及方向向量 (UP, DOWN, LEFT, RIGHT) 定义在文件的更下方，这里省略它们的注释，
# 因为之前的交互中已经解释过它们的作用。

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

# --- 字体 ---
# *** 新增：指定要捆绑在项目目录中的字体文件名 ***
# BUNDLED_FONT_FILENAME = "chinese_font.ttf" # <--- 请确保这个文件名与你放入项目目录的字体文件一致！

# # (保留旧的系统字体名称作为备用，但优先级降低)
# PRIMARY_FONT_NAME = "simhei.ttf" # 备用系统字体1：黑体
# FALLBACK_FONT_NAME = "msyh.ttc" # 备用系统字体2：微软雅黑

# *** 修改：尝试更精确的 Windows 系统字体名称 ***
SYSTEM_FONT_CANDIDATES = [
    "Microsoft YaHei", # 微软雅黑 (优先尝试)
    "SimHei",          # 黑体
    "Dengxian",        # 等线 (较新 Windows 系统)
    "SimSun",          # 宋体
    "NSimSun",         # 新宋体
    "FangSong",        # 仿宋
    "KaiTi"            # 楷体
]

def get_font(size):
    """
    加载字体函数，优先尝试常见的 Windows 中文字体名称。
    如果失败，则使用 Pygame 默认字体。
    """
    # --- 1. 尝试加载 Windows 系统字体 ---
    for font_name in SYSTEM_FONT_CANDIDATES:
        try:
            font = pygame.font.SysFont(font_name, size)
            print(f"成功加载系统字体: {font_name}")
            return font
        except Exception as e:
            # print(f"尝试加载系统字体 '{font_name}' 失败: {e}") # 可以取消注释来查看详细错误
            pass # 继续尝试下一个

    # --- 2. 如果以上都失败，使用 Pygame 默认字体 ---
    print(f"警告：所有指定的系统字体加载失败！将使用 Pygame 默认字体，中文字符可能无法显示。")
    try:
        return pygame.font.Font(None, size + 4)
    except Exception as e_default:
        print(f"加载 Pygame 默认字体时也出错: {e_default}")
        return None


# ... (方向向量等保持不变) ...
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)