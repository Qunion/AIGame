import pygame
import logging
import math
import pymunk
from config import *
from src.physics_handler import PhysicsHandler
from src.machine import Machine, MachinePart
from src.ai_builder import create_ai_machine
from ui.ui_manager import UIManager

class Game:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.running = True
        
        # --- 最终修复：将真实的screen对象传递给PhysicsHandler ---
        self.physics = PhysicsHandler(GRAVITY, self.screen)
        self.physics.add_ground_and_boundaries()
        
        self.ui_manager = UIManager(self)
        self._setup_assembly_phase()
        logging.info("游戏初始化完成，进入组装阶段。")

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            action = self.ui_manager.handle_event(event)
            if action: self._handle_ui_action(action)
            if self.game_state == GameState.ASSEMBLY: self._handle_assembly_events(event)

    def _handle_ui_action(self, action):
        if 'select_device' in action:
            self._selected_device_type = action['select_device']
            self._is_placing_steel_bar = False; self._rotation_angle = 0
        elif action == "start_combat": self.start_combat()
        elif action == "reset_assembly": self._setup_assembly_phase()

    def _handle_assembly_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self._rotation_angle = (self._rotation_angle - 45) % 360
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.ui_manager.is_in_build_area(event.pos): return
            world_pos = pymunk.pygame_util.from_pygame(event.pos, self.screen)
            if event.button == 1:
                if self._selected_device_type == "钢条": self._handle_steel_bar_placement(world_pos)
                elif self._selected_device_type: self._handle_part_placement(world_pos)
            elif event.button == 3: self.player_machine.remove_part_at_pos(world_pos)

    def _handle_steel_bar_placement(self, world_pos):
        snapped_pos, _ = self._get_snap_target(world_pos)
        final_pos = snapped_pos if snapped_pos and self.player_machine.parts else world_pos
        if not self._is_placing_steel_bar:
            self._is_placing_steel_bar = True; self._steel_bar_start_pos = final_pos
        else:
            p1 = pymunk.Vec2d(*self._steel_bar_start_pos); p2 = pymunk.Vec2d(*final_pos)
            if p1.get_distance(p2) > 10:
                part = MachinePart("钢条", owner="player", start_pos=p1, end_pos=p2)
                self.player_machine.add_part(part)
            self._is_placing_steel_bar = False

    def _handle_part_placement(self, world_pos):
        snapped_pos, _ = self._get_snap_target(world_pos)
        if snapped_pos:
            part = MachinePart(self._selected_device_type, owner="player", position=snapped_pos, angle=math.radians(self._rotation_angle))
            self.player_machine.add_part(part)
        else: logging.info("无法放置：附近没有可用的吸附点。")

    def _get_snap_target(self, world_pos):
        all_parts = self.player_machine.parts
        if not all_parts: return None, -1
        closest_point = None; closest_dist = float('inf')
        current_mouse_pos = pymunk.Vec2d(*world_pos)
        all_snap_points = self.player_machine.get_all_snap_points()
        occupied_points = {tuple(p.position) for p in all_parts if p.type_name != "钢条"}
        available_points = [p for p in all_snap_points if tuple(p) not in occupied_points] if self._selected_device_type != "钢条" else all_snap_points
        if available_points:
            for point in available_points:
                dist = current_mouse_pos.get_distance(pymunk.Vec2d(*point))
                if dist < closest_dist: closest_dist, closest_point = dist, point
        if self._selected_device_type == "钢条":
            for part in all_parts:
                if part.type_name == "钢条":
                    p, a, b = current_mouse_pos, part.start_pos, part.end_pos
                    ab, ap = b - a, p - a; proj = ap.dot(ab); ab_len_sq = ab.dot(ab)
                    if ab_len_sq == 0: segment_point = a
                    else: t = proj / ab_len_sq; segment_point = a + t * ab if 0 <= t <= 1 else (a if t < 0 else b)
                    dist = current_mouse_pos.get_distance(segment_point)
                    if dist < closest_dist: closest_dist, closest_point = dist, segment_point
        if closest_dist < SNAP_DISTANCE: return pymunk.Vec2d(*closest_point), closest_dist
        return None, -1

    def _update(self, dt):
        mouse_world_pos = pymunk.pygame_util.from_pygame(pygame.mouse.get_pos(), self.screen)
        if self.game_state == GameState.ASSEMBLY:
            self.snap_target, _ = self._get_snap_target(mouse_world_pos)
        if self.game_state == GameState.COMBAT:
            self.physics.space.step(dt)
            if self.player_machine: self.player_machine.update_combat(dt, self.ai_machine, self.physics)
            if self.ai_machine: self.ai_machine.update_combat(dt, self.player_machine, self.physics)
            self._check_win_condition()

    def _draw(self):
        self.screen.fill(COLORS["background"])
        
        # 总是让物理引擎绘制静态物体（地面、墙壁）
        self.physics.draw(self.screen)

        if self.game_state == GameState.ASSEMBLY:
            self.ui_manager.draw_grid(self.screen)
            for part in self.player_machine.parts:
                part.draw_assembly(self.screen)
            self._draw_assembly_ghosts()
        elif self.game_state == GameState.COMBAT:
            for machine in [self.player_machine, self.ai_machine]:
                if machine:
                    for p in machine.parts: p.draw_effects(self.screen)
        self.ui_manager.draw(self.screen, self)

    def _draw_assembly_ghosts(self):
        mouse_pos_screen = pygame.mouse.get_pos()
        if not self.ui_manager.is_in_build_area(mouse_pos_screen): return
        mouse_pos_world = pymunk.pygame_util.from_pygame(mouse_pos_screen, self.screen)
        current_mouse_pos_vec = pymunk.Vec2d(*mouse_pos_world)
        if self.snap_target and self._selected_device_type:
            snap_target_vec = pymunk.Vec2d(*self.snap_target)
            if current_mouse_pos_vec.get_distance(snap_target_vec) < SNAP_DISTANCE:
                pygame.draw.circle(self.screen, COLORS["snap_indicator"], pymunk.pygame_util.to_pygame(snap_target_vec, self.screen), 10, 2)
        if self._is_placing_steel_bar:
            start_pos_vec = pymunk.Vec2d(*self._steel_bar_start_pos)
            start_screen = pymunk.pygame_util.to_pygame(start_pos_vec, self.screen)
            target_pos = current_mouse_pos_vec
            if self.snap_target:
                snap_target_vec = pymunk.Vec2d(*self.snap_target)
                if current_mouse_pos_vec.get_distance(snap_target_vec) < SNAP_DISTANCE: target_pos = snap_target_vec
            end_screen = pymunk.pygame_util.to_pygame(target_pos, self.screen)
            pygame.draw.line(self.screen, COLORS["snap_indicator"], start_screen, end_screen, 2)
        elif self._selected_device_type:
            pos = self.snap_target if self._selected_device_type != "钢条" and self.snap_target else current_mouse_pos_vec
            self.ui_manager.draw_ghost_device(self.screen, self._selected_device_type, self._rotation_angle, pymunk.pygame_util.to_pygame(pos, self.screen))

    def _setup_assembly_phase(self):
        self.physics.clear_dynamic_objects()
        self.game_state = GameState.ASSEMBLY
        self.winner = None
        self.player_machine = Machine(owner="player", physics_handler=self.physics)
        self.ai_machine = None
        self._selected_device_type = None; self._rotation_angle = 0
        self._is_placing_steel_bar = False; self._steel_bar_start_pos = None
        self.snap_target = None
        logging.info("已重置并进入组装阶段。")
        
    def start_combat(self):
        if not self.player_machine or not self.player_machine.has_core():
            self.ui_manager.show_feedback("需要一个核心(魔像头)才能开始战斗！", 3)
            return
        logging.info("战斗开始！")
        self.game_state = GameState.COMBAT
        self.player_machine.finalize_for_combat(pymunk.Vec2d(400, 300))
        self.ai_machine = create_ai_machine(self.physics)
        self.ai_machine.finalize_for_combat(pymunk.Vec2d(SCREEN_WIDTH - 400, 300))

    def _check_win_condition(self):
        if self.game_state != GameState.COMBAT: return
        player_alive = self.player_machine.has_core() if self.player_machine else False
        ai_alive = self.ai_machine.has_core() if self.ai_machine else False
        if not player_alive and not ai_alive: self.winner = "draw"
        elif not ai_alive: self.winner = "player"
        elif not player_alive: self.winner = "ai"
        if self.winner:
            logging.info(f"战斗结束：{self.winner} 胜利！")
            self.game_state = GameState.END_SCREEN