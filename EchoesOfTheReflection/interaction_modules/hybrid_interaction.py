# src/interaction_modules/hybrid_interaction.py
import pygame
from settings import Settings
from image_renderer import ImageRenderer
# 导入基础互动模块
from interaction_modules.click_reveal import ClickReveal
from interaction_modules.clean_erase import CleanErase
from interaction_modules.drag_puzzle import DragPuzzle

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
        self.settings = image_renderer.settings
        self.screen = screen

        # 根据 hybrid_type 初始化并管理子互动模块
        self.sub_interactions = {} # {step_id: interaction_instance}
        self.interaction_sequence = [] # 互动步骤的序列 [(step_id, interaction_type), ...]
        self.current_step_index = 0

        self._is_completed = False
        self._triggered_narrative_events = set()

        self._setup_sequence_and_interactions()

    def _setup_sequence_and_interactions(self):
        """根据 hybrid_type 和 config 设置互动序列和子模块"""
        print(f"设置混合互动类型: {self.hybrid_type}")
        sequence_config = self.config.get("interaction_sequence", []) # 在image_config中为混合玩法定义序列

        if self.hybrid_type == self.settings.INTERACTION_HYBRID_ERASE_THEN_CLICK:
             # 示例 Stage 3.2 & Stage 5.1
             # Step 1: Clean Erase (剥离蒙版)
             erase_config = {"mask_texture": self.config.get("mask_texture"), "unerasable_areas": self.config.get("unerasable_areas", []), "erase_threshold": self.config.get("erase_threshold", 0.95)}
             self.sub_interactions["step1_erase"] = CleanErase(erase_config, self.image_renderer, self.screen)
             self.interaction_sequence.append(("step1_erase", self.settings.INTERACTION_CLEAN_ERASE))

             # Step 2: Click Reveal (点击显现点)
             click_config = {"click_points": self.config.get("post_erase_click_points", [])} # 点击点是擦除后才出现的
             self.sub_interactions["step2_click"] = ClickReveal(click_config, self.image_renderer)
             self.interaction_sequence.append(("step2_click", self.settings.INTERACTION_CLICK_REVEAL))

             # 初始只启用第一个互动
             self._set_active_interaction("step1_erase")


        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_CLICK_THEN_DRAG:
             # 示例 Stage 5.2
             # Step 1: Click (点击节点生成碎片)
             click_config = {"click_points": self.config.get("clickable_nodes", [])} # 可点击的节点是点击点
             self.sub_interactions["step1_click_nodes"] = ClickReveal(click_config, self.image_renderer)
             self.interaction_sequence.append(("step1_click_nodes", self.settings.INTERACTION_CLICK_REVEAL))

             # Step 2: Drag Puzzle (拖拽拼合碎片)
             # 拼图配置需要知道碎片定义和目标区域
             puzzle_config = {"pieces": self.config.get("puzzle_pieces", []), "drop_target": self.config.get("puzzle_drop_target")}
             self.sub_interactions["step2_drag_puzzle"] = DragPuzzle(puzzle_config, self.image_renderer) # TODO: DragPuzzle 初始化需要调整以接受这种配置
             self.interaction_sequence.append(("step2_drag_puzzle", self.settings.INTERACTION_DRAG_PUZZLE))

             self._set_active_interaction("step1_click_nodes")

        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_FINAL_ACTIVATION:
             # 示例 Stage 5.3
             # Step 1: Click (点击最终汇聚点)
             click_config = {"click_points": [self.config.get("final_activation_point")].copy() if self.config.get("final_activation_point") else []}
             self.sub_interactions["step1_activate"] = ClickReveal(click_config, self.image_renderer)
             self.interaction_sequence.append(("step1_activate", self.settings.INTERACTION_CLICK_REVEAL))

             self._set_active_interaction("step1_activate")

        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_RESONANCE_PERCEIVE:
             # 示例 Stage 6.1
             # Step 1: Click (点击共振感知点)
             click_config = {"click_points": self.config.get("resonance_points", [])}
             self.sub_interactions["step1_perceive"] = ClickReveal(click_config, self.image_renderer) # 可以复用ClickReveal，但其update/draw/handle_event需要处理Stage 6的特殊逻辑
             self.interaction_sequence.append(("step1_perceive", self.settings.INTERACTION_CLICK_REVEAL))

             self._set_active_interaction("step1_perceive")

        elif self.hybrid_type == self.settings.INTERACTION_HYBRID_FINAL_CONNECTION:
             # 示例 Stage 6.2
             # Step 1: Click (点击连接印记)
             click_config = {"click_points": [self.config.get("final_connection_point")].copy() if self.config.get("final_connection_point") else []}
             self.sub_interactions["step1_connect"] = ClickReveal(click_config, self.image_renderer) # 复用ClickReveal
             self.interaction_sequence.append(("step1_connect", self.settings.INTERACTION_CLICK_REVEAL))

             self._set_active_interaction("step1_connect")

        else:
             print(f"错误：未知的混合互动类型 {self.hybrid_type}")
             self._is_completed = True # 未知类型直接标记完成

        # TODO: 可以根据 config 定义更复杂的序列，例如并行步骤，或者基于条件的跳转

    def _set_active_interaction(self, step_id):
        """设置当前活动的互动步骤"""
        self.current_active_step_id = step_id
        self.current_active_interaction = self.sub_interactions.get(step_id)
        print(f"激活混合互动步骤: {step_id}")
        # TODO: 可能需要通知其他子模块禁用互动，只启用当前活动的

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
        is_step_completed, narrative_events = self.current_active_interaction.update(image_display_rect)

        # 检查是否触发了当前混合互动本身的叙事事件 (例如，on_stage_enter)
        hybrid_narrative_events = self._check_and_trigger_narrative_events()


        if is_step_completed:
            print(f"混合互动步骤 {self.current_active_step_id} 完成。")
            self.current_step_index += 1

            if self.current_step_index < len(self.interaction_sequence):
                # 激活下一个步骤
                next_step_id, next_interaction_type = self.interaction_sequence[self.current_step_index]
                self._set_active_interaction(next_step_id)
                # TODO: 可能需要在这里触发新步骤开始的叙事或视觉提示
                # TODO: 通知新激活的子模块进行初始化或状态重置

                # 返回当前步骤完成触发的叙事，不标记整个混合互动完成
                return False, {**narrative_events, **hybrid_narrative_events}
            else:
                # 所有步骤都完成了
                self._is_completed = True
                print(f"混合互动 {self.hybrid_type} 完成。")
                # 触发整个混合互动完成的叙事 (on_complete)
                complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
                return True, {**narrative_events, **hybrid_narrative_events, **complete_narrative} # 返回完成状态和所有触发的叙事事件

        return False, {**narrative_events, **hybrid_narrative_events} # 未完成，返回子模块触发的叙事和自身触发的叙事

    def draw(self, screen: pygame.Surface, image_display_rect: pygame.Rect):
        """绘制混合互动模块的视觉元素"""
        # 绘制当前活动的子互动模块的视觉元素
        if self.current_active_interaction:
            self.current_active_interaction.draw(screen, image_display_rect)

        # TODO: 绘制一些表示序列进度的UI元素 (可选)
        # TODO: 绘制非活动但可见的子模块元素 (例如，Stage 5.2 碎片生成后，即使点击步骤完成，碎片还需要绘制)

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
    # def load_state(self, state_data):
    #     self.hybrid_type = state_data["hybrid_type"]
    #     self.current_step_index = state_data["current_step_index"]
    #     self._triggered_narrative_events = set(state_data["triggered_narrative_events"])
    #     self._setup_sequence_and_interactions() # 重新设置序列和子模块
    #     # 加载子模块的状态
    #     sub_states = state_data["sub_interactions_state"]
    #     for step_id, interaction in self.sub_interactions.items():
    #          if step_id in sub_states and hasattr(interaction, 'load_state'):
    #               interaction.load_state(sub_states[step_id])
    #     # 激活正确的步骤
    #     if self.current_step_index < len(self.interaction_sequence):
    #          self._set_active_interaction(self.interaction_sequence[self.current_step_index][0])
    #     else:
    #          self._is_completed = True # 所有步骤都已完成
    #          self.current_active_interaction = None # 不再有活动模块