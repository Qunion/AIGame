# FILENAME: config.py
#
# 存放所有可配置的常量

import pygame # 导入 pygame 库，主要用于定义 Rect 等对象

# --- 显示与性能 ---
# 游戏窗口的默认宽度（像素）
SCREEN_WIDTH = 1920
# 游戏窗口的默认高度（像素）
SCREEN_HEIGHT = 1080
# 游戏的目标帧率（Frames Per Second），即每秒刷新画面的次数，60是流畅的标准
FPS = 60
# 字体名称列表，程序会按此顺序在你的操作系统中寻找可用的字体
# 用于显示所有中文和英文字符。如果第一个没找到，会尝试下一个。
FONT_NAMES = [
    "Microsoft YaHei", # 微软雅黑 (Windows 常用)
    "SimHei",          # 黑体 (Windows 常用)
    "PingFang SC",     # 苹方 (macOS 常用)
    "WenQuanYi Zen Hei", # 文泉驿正黑 (Linux 常用)
    None               # 如果以上都找不到，则使用 Pygame 的默认英文字体
]
# 游戏窗口的标题
TITLE = "思维火花 (Mind Spark)"

# --- 颜色 ---
# 背景颜色，使用 RGB 值 (Red, Green, Blue)，范围 0-255。这是一个深灰色。
BG_COLOR = (23, 23, 31)
# 默认的文本颜色，如UI面板上的文字颜色。这是一个灰白色。
TEXT_COLOR = (240, 240, 240)
# 节点（神经元）的颜色列表。新创建的节点会按顺序循环使用这些颜色。
NEURON_COLORS = [
    (59, 130, 246),  # 蓝色
    (34, 197, 94),   # 绿色
    (234, 179, 8),   # 黄色
    (239, 68, 68),   # 红色
    (168, 85, 247),  # 紫色
    (236, 72, 153)   # 粉色
]
# 用于删除相关提示的颜色，如删除图标和警告文字。这是一个鲜红色。
DELETE_COLOR = (220, 38, 38)
# 用于警告提示的颜色，如组删除前的确认符号 "!"。这是一个黄色。
WARNING_COLOR = (234, 179, 8)

# --- 节点（神经元）物理属性 ---
# 创建新节点时，其质量的随机范围下限。质量影响大小和碰撞行为。
INITIAL_NEURON_MASS_MIN = 50
# 创建新节点时，其质量的随机范围上限。
INITIAL_NEURON_MASS_MAX = 100
# 节点的最小质量。在质量传递后，节点的质量不会低于此值。
MIN_NEURON_MASS = 5
# 半径的基础缩放因子。节点的视觉半径 = sqrt(质量) * 此因子。
RADIUS_BASE_SCALE = 5
# 创建新节点时，其初始速度在每个轴向上的最大绝对值。
MAX_INITIAL_SPEED = 100.0
# 节点与窗口边缘碰撞时的“弹性”系数。1.0 表示完全弹性碰撞（没有能量损失）。
WALL_RESTITUTION = 1.0
# 节点之间碰撞时的“弹性”系数。1.0 表示完全弹性碰撞。
NEURON_COLLISION_RESTITUTION = 1.0
# 节点碰撞时，质量从较小者向较大者转移的百分比。例如 0.01 表示转移自身质量的 1%。
MASS_TRANSFER_PERCENTAGE = 0.01

# --- 交互与动画 ---
# 拖拽设置速度时，鼠标位移转换成节点速度的缩放因子。值越大，速度越大。
VELOCITY_SCALING_FACTOR = 0.5
# 调整速度时，先松开右键的宽限期（毫秒）。在此时间内松开左键，速度依然会被设置。
VELOCITY_GRACE_PERIOD = 500
# 节点碰撞时，瞬间放大的倍数，用于产生 "Q弹" 效果。1.25 表示放大到 125%。
NEURON_BOUNCE_FACTOR = 1.25
# 节点 "Q弹" 效果的恢复速度。值在 0 到 1 之间，越大恢复得越快。
NEURON_BOUNCE_RECOVERY = 0.15

# --- UI 元素 ---
# 拖拽节点时，其边框的高亮颜色。
HELD_NEURON_BORDER_COLOR = (250, 250, 250)
# 拖拽节点时，其边框的宽度（像素）。
HELD_NEURON_BORDER_WIDTH = 3
# （此参数当前未使用，但可用于实现半透明效果）被拖拽节点的透明度。
HELD_NEURON_OPACITY = 200
# 当节点被拖拽到非法位置（如与其他节点重叠）时，其边框显示的颜色。
INVALID_PLACEMENT_BORDER_COLOR = DELETE_COLOR

# NEW: 节点删除区域的定义
# 一个 pygame.Rect 对象，定义了屏幕右下角的删除区域 (x, y, 宽度, 高度)。
DELETE_ZONE_RECT = pygame.Rect(SCREEN_WIDTH - 120, SCREEN_HEIGHT - 120, 100, 100)

# 节点内文字的最小字号。即使空间再小，字体也不会小于此值。
MIN_FONT_SIZE = 8
# （此参数当前未使用，但可用于旧的简单字体缩放逻辑）
MAX_FONT_SIZE_PROPORTION = 0.8
# （此参数当前未使用，但可用于旧的简单字体缩放逻辑）
FONT_LENGTH_ADJUST_FACTOR = 0.8

# 左上角信息面板的背景颜色，RGBA格式 (Red, Green, Blue, Alpha/透明度)。
INFO_PANEL_COLOR = (39, 39, 47, 200)
# 右上角组管理菜单的背景颜色，RGBA格式。
GROUP_MENU_COLOR = (39, 39, 47, 220)
# 右上角组管理菜单图标（汉堡菜单）的中心坐标 (x, y)。
GROUP_MENU_ICON_POS = (SCREEN_WIDTH - 50, 30)
# （此参数当前未使用，但可用于定义图标的点击范围）
GROUP_MENU_ICON_RADIUS = 15
# 鼠标悬浮在菜单图标附近多大范围内（像素半径）时，图标会高亮。
GROUP_MENU_HOVER_RADIUS = 100