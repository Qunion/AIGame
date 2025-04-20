# image_manager.py
# 负责图片的加载、处理、碎片生成、管理图片状态和提供碎片/完整图资源

import pygame
import settings
import os
import time
import math # 用于计算加载进度百分比
from piece import Piece # Piece 类可能在 ImageManager 中创建实例，所以需要导入

# 尝试导入 Pillow 库，用于更灵活的图像处理
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    print("警告: Pillow库未安装。部分图像处理功能可能受限。建议安装: pip install Pillow")
    PIL_AVAILABLE = False


class ImageManager:
    def __init__(self, game):
        """
        初始化图像管理器。扫描图片文件，执行初始加载。

        Args:
            game (Game): Game实例，用于在加载时显示加载界面 (可选)。
        """
        self.game = game # 持有Game实例的引用

        # 存储加载和处理后的原始图片表面 {id: pygame.Surface} (用于图库大图)
        self.processed_full_images = {}
        # 存储生成的碎片表面 {id: { (row, col): pygame.Surface }}
        # 只有当图片的全部碎片成功加载或生成时，才会在这个字典中创建 entry
        self.pieces_surfaces = {}
        # 存储已点亮图片的完成时间 {id: timestamp} # 用于图库排序
        self.completed_times = {}

        # 存储每张图片的状态 {id: 'unentered' / 'unlit' / 'lit'}
        self.image_status = {} # {image_id: status} - 必须在扫描前初始化

        # 存储所有原始图片文件的信息 {id: filepath}
        self.all_image_files = {} # {image_id: full_filepath}
        self._scan_image_files() # 扫描图片文件，获取所有图片ID和路径 (现在 self.image_status 已经存在)

        # 跟踪图片加载进度
        # _loaded_image_count 记录已**成功生成全部碎片**的图片数量 (即在 self.pieces_surfaces 中有完整 entry 的图片数量)
        self._loaded_image_count = 0 # 这个计数在 _update_loaded_count 中维护
        self._total_image_count = len(self.all_image_files) # 总共扫描到的图片数量

        # 跟踪下一批需要从哪张图片取碎片
        self.next_image_to_consume_id = -1 # 初始化时确定
        self.pieces_consumed_from_current_image = 0 # 初始化时确定

        # 执行初始加载
        self._initial_load_images(settings.INITIAL_LOAD_IMAGE_COUNT)

        # 初始化碎片消耗机制，基于**所有**扫描到的图片ID列表 (确定从哪张图开始消耗，以及初始消耗了多少)
        self._initialize_consumption()

        print(f"ImageManager 初始化完成。总图片文件数: {self._total_image_count}，初始加载成功图片数: {self._loaded_image_count}") # 调试信息


    def _scan_image_files(self):
        """扫描 assets 目录，找到所有符合 image_N.png 命名规则的图片文件路径和ID"""
        image_files = [f for f in os.listdir(settings.ASSETS_DIR) if f.startswith("image_") and f.endswith(".png")]
        # 使用 os.path.splitext 分离文件名和扩展名，然后处理文件名部分来获取ID
        image_files.sort(key=lambda f: int(os.path.splitext(f)[0].replace("image_", ""))) # 确保按图片ID排序

        for filename in image_files:
            try:
                # 从文件名中提取图片ID
                image_id = int(os.path.splitext(filename)[0].replace("image_", ""))
                full_path = os.path.join(settings.ASSETS_DIR, filename)
                self.all_image_files[image_id] = full_path
                # 所有扫描到的图片初始状态都是未入场
                # 只有当碎片被加载或生成后，状态才可能变为 'unlit' 或保持 'unentered' 如果不用于初始填充
                if image_id not in self.image_status: # 避免重复扫描时覆盖状态
                    self.image_status[image_id] = 'unentered'
            except ValueError:
                print(f"警告: 文件名格式不正确，无法提取图片ID: {filename}")
            except Exception as e:
                print(f"警告: 扫描文件 {filename} 时发生错误: {e}")

        self._total_image_count = len(self.all_image_files) # 更新总图片数量


    def _initial_load_images(self, count):
        """初始化时加载和处理前 'count' 张图片，这些图片会尝试生成/加载碎片 surface"""
        # 获取所有图片ID，按顺序
        all_image_ids = sorted(self.all_image_files.keys())
        # 确定要进行初始加载处理的图片ID列表，不超过总数
        images_to_process_ids = all_image_ids[:min(count, len(all_image_ids))]

        print(f"正在进行初始加载处理前 {len(images_to_process_ids)} 张图片...") # 调试信息

        for image_id in images_to_process_ids:
             # 加载并处理单张图片，包括尝试从缓存加载, _load_and_process_single_image 会返回处理是否成功
             self._load_and_process_single_image(image_id)

        # _loaded_image_count 会在 _load_and_process_single_image 内部根据处理成功情况更新。
        # 在整个初始加载批次处理完后，再次更新 _loaded_image_count 可以确保计数准确
        self._update_loaded_count()


        # 根据初始填充的需求，设置对应图片的初始状态为 'unlit'
        # 这些图片ID来自 all_image_files 的前几个，无论它们是否已成功加载碎片
        initial_fill_image_ids = all_image_ids[:min(settings.INITIAL_FULL_IMAGES_COUNT + (1 if settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT > 0 else 0), len(all_image_ids))]
        for img_id in initial_fill_image_ids:
            if img_id in self.image_status:
                # 只有当这些图片的状态还是 'unentered' 时，才设置为 'unlit'
                if self.image_status[img_id] == 'unentered':
                    self.image_status[img_id] = 'unlit'
            else:
                 print(f"警告: 尝试设置初始填充图片ID {img_id} 状态时，该ID不在 image_status 列表中。")


    def _load_and_process_single_image(self, image_id):
        """
        加载、处理单张原始图片，生成碎片surface，并尝试保存到缓存。
        如果缓存存在且不需要重新生成，则从缓存加载。
        这个方法只负责处理单张图片，并返回处理是否成功 (即该图片的全部碎片surface是否已在 self.pieces_surfaces 中可用)。
        它不负责更新 _loaded_image_count。

        Args:
            image_id (int): 要加载处理的图片ID。

        Returns:
            bool: True 如果成功生成或从缓存加载了该图片的全部碎片surface，否则返回 False。
        """
        if image_id not in self.all_image_files:
             print(f"警告: 图片ID {image_id} 文件路径未知，无法加载和处理。")
             return False # 处理失败

        # 如果该图片的全部碎片已经成功加载或生成过了，直接返回成功
        if image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces[image_id]) == settings.PIECES_PER_IMAGE:
             # print(f"图片ID {image_id} 碎片已存在内存，跳过加载处理。")
             return True # 已加载，视为成功

        filepath = self.all_image_files[image_id]
        # print(f"正在处理图片: ID {image_id}, 文件 {os.path.basename(filepath)}") # 调试信息

        fragments_loaded_from_cache = False
        if not settings.REGENERATE_PIECES: # Only try cache if not regenerating
            fragments_loaded_from_cache = self._load_pieces_from_cache(image_id)

        success = False # Flag to track if pieces were successfully loaded/generated for this image

        if settings.REGENERATE_PIECES or not fragments_loaded_from_cache:
            # If regenerating or cache failed, process from source image file
            # print(f"  图片ID {image_id}: { '重新生成' if settings.REGENERATE_PIECES else '缓存不存在或加载失败'}，开始裁剪和分割碎片...") # Debug

            try:
                original_img_pg = pygame.image.load(filepath).convert_alpha()
            except pygame.error as e:
                 print(f"错误: Pygame无法加载原始图片 {filepath}: {e}")
                 return False # Loading failed

            # 处理图片尺寸 (缩放和居中裁剪)
            # 目标尺寸是 settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE 宽 x settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE 高
            target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE # 5 * 120 = 600
            target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE # 9 * 120 = 1080
            target_size = (target_width, target_height) # <-- 确认这里是 (600, 1080)

            processed_img_pg = self._process_image_for_pieces(original_img_pg, target_size)

            # 如果处理成功，存储处理后的完整图片 (用于图库大图)
            if processed_img_pg and processed_img_pg.get_size() == target_size: # 确保处理后尺寸正确
                 self.processed_full_images[image_id] = processed_img_pg
                 # 尝试分割碎片 surface
                 pieces_for_this_image = self._split_image_into_pieces(processed_img_pg) # 修改 split 方法返回碎片字典

                 # 如果碎片成功生成，存储到 self.pieces_surfaces 并尝试保存到缓存
                 if pieces_for_this_image and len(pieces_for_this_image) == settings.PIECES_PER_IMAGE:
                     self.pieces_surfaces[image_id] = pieces_for_this_image # 存储碎片 surface 字典
                     self._save_pieces_to_cache(image_id) # 尝试保存到缓存
                     success = True # 碎片成功生成

                 else:
                      print(f"警告: 图片ID {image_id} 碎片分割数量不完整 ({len(pieces_for_this_image)}/{settings.PIECES_PER_IMAGE})。标记处理失败。")
                      # 不完整的碎片不存储到 self.pieces_surfaces，标记失败
                      success = False
            else:
                 print(f"警告: 图片ID {image_id} 处理后图片无效或尺寸不符 ({processed_img_pg.get_size() if processed_img_pg else 'None'} vs {target_size})，无法分割碎片。标记处理失败。")
                 success = False

        elif fragments_loaded_from_cache:
             # If cache loading was successful, pieces are already in self.pieces_surfaces[image_id]
             # Ensure processed_full_images exists for the gallery, load it if needed
             if image_id not in self.processed_full_images or not self.processed_full_images.get(image_id):
                  # print(f"  图片ID {image_id}: 从缓存加载碎片成功，需要处理原始图 {os.path.basename(filepath)} 用于图库完整图。") # Debug
                  try:
                     original_img_pg = pygame.image.load(filepath).convert_alpha()
                     target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE
                     target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE
                     processed_img_pg = self._process_image_for_pieces(original_img_pg, (target_width, target_height))
                     if processed_img_pg and processed_img_pg.get_size() == (target_width, target_height):
                         self.processed_full_images[image_id] = processed_img_pg
                     else:
                          print(f"警告: 处理图片 {filepath} 用于图库完整图时返回无效 Surface 或尺寸不符。")
                  except pygame.error as e:
                      print(f"错误: Pygame无法加载原始图片 {filepath} 用于图库完整图: {e}")
                  except Exception as e:
                      print(f"错误: 处理图片 {filepath} 用于图库完整图时发生未知错误: {e}")
             success = True # Cache loading was successful

        # Note: _loaded_image_count is NOT updated here. It is updated in the methods that call this one.
        return success # Return whether pieces for this image were successfully loaded/generated


    def load_next_batch_background(self, batch_size):
        """
        在后台按批次加载和处理未加载的图片。
        只处理 ImageManager 知道文件路径但碎片surface尚未加载的图片。

        Args:
            batch_size (int): 本次尝试加载处理的图片数量。

        Returns:
            int: 实际成功完成加载和处理（生成碎片 surface）的图片数量。
        """
        # is_loading_finished() 会检查 self._loaded_image_count 和 self._total_image_count
        if self.is_loading_finished():
             # print("后台加载：所有图片已加载完成。") # Debug, avoid spamming
             return 0 # 全部加载完成了

        all_image_ids = sorted(self.all_image_files.keys()) # 所有图片ID，按顺序
        processed_count_this_batch = 0

        # 找到下一张未成功加载碎片的图片ID
        next_unloaded_image_id = None
        for img_id in all_image_ids:
            # Check if the image ID is NOT in self.pieces_surfaces OR if its entry is incomplete
            if img_id not in self.pieces_surfaces or self.pieces_surfaces.get(img_id) is None or len(self.pieces_surfaces.get(img_id, {})) != settings.PIECES_PER_IMAGE:
                next_unloaded_image_id = img_id
                break

        if next_unloaded_image_id is None:
             # 如果没有未加载的图片ID，更新计数到总数 (理论上 is_loading_finished() 应该已经为 True)
             self._update_loaded_count() # 再次确保计数正确
             # print("后台加载：没有找到未加载的图片。") # Debug
             return 0


        # From the found unloaded image ID, get the next batch_size image IDs
        # Find the index of the next unloaded image ID in the list of all image IDs
        try:
            start_index = all_image_ids.index(next_unloaded_image_id)
        except ValueError:
             # This shouldn't happen if next_unloaded_image_id is from all_image_files, but for safety:
             print(f"错误: 后台加载图片ID {next_unloaded_image_id} 在 all_image_files 中不存在。")
             return 0

        # Get the IDs for the current batch, ensuring we don't go out of bounds
        images_for_this_batch_ids = all_image_ids[start_index : min(start_index + batch_size, len(all_image_ids))]

        # print(f"后台加载：正在处理图片ID列表: {images_for_this_batch_ids}") # Debug

        for image_id in images_for_this_batch_ids:
             # Only try to load/process if pieces are not already successfully loaded
             if image_id not in self.pieces_surfaces or self.pieces_surfaces.get(image_id) is None or len(self.pieces_surfaces.get(image_id, {})) != settings.PIECES_PER_IMAGE:
                success = self._load_and_process_single_image(image_id) # Load and process single image
                if success:
                     processed_count_this_batch += 1
                     # print(f"  后台加载成功处理图片ID {image_id}") # Debug
                else:
                     print(f"警告: 后台加载图片ID {image_id} 处理失败。")

        # After processing the batch, recalculate the total loaded count
        self._update_loaded_count()
        # print(f"后台加载批次完成。已成功处理/加载碎片图片数量更新为: {self._loaded_image_count}/{self._total_image_count}") # Debug


        # Return the number of images successfully processed in *this batch*
        return processed_count_this_batch


    def _update_loaded_count(self):
         """重新计算并更新 _loaded_image_count."""
         # 统计在 self.pieces_surfaces 中有完整 entry 的图片数量
         loaded_count_now = len([img_id for img_id in self.all_image_files if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])
         self._loaded_image_count = loaded_count_now


    def is_initial_load_finished(self):
        """检查初始设定的图片数量是否已加载完成 (即前 settings.INITIAL_LOAD_IMAGE_COUNT 张图片的碎片是否已准备好)。"""
        # 获取所有图片ID，按顺序
        all_image_ids = sorted(self.all_image_files.keys())
        # 确定初始应该加载的图片ID列表
        initial_load_ids = all_image_ids[:min(settings.INITIAL_LOAD_IMAGE_COUNT, len(all_image_ids))]

        # 检查初始加载列表中的所有图片是否都已经成功生成碎片
        for img_id in initial_load_ids:
             if img_id not in self.pieces_surfaces or self.pieces_surfaces.get(img_id) is None or len(self.pieces_surfaces.get(img_id, {})) != settings.PIECES_PER_IMAGE:
                 # 发现一个初始应加载但未加载的图片 (或者碎片数量不对)
                 # print(f"初始加载检查：图片ID {img_id} 碎片尚未加载或不完整。") # Debug
                 return False # 初始加载未完成

        # 所有初始图片都已加载碎片
        # print("初始加载的所有图片碎片已准备就绪。") # Debug
        return True


    def is_loading_finished(self):
        """检查是否所有扫描到的原始图片都已加载和处理（即全部碎片surface已生成）。"""
        # 检查已成功生成碎片 surface 的图片数量是否等于扫描到的总图片数量
        # print(f"检查总加载状态: 已加载 {self._loaded_image_count} / 总数 {self._total_image_count}") # Debug
        return self._loaded_image_count >= self._total_image_count


    def get_loading_progress(self):
         """返回当前加载进度信息，例如 '5/10'"""
         return f"{self._loaded_image_count}/{self._total_image_count}"

    def get_loading_progress_percentage(self):
         """返回当前加载进度百分比 (0.0 到 1.0)"""
         if self._total_image_count == 0:
              return 1.0 # 没有图片，视为加载完成
         return self._loaded_image_count / self._total_image_count


    def _process_image_for_pieces(self, image_surface_pg, target_size):
        """
        将 Pygame Surface 缩放和居中裁剪到目标尺寸。
        如果 PIL 可用且需要，可以使用PIL进行更复杂的处理。
        返回处理后的 Pygame Surface或None(如果失败)。
        目标尺寸是 (IMAGE_LOGIC_COLS * PIECE_SIZE, IMAGE_LOGIC_ROWS * PIECE_SIZE)。
        """
        if not PIL_AVAILABLE:
            # print("警告: PIL未安装，使用Pygame处理图片。")
            return self._process_image_with_pygame(image_surface_pg, target_size) # 回退到Pygame处理
        else:
             # print("使用PIL处理图片。")
             return self._process_image_with_pil(image_surface_pg, target_size)


    def _process_image_with_pygame(self, image_surface_pg, target_size):
        """使用Pygame进行缩放和裁剪"""
        img_w, img_h = image_surface_pg.get_size()
        target_w, target_h = target_size # <-- target_w = 600, target_h = 1080

        if img_h == 0 or target_h == 0:
             print("警告: 图像高度或目标高度为0，无法计算比例。")
             return None

        img_aspect = img_w / img_h
        target_aspect = target_w / target_h # <-- 目标比例是 600 / 1080 = 9 / 16 (0.5625)

        # 计算缩放后的尺寸
        # 保持原始比例，使其至少一个维度达到目标尺寸，另一个维度超出或刚好
        if img_aspect > target_aspect: # 原始图偏宽 (例如 16:9), 按目标高度缩放，宽度会超出，需要裁剪两侧
            scaled_h = target_h # 缩放后高度等于目标高度 (1080)
            scaled_w = int(scaled_h * img_aspect) # 缩放后宽度按原始比例计算
        else: # 原始图偏高 (例如 9:16) 或比例接近目标比例 (9:16), 按目标宽度缩放，高度会超出或刚好，需要裁剪上下
            scaled_w = target_w # 缩放后宽度等于目标宽度 (600)
            scaled_h = int(scaled_w / img_aspect) # 缩放后高度按原始比例计算

        # 确保缩放后的尺寸有效且不小于目标尺寸
        # Check if scaled dimensions are large enough to contain the target area
        if scaled_w < target_w or scaled_h < target_h or scaled_w <= 0 or scaled_h <= 0:
             print(f"警告: Pygame缩放尺寸计算异常，原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}, 缩放 {scaled_w}x{scaled_h}. 返回None.")
             return None # 返回 None 表示失败


        try:
             # 缩放
             scaled_img_pg = pygame.transform.scale(image_surface_pg, (scaled_w, scaled_h))
        except pygame.error as e:
             print(f"警告: Pygame缩放失败: {e}。返回None。")
             return None # 返回 None 表示失败


        # 计算裁剪区域
        # 裁剪的尺寸就是目标尺寸
        crop_width = target_w  # 裁剪宽度是目标宽度 (600)
        crop_height = target_h # 裁剪高度是目标高度 (1080)
        # 裁剪的起始点，使其居中
        crop_x = (scaled_w - crop_width) // 2
        crop_y = (scaled_h - crop_height) // 2

        # 确保裁剪区域在有效范围内
        # 检查裁剪起始点是否非负，以及裁剪结束点是否在缩放图片范围内
        if crop_x < 0 or crop_y < 0 or crop_x + crop_width > scaled_w or crop_y + crop_height > scaled_h:
             print(f"警告: Pygame裁剪区域 ({crop_x},{crop_y},{crop_width},{crop_height}) 超出缩放图片范围 ({scaled_w}x{scaled_h})，返回None。")
             return None # 返回 None 表示失败


        try:
            # 使用 Pygame 的 subsurface 进行裁剪，并复制以获得独立的 surface
            cropped_img_pg = scaled_img_pg.subsurface((crop_x, crop_y, crop_width, crop_height)).copy()
            return cropped_img_pg
        except ValueError as e:
             print(f"警告: Pygame subsurface 失败: {e}. 返回None。")
             return None


    def _process_image_with_pil(self, image_surface_pg, target_size):
        """使用Pillow进行缩放和居中裁剪到目标尺寸。"""
        if not PIL_AVAILABLE:
             print("错误: PIL未安装，无法使用PIL处理图片。")
             return None # 理论上不会走到这里，因为外层已检查PIL_AVAILABLE

        try:
            # 将Pygame Surface转换为PIL Image
            mode = "RGBA" if image_surface_pg.get_flags() & pygame.SRCALPHA else "RGB"
            try:
                # Ensure original surface is not locked or has a compatible format
                pil_img = Image.frombytes(mode, image_surface_pg.get_size(), pygame.image.tostring(image_surface_pg, mode))
            except Exception as e:
                 print(f"警告: Pygame tostring failed for PIL conversion: {e}. Returning None.")
                 # This might happen if surface is locked or has unusual format
                 return None # Fail conversion if tostring fails

            img_w, img_h = pil_img.size
            target_w, target_h = target_size # target_w = 600, target_h = 1080

            if img_h == 0 or target_h == 0:
                 print("警告: 图像高度或目标高度为0，无法计算比例。")
                 return None

            img_aspect = img_w / img_h
            target_aspect = target_w / target_h # 目标比例是 600 / 1080 = 9 / 16

            # 计算缩放后的尺寸
            # Keep original aspect ratio, scale to fit or exceed one target dimension
            if img_aspect > target_aspect: # Original is wider (e.g., 16:9), scale to target height
                scaled_h = target_h # Scaled height equals target height (1080)
                scaled_w = int(scaled_h * img_aspect) # Calculate scaled width based on original aspect
            else: # Original is taller (e.g., 9:16) or similar aspect, scale to target width
                scaled_w = target_w # Scaled width equals target width (600)
                scaled_h = int(scaled_w / img_aspect) # Calculate scaled height based on original aspect

            # Ensure scaled dimensions are valid and large enough for the target crop
            # This check is simplified: make sure dimensions are positive and at least target size (should hold if logic above is right)
            if scaled_w < target_w or scaled_h < target_h or scaled_w <= 0 or scaled_h <= 0:
                 print(f"警告: PIL缩放尺寸计算异常，原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}, 缩放 {scaled_w}x{scaled_h}. 返回None.")
                 return None # <--- **关键修改：异常时返回 None**


            try:
                 # PIL resize (using a high quality filter like LANCZOS)
                 scaled_pil_img = pil_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            except Exception as e:
                 print(f"警告: PIL缩放失败: {e}. 返回None.")
                 return None # <--- **关键修改：缩放失败时返回 None**


            # Calculate crop area
            crop_width = target_w # Crop width is target width (600)
            crop_height = target_h # Crop height is target height (1080)
            # Calculate crop start coordinates to center the crop
            crop_x = (scaled_w - crop_width) // 2
            crop_y = (scaled_h - crop_height) // 2

            # Ensure crop area is valid (non-negative start and end within scaled image bounds)
            if crop_x < 0 or crop_y < 0 or crop_x + crop_width > scaled_w or crop_y + crop_height > scaled_h:
                 print(f"警告: PIL裁剪区域 ({crop_x},{crop_y},{crop_width},{crop_height}) 超出缩放图片范围 ({scaled_w}x{scaled_h})，返回None。")
                 return None # <--- **关键修改：裁剪区域无效时返回 None**

            try:
                 cropped_pil_img = scaled_pil_img.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
            except Exception as e:
                 print(f"警告: PIL裁剪失败: {e}. 返回None.")
                 return None # <--- **关键修改：裁剪失败时返回 None**


            # 将PIL Image转换回Pygame Surface
            # Ensure mode is compatible with Pygame (RGBA)
            if cropped_pil_img.mode != 'RGBA':
                 # print(f"警告: PIL裁剪后模式为 {cropped_pil_img.mode}, 转换为 RGBA。")
                 cropped_pil_img = cropped_pil_img.convert('RGBA')
            # Use pygame.image.fromstring to create Pygame Surface
            try:
                 pygame_surface = pygame.image.fromstring(cropped_pil_img.tobytes(), cropped_pil_img.size, "RGBA")
                 return pygame_surface # <--- 成功返回 Surface
            except Exception as e:
                 print(f"警告: PIL to Pygame conversion failed: {e}. 返回None.")
                 return None # <--- 转换失败时返回 None

        except Exception as e:
            # Catch any other unexpected exceptions during PIL processing
            print(f"错误: 使用PIL处理图片时发生未知错误: {e}. 返回None.")
            # Optionally fallback to Pygame processing here, but returning None is safer on failure
            return None # <--- 捕获其他异常时返回 None


    # def _split_image_into_pieces(self, image_id, processed_image_surface): # Change signature
    def _split_image_into_pieces(self, processed_image_surface):
        """
        将处理好的图片分割成碎片surface并返回字典。

        Args:
            processed_image_surface (pygame.Surface): 已缩放和裁剪到目标尺寸的完整图片 Surface。
                                                     预期尺寸为 (IMAGE_LOGIC_COLS * PIECE_SIZE, IMAGE_LOGIC_ROWS * PIECE_SIZE).
                                                     即 (600, 1080)

        Returns:
            dict: { (row, col): pygame.Surface } 形式的碎片字典，或 None (如果分割失败或尺寸不匹配)。
        """
        img_w, img_h = processed_image_surface.get_size()
        piece_w, piece_h = settings.PIECE_SIZE, settings.PIECE_SIZE

        expected_w = settings.IMAGE_LOGIC_COLS * piece_w # 5 * 120 = 600
        expected_h = settings.IMAGE_LOGIC_ROWS * piece_h # 9 * 120 = 1080

        if img_w != expected_w or img_h != expected_h:
            # 这个检查理论上应该在 _process_image_for_pieces 中处理
            print(f"错误: 处理后的图片尺寸 {img_w}x{img_h} 与预期 {expected_w}x{expected_h} 不符。无法分割碎片。")
            return None # 尺寸不匹配，无法分割

        pieces_dict = {} # 存储本次分割的碎片

        # Iterate through the logical grid (rows x cols) to extract pieces
        # Iterate through Rows first (0 to 8), then Columns (0 to 4)
        for r in range(settings.IMAGE_LOGIC_ROWS): # Iterate through rows (0 to 8)
            for c in range(settings.IMAGE_LOGIC_COLS): # Iterate through columns (0 to 4)
                x = c * piece_w # Calculate x-coordinate for the piece (Col affects X)
                y = r * piece_h # Calculate y-coordinate for the piece (Row affects Y)

                # Ensure extraction area is within the image bounds
                if x >= 0 and y >= 0 and x + piece_w <= img_w and y + piece_h <= img_h:
                    try:
                         # 从大图 surface 中提取碎片区域
                         # 使用copy()确保每个碎片surface是独立的
                         piece_surface = processed_image_surface.subsurface((x, y, piece_w, piece_h)).copy()
                         pieces_dict[(r, c)] = piece_surface
                    except ValueError as e:
                         print(f"警告: subsurface 提取碎片 r{r}_c{c} 失败: {e}. 跳过。")
                    except Exception as e:
                        print(f"警告: 提取碎片 r{r}_c{c} 时发生未知错误: {e}. 跳过。")
                else:
                     print(f"警告: 碎片 r{r}_c{c} 的提取区域 ({x},{y},{piece_w},{piece_h}) 超出图片范围 ({img_w}x{img_h})，跳过。")

        # 检查实际生成的碎片数量
        if len(pieces_dict) != settings.PIECES_PER_IMAGE:
             print(f"警告: 实际生成的碎片数量 ({len(pieces_dict)}) 不等于预期数量 ({settings.PIECES_PER_IMAGE})。")
             # 如果数量不对，返回 None，表示分割不完整
             return None

        return pieces_dict # 返回分割成功的碎片字典


    def _save_pieces_to_cache(self, image_id):
        """将指定图片的碎片 surface 保存为文件缓存"""
        if image_id not in self.pieces_surfaces or not self.pieces_surfaces[image_id] or len(self.pieces_surfaces[image_id]) != settings.PIECES_PER_IMAGE:
             # print(f"警告: 没有图片 {image_id} 的完整碎片可以保存到缓存。")
             return False # 没有完整碎片可保存

        # print(f"正在保存图片 {image_id} 的碎片到缓存...") # Debug
        os.makedirs(settings.GENERATED_PIECE_DIR, exist_ok=True)

        success_count = 0
        total_pieces = len(self.pieces_surfaces[image_id])

        for (r, c), piece_surface in self.pieces_surfaces[image_id].items():
            filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
            filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
            try:
                 pygame.image.save(piece_surface, filepath)
                 success_count += 1
            except pygame.error as e:
                 print(f"警告: 无法保存碎片 {filepath} 到缓存: {e}")

        # print(f"图片 {image_id} 共有 {total_pieces} 个碎片，成功保存 {success_count} 个到缓存。")
        return success_count == total_pieces # 所有碎片都成功保存才算成功


    def _load_pieces_from_cache(self, image_id):
        """尝试从缓存文件加载指定图片的碎片"""
        # print(f"尝试从缓存加载图片 {image_id} 的碎片...") # Debug
        expected_pieces_count = settings.PIECES_PER_IMAGE # 5x9 = 45

        # 快速检查：是否存在所有预期的碎片文件
        all_files_exist_quick_check = True
        # Iterate through the logical grid (rows x cols)
        for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
            for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                 filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                 filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                 if not os.path.exists(filepath):
                     all_files_exist_quick_check = False
                     break
            if not all_files_exist_quick_check: break

        if not all_files_exist_quick_check:
             # print(f"  图片 {image_id} 的缓存文件不完整或不存在，跳过缓存加载。") # Debug
             return False # 缓存文件不完整或不存在

        # 如果文件存在，尝试加载
        # print(f"  找到图片 {image_id} 的所有 {expected_pieces_count} 个缓存文件，开始加载...") # Debug
        potential_pieces_surfaces = {} # 临时存储加载的碎片surface
        loaded_count = 0
        try:
            # Iterate through the logical grid (rows x cols)
            for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
                for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                    filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                    filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                    piece_surface = pygame.image.load(filepath).convert_alpha()
                    # 检查加载的碎片尺寸是否正确
                    if piece_surface.get_size() != (settings.PIECE_SIZE, settings.PIECE_SIZE):
                         print(f"警告: 缓存碎片文件 {filepath} 尺寸不正确 ({piece_surface.get_size()})。缓存加载失败。")
                         potential_pieces_surfaces = {} # 清空不完整的加载结果
                         return False # 标记加载失败
                    potential_pieces_surfaces[(r, c)] = piece_surface
                    loaded_count += 1

            # 检查是否加载了所有预期的碎片数量
            if loaded_count == expected_pieces_count:
                # 如果加载成功，将临时字典存储到 self.pieces_surfaces
                self.pieces_surfaces[image_id] = potential_pieces_surfaces
                # print(f"  成功从缓存加载图片 {image_id} 的 {loaded_count} 个碎片。") # Debug
                return True # 加载成功
            else:
                # 这通常不应该发生，如果文件存在快速检查通过但数量不对
                print(f"警告: 从缓存加载图片 {image_id} 的碎片数量不完整。预期 {expected_pieces_count}，实际加载 {loaded_count}。缓存加载失败。") # Debug
                potential_pieces_surfaces = {} # 清空不完整的加载结果
                return False

        except pygame.error as e:
             print(f"警告: 从缓存加载图片 {image_id} 的碎片时发生Pygame错误: {e}. 缓存加载失败。")
             self.pieces_surfaces[image_id] = {} # 确保对应的entry被清空或不存在
             return False
        except Exception as e:
             print(f"警告: 从缓存加载图片 {image_id} 的碎片时发生未知错误: {e}. 缓存加载失败。")
             self.pieces_surfaces[image_id] = {} # 确保对应的entry被清空或不存在
             return False


    def _initialize_consumption(self):
        """确定第一张要消耗碎片的图片ID，并计算初始填充消耗的碎片数量。"""
        # 这里只需要基于 self.all_image_files 的键来计算消耗顺序
        all_image_ids = sorted(self.all_image_files.keys())

        if not all_image_ids:
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             print("警告：没有找到任何图片文件，无法初始化碎片消耗机制！") # 调试信息
             return

        # 初始填充会从 image_ids[0] 开始，直到 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
        # 实际开始消耗的图片是 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]，如果它存在的话
        next_consume_img_index_in_all = settings.INITIAL_FULL_IMAGES_COUNT

        if next_consume_img_index_in_all < len(all_image_ids):
            self.next_image_to_consume_id = all_image_ids[next_consume_img_index_in_all]
            # 初始填充时已经从这张图片获取了 settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个碎片
            self.pieces_consumed_from_current_image = settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT

            print(f"初始化碎片消耗：从图片ID {self.next_image_to_consume_id} 开始消耗，已消耗 {self.pieces_consumed_from_current_image} 个碎片 (用于初始填充)。") # 调试信息
        else:
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             print("警告：所有图片都用于初始填充或图片数量不足，没有更多图片可供后续消耗。") # 调试信息


    def get_initial_pieces_for_board(self):
        """
        获取游戏开始时需要填充到拼盘的 Piece 对象列表。
        这些碎片来自**初始加载批次中已成功加载碎片**的图片。
        """
        initial_pieces_list = []
        # 只考虑 ImageManager 已经成功加载或生成了碎片 surface 的图片ID
        image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])

        if not image_ids_with_pieces:
            print("错误: 没有图片碎片表面可供初始化 Board。")
            return [] # 没有图片直接返回空列表

        # 确定哪些已加载碎片的图片将用于初始填充
        # 这些图片是 all_image_files 中前 INITIAL_FULL_IMAGES_COUNT + (1 if ...) 个，且碎片已加载成功的
        all_image_ids_ordered = sorted(self.all_image_files.keys())
        initial_fill_candidates_ids = all_image_ids_ordered[:min(settings.INITIAL_FULL_IMAGES_COUNT + (1 if settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT > 0 else 0), len(all_image_ids_ordered))]
        
        initial_fill_images_with_loaded_pieces = [
            img_id for img_id in initial_fill_candidates_ids
            if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE
        ]
        
        if not initial_fill_images_with_loaded_pieces:
             print("错误: 用于初始填充的图片碎片均未成功加载。")
             return []


        pieces_added_count = 0
        
        # 添加前 INITIAL_FULL_IMAGES_COUNT 张完整图片的碎片 (从已加载且用于初始填充的列表中取)
        num_full_images_added = 0
        for img_id in initial_fill_images_with_loaded_pieces:
            if num_full_images_added >= settings.INITIAL_FULL_IMAGES_COUNT:
                break # 已经添加了足够数量的完整图片
                
            # 确保是完整图片所需的全部碎片
            if img_id in initial_fill_candidates_ids[:settings.INITIAL_FULL_IMAGES_COUNT]:
                 # print(f"正在获取图片 {img_id} 的所有碎片 ({settings.PIECES_PER_IMAGE} 个) 用于初始完整填充。") # Debug
                 # Iterate through the logical grid (rows x cols)
                 for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
                     for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                          # 确保碎片surface存在
                          piece_surface = self.pieces_surfaces[img_id][(r, c)] # 此时pieces_surfaces[img_id] guaranteed non-None and full
                          # 创建Piece对象，初始网格位置先填 -1,-1，Board后续会随机分配
                          initial_pieces_list.append(Piece(piece_surface, img_id, r, c, -1, -1))
                          pieces_added_count += 1
                 self.image_status[img_id] = 'unlit' # 这几张图片现在是“未点亮”状态
                 num_full_images_added += 1
            
        # 添加下一张图片的碎片 (遵循 Initial_partial_image_pieces_count 规则)
        # 这张图片是 initial_fill_candidates_ids 列表中排在 num_full_images_added 后面的第一张，且碎片已加载
        next_partial_img_index = settings.INITIAL_FULL_IMAGES_COUNT
        if next_partial_img_index < len(initial_fill_candidates_ids):
             current_consume_img_id = initial_fill_candidates_ids[next_partial_img_index]
             
             # 确保这张图的碎片已加载成功
             if current_consume_img_id in self.pieces_surfaces and self.pieces_surfaces.get(current_consume_img_id) is not None and len(self.pieces_surfaces[current_consume_img_id]) == settings.PIECES_PER_IMAGE:
                  # print(f"正在从图片 {current_consume_img_id} 获取前 {settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT} 个碎片用于初始填充。") # Debug

                  piece_count_from_current = 0
                  # 按照逻辑顺序 (行优先，列优先) 获取碎片
                  total_piece_index_in_img = 0
                  for r in range(settings.IMAGE_LOGIC_ROWS):
                      for c in range(settings.IMAGE_LOGIC_COLS):
                          if piece_count_from_current < settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                              # 确保碎片surface存在
                              piece_surface = self.pieces_surfaces[current_consume_img_id][(r, c)]
                              initial_pieces_list.append(Piece(piece_surface, current_consume_img_id, r, c, -1, -1))
                              pieces_added_count += 1
                              piece_count_from_current += 1
                              # self.pieces_consumed_from_current_image += 1 # 这个计数在 _initialize_consumption 中处理
                          else:
                              break # 达到指定数量
                          total_piece_index_in_img += 1
                      if piece_count_from_current == settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                          break

                  # 设置这张图片的状态为 'unlit'
                  if current_consume_img_id in self.image_status:
                      if self.image_status[current_consume_img_id] == 'unentered': # 只有从未入场才变为未点亮
                          self.image_status[current_consume_img_id] = 'unlit'
                  else:
                       print(f"警告: 初始填充图片ID {current_consume_img_id} 不在 image_status 列表中。")
             # else:
                  # print(f"警告: 图片ID {current_consume_img_id} 用于初始部分填充，但碎片未成功加载。") # Debug

        print(f"总共获取了 {pieces_added_count} 个碎片用于初始填充。") # 调试信息
        
        # 计算预期总碎片数量，并进行检查
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS
        if pieces_added_count > total_required_pieces:
             print(f"错误: 获取的初始碎片数量 {pieces_added_count} 多于拼盘总槽位 {total_required_pieces}！将截断列表。")
             initial_pieces_list = initial_pieces_list[:total_required_pieces] # 截断，避免溢出
        elif pieces_added_count < total_required_pieces:
              print(f"警告: 获取的初始碎片数量 {pieces_added_count} 少于拼盘总槽位 {total_required_pieces}！拼盘将有空位。")


        # 将列表随机打乱
        import random
        random.shuffle(initial_pieces_list)

        return initial_pieces_list


    def get_next_fill_pieces(self, count):
        """
        根据填充规则，从 image_manager 获取下一批指定数量的新 Piece 对象用于填充空位。
        这些碎片来自**已加载**（包括后台加载）的图片。
        """
        new_pieces = []
        pieces_needed = count
        # 只从已成功生成碎片 surface 的图片中获取
        image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])


        # print(f"需要填充 {pieces_needed} 个空位...") # Debug

        # 如果当前没有需要消耗的图片了，或者下一张图片碎片还未加载完成
        if self.next_image_to_consume_id is None or self.next_image_to_consume_id not in image_ids_with_pieces:
             # print("警告: 没有更多已加载的图片可供消耗碎片。") # Debug
             return [] # 返回空列表

        # 找到当前正在消耗的图片的逻辑索引 (在所有已加载碎片的图片ID列表中)
        try:
            current_img_index_in_loaded = image_ids_with_pieces.index(self.next_image_to_consume_id)
        except ValueError:
             print(f"错误: 当前消耗的图片ID {self.next_image_to_consume_id} 不在已加载碎片图片列表中。")
             self.next_image_to_consume_id = None # 状态异常，重置
             return []


        # 循环直到获取足够碎片或没有更多已加载的图片
        while pieces_needed > 0 and self.next_image_to_consume_id is not None:
            current_img_id = self.next_image_to_consume_id

            # 确保当前图片的碎片 surface 已经加载并存在 (理论上因为上面的判断，这里应该为真)
            if current_img_id not in self.pieces_surfaces or self.pieces_surfaces.get(current_img_id) is None or len(self.pieces_surfaces.get(current_img_id, {})) != settings.PIECES_PER_IMAGE:
                print(f"警告: 当前消耗图片ID {current_img_id} 的碎片 surface 尚未加载或不完整。停止获取新碎片。") # Debug
                self.next_image_to_consume_id = None # 没有已加载的碎片可用，停止消耗
                break

            total_pieces_in_current_img = settings.PIECES_PER_IMAGE # 45
            pieces_remaining_in_current_img = total_pieces_in_current_img - self.pieces_consumed_from_current_image

            # 计算从当前图片可以获取多少碎片
            pieces_to_take_from_current = min(pieces_needed, pieces_remaining_in_current_img)

            # print(f"从图片 {current_img_id} 剩余 {pieces_remaining_in_current_img} 个，本次尝试获取 {pieces_to_take_from_current} 个。") # Debug

            if pieces_to_take_from_current > 0:
                # 从当前图片获取碎片，按照逻辑顺序继续上次消耗的位置
                pieces_taken_count = 0
                # 根据 self.pieces_consumed_from_current_image 计算开始的逻辑 (row, col)
                start_total_index = self.pieces_consumed_from_current_image # 总碎片索引

                # 遍历逻辑碎片位置，找到要取的碎片
                current_total_index = 0
                found_start = False
                for r in range(settings.IMAGE_LOGIC_ROWS):
                    for c in range(settings.IMAGE_LOGIC_COLS):
                         if current_total_index >= start_total_index and pieces_taken_count < pieces_to_take_from_current:
                              found_start = True
                              # 确保碎片表面存在
                              if (r, c) in self.pieces_surfaces[current_img_id]: # 此时pieces_surfaces[current_img_id] guaranteed non-None and full
                                  piece_surface = self.pieces_surfaces[current_img_id][(r, c)]
                                  new_pieces.append(Piece(piece_surface, current_img_id, r, c, -1, -1)) # -1,-1 表示待分配位置
                                  pieces_taken_count += 1
                                  self.pieces_consumed_from_current_image += 1 # 标记已消耗数量
                                  # print(f"  获取碎片: 图片{current_img_id}_行{r}_列{c}") # Debug
                              else:
                                   # 这通常不应该发生，如果图片ID在pieces_surfaces中且完整，其碎片应该存在
                                   print(f"错误: 图片 {current_img_id} 的逻辑碎片 ({r},{c}) 表面不存在，但图片被标记为完整加载。") # Debug
                         current_total_index += 1 # 无论是否达到start_total_index，计数器都前进，以保持逻辑顺序

                         if pieces_taken_count == pieces_to_take_from_current:
                             break # 达到本次从当前图片取碎片的数量
                    if pieces_taken_count == pieces_to_take_from_current:
                        break # 达到本次从当前图片取碎片的数量
                    # 如果已经找到了开始索引，但遍历完一行还没取够，并且还需要更多碎片
                    if found_start and pieces_taken_count < pieces_to_take_from_current and r < settings.IMAGE_LOGIC_ROWS - 1:
                         pass # 继续到下一行


                pieces_needed -= pieces_taken_count
                # print(f"本次从图片 {current_img_id} 实际获取了 {pieces_taken_count} 个碎片。还需要 {pieces_needed} 个。") # Debug


            # 检查当前图片的碎片是否已消耗完
            # 使用 >= total_pieces_in_current_img 确保健壮性
            if self.pieces_consumed_from_current_image >= total_pieces_in_current_img:
                # print(f"图片 {current_img_id} 的碎片已消耗完或超出。") # Debug
                # 切换到下一张已加载碎片的图片
                current_img_index_in_loaded += 1
                # 重新获取已加载列表，以防后台加载增加了新图片
                image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])

                if current_img_index_in_loaded < len(image_ids_with_pieces):
                    self.next_image_to_consume_id = image_ids_with_pieces[current_img_index_in_loaded]
                    self.pieces_consumed_from_current_image = 0 # 重置消耗计数
                    # self.image_status[self.next_image_to_consume_id] = 'unlit' # 新进入的图片状态变为未点亮 (已经在_initial_load_images处理了)
                    print(f"下一张消耗图片ID设置为: {self.next_image_to_consume_id}") # Debug
                else:
                    self.next_image_to_consume_id = None # 没有更多已加载的图片了
                    print("没有更多已加载图片可供消耗。") # Debug
                # 如果切换图片，并且 pieces_needed 仍大于 0，循环会继续，尝试从下一张图片获取

            # 如果还需要碎片，但是已经没有下一张已加载的图片了
            # 这个条件已经在 while 循环头检查了 next_image_to_consume_id is not None
            # 但是为了清晰，可以再次检查
            # if pieces_needed > 0 and self.next_image_to_consume_id is None:
                 # print(f"警告: 需要 {count} 个碎片，但没有更多已加载图片可用。最终只获取到 {len(new_pieces)} 个。") # Debug
                 # break # 退出循环


        # 注意：新获取的碎片不需要打乱，它们会根据填充空位的顺序放置到拼盘中。
        return new_pieces


    def get_all_entered_pictures_status(self):
        """
        获取所有已入场（未点亮或已点亮）图片的ID、状态和完成时间。
        已入场的图片定义为：ImageManager 知道文件路径且状态不是 'unentered'。
        返回所有已入场图片的信息，不限碎片加载状态。
        """
        status_list = []
        # 确保遍历顺序与图片ID一致
        all_image_ids = sorted(self.all_image_files.keys())

        for img_id in all_image_ids:
             status = self.image_status.get(img_id, 'unentered')
             # 图库中只显示 'unlit' 和 'lit' 状态的图片
             if status in ['unlit', 'lit']:
                status_info = {'id': img_id, 'state': status}
                if status == 'lit':
                    # 获取完成时间，如果没有完成时间 (不应该发生)，使用当前时间
                    status_info['completion_time'] = self.completed_times.get(img_id, time.time())
                # 添加一个标志，表示碎片 surface 是否已加载，用于图库是否能显示缩略图
                status_info['is_pieces_loaded'] = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE)
                status_list.append(status_info)

        return status_list

    def set_image_state(self, image_id, state):
        """
        设置指定图片的完成状态。

        Args:
            image_id (int): 图片ID
            state (str): 新状态 ('unentered', 'unlit', 'lit')
        """
        # 只有当 image_id 在 ImageManager 已知的图片列表中才更新状态
        if image_id in self.all_image_files: # 使用 all_image_files 来检查图片是否存在
            old_status = self.image_status.get(image_id, 'unentered')
            self.image_status[image_id] = state
            # print(f"图片 {image_id} 状态改变: {old_status} -> {state}") # Debug
            if state == 'lit' and old_status != 'lit':
                 # 如果状态从非lit变为lit，记录完成时间
                 self.completed_times[image_id] = time.time() # 记录点亮时间
        else:
             print(f"警告: 尝试设置未知图片ID {image_id} 的状态为 {state}。")


    def get_thumbnail(self, image_id):
         """获取指定图片的缩略图surface，用于图库列表"""
         # 尝试从已处理的完整图片获取
         if image_id in self.processed_full_images and self.processed_full_images.get(image_id):
             full_img = self.processed_full_images[image_id]
             try:
                thumbnail = pygame.transform.scale(full_img, (settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT))
                return thumbnail
             except pygame.error as e:
                 print(f"警告: 无法为图片 {image_id} 生成缩略图 (缩放失败): {e}")
                 return None
         # 如果 processed_full_images 不存在，并且碎片存在且完整，尝试从碎片拼合 (可选，复杂)
         elif image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces[image_id]) == settings.PIECES_PER_IMAGE:
              # print(f"警告: 图片ID {image_id} 的完整处理后图片不存在，尝试从碎片拼合缩略图...") # Debug
              # TODO: 实现从碎片拼合缩略图 (可选，优先级较低)
              pass # 暂时返回 None

         # print(f"警告: 无法获取图片 {image_id} 的完整处理后图片或碎片，无法生成缩略图。") # Debug
         return None # 返回 None 表示失败


    def get_full_processed_image(self, image_id):
         """获取指定图片的完整处理后的surface (用于图库大图查看)"""
         # 只有当图片的全部碎片已成功加载时，其完整处理后的图片才可能在 processed_full_images 中
         if image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces[image_id]) == settings.PIECES_PER_IMAGE:
             return self.processed_full_images.get(image_id) # 如果图片ID不存在，返回None
         else:
             # print(f"警告: 尝试获取图片ID {image_id} 的完整处理后图片，但碎片尚未完整加载。") # Debug
             return None # 碎片未加载完成，完整图不可用

    def get_state(self):
        """
        获取ImageManager需要存档的状态信息。

        Returns:
            dict: 包含图片状态、完成时间、碎片消耗进度等的字典。
        """
        state = {
            'image_status': self.image_status, # 存储所有图片的最新状态
            'completed_times': self.completed_times, # 存储已点亮图片的完成时间
            'next_image_to_consume_id': self.next_image_to_consume_id, # 存储下一个要消耗碎片的图片ID
            'pieces_consumed_from_current_image': self.pieces_consumed_from_current_image # 存储当前消耗图片的已消耗碎片数量
        }
        # Note: self.all_image_files 是根据文件扫描获得的，不需要存档
        # self.processed_full_images 和 self.pieces_surfaces 是运行时加载的，不需要存档，读档时需要重新加载
        return state

    def load_state(self, state_data):
        """
        从存档数据加载ImageManager的状态。

        Args:
            state_data (dict): 从存档文件中读取的状态字典。
        """
        if not state_data:
            print("警告: ImageManager 尝试从空的存档数据加载状态。")
            return # 没有有效的存档数据，不加载

        # 从存档数据更新ImageManager的状态属性
        # 确保键存在于 state_data 中以避免 KeyError
        if 'image_status' in state_data:
             # 确保只加载扫描到的图片的状态，避免加载不存在图片的记录
             loaded_image_status = state_data['image_status']
             self.image_status = {
                 img_id: status
                 for img_id, status in loaded_image_status.items()
                 if img_id in self.all_image_files # 只加载扫描到的图片的状态
             }
             print(f"ImageManager 从存档加载了 {len(self.image_status)} 张图片的状态。") # Debug

        if 'completed_times' in state_data:
             # 确保只加载状态为 lit 的图片的完成时间，且图片ID存在
             loaded_completed_times = state_data['completed_times']
             self.completed_times = {
                 img_id: comp_time
                 for img_id, comp_time in loaded_completed_times.items()
                 if img_id in self.image_status and self.image_status.get(img_id) == 'lit' # 只加载已入场且已点亮图片的完成时间
             }
             print(f"ImageManager 从存档加载了 {len(self.completed_times)} 张已点亮图片的完成时间。") # Debug


        if 'next_image_to_consume_id' in state_data:
             # 确保加载的 next_image_to_consume_id 是一个已知的图片ID
             next_id = state_data['next_image_to_consume_id']
             if next_id is None or next_id in self.all_image_files:
                 self.next_image_to_consume_id = next_id
                 print(f"ImageManager 从存档加载 next_image_to_consume_id: {self.next_image_to_consume_id}") # Debug
             else:
                 print(f"警告: 存档中的 next_image_to_consume_id ({next_id}) 不是已知图片ID。使用默认值或重新计算。") # Debug
                 # 如果加载的ID无效，需要重新确定下一个要消耗的ID
                 self._initialize_consumption() # 重新初始化消耗状态


        if 'pieces_consumed_from_current_image' in state_data:
             # 确保加载的已消耗数量在有效范围内 (0 到 settings.PIECES_PER_IMAGE)
             consumed_count = state_data['pieces_consumed_from_current_image']
             if 0 <= consumed_count <= settings.PIECES_PER_IMAGE:
                 self.pieces_consumed_from_current_image = consumed_count
                 print(f"ImageManager 从存档加载 pieces_consumed_from_current_image: {self.pieces_consumed_from_current_image}") # Debug
             else:
                 print(f"警告: 存档中的 pieces_consumed_from_current_image ({consumed_count}) 无效。使用默认值或重新计算。") # Debug
                 # 如果加载的数量无效，需要重新初始化消耗数量
                 if self.next_image_to_consume_id is not None:
                     self.pieces_consumed_from_current_image = 0 # 简单重置为0
                 else:
                     self.pieces_consumed_from_current_image = 0


        # Note: 加载状态后，需要确保对应图片的碎片 surface 在内存中可用
        # ImageManager 的初始加载(_initial_load_images) 和后台加载(_load_and_process_single_image) 会负责加载碎片
        # 在 main.py 中加载 ImageManager 状态后，Board 在加载其状态时会需要这些碎片
        # Board.load_state 会检查碎片是否已加载，并在需要时触发加载。

