# gallery.py
# 管理图库界面的逻辑和绘制

import pygame
import settings
import time # 用于计时
import utils # 导入工具函数
from ui_elements import Button # 导入 Button 类


class Gallery:
    def __init__(self, image_manager, game_instance):
        """
        初始化图库管理器。

        Args:
            image_manager (ImageManager): 图像管理器实例。
            game_instance (Game): Game实例，用于状态切换、显示提示等。
        """
        self.image_manager = image_manager
        self.game = game_instance # 持有Game实例的引用

        # 存储所有已入场图片的列表，包含图片ID和状态
        # self.pictures_in_gallery = [] # 会在打开图库时动态更新

        # 图库列表的滚动位置
        self.scroll_y = 0
        self._max_scroll_y = 0 # 最大可滚动距离，需要根据图片数量计算

        # 当前正在查看的已点亮大图的索引 (在已点亮图片列表中的索引)
        self.viewing_lit_image_index = -1 # -1表示没有查看大图
        self._lit_images_list = [] # 存储已点亮图片的ID列表，用于大图导航

        # UI元素 - 图库列表界面
        self.list_view_surface = pygame.Surface((settings.GALLERY_WIDTH, settings.GALLERY_HEIGHT), pygame.SRCALPHA) # 用于绘制列表内容，支持透明度
        self.list_view_rect = self.list_view_surface.get_rect(topleft=(settings.GALLERY_X, settings.GALLERY_Y)) # 图库窗口在屏幕上的位置和大小
        self._list_content_height = 0 # 图库列表内容的实际总高度，用于计算滚动条和最大滚动距离


        # UI元素 - 大图查看界面
        # 左右导航按钮
        self.left_button = Button(settings.LEFT_BUTTON_PATH, (0, 0), anchor='center', callback=lambda: self.navigate_lit_images(-1))
        self.right_button = Button(settings.RIGHT_BUTTON_PATH, (0, 0), anchor='center', callback=lambda: self.navigate_lit_images(1))

        # Sprite Group 用于管理大图查看界面的按钮，方便绘制和事件处理
        self.view_lit_buttons = pygame.sprite.Group(self.left_button, self.right_button)


        # 加载字体 (也可以在Game类中统一加载)
        # self.font_thumbnail_id = pygame.font.Font(None, 24) # 示例：在缩略图下方显示图片ID


    def open_gallery(self):
        """打开图库界面，切换游戏状态"""
        print("打开图库。") # 调试信息
        self._update_picture_list() # 在打开时更新列表内容和排序
        self.scroll_y = 0 # 打开图库时滚动位置归零
        self.viewing_lit_image_index = -1 # 确保不在大图查看状态
        # Game类调用 change_state 方法来切换状态
        # self.game.change_state(settings.GAME_STATE_GALLERY_LIST) # 这是在Game类中调用的


    def close_gallery(self):
        """关闭图库界面，切换回游戏主状态"""
        print("关闭图库。") # 调试信息
        self.viewing_lit_image_index = -1 # 确保退出大图查看
        # Game类调用 change_state 方法来切换状态
        # self.game.change_state(settings.GAME_STATE_PLAYING) # 这是在Game类中调用的


    def _update_picture_list(self):
        """从image_manager获取并更新图库中的图片列表及状态，并进行排序"""
        # 获取所有已入场(未点亮+已点亮)图片的原始列表和状态信息
        # ImageManager 提供的列表已包含状态和完成时间
        all_entered_pictures = self.image_manager.get_all_entered_pictures_status() # 需要image_manager提供这个方法

        # 分离已点亮和未点亮图片
        # 筛选出碎片已加载完成的图片，因为只有这些图片才能生成缩略图
        lit_pictures = sorted([p for p in all_entered_pictures if p['state'] == 'lit' and p['is_pieces_loaded']],
                              key=lambda x: x['completion_time'], reverse=True) # 按完成时间倒序

        # 未点亮图片，也只显示碎片已加载完成的
        unlit_pictures = sorted([p for p in all_entered_pictures if p['state'] == 'unlit' and p['is_pieces_loaded']],
                                key=lambda x: x['id']) # 按ID顺序 (即文件命名顺序)

        # 合并列表，已点亮在前
        self.pictures_in_gallery = lit_pictures + unlit_pictures

        # 更新已点亮图片列表，用于大图导航
        self._lit_images_list = [p['id'] for p in lit_pictures]

        # 计算列表内容的实际总高度
        # 每行 settings.GALLERY_IMAGES_PER_ROW 张图片
        # 缩略图高度 settings.GALLERY_THUMBNAIL_HEIGHT
        # 垂直间距 settings.GALLERY_THUMBNAIL_GAP_Y
        # 上下内边距 settings.GALLERY_PADDING
        num_pictures = len(self.pictures_in_gallery)
        if num_pictures == 0:
            self._list_content_height = 0
        else:
            num_rows = (num_pictures + settings.GALLERY_IMAGES_PER_ROW - 1) // settings.GALLERY_IMAGES_PER_ROW # 向上取整的行数
            self._list_content_height = num_rows * settings.GALLERY_THUMBNAIL_HEIGHT + (num_rows - 1) * settings.GALLERY_THUMBNAIL_GAP_Y + 2 * settings.GALLERY_PADDING

        # 计算最大可滚动距离
        self._max_scroll_y = max(0, self._list_content_height - settings.GALLERY_HEIGHT)

        print(f"图库列表更新: 共 {num_pictures} 张图 (已点亮 {len(lit_pictures)}, 未点亮 {len(unlit_pictures)})") # 调试信息
        # print(f"列表内容总高度: {self._list_content_height}, 最大可滚动: {self._max_scroll_y}") # 调试信息


    # def add_completed_image(self, image_id):
    #     """当有图片完成时被board调用，更新图库列表。目前由Board调用ImageManager更新状态，Gallery在打开时自己拉取数据。"""
    #     # 当图片完成时，ImageManager会更新状态和完成时间。
    #     # 图库列表应在打开时刷新，或者在 Board 流程结束后通知 Game/Gallery 刷新。
    #     # 简单的做法是只在打开时刷新。更实时的做法是在图片点亮时（由Board通知Game/Gallery）调用这里的 _update_picture_list()
    #     # 为了避免在频繁交换检查时调用，最好是在 Board 完成移除/下落/填充整个流程后，再通知 Gallery 刷新。
    #     # Board 完成流程后，回到 PLAYING 状态，可以在 Board._process_completed_picture 末尾通知 Game，Game再通知 Gallery。
    #     # self._update_picture_list() # 触发列表更新和重新排序 (这里调用可能太早，图库界面可能未打开)
    #     pass # 由 Board 完成流程后触发 Game 通知


    def handle_event_list(self, event):
        """处理图库列表界面的事件"""
        # 检查是否点击了图库窗口外部区域 (这里假设图库是叠加在游戏界面之上的)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             # 创建图库窗口的Rect
             gallery_window_rect = pygame.Rect(settings.GALLERY_X, settings.GALLERY_Y, settings.GALLERY_WIDTH, settings.GALLERY_HEIGHT)
             if not gallery_window_rect.collidepoint(event.pos):
                 self.close_gallery() # 点击外部，关闭图库
                 return True # 事件已被处理

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 左键点击 (在图库窗口内部)
                 # 检查点击了哪个缩略图
                 clicked_thumbnail_index = self._get_thumbnail_index_at_pos(event.pos)
                 if clicked_thumbnail_index is not None:
                     # 获取点击的图片信息
                     if 0 <= clicked_thumbnail_index < len(self.pictures_in_gallery):
                         clicked_picture_info = self.pictures_in_gallery[clicked_thumbnail_index]
                         if clicked_picture_info['state'] == 'lit':
                             # 如果点击已点亮图片，切换到大图查看模式
                             print(f"点击已点亮图片: ID {clicked_picture_info['id']}, 切换到大图查看。") # 调试信息
                             self.start_viewing_lit_image(clicked_thumbnail_index)
                             return True # 事件已被处理
                         elif clicked_picture_info['state'] == 'unlit':
                             # 如果点击未点亮图片，显示提示
                             print(f"点击未点亮图片: ID {clicked_picture_info['id']}, 显示提示。") # 调试信息
                             # Game类显示提示
                             if hasattr(self.game, 'show_popup_tip'):
                                  self.game.show_popup_tip("美图尚未点亮")
                             return True # 事件已被处理
                 # 点击在图库窗口内部，但不是图片缩略图
                 # pass # 不做处理，事件不被消耗，例如可以用于拖拽滚动条 (如果实现的话)

        elif event.type == pygame.MOUSEWHEEL: # 鼠标滚轮事件
            # 根据滚轮方向调整滚动位置
            # event.y 是滚轮垂直滚动的量，向上通常是1，向下通常是-1
            self.scroll_y -= event.y * settings.GALLERY_SCROLL_SPEED # 负号因为滚轮向上 scroll_y 减小 (内容向上移动)
            # 限制滚动范围
            self.scroll_y = max(0, self.scroll_y) # 不能滚到顶部以上
            self.scroll_y = min(self._max_scroll_y, self.scroll_y) # 不能滚到底部以下
            # print(f"滚动图库列表，新 scroll_y: {self.scroll_y}") # 调试信息
            return True # 事件已被处理

        # TODO: 处理可能的滑动条拖拽事件 (如果实现滑动条)
        # TODO: 处理其他可能的UI元素的事件

        return False # 事件未被处理

    def _get_thumbnail_index_at_pos(self, mouse_pos):
        """
        将鼠标像素位置转换为图库列表中的缩略图索引。

        Args:
            mouse_pos (tuple): 鼠标的屏幕像素坐标 (x, y)。

        Returns:
            int or None: 缩略图在 self.pictures_in_gallery 列表中的索引，如果未点击在任何缩略图上则返回 None。
        """
        # 检查点击位置是否在图库窗口内部
        gallery_window_rect = pygame.Rect(settings.GALLERY_X, settings.GALLERY_Y, settings.GALLERY_WIDTH, settings.GALLERY_HEIGHT)
        if not gallery_window_rect.collidepoint(mouse_pos):
            return None # 点击位置不在图库窗口内

        # 将鼠标坐标转换为图库窗口内部的相对坐标，并考虑滚动
        relative_x = mouse_pos[0] - settings.GALLERY_X
        relative_y = mouse_pos[1] - settings.GALLERY_Y + self.scroll_y # 加上滚动偏移

        # 计算点击位置可能所在的行和列 (相对于缩略图网格)
        # 需要减去内边距
        content_x = relative_x - settings.GALLERY_PADDING
        content_y = relative_y - settings.GALLERY_PADDING

        if content_x < 0 or content_y < 0:
            return None # 点击在内边距区域

        # 计算可能的网格列和行
        # 考虑缩略图尺寸和间距
        col_guess = content_x // (settings.GALLERY_THUMBNAIL_WIDTH + settings.GALLERY_THUMBNAIL_GAP_X)
        row_guess = content_y // (settings.GALLERY_THUMBNAIL_HEIGHT + settings.GALLERY_THUMBNAIL_GAP_Y)

        # 检查计算出的行和列是否在有效范围内
        if col_guess < 0 or col_guess >= settings.GALLERY_IMAGES_PER_ROW:
             return None # 点击位置在缩略图列范围外

        # 计算点击位置在潜在缩略图网格单元内的相对坐标
        x_in_cell = content_x % (settings.GALLERY_THUMBNAIL_WIDTH + settings.GALLERY_THUMBNAIL_GAP_X)
        y_in_cell = content_y % (settings.GALLERY_THUMBNAIL_HEIGHT + settings.GALLERY_THUMBNAIL_GAP_Y)

        # 检查点击位置是否在缩略图图像区域内 (排除间距区域)
        if x_in_cell < settings.GALLERY_THUMBNAIL_WIDTH and y_in_cell < settings.GALLERY_THUMBNAIL_HEIGHT:
            # 计算对应的图片索引在 self.pictures_in_gallery 列表中的位置
            thumbnail_index = row_guess * settings.GALLERY_IMAGES_PER_ROW + col_guess

            # 确保索引在当前图片列表的范围内
            if 0 <= thumbnail_index < len(self.pictures_in_gallery):
                # print(f"点击了缩略图索引: {thumbnail_index}") # 调试信息
                return thumbnail_index
            else:
                 # print(f"点击位置对应索引 {thumbnail_index} 超出图片列表范围 {len(self.pictures_in_gallery)}") # 调试信息
                 return None # 索引超出范围
        else:
            # 点击位置在缩略图之间的间距区域
            return None


    def start_viewing_lit_image(self, thumbnail_index_in_gallery_list):
        """
        开始查看已点亮的大图。

        Args:
            thumbnail_index_in_gallery_list (int): 在 self.pictures_in_gallery 列表中的索引。
        """
        # 获取对应的图片信息
        if 0 <= thumbnail_index_in_gallery_list < len(self.pictures_in_gallery):
            picture_info = self.pictures_in_gallery[thumbnail_index_in_gallery_list]
            if picture_info['state'] == 'lit':
                 # 找到这张图片ID在 _lit_images_list 中的索引，以便后续导航
                 try:
                     lit_list_index = self._lit_images_list.index(picture_info['id'])
                     self.viewing_lit_image_index = lit_list_index # 设置当前查看的图片索引
                     # 切换游戏状态到大图查看
                     if hasattr(self.game, 'change_state'):
                         self.game.change_state(settings.GAME_STATE_GALLERY_VIEW_LIT)
                     print(f"开始查看图片ID {picture_info['id']} ({lit_list_index}/{len(self._lit_images_list)-1})") # 调试信息
                 except ValueError:
                     print(f"错误: 已点亮图片ID {picture_info['id']} 不在 _lit_images_list 中。")
                     self.viewing_lit_image_index = -1 # 状态异常

            else:
                 print(f"错误: 尝试查看未点亮图片ID {picture_info['id']} 的大图。")
                 self.viewing_lit_image_index = -1 # 状态异常
        else:
            print(f"错误: 尝试查看索引 {thumbnail_index_in_gallery_list} 的图片，超出列表范围。")
            self.viewing_lit_image_index = -1


    def stop_viewing_lit_image(self):
        """停止查看大图，返回图库列表界面"""
        print("停止查看大图，返回列表。") # 调试信息
        self.viewing_lit_image_index = -1 # 退出大图查看状态
        # 切换游戏状态回图库列表
        if hasattr(self.game, 'change_state'):
            self.game.change_state(settings.GAME_STATE_GALLERY_LIST)


    def navigate_lit_images(self, direction):
        """
        在大图查看模式下导航已点亮图片。

        Args:
            direction (int): 导航方向，-1 为上一张，1 为下一张。
        """
        if self.viewing_lit_image_index != -1 and self._lit_images_list:
            current_index = self.viewing_lit_image_index
            num_lit_images = len(self._lit_images_list)
            if num_lit_images <= 1:
                 print("只有一张已点亮图片，无法导航。") # 调试信息
                 return # 只有一张图，不能导航

            # 计算下一个索引，支持循环
            new_index = (current_index + direction) % num_lit_images
            self.viewing_lit_image_index = new_index

            # print(f"导航到已点亮图片索引 {new_index} (ID: {self._lit_images_list[new_index]})") # 调试信息

            # 每次导航到新图片时，可能需要刷新大图显示（虽然大图绘制方法会在draw循环中自动获取新的图片ID）
            # 如果需要，可以在这里加载或准备下一张大图资源


    def handle_event_view_lit(self, event):
        """处理图库大图查看界面的事件"""
        # 处理左右导航按钮的事件
        handled = self.view_lit_buttons.handle_event(event) # Button 类需要有 handle_event 方法并返回 True/False

        if handled:
             return True # 事件被按钮处理了

        # 如果事件未被按钮处理，检查是否点击了正在显示的大图本身
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             # 获取当前正在查看的图片 surface，计算其屏幕 Rect，检查点击是否在其范围内
             if self.viewing_lit_image_index != -1 and self._lit_images_list:
                 current_image_id = self._lit_images_list[self.viewing_lit_image_index]
                 full_image_surface = self.image_manager.get_full_processed_image(current_image_id)

                 if full_image_surface:
                     # 缩放图片以适应屏幕，保持比例
                     img_w, img_h = full_image_surface.get_size()
                     screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
                     scale_factor = min(screen_w / img_w, screen_h / img_h)
                     scaled_w = int(img_w * scale_factor)
                     scaled_h = int(img_h * scale_factor)

                     # 计算绘制位置 (居中)
                     img_rect = pygame.Rect(0, 0, scaled_w, scaled_h)
                     img_rect.center = (screen_w // 2, screen_h // 2)

                     # 检查点击位置是否在大图 Rect 范围内
                     if img_rect.collidepoint(event.pos):
                          print("点击大图本身，退出查看。") # 调试信息
                          self.stop_viewing_lit_image() # 退出大图查看
                          return True # 事件已被处理

        return False # 事件未被处理


    def draw(self, surface):
        """
        根据图库当前子状态 (列表或大图查看) 绘制相应的界面。
        这个方法由 Game 类在主 draw 循环中调用。
        """
        # 绘制一个半透明背景，覆盖主游戏界面
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(settings.OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        if self.viewing_lit_image_index != -1:
             # 绘制大图查看界面
             self.draw_view_lit(surface)
        else:
             # 绘制图库列表界面
             self.draw_list(surface)


    def draw_list(self, surface):
        """绘制图库列表界面"""
        # 绘制图库窗口背景
        pygame.draw.rect(surface, settings.GALLERY_BG_COLOR, self.list_view_rect)

        # 计算可见区域（图库窗口内部）
        clip_rect = self.list_view_rect.copy() # 复制图库窗口 Rect
        # 将绘制限制在这个区域内
        # Pygame 的 set_clip 可以限制绘制区域
        # old_clip = surface.get_clip() # 保存旧的裁剪区域
        # surface.set_clip(clip_rect) # 设置新的裁剪区域

        # 绘制列表内容，需要考虑滚动偏移 self.scroll_y
        # 遍历 self.pictures_in_gallery
        for i, pic_info in enumerate(self.pictures_in_gallery):
            # 计算当前缩略图在列表内容中的位置 (不考虑滚动)
            row_in_list = i // settings.GALLERY_IMAGES_PER_ROW
            col_in_row = i % settings.GALLERY_IMAGES_PER_ROW
            # 计算绘制的屏幕坐标
            draw_x = settings.GALLERY_X + settings.GALLERY_PADDING + col_in_row * (settings.GALLERY_THUMBNAIL_WIDTH + settings.GALLERY_THUMBNAIL_GAP_X)
            draw_y = settings.GALLERY_Y + settings.GALLERY_PADDING + row_in_list * (settings.GALLERY_THUMBNAIL_HEIGHT + settings.GALLERY_THUMBNAIL_GAP_Y) - self.scroll_y # 应用滚动偏移

            # 只有当缩略图在可见区域内时才绘制 (简单的裁剪判断)
            thumbnail_rect = pygame.Rect(draw_x, draw_y, settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT)
            if thumbnail_rect.colliderect(self.list_view_rect): # 检查缩略图是否与图库窗口 Rect 相交

                # 获取缩略图 surface
                thumbnail_surface = self.image_manager.get_thumbnail(pic_info['id'])

                if thumbnail_surface:
                    # 如果是未点亮状态，将缩略图灰度化
                    if pic_info['state'] == 'unlit':
                         thumbnail_surface = utils.grayscale_surface(thumbnail_surface)

                    # 绘制缩略图
                    surface.blit(thumbnail_surface, (draw_x, draw_y))

                    # TODO: 可以绘制图片ID或状态文字 (可选)
                    # text_surface = self.font_thumbnail_id.render(f"ID:{pic_info['id']}", True, settings.WHITE)
                    # surface.blit(text_surface, (draw_x, draw_y + settings.GALLERY_THUMBNAIL_HEIGHT + 5)) # 绘制在缩略图下方

                else:
                     # 如果无法获取缩略图，绘制一个占位符
                     placeholder_rect = pygame.Rect(draw_x, draw_y, settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT)
                     pygame.draw.rect(surface, settings.GRAY, placeholder_rect) # 绘制灰色矩形
                     # 可以在占位符上绘制文字，比如"加载失败"或"等待加载"
                     # placeholder_font = pygame.font.Font(None, 20)
                     # placeholder_text = placeholder_font.render("加载中...", True, settings.BLACK)
                     # text_center = placeholder_rect.center
                     # text_rect = placeholder_text.get_rect(center=text_center)
                     # surface.blit(placeholder_text, text_rect)


        # TODO: 绘制滚动条 (可选)

        # 恢复旧的裁剪区域
        # surface.set_clip(old_clip)


    def draw_view_lit(self, surface):
        """绘制图库大图查看界面"""
        if self.viewing_lit_image_index == -1 or not self._lit_images_list:
             print("警告: 尝试绘制大图查看界面，但没有图片可查看。") # 不应该发生
             return

        # 获取当前正在查看的图片ID
        current_image_id = self._lit_images_list[self.viewing_lit_image_index]
        full_image_surface = self.image_manager.get_full_processed_image(current_image_id)

        if full_image_surface:
            # 缩放图片以适应屏幕，保持比例
            img_w, img_h = full_image_surface.get_size()
            screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

            # 计算缩放因子，以适应屏幕尺寸，保持比例，且不超出屏幕
            scale_factor = min(screen_w / img_w, screen_h / img_h)
            # 留一点边距，避免图片紧贴屏幕边缘 (例如留20像素边距)
            margin = 40
            scale_factor = min((screen_w - margin) / img_w, (screen_h - margin) / img_h, scale_factor) # 确保不超出屏幕并留白

            scaled_w = int(img_w * scale_factor)
            scaled_h = int(img_h * scale_factor)

            # 确保缩放后的尺寸有效
            if scaled_w <= 0 or scaled_h <= 0:
                print(f"警告: 大图图片 {current_image_id} 缩放后尺寸无效 ({scaled_w}x{scaled_h})。")
                # 绘制一个占位符
                placeholder_rect = pygame.Rect(0, 0, 200, 150) # 示例占位符大小
                placeholder_rect.center = (screen_w // 2, screen_h // 2)
                pygame.draw.rect(surface, settings.GRAY, placeholder_rect)
                # 可以绘制文字 "加载失败"
                return

            scaled_image = pygame.transform.scale(full_image_surface, (scaled_w, scaled_h))

            # 计算绘制位置 (居中)
            img_rect = scaled_image.get_rect(center=(screen_w // 2, screen_h // 2))
            surface.blit(scaled_image, img_rect)

            # 绘制左右导航按钮
            # 计算按钮位置，相对于绘制的大图Rect
            button_offset_x = max(50, (screen_w - scaled_w) // 4) # 按钮距离图片边缘的距离，或者屏幕边缘的距离
            self.left_button.rect.centery = img_rect.centery
            self.left_button.rect.right = img_rect.left - button_offset_x # 按钮放在图片左侧

            self.right_button.rect.centery = img_rect.centery
            self.right_button.rect.left = img_rect.right + button_offset_x # 按钮放在图片右侧

            # 绘制按钮组
            self.view_lit_buttons.draw(surface)

        else:
             # 如果无法获取完整处理后的图片，绘制一个加载中或占位符
             # 这不应该经常发生，因为只有碎片加载完成后才可能进入已点亮状态
             print(f"警告: 无法获取图片 {current_image_id} 的完整处理后图片，可能尚未加载。")
             # 绘制一个文本提示
             font = self.game.font_loading # 使用加载界面的字体或通用字体
             text_surface = font.render("图片加载中...", True, settings.WHITE)
             text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2))
             surface.blit(text_surface, text_rect)


    # def update_list(self, dt): pass # 如果列表有动画或需要随时间更新的状态
    # def update_view_lit(self, dt): pass # 如果大图查看有动画或需要随时间更新的状态
    # def update(self, dt): # 如果图库需要整体更新
    #     if self.game.current_state == settings.GAME_STATE_GALLERY_LIST:
    #          # self.update_list(dt)
    #          pass
    #     elif self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
    #          # self.update_view_lit(dt)
    #          pass