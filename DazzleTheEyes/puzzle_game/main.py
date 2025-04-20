# main.py
# 游戏主入口，负责初始化，主循环和状态管理

import pygame
import sys
import settings
import time # 用于计时
import random # 用于随机选择加载图片
import os # 用于检查文件存在性


# 导入其他模块
from board import Board
from input_handler import InputHandler
from gallery import Gallery
from image_manager import ImageManager
# from piece import Piece # 通常不需要在main中直接导入Piece
from ui_elements import PopupText, Button # 导入 UI 元素类


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
        # 初始状态设置为加载中
        self.current_state = settings.GAME_STATE_LOADING

        # 字体初始化 (统一管理)
        # 使用 settings.FONT_NAME 尝试加载系统字体
        # SysFont 如果找不到精确匹配的字体，会尝试查找相似字体或使用系统默认字体，不会抛出 FileNotFoundError
        try:
            self.font_loading = pygame.font.SysFont(settings.FONT_NAME, 60) # 加载界面字体
            self.font_tip = pygame.font.SysFont(settings.FONT_NAME, settings.TIP_FONT_SIZE) # 提示信息字体
            self.font_thumbnail = pygame.font.SysFont(settings.FONT_NAME, 24) # 图库缩略图字体 (可选)
            # 检查 SysFont 是否成功返回了字体对象 (尽管 SysFont 很少返回 None, 但这是一个好的实践)
            if self.font_loading is None or self.font_tip is None or self.font_thumbnail is None:
                 raise ValueError("SysFont returned None for one or more fonts") # 如果返回 None，抛出异常进入 except 块
            print(f"系统字体 '{settings.FONT_NAME}' 加载成功或找到相似字体。") # Debug success

        except Exception as e: # 捕获加载系统字体时可能发生的任何异常 (尽管 SysFont 很少见)
            print(f"警告: 加载系统字体 '{settings.FONT_NAME}' 时发生错误: {e}。使用 Pygame 默认字体。")
            # Fallback to Pygame's default font if SysFont had an unexpected issue or returned None
            self.font_loading = pygame.font.Font(None, 60)
            self.font_tip = pygame.font.Font(None, settings.TIP_FONT_SIZE)
            self.font_thumbnail = pygame.font.Font(None, 24)
            print("使用 Pygame 默认字体。") # Debug fallback

        # --- 加载界面相关 ---
        self.loading_start_time = time.time() # 记录进入加载阶段的时间

        # 加载加载画面图片 (必须在显示加载画面之前加载)
        self.loading_image = self._load_random_loading_image()

        # === 在这里调用 draw_loading_screen 来显示初始加载画面 ===
        # 这个调用确保在ImageManager初始化（耗时操作）之前，玩家能看到加载界面
        self.draw_loading_screen("初始化...") # 显示初始文本
        pygame.display.flip() # 立即更新屏幕，显示加载画面
        # =========================================================

        # 初始化核心模块的实例 ( ImageManager 的初始化将触发首次图片加载 )
        # ImageManager 的初始化现在只加载 INITIAL_LOAD_IMAGE_COUNT 数量的图片
        self.image_manager = ImageManager(self) # 将Game实例传递给ImageManager

        # 加载Board等其他需要初始图片数据的模块
        # Board 的初始化需要 ImageManager 已经加载了初始拼盘所需的碎片
        # 如果 ImageManager 初始化失败（没有足够的图片），Board 初始化可能会有问题
        try:
            # Board需要Game实例以便在图片完成时通知Gallery更新等 - 实际上通过ImageManager间接访问
            self.board = Board(self.image_manager) # 将 image_manager 实例传递给 Board
            # InputHandler需要Board和Game实例
            self.input_handler = InputHandler(self.board, self)
            # Gallery需要ImageManager和Game实例
            self.gallery = Gallery(self.image_manager, self)

        except Exception as e:
            print(f"致命错误: 模块初始化失败: {e}")
            # 在遇到致命错误时，显示错误信息并等待几秒后退出
            self._display_fatal_error(f"初始化失败: {e}")
            time.sleep(5) # 显示错误信息5秒
            pygame.quit()
            sys.exit()


        # 加载UI元素 (图库入口图标使用Button类管理)
        # 创建图库入口按钮，并指定点击回调函数为 self.open_gallery
        self.gallery_icon_button = Button(settings.GALLERY_ICON_PATH, (settings.SCREEN_WIDTH - 20, 20), anchor='topright', callback=self.open_gallery)


        # 提示信息管理 (例如“美图尚未点亮”)
        self.popup_text = PopupText(self) # 将Game实例传递给PopupText


        # 后台加载相关的变量
        self._last_background_load_time = time.time() # 上次执行后台加载任务的时间


        # __init__ 完成后，游戏状态仍然是 LOADING。
        # 状态切换到 PLAYING 将在 update 循环中，根据加载进度和最小时间来决定。


    # === 加载画面相关方法 ===
    def draw_loading_screen(self, message="加载中..."):
        """
        绘制加载画面。
        在游戏初始化或 LOADING 状态的 draw 方法中调用。
        """
        self.screen.fill(settings.BLACK) # 黑色背景

        # 绘制加载背景图片
        if self.loading_image:
            # 计算加载图片居中位置
            img_rect = self.loading_image.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
            self.screen.blit(self.loading_image, img_rect)

        # 绘制加载文本
        text_surface = self.font_loading.render(message, True, settings.LOADING_TEXT_COLOR)
        # 计算文本位置，放在图片下方或屏幕中央下方
        text_y_offset = (self.loading_image.get_height()//2 + 30 if self.loading_image else 50) # 文本与图片底部的间距，或屏幕中心的偏移
        text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + text_y_offset ))
        self.screen.blit(text_surface, text_rect)


    def _load_random_loading_image(self):
        """从列表中随机选择一张加载画面图片并加载，自适应屏幕大小"""
        if not settings.LOADING_IMAGE_PATHS:
            # print("警告: 没有配置加载画面图片路径，加载画面将只有文本。")
            return None

        valid_image_paths = [path for path in settings.LOADING_IMAGE_PATHS if os.path.exists(path)]
        if not valid_image_paths:
            # print("警告: 配置的加载画面图片文件都不存在，加载画面将只有文本。")
            return None

        selected_path = random.choice(valid_image_paths)
        try:
            # 尝试加载图片并保持透明度，以防loading图需要透明
            loading_img = pygame.image.load(selected_path).convert_alpha()

            # 缩放图片以适应屏幕，保持比例
            img_w, img_h = loading_img.get_size()
            screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

            # 计算缩放因子，以适应屏幕尺寸，保持比例
            scale_factor = min(screen_w / img_w, screen_h / img_h)

            # 确保缩放后的尺寸有效
            new_w = int(img_w * scale_factor)
            new_h = int(img_h * scale_factor)

            if new_w <= 0 or new_h <= 0:
                print(f"警告: 加载画面图片 {selected_path} 缩放后尺寸无效 ({new_w}x{new_h})。")
                return None

            scaled_img = pygame.transform.scale(loading_img, (new_w, new_h))
            # print(f"加载画面 {selected_path} 加载成功，缩放到 {new_w}x{new_h}") # Debug
            return scaled_img

        except pygame.error as e:
            print(f"警告: 无法加载加载画面图片 {selected_path}: {e}")
            return None # 加载失败
    # ==========================================

    def _display_fatal_error(self, message):
        """在屏幕上显示致命错误信息"""
        self.screen.fill(settings.BLACK)
        font = pygame.font.Font(None, 50)
        lines = message.split('\n') # 支持多行错误信息
        y_offset = settings.SCREEN_HEIGHT // 2 - len(lines) * 30
        for line in lines:
            text_surface = font.render(line, True, settings.WHITE)
            text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(text_surface, text_rect)
            y_offset += 60 # 行间距
        pygame.display.flip()


    # === 图库相关方法 (由 InputHandler 或其他地方调用) ===
    def open_gallery(self):
        """打开图库界面"""
        # Game类调用 change_state 方法来切换状态
        if self.current_state != settings.GAME_STATE_PLAYING:
             # print("警告: 当前不在PLAYING状态，无法打开图库。") # Debug
             return
        self.change_state(settings.GAME_STATE_GALLERY_LIST) # 切换到图库列表状态

    def close_gallery(self):
        """关闭图库界面"""
        # Game类调用 change_state 方法来切换状态
        if self.current_state not in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
             # print("警告: 当前不在图库状态，无法关闭图库。") # Debug
             return
        self.change_state(settings.GAME_STATE_PLAYING) # 切换回PLAYING状态


    # === 提示信息方法 ===
    def show_popup_tip(self, text):
         """在屏幕中央显示一个短暂的提示信息"""
         self.popup_text.show(text) # 使用PopupText的默认颜色和时长


    # === 核心游戏循环方法 ===
    def run(self):
        """游戏主循环"""
        running = True
        while running:
            self.delta_time = self.clock.tick(60) / 1000.0 # 精确计算dt

            # --- 事件处理 ---
            # 将所有事件传递给输入处理器，由它根据游戏状态分发
            # InputHandler 会处理 QUIT 事件并退出
            for event in pygame.event.get():
                 self.input_handler.handle_event(event)

            # --- 游戏状态更新 ---
            self.update(self.delta_time)

            # --- 绘制所有内容 ---
            self.draw()

            # 更新屏幕显示
            pygame.display.flip()

        # Pygame退出在InputHandler或致命错误处理中完成


    def update(self, dt):
        """
        更新游戏逻辑。

        Args:
            dt (float): 自上一帧以来的时间（秒）。
        """
        # 根据 self.current_state 调用对应模块的 update 方法或执行状态逻辑
        if self.current_state == settings.GAME_STATE_LOADING:
            # 在 LOADING 状态的 update 中，检查加载进度和时间
            elapsed_time = time.time() - self.loading_start_time
            initial_load_done = self.image_manager.is_initial_load_finished()
            total_load_done = self.image_manager.is_loading_finished() # 检查是否所有图片都已加载完

            # 在加载阶段也驱动后台加载，以便在加载界面显示加载进度
            # ImageManager 的 load_next_batch_background 会自己检查是否已全部加载完
            # 可以稍微控制后台加载的频率，但不要完全阻塞
            if time.time() - self._last_background_load_time >= settings.BACKGROUND_LOAD_DELAY / 10.0: # 加载期间可以更快加载
                 self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
                 self._last_background_load_time = time.time()


            # 只有当初始加载完成并且满足最小加载时间时，才切换到 PLAYING
            if initial_load_done and elapsed_time >= settings.MIN_LOADING_DURATION:
                 print("初始加载完成并满足最小时间，切换到游戏主状态。") # Debug
                 self.change_state(settings.GAME_STATE_PLAYING)


        elif self.current_state == settings.GAME_STATE_PLAYING:
            # 更新 Board (处理下落动画和完成流程状态机)
            if self.board:
                 self.board.update(dt)
            # 更新可能的提示信息计时
            if self.popup_text:
                 self.popup_text.update(dt)

            # 在PLAYING状态下，检查是否需要继续后台加载
            self._check_and_continue_background_loading()


        elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # 更新图库列表状态 (例如处理滚动条动画，如果实现的话)
            if hasattr(self.gallery, 'update'): # 检查gallery是否有update方法
                 self.gallery.update(dt) # Gallery类内部 update 方法会根据子状态调用
            # 更新可能的提示信息计时 (提示信息可能在图库界面显示)
            if self.popup_text:
                 self.popup_text.update(dt)


        elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # 更新图库大图查看状态 (例如处理图片切换动画，如果实现的话)
            if hasattr(self.gallery, 'update'): # 检查gallery是否有update方法
                 self.gallery.update(dt) # Gallery类内部 update method

            # 更新可能的提示信息计时 (提示信息可能在大图查看界面显示)
            if self.popup_text:
                 self.popup_text.update(dt)


    def draw(self):
        """绘制所有游戏元素"""
        # 清屏，使用背景色填充整个屏幕
        self.screen.fill(settings.BLACK)

        # 根据 self.current_state 绘制不同界面
        if self.current_state == settings.GAME_STATE_LOADING:
            # 绘制加载画面
            # 获取当前加载进度信息
            if self.image_manager: # 确保ImageManager已初始化
                 progress_text = self.image_manager.get_loading_progress()
                 display_message = f"加载中... {progress_text}"
            else:
                 display_message = "初始化..." # ImageManager尚未初始化时
            self.draw_loading_screen(display_message)

        elif self.current_state == settings.GAME_STATE_PLAYING:
            # 绘制拼盘
            if self.board: # 确保 Board 实例存在
                 self.board.draw(self.screen)

            # 绘制主游戏界面的UI元素，如图库入口按钮
            if hasattr(self, 'gallery_icon_button') and self.gallery_icon_button:
                 self.gallery_icon_button.draw(self.screen)

            # 绘制可能的提示信息，提示信息应该绘制在所有之上
            if self.popup_text and self.popup_text.is_active:
                 self.popup_text.draw(self.screen)


        elif self.current_state in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
            # 绘制图库界面 (Gallery 类内部会根据其子状态绘制列表或大图)
            if self.gallery: # 确保 Gallery 实例存在
                 self.gallery.draw(self.screen)

            # 在图库界面也绘制提示信息，确保提示信息在最顶层
            if self.popup_text and self.popup_text.is_active:
                 self.popup_text.draw(self.screen)


    # Game 状态切换方法
    def change_state(self, new_state):
        """
        切换游戏状态

        Args:
            new_state (int): 目标游戏状态常量 (settings.GAME_STATE_...)
        """
        if self.current_state == new_state:
             return # 状态没有改变

        print(f"Changing state from {self.current_state} to {new_state}") # Debug
        old_state = self.current_state # 记录旧状态
        self.current_state = new_state

        # 根据状态切换执行初始化/清理工作
        if old_state == settings.GAME_STATE_LOADING and new_state == settings.GAME_STATE_PLAYING:
             # 从LOADING切换到PLAYING
             print("进入游戏主状态PLAYING。")
             # 此时 Board 和 Gallery 实例都已创建
             # 后台加载将在 PLAYING 状态的 update 中继续
             pass # 可以加一些过渡效果

        elif new_state == settings.GAME_STATE_GALLERY_LIST:
            # 进入图库列表
            print("进入图库列表状态。")
            if self.gallery: # 确保 gallery 实例存在
                self.gallery.open_gallery() # 通知Gallery准备打开列表 (会更新列表内容)
            # 停止主游戏中的活动，如取消选中/拖拽
            if self.board:
                self.board.unselect_piece()
                self.board.stop_dragging()
                # TODO: 暂停 Board 的 update (下落动画等)？目前 Board update 会检查自身状态，非PLAYING时不做主逻辑
                # 所以不需要在这里显式暂停 Board update

        elif old_state == settings.GAME_STATE_GALLERY_LIST and new_state == settings.GAME_STATE_PLAYING:
            # 从图库列表返回主游戏
            print("从图库列表返回主游戏状态。")
            if self.gallery: # 确保 gallery 实例存在
                self.gallery.close_gallery() # 通知Gallery关闭 (会重置一些内部状态)
            # TODO: 恢复 Board 的 update (如果之前暂停了) - 目前不需要

        elif new_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
             # 进入图库大图查看状态 (从列表状态进入)
             print("进入图库大图查看状态。")
             # 由 Gallery.start_viewing_lit_image 触发此状态切换，Gallery 内部已记录要查看的图片
             pass # 可以加一些过渡效果


        elif old_state == settings.GAME_STATE_GALLERY_VIEW_LIT and new_state == settings.GAME_STATE_GALLERY_LIST:
             # 从大图查看返回图库列表
             print("从大图查看返回图库列表状态。")
             # 由 Gallery.stop_viewing_lit_image 触发此状态切换


        # TODO: 添加其他状态切换的清理/初始化逻辑


    def _check_and_continue_background_loading(self):
         """
         检查是否需要继续后台加载未处理的图片。
         这个方法只在 GAME_STATE_PLAYING 状态的 update 中被调用。
         """
         # 只有当 ImageManager 知道还有未加载的图片时才尝试加载
         if self.image_manager and self.image_manager.is_loading_finished():
              return # 所有图片已加载完成或 ImageManager 未初始化

         # 检查是否到了执行下一批后台加载任务的时间
         current_time = time.time()
         if current_time - self._last_background_load_time >= settings.BACKGROUND_LOAD_DELAY:
             # 执行一次后台加载任务批次
             # ImageManager 的 load_next_batch_background 会自己处理加载逻辑
             if self.image_manager: # 确保 ImageManager 已初始化
                 loaded_count = self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
                 # print(f"后台加载完成 {loaded_count} 张图片/批次。") # Debug
                 self._last_background_load_time = current_time # 更新时间


if __name__ == "__main__":
    game = Game()
    game.run()