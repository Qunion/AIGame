# board.py
# 管理拼盘的状态、碎片布局、交换、完成检测、动态填充及动画

from ast import Return
import pygame
import settings
import random # 用于随机打乱碎片
import time # 用于计时
from piece import Piece # 导入Piece类
# from image_manager import ImageManager # image_manager 在 __init__ 中传入了
# from main import Game # Board 可能需要 Game 实例来触发状态改变 (如图片完成提示)
import utils # 导入工具函数


class Board:
    def __init__(self, image_manager):
        """
        初始化拼盘

        Args:
            image_manager (ImageManager): 图像管理器实例
            # game_instance (Game): Game实例，用于触发事件或状态改变 (例如显示提示或切换图库状态) - 通过ImageManager间接访问
        """
        self.image_manager = image_manager
        # self.game = game_instance # 持有Game实例引用，用于调用Game方法

        # 存储拼盘中的碎片，使用二维列表表示物理网格 (16x9)
        # 列表中的元素将是 Piece 对象或 None (表示空槽位)
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]

        # 获取初始碎片并填充到拼盘
        self.fill_initial_pieces()

        # 选中的碎片 (用于点击交换)
        self.selected_piece = None

        # 正在拖拽的碎片
        self.dragging_piece = None

        # 选中碎片的视觉反馈 Rect (直接绘制即可，不与碎片对象关联)
        self.selection_rect = None

        # Board内部状态，管理完成 -> 移除 -> 下落 -> 填充流程
        self.current_board_state = settings.BOARD_STATE_PLAYING
        self._completed_image_id_pending_process = None # 完成的图片ID，等待处理
        self._completed_area_start_pos = None # 已完成区域的左上角网格位置

        # 用于管理所有 Piece Sprite 的 Group
        self.all_pieces_group = pygame.sprite.Group()
        # 将所有初始碎片添加到 Group
        for r in range(settings.BOARD_ROWS):
            for c in range(settings.BOARD_COLS):
                if self.grid[r][c]:
                    self.all_pieces_group.add(self.grid[r][c])

        # 动画完成后的回调队列 (当下落动画完成后，需要触发填充等后续流程)
        self._animation_completion_callbacks = []


    def fill_initial_pieces(self):
        """根据settings填充初始碎片并随机打乱"""
        initial_pieces = self.image_manager.get_initial_pieces_for_board()

        # 确保获取到的碎片数量符合预期
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS
        if len(initial_pieces) != total_required_pieces:
             print(f"错误: 获取的初始碎片数量 {len(initial_pieces)} 与预期 {total_required_pieces} 不符。无法填充拼盘。")
             # 如果数量不匹配，清空grid，避免后续错误
             self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
             self.all_pieces_group.empty() # 清空Sprite Group
             # TODO: 填充一些空白或错误提示碎片
             return # 碎片数量不匹配，停止填充

        print(f"获取了 {len(initial_pieces)} 个初始碎片，开始填充拼盘。") # 调试信息

        # 生成所有网格位置的列表
        all_grid_positions = [(r, c) for r in range(settings.BOARD_ROWS) for c in range(settings.BOARD_COLS)]
        # 随机打乱位置列表
        random.shuffle(all_grid_positions)

        # 将每个碎片放置到一个随机的网格位置上
        for i, piece in enumerate(initial_pieces):
            # 获取一个随机的网格位置
            r, c = all_grid_positions[i]

            # 将碎片放到网格中
            self.grid[r][c] = piece
            # 更新碎片自身的当前网格位置和屏幕位置 (非动画)
            piece.set_grid_position(r, c, animate=False)

            # self.all_pieces_group.add(piece) # 在__init__末尾统一添加


    def swap_pieces(self, pos1_grid, pos2_grid):
        """
        交换两个网格位置上的碎片。
        只会交换在 BOARD_STATE_PLAYING 状态下。

        Args:
            pos1_grid (tuple): 第一个碎片的网格坐标 (row, col)
            pos2_grid (tuple): 第二个碎片的网格坐标 (row, col)

        Returns:
            bool: True 如果交换成功，False 如果交换失败或当前Board状态不允许交换。
        """
        # 只有在 PLAYING 状态下才能交换碎片
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             # print("警告: Board 当前状态不允许交换碎片。") # 频繁打印可能影响性能
             return False

        r1, c1 = pos1_grid
        r2, c2 = pos2_grid

        # 确保坐标有效且在板子上
        if not (0 <= r1 < settings.BOARD_ROWS and 0 <= c1 < settings.BOARD_COLS and
                0 <= r2 < settings.BOARD_ROWS and 0 <= c2 < settings.BOARD_COLS):
            # print(f"警告: 无效的网格位置 ({r1},{c1}) 或 ({r2},{c2})，无法交换。")
            return False # 交换失败

        piece1 = self.grid[r1][c1]
        piece2 = self.grid[r2][c2]

        # 检查至少有一个位置不是 None，否则交换没有意义
        if piece1 is None and piece2 is None:
             # print(f"警告: 交换位置 ({r1},{c1}) 和 ({r2},{c2}) 都为空槽位，不进行交换。")
             return False # 交换失败

        # 在网格中交换
        self.grid[r1][c1] = piece2
        self.grid[r2][c2] = piece1

        # 更新碎片自身的网格位置属性 (非动画方式，因为这是瞬间交换)
        if piece1:
            piece1.set_grid_position(r2, c2, animate=False)
        if piece2:
            piece2.set_grid_position(r1, c1, animate=False)

        # print(f"交换了碎片位置: ({r1},{c1}) 与 ({r2},{c2})") # 调试信息，频繁交换时打印信息太多

        # 交换成功后立即检查是否有图片完成
        self.check_and_process_completion()

        return True # 交换成功


    def select_piece(self, piece):
        """选中一个碎片 (用于点击交换模式)"""
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return # 只在PLAYING状态下允许选中

        if self.selected_piece:
             # 如果已经有选中的，先取消上一个的选中状态
             self.unselect_piece()

        self.selected_piece = piece
        # 计算选中高亮框的位置和大小，直接使用碎片的rect
        # 使用 inflate 和 topleft 计算边框位置
        border_thickness = 5 # 和 draw 中的一致
        self.selection_rect = piece.rect.inflate(border_thickness * 2, border_thickness * 2)
        self.selection_rect.topleft = (piece.rect.left - border_thickness, piece.rect.top - border_thickness)

        # print(f"选中碎片: 图片ID {piece.original_image_id}, 原始位置 ({piece.original_row},{piece.original_col}), 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def unselect_piece(self):
        """取消选中状态"""
        self.selected_piece = None
        self.selection_rect = None # 移除选中高亮框
        # print("取消选中碎片。") # 调试信息


    def start_dragging(self, piece):
        """开始拖拽一个碎片"""
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return # 只在PLAYING状态下允许拖拽

        self.dragging_piece = piece
        # 将正在拖拽的碎片从 Group 中移除，以便单独绘制它在最上层
        if self.dragging_piece in self.all_pieces_group:
             self.all_pieces_group.remove(self.dragging_piece)

        # print(f"开始拖拽碎片: 图片ID {piece.original_image_id}, 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def stop_dragging(self):
        """停止拖拽"""
        if self.dragging_piece:
            # print(f"停止拖拽碎片: 图片ID {self.dragging_piece.original_image_id}, 当前位置 ({self.dragging_piece.current_grid_row},{self.dragging_piece.current_grid_col})") # 调试信息
            # 将碎片放回其当前网格位置的精确屏幕坐标 (如果拖拽时位置有偏移的话)
            current_grid_pos = (self.dragging_piece.current_grid_row, self.dragging_piece.current_grid_col)
            self.dragging_piece.set_grid_position(current_grid_pos[0], current_grid_pos[1], animate=False) # 停止拖拽瞬间归位

            # 将碎片加回 Sprite Group
            if self.dragging_piece not in self.all_pieces_group:
                 self.all_pieces_group.add(self.dragging_piece)

            self.dragging_piece = None


    def check_and_process_completion(self):
        """
        检查是否有图片完成，如果完成则触发处理流程。
        只在 BOARD_STATE_PLAYING 状态下执行检查。
        如果检测到完成，改变 Board 内部状态到 BOARD_STATE_PICTURE_COMPLETED。
        """
        if self.current_board_state != settings.BOARD_STATE_PLAYING:
             return False # 只在PLAYING状态下检查

        completed_image_id = self.check_completion()
        if completed_image_id is not None:
            print(f"检测到图片 {completed_image_id} 完成了！触发处理流程。") # 调试信息

            # 设置 Board 内部状态为图片完成，等待处理
            self.current_board_state = settings.BOARD_STATE_PICTURE_COMPLETED
            self._completed_image_id_pending_process = completed_image_id
            # self._completed_area_start_pos 已在 check_completion 中记录

            # 停止当前可能的交互 (取消选中，停止拖拽)
            self.unselect_piece()
            self.stop_dragging() # 这会把碎片归位

            # 通知 ImageManager 更新图片状态并记录完成时间 (在这里通知，因为完成了)
            self.image_manager.set_image_state(completed_image_id, 'lit')

            # TODO: 可以在这里触发一个全局的游戏事件，比如播放音效，显示祝贺信息等
            # 可以通过 ImageManager 间接访问 Game 实例来调用 Game 的方法
            # if hasattr(self.image_manager.game, 'show_completion_effect'):
            #     self.image_manager.game.show_completion_effect(completed_image_id)

            return True # 有图片完成
        return False # 没有图片完成


    def check_completion(self):
        """
        检查拼盘中是否存在一个完整的 5x9 图片块。
        返回已完成的图片ID，如果没有则返回None。
        如果找到，记录完成区域的左上角位置在 self._completed_area_start_pos。
        """
        # 遍历所有可能的 5x9 块的左上角起始点
        # 物理板子是 9行 x 16列
        # 逻辑图片是 5行 x 9列
        # 起始行的范围: 从 0 到 BOARD_ROWS - IMAGE_LOGIC_ROWS (9 - 5 = 4)。所以是 0, 1, 2, 3, 4
        # 起始列的范围: 从 0 到 BOARD_COLS - IMAGE_LOGIC_COLS (16 - 9 = 7)。所以是 0, 1, 2, 3, 4, 5, 6, 7
        for start_row in range(settings.BOARD_ROWS - settings.IMAGE_LOGIC_ROWS + 1):
            for start_col in range(settings.BOARD_COLS - settings.IMAGE_LOGIC_COLS + 1):

                # 获取该 5x9 区域左上角的碎片
                top_left_piece = self.grid[start_row][start_col]

                # 如果左上角没有碎片，或者碎片的原始位置不是逻辑上的 (0,0)，则不可能从这里开始一个完整的图片
                if top_left_piece is None or top_left_piece.original_row != 0 or top_left_piece.original_col != 0:
                    continue # 检查下一个可能的起始位置

                # 确定要检查的图片ID
                target_image_id = top_left_piece.original_image_id
                is_complete = True # 假设这个区域是一个完整的图片块

                # 遍历这个 5x9 区域内的所有位置 (相对于起始点的偏移 dr, dc)
                for dr in range(settings.IMAGE_LOGIC_ROWS): # 0 to 4
                    for dc in range(settings.IMAGE_LOGIC_COLS): # 0 to 8
                        current_row = start_row + dr
                        current_col = start_col + dc
                        # 确保在板子范围内检查
                        if not (0 <= current_row < settings.BOARD_ROWS and 0 <= current_col < settings.BOARD_COLS):
                            is_complete = False # 区域超出版子范围 (理论上不会发生，因为外层循环已限制)
                            break
                        current_piece = self.grid[current_row][current_col]

                        # 检查当前位置是否有碎片
                        if current_piece is None:
                            is_complete = False
                            break # 该块不完整，跳出内层循环

                        # 检查碎片的原始信息是否与目标图片ID和预期的原始位置匹配
                        if (current_piece.original_image_id != target_image_id or
                            current_piece.original_row != dr or
                            current_piece.original_col != dc):
                            is_complete = False
                            break # 信息不匹配，该块不完整，跳出内层循环

                    if not is_complete:
                        break # 如果内层循环发现不完整，跳出外层循环

                # 如果内层循环都通过，说明找到了一个完整的图片块
                if is_complete:
                    # 在返回图片ID之前，先记录这个完成的区域，以便后续移除
                    self._completed_area_start_pos = (start_row, start_col)
                    return target_image_id # 返回完成的图片ID

        return None # 遍历所有可能位置后没有找到完整的图片


    def _process_completed_picture(self):
        """
        处理已完成图片的流程状态机。
        根据 current_board_state 执行相应的步骤。
        这个方法在 Board 的 update 中被调用。
        """
        if self.current_board_state == settings.BOARD_STATE_PICTURE_COMPLETED:
            # 状态：图片已检测完成，刚进入处理流程
            print(f"Board State: PICTURE_COMPLETED -> REMOVING_PIECES for image {self._completed_image_id_pending_process}") # 调试信息
            self.current_board_state = settings.BOARD_STATE_REMOVING_PIECES
            # 移除碎片 (瞬间完成)
            self.remove_completed_pieces()
            # 移除完成后，立即切换到下落状态并启动下落动画
            self.current_board_state = settings.BOARD_STATE_PIECES_FALLING
            self.initiate_fall_down_pieces()


        elif self.current_board_state == settings.BOARD_STATE_PIECES_FALLING:
             # 状态：碎片正在下落动画中
             # 碎片下落动画的更新由 Piece 的 update 方法处理，并在 Board 的 update 中调用 group.update
             # 在 Board 的 update 方法中会检查是否所有碎片都已停止下落，并切换到 PENDING_FILL 状态
             return # 等待下落动画完成


        elif self.current_board_state == settings.BOARD_STATE_PENDING_FILL:
            # 状态：碎片下落完成，等待填充
            print("Board State: PENDING_FILL -> PLAYING (after fill)") # 调试信息
            # 填充新碎片 (瞬间完成)
            self.fill_new_pieces()

            # 清理完成图片的记录
            self._completed_image_id_pending_process = None
            self._completed_area_start_pos = None

            # 填充完成后，切换回 PLAYING 状态
            self.current_board_state = settings.BOARD_STATE_PLAYING

            # TODO: 通知 Game 或 Gallery 图库需要刷新 (Board不能直接访问Gallery，通过Game间接通知)
            if hasattr(self.image_manager.game, 'gallery'): # 检查Game实例是否有gallery属性
                print("通知 Gallery 更新列表...") # Debug
                self.image_manager.game.gallery._update_picture_list() # 直接调用更新方法



    def remove_completed_pieces(self):
        """根据记录的 _completed_area_start_pos，从拼盘中移除已完成图片的碎片"""
        if self._completed_area_start_pos is None or self._completed_image_id_pending_process is None:
             print("错误: 没有记录已完成区域或图片ID，无法移除碎片。")
             return

        start_row, start_col = self._completed_area_start_pos
        completed_image_id = self._completed_image_id_pending_process
        # print(f"移除图片 {completed_image_id} 在 ({start_row},{start_col}) 开始的 5x9 区域碎片...") # Debug

        pieces_to_remove_list = [] # 收集要移除的碎片对象

        for dr in range(settings.IMAGE_LOGIC_ROWS):
            for dc in range(settings.IMAGE_LOGIC_COLS):
                r = start_row + dr
                c = start_col + dc
                # 确保坐标在板子范围内
                if 0 <= r < settings.BOARD_ROWS and 0 <= c < settings.BOARD_COLS:
                    piece_to_remove = self.grid[r][c]
                    # 再次检查碎片是否属于当前完成的图片 (安全检查)
                    if piece_to_remove and piece_to_remove.original_image_id == completed_image_id and \
                       piece_to_remove.original_row == dr and piece_to_remove.original_col == dc:
                         pieces_to_remove_list.append(piece_to_remove)
                         self.grid[r][c] = None # 将网格位置设为 None
                    # else:
                         # print(f"警告: 尝试移除的区域 ({r},{c}) 没有属于完成图片 {completed_image_id} 的碎片或为空。") # Debug

        # 从 Sprite Group 中移除收集到的碎片
        self.all_pieces_group.remove(*pieces_to_remove_list)
        # TODO: 可以添加一个效果，让移除的碎片消失或爆炸等 (可选)


    def initiate_fall_down_pieces(self):
        """启动碎片下落动画：计算所有碎片的最终目标位置，并标记它们为正在下落"""
        # print("启动碎片下落动画...") # Debug
        # 遍历每一列，确定每个非空碎片的最终下落位置
        for c in range(settings.BOARD_COLS): # 遍历每一列
            bottom_row_index_to_fill = settings.BOARD_ROWS - 1 # 当前列底部可以填充的行索引

            # 从底向上遍历当前列
            pieces_in_column = [] # 临时存储本列非空碎片
            for r in range(settings.BOARD_ROWS - 1, -1, -1):
                if self.grid[r][c]:
                     pieces_in_column.append(self.grid[r][c])
                     self.grid[r][c] = None # 先将原位置设为None

            # 从底向上重新放置收集到的碎片，并启动下落动画
            current_row = settings.BOARD_ROWS - 1
            for piece in pieces_in_column:
                 self.grid[current_row][c] = piece
                 # 更新碎片的网格位置并启动下落动画到新的屏幕Y坐标
                 piece.set_grid_position(current_row, c, animate=True)
                 current_row -= 1

        # 动画的实际更新由各个 Piece 的 update 方法处理，并在 Board 的 update 方法中调用 Sprite Group 的 update


    def is_any_piece_falling(self):
        """检查是否有任何碎片正在下落动画中"""
        # 遍历 Sprite Group 中的所有碎片，检查 is_falling 属性
        for piece in self.all_pieces_group:
             if piece.is_falling:
                 return True
        return False


    def fill_new_pieces(self):
        """根据填充规则，从 image_manager 获取新碎片填充顶部空位"""
        # print("触发填充新碎片...") # Debug
        # 统计有多少个空槽位需要填充 (即网格中为 None 的位置)
        empty_slots_positions = [] # 记录空槽位的位置 (从上往下，从左往右遍历获取)
        for r in range(settings.BOARD_ROWS):
            for c in range(settings.BOARD_COLS):
                if self.grid[r][c] is None:
                     empty_slots_positions.append((r, c)) # 记录空位位置

        empty_slots_count = len(empty_slots_positions)
        # print(f"检测到 {empty_slots_count} 个空槽位需要填充。") # Debug

        if empty_slots_count == 0:
             # print("没有空槽位需要填充。")
             return

        # 从 ImageManager 获取相应数量的新碎片
        new_pieces = self.image_manager.get_next_fill_pieces(empty_slots_count)
        # print(f"ImageManager 提供了 {len(new_pieces)} 个新碎片。") # Debug

        # 将新碎片放置到空槽位中
        for i, piece in enumerate(new_pieces):
             if i < len(empty_slots_positions):
                 r, c = empty_slots_positions[i]
                 self.grid[r][c] = piece
                 # 将新碎片放置到其目标网格位置 (非动画，瞬间出现)
                 piece.set_grid_position(r, c, animate=False)
                 # 将新碎片添加到 Sprite Group
                 self.all_pieces_group.add(piece)
             else:
                 print(f"警告: 有多余的新碎片 ({len(new_pieces)} 个) 但没有足够的空槽位 ({empty_slots_count} 个) 来放置。")
                 break # 没有更多空槽位了

        if len(new_pieces) < empty_slots_count:
            print(f"警告: 需要 {empty_slots_count} 个碎片，但 ImageManager 只提供了 {len(new_pieces)} 个。拼盘将会有空位。")


    def draw(self, surface):
        """在指定的surface上绘制拼盘中的所有碎片和选中效果"""
        # 绘制所有非拖拽中的碎片
        # 使用 Sprite Group 的 draw 方法绘制所有碎片，除了正在拖拽的那个
        # 先将拖拽碎片临时从 group 中移除，绘制完 group 后再绘制拖拽碎片，确保其在最上层
        if self.dragging_piece and self.dragging_piece in self.all_pieces_group:
             self.all_pieces_group.remove(self.dragging_piece)

        self.all_pieces_group.draw(surface)

        # 绘制选中碎片的特殊效果 (例如绘制边框)
        if self.selection_rect:
             # 确保选中高亮框的位置与选中碎片 rect 同步
             if self.selected_piece:
                 border_thickness = 5
                 self.selection_rect.topleft = (self.selected_piece.rect.left - border_thickness, self.selected_piece.rect.top - border_thickness)
             pygame.draw.rect(surface, settings.HIGHLIGHT_COLOR, self.selection_rect, 5) # 绘制边框，最后一个参数是线条宽度


        # 在最后绘制正在拖拽的碎片，使其显示在最上层
        if self.dragging_piece:
             # InputHandler 会在 MOUSEMOTION 中实时更新 dragging_piece.rect 的位置
             self.dragging_piece.draw(surface)

        # 绘制完成后，将拖拽碎片加回 group
        if self.dragging_piece and self.dragging_piece not in self.all_pieces_group:
             self.all_pieces_group.add(self.dragging_piece)


    def update(self, dt):
         """
         更新Board的状态，包括处理完成流程和碎片下落动画。

         Args:
             dt (float): 自上一帧以来的时间（秒）
         """
         # 如果 Board 状态不是 PLAYING，则调用 _process_completed_picture 处理状态机
         if self.current_board_state != settings.BOARD_STATE_PLAYING:
             self._process_completed_picture() # 处理完成流程状态机

         # 更新所有碎片的动画 (特别是正在下落的碎片)
         # 即使 Board 状态不是 FALLING，也需要更新，因为 Board 可能会在 PLAYING 状态下突然切换到 FALLING
         # 碎片 Piece 的 update 方法会根据自身的 is_falling 属性决定是否移动
         self.all_pieces_group.update(dt)

         # 如果 Board 状态是 FALLING，检查是否所有碎片都已停止下落，然后切换状态
         if self.current_board_state == settings.BOARD_STATE_PIECES_FALLING:
              if not self.is_any_piece_falling():
                   print("所有碎片下落完成。状态切换到 PENDING_FILL。") # Debug
                   self.current_board_state = settings.BOARD_STATE_PENDING_FILL # 切换状态，等待填充


    def get_piece_at_grid(self, row, col):
         """获取指定网格位置的碎片对象，或None"""
         if 0 <= row < settings.BOARD_ROWS and 0 <= col < settings.BOARD_COLS:
             return self.grid[row][col]
         return None # 坐标无效

    # 提供给 InputHandler 用于判断点击或拖拽是否在 Board 区域内
    def get_board_rect(self):
        """返回拼盘区域在屏幕上的Rect"""
        return pygame.Rect(settings.BOARD_OFFSET_X, settings.BOARD_OFFSET_Y,
                           settings.BOARD_COLS * settings.PIECE_SIZE,
                           settings.BOARD_ROWS * settings.PIECE_SIZE)

    # def _update_falling_pieces(self, dt): ... (已整合到 all_pieces_group.update)