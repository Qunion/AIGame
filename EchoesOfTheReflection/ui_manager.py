# ui_manager.py
import pygame
import os
# 导入自定义模块 - 它们现在位于根目录
from settings import Settings

# UI元素基类 (可选，用于管理通用UI属性和绘制)
class UIElement:
    def __init__(self, element_id: str, image_path: str = None, position: tuple[int, int] = (0, 0), relative_to="image_area"):
        self.id = element_id
        self.image_path = image_path # UI图片文件路径
        self.surface = None # Pygame Surface (从缓存获取)
        self._original_position = position # 存储初始位置偏移量 (像素或相对比例)
        self.relative_to = relative_to # 定位参考系："image_area", "screen", "image_area_bottom_right" (或其他自定义区域ID)

        # 初始矩形大小为0，后续根据图片加载和定位计算
        # 即使没有图片，也需要一个Rect来定义点击区域或文本绘制区域
        # self.rect = pygame.Rect(position[0], position[1], 0, 0)

        self.visible = False # 默认不可见

        # Rect的尺寸将在UIManager._load_ui_images_to_cache 或 UIManager._calculate_ui_positions 中设置

    def set_position(self, position: tuple[int, int]):
        """设置元素在屏幕上的绝对位置 (topleft)"""
        self.rect.topleft = position

    def is_clicked(self, mouse_pos: tuple[int, int]) -> bool:
        """检查点击是否在元素矩形内且可见"""
        return self.visible and self.rect.collidepoint(mouse_pos)

    def draw(self, screen: pygame.Surface, ui_image_cache: dict): # 传递图片缓存
        """绘制UI元素"""
        if self.visible:
            # 从缓存获取图片Surface
            self.surface = ui_image_cache.get(self.image_path) # 在UIManager加载时填充缓存

            if self.surface:
                 # 绘制时才根据当前rect位置绘制
                 screen.blit(self.surface, self.rect.topleft)

            # TODO: 可以添加绘制其他类型的UI元素，如进度条、文本框背景等 (如果它们不是图片资源)


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
        # 加载UI图片资源到缓存
        self._load_ui_images_to_cache()

        # 当前活动的UI集合 ID (例如 "game_ui", "gallery_ui")
        self.active_ui_set_id = None

        # 初始设置UI集合
        # self.set_ui_set_active("game_ui") # 由GameManager在_set_state中调用


    def _load_ui_elements(self):
        """加载所有预定义的UI元素"""
        # 加载通用UI元素
        # 前进按钮 - 示例位置 (相对于图片区域右下角偏移量)
        # 假设前进按钮图片尺寸 100x50
        self._create_element("next_button", self.settings.UI_NEXT_BUTTON_IMAGE, (-100, -50), relative_to="image_area_bottom_right") # 偏移量是元素右下角相对于参考区域右下角


        # 加载画廊UI元素
        # 退出画廊按钮 - 示例位置 (相对于屏幕左上角偏移量)
        # 假设退出按钮图片尺寸 100x50
        self._create_element("gallery_exit_button", self.settings.UI_GALLERY_EXIT_BUTTON_IMAGE, (50, 50), relative_to="screen") # 偏移量是元素左上角相对于参考区域左上角

        # TODO: 加载其他UI元素，如进度条（可能是背景和前景两个图片）
        # TODO: 添加画廊缩略图的点击区域定义（虽然绘制在GalleryManager，但点击检测可以在UIManager处理）


    def _create_element(self, element_id: str, image_path: str = None, position: tuple[int, int] = (0, 0), relative_to="image_area"):
        """创建并添加一个UI元素到管理列表"""
        element = UIElement(element_id, image_path, position, relative_to)
        self.ui_elements[element_id] = element
        return element

    def _load_ui_images_to_cache(self):
        """加载所有UI元素引用的图片资源到缓存"""
        for element_id, element in self.ui_elements.items():
            if element.image_path and element.image_path not in self.ui_image_cache:
                if os.path.exists(element.image_path):
                    try:
                        self.ui_image_cache[element.image_path] = pygame.image.load(element.image_path).convert_alpha()
                        # 在加载时就计算图片的原始尺寸，并更新元素的 Rect 尺寸
                        element.rect.size = self.ui_image_cache[element.image_path].get_size()
                        print(f"加载UI图片到缓存: {element.image_path}, 尺寸: {element.rect.size}")
                    except pygame.error as e:
                        print(f"警告：无法加载UI图片到缓存 {element.image_path}: {e}")
                        self.ui_image_cache[element.image_path] = None # 加载失败


    def set_ui_set_active(self, ui_set_id: str):
        """
        设置当前活动的UI集合。
        根据集合ID控制哪些UI元素可见。
        """
        print(f"激活UI集合: {ui_set_id}")
        self.active_ui_set_id = ui_set_id

        # 根据集合ID设置元素的可见性
        # 这是一个简化的示例，你可能需要更精细的控制哪些元素属于哪个集合
        # 例如，在每个 UIElement 中添加一个 'ui_set_id' 属性
        for element_id, element in self.ui_elements.items():
            # 临时简单判断：如果 element_id 包含 ui_set_id (如 "game_next_button") 或在特定列表中
            if ui_set_id == "game_ui" and element_id == "next_button":
                 element.visible = True # 前进按钮由 update 控制可见，这里只标记它属于 game_ui
            elif ui_set_id == "gallery_ui" and element_id == "gallery_exit_button":
                 element.visible = True
            # TODO: 添加其他UI集合的元素可见性控制
            else:
                 element.visible = False # 默认隐藏


    def set_element_visible(self, element_id: str, visible: bool):
        """设置指定UI元素的可见性"""
        if element_id in self.ui_elements:
            self.ui_elements[element_id].visible = visible
        else:
            print(f"警告：尝试设置未知UI元素可见性: {element_id}")


    def handle_event(self, event, reference_rect: pygame.Rect) -> bool:
        """
        处理Pygame事件，检查UI元素点击。
        返回 True 如果事件被UI处理，否则返回 False。
        reference_rect: 用于计算相对位置的参考矩形 (美图区域或屏幕区域)。
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for element_id, element in self.ui_elements.items():
                if element.visible and element.rect.collidepoint(mouse_pos): # 只检查可见元素的点击
                    # 处理UI元素的点击事件
                    print(f"UI元素点击: {element_id}")
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
                 self.game_manager._go_to_next_image() # 通知GameManager进入下一图
                 # TODO: 播放UI点击音效 sfx_ui_click
                 if self.game_manager.audio_manager:
                      self.game_manager.audio_manager.play_sfx("sfx_ui_click")


        elif element_id == "gallery_exit_button":
            # 点击退出画廊按钮
             self.game_manager.gallery_manager.exit_gallery() # 通知画廊管理器退出
             # TODO: 播放UI点击音效 sfx_ui_click
             if self.game_manager.audio_manager:
                 self.game_manager.audio_manager.play_sfx("sfx_ui_click")


        # TODO: 添加其他UI元素的点击逻辑，例如菜单按钮、画廊缩略图（画廊缩略图点击由GalleryManager处理更合适）


    def update(self, current_image_display_rect: pygame.Rect):
        """更新UI元素状态 (例如位置计算，动画等)"""
        # 根据当前的图片显示区域或屏幕尺寸计算并设置相对定位UI元素的位置
        # 传递美图区域或屏幕区域作为参考矩形
        self._calculate_ui_positions(current_image_display_rect)

        # 控制前进按钮的可见性：当游戏状态，且当前图片的互动完成，且所有文本播放完毕时，前进按钮可见
        if self.game_manager.current_state == self.settings.STATE_GAME:
             is_image_interactive_complete = self.game_manager.current_image_interaction_state and self.game_manager.current_image_interaction_state._is_completed
             # 引子等纯文本类型没有互动模块，但文本播放完毕后也应该显示前进按钮或自动跳转
             is_pure_text_image_needs_next = self.game_manager.current_image_id and self.game_manager.image_configs.get(self.game_manager.current_image_id) and self.game_manager.image_configs[self.game_manager.current_image_id].get("type") in [self.settings.INTERACTION_INTRO] # 引子等纯文本类型
             is_all_narrative_done = not self.game_manager.narrative_manager.is_narrative_active()

             # 只有在 Stage 6.2 完成后才进入画廊，其他图片互动完成后显示前进按钮
             is_stage_6_2 = self.game_manager.current_image_id == "stage6_2"


             # 显示前进按钮条件：
             # 1. 游戏状态
             # 2. 不是引子阶段 (引子阶段自动跳转)
             # 3. 当前图片的互动已完成 OR 当前图片是纯文本图片且文本已播放完毕
             # 4. 所有叙事文本都已播放完毕
             # 5. 不是 Stage 6.2 (Stage 6.2 完成后自动进入画廊)
             should_show_next = (
                 self.game_manager.current_state == self.settings.STATE_GAME and
                 self.game_manager.current_image_id != "intro_title" and
                 (is_image_interactive_complete or (is_pure_text_image_needs_next and is_all_narrative_done)) and
                 is_all_narrative_done and
                 not is_stage_6_2 # Stage 6.2 不显示前进按钮
             )

             self.set_element_visible("next_button", should_show_next)

        # TODO: 更新其他UI元素的动画状态 (如果UI有动画)
        # TODO: 更新进度条的显示 (如果当前互动有进度条)


    def draw(self, screen: pygame.Surface):
        """绘制所有可见的UI元素"""
        for element_id, element in self.ui_elements.items():
            if element.visible:
                # 绘制UI元素，传递缓存
                element.draw(screen, self.ui_image_cache)


    def _calculate_ui_positions(self, current_image_display_rect: pygame.Rect):
        """
        根据当前的图片显示区域或屏幕尺寸计算并设置UI元素在屏幕上的绝对位置。
        这个方法应该在窗口大小改变或图片加载时被调用。
        """
        screen_width, screen_height = self.screen.get_size()
        screen_rect = self.screen.get_rect()

        for element_id, element in self.ui_elements.items():
            # 获取元素的原始尺寸 (从加载的图片中获取)
            element_width, element_height = element.rect.size

            absolute_x, absolute_y = element.rect.topleft # 默认保持当前位置

            if element.relative_to == "image_area":
                 # 相对于图片显示区域左上角定位
                 # element._original_position 是相对于图片区域左上角的偏移量 (像素)
                 absolute_x = current_image_display_rect.left + element._original_position[0]
                 absolute_y = current_image_display_rect.top + element._original_position[1]
                 element.set_position((absolute_x, absolute_y))

                 # TODO: 如果 _original_position 是相对比例 (0-1)，需要乘以 image_display_rect 的尺寸
                 # absolute_x = current_image_display_rect.left + int(element._original_position[0] * current_image_display_rect.width)
                 # absolute_y = current_image_display_rect.top + int(element._original_position[1] * current_image_display_rect.height)
                 # element.set_position((absolute_x, absolute_y))

            elif element.relative_to == "image_area_bottom_right": # 相对于图片显示区域右下角定位
                 # element._original_position 是相对于图片区域右下角的偏移量 (像素) (通常是负值)
                 absolute_x = current_image_display_rect.right + element._original_position[0] - element_width # 减去元素自身宽度
                 absolute_y = current_image_display_rect.bottom + element._original_position[1] - element_height # 减去元素自身高度
                 element.set_position((absolute_x, absolute_y))


            elif element.relative_to == "screen":
                 # 相对于屏幕左上角定位 (_original_position 是屏幕像素坐标)
                 element.set_position(element._original_position)

            # TODO: 添加其他相对定位类型，例如 相对于某个特定矩形区域的ID "custom_rect_id"


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