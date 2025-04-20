# board.py
# 管理拼盘的状态、碎片布局、交换、完成检测及动态填充

import pygame
import settings
import random # 用于随机打乱碎片
from piece import Piece # 导入Piece类
# from image_manager import ImageManager # image_manager 在 __init__ 中传入了
# from main import Game # Board 可能需要 Game 实例来触发状态改变 (如图片完成)
import time # 用于记录完成时间 (可能在Board中触发，然后通知ImageManager)


class Board:
    def __init__(self, image_manager):
        """
        初始化拼盘

        Args:
            image_manager (ImageManager): 图像管理器实例
        """
        self.image_manager = image_manager
        # 存储拼盘中的碎片，使用二维列表表示物理网格 (16x9)
        # 列表中的元素将是 Piece 对象或 None (表示空槽位)
        self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]

        # 获取初始碎片并填充到拼盘
        self.fill_initial_pieces()

        # 选中的碎片 (用于点击交换)
        self.selected_piece = None

        # 正在拖拽的碎片 (用于拖拽交换)
        self.dragging_piece = None

        # 用于管理所有 Piece Sprite 的 Group (如果需要，可以方便绘制和更新)
        # self.all_pieces_group = pygame.sprite.Group() # 暂时不用Sprite Group，手动管理绘制层级
        # 初始化时将所有初始碎片添加到 Group (如果启用的话)
        # for r in range(settings.BOARD_ROWS):
        #     for c in range(settings.BOARD_COLS):
        #         if self.grid[r][c]:
        #             self.all_pieces_group.add(self.grid[r][c])

        # 选中碎片的视觉反馈 Rect (直接绘制即可，不与碎片对象关联)
        self.selection_rect = None


    def fill_initial_pieces(self):
        """根据settings填充初始碎片并随机打乱"""
        initial_pieces = self.image_manager.get_initial_pieces_for_board()

        # 确保获取到的碎片数量符合预期
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS
        if len(initial_pieces) != total_required_pieces:
             print(f"错误: 获取的初始碎片数量 {len(initial_pieces)} 与预期 {total_required_pieces} 不符，无法填充拼盘。请检查图片资源数量或设置。")
             # 如果数量不匹配，清空grid，避免后续错误
             self.grid = [[None for _ in range(settings.BOARD_COLS)] for _ in range(settings.BOARD_ROWS)]
             # 尝试填充一些空白，避免完全空白界面
             # for r in range(settings.BOARD_ROWS):
             #     for c in range(settings.BOARD_COLS):
             #          self.grid[r][c] = Piece(pygame.Surface((settings.PIECE_SIZE, settings.PIECE_SIZE)), -1, -1, -1, r, c) # 填充空白碎片
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
            # 更新碎片自身的当前网格位置和屏幕位置
            piece.set_grid_position(r, c)

            # self.all_pieces_group.add(piece) # 统一在__init__末尾添加


    def swap_pieces(self, pos1_grid, pos2_grid):
        """
        交换两个网格位置上的碎片

        Args:
            pos1_grid (tuple): 第一个碎片的网格坐标 (row, col)
            pos2_grid (tuple): 第二个碎片的网格坐标 (row, col)
        """
        r1, c1 = pos1_grid
        r2, c2 = pos2_grid

        # 确保坐标有效且在板子上
        if not (0 <= r1 < settings.BOARD_ROWS and 0 <= c1 < settings.BOARD_COLS and
                0 <= r2 < settings.BOARD_ROWS and 0 <= c2 < settings.BOARD_COLS):
            print(f"警告: 无效的网格位置 ({r1},{c1}) 或 ({r2},{c2})，无法交换。")
            return False # 交换失败

        piece1 = self.grid[r1][c1]
        piece2 = self.grid[r2][c2]

        # 检查至少有一个位置不是 None，否则交换没有意义
        if piece1 is None and piece2 is None:
             print(f"警告: 交换位置 ({r1},{c1}) 和 ({r2},{c2}) 都为空槽位，不进行交换。")
             return False

        # 在网格中交换
        self.grid[r1][c1] = piece2
        self.grid[r2][c2] = piece1

        # 更新碎片自身的网格位置属性
        if piece1:
            piece1.set_grid_position(r2, c2)
        if piece2:
            piece2.set_grid_position(r1, c1)

        # print(f"交换了碎片位置: ({r1},{c1}) 与 ({r2},{c2})") # 调试信息，频繁交换时打印信息太多
        return True # 交换成功


    def select_piece(self, piece):
        """选中一个碎片 (用于点击交换模式)"""
        if self.selected_piece:
             # 如果已经有选中的，先取消上一个的选中状态
             # TODO: 移除上一个选中碎片的视觉高亮 (通过清除 selection_rect 实现)
             pass # selection_rect 会在设置新选中时更新或在 unselect_piece 中清除

        self.selected_piece = piece
        # 计算选中高亮框的位置和大小，直接使用碎片的rect
        self.selection_rect = pygame.Rect(piece.rect.x, piece.rect.y, settings.PIECE_SIZE, settings.PIECE_SIZE)
        print(f"选中碎片: 图片ID {piece.original_image_id}, 原始位置 ({piece.original_row},{piece.original_col}), 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def unselect_piece(self):
        """取消选中状态"""
        self.selected_piece = None
        self.selection_rect = None # 移除选中高亮框
        # print("取消选中碎片。") # 调试信息


    def start_dragging(self, piece):
        """开始拖拽一个碎片"""
        self.dragging_piece = piece
        # TODO: 添加拖拽碎片的视觉效果 (例如层级提高，使其绘制在其他碎片上方)
        # 这可以通过调整 draw 方法中的绘制顺序实现
        print(f"开始拖拽碎片: 图片ID {piece.original_image_id}, 当前位置 ({piece.current_grid_row},{piece.current_grid_col})") # 调试信息


    def stop_dragging(self):
        """停止拖拽"""
        if self.dragging_piece:
            # TODO: 移除拖拽碎片的视觉效果
            print(f"停止拖拽碎片: 图片ID {self.dragging_piece.original_image_id}, 当前位置 ({self.dragging_piece.current_grid_row},{self.dragging_piece.current_grid_col})") # 调试信息
            self.dragging_piece = None


    def check_and_process_completion(self):
        """
        检查是否有图片完成，如果完成则处理移除和填充。
        返回 True 如果有图片完成，否则返回 False。
        """
        completed_image_id = self.check_completion()
        if completed_image_id is not None:
            print(f"图片 {completed_image_id} 完成了！") # 调试信息

            # 通知 ImageManager 更新图片状态并记录完成时间
            self.image_manager.set_image_state(completed_image_id, 'lit')

            # TODO: 触发图片点亮效果 (可选，例如短暂的高亮或动画)

            # 移除碎片 (将该 5x9 区域设为 None)
            self.remove_completed_pieces(completed_image_id)

            # 碎片下落
            # self.fall_down_pieces() # TODO: 实现下落动画或瞬间下落

            # 填充新碎片 (通常填充 45 个空位，如果还有碎片的话)
            # empty_slots_count = settings.PIECES_PER_IMAGE # 如果每次移除正好45个
            # new_pieces = self.image_manager.get_next_fill_pieces(empty_slots_count)
            # self.fill_new_pieces(new_pieces) # TODO: 实现填充逻辑

            # 通知 Game 或 Gallery 更新图库 (Game实例需要传递进来)
            # if hasattr(self.game, 'gallery'): # 检查Game实例是否有gallery属性
            #      self.game.gallery.add_completed_image(completed_image_id) # 通知Gallery更新列表

            return True # 有图片完成
        return False # 没有图片完成


    def check_completion(self):
        """
        检查拼盘中是否存在一个完整的 5x9 图片块。
        返回已完成的图片ID，如果没有则返回None。
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
                    # 在返回图片ID之前，可以先记录这个完成的区域，以便后续移除
                    self._completed_area_start_pos = (start_row, start_col)
                    return target_image_id # 返回完成的图片ID

        return None # 遍历所有可能位置后没有找到完整的图片


    def remove_completed_pieces(self, completed_image_id):
        """从拼盘中移除指定已完成图片的碎片"""
        # 需要知道是哪个区域完成了，check_completion 应该已经保存了起始位置
        if not hasattr(self, '_completed_area_start_pos'):
             print("错误: 没有记录已完成区域的起始位置，无法移除碎片。")
             return

        start_row, start_col = self._completed_area_start_pos
        print(f"移除图片 {completed_image_id} 在 ({start_row},{start_col}) 开始的 5x9 区域碎片...") # 调试信息

        pieces_to_remove_count = 0
        for dr in range(settings.IMAGE_LOGIC_ROWS):
            for dc in range(settings.IMAGE_LOGIC_COLS):
                r = start_row + dr
                c = start_col + dc
                piece_to_remove = self.grid[r][c]
                if piece_to_remove:
                    # 从 Sprite Group 中移除 (如果使用Group的话)
                    # if piece_to_remove in self.all_pieces_group:
                    #      self.all_pieces_group.remove(piece_to_remove)
                    # 将网格位置设为 None
                    self.grid[r][c] = None
                    pieces_to_remove_count += 1
                else:
                    print(f"警告: 尝试移除的区域 ({r},{c}) 没有碎片。")

        print(f"共移除了 {pieces_to_remove_count} 个碎片。") # 调试信息
        # 清除记录的完成区域位置
        del self._completed_area_start_pos


    def fall_down_pieces(self):
        """处理碎片下落以填补空位"""
        print("触发碎片下落...") # 调试信息
        # 简单的瞬间下落实现：从底向上遍历每一列，将非空碎片“压”到底部
        for c in range(settings.BOARD_COLS): # 遍历每一列
            # bottom_row_index_to_fill = settings.BOARD_ROWS - 1 # 最底部的空位索引，从最下面开始
            pieces_in_column = [] # 存储本列所有的非空碎片

            # 从下往上收集非空碎片
            for r in range(settings.BOARD_ROWS - 1, -1, -1):
                if self.grid[r][c]:
                    pieces_in_column.append(self.grid[r][c])
                    self.grid[r][c] = None # 先将原位置设为None

            # 从下往上重新放置收集到的碎片
            current_row = settings.BOARD_ROWS - 1
            for piece in pieces_in_column:
                 self.grid[current_row][c] = piece
                 piece.set_grid_position(current_row, c) # 更新碎片的位置
                 current_row -= 1

        # TODO: 如果需要平滑动画，这里的实现需要更复杂，管理每个碎片的垂直速度和目标位置


    def fill_new_pieces(self):
        """根据填充规则，从 image_manager 获取新碎片填充顶部空位"""
        print("触发填充新碎片...") # 调试信息
        # 统计有多少个空槽位需要填充 (通常是 45 个，但如果初始填充不足或移除逻辑有误可能不是)
        empty_slots_count = 0
        empty_slots_positions = [] # 记录空槽位的位置 (从上往下，从左往右)
        for r in range(settings.BOARD_ROWS):
            for c in range(settings.BOARD_COLS):
                if self.grid[r][c] is None:
                     empty_slots_count += 1
                     empty_slots_positions.append((r, c)) # 记录空位位置

        print(f"检测到 {empty_slots_count} 个空槽位需要填充。") # 调试信息

        if empty_slots_count == 0:
             print("没有空槽位需要填充。")
             return

        # 从 ImageManager 获取相应数量的新碎片
        new_pieces = self.image_manager.get_next_fill_pieces(empty_slots_count)
        print(f"ImageManager 提供了 {len(new_pieces)} 个新碎片。") # 调试信息

        # 将新碎片放置到空槽位中
        for i, piece in enumerate(new_pieces):
             if i < len(empty_slots_positions):
                 r, c = empty_slots_positions[i]
                 self.grid[r][c] = piece
                 piece.set_grid_position(r, c) # 更新碎片的位置
                 # self.all_pieces_group.add(piece) # 如果使用 Sprite Group
             else:
                 print(f"警告: 有多余的新碎片 ({len(new_pieces)} 个) 但没有足够的空槽位 ({empty_slots_count} 个) 来放置。")
                 break # 没有更多空槽位了

        if len(new_pieces) < empty_slots_count:
            print(f"警告: 需要 {empty_slots_count} 个碎片，但 ImageManager 只提供了 {len(new_pieces)} 个。拼盘将会有空位。")


    def draw(self, surface):
        """在指定的surface上绘制拼盘中的所有碎片和选中效果"""
        # 遍历 self.grid，绘制所有碎片
        # 正常绘制所有碎片
        for r in range(settings.BOARD_ROWS):
            for c in range(settings.BOARD_COLS):
                piece = self.grid[r][c]
                if piece and piece != self.dragging_piece: # 不绘制正在拖拽的那个碎片
                    piece.draw(surface)

        # 绘制选中碎片的特殊效果 (例如绘制边框)
        if self.selection_rect:
             # 绘制一个比碎片稍大一点的矩形作为边框
             border_thickness = 5
             border_rect = self.selection_rect.inflate(border_thickness * 2, border_thickness * 2) # 宽高各增加 border_thickness * 2
             # 计算边框的左上角位置，使其以选中碎片为中心
             border_rect.topleft = (self.selection_rect.left - border_thickness, self.selection_rect.top - border_thickness)
             pygame.draw.rect(surface, settings.HIGHLIGHT_COLOR, border_rect, border_thickness) # 绘制边框，最后一个参数是线条宽度

        # 在最后绘制正在拖拽的碎片，使其显示在最上层
        if self.dragging_piece:
             # TODO: 如果需要拖拽时碎片跟随鼠标移动的视觉效果，在这里更新 dragging_piece.rect 的位置
             # 这需要在 update 方法中根据鼠标位置实时计算并设置，而不是在 draw 方法中
             self.dragging_piece.draw(surface)


    def update(self, dt):
         """更新Board的状态，例如处理碎片下落动画"""
         # if self.all_pieces_group: # 如果使用Sprite Group
         #      self.all_pieces_group.update(dt) # 调用所有碎片的update方法 (当下落时)

         # 如果实现了平滑下落动画，在这里调用处理动画的方法
         # self._update_falling_pieces(dt)

         # 在这里检查拼图完成并触发后续流程 (或者在交换完成后立即检查)
         # 频繁检查可能会影响性能，但简化逻辑
         # self.check_and_process_completion() # 不要在update里检查，太频繁了，在交换后检查

         pass # TODO: 实现Board的update逻辑，特别是碎片下落动画的协调


    def get_piece_at_grid(self, row, col):
         """获取指定网格位置的碎片对象，或None"""
         if 0 <= row < settings.BOARD_ROWS and 0 <= col < settings.BOARD_COLS:
             return self.grid[row][col]
         return None # 坐标无效

    # def _update_falling_pieces(self, dt):
    #      """更新正在下落的碎片位置 (平滑动画)"""
    #      # 遍历所有碎片，如果 is_falling 为 True，更新其位置并检查是否到达目标
    #      pass # TODO: 实现平滑下落动画逻辑