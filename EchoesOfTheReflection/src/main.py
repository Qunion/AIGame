# main.py
import pygame
import sys

# 导入自定义模块
from src.settings import Settings
from src.game_manager import GameManager

def run_game():
    """初始化pygame，设置，并启动主循环"""
    pygame.init() # 初始化所有 Pygame 模块

    # 加载设置
    settings = Settings()

    # 创建屏幕对象
    screen = pygame.display.set_mode((settings.DEFAULT_SCREEN_WIDTH, settings.DEFAULT_SCREEN_HEIGHT), pygame.RESIZABLE) # 支持窗口大小调整
    pygame.display.set_caption("映象回响") # 设置窗口标题

    # 创建游戏管理器
    game_manager = GameManager(screen, settings)

    # 主游戏循环
    while True:
        # 处理事件
        game_manager.handle_events()

        # 更新游戏状态
        game_manager.update()

        # 绘制游戏元素
        game_manager.draw()

        # 使最近绘制的屏幕可见
        pygame.display.flip()

def main():
    run_game()

if __name__ == '__main__':
    main()
