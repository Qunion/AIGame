import pygame
import pymunk
import math
import logging
from config import *

class MachinePart:
    def __init__(self, type_name, owner, **kwargs):
        self.type_name = type_name; self.owner = owner
        self.definition = DEVICE_DEFINITIONS[type_name]; self.color = self.definition['color']
        self.is_destroyed = False; self.body = None; self.shape = None; self.combat_cooldown = 0; self.laser_target = None
        if self.type_name == "钢条":
            self.start_pos = pymunk.Vec2d(*kwargs['start_pos']); self.end_pos = pymunk.Vec2d(*kwargs['end_pos'])
            length = self.start_pos.get_distance(self.end_pos)
            self.position = (self.start_pos + self.end_pos) / 2; self.angle = (self.end_pos - self.start_pos).angle
            self.hp = self.definition['hp_per_length'] * length; self.mass = self.definition['mass_per_length'] * length
        else:
            self.position = pymunk.Vec2d(*kwargs['position']); self.angle = kwargs['angle']
            self.hp = self.definition['hp']; self.mass = self.definition['mass']

    def draw_assembly(self, screen):
        if self.type_name == "钢条":
            p1 = pymunk.pygame_util.to_pygame(self.start_pos, screen); p2 = pymunk.pygame_util.to_pygame(self.end_pos, screen)
            pygame.draw.line(screen, self.color, p1, p2, self.definition['shape_info']['radius'] * 2)
        else:
            info = self.definition['shape_info']; pos_screen = pymunk.pygame_util.to_pygame(self.position, screen)
            if info['type'] == 'box':
                w, h = info['size']; surface = pygame.Surface((w, h), pygame.SRCALPHA); surface.fill(self.color)
                rotated_surface = pygame.transform.rotate(surface, -math.degrees(self.angle))
                screen.blit(rotated_surface, rotated_surface.get_rect(center=pos_screen))
            elif info['type'] == 'circle': pygame.draw.circle(screen, self.color, pos_screen, info['radius'])

    def get_snap_points(self): return [self.start_pos, self.end_pos] if self.type_name == "钢条" else [self.position]

    def is_clicked(self, world_pos):
        if self.type_name == "钢条": return world_pos.get_dist_to_segment(self.start_pos, self.end_pos) < self.definition['shape_info']['radius'] + 5
        info = self.definition['shape_info']; radius = max(info.get('size', (0,0))) / 2 if info['type'] == 'box' else info.get('radius', 0)
        return self.position.get_distance(world_pos) < radius

    def take_damage(self, amount):
        if self.is_destroyed: return
        self.hp -= amount
        if self.hp <= 0: self.hp = 0; self.is_destroyed = True; logging.info(f"'{self.owner}' 的零件 '{self.type_name}' 被摧毁。")

    def update_combat(self, dt, target_machine, physics):
        if self.is_destroyed: return
        self.combat_cooldown = max(0, self.combat_cooldown - dt); self.laser_target = None
        stats = self.definition.get("combat_stats")
        if not stats or stats['type'] != 'controller' or self.combat_cooldown > 0: return None
        self.combat_cooldown = stats['scan_interval']; target_part = target_machine.get_core_part()
        if target_part and not target_part.is_destroyed and self.body.position.get_distance(target_part.body.position) < stats['scan_range']: return target_part
        return None

    def fire_at(self, target_part, physics, own_parts_set):
        if self.is_destroyed or self.combat_cooldown > 0: return
        stats = self.definition.get("combat_stats")
        if not (stats and stats['type'] == 'weapon'): return
        start_pos = self.body.position + (15, 0).rotated(self.body.angle)
        direction = (target_part.body.position - start_pos).normalized()
        end_pos = start_pos + direction * stats['range']
        hit_part, _ = physics.cast_ray(start_pos, end_pos, stats['range'], own_parts_set)
        self.laser_target = hit_part.body.position if hit_part else end_pos
        if hit_part: hit_part.take_damage(stats['damage'])
        self.combat_cooldown = stats['cooldown']

    def draw_effects(self, screen):
        if self.laser_target:
            start_pos = self.body.position + (15, 0).rotated(self.body.angle)
            start_screen = pymunk.pygame_util.to_pygame(start_pos, screen); end_screen = pymunk.pygame_util.to_pygame(self.laser_target, screen)
            pygame.draw.line(screen, COLORS["laser"], start_screen, end_screen, 2)

class Machine:
    def __init__(self, owner, physics_handler):
        self.owner = owner; self.physics = physics_handler; self.parts = []; self.target_part = None

    def add_part(self, part_obj): self.parts.append(part_obj); logging.info(f"{self.owner} 添加零件 '{part_obj.type_name}'")
    
    def get_all_snap_points(self):
        raw_points = [p for part in self.parts for p in part.get_snap_points()]
        unique_points = []; seen_coords = set()
        for point in raw_points:
            coords = (int(point.x), int(point.y))
            if coords not in seen_coords: unique_points.append(point); seen_coords.add(coords)
        return unique_points

    def remove_part_at_pos(self, world_pos):
        for part in reversed(self.parts):
            if part.is_clicked(world_pos): self.parts.remove(part); logging.info(f"玩家移除了零件 '{part.type_name}'。"); return

    def finalize_for_combat(self, base_position):
        if not self.parts: return
        total_mass = sum(p.mass for p in self.parts); total_mass = 1 if total_mass == 0 else total_mass
        blueprint_centroid = sum((p.position * p.mass for p in self.parts), pymunk.Vec2d(0,0)) / total_mass
        
        for part in self.parts:
            relative_pos = part.position - blueprint_centroid
            part.position = base_position + relative_pos
            if part.type_name == "钢条":
                part.start_pos = base_position + (part.start_pos - blueprint_centroid)
                part.end_pos = base_position + (part.end_pos - blueprint_centroid)
            part.body, part.shape = self.physics.add_dynamic_part(part)
        
        welded_pairs = set()
        for p1 in self.parts:
            for p2 in self.parts:
                pair = tuple(sorted((id(p1), id(p2))))
                if p1 == p2 or not p1.body or not p2.body or pair in welded_pairs: continue
                
                for snap_point1 in p1.get_snap_points():
                    for snap_point2 in p2.get_snap_points():
                        if snap_point1.get_distance(snap_point2) < 1:
                            # 调用新的稳定连接函数
                            self.physics.add_stable_joint(p1.body, p2.body)
                            welded_pairs.add(pair)
                            break
                    else: continue
                    break
        logging.info(f"'{self.owner}' 的机器已完成战斗准备。")

    def update_combat(self, dt, target_machine, physics):
        for part in self.parts[:]:
            if part.is_destroyed:
                if part.body: self.physics.remove_body_shape(part.body, part.shape)
                self.parts.remove(part)
        controller = self.get_core_part()
        if not controller: return
        new_target = controller.update_combat(dt, target_machine, physics)
        if new_target: self.target_part = new_target
        if not self.target_part or self.target_part.is_destroyed: self.target_part = None; return
        for part in self.parts:
            stats = part.definition.get('combat_stats')
            if stats and not part.is_destroyed:
                if stats['type'] == 'mobility':
                    direction = -1 if self.owner == 'ai' else 1
                    rate = math.copysign(stats['rate'], direction)
                    self.physics.add_motor(part.body, rate, stats['torque'])
                elif stats['type'] == 'weapon': part.fire_at(self.target_part, physics, {p.shape for p in self.parts if p.shape})

    def get_core_part(self):
        for part in self.parts:
            if part.definition.get('is_core') and not part.is_destroyed: return part
        return None
    def has_core(self): return self.get_core_part() is not None