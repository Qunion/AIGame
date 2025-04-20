# audio_manager.py
import pygame
import os
from settings import Settings
# 导入类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class AudioManager:
    """管理背景音乐和音效的播放"""

    def __init__(self, settings: Settings):
        """初始化音频管理器"""
        self.settings = settings
        pygame.mixer.init() # 初始化混音器模块

        self.bgm_channel = pygame.mixer.Channel(0) # 专门用于背景音乐的通道
        # 获取可用通道数，并为音效分配通道
        num_channels = pygame.mixer.get_num_channels()
        self.sfx_channels = [pygame.mixer.Channel(i) for i in range(1, num_channels)] # 用于音效的通道，排除0
        # 检查可用通道是否足够，Pygame默认可能只有8个通道
        if num_channels < 8:
            pygame.mixer.set_num_channels(8) # 尝试增加通道数
            num_channels = pygame.mixer.get_num_channels()
            self.sfx_channels = [pygame.mixer.Channel(i) for i in range(1, num_channels)]
            # print(f"混音器通道数设置为: {num_channels}") # 调试


        self.bgm_volume = settings.BGM_VOLUME
        self.sfx_volume = settings.SFX_VOLUME
        self.ai_sfx_volume = settings.AI_SFX_VOLUME

        # 加载音效字典 (AI声音和其他音效)
        self.loaded_sfx = {}
        self._load_all_sfx()


    def _load_all_sfx(self):
        """加载所有预定义的音效文件"""
        # 加载AI声音音效
        # self.settings.AI_SOUND_EFFECTS 是一个字典 {text_id: file_name}
        for text_id, file_name in self.settings.AI_SOUND_EFFECTS.items():
             # 修正: 拼接音频目录和文件名
             full_path = os.path.join(self.settings.AUDIO_DIR, file_name)
             if os.path.exists(full_path):
                 try:
                     self.loaded_sfx[text_id] = pygame.mixer.Sound(full_path)
                     # print(f"成功加载AI音效: {file_name}") # 调试
                 except pygame.error as e:
                     print(f"警告：无法加载AI声音音效 {full_path}: {e}")
                     self.loaded_sfx[text_id] = None # 加载失败则设为None
             else:
                  print(f"警告：AI声音音效文件未找到 {full_path}")
                  self.loaded_sfx[text_id] = None # 未找到则设为None


        # 加载其他通用音效 (key 是音效ID，value 是文件名)
        # self.settings.GENERIC_SFX 现在是一个字典 {id: filename}
        # 修正: 遍历字典的 items()
        for sfx_id, file_name in self.settings.GENERIC_SFX.items(): # 修正: 使用 self.settings.GENERIC_SFX
            # 修正: 拼接音频目录和文件名
            full_path = os.path.join(self.settings.AUDIO_DIR, file_name)
            if os.path.exists(full_path):
                try:
                    self.loaded_sfx[sfx_id] = pygame.mixer.Sound(full_path)
                    # print(f"成功加载通用音效: {file_name}") # 调试
                except pygame.error as e:
                    print(f"警告：无法加载通用音效 {full_path}: {e}")
                    self.loaded_sfx[sfx_id] = None
            else:
                print(f"警告：通用音效文件未找到 {full_path}")
                self.loaded_sfx[sfx_id] = None


    # play_bgm 方法已正确，加载时拼接路径
    def play_bgm(self, bgm_path, loop=-1, volume=None):
        """播放背景音乐"""
        if volume is None:
            volume = self.bgm_volume

        # bgm_path 应该已经是完整路径 (在 GameManager 中拼接)
        if not os.path.exists(bgm_path):
            print(f"警告：背景音乐文件未找到 {bgm_path}")
            return

        try:
            # Pygame mixer.music 可以播放OGG，更适合BGM
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=loop)
        except pygame.error as e:
            print(f"警告：无法播放背景音乐 {bgm_path}: {e}")

    def stop_bgm(self):
        """停止背景音乐"""
        pygame.mixer.music.stop()

    def play_sfx(self, sfx_id, loop=0, volume=None): # 参数名更清晰，明确是ID
        """
        播放音效。
        sfx_id: 音效ID (如文本ID) 或已加载到 self.loaded_sfx 的key。
        """
        if volume is None:
            # 根据ID判断是AI声音还是通用音效来设置音量
            # 检查ID是否存在于 AI_SOUND_EFFECTS 的键中
            if sfx_id in self.settings.AI_SOUND_EFFECTS:
                 volume = self.ai_sfx_volume
            # 检查ID是否存在于 GENERIC_SFX 的键中
            elif sfx_id in self.settings.GENERIC_SFX: # 修正: 使用 self.settings.GENERIC_SFX
                  volume = self.sfx_volume
            else:
                 # 如果 ID 既不在 AI 也不在通用列表中，可能是无效ID或特殊音效，使用默认音效音量
                 # print(f"警告：音效ID {sfx_id} 未在 AI 或通用音效列表中定义。使用默认音效音量。") # 调试警告，可能不需要
                 volume = self.sfx_volume # 使用通用音效音量作为默认

        sfx_sound = self.loaded_sfx.get(sfx_id) # 尝试从加载的音效字典中获取 Pygame Sound 对象

        if sfx_sound:
            sfx_sound.set_volume(volume)
            # 查找一个空闲的音效通道播放
            for channel in self.sfx_channels:
                if not channel.get_busy():
                    channel.play(sfx_sound, loops=loop)
                    return
            # 如果没有空闲通道，忽略本次播放（避免打断正在播放的重要音效）
            # print(f"警告：音效通道不足，无法播放音效: {sfx_id}")

        # else: 音效ID未找到或加载失败（已在加载时警告）


    def stop_sfx(self, sfx_id=None):
        """停止指定的音效 (如果已加载) 或所有音效通道的音效"""
        if sfx_id is None:
            # 停止所有音效通道
            for channel in self.sfx_channels:
                channel.stop()
        else:
             # 停止播放指定 Sound 对象的通道 (需要查找)
             sound_to_stop = self.loaded_sfx.get(sfx_id)
             if sound_to_stop:
                  for channel in self.sfx_channels:
                       # channel.get_sound() 返回当前通道播放的 Sound 对象
                       if channel.get_sound() == sound_to_stop and channel.get_busy():
                            channel.stop()
                            # print(f"停止音效 {sfx_id} 在通道 {channel.get_id()}") # 调试
                            return
             # print(f"警告：音效 {sfx_id} 未找到或未在音效通道中播放。") # 调试未找到


    def is_sfx_playing(self, sfx_id):
        """检查指定的音效是否正在播放 (如果已加载)"""
        sound_to_check = self.loaded_sfx.get(sfx_id)
        if sound_to_check:
            for channel in self.sfx_channels:
                if channel.get_sound() == sound_to_check and channel.get_busy():
                    return True
        return False


    def set_volume(self, audio_type, volume):
        """设置指定类型的音量 (bgm, sfx, ai_sfx)"""
        if audio_type == "bgm":
            self.bgm_volume = volume
            pygame.mixer.music.set_volume(volume)
        elif audio_type == "sfx":
            self.sfx_volume = volume
            # TODO: 更新所有正在播放的通用音效的音量，或只影响新播放的音效
            for sfx_id in self.settings.GENERIC_SFX: # 修正: 遍历 GENERIC_SFX 的键
                 sound = self.loaded_sfx.get(sfx_id)
                 if sound:
                      for channel in self.sfx_channels:
                           if channel.get_sound() == sound and channel.get_busy():
                                channel.set_volume(volume)
            # 新播放的音效会使用更新后的 self.sfx_volume
            pass
        elif audio_type == "ai_sfx":
            self.ai_sfx_volume = volume
            # 更新正在播放的AI声音音量
            for text_id in self.settings.AI_SOUND_EFFECTS: # 遍历AI音效ID列表
                 sound = self.loaded_sfx.get(text_id)
                 if sound:
                      for channel in self.sfx_channels:
                           if channel.get_sound() == sound and channel.get_busy():
                                channel.set_volume(volume)
            # 新播放的AI声音会使用更新后的 self.ai_sfx_volume
            pass

    # TODO: 添加保存和加载音量设置的方法
    # def get_state(self):
    #     return {"bgm_volume": self.bgm_volume, "sfx_volume": self.sfx_volume, "ai_sfx_volume": self.ai_sfx_volume}
    # def load_state(self, state_data):
    #     self.set_volume("bgm", state_data.get("bgm_volume", self.settings.BGM_VOLUME))
    #     self.set_volume("sfx", state_data.get("sfx_volume", self.settings.SFX_VOLUME))
    #     self.set_volume("ai_sfx", state_data.get("ai_sfx_volume", self.settings.AI_SFX_VOLUME))