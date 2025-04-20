# interaction_modules/hybrid_interaction.py
import pygame
# 导入自定义模块 - 它们现在位于根目录
from settings import Settings
from image_renderer import ImageRenderer
from audio_manager import AudioManager # 需要AudioManager来播放音效
# 导入基础互动模块 - 它们在同一个子目录
from .click_reveal import ClickReveal
from .clean_erase import CleanErase
from .drag_puzzle import DragPuzzle
# from . import puzzle_piece # HybridInteraction 可能不需要直接导入 PuzzlePiece

class HybridInteraction:
    """
    处理混合玩法逻辑。
    根据配置序列协调多种互动。
    """

    def __init__(self, hybrid_type: str, config: dict, image_renderer: ImageRenderer, screen: pygame.Surface):
        """
        初始化混合互动模块。
        hybrid_type: 混合互动类型 (例如, "hybrid_erase_then_click")
        config: 来自image_config.json的当前图片配置。
        image_renderer: 用于图片显示和效果控制的ImageRenderer实例。
        screen: 主屏幕Surface。
        """
        self.hybrid_type = hybrid_type
        self.config = config
        self.image_renderer = image_renderer
        self.settings: Settings = image_renderer.settings
        self.screen = screen
        self.audio_manager: AudioManager = self.settings.game_manager.audio_manager

        # 根据 hybrid_type 初始化并管理子互动模块和序列
        self.sub_interactions = {} # 字典 {step_id: interaction_instance}
        self.interaction_sequence = [] # 互动步骤的序列 [(step_id, interaction_type), ...]
        self.current_step_index = 0 # 当前正在进行的步骤索引

        self._is_completed = False
        self._triggered_narrative_events = set()

        self._setup_sequence_and_interactions() # 初始化序列和子模块
        self.current_active_step_id = None # 当前活动的步骤ID
        self.current_active_interaction = None # 当前活动的子互动模块实例

        # 初始设置活动互动
        if self.interaction_sequence:
            first_step_id, _ = self.interaction_sequence[0]
            self._set_active_interaction(first_step_id)


    def _setup_sequence_and_interactions(self):
        """根据 hybrid_type 和 config 设置互动序列和子模块"""
        print(f"设置混合互动类型: {self.hybrid_type} for image {self.config.get('file', self.config.get('description'))}")
        # sequence_config = self.config.get("interaction_sequence", []) # 在image_config中为混合玩法定义序列 - 使用硬编码的序列逻辑更清晰

        # 示例 Stage 3.2: hybrid_erase_then_click
        if self.hybrid_type == self.settings.INTERACTION_HYBRID_ERASE_THEN_CLICK:
             # Sequence: Erase -> Click
             self.interaction_sequence = [("step1_erase", self.settings.INTERACTION_CLEAN_ERASE), ("step2_click", self.settings.INTERACTION_CLICK_REVEAL)]

             # Step 1: Clean Erase (剥离蒙版)
             erase_config = {
                 "mask_texture": self.config.get("mask_texture"),
                 "unerasable_areas": self.config.get("unerasable_areas", []),
                 "erase_threshold": self.config.get("erase_threshold", 0.95),
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step1_erase"] = CleanErase(erase_config, self.image_renderer, self.screen)

             # Step 2: Click Reveal (点击显现点) - 这个点击点在擦除后才“出现”
             click_config = {
                 "click_points": self.config.get("post_erase_click_points", []), # 点击点是擦除后才出现的
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step2_click"] = ClickReveal(click_config, self.image_renderer)


        # 示例 Stage 5.1: hybrid_erase_then_click (同 Stage 3.2，但叙事和画面不同)
        # 示例 Stage 5.2: hybrid_click_then_drag
        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_CLICK_THEN_DRAG:
             # Sequence: Click Nodes -> Drag Puzzle
             self.interaction_sequence = [("step1_click_nodes", self.settings.INTERACTION_CLICK_REVEAL), ("step2_drag_puzzle", self.settings.INTERACTION_DRAG_PUZZLE)]

             # Step 1: Click (点击节点生成碎片)
             click_config = {
                 "click_points": self.config.get("clickable_nodes", []), # 可点击的节点是点击点
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step1_click_nodes"] = ClickReveal(click_config, self.image_renderer) # 需要 ClickReveal 支持生成碎片或触发 HybridInteraction 来生成

             # Step 2: Drag Puzzle (拖拽拼合碎片)
             puzzle_config = {
                 "pieces": self.config.get("puzzle_pieces", []), # 需要知道碎片定义和目标区域
                 "drop_target": self.config.get("puzzle_drop_target"),
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step2_drag_puzzle"] = DragPuzzle(puzzle_config, self.image_renderer) # TODO: DragPuzzle 初始化需要调整以接受这种配置


        # 示例 Stage 5.3: hybrid_final_activation
        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_FINAL_ACTIVATION:
             # Sequence: Click Final Point
             self.interaction_sequence = [("step1_activate", self.settings.INTERACTION_CLICK_REVEAL)]
             click_config = {
                 "click_points": [self.config.get("final_activation_point")].copy() if self.config.get("final_activation_point") else [],
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step1_activate"] = ClickReveal(click_config, self.image_renderer)


        # 示例 Stage 6.1: hybrid_resonance_perceive
        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_RESONANCE_PERCEIVE:
             # Sequence: Click Resonance Points
             self.interaction_sequence = [("step1_perceive", self.settings.INTERACTION_CLICK_REVEAL)]
             click_config = {
                 "click_points": self.config.get("resonance_points", []),
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step1_perceive"] = ClickReveal(click_config, self.image_renderer) # 可以复用ClickReveal


        # 示例 Stage 6.2: hybrid_final_connection
        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_FINAL_CONNECTION:
             # Sequence: Click Connection Point
             self.interaction_sequence = [("step1_connect", self.settings.INTERACTION_CLICK_REVEAL)]
             click_config = {
                 "click_points": [self.config.get("final_connection_point")].copy() if self.config.get("final_connection_point") else [],
                 "narrative_triggers": self.config.get("narrative_triggers", {}) # 传递叙事触发给子模块
             }
             self.sub_interactions["step1_connect"] = ClickReveal(click_config, self.image_renderer) # 复用ClickReveal

        else:
             print(f"错误：未知的混合互动类型 {self.hybrid_type}")
             self.interaction_sequence = [] # 清空序列
             self._is_completed = True # 未知类型直接标记完成


    def _set_active_interaction(self, step_id):
        """设置当前活动的互动步骤"""
        self.current_active_step_id = step_id
        self.current_active_interaction = self.sub_interactions.get(step_id)
        print(f"激活混合互动步骤: {step_id}")
        # TODO: 可能需要通知其他子模块禁用互动，只启用当前活动的 (如果它们在draw/handle_event中有独立逻辑)

        # TODO: Stage 5.2 点击后生成碎片并启用拖拽，需要 HybridInteraction 协调
        # 在 Stage 5.2 ClickReveal 的 update 中，当所有节点点击完成时，除了触发 narrtive event，还需要通知 HybridInteraction
        # HybridInteraction 收到通知后，需要：1. 禁用 ClickReveal 子模块； 2. 生成拼图碎片； 3. 启用 DragPuzzle 子模块。
        # 这需要 HybridInteraction 监听子模块的特定事件，或者子模块返回更详细的状态

        # 示例：监听 ClickReveal 的 "on_all_clicked" 事件来触发下一步
        if isinstance(self.current_active_interaction, ClickReveal):
             pass # ClickReveal 的完成状态在 update 中检查

        # 示例：监听 CleanErase 的 "on_complete_erase" 事件来触发下一步
        if isinstance(self.current_active_interaction, CleanErase):
             pass # CleanErase 的完成状态在 update 中检查


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """将事件传递给当前活动的子互动模块"""
        if self._is_completed or not self.current_active_interaction:
            return

        # 将事件传递给当前活动的子模块
        self.current_active_interaction.handle_event(event, image_display_rect)

    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """更新混合互动状态"""
        if self._is_completed or not self.current_active_interaction:
            return True, {} # 已完成或无活动互动

        # 更新当前活动的子互动模块
        # 子模块返回 (是否完成当前步骤, 触发的叙事事件字典)
        is_step_completed, narrative_events = self.current_active_interaction.update(image_display_rect)

        # 检查是否触发了当前混合互动本身的叙事事件 (例如，on_stage_enter)
        hybrid_narrative_events = self._check_and_trigger_narrative_events()
        # 合并子模块和自身的叙事事件
        all_narrative_events = {**narrative_events, **hybrid_narrative_events}


        if is_step_completed:
            print(f"混合互动步骤 {self.current_active_step_id} 完成。")

            # 处理步骤完成后的逻辑，根据 hybrid_type 执行特定操作或进入下一阶段
            current_step_id, current_interaction_type = self.interaction_sequence[self.current_step_index]

            if self.hybrid_type == self.settings.INTERACTION_HYBRID_ERASE_THEN_CLICK and current_step_id == "step1_erase":
                 # Stage 3.2 & 5.1: 擦除完成 -> 显现点击点，激活点击步骤
                 # 显现点击点已经在 CleanErase 模块的 draw 方法中根据状态实现
                 self.current_step_index += 1
                 next_step_id, _ = self.interaction_sequence[self.current_step_index]
                 self._set_active_interaction(next_step_id)
                 # CleanErase 模块的 on_complete_erase 事件在这里返回，GameManager会处理其叙事
                 # 返回False，因为整个Hybrid互动未完成
                 return False, all_narrative_events

            elif self.hybrid_type == self.settings.INTERACTION_HYBRID_CLICK_THEN_DRAG and current_step_id == "step1_click_nodes":
                 # Stage 5.2: 点击节点完成 -> 生成碎片，激活拖拽步骤
                 # TODO: 在这里生成拼图碎片 (需要访问 ImageRenderer 和 DragPuzzle 子模块)
                 # self._generate_puzzle_pieces_for_drag_step() # 需要实现此方法
                 self.current_step_index += 1
                 next_step_id, _ = self.interaction_sequence[self.current_step_index]
                 self._set_active_interaction(next_step_id)
                 # 返回False，因为整个Hybrid互动未完成
                 return False, all_narrative_events


            else:
                # 其他类型的步骤完成，或者这是序列的最后一个步骤
                self.current_step_index += 1 # 尝试进入下一个索引

                if self.current_step_index < len(self.interaction_sequence):
                    # 还有后续步骤，激活下一个
                    next_step_id, _ = self.interaction_sequence[self.current_step_index]
                    self._set_active_interaction(next_step_id)
                    return False, all_narrative_events # 返回False，整个Hybrid互动未完成
                else:
                    # 所有步骤都完成了
                    self._is_completed = True
                    print(f"混合互动 {self.hybrid_type} 完成。")
                    # 触发整个混合互动完成的叙事 (on_complete)
                    complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
                    return True, {**all_narrative_events, **complete_narrative} # 返回完成状态和所有触发的叙事事件


        return False, all_narrative_events # 未完成，返回子模块和自身触发的叙事

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制混合互动模块的视觉元素"""
        # 绘制所有子互动模块的视觉元素 (有些即使不活跃也可能需要绘制)
        for step_id, interaction in self.sub_interactions.items():
            # TODO: 根据互动类型和当前步骤，决定是否绘制该子模块
            # 例如，CleanErase 模块在擦除完成但点击未开始前，需要绘制蒙版最终状态
            # DragPuzzle 模块在碎片生成后，即使点击步骤完成，碎片也需要绘制
            # 简单示例：绘制当前活动的，和已完成且需要持续显示的子模块
            # if interaction is self.current_active_interaction or (interaction._is_completed and self._should_draw_after_complete(step_id)): # _should_draw_after_complete 需要实现
            if interaction: # 临时：绘制所有已初始化的子模块，由子模块内部控制可见性
                 interaction.draw(screen, image_display_rect)


    # TODO: 实现判断步骤完成后是否需要持续绘制的方法 (_should_draw_after_complete)
    # 例如，拖拽拼图完成后的碎片需要持续绘制，但 ClickReveal 完成后可能不需要绘制点击点


    def _check_and_trigger_narrative_events(self, check_complete=False) -> dict:
        """检查当前混合互动是否触发了自身的叙事事件"""
        # 混合互动可能只有 on_stage_enter 和 on_complete 两个叙事触发
        # 具体步骤的叙事触发由子模块处理
        triggered = {}
        config_triggers = self.config.get("narrative_triggers", {})

        # 检查 on_stage_enter (在 GameManager 中触发，这里只作为参考)

        # 检查 on_complete (整个混合互动完成)
        if check_complete and "on_complete" in config_triggers:
             event_id = "on_complete"
             if event_id not in self._triggered_narrative_events:
                 triggered[event_id] = config_triggers[event_id]
                 self._triggered_narrative_events.add(event_id)

        # TODO: 可以添加其他混合互动特有的叙事触发条件

        return triggered

    # 在窗口resize时，需要通知所有子模块重新计算位置和内部Surface尺寸
    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
         """处理窗口大小改变事件，通知子互动模块"""
         for interaction in self.sub_interactions.values():
              if hasattr(interaction, 'resize'):
                   interaction.resize(new_width, new_height, image_display_rect)


    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     # 需要保存当前步骤索引，以及每个子互动模块的状态
    #     sub_states = {}
    #     for step_id, interaction in self.sub_interactions.items():
    #          if hasattr(interaction, 'get_state'): # 检查子模块是否支持状态保存
    #              sub_states[step_id] = interaction.get_state()
    #     return {
    #          "hybrid_type": self.hybrid_type,
    #          "current_step_index": self.current_step_index,
    #          "sub_interactions_state": sub_states,
    #          "triggered_narrative_events": list(self._triggered_narrative_events)
    #     }

    # def load_state(self, state_data, image_display_rect: pygame.Rect):
    #     self.hybrid_type = state_data["hybrid_type"]
    #     self.current_step_index = state_data["current_step_index"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._setup_sequence_and_interactions() # 重新设置序列和子模块 (这会重新创建子模块)
    #     # 加载子模块的状态
    #     sub_states = state_data.get("sub_interactions_state", {})
    #     for step_id, interaction in self.sub_interactions.items():
    #          if step_id in sub_states and hasattr(interaction, 'load_state'):
    #               # 加载子模块状态，需要传递 image_display_rect给可能需要它的模块 (如 CleanErase)
    #               interaction.load_state(sub_states[step_id], image_display_rect)
    #     # 激活正确的步骤
    #     if self.current_step_index < len(self.interaction_sequence):
    #          self._set_active_interaction(self.interaction_sequence[self.current_step_index][0])
    #     else:
    #          self._is_completed = True # 所有步骤都已完成
    #          self.current_active_interaction = None # 不再有活动模块