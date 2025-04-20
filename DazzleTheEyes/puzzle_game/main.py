# main.py
# 游戏主入口，负责初始化，主循环和状态管理

import pygame
import sys
import settings
import time # 用于获取当前时间戳，例如图库排序

# 导入其他模块
from board import Board
from input_handler import InputHandler
# from gallery import Gallery # 暂时还未实现，后续导入
from image_manager import ImageManager
# from piece import Piece # 通常不需要在main中直接导入Piece
from ui_elements import PopupText # 导入 PopupText (假设在这里管理)
# from ui_elements import Button # 如果图库图标使用Button类，需要导入

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
        self.current_state = settings.GAME_STATE_PLAYING # 初始状态暂时设为PLAYING，后续会改为LOADING

        # 加载加载画面图片 (必须在显示加载画面之前加载)
        self.loading_image = None
        try:
            self.loading_image = pygame.image.load(settings.LOADING_IMAGE_PATH).convert() # 加载时不带透明度
            # 缩放加载图片以适应屏幕 (可选，如果图片尺寸不符)
            # self.loading_image = pygame.transform.scale(self.loading_image, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"警告: 无法加载加载画面图片 {settings.LOADING_IMAGE_PATH}: {e}. 将使用黑色背景作为加载画面。")
            self.loading_image = None # 加载失败则设为None

        # 显示加载画面
        self.draw_loading_screen("加载中...") # 显示初始文本

        # 初始化核心模块的实例 (耗时操作)
        self.image_manager = ImageManager(self) # 将Game实例传递给ImageManager
        self.board = Board(self.image_manager) # 将 image_manager 实例传递给 Board
        self.input_handler = InputHandler(self.board, self) # 将 Board 和 Game 实例传递给 InputHandler

        # 初始化其他模块的实例 (这些将在后续阶段实现和实例化)
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
        self.popup_text = PopupText("", settings.TIP_TEXT_COLOR, 0) # 初始时不显示

        # 加载完成后，游戏状态切换到PLAYING
        self.current_state = settings.GAME_STATE_PLAYING
        print("加载完成，进入游戏。") # 调试信息


    def run(self):
        """游戏主循环"""
        running = True
        while running:
            self.delta_time = self.clock.tick(60) / 1000.0 # 精确计算dt

            # --- 事件处理 ---
            for event in pygame.event.get():
                # 将所有事件传递给输入处理器，由它根据游戏状态分发
                self.input_handler.handle_event(event)

            # --- 游戏状态更新 ---
            self.update(self.delta_time)

            # --- 绘制所有内容 ---
            self.draw()

            # 更新屏幕显示
            pygame.display.flip()

        # Pygame退出在InputHandler中处理


    def update(self, dt):
        """
        更新游戏逻辑

        Args:
            dt (float): 自上一帧以来的时间（秒）
        """
        # 根据 self.current_state 调用对应模块的 update 方法
        if self.current_state == settings.GAME_STATE_PLAYING:
            self.board.update(dt) # 更新Board中的动画等 (目前只有下落骨架)
            self.popup_text.update(dt) # 更新可能的提示信息计时

        # elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # self.gallery.update_list(dt)

        # elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # self.gallery.update_view_lit(dt)


    def draw(self):
        """绘制所有游戏元素"""
        # 清屏
        self.screen.fill(settings.BLACK)

        # 根据 self.current_state 绘制不同界面
        if self.current_state == settings.GAME_STATE_PLAYING:
            self.board.draw(self.screen) # 绘制拼盘
            if self.gallery_icon:
                self.screen.blit(self.gallery_icon, self.gallery_icon_rect)
            self.popup_text.draw(self.screen) # 绘制提示信息

        # elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # self.gallery.draw_list(self.screen)

        # elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # self.gallery.draw_view_lit(self.screen)


    def draw_loading_screen(self, message="加载中..."):
        """
        绘制加载画面，并在屏幕上立即显示。
        在游戏初始化时调用。
        """
        self.screen.fill(settings.BLACK) # 黑色背景

        if self.loading_image:
            # 计算加载图片居中位置
            img_rect = self.loading_image.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
            self.screen.blit(self.loading_image, img_rect)

        # 绘制加载文本
        font = pygame.font.Font(None, 48)
        text_surface = font.render(message, True, settings.WHITE)
        text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 100)) # 放在图片下方
        self.screen.blit(text_surface, text_rect)

        pygame.display.flip() # 立即更新屏幕显示加载画面


    # Game 状态切换方法
    def change_state(self, new_state):
        """
        切换游戏状态

        Args:
            new_state (int): 目标游戏状态常量
        """
        print(f"Changing state from {self.current_state} to {new_state}") # 调试信息
        self.current_state = new_state
        # 可能需要进行状态切换时的初始化/清理工作
        # 例如，从主游戏进入图库时，可能需要更新图库列表
        # if new_state == settings.GAME_STATE_GALLERY_LIST:
        #     if hasattr(self, 'gallery') and self.gallery: # 确保 gallery 实例存在
        #         self.gallery._update_picture_list() # 更新图库列表内容和排序
        #         self.gallery.scroll_y = 0 # 打开图库时滚动位置归零
        #     # 停止主游戏中的活动，如取消选中/拖拽
        #     self.board.unselect_piece()
        #     self.board.stop_dragging()
        # elif new_state == settings.GAME_STATE_PLAYING:
        #      # 从图库返回主游戏时，可能需要确保游戏状态正确
        #      pass

    def show_popup_tip(self, text):
         """在屏幕中央显示一个短暂的提示信息"""
         self.popup_text.show(text) # 使用PopupText的默认颜色和时长


if __name__ == "__main__":
    game = Game()
    game.run()