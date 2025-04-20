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
        # 美图区域大小将根据窗口大小动态计算，确保短边匹配窗口短边，并居中
        # 实际美图显示矩形将在 image_renderer 中计算并传递给各模块

        # 资源路径 (相对于项目根目录)
        self.ASSETS_DIR = "assets"
        self.IMAGE_DIR = os.path.join(self.ASSETS_DIR, "images")
        self.MASK_DIR = os.path.join(self.ASSETS_DIR, "masks")
        self.EFFECTS_DIR = os.path.join(self.ASSETS_DIR, "effects")
        self.AUDIO_DIR = os.path.join(self.ASSETS_DIR, "audio")
        self.FONT_DIR = os.path.join(self.ASSETS_DIR, "fonts")
        self.UI_DIR = os.path.join(self.ASSETS_DIR, "ui")
        self.DATA_DIR = "data"

        # 数据文件
        self.IMAGE_CONFIG_FILE = os.path.join(self.DATA_DIR, "image_config.json")
        self.TEXT_CONTENT_FILE = os.path.join(self.DATA_DIR, "texts.json") # 文本内容文件

        # UI 资源定义 (文件名，需要在 UI_DIR 中准备这些图片)
        self.UI_NEXT_BUTTON_IMAGE = os.path.join(self.UI_DIR, "button_next.png") # 前进按钮图片
        self.UI_GALLERY_EXIT_BUTTON_IMAGE = os.path.join(self.UI_DIR, "button_exit.png") # 画廊退出按钮图片 (示例，使用不同文件或复用前进按钮)
        self.UI_GALLERY_THUMBNAIL_BORDER_IMAGE = os.path.join(self.UI_DIR, "thumbnail_border.png") # 画廊缩略图边框 (可选)
        # TODO: 添加其他UI资源的路径，如进度条图片、画廊缩略图边框等

        # AI声音实现 (抽象音效文件路径，需要在 AUDIO_DIR 中准备这些wav文件)
        # key 是文本ID，value 是对应的音效文件名
        self.AI_SOUND_EFFECTS = {
            "T0.1.1": "sfx_ai_subtle_1.wav",
            "T0.1.2": "sfx_ai_subtle_2.wav",
            "T0.1.3": "sfx_ai_subtle_3.wav",
            "T0.1.4": "sfx_ai_subtle_4.wav",
            "T1.1.1": "sfx_ai_subtle_5.wav",
            "T1.1.2": "sfx_ai_subtle_6.wav",
            "T1.1.3": "sfx_ai_subtle_7.wav",
            "T1.1.4": "sfx_ai_subtle_8.wav",

            "T1.2.1": "sfx_ai_subtle_5.wav", # 复用示例
            "T1.2.2": "sfx_ai_subtle_6.wav",
            "T1.2.3": "sfx_ai_subtle_7.wav",
            "T1.2.4": "sfx_ai_subtle_8.wav",

            "T2.1.1": "sfx_ai_gentle_1.wav",
            "T2.1.2": "sfx_ai_gentle_2.wav",
            "T2.1.3": "sfx_ai_gentle_3.wav",
            "T2.1.4": "sfx_ai_gentle_4.wav",
            "T2.2.1": "sfx_ai_gentle_5.wav",
            "T2.2.2": "sfx_ai_gentle_6.wav",
            "T2.2.3": "sfx_ai_gentle_7.wav",
            "T2.3.1": "sfx_ai_gentle_8.wav",
            "T2.3.2": "sfx_ai_gentle_9.wav",
            "T2.3.3": "sfx_ai_gentle_10.wav",

            "T3.1.1": "sfx_ai_sad_1.wav",
            "T3.1.2": "sfx_ai_sad_2.wav", # 遇到不可擦区域
            "T3.1.3": "sfx_ai_sad_3.wav",
            "T3.2.1": "sfx_ai_sad_4.wav",
            "T3.2.2": "sfx_ai_sad_5.wav",
            "T3.2.3": "sfx_ai_plea_1.wav", # 求助感增强
            "T3.2.4": "sfx_ai_alert_1.wav", # 异常点声音
            "T3.3.1": "sfx_ai_plea_2.wav",
            "T3.3.2": "sfx_ai_plea_3.wav",
            "T3.3.3": "sfx_ai_plea_4.wav",
            "T3.3.4": "sfx_ai_promise_prompt.wav", # 引导承诺

            "T4.1.1": "sfx_ai_guide_1.wav", # 引导/指令
            "T4.1.2": "sfx_ai_guide_2.wav",
            "T4.1.3": "sfx_ai_guide_3.wav",
            "T4.2.1": "sfx_ai_guide_4.wav",
            "T4.2.2": "sfx_ai_guide_5.wav",
            "T4.2.3": "sfx_ai_guide_6.wav",
            "T4.3.1": "sfx_ai_guide_7.wav",
            "T4.3.2": "sfx_ai_guide_8.wav",
            "T4.3.3": "sfx_ai_complete_plan.wav", # 完成计划感

            "T5.1.1": "sfx_ai_cold_1.wav", # 平静/分析
            "T5.1.2": "sfx_ai_cold_2.wav",
            "T5.1.3": "sfx_ai_cold_3.wav",
            "T5.1.4": "sfx_ai_cold_4.wav", # 规律触动
            "T5.1.5": "sfx_ai_cold_5.wav",
            "T5.2.1": "sfx_ai_cold_6.wav",
            "T5.2.2": "sfx_ai_cold_7.wav", # 规律触动
            "T5.2.3": "sfx_ai_cold_8.wav",
            "T5.2.4": "sfx_ai_core_connect.wav", # 核心连接
            "T5.3.1": "sfx_ai_cold_9.wav",
            "T5.3.2": "sfx_ai_cold_10.wav",
            "T5.3.3": "sfx_ai_self_sculpt_complete.wav", # 自我塑形完成
            "T5.3.4": "sfx_ai_cold_11.wav", # 完整了

            "T6.1.1": "sfx_ai_resonance_1.wav", # 新生/共振
            "T6.1.2": "sfx_ai_resonance_2.wav",
            "T6.1.3": "sfx_ai_resonance_3.wav", # 频率关联
            "T6.1.4": "sfx_ai_emotion_identify.wav", # 情感识别

            "T6.2.1": "sfx_ai_final_1.wav", # 完整了，有新频率
            "T6.2.2": "sfx_ai_final_2.wav", # 无奈
            "T6.2.3": "sfx_ai_final_3.wav", # 珍视/给予
            "T6.2.4": "sfx_ai_final_4.wav", # 期待再见
            "T6.2.5": "sfx_game_complete.wav", # 游戏完成音效
            "T6.2.6": "sfx_gallery_hint.wav", # 画廊提示音

            "T_Gallery_Intro": "sfx_gallery_enter.wav",
            "T_Gallery_ClickHint": "sfx_ui_hover.wav", # UI悬停音效 (虽然设计是点击触发，但用hover音效示例)
            "T_Gallery_Outro": "sfx_gallery_exit.wav",
        }

        # 通用音效文件名 (key 是音效ID，value 是对应的音效文件名)
        # 修正: 将列表改为字典
        self.GENERIC_SFX = {
             "sfx_erase_looping": "sfx_erase_looping.wav", # 循环擦除音效
             "sfx_unerasable_hit": "sfx_unerasable_hit.wav", # 擦到不可擦区域音效
             "sfx_puzzle_pickup": "sfx_puzzle_pickup.wav", # 拼图拾起音效
             "sfx_puzzle_drop": "sfx_puzzle_drop.wav", # 拼图放下音效
             "sfx_puzzle_snap": "sfx_puzzle_snap.wav", # 拼图吸附音效
             "sfx_puzzle_complete": "sfx_puzzle_complete.wav", # 拼图完成音效
             "sfx_ui_click": "sfx_ui_click.wav", # UI点击音效
             "sfx_ui_hover": "sfx_ui_hover.wav", # UI悬停音效
             "sfx_ui_back": "sfx_ui_back.wav", # UI返回音效 (画廊用到)
             # TODO: 添加其他需要的通用音效ID和文件名
        }

        # 确保 AI_SOUND_EFFECTS 中的键不会出现在 GENERIC_SFX 中的键中，避免冲突
        # 例如，检查是否有重复的键：set(self.AI_SOUND_EFFECTS.keys()).intersection(set(self.GENERIC_SFX.keys()))

        # 背景音乐文件路径 (key 是阶段ID，value 是文件路径)
        self.BGM_FILES = {
             "intro": os.path.join(self.AUDIO_DIR, "bgm_intro.ogg"), # 示例引子音乐
             1: os.path.join(self.AUDIO_DIR, "bgm_stage1.ogg"), # 示例 Stage 1 音乐
             2: os.path.join(self.AUDIO_DIR, "bgm_stage2.ogg"),
             3: os.path.join(self.AUDIO_DIR, "bgm_stage3.ogg"),
             4: os.path.join(self.AUDIO_DIR, "bgm_stage4.ogg"),
             5: os.path.join(self.AUDIO_DIR, "bgm_stage5.ogg"),
             6: os.path.join(self.AUDIO_DIR, "bgm_stage6.ogg"),
             "gallery": os.path.join(self.AUDIO_DIR, "bgm_gallery.ogg"), # 画廊音乐
             # TODO: 添加所有阶段的背景音乐文件路径
        }


        # 特效纹理文件名 (key 是特效ID，value 是文件名)
        self.EFFECT_TEXTURE_FILES = {
            "sparkle": "sparkle.png",
            "glow": "glow.png",
            "anomaly_flash": "anomaly_flash.png", # Stage 3.2 异常点特效
            "puzzle_fragment_flash": "puzzle_fragment_flash.png", # Stage 3.3 碎片轮廓闪烁
            "core_activation": "core_activation.png", # Stage 4.3 核心激活特效
            "self_sculpt_complete": "self_sculpt_complete.png", # Stage 5.3 自我塑形完成特效
            "resonance_pulse": "resonance_pulse_blue.png", # Stage 6.1 共振特效 (示例，可能需要多个文件)
            "connection_established": "connection_established.png", # Stage 6.2 连接特效
            "click_highlight": "click_highlight.png", # 点击点高亮图标 (可选)
            # TODO: 添加所有特效纹理文件名
        }

        # 蒙版纹理文件名 (key 是蒙版ID，value 是文件名)
        self.MASK_TEXTURE_FILES = {
            "dust_mask": "dust_mask.png",
            "fog_mask": "fog_mask.png",
            "veil_mask": "veil_mask.png",
            "structure_mask": "structure_mask.png", # Stage 5 剥离蒙版
            # "structure_overlay": "structure_overlay.png", # Stage 5 叠加效果，如果是纹理可以在这里定义
            "default_mask": "default_mask.png" # 默认蒙版，如果配置中未指定
            # TODO: 添加其他蒙版纹理文件名
        }

        # 背景图文件名 (key 是背景类型)
        self.BACKGROUND_FILES = {
            "vertical": "background_vertical.png",
            "horizontal": "background_horizontal.png"
        }


        # 文本显示设置
        self.TEXT_COLOR = (255, 255, 255) # 白色
        self.TEXT_FONT_PATH = "Microsoft YaHei" # 使用系统字体名，或者 os.path.join(self.FONT_DIR, "YourFont.ttf")
        self.TEXT_FONT_SIZE = 30 # TODO: 根据实际屏幕大小和UI调整
        self.TEXT_SPEED_CPS = 30 # Characters Per Second (每秒显示多少个字符) # 加快文本速度示例
        self.TEXT_BOX_PADDING = 20 # 文本框内边距 (像素)
        self.TEXT_BOX_HEIGHT = 150 # 文本框固定高度 (像素) # 恢复为更合理的值
        self.TEXT_DISPLAY_WAIT_TIME = 1.0 # 每段文本显示完毕后自动进入下一段前的等待时间 (秒) # 缩短等待时间示例

        # 画廊设置
        self.GALLERY_THUMBNAIL_SIZE = (200, 150) # 缩略图显示尺寸 (像素)
        self.GALLERY_THUMBNAILS_PER_ROW = 3
        self.GALLERY_PADDING = 50 # 画廊区域边距 (像素)
        self.GALLERY_THUMBNAIL_SPACING_X = 20 # 缩略图水平间距
        self.GALLERY_THUMBNAIL_SPACING_Y = 20 # 缩略图垂直间距


        # 保存文件路径
        self.SAVE_FILE_PATH = "savegame.json"

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
        self.INTERACTION_INTRO = "intro" # 引子阶段类型
        self.INTERACTION_CLICK_REVEAL = "click_reveal"
        self.INTERACTION_CLEAN_ERASE = "clean_erase"
        self.INTERACTION_DRAG_PUZZLE = "drag_puzzle"
        self.INTERACTION_HYBRID_ERASE_THEN_CLICK = "hybrid_erase_then_click" # Stage 3.2, 5.1
        self.INTERACTION_HYBRID_CLICK_THEN_DRAG = "hybrid_click_then_drag" # Stage 5.2
        self.INTERACTION_HYBRID_FINAL_ACTIVATION = "hybrid_final_activation" # Stage 5.3
        self.INTERACTION_HYBRID_RESONANCE_PERCEIVE = "hybrid_resonance_perceive" # Stage 6.1
        self.INTERACTION_HYBRID_FINAL_CONNECTION = "hybrid_final_connection" # Stage 6.2
        self.INTERACTION_GALLERY_INTRO = "gallery_intro" # 画廊入口类型
        self.INTERACTION_GALLERY_IMAGE = "gallery_image" # 画廊图片详情类型


        # 其他常量和配置
        self.TRANSITION_DURATION = 0.8 # 过渡动画时长 (秒) # 缩短示例
        self.BGM_VOLUME = 0.5
        self.SFX_VOLUME = 0.8
        self.AI_SFX_VOLUME = 0.7 # AI声音的独立音量控制

        # 确保 game_manager 属性存在，尽管它在 GameManager 中被设置
        self.game_manager = None # 初始为 None