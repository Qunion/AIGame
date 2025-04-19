# src/narrative_manager.py
import pygame
import time
import os
from src.settings import Settings

class NarrativeManager:
    """
    管理叙事文本的加载、显示和逐字播放。
    控制文本框的绘制。
    """

    def __init__(self, screen, settings: Settings):
        """初始化叙事管理器"""
        self.screen = screen
        self.settings = settings

        # 文本显示相关
        self.current_texts = [] # 当前需要显示的文本ID列表
        self.current_text_index = 0 # 当前正在播放的文本在列表中的索引
        self.current_display_text = "" # 正在逐字显示的文本内容
        self.chars_to_display_count = 0 # 需要显示的字符数（用于逐字效果）
        self.last_char_time = 0 # 上次显示字符的时间

        # 文本框绘制相关
        # 文本框是透明的，UI元素会相对于美图区域。这里只负责文本内容的绘制位置
        self.text_area_rect = None # 文本绘制区域的矩形 (需要根据美图显示区域和UI设计确定)

        # 字体加载
        try:
            self.font = pygame.font.Font(self.settings.TEXT_FONT_PATH, self.settings.TEXT_FONT_SIZE)
        except pygame.error as e:
            print(f"警告：无法加载字体 {self.settings.TEXT_FONT_PATH}: {e}")
            self.font = pygame.font.SysFont("Arial", self.settings.TEXT_FONT_SIZE) # 使用系统默认字体作为Fallback

        # AI声音回调函数
        self._get_ai_sound_callback = None


    def start_narrative(self, text_ids: list[str], get_ai_sound_callback=None):
        """开始播放一系列叙事文本"""
        if not text_ids:
            return

        print(f"开始播放叙事: {text_ids}")
        self.current_texts = text_ids
        self.current_text_index = 0
        self._start_current_text() # 开始播放第一个文本

        self._get_ai_sound_callback = get_ai_sound_callback # 存储回调函数

    def _start_current_text(self):
        """开始播放当前索引的文本"""
        if self.current_text_index < len(self.current_texts):
            text_id = self.current_texts[self.current_text_index]
            # TODO: 从某个地方获取文本内容，例如硬编码、CSV或另一个JSON
            # 假设文本内容和音效路径都存在于 settings.AI_SOUND_EFFECTS 里，value 是音效路径，key是文本ID
            # 或者文本内容在另一个文件里，通过文本ID查找
            # 暂定文本内容硬编码为文本ID本身，或者在 image_config 里添加 texts 字段 {text_id: "text content"}
            # 从 image_config 里加载文本内容更灵活
            # self.current_text_content = self._get_text_content(text_id) # 需要实现一个获取文本内容的方法
            # 假设我们直接使用文本ID作为内容，或者在一个大字典里查找
            # 让我们假设文本内容就存储在 image_config.json 的某个地方，或者独立文件
            # 为了简化，我们假设文本内容就在 config.json 里，与 trigger 绑定
            # 这是一个临时的假设，实际需要更完善的文本管理
            # 从 GameManager 中传递完整的 image_config 或一个文本字典可能更好

            # 假设通过 text_id 可以查找到文本内容
            # text_content = get_text_content_by_id(text_id) # TODO: 实现一个全局文本查找函数
            # 暂时使用文本ID作为内容
            text_content = text_id # 临时占位

            self.current_display_text = "" # 重置显示内容
            self.chars_to_display_count = 0 # 从0开始显示字符
            self.last_char_time = time.time() # 重置时间

            print(f"正在播放文本: {text_id}") # 打印文本ID方便调试

            # 播放对应的AI声音音效 (如果回调函数存在且能找到音效)
            if self._get_ai_sound_callback:
                 sound_path = self._get_ai_sound_callback(text_id)
                 if sound_path:
                      self.settings.audio_manager.play_sfx(sound_path, volume=self.settings.AI_SFX_VOLUME) # 使用AI声音的音量设置

        else:
            self.current_texts = [] # 所有文本播放完毕
            self.current_text_index = 0
            # TODO: 文本播放完毕后的处理，例如显现前进按钮，或者通知 GameManager 进入下一图 (对于引子或纯文本图片)

    def update(self):
        """更新文本显示状态"""
        if not self.current_texts or self.current_text_index >= len(self.current_texts):
            # 如果当前没有文本在播放，或者所有文本都已播放完毕
            # 对于引子或纯文本图片 (interaction_type == intro)，文本播放完毕后自动进入下一图
            # TODO: 需要 GameManager 提供当前图片是否是纯文本类型的判断，或者直接在 GameManager 里判断并调用 _go_to_next_image
            return False # 没有正在播放的文本

        # 逐字显示文本
        current_text_id = self.current_texts[self.current_text_index]
        # text_content = get_text_content_by_id(current_text_id) # TODO: 获取文本内容
        text_content = current_text_id # 临时占位

        if self.chars_to_display_count < len(text_content):
            # 如果还有未显示的字符
            current_time = time.time()
            time_elapsed = current_time - self.last_char_time
            chars_to_add = int(time_elapsed * self.settings.TEXT_SPEED_CPS)
            self.chars_to_display_count += chars_to_add
            self.chars_to_display_count = min(self.chars_to_display_count, len(text_content)) # 不要超过总字符数
            self.current_display_text = text_content[:self.chars_to_display_count]
            self.last_char_time = current_time # 更新上次显示字符的时间

            # TODO: 播放逐字音效 (可选) sfx_text_type

        elif self.current_display_text == text_content:
            # 当前文本已显示完毕
            # 等待一段时间，然后自动播放下一段文本
            time_since_complete = time.time() - self.last_char_time # 这里的 last_char_time 需要在最后一个字符显示后更新
            # TODO: 定义每段文本显示完毕后的等待时间
            # 简单的处理：等文本显示完毕后，过1秒自动进入下一段
            # 准确做法：在最后一个字符显示时，记录完成时间
            completion_time = self.last_char_time # 假设 last_char_time 在最后一个字符显示时被更新

            # TODO: 需要一个机制来判断当前文本是否完全显示完毕，并触发等待
            # 可以在 _start_current_text 中计算总显示时间
            # 或者简单地判断 self.chars_to_display_count == len(text_content)

            # 如果当前文本已完全显示，并且等待时间已过
            # TODO: 需要实现一个判断文本是否已完全显示的方法，以及等待计时器
            # if self._current_text_fully_displayed() and time.time() - self._current_text_display_complete_time > self.settings.TEXT_DISPLAY_WAIT_TIME:

            # 简化处理：文本完全显示后，等待点击前进按钮 (或者在纯文本图片时自动跳)
            # 纯文本图片(intro, gallery_intro)的自动跳过由 GameManager 控制

            pass # 等待进一步的事件 (如点击前进按钮) 或 GameManager 的指令

        # 如果所有文本都已播放完毕，且当前图片不是纯文本类型，则需要显现前进按钮 (由 UIManager 管理)
        # if not self.current_texts and not self.is_narrative_active():
        #    self.ui_manager.show_button("next_button") # TODO: UIManager 提供方法

        return True # 有正在播放的文本

    def draw(self, screen: pygame.Surface):
        """绘制文本框和当前显示的文本"""
        if not self.current_texts or self.current_text_index >= len(self.current_texts):
             # 没有需要绘制的文本
             return

        # TODO: 根据美图显示区域和UI设计，计算文本绘制区域 self.text_area_rect
        # 文本框是透明的，只需要计算文本的绘制位置和最大宽度
        # 假设文本显示在美图区域下方，或者直接叠加在美图区域的底部
        # 假设文本区域宽度与美图区域同宽，高度固定在底部
        image_rect = self.settings.game_manager.image_renderer.image_display_rect # 获取当前图片显示区域
        screen_width, screen_height = screen.get_size()

        # 示例：文本区域位于美图区域下方，宽度与美图区域一致，高度固定
        # 如果美图区域在屏幕中央，文本区域也在美图下方中央
        text_area_width = image_rect.width - 2 * self.settings.TEXT_BOX_PADDING
        text_area_height = self.settings.TEXT_BOX_HEIGHT
        text_area_x = image_rect.left + self.settings.TEXT_BOX_PADDING
        text_area_y = image_rect.bottom - text_area_height - self.settings.TEXT_BOX_PADDING # 放在图片底部上方一点

        self.text_area_rect = pygame.Rect(text_area_x, text_area_y, text_area_width, text_area_height)


        # 绘制透明文本框背景 (如果需要，虽然设计说是透明，但可能有视觉风格上的框)
        # pygame.draw.rect(screen, (0,0,0,100), self.text_area_rect, 0) # 示例半透明黑色背景

        # 绘制当前显示的文本
        text_surface = self.font.render(self.current_display_text, True, self.settings.TEXT_COLOR)

        # 文本自动换行
        # TODO: 实现文本自动换行逻辑，根据 text_area_rect 的宽度 разбиение文本
        # 这是 Pygame 文本绘制中比较繁琐的部分，需要手动计算每行能容纳的字符数
        # 示例：简单的单行绘制 (不换行)
        # screen.blit(text_surface, self.text_area_rect.topleft)

        # 示例：简单的多行绘制 (需要手动 разбиение)
        lines = self._wrap_text(self.current_display_text, self.text_area_rect.width)
        line_y = self.text_area_rect.top
        line_height = self.font.get_linesize()
        for line in lines:
             line_surface = self.font.render(line, True, self.settings.TEXT_COLOR)
             screen.blit(line_surface, (self.text_area_rect.left, line_y))
             line_y += line_height


    def is_narrative_active(self):
        """检查当前是否有叙事文本正在播放或等待下一段"""
        return len(self.current_texts) > 0

    # TODO: 实现文本自动换行 (_wrap_text)
    def _wrap_text(self, text, max_width):
        """将文本按最大宽度进行自动换行"""
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            if self.font.size(' '.join(current_line + [word]))[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line)) # 添加最后一行
        return lines

    # TODO: 实现获取文本内容的方法 (_get_text_content)
    # def _get_text_content(self, text_id):
    #     # 需要 GameManager 或一个全局文本字典来查找
    #     # GameManager 持有 image_configs，可以从中提取文本
    #     # 假设 image_config.json 中有一个顶级 "texts" 字段 { "T1.1.1": "一个波动...", ...}
    #     # 或者文本内容直接存储在 narrative_triggers 字段里
    #     # 让我们假设 GameManager 知道如何查找文本内容，并将其作为参数传递给 start_narrative
    #     # 或者 NarrativeManager 在初始化时加载一个完整的文本字典
    #     # 示例:
    #     # text_dictionary = {
    #     #      "T1.1.1": "一个波动...",
    #     #      "T1.1.2": "频率... 正在靠近...",
    #     #      # ... 所有文本
    #     # }
    #     # self.text_dictionary = text_dictionary # 在 __init__ 或加载时加载
    #     # return self.text_dictionary.get(text_id, f"文本ID未找到: {text_id}")
    #     return text_id # 临时使用ID作为内容


    # TODO: 实现判断当前文本是否完全显示的方法 (_current_text_fully_displayed)
    # TODO: 实现文本显示完毕后的等待计时器和下一段文本的逻辑

    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     return {
    #          "current_texts": self.current_texts,
    #          "current_text_index": self.current_text_index,
    #          "current_display_text": self.current_display_text,
    #          "chars_to_display_count": self.chars_to_display_count,
    #          "last_char_time": self.last_char_time
    #          # AI声音回调不需要保存
    #     }
    # def load_state(self, state_data):
    #     self.current_texts = state_data["current_texts"]
    #     self.current_text_index = state_data["current_text_index"]
    #     self.current_display_text = state_data["current_display_text"]
    #     self.chars_to_display_count = state_data["chars_to_display_count"]
    #     self.last_char_time = state_data["last_char_time"]
    #     # AI声音回调需要在 GameManager 加载 NarrativeManager 后重新设置