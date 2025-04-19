# src/input_handler.py
import pygame

class InputHandler:
    """
    处理原始Pygame输入事件，并可能将其转换为更高级别的游戏操作。
    负责过滤或分发事件给不同的游戏状态或模块。
    """

    def __init__(self):
        """初始化输入处理器"""
        # TODO: 可以存储按键状态等
        pass

    def handle_event(self, event):
        """
        处理单个Pygame事件。
        根据事件类型返回一个表示游戏操作的自定义事件或标志。
        """
        # 处理退出事件
        if event.type == pygame.QUIT:
            return "quit"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
            # TODO: 处理其他通用按键，例如画廊导航按键
        elif event.type == pygame.MOUSEBUTTONDOWN:
             if event.button == 1: # 左键点击
                  return ("mouse_click", event.pos) # 返回事件类型和点击位置
        elif event.type == pygame.MOUSEMOTION:
             return ("mouse_move", event.pos) # 返回事件类型和鼠标位置
        # TODO: 处理拖拽相关的MOUSEBUTTONUP事件

        # TODO: 处理窗口大小调整事件
        if event.type == pygame.VIDEORESIZE:
            return ("window_resize", (event.w, event.h))


        # 返回None或 False 表示未处理或不相关的事件
        return None

    # TODO: 可以添加方法用于检查特定按键是否被按下，获取鼠标位置等
    # def get_mouse_position(self):
    #     return pygame.mouse.get_pos()

    # def is_key_pressed(self, key_code):
    #     return pygame.key.get_pressed()[key_code]