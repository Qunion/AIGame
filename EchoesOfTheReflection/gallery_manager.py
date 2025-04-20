# gallery_manager.py
import pygame
import os
import json
# 修正导入路径，Settings, ImageRenderer, NarrativeManager, AudioManager 都在根目录
from settings import Settings
from image_renderer import ImageRenderer
from narrative_manager import NarrativeManager
from audio_manager import AudioManager
# 导入 GameManager 类型提示，避免循环引用
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_manager import GameManager


class GalleryManager:
    """管理画廊界面，显示已解锁图片并允许回顾"""

    def __init__(self, screen, settings: Settings, game_manager: 'GameManager'): # 明确game_manager的类型提示
        """初始化画廊管理器"""
        self.screen = screen
        self.settings = settings
        self.game_manager = game_manager # 需要GameManager引用来获取已解锁图片、文本和 AudioManager

        # 确保 GameManager 已将自身引用赋给 settings.game_manager (GameManager.__init__ 中已做)
        # 否则，如果 NarrativeManager 在初始化时需要通过 settings 访问 game_manager，可能会有问题

        self.unlocked_images = {} # 从GameManager获取的已解锁图片 {image_id: True}
        # 使用 GameManager 加载 image_configs，确保一致性
        self.image_configs = self.game_manager.image_configs # 从game_manager获取加载好的图片配置

        self.thumbnails = [] # Pygame Surface列表，用于绘制缩略图
        self.thumbnail_rects = [] # 每个缩略图在屏幕上的 Rect
        self.thumbnail_image_ids = [] # 每个缩略图对应的图片ID

        self.displaying_detail = False # 是否正在显示单张大图和文本
        self.detail_image_id = None # 正在显示的详情图片ID
        self.detail_image_surface = None # 详情大图Surface
        # 修复 TypeError: NarrativeManager.__init__() 缺少 audio_manager 参数
        # 通过 self.game_manager 获取 audio_manager 实例并传递
        self.detail_text_manager = NarrativeManager(screen, settings, self.game_manager.audio_manager) # 独立的叙事管理器用于详情文本


        # 布局参数 (使用 settings 中的配置)
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
        self.detail_text_manager.current_texts_ids = [] # 清空正在播放的文本ID列表 (修正属性名)

        # TODO: 播放画廊背景音乐
        # 示例文件名，你需要根据实际资源命名规则调整
        # bgm_file = "bgm_gallery.ogg"
        # bgm_path = os.path.join(self.settings.AUDIO_DIR, bgm_file)
        # self.settings.audio_manager.play_bgm(bgm_path) # 使用settings中的audio_manager

        # 触发画廊进入文本 (如果配置了)
        intro_config = self.image_configs.get("gallery_intro")
        if intro_config and "on_stage_enter" in intro_config.get("narrative_triggers", {}):
             # start_narrative 方法不再需要 get_ai_sound_callback 参数
             self.detail_text_manager.start_narrative(intro_config["narrative_triggers"]["on_stage_enter"])


    def _generate_thumbnails(self):
        """生成所有已解锁图片的缩略图"""
        self.thumbnails = []
        self.thumbnail_rects = []
        self.thumbnail_image_ids = []

        unlocked_image_ids = list(self.unlocked_images.keys())
        # 排序以便缩略图顺序一致
        # 可以按阶段和图片索引排序，如果 image_config 中有这些字段且可以转换为数字
        def sort_key(image_id):
             config = self.image_configs.get(image_id)
             if config:
                  # 示例排序：先按阶段，再按索引
                  stage_order = config.get("stage", float('inf')) # 无阶段的放最后
                  index_order = config.get("index", float('inf')) # 无索引的放最后
                  return (stage_order, index_order)
             return (float('inf'), float('inf')) # 无配置的放最后

        unlocked_image_ids.sort(key=sort_key)


        current_x = self.start_x
        current_y = self.start_y
        row_count = 0
        screen_width = self.screen.get_width() # 获取当前屏幕宽度来计算布局

        for image_id in unlocked_image_ids:
            config = self.image_configs.get(image_id)
            # 跳过没有文件的配置，以及画廊入口图本身 (它不是普通缩略图)
            if config and config.get("file") and image_id != "gallery_intro":
                 try:
                     # 加载原始图片，缩放到缩略图尺寸
                     original_image_path = os.path.join(self.settings.IMAGE_DIR, config["file"])
                     original_image = pygame.image.load(original_image_path).convert_alpha()

                     # 缩略图裁剪和缩放策略：保持比例，短边匹配，长边裁剪
                     original_width, original_height = original_image.get_size()
                     original_aspect = original_width / original_height
                     target_width, target_height = self.settings.GALLERY_THUMBNAIL_SIZE
                     target_aspect = target_width / target_height

                     if original_aspect > target_aspect:
                         # 原始图片更宽，匹配目标高度，裁剪宽度
                         scaled_height = target_height
                         scaled_width = int(scaled_height * original_aspect)
                         scaled_image = pygame.transform.scale(original_image, (scaled_width, scaled_height))
                         crop_width = scaled_width - target_width
                         thumbnail_surface = scaled_image.subsurface(pygame.Rect(crop_width // 2, 0, target_width, target_height))
                     else:
                         # 原始图片更高或同比例，匹配目标宽度，裁剪高度
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
                     # 检查是否达到每行最大数量，并且下一张图的位置会超出屏幕宽度
                     if row_count >= self.settings.GALLERY_THUMBNAILS_PER_ROW or (current_x + target_width + self.settings.GALLERY_PADDING > screen_width and row_count > 0): # 如果下一张超出屏幕且当前行有图，就换行
                         current_x = self.start_x
                         current_y += target_height + self.thumbnail_spacing_y
                         row_count = 0

                 except pygame.error as e:
                     print(f"警告：无法加载或处理缩略图 {image_id}: {e}")
                     # TODO: 绘制一个占位符缩略图
                 except Exception as e:
                     print(f"处理缩略图 {image_id} 时发生未知错误: {e}")
                     # TODO: 绘制一个占位符缩略图


    def handle_event(self, event):
        """处理画廊界面的事件"""
        # UIManager 已经处理了画廊UI按钮（如退出按钮）的点击，这里只处理缩略图点击
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.displaying_detail:
                # 如果正在显示详情，点击任意处返回画廊网格
                self._hide_image_detail()
                # TODO: 播放返回音效
                if self.settings.audio_manager:
                     self.settings.audio_manager.play_sfx("sfx_ui_back")

            else:
                # 检查是否点击了某个缩略图
                clicked_image_id = self.get_clicked_thumbnail_id(mouse_pos)
                if clicked_image_id:
                    self.display_image_detail(clicked_image_id)
                    # TODO: 播放点击缩略图音效
                    if self.settings.audio_manager:
                         self.settings.audio_manager.play_sfx("sfx_ui_click")


    def update(self):
        """更新画廊状态"""
        if self.displaying_detail:
            # 更新详情文本的播放
            # NarrativeManager.update 返回是否活跃，用于控制画廊详情页的文本播放状态
            narrative_is_active = self.detail_text_manager.update()
            # TODO: 如果画廊详情文本播放完毕，可能需要显示一个返回按钮
            # if not narrative_is_active:
            #    self.settings.game_manager.ui_manager.set_element_visible("gallery_detail_back_button", True)

        else:
            # 更新缩略图或其他画廊元素的动画 (可选)
            pass

    def draw(self, screen: pygame.Surface):
        """绘制画廊界面"""
        # TODO: 绘制画廊背景
        # 可以使用 GameManager 的 image_renderer 绘制横屏背景
        self.game_manager.image_renderer.draw_background(screen.get_size()) # 使用GameManager的image_renderer绘制背景


        if self.displaying_detail:
            # 绘制详情大图
            if self.detail_image_surface:
                 # 详情大图也需要缩放以适应屏幕的16:9游戏区域，并居中
                 screen_width, screen_height = screen.get_size()
                 img_width, img_height = self.detail_image_surface.get_size()

                 # 计算适应屏幕16:9游戏区域的尺寸和位置
                 # 游戏区域是与屏幕同高同宽的16:9区域，居中
                 game_area_width = int(screen_height * self.settings.ASPECT_RATIO)
                 game_area_height = screen_height
                 if game_area_width > screen_width:
                      game_area_width = screen_width
                      game_area_height = int(screen_width / self.settings.ASPECT_RATIO)

                 game_area_rect = pygame.Rect(
                      (screen_width - game_area_width) // 2,
                      (screen_height - game_area_height) // 2,
                      game_area_width,
                      game_area_height
                 )

                 # 在游戏区域内居中显示详情大图，保持原图比例，缩放到游戏区域允许的最大尺寸
                 scale_factor = min(game_area_rect.width / img_width, game_area_rect.height / img_height)
                 display_width = int(img_width * scale_factor)
                 display_height = int(img_height * scale_factor)
                 display_x = game_area_rect.left + (game_area_rect.width - display_width) // 2
                 display_y = game_area_rect.top + (game_area_rect.height - display_height) // 2
                 display_rect = pygame.Rect(display_x, display_y, display_width, display_height)

                 scaled_detail_image = pygame.transform.scale(self.detail_image_surface, display_rect.size)
                 screen.blit(scaled_detail_image, display_rect.topleft)


            # 绘制详情文本
            # 文本绘制位置需要调整，可能在详情图下方或屏幕底部
            # 复用 NarrativeManager 的绘制逻辑，但传递详情图的显示区域作为参考
            # 如果详情图未加载，传递游戏区域作为参考
            text_ref_rect = display_rect if self.detail_image_surface else game_area_rect
            self.detail_text_manager.draw(screen, text_ref_rect)

            # TODO: 绘制返回按钮或提示 (由 UIManager 处理)
            # self.settings.ui_manager.draw_button("gallery_detail_back_button") # 示例

        else:
            # 绘制缩略图网格
            for i, thumbnail_surface in enumerate(self.thumbnails):
                rect = self.thumbnail_rects[i]
                screen.blit(thumbnail_surface, rect.topleft)

                # TODO: 绘制缩略图上的ID或标题 (可选)
                # TODO: 绘制缩略图边框或高亮 (可选)

            # TODO: 绘制画廊退出按钮 (由 UIManager 处理) - UIManager 会自己绘制可见的UI元素


    def get_clicked_thumbnail_id(self, mouse_pos) -> str | None:
        """检查鼠标位置是否点击了某个缩略图，返回其图片ID"""
        # 只有在没有显示详情时才检测缩略图点击
        if not self.displaying_detail:
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
                  # 避免重复添加同一个文本ID
                  for text_id in text_ids:
                       if text_id not in all_related_text_ids:
                           all_related_text_ids.append(text_id)


        # TODO: 需要一个方法来按故事顺序或文本ID顺序对文本进行排序
        # 最简单的：按文本ID字符串排序（如果编号规则合适）
        # better: 在 image_config 中定义文本内容和顺序，或者在单独的文本文件中
        # 让我们假设 text_ids 列表本身就是按顺序的，并且在收集时保持了原始顺序
        # 如果需要按阶段和索引排序，需要更复杂的逻辑，例如：
        # sorted_text_ids = self._sort_text_ids_by_story_order(all_related_text_ids) # TODO: 实现排序方法
        # self.detail_text_manager.start_narrative(sorted_text_ids)

        self.detail_text_manager.start_narrative(all_related_text_ids) # 在详情界面播放所有相关文本


    def _hide_image_detail(self):
        """隐藏图片详情，返回画廊网格"""
        print("隐藏画廊图片详情")
        self.displaying_detail = False
        self.detail_image_id = None
        self.detail_image_surface = None
        self.detail_text_manager.current_texts_ids = [] # 清空正在播放的文本ID列表
        self.detail_text_manager._is_playing_text = False
        self.detail_text_manager._is_waiting_after_text = False


    def exit_gallery(self):
        """退出画廊，返回游戏主流程"""
        print("退出画廊")
        # 确保隐藏详情页
        self._hide_image_detail()
        # TODO: 停止画廊背景音乐
        if self.settings.audio_manager:
             self.settings.audio_manager.stop_bgm()
        # 返回游戏主流程的最后一个状态或一个特定状态 (例如，主菜单)
        # 根据设计，Stage 6.2 完成后进入画廊，退出画廊就是退出游戏
        self.game_manager._quit_game()