# input_handler.py
# 负责处理用户输入 (鼠标点击、拖拽等) 并转换为游戏动作

import pygame
import sys
import settings
# 修改导入语句
import utils  # 替代 from utils import screen_to_grid
from utils import screen_to_grid # 导入工具函数
# from board import Board # 需要导入Board类来操作拼盘
import board # 需要导入Board类来操作拼盘
# from main import Game # 可能需要Game实例来改变状态 (如打开图库)
import math # 用于计算鼠标按下和释放位置的距离


class InputHandler:
    def __init__(self, board, game):
        """
        初始化输入处理器

        Args:
            board (Board): 游戏板实例
            game (Game): Game实例，用于状态切换等
        """
        self.board = board
        self.game = game # Game实例用于访问游戏状态和状态切换方法
        self.is_dragging = False # 是否正在拖拽

        # 记录鼠标左键按下的像素位置，用于判断是点击还是拖拽
        self.mouse_down_pos = (-1, -1)
        self.mouse_down_grid_pos = (-1, -1) # 记录鼠标按下时的网格位置

        self.dragging_piece = None # 当前正在被拖拽的 Piece 对象 (引用 Board.dragging_piece)
        self.drag_start_grid_pos = (-1, -1) # 拖拽开始时，该碎片所在的网格位置

        # 拖拽时碎片的视觉偏移量 (如果需要碎片中心不完全跟随鼠标，但目前是完全跟随)
        # self.drag_offset_from_center = (0, 0)

        self.last_processed_grid_pos = (-1, -1) # 拖拽过程中，鼠标上一次进行交换或检查的网格位置


    def handle_event(self, event):
        """
        处理单个Pygame事件。

        Args:
            event (pygame.event.Event): Pygame事件对象。
        """
        # 首先处理那些与游戏状态无关的事件，比如退出
        if event.type == pygame.QUIT:
            # 当接收到退出事件时，调用 Game 类的退出方法，该方法会负责存档和退出
            if hasattr(self.game, 'quit_game'):
                self.game.quit_game()
                print("退出游戏")
            else:
                 # If quit_game method is not available (e.g., fatal error during init), exit directly
                 print("退出游戏 (错误)")
                 pygame.quit()
                 sys.exit()


        # 根据当前游戏状态，将事件分发给对应的处理逻辑
        if self.game.current_state == settings.GAME_STATE_PLAYING:
            # 处理主游戏界面的输入
            self._handle_playing_input(event)
        elif self.game.current_state == settings.GAME_STATE_GALLERY_LIST:
            # 事件交给 Gallery 类处理列表视图逻辑
            if hasattr(self.game, 'gallery') and self.game.gallery:
                 # Gallery's handle_event_list method should return True if event is consumed
                 self.game.gallery.handle_event_list(event)
                 # If Gallery handles click on external area, it will change state and return True, no further handling needed here.

        elif self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # 事件交给 Gallery 类处理大图查看逻辑
            if hasattr(self.game, 'gallery') and self.game.gallery:
                 # Gallery's handle_event_view_lit method should return True if event is consumed
                 self.game.gallery.handle_event_view_lit(event)

        # else: # LOADING state: only QUIT event handled above. Other events are ignored.


    def _handle_playing_input(self, event):
        """处理游戏进行中状态下的输入事件"""

        # 处理键盘事件 (例如用于 debug 显示切换)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # 按下空格键，切换 debug 显示标志为 True
                if hasattr(self.game, 'display_piece_info'): # 安全检查
                    self.game.display_piece_info = True
                    # print("Debug显示开启") # Debug

        elif event.type == pygame.KEYUP:
             if event.key == pygame.K_SPACE:
                # 释放空格键，切换 debug 显示标志为 False
                if hasattr(self.game, 'display_piece_info'): # 安全检查
                    self.game.display_piece_info = False
                    # print("Debug显示关闭") # Debug

        # === 关键修改：在 Board 状态不是 PLAYING 或完成动画状态下，屏蔽玩家操作 ===
        # Allow mouse up event processing to clean up dragging state even if not PLAYING/ANIMATING
        # Also allow event handling by the active animation
        if self.board.current_board_state != settings.BOARD_STATE_PLAYING and \
           self.board.current_board_state != settings.BOARD_STATE_COMPLETION_ANIMATING:
            # Process mouse up to stop dragging if state changed mid-drag
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._handle_mouse_up(event) # <-- Pass event
            # For any other event in this state, return False to indicate not handled by playing input
            return # Shield input

        # === 关键修改：在 完成动画状态下，将事件传递给动画处理 ===
        if self.board.current_board_state == settings.BOARD_STATE_COMPLETION_ANIMATING:
             # During animation, player input is mostly shielded, BUT the animation itself needs to handle input for dismissal.
             # Pass the event to the active animation instance.
             if hasattr(self.game, 'active_animation') and self.game.active_animation:
                  # The animation's handle_event method should return True if it consumes the event (e.g., click to dismiss)
                  if self.game.active_animation.handle_event(event):
                       return # Event was handled by the animation.

             # Even if the event was not handled by the animation, shield other playing input logic
             # Allow mouse up event processing to clean up dragging state if it ended here (unlikely if drag started in PLAYING)
             if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                 self._handle_mouse_up(event) # <-- Pass event
             # For any other event in this state (if not handled by animation), return False to indicate not handled by playing input
             return # Shield input


        # If we reach here, Board state is PLAYING. Process regular input.

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 左键点击
                self._handle_mouse_down(event) # <-- Pass event
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: # 左键释放
                self._handle_mouse_up(event) # <-- Pass event
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event) # <-- Pass event


    # def _handle_mouse_down(self, mouse_pos): # Old signature
    def _handle_mouse_down(self, event): # <-- New method signature
        """Handles mouse left button down event."""
        # event parameter now contains pos, button, etc.
        mouse_pos = event.pos # <-- Get mouse_pos from event

        # Board state check already happened in _handle_playing_input.

        self.mouse_down_pos = mouse_pos # Record pixel position of mouse down

        # Check if the gallery icon button was clicked
        if hasattr(self.game, 'gallery_icon_button') and self.game.gallery_icon_button:
            # Pass the complete event object to the button handler
            # Button.handle_event checks for click and executes callback
            # If Button handles the event, it returns True
            # We only care about MouseButtonDown here (already filtered outside)
            if self.game.gallery_icon_button.handle_event(event): # <-- Pass the actual event to the button handler
                # If gallery button handled the click, return. Do not process board logic.
                # print("Gallery button click event handled.") # Debug
                return # Event consumed

        # If the click was not handled by the gallery button, continue with board click logic
        self.mouse_down_grid_pos = utils.screen_to_grid(mouse_pos) # Record grid position of mouse down

        # Convert pixel coordinates to grid coordinates
        grid_pos = utils.screen_to_grid(mouse_pos)
        r, c = grid_pos

        # Check if click position is within board boundaries
        if grid_pos == (-1, -1): # Outside board
            # If a piece is currently selected (in click-swap mode), click in empty area cancels selection
            if self.board.selected_piece:
                 self.board.unselect_piece() # Notify board to unselect
            return # Click outside board, do not process

        # Click position is within board boundaries (grid_pos is valid)
        clicked_piece = self.board.grid[r][c]

        if clicked_piece:
            # If there's a piece at the clicked position, mark it as potentially starting a drag
            # Assign the clicked piece to dragging_piece
            self.dragging_piece = clicked_piece
            self.drag_start_grid_pos = (r, c)
            self.last_processed_grid_pos = (r, c) # Record grid position at start of drag, used for subsequent drag-swap checks

            # Calculate mouse offset from piece center for dragging (if needed)
            # self.drag_offset_from_center = (mouse_pos[0] - clicked_piece.rect.centerx, mouse_pos[1] - clicked_piece.rect.centery)

            # Note: Do not call board.start_dragging or select_piece immediately here.
            # Wait for MOUSEMOTION (to determine drag) or MOUSEBUTTONUP (to determine click) to decide the specific operation.

        else:
            # If there is no piece at the clicked position (empty slot)
            # And a piece is currently selected (in click-swap mode), unselect it
            if self.board.selected_piece:
                 self.board.unselect_piece()
            # If no piece is selected, clicking an empty slot triggers no action


    def _handle_mouse_up(self, event): # <-- New method signature
        """Handles mouse left button release event."""
        mouse_pos = event.pos # <-- Get mouse_pos from event

        # If mouse down position was invalid, or Board state disallowed operation, do not process further logic
        # Board state check is handled in _handle_playing_input, but mouse_down_pos still needs check.
        if self.mouse_down_pos == (-1, -1):
            # ... (Cleanup state logic remains the same) ...
            self.is_dragging = False # Ensure dragging stops if mouse_down was invalid
            if self.dragging_piece:
                self.board.stop_dragging()
                self.dragging_piece = None
            self.drag_start_grid_pos = (-1, -1)
            self.last_processed_grid_pos = (-1, -1)
            self.mouse_down_grid_pos = (-1, -1) # Ensure mouse_down_grid_pos is also reset
            self.mouse_down_pos = (-1, -1) # Ensure mouse_down_pos is also reset
            return # Invalid mouse down state


        # Calculate distance between mouse down and up positions
        click_distance = math.dist(self.mouse_down_pos, mouse_pos)

        # Grid position at release point
        release_grid_pos = utils.screen_to_grid(mouse_pos)
        release_r, release_c = release_grid_pos


        if self.is_dragging:
            # If releasing mouse while dragging
            self.is_dragging = False # Exit dragging state

            if self.dragging_piece:
                self.board.stop_dragging() # Notify board to stop dragging state, piece snaps back to its current grid position

            # Clear drag-related state variables
            self.dragging_piece = None
            self.drag_start_grid_pos = (-1, -1)
            self.last_processed_grid_pos = (-1, -1)

            # Completion check after drag-swap is triggered in board.swap_pieces, not here.

        # If not dragging (mouse moved less than threshold), this is a simple click
        elif click_distance < settings.DRAG_THRESHOLD:
             # This is a click event
             # Check if click release position is within board for click-swap processing
            if release_grid_pos != (-1, -1): # Within board
                 # If there is a piece at the click release position
                 clicked_piece = self.board.grid[release_r][release_c]
                 if clicked_piece:
                      self._handle_click_swap(clicked_piece, release_grid_pos)
                 else:
                      # If no piece at click release position, and a piece is currently selected, unselect it
                      if self.board.selected_piece:
                           self.board.unselect_piece()
            else: # Click release position is outside board
                 # If a piece is currently selected, clicking outside the board cancels selection
                 if self.board.selected_piece:
                      self.board.unselect_piece()


        # Reset mouse down position records
        self.mouse_down_pos = (-1, -1)
        self.mouse_down_grid_pos = (-1, -1)


    def _handle_mouse_motion(self, event):
        """
        Handles mouse motion event.

        Args:
            event (pygame.event.Event): Mouse motion event object.
        """
        # Ensure left mouse button is pressed and Board state allows operation (dragging only in PLAYING)
        # Board state check already happened in _handle_playing_input.
        # Just check if left button is pressed.
        if not pygame.mouse.get_pressed()[0]:
             # If left mouse button is not pressed, and we were dragging, clean up
             if self.is_dragging:
                 # print("Mouse button released during motion, stopping drag.") # Debug
                 self.board.stop_dragging() # Notify Board to stop dragging state
                 self.is_dragging = False
                 self.dragging_piece = None
                 self.drag_start_grid_pos = (-1, -1)
                 self.last_processed_grid_pos = (-1, -1)
             return # Do not process motion event

        # Get current mouse pixel position
        mouse_pos = event.pos

        # Check if dragging should start
        # Only enter formal dragging state if left mouse button was pressed on a piece (self.dragging_piece is temporarily assigned),
        # and mouse has moved beyond the threshold.
        if not self.is_dragging and self.mouse_down_pos != (-1, -1) and self.dragging_piece is not None:
             move_distance = math.dist(self.mouse_down_pos, mouse_pos)
             if move_distance >= settings.DRAG_THRESHOLD:
                 # Moved beyond threshold, officially enter dragging state
                 self.is_dragging = True
                 # print(f"Starting formal drag, initial grid: {self.drag_start_grid_pos}") # Debug
                 # Notify board that this piece is being dragged (for potential visual effects)
                 self.board.start_dragging(self.dragging_piece) # Call board method to start dragging state

                 # If a piece was previously selected (click-swap mode), unselect it
                 if self.board.selected_piece:
                      self.board.unselect_piece()

                 # Initialize the last processed grid position to the starting grid position of the drag
                 self.last_processed_grid_pos = self.drag_start_grid_pos


        # If already in dragging state
        if self.is_dragging and self.dragging_piece:
            # Update the screen position of the dragging piece, centering it on the mouse
            # This is just visual following, the piece's current_grid_row/col and position in the grid array are only updated during swap.
            # Apply drag offset if needed:
            # self.dragging_piece.rect.center = (mouse_pos[0] - self.drag_offset_from_center[0], mouse_pos[1] - self.drag_offset_from_center[1])
            self.dragging_piece.rect.center = mouse_pos # Piece center follows mouse directly

            # Get the grid position the mouse is currently over
            current_grid_pos = utils.screen_to_grid(mouse_pos)
            current_r, current_c = current_grid_pos

            # Check if the current grid position is on the board AND different from the last position processed for swap/check
            # Only consider swapping when the mouse moves into a *new* grid cell.
            if (current_grid_pos != (-1, -1) and # Mouse is on the board
                current_grid_pos != self.last_processed_grid_pos): # Mouse entered a new grid cell

                # Get the current grid position of the piece being dragged (its logical position in the grid array)
                # Note: This position might have changed during dragging due to quick swaps
                dragging_piece_current_grid_pos = (self.dragging_piece.current_grid_row, self.dragging_piece.current_grid_col)

                # Check if the mouse's new grid position is different from the dragged piece's current grid position
                # (This is usually true if current_grid_pos != self.last_processed_grid_pos, but double-checking)
                if current_grid_pos != dragging_piece_current_grid_pos:

                    # Attempt to swap with the piece at the new grid position
                    # swap_pieces method handles the case where the target position is empty
                    swap_successful = self.board.swap_pieces(dragging_piece_current_grid_pos, current_grid_pos)

                    if swap_successful:
                        # If swap was successful, the piece object previously at dragging_piece_current_grid_pos
                        # is now at current_grid_pos. self.dragging_piece needs to reference this object.
                        # This is the crucial step that transfers the identity of the "held" piece during drag.
                        # The piece object that *was* self.dragging_piece before the swap is now at dragging_piece_current_grid_pos.
                        self.dragging_piece = self.board.grid[current_r][current_c]

                        # Update the last processed grid position to the position where the swap just occurred
                        self.last_processed_grid_pos = current_grid_pos # Update record

                        # Completion check after each swap is already triggered in board.swap_pieces.
                        # self.board.check_and_process_completion()

                    # If swap failed (e.g., Board state suddenly disallowed), last_processed_grid_pos is not updated.
                else:
                     # Mouse is moving within the same grid cell as the last processed one (even while dragging).
                     # No swap is triggered. last_processed_grid_pos remains unchanged.
                     pass # No action needed

    def _handle_click_swap(self, clicked_piece, grid_pos):
        """Handles click-swap logic."""
        # Board state check already handled in _handle_playing_input.
        # if self.board.current_board_state != settings.BOARD_STATE_PLAYING:
        #      return # Shield input

        if self.board.selected_piece is None:
            # If no piece is currently selected, select the clicked piece
            self.board.select_piece(clicked_piece)
            # print(f"Selected piece: Image ID {clicked_piece.original_image_id}, Original position ({clicked_piece.original_row},{clicked_piece.original_col}), Current position ({grid_pos[0]},{grid_pos[1]})") # Debug
        else:
            # If a piece is already selected
            selected_pos = (self.board.selected_piece.current_grid_row, self.board.selected_piece.current_grid_col)
            # If the clicked piece is different from the selected piece
            if self.board.selected_piece != clicked_piece:
                 # Swap these two pieces
                 print(f"Click swap: ({selected_pos[0]},{selected_pos[1]}) <-> ({grid_pos[0]},{grid_pos[1]})") # Debug
                 swap_successful = self.board.swap_pieces(selected_pos, grid_pos)

                 # After attempting swap, unselect the piece, regardless of whether swap actually occurred (e.g., clicked on itself)
                 self.board.unselect_piece()

                 # If swap was successful, check for completed picture (already triggered in board.swap_pieces)
                 # if swap_successful:
                 #      self.board.check_and_process_completion()
            else:
                 # If the same selected piece is clicked, unselect it
                 # print("Unselecting piece.") # Debug
                 self.board.unselect_piece()