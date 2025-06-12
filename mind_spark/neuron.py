# FILENAME: neuron.py

import pygame
import pygame.gfxdraw
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
        self.mass = mass if mass is not None else random.uniform(config.INITIAL_NEURON_MASS_MIN, config.INITIAL_NEURON_MASS_MAX)
        self.velocity = velocity if velocity is not None else vec(random.uniform(-config.MAX_INITIAL_SPEED, config.MAX_INITIAL_SPEED), random.uniform(-config.MAX_INITIAL_SPEED, config.MAX_INITIAL_SPEED))
        self.color = color if color is not None else random.choice(config.NEURON_COLORS)
        self.radius = self.calculate_radius()
        
        # 状态
        self.isHeld = False
        self.isInvalidPlacement = False
        self.originalPositionBeforeDrag = None
        self.scale = 1.0
        self.is_marked_for_deletion = False # NEW: 待删除标记

    def calculate_radius(self): return math.sqrt(self.mass) * config.RADIUS_BASE_SCALE
    def update_radius(self): self.radius = self.calculate_radius()
    def trigger_bounce(self): self.scale = config.NEURON_BOUNCE_FACTOR

    def update(self, dt, container_rect):
        self.position += self.velocity * dt
        if self.scale > 1.0: self.scale += (1.0 - self.scale) * config.NEURON_BOUNCE_RECOVERY
        else: self.scale = 1.0

        r = self.radius * self.scale
        if self.position.x - r < 0: self.position.x = r; self.velocity.x *= -config.WALL_RESTITUTION
        elif self.position.x + r > container_rect.width: self.position.x = container_rect.width - r; self.velocity.x *= -config.WALL_RESTITUTION
        if self.position.y - r < 0: self.position.y = r; self.velocity.y *= -config.WALL_RESTITUTION
        elif self.position.y + r > container_rect.height: self.position.y = container_rect.height - r; self.velocity.y *= -config.WALL_RESTITUTION

    def draw(self, surface):
        visual_radius = int(self.radius * self.scale)
        pos_x, pos_y = int(self.position.x), int(self.position.y)

        pygame.gfxdraw.aacircle(surface, pos_x, pos_y, visual_radius, self.color)
        pygame.gfxdraw.filled_circle(surface, pos_x, pos_y, visual_radius, self.color)

        if self.text: utils.render_text_in_circle(surface, self.text, self.position, visual_radius, config.TEXT_COLOR)

        # NEW: 如果标记为待删除，绘制一个 "X"
        if self.is_marked_for_deletion:
            utils.render_text_ui(surface, "X", pygame.Rect(0, 0, visual_radius*2, visual_radius*2), config.DELETE_COLOR, font_size=int(visual_radius*1.5), center=self.position)

        if self.isHeld:
            border_color = config.INVALID_PLACEMENT_BORDER_COLOR if self.isInvalidPlacement or self.is_marked_for_deletion else config.HELD_NEURON_BORDER_COLOR
            pygame.gfxdraw.aacircle(surface, pos_x, pos_y, visual_radius, border_color)
            if config.HELD_NEURON_BORDER_WIDTH > 1:
                pygame.gfxdraw.aacircle(surface, pos_x, pos_y, visual_radius - (config.HELD_NEURON_BORDER_WIDTH - 1), border_color)

    def start_drag(self):
        if not self.isHeld: self.isHeld = True; self.originalPositionBeforeDrag = vec(self.position)

    def stop_drag(self, is_legal_pos):
        if not is_legal_pos and self.originalPositionBeforeDrag: self.position = self.originalPositionBeforeDrag
        self.isHeld = False; self.isInvalidPlacement = False; self.originalPositionBeforeDrag = None; self.is_marked_for_deletion = False