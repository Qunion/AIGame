# main.py
# 游戏主入口，负责初始化，主循环和状态管理，并添加存档读档功能

import pygame
import sys
import settings
import time # 用于计时
import random # 用于随机选择加载图片
import os # 用于检查文件存在性
import json # 用于 JSON 序列化和反序列化

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
        try:
            self.font_loading = pygame.font.SysFont(settings.FONT_NAME, 60) # 加载界面字体
            self.font_tip = pygame.font.SysFont(settings.FONT_NAME, settings.TIP_FONT_SIZE) # 提示信息字体
            self.font_thumbnail = pygame.font.SysFont(settings.FONT_NAME, 24) # 图库缩略图字体 (可选)
            self.font_debug = pygame.font.SysFont(settings.FONT_NAME, settings.DEBUG_FONT_SIZE) # Debug 文字字体
            # 检查 SysFont 是否成功返回了字体对象
            if self.font_loading is None or self.font_tip is None or self.font_thumbnail is None or self.font_debug is None:
                 # 如果 SysFont 返回 None，抛出异常进入 except 块
                 raise ValueError("SysFont returned None for one or more fonts")
            print(f"系统字体 '{settings.FONT_NAME}' 加载成功或找到相似字体。") # Debug success

        except Exception as e: # 捕获加载系统字体时可能发生的任何异常
            print(f"警告: 加载系统字体 '{settings.FONT_NAME}' 时发生错误: {e}。使用 Pygame 默认字体。")
            # Fallback to Pygame's default font
            self.font_loading = pygame.font.Font(None, 60)
            self.font_tip = pygame.font.Font(None, settings.TIP_FONT_SIZE)
            self.font_thumbnail = pygame.font.Font(None, 24)
            self.font_debug = pygame.font.Font(None, settings.DEBUG_FONT_SIZE)
            print("使用 Pygame 默认字体。") # Debug fallback


        # --- Debug 相关属性 ---
        self.display_piece_info = False # 是否显示碎片 debug 信息


        # --- 加载界面相关 ---
        self.loading_start_time = time.time() # 记录进入加载阶段的时间

        # 加载加载画面图片 (必须在显示加载画面之前加载)
        self.loading_image = self._load_random_loading_image()

        # === 在这里调用 draw_loading_screen 来显示初始加载画面 ===
        # 这个调用确保在ImageManager初始化（耗时操作）之前，玩家能看到加载界面
        self.draw_loading_screen("初始化...") # 显示初始文本
        pygame.display.flip() # 立即更新屏幕，显示加载画面
        # =========================================================

        # --- 尝试加载存档数据 ---
        print("尝试加载存档数据...") # Debug
        loaded_game_data = self.load_game_data() # 尝试加载存档，成功返回数据字典，失败返回None

        # --- 初始化核心模块的实例 ---
        # ImageManager 总是需要初始化，它负责扫描文件和加载初始批次图片
        self.image_manager = ImageManager(self) # Pass Game instance to ImageManager

        # 如果成功加载了存档数据，则使用存档数据加载 ImageManager 的状态
        if loaded_game_data and 'image_manager_state' in loaded_game_data:
            print("加载 ImageManager 状态...") # Debug
            self.image_manager.load_state(loaded_game_data['image_manager_state'])


        # 初始化 Board，并传递存档的网格数据（如果存在）
        try:
            saved_grid_data = loaded_game_data.get('board_grid') if loaded_game_data else None
            # Board 的 __init__ 方法会根据 saved_grid_data 是否为 None 来决定是加载存档还是初始填充
            self.board = Board(self.image_manager, saved_grid_data) # Pass image_manager and saved grid data
        except Exception as e:
            print(f"致命错误: Board 初始化失败: {e}")
            self._display_fatal_error(f"Board 初始化失败: {e}")
            time.sleep(5) # 显示错误信息5秒
            pygame.quit()
            sys.exit()


        # 初始化 InputHandler 和 Gallery
        try:
             self.input_handler = InputHandler(self.board, self) # Pass Board and Game instances
             self.gallery = Gallery(self.image_manager, self) # Pass ImageManager and Game instances
        except Exception as e:
             print(f"致命错误: InputHandler 或 Gallery 初始化失败: {e}")
             self._display_fatal_error(f"InputHandler/Gallery 初始化失败: {e}")
             time.sleep(5)
             pygame.quit()
             sys.exit()


        # 加载UI元素 (图库入口图标使用Button类管理)
        # Create gallery icon button, callback is self.open_gallery
        try:
            self.gallery_icon_button = Button(settings.GALLERY_ICON_PATH, (settings.SCREEN_WIDTH - 20, 20), anchor='topright', callback=self.open_gallery)
        except Exception as e:
            print(f"警告: 无法创建图库图标按钮: {e}. 图库入口可能无法使用。")
            self.gallery_icon_button = None # Button creation failed


        # 提示信息管理 (例如“美图尚未点亮”)
        self.popup_text = PopupText(self) # Pass Game instance to PopupText


        # 自动存档相关的变量
        self.last_autosave_time = time.time() # 记录上次自动存档的时间

        # 后台加载定时器 <-- **新增注释**
        self._last_background_load_time = time.time() # <-- **新增：初始化后台加载定时器**


        # __init__ completes. Game state is LOADING.
        # Transition to PLAYING happens in the update loop, based on loading progress and min duration.


    # === 加载画面相关方法 ===
    def draw_loading_screen(self, message="加载中..."):
        """
        绘制加载画面。
        在游戏初始化或 LOADING 状态的 draw 方法中调用。
        """
        self.screen.fill(settings.BLACK) # Black background

        # Draw loading background image
        if self.loading_image:
            # Calculate center position for the loading image
            img_rect = self.loading_image.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
            self.screen.blit(self.loading_image, img_rect)

        # 绘制加载文本
        # Get loading text surface using the loading font
        text_surface = self.font_loading.render(message, True, settings.LOADING_TEXT_COLOR)
        # Calculate text position, centered below the image or screen center
        text_y_offset = (self.loading_image.get_height()//2 + 30 if self.loading_image else 50) # Gap below image or offset from screen center
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
            # Try loading image, keep alpha for transparency
            loading_img = pygame.image.load(selected_path).convert_alpha()

            # Scale image to fit screen, maintain aspect ratio, centered
            img_w, img_h = loading_img.get_size()
            screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

            # Calculate scale factor to fit screen while maintaining aspect ratio
            scale_factor = min(screen_w / img_w, screen_h / img_h)

            # Ensure scaled dimensions are valid
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
            return None # Loading failed
    # ==========================================

    def _display_fatal_error(self, message):
        """在屏幕上显示致命错误信息"""
        self.screen.fill(settings.BLACK)
        font = pygame.font.Font(None, 50)
        lines = message.split('\n') # Supports multi-line error messages
        y_offset = settings.SCREEN_HEIGHT // 2 - (len(lines) * 60) // 2 # Center vertically based on number of lines
        for line in lines:
            text_surface = font.render(line, True, settings.WHITE)
            text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(text_surface, text_rect)
            y_offset += 60 # Line spacing
        pygame.display.flip()


    # === 存档/读档方法 ===
    def save_game_data(self):
        """
        保存当前游戏状态到文件。
        保存内容包括 Board 布局和 ImageManager 状态。
        """
        if self.board is None or self.image_manager is None:
             print("警告: Board 或 ImageManager 未初始化，无法保存游戏状态。")
             return # Cannot save if core components aren't ready

        print("保存游戏状态...") # Debug

        # 获取 Board 和 ImageManager 的状态数据
        board_state = self.board.get_state()
        image_manager_state = self.image_manager.get_state()

        # 构建总的存档数据字典
        game_state_data = {
            'board_grid': board_state,
            'image_manager_state': image_manager_state,
            'save_time': time.time() # Add current time as save timestamp
        }

        # 确定存档文件路径
        save_file_path = os.path.join(settings.BASE_DIR, settings.SAVE_FILE_NAME)

        # 将数据写入 JSON 文件
        try:
            with open(save_file_path, 'w', encoding='utf-8') as f:
                # Use json.dump to write the dictionary to the file
                # indent=4 for pretty printing (optional)
                json.dump(game_state_data, f, indent=4)
            print(f"游戏状态已保存到 {save_file_path}") # Debug success
        except Exception as e:
            print(f"错误: 保存游戏状态失败到 {save_file_path}: {e}") # Debug error


    def load_game_data(self):
        """
        尝试从文件加载游戏状态。

        Returns:
            dict or None: 加载到的游戏状态字典，如果文件不存在或加载失败则返回 None。
        """
        save_file_path = os.path.join(settings.BASE_DIR, settings.SAVE_FILE_NAME)

        # 检查存档文件是否存在
        if not os.path.exists(save_file_path):
            print("没有找到存档文件，开始新游戏。") # Debug
            return None # File does not exist, return None

        # 尝试从 JSON 文件加载数据
        try:
            with open(save_file_path, 'r', encoding='utf-8') as f:
                # Use json.load to read the dictionary from the file
                game_state_data = json.load(f)
                # print(f"完整输出加载的数据，看是否加载成功:game_state_data: {game_state_data}")#结果是成功的
            print(f"游戏状态已从 {save_file_path} 加载成功。") # Debug success

            # TODO: 可以添加对加载到的数据结构的验证 (可选)
            if not isinstance(game_state_data, dict) or 'board_grid' not in game_state_data or 'image_manager_state' not in game_state_data:
                 print("警告: 存档文件格式不正确。开始新游戏。") # Debug
                 return None # Data structure is invalid

            return game_state_data # Return loaded data

        except json.JSONDecodeError as e:
            print(f"错误: 存档文件 {save_file_path} 格式错误，无法解析 JSON: {e}. 删除损坏的存档。") # Debug error
            # Optional: Delete the corrupted save file
            # os.remove(save_file_path)
            return None
        except Exception as e:
            print(f"错误: 加载存档状态失败从 {save_file_path}: {e}") # Debug error
            return None


    # === 游戏退出方法 (由 InputHandler 调用) ===
    def quit_game(self):
        """
        在退出游戏前执行保存操作并关闭Pygame。
        由 InputHandler 在接收到 QUIT 事件时调用。
        """
        print("接收到退出信号，正在保存并退出...") # Debug
        self.save_game_data() # 保存游戏状态
        print("游戏已保存，退出中...") # Debug
        pygame.quit()
        sys.exit()


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
         if self.popup_text: # Ensure popup_text is initialized
             self.popup_text.show(text) # Use PopupText's default color and duration


    # === 核心游戏循环方法 ===
    def run(self):
        """游戏主循环"""
        running = True
        while running:
            self.delta_time = self.clock.tick(60) / 1000.0 # 精确计算dt

            # --- 事件处理 ---
            # 将所有事件传递给输入处理器，由它根据游戏状态分发
            # InputHandler 会处理 QUIT 事件并调用 game.quit_game()
            for event in pygame.event.get():
                 # Pass event to InputHandler
                 if self.input_handler: # Ensure InputHandler is initialized
                     self.input_handler.handle_event(event)
                 else:
                     # If InputHandler not ready (e.g. fatal error), handle QUIT directly
                     if event.type == pygame.QUIT:
                         running = False # Exit loop


            # --- 游戏状态更新 ---
            self.update(self.delta_time)

            # --- 绘制所有内容 ---
            self.draw()

            # 更新屏幕显示
            pygame.display.flip()

        # Pygame exit is handled by game.quit_game() or direct QUIT handling on fatal error


    def update(self, dt):
        """
        更新游戏逻辑。

        Args:
            dt (float): 自上一帧以来的时间（秒）。
        """
        # 根据 self.current_state 调用对应模块的 update 方法或执行状态逻辑
        if self.current_state == settings.GAME_STATE_LOADING:
            # In LOADING state update, check loading progress and time
            elapsed_time = time.time() - self.loading_start_time
            # Check if initial load batch is done AND minimum duration is met
            initial_load_done = self.image_manager.is_initial_load_finished() if self.image_manager else False
            # total_load_done = self.image_manager.is_loading_finished() if self.image_manager else False # Check if all images loaded

            # In loading phase, also drive background loading to show progress
            if self.image_manager: # Ensure ImageManager is initialized
                 # Control background loading frequency
                 if time.time() - self.last_autosave_time >= settings.BACKGROUND_LOAD_DELAY / 10.0: # Use last_autosave_time as a general timer
                      self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
                      self.last_autosave_time = time.time() # Update timer (using autosave timer for background load timing)


            # Only transition to PLAYING if initial load is done AND min duration is met
            if initial_load_done and elapsed_time >= settings.MIN_LOADING_DURATION:
                 print("Initial load complete and min duration met, transitioning to PLAYING.") # Debug
                 self.change_state(settings.GAME_STATE_PLAYING)


        elif self.current_state == settings.GAME_STATE_PLAYING:
            # Update Board (handle falling animation and completion state machine)
            if self.board: # Ensure Board is initialized
                 self.board.update(dt)
            # Update possible popup text timer
            if self.popup_text: # Ensure popup_text is initialized
                 self.popup_text.update(dt)

            # Check and continue background loading
            if self.image_manager: # Ensure ImageManager is initialized
                 self._check_and_continue_background_loading()

            # --- 自动存档 ---
            current_time = time.time()
            if current_time - self.last_autosave_time >= settings.AUTOSAVE_INTERVAL:
                self.save_game_data() # Perform autosave
                self.last_autosave_time = current_time # Reset timer


        elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # Update Gallery list state (e.g., scrollbar animation if implemented)
            # Update possible popup text timer (hint might be shown in gallery)
            if self.popup_text:
                 self.popup_text.update(dt)
            # Note: Gallery itself doesn't have a continuous update method in the provided code,
            # its state changes based on user input handled in handle_event_list.
            # If Gallery update logic is added later, call it here.
            # if hasattr(self.gallery, 'update'): self.gallery.update(dt)
            pass


        elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # Update Gallery big view state (e.g., image transition animation if implemented)
            # Update possible popup text timer (hint might be shown in gallery)
            if self.popup_text:
                 self.popup_text.update(dt)
            # Note: Gallery itself doesn't have a continuous update method in the provided code
            # if hasattr(self.gallery, 'update'): self.gallery.update(dt)
            pass


    def draw(self):
        """绘制所有游戏元素"""
        # Clear screen with background color
        self.screen.fill(settings.BLACK)

        # Draw content based on current state
        if self.current_state == settings.GAME_STATE_LOADING:
            # Draw loading screen
            if self.image_manager: # Ensure ImageManager is initialized
                 progress_text = self.image_manager.get_loading_progress()
                 display_message = f"加载中... {progress_text}"
            else:
                 display_message = "初始化..." # Before ImageManager is ready
            self.draw_loading_screen(display_message)

        elif self.current_state == settings.GAME_STATE_PLAYING:
            # Draw Board
            if self.board: # Ensure Board is initialized
                 self.board.draw(self.screen)

            # Draw primary UI elements, like gallery icon button
            if hasattr(self, 'gallery_icon_button') and self.gallery_icon_button: # Ensure button is initialized
                 self.gallery_icon_button.draw(self.screen)

            # Draw possible popup text (should be on top)
            if self.popup_text and self.popup_text.is_active: # Ensure popup_text is initialized and active
                 self.popup_text.draw(self.screen)


        elif self.current_state in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
            # Draw Gallery interface (Gallery class handles drawing list or big image)
            if self.gallery: # Ensure Gallery is initialized
                 self.gallery.draw(self.screen)

            # Draw popup text on top of Gallery
            if self.popup_text and self.popup_text.is_active: # Ensure popup_text is initialized and active
                 self.popup_text.draw(self.screen)


    # Game state transition method
    def change_state(self, new_state):
        """
        Changes the game state.

        Args:
            new_state (int): Target game state constant (settings.GAME_STATE_...).
        """
        if self.current_state == new_state:
             return # State not changing

        print(f"Changing state from {self.current_state} to {new_state}") # Debug
        old_state = self.current_state # Record old state
        self.current_state = new_state

        # Perform initialization/cleanup based on state change
        if old_state == settings.GAME_STATE_LOADING and new_state == settings.GAME_STATE_PLAYING:
             # Transition from LOADING to PLAYING
             print("Entering PLAYING state.")
             # Board and Gallery instances are ready at this point
             # Background loading continues in PLAYING state's update
             pass # Optional transition effects

        elif new_state == settings.GAME_STATE_GALLERY_LIST:
            # Entering Gallery list
            print("Entering GALLERY_LIST state.")
            if self.gallery: # Ensure gallery instance exists
                self.gallery.open_gallery() # Notify Gallery to prepare list view (updates list content)
            # Stop interactions in main game view (unselect, stop drag)
            if self.board: # Ensure board instance exists
                self.board.unselect_piece()
                self.board.stop_dragging()
            # Note: Board's update method checks its own internal state, doesn't need explicit pausing here.

        elif old_state == settings.GAME_STATE_GALLERY_LIST and new_state == settings.GAME_STATE_PLAYING:
            # Transition from Gallery list back to main game
            print("Returning from GALLERY_LIST to PLAYING.")
            if self.gallery: # Ensure gallery instance exists
                self.gallery.close_gallery() # Notify Gallery to close (resets internal state)

        elif new_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
             # Entering Gallery big view (from list state)
             print("Entering GALLERY_VIEW_LIT state.")
             # Transition triggered by Gallery.start_viewing_lit_image, Gallery knows which image to view

        elif old_state == settings.GAME_STATE_GALLERY_VIEW_LIT and new_state == settings.GAME_STATE_GALLERY_LIST:
             # Transition from big view back to Gallery list
             print("Returning from GALLERY_VIEW_LIT to GALLERY_LIST state.")
             # Transition triggered by Gallery.stop_viewing_lit_image

        # TODO: Add cleanup/initialization logic for other state transitions


# main.py

# ... 其他代码 ...

    # main.py

# ... 其他代码 ...

    def _check_and_continue_background_loading(self):
         """
         检查并继续未处理图片的后台加载。
         这个方法在 GAME_STATE_PLAYING update 中被调用。
         """
         # Only attempt if ImageManager is initialized and there are unprocessed images
         if self.image_manager is None or self.image_manager.is_loading_finished():
              # print("后台加载：所有图片已加载完成或 ImageManager 未初始化。") # Debug, avoid spamming
              return # All images loaded or ImageManager not ready

         # Check if it's time to execute the next batch of background loading tasks
         current_time = time.time()
         # Use a separate timer for background loading frequency
         # We use _last_background_load_time initialized in __init__ and updated here.

         if current_time - self._last_background_load_time >= settings.BACKGROUND_LOAD_DELAY:
             # Execute a batch of background loading tasks via ImageManager
             # ImageManager.load_next_batch_background will process images from its queues
             processed_count_this_batch = self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
             
             if processed_count_this_batch > 0:
                 # If at least one image was processed in this batch, update the timer
                 self._last_background_load_time = current_time
                 # print(f"后台加载完成 {processed_count_this_batch} 张图片/批次。") # Debug
             # else: print("后台加载检查，但队列中没有可处理的图片或处理失败。") # Debug # Update timer
                    # print(f"后台加载完成 {loaded_count} 张图片/批次。") # Debug
                 # else: print("后台加载检查，但没有可处理的图片或处理失败。") # Debug


    # ... (后续方法保持不变) ...

if __name__ == "__main__":
    game = Game()
    game.run()