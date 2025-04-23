# completion_animation.py
# 管理图片完成时的动画表现

import pygame
import settings
import time
import utils
import image_manager # 需要 ImageManager 获取图片 Surface
import math # 用于计算缩放比例

class CompletionAnimation:
    def __init__(self, image_id, completed_area_start_pos_grid, image_manager, board):
        """
        初始化完成动画。

        Args:
            image_id (int): 完成图片的ID。
            completed_area_start_pos_grid (tuple): 完成区域的左上角物理网格坐标 (row, col)。
            image_manager (ImageManager): 图像管理器实例。
            board (Board): Board 实例，用于获取 Board 的像素偏移等信息。
        """
	
        # === 动画阶段状态常量 ===
        self._STATE_MOVE_SCALE = 'move_scale'
        self._STATE_CROSS_FADE = 'cross_fade'
        self._STATE_PAUSED_TIMED = 'paused_timed'   # 新状态：定时暂停中
        self._STATE_PAUSED_INPUT = 'paused_input' # 新状态：等待用户输入
        self._STATE_FINISHED = 'finished'


        self.image_id = image_id
        self.image_manager = image_manager
        self.board = board # Store Board instance

        # === 获取动画所需的图片 Surface ===
        # 获取为碎片处理后的完整图片 (用于第一阶段动画)
        # 需要 ImageManager 有 get_full_processed_image 方法
        if hasattr(self.image_manager, 'get_full_processed_image'):
             self.processed_img_surface = self.image_manager.get_full_processed_image(self.image_id)
        else:
             print("错误: ImageManager 缺少 get_full_processed_image 方法，无法播放完成动画。") # Debug
             self.processed_img_surface = None

        # 获取原始图片 (用于第二阶段动画)
        # 需要 ImageManager 有 get_original_full_image 方法
        if hasattr(self.image_manager, 'get_original_full_image'):
            self.original_img_surface = self.image_manager.get_original_full_image(self.image_id)
        else:
             print("错误: ImageManager 缺少 get_original_full_image 方法，无法播放完成动画。") # Debug
             self.original_img_surface = None


        # 如果任何一个图片Surface获取失败，动画无法进行
        if self.processed_img_surface is None or self.original_img_surface is None:
            print(f"错误: 完成动画初始化失败，无法获取图片ID {self.image_id} 的处理后或原始图片 Surface。") # Debug
            self._is_finished = True # 直接标记动画完成 (失败)
            return
        else:
            self._is_finished = False # 标记动画未完成


        # === 计算动画的起始和结束尺寸及 Rect ===

        # 1. 起始尺寸 (处理后图片的原始尺寸)
        self.start_size_processed = self.processed_img_surface.get_size()
        print(f"完成动画初始化: 图片ID {self.image_id} 处理后图片尺寸 {self.start_size_processed}.") # Debug
        # 初始 Rect (处理后图片在 Board 完成区域的位置)
        start_screen_x = settings.BOARD_OFFSET_X + completed_area_start_pos_grid[1] * settings.PIECE_WIDTH
        start_screen_y = settings.BOARD_OFFSET_Y + completed_area_start_pos_grid[0] * settings.PIECE_HEIGHT
        self.start_rect_processed = pygame.Rect(start_screen_x, start_screen_y, self.start_size_processed[0], self.start_size_processed[1])


        # 2. 中间目标尺寸 (处理后图片放大/缩小，使其能够包含原始图片尺寸后的尺寸)
        original_img_w, original_img_h = self.original_img_surface.get_size()
        processed_img_w, processed_img_h = self.start_size_processed

        screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        # 3. 最终目标尺寸 (原始图片按比例缩放适应屏幕并留有边距后的尺寸)
        # 使用 Gallery 中原始图片大图查看的缩放逻辑计算最终尺寸
        margin = settings.COMPLETION_ANIM_MARGIN
        # Calculate the maximum scale factor to fit within the screen boundaries with margins
        # Avoid division by zero if original image dimensions are 0
        if original_img_w <= 0 or original_img_h <= 0:
             print(f"警告: 完成动画初始化: 原始图片尺寸 ({original_img_w}x{original_img_h}) 无效，无法计算最终尺寸。") # Debug
             self.final_size_original = (200, 150) # Fallback size
        else:
             max_scale_factor = min((screen_w - margin) / original_img_w, (screen_h - margin) / original_img_h)
             # Ensure scale factor is valid
             if max_scale_factor <= 0 or not math.isfinite(max_scale_factor):
                  print(f"警告: 完成动画初始化: 原始图片适应屏幕缩放因子 ({max_scale_factor}) 无效。") # Debug
                  self.final_size_original = (original_img_w, original_img_h) # Fallback to original size
             else:
                  self.final_size_original = (int(original_img_w * max_scale_factor), int(original_img_h * max_scale_factor))
                  print(f"完成动画初始化: 原始图片最终尺寸 (适应屏幕) {self.final_size_original}.") # Debug


        # 动画第二阶段（交叉淡出原始图）的结束 Rect，位于屏幕中心，尺寸是 final_size_original
        self._final_original_rect = pygame.Rect(0, 0, self.final_size_original[0], self.final_size_original[1]) # Create rect with final size
        self._final_original_rect.center = (screen_w // 2, screen_h // 2) # Center it


        # 避免除以零，确保尺寸有效
        if processed_img_w <= 0 or processed_img_h <= 0 or original_img_w <= 0 or original_img_h <= 0:
             print(f"警告: 完成动画初始化: 图片尺寸无效，无法计算放大比例。原始 {original_img_w}x{original_img_h}, 处理后 {processed_img_w}x{processed_img_h}.") # Debug
             # Fallback to using processed image size as middle size (no scaling in phase 1)
             self.middle_size_processed = self.start_size_processed
        else:
            # === 关键修改：根据您提供的逻辑计算整体放大比例 ===
            processed_aspect = processed_img_h / processed_img_w
            original_aspect = original_img_h / original_img_w
            print(f"完成动画初始化: 原始宽度 {original_img_w}, 处理后图片宽度 {processed_img_w}.") # Debug

            if original_aspect >= processed_aspect:
                # 原始图片相对更“高瘦”或比例接近，以原始图片的高度为基准计算比例
                overall_scale_factor = self.final_size_original[0] / processed_img_w        #不能用原始图片作为比例，要用实际在游戏显示的大图作为比例
            else:
                # 原始图片相对更“矮胖”，以原始图片的宽度为基准计算比例
                overall_scale_factor = self.final_size_original[1] / processed_img_h

            # 确保计算出的比例有效且不是无穷大
            print(f"完成动画初始化: 原始图片比例 {original_aspect:.2f}, 处理后图片比例 {processed_aspect:.2f}, 整体放大比例 {overall_scale_factor:.2f}.") # Debug
            if overall_scale_factor <= 0 or not math.isfinite(overall_scale_factor):
                 print(f"警告: 完成动画初始化: 计算出的整体放大比例 ({overall_scale_factor}) 无效。") # Debug
                 # Fallback to using processed image size as middle size (no scaling)
                 self.middle_size_processed = self.start_size_processed
            else:
                 # 使用计算出的整体放大比例计算中间目标尺寸
                 self.middle_size_processed = (int(processed_img_w * overall_scale_factor),
                                              int(processed_img_h * overall_scale_factor))

        # 动画第一阶段（移动和缩放）的结束 Rect，位于屏幕中心，尺寸是 middle_size_processed

        self.end_rect = pygame.Rect(0, 0, self.middle_size_processed[0], self.middle_size_processed[1]) # Create rect with middle size
        self.end_rect.center = (screen_w // 2, screen_h // 2) # Center it




        # === 动画参数和状态 ===
        self.duration_move_scale = settings.COMPLETION_ANIM_MOVE_SCALE_DURATION
        self.duration_cross_fade = settings.COMPLETION_ANIM_CROSS_FADE_DURATION
        # === 关键修改：新增暂停时长参数 ===
        self.duration_pause = settings.COMPLETION_ANIM_PAUSE_DURATION
        self._total_duration = self.duration_move_scale + self.duration_cross_fade + self.duration_pause # 增加总时长（虽然不直接用）

        self._start_time = time.time() # 动画开始时间 (总动画开始时间)
        self._elapsed_time = 0.0 # 动画已进行时间 (当前阶段已进行时间)

        self._state = self._STATE_MOVE_SCALE # 动画阶段: 'move_scale', 'cross_fade', 'paused_timed', 'paused_input', 'finished'

        # 初始透明度
        self.current_alpha_processed = 255 # 初始完全不透明
        self.current_alpha_original = 0 # 初始完全透明

        # === 初始化用于绘制的当前 Rect (Phase 1) ===
        self._current_draw_rect = self.start_rect_processed.copy() # 动画开始时，绘制位置和尺寸就是起始位置和尺寸

        # Note: set_alpha should be applied during draw, not here permanently on cached surfaces.

        print(f"完成动画已初始化: 图片ID {self.image_id}. 起始: {self.start_rect_processed}, 中间目标: {self.end_rect}, 最终目标 (原始图): {self._final_original_rect}.") # Debug


# ... (保留 CompletionAnimation 类其他方法不变) ... # Debug


    def update(self, dt):
        """更新动画状态和进度。由 Game 的 update 调用。"""
        if self._is_finished:
            return

        self._elapsed_time += dt # 累加当前阶段已进行时间

        # === 动画阶段逻辑 ===
        if self._state == self._STATE_MOVE_SCALE:
            # 阶段进度 (0.0 to 1.0)
            progress = min(1.0, self._elapsed_time / self.duration_move_scale)

            # 差值计算当前 Rect (从起始 Rect 插值到 中间目标 Rect)
            # 插值位置 (topleft)
            current_x = self.start_rect_processed.x + (self.end_rect.x - self.start_rect_processed.x) * progress
            current_y = self.start_rect_processed.y + (self.end_rect.y - self.start_rect_processed.y) * progress
            # 插值尺寸
            current_w = self.start_rect_processed.width + (self.end_rect.width - self.start_rect_processed.width) * progress
            current_h = self.start_rect_processed.height + (self.end_rect.height - self.start_rect_processed.height) * progress

            # 更新用于绘制的当前 Rect (处理后图片在 phase 1 绘制于此)
            self._current_draw_rect = pygame.Rect(int(current_x), int(current_y), int(current_w), int(current_h))

            # 检查阶段是否结束
            if progress >= 1.0:
                print("完成动画阶段 1 (移动/缩放处理后图到中间尺寸) 结束。") # Debug
                self._state = self._STATE_CROSS_FADE
                self._elapsed_time = 0.0 # 重置阶段已进行时间
                # 在淡出阶段，处理后图片和原始图片都将以其各自的目标结束尺寸绘制在屏幕中心。
                # 处理后图片将以 middle_size_processed (即 self.end_rect.size) 绘制。


        elif self._state == self._STATE_CROSS_FADE:
            # 阶段进度 (0.0 to 1.0)
            progress = min(1.0, self._elapsed_time / self.duration_cross_fade)

            # 交叉淡出透明度
            self.current_alpha_processed = int(255 * (1.0 - progress)) # 处理后图淡出 (255 -> 0)
            self.current_alpha_original = int(255 * progress)         # 原始图淡入 (0 -> 255)

            # 确保 alpha 值在有效范围 [0, 255] 内
            self.current_alpha_processed = max(0, min(255, self.current_alpha_processed))
            self.current_alpha_original = max(0, min(255, self.current_alpha_original))


            # 检查阶段是否结束
            if progress >= 1.0:
                print("完成动画阶段 2 (交叉淡出) 结束。") # Debug
                # === 关键修改：切换到定时暂停阶段 ===
                self._state = self._STATE_PAUSED_TIMED
                self._elapsed_time = 0.0 # 重置阶段已进行时间


        # === 关键修改：新增定时暂停阶段 ===
        elif self._state == self._STATE_PAUSED_TIMED:
            # 阶段进度 (0.0 to 1.0) - 用于计时
            progress = min(1.0, self._elapsed_time / self.duration_pause)

            # 在此阶段，动画画面保持不变 (已完成淡出)，只进行计时。
            # 绘制逻辑将在 draw 方法中处理。

            # 检查定时暂停是否结束
            if progress >= 1.0:
                print(f"完成动画阶段 3 (定时暂停 {self.duration_pause}s) 结束。等待用户输入。") # Debug
                # === 关键修改：切换到等待用户输入阶段 ===
                self._state = self._STATE_PAUSED_INPUT
                self._elapsed_time = 0.0 # 重置阶段已进行时间 (虽然在此阶段不直接使用)


        # === 关键修改：新增等待用户输入阶段 ===
        elif self._state == self._STATE_PAUSED_INPUT:
            # 在此阶段，动画画面保持不变，等待 handle_event 方法接收到用户输入。
            # update 方法在此阶段不做任何计时或画面更新。
            pass


        # 'finished' state does nothing in update, just waits for Game to check is_finished()


    def draw(self, surface):
        """在指定的 Surface 上绘制动画的当前帧。由 Game 的 draw 调用。"""
        # 不在 finished 状态时进行绘制
        if self._is_finished:
            return

        # === 绘制当前动画帧 ===
        if self._state == self._STATE_MOVE_SCALE:
            # 在移动/缩放阶段，只绘制 处理后图片，将其缩放到当前插值尺寸并绘制到当前插值位置。
            if self.processed_img_surface and self._current_draw_rect:
                # 只有当 Rect 尺寸有效时才尝试缩放和绘制
                if self._current_draw_rect.width > 0 and self._current_draw_rect.height > 0:
                    try:
                        # 缩放处理后图片到当前插值计算出的尺寸
                        scaled_processed_img = pygame.transform.scale(self.processed_img_surface, self._current_draw_rect.size)
                        # 绘制到当前插值计算出的位置
                        surface.blit(scaled_processed_img, self._current_draw_rect.topleft)
                    except pygame.error as e:
                        print(f"警告: 完成动画绘制阶段1缩放/绘制失败: {e}") # Debug
                    except Exception as e:
                        print(f"警告: 完成动画绘制阶段1发生未知错误: {e}") # Debug


        elif self._state == self._STATE_CROSS_FADE:
            # 在交叉淡出阶段，同时绘制 处理后图片 (淡出) 和 原始图片 (淡入)。
            # 它们各自缩放到自己的目标结束尺寸，并绘制在屏幕中心。

            # 绘制 原始图片 淡入
            if self.original_img_surface and self.current_alpha_original > 0 and self._final_original_rect:
                 # 只有当 Rect 尺寸有效时才尝试缩放和绘制
                 if self._final_original_rect.width > 0 and self._final_original_rect.height > 0:
                      # 临时设置原始图片的 alpha 值
                      original_alpha = self.original_img_surface.get_alpha() # 保存原始 alpha
                      self.original_img_surface.set_alpha(self.current_alpha_original)

                      try:
                           # 缩放原始图片到 最终目标尺寸 (final_size_original)
                           scaled_original_img = pygame.transform.scale(self.original_img_surface, self._final_original_rect.size)
                           # 绘制到屏幕中心 (_final_original_rect 的位置就是屏幕中心)
                           surface.blit(scaled_original_img, self._final_original_rect.topleft)
                      except pygame.error as e:
                           print(f"警告: 完成动画绘制阶段2原始图缩放/绘制失败: {e}") # Debug
                      except Exception as e:
                           print(f"警告: 完成动画绘制阶段2原始图发生未知错误: {e}") # Debug
                      finally:
                           # 恢复原始图片的 alpha 值
                           self.original_img_surface.set_alpha(original_alpha)


            # 绘制 处理后图片 淡出
            if self.processed_img_surface and self.current_alpha_processed > 0 and self.end_rect:
                 # 只有当 Rect 尺寸有效时才尝试缩放和绘制
                 if self.end_rect.width > 0 and self.end_rect.height > 0:
                      # 临时设置处理后图片的 alpha 值
                      processed_alpha = self.processed_img_surface.get_alpha() # 保存原始 alpha
                      self.processed_img_surface.set_alpha(self.current_alpha_processed)

                      try:
                           # 缩放处理后图片到 中间目标尺寸 (middle_size_processed)
                           scaled_processed_img = pygame.transform.scale(self.processed_img_surface, self.end_rect.size)
                           # 绘制到屏幕中心 (end_rect 的位置就是屏幕中心)
                           surface.blit(scaled_processed_img, self.end_rect.topleft)
                      except pygame.error as e:
                           print(f"警告: 完成动画绘制阶段2处理图缩放/绘制失败: {e}") # Debug
                      except Exception as e:
                           print(f"警告: 完成动画绘制阶段2处理图发生未知错误: {e}") # Debug
                      finally:
                           # 恢复处理后图片的 alpha 值
                           self.processed_img_surface.set_alpha(processed_alpha)


        # === 关键修改：新增绘制暂停阶段的画面 ===
        elif self._state == self._STATE_PAUSED_TIMED or self._state == self._STATE_PAUSED_INPUT:
            # 在暂停阶段，只绘制完全不透明的原始图片在最终目标位置。
            if self.original_img_surface and self._final_original_rect:
                 # 只有当 Rect 尺寸有效时才尝试缩放和绘制
                 if self._final_original_rect.width > 0 and self._final_original_rect.height > 0:
                      # 确保 alpha 是完全不透明的，或者使用保存的原始 alpha
                      original_alpha = self.original_img_surface.get_alpha() # 保存原始 alpha
                      self.original_img_surface.set_alpha(255) # 强制不透明绘制

                      try:
                           # 缩放原始图片到 最终目标尺寸 (final_size_original)
                           scaled_original_img = pygame.transform.scale(self.original_img_surface, self._final_original_rect.size)
                           # 绘制到屏幕中心 (_final_original_rect 的位置就是屏幕中心)
                           surface.blit(scaled_original_img, self._final_original_rect.topleft)
                      except pygame.error as e:
                           print(f"警告: 完成动画绘制暂停阶段缩放/绘制失败: {e}") # Debug
                      except Exception as e:
                           print(f"警告: 完成动画绘制暂停阶段发生未知错误: {e}") # Debug
                      finally:
                           # 恢复原始图片的 alpha 值
                           self.original_img_surface.set_alpha(original_alpha)


        # 'finished' state does nothing in draw.


    def is_finished(self):
        """返回动画是否已完成。"""
        # 动画在状态为 'finished' 时才算完成。
        return self._state == self._STATE_FINISHED

    # Add a start method if you want to be explicit about starting
    # def start(self):
    #     """Starts the animation."""
    #     self._start_time = time.time()
    #     self._state = self._STATE_MOVE_SCALE # Set initial state
    #     self._is_finished = False # Reset finished flag
    #     self._elapsed_time = 0.0 # Reset elapsed time
    #     self._current_draw_rect = self.start_rect_processed.copy() # Reset drawing rect
    #     self.current_alpha_processed = 255 # Reset alpha
    #     self.current_alpha_original = 0 # Reset alpha
    #     print("Completion animation started.") # Debug

    # === 关键修改：新增事件处理方法 ===
    def handle_event(self, event):
        """处理动画状态下的事件。由 InputHandler 传递。"""
        # 只在等待用户输入阶段处理特定事件
        if self._state == self._STATE_PAUSED_INPUT:
             # 例如，处理鼠标左键点击任意位置
             if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                  print("完成动画：接收到用户点击，结束等待输入阶段。") # Debug
                  # 切换状态到 finished，通知动画结束
                  self._state = self._STATE_FINISHED
                  self._is_finished = True
                  # Return True to indicate the event was handled by the animation
                  return True

        # If not in paused_input state or event not handled, return False
        return False


# ... (保留文件其他方法不变) ...