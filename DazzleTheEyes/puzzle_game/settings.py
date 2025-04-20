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
IMAGE_LOGIC_COLS = 9    # 完整图片的逻辑列数 (宽度方向)
IMAGE_LOGIC_ROWS = 5    # 完整图片的逻辑行数 (高度方向)
PIECES_PER_IMAGE = IMAGE_LOGIC_COLS * IMAGE_LOGIC_ROWS # 每张完整图片的碎片数量 (5*9=45)

# 资源路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # 获取当前文件所在目录的绝对路径
ASSETS_DIR = os.path.join(BASE_DIR, "assets") + os.sep # assets文件夹路径

# 碎片生成与缓存设置
REGENERATE_PIECES = 0 # 是否重新生成碎片：1-是，0-否。设置为0时优先从文件加载。
# 生成的碎片存放目录
GENERATED_PIECE_DIR = os.path.join(ASSETS_DIR, "pieces") + os.sep
# 确保碎片目录存在 (这一行已经有了，确认一下)
os.makedirs(GENERATED_PIECE_DIR, exist_ok=True)
# 碎片文件命名格式，用于保存和加载
PIECE_FILENAME_FORMAT = "image_{}_r{}_c{}.png" # 例如 image_1_r0_c0.png

# 加载界面图片
LOADING_IMAGE_PATH = os.path.join(ASSETS_DIR, "loading.png")


# UI元素图片路径
GALLERY_ICON_PATH = os.path.join(ASSETS_DIR, "gallery_icon.png")
LEFT_BUTTON_PATH = os.path.join(ASSETS_DIR, "left_button.png")
RIGHT_BUTTON_PATH = os.path.join(ASSETS_DIR, "right_button.png")
# 原始图片文件前缀, 如 image_1.png, image_2.png
SOURCE_IMAGE_PREFIX = os.path.join(ASSETS_DIR, "image_")
# 生成的碎片存放目录 (如果选择保存为文件)
GENERATED_PIECE_DIR = os.path.join(ASSETS_DIR, "pieces") + os.sep
# 确保碎片目录存在
os.makedirs(GENERATED_PIECE_DIR, exist_ok=True)


# 初始填充设置
# 游戏开始时，拼盘中包含的完整图片数量和来自下一张图片的碎片数量
INITIAL_FULL_IMAGES_COUNT = 3
INITIAL_PARTIAL_IMAGE_PIECES_COUNT = 9
# 初始碎片总数应为 BOARD_COLS * BOARD_ROWS
EXPECTED_INITIAL_PIECE_COUNT = BOARD_COLS * BOARD_ROWS


# 颜色定义 (RGB格式)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150) # 用于未点亮图片在图库中显示
HIGHLIGHT_COLOR = (255, 255, 0) # 选中碎片高亮色
GALLERY_BG_COLOR = (50, 50, 50, 200) # 图库背景色 (带透明度，如果Surface支持阿尔法通道)
OVERLAY_COLOR = (0, 0, 0, 180) # 全屏覆盖层颜色 (带透明度)


# 游戏状态常量
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
GALLERY_PADDING = 15
GALLERY_THUMBNAIL_GAP = 15
GALLERY_THUMBNAIL_WIDTH = (GALLERY_WIDTH - (GALLERY_IMAGES_PER_ROW + 1) * GALLERY_THUMBNAIL_GAP) // GALLERY_IMAGES_PER_ROW
# 保持原始图片逻辑比例 (宽度:高度 = 9:5) 来计算缩略图高度
GALLERY_THUMBNAIL_HEIGHT = int(GALLERY_THUMBNAIL_WIDTH * (IMAGE_LOGIC_ROWS / IMAGE_LOGIC_COLS))
GALLERY_SCROLL_SPEED = 20 # 图库滑动速度 (像素/帧)


# 提示信息设置 ("美图尚未点亮")
TIP_TEXT_COLOR = WHITE
TIP_DISPLAY_DURATION = 3 # 提示信息显示时长 (秒)


# 动画速度 (下落等) - 如果需要平滑动画
FALL_SPEED_PIXELS_PER_FRAME = 10 # 碎片下落速度 (像素/帧)


# 其他需要调试的参数...