# main.py
# 游戏主入口，负责初始化，主循环和状态管理

import pygame
import sys
import settings
import time # 用于获取当前时间戳，例如图库排序
import random # 用于随机选择加载图片
# import threading # 用于后台加载 (可选，Pygame主线程最好不要做耗时操作)
# import queue # 用于线程间通信 (可选)


# 导入其他模块
from board import Board
from input_handler import InputHandler
# from gallery import Gallery # 暂时还未实现，后续导入
from image_manager import ImageManager
# from piece import Piece # 通常不需要在main中直接导入Piece
from ui_elements import PopupText # 导入 PopupText (假设在这里管理)
# from ui_elements import Button # 如果图库图标使用Button类，需要导入

# TODO: 后台加载相关的队列和事件 (如果使用线程)
# finished_loading_queue = queue.Queue() # 用于接收后台加载完成的信号
# new_pieces_queue = queue.Queue() # 用于接收后台加载好的碎片 (如果后台处理到碎片生成)
# loading_finished_event = threading.Event() # 用于标记加载是否完全完成


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
        # 初始状态改为 LOADING，直到图片加载完成
        self.current_state = settings.GAME_STATE_LOADING

        # 加载加载画面图片 (必须在显示加载画面之前加载)
        self.loading_image = self._load_random_loading_image()

        # === 在这里调用 draw_loading_screen 来显示初始加载画面 ===
        # 这个调用确保在ImageManager初始化（耗时操作）之前，玩家能看到加载界面
        self.draw_loading_screen("初始化...") # 显示初始文本
        # =========================================================

        # 初始化核心模块的实例 ( ImageManager 的初始化将触发首次图片加载 )
        # ImageManager 的初始化现在只加载 INITIAL_LOAD_IMAGE_COUNT 数量的图片
        self.image_manager = ImageManager(self) # 将Game实例传递给ImageManager

        # 加载Board等其他需要初始图片数据的模块
        # Board 的初始化需要 ImageManager 已经加载了初始拼盘所需的碎片
        # 如果 ImageManager 初始化失败（没有足够的图片），Board 初始化可能会有问题
        try:
            self.board = Board(self.image_manager) # 将 image_manager 实例传递给 Board
            self.input_handler = InputHandler(self.board, self) # 将 Board 和 Game 实例传递给 InputHandler
        except Exception as e:
            print(f"致命错误: Board 或 InputHandler 初始化失败: {e}")
            pygame.quit()
            sys.exit()


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

        # 后台加载相关的变量
        self._last_background_load_time = time.time() # 上次执行后台加载任务的时间
        # 后台加载完成后，会调用 change_state 切换到 PLAYING

        # __init__ 完成后，游戏状态仍然是 LOADING。
        # 状态切换到 PLAYING 将在第一次 update 循环中进行，以确保加载画面至少显示一帧。


    # === draw_loading_screen 方法定义 ===
    def draw_loading_screen(self, message="加载中..."):
        """
        绘制加载画面，并在屏幕上立即显示。
        在游戏初始化或 LOADING 状态的 draw 方法中调用。
        """
        self.screen.fill(settings.BLACK) # 黑色背景

        if self.loading_image:
            # 计算加载图片居中位置
            img_rect = self.loading_image.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
            self.screen.blit(self.loading_image, img_rect)

        # 绘制加载文本
        # 字体初始化可以在这里，或者更早一次性完成
        # 每次调用render会创建新的Surface，如果频繁调用可能影响性能，但对于加载画面影响不大
        font = pygame.font.Font(None, 48)
        # text_message = f"加载中... ({self.image_manager.get_loading_progress()})" # 假设ImageManager提供进度信息
        text_message = message # 使用传入的消息
        text_surface = font.render(text_message, True, settings.WHITE)
        # 计算文本位置，放在图片下方或屏幕中央下方
        text_y_offset = (self.loading_image.get_height()//2 + 30 if self.loading_image else 50) # 文本与图片底部的间距，或屏幕中心的偏移
        text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + text_y_offset ))
        self.screen.blit(text_surface, text_rect)

        # 在初始化时调用此方法后，需要手动调用 pygame.display.flip() 来更新屏幕
        # 在 draw 循环中调用时，run 方法末尾的 flip() 会负责更新


    # === _load_random_loading_image 方法定义 ===
    def _load_random_loading_image(self):
        """从列表中随机选择一张加载画面图片并加载，自适应屏幕大小"""
        if not settings.LOADING_IMAGE_PATHS:
            print("警告: 没有配置加载画面图片路径。")
            return None

        selected_path = random.choice(settings.LOADING_IMAGE_PATHS)
        try:
            # 尝试加载图片并保持透明度，以防loading图需要透明
            loading_img = pygame.image.load(selected_path).convert_alpha()

            # 缩放图片以适应屏幕，保持比例，居中
            img_w, img_h = loading_img.get_size()
            screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

            # 计算缩放因子，以适应屏幕尺寸，保持比例
            scale_factor = min(screen_w / img_w, screen_h / img_h)
            new_w = int(img_w * scale_factor)
            new_h = int(img_h * scale_factor)

            # 确保缩放后的尺寸有效
            if new_w <= 0 or new_h <= 0:
                print(f"警告: 加载画面图片 {selected_path} 缩放后尺寸无效 ({new_w}x{new_h})。")
                return None

            scaled_img = pygame.transform.scale(loading_img, (new_w, new_h))
            print(f"加载画面 {selected_path} 加载成功，缩放到 {new_w}x{new_h}") # 调试信息
            return scaled_img

        except pygame.error as e:
            print(f"警告: 无法加载加载画面图片 {selected_path}: {e}")
            return None # 加载失败
    # ==========================================


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

            # 在PLAYING状态下，检查是否需要继续后台加载
            self._check_and_continue_background_loading()


        # elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # self.gallery.update_list(dt)

        # elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # self.gallery.update_view_lit(dt)

        elif self.current_state == settings.GAME_STATE_LOADING:
            # 在 LOADING 状态的 update 中，进行状态切换
            # 这确保加载画面在 __init__ 中绘制并显示至少一帧后，游戏再开始
            print("加载状态 update, 切换到 PLAYING...") # 调试信息
            self.change_state(settings.GAME_STATE_PLAYING)

            # 注意：如果ImageManager初始化非常快，LOADING状态可能只持续一帧。
            # 如果需要 LOADING 状态持续更长时间或显示加载进度，需要在这里
            # 根据 ImageManager 的加载进度来决定是否切换状态，并调用 ImageManager 的后台加载方法。
            # 例如：
            # if not self.image_manager.is_loading_finished():
            #      # 在LOADING状态也驱动后台加载，并更新加载画面文本
            #      self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
            #      self.draw_loading_screen(f"加载中... ({self.image_manager.get_loading_progress()})")
            # else:
            #      self.change_state(settings.GAME_STATE_PLAYING)


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

        elif self.current_state == settings.GAME_STATE_LOADING:
            # 在加载状态下，绘制加载画面
            # 直接调用 draw_loading_screen 绘制当前加载状态的画面
            self.draw_loading_screen("加载中...") # 在每一帧绘制加载画面


    # Game 状态切换方法
    def change_state(self, new_state):
        """
        切换游戏状态

        Args:
            new_state (int): 目标游戏状态常量
        """
        print(f"Changing state from {self.current_state} to {new_state}") # 调试信息
        old_state = self.current_state # 记录旧状态
        self.current_state = new_state

        # 根据状态切换执行初始化/清理工作
        if old_state == settings.GAME_STATE_LOADING and new_state == settings.GAME_STATE_PLAYING:
             print("完成初始化加载，进入游戏主状态。后台加载将在游戏运行时继续。")
             # 从LOADING切换到PLAYING时，可以在这里加一些过渡动画或音效
             # 例如，短暂的黑屏淡入淡出等，但主线程不适合长时间阻塞

        elif new_state == settings.GAME_STATE_GALLERY_LIST:
            # 进入图库列表
            print("进入图库列表状态。") # 调试信息
            if hasattr(self, 'gallery') and self.gallery: # 确保 gallery 实例存在
                # TODO: gallery._update_picture_list() # 更新图库列表内容和排序
                self.gallery.scroll_y = 0 # 打开图库时滚动位置归零
            # 停止主游戏中的活动，如取消选中/拖拽
            self.board.unselect_piece()
            self.board.stop_dragging()

        # elif old_state == settings.GAME_STATE_GALLERY_LIST and new_state == settings.GAME_STATE_PLAYING:
        #     # 从图库列表返回主游戏
        #     print("从图库列表返回主游戏状态。") # 调试信息
        #     # TODO: gallery cleanup (e.g., hide gallery UI elements)

        # elif old_state == settings.GAME_STATE_GALLERY_VIEW_LIT and new_state == settings.GAME_STATE_GALLERY_LIST:
        #     # 从大图查看返回图库列表
        #     print("从大图查看返回图库列表状态。") # 调试信息
        #     # TODO: hide big image view UI elements


    def show_popup_tip(self, text):
         """在屏幕中央显示一个短暂的提示信息"""
         self.popup_text.show(text) # 使用PopupText的默认颜色和时长

    # TODO: 实现后台加载逻辑的驱动方法 (如果不用线程)
    def _check_and_continue_background_loading(self):
         """
         检查是否需要继续后台加载未处理的图片。
         这个方法只在 GAME_STATE_PLAYING 状态的 update 中被调用。
         """
         # 只有当 ImageManager 知道还有未加载的图片时才尝试加载
         if self.image_manager.is_loading_finished():
              return # 所有图片已加载完成

         # 检查是否到了执行下一批后台加载任务的时间
         current_time = time.time()
         if current_time - self._last_background_load_time >= settings.BACKGROUND_LOAD_DELAY:
             # 执行一次后台加载任务批次
             # print("正在执行后台加载任务...") # 调试信息，频繁打印可能影响性能
             loaded_count = self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
             # print(f"后台加载完成 {loaded_count} 张图片/批次。") # 调试信息
             self._last_background_load_time = current_time # 更新时间


if __name__ == "__main__":
    game = Game()
    game.run()