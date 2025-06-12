# FILENAME: neuron.py

import pygame
import pygame.gfxdraw # NEW: 导入用于抗锯齿绘图的模块
import uuid
import math
import random
import config
import utils

vec = pygame.math.Vector2

class Neuron:
    def __init__(self, text, position, mass=None, velocity=None, color=None):
        self.id = str(uuid.uuid4())
        self.text = text
        self.position = vec(position)
        
        self.mass = mass if mass is not None else random.uniform(
            config.INITIAL_NEURON_MASS_MIN, config.INITIAL_NEURON_MASS_MAX
        )
        self.velocity = velocity if velocity is not None else vec(
            random.uniform(-config.MAX_INITIAL_SPEED, config.MAX_INITIAL_SPEED),
            random.uniform(-config.MAX_INITIAL_SPEED, config.MAX_INITIAL_SPEED)
        )
        
        self.color = color if color is not None else random.choice(config.NEURON_COLORS)
        self.radius = self.calculate_radius()

        # 状态
        self.isHeld = False
        self.isInvalidPlacement = False
        self.originalPositionBeforeDrag = None

        # NEW: Q弹动画属性
        self.scale = 1.0

    def calculate_radius(self):
        return math.sqrt(self.mass) * config.RADIUS_BASE_SCALE

    def update_radius(self):
        self.radius = self.calculate_radius()

    def trigger_bounce(self):
        """触发Q弹动画"""
        self.scale = config.NEURON_BOUNCE_FACTOR

    def update(self, dt, container_rect):
        """更新神经元的位置、动画和处理边界碰撞"""
        # 更新位置
        self.position += self.velocity * dt

        # NEW: 更新Q弹动画的缩放值，使其平滑恢复到1.0
        # 使用lerp (线性插值) 的思想来平滑过渡
        if self.scale != 1.0:
            self.scale += (1.0 - self.scale) * config.NEURON_BOUNCE_RECOVERY

        # 边界碰撞
        if self.position.x - self.radius < 0:
            self.position.x = self.radius; self.velocity.x *= -config.WALL_RESTITUTION
        elif self.position.x + self.radius > container_rect.width:
            self.position.x = container_rect.width - self.radius; self.velocity.x *= -config.WALL_RESTITUTION
        if self.position.y - self.radius < 0:
            self.position.y = self.radius; self.velocity.y *= -config.WALL_RESTITUTION
        elif self.position.y + self.radius > container_rect.height:
            self.position.y = container_rect.height - self.radius; self.velocity.y *= -config.WALL_RESTITUTION

    def draw(self, surface):
        """MODIFIED: 使用gfxdraw绘制平滑的、可缩放的神经元"""
        # 计算视觉半径（应用Q弹缩放效果）
        visual_radius = int(self.radius * self.scale)
        # 绘图函数需要整数坐标
        pos_x, pos_y = int(self.position.x), int(self.position.y)

        # 绘制主体 (两步法实现抗锯齿填充圆形)
        pygame.gfxdraw.aacircle(surface, pos_x, pos_y, visual_radius, self.color)
        pygame.gfxdraw.filled_circle(surface, pos_x, pos_y, visual_radius, self.color)

        # 绘制文本 (文本也应在视觉中心)
        utils.draw_text_in_circle(surface, self.text, self.position, visual_radius)

        # 绘制高亮或警示边框
        if self.isHeld:
            border_color = config.INVALID_PLACEMENT_BORDER_COLOR if self.isInvalidPlacement else config.HELD_NEURON_BORDER_COLOR
            # 使用gfxdraw绘制平滑的边框
            pygame.gfxdraw.aacircle(surface, pos_x, pos_y, visual_radius, border_color)
            if config.HELD_NEURON_BORDER_WIDTH > 1:
                pygame.gfxdraw.aacircle(surface, pos_x, pos_y, visual_radius - (config.HELD_NEURON_BORDER_WIDTH -1), border_color)

    def start_drag(self):
        if not self.isHeld:
            self.isHeld = True
            self.originalPositionBeforeDrag = vec(self.position)

    def stop_drag(self, is_legal_pos):
        if not is_legal_pos and self.originalPositionBeforeDrag:
            self.position = self.originalPositionBeforeDrag
        self.isHeld = False
        self.isInvalidPlacement = False
        self.originalPositionBeforeDrag = None