# src/game_manager.py
import pygame
import json
import sys
import os
from src.settings import Settings
from src.image_renderer import ImageRenderer
from src.narrative_manager import NarrativeManager
from src.audio_manager import AudioManager
from src.input_handler import InputHandler
# 导入互动模块 (需要你创建这些文件)
from src.interaction_modules import click_reveal, clean_erase, drag_puzzle, hybrid_interaction
from src.gallery_manager import GalleryManager
from src.save_manager import SaveManager
from jsoncomment import JsonComment # 确保你已经安装了这个库

class GameManager:
    """管理游戏状态、阶段、图片加载和流程控制"""

    def _load_image_configs(self):
        """从JSON文件加载所有图片配置 (支持注释)"""
        # 创建一个 JsonComment 解析器实例
        parser = JsonComment() # 默认支持 // 和 /*...*/ 注释

        try:
            # 使用 parser 的 load 方法来加载文件
            with open(self.settings.IMAGE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                # return json.load(f) # 标准 json.load 会在这里报错
                return parser.load(f) # 使用 jsoncomment 加载，会自动忽略注释

        except FileNotFoundError:
            print(f"错误：图片配置文件未找到 {self.settings.IMAGE_CONFIG_FILE}")
            # TODO: 处理错误，例如退出游戏或显示错误信息
            sys.exit()
        except Exception as e: # 捕获更广泛的异常，包括 jsoncomment 的解析错误
            print(f"错误：解析图片配置文件时出错 {self.settings.IMAGE_CONFIG_FILE}: {e}")
            # TODO: 处理错误
            sys.exit()


    def __init__(self, screen, settings: Settings):
        """初始化游戏管理器"""
        self.screen = screen
        self.settings = settings
        self.current_state = settings.STATE_GAME # 初始状态设置为游戏 (跳过菜单)

        # 初始化子系统
        self.image_renderer = ImageRenderer(screen, settings)
        self.narrative_manager = NarrativeManager(screen, settings)
        self.audio_manager = AudioManager(settings)
        self.input_handler = InputHandler()
        self.gallery_manager = GalleryManager(screen, settings, self) # 需要GameManager引用来加载图片和文本
        self.save_manager = SaveManager(settings.SAVE_FILE_PATH)

        # 加载图片配置数据
        self.image_configs = self._load_image_configs()

        # 游戏进度变量
        self.current_stage_id = self.settings.STAGE_INTRO # 当前阶段ID
        self.current_image_id = None # 当前图片ID
        self.unlocked_images = {} # 已解锁的图片ID列表或字典 {image_id: True}
        self.current_image_interaction_state = None # 当前图片的互动模块实例

        # 加载或开始新游戏
        self._load_or_start_game()

        # 标记首次进入某个阶段，用于触发on_stage_enter文本
        self._entered_stages = {stage_id: False for stage_id in [
            self.settings.STAGE_INTRO, self.settings.STAGE_1, self.settings.STAGE_2,
            self.settings.STAGE_3, self.settings.STAGE_4, self.settings.STAGE_5,
            self.settings.STAGE_6, self.settings.STAGE_GALLERY
        ]}

    def _load_or_start_game(self):
        """尝试加载进度，否则开始新游戏"""
        saved_game = self.save_manager.load_game()
        if saved_game:
            print("加载游戏进度...")
            self.current_stage_id = saved_game.get("current_stage_id", self.settings.STAGE_INTRO)
            self.current_image_id = saved_game.get("current_image_id", None)
            self.unlocked_images = saved_game.get("unlocked_images", {})
            # TODO: 加载更详细的当前图片互动状态 (例如，点击显影已点的点，擦除进度，拼图已完成的块等)
            # 这需要每个互动模块提供保存和加载自身状态的方法

            # 根据加载的进度跳转到对应的阶段和图片
            if self.current_stage_id == self.settings.STAGE_GALLERY:
                self._set_state(self.settings.STATE_GALLERY)
            else:
                 self._set_state(self.settings.STATE_GAME)
                 self._load_stage(self.current_stage_id, self.current_image_id)

        else:
            print("开始新游戏...")
            # 从引子阶段开始
            self._set_state(self.settings.STATE_GAME)
            self.unlocked_images = {}
            self._load_stage(self.settings.STAGE_INTRO) # 从引子阶段开始

    def _set_state(self, new_state):
        """设置当前游戏状态"""
        print(f"游戏状态切换：从 {self.current_state} 到 {new_state}")
        self.current_state = new_state
        # TODO: 根据状态切换，控制不同管理器的启用/禁用，例如：
        # if new_state == self.settings.STATE_GALLERY:
        #    self.gallery_manager.enter_gallery(self.unlocked_images)
        # elif self.current_state == self.settings.STATE_GALLERY and new_state == self.settings.STATE_GAME:
        #    self.gallery_manager.exit_gallery()
        # etc.

    def _load_stage(self, stage_id, image_id=None):
        """加载指定阶段"""
        print(f"加载阶段: {stage_id}")
        self.current_stage_id = stage_id
        # TODO: 根据阶段ID加载背景音乐
        # self.audio_manager.play_bgm(f"bgm_stage{stage_id}.ogg") # 示例

        # 触发阶段进入文本 (如果尚未进入过)
        if not self._entered_stages.get(stage_id, False):
            self._entered_stages[stage_id] = True
            # 找到该阶段的第一张图或引子配置，看是否有on_stage_enter文本
            if stage_id == self.settings.STAGE_INTRO:
                 config = self.image_configs.get("intro_title")
            else:
                 # 找到该阶段的第一张图配置
                 first_image_id_in_stage = None
                 for img_id, cfg in self.image_configs.items():
                     if cfg.get("stage") == stage_id and cfg.get("index") == 1:
                         first_image_id_in_stage = img_id
                         break
                 config = self.image_configs.get(first_image_id_in_stage) if first_image_id_in_stage else None

            if config and "on_stage_enter" in config.get("narrative_triggers", {}):
                 self.narrative_manager.start_narrative(config["narrative_triggers"]["on_stage_enter"])


        # 加载该阶段的第一张图片或指定的图片
        if image_id:
            self._load_image(image_id)
        else:
            # 找到该阶段的第一张图片ID (引子阶段除外，它没有图片)
            if stage_id != self.settings.STAGE_INTRO:
                first_image_id_in_stage = None
                for img_id, cfg in self.image_configs.items():
                    if cfg.get("stage") == stage_id and cfg.get("index") == 1:
                        first_image_id_in_stage = img_id
                        break
                if first_image_id_in_stage:
                     self._load_image(first_image_id_in_stage)
                else:
                     print(f"错误：未找到阶段 {stage_id} 的第一张图片配置")
                     # TODO: 错误处理

    def _load_image(self, image_id):
        """加载指定图片及其互动配置"""
        config = self.image_configs.get(image_id)
        if not config:
            print(f"错误：未找到图片配置 {image_id}")
            # TODO: 错误处理
            return

        print(f"加载图片: {image_id}")
        self.current_image_id = image_id

        # 加载图片并应用初始效果
        if config.get("file"):
             image_path = os.path.join(self.settings.IMAGE_DIR, config["file"])
             self.image_renderer.load_image(image_path)
             if config.get("initial_effect"):
                 self.image_renderer.apply_effect(config["initial_effect"]["type"], config["initial_effect"].get("strength")) # 示例参数

        # 创建并初始化对应的互动模块
        interaction_type = config.get("type")
        if interaction_type == self.settings.INTERACTION_CLICK_REVEAL:
            self.current_image_interaction_state = click_reveal.ClickReveal(config, self.image_renderer)
        elif interaction_type == self.settings.INTERACTION_CLEAN_ERASE:
            self.current_image_interaction_state = clean_erase.CleanErase(config, self.image_renderer, self.screen) # Clean Erase 需要screen来绘制RenderTexture
        elif interaction_type == self.settings.INTERACTION_DRAG_PUZZLE:
            self.current_image_interaction_state = drag_puzzle.DragPuzzle(config, self.image_renderer)
        elif interaction_type.startswith("hybrid_"): # 混合玩法
             self.current_image_interaction_state = hybrid_interaction.HybridInteraction(interaction_type, config, self.image_renderer, self.screen) # 混合玩法可能需要screen
        elif interaction_type == self.settings.INTERACTION_INTRO or interaction_type == self.settings.INTERACTION_GALLERY_INTRO:
             # 引子或画廊入口，可能只有文本或简单的展示
             self.current_image_interaction_state = None # 没有复杂的互动状态
        else:
            print(f"警告：未知的互动类型 {interaction_type} for {image_id}")
            self.current_image_interaction_state = None

        # 解锁当前图片到画廊 (在加载时解锁，而不是完成时，为了能看到加载时的效果)
        self.unlocked_images[image_id] = True
        self.save_manager.save_game({
             "current_stage_id": self.current_stage_id,
             "current_image_id": self.current_image_id,
             "unlocked_images": self.unlocked_images
             # TODO: 保存当前互动模块的状态
        })

        # 触发图片进入文本 (on_stage_enter 在_load_stage里触发)
        # on_stage_enter 在_load_stage里触发，这里不重复
        # if "on_stage_enter" in config.get("narrative_triggers", {}):
        #      self.narrative_manager.start_narrative(config["narrative_triggers"]["on_stage_enter"])


    def handle_events(self):
        """处理Pygame事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: # 按下Esc键
                    self._quit_game()
                # TODO: 其他键盘事件，例如画廊的导航

            # 将事件传递给当前状态或互动模块处理
            if self.current_state == self.settings.STATE_GAME:
                # 将事件传递给当前的互动模块
                if self.current_image_interaction_state:
                    self.current_image_interaction_state.handle_event(event, self.image_renderer.image_display_rect) # 将图片显示区域传递过去进行坐标转换
            elif self.current_state == self.settings.STATE_GALLERY:
                self.gallery_manager.handle_event(event)
            # TODO: 其他状态的事件处理 (如菜单)

            # 处理UI点击事件 (前进按钮等)
            # 这里的UI管理需要一个集中的地方处理，例如 UIManager 类
            # if event.type == pygame.MOUSEBUTTONDOWN:
            #    if self.ui_manager.is_button_clicked("next_button", event.pos):
            #        self._go_to_next_image()

    def update(self):
        """更新游戏状态"""
        # 根据当前状态更新不同的部分
        if self.current_state == self.settings.STATE_GAME:
            # 更新当前图片的互动状态
            if self.current_image_interaction_state:
                # 互动模块的update方法返回是否完成当前互动，以及可能触发的叙事文本ID
                is_completed, narrative_events = self.current_image_interaction_state.update(self.image_renderer.image_display_rect)

                # 处理互动完成和叙事触发
                if is_completed:
                     self._on_interaction_complete()

                if narrative_events:
                     for event_type, text_ids in narrative_events.items():
                          if text_ids:
                                print(f"触发叙事事件: {event_type}, 文本ID: {text_ids}")
                                self.narrative_manager.start_narrative(text_ids, self._get_ai_sound_for_text_id) # 传递获取音效的函数
            else:
                # 对于只有文本的图片 (如引子)，等待文本播放完毕自动进入下一图
                if self.image_configs.get(self.current_image_id) and self.image_configs[self.current_image_id].get("type") in [self.settings.INTERACTION_INTRO] and not self.narrative_manager.is_narrative_active():
                     self._go_to_next_image()


            # 更新叙事文本显示
            self.narrative_manager.update()

            # TODO: 更新其他游戏元素，如特效、背景动画等
            # self.image_renderer.update_effects() # 如果有随时间变化的特效

        elif self.current_state == self.settings.STATE_GALLERY:
            self.gallery_manager.update()
        # TODO: 其他状态的更新 (如菜单)

        # 保存进度 (可以定期保存，或在关键节点保存)
        # self._save_game() # 示例，实际应用中不宜频繁保存

    def draw(self):
        """绘制所有游戏元素"""
        # 清屏
        self.screen.fill(self.settings.BLACK) # 或绘制背景图

        # TODO: 绘制背景图 (根据当前屏幕分辨率和全屏状态绘制横屏或竖屏背景)
        # self.image_renderer.draw_background()

        # 根据当前状态绘制不同的内容
        if self.current_state == self.settings.STATE_GAME:
            # 绘制当前图片及其效果
            if self.current_image_id and self.image_configs.get(self.current_image_id) and self.image_configs[self.current_image_id].get("file"):
                 self.image_renderer.draw_image(self.current_image_id) # ImageRenderer需要知道如何根据当前互动状态绘制图片 (例如，应用蒙版，绘制拼图块等)

            # 绘制当前的互动元素 (例如，点击点的高亮，拼图块)
            if self.current_image_interaction_state:
                self.current_image_interaction_state.draw(self.screen, self.image_renderer.image_display_rect) # 将图片显示区域传递过去进行坐标转换

            # 绘制UI元素 (文本框、前进按钮等)
            self.narrative_manager.draw(self.screen) # 绘制文本框和文本
            # self.ui_manager.draw(self.screen) # 绘制按钮等

        elif self.current_state == self.settings.STATE_GALLERY:
            self.gallery_manager.draw(self.screen)
        # TODO: 其他状态的绘制 (如菜单)

    def _on_interaction_complete(self):
        """当前图片的主要互动完成后触发"""
        print(f"图片 {self.current_image_id} 互动完成。")
        config = self.image_configs.get(self.current_image_id)
        if not config:
            return

        # 播放完成音效或触发完成动画
        # self.audio_manager.play_sfx(self.settings.SFX_COMPLETE) # 示例通用完成音效
        # if config.get("complete_feedback_effect_id"):
        #      self.image_renderer.trigger_effect(config["complete_feedback_effect_id"]) # 触发图片完成特效

        # 在互动完成后，通常会播放这张图的最终叙事文本 (如果还没播放的话)
        # 互动模块的 update 方法已经触发了相应的 narrative_events，这里确保所有完成后的文本都已播放
        if "on_complete" in config.get("narrative_triggers", {}):
             self.narrative_manager.start_narrative(config["narrative_triggers"]["on_complete"], self._get_ai_sound_for_text_id) # 传递获取音效的函数

        # 互动完成后，等待所有文本播放完毕才能进入下一张图
        # 进入下一图的逻辑放在 NarrativeManager 的 update 方法中判断文本播放结束时触发，或者由一个“前进”按钮触发

        # TODO: 保存完成状态
        # self._save_game() # 关键节点保存

    def _go_to_next_image(self):
        """加载下一张图片"""
        config = self.image_configs.get(self.current_image_id)
        if not config:
            print(f"错误：无法找到当前图片配置 {self.current_image_id} 来确定下一张图片。")
            # TODO: 错误处理
            return

        next_image_id = config.get("next_image")
        next_stage_id = config.get("next_stage") # 如果配置了阶段跳转

        if next_stage_id == self.settings.STAGE_GALLERY:
             # 进入画廊阶段
             self._set_state(self.settings.STATE_GALLERY)
             self._load_stage(self.settings.STAGE_GALLERY) # 加载画廊阶段
        elif next_stage_id:
             # 跳转到新的阶段 (通常从新阶段的第一张图开始)
             self._load_stage(next_stage_id)
        elif next_image_id:
            # 加载同一阶段的下一张图片
            self._load_image(next_image_id)
        else:
            # 这是最后一张图片且没有下一阶段/图片
            print("游戏流程结束！")
            # TODO: 游戏通关结局处理，例如显示一个最终画面或直接进入画廊（如果没有特殊结局画面）
            self._set_state(self.settings.STATE_GALLERY)
            self._load_stage(self.settings.STAGE_GALLERY)


    def _get_ai_sound_for_text_id(self, text_id):
         """根据文本ID获取对应的AI声音音效路径"""
         # 这个函数作为回调传递给 NarrativeManager
         return self.settings.AI_SOUND_EFFECTS.get(text_id)

    def _save_game(self):
        """保存游戏进度"""
        save_data = {
            "current_stage_id": self.current_stage_id,
            "current_image_id": self.current_image_id,
            "unlocked_images": self.unlocked_images,
            # TODO: 添加当前图片互动模块的状态保存数据
            # "current_interaction_state_data": self.current_image_interaction_state.get_state() if self.current_image_interaction_state else None
        }
        self.save_manager.save_game(save_data)

    # TODO: 添加_load_game方法，在初始化时调用 SaveManager 加载

    def _quit_game(self):
        """退出游戏"""
        # TODO: 在退出前保存游戏进度
        # self._save_game()
        pygame.quit()
        sys.exit()

    # UI点击处理示例 (可以集成到 UIManager 或 GameManager 中)
    # def _handle_ui_click(self, pos):
    #    if self.current_state == self.settings.STATE_GAME:
    #        if self.ui_manager.is_button_clicked("next_button", pos) and not self.narrative_manager.is_narrative_active():
    #            self._go_to_next_image()
    #    elif self.current_state == self.settings.STATE_GALLERY:
    #        clicked_image_id = self.gallery_manager.get_clicked_thumbnail_id(pos)
    #        if clicked_image_id:
    #            self.gallery_manager.display_image_detail(clicked_image_id)
    #        elif self.ui_manager.is_button_clicked("gallery_exit_button", pos):
    #            self._exit_gallery() # TODO: 实现退出画廊方法