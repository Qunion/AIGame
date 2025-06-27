import pygame
import logging
from game import Game
from config import SCREEN_WIDTH, SCREEN_HEIGHT, CAPTION
from src.utils import setup_logging

def main():
    """游戏主入口函数"""
    # 设置日志记录
    setup_logging()
    logging.info("游戏启动...")

    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(CAPTION)
    clock = pygame.time.Clock()

    # 创建游戏实例并运行
    try:
        game = Game(screen, clock)
        game.run()
    except Exception as e:
        logging.critical("发生未捕获的严重错误: %s", e, exc_info=True)
        # exc_info=True 会将详细的错误堆栈信息记录到日志中

    # 退出游戏
    logging.info("游戏关闭。")
    pygame.quit()

if __name__ == '__main__':
    main()