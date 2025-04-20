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

        # 存储所有已入场图片的列表，包含图片ID、状态、完成时间、碎片是否加载标志
        self.pictures_in_gallery = [] # 会在打开图库时动态更新

        # 图库列表的滚动位置
        self.scroll_y = 0
        self._max_scroll_y = 0 # 最大可滚动距离，需要根据图片数量计算

        # 当前正在查看的已点亮大图的索引 (在 _lit_images_list 中的索引)
        self.viewing_lit_image_index = -1 # -1表示没有查看大图
        self._lit_images_list = [] # 存储已点亮图片的ID列表，用于大图导航 (按图库列表的已点亮排序)

        # UI元素 - 图库列表界面
        # 图库窗口背景 Surface (带透明度)
        self.gallery_window_surface = pygame.Surface((settings.GALLERY_WIDTH, settings.GALLERY_HEIGHT), pygame.SRCALPHA)
        self.gallery_window_surface.fill(settings.GALLERY_BG_COLOR)
        self.gallery_window_rect = self.gallery_window_surface.get_rect(topleft=(settings.GALLERY_X, settings.GALLERY_Y)) # 图库窗口在屏幕上的位置和大小

        # UI元素 - 大图查看界面
        # 左右导航按钮 (位置在 draw 方法中根据当前显示的大图Rect动态计算)
        # callback 参数使用了 lambda 匿名函数，以便在点击时调用 navigate_lit_images
        self.left_button = Button(settings.LEFT_BUTTON_PATH, (0, 0), anchor='center', callback=lambda: self.navigate_lit_images(-1))
        self.right_button = Button(settings.RIGHT_BUTTON_PATH, (0, 0), anchor='center', callback=lambda: self.navigate_lit_images(1))

        # Sprite Group 用于管理大图查看界面的按钮，方便绘制和事件处理
        self.view_lit_buttons = pygame.sprite.Group(self.left_button, self.right_button)

        # 字体 (使用Game实例中的字体) - Optional, if you draw text on thumbnails
        # self.font_thumbnail = self.game.font_thumbnail # Assumption, using it for optional drawing

        # 图库列表的可见区域 Rect，用于 set_clip
        # 这是图库窗口内部，排除内边距的区域，用于限制绘制范围
        self._list_visible_clip_rect = pygame.Rect(
             settings.GALLERY_X + settings.GALLERY_PADDING,
             settings.GALLERY_Y + settings.GALLERY_PADDING,
             settings.GALLERY_WIDTH - 2 * settings.GALLERY_PADDING,
             settings.GALLERY_HEIGHT - 2 * settings.GALLERY_PADDING
        )


    def open_gallery(self):
        """打开图库界面，切换游戏状态。这个方法由Game类调用。"""
        print("打开图库。") # Debug
        # 在打开时更新列表内容和排序
        self._update_picture_list()
        # 滚动位置归零
        self.scroll_y = 0
        # 确保不在大图查看状态
        self.viewing_lit_image_index = -1
        # Game类调用 change_state 方法来切换状态 (Game类负责调用此方法)
        # self.game.change_state(settings.GAME_STATE_GALLERY_LIST)


    def close_gallery(self):
        """关闭图库界面，切换回游戏主状态。这个方法由Game类调用。"""
        print("关闭图库。") # Debug
        # 确保退出大图查看状态 (如果在大图查看状态下点击外部区域，也会调用此方法)
        self.viewing_lit_image_index = -1
        # Game类调用 change_state 方法来切换状态 (Game类负责调用此方法)
        # self.game.change_state(settings.GAME_STATE_PLAYING)


    def _update_picture_list(self):
        """从image_manager获取并更新图库中的图片列表及状态，并进行排序。"""
        # 获取所有已入场(未点亮+已点亮)且碎片已加载的图片列表，包含状态和完成时间
        # ImageManager 提供的列表已包含必要信息，并且已经过滤掉了碎片未加载完整的图片
        all_entered_and_loaded_pictures = self.image_manager.get_all_entered_pictures_status() # ImageManager 提供的列表已包含必要信息

        # 分离已点亮和未点亮图片
        # 已点亮的按完成时间倒序排列
        lit_pictures = sorted([p for p in all_entered_and_loaded_pictures if p['state'] == 'lit'],
                              key=lambda x: x['completion_time'], reverse=True)

        # 未点亮的按图片ID顺序排列
        unlit_pictures = sorted([p for p in all_entered_and_loaded_pictures if p['state'] == 'unlit'],
                                key=lambda x: x['id'])

        # 合并列表，已点亮图片在前
        self.pictures_in_gallery = lit_pictures + unlit_pictures

        # 更新已点亮图片ID列表，用于大图导航 (确保顺序与图库列表一致)
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
            # 计算所需的总行数，向上取整
            num_rows = (num_pictures + settings.GALLERY_IMAGES_PER_ROW - 1) // settings.GALLERY_IMAGES_PER_ROW
            # 总高度 = 行数 * 缩略图高度 + (行数 - 1) * 垂直间距 + 2 * 上下内边距
            self._list_content_height = num_rows * settings.GALLERY_THUMBNAIL_HEIGHT + max(0, num_rows - 1) * settings.GALLERY_THUMBNAIL_GAP_Y + 2 * settings.GALLERY_PADDING

        # 计算最大可滚动距离
        # 如果内容总高度小于窗口高度，最大滚动距离为0
        self._max_scroll_y = max(0, self._list_content_height - settings.GALLERY_HEIGHT)

        # print(f"图库列表更新: 共 {num_pictures} 张图 (已点亮 {len(lit_pictures)}, 未点亮 {len(unlit_pictures)})") # Debug
        # print(f"列表内容总高度: {self._list_content_height}, 最大可滚动: {self._max_scroll_y}") # Debug


    def handle_event_list(self, event):
        """处理图库列表界面的事件。返回 True 表示事件被消耗，False 表示未处理。"""
        # 检查事件是否发生在图库窗口区域内
        gallery_window_rect = self.gallery_window_rect # 使用 self.gallery_window_rect
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             if not gallery_window_rect.collidepoint(event.pos):
                 # 点击了图库窗口外部区域
                 # 通知 Game 关闭图库 (Game类负责切换状态)
                 if hasattr(self.game, 'close_gallery'):
                     self.game.close_gallery()
                 return True # 事件已被处理

        # 如果事件发生在图库窗口内部，处理内部交互
        # 将鼠标位置转换为相对于图库窗口内容的偏移量 (不含滚动)
        # relative_mouse_pos = (event.pos[0] - settings.GALLERY_X, event.pos[1] - settings.GALLERY_Y)

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
                             print(f"点击已点亮图片: ID {clicked_picture_info['id']}, 切换到大图查看。") # Debug
                             self.start_viewing_lit_image(clicked_thumbnail_index)
                             return True # 事件已被处理
                         elif clicked_picture_info['state'] == 'unlit':
                             # 如果点击未点亮图片，显示提示
                             print(f"点击未点亮图片: ID {clicked_picture_info['id']}, 显示提示。") # Debug
                             # Game类显示提示
                             if hasattr(self.game, 'show_popup_tip'):
                                  self.game.show_popup_tip("美图尚未点亮")
                             return True # 事件已被处理
                 # 点击在图库窗口内部，但不是图片缩略图
                 # 如果点击在图库窗口背景上，且不是缩略图或按钮等，事件未消耗
                 # return False # Event not handled by internal UI elements

        elif event.type == pygame.MOUSEWHEEL: # 鼠标滚轮事件
            # 确保鼠标在图库窗口区域内时，滚轮事件才有效
            if gallery_window_rect.collidepoint(pygame.mouse.get_pos()): # Pygame 的 mouse.get_pos() 获取当前鼠标位置
                # 根据滚轮方向调整滚动位置
                # event.y 是滚轮垂直滚动的量，向上通常是1，向下通常是-1
                self.scroll_y -= event.y * settings.GALLERY_SCROLL_SPEED # 负号因为滚轮向上 scroll_y 减小 (内容向上移动)
                # 限制滚动范围
                self.scroll_y = max(0, self.scroll_y) # 不能滚到顶部以上
                self.scroll_y = min(self._max_scroll_y, self.scroll_y) # 不能滚到底部以下
                # print(f"滚动图库列表，新 scroll_y: {self.scroll_y}") # Debug
                return True # 事件已被处理

        # TODO: 处理可能的滑动条拖拽事件 (如果实现滑动条)
        # TODO: 处理其他可能的UI元素的事件 (例如搜索框等)

        return False # 事件未被处理

    def _get_thumbnail_index_at_pos(self, mouse_pos):
        """
        将鼠标像素位置转换为图库列表中的缩略图索引。

        Args:
            mouse_pos (tuple): 鼠标的屏幕像素坐标 (x, y)。

        Returns:
            int or None: 缩略图在 self.pictures_in_gallery 列表中的索引，如果未点击在任何缩略图上则返回 None。
        """
        # 检查点击位置是否在图库内容可见区域内
        if not self._list_visible_clip_rect.collidepoint(mouse_pos):
            return None # 点击位置不在图库内容可见区域内

        # 将鼠标坐标转换为图库内容区域内的相对坐标，并考虑滚动
        relative_x_in_content_area = mouse_pos[0] - self._list_visible_clip_rect.left
        relative_y_in_content_area = mouse_pos[1] - self._list_visible_clip_rect.top + self.scroll_y # 加上滚动偏移

        # 计算点击位置可能所在的行和列 (相对于缩略图网格)
        # 不需要减去内边距了，因为 _list_visible_clip_rect 已经是内容区域了
        col_guess = relative_x_in_content_area // (settings.GALLERY_THUMBNAIL_WIDTH + settings.GALLERY_THUMBNAIL_GAP_X)
        row_guess = relative_y_in_content_area // (settings.GALLERY_THUMBNAIL_HEIGHT + settings.GALLERY_THUMBNAIL_GAP_Y)

        # 检查计算出的列是否在有效范围内
        if col_guess < 0 or col_guess >= settings.GALLERY_IMAGES_PER_ROW:
             return None # 点击位置在缩略图列范围外

        # 计算点击位置在潜在缩略图网格单元内的相对坐标
        x_in_cell = relative_x_in_content_area % (settings.GALLERY_THUMBNAIL_WIDTH + settings.GALLERY_THUMBNAIL_GAP_X)
        y_in_cell = relative_y_in_content_area % (settings.GALLERY_THUMBNAIL_HEIGHT + settings.GALLERY_THUMBNAIL_GAP_Y)

        # 检查点击位置是否在缩略图图像区域内 (排除间距区域)
        if x_in_cell < settings.GALLERY_THUMBNAIL_WIDTH and y_in_cell < settings.GALLERY_THUMBNAIL_HEIGHT:
            # 计算对应的图片索引在 self.pictures_in_gallery 列表中的位置
            thumbnail_index = row_guess * settings.GALLERY_IMAGES_PER_ROW + col_guess

            # 确保索引在当前图片列表的范围内
            if 0 <= thumbnail_index < len(self.pictures_in_gallery):
                # print(f"点击了缩略图索引: {thumbnail_index}") # Debug
                return thumbnail_index
            else:
                 # print(f"点击位置对应索引 {thumbnail_index} 超出图片列表范围 {len(self.pictures_in_gallery)}") # Debug
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
                     print(f"开始查看图片ID {picture_info['id']} ({lit_list_index+1}/{len(self._lit_images_list)})") # Debug (索引+1方便人类阅读)
                 except ValueError:
                     print(f"错误: 已点亮图片ID {picture_info['id']} 不在 _lit_images_list 中。") # Debug
                     self.viewing_lit_image_index = -1 # 状态异常

            else:
                 print(f"错误: 尝试查看未点亮图片ID {picture_info['id']} 的大图。") # Debug
                 self.viewing_lit_image_index = -1 # 状态异常
        else:
            print(f"错误: 尝试查看索引 {thumbnail_index_in_gallery_list} 的图片，超出列表范围。") # Debug
            self.viewing_lit_image_index = -1


    def stop_viewing_lit_image(self):
        """停止查看大图，返回图库列表界面"""
        print("停止查看大图，返回列表。") # Debug
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
                 # print("只有一张已点亮图片，无法导航。") # Debug, avoid spamming
                 return # 不能导航，如果只有一张图片

            # 计算下一个索引，支持循环
            new_index = (current_index + direction) % num_lit_images
            self.viewing_lit_image_index = new_index

            # print(f"导航到已点亮图片索引 {new_index} (ID: {self._lit_images_list[new_index]})") # Debug

            # 每次导航到新图片时，可以在这里加载或准备下一张大图资源 (ImageManager.get_full_processed_image 会缓存，所以通常不需要额外加载)


    def handle_event_view_lit(self, event):
        """处理图库大图查看界面的事件。返回 True 表示事件被消耗，False 表示未处理。"""
        # 处理左右导航按钮的事件
        # Button 类需要有 handle_event 方法并返回 True 如果事件被处理
        handled = self.view_lit_buttons.handle_event(event)

        if handled:
             return True # 事件被按钮处理了

        # 如果事件未被按钮处理，检查是否点击了正在显示的大图本身 (用于退出查看)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             # 获取当前正在查看的图片ID
             if self.viewing_lit_image_index != -1 and self._lit_images_list:
                 current_image_id = self._lit_images_list[self.viewing_lit_image_index]
                 full_image_surface = self.image_manager.get_full_processed_image(current_image_id)

                 if full_image_surface:
                     # 缩放图片以适应屏幕，保持比例，计算 Rect
                     img_w, img_h = full_image_surface.get_size()
                     screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

                     # 计算缩放因子，以适应屏幕尺寸，保持比例，且不超出屏幕 (留边距)
                     margin = 40
                     max_scale_factor = min((screen_w - margin) / img_w, (screen_h - margin) / img_h)
                     # 确保不放大超过原始处理尺寸 (这里假设原始处理尺寸就是 full_image_surface 的尺寸), 且留白
                     scale_factor = min(1.0, max_scale_factor)

                     scaled_w = int(img_w * scale_factor)
                     scaled_h = int(img_h * scale_factor)

                     # 计算绘制位置 (居中)
                     img_rect = pygame.Rect(0, 0, scaled_w, scaled_h)
                     img_rect.center = (screen_w // 2, screen_h // 2)

                     # 检查点击位置是否在大图 Rect 范围内
                     if img_rect.collidepoint(event.pos):
                          print("点击大图本身，退出查看。") # Debug
                          self.stop_viewing_lit_image() # 退出大图查看
                          return True # 事件已被处理
                 else:
                      print(f"警告: 尝试获取图片ID {current_image_id} 的大图 surface 失败，但状态是 VIEW_LIT。") # Debug

        return False # 事件未被处理


    # def update(self, dt): # Gallery 类自身的 update 方法 (如果有动画等需要更新)
    #      # 如果列表有动画或需要随时间更新的状态
    #      if self.game.current_state == settings.GAME_STATE_GALLERY_LIST:
    #          pass # self.update_list(dt)
    #      # 如果大图查看有动画或需要随时间更新的状态
    #      elif self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
    #          # self.view_lit_buttons.update(dt) # 如果按钮有动画等
    #          pass # self.update_view_lit(dt)


    def draw(self, surface):
        """
        根据图库当前子状态 (列表或大图查看) 绘制相应的界面。
        这个方法由 Game 类在主 draw 循环中调用。
        """
        # 绘制一个半透明背景，覆盖主游戏界面
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(settings.OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        # 绘制相应的图库界面
        if self.viewing_lit_image_index != -1:
             # 绘制大图查看界面
             self.draw_view_lit(surface)
        else:
             # 绘制图库列表界面
             self.draw_list(surface)


    def draw_list(self, surface):
        """绘制图库列表界面。"""
        # 将图库窗口背景 Surface 绘制到主屏幕 Surface 上
        surface.blit(self.gallery_window_surface, self.gallery_window_rect)

        # 设置一个裁剪区域，将绘制限制在图库窗口内部的内容区域
        old_clip = surface.get_clip() # 保存旧的裁剪区域
        surface.set_clip(self._list_visible_clip_rect) # 设置新的裁剪区域到可见内容区域


        # 绘制列表内容，需要考虑滚动偏移 self.scroll_y
        # 遍历 self.pictures_in_gallery 列表中的图片信息
        for i, pic_info in enumerate(self.pictures_in_gallery):
            # 计算当前缩略图在列表内容网格中的位置 (不考虑滚动)
            row_in_list = i // settings.GALLERY_IMAGES_PER_ROW # 在列表中的行索引
            col_in_row = i % settings.GALLERY_IMAGES_PER_ROW # 在当前行中的列索引
            # 计算绘制到屏幕上的像素坐标 (相对于屏幕左上角)
            draw_x = settings.GALLERY_X + settings.GALLERY_PADDING + col_in_row * (settings.GALLERY_THUMBNAIL_WIDTH + settings.GALLERY_THUMBNAIL_GAP_X)
            draw_y = settings.GALLERY_Y + settings.GALLERY_PADDING + row_in_list * (settings.GALLERY_THUMBNAIL_HEIGHT + settings.GALLERY_THUMBNAIL_GAP_Y) - self.scroll_y # 应用滚动偏移


            # 获取缩略图 surface (ImageManager 会处理缓存和生成)
            thumbnail_surface = self.image_manager.get_thumbnail(pic_info['id'])

            if thumbnail_surface:
                # 如果是未点亮状态，将缩略图灰度化处理
                if pic_info['state'] == 'unlit':
                     # 使用 utils.grayscale_surface 工具函数
                     thumbnail_surface = utils.grayscale_surface(thumbnail_surface)

                # 绘制缩略图到屏幕 Surface 上
                surface.blit(thumbnail_surface, (draw_x, draw_y))

                # TODO: 可以绘制图片ID或状态文字 (可选)
                # if hasattr(self.game, 'font_thumbnail') and self.game.font_thumbnail:
                #     text_surface = self.game.font_thumbnail.render(f"ID:{pic_info['id']}", True, settings.WHITE)
                #     surface.blit(text_surface, (draw_x, draw_y + settings.GALLERY_THUMBNAIL_HEIGHT + 5)) # 绘制在缩略图下方

            else:
                 # 如果无法获取缩略图 surface，绘制一个占位符矩形
                 placeholder_rect = pygame.Rect(draw_x, draw_y, settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT)
                 pygame.draw.rect(surface, settings.GRAY, placeholder_rect) # 绘制灰色矩形
                 # 可选：在占位符上绘制文字，例如 "加载中..." 或 "无法加载"


        # 恢复旧的裁剪区域，以便后续绘制其他UI元素或主游戏界面
        surface.set_clip(old_clip)


    def draw_view_lit(self, surface):
        """绘制图库大图查看界面。"""
        # 检查是否正在查看已点亮大图
        if self.viewing_lit_image_index == -1 or not self._lit_images_list:
             print("警告: 尝试绘制大图查看界面，但没有图片被选中查看或已点亮图片列表为空。") # Debug
             return

        # 获取当前正在查看的图片ID
        current_image_id = self._lit_images_list[self.viewing_lit_image_index]
        # 从 ImageManager 获取完整处理后的图片 surface
        # ImageManager 会处理缓存
        full_image_surface = self.image_manager.get_full_processed_image(current_image_id)

        if full_image_surface:
            # 缩放图片以适应屏幕显示，保持比例
            img_w, img_h = full_image_surface.get_size()
            screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

            # 计算缩放因子，使其完整适应屏幕，并留有边距
            margin = 40
            # 计算能适应屏幕并留有边距的最大缩放因子
            max_scale_factor = min((screen_w - margin) / img_w, (screen_h - margin) / img_h)
            # 最终缩放因子取 1.0 和最大适应因子的最小值，确保不放大超过原始处理尺寸 (600x1080)，并遵守边距
            scale_factor = min(1.0, max_scale_factor)

            # 计算缩放后的图片尺寸
            scaled_w = int(img_w * scale_factor)
            scaled_h = int(img_h * scale_factor)

            # 确保缩放后的尺寸有效
            if scaled_w <= 0 or scaled_h <= 0:
                print(f"警告: 大图图片 {current_image_id} 缩放后尺寸无效 ({scaled_w}x{scaled_h})。") # Debug
                # 绘制一个占位符矩形
                placeholder_rect = pygame.Rect(0, 0, 200, 150) # 示例占位符大小
                placeholder_rect.center = (screen_w // 2, screen_h // 2)
                pygame.draw.rect(surface, settings.GRAY, placeholder_rect)
                # 可选：在占位符上绘制文字 "加载失败"
                return

            # 进行图片缩放
            scaled_image = pygame.transform.scale(full_image_surface, (scaled_w, scaled_h))

            # 计算绘制位置，使其在屏幕上居中
            img_rect = scaled_image.get_rect(center=(screen_w // 2, screen_h // 2))
            # 绘制缩放后的图片到屏幕 Surface 上
            surface.blit(scaled_image, img_rect)

            # 绘制左右导航按钮
            # 计算按钮位置，相对于绘制的大图 Rect
            # 按钮与大图垂直居中对齐
            # 按钮在水平方向上位于大图外部，并留有一定偏移量
            button_offset_x = max(50, (screen_w - scaled_w) // 4) # 按钮距离图片边缘或屏幕边缘的距离，取较大值确保可见
            self.left_button.rect.centery = img_rect.centery
            self.left_button.rect.right = img_rect.left - button_offset_x # 左按钮的右边缘在大图左边缘左侧

            self.right_button.rect.centery = img_rect.centery
            self.right_button.rect.left = img_rect.right + button_offset_x # 右按钮的左边缘在大图右边缘右侧

            # 绘制按钮组 (包含左右导航按钮)
            self.view_lit_buttons.draw(surface)

        else:
             # 如果无法获取完整处理后的图片 surface，绘制一个加载中或占位符文本
             # 这通常不应该发生，因为进入 VIEW_LIT 状态的前提是图片碎片已加载
             print(f"警告: 尝试获取图片ID {current_image_id} 的完整处理后图片，但 surface 为 None。") # Debug
             # 绘制提示文本 "图片加载中..."
             # 使用 Game 实例中的字体
             if hasattr(self.game, 'font_loading') and self.game.font_loading: # 检查 Game 实例和字体属性是否存在
                font = self.game.font_loading
                text_surface = font.render("图片加载中...", True, settings.WHITE)
                text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2))
                surface.blit(text_surface, text_rect)
             else:
                # 如果 Game 实例或字体不可用，使用 Pygame 默认字体作为回退
                font_fallback = pygame.font.Font(None, 40)
                text_surface = font_fallback.render("图片加载中...", True, settings.WHITE)
                text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2))
                surface.blit(text_surface, text_rect)

    # def update(self, dt): # Gallery 类自身的 update 方法 (如果 Gallery 内部有动画等需要随时间更新的状态)
    #      # 例如，如果按钮有动画效果，需要调用它们的 update 方法
    #      # if self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
    #      #      self.view_lit_buttons.update(dt)
    #      pass