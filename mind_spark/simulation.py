# FILENAME: simulation.py

import pygame
import random
import math
from neuron import Neuron
from ui_manager import UIManager
from data_manager import DataManager
import config
import utils

vec = pygame.math.Vector2

class Simulation:
    def __init__(self):
        pygame.init()
        self.fullscreen = False
        flags = pygame.RESIZABLE
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        pygame.display.set_caption(config.TITLE)
        self.clock = pygame.time.Clock()
        self.data_manager = DataManager()
        self.ui_manager = UIManager(self)
        self.is_running = True; self.paused = False; self.is_loading = True
        self.neurons = []; self.neuron_groups = []; self.active_group_index = 0
        self.held_neuron = None; self.velocity_adjust_mode = False; self.velocity_grace_period_timer = None
        
        # NEW: IME 支持属性
        self.ime_editing = False
        self.ime_text = ""
        self.ime_editing_pos = 0
        self.ime_cursor_pos = None

        self.new_neuron_preview = None; self.input_text = ""
        self._load_initial_data()

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN | pygame.SCALED if self.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        self.ui_manager.screen_rect = self.screen.get_rect()

    def run(self):
        while self.is_running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self._handle_events()
            if not self.paused: self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        if self.velocity_grace_period_timer and pygame.time.get_ticks() - self.velocity_grace_period_timer > config.VELOCITY_GRACE_PERIOD:
            self.velocity_adjust_mode = False; self.velocity_grace_period_timer = None
        
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.is_running = False
            
            # MODIFIED: 重构事件处理以支持中文输入 (IME)
            if self.new_neuron_preview: # 如果正在创建新节点
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN: self._confirm_new_neuron()
                    elif event.key == pygame.K_ESCAPE: self._cancel_new_neuron()
                    elif event.key == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
                elif event.type == pygame.TEXTINPUT:
                    self.input_text += event.text
                # NEW: 处理IME事件
                elif event.type == pygame.TEXTEDITING:
                    self.ime_editing = True
                    self.ime_text = event.text
                    self.ime_editing_pos = event.start
                if event.type in [pygame.KEYDOWN, pygame.TEXTINPUT]:
                    self.ime_editing = False # 任何常规输入都会终止IME编辑
                continue

            # --- 常规事件处理 ---
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                self._toggle_fullscreen()
            if self.ui_manager.handle_event(event): continue
            self._handle_mouse_events(event, mouse_pos)

    def _handle_mouse_events(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.held_neuron = self._get_neuron_at(mouse_pos)
                if self.held_neuron: self.held_neuron.start_drag(); self.paused = True
                elif self.new_neuron_preview: self._cancel_new_neuron()
            elif event.button == 3:
                if self.held_neuron: self.velocity_adjust_mode = True; self.velocity_grace_period_timer = None
                else: self._start_new_neuron(mouse_pos)
        
        elif event.type == pygame.MOUSEMOTION:
            if self.held_neuron and not pygame.mouse.get_pressed()[2]:
                self.held_neuron.position = vec(mouse_pos)
                self.held_neuron.isInvalidPlacement = not self._check_placement_validity(self.held_neuron)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.velocity_adjust_mode or self.velocity_grace_period_timer: self._set_neuron_velocity(mouse_pos)
                if self.held_neuron:
                    self.held_neuron.stop_drag(not self.held_neuron.isInvalidPlacement)
                    self.held_neuron = None; self.paused = False; self.velocity_adjust_mode = False; self.velocity_grace_period_timer = None
            elif event.button == 3:
                if self.velocity_adjust_mode: self.velocity_grace_period_timer = pygame.time.get_ticks()

    def _update(self, dt):
        for n in self.neurons: n.update(dt, self.screen.get_rect())
        for i in range(len(self.neurons)):
            for j in range(i + 1, len(self.neurons)): self._handle_neuron_collision(self.neurons[i], self.neurons[j])

    def _handle_neuron_collision(self, n1, n2):
        delta = n1.position - n2.position
        dist_sq = delta.length_squared()
        min_dist = n1.radius + n2.radius
        
        if dist_sq < min_dist**2:
            # BUG FIX: 节点粘连修复
            # 1. 只有当它们相互靠近时才进行动量交换
            if delta.dot(n1.velocity - n2.velocity) < 0:
                n1.trigger_bounce(); n2.trigger_bounce()
                # --- 物理响应 ---
                normal = delta.normalize(); tangent = vec(-normal.y, normal.x)
                v1n = n1.velocity.dot(normal); v1t = n1.velocity.dot(tangent)
                v2n = n2.velocity.dot(normal); v2t = n2.velocity.dot(tangent)
                m1, m2 = n1.mass, n2.mass
                new_v1n = (v1n * (m1 - m2) + 2 * m2 * v2n) / (m1 + m2) * config.NEURON_COLLISION_RESTITUTION
                new_v2n = (v2n * (m2 - m1) + 2 * m1 * v1n) / (m1 + m2) * config.NEURON_COLLISION_RESTITUTION
                n1.velocity = normal * new_v1n + tangent * v1t
                n2.velocity = normal * new_v2n + tangent * v2t
                
                transfer_amount = min(m1, m2) * config.MASS_TRANSFER_PERCENTAGE
                if m1 > m2 and m2 - transfer_amount > config.MIN_NEURON_MASS: n1.mass += transfer_amount; n2.mass -= transfer_amount
                elif m2 > m1 and m1 - transfer_amount > config.MIN_NEURON_MASS: n2.mass += transfer_amount; n1.mass -= transfer_amount
                n1.update_radius(); n2.update_radius()

            # 2. 强力分离重叠的节点
            dist = dist_sq**0.5
            overlap = (min_dist - dist)
            separation_vec = delta.normalize() * overlap * 0.5
            n1.position += separation_vec
            n2.position -= separation_vec
    
    def _draw(self):
        self.screen.fill(config.BG_COLOR)
        for n in self.neurons: n.draw(self.screen)
        if self.velocity_adjust_mode and pygame.mouse.get_pressed()[2]:
            start_pos = self.held_neuron.position; end_pos = vec(pygame.mouse.get_pos())
            utils.draw_arrow(self.screen, config.HELD_NEURON_BORDER_COLOR, start_pos, end_pos)
        
        # MODIFIED: 绘制输入框和IME文本
        if self.new_neuron_preview:
            # 基础输入框
            input_rect = pygame.Rect(0, 0, 300, 40)
            input_rect.center = self.new_neuron_preview
            pygame.draw.rect(self.screen, (50, 50, 50), input_rect, border_radius=5)
            pygame.draw.rect(self.screen, config.HELD_NEURON_BORDER_COLOR, input_rect, 1, 5)
            
            font = utils.get_font(20)
            # 绘制已确认的文本
            text_surface = font.render(self.input_text, True, config.TEXT_COLOR)
            self.screen.blit(text_surface, (input_rect.x + 10, input_rect.centery - text_surface.get_height() // 2))
            
            # 绘制IME正在编辑的文本
            if self.ime_editing:
                ime_surface = font.render(self.ime_text, True, (200, 200, 200))
                # 在已确认文本后面绘制
                ime_x = input_rect.x + 10 + text_surface.get_width()
                ime_y = input_rect.centery - ime_surface.get_height() // 2
                pygame.draw.rect(ime_surface, (0, 255, 0), (0, ime_surface.get_height() - 2, ime_surface.get_width(), 2)) # 下划线
                self.screen.blit(ime_surface, (ime_x, ime_y))

        self.ui_manager.draw(self.screen, pygame.mouse.get_pos())
        pygame.display.flip()

    def _start_new_neuron(self, pos):
        self.paused = True; self.new_neuron_preview = pos; self.input_text = ""
        # NEW: 启用IME支持
        pygame.key.start_text_input()
        if self.ime_cursor_pos:
            pygame.key.set_text_input_rect(pygame.Rect(self.ime_cursor_pos, (300, 40)))

    def _cancel_new_neuron(self):
        pygame.key.stop_text_input()
        self.new_neuron_preview = None; self.input_text = ""
        self.ime_editing = False; self.ime_text = ""
        if not self.held_neuron: self.paused = False
    
    # --- 其他方法保持不变，为简洁省略 ---
    def _load_initial_data(self):
        self.is_loading = True; self.neuron_groups = self.data_manager.load_neuron_groups(); self.switch_group(0)
        self.is_loading = False; self.paused = False

    def _create_neurons_from_group(self, group_index):
        self.neurons.clear()
        group = self.neuron_groups[group_index]
        words = group.get('neurons', [])
        for i, word in enumerate(words):
            while True:
                pos = vec(random.randint(50, config.SCREEN_WIDTH - 50), random.randint(50, config.SCREEN_HEIGHT - 50))
                new_neuron = Neuron(text=word, position=pos, color=config.NEURON_COLORS[i % len(config.NEURON_COLORS)])
                if not any((new_neuron.position - n.position).length() < new_neuron.radius + n.radius for n in self.neurons):
                    self.neurons.append(new_neuron); break

    def switch_group(self, group_index):
        if 0 <= group_index < len(self.neuron_groups):
            self.active_group_index = group_index; self._create_neurons_from_group(group_index)

    def add_new_group(self):
        new_group_name = f"神经元组 {len(self.neuron_groups) + 1}"
        new_group = {"name": new_group_name, "neurons": ["神经元"]}
        self.neuron_groups.append(new_group)
        self.switch_group(len(self.neuron_groups) - 1); self.data_manager.save_neuron_groups(self.neuron_groups)

    def _get_neuron_at(self, pos):
        for n in reversed(self.neurons):
            if (vec(pos) - n.position).length_squared() < n.radius**2: return n
        return None

    def _check_placement_validity(self, neuron):
        r = neuron.radius * neuron.scale
        if not (r <= neuron.position.x <= self.screen.get_width() - r and r <= neuron.position.y <= self.screen.get_height() - r): return False
        for other in self.neurons:
            if other.id != neuron.id and (neuron.position - other.position).length() < r + other.radius * other.scale: return False
        return True

    def _set_neuron_velocity(self, mouse_pos):
        if self.held_neuron: self.held_neuron.velocity = (vec(mouse_pos) - self.held_neuron.position) * config.VELOCITY_SCALING_FACTOR

    def _confirm_new_neuron(self):
        text = self.input_text.strip()
        if text:
            pos = self.new_neuron_preview
            new_neuron = Neuron(text, pos)
            for _ in range(100):
                if self._check_placement_validity(new_neuron): break
                new_neuron.position += vec(random.uniform(-10, 10), random.uniform(-10, 10))
            self.neurons.append(new_neuron)
            self.neuron_groups[self.active_group_index]['neurons'].append(text)
            self.data_manager.save_neuron_groups(self.neuron_groups)
        self._cancel_new_neuron()