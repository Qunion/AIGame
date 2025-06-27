import pygame
import pymunk
import pymunk.pygame_util
import logging
from config import *

class PhysicsHandler:
    """封装所有与Pymunk物理引擎的交互"""

    def __init__(self, gravity, screen):
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.iterations = 30
        
        # --- 最终修复：直接使用真实的screen对象初始化DrawOptions ---
        self.draw_options = pymunk.pygame_util.DrawOptions(screen)
        
        self.ground = None
        logging.info("物理引擎已初始化。")

    def add_ground_and_boundaries(self):
        """添加一个不可破坏的地面和四面墙壁"""
        screen_width = self.draw_options.surface.get_width()
        screen_height = self.draw_options.surface.get_height()
        
        # Pymunk坐标系中，(0,0)是左下角
        static_lines = [
            # 地面，离底部100像素
            pymunk.Segment(self.space.static_body, (0, 100), (screen_width, 100), 5),
            # 左墙
            pymunk.Segment(self.space.static_body, (5, 0), (5, screen_height), 5),
            # 右墙
            pymunk.Segment(self.space.static_body, (screen_width - 5, 0), (screen_width - 5, screen_height), 5),
            # 天花板
            pymunk.Segment(self.space.static_body, (0, screen_height - 5), (screen_width, screen_height - 5), 5)
        ]
        
        for line in static_lines:
            line.friction = 0.8
            line.elasticity = 0.5
            line.color = (*COLORS["ground"], 255)
        
        self.ground = static_lines[0] # 将第一条线指定为地面
        self.space.add(*static_lines)
        logging.info("地面和边界已创建。")

    def add_dynamic_part(self, part):
        device_def = part.definition; info = device_def['shape_info']; mass = part.mass
        if info['type'] == 'segment':
            a, b = part.start_pos - part.position, part.end_pos - part.position
            moment = pymunk.moment_for_segment(mass, a, b, 0); body = pymunk.Body(mass, moment)
            shape = pymunk.Segment(body, a, b, info['radius'])
        elif info['type'] == 'box':
            moment = pymunk.moment_for_box(mass, info['size']); body = pymunk.Body(mass, moment)
            shape = pymunk.Poly.create_box(body, info['size'])
        elif info['type'] == 'circle':
            moment = pymunk.moment_for_circle(mass, 0, info['radius']); body = pymunk.Body(mass, moment)
            shape = pymunk.Circle(body, info['radius'])
        else: return None, None
        body.position = part.position; body.angle = part.angle
        shape.friction = 0.7; shape.elasticity = 0.2
        shape.collision_type = COLLISION_TYPES["machine_part"]; shape.part_ref = part
        shape.color = (*device_def.get("color", (200,200,200)), 255)
        self.space.add(body, shape)
        return body, shape

    def add_stable_joint(self, body1, body2):
        pivot = pymunk.PivotJoint(body1, body2, body1.position); self.space.add(pivot)
        spring = pymunk.DampedRotarySpring(body1, body2, 0, 1e9, 1e7); self.space.add(spring)
        try:
            shape1 = list(body1.shapes)[0]; shape2 = list(body2.shapes)[0]
            logging.debug(f"稳定连接 {shape1.part_ref.type_name} 和 {shape2.part_ref.type_name}")
        except IndexError: logging.warning("尝试连接一个没有形状的物体。")

    def add_motor(self, body, rate, torque):
        for c in self.space.constraints:
            if isinstance(c, pymunk.SimpleMotor) and c.b == body: c.rate = rate; return
        motor = pymunk.SimpleMotor(self.space.static_body, body, rate); motor.max_force = torque
        self.space.add(motor)

    def cast_ray(self, start, end, max_dist, own_parts_set):
        ray_query = self.space.segment_query_first(start, end, 1, pymunk.ShapeFilter())
        if ray_query and ray_query.shape and hasattr(ray_query.shape, 'part_ref'):
            if ray_query.shape.part_ref not in own_parts_set: return ray_query.shape.part_ref, ray_query.point
        return None, None

    def remove_body_shape(self, body, shape):
        if not body: return
        for joint in list(body.constraints):
            if joint in self.space.constraints: self.space.remove(joint)
        if shape and shape in self.space.shapes: self.space.remove(shape)
        if body in self.space.bodies: self.space.remove(body)

    def clear_dynamic_objects(self):
        for constraint in list(self.space.constraints): self.space.remove(constraint)
        bodies_to_remove = [body for body in self.space.bodies if body.body_type == pymunk.Body.DYNAMIC]
        for body in bodies_to_remove:
            for shape in list(body.shapes): self.space.remove(shape)
            self.space.remove(body)
        logging.info("已清除所有动态物体。")

    def draw(self, screen):
        # self.draw_options.surface 不再需要更新，因为它在初始化时就是正确的
        try:
            self.space.debug_draw(self.draw_options)
        except TypeError as e:
            if "center argument must be a pair of numbers" in str(e): pass
            else: raise e