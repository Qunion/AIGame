# input_handler.py
# 负责处理用户输入 (鼠标点击、拖拽等) 并转换为游戏动作

import pygame
import sys
import settings
# 修改导入语句
import utils  # 替代 from utils import screen_to_grid
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
        self.mouse_down_grid_pos = (-1, -1) # 记录鼠标按下时的网格位置

        self.dragging_piece = None # 当前正在被拖拽的 Piece 对象 (引用 Board.dragging_piece)
        self.drag_start_grid_pos = (-1, -1) # 拖拽开始时，该碎片所在的网格位置

        # 拖拽时碎片的视觉偏移量 (如果需要碎片中心不完全跟随鼠标，但目前是完全跟随)
        # self.drag_offset_from_center = (0, 0)

        self.last_processed_grid_pos = (-1, -1) # 拖拽过程中，鼠标上一次进行交换或检查的网格位置


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
        elif self.game.current_state == settings.GAME_STATE_GALLERY_LIST:
            # 事件交给 Gallery 类处理列表视图逻辑
            if hasattr(self.game, 'gallery') and self.game.gallery:
                 # 只有当事件发生在图库窗口区域时才处理？或者 Gallery 自己判断？ Gallery 自己判断更灵活。
                 handled = self.game.gallery.handle_event_list(event)
                 # 如果 Gallery 处理了事件 (例如点击外部区域关闭图库)，则不再继续处理
                 # if handled:
                 #      return
        elif self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
            # 事件交给 Gallery 类处理大图查看逻辑
            if hasattr(self.game, 'gallery') and self.game.gallery:
                 handled = self.game.gallery.handle_event_view_lit(event)
                 # if handled:
                 #      return
        # else: # LOADING 状态下，只处理退出事件，其他忽略


    def _handle_playing_input(self, event):
        """处理游戏进行中状态下的输入事件"""
        # 在 Board 正在处理完成流程（移除、下落、填充）时，禁止玩家操作
        if self.board.current_board_state != settings.BOARD_STATE_PLAYING:
            # ... (处理 mouse up 清理状态的逻辑保持不变) ...
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._handle_mouse_up(event) # <-- 将 event 传递进去
            return # 屏蔽输入


        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 左键点击
                self._handle_mouse_down(event) # <-- 将 event 传递进去
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: # 左键释放
                self._handle_mouse_up(event) # <-- 将 event 传递进去
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event) # <-- 将 event 传递进去


    # def _handle_mouse_down(self, mouse_pos):
    def _handle_mouse_down(self, event): # <-- 新的方法签名
        """处理鼠标左键按下事件"""
        # event 参数现在包含了 pos 和 button 等信息
        mouse_pos = event.pos # <-- 从 event 中获取 mouse_pos

        # 在 Board 正在处理完成流程时，已经在 _handle_playing_input 中检查并返回了，这里无需重复检查
        # if self.board.current_board_state != settings.BOARD_STATE_PLAYING:
        #     return

        self.mouse_down_pos = mouse_pos # 记录按下时的鼠标像素位置

        # 检查是否点击了图库图标按钮
        if hasattr(self.game, 'gallery_icon_button') and self.game.gallery_icon_button:
            # 将完整的 event 对象传递给按钮处理
            # Button.handle_event 会检查是否点击，并执行回调
            # 如果 Button 处理了事件，返回 True
            # 我們在這裡只關心 MouseButtonDown 事件 (已在外層篩選)
            # 移除创建 fake_event 和检查 hasattr(event, ...) 的逻辑
            if self.game.gallery_icon_button.handle_event(event): # <-- 将真实的 event 传递给按钮处理
                # 如果图库按钮处理了点击事件，返回，不再处理拼盘逻辑
                # print("图库按钮点击事件已处理。") # Debug
                return # 事件已被消耗

        # 如果点击未被图库按钮处理，则继续处理拼盘点击逻辑
        self.mouse_down_grid_pos = utils.screen_to_grid(mouse_pos) # 记录按下时的网格位置

        # 将像素坐标转换为网格坐标
        grid_pos = utils.screen_to_grid(mouse_pos)
        r, c = grid_pos

        # 检查点击位置是否在拼盘范围内
        if grid_pos == (-1, -1): # 不在拼盘范围内
            # 如果当前有选中的碎片 (点击交换模式下)，点击空白区域取消选中
            if self.board.selected_piece:
                 self.board.unselect_piece() # 通知board取消选中
            return # 点击在拼盘外，不处理

        # 点击位置在拼盘范围内 (grid_pos is valid)
        clicked_piece = self.board.grid[r][c]

        if clicked_piece:
            # 如果点击位置有碎片，标记可能开始拖拽
            # 将点击的碎片赋值给 dragging_piece
            self.dragging_piece = clicked_piece
            self.drag_start_grid_pos = (r, c)
            self.last_processed_grid_pos = (r, c) # 记录拖拽开始时的网格位置，用于后续拖拽交换判断

            # 计算拖拽时的鼠标偏移量 (如果需要让碎片中心不完全跟随鼠标)
            # self.drag_offset_from_center = (mouse_pos[0] - clicked_piece.rect.centerx, mouse_pos[1] - clicked_piece.rect.centery)

            # 注意：在这里不立即调用 board.start_dragging 或 select_piece
            # 等待 MOUSEMOTION (判断拖拽) 或 MOUSEBUTTONUP (判断点击) 来确定具体操作

        else:
            # 如果点击位置没有碎片 (空槽位)
            # 并且当前有选中的碎片 (点击交换模式下)，则取消选中
            if self.board.selected_piece:
                 self.board.unselect_piece()
            # 如果没有选中的碎片，点击空位不触发任何操作


    def _handle_mouse_up(self, event): # <-- 新的方法签名
        """处理鼠标左键释放事件"""
        mouse_pos = event.pos # <-- 从 event 中获取 mouse_pos

        # 如果鼠标按下位置无效，或者 Board 状态不允许操作，不处理后续逻辑
        # 这个检查在 _handle_playing_input 已经处理了 Board 状态，但是 mouse_down_pos 仍然需要检查是否有效
        if self.mouse_down_pos == (-1, -1):
            # ... (清理状态的逻辑保持不变) ...
            self.is_dragging = False # Ensure dragging stops if mouse_down was invalid
            if self.dragging_piece:
                self.board.stop_dragging()
                self.dragging_piece = None
            self.drag_start_grid_pos = (-1, -1)
            self.last_processed_grid_pos = (-1, -1)
            self.mouse_down_grid_pos = (-1, -1) # Ensure mouse_down_grid_pos is also reset
            self.mouse_down_pos = (-1, -1) # Ensure mouse_down_pos is also reset
            return # 无效的 mouse down 状态


        # 计算鼠标按下和释放位置的距离
        click_distance = math.dist(self.mouse_down_pos, mouse_pos)

        # 释放时所在的网格位置
        release_grid_pos = utils.screen_to_grid(mouse_pos)
        release_r, release_c = release_grid_pos


        if self.is_dragging:
            # 如果正在拖拽中释放鼠标
            self.is_dragging = False # 退出拖拽状态

            if self.dragging_piece:
                self.board.stop_dragging() # 通知board停止拖拽状态，碎片归位到其当前网格位置

            # 清除拖拽相关的状态变量
            self.dragging_piece = None
            self.drag_start_grid_pos = (-1, -1)
            self.last_processed_grid_pos = (-1, -1)

            # 拖拽结束后的检查完成已在每次拖拽交换时触发，这里不再重复检查

        # 如果不是拖拽 (鼠标移动距离小于阈值)，这是一个单纯的点击
        elif click_distance < settings.DRAG_THRESHOLD:
             # 这是一个点击事件
             # 检查点击释放位置是否在拼盘范围内进行点击交换处理
            if release_grid_pos != (-1, -1): # 在拼盘范围内
                 # 如果点击释放位置有碎片
                 clicked_piece = self.board.grid[release_r][release_c]
                 if clicked_piece:
                      self._handle_click_swap(clicked_piece, release_grid_pos)
                 else:
                      # 如果点击释放位置没有碎片，并且当前有选中的碎片，取消选中
                      if self.board.selected_piece:
                           self.board.unselect_piece()
            else: # 点击释放位置在拼盘外
                 # 如果当前有选中的碎片，点击拼盘外取消选中
                 if self.board.selected_piece:
                      self.board.unselect_piece()


        # 重置鼠标按下位置记录
        self.mouse_down_pos = (-1, -1)
        self.mouse_down_grid_pos = (-1, -1)


    def _handle_mouse_motion(self, event):
        """
        处理鼠标移动事件。

        Args:
            event (pygame.event.Event): 鼠标移动事件对象。
        """
        # 确保鼠标左键是按下的，并且 Board 状态允许操作 (拖拽只能在 PLAYING 状态)
        if not pygame.mouse.get_pressed()[0] or self.board.current_board_state != settings.BOARD_STATE_PLAYING:
             # 如果鼠标左键没有按下，或者 Board 状态不允许，并且我们之前处于拖拽状态，需要清理
             if self.is_dragging:
                 # print("Board 状态不允许或鼠标释放，停止拖拽。") # Debug
                 self.board.stop_dragging() # 通知 Board 停止拖拽状态
                 self.is_dragging = False
                 self.dragging_piece = None
                 self.drag_start_grid_pos = (-1, -1)
                 self.last_processed_grid_pos = (-1, -1)
             return # 不处理移动事件

        # 获取当前的鼠标像素位置
        mouse_pos = event.pos

        # 检查是否应该开始拖拽
        # 只有当鼠标左键在 Board 区域某个碎片上按下 (self.dragging_piece 被临时赋值)，
        # 且鼠标移动距离超过阈值时，才进入正式拖拽状态。
        if not self.is_dragging and self.mouse_down_pos != (-1, -1) and self.dragging_piece is not None:
             move_distance = math.dist(self.mouse_down_pos, mouse_pos)
             if move_distance >= settings.DRAG_THRESHOLD:
                 # 移动距离超过阈值，正式进入拖拽状态
                 self.is_dragging = True
                 # print(f"开始正式拖拽，起始网格: {self.drag_start_grid_pos}") # Debug
                 # 通知board该碎片正在被拖拽 (用于可能的视觉效果)
                 self.board.start_dragging(self.dragging_piece) # 调用board的方法启动拖拽状态

                 # 如果之前有选中的碎片 (点击交换模式)，取消选中
                 if self.board.selected_piece:
                      self.board.unselect_piece()

                 # 初始化上一次处理的网格位置为拖拽开始时的网格位置
                 self.last_processed_grid_pos = self.drag_start_grid_pos


        # 如果已经处于拖拽状态
        if self.is_dragging and self.dragging_piece:
            # 更新正在拖拽碎片的屏幕位置，使其中心跟随鼠标
            # 这只是视觉上的跟随，碎片的 current_grid_row/col 和在 grid 数组中的位置只在交换时更新
            self.dragging_piece.rect.center = mouse_pos

            # 获取鼠标当前所在的网格位置
            current_grid_pos = utils.screen_to_grid(mouse_pos)
            current_r, current_c = current_grid_pos

            # 检查当前网格位置是否在板子上，并且与上一次进行交换/处理的位置不同
            # 只有当鼠标移动到 *新* 的网格单元时，才考虑交换
            if (current_grid_pos != (-1, -1) and # 鼠标在板子上
                current_grid_pos != self.last_processed_grid_pos): # 鼠标进入了新的网格单元

                # 获取拖拽中的碎片当前所在的网格位置 (这是它在 grid 数组中的逻辑位置)
                # 注意：这个位置可能会在拖拽过程中因为快速交换而改变
                dragging_piece_current_grid_pos = (self.dragging_piece.current_grid_row, self.dragging_piece.current_grid_col)

                # 只有当鼠标进入的新网格位置与拖拽碎片当前所在的网格位置不同时，才进行交换
                # 理论上，如果我们只在进入新单元时检查，且上一次处理位置更新正确，这个条件总是满足的，但作为安全检查也可以保留
                if current_grid_pos != dragging_piece_current_grid_pos:

                    # 尝试与新位置的碎片进行交换
                    # swap_pieces 方法会处理目标位置是空的情况
                    swap_successful = self.board.swap_pieces(dragging_piece_current_grid_pos, current_grid_pos)

                    if swap_successful:
                        # 交换成功后，拖拽中的 piece 对象（现在是目标位置的那个）已经去了 dragging_piece_current_grid_pos
                        # 而原来的 dragging_piece (现在是 piece1) 去了 current_grid_pos
                        # 我们需要更新 self.dragging_piece 引用到那个去了 current_grid_pos (新位置) 的碎片对象
                        # 这是关键步骤，实现了拖拽过程中“手持”碎片身份的转移
                        self.dragging_piece = self.board.grid[current_r][current_c]

                        # 更新上一次处理的网格位置为刚刚进行交换的位置
                        self.last_processed_grid_pos = current_grid_pos # 更新记录

                        # 每次交换后立即检查是否有图片完成 (已在 board.swap_pieces 中调用)
                        # self.board.check_and_process_completion()

                    # 如果交换失败 (例如 Board 状态突然不允许)，则 last_processed_grid_pos 不更新
                else:
                     # 鼠标在同一个网格内移动（即使是拖拽中），不触发交换。last_processed_grid_pos 保持不变。
                     pass # No action needed if mouse is in the same grid cell as the last processed one


    def _handle_click_swap(self, clicked_piece, grid_pos):
        """处理点击交换逻辑"""
        # 确保 Board 状态允许点击交换 (已在外层 _handle_playing_input 检查)
        # if self.board.current_board_state != settings.BOARD_STATE_PLAYING:
        #      return # 屏蔽输入

        if self.board.selected_piece is None:
            # 如果当前没有选中的碎片，则选中当前点击的碎片
            self.board.select_piece(clicked_piece)
            # print(f"选中碎片: 图片ID {clicked_piece.original_image_id}, 原始位置 ({clicked_piece.original_row},{clicked_piece.original_col}), 当前位置 ({grid_pos[0]},{grid_pos[1]})") # Debug
        else:
            # 如果已有选中的碎片
            selected_pos = (self.board.selected_piece.current_grid_row, self.board.selected_piece.current_grid_col)
            # 如果点击的是另一个碎片
            if self.board.selected_piece != clicked_piece:
                 # 交换这两个碎片
                 print(f"点击交换: ({selected_pos[0]},{selected_pos[1]}) <-> ({grid_pos[0]},{grid_pos[1]})") # Debug
                 swap_successful = self.board.swap_pieces(selected_pos, grid_pos)

                 # 交换完成后，取消选中状态，无论交换是否真的发生 (例如点了自己)
                 self.board.unselect_piece()

                 # 如果交换成功，检查是否有图片完成 (已在 board.swap_pieces 中调用)
                 # if swap_successful:
                 #      self.board.check_and_process_completion()
            else:
                 # 如果点击的是同一个已选中碎片，则取消选中
                 # print("取消选中碎片。") # Debug
                 self.board.unselect_piece()