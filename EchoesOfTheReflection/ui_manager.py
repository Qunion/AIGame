# ui_manager.py
import pygame
import os
from settings import Settings

# UI元素基类 (可选，用于管理通用UI属性和绘制)
class UIElement:
    def __init__(self, element_id: str, image_path: str = None, position: tuple[int, int] = (0, 0), relative_to="image_area"):
        self.id = element_id
        self.image_path = image_path
        self.surface = None # This will be loaded in _load_ui_images_to_cache

        self._original_position = position # 存储初始位置，用于相对定位
        self.relative_to = relative_to # 定位参考系："image_area", "screen", "custom_rect_id", "image_area_bottom_right" (新增示例)

        # 总是创建 rect 属性，无论是否有图片。初始尺寸可以为0，位置基于参数。
        # 尺寸将在图片加载到缓存后更新。
        self.rect = pygame.Rect(position[0], position[1], 0, 0)

        self.visible = False # 默认不可见


    def set_position(self, position: tuple[int, int]):
        """设置元素在屏幕上的绝对位置"""
        self.rect.topleft = position

    # 修正类型提示，Python 3.9+ 支持 tuple[int, int]，旧版本用 Tuple[int, int]
    def is_clicked(self, mouse_pos: tuple[int, int]) -> bool:
        """检查点击是否在元素矩形内且可见"""
        return self.visible and self.rect.collidepoint(mouse_pos)

    # draw 方法不再需要 ui_image_cache 参数
    def draw(self, screen: pygame.Surface):
        """绘制UI元素"""
        # 使用元素自身的 surface 进行绘制
        if self.visible and self.surface:
            screen.blit(self.surface, self.rect.topleft)
        # TODO: 可以添加绘制其他类型的UI元素，如进度条、文本框背景等 (如果它们不是图片)


class UIManager:
    """管理游戏中的所有UI元素"""

    def __init__(self, screen, settings: Settings, game_manager):
        """初始化UI管理器"""
        self.screen = screen
        self.settings = settings
        self.game_manager = game_manager # 需要访问 GameManager 的状态和方法

        self.ui_elements = {} # 字典 {element_id: UIElement instance}
        self.ui_image_cache = {} # UI图片资源缓存 {image_path: Pygame Surface}

        # 加载和创建UI元素
        self._load_ui_elements()
        # 加载UI图片资源到缓存，并设置UI元素的初始尺寸
        self._load_ui_images_to_cache()

        # 当前活动的UI集合 ID (例如 "game_ui", "gallery_ui")
        self.active_ui_set_id = None

        # 初始设置UI集合
        # self.set_ui_set_active("game_ui") # 由GameManager在_set_state中调用


    def _load_ui_elements(self):
        """加载所有预定义的UI元素"""
        # 加载通用UI元素
        # 前进按钮 - 示例位置 (相对于图片区域右下角偏移量)
        # 注意：这里的位置是相对偏移量，不是绝对像素坐标
        self._create_element("next_button", self.settings.UI_NEXT_BUTTON_IMAGE, (-150, -80), relative_to="image_area_bottom_right") # 新增相对定位类型

        # 加载画廊UI元素
        # 退出画廊按钮 - 示例位置 (相对于屏幕左上角偏移量)
        self._create_element("gallery_exit_button", self.settings.UI_NEXT_BUTTON_IMAGE, (50, 50), relative_to="screen") # 示例位置，复用前进按钮图片

        # TODO: 加载其他UI元素，如进度条（可能是背景和前景两个图片）
        # TODO: 添加画廊缩略图的点击区域定义（虽然绘制在GalleryManager，但点击检测可以在UIManager处理）


    def _create_element(self, element_id: str, image_path: str = None, position: tuple[int, int] = (0, 0), relative_to="image_area"):
        """创建并添加一个UI元素到管理列表"""
        element = UIElement(element_id, image_path, position, relative_to)
        self.ui_elements[element_id] = element
        return element

    def _load_ui_images_to_cache(self):
        """加载所有UI元素引用的图片资源到缓存，并设置元素的初始尺寸"""
        for element_id, element in self.ui_elements.items():
            if element.image_path: # Only process elements that have an image path
                if element.image_path not in self.ui_image_cache:
                    # 检查文件是否存在
                    if os.path.exists(element.image_path):
                        try:
                            loaded_surface = pygame.image.load(element.image_path).convert_alpha()
                            self.ui_image_cache[element.image_path] = loaded_surface # Cache the surface
                            element.surface = loaded_surface # Assign the loaded surface directly to the element
                            element.rect.size = loaded_surface.get_size() # Set the rect size based on the loaded image size
                            print(f"加载UI图片到缓存: {element.image_path}, 尺寸: {element.rect.size}")
                        except pygame.error as e:
                            print(f"警告：无法加载UI图片到缓存 {element.image_path}: {e}")
                            self.ui_image_cache[element.image_path] = None # Cache None on failure
                            element.surface = None # Assign None to element
                            # Rect size remains 0 or placeholder if image failed
                    else:
                         print(f"警告：UI图片文件未找到 {element.image_path}")
                         self.ui_image_cache[element.image_path] = None # Cache None
                         element.surface = None # Assign None
                else: # 图片已经在缓存中
                     element.surface = self.ui_image_cache.get(element.image_path) # 从缓存获取Surface
                     if element.surface:
                         element.rect.size = element.surface.get_size() # 确保rect尺寸已设置


    def set_ui_set_active(self, ui_set_id: str):
        """
        设置当前活动的UI集合。
        根据集合ID控制哪些UI元素可见。
        """
        print(f"激活UI集合: {ui_set_id}")
        self.active_ui_set_id = ui_set_id

        # 根据集合ID设置元素的可见性
        # 这是一个简化的示例，你可能需要更精细的控制哪些元素属于哪个集合
        for element_id, element in self.ui_elements.items():
             element.visible = False # 默认全部隐藏

        if ui_set_id == "game_ui":
             # 游戏中的UI，例如前进按钮 (仅当需要时才可见，由 update 方法或 NarrativeManager 控制)
             # self.set_element_visible("next_button", True) # 示例，实际由 GameManager/NarrativeManager 控制
             pass # 游戏UI元素的可见性由其他逻辑控制，但它们存在并能被激活

        elif ui_set_id == "gallery_ui":
             # 画廊中的UI
             self.set_element_visible("gallery_exit_button", True)
             # self.set_element_visible("gallery_hint", False) # 如果有画廊入口提示，进入画廊后隐藏

        elif ui_set_id == "menu_ui": # 示例菜单UI
             # self.set_element_visible("start_button", True)
             # self.set_element_visible("exit_button", True)
             pass # 待实现菜单UI


    def set_element_visible(self, element_id: str, visible: bool):
        """设置指定UI元素的可见性"""
        if element_id in self.ui_elements:
            self.ui_elements[element_id].visible = visible
        else:
            print(f"警告：尝试设置未知UI元素可见性: {element_id}")


    def handle_event(self, event, relative_rect=None) -> bool: # 调整参数名，使其更通用
        """
        处理Pygame事件，检查UI元素点击。
        返回 True 如果事件被UI处理，否则返回 False。
        relative_rect: 用于相对定位计算的参考矩形 (如 image_display_rect 或 screen_rect)
        """
        # 在处理事件前，确保UI位置是最新的，因为事件可能发生在窗口resize后
        # self._calculate_ui_positions(relative_rect) # 这个应该在update里定期调用或resize后调用，事件处理时不应修改状态

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for element_id, element in self.ui_elements.items():
                if element.visible and element.rect.collidepoint(mouse_pos): # 只检查可见元素的点击
                    # 处理UI元素的点击事件
                    # print(f"UI元素点击: {element_id} at {mouse_pos}") # 调试点击
                    self._handle_ui_click(element_id, mouse_pos)
                    return True # 事件被UI处理，不再向底层传递

        # TODO: 处理其他UI相关的事件，如鼠标悬停效果 (可能需要遍历可见元素并检查鼠标位置)

        return False # 事件未被UI处理

    def _handle_ui_click(self, element_id: str, click_pos: tuple[int, int]):
        """处理指定UI元素的点击逻辑"""
        # 根据UI元素ID触发不同的游戏操作
        if element_id == "next_button":
            # 只有当叙事文本播放完毕时，点击前进按钮才有效
            if not self.game_manager.narrative_manager.is_narrative_active():
                 self.set_element_visible("next_button", False) # 隐藏前进按钮
                 # TODO: 播放UI点击音效 sfx_ui_click
                 if self.game_manager.audio_manager:
                      self.game_manager.audio_manager.play_sfx("sfx_ui_click")
                 self.game_manager._go_to_next_image() # 通知GameManager进入下一图


        elif element_id == "gallery_exit_button":
            # 点击退出画廊按钮
             # TODO: 播放UI点击音效 sfx_ui_click
             if self.game_manager.audio_manager:
                 self.game_manager.audio_manager.play_sfx("sfx_ui_click")
             self.game_manager.gallery_manager.exit_gallery() # 通知画廊管理器退出


        # TODO: 添加其他UI元素的点击逻辑，例如菜单按钮、画廊缩略图（画廊缩略图点击由GalleryManager处理更合适）


    def update(self, current_image_display_rect: pygame.Rect):
        """更新UI元素状态 (例如位置计算，动画等)"""
        # 根据当前的图片显示区域或屏幕尺寸计算并设置相对定位UI元素的位置
        self._calculate_ui_positions(current_image_display_rect)

        # 控制前进按钮的可见性：当游戏状态，且当前图片的互动完成，且所有文本播放完毕时，前进按钮可见
        if self.game_manager.current_state == self.settings.STATE_GAME:
             # 检查当前图片是否有互动模块，以及该模块是否已完成
             is_image_interactive_complete = False
             if self.game_manager.current_image_interaction_state:
                  # 检查 _is_completed 属性是否存在且为 True
                  is_image_interactive_complete = getattr(self.game_manager.current_image_interaction_state, '_is_completed', False) # 使用getattr安全访问

             is_pure_text_image = self.game_manager.current_image_id and self.game_manager.image_configs.get(self.game_manager.current_image_id) and self.game_manager.image_configs[self.game_manager.current_image_id].get("type") in [self.settings.INTERACTION_INTRO, self.settings.INTERACTION_GALLERY_INTRO] # 引子等纯文本类型，也包括画廊入口图

             is_all_narrative_done = not self.game_manager.narrative_manager.is_narrative_active()

             # 对于非纯文本/非画廊入口图片，当互动完成且文本播放完毕时显示前进按钮
             if is_image_interactive_complete and is_all_narrative_done and not is_pure_text_image:
                  self.set_element_visible("next_button", True)
             # 对于纯文本/画廊入口图片，文本播放完毕后 GameManager 会自动跳转，不需要前进按钮
             elif is_pure_text_image and is_all_narrative_done:
                 self.set_element_visible("next_button", False) # 确保隐藏
             # 其他情况，前进按钮保持隐藏 (例如，互动未完成，文本正在播放)
             elif self.ui_elements.get("next_button", None) and self.ui_elements["next_button"].visible:
                 # 如果前进按钮当前可见，但条件不满足，隐藏它 (防止文本播放一半时按钮出现)
                 self.set_element_visible("next_button", False)


        # TODO: 更新其他UI元素的动画状态 (如果UI有动画)
        # TODO: 更新进度条的显示 (如果当前互动有进度条)


    def draw(self, screen: pygame.Surface): # draw 方法不需要 image_display_rect 参数
        """绘制所有可见的UI元素"""
        for element_id, element in self.ui_elements.items():
            # draw 方法使用元素自身的 rect 和 surface
            element.draw(screen)


    def _calculate_ui_positions(self, current_image_display_rect: pygame.Rect):
        """
        根据当前的图片显示区域或屏幕尺寸计算并设置UI元素在屏幕上的绝对位置。
        这个方法应该在窗口大小改变或图片加载时被调用。
        """
        screen_width, screen_height = self.screen.get_size()
        screen_rect = self.screen.get_rect()

        for element_id, element in self.ui_elements.items():
            if element.surface is None: # 跳过没有加载图片的元素
                 continue

            element_width, element_height = element.rect.size # 获取元素的尺寸 (已在加载时设置)

            absolute_x, absolute_y = element.rect.topleft # 默认保持当前位置

            if element.relative_to == "image_area":
                 # 相对于图片显示区域左上角定位
                 # element._original_position 是相对于图片区域左上角的偏移量 (像素)
                 absolute_x = current_image_display_rect.left + element._original_position[0]
                 absolute_y = current_image_display_rect.top + element._original_position[1]

            elif element.relative_to == "image_area_bottom_right":
                 # 相对于图片显示区域右下角定位
                 # element._original_position 是相对于图片区域右下角的偏移量 (像素) (通常是负值)
                 absolute_x = current_image_display_rect.right + element._original_position[0] - element_width # 减去元素自身宽度
                 absolute_y = current_image_display_rect.bottom + element._original_position[1] - element_height # 减去元素自身高度

            elif element.relative_to == "screen":
                 # 相对于屏幕左上角定位 (_original_position 是屏幕像素坐标)
                 absolute_x = element._original_position[0]
                 absolute_y = element._original_position[1]

            # TODO: 添加其他相对定位类型，例如 相对于某个特定矩形区域的ID "custom_rect_id"

            # 更新元素在屏幕上的位置
            element.set_position((absolute_x, absolute_y))


    # TODO: 添加保存和加载模块状态的方法 (如果UI元素状态需要保存，例如按钮是否被禁用)
    # def get_state(self):
    #     return {
    #         # "ui_element_visible_status": {id: element.visible for id, element in self.ui_elements.items()}
    #         # 简单的UI可能不需要保存状态
    #     }
    # def load_state(self, state_data):
    #      # for id, visible_status in state_data["ui_element_visible_status"].items():
    #      #    if id in self.ui_elements:
    #      #         self.ui_elements[id].visible = visible_status
    #      pass