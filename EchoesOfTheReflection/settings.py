# settings.py

import os

class Settings:
    """存储游戏的所有设置"""

    def __init__(self):
        """初始化游戏设置"""
        # 游戏窗口设置
        self.DEFAULT_SCREEN_WIDTH = 1920
        self.DEFAULT_SCREEN_HEIGHT = 1080
        self.ASPECT_RATIO = self.DEFAULT_SCREEN_WIDTH / self.DEFAULT_SCREEN_HEIGHT # 16:9

        # 美图显示区域设置 (相对于窗口，居中)
        self.IMAGE_AREA_ASPECT_RATIO = 16 / 9 # 美图区域保持16:9
        # 实际美图显示矩形将在 image_renderer 中计算并传递给各模块

        # 资源路径 (使用 os.path.join 组合路径)
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # 获取 settings.py 所在的目录 (项目根目录)
        self.ASSETS_DIR = os.path.join(self.BASE_DIR, "assets")
        self.IMAGE_DIR = os.path.join(self.ASSETS_DIR, "images")
        self.MASK_DIR = os.path.join(self.ASSETS_DIR, "masks")
        self.EFFECTS_DIR = os.path.join(self.ASSETS_DIR, "effects")
        self.AUDIO_DIR = os.path.join(self.ASSETS_DIR, "audio")
        self.FONT_DIR = os.path.join(self.ASSETS_DIR, "fonts")
        self.UI_DIR = os.path.join(self.ASSETS_DIR, "ui")
        self.DATA_DIR = os.path.join(self.BASE_DIR, "data") # data 目录也在根目录

        # 数据文件
        self.IMAGE_CONFIG_FILE = os.path.join(self.DATA_DIR, "image_config.json")

        # UI 资源定义 (示例，需要你根据实际图片资源来创建)
        self.UI_NEXT_BUTTON_IMAGE = os.path.join(self.UI_DIR, "button_next.png")
        self.UI_GALLERY_HINT_IMAGE = os.path.join(self.UI_DIR, "hint_gallery.png")
        self.UI_GALLERY_EXIT_BUTTON_IMAGE = os.path.join(self.UI_DIR, "button_next.png") # 暂复用前进按钮图片
        # TODO: 添加其他UI资源的路径，如进度条图片、画廊缩略图边框等

        # AI声音实现 (最简单的抽象音效方案) - 使用 os.path.join 确保路径正确
        self.AI_SOUND_EFFECTS = {
            "T0.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_1.wav"),
            "T0.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_2.wav"),
            "T0.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_3.wav"),
            "T0.1.4": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_4.wav"),
            "T1.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_5.wav"),
            "T1.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_6.wav"),
            "T1.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_7.wav"),
            "T1.1.4": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_8.wav"),

            "T1.2.1": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_9.wav"),
            "T1.2.2": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_10.wav"),
            "T1.2.3": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_11.wav"),
            "T1.2.4": os.path.join(self.AUDIO_DIR, "sfx_ai_subtle_12.wav"),

            "T2.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_1.wav"),
            "T2.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_2.wav"),
            "T2.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_3.wav"),
            "T2.1.4": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_4.wav"),
            "T2.2.1": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_5.wav"),
            "T2.2.2": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_6.wav"),
            "T2.2.3": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_7.wav"),
            "T2.3.1": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_8.wav"),
            "T2.3.2": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_9.wav"),
            "T2.3.3": os.path.join(self.AUDIO_DIR, "sfx_ai_gentle_10.wav"),

            "T3.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_sad_1.wav"),
            "T3.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_sad_2.wav"), # 遇到不可擦区域
            "T3.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_sad_3.wav"),
            "T3.2.1": os.path.join(self.AUDIO_DIR, "sfx_ai_sad_4.wav"),
            "T3.2.2": os.path.join(self.AUDIO_DIR, "sfx_ai_sad_5.wav"),
            "T3.2.3": os.path.join(self.AUDIO_DIR, "sfx_ai_plea_1.wav"), # 求助感增强
            "T3.2.4": os.path.join(self.AUDIO_DIR, "sfx_ai_alert_1.wav"), # 异常点声音
            "T3.3.1": os.path.join(self.AUDIO_DIR, "sfx_ai_plea_2.wav"),
            "T3.3.2": os.path.join(self.AUDIO_DIR, "sfx_ai_plea_3.wav"),
            "T3.3.3": os.path.join(self.AUDIO_DIR, "sfx_ai_plea_4.wav"),
            "T3.3.4": os.path.join(self.AUDIO_DIR, "sfx_ai_promise_prompt.wav"), # 引导承诺

            "T4.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_1.wav"), # 引导/指令
            "T4.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_2.wav"),
            "T4.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_3.wav"),
            "T4.2.1": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_4.wav"),
            "T4.2.2": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_5.wav"),
            "T4.2.3": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_6.wav"),
            "T4.3.1": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_7.wav"),
            "T4.3.2": os.path.join(self.AUDIO_DIR, "sfx_ai_guide_8.wav"),
            "T4.3.3": os.path.join(self.AUDIO_DIR, "sfx_ai_complete_plan.wav"), # 完成计划感

            "T5.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_1.wav"), # 平静/分析
            "T5.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_2.wav"),
            "T5.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_3.wav"),
            "T5.1.4": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_4.wav"), # 规律触动
            "T5.1.5": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_5.wav"),
            "T5.2.1": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_6.wav"),
            "T5.2.2": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_7.wav"), # 规律触动
            "T5.2.3": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_8.wav"),
            "T5.2.4": os.path.join(self.AUDIO_DIR, "sfx_ai_core_connect.wav"), # 核心连接
            "T5.3.1": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_9.wav"),
            "T5.3.2": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_10.wav"),
            "T5.3.3": os.path.join(self.AUDIO_DIR, "sfx_ai_self_sculpt_complete.wav"), # 自我塑形完成
            "T5.3.4": os.path.join(self.AUDIO_DIR, "sfx_ai_cold_11.wav"), # 完整了

            "T6.1.1": os.path.join(self.AUDIO_DIR, "sfx_ai_resonance_1.wav"), # 新生/共振
            "T6.1.2": os.path.join(self.AUDIO_DIR, "sfx_ai_resonance_2.wav"),
            "T6.1.3": os.path.join(self.AUDIO_DIR, "sfx_ai_resonance_3.wav"), # 频率关联
            "T6.1.4": os.path.join(self.AUDIO_DIR, "sfx_ai_emotion_identify.wav"), # 情感识别

            "T6.2.1": os.path.join(self.AUDIO_DIR, "sfx_ai_final_1.wav"), # 完整了，有新频率
            "T6.2.2": os.path.join(self.AUDIO_DIR, "sfx_ai_final_2.wav"), # 无奈
            "T6.2.3": os.path.join(self.AUDIO_DIR, "sfx_ai_final_3.wav"), # 珍视/给予
            "T6.2.4": os.path.join(self.AUDIO_DIR, "sfx_ai_final_4.wav"), # 期待再见
            "T6.2.5": os.path.join(self.AUDIO_DIR, "sfx_game_complete.wav"), # 游戏完成音效
            "T6.2.6": os.path.join(self.AUDIO_DIR, "sfx_gallery_hint.wav"), # 画廊提示音

            "T_Gallery_Intro": os.path.join(self.AUDIO_DIR, "sfx_gallery_enter.wav"),
            "T_Gallery_ClickHint": os.path.join(self.AUDIO_DIR, "sfx_ui_hover.wav"), # UI悬停音效
            # T_Gallery_Image_Desc_[Stage.Image] 会使用原图对应的AI音效
            "T_Gallery_Outro": os.path.join(self.AUDIO_DIR, "sfx_gallery_exit.wav"),

            # 通用UI音效
            "sfx_ui_click": os.path.join(self.AUDIO_DIR, "sfx_ui_click.wav"),
            "sfx_ui_hover": os.path.join(self.AUDIO_DIR, "sfx_ui_hover.wav"),

            # TODO: 需要你根据设计和资源，为每个AI文本ID或重要的互动事件定义具体的音效文件路径
            # 资源文件需要你自行准备，并确保路径正确
        }
        # TODO: 添加更多通用音效，如擦除声音、拼图拖拽/吸附声音、特效声音等

        # 文本显示设置
        self.TEXT_COLOR = (255, 255, 255) # 白色
        # self.TEXT_FONT_PATH = os.path.join(self.FONT_DIR, "Microsoft YaHei") # 尝试加载系统字体或文件
        self.TEXT_FONT_PATH = "Microsoft YaHei" # 优先尝试加载系统字体
        self.TEXT_FONT_SIZE = 30 # TODO: 根据实际屏幕大小和UI调整
        self.TEXT_SPEED_CPS = 20 # Characters Per Second (每秒显示多少个字符)
        self.TEXT_BOX_PADDING = 20 # 文本框内边距 (像素)
        self.TEXT_BOX_HEIGHT = 150 # 文本框固定高度 (像素) - TODO: 确认UI设计，是否固定高度
        # 文本框高度自适应或固定，位置RelativeToImageArea 将在 UIManager 中处理

        # 画廊设置
        self.GALLERY_THUMBNAIL_SIZE = (200, 150) # 缩略图显示尺寸 (像素)
        self.GALLERY_THUMBNAILS_PER_ROW = 3
        self.GALLERY_PADDING = 50 # 画廊区域边距 (像素)

        # 保存文件路径
        self.SAVE_FILE_PATH = os.path.join(self.BASE_DIR, "savegame.json") # 保存文件也在根目录

        # 颜色定义 (Pygame常用)
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        # TODO: 添加其他需要的颜色

        # 游戏状态常量
        self.STATE_MENU = "menu"
        self.STATE_GAME = "game"
        self.STATE_GALLERY = "gallery"
        self.STATE_EXIT = "exit"

        # 阶段常量
        self.STAGE_INTRO = "intro"
        self.STAGE_1 = 1
        self.STAGE_2 = 2
        self.STAGE_3 = 3
        self.STAGE_4 = 4
        self.STAGE_5 = 5
        self.STAGE_6 = 6
        self.STAGE_GALLERY = "gallery"

        # 互动类型常量
        self.INTERACTION_INTRO = "intro" # 引子
        self.INTERACTION_CLICK_REVEAL = "click_reveal"
        self.INTERACTION_CLEAN_ERASE = "clean_erase"
        self.INTERACTION_DRAG_PUZZLE = "drag_puzzle"
        self.INTERACTION_HYBRID_ERASE_THEN_CLICK = "hybrid_erase_then_click" # Stage 3.2, 5.1
        self.INTERACTION_HYBRID_CLICK_THEN_DRAG = "hybrid_click_then_drag" # Stage 5.2
        self.INTERACTION_HYBRID_FINAL_ACTIVATION = "hybrid_final_activation" # Stage 5.3
        self.INTERACTION_HYBRID_RESONANCE_PERCEIVE = "hybrid_resonance_perceive" # Stage 6.1
        self.INTERACTION_HYBRID_FINAL_CONNECTION = "hybrid_final_connection" # Stage 6.2
        self.INTERACTION_CLEAN_ERASE_HINT = "clean_erase_hint" # Stage 3.3 擦除+提示
        self.INTERACTION_GALLERY_INTRO = "gallery_intro" # 画廊入口类型
        self.INTERACTION_GALLERY_VIEW = "gallery_view" # 画廊查看单图类型


        # 其他常量和配置
        # 例如， Stage 完成后过渡动画时长，音效音量，背景音乐音量等
        self.TRANSITION_DURATION = 1.0 # 过渡动画时长 (秒)
        self.BGM_VOLUME = 0.5
        self.SFX_VOLUME = 0.8
        self.AI_SFX_VOLUME = 0.7 # AI声音的独立音量控制


        # GameManager 引用 (用于在 Settings 中访问 GameManager，例如在 _load_all_texts 中)
        self.game_manager = None # 初始为None，GameManager 初始化后赋值