import logging
import pymunk
from .machine import Machine, MachinePart

def create_ai_machine(physics_handler):
    logging.info("正在为AI生成机器...")
    ai_machine = Machine(owner="ai", physics_handler=physics_handler)
    
    # AI现在也使用钢条作为基础
    bar1_start = pymunk.Vec2d(0, 0)
    bar1_end = pymunk.Vec2d(100, 0)
    bar1 = MachinePart("钢条", owner="ai", start_pos=bar1_start, end_pos=bar1_end)
    ai_machine.add_part(bar1)

    # 在钢条的端点上放置零件
    core = MachinePart("魔像头", owner="ai", position=bar1_start, angle=0)
    ai_machine.add_part(core)

    weapon = MachinePart("光线头", owner="ai", position=bar1_start, angle=3.14159) # 朝后
    ai_machine.add_part(weapon)

    wheel1 = MachinePart("小轮胎", owner="ai", position=bar1_start, angle=0)
    ai_machine.add_part(wheel1)

    wheel2 = MachinePart("小轮胎", owner="ai", position=bar1_end, angle=0)
    ai_machine.add_part(wheel2)

    logging.info(f"AI机器创建完毕，包含 {len(ai_machine.parts)} 个零件。")
    return ai_machine