# src/gallery_manager.py
import pygame
import os
import json
from settings import Settings
from image_renderer import ImageRenderer
from narrative_manager import NarrativeManager

class GalleryManager:
    """管理画廊界面，显示已解锁图片并允许回顾"""

    def __init__(self, screen, settings: Settings, game_manager):
        """初始化画廊管理器"""
        self.screen = screen
        self.settings = settings
        self.game_manager = game_manager # 需要GameManager引用来获取已解锁图片和文本

        self.unlocked_images = {} # 从GameManager获取的已解锁图片 {image_id: True}
        self.image_configs = game_manager._load_image_configs() # 需要访问所有图片配置来获取文件路径和文本

        self.thumbnails = [] # Pygame Surface列表，用于绘制缩略图
        self.thumbnail_rects = [] # 每个缩略图在屏幕上的 Rect
        self.thumbnail_image_ids = [] # 每个缩略图对应的图片ID

        self.displaying_detail = False # 是否正在显示单张大图和文本
        self.detail_image_id = None # 正在显示的详情图片ID
        self.detail_image_surface = None # 详情大图Surface
        self.detail_text_manager = NarrativeManager(screen, settings) # 独立的叙事管理器用于详情文本

        # 布局参数
        self.start_x = self.settings.GALLERY_PADDING
        self.start_y = self.settings.GALLERY_PADDING
        self.thumbnail_spacing_x = 20 # 缩略图水平间距
        self.thumbnail_spacing_y = 20 # 缩略图垂直间距


    def enter_gallery(self, unlocked_images: dict):
        """进入画廊，加载并准备缩略图"""
        print("进入画廊")
        self.unlocked_images = unlocked_images
        self._generate_thumbnails()
        self.displaying_detail = False
        self.detail_image_id = None
        self.detail_image_surface = None
        self.detail_text_manager.current_texts = [] # 清空文本

        # TODO: 播放画廊背景音乐
        # self.settings.audio_manager.play_bgm("bgm_gallery.ogg") # 示例

        # 触发画廊进入文本 (如果配置了)
        intro_config = self.image_configs.get("gallery_intro")
        if intro_config and "on_stage_enter" in intro_config.get("narrative_triggers", {}):
             self.detail_text_manager.start_narrative(intro_config["narrative_triggers"]["on_stage_enter"], self.game_manager._get_ai_sound_for_text_id) # 复用detail_text_manager


    def _generate_thumbnails(self):
        """生成所有已解锁图片的缩略图"""
        self.thumbnails = []
        self.thumbnail_rects = []
        self.thumbnail_image_ids = []

        unlocked_image_ids = list(self.unlocked_images.keys())
        unlocked_image_ids.sort() # 按某种顺序排序，例如图片ID字符串或根据Stage/Index排序

        current_x = self.start_x
        current_y = self.start_y
        row_count = 0

        for image_id in unlocked_image_ids:
            config = self.image_configs.get(image_id)
            if config and config.get("file"):
                 try:
                     # 加载原始图片，缩放到缩略图尺寸
                     original_image_path = os.path.join(self.settings.IMAGE_DIR, config["file"])
                     original_image = pygame.image.load(original_image_path).convert_alpha()

                     # 缩略图裁剪和缩放策略：保持比例，短边匹配，长边裁剪
                     original_aspect = original_image.get_width() / original_image.get_height()
                     target_width, target_height = self.settings.GALLERY_THUMBNAIL_SIZE
                     target_aspect = target_width / target_height

                     if original_aspect > target_aspect:
                         # 原始图片更宽，匹配高度，裁剪宽度
                         scaled_height = target_height
                         scaled_width = int(scaled_height * original_aspect)
                         scaled_image = pygame.transform.scale(original_image, (scaled_width, scaled_height))
                         crop_width = scaled_width - target_width
                         thumbnail_surface = scaled_image.subsurface(pygame.Rect(crop_width // 2, 0, target_width, target_height))
                     else:
                         # 原始图片更高或同比例，匹配宽度，裁剪高度
                         scaled_width = target_width
                         scaled_height = int(scaled_width / original_aspect)
                         scaled_image = pygame.transform.scale(original_image, (scaled_width, scaled_height))
                         crop_height = scaled_height - target_height
                         thumbnail_surface = scaled_image.subsurface(pygame.Rect(0, crop_height // 2, target_width, target_height))

                     # TODO: 可以在缩略图上叠加一个“已解锁”标记或边框 (使用UI图片资源)

                     self.thumbnails.append(thumbnail_surface)
                     rect = pygame.Rect(current_x, current_y, target_width, target_height)
                     self.thumbnail_rects.append(rect)
                     self.thumbnail_image_ids.append(image_id)

                     # 计算下一个位置
                     current_x += target_width + self.thumbnail_spacing_x
                     row_count += 1
                     if row_count >= self.settings.GALLERY_THUMBNAILS_PER_ROW:
                         current_x = self.start_x
                         current_y += target_height + self.thumbnail_spacing_y
                         row_count = 0

                 except pygame.error as e:
                     print(f"警告：无法加载或处理缩略图 {image_id}: {e}")
                     # TODO: 绘制一个占位符缩略图

    def handle_event(self, event):
        """处理画廊界面的事件"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.displaying_detail:
                # 如果正在显示详情，点击任意处返回画廊网格
                self._hide_image_detail()
                # TODO: 播放返回音效
                # self.settings.audio_manager.play_sfx("sfx_ui_back")
            else:
                # 检查是否点击了某个缩略图
                clicked_image_id = self.get_clicked_thumbnail_id(mouse_pos)
                if clicked_image_id:
                    self.display_image_detail(clicked_image_id)
                    # TODO: 播放点击缩略图音效
                    # self.settings.audio_manager.play_sfx("sfx_ui_click")


        # TODO: 处理画廊退出按钮的点击事件 (由 UIManager 处理)
        # if self.settings.ui_manager.is_button_clicked("gallery_exit_button", mouse_pos):
        #    self.exit_gallery()


    def update(self):
        """更新画廊状态"""
        if self.displaying_detail:
            self.detail_text_manager.update() # 更新详情文本的播放
        else:
            # 更新缩略图或其他画廊元素的动画 (可选)
            pass

    def draw(self, screen: pygame.Surface):
        """绘制画廊界面"""
        # TODO: 绘制画廊背景 (可以与游戏背景不同，或者使用游戏背景但效果不同)
        # self.game_manager.image_renderer.draw_background() # 使用游戏背景示例
        screen.fill(self.settings.BLACK) # 简单黑色背景

        if self.displaying_detail:
            # 绘制详情大图
            if self.detail_image_surface:
                 # 详情大图也需要缩放以适应屏幕，并居中
                 screen_width, screen_height = screen.get_size()
                 img_width, img_height = self.detail_image_surface.get_size()
                 # 保持原图比例，缩放到屏幕允许的最大尺寸并居中
                 scale_factor = min(screen_width / img_width, screen_height / img_height)
                 display_width = int(img_width * scale_factor)
                 display_height = int(img_height * scale_factor)
                 display_x = (screen_width - display_width) // 2
                 display_y = (screen_height - display_height) // 2
                 display_rect = pygame.Rect(display_x, display_y, display_width, display_height)

                 scaled_detail_image = pygame.transform.scale(self.detail_image_surface, display_rect.size)
                 screen.blit(scaled_detail_image, display_rect.topleft)

            # 绘制详情文本
            self.detail_text_manager.draw(screen) # 文本绘制位置需要调整，可能在详情图下方

            # TODO: 绘制返回按钮或提示
            # self.settings.ui_manager.draw_button("back_button") # 示例


        else:
            # 绘制缩略图网格
            for i, thumbnail_surface in enumerate(self.thumbnails):
                rect = self.thumbnail_rects[i]
                screen.blit(thumbnail_surface, rect.topleft)

                # TODO: 绘制缩略图上的ID或标题 (可选)
                # TODO: 绘制缩略图边框或高亮 (可选)

            # TODO: 绘制画廊退出按钮 (由 UIManager 处理)
            # self.settings.ui_manager.draw_button("gallery_exit_button")

    def get_clicked_thumbnail_id(self, mouse_pos) -> str | None:
        """检查鼠标位置是否点击了某个缩略图，返回其图片ID"""
        for i, rect in enumerate(self.thumbnail_rects):
            if rect.collidepoint(mouse_pos):
                return self.thumbnail_image_ids[i]
        return None

    def display_image_detail(self, image_id):
        """显示指定图片的大图和所有相关文本"""
        print(f"显示画廊图片详情: {image_id}")
        self.displaying_detail = True
        self.detail_image_id = image_id

        config = self.image_configs.get(image_id)
        if config and config.get("file"):
             try:
                 # 加载原始图片用于详情显示
                 original_image_path = os.path.join(self.settings.IMAGE_DIR, config["file"])
                 self.detail_image_surface = pygame.image.load(original_image_path).convert_alpha()
             except pygame.error as e:
                 print(f"警告：无法加载详情图片 {image_id}: {e}")
                 self.detail_image_surface = None # 加载失败

        # 收集与该图片相关的所有叙事文本ID
        all_related_text_ids = []
        if "narrative_triggers" in config:
             for trigger_type, text_ids in config["narrative_triggers"].items():
                  all_related_text_ids.extend(text_ids)

        # TODO: 需要一个方法来按故事顺序或文本ID顺序对文本进行排序
        # 最简单的：按文本ID字符串排序（如果编号规则合适）
        # better: 在 image_config 中定义文本内容和顺序，或者在单独的文本文件中
        # 让我们假设 text_ids 列表本身就是按顺序的

        self.detail_text_manager.start_narrative(all_related_text_ids, self.game_manager._get_ai_sound_for_text_id) # 在详情界面播放所有相关文本


    def _hide_image_detail(self):
        """隐藏图片详情，返回画廊网格"""
        print("隐藏画廊图片详情")
        self.displaying_detail = False
        self.detail_image_id = None
        self.detail_image_surface = None
        self.detail_text_manager.current_texts = [] # 清空正在播放的文本

    def exit_gallery(self):
        """退出画廊，返回游戏主流程"""
        print("退出画廊")
        # TODO: 停止画廊背景音乐
        # self.settings.audio_manager.stop_bgm()
        # 返回游戏主流程的最后一个状态或一个特定状态 (例如，主菜单)
        # self.game_manager._set_state(self.settings.STATE_MENU) # 示例返回菜单
        # 如果通关后直接进入画廊，退出画廊就是退出游戏
        self.game_manager._quit_game() # 示例退出游戏