# input_handler.py
# 负责处理用户输入 (鼠标点击、拖拽等) 并转换为游戏动作

import pygame
import sys
import settings
from utils import screen_to_grid # 导入工具函数
# from board import Board # 需要导入Board类来操作拼盘
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

        self.dragging_piece = None # 当前正在被拖拽的 Piece 对象
        self.drag_start_grid_pos = (-1, -1) # 拖拽开始时，该碎片所在的网格位置
        self.last_processed_grid_pos = (-1, -1) # 拖拽过程中，鼠标上一次所在的网格位置

        # 定义一个阈值，鼠标移动超过这个距离就判定为拖拽
        self.DRAG_THRESHOLD = 5 # 像素


    def handle_event(self, event):
        """处理单个Pygame事件"""
        # 首先处理那些与游戏状态无关的事件，比如退出
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # 根据当前游戏状态，将事件分发给对应的处理逻辑
        if self.game.current_state == settings.GAME_STATE_PLAYING:
            # 处理主游戏界面的输入
            self._handle_playing_input(event)
        # elif self.game.current_state == settings.GAME_STATE_GALLERY_LIST:
            # 事件交给 Gallery 类处理列表视图逻辑
            # self.game.gallery.handle_event_list(event)
        # elif self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # 事件交给 Gallery 类处理大图查看逻辑
            # self.game.gallery.handle_event_view_lit(event)


    def _handle_playing_input(self, event):
        """处理游戏进行中状态下的输入事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 左键点击
                self._handle_mouse_down(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: # 左键释放
                self._handle_mouse_up(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event.pos)
        # TODO: 添加其他输入事件处理，如按键（如果需要暂停、提示等）


    def _handle_mouse_down(self, mouse_pos):
        """处理鼠标左键按下事件"""
        self.mouse_down_pos = mouse_pos # 记录按下时的鼠标位置

        # 检查是否点击了图库图标 (只有在PLAYING状态下才能点击图库入口)
        if self.game.current_state == settings.GAME_STATE_PLAYING and self.game.gallery_icon_rect and self.game.gallery_icon_rect.collidepoint(mouse_pos):
             print("点击了图库图标!") # 调试信息
             # TODO: 确保 Gallery 模块和 change_state 方法已实现并正确导入
             # self.game.change_state(settings.GAME_STATE_GALLERY_LIST) # 切换到图库列表状态
             return # 事件已被消耗，不再处理拼盘点击

        # 将像素坐标转换为网格坐标
        grid_pos = screen_to_grid(mouse_pos)
        r, c = grid_pos

        # 检查点击位置是否在拼盘范围内
        if not (0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS):
            # 点击在拼盘外，并且不是UI元素
            # 如果当前有选中的碎片 (点击交换模式下)，点击空白区域取消选中
            if self.board.selected_piece:
                 self.board.unselect_piece() # 通知board取消选中
            return

        # 点击位置在拼盘范围内
        clicked_piece = self.board.grid[r][c]

        if clicked_piece:
            # 如果点击位置有碎片，标记可能开始拖拽
            # 真正的拖拽状态在 MOUSEMOTION 中根据鼠标移动距离来判断是否开始
            self.dragging_piece = clicked_piece
            self.drag_start_grid_pos = (r, c)
            self.last_processed_grid_pos = (r, c) # 记录拖拽开始时的网格位置

            # 注意：在这里不立即调用 board.start_dragging 或 select_piece
            # 等待 MOUSEMOTION 或 MOUSEBUTTONUP 来确定是拖拽还是点击


        else:
            # 如果点击位置没有碎片，并且当前有选中的碎片 (点击交换模式下)，则取消选中
            if self.board.selected_piece:
                 self.board.unselect_piece()
            # 如果没有选中的碎片，点击空位不触发任何操作


    def _handle_mouse_up(self, mouse_pos):
        """处理鼠标左键释放事件"""
        # 计算鼠标按下和释放位置的距离
        click_distance = math.dist(self.mouse_down_pos, mouse_pos)

        grid_pos = screen_to_grid(mouse_pos)
        r, c = grid_pos

        if self.is_dragging:
            # 如果正在拖拽中释放鼠标
            self.is_dragging = False
            if self.dragging_piece:
                self.board.stop_dragging() # 通知board停止拖拽状态
                # 拖拽过程中的交换已经在 handle_mouse_motion 中处理了。
                # 这里不再进行额外的交换。
                # 拖拽结束后检查是否有图片完成
                # self.board.check_and_process_completion() # 如果每次交换后检查了，这里就不需要再检查

            self.dragging_piece = None # 清除拖拽中的碎片引用
            self.drag_start_grid_pos = (-1, -1)
            self.last_processed_grid_pos = (-1, -1) # 清除拖拽状态变量


        # 如果不是拖拽 (鼠标移动距离小于阈值)，这是一个单纯的点击
        elif click_distance < self.DRAG_THRESHOLD:
             # 这是一个点击事件
             # 检查点击位置是否在拼盘范围内进行点击交换处理
            if 0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS:
                 # 如果点击位置有碎片
                 clicked_piece = self.board.grid[r][c]
                 if clicked_piece:
                      self._handle_click_swap(clicked_piece, grid_pos)
                 else:
                      # 如果点击位置没有碎片，并且当前有选中的碎片，取消选中
                      if self.board.selected_piece:
                           self.board.unselect_piece()
            else:
                 # 点击在拼盘外
                 if self.board.selected_piece:
                      self.board.unselect_piece() # 点击空白区域取消选中


        # 重置鼠标按下位置记录
        self.mouse_down_pos = (-1, -1)


    def _handle_mouse_motion(self, mouse_pos):
        """处理鼠标移动事件"""
        # 如果鼠标左键没有按下，不处理移动事件
        if not pygame.mouse.get_pressed()[0]:
             self.is_dragging = False # 确保在鼠标松开但在区域外时停止拖拽状态
             self.dragging_piece = None
             self.drag_start_grid_pos = (-1, -1)
             self.last_processed_grid_pos = (-1, -1)
             return


        # 检查是否应该开始拖拽 (如果在碎片上按下，并且鼠标移动超过阈值)
        if not self.is_dragging and self.dragging_piece and self.mouse_down_pos != (-1, -1):
             move_distance = math.dist(self.mouse_down_pos, mouse_pos)
             if move_distance >= self.DRAG_THRESHOLD:
                 # 移动距离超过阈值，正式进入拖拽状态
                 self.is_dragging = True
                 print(f"开始正式拖拽，起始网格: {self.drag_start_grid_pos}") # 调试信息
                 # 通知board该碎片正在被拖拽 (用于可能的视觉效果)
                 self.board.start_dragging(self.dragging_piece)

                 # 如果之前有选中的碎片 (点击交换模式)，取消选中
                 if self.board.selected_piece:
                      self.board.unselect_piece()


        # 如果已经处于拖拽状态
        if self.is_dragging and self.dragging_piece:
            current_grid_pos = screen_to_grid(mouse_pos) # 获取鼠标当前所在的网格位置
            r, c = current_grid_pos

            # 检查当前网格位置是否在板子上，并且与上一次处理的位置不同
            if (0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS and
                current_grid_pos != self.last_processed_grid_pos):

                # 当前鼠标下的网格位置
                target_piece = self.board.grid[r][c]

                # 如果目标位置有碎片，则与拖拽中的碎片进行交换
                if target_piece:
                    # 获取拖拽中碎片当前所在的网格位置
                    dragging_piece_current_pos = (self.dragging_piece.current_grid_row, self.dragging_piece.current_grid_col)

                    # 只有当拖拽中的碎片和目标位置的碎片都存在时才进行交换
                    if self.dragging_piece and target_piece:
                        # print(f"拖拽交换: ({dragging_piece_current_pos[0]},{dragging_piece_current_pos[1]}) <-> ({r},{c})") # 调试信息
                        self.board.swap_pieces(dragging_piece_current_pos, current_grid_pos)

                        # 交换后，拖拽中的 piece 对象（现在是 target_piece）已经去了 dragging_piece_current_pos
                        # 原来的 dragging_piece (现在是 piece1) 去了 current_grid_pos
                        # 需要更新 self.dragging_piece 引用到新的“被手持”的碎片对象
                        # 最简单的做法是：如果交换成功，现在 grid[r][c] 应该是那个我们“开始拖拽”的原始对象
                        self.dragging_piece = self.board.grid[r][c] # 交换后，原先拖拽的碎片现在在目标位置了

                        # 更新上一次处理的网格位置为刚刚进行交换的位置
                        self.last_processed_grid_pos = current_grid_pos # 更新记录

                        # 每次交换后立即检查是否有图片完成
                        self.board.check_and_process_completion()

                    # TODO: 如果需要拖拽时碎片跟随鼠标移动的视觉效果，在这里更新 self.dragging_piece.rect 的位置
                    # self.dragging_piece.rect.center = mouse_pos # 示例：让碎片中心跟随鼠标


    def _handle_click_swap(self, clicked_piece, grid_pos):
        """处理点击交换逻辑"""
        if self.board.selected_piece is None:
            # 如果当前没有选中的碎片，则选中当前点击的碎片
            self.board.select_piece(clicked_piece)
            # print(f"选中碎片: 图片ID {clicked_piece.original_image_id}, 原始位置 ({clicked_piece.original_row},{clicked_piece.original_col}), 当前位置 ({grid_pos[0]},{grid_pos[1]})") # 调试信息
        else:
            # 如果已有选中的碎片
            selected_pos = (self.board.selected_piece.current_grid_row, self.board.selected_piece.current_grid_col)
            # 如果点击的是另一个碎片
            if self.board.selected_piece != clicked_piece:
                 # 交换这两个碎片
                 print(f"点击交换: ({selected_pos[0]},{selected_pos[1]}) <-> ({grid_pos[0]},{grid_pos[1]})") # 调试信息
                 self.board.swap_pieces(selected_pos, grid_pos)
                 # 交换完成后，取消选中状态
                 self.board.unselect_piece()
                 # 交换后检查是否有图片完成
                 self.board.check_and_process_completion()
            else:
                 # 如果点击的是同一个已选中碎片，则取消选中
                 # print("取消选中碎片。") # 调试信息
                 self.board.unselect_piece()


    # TODO: 辅助函数，将鼠标像素位置转换为 Board 网格位置，可能放在 utils 中更合适
    # def _get_grid_pos_from_mouse_pos(self, mouse_pos): pass