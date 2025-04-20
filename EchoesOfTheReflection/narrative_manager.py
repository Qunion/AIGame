# narrative_manager.py
import pygame
import time
import os
import json
# 修正导入路径，Settings 现在在根目录
from settings import Settings
# 导入 AudioManager 类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from audio_manager import AudioManager # AudioManager 在根目录

# 定义文本文件路径 (相对于根目录)
TEXT_CONTENT_FILE = os.path.join("data", "texts.json")


class NarrativeManager:
    """
    管理叙事文本的加载、显示和逐字播放。
    控制文本框的绘制。
    """

    # 构造函数新增 audio_manager 参数
    def __init__(self, screen, settings: Settings, audio_manager: 'AudioManager'):
        """初始化叙事管理器"""
        self.screen = screen
        self.settings = settings
        self.audio_manager = audio_manager # 存储 AudioManager 实例

        # 文本内容字典 (从文件加载所有文本内容)
        # 加载所有文本内容字典到 self.text_dictionary
        self.text_dictionary = self._load_all_texts_content()


        # 文本显示相关
        self.current_texts_ids = [] # 当前需要显示的文本ID列表 (从 GameManager 接收)
        self.current_text_index = 0 # 当前正在播放的文本在列表中的索引
        self.current_text_content = "" # 当前正在播放的文本的完整内容 (查找后的实际内容)
        self.current_display_text = "" # 正在逐字显示的文本内容
        self.chars_to_display_count = 0 # 需要显示的字符数（用于逐字效果）
        self.last_char_time = 0 # 上次显示字符的时间

        # 文本播放状态
        self._is_playing_text = False # 是否有文本正在播放 (用于逐字效果)
        self._is_waiting_after_text = False # 是否在文本播放完毕后等待 (用于自动进入下一段)
        self._text_display_complete_time = 0 # 当前文本完全显示完毕的时间

        self.TEXT_DISPLAY_WAIT_TIME = 1.5 # 每段文本显示完毕后自动进入下一段前的等待时间 (秒) # TODO: 移动到settings

        # 文本框绘制相关
        self.text_area_rect = pygame.Rect(0, 0, 0, 0) # 文本绘制区域的矩形，由 draw 方法根据图片区域计算

        # 字体加载
        try:
            # 尝试加载指定的字体文件
            # self.font = pygame.font.Font(self.settings.TEXT_FONT_PATH, self.settings.TEXT_FONT_SIZE)
            # 如果 TEXT_FONT_PATH 是系统字体名，用 SysFont
            if os.path.exists(self.settings.TEXT_FONT_PATH):
                 self.font = pygame.font.Font(self.settings.TEXT_FONT_PATH, self.settings.TEXT_FONT_SIZE)
                 print(f"成功加载字体文件: {self.settings.TEXT_FONT_PATH}")
            else:
                 # 尝试加载系统字体
                 self.font = pygame.font.SysFont(self.settings.TEXT_FONT_PATH, self.settings.TEXT_FONT_SIZE)
                 print(f"尝试加载系统字体: {self.settings.TEXT_FONT_PATH}")

        except pygame.error as e:
            print(f"警告：无法加载字体 {self.settings.TEXT_FONT_PATH}: {e}")
            self.font = pygame.font.SysFont("Arial", self.settings.TEXT_FONT_SIZE) # 使用系统默认字体作为Fallback
            print("使用 Arial 字体作为Fallback。")


    def _load_all_texts_content(self):
        """从 data/texts.json 文件加载所有文本内容"""
        # TODO: 修改为从 data/texts.json 文件加载
        text_file_path = TEXT_CONTENT_FILE # 使用定义的常量

        if not os.path.exists(text_file_path):
            print(f"错误：文本内容文件未找到 {text_file_path}")
            # 返回一个空字典，以免后续查找时崩溃
            return {}


        try:
             # 使用 json 标准库加载，texts.json 不应包含注释
             with open(text_file_path, 'r', encoding='utf-8') as f:
                 return json.load(f)
        except json.JSONDecodeError as e:
             print(f"错误：解析文本内容文件 {text_file_path} 格式错误: {e}")
             # 返回空字典或包含错误信息的字典
             return {"Error": f"Failed to load texts: {e}"}
        except Exception as e:
             print(f"错误：加载文本内容文件 {text_file_path} 时出错: {e}")
             return {"Error": f"Failed to load texts: {e}"}


    # start_narrative 方法不再需要 get_ai_sound_callback 参数
    def start_narrative(self, text_ids: list[str]):
        """开始播放一系列叙事文本"""
        if not text_ids:
            return

        # 如果当前有文本正在播放，中断它
        if self._is_playing_text or self.current_texts_ids:
            print("中断当前叙事，开始新叙事...")
            # TODO: 停止正在播放的AI声音音效 (如果需要，需要跟踪正在播放的AI声音ID)
            # self.audio_manager.stop_sfx(current_ai_sound_id) # 需要跟踪正在播放的AI声音ID
            pass # 暂不实现中断音效

        print(f"开始播放叙事序列: {text_ids}")
        self.current_texts_ids = text_ids
        self.current_text_index = 0

        self._start_current_text() # 开始播放第一个文本


    # _start_current_text 方法直接使用 self.audio_manager，并调用 _get_text_content 方法
    def _start_current_text(self):
        """开始播放当前索引的文本"""
        if self.current_text_index < len(self.current_texts_ids):
            text_id = self.current_texts_ids[self.current_text_index]
            # 调用内部方法获取文本内容
            self.current_text_content = self._get_text_content(text_id) # <-- 这里调用的是即将定义的内部方法

            if not self.current_text_content or self.current_text_content.strip() == "":
                 print(f"警告：文本ID {text_id} 内容为空或未找到，跳过。")
                 self.current_text_index += 1
                 self._start_current_text() # 尝试播放下一段
                 return


            self.current_display_text = "" # 重置显示内容
            self.chars_to_display_count = 0 # 从0开始显示字符
            self.last_char_time = time.time() # 重置时间计时器

            self._is_playing_text = True # 标记正在播放
            self._is_waiting_after_text = False # 不在等待状态
            self._text_display_complete_time = 0 # 重置完成时间

            print(f"正在播放文本: {text_id} - '{self.current_text_content}'") # 打印文本ID和内容方便调试

            # 播放对应的AI声音音效 (如果能找到音效)
            # 现在直接通过 self.audio_manager 播放，音效ID就是文本ID
            # AudioManager 会在播放时根据ID查找路径和设置音量
            self.audio_manager.play_sfx(text_id, loop=0, volume=self.settings.AI_SFX_VOLUME)


        else:
            # 所有文本播放完毕
            self.current_texts_ids = [] # 清空列表
            self.current_text_index = 0
            self._is_playing_text = False
            self._is_waiting_after_text = False
            print("叙事序列播放完毕。")
            # 通知 GameManager 文本播放完毕状态，由 GameManager 控制前进按钮的可见性

    # 添加 _get_text_content 方法作为标准的类方法
    def _get_text_content(self, text_id):
         """通过文本ID查找文本内容"""
         # 从 self.text_dictionary 中查找文本内容
         return self.text_dictionary.get(text_id, f"Text ID not found: {text_id}")


    # ... update 方法同之前

    def update(self):
        """更新文本显示状态"""
        if not self.current_texts_ids and not self._is_playing_text and not self._is_waiting_after_text:
             # 如果没有文本序列，且没有正在播放或等待的文本
             return False # 没有需要更新的叙事，返回不活跃状态


        # 如果有文本正在播放 (逐字显示中)
        text_content = self.current_text_content

        if self._is_playing_text:
            if self.chars_to_display_count < len(text_content):
                # 逐字显示
                current_time = time.time()
                time_elapsed = current_time - self.last_char_time
                # 计算这次更新需要增加的字符数
                chars_to_add = int(time_elapsed * self.settings.TEXT_SPEED_CPS) - (self.chars_to_display_count - len(self.current_display_text)) # 减去上次计算但可能未显示的字符
                self.chars_to_display_count += chars_to_add
                self.chars_to_display_count = min(self.chars_to_display_count, len(text_content)) # 不要超过总字符数
                self.current_display_text = text_content[:self.chars_to_display_count]
                self.last_char_time = current_time # 更新上次显示字符的时间

                # TODO: 播放逐字音效 (可选) sfx_text_type (需要确保音效不会太密集)

                if self.chars_to_display_count == len(text_content):
                     # 当前文本刚刚显示完毕
                     self._is_playing_text = False # 标记播放完毕
                     self._is_waiting_after_text = True # 进入等待状态
                     self._text_display_complete_time = time.time() # 记录完成时间
                     print(f"文本 '{text_content}' 显示完毕。等待 {self.TEXT_DISPLAY_WAIT_TIME} 秒。")

        elif self._is_waiting_after_text:
             # 如果在等待进入下一段
             if time.time() - self._text_display_complete_time > self.TEXT_DISPLAY_WAIT_TIME:
                  # 等待时间已过，进入下一段文本
                  self._is_waiting_after_text = False
                  self.current_text_index += 1
                  self._start_current_text() # 启动下一段文本

        return True # 有正在播放的文本或在等待

    # ... draw 方法同之前

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制文本框和当前显示的文本"""
        # 只有当有文本内容正在显示时才绘制
        if not self.current_display_text:
             return

        # 计算文本绘制区域 self.text_area_rect
        # 文本框是透明的，只需要计算文本的绘制位置和最大宽度
        screen_width, screen_height = screen.get_size()

        # 如果没有图片显示区域 (如引子阶段)，文本区域可能固定在屏幕底部中央
        if image_display_rect.width == 0 or image_display_rect.height == 0:
             # 示例：屏幕底部中央固定区域
             text_area_width = screen_width * 0.8 # 屏幕宽度的80%
             text_area_height = self.settings.TEXT_BOX_HEIGHT # 固定高度 (由settings提供)
             text_area_x = (screen_width - text_area_width) // 2
             text_area_y = screen_height - text_area_height - self.settings.TEXT_BOX_PADDING # 距离底部设置的边距

             self.text_area_rect = pygame.Rect(text_area_x, text_area_y, text_area_width, text_area_height)

        else:
            # 文本区域宽度与美图区域同宽 (减去边距)，高度固定，位于美图区域下方
            text_area_width = image_display_rect.width - 2 * self.settings.TEXT_BOX_PADDING
            text_area_height = self.settings.TEXT_BOX_HEIGHT # 固定高度 (由settings提供)
            text_area_x = image_display_rect.left + self.settings.TEXT_BOX_PADDING
            text_area_y = image_display_rect.bottom - text_area_height - self.settings.TEXT_BOX_PADDING # 位于图片底部上方一点

            self.text_area_rect = pygame.Rect(text_area_x, text_area_y, text_area_width, text_area_height)


        # 绘制透明文本框背景 (如果需要，虽然设计说是透明，但可能有视觉风格上的框)
        # pygame.draw.rect(screen, (0,0,0,100), self.text_area_rect, 0) # 示例半透明黑色背景
        # 绘制当前显示的文本，自动换行
        # 确保有文本内容可绘制
        if self.current_display_text:
            # 文本自动换行
            lines = self._wrap_text(self.current_display_text, self.text_area_rect.width)
            line_y = self.text_area_rect.top # 文本绘制起始Y坐标
            line_height = self.font.get_linesize() # 每行文本的高度

            # 绘制每一行文本
            for line in lines:
                 # 防止文本超出绘制区域底部
                 if line_y + line_height <= self.text_area_rect.bottom + 2: # 加一点容忍度
                     rendered_line = self.font.render(line, True, self.settings.TEXT_COLOR)
                     screen.blit(rendered_line, (self.text_area_rect.left, line_y))
                     line_y += line_height # 更新下一行的Y坐标
                 else:
                     # 超出区域，停止绘制后续行
                     break


    def is_narrative_active(self):
        """检查当前是否有叙事文本正在播放或等待下一段"""
        # 只要还有未播放的文本ID，或者正在播放文本，或者在等待下一段，都视为活跃
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
                # 如果新单词本身就超出最大宽度，单独一行显示
                # Pygame render 不支持裁剪，长单词会超出边界
                # 如果不希望长单词超界，需要在代码中手动截断单词或使用其他库
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
    #          "current_text_content": self.current_text_content, # 保存完整文本内容
    #          "current_display_text": self.current_display_text, # 保存当前显示内容
    #          "chars_to_display_count": self.chars_to_display_count,
    #          "last_char_time": self.last_char_time,
    #          "_is_playing_text": self._is_playing_text,
    #          "_is_waiting_after_text": self._is_waiting_after_text,
    #          "_text_display_complete_time": self._text_display_complete_time
    #     }
    # def load_state(self, state_data): # NarrativeManager 自己加载状态
    #     self.current_texts_ids = state_data["current_texts_ids"]
    #     self.current_text_index = state_data["current_text_index"]
    #     self.current_text_content = state_data["current_text_content"]
    #     self.current_display_text = state_data["current_display_text"]
    #     self.chars_to_display_count = state_data["chars_to_display_count"]
    #     self.last_char_time = state_data["last_char_time"]
    #     self._is_playing_text = state_data["_is_playing_text"]
    #     self._is_waiting_after_text = state_data["_is_waiting_after_text"]
    #     self._text_display_complete_time = state_data["_text_display_complete_time"]