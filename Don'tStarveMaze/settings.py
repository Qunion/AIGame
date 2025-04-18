import pygame
import os
import random # 需要导入 random 用于生成噪声种子

# --- 基本设置 ---
GAME_TITLE = "饥荒迷宫"
WIDTH = 1920
HEIGHT = 1080
FPS = 60
TILE_SIZE = 60  # 每个格子的像素大小
GRID_WIDTH = 60 # 迷宫宽度（格子数）
GRID_HEIGHT = 60 # 迷宫高度（格子数）

# --- 路径 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_FOLDER = os.path.join(BASE_DIR, 'assets')
IMAGE_FOLDER = os.path.join(ASSET_FOLDER, 'images')
SOUND_FOLDER = os.path.join(ASSET_FOLDER, 'sounds')
SAVE_FILE = os.path.join(BASE_DIR, 'savegame.pkl')

# --- 颜色 ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GREY = (128, 128, 128)
DARKGREY = (64, 64, 64)
LIGHTGREY = (192, 192, 192)
YELLOW = (255, 255, 0)
FOW_MEMORY_COLOR = (100, 100, 100) # 记忆区域的基础颜色 (会被亮度调整)

# --- 字体 ---
FONT_NAME = pygame.font.match_font('Microsoft YaHei') # 或者指定一个 .ttf 文件路径 原来是arial
UI_FONT_SIZE = 30
MESSAGE_FONT_SIZE = 50

# --- 玩家设置 ---
PLAYER_START_POS = None # 由迷宫生成后随机设置
PLAYER_SPEED = 4.0 * TILE_SIZE / FPS # 2 m/s (单位: 像素/帧) #玩家移动速度 #测试改成4m，默认应该为2m
PLAYER_RADIUS_M = 0.3 # 半径 0.3m
PLAYER_RADIUS_PX = int(PLAYER_RADIUS_M * TILE_SIZE) # 像素半径
PLAYER_HIT_RECT = pygame.Rect(0, 0, int(PLAYER_RADIUS_PX * 1.8), int(PLAYER_RADIUS_PX * 1.8)) # 碰撞矩形简化处理# 这个现在可能只用于初始位置? 碰撞用圆形
PLAYER_START_HUNGER = 50
PLAYER_MAX_HUNGER = 100
PLAYER_HUNGER_DECAY_RATE = 1 # 每多少秒降低1点饱食度
PLAYER_HUNGER_DECAY_INTERVAL = 2 * FPS # 饱食度降低间隔（帧）
PLAYER_HUNGER_WARN_THRESHOLD = 10 # 10%
PLAYER_HUNGER_WARN_INTERVAL = 8 * FPS # 警告间隔（帧）
# 新增：奔跑相关设置
PLAYER_RUN_SPEED_MULTIPLIER = 2.0 # 奔跑时速度变为基础的多少倍
PLAYER_RUN_HUNGER_MULTIPLIER = 2.0 # 奔跑时饱食度消耗变为基础的多少倍
PLAYER_RUN_MATCH_BURN_MULTIPLIER = 2.0 # 奔跑时火柴燃烧速度变为基础的多少倍


# --- 火柴设置 ---
MATCH_INITIAL_COUNT = 3  #初始火柴数量
MATCH_BURN_TIME_SECONDS = 30 #每根燃烧持续时间
MATCH_BURN_TIME_FRAMES = MATCH_BURN_TIME_SECONDS * FPS # 基础燃烧时间（帧）
MATCH_RADIUS_SMALL_M = 4
MATCH_RADIUS_LARGE_M = 6
MATCH_RADIUS_SMALL_PX = MATCH_RADIUS_SMALL_M * TILE_SIZE
MATCH_RADIUS_LARGE_PX = MATCH_RADIUS_LARGE_M * TILE_SIZE
MATCH_COUNT_THRESHOLD_RADIUS = 5 # 大于等于5根时用大半径
MATCH_OUT_DEATH_TIMER_SECONDS = 3
MATCH_OUT_DEATH_TIMER_FRAMES = MATCH_OUT_DEATH_TIMER_SECONDS * FPS
# 火柴低亮度阈值 (秒)
MATCH_LOW_THRESHOLDS_SEC = [15, 10, 5]
# MATCH_LOW_THRESHOLDS_FRAMES = [t * FPS for t in MATCH_LOW_THRESHOLDS_SEC]
MATCH_LOW_THRESHOLDS_FRAMES = [t * FPS * MATCH_INITIAL_COUNT for t in MATCH_LOW_THRESHOLDS_SEC] # *粗略* 调整阈值以反映总时间 (这里逻辑需要更精确，可能需要运行时动态计算总时间阈值)
# 或者更简单的做法：将亮度衰减的阈值改为总火柴数量？例如低于 3 根开始衰减？
# 暂时保持基于总时间的帧数，但需要知道这个阈值可能需要根据实际火柴数调整
# --- 修正：还是让阈值基于 *比例* 更合理 ---
# 例如：总时间低于满状态的 75%, 50%, 25% 时降低亮度？
# 暂时保留基于绝对帧数的逻辑，但标记为可能需要调整
# 对应的亮度百分比 (1.0 = 100%)
MATCH_LOW_BRIGHTNESS = [0.85, 0.70, 0.55]
# 亮度 < 5s 时，记忆效果消失
MATCH_MEMORY_FADE_THRESHOLD_FRAMES = 5 * FPS # 这个仍基于 *当前* 火柴

# 火柴魔法道具
MATCH_MAGIC_DURATION_SEC = 10
MATCH_MAGIC_DURATION_FRAMES = MATCH_MAGIC_DURATION_SEC * FPS

# --- 食物设置 ---
FOOD_BREAD_VALUE = 20
FOOD_MEAT_VALUE = 50
FOOD_MEAT_SPEED_BOOST_FACTOR = 1.5 # 速度变为原来的1.5倍
FOOD_MEAT_BOOST_DURATION_SEC = 10
FOOD_MEAT_BOOST_DURATION_FRAMES = FOOD_MEAT_BOOST_DURATION_SEC * FPS

# --- 地形/生物群系 (Biomes) 设置 ---
NUM_BIOMES = 3 # 当前地形种类数量
# 地形图片文件基础名 (代码会自动添加 biome_id 和 .png)
BIOME_FLOOR_BASENAME = "floor_"
BIOME_WALL_BASENAME = "wall_"
# Perlin Noise 参数 (需要 pip install noise)
NOISE_SCALE = 20.0 # 噪声缩放比例，越大区域越大越平滑
NOISE_OCTAVES = 4     # 噪声细节层次
NOISE_PERSISTENCE = 0.5 # 噪声持续性/幅度衰减
NOISE_LACUNARITY = 2.0  # 噪声频率倍增
NOISE_SEED = random.randint(0, 100) # 随机种子，用于生成不同地图
# 噪声值到地形 ID 的映射阈值 (从低到高)
# 噪声值范围通常在 -1 到 1 之间，需要根据实际效果调整阈值
BIOME_THRESHOLDS = {
    # biome_id: max_noise_value (低于此值为该 biome)
    1: -0.1, # 如果 noise < -0.1，则为 biome 1
    2: 0.2,  # 如果 -0.1 <= noise < 0.2，则为 biome 2
             # 其他情况（noise >= 0.2）则为 biome 3
}
DEFAULT_BIOME_ID = 1 # 默认地形ID（例如用于孤立的墙）

# --- 杂草装饰设置 ---
# 杂草图片文件基础名列表 (可扩展)
WEED_FILES = ['weed_1', 'weed_2']
# 各地形生成杂草的基础概率 (可扩展)
WEED_SPAWN_CHANCE_PER_BIOME = {
    1: 0.15, # 地形1有 15% 概率生成杂草
    2: 0.30, # 地形2有 30% 概率生成杂草
    3: 0.05, # 地形3有 5% 概率生成杂草
    # 如果有更多地形，在这里添加
}
# 生成杂草时，选择不同类型杂草的权重 (字典方便按名字扩展)
WEED_TYPE_WEIGHTS = {
    'weed_1': 1, # 权重为 1
    'weed_2': 1, # 权重为 1 (默认等概率)
    # 'weed_3': 2, # 如果有 weed_3.png, 权重可以不同
}
WEED_IMAGE_SIZE = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8)) # 杂草显示大小 (可选)


# --- 黑暗迷雾 (FoW) 设置 ---
FOW_MEMORY_BRIGHTNESS = 0.6 # 离开后记忆区域的基础亮度 (60%)
FOW_FORGET_TIME_SEC = 20 #遗忘时间：30s
FOW_FORGET_TIME_FRAMES = FOW_FORGET_TIME_SEC * FPS
# 亮度衰减时间点 (秒, 相对于进入记忆状态) 和 对应的亮度倍数 (基于FOW_MEMORY_BRIGHTNESS)
# 设计案描述有点歧义，这里采用：20s时降为初始记忆的1/3，25s时再降为初始记忆的1/3 (即变为2/3的衰减量) -> 似乎不太对
# 重新解读：20s时减弱1/3 (变为2/3)，25s时再减弱1/3 (变为1/3)
# 改为更清晰的设定：
FOW_DECAY_TIMES_SEC = [20, 25, 30]
FOW_DECAY_TIMES_FRAMES = [t * FPS for t in FOW_DECAY_TIMES_SEC]
# 对应的最终亮度百分比 (相对于完全可见=1.0)
FOW_DECAY_BRIGHTNESS = [FOW_MEMORY_BRIGHTNESS * (2/3), FOW_MEMORY_BRIGHTNESS * (1/3), 0.0]
# [DEBUG] 简化衰减用于测试:
# FOW_DECAY_TIMES_FRAMES = [5 * FPS, 8 * FPS, 10 * FPS]
# FOW_DECAY_BRIGHTNESS = [0.4, 0.2, 0.0]

# 光照梯度效果 (越往外越暗)
# [(半径比例阈值, 亮度减少值应用比例), ...]
# 例如：(0.8, 0.3) 表示 0%到80%半径区域，应用0%-30%的亮度减少
#       (1.0, 1.0) 表示 80%到100%半径区域，应用30%-100%的亮度减少
LIGHT_GRADIENT_STOPS = [(0.8, 0.3), (1.0, 1.0)]

# --- 怪物设置 ---
MONSTER_COUNT = 4
# 将迷宫划分为4个区域用于生成
# A=左上, B=右上, C=左下, D=右下
MONSTER_SPAWN_ZONES = [(0, 0, GRID_WIDTH // 2, GRID_HEIGHT // 2),
                       (GRID_WIDTH // 2, 0, GRID_WIDTH, GRID_HEIGHT // 2),
                       (0, GRID_HEIGHT // 2, GRID_WIDTH // 2, GRID_HEIGHT),
                       (GRID_WIDTH // 2, GRID_HEIGHT // 2, GRID_WIDTH, GRID_HEIGHT)]
MONSTER_NAMES = ["战士哥哥", "战士弟弟", "法师姐姐", "法师妹妹"]
MONSTER_TYPES = ["warrior", "warrior", "mage", "mage"]
MONSTER_SPEED_FACTOR = 0.9 # 怪物速度 = 玩家初始速度 * 这个因子
MONSTER_AGGRO_RANGE_FACTOR = 1.1 # 激活距离略大于视野边缘
MONSTER_DESPAWN_DISTANCE_M = 7 # 路径距离大于等于7米时停止追击
MONSTER_DESPAWN_DISTANCE_TILES = MONSTER_DESPAWN_DISTANCE_M
MONSTER_PREDICTION_STEPS = 4 # 法师预测玩家移动格数
MONSTER_HIT_RECT = pygame.Rect(0, 0, TILE_SIZE * 0.8, TILE_SIZE * 0.8) # 怪物碰撞矩形

# --- 武器设置 ---
WEAPON_BROKEN_USES = 1
WEAPON_GOOD_USES = 2

# --- 物品生成数量 ---
# 确保总格子数 > 物品数 + 怪物数 + 玩家 + 出口
TOTAL_TILES = GRID_WIDTH * GRID_HEIGHT
MATCH_SPAWN_COUNT = 16
FOOD_BREAD_COUNT = 12
FOOD_MEAT_COUNT = 4
WEAPON_SPAWN_COUNT = 2 # 1 broken, 1 good

# --- UI 设置 ---
UI_PANEL_HEIGHT = 150 # 顶部UI区域高度 (预留，可以不用)
UI_PADDING = 10
UI_ICON_SIZE = 128 # 饱食度图标大小
UI_MATCH_WIDTH = 32
UI_MATCH_HEIGHT = 128
UI_MATCH_PROGRESS_COLOR_FG = GREEN
UI_MATCH_PROGRESS_COLOR_BG = GREY
UI_MATCH_SPACING = 5 # 火柴图标间距

# --- 出口放置设置 (新) ---
EXIT_ZONE_WEIGHTS = {'edge': 6, 'outer': 3, 'middle': 1} # 边缘:外围:中间 的权重
EXIT_OUTER_RING_DISTANCE = 10 # 外围区域定义为距离边缘 <= 10 格

# --- 图层 ---
WALL_LAYER = 1
DECORATION_LAYER = 2.5 # 杂草图层
MARKER_LAYER = 2.7     # 新增：放置标记物图层 (在杂草之上, 物品/玩家/怪物之下)
ITEM_LAYER = 3         # 物品图层 (调整一下让标记物在下面?) 或者 Marker 3, Item 3.1? 决定 Marker 2.7, Item 3
PLAYER_LAYER = 3.5       # 玩家图层
MONSTER_LAYER = 3.5      # 怪物图层 (与玩家同层或稍低/高?) 保持 3.5
EFFECT_LAYER = 4
FOG_LAYER = 5


# --- 图片文件名 (扩展地形和杂草) ---
# 主字典现在可以移除具体地形/杂草，由代码根据配置动态生成 key
IMAGE_FILES = {
    # 'wall': 'wall.png', # 移除旧的单一地形
    # 'floor': 'floor.png',
    'player': 'player.png',
    'monster_warrior_1': 'monster_warrior_1.png',
    'monster_warrior_2': 'monster_warrior_2.png',
    'monster_mage_1': 'monster_mage_1.png',
    'monster_mage_2': 'monster_mage_2.png',
    'food_bread': 'food_bread.png',
    'food_meat': 'food_meat.png',
    'match_item': 'match_item.png',
    'weapon_sword_broken': 'weapon_sword_broken.png',
    'weapon_sword_good': 'weapon_sword_good.png',
    'ui_hunger': 'ui_hunger.png',
    'ui_match': 'ui_match.png',
    'exit': 'exit.png', # 假设有个出口的图片
    'effect_hunger': 'effect_hunger_wave.png' # 假设饥饿波纹有图片
}
# 地形和杂草文件名会在 AssetManager 中根据配置动态添加到加载列表

# 新增：标记物图片文件名字典 (方便管理和加载)
MARKER_IMAGE_FILES = {
    'apple_core_1': 'apple_core_1.png',
    'apple_core_2': 'apple_core_2.png',
    'monster_mage_corpse_1': 'monster_mage_corpse_1.png',
    'monster_mage_corpse_2': 'monster_mage_corpse_2.png',
    'monster_warrior_corpse_1': 'monster_warrior_corpse_1.png',
    'monster_warrior_corpse_2': 'monster_warrior_corpse_2.png',
}

# 物品/怪物图片大小建议 (加载后可以缩放)
# 可以根据实际图片调整
ITEM_IMAGE_SIZE = (int(TILE_SIZE * 0.6), int(TILE_SIZE * 0.6))
MONSTER_IMAGE_SIZE = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))
PLAYER_IMAGE_SIZE = (PLAYER_RADIUS_PX * 2, PLAYER_RADIUS_PX * 2)

# 标记物图片大小 (地图上和 UI 上可能需要不同处理)
MARKER_SPRITE_SIZE = ITEM_IMAGE_SIZE # 地图上的标记物大小，暂定同物品
MARKER_UI_ICON_SIZE = (60, 60)       # UI上标记物图标大小

# --- 音效文件名 ---
SOUND_FILES = {
    'background': 'background.ogg',
    'step': 'step.wav',
    'pickup': 'pickup.wav',
    'monster_roar': 'monster_roar.wav',
    'match_burn': 'match_burn.wav', # 可能需要循环播放
    'hunger_growl': 'hunger_growl.wav',
    'player_die': 'player_die.wav',
    'monster_die': 'monster_die.wav',
    'weapon_break': 'weapon_break.wav',
    'win': 'win.wav',
    'attack': 'attack.wav' # 新增攻击音效
}

# --- 存档设置 ---
SAVE_ON_PICKUP = True
SAVE_ON_EXIT = True

# --- Ray Casting / FOV ---
FOV_NUM_RAYS = 120 # 投射的光线数量，越多越精确但越慢
FOV_LIGHT_WALLS = True # 是否照亮墙壁本身