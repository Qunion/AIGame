# gallery.py
# 管理图库界面的逻辑和绘制

import pygame
import settings
import time # 用于计时
import utils # 导入工具函数
import image_manager # 导入图像管理器
from ui_elements import Button # 导入 Button 类
import input_handler # 导入输入处理器
import math


class Gallery:
    def __init__(self, image_manager, game_instance):
        """
        初始化图库管理器。

        Args:
            image_manager (ImageManager): 图像管理器实例。
            game_instance (Game): Game实例，用于状态切换、显示提示等。
        """
        # 添加类型检查
        if not hasattr(image_manager, 'get_all_entered_pictures_status'):
            raise TypeError("传入的image_manager参数缺少get_all_entered_pictures_status方法")
        else: print("image_manager 检查通过。") # Debug
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
        # self.view_lit_buttons = input_handler.InputHandler.handle_event(self.left_button, self.right_button)

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
        print("Gallery: 正在从 ImageManager 获取图片状态列表...") # Debug <-- 新增
        all_entered_and_loaded_pictures = self.image_manager.get_all_entered_pictures_status() # ImageManager 提供的列表已包含必要信息
        print(f"Gallery: 从 ImageManager 获取到 {len(all_entered_and_loaded_pictures)} 张已入场且可用于图库的图片。") # Debug <-- 新增

        # 分离已点亮和未点亮图片
        # 已点亮的按完成时间倒序排列
        lit_pictures = sorted([p for p in all_entered_and_loaded_pictures if p['state'] == 'lit'],
                              key=lambda x: x['completion_time'], reverse=True) # 按完成时间倒序

        # 未点亮的按图片ID顺序排列
        unlit_pictures = sorted([p for p in all_entered_and_loaded_pictures if p['state'] == 'unlit'],
                                key=lambda x: x['id']) # 按ID顺序 (即文件命名顺序)

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

        print(f"Gallery: 图库列表更新完成: 共 {num_pictures} 张图 (已点亮 {len(lit_pictures)}, 未点亮 {len(unlit_pictures)})") # Debug <-- 新增
        # print(f"Gallery: 列表内容总高度: {self._list_content_height}, 最大可滚动: {self._max_scroll_y}") # Debug

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
        """
        处理图库大图查看界面的事件。

        Args:
            event (pygame.event.Event): Pygame事件对象。

        Returns:
            bool: True 表示事件已被消耗，False 表示未被Gallery的此状态处理。
        """

        # 只处理鼠标左键按下事件
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             handled_by_button = False # 标志是否有按钮处理了事件

             # 遍历 Group 中的所有按钮，并将事件传递给每个按钮处理
             # Button 类需要有 handle_event 方法并返回 True 如果事件被处理
             for button in self.view_lit_buttons:  # 遍历 Group 中的所有按钮 (Button 实例)
                 # 将事件传递给当前按钮处理
                 # Button.handle_event 方法会根据 event.pos 和 event.button 判断是否点击
                 if button.handle_event(event):  # 调用每个按钮的handle_event方法
                     handled_by_button = True # 标记事件已被处理
                     # 如果你希望一个事件只被一个按钮处理（例如点击左按钮不会同时触发右按钮的逻辑），可以在这里 break
                     # break # 假设事件只会被一个按钮处理

             # 如果点击未被任何按钮处理 (即 handled_by_button 在循环后仍为 False)
             if not handled_by_button:
                  # 任何点击在按钮外部的区域都关闭大图查看界面
                  print("点击在按钮外部，关闭大图查看界面。") # Debug
                  self.stop_viewing_lit_image() # 调用方法关闭大图查看界面
                  return True # 事件已被处理 (因为它导致了界面关闭操作)

             # 如果事件被按钮处理了 (handled_by_button 在循环后为 True)
             # 按钮的回调函数已经执行，事件被视为已被Gallery的view_lit状态处理
             return True # 事件被按钮处理了

        # 如果事件类型不是 MouseButtonDown 或未被以上逻辑处理，则未被Gallery的view_lit状态处理
        # (例如 MouseMotion, MouseButtonUp, 键盘事件等，如果这些在view_lit状态下需要处理，可以在上面添加)
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


# gallery.py

# ... 其他代码 ...

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


            # 获取缩略图 surface (ImageManager 会处理缓存)
            # 使用 is_ready_for_gallery 标志决定是否尝试获取并绘制缩略图
            if pic_info.get('is_ready_for_gallery', False): # Check if 'is_ready_for_gallery' key exists and is True
                 if pic_info['state'] == 'lit':
                     thumbnail_surface = self.image_manager.get_thumbnail(pic_info['id']) # 获取普通缩略图
                 else: # 'unlit' state
                     thumbnail_surface = self.image_manager.get_unlit_thumbnail(pic_info['id']) # 获取灰度缩略图

                 if thumbnail_surface:
                     # 绘制缩略图到屏幕 Surface 上
                     surface.blit(thumbnail_surface, (draw_x, draw_y))

                     # TODO: 可以绘制图片ID或状态文字 (可选)
                     # if hasattr(self.game, 'font_thumbnail') and self.game.font_thumbnail:
                     #     text_surface = self.game.font_thumbnail.render(f"ID:{pic_info['id']}", True, settings.WHITE)
                     #     surface.blit(text_surface, (draw_x, draw_y + settings.GALLERY_THUMBNAIL_HEIGHT + 5)) # 绘制在缩略图下方

                 else:
                      # 如果 is_ready_for_gallery 是 True 但获取缩略图失败 (不应该发生)，绘制错误占位符
                      placeholder_rect = pygame.Rect(draw_x, draw_y, settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT)
                      pygame.draw.rect(surface, (255,0,0), placeholder_rect) # 红色框表示错误
                      # Optional text: "Error"

            else:
                 # 如果 is_ready_for_gallery 是 False (碎片或缩略图未加载完成)，绘制加载中占位符
                 placeholder_rect = pygame.Rect(draw_x, draw_y, settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT)
                 pygame.draw.rect(surface, settings.GRAY, placeholder_rect) # 绘制灰色矩形作为加载中指示
                 # 可选：在占位符上绘制文字 "加载中..."
                 # if hasattr(self.game, 'font_loading') and self.game.font_loading:
                 #     font = self.game.font_loading # Use loading font or a smaller one
                 #     text_surface = font.render("加载中...", True, settings.BLACK)
                 #     text_rect = text_surface.get_rect(center=placeholder_rect.center)
                 #     surface.blit(text_surface, text_rect)


        # 恢复旧的裁剪区域，以便后续绘制其他UI元素或主游戏界面
        surface.set_clip(old_clip)
    # 注意：在允许点击图片查看大图或显示提示之前，handle_event_list 方法也应该检查 'is_ready_for_gallery' 标志。
    # 修改 _get_thumbnail_index_at_pos 方法以返回图片信息。
    # 不，应该在获取索引之后修改点击处理逻辑。

    # 修改 handle_event_list 方法，在开始查看大图或显示提示之前检查该标志
    # 用以下方法替换现有的 handle_event_list 方法：

    # 用这个方法替换现有的 handle_event_list 方法：
    def handle_event_list(self, event):
        """处理图库列表界面的事件。返回 True 表示事件被消耗，False 表示未处理。"""
        # 检查事件是否发生在图库窗口区域内
        gallery_window_rect = self.gallery_window_rect
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             if not gallery_window_rect.collidepoint(event.pos):
                 # 点击发生在图库窗口外部
                 if hasattr(self.game, 'close_gallery'):
                     self.game.close_gallery()
                 return True # 事件已处理

        # 如果事件发生在窗口内，则处理内部交互（由上述检查处理）

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左键点击
             # 检查点击了哪个缩略图
             clicked_thumbnail_index = self._get_thumbnail_index_at_pos(event.pos)
             if clicked_thumbnail_index is not None:
                 # 获取点击的图片信息
                 if 0 <= clicked_thumbnail_index < len(self.pictures_in_gallery):
                     clicked_picture_info = self.pictures_in_gallery[clicked_thumbnail_index]

                     # --- **关键修改：检查 is_ready_for_gallery 标志** ---
                     if clicked_picture_info.get('is_ready_for_gallery', False):
                         # 图片已准备好进行交互（碎片和缩略图已加载）
                         if clicked_picture_info['state'] == 'lit':
                             # 如果点击已点亮的图片，切换到大图查看模式
                             print(f"点击已准备好且已点亮的图片: ID {clicked_picture_info['id']}，切换到大图查看。") # 调试信息
                             self.start_viewing_lit_image(clicked_thumbnail_index)
                             return True # 事件已处理
                         elif clicked_picture_info['state'] == 'unlit':
                             # 如果点击未点亮的图片，显示提示
                             print(f"点击已准备好且未点亮的图片: ID {clicked_picture_info['id']}，显示提示。") # 调试信息
                             if hasattr(self.game, 'show_popup_tip'):
                                  self.game.show_popup_tip("美图尚未点亮")
                             return True # 事件已处理
                         # else: # 如果状态是已点亮或未点亮，不应该发生这种情况
                     else:
                          # 图片尚未准备好进行交互（正在后台加载）
                          print(f"点击图片 ID {clicked_picture_info['id']}，但尚未准备好进行图库交互。显示加载提示。") # 调试信息
                          if hasattr(self.game, 'show_popup_tip'):
                                  self.game.show_popup_tip("图片加载中...") # 显示不同的提示
                          return True # 事件已处理（通过显示提示）

                 # 如果点击在图库窗口内部，但不是在识别的缩略图上（get_thumbnail_index_at_pos 返回 None）
                 return False # 特定图片未处理该事件

        elif event.type == pygame.MOUSEWHEEL: # 鼠标滚轮事件
            # 确保鼠标在图库窗口区域内时，滚轮事件才有效
            if gallery_window_rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_y -= event.y * settings.GALLERY_SCROLL_SPEED
                self.scroll_y = max(0, self.scroll_y)
                self.scroll_y = min(self._max_scroll_y, self.scroll_y)
                # print(f"滚动图库列表，新的 scroll_y: {self.scroll_y}") # 调试信息
                return True # 事件已处理

        # 如果此方法未处理该事件类型，则返回 False
        return False
# gallery.py
# ... (保留文件开头的导入和类定义等不变) ...

    def draw_view_lit(self, surface):
        """绘制图库大图查看界面。"""
        # 检查是否正在查看已点亮大图
        # Ensure the index is valid within _lit_images_list
        if self.viewing_lit_image_index == -1 or not self._lit_images_list or not (0 <= self.viewing_lit_image_index < len(self._lit_images_list)):
             # print("警告: 尝试绘制大图查看界面，但状态无效。") # Debug
             self.viewing_lit_image_index = -1 # Reset state
             return

        # 获取当前正在查看的图片ID
        current_image_id = self._lit_images_list[self.viewing_lit_image_index]

        # === 关键修改：直接从 ImageManager 获取原始图片文件路径并加载 ===
        # ImageManager stores the file paths of all scanned original images
        original_image_filepath = self.image_manager.all_image_files.get(current_image_id)

        original_image_surface = None # Surface to be drawn
        if original_image_filepath:
             try:
                 # Load the original image directly from the file path
                 original_image_surface = pygame.image.load(original_image_filepath).convert_alpha()
                 # print(f"Gallery: draw_view_lit: 成功加载原始图片文件 {original_image_filepath}") # Debug
             except pygame.error as e:
                  print(f"错误: Gallery: draw_view_lit: Pygame无法加载原始图片文件 {original_image_filepath}: {e}") # Debug
                  original_image_surface = None # Loading failed
             except Exception as e:
                  print(f"错误: Gallery: draw_view_lit: 加载原始图片文件 {original_image_filepath} 时发生未知错误: {e}") # Debug
                  original_image_surface = None # Loading failed
        else:
             print(f"警告: Gallery: draw_view_lit: 图片ID {current_image_id} 的原始文件路径未知。") # Debug


        if original_image_surface:
            # Scale the loaded original image to fit the screen, maintaining aspect ratio
            img_w, img_h = original_image_surface.get_size()
            screen_w, screen_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

            # Calculate scale factor to fit within the screen boundaries with margins
            margin = 80 # Ensure buttons have space
            # Calculate the maximum scale factor to fit within the screen boundaries with margins
            max_scale_factor = min((screen_w - margin) / img_w, (screen_h - margin) / img_h)
            # We allow scaling UP if needed to fill the screen space better, maintaining aspect ratio.
            scale_factor = max_scale_factor

            # Ensure scale factor is valid
            if scale_factor <= 0 or not math.isfinite(scale_factor): # Check for non-positive or infinite scale
                 print(f"警告: 大图图片 {current_image_id} 计算出的缩放因子无效 ({scale_factor})。") # Debug
                 # Use a default valid scale or fallback
                 scale_factor = 1.0 # Default to no scaling

            # Calculate scaled image dimensions
            scaled_w = int(img_w * scale_factor)
            scaled_h = int(img_h * scale_factor)

            # Ensure scaled dimensions are valid and non-zero
            if scaled_w <= 0 or scaled_h <= 0:
                print(f"警告: 大图图片 {current_image_id} 缩放后尺寸无效 ({scaled_w}x{scaled_h})。") # Debug
                # Draw a placeholder rectangle
                placeholder_rect = pygame.Rect(0, 0, 200, 150) # Example placeholder size
                placeholder_rect.center = (screen_w // 2, screen_h // 2)
                pygame.draw.rect(surface, settings.GRAY, placeholder_rect) # Draw a gray rectangle
                # Optional text: "无法显示图片"
                if hasattr(self.game, 'font_tip') and self.game.font_tip:
                     font = self.game.font_tip
                     text_surface = font.render("无法显示图片", True, settings.WHITE)
                     text_rect = text_surface.get_rect(center=placeholder_rect.center)
                     surface.blit(text_surface, text_rect)
                return

            # Perform image scaling
            try:
                scaled_image = pygame.transform.scale(original_image_surface, (scaled_w, scaled_h))
            except pygame.error as e:
                print(f"错误: 大图图片 {current_image_id} 缩放失败: {e}") # Debug
                # Fallback to placeholder
                placeholder_rect = pygame.Rect(0, 0, scaled_w, scaled_h) # Use calculated invalid size
                placeholder_rect.center = (screen_w // 2, screen_h // 2)
                pygame.draw.rect(surface, settings.GRAY, placeholder_rect)
                if hasattr(self.game, 'font_tip') and self.game.font_tip:
                     font = self.game.font_tip
                     text_surface = font.render("缩放失败", True, settings.WHITE)
                     text_rect = text_surface.get_rect(center=placeholder_rect.center)
                     surface.blit(text_surface, text_rect)
                return
            except Exception as e:
                print(f"错误: 大图图片 {current_image_id} 缩放发生未知错误: {e}") # Debug
                # Fallback to placeholder
                placeholder_rect = pygame.Rect(0, 0, scaled_w, scaled_h) # Use calculated invalid size
                placeholder_rect.center = (screen_w // 2, screen_h // 2)
                pygame.draw.rect(surface, settings.GRAY, placeholder_rect)
                if hasattr(self.game, 'font_tip') and self.game.font_tip:
                     font = self.game.font_tip
                     text_surface = font.render("缩放错误", True, settings.WHITE)
                     text_rect = text_surface.get_rect(center=placeholder_rect.center)
                     surface.blit(text_surface, text_rect)
                return


            # Calculate draw position to center it on the screen
            img_rect = scaled_image.get_rect(center=(screen_w // 2, screen_h // 2))
            # Draw the scaled image onto the main surface
            surface.blit(scaled_image, img_rect)

            # Draw left/right navigation buttons
            # Calculate button positions relative to the drawn large image Rect
            # Buttons should be vertically centered with the large image
            # Buttons are horizontally placed outside the large image, with some offset
            button_offset_x = max(40, (screen_w - scaled_w) // 4) # Offset from image edge, ensuring visibility

            # Ensure buttons exist and are in the view_lit_buttons group before positioning/drawing
            if self.left_button in self.view_lit_buttons: # Check if in group
                self.left_button.rect.centery = img_rect.centery
                self.left_button.rect.right = img_rect.left - button_offset_x # Right edge of left button is left of image left edge

            if self.right_button in self.view_lit_buttons: # Check if in group
                self.right_button.rect.centery = img_rect.centery
                self.right_button.rect.left = img_rect.right + button_offset_x # Left edge of right button is right of image right edge


            # Draw the button group (containing left/right navigation buttons)
            # Ensure the sprite group is valid before drawing
            if isinstance(self.view_lit_buttons, pygame.sprite.Group):
                 self.view_lit_buttons.draw(surface)
            # else: print("警告: Gallery.view_lit_buttons 不是 Sprite Group，无法绘制按钮。") # Debug

        else:
             # If unable to get the original full image surface (file not found or loading failed)
             print(f"警告: 尝试绘制图片ID {current_image_id} 的原始图片，但 surface 为 None (文件加载失败)。") # Debug
             # Draw "Image Loading..." or similar text
             # Use Game instance's font
             if hasattr(self.game, 'font_loading') and self.game.font_loading: # Check if Game instance and font attribute exist
                font = self.game.font_loading
                text_surface = font.render("图片加载失败", True, settings.WHITE) # Change text to indicate failure
                text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2))
                surface.blit(text_surface, text_rect)
             else:
                # If Game instance or font not available, use Pygame default font as fallback
                font_fallback = pygame.font.Font(None, 40)
                text_surface = font_fallback.render("图片加载失败", True, settings.WHITE) # Change text
                text_rect = text_surface.get_rect(center=(settings.SCREEN_WIDTH//2, settings.SCREEN_HEIGHT//2))
                surface.blit(text_surface, text_rect)

    # def update(self, dt): # Gallery 类自身的 update 方法 (如果 Gallery 内部有动画等需要随时间更新的状态)
    #      # 例如，如果按钮有动画效果，需要调用它们的 update 方法
    #      # if self.game.current_state == settings.GAME_STATE_GALLERY_VIEW_LIT:
    #      #      self.view_lit_buttons.update(dt)
    #      pass