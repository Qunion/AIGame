# src/audio_manager.py
import pygame
import os
from src.settings import Settings

class AudioManager:
    """管理背景音乐和音效的播放"""

    def __init__(self, settings: Settings):
        """初始化音频管理器"""
        self.settings = settings
        pygame.mixer.init() # 初始化混音器模块

        self.bgm_channel = pygame.mixer.Channel(0) # 专门用于背景音乐的通道
        self.sfx_channels = [pygame.mixer.Channel(i) for i in range(1, pygame.mixer.get_num_channels())] # 用于音效的通道，排除0

        self.bgm_volume = settings.BGM_VOLUME
        self.sfx_volume = settings.SFX_VOLUME
        self.ai_sfx_volume = settings.AI_SFX_VOLUME

        # 加载音效字典 (AI声音和其他音效)
        # AI声音音效路径已在 settings.AI_SOUND_EFFECTS 中定义
        # TODO: 加载其他通用音效到字典 {sfx_id: Pygame Sound}
        self.loaded_sfx = {}
        self._load_all_sfx()


    def _load_all_sfx(self):
        """加载所有预定义的音效文件"""
        # 加载AI声音音效
        for text_id, file_path in self.settings.AI_SOUND_EFFECTS.items():
             try:
                 self.loaded_sfx[text_id] = pygame.mixer.Sound(file_path)
             except pygame.error as e:
                 print(f"警告：无法加载AI声音音效 {file_path}: {e}")
                 self.loaded_sfx[text_id] = None # 加载失败则设为None

        # 加载其他通用音效 (例如，在 settings 中添加一个通用音效字典)
        # 例如：
        # self.settings.GENERIC_SFX = {"sfx_click": "path/to/click.wav", ...}
        # for sfx_id, file_path in self.settings.GENERIC_SFX.items():
        #     try:
        #         self.loaded_sfx[sfx_id] = pygame.mixer.Sound(os.path.join(self.settings.AUDIO_DIR, file_path))
        #     except pygame.error as e:
        #         print(f"警告：无法加载通用音效 {file_path}: {e}")
        #         self.loaded_sfx[sfx_id] = None


    def play_bgm(self, bgm_path, loop=-1, volume=None):
        """播放背景音乐"""
        if volume is None:
            volume = self.bgm_volume

        try:
            bgm_sound = pygame.mixer.Sound(bgm_path)
            bgm_sound.set_volume(volume)
            self.bgm_channel.play(bgm_sound, loops=loop)
        except pygame.error as e:
            print(f"警告：无法播放背景音乐 {bgm_path}: {e}")

    def stop_bgm(self):
        """停止背景音乐"""
        self.bgm_channel.stop()

    def play_sfx(self, sfx_id_or_path, loop=0, volume=None):
        """
        播放音效。
        sfx_id_or_path: 音效ID (如文本ID) 或直接的文件路径。
        """
        if volume is None:
            # 根据ID判断是AI声音还是通用音效来设置音量
            if sfx_id_or_path in self.settings.AI_SOUND_EFFECTS:
                 volume = self.ai_sfx_volume
            # elif sfx_id_or_path in self.settings.GENERIC_SFX: # 示例
            #      volume = self.sfx_volume
            else: # 默认为通用音效音量
                 volume = self.sfx_volume


        sfx_sound = self.loaded_sfx.get(sfx_id_or_path) # 尝试从加载的音效中获取

        # 如果不是已加载的音效ID，尝试作为文件路径加载（不推荐，效率低）
        # if sfx_sound is None and os.path.exists(sfx_id_or_path):
        #     try:
        #         sfx_sound = pygame.mixer.Sound(sfx_id_or_path)
        #     except pygame.error as e:
        #         print(f"警告：无法加载音效 {sfx_id_or_path}: {e}")
        #         return

        if sfx_sound:
            sfx_sound.set_volume(volume)
            # 查找一个空闲的音效通道播放
            for channel in self.sfx_channels:
                if not channel.get_busy():
                    channel.play(sfx_sound, loops=loop)
                    return
            # 如果没有空闲通道，强制停止一个最老的通道或忽略
            # print("警告：音效通道不足，无法播放音效")
            # 简单处理：如果通道0（BGM通道）空闲且不是BGM，可以用一下
            if not self.bgm_channel.get_busy() or self.bgm_channel.get_sound() != self.bgm_channel.get_sound(): # 确保不是正在播BGM
                 self.bgm_channel.play(sfx_sound, loops=loop)
            # else: 忽略播放

    def stop_sfx(self, sfx_id_or_path=None):
        """停止指定的音效或所有音效"""
        if sfx_id_or_path is None:
            # 停止所有音效通道
            for channel in self.sfx_channels:
                channel.stop()
        else:
             # TODO: 找到播放指定音效的通道并停止
             # This is tricky as channels only return Sound objects, not IDs
             pass # Not implemented in this basic framework

    def is_sfx_playing(self, sfx_id_or_path):
        """检查指定的音效是否正在播放"""
        # TODO: Need to track which sound is playing on which channel
        pass # Not implemented in this basic framework

    def set_volume(self, audio_type, volume):
        """设置指定类型的音量 (bgm, sfx, ai_sfx)"""
        if audio_type == "bgm":
            self.bgm_volume = volume
            self.bgm_channel.set_volume(volume)
        elif audio_type == "sfx":
            self.sfx_volume = volume
            # TODO: 更新所有音效通道的音量，或只影响新播放的音效
            pass
        elif audio_type == "ai_sfx":
            self.ai_sfx_volume = volume
            # TODO: 更新正在播放的AI声音音量
            pass

    # TODO: 添加保存和加载音量设置的方法