# main.py
# 游戏主入口，负责初始化，主循环和状态管理，并添加存档读档功能

import pygame
import sys
from piece import Piece
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
# from piece import Piece # Typically no need to import Piece directly in main
from ui_elements import PopupText, Button # Import UI element classes
# === 新增：导入 CompletionAnimation 类 ===
from completion_animation import CompletionAnimation


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

        # --- 完成动画实例 ---
        self.active_animation = None # Holds the current completion animation instance


        # 字体初始化 (统一管理)
        # 使用 settings.FONT_NAME 尝试加载系统字体
        try:
            # Attempt to load the preferred system font
            self.font_loading = pygame.font.SysFont(settings.FONT_NAME, 60) # 加载界面字体
            self.font_tip = pygame.font.SysFont(settings.FONT_NAME, settings.TIP_FONT_SIZE) # 提示信息字体
            self.font_thumbnail = pygame.font.SysFont(settings.FONT_NAME, 24) # 图库缩略图字体 (可选)
            self.font_debug = pygame.font.SysFont(settings.FONT_NAME, settings.DEBUG_FONT_SIZE) # Debug 文字字体

            # Check if SysFont successfully returned font objects (SysFont returns None if font not found)
            if self.font_loading is None or self.font_tip is None or self.font_thumbnail is None or self.font_debug is None:
                 # If any font failed to load via SysFont, raise an error to use fallback
                 raise ValueError("SysFont returned None for one or more fonts")
            # print(f"系统字体 '{settings.FONT_NAME}' 加载成功或找到相似字体。") # Debug success

        except Exception as e: # Catch any exception during SysFont loading
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
        # This call ensures the player sees the loading screen before ImageManager initialization (potentially time-consuming).
        self.draw_loading_screen("初始化...") # Display initial text
        pygame.display.flip() # Update the screen immediately to show the loading screen
        # =========================================================

        # --- 尝试加载存档数据 ---
        print("尝试加载存档数据...") # Debug
        self.loaded_game_data = self.load_game_data() # Attempt to load save, returns data dict or None

        # --- 初始化核心模块的实例 ---
        # ImageManager is always initialized first.
        try:
             self.image_manager = ImageManager(self) # Pass Game instance to ImageManager
        except Exception as e:
             print(f"致命错误: ImageManager 初始化失败: {e}")
             self._display_fatal_error(f"ImageManager 初始化失败:\n{e}")
             time.sleep(5) # Display error message for 5 seconds
             pygame.quit()
             sys.exit()


        # If save data loaded successfully, load ImageManager state
        if self.loaded_game_data: # Check if loaded_game_data is not None
            if 'image_manager_state' in self.loaded_game_data:
                print("加载 ImageManager 状态...") # Debug
                try:
                     self.image_manager.load_state(self.loaded_game_data['image_manager_state'])
                     # ImageManager.load_state populates high-priority queue based on loaded state
                except Exception as e:
                     print(f"致命错误: ImageManager 状态加载失败: {e}. 存档可能已损坏。开始新游戏。")
                     # Re-initialize ImageManager to start fresh if state loading fails
                     self.image_manager = ImageManager(self)
                     # Continue without loaded board state, will trigger new game init in Board
                     self.loaded_game_data = None # Discard corrupted loaded data
            else:
                 print("警告: 存档数据缺少 'image_manager_state' 字段。ImageManager 状态将为默认初始化状态。开始新游戏。") # Debug
                 self.loaded_game_data = None # Treat as no valid loaded data


        # Initialize Board, passing loaded game data (if available)
        # Board's __init__ decides whether to load from save or start new game based on saved_game_data
        try:
            # === Pass the entire loaded_game_data to Board ===
            self.board = Board(self.image_manager, self.loaded_game_data) # Pass image_manager and the entire loaded_game_data
        except Exception as e:
            print(f"致命错误: Board 初始化失败: {e}")
            self._display_fatal_error(f"Board 初始化失败:\n{e}")
            time.sleep(5) # Display error message for 5 seconds
            pygame.quit()
            sys.exit()


        # Initialize InputHandler and Gallery
        try:
             self.input_handler = InputHandler(self.board, self) # Pass Board and Game instances
             self.gallery = Gallery(self.image_manager, self) # Pass ImageManager and Game instances
        except Exception as e:
             print(f"致命错误: InputHandler 或 Gallery 初始化失败: {e}")
             self._display_fatal_error(f"InputHandler/Gallery 初始化失败:\n{e}")
             time.sleep(5)
             pygame.quit()
             sys.exit()


        # Load UI elements (Gallery icon button)
        # Create gallery icon button, callback is self.open_gallery
        try:
            # Position calculated based on screen width and padding
            gallery_button_x = settings.SCREEN_WIDTH - 20 # 20 pixels from right edge
            gallery_button_y = 20 # 20 pixels from top edge
            self.gallery_icon_button = Button(settings.GALLERY_ICON_PATH, (gallery_button_x, gallery_button_y), anchor='topright', callback=self.open_gallery)
        except Exception as e:
            print(f"警告: 无法创建图库图标按钮: {e}. 图库入口可能无法使用。")
            self.gallery_icon_button = None # Button creation failed


        # Popup text manager (e.g., "美图尚未点亮")
        try:
             self.popup_text = PopupText(self) # Pass Game instance to PopupText
        except Exception as e:
             print(f"警告: PopupText 初始化失败: {e}. 提示功能可能无法使用。")
             self.popup_text = None # PopupText creation failed


        # Autosave variables
        self.last_autosave_time = time.time() # Record time of last autosave

        # Background loading timer
        self._last_background_load_time = time.time() # Initialize background loading timer


        # __init__ completes. Game state is LOADING.
        # Transition to PLAYING happens in the update loop, based on loading progress and min duration.


    # === Loading screen related methods ===
    def draw_loading_screen(self, message="加载中..."):
        """
        Draws the loading screen.
        Called during game initialization or in the LOADING state's draw method.
        """
        self.screen.fill(settings.BLACK) # Black background

        # Draw loading background image
        if self.loading_image:
            # Calculate center position for the loading image
            img_rect = self.loading_image.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
            self.screen.blit(self.loading_image, img_rect)

        # Draw loading text
        # Get loading text surface using the loading font
        if self.font_loading: # Ensure loading font is available
             text_surface = self.font_loading.render(message, True, settings.LOADING_TEXT_COLOR)
             # Calculate text position, centered below the image or screen center
             text_y_offset = (self.loading_image.get_height()//2 + 30 if self.loading_image else 50) # Gap below image or offset from screen center
             text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + text_y_offset ))
             self.screen.blit(text_surface, text_rect)
        else:
             # Fallback text if font failed
             font_fallback = pygame.font.Font(None, 60)
             text_surface = font_fallback.render("加载中...", True, settings.WHITE)
             text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
             self.screen.blit(text_surface, text_rect)


    def _load_random_loading_image(self):
        """Loads a random loading screen image from the list, scaled to fit the screen."""
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

            # Ensure scaled dimensions are valid and non-zero
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
        """Displays a fatal error message on the screen."""
        self.screen.fill(settings.BLACK)
        # Use a fallback font in case main fonts failed
        try:
             font = pygame.font.Font(None, 50)
        except pygame.error:
             font = pygame.font.SysFont("Arial", 50) # System font fallback

        lines = message.split('\n') # Supports multi-line error messages
        y_offset = settings.SCREEN_HEIGHT // 2 - (len(lines) * 60) // 2 # Center vertically based on number of lines
        for line in lines:
            text_surface = font.render(line, True, settings.WHITE)
            text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(text_surface, text_rect)
            y_offset += 60 # Line spacing
        pygame.display.flip()


    # === Save/Load methods ===
    def save_game_data(self):
        """
        Saves the current game state to a file.
        Saves Board layout and state, ImageManager state.
        """
        if self.board is None or self.image_manager is None:
             print("警告: Board 或 ImageManager 未初始化，无法保存游戏状态。")
             return # Cannot save if core components are not ready

        # Only save if the game is in a savable state (e.g., not loading, not upgrading area transition)
        # Do not save during completion animation state
        if self.current_state not in [settings.GAME_STATE_PLAYING,
                                     settings.GAME_STATE_GALLERY_LIST,
                                     settings.GAME_STATE_GALLERY_VIEW_LIT]:
             # print(f"警告: 当前游戏状态 ({self.current_state}) 不允许保存。") # Debug, avoid spamming
             return # Do not save during state transitions like loading or upgrading/animating


        print("保存游戏状态...") # Debug

        # Get Board and ImageManager state data
        try:
            board_state = self.board.get_state() # Board's get_state now includes playable area info etc.
            image_manager_state = self.image_manager.get_state()
        except Exception as e:
            print(f"错误: 获取 Board 或 ImageManager 状态失败，无法保存: {e}") # Debug error
            return # Cannot get state, skip saving


        # Build total save data dictionary
        game_state_data = {
            'board_state': board_state, # <-- Save Board state
            'image_manager_state': image_manager_state, # ImageManager state
            'save_time': time.time() # Add current time as save timestamp
        }

        # Determine save file path
        save_file_path = os.path.join(settings.BASE_DIR, settings.SAVE_FILE_NAME)

        # Write data to JSON file
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
        Attempts to load complete game state data from a file.

        Returns:
            dict or None: Loaded game state dictionary, or None if file doesn't exist or loading fails.
        """
        save_file_path = os.path.join(settings.BASE_DIR, settings.SAVE_FILE_NAME)

        # Check if save file exists
        if not os.path.exists(save_file_path):
            print("没有找到存档文件，开始新游戏。") # Debug
            return None # File does not exist, return None

        # Attempt to load data from JSON file
        try:
            with open(save_file_path, 'r', encoding='utf-8') as f:
                # Use json.load to read the dictionary from the file
                game_state_data = json.load(f)
                # print(f"完整输出加载的数据，看是否加载成功:game_state_data: {game_state_data}")# Result was successful
            print(f"游戏状态已从 {save_file_path} 加载成功。") # Debug success

            # TODO: Optional: Add validation for loaded data structure
            if not isinstance(game_state_data, dict) or 'board_state' not in game_state_data or 'image_manager_state' not in game_state_data:
                 print("警告: 存档文件格式不正确。缺少 'board_state' 或 'image_manager_state' 字段。开始新游戏。") # Debug
                 return None # Data structure is invalid

            # Optional: Validate key types/values if necessary for safety

            return game_state_data # Return loaded data

        except json.JSONDecodeError as e:
            print(f"错误: 存档文件 {save_file_path} 格式错误，无法解析 JSON: {e}. 删除损坏的存档。") # Debug error
            # Optional: Delete the corrupted save file
            # try:
            #     os.remove(save_file_path)
            #     print("已删除损坏的存档文件。")
            # except OSError as os_e:
            #     print(f"错误: 无法删除损坏的存档文件 {save_file_path}: {os_e}")
            return None
        except Exception as e:
            print(f"错误: 加载存档状态失败从 {save_file_path}: {e}") # Debug error
            return None


    # === Game exit method (called by InputHandler) ===
    def quit_game(self):
        """
        Performs save before quitting the game and shuts down Pygame.
        Called by InputHandler when receiving the QUIT event.
        """
        print("接收到退出信号，正在保存并退出...") # Debug
        # Only attempt save if main components are initialized and not in loading state
        if self.board and self.image_manager and self.current_state != settings.GAME_STATE_LOADING:
             self.save_game_data() # Save game state
             print("游戏已保存，退出中...") # Debug
        else:
             print("游戏未初始化或在加载中，不保存。直接退出。") # Debug

        pygame.quit()
        sys.exit()


    # === Gallery related methods (called by InputHandler or elsewhere) ===
    def open_gallery(self):
        """Opens the gallery interface."""
        # Change state using the change_state method
        if self.current_state != settings.GAME_STATE_PLAYING:
             # print("警告: 当前不在PLAYING状态，无法打开图库。") # Debug
             return
        self.change_state(settings.GAME_STATE_GALLERY_LIST) # Switch to gallery list state

    def close_gallery(self):
        """Closes the gallery interface."""
        # Change state using the change_state method
        if self.current_state not in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
             # print("警告: 当前不在图库状态，无法关闭图库。") # Debug
             return
        self.change_state(settings.GAME_STATE_PLAYING) # Switch back to PLAYING state


    # === Popup tip method ===
    def show_popup_tip(self, text):
         """Displays a brief popup tip in the center of the screen."""
         if self.popup_text: # Ensure popup_text is initialized
             self.popup_text.show(text) # Use PopupText's default color and duration

    def start_completion_animation(self, image_id, completed_area_start_pos_grid):
        """
        启动完成动画。
        由 Board 在图片完成时调用。
        返回 True 如果动画成功启动，否则返回 False。

        Args:
            image_id (int): 完成图片的ID。
            completed_area_start_pos_grid (tuple): 完成区域的左上角物理网格坐标 (row, col)。
        Returns:
            bool: True if animation started successfully, False otherwise.
        """
        # Game 状态必须是 PLAYING 才能启动动画。
        # Board 状态应该已经是 PICTURE_COMPLETED。Board 已在调用前检查了这一点。
        if self.current_state == settings.GAME_STATE_PLAYING:
             print(f"Game: 尝试启动图片ID {image_id} 的完成动画。") # 调试信息
             try:
                 # Game is responsible for creating and holding the animation instance.
                 # Pass necessary info to the animation class.
                 # Animation also needs the screen rect of the completed area, calculate it from grid pos.
                 completed_area_screen_rect = self.board.get_completed_area_screen_rect()

                 if completed_area_screen_rect is None:
                      print(f"警告: Game: 无法获取图片ID {image_id} 的完成区域屏幕 Rect，无法启动动画。") # Debug
                      return False # Animation cannot start

                 # === 关键修改：修正传递给 CompletionAnimation 构造函数的参数 ===
                 # 构造函数期望的参数顺序是: image_id, completed_area_start_pos_grid, image_manager, board
                 # 根据 completion_animation.py 文件中的 CompletionAnimation.__init__ 方法定义来传递参数
                 self.active_animation = CompletionAnimation(
                     image_id,                            # 图片ID
                     completed_area_start_pos_grid,       # 完成区域的起始网格坐标
                     self.image_manager,                  # ImageManager 实例
                     self.board                           # Board 实例 (如果动画需要 Board 信息)
                 )
                 # Note: completion_animation.py version I provided expects start_pos_grid, not screen_rect.
                 # Let's confirm what CompletionAnimation.__init__ truly expects from the code.
                 # Looking at completion_animation.py again, the __init__ signature is:
                 # def __init__(self, image_id, completed_area_start_pos_grid, image_manager, board):
                 # It uses completed_area_start_pos_grid and board to calculate start_screen_rect.

                 # Okay, let's ensure we pass the correct parameters as expected by CompletionAnimation.__init__
                 # The previous attempt passed completed_area_screen_rect.topleft and completed_area_screen_rect.size instead of grid pos and board.

                 # === Revised Key Modification based on CompletionAnimation.__init__ signature ===
                 self.active_animation = CompletionAnimation(
                     image_id,                            # int: 图片ID
                     completed_area_start_pos_grid,       # tuple: 完成区域的左上角物理网格坐标 (row, col)
                     self.image_manager,                  # ImageManager 实例
                     self.board                           # Board 实例
                 )
                 # Debugging: Check the types being passed
                 # print(f"Debug: Passing to CompletionAnimation: image_id={image_id} ({type(image_id)}), grid_pos={completed_area_start_pos_grid} ({type(completed_area_start_pos_grid)}), image_manager={self.image_manager} ({type(self.image_manager)}), board={self.board} ({type(self.board)})")


                 # Check if animation instance was initialized successfully (e.g., got image surfaces)
                 if not self.active_animation.is_finished():
                      # Animation initialized successfully.
                      # === 关键修改：Game 负责将 Board 状态设置为 COMPLETION_ANIMATING ===
                      self.board.current_board_state = settings.BOARD_STATE_COMPLETION_ANIMATING
                      print(f"Game: 完成动画已初始化并启动。Board 状态设置为 {self.board.current_board_state}。") # 调试信息
                      # Animation starts playing in Game's update loop.
                      return True # Animation successfully started

                 else:
                      # Animation initialization failed (e.g., couldn't get image surfaces).
                      print(f"警告: Game: 完成动画初始化失败 (is_finished=True)。跳过动画。") # Debug
                      self.active_animation = None # Clear failed animation instance
                      # Return False so Board knows to skip.
                      return False # Animation could not start


             except Exception as e:
                 # Catch any exception during animation creation/initialization
                 print(f"致命错误: Game: 启动完成动画时发生异常: {e}") # Debug
                 self.active_animation = None # Clear faulty animation instance
                 # Return False so Board knows to skip.
                 # Display fatal error message.
                 self._display_fatal_error(f"完成动画启动失败:\n{e}") # Display error and potentially exit Game loop
                 return False # Animation could not start


        else:
             # Game state is not PLAYING. Board should not call this method in other Game states.
             print(f"警告: Game: 在 Game 状态非 PLAYING ({self.current_state}) 时调用 start_completion_animation。忽略请求。") # Debug
             return False # Animation did not start


    # === Core game loop methods ===
    def run(self):
        """Main game loop."""
        running = True
        while running:
            self.delta_time = self.clock.tick(60) / 1000.0 # Calculate precise delta time in seconds

            # --- Event Handling ---
            # All events are passed to the input handler, which dispatches based on game state
            # InputHandler will handle the QUIT event and call game.quit_game()
            for event in pygame.event.get():
                 # Pass event to InputHandler
                 if self.input_handler: # Ensure InputHandler is initialized
                     self.input_handler.handle_event(event)
                 else:
                     # If InputHandler is not ready (e.g., fatal error during init), handle QUIT directly
                     if event.type == pygame.QUIT:
                         running = False # Exit loop


            # --- Game State Update ---
            # Wrap update in try-except to catch errors during gameplay
            try:
                 self.update(self.delta_time)
            except Exception as e:
                 print(f"致命错误: 游戏主循环更新时发生异常: {e}")
                 self._display_fatal_error(f"游戏更新错误:\n{e}")
                 time.sleep(5) # Display error for 5 seconds
                 running = False # Exit loop


            # --- Draw all content ---
            # Wrap draw in try-except as well
            try:
                 self.draw()
            except Exception as e:
                 print(f"致命错误: 游戏主循环绘制时发生异常: {e}")
                 self._display_fatal_error(f"游戏绘制错误:\n{e}")
                 time.sleep(5) # Display error for 5 seconds
                 running = False # Exit loop


            # Update screen display
            pygame.display.flip()

        # Pygame exit is handled by game.quit_game() or direct QUIT handling on fatal error


    def update(self, dt):
        """
        Updates the game logic.

        Args:
            dt (float): Time elapsed since the last frame in seconds.
        """
        # Update based on current game state
        if self.current_state == settings.GAME_STATE_LOADING:
            # In LOADING state update, check loading progress and time
            elapsed_time = time.time() - self.loading_start_time
            # Check if initial load batch is done AND minimum duration is met
            initial_load_done = self.image_manager.is_initial_load_finished() if self.image_manager else False

            # In loading phase, also drive background loading to show progress
            if self.image_manager: # Ensure ImageManager is initialized
                 # Control background loading frequency
                 # Use _last_background_load_time for background load timing
                 # Load batches more frequently during loading state for faster progress display
                 if time.time() - self._last_background_load_time >= settings.BACKGROUND_LOAD_DELAY / 5.0:
                      self.image_manager.load_next_batch_background(settings.BACKGROUND_LOAD_BATCH_SIZE)
                      self._last_background_load_time = time.time() # Update timer


            # Only transition to PLAYING if initial load is done AND min duration is met
            if initial_load_done and elapsed_time >= settings.MIN_LOADING_DURATION:
                 print("Initial load complete and min duration met, transitioning to PLAYING.") # Debug
                 self.change_state(settings.GAME_STATE_PLAYING)


        elif self.current_state == settings.GAME_STATE_PLAYING:
            # === Update the active completion animation if any ===
            if self.active_animation:
                 self.active_animation.update(dt)
                 # Check if the animation is finished
                 if self.active_animation.is_finished():
                      print("Game: 检测到完成动画结束。") # Debug
                      # Notify Board to resume its completion process
                      if self.board:
                           self.board.resume_completion_process_after_animation()
                      self.active_animation = None # Clear the animation instance
                      # Note: Board will handle the state change back to PLAYING


            # === Update Board ===
            # Board's update handles its internal state machine (falling, pending fill, upgrade)
            # Board update should run regardless of whether animation is active,
            # but its internal state machine logic is skipped if state is COMPLETION_ANIMATING.
            if self.board: # Ensure Board is initialized
                 self.board.update(dt) # Board update includes piece updates and its state machine logic (conditional)


            # Update possible popup text timer
            if self.popup_text: # Ensure popup_text is initialized
                 self.popup_text.update(dt)

            # Check and continue background loading (for images not in the initial batch)
            # Only continue background loading if no animation is active
            if self.image_manager and self.active_animation is None: # Ensure ImageManager is initialized AND no active animation
                 self._check_and_continue_background_loading()

            # --- Autosave ---
            current_time = time.time()
            # Only autosave if no animation is active
            if self.active_animation is None and current_time - self.last_autosave_time >= settings.AUTOSAVE_INTERVAL:
                self.save_game_data() # Perform autosave
                self.last_autosave_time = current_time # Reset timer


        elif self.current_state == settings.GAME_STATE_GALLERY_LIST:
            # Update Gallery list state (e.g., scrollbar animation if implemented)
            # Update possible popup text timer (hint might be shown in gallery)
            if self.popup_text:
                 self.popup_text.update(dt)
            # If Gallery update logic is added later, call it here.
            # if hasattr(self.gallery, 'update'): self.gallery.update(dt)
            pass


        elif self.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # Update Gallery big view state (e.g., image transition animation if implemented)
            # Update possible popup text timer (hint might be shown in gallery)
            if self.popup_text:
                 self.popup_text.update(dt)
            # If Gallery update logic is added later, call it here.
            # if hasattr(self.gallery, 'update'): self.gallery.update(dt)
            pass

        # Note: BOARD_STATE_UPGRADING_AREA update is handled within Board.update when Board's state machine runs.


    def draw(self):
        """Draws all game elements."""
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
            # Draw Board (Board.draw will handle drawing pieces unless animation is active)
            if self.board: # Ensure Board is initialized
                 self.board.draw(self.screen)

            # === Draw the active completion animation if any (on top of the board) ===
            if self.active_animation:
                 self.active_animation.draw(self.screen)

            # Draw primary UI elements, like gallery icon button (always on top)
            if hasattr(self, 'gallery_icon_button') and self.gallery_icon_button: # Ensure button is initialized
                 self.gallery_icon_button.draw(self.screen)

            # Draw possible popup text (should be on top of everything else)
            if self.popup_text and self.popup_text.is_active: # Ensure popup_text is initialized and active
                 self.popup_text.draw(self.screen)


        elif self.current_state in [settings.GAME_STATE_GALLERY_LIST, settings.GAME_STATE_GALLERY_VIEW_LIT]:
            # Draw Gallery interface (Gallery class handles drawing list or big image)
            if self.gallery: # Ensure Gallery is initialized
                 self.gallery.draw(self.screen)

            # Draw popup text on top of Gallery
            if self.popup_text and self.popup_text.is_active: # Ensure popup_text is initialized and active
                 self.popup_text.draw(self.screen)

        # Note: BOARD_STATE_UPGRADING_AREA drawing is handled by Board.draw method.


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

        # Execute initialization/cleanup based on state change
        if old_state == settings.GAME_STATE_LOADING and new_state == settings.GAME_STATE_PLAYING:
              # Transition from loading to main game state
             print("进入游戏主状态 PLAYING。")

             # At this point, initial load batch is done, Board and Gallery are initialized.
             # Background loading continues in PLAYING state update.
             pass # Optional transition effects

             # --- 新增：在进入 PLAYING 状态后打印所有碎片位置和状态 (调试) ---
             print("\n--- 所有碎片位置和状态信息 (进入PLAYING时) ---") # Debug header
             # Check if Board and its Sprite Group are initialized and valid
             if self.board and isinstance(self.board, Board) and isinstance(self.board.all_pieces_group, pygame.sprite.Group):
                 # Check if Group has any pieces
                 if not self.board.all_pieces_group:
                     print("  Board 的 Sprite Group 是空的，没有碎片对象。") # Debug Group is empty
                 else:
                     # Print number of sprites in the Group
                     print(f"  Board 的 Sprite Group 包含 {len(self.board.all_pieces_group)} 个碎片对象。") # Debug Group size
                     # Iterate through the group to print info for each Piece
                     for piece in self.board.all_pieces_group:
                          # Safety check to ensure it's a Piece object
                          if isinstance(piece, Piece):
                              # Print key info for the piece
                              # Convert rect coordinates to integers for clarity
                              print(
                                  f"  碎片 ID:{piece.original_image_id}, "
                                  f"原始位置 ({piece.original_row},{piece.original_col}), "
                                  f"当前网格 ({piece.current_grid_row},{piece.current_grid_col}), "
                                  f"当前屏幕 ({int(piece.rect.x)},{int(piece.rect.y)}), "
                                  f"正在下落: {piece.is_falling}" # Print if falling
                              ) # Debug piece info
                          else:
                              # If non-Piece objects are in the Group, print warning
                              print(f"  警告: Board 的 Sprite Group 中包含非 Piece/非 Sprite 对象: {type(piece)}") # Debug invalid object
             else:
                 # If Board or Sprite Group is not initialized or invalid, print warning
                 print("警告: Board 或其 Sprite Group 未初始化或无效，无法打印碎片信息。") # Debug Board not ready
             print("--- 碎片信息打印结束 ---\n") # Debug footer
             # --- End of debug print ---


        elif new_state == settings.GAME_STATE_GALLERY_LIST:
            # Enter gallery list interface
            print("进入图库列表状态。")
            if self.gallery: # Ensure gallery instance exists
                # Notify gallery to prepare list view (update list content)
                self.gallery.open_gallery()
            # Stop interactions in the main game view (unselect, stop dragging)
            if self.board: # Ensure board instance exists
                self.board.unselect_piece()
                self.board.stop_dragging()
            # Board update method checks its internal state, no need to explicitly pause it here.

        elif old_state == settings.GAME_STATE_GALLERY_LIST and new_state == settings.GAME_STATE_PLAYING:
            # Return from gallery list interface to main game
            print("从图库列表状态返回游戏主状态。")
            if self.gallery: # Ensure gallery instance exists
                # Notify gallery to close (reset internal state)
                self.gallery.close_gallery()

        elif new_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # Enter large image viewing interface (from list state)
            print("进入图库大图查看状态。")
            # This state change is triggered by Gallery.start_viewing_lit_image

        elif old_state == settings.GAME_STATE_GALLERY_VIEW_LIT and new_state == settings.GAME_STATE_GALLERY_LIST:
            # Return from large image viewing interface to gallery list
            print("从图库大图查看状态返回图库列表状态。")
            # This state change is triggered by Gallery.stop_viewing_lit_image

        # Note: BOARD_STATE_UPGRADING_AREA and BOARD_STATE_COMPLETION_ANIMATING
        # are Board internal states, not Game states. Game state remains PLAYING
        # during these Board transitions, but input is blocked.
        # The transition to these states is triggered by Board.
        # The transition *out* of COMPLETION_ANIMATING is triggered by Game after animation.


        # TODO: Add cleanup/initialization logic for other state transitions


    # ... Other methods ...

    def _check_and_continue_background_loading(self):
         """
         Checks and continues background loading of unprocessed images.
         This method is called in the GAME_STATE_PLAYING update.
         """
         # Only attempt if ImageManager is initialized and there are unprocessed images
         # Also, do not load during the completion animation as it's resource intensive
         if self.image_manager is None or self.image_manager.is_loading_finished() or self.active_animation is not None:
              # print("后台加载：所有图片已加载完成或 ImageManager 未初始化 或 正在播放动画。") # Debug, avoid spamming
              return # All images loaded or ImageManager not ready or animation is active

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


    # ... (Rest of the main.py file remains the same) ...

if __name__ == "__main__":
    game = Game()
    game.run()