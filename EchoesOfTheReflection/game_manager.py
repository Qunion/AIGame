# game_manager.py
import pygame
import json
import sys
import os
# 导入自定义模块 - 现在它们位于根目录
from settings import Settings
from image_renderer import ImageRenderer
from narrative_manager import NarrativeManager
from audio_manager import AudioManager
from input_handler import InputHandler
# 导入互动模块 - 现在它们在 interaction_modules 子目录
from interaction_modules import click_reveal, clean_erase, drag_puzzle, hybrid_interaction
from gallery_manager import GalleryManager
from save_manager import SaveManager
from ui_manager import UIManager
from jsoncomment import JsonComment # 确保你已经安装了这个库
import os # 导入 os 模块


class GameManager:
    """管理游戏状态、阶段、图片加载和流程控制"""

    def _load_image_configs(self):
        """从JSON文件加载所有图片配置 (支持注释)"""
        # 创建一个 JsonComment 解析器实例
        parser = JsonComment() # 默认支持 // 和 /*...*/ 注释

        try:
            # 使用 parser 的 load 方法来加载文件
            # 使用 settings.IMAGE_CONFIG_FILE 获取完整路径
            with open(self.settings.IMAGE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return parser.load(f) # 使用 jsoncomment 加载，会自动忽略注释
        except FileNotFoundError:
            print(f"错误：图片配置文件未找到 {self.settings.IMAGE_CONFIG_FILE}")
            # TODO: 处理错误，例如退出游戏或显示错误信息
            self.should_quit = True # 无法加载配置，标记退出
            return {} # 返回空字典避免后续错误
        except Exception as e: # 捕获更广泛的异常，包括 jsoncomment 的解析错误
            print(f"错误：解析图片配置文件时出错 {self.settings.IMAGE_CONFIG_FILE}: {e}")
            # TODO: 处理错误
            self.should_quit = True # 解析错误，标记退出
            return {} # 返回空字典


    def __init__(self, screen, settings: Settings):
        """初始化游戏管理器"""
        self.screen = screen
        self.settings = settings

        # 将 GameManager 引用赋值给 settings，以便其他模块可以访问
        self.settings.game_manager = self

        # 初始化子系统 (ImageRenderer 需要在最前面初始化，因为它负责显示)
        self.image_renderer = ImageRenderer(screen, settings) # ImageRenderer 在 __init__ 中不需要 GameManager 引用

        # 初始化其他管理器
        self.audio_manager = AudioManager(settings) # AudioManager 在 __init__ 中也不需要 GameManager 引用
        # NarrativeManager 需要 settings 才能获取文本
        self.narrative_manager = NarrativeManager(screen, settings)
        # NarrativeManager 在 __init__ 中加载文本时需要 settings.game_manager 引用，所以在赋值 settings.game_manager = self 之后初始化它

        self.input_handler = InputHandler()

        # UIManager 需要 GameManager 引用
        self.ui_manager = UIManager(screen, settings, self)
        self.gallery_manager = GalleryManager(screen, settings, self)
        self.save_manager = SaveManager(settings.SAVE_FILE_PATH)

        # 加载图片配置数据 (在所有管理器初始化后加载，因为它们可能需要在加载时访问settings或彼此)
        self.image_configs = self._load_image_configs()

        # 游戏进度变量
        self.current_stage_id = None
        self.current_image_id = None # 当前图片ID
        self.unlocked_images = {} # 已解锁的图片ID列表或字典 {image_id: True}
        self.current_image_interaction_state = None # 当前图片的互动模块实例

        # 标记首次进入某个阶段，用于触发on_stage_enter文本
        self._entered_stages = {stage_id: False for stage_id in [
            self.settings.STAGE_INTRO, self.settings.STAGE_1, self.settings.STAGE_2,
            self.settings.STAGE_3, self.settings.STAGE_4, self.settings.STAGE_5,
            self.settings.STAGE_6, self.settings.STAGE_GALLERY
        ]}

        # 标记游戏是否应该退出
        self.should_quit = False

        # 加载或开始新游戏
        if not self.should_quit: # 只有在加载配置没有错误时才开始游戏流程
            self._load_or_start_game() # _load_or_start_game 会设置初始状态和加载第一张图/阶段


    def _load_or_start_game(self):
        """尝试加载进度，否则开始新游戏"""
        saved_game = self.save_manager.load_game()
        if saved_game:
            print("加载游戏进度...")
            self.current_stage_id = saved_game.get("current_stage_id", self.settings.STAGE_INTRO)
            self.current_image_id = saved_game.get("current_image_id", None)
            self.unlocked_images = saved_game.get("unlocked_images", {})
            self._entered_stages = saved_game.get("_entered_stages", {stage_id: False for stage_id in self._entered_stages}) # 加载已进入过的阶段，确保字典结构正确
            # TODO: 加载更详细的当前图片互动模块的状态 (需要每个互动模块实现保存和加载自身状态的方法)
            # saved_interaction_state_data = saved_game.get("current_interaction_state_data") # 示例


            # 根据加载的进度跳转到对应的阶段和图片
            if self.current_stage_id == self.settings.STAGE_GALLERY:
                self._set_state(self.settings.STATE_GALLERY)
                # 如果加载时就在画廊，可能需要恢复画廊查看的具体图片
                if self.current_image_id: # 如果画廊状态还保存了当前查看的图片ID
                    self.gallery_manager.display_image_detail(self.current_image_id) # 通知画廊管理器显示详情
                    self.gallery_manager.detail_text_manager.update() # 立即更新一次文本显示

            else: # 游戏阶段
                 self._set_state(self.settings.STATE_GAME)
                 # 加载时需要判断是继续当前图片还是进入下一张/阶段
                 if self.current_image_id:
                      # 加载图片
                       self._load_image(self.current_image_id)
                       # 恢复互动模块状态 (在 _load_image 创建模块后)
                       # if self.current_image_interaction_state and saved_interaction_state_data:
                       #    if hasattr(self.current_image_interaction_state, 'load_state'):
                       #         self.current_image_interaction_state.load_state(saved_interaction_state_data, self.image_renderer.image_display_rect) # 示例

                 else:
                      # 从当前阶段的第一张图开始 (如果 current_image_id 为 None)
                      self._load_stage(self.current_stage_id)


        else:
            print("开始新游戏...")
            # 从引子阶段开始
            self._set_state(self.settings.STATE_GAME) # 初始状态设为 GAME
            self.unlocked_images = {}
            self._entered_stages = {stage_id: False for stage_id in self._entered_stages} # 重置已进入过的阶段
            self.current_image_id = "intro_title" # 明确从引子开始
            self._load_stage(self.settings.STAGE_INTRO) # 从引子阶段开始加载


    def _set_state(self, new_state):
        """设置当前游戏状态"""
        # 检查是否已经在目标状态
        if hasattr(self, 'current_state') and self.current_state == new_state:
             return

        # 停止当前状态可能有的循环音效等
        # TODO: 停止当前互动模块的循环音效
        # if hasattr(self, 'current_state') and self.current_state == self.settings.STATE_GAME and self.current_image_interaction_state and hasattr(self.current_image_interaction_state, 'stop_looping_sfx'):
        #     self.current_image_interaction_state.stop_looping_sfx() # 示例停止互动模块的循环音效
        # TODO: 停止当前阶段的背景音乐
        self.audio_manager.stop_bgm()


        old_state = getattr(self, 'current_state', None) # 获取旧状态，处理第一次初始化
        self.current_state = new_state
        print(f"游戏状态切换：从 {old_state} 到 {self.current_state}")

        # 根据状态切换，控制不同管理器的启用/禁用，UI集合的激活
        if new_state == self.settings.STATE_GAME:
           self.ui_manager.set_ui_set_active("game_ui")
           # 游戏阶段背景音乐在 _load_stage 里加载第一张图时播放
           self.image_renderer.switch_background("vertical") # 切换到竖屏背景 (默认窗口)
           pass
        elif new_state == self.settings.STATE_GALLERY:
           self.ui_manager.set_ui_set_active("gallery_ui")
           # GalleryManager.enter_gallery 在这里调用，它内部加载缩略图和触发画廊进入文本
           # 它需要知道已解锁的图片列表
           self.gallery_manager.enter_gallery(self.unlocked_images)
           # TODO: 播放画廊背景音乐
           # self.audio_manager.play_bgm("bgm_gallery.ogg") # 示例
           self.image_renderer.switch_background("horizontal") # 切换到横屏背景
           pass
        # elif new_state == self.settings.STATE_MENU: # 示例菜单状态
        #    self.ui_manager.set_ui_set_active("menu_ui")
        #    self.audio_manager.play_bgm("bgm_menu.ogg") # 示例
        #    self.image_renderer.switch_background("vertical") # 切换到竖屏背景
        #    pass
        # elif new_state == self.settings.STATE_EXIT: # 退出状态
        #    self.ui_manager.set_ui_set_active(None) # 隐藏所有UI
        #    self.audio_manager.stop_bgm() # 停止背景音乐
        #    self.audio_manager.stop_sfx() # 停止所有音效
        #    self.should_quit = True # 设置退出标志


    def _load_stage(self, stage_id, image_id=None):
        """加载指定阶段"""
        # ... _load_stage 方法内容同之前，确保逻辑正确
        print(f"加载阶段: {stage_id}")
        self.current_stage_id = stage_id

        # 激活当前阶段对应的UI集合 (已经在 _set_state 中处理)

        # TODO: 根据阶段ID加载背景音乐 (在这里播放背景音乐更合适)
        # Stage 1, 2, 3, 4, 5, 6 是游戏阶段
        if stage_id in [self.settings.STAGE_1, self.settings.STAGE_2, self.settings.STAGE_3, self.settings.STAGE_4, self.settings.STAGE_5, self.settings.STAGE_6]:
             self.audio_manager.play_bgm(f"bgm_stage{stage_id}.ogg") # 示例，需要根据实际Stage ID映射到音乐文件


        # 触发阶段进入文本 (如果尚未进入过)
        if not self._entered_stages.get(stage_id, False):
            self._entered_stages[stage_id] = True
            # 找到该阶段的第一张图或引子配置，看是否有on_stage_enter文本
            if stage_id == self.settings.STAGE_INTRO:
                 config = self.image_configs.get("intro_title")
            elif stage_id == self.settings.STAGE_GALLERY: # 画廊阶段也有进入文本
                 config = self.image_configs.get("gallery_intro")
            else:
                 # 找到该阶段的第一张图配置
                 first_image_id_in_stage = None
                 # 按照 index 找到该阶段 index 为 1 的图片ID
                 for img_id, cfg in self.image_configs.items():
                     if cfg.get("stage") == stage_id and cfg.get("index") == 1:
                         first_image_id_in_stage = img_id
                         break
                 config = self.image_configs.get(first_image_id_in_stage) if first_image_id_in_stage else None

            if config and "on_stage_enter" in config.get("narrative_triggers", {}):
                 self.narrative_manager.start_narrative(config["narrative_triggers"]["on_stage_enter"], self._get_ai_sound_for_text_id)
                 # 引子阶段没有图片，加载引子文本后，当文本播放完毕，_go_to_next_image 会被调用

        # 加载该阶段的第一张图片或指定的图片
        # 只有游戏阶段 (Stage 1-6) 有图片需要加载
        if stage_id in [self.settings.STAGE_1, self.settings.STAGE_2, self.settings.STAGE_3, self.settings.STAGE_4, self.settings.STAGE_5, self.settings.STAGE_6]:
             if image_id:
                 self._load_image(image_id)
             else:
                 # 找到该阶段的第一张图片ID
                 first_image_id_in_stage = None
                 # 按照 index 找到该阶段 index 为 1 的图片ID
                 for img_id, cfg in self.image_configs.items():
                     if cfg.get("stage") == stage_id and cfg.get("index") == 1:
                         first_image_id_in_stage = img_id
                         break
                 if first_image_id_in_stage:
                      self._load_image(first_image_id_in_stage)
                 else:
                      print(f"错误：游戏阶段 {stage_id} 没有配置 index 为 1 的图片。")
                      # TODO: 错误处理，例如加载一个错误占位图或进入错误状态


    def _load_image(self, image_id):
        """加载指定图片及其互动配置"""
        # ... _load_image 方法内容同之前，确保逻辑正确
        config = self.image_configs.get(image_id)
        if not config:
            print(f"错误：未找到图片配置 {image_id}")
            # TODO: 错误处理，例如加载一个错误占位图或进入错误状态
            self.current_image_id = None
            self.current_image_interaction_state = None
            self.image_renderer.current_image = None # 清空图片显示
            self.image_renderer.original_image = None
            self.image_renderer.original_image_size = (0,0)
            self.image_renderer.image_display_rect = pygame.Rect(0, 0, 0, 0) # 没有图片区域
            self.ui_manager._calculate_ui_positions(self.image_renderer.image_display_rect) # 重新计算UI位置
            self.ui_manager.set_element_visible("next_button", False) # 确保前进按钮隐藏
            return


        print(f"加载图片: {image_id}")
        self.current_image_id = image_id

        # 加载图片并应用初始效果
        if config.get("file"):
             # 使用 settings.IMAGE_DIR 获取完整路径
             image_path = os.path.join(self.settings.IMAGE_DIR, config["file"])
             self.image_renderer.load_image(image_path) # load_image 中会计算 image_display_rect

             # 当图片加载完成且显示区域确定后，更新UI元素的位置
             self.ui_manager._calculate_ui_positions(self.image_renderer.image_display_rect)

             # 应用初始效果
             if config.get("initial_effect"):
                 # ImageRenderer 应用效果时需要知道当前图片ID，以便在draw中根据状态绘制不同效果
                 self.image_renderer.apply_effect(config["initial_effect"]["type"], config["initial_effect"].get("strength"), image_id) # 传递 image_id

        else: # 纯文本图片 (如引子), 没有文件，清空当前图片显示
            self.image_renderer.current_image = None
            self.image_renderer.original_image = None
            self.image_renderer.original_image_size = (0,0)
            self.image_renderer.image_display_rect = pygame.Rect(0, 0, 0, 0) # 没有图片区域
            self.ui_manager._calculate_ui_positions(self.image_renderer.image_display_rect) # 仍然计算UI位置，虽然相对零区域可能不精确，取决于UI定位设计


        # 创建并初始化对应的互动模块
        interaction_type = config.get("type")
        if interaction_type == self.settings.INTERACTION_CLICK_REVEAL:
            self.current_image_interaction_state = click_reveal.ClickReveal(config, self.image_renderer)
        elif interaction_type == self.settings.INTERACTION_CLEAN_ERASE:
            self.current_image_interaction_state = clean_erase.CleanErase(config, self.image_renderer, self.screen) # Clean Erase 需要screen来绘制RenderTexture
        elif interaction_type == self.settings.INTERACTION_DRAG_PUZZLE:
            self.current_image_interaction_state = drag_puzzle.DragPuzzle(config, self.image_renderer)
        elif interaction_type.startswith("hybrid_"): # 混合玩法
             self.current_image_interaction_state = hybrid_interaction.HybridInteraction(interaction_type, config, self.image_renderer, self.screen)
        elif interaction_type in [self.settings.INTERACTION_INTRO, self.settings.INTERACTION_GALLERY_INTRO]:
             # 引子或画廊入口，没有复杂的互动状态
             self.current_image_interaction_state = None

        else:
            print(f"警告：未知的互动类型 {interaction_type} for {image_id}")
            self.current_image_interaction_state = None


        # 解锁当前图片到画廊 (在加载时解锁，而不是完成时，为了能看到加载时的效果)
        self.unlocked_images[image_id] = True
        self._save_game() # 加载新图后保存进度
        # self.save_manager.save_game({
        #      "current_stage_id": self.current_stage_id,
        #      "current_image_id": self.current_image_id,
        #      "unlocked_images": self.unlocked_images
        #      # TODO: 保存当前互动模块的状态
        # })


        # 确保前进按钮初始隐藏
        self.ui_manager.set_element_visible("next_button", False)


    def handle_events(self, events):
        """处理Pygame事件列表"""
        for event in events:
            # 先处理通用事件 (退出，窗口大小调整)
            handled_by_general = self.input_handler.handle_event(event)

            if handled_by_general == "quit":
                self.should_quit = True # 设置退出标志
                return # 事件已处理
            elif handled_by_general and handled_by_general[0] == "window_resize": # 检查返回的是否是resize事件
                 new_width, new_height = handled_by_general[1]
                 # 重新设置屏幕模式以应用新的尺寸
                 self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                 self.image_renderer.resize(new_width, new_height) # 通知图片渲染器处理窗口大小改变
                 # 窗口大小改变后需要重新计算UI位置
                 self.ui_manager._calculate_ui_positions(self.image_renderer.image_display_rect)
                 # TODO: 通知其他需要知道屏幕尺寸变化的模块 (如 CleanErase 的 Render Texture)
                 if self.current_image_interaction_state and hasattr(self.current_image_interaction_state, 'resize'):
                      self.current_image_interaction_state.resize(new_width, new_height, self.image_renderer.image_display_rect) # 示例

                 return # 事件已处理


            # 将事件传递给当前状态或管理器处理
            if self.current_state == self.settings.STATE_GAME:
                # 先让UIManager处理UI点击
                handled_by_ui = self.ui_manager.handle_event(event, self.image_renderer.image_display_rect)
                if handled_by_ui:
                     return # 事件被UI处理

                # 如果事件未被UI处理，传递给当前的互动模块
                if self.current_image_interaction_state:
                    self.current_image_interaction_state.handle_event(event, self.image_renderer.image_display_rect) # 将图片显示区域传递过去进行坐标转换
            elif self.current_state == self.settings.STATE_GALLERY:
                # 先让UIManager处理画廊UI点击 (如退出按钮)
                # Gallery UI's relative_to might be 'screen', so pass screen rect instead of image_display_rect
                handled_by_ui = self.ui_manager.handle_event(event, self.screen.get_rect()) # 画廊UI可能不相对于图片区域，需要UIManager内部处理
                if handled_by_ui:
                     return # 事件被UI处理

                # 如果未被UI处理，传递给GalleryManager处理缩略图点击等
                self.gallery_manager.handle_event(event)

            # TODO: 其他状态的事件处理 (如菜单)


    def update(self):
        """更新游戏状态"""
        # 根据当前状态更新不同的部分
        screen_width, screen_height = self.screen.get_size() # 获取当前屏幕尺寸

        if self.current_state == self.settings.STATE_GAME:
            # 更新当前图片的互动状态
            if self.current_image_interaction_state:
                # 互动模块的update方法返回是否完成当前互动，以及可能触发的叙事文本ID
                is_completed, narrative_events = self.current_image_interaction_state.update(self.image_renderer.image_display_rect)

                # 处理互动完成和叙事触发
                if is_completed:
                     self._on_interaction_complete() # 互动完成后触发

                if narrative_events:
                     for event_type, text_ids in narrative_events.items():
                          if text_ids:
                                print(f"触发叙事事件: {event_type}, 文本ID: {text_ids}")
                                # narrative_manager.start_narrative 现在接收 AI声音回调
                                self.narrative_manager.start_narrative(text_ids, self._get_ai_sound_for_text_id) # 传递获取音效的函数

            # 更新叙事文本显示
            # NarrativeManager.update 返回是否有叙事正在播放，用于控制前进按钮
            narrative_is_active = self.narrative_manager.update()

            # 更新UI状态 (例如前进按钮的可见性) - 需要传递当前图片区域
            self.ui_manager.update(self.image_renderer.image_display_rect)


            # 对于引子或纯文本图片 (没有互动模块)，在叙事播放完毕后自动进入下一图
            # 需要判断当前图片ID是否是纯文本类型
            if self.current_image_id and self.image_configs.get(self.current_image_id) and self.image_configs[self.current_image_id].get("type") in [self.settings.INTERACTION_INTRO, self.settings.INTERACTION_GALLERY_INTRO] and not narrative_is_active:
                 self._go_to_next_image()


            # TODO: 更新其他游戏元素，如特效、背景动画等
            # self.image_renderer.update_effects() # 如果有随时间变化的特效


        elif self.current_state == self.settings.STATE_GALLERY:
            self.gallery_manager.update()
            self.ui_manager.update(self.screen.get_rect()) # 画廊UI更新，相对于屏幕区域


        # TODO: 其他状态的更新 (如菜单)

        # 保存进度 (可以定期保存，或在关键节点保存)
        # self._save_game() # 示例，实际应用中不宜频繁保存

    def draw(self):
        """绘制所有游戏元素"""
        # 清屏并绘制背景图 (背景图绘制放在 ImageRenderer 中)
        # self.screen.fill(self.settings.BLACK) # Clear screen before drawing background
        # Background is now drawn inside ImageRenderer.draw_image or ImageRenderer.draw_background

        current_image_id = self.current_image_id
        config = None
        if current_image_id:
             config = self.image_configs.get(current_image_id)


        # 根据当前状态绘制不同的内容
        if self.current_state == self.settings.STATE_GAME:
            # 绘制当前图片及其效果 (ImageRenderer 负责绘制图片本体和底层效果)
            if config and config.get("file"): # 只有有图片的阶段才绘制图片
                 self.image_renderer.draw_image(self.current_image_id) # ImageRenderer需要知道如何根据当前互动状态绘制图片
            else: # 没有图片的阶段 (如引子)，只绘制背景
                 self.image_renderer.draw_background(self.screen.get_size())


            # 绘制当前的互动元素 (叠加在图片上层，例如点击点的高亮，拼图块)
            if self.current_image_interaction_state:
                self.current_image_interaction_state.draw(self.screen, self.image_renderer.image_display_rect) # 将图片显示区域传递过去进行坐标转换

            # 绘制叙事文本 (叠加在最上层)
            # NarrativeManager 绘制文本框和文本，位置相对于图片区域计算
            # 即使没有图片，文本框也可能需要绘制在屏幕底部某个位置
            self.narrative_manager.draw(self.screen, self.image_renderer.image_display_rect) # 将图片显示区域传递给文本管理器，由其决定位置

            # 绘制UI元素 (叠加在最上层，前进按钮等)
            self.ui_manager.draw(self.screen)


        elif self.current_state == self.settings.STATE_GALLERY:
            self.gallery_manager.draw(self.screen) # 画廊管理器绘制所有画廊内容 (包括背景、缩略图、详情图、详情文本)
            self.ui_manager.draw(self.screen) # 绘制画廊UI (如退出按钮)

        # TODO: 其他状态的绘制 (如菜单)

        # 使最近绘制的屏幕可见 - 放在 main.py 的主循环中

    def _on_interaction_complete(self):
        """当前图片的主要互动完成后触发"""
        print(f"图片 {self.current_image_id} 互动完成。")
        config = self.image_configs.get(self.current_image_id)
        if not config:
            # 理论上不应该发生，因为只有加载了配置的图片才会触发互动完成
            return

        # 播放完成音效或触发完成动画
        # self.audio_manager.play_sfx(self.settings.SFX_COMPLETE) # 示例通用完成音效
        # if config.get("complete_feedback_effect_id"):
        #      self.image_renderer.trigger_effect(config["complete_feedback_effect_id"]) # 触发图片完成特效

        # 在互动完成后，通常会播放这张图的最终叙事文本 (如果还没播放的话)
        # 互动模块的 update 方法已经触发了相应的 narrative_events，这里确保所有完成后的文本都已播放
        # NarrativeManager 的 start_narrative 已经处理了防止重复触发同一个文本序列
        if "on_complete" in config.get("narrative_triggers", {}):
             self.narrative_manager.start_narrative(config["narrative_triggers"]["on_complete"], self._get_ai_sound_for_text_id) # 传递获取音效的函数

        # 互动完成后，等待所有文本播放完毕才能进入下一张图
        # 进入下一图的逻辑放在 NarrativeManager 的 update 方法中判断文本播放结束时触发，或者由一个“前进”按钮触发 (设计是前进按钮)

        # TODO: 保存完成状态
        # self._save_game() # 关键节点保存

    def _go_to_next_image(self):
        """加载下一张图片"""
        # ... _go_to_next_image 方法同之前
        config = self.image_configs.get(self.current_image_id)
        if not config:
            print(f"错误：无法找到当前图片配置 {self.current_image_id} 来确定下一张图片。")
            # TODO: 错误处理
            return

        next_image_id = config.get("next_image")
        next_stage_id = config.get("next_stage") # 如果配置了阶段跳转

        # 先保存当前进度，再跳转
        self._save_game()

        if next_stage_id == self.settings.STAGE_GALLERY:
             # 进入画廊阶段
             self._set_state(self.settings.STATE_GALLERY)
             # GalleryManager.enter_gallery 在 _set_state 中调用

        elif next_stage_id:
             # 跳转到新的阶段 (通常从新阶段的第一张图开始)
             self._load_stage(next_stage_id)
        elif next_image_id:
            # 加载同一阶段的下一张图片
            self._load_image(next_image_id)
        else:
            # 这是最后一张图片且没有下一阶段/图片
            print("游戏流程结束！没有更多图片或阶段。")
            # 游戏通关结局处理，例如显示一个最终画面或直接进入画廊
            # 根据设计，Stage 6.2 完成后进入画廊，所以理论上不会走到这里
            # 如果 Stage 6.2 配置有问题，走到这里，也默认进入画廊
            self._set_state(self.settings.STAGE_GALLERY)


    def _get_ai_sound_for_text_id(self, text_id):
         """根据文本ID获取对应的AI声音音效路径"""
         # 这个函数作为回调传递给 NarrativeManager
         # 确保 audio_manager 已经初始化
         if self.audio_manager:
             return self.settings.AI_SOUND_EFFECTS.get(text_id)
         return None


    def _save_game(self):
        """保存游戏进度"""
        save_data = {
            "current_stage_id": self.current_stage_id,
            "current_image_id": self.current_image_id,
            "unlocked_images": self.unlocked_images,
            "_entered_stages": self._entered_stages, # 保存已进入过的阶段
            # TODO: 添加当前图片互动模块的状态保存数据
            # "current_interaction_state_data": self.current_image_interaction_state.get_state() if self.current_image_interaction_state else None
        }
        self.save_manager.save_game(save_data)


    # TODO: 添加_load_game方法，在初始化时调用 SaveManager 加载
    # _load_or_start_game 已经包含了加载逻辑，但需要完善加载互动模块状态的部分


    def _quit_game(self):
        """退出游戏"""
        # TODO: 在退出前保存游戏进度
        self._save_game() # 在退出前保存当前进度
        self.should_quit = True # 设置退出标志，主循环会检查它并退出