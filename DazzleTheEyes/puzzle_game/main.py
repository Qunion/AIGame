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
        self.font_loading = pygame.font.Font(None, 60) # 加载界面字体
        self.font_tip = pygame.font.Font(None, settings.TIP_FONT_SIZE) # 提示信息字体
        self.font_thumbnail = pygame.font.Font(None, 24) # 图库缩略图字体 (可选)

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
            # Board需要Game实例以便在图片完成时通知Gallery更新等
            self.board = Board(self.image_manager) # 将 image_manager 实例传递给 Board
            # InputHandler需要Board和Game实例
            self.input_handler = InputHandler(self.board, self)
            # Gallery需要ImageManager和Game实例
            self.gallery = Gallery(self.image_manager, self)

        except Exception as e:
            print(f"致命错误: Board 或 InputHandler 或 Gallery 初始化失败: {e}")
            pygame.quit()
            sys.exit()


        # 加载UI元素 (图库入口图标使用Button类管理)
        # self.gallery_icon_button = Button(settings.GALLERY_ICON_PATH, (settings.SCREEN_WIDTH - 20, 20), anchor='topright', callback=self.open_gallery)
        # 因为 Button 类需要 self.open_gallery 方法，Button 的创建放在 open_gallery 实现后，或者放在这里但传入 lambda 函数

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
            print("警告: 没有配置加载画面图片路径，加载画面将只有文本。")
            return None

        valid_image_paths = [path for path in settings.LOADING_IMAGE_PATHS if os.path.exists(path)]
        if not valid_image_paths:
            print("警告: 配置的加载画面图片文件都不存在，加载画面将只有文本。")
            return None

        selected_path = random.choice(valid_image_paths)
        try:
            # 尝试加载图片并保持透明度，以防loading图需要透明
            loading_img = pygame.image.load(selected_path).convert_alpha()

            # 缩放图片以适应屏幕，保持比例，居中
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
            print(f"加载画面 {selected_path} 加载成功，缩放到 {new_w}x{new_h}") # 调试信息
            return scaled_img

        except pygame.error as e:
            print(f"警告: 无法加载加载画面图片 {selected_path}: {e}")
            return None # 加载失败
    # ==========================================


    # === 图库相关方法 (由 InputHandler 或其他地方调用) ===
    def open_gallery(self):
        """打开图库界面"""
        # Game类调用 change_state 方法来切换状态
        if self.current_state != settings.GAME_STATE_PLAYING:
             print("警告: 当前不在PLAYING状态，无法打开图库。")
             return
        self.change_state(settings.GAME_STATE_GALLERY_LIST) # 切换到图库列表状态

    def close_gallery(self):
        """关闭图库界面"""
        # Game类调用 change_state 方法来切换状态
        if self.current_state not in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
             print("警告: 当前不在图库状态，无法关闭图库。")
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
            for event in pygame.event.get():
                 # 检查退出事件，优先级最高
                 if event.type == pygame.QUIT:
                     running = False # 设置 running 为 False 退出主循环

                 # 将其他事件传递给 InputHandler
                 self.input_handler.handle_event(event)

            # --- 游戏状态更新 ---
            self.update(self.delta_time)

            # --- 绘制所有内容 ---
            self.draw()

            # 更新屏幕显示
            pygame.display.flip()

        # 游戏循环结束，退出Pygame
        pygame.quit()
        sys.exit()


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

            if initial_load_done and elapsed_time >= settings.MIN_LOADING_DURATION:
                 # 初始加载完成并且满足最小加载时间，切换到 PLAYING
                 print("初始加载完成并满足最小时间，切换到游戏主状态。") # 调试信息
                 self.change_state(settings.GAME_STATE_PLAYING)
            else:
                 # 驱动后台加载，并更新加载画面文本（如果需要显示进度条或其他动态元素，可以在这里更新它们的内部状态）
                 # ImageManager 的 load_next_batch_background 会自己检查是否已全部加载完
                 self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
                 # draw 方法会在下一帧绘制更新的加载画面
                 pass # LOADING 状态主要靠 draw 方法来更新视觉，逻辑更新是检查状态和触发后台加载


        elif self.current_state == settings.GAME_STATE_PLAYING:
            # 更新 Board (处理下落动画和完成流程状态机)
            self.board.update(dt)
            # 更新可能的提示信息计时
            self.popup_text.update(dt)

            # 在PLAYING状态下，检查是否需要继续后台加载
            self._check_and_continue_background_loading()


        elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # 更新图库列表状态 (例如处理滚动条动画，如果实现的话)
            # self.gallery.update_list(dt) # Gallery类内部 update 方法会根据子状态调用
            if hasattr(self.gallery, 'update'): # 检查gallery是否有update方法
                 self.gallery.update(dt)


        elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # 更新图库大图查看状态 (例如处理图片切换动画，如果实现的话)
            # self.gallery.update_view_lit(dt) # Gallery类内部 update 方法会根据子状态调用
            if hasattr(self.gallery, 'update'): # 检查gallery是否有update方法
                 self.gallery.update(dt)


    def draw(self):
        """绘制所有游戏元素"""
        # 清屏，使用背景色填充整个屏幕
        self.screen.fill(settings.BLACK)

        # 根据 self.current_state 绘制不同界面
        if self.current_state == settings.GAME_STATE_LOADING:
            # 绘制加载画面
            # 获取当前加载进度信息
            progress_text = self.image_manager.get_loading_progress()
            display_message = f"加载中... {progress_text}"
            self.draw_loading_screen(display_message)

        elif self.current_state == settings.GAME_STATE_PLAYING:
            # 绘制拼盘
            if self.board: # 确保 Board 实例存在
                 self.board.draw(self.screen)
            # 绘制主游戏界面的UI元素，如图库入口图标 (现在用Button类管理)
            # if self.gallery_icon_button:
            #     self.gallery_icon_button.draw(self.screen)
            # TODO: 暂时直接绘制图库图标，等 Button 整合进事件处理再切换
            try:
                gallery_icon_img = pygame.image.load(settings.GALLERY_ICON_PATH).convert_alpha()
                gallery_icon_rect = gallery_icon_img.get_rect(topright=(settings.SCREEN_WIDTH - 20, 20))
                self.screen.blit(gallery_icon_img, gallery_icon_rect)
            except pygame.error:
                pass # 加载失败不绘制

            # 绘制可能的提示信息，提示信息应该绘制在所有之上
            if self.popup_text and self.popup_text.is_active:
                 self.popup_text.draw(self.screen)


        elif self.current_state in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
            # 绘制图库界面 (Gallery 类内部会根据其子状态绘制列表或大图)
            if self.gallery: # 确保 Gallery 实例存在
                 self.gallery.draw(self.screen)

        # TODO: 在图库界面显示时，是否需要绘制底下的 Board？
        # 如果图库背景是半透明的，绘制 Board 可以让它作为背景模糊可见。
        # 目前 Gallery.draw 内部绘制了半透明覆盖层，所以可以在图库状态下也绘制 Board。
        # 但是为了效率，只有当图库背景是半透明时才这样做。目前的 GALLERY_BG_COLOR 和 OVERLAY_COLOR 都是带透明度的。
        # 所以可以在图库状态下也绘制 board，但要在 Gallery.draw 之前绘制。
        # 将 Board 的绘制放到 if/elif 结构之外，或者根据状态决定是否绘制。
        # 简单起见，只在 PLAYING 状态绘制 Board。图库的半透明背景层会覆盖它。


    # Game 状态切换方法
    def change_state(self, new_state):
        """
        切换游戏状态

        Args:
            new_state (int): 目标游戏状态常量 (settings.GAME_STATE_...)
        """
        if self.current_state == new_state:
             return # 状态没有改变

        print(f"Changing state from {self.current_state} to {new_state}") # 调试信息
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
                # TODO: 暂停 Board 的 update (下落动画等)，可以在 Board 的 update 方法中检查 Game 状态

        elif old_state == settings.GAME_STATE_GALLERY_LIST and new_state == settings.GAME_STATE_PLAYING:
            # 从图库列表返回主游戏
            print("从图库列表返回主游戏状态。")
            if self.gallery: # 确保 gallery 实例存在
                self.gallery.close_gallery() # 通知Gallery关闭 (会重置一些内部状态)
            # TODO: 恢复 Board 的 update (如果之前暂停了)


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
         if self.image_manager.is_loading_finished():
              return # 所有图片已加载完成

         # 检查是否到了执行下一批后台加载任务的时间
         current_time = time.time()
         if current_time - self._last_background_load_time >= settings.BACKGROUND_LOAD_DELAY:
             # 执行一次后台加载任务批次
             # ImageManager 的 load_next_batch_background 会自己处理加载逻辑
             loaded_count = self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
             # print(f"后台加载完成 {loaded_count} 张图片/批次。") # 调试信息
             self._last_background_load_time = current_time # 更新时间


if __name__ == "__main__":
    game = Game()
    game.run()