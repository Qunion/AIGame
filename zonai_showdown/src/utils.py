import logging

def setup_logging():
    """
    配置日志记录器，将日志输出到文件和控制台。
    """
    logging.basicConfig(
        level=logging.DEBUG,  # 记录所有级别的日志
        format='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.FileHandler("log.txt", mode='w'),  # 写入到log.txt文件，每次运行覆盖
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )

def world_to_screen(pos, screen):
    """pymunk坐标转换到pygame坐标 (y轴翻转)"""
    return int(pos[0]), int(screen.get_height() - pos[1])

def screen_to_world(pos, screen):
    """pygame坐标转换到pymunk坐标 (y轴翻转)"""
    return int(pos[0]), int(screen.get_height() - pos[1])