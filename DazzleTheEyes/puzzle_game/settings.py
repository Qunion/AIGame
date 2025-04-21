# settings.py
# 游戏设置及配置参数

import os

# 屏幕设置
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# 拼盘设置
BOARD_COLS = 16         # 拼盘的列数
BOARD_ROWS = 9          # 拼盘的行数
PIECE_SIZE = 120        # 每个碎片的边长 (像素)

# 计算拼盘在屏幕上的起始位置 (目前是全屏覆盖，所以是0,0)
BOARD_OFFSET_X = 0
BOARD_OFFSET_Y = 0

# 图片逻辑尺寸 (一张完整图片被分割成的网格尺寸)
# 注意：这里是 5列 x 9行
IMAGE_LOGIC_COLS = 5    # 完整图片的逻辑列数 (宽度方向的碎片数量)
IMAGE_LOGIC_ROWS = 9    # 完整图片的逻辑行数 (高度方向的碎片数量)
PIECES_PER_IMAGE = IMAGE_LOGIC_COLS * IMAGE_LOGIC_ROWS # 每张完整图片的碎片数量 (5*9=45)

# 字体设置
FONT_NAME = "Microsoft YaHei" # 主要游戏字体名称 (使用系统字体名称)
# 如果需要备用字体，可以添加 FONT_FALLBACK = None 或 "Arial"

# 资源路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # 获取当前文件所在目录的绝对路径
ASSETS_DIR = os.path.join(BASE_DIR, "assets") + os.sep # assets文件夹路径

# 碎片生成与缓存设置
REGENERATE_PIECES = 1 # 是否重新生成碎片：1-是，0-否。设置为0时优先从文件加载。
# 生成的碎片存放目录
GENERATED_PIECE_DIR = os.path.join(ASSETS_DIR, "pieces") + os.sep
# 确保碎片目录存在
os.makedirs(GENERATED_PIECE_DIR, exist_ok=True) # 修正了这里的 typo
# 碎片文件命名格式，用于保存和加载
PIECE_FILENAME_FORMAT = "image_{}_r{}_c{}.png" # 例如 image_1_r0_c0.png


# 图片加载与后台处理设置
# 第一次进入游戏时加载的图片数量 (用于初始拼盘和前期的图库)
# 必须至少包含 INITIAL_FULL_IMAGES_COUNT + (1 if INITIAL_PARTIAL_IMAGE_PIECES_COUNT > 0 else 0) 张图片
INITIAL_LOAD_IMAGE_COUNT = 5 # 根据你的图片数量和期望加载速度调整

# 后台加载图片的速度控制
BACKGROUND_LOAD_BATCH_SIZE = 1 # 每次后台尝试加载处理的图片数量 (可以调整)
BACKGROUND_LOAD_DELAY = 100 # 每批处理之间的最小延迟 (秒)，避免完全占用CPU，让Pygame有时间绘制和处理事件


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


# 初始填充设置
# 游戏开始时，拼盘中包含的完整图片数量和来自下一张图片的碎片数量
INITIAL_FULL_IMAGES_COUNT = 3
INITIAL_PARTIAL_IMAGE_PIECES_COUNT = 9 # 确保初始碎片总数是 16*9=144
# 初始碎片总数应为 BOARD_COLS * BOARD_ROWS
EXPECTED_INITIAL_PIECE_COUNT = BOARD_COLS * BOARD_ROWS


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
# 计算缩略图宽度，考虑了窗口宽度、内边距和水平间距
GALLERY_THUMBNAIL_WIDTH = (GALLERY_WIDTH - 2 * GALLERY_PADDING - (GALLERY_IMAGES_PER_ROW - 1) * GALLERY_THUMBNAIL_GAP_X) // GALLERY_IMAGES_PER_ROW
# 保持原始图片逻辑比例 (宽度:高度 = 5:9) 来计算缩略图高度
GALLERY_THUMBNAIL_HEIGHT = int(GALLERY_THUMBNAIL_WIDTH * (IMAGE_LOGIC_ROWS / IMAGE_LOGIC_COLS)) # 注意这里是 Rows / Cols

GALLERY_SCROLL_SPEED = 90 # 图库滑动速度 (像素/帧)


# 提示信息设置 ("美图尚未点亮")
TIP_TEXT_COLOR = WHITE
TIP_DISPLAY_DURATION = 2 # 提示信息显示时长 (秒)
TIP_FONT_SIZE = 20 # 提示信息字体大小


# 动画速度 (下落等)
FALL_SPEED_PIXELS_PER_SECOND = 600 # 碎片下落速度 (像素/秒)


# 拖拽操作阈值
DRAG_THRESHOLD = 5 # 鼠标移动超过此像素距离判定为拖拽


# Board内部状态常量 (用于管理完成 -> 移除 -> 下落 -> 填充流程)
BOARD_STATE_PLAYING = 0
BOARD_STATE_PICTURE_COMPLETED = 1 # 图片完成，等待处理
BOARD_STATE_REMOVING_PIECES = 2 # 正在移除碎片
BOARD_STATE_PIECES_FALLING = 3 # 碎片正在下落
BOARD_STATE_PENDING_FILL = 4 # 下落完成，等待填充新碎片


# 存档设置
SAVE_FILE_NAME = "savegame.json" # 存档文件名
# 完整的存档文件路径将是 os.path.join(BASE_DIR, SAVE_FILE_NAME)
AUTOSAVE_INTERVAL = 30 # 自动存档间隔 (秒)

# Debug 设置
DEBUG_TEXT_COLOR = (255, 255, 255) # Debug 文字颜色 (白色)
DEBUG_FONT_SIZE = 15 # Debug 文字字体大小

# 其他需要调试的参数...