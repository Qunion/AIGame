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

        # 文本内容字典 (假设从某个地方加载所有文本内容)
        # TODO: 需要一个地方存储所有文本内容，例如一个独立的JSON文件或 image_config 的一个子集
        # 暂时假设文本内容就是文本ID本身，或从 settings.AI_SOUND_EFFECTS 的key获取
        # 更合理的做法是在 image_config.json 或独立的 texts.json 文件中 { "T1.1.1": "这里是文本内容", ... }
        # 让我们假设从 image_config.json 的 "texts" 字段加载所有文本内容
        # self.texts_content = self._load_texts_content() # TODO: 实现加载文本内容的方法
        # 暂时代替文本内容查找函数
        def get_text_content_placeholder(text_id):
             # 这是一个临时的占位函数
             # 在实际开发中，你需要根据 text_id 从加载的文本字典中查找真实的文本内容
             # 例如: return self.text_dictionary.get(text_id, f"文本ID未找到: {text_id}")
             # 为了让逐字显示能工作，返回一个非空的字符串
             # return f"文本内容 for {text_id}" # 返回一个占位字符串
             return text_id # 临时使用文本ID作为内容

        self._get_text_content = get_text_content_placeholder # 存储查找文本内容的函数

        # 文本显示相关
        self.current_texts_ids = [] # 当前需要显示的文本ID列表 (从 GameManager 接收)
        self.current_text_index = 0 # 当前正在播放的文本在列表中的索引
        self.current_text_content = "" # 当前正在播放的文本的完整内容
        self.current_display_text = "" # 正在逐字显示的文本内容
        self.chars_to_display_count = 0 # 需要显示的字符数（用于逐字效果）
        self.last_char_time = 0 # 上次显示字符的时间

        # 文本播放状态
        self._is_playing_text = False # 是否有文本正在播放 (用于逐字效果)
        self._is_waiting_after_text = False # 是否在文本播放完毕后等待 (用于自动进入下一段)
        self._text_display_complete_time = 0 # 当前文本完全显示完毕的时间

        self.TEXT_DISPLAY_WAIT_TIME = 1.5 # 每段文本显示完毕后自动进入下一段前的等待时间 (秒) - TODO: 移动到settings

        # 文本框绘制相关
        self.text_area_rect = pygame.Rect(0, 0, 0, 0) # 文本绘制区域的矩形，由 draw 方法根据图片区域计算

        # 字体加载
        try:
            self.font = pygame.font.Font(self.settings.TEXT_FONT_PATH, self.settings.TEXT_FONT_SIZE)
        except pygame.error as e:
            print(f"警告：无法加载字体 {self.settings.TEXT_FONT_PATH}: {e}")
            self.font = pygame.font.SysFont("Arial", self.settings.TEXT_FONT_SIZE) # 使用系统默认字体作为Fallback

        # AI声音回调函数 (从 GameManager 接收)
        self._get_ai_sound_callback = None


    def start_narrative(self, text_ids: list[str], get_ai_sound_callback=None):
        """开始播放一系列叙事文本"""
        if not text_ids:
            return

        # 如果当前有文本正在播放，中断它
        if self._is_playing_text or self.current_texts_ids:
            print("中断当前叙事，开始新叙事...")
            # TODO: 停止正在播放的AI声音音效
            pass # self.settings.audio_manager.stop_sfx(current_ai_sound_id) # 需要跟踪正在播放的AI声音ID

        print(f"开始播放叙事序列: {text_ids}")
        self.current_texts_ids = text_ids
        self.current_text_index = 0
        self._get_ai_sound_callback = get_ai_sound_callback # 存储回调函数

        self._start_current_text() # 开始播放第一个文本


    def _start_current_text(self):
        """开始播放当前索引的文本"""
        if self.current_text_index < len(self.current_texts_ids):
            text_id = self.current_texts_ids[self.current_text_index]
            # TODO: 从某个地方获取文本内容，例如硬编码、CSV或另一个JSON
            # 假设文本内容和音效路径都存在于 settings.AI_SOUND_EFFECTS 里，value 是音效路径，key是文本ID
            # 或者文本内容在另一个文件里，通过文本ID查找
            # 暂定文本内容硬编码为文本ID本身，或者在 image_config 里添加 texts 字段 {text_id: "text content"}
            # 从 image_config 里加载文本内容更灵活
            self.current_text_content = self._get_text_content(text_id) # 获取文本内容
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
            self.last_char_time = time.time() # 重置时间计时器

            self._is_playing_text = True # 标记正在播放
            self._is_waiting_after_text = False # 不在等待状态
            self._text_display_complete_time = 0 # 重置完成时间

            print(f"正在播放文本: {text_id} - '{self.current_text_content}'") # 打印文本ID和内容方便调试

            # 播放对应的AI声音音效 (如果回调函数存在且能找到音效)
            if self._get_ai_sound_callback:
                 sound_path = self._get_ai_sound_callback(text_id)
                 if sound_path:
                      self.settings.audio_manager.play_sfx(sound_path, loop=0, volume=self.settings.AI_SFX_VOLUME)


        else:
            # 所有文本播放完毕
            self.current_texts_ids = [] # 清空列表
            self.current_text_index = 0
            self._is_playing_text = False
            self._is_waiting_after_text = False
            print("叙事序列播放完毕。")
            # 通知 GameManager 文本播放完毕状态，由 GameManager 控制前进按钮的可见性


    def update(self):
        """更新文本显示状态"""
        if not self._is_playing_text:
             # 如果没有文本正在播放，检查是否在等待进入下一段
             if self._is_waiting_after_text:
                  if time.time() - self._text_display_complete_time > self.TEXT_DISPLAY_WAIT_TIME:
                       # 等待时间已过，进入下一段文本
                       self._is_waiting_after_text = False
                       self.current_text_index += 1
                       self._start_current_text() # 启动下一段文本
             return # 没有正在播放的文本，也不在等待


        # 如果有文本正在播放 (逐字显示中)
        text_content = self.current_text_content

        if self.chars_to_display_count < len(text_content):
            # 逐字显示
            current_time = time.time()
            time_elapsed = current_time - self.last_char_time
            chars_to_add = int(time_elapsed * self.settings.TEXT_SPEED_CPS)
            self.chars_to_display_count += chars_to_add
            self.chars_to_display_count = min(self.chars_to_display_count, len(text_content)) # 不要超过总字符数
            self.current_display_text = text_content[:self.chars_to_display_count]
            self.last_char_time = current_time # 更新上次显示字符的时间

            # TODO: 播放逐字音效 (可选) sfx_text_type (需要确保音效不会太密集)

            if self.chars_to_display_count == len(text_content):
                 # 当前文本刚刚显示完毕
                 self._is_playing_text = False # 标记播放完毕
                 self._is_waiting_after_text = True # 进入等待状态
            # TODO: 定义每段文本显示完毕后的等待时间
            # 简单的处理：等文本显示完毕后，过1秒自动进入下一段
            # 准确做法：在最后一个字符显示时，记录完成时间
                 self._text_display_complete_time = time.time() # 记录完成时间
                 print(f"文本 '{current_text_content}' 显示完毕。等待 {self.TEXT_DISPLAY_WAIT_TIME} 秒。")
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


    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制文本框和当前显示的文本"""
        if not self.current_texts_ids or (not self._is_playing_text and not self._is_waiting_after_text):
             # 没有需要绘制的文本，也不在等待状态
             return

        # 计算文本绘制区域 self.text_area_rect
        # 文本框是透明的，只需要计算文本的绘制位置和最大宽度
        # 假设文本显示在美图区域下方，或者直接叠加在美图区域的底部
        # 假设文本区域宽度与美图区域同宽，高度固定在底部
        image_rect = self.settings.game_manager.image_renderer.image_display_rect # 获取当前图片显示区域
        screen_width, screen_height = screen.get_size()

        # 文本区域宽度与美图区域同宽 (减去边距)，高度固定，位于美图区域下方
        text_area_width = image_display_rect.width - 2 * self.settings.TEXT_BOX_PADDING
        text_area_height = self.settings.TEXT_BOX_HEIGHT
        text_area_x = image_display_rect.left + self.settings.TEXT_BOX_PADDING
        text_area_y = image_display_rect.bottom - text_area_height - self.settings.TEXT_BOX_PADDING # 位于图片底部上方一点

        self.text_area_rect = pygame.Rect(text_area_x, text_area_y, text_area_width, text_area_height)

        # 绘制透明文本框背景 (如果需要，虽然设计说是透明，但可能有视觉风格上的框)
        # pygame.draw.rect(screen, (0,0,0,100), self.text_area_rect, 0) # 示例半透明黑色背景
        # 绘制当前显示的文本，自动换行
        text_surface = self.font.render(self.current_display_text, True, self.settings.TEXT_COLOR)

        # 文本自动换行
        # TODO: 实现文本自动换行逻辑，根据 text_area_rect 的宽度 разбиение文本
        # 这是 Pygame 文本绘制中比较繁琐的部分，需要手动计算每行能容纳的字符数
        # 示例：简单的单行绘制 (不换行)
        # screen.blit(text_surface, self.text_area_rect.topleft)

        # 示例：简单的多行绘制 (需要手动 разбиение)
        lines = self._wrap_text(self.current_display_text, self.text_area_rect.width)
        line_y = self.text_area_rect.top # 文本绘制起始Y坐标
        line_height = self.font.get_linesize() # 每行文本的高度

        # 绘制每一行文本
        for line in lines:
             line_surface = self.font.render(line, True, self.settings.TEXT_COLOR)
             screen.blit(line_surface, (self.text_area_rect.left, line_y))
             line_y += line_height # 更新下一行的Y坐标


    def is_narrative_active(self):
        """检查当前是否有叙事文本正在播放或等待下一段"""
        return len(self.current_texts_ids) > self.current_text_index or self._is_playing_text or self._is_waiting_after_text


    def _wrap_text(self, text, max_width):
        """将文本按最大宽度进行自动换行"""
        words = text.split(' ')
        if not words: return []

        lines = []
        current_line_words = []

        for word in words:
            # 检查当前行加上新单词是否超出宽度
            test_line = ' '.join(current_line_words + [word])
            if self.font.size(test_line)[0] <= max_width:
                current_line_words.append(word)
            else:
                # 如果新单词本身就超出最大宽度，单独一行显示（并可能被裁剪，Pygame render 不支持裁剪）
                # 或者在这里处理更复杂的单词截断逻辑
                if not current_line_words: # 当前行没有单词，且新单词太长
                    lines.append(word) # 简单处理：长单词自己一行
                    current_line_words = []
                else:
                    lines.append(' '.join(current_line_words))
                    current_line_words = [word]

        if current_line_words: # 添加最后一行
            lines.append(' '.join(current_line_words))

        return lines

    # TODO: 实现获取文本内容的方法 (_get_text_content)
    # 这个方法需要在初始化时加载所有文本内容字典
    # def _load_texts_content(self):
    #     """从文件加载所有文本内容"""
    #     # 假设文本内容在一个独立的 JSON 文件中，或者在 image_config.json 中
    #     # 如果在 image_config.json 中，需要GameManager加载后传递过来
    #     # 示例从 image_config.json 中提取所有 narrative_triggers 的文本ID和内容
    #     texts_dict = {}
    #     for img_id, config in self.settings.game_manager.image_configs.items(): # 需要 GameManager 引用
    #          if "narrative_triggers" in config:
    #               for trigger_type, text_ids in config["narrative_triggers"].items():
    #                    for text_id in text_ids:
    #                         # 这里假设 text_id 就是文本内容，或者需要更复杂的查找
    #                         # 如果你的文本内容在另一个结构里，需要相应修改
    #                         if text_id not in texts_dict:
    #                             texts_dict[text_id] = text_id # 占位，实际应是查找到的文本内容
    #     return texts_dict

    # TODO: 添加保存和加载模块状态的方法 (保存当前正在播放的文本序列和索引)
    # def get_state(self):
    #     return {
    #          "current_texts_ids": self.current_texts_ids,
    #          "current_text_index": self.current_text_index,
    #          "current_display_text": self.current_display_text, # 可能需要保存，以便从中断处继续
    #          "chars_to_display_count": self.chars_to_display_count,
    #          "last_char_time": self.last_char_time,
    #          "_is_playing_text": self._is_playing_text,
    #          "_is_waiting_after_text": self._is_waiting_after_text,
    #          "_text_display_complete_time": self._text_display_complete_time
    #     }
    # def load_state(self, state_data, get_ai_sound_callback): # 加载时需要重新设置回调
    #     self.current_texts_ids = state_data["current_texts_ids"]
    #     self.current_text_index = state_data["current_text_index"]
    #     self.current_display_text = state_data["current_display_text"]
    #     self.chars_to_display_count = state_data["chars_to_display_count"]
    #     self.last_char_time = state_data["last_char_time"]
    #     self._is_playing_text = state_data["_is_playing_text"]
    #     self._is_waiting_after_text = state_data["_is_waiting_after_text"]
    #     self._text_display_complete_time = state_data["_text_display_complete_time"]
    #     self._get_ai_sound_callback = get_ai_sound_callback # 重新设置回调
    #     self.current_text_content = self._get_text_content(self.current_texts_ids[self.current_text_index]) if self.current_texts_ids else "" # 重新获取完整文本内容