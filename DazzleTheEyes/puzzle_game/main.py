# main.py
# 游戏主入口，负责初始化，主循环和状态管理

import pygame
import sys
import settings
import time # 用于获取当前时间戳，例如图库排序

# 导入其他模块
from board import Board
# from input_handler import InputHandler # 暂时还未实现，后续导入
# from gallery import Gallery # 暂时还未实现，后续导入
from image_manager import ImageManager
# from piece import Piece # 通常不需要在main中直接导入Piece
# from ui_elements import Button, PopupText # 暂时还未实现，后续导入

class Game:
    def __init__(self):
        """初始化游戏"""
        pygame.init()
        # 设置屏幕大小，Pygame窗口将占满 1920x1080
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("多图动态填充交换拼图") # 设置窗口标题

        # 游戏时钟，用于控制帧率和计算delta time
        self.clock = pygame.time.Clock()
        self.delta_time = 0.0 # 存储两帧之间的时间差（秒）

        # 游戏状态管理
        self.current_state = settings.GAME_STATE_PLAYING

        # 初始化核心模块的实例
        self.image_manager = ImageManager()
        self.board = Board(self.image_manager) # 将 image_manager 实例传递给 Board

        # 初始化其他模块的实例 (这些将在后续阶段实现和实例化)
        # self.input_handler = InputHandler(self.board, self)
        # self.gallery = Gallery(self.image_manager, self)

        # 加载UI元素 (目前只加载图库入口图标作为示例，后续Button类实现后会重构)
        try:
            self.gallery_icon = pygame.image.load(settings.GALLERY_ICON_PATH).convert_alpha()
            # 计算图库入口图标的位置，放在右上角，距离边缘20像素
            self.gallery_icon_rect = self.gallery_icon.get_rect(topright=(settings.SCREEN_WIDTH - 20, 20))
        except pygame.error as e:
            print(f"警告: 无法加载图库图标 {settings.GALLERY_ICON_PATH}: {e}")
            self.gallery_icon = None # 加载失败则设为None，避免后续报错
            self.gallery_icon_rect = None


        # 提示信息管理 (例如“美图尚未点亮”)
        # self.popup_text = PopupText("", settings.WHITE, 0) # 初始时不显示


    def run(self):
        """游戏主循环"""
        running = True
        while running:
            # 获取自上一帧以来的时间，单位为秒
            # self.delta_time = self.clock.tick(60) / 1000.0 # 将毫秒转换为秒
            self.clock.tick(60) # 简单控制帧率，不精确计算dt


            # --- 事件处理 ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # 根据当前游戏状态，将事件分发给对应的处理者 (后续实现)
                # if self.current_state == settings.GAME_STATE_PLAYING:
                #     # 处理主游戏界面的事件 (主要通过 InputHandler)
                #     # 如果图库图标已加载且点击了图库图标，切换状态
                #     if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.gallery_icon_rect and self.gallery_icon_rect.collidepoint(event.pos):
                #          self.change_state(settings.GAME_STATE_GALLERY_LIST)
                #     else:
                #          self.input_handler.handle_event(event) # 其他事件交给输入处理器
                # elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
                #     # 事件交给 Gallery 类处理列表视图逻辑 (点击缩略图、滚动、点击外部关闭等)
                #     self.gallery.handle_event_list(event)
                # elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
                #     # 事件交给 Gallery 类处理大图查看逻辑 (点击左右按钮、点击大图退出)
                #     self.gallery.handle_event_view_lit(event)

                # 临时事件处理，用于测试
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    print(f"鼠标点击位置: {event.pos}")
                    # 如果图库图标存在且被点击
                    if self.gallery_icon_rect and self.gallery_icon_rect.collidepoint(event.pos):
                         print("点击了图库图标!")
                         # self.change_state(settings.GAME_STATE_GALLERY_LIST) # 等Gallery实现后再启用

            # --- 游戏状态更新 ---
            # self.update(self.delta_time) # 根据 delta_time 更新游戏逻辑 (动画、计时器等)

            # --- 绘制所有内容 ---
            self.draw()

            # 更新屏幕显示
            pygame.display.flip() # 将所有绘制的内容显示到屏幕上

        # 游戏循环结束，退出Pygame
        pygame.quit()
        sys.exit()

    def update(self, dt):
        """
        更新游戏逻辑

        Args:
            dt (float): 自上一帧以来的时间（秒）
        """
        # 根据 self.current_state 调用对应模块的 update 方法
        # 例如，如果碎片在下落，board.update(dt) 会处理下落动画
        # 如果有提示信息在显示，self.popup_text.update(dt) 会处理淡出计时

        # if self.current_state == settings.GAME_STATE_PLAYING:
            # self.board.update(dt) # 更新Board中的动画等
            # self.popup_text.update(dt) # 更新可能的提示信息

        # elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # self.gallery.update_list(dt) # 更新图库列表的滑动等

        # elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # self.gallery.update_view_lit(dt) # 更新大图查看的动画等 (如果需要)

        pass # TODO: 实现游戏状态的更新逻辑


    def draw(self):
        """绘制所有游戏元素"""
        # 清屏，使用背景色填充整个屏幕
        self.screen.fill(settings.BLACK)

        # 根据 self.current_state 绘制不同界面 (后续实现状态切换后再启用)
        # if self.current_state == settings.GAME_STATE_PLAYING:
            # 绘制拼盘中的所有碎片
        self.board.draw(self.screen) # 在所有状态下都绘制board，这样图库弹出时碎片在下面可见 (或者只在PLAYING状态绘制)
        # 绘制主游戏界面的UI元素，如图库入口图标
        if self.gallery_icon: # 只有当图库图标成功加载才绘制
            self.screen.blit(self.gallery_icon, self.gallery_icon_rect)
            # 绘制可能的提示信息
            # self.popup_text.draw(self.screen)

        # elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
        #     # 绘制图库列表界面 (通常会覆盖主界面)
        #     self.gallery.draw_list(self.screen)

        # elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
        #     # 绘制图库大图查看界面
        #     self.gallery.draw_view_lit(self.screen)

        # 临时绘制文本和图标，以便在没有碎片时也能看到窗口运行
        # font = pygame.font.Font(None, 74)
        # text = font.render("Puzzle Game Running", True, settings.WHITE)
        # text_rect = text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
        # self.screen.blit(text, text_rect)

        # 临时绘制图库图标，确保加载成功且位置正确 (已在上面包含)
        # if self.gallery_icon:
        #      self.screen.blit(self.gallery_icon, self.gallery_icon_rect)


    # 切换游戏状态的方法，供其他模块调用
    # def change_state(self, new_state):
    #     print(f"Changing state from {self.current_state} to {new_state}") # 调试信息
    #     self.current_state = new_state
    #     # 可能需要进行状态切换时的初始化/清理工作
    #     # 例如，从主游戏进入图库时，可能需要更新图库列表
    #     # if new_state == settings.GAME_STATE_GALLERY_LIST:
    #     #     self.gallery._update_picture_list()
    #     #     self.gallery.scroll_y = 0 # 打开图库时滚动位置归零

    # def show_popup_tip(self, text):
    #      """在屏幕中央显示一个短暂的提示信息"""
    #      self.popup_text.show(text, settings.TIP_TEXT_COLOR, settings.TIP_DISPLAY_DURATION)


if __name__ == "__main__":
    # 运行游戏实例
    game = Game()
    game.run()