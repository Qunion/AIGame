import pymunk

# --- 窗口与界面 ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
CAPTION = "左纳乌平台对决"
FPS = 60
SNAP_DISTANCE = 30 # 吸附距离（像素）

# --- 颜色定义 ---
COLORS = {
    "background": (21, 30, 39), "ground": (50, 60, 70), "grid": (40, 55, 70),
    "ui_background": (30, 45, 60), "text": (220, 225, 230), "button": (50, 70, 90),
    "button_hover": (80, 100, 120), "player_hp": (0, 255, 150), "ai_hp": (255, 0, 100),
    "hp_bg": (10, 20, 30), "laser": (0, 255, 255), "snap_indicator": (255, 255, 0), # 吸附指示器颜色
}

# --- 物理引擎 ---
GRAVITY = (0, -981) # 修复：Pymunk中Y轴向上，所以重力是负值

# --- 游戏状态 ---
class GameState:
    ASSEMBLY = 1; COMBAT = 2; END_SCREEN = 3

# --- 碰撞类型 ---
COLLISION_TYPES = {"machine_part": 1}

# --- 物理引擎 ---
GRAVITY = (0, 981) # 修复：Pygame中Y轴向下为正，所以重力是正值

# --- 左纳乌装置定义 ---
DEVICE_DEFINITIONS = {
    "钢条": {
        "cost": 5, "mass_per_length": 0.1, "hp_per_length": 2,
        "color": (150, 160, 170),
        "shape_info": {"type": "segment", "radius": 5},
    },
    "平台方块": {
        "cost": 10, "mass": 20, "hp": 200, "color": (110, 130, 150),
        "shape_info": {"type": "box", "size": (50, 50)},
    },
    "小轮胎": {
        "cost": 20, "mass": 15, "hp": 80, "color": (70, 80, 90),
        "shape_info": {"type": "circle", "radius": 20},
        "combat_stats": {"type": "mobility", "torque": 1_000_000 * 5, "rate": 10}
    },
    "魔像头": {
        "cost": 50, "mass": 30, "hp": 150, "color": (255, 180, 0),
        "shape_info": {"type": "box", "size": (60, 40)},
        "is_core": True,
        "combat_stats": {"type": "controller", "scan_range": 400, "scan_interval": 0.25}
    },
    "光线头": {
        "cost": 40, "mass": 10, "hp": 60, "color": (0, 200, 220),
        "shape_info": {"type": "box", "size": (30, 20)},
        "combat_stats": {"type": "weapon", "damage": 2, "range": 500, "cooldown": 0.1}
    }
}