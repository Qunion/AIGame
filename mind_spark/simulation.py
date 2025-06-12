# FILENAME: simulation.py

import pygame
import random
import math
from neuron import Neuron
from ui_manager import UIManager
from data_manager import DataManager
import config
import utils
import input_dialog

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
        self.is_running = True
        
        self.paused = False
        self.paused_by_user = False

        self.is_loading = True
        self.neurons = []; self.neuron_groups = []; self.active_group_index = 0
        self.held_neuron = None; self.velocity_adjust_mode = False; self.velocity_grace_period_timer = None
        self._load_initial_data()

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN | pygame.SCALED if self.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        self.ui_manager.screen_rect = self.screen.get_rect()

    def run(self):
        while self.is_running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self.paused = self.paused_by_user
            self._handle_events()
            if not self.paused: self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        if self.velocity_grace_period_timer and pygame.time.get_ticks() - self.velocity_grace_period_timer > config.VELOCITY_GRACE_PERIOD:
            self.velocity_adjust_mode = False; self.velocity_grace_period_timer = None
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.is_running = False
            
            if self.ui_manager.handle_event(event): continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                self._toggle_fullscreen()
            
            self._handle_mouse_events(event)

    def _handle_mouse_events(self, event):
        mouse_pos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.held_neuron = self._get_neuron_at(mouse_pos)
                if self.held_neuron: self.held_neuron.start_drag(); self.paused_by_user = True
            elif event.button == 3:
                if self.held_neuron: self.velocity_adjust_mode = True; self.velocity_grace_period_timer = None
                else: self._create_new_neuron_at(mouse_pos)
        
        elif event.type == pygame.MOUSEMOTION:
            if self.held_neuron and not pygame.mouse.get_pressed()[2]:
                self.held_neuron.position = vec(mouse_pos)
                self.held_neuron.isInvalidPlacement = not self._check_placement_validity(self.held_neuron)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.velocity_adjust_mode or self.velocity_grace_period_timer: self._set_neuron_velocity(mouse_pos)
                if self.held_neuron:
                    self.held_neuron.stop_drag(not self.held_neuron.isInvalidPlacement)
                    self.held_neuron = None; self.paused_by_user = False; self.velocity_adjust_mode = False; self.velocity_grace_period_timer = None
            elif event.button == 3:
                if self.velocity_adjust_mode: self.velocity_grace_period_timer = pygame.time.get_ticks()

    def _create_new_neuron_at(self, pos):
        """MODIFIED: 移除窗口最小化调用"""
        self.paused_by_user = True
        
        # 不再最小化窗口
        # pygame.display.iconify() 

        text = input_dialog.ask_string("创建新节点", "请输入节点文本:")

        # 也不再需要恢复窗口
        # pygame.display.flip() 
        # pygame.display.set_mode(self.screen.get_size(), self.screen.get_flags())
        
        if text and text.strip():
            text = text.strip()
            new_neuron = Neuron(text, pos)
            for _ in range(100):
                if self._check_placement_validity(new_neuron): break
                new_neuron.position += vec(random.uniform(-10, 10), random.uniform(-10, 10))
            self.neurons.append(new_neuron)
            self.neuron_groups[self.active_group_index]['neurons'].append(text)
            self.data_manager.save_neuron_groups(self.neuron_groups)
        
        self.paused_by_user = False

    def add_new_group(self):
        """MODIFIED: 移除窗口最小化调用"""
        self.paused_by_user = True
        
        new_group_name = input_dialog.ask_string("创建新节点组", "请输入新组的名称:")

        if not new_group_name or not new_group_name.strip():
            self.paused_by_user = False
            return # 如果用户取消或输入为空，则直接返回
        
        new_group_name = new_group_name.strip()
        
        new_group = {"name": new_group_name, "neurons": ["新节点"]}
        self.neuron_groups.append(new_group)
        
        new_index = len(self.neuron_groups) - 1
        self.switch_group(new_index)
        self.data_manager.save_neuron_groups(self.neuron_groups)
        
        self.paused_by_user = False

    # --- 以下方法保持不变 ---
    def _update(self, dt):
        for n in self.neurons: n.update(dt, self.screen.get_rect())
        for i in range(len(self.neurons)):
            for j in range(i + 1, len(self.neurons)): self._handle_neuron_collision(self.neurons[i], self.neurons[j])

    def _handle_neuron_collision(self, n1, n2):
        delta = n1.position - n2.position; dist_sq = delta.length_squared()
        min_dist = n1.radius + n2.radius
        if dist_sq < min_dist**2:
            if delta.dot(n1.velocity - n2.velocity) < 0:
                n1.trigger_bounce(); n2.trigger_bounce()
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
            dist = dist_sq**0.5; overlap = (min_dist - dist); separation_vec = delta.normalize() * overlap * 0.5
            n1.position += separation_vec; n2.position -= separation_vec
    
    def _draw(self):
        self.screen.fill(config.BG_COLOR)
        for n in self.neurons: n.draw(self.screen)
        if self.velocity_adjust_mode and pygame.mouse.get_pressed()[2]:
            start_pos = self.held_neuron.position; end_pos = vec(pygame.mouse.get_pos())
            utils.draw_arrow(self.screen, config.HELD_NEURON_BORDER_COLOR, start_pos, end_pos)
        self.ui_manager.draw(self.screen, pygame.mouse.get_pos())
        pygame.display.flip()
        
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