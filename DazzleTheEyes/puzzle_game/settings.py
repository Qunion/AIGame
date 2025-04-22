# settings.py
# 游戏设置及配置参数

import os

# TODO: PIECES_PER_IMAGE 是一个遗留常量，不代表每张图片的实际碎片总数，应根据 IMAGE_LOGIC_DIMS 动态计算。
# 保留此处仅作记录，实际代码中应避免使用此固定值判断图片碎片总数。
PIECES_PER_IMAGE = 20
# TODO: GALLERY_THUMBNAIL_HEIGHT 这个固定高度的设置可能需要根据实际设计调整，
# 目前 ImageManager 根据缩略图宽度和图片逻辑比例计算高度。
GALLERY_THUMBNAIL_HEIGHT = 500

# 碎片生成与缓存设置
REGENERATE_PIECES = 0 # 是否重新生成碎片：1-是，0-否。设置为0时优先从文件加载。

# 屏幕设置 (固定)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# 碎片尺寸 (可配置)
# 所有图片的碎片都将是这个尺寸
PIECE_WIDTH = 128 # 碎片宽度 (像素)
PIECE_HEIGHT = 135 # 碎片高度 (像素)
# 注意：PIECE_SIZE 已不再使用，请使用 PIECE_WIDTH 和 PIECE_HEIGHT


# 拼盘尺寸 (物理网格，根据屏幕和碎片尺寸计算，固定)
BOARD_COLS = SCREEN_WIDTH // PIECE_WIDTH # 物理拼盘列数
BOARD_ROWS = SCREEN_HEIGHT // PIECE_HEIGHT # 物理拼盘行数
# 注意：这里计算的是总的物理网格大小，不等于可放置区域大小

BOARD_OFFSET_X = 0
BOARD_OFFSET_Y = 0

# 图片逻辑尺寸 (每张图独立配置)
# 这是一个字典，键是图片ID，值是 (逻辑列数, 逻辑行数) 的元组
IMAGE_LOGIC_DIMS = {
    # 根据图片宽高和期望的碎片数量及比例配置，逻辑尺寸 * 碎片尺寸应接近原始图片尺寸
    # (逻辑列数 * PIECE_WIDTH, 逻辑行数 * PIECE_HEIGHT) 决定了原图被处理（缩放裁剪）到的目标尺寸
    1: (2, 3),  # image_1 裁剪为 2列x3行
    2: (3, 3), # image_2 裁剪为 3列x3行
    3: (3, 3),  
    4: (3, 4),  
    5: (3, 5),  
    6: (4, 4), 
    7: (4, 5), 
    8: (3, 6),  
    9: (4, 7), 
    10: (5, 7), 
    # ... 根据你的图片数量和期望的裁剪方式添加更多条目
    # 注意：这里的行列数定义了图片的逻辑结构和碎片数量，不是拼盘的物理尺寸。
    # 确保 IMAGE_LOGIC_DIMS 中的所有图片ID在 assets 目录中都有对应的 image_ID.png 文件。
}

# 可放置区域配置 (根据点亮图片数量动态变化)
# 这是一个字典，键是点亮图片数量阈值，值是包含 'cols', 'rows', 'bg' 的字典
# 'cols' 和 'rows' 是可放置区域在物理网格中的尺寸， 'bg' 是对应的背景图文件名
# 升级阈值必须按升序排列
PLAYABLE_AREA_CONFIG = {
    0: {'cols': 2, 'rows': 3, 'bg': 'background_1.png'},     # 初始区域 5x5
    1: {'cols': 4, 'rows': 4, 'bg': 'background_2.png'},     # 点亮 1 张图后升级到 7x7
    3: {'cols': 5, 'rows': 5, 'bg': 'background_3.png'},     # 点亮 3 张图后升级到 9x9
    5: {'cols': 8, 'rows': 8, 'bg': 'background_4.png'},    # 点亮 6 张图后升级到 12x9
    10: {'cols': 15, 'rows': 8, 'bg': 'background_5.png'},   # 点亮 10 张图后升级到 15x8 (最大可放置区域等于物理拼盘尺寸)
    # ... 添加更多阈值和配置
    # 注意：确保可放置区域的尺寸 (cols * PIECE_WIDTH, rows * PIECE_HEIGHT) 不超过屏幕尺寸
    # (即 cols <= BOARD_COLS 且 rows <= BOARD_ROWS)
}

# 派生计算
# 物理拼盘总槽位数
BOARD_TOTAL_SLOTS = BOARD_COLS * BOARD_ROWS


# 可放置区域指示图层颜色 (黑色 50% 透明)
PLAYABLE_AREA_OVERLAY_COLOR = (0, 0, 0, 128)


# 字体设置
FONT_NAME = "Microsoft YaHei" # 主要游戏字体名称 (使用系统字体名称)
# 如果需要备用字体，可以添加 FONT_FALLBACK = None 或 "Arial"

# 资源路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # 获取当前文件所在目录的绝对路径
ASSETS_DIR = os.path.join(BASE_DIR, "assets") + os.sep # assets文件夹路径
BACKGROUND_DIR = os.path.join(ASSETS_DIR, "backgrounds") + os.sep # 背景图文件夹
os.makedirs(BACKGROUND_DIR, exist_ok=True) # 确保背景图目录存在



# 生成的碎片存放目录
GENERATED_PIECE_DIR = os.path.join(ASSETS_DIR, "pieces") + os.sep
# 确保碎片目录存在
os.makedirs(GENERATED_PIECE_DIR, exist_ok=True)
# 碎片文件命名格式，用于保存和加载
# image_ID_r行索引_c列索引.png (行和列是碎片在原图的逻辑位置)
PIECE_FILENAME_FORMAT = "image_{}_r{}_c{}.png"


# 图片加载与后台处理设置
# 游戏启动时，ImageManager 会尝试加载所有在 IMAGE_LOGIC_DIMS 中配置的图片文件，
# 并优先处理那些在存档中状态不为 'unentered' (已入场/已点亮) 的图片资源（碎片和缩略图），
# 然后按顺序处理剩余的图片。
# INITIAL_LOAD_IMAGE_COUNT 可以在 ImageManager 初始化时控制初始同步加载的图片数量。
# 推荐这个数量至少覆盖初始可放置区域所需的碎片所对应的图片，或设置一个合理的值以便快速进入游戏并显示一些图库项。
INITIAL_LOAD_IMAGE_COUNT = 5 # 示例：初始加载前5张图的碎片和缩略图。

# 后台加载图片的速度控制
BACKGROUND_LOAD_BATCH_SIZE = 1 # 每次后台尝试加载处理的图片数量 (可以调整)
BACKGROUND_LOAD_DELAY = 0.05 # 每批处理之间的最小延迟 (秒)，避免完全占用CPU，让Pygame有时间绘制和处理事件


# 加载界面设置
MIN_LOADING_DURATION = 2.0 # 最小加载持续时间 (秒)

# 加载界面图片文件列表 (从这里随机选择一张作为加载背景)
LOADING_IMAGE_FILENAMES = ["loading_1.png", "loading_2.png", "loading_3.png", "loading_4.png", "loading_5.png"] # 请确保assets中有这些文件
LOADING_IMAGE_PATHS = [os.path.join(ASSETS_DIR, f) for f in LOADING_IMAGE_FILENAMES]


# UI元素图片路径
GALLERY_ICON_PATH = os.path.join(ASSETS_DIR, "gallery_icon.png")
LEFT_BUTTON_PATH = os.path.join(ASSETS_DIR, "left_button.png")
RIGHT_BUTTON_PATH = os.path.join(ASSETS_DIR, "right_button.png")
# 原始图片文件前缀, 如 image_1.png, image_2.png
SOURCE_IMAGE_PREFIX = os.path.join(ASSETS_DIR, "image_")


# 颜色定义 (RGB格式)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150) # 用于未点亮图片在图库中显示
HIGHLIGHT_COLOR = (255, 255, 0) # 选中碎片高亮色
GALLERY_BG_COLOR = (30, 30, 30, 200) # 图库背景色 (带透明度)
OVERLAY_COLOR = (0, 0, 0, 180) # 全屏覆盖层颜色 (带透明度)

LOADING_TEXT_COLOR = WHITE

# 游戏状态常量
GAME_STATE_LOADING = -1 # 加载状态
GAME_STATE_PLAYING = 0           # 正在玩拼图
GAME_STATE_GALLERY_LIST = 1      # 打开图库列表界面
GAME_STATE_GALLERY_VIEW_LIT = 2  # 打开图库已点亮图片大图查看界面


# 图库设置
GALLERY_WIDTH = 1080
GALLERY_HEIGHT = 900
# 计算图库窗口居中时的屏幕坐标
GALLERY_X = (SCREEN_WIDTH - GALLERY_WIDTH) // 2
GALLERY_Y = (SCREEN_HEIGHT - GALLERY_HEIGHT) // 2
GALLERY_IMAGES_PER_ROW = 3 # 图库列表每行显示的图片数量
# 示例缩略图大小计算，需要考虑间距，假设边距和间距都是15像素
GALLERY_PADDING = 20 # 图库窗口内边距
GALLERY_THUMBNAIL_GAP_X = 20 # 缩略图水平间距
GALLERY_THUMBNAIL_GAP_Y = 20 # 缩略图垂直间距
# 缩略图宽度是固定的，高度在 ImageManager 中根据图片逻辑比例动态计算
GALLERY_THUMBNAIL_WIDTH = (GALLERY_WIDTH - 2 * GALLERY_PADDING - (GALLERY_IMAGES_PER_ROW - 1) * GALLERY_THUMBNAIL_GAP_X) // GALLERY_IMAGES_PER_ROW
# GALLERY_THUMBNAIL_HEIGHT 在 ImageManager 中根据图片逻辑比例和 GALLERY_THUMBNAIL_WIDTH 计算

GALLERY_SCROLL_SPEED = 90 # 图库滑动速度 (像素/帧)


# 提示信息设置 ("美图尚未点亮")
TIP_TEXT_COLOR = WHITE
TIP_DISPLAY_DURATION = 2 # 提示信息显示时长 (秒)
TIP_FONT_SIZE = 20 # 提示信息字体大小


# 动画速度 (下落等)
FALL_SPEED_PIXELS_PER_SECOND = 600 # 碎片下落速度 (像素/秒)


# 拖拽操作阈值
DRAG_THRESHOLD = 5 # 鼠标移动超过此像素距离判定为拖拽


# Board内部状态常量 (用于管理完成 -> 移除 -> 下落 -> 填充 -> 升级流程)
BOARD_STATE_PLAYING = 0
BOARD_STATE_PICTURE_COMPLETED = 1 # 图片完成，等待处理
BOARD_STATE_REMOVING_PIECES = 2 # 正在移除碎片动画 (可选，目前瞬移)
BOARD_STATE_PIECES_FALLING = 3 # 碎片正在下落动画
BOARD_STATE_PENDING_FILL = 4 # 下落完成，等待填充新碎片
BOARD_STATE_UPGRADING_AREA = 5 # 正在升级可放置区域 (移动碎片、加载背景等)


# 存档设置
SAVE_FILE_NAME = "savegame.json" # 存档文件名
# 完整的存档文件路径将是 os.path.join(BASE_DIR, SAVE_FILE_NAME)
AUTOSAVE_INTERVAL = 10 # 自动存档间隔 (秒)

# Debug 设置
DEBUG_TEXT_COLOR = (255, 255, 255) # Debug 文字颜色 (白色)
DEBUG_FONT_SIZE = 15 # Debug 文字字体大小