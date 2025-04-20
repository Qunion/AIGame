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
from .puzzle_piece import PuzzlePiece # 导入 PuzzlePiece 类 for Stage 5.2
# from . import puzzle_piece # HybridInteraction 可能不需要直接导入 PuzzlePiece

# 导入类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # from audio_manager import AudioManager # AudioManager 在根目录
    pass # 已经在 class 定义中导入了类型提示


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

        # 从 settings 获取 AudioManager 实例
        self.audio_manager: AudioManager = self.settings.game_manager.audio_manager


        # 根据 hybrid_type 初始化并管理子互动模块和序列
        self.sub_interactions = {} # 字典 {step_id: interaction_instance}
        self.interaction_sequence = [] # 互动步骤的序列 [step_config_dict, ...]
        self.current_step_index = 0 # 当前正在进行的步骤索引

        self._is_completed = False
        self._triggered_narrative_events = set()

        # 调用方法设置序列和子模块
        # 确保在 _setup_sequence_and_interactions 中，子模块的初始化不会立即进行复杂的图像或屏幕操作
        self._setup_sequence_and_interactions()

        # 当前活动的互动步骤 ID 和实例
        self.current_active_step_id = None
        self.current_active_interaction = None

        # 初始设置活动互动 (如果序列不为空且第一个步骤模块创建成功)
        if self.interaction_sequence:
             first_step_config = self.interaction_sequence[0]
             first_step_id = first_step_config.get("id")
             if first_step_id and first_step_id in self.sub_interactions:
                 self._set_active_interaction(first_step_id)
             else:
                 print(f"错误：混合互动 {self.hybrid_type} 序列的第一个步骤无效或模块创建失败: {first_step_config}")
                 self._is_completed = True # 第一个步骤无效，标记混合互动完成


    def _setup_sequence_and_interactions(self):
        """根据 hybrid_type 和 config 设置互动序列和子模块"""
        print(f"设置混合互动类型: {self.hybrid_type} for image {self.config.get('file', self.config.get('description', 'current image'))}")
        # interaction_sequence 配置应该在 config 中定义，而不是根据 type 硬编码
        self.interaction_sequence = self.config.get("interaction_sequence", []) # 从 config 中获取互动序列定义


        if not self.interaction_sequence:
             print(f"错误：混合互动 {self.hybrid_type} 没有定义 'interaction_sequence'。")
             self._is_completed = True # 没有序列定义，直接标记完成
             return

        # 遍历序列配置，创建子模块实例
        for step_config in self.interaction_sequence:
            step_id = step_config.get("id")
            step_type = step_config.get("type")
            if not step_id or not step_type:
                 print(f"警告：混合互动 {self.hybrid_type} 序列中存在无效步骤配置: {step_config}")
                 continue

            # 根据步骤类型创建子模块实例
            try:
                if step_type == self.settings.INTERACTION_CLEAN_ERASE:
                    # CleanErase 需要 screen, image_renderer, config (这里传递step_config)
                    self.sub_interactions[step_id] = CleanErase(step_config, self.image_renderer, self.screen)
                elif step_type == self.settings.INTERACTION_CLICK_REVEAL:
                    # ClickReveal 需要 image_renderer, config (这里传递step_config)
                    self.sub_interactions[step_id] = ClickReveal(step_config, self.image_renderer)
                elif step_type == self.settings.INTERACTION_DRAG_PUZZLE:
                    # DragPuzzle 需要 image_renderer, config (这里传递step_config)
                    self.sub_interactions[step_id] = DragPuzzle(step_config, self.image_renderer)
                # TODO: 添加其他可能的互动类型

                else:
                    print(f"警告：混合互动 {self.hybrid_type} 序列中包含未知的步骤类型 {step_type}. Config: {step_config}")
                    self.sub_interactions[step_id] = None # 标记为无效模块

            except Exception as e:
                 print(f"错误：混合互动 {self.hybrid_type} 初始化步骤 {step_id} ({step_type}) 时出错: {e}")
                 self.sub_interactions[step_id] = None # 标记为无效模块


        # 初始设置活动互动 (在 __init__ 的最后调用)
        # if self.interaction_sequence:
        #      first_step_id = self.interaction_sequence[0]["id"]
        #      self._set_active_interaction(first_step_id) # 在 __init__ 最后调用


    def _set_active_interaction(self, step_id: str):
        """设置当前活动的互动步骤"""
        # 确保旧的互动停止循环音效等
        if self.current_active_interaction and hasattr(self.current_active_interaction, 'stop_looping_sfx'):
             self.current_active_interaction.stop_looping_sfx() # 示例停止循环音效

        self.current_active_step_id = step_id
        self.current_active_interaction = self.sub_interactions.get(step_id)
        if self.current_active_interaction:
             print(f"激活混合互动步骤: {step_id} ({type(self.current_active_interaction).__name__})")
             # TODO: 可能需要通知非活动的子模块禁用互动 (如果它们有 isActive 标志或类似机制)
             # TODO: 通知新激活的子模块进行一些初始化或状态重置 (例如，CleanErase 需要初始化蒙版，ClickReveal 需要准备点击点视觉)
             # 大部分初始化应该在子模块 __init__ 或第一次 update/draw 时根据是否存在图片和 display_rect 进行
             # 例如，CleanErase 的 _ensure_mask_surface 在 update/handle_event 中根据 display_rect 调用

        else:
             print(f"警告：尝试激活未知的或无效的混合互动步骤ID: {step_id}. 检查 interaction_sequence 和 sub_interactions。")
             # 如果当前步骤无效，尝试跳到下一个步骤
             if self.current_step_index < len(self.interaction_sequence):
                 print("尝试跳到混合序列的下一个步骤...")
                 self.current_step_index += 1
                 if self.current_step_index < len(self.interaction_sequence):
                      next_step_config = self.interaction_sequence[self.current_step_index]
                      next_step_id = next_step_config.get("id")
                      if next_step_id:
                           self._set_active_interaction(next_step_id) # 递归调用尝试激活下一个
                      else:
                           print(f"警告：混合序列索引 {self.current_step_index} 的步骤配置没有ID。")
                           self._is_completed = True # 序列中断，标记完成
                           self.current_active_interaction = None
                 else:
                      print("混合序列已无更多步骤。标记混合互动完成。")
                      self._is_completed = True
                      self.current_active_interaction = None # 没有活动模块


    def handle_event(self, event, image_display_rect: pygame.Rect):
        """将事件传递给当前活动的子互动模块"""
        if self._is_completed or not self.current_active_interaction:
            return

        # 将事件传递给当前活动的子模块
        self.current_active_interaction.handle_event(event, image_display_rect)

    def update(self, image_display_rect: pygame.Rect) -> tuple[bool, dict]:
        """更新混合互动状态"""
        # 检查整个混合互动是否已完成
        if self._is_completed:
            return True, {}

        # 更新当前活动的子互动模块 (如果存在)
        narrative_events = {}
        if self.current_active_interaction:
            # 子模块返回 (是否完成当前步骤, 触发的叙事事件字典)
            is_step_completed, narrative_events = self.current_active_interaction.update(image_display_rect)

            # 检查是否触发了当前混合互动本身的叙事事件 (例如，on_stage_enter)
            # on_stage_enter 由 GameManager 在加载阶段时触发
            # 可以在这里检查并返回其他混合互动特有的叙事触发
            hybrid_narrative_events = self._check_and_trigger_narrative_events()
            # 合并子模块和自身的叙事事件
            all_narrative_events = {**narrative_events, **hybrid_narrative_events}

            # TODO: Stage 5.2 特殊处理：在 ClickReveal 的 "on_all_clicked" 事件发生后，触发生成碎片和切换到 DragPuzzle
            # ClickReveal 的 update 方法会返回这个 narrative event
            # 我们在这里检查返回的事件是否包含 "on_all_clicked"
            if self.hybrid_type == self.settings.INTERACTION_HYBRID_CLICK_THEN_DRAG and "on_all_clicked" in narrative_events:
                 # 这个事件表示 ClickReveal 步骤已经完成所有点击
                 # 此时 ClickReveal 模块会返回 is_step_completed = True
                 # 但我们需要在这里拦截，先生成碎片，再激活 DragPuzzle
                 print("Stage 5.2 Click Reveal 完成，触发碎片生成和拖拽步骤。")
                 # TODO: 生成拼图碎片，并传递给 DragPuzzle 子模块
                 self._generate_puzzle_pieces_for_drag_step(image_display_rect) # 需要实现此方法，并传递 display_rect

                 # 标记 ClickReveal 步骤为完成 (以便进入下一个步骤)
                 # is_step_completed = True # 已经从子模块返回了

                 # 返回触发的叙事事件，但整个 Hybrid 互动未完成，步骤切换在下面处理
                 return False, all_narrative_events


            if is_step_completed:
                print(f"混合互动步骤 {self.current_active_step_id} 完成。")

                # 处理步骤完成后的逻辑，进入下一阶段或激活下一个步骤
                self.current_step_index += 1

                if self.current_step_index < len(self.interaction_sequence):
                    # 还有后续步骤，激活下一个
                    next_step_config = self.interaction_sequence[self.current_step_index]
                    next_step_id = next_step_config.get("id")
                    if next_step_id:
                         self._set_active_interaction(next_step_id)
                         return False, all_narrative_events # 返回False，整个Hybrid互动未完成
                    else:
                         print(f"警告：混合序列索引 {self.current_step_index} 的步骤配置没有ID。")
                         self._is_completed = True # 序列中断，标记完成
                         self.current_active_interaction = None # 没有活动模块
                         # 触发整个混合互动完成的叙事 (on_complete)
                         complete_narrative = self._check_and_trigger_narrative_events(check_complete=True)
                         return True, {**all_narrative_events, **complete_narrative}


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
        for step_config in self.interaction_sequence:
             step_id = step_config.get("id")
             interaction = self.sub_interactions.get(step_id)
             if interaction:
                 # TODO: 根据互动类型和当前步骤，决定是否绘制该子模块
                 # 例如，CleanErase 模块在擦除完成但点击未开始前，需要绘制蒙版最终状态
                 # DragPuzzle 模块在碎片生成后，即使点击步骤完成，碎片也需要绘制
                 # 简单示例：绘制所有子模块，由子模块内部根据其状态控制绘制内容
                  interaction.draw(screen, image_display_rect)


    # TODO: 实现 Stage 5.2 生成拼图碎片的方法
    def _generate_puzzle_pieces_for_drag_step(self, image_display_rect: pygame.Rect):
        """在 Stage 5.2 Click Reveal 完成后，生成碎片并传递给 DragPuzzle"""
        if self.hybrid_type != self.settings.INTERACTION_HYBRID_CLICK_THEN_DRAG:
            return

        drag_puzzle_interaction: DragPuzzle | None = self.sub_interactions.get("step2_drag_puzzle")
        click_nodes_interaction: ClickReveal | None = self.sub_interactions.get("step1_click_nodes")

        if drag_puzzle_interaction and click_nodes_interaction:
            # 获取点击节点和它们生成碎片的配置
            clickable_nodes_config = self.config.get("clickable_nodes", [])
            puzzle_config_data = self.config.get("puzzle_config", {})
            puzzle_pieces_config = puzzle_config_data.get("pieces", [])

            generated_pieces = []
            for node_config in clickable_nodes_config:
                 # 检查节点是否已激活，并且配置了生成碎片
                 if click_nodes_interaction.activated_points.get(node_config["id"]) and "generates_piece_id" in node_config:
                      piece_id_to_generate = node_config["generates_piece_id"]
                      # 在 pieces_config 中找到这个碎片ID对应的配置
                      piece_cfg = next((p for p in puzzle_pieces_config if p.get("id") == piece_id_to_generate), None)

                      if piece_cfg:
                          piece_id = piece_cfg["id"]
                          correct_pos_local = tuple(piece_cfg.get("correct_pos_local", (0,0)))
                          # TODO: **创建实际的碎片 Surface** (可能需要从某个资源加载或生成)
                          # 这里是关键，碎片的视觉是什么样的？是抽象符号还是图片一部分？
                          # 假设碎片是简单的颜色块或预加载的小纹理
                          # 例如，如果 piece_cfg 有 "texture_file": "fragment_A.png"
                          piece_surface = None
                          if "texture_file" in piece_cfg:
                               texture_path = os.path.join(self.settings.IMAGE_DIR, piece_cfg["texture_file"]) # 假设碎片纹理在images目录
                               try:
                                    piece_surface = pygame.image.load(texture_path).convert_alpha()
                                    # TODO: 缩放碎片纹理以适应其在屏幕上的预期大小 (复杂)
                               except pygame.error as e:
                                    print(f"警告：Stage 5.2 无法加载碎片纹理 {texture_path}: {e}")
                                    piece_surface = pygame.Surface((50, 50)).convert_alpha() # 默认占位
                                    piece_surface.fill((200, 100, 100)) # 示例颜色
                          elif "source_rect_original" in piece_cfg:
                               # 如果碎片是原图的一部分
                               if self.image_renderer.current_image:
                                   original_source_rect_config = piece_cfg["source_rect_original"]
                                   original_source_rect = pygame.Rect(*original_source_rect_config)
                                   # 将原始矩形转换为显示区域上的矩形，并从当前显示图片中切割
                                   display_source_rect = self.image_renderer.get_screen_rect_from_original(original_source_rect) # ImageRenderer 需要实现此方法
                                   # 确保矩形在图片 Surface 范围内
                                   source_surface = self.image_renderer.current_image
                                   if display_source_rect.colliderect(source_surface.get_rect()):
                                        piece_surface = source_surface.subsurface(display_source_rect)
                                   else:
                                        print(f"警告：Stage 5.2 碎片 {piece_id} 的原始源矩形在显示区域外或无效。")
                                        piece_surface = pygame.Surface((50, 50)).convert_alpha() # 默认占位
                                        piece_surface.fill((100, 200, 100)) # 示例颜色

                               else:
                                    print("警告：Stage 5.2 图片未加载，无法从原图切割碎片。")
                                    piece_surface = pygame.Surface((50, 50)).convert_alpha() # 默认占位
                                    piece_surface.fill((100, 100, 200)) # 示例颜色


                          if piece_surface:
                               # 创建 PuzzlePiece 实例
                               generated_pieces.append(PuzzlePiece(piece_id, piece_surface, correct_pos_local, piece_cfg.get("grid_pos")))


            # 将生成的碎片列表传递给 DragPuzzle 子模块并启用它
            if generated_pieces:
                drag_puzzle_interaction.set_pieces(generated_pieces) # DragPuzzle 需要添加 set_pieces 方法
                # 计算碎片的初始随机散开位置 (在图片显示区域范围内)
                scatter_width = image_display_rect.width * drag_puzzle_interaction.initial_scatter_range # 从DragPuzzle获取散开范围
                scatter_height = image_display_rect.height * drag_puzzle_interaction.initial_scatter_range

                initial_positions = [] # 存储初始随机位置
                for piece in generated_pieces:
                    # 计算碎片的正确屏幕位置 (相对于屏幕左上角)
                    correct_screen_pos = (
                        image_display_rect.left + piece.correct_pos_local[0],
                        image_display_rect.top + piece.correct_pos_local[1]
                    )
                    # 在正确位置周围随机偏移
                    initial_pos_screen = (
                        correct_screen_pos[0] + random.uniform(-scatter_width, scatter_width),
                        correct_screen_pos[1] + random.uniform(-scatter_height, scatter_height)
                    )
                    initial_positions.append(initial_pos_screen)

                # 打乱初始位置，然后按碎片在 generated_pieces 列表中的顺序设置
                random.shuffle(initial_positions)
                for i, piece in enumerate(generated_pieces):
                     piece.set_position(initial_positions[i])
                     piece.set_locked(False) # 初始为可拖拽状态


            else:
                print("警告：Stage 5.2 Click Reveal 完成，但没有生成任何拼图碎片。检查配置。")


        else:
            print("警告：Stage 5.2 Click Reveal 完成，但找不到 DragPuzzle 子模块。检查 HybridInteraction 设置。")


    # ... _check_and_trigger_narrative_events 方法同之前

    # 在窗口resize时，需要通知所有子模块重新计算位置和内部Surface尺寸
    def resize(self, new_width, new_height, image_display_rect: pygame.Rect):
         """处理窗口大小改变事件，通知子互动模块"""
         for step_id, interaction in self.sub_interactions.items():
              if interaction and hasattr(interaction, 'resize'): # 检查子模块是否存在且有 resize 方法
                   interaction.resize(new_width, new_height, image_display_rect)


    # TODO: 添加保存和加载模块状态的方法
    # def get_state(self):
    #     # 需要保存当前步骤索引，以及每个子互动模块的状态
    #     sub_states = {}
    #     for step_config in self.interaction_sequence: # 遍历序列配置来获取 step_id
    #          step_id = step_config.get("id")
    #          if step_id:
    #              interaction = self.sub_interactions.get(step_id)
    #              if interaction and hasattr(interaction, 'get_state'): # 检查子模块是否存在且支持状态保存
    #                  sub_states[step_id] = interaction.get_state()
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
    #     for step_config in self.interaction_sequence: # 遍历序列配置来获取 step_id
    #          step_id = step_config.get("id")
    #          if step_id:
    #              interaction = self.sub_interactions.get(step_id)
    #              if interaction and step_id in sub_states and hasattr(interaction, 'load_state'):
    #                   # 加载子模块状态，需要传递 image_display_rect给可能需要它的模块 (如 CleanErase, DragPuzzle)
    #                   interaction.load_state(sub_states[step_id], image_display_rect)
    #     # 激活正确的步骤
    #     if self.current_step_index < len(self.interaction_sequence):
    #          next_step_config = self.interaction_sequence[self.current_step_index]
    #          next_step_id = next_step_config.get("id")
    #          if next_step_id:
    #               self._set_active_interaction(next_step_id)
    #     else:
    #          self._is_completed = True # 所有步骤都已完成
    #          self.current_active_interaction = None # 不再有活动模块