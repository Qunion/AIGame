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
        self.neurons = []
        self.neuron_groups = []
        self.active_group_index = 0
        self.held_neuron = None
        self.velocity_adjust_mode = False
        self.velocity_grace_period_timer = None

        # 输入线程状态管理
        self.input_thread = None
        self.input_callback = None
        self.input_pos = None

        self._load_initial_data()

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN | pygame.SCALED if self.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        self.ui_manager.screen_rect = self.screen.get_rect()

    def run(self):
        while self.is_running:
            dt = self.clock.tick(config.FPS) / 1000.0
            
            # 暂停条件：用户交互 或 正在等待输入
            self.paused = self.paused_by_user or (self.input_thread is not None)
            
            self._handle_events()

            if not self.paused:
                self._update(dt)

            self._draw()
        pygame.quit()

    def _handle_events(self):
        # 检查输入线程的结果
        if self.input_thread:
            result = self.input_thread.get_result()
            if result != "NO_RESULT_YET":
                if self.input_callback:
                    # 如果有结果 (不是 None)，则调用回调
                    if result is not None:
                        self.input_callback(result, self.input_pos)
                self._stop_input_thread()
        
        # 宽限期计时器
        if self.velocity_grace_period_timer and pygame.time.get_ticks() - self.velocity_grace_period_timer > config.VELOCITY_GRACE_PERIOD:
            self.velocity_adjust_mode = False
            self.velocity_grace_period_timer = None
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                self._stop_input_thread() # 退出时确保线程关闭
                return
            
            # 如果正在输入，任何点击都取消输入
            if self.input_thread is not None:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    print("检测到遮罩被点击，取消输入。")
                    self._stop_input_thread()
                continue # 消耗所有其他事件

            if self.ui_manager.handle_event(event):
                continue
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                self._toggle_fullscreen()
            
            self._handle_mouse_events(event)

    def _handle_mouse_events(self, event):
        mouse_pos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and not self.ui_manager.is_menu_open:
                self.held_neuron = self._get_neuron_at(mouse_pos)
                if self.held_neuron:
                    self.held_neuron.start_drag()
                    self.paused_by_user = True
            elif event.button == 3:
                if self.held_neuron:
                    self.velocity_adjust_mode = True
                    self.velocity_grace_period_timer = None
                else:
                    self._create_new_neuron_at(mouse_pos)
        elif event.type == pygame.MOUSEMOTION:
            if self.held_neuron and not pygame.mouse.get_pressed()[2]:
                self.held_neuron.position = vec(mouse_pos)
                is_in_delete_zone = config.DELETE_ZONE_RECT.collidepoint(self.held_neuron.position)
                self.held_neuron.is_marked_for_deletion = is_in_delete_zone
                self.held_neuron.isInvalidPlacement = not self._check_placement_validity(self.held_neuron) and not is_in_delete_zone
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.held_neuron and self.held_neuron.is_marked_for_deletion:
                    self._delete_neuron(self.held_neuron)
                elif self.velocity_adjust_mode or self.velocity_grace_period_timer:
                    self._set_neuron_velocity(mouse_pos)
                if self.held_neuron:
                    self.held_neuron.stop_drag(not self.held_neuron.isInvalidPlacement)
                self.held_neuron = None
                self.paused_by_user = False
                self.velocity_adjust_mode = False
                self.velocity_grace_period_timer = None
            elif event.button == 3:
                if self.velocity_adjust_mode:
                    self.velocity_grace_period_timer = pygame.time.get_ticks()

    def _start_input_thread(self, title, prompt, callback, pos=None):
        """启动一个非阻塞的输入线程"""
        if self.input_thread: return
        self.input_callback = callback
        self.input_pos = pos
        self.input_thread = input_dialog.ask_string_non_blocking(title, prompt)

    def _stop_input_thread(self):
        """安全地停止输入线程"""
        if self.input_thread:
            self.input_thread.close()
            self.input_thread = None
            self.input_callback = None
            self.input_pos = None

    def _create_new_neuron_at(self, pos):
        self._start_input_thread("创建新节点", "请输入节点文本:", self._finalize_neuron_creation, pos)

    def _finalize_neuron_creation(self, text, pos):
        if text and text.strip():
            text = text.strip()
            new_neuron = Neuron(text, pos)
            for _ in range(100):
                if self._check_placement_validity(new_neuron):
                    break
                new_neuron.position += vec(random.uniform(-10, 10), random.uniform(-10, 10))
            self.neurons.append(new_neuron)
            self.neuron_groups[self.active_group_index]['neurons'].append(text)
            self.data_manager.save_neuron_groups(self.neuron_groups)

    def add_new_group(self):
        self._start_input_thread("创建新节点组", "请输入新组的名称:", self._finalize_group_creation)

    def _finalize_group_creation(self, text, pos=None): # pos 参数是为了统一回调格式
        if text and text.strip():
            new_group_name = text.strip()
        else:
            return

        new_group = {"name": new_group_name, "neurons": ["新节点"]}
        self.neuron_groups.append(new_group)
        new_index = len(self.neuron_groups) - 1
        self.switch_group(new_index)
        self.data_manager.save_neuron_groups(self.neuron_groups)

    def _delete_neuron(self, neuron_to_delete):
        self.neurons.remove(neuron_to_delete)
        try:
            current_group_neurons = self.neuron_groups[self.active_group_index]['neurons']
            if neuron_to_delete.text in current_group_neurons:
                current_group_neurons.remove(neuron_to_delete.text)
                self.data_manager.save_neuron_groups(self.neuron_groups)
        except (ValueError, IndexError) as e:
            print(f"警告: 删除节点时未在数据源中找到文本: {e}")

    def delete_group(self, group_index):
        if not (0 <= group_index < len(self.neuron_groups)):
            return
        if len(self.neuron_groups) <= 1:
            return
        del self.neuron_groups[group_index]
        self.data_manager.save_neuron_groups(self.neuron_groups)
        if self.active_group_index == group_index or self.active_group_index >= len(self.neuron_groups):
            self.switch_group(0)
        else:
            self.switch_group(self.active_group_index)

    def _update(self, dt):
        for n in self.neurons:
            n.update(dt, self.screen.get_rect())
        for i in range(len(self.neurons)):
            for j in range(i + 1, len(self.neurons)):
                self._handle_neuron_collision(self.neurons[i], self.neurons[j])

    def _handle_neuron_collision(self, n1, n2):
        delta = n1.position - n2.position
        dist_sq = delta.length_squared()
        min_dist = n1.radius + n2.radius
        if dist_sq < min_dist**2:
            if delta.dot(n1.velocity - n2.velocity) < 0:
                n1.trigger_bounce()
                n2.trigger_bounce()
                normal = delta.normalize()
                tangent = vec(-normal.y, normal.x)
                v1n = n1.velocity.dot(normal)
                v1t = n1.velocity.dot(tangent)
                v2n = n2.velocity.dot(normal)
                v2t = n2.velocity.dot(tangent)
                m1, m2 = n1.mass, n2.mass
                new_v1n = (v1n * (m1 - m2) + 2 * m2 * v2n) / (m1 + m2) * config.NEURON_COLLISION_RESTITUTION
                new_v2n = (v2n * (m2 - m1) + 2 * m1 * v1n) / (m1 + m2) * config.NEURON_COLLISION_RESTITUTION
                n1.velocity = normal * new_v1n + tangent * v1t
                n2.velocity = normal * new_v2n + tangent * v2t
                transfer_amount = min(m1, m2) * config.MASS_TRANSFER_PERCENTAGE
                if m1 > m2 and m2 - transfer_amount > config.MIN_NEURON_MASS:
                    n1.mass += transfer_amount
                    n2.mass -= transfer_amount
                elif m2 > m1 and m1 - transfer_amount > config.MIN_NEURON_MASS:
                    n2.mass += transfer_amount
                    n1.mass -= transfer_amount
                n1.update_radius()
                n2.update_radius()
            dist = dist_sq**0.5
            overlap = (min_dist - dist)
            separation_vec = delta.normalize() * overlap * 0.5
            n1.position += separation_vec
            n2.position -= separation_vec

    def _draw(self):
        self.screen.fill(config.BG_COLOR)
        for n in self.neurons:
            n.draw(self.screen)
        if self.velocity_adjust_mode and pygame.mouse.get_pressed()[2]:
            start_pos = self.held_neuron.position
            end_pos = vec(pygame.mouse.get_pos())
            utils.draw_arrow(self.screen, config.HELD_NEURON_BORDER_COLOR, start_pos, end_pos)
        self.ui_manager.draw(self.screen, pygame.mouse.get_pos())
        pygame.display.flip()

    def _load_initial_data(self):
        self.is_loading = True
        self.neuron_groups = self.data_manager.load_neuron_groups()
        self.switch_group(0)
        self.is_loading = False
        self.paused = False

    def _create_neurons_from_group(self, group_index):
        self.neurons.clear()
        group = self.neuron_groups[group_index]
        words = group.get('neurons', [])
        for i, word in enumerate(words):
            while True:
                pos = vec(random.randint(50, config.SCREEN_WIDTH - 50), random.randint(50, config.SCREEN_HEIGHT - 50))
                new_neuron = Neuron(text=word, position=pos, color=config.NEURON_COLORS[i % len(config.NEURON_COLORS)])
                if not any((new_neuron.position - n.position).length() < new_neuron.radius + n.radius for n in self.neurons):
                    self.neurons.append(new_neuron)
                    break

    def switch_group(self, group_index):
        if 0 <= group_index < len(self.neuron_groups):
            self.active_group_index = group_index
            self._create_neurons_from_group(group_index)

    def _get_neuron_at(self, pos):
        for n in reversed(self.neurons):
            if (vec(pos) - n.position).length_squared() < n.radius**2:
                return n
        return None

    def _check_placement_validity(self, neuron):
        r = neuron.radius * neuron.scale
        if not (r <= neuron.position.x <= self.screen.get_width() - r and r <= neuron.position.y <= self.screen.get_height() - r):
            return False
        for other in self.neurons:
            if other.id != neuron.id and (neuron.position - other.position).length() < r + other.radius * other.scale:
                return False
        return True

    def _set_neuron_velocity(self, mouse_pos):
        if self.held_neuron:
            self.held_neuron.velocity = (vec(mouse_pos) - self.held_neuron.position) * config.VELOCITY_SCALING_FACTOR