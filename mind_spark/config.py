# FILENAME: config.py
#
# 存放所有可配置的常量

import pygame

# --- 显示与性能 ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
FONT_NAMES = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "WenQuanYi Zen Hei", None
]
TITLE = "思维火花 (Mind Spark)"

# --- 颜色 ---
BG_COLOR = (23, 23, 31)
TEXT_COLOR = (240, 240, 240)
NEURON_COLORS = [
    (59, 130, 246), (34, 197, 94), (234, 179, 8),
    (239, 68, 68), (168, 85, 247), (236, 72, 153)
]

# --- 神经元物理属性 ---
# 神经元初始质量的最小值，单位任意，用于初始化神经元时确定其质量下限
INITIAL_NEURON_MASS_MIN = 50
# 神经元初始质量的最大值，单位任意，用于初始化神经元时确定其质量上限
INITIAL_NEURON_MASS_MAX = 100
# 神经元质量的最小值，单位任意，神经元质量不会低于此值
MIN_NEURON_MASS = 5
# 半径基础缩放因子，用于根据神经元质量计算其半径
RADIUS_BASE_SCALE = 5
# 神经元初始速度的最大值，单位任意，用于初始化神经元时确定其速度上限
MAX_INITIAL_SPEED = 100.0
# 神经元与墙壁碰撞时的恢复系数，取值范围 0-1，值越大碰撞后损失的能量越小
WALL_RESTITUTION = 1
# 神经元之间碰撞时的恢复系数，取值范围 0-1，值越大碰撞后损失的能量越小
NEURON_COLLISION_RESTITUTION = 1
# 质量转移百分比，当神经元发生某些交互时，质量转移的比例
MASS_TRANSFER_PERCENTAGE = 0.01

# --- 交互与动画 ---
VELOCITY_SCALING_FACTOR = 0.5 # 速度缩放因子
VELOCITY_GRACE_PERIOD = 500 # 速度调整的宽限期 (毫秒)

# NEW: Q弹动画参数
NEURON_BOUNCE_FACTOR = 1.25  # 碰撞时放大的倍数
NEURON_BOUNCE_RECOVERY = 0.15 # 恢复到正常大小的速度 (值越大恢复越快)


# --- UI 元素 ---
HELD_NEURON_BORDER_COLOR = (250, 250, 250)
HELD_NEURON_BORDER_WIDTH = 3
HELD_NEURON_OPACITY = 200
INVALID_PLACEMENT_BORDER_COLOR = (220, 38, 38)

MIN_FONT_SIZE = 10
MAX_FONT_SIZE_PROPORTION = 0.6
FONT_LENGTH_ADJUST_FACTOR = 0.8

INFO_PANEL_COLOR = (39, 39, 47, 200)
GROUP_MENU_COLOR = (39, 39, 47, 220)
GROUP_MENU_ICON_POS = (SCREEN_WIDTH - 50, 30)
GROUP_MENU_ICON_RADIUS = 15
GROUP_MENU_HOVER_RADIUS = 100

MOUSE_FOLLOWER_COLOR = (56, 189, 248, 100)
MOUSE_FOLLOWER_RADIUS = 15