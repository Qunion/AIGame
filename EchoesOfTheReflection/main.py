# main.py
import pygame
import sys

# 导入自定义模块
from settings import Settings
from game_manager import GameManager
# from ui_manager import UIManager # 由GameManager内部创建和管理

def run_game():
    """初始化pygame，设置，并启动主循环"""
    pygame.init() # 初始化所有 Pygame 模块
    pygame.mixer.init() # 确保混音器初始化

    # 加载设置
    settings = Settings()

    # 创建屏幕对象
    screen = pygame.display.set_mode((settings.DEFAULT_SCREEN_WIDTH, settings.DEFAULT_SCREEN_HEIGHT), pygame.RESIZABLE) # 支持窗口大小调整
    pygame.display.set_caption("映象回响") # 设置窗口标题

    # 创建游戏管理器
    # GameManager 内部会创建 ImageRenderer, NarrativeManager, UIManager, AudioManager 等
    game_manager = GameManager(screen, settings)

    # 主游戏循环
    running = True
    clock = pygame.time.Clock() # 用于控制帧率

    while running:
        # 处理事件 - 将事件列表传递给 GameManager
        events = pygame.event.get()
        game_manager.handle_events(events) # <-- 修复: 传递事件列表

        # 检查 GameManager 是否标记了退出
        if game_manager.should_quit:
             running = False
             continue # 跳过本轮后续更新和绘制

        # 更新游戏状态
        game_manager.update()

        # 绘制游戏元素
        game_manager.draw() # <-- 修复: GameManager.draw 不需要屏幕参数，它内部知道screen

        # 使最近绘制的屏幕可见
        pygame.display.flip()

        # 控制帧率
        clock.tick(60) # 设定帧率为60 FPS

    pygame.quit() # 主循环结束后退出 Pygame
    sys.exit()

def main():
    run_game()

if __name__ == '__main__':
    main()