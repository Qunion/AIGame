# image_manager.py
# 负责图片的加载、处理、碎片生成、管理图片状态和提供碎片/完整图资源

import pygame
import settings
import os
import time
import math # 用于计算加载进度百分比
import collections # 导入 collections 模块用于 deque
from piece import Piece # Piece 类可能在 ImageManager 中创建实例，所以需要导入
import utils # 导入工具函数模块 <--- 确保这行正确且没有被注释

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    print("警告: Pillow库未安装。部分图像处理功能可能受限。建议安装: pip install Pillow")
    PIL_AVAILABLE = False


class ImageManager:
    def __init__(self, game):
        """
        初始化图像管理器。扫描图片文件，建立加载队列，执行初始加载批次。

        Args:
            game (Game): Game实例，用于在加载时显示加载界面 (可选)。
        """
        self.game = game # 持有Game实例的引用

        self.image_status = {} # 存储每张图片的状态 {id: 'unentered' / 'unlit' / 'lit'} - 必须在扫描前初始化

        # 存储所有原始图片文件的信息 {id: filepath}
        self.all_image_files = {} # {image_id: full_filepath}
        self._scan_image_files() # 扫描图片文件，获取所有图片ID和路径 (现在 self.image_status 已经存在)

        # 存储加载和处理后的原始图片表面 {id: pygame.Surface} (用于图库大图)
        self.processed_full_images = {}
        # 存储生成的碎片表面 {id: { (row, col): pygame.Surface }}
        # 只有当图片的全部碎片成功加载或生成时，才会在这个字典中创建 entry
        self.pieces_surfaces = {}

        # --- 缓存的缩略图和灰度缩略图 ---
        self.cached_thumbnails = {} # {id: pygame.Surface}
        self.cached_unlit_thumbnails = {} # {id: pygame.Surface}


        # 存储已点亮图片的完成时间 {id: timestamp} # 用于图库排序
        self.completed_times = {}

        # --- 加载队列 ---
        # 高优先级队列：存放从存档加载状态后，需要优先加载的图片ID (未点亮/已点亮)
        self._high_priority_load_queue = collections.deque()
        # 普通队列：存放初始加载批次和所有剩余的未入场图片ID
        self._normal_load_queue = collections.deque()

        # 跟踪图片加载进度
        self._loaded_image_count = 0 # Counts images where ALL pieces AND thumbnails were successfully loaded/generated
        self._total_image_count = len(self.all_image_files) # Total scanned image files

        # 跟踪下一批需要从哪张图片取碎片 (仅用于碎片消耗，与加载顺序无关)
        self.next_image_to_consume_id = -1 # Determined in _initialize_consumption
        self.pieces_consumed_from_current_image = 0 # Determined in _initialize_consumption

        # === 初始化时填充加载队列 ===
        self._populate_load_queues()

        # 执行初始加载批次 (从队列中取前 settings.INITIAL_LOAD_IMAGE_COUNT 个处理)
        # 这会在 Board 初始化前完成，确保 Board 需要的碎片可用
        self._process_initial_load_batch(settings.INITIAL_LOAD_IMAGE_COUNT)

        # 初始化碎片消耗机制，基于**所有**扫描到的图片ID列表 (确定从哪张图开始消耗，以及初始消耗了多少)
        self._initialize_consumption()

        print(f"ImageManager 初始化完成。总图片文件数: {self._total_image_count}，初始加载成功图片数: {self._loaded_image_count}") # Debug


    def _scan_image_files(self):
        """扫描 assets 目录，找到所有符合 image_N.png 命名规则的图片文件路径和ID，并初始化状态。"""
        image_files = [f for f in os.listdir(settings.ASSETS_DIR) if f.startswith("image_") and f.endswith(".png")]
        # 按图片ID排序
        image_files.sort(key=lambda f: int(os.path.splitext(f)[0].replace("image_", "")))

        for filename in image_files:
            try:
                # 从文件名中提取图片ID
                image_id = int(os.path.splitext(filename)[0].replace("image_", ""))
                full_path = os.path.join(settings.ASSETS_DIR, filename)
                # print(f"扫描到图片文件: {filename} (ID: {image_id})") # Debug
                self.all_image_files[image_id] = full_path
                # print(f"路径: {self.all_image_files}")
                # 所有扫描到的图片初始状态都是未入场
                if image_id not in self.image_status: # 避免重复扫描时覆盖状态 (如果ImageManager被多次初始化)
                    self.image_status[image_id] = 'unentered'
            except ValueError:
                print(f"警告: 文件名格式不正确，无法提取图片ID: {filename}")
            except Exception as e:
                print(f"警告: 扫描文件 {filename} 时发生错误: {e}")
        # print(f"文件路径: {self.all_image_files}")

        self._total_image_count = len(self.all_image_files)
        print(f"扫描到 {self._total_image_count} 张原始图片文件。") # Debug

    def _populate_load_queues(self):
        """根据扫描到的文件，初始化填充加载队列。"""
        all_image_ids_ordered = sorted(self.all_image_files.keys())

        # 最初，所有图片的ID都进入普通加载队列
        # 高优先级队列在加载存档状态时填充
        self._normal_load_queue.extend(all_image_ids_ordered)
        print(f"初始加载队列填充完成， {len(self._normal_load_queue)} 张图片进入普通队列。") # Debug


    def _process_initial_load_batch(self, count):
        """从普通加载队列处理前 'count' 张图片，用于游戏启动时的初始加载批次。"""
        print(f"正在处理初始加载批次前 {count} 张图片...") # Debug
        processed_count = 0
        # 从普通队列左侧处理最多 'count' 张图片
        for _ in range(count):
            if not self._normal_load_queue:
                break # 队列已空

            image_id = self._normal_load_queue.popleft() # 从队列左侧获取图片ID

            # 加载并处理单张图片，包括缓存加载和资源生成 (会更新内部缓存字典)
            # 无论处理是否成功，_load_and_process_single_image 都会尝试加载或生成资源
            self._load_and_process_single_image(image_id)

            # Update processed_count_this_batch? Not needed here, _update_loaded_count handles total.

        # 在整个初始加载批次处理完后，更新已加载计数
        self._update_loaded_count()
        # Note: The actual number of successfully loaded images in this batch might be less than 'count'
        # if some images failed to process. _update_loaded_count reflects total success.
        # print(f"初始加载批次处理完成。") # Debug


    def _load_and_process_single_image(self, image_id):
        """
        加载、处理单张原始图片，生成碎片surface，保存到缓存，并生成缩略图缓存。
        如果缓存存在且不重新生成，则从缓存加载。
        这个方法负责确保给定图片ID的碎片和缩略图都已加载到内存缓存。
        这个方法会更新内部缓存字典。它**不**更新 _loaded_image_count，由调用方在批次处理后统一调用 _update_loaded_count。
        Args:
            image_id (int): 要处理的图片ID。

        Returns:
            bool: True 如果成功加载或生成了该图片的全部碎片surface和缩略图，否则返回 False。
        """
        if image_id not in self.all_image_files:
             print(f"警告: 图片ID {image_id} 文件路径未知，无法加载和处理。")
             return False

        # 检查碎片和缩略图是否都已经成功加载/生成并缓存在内存中
        pieces_already_loaded = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == settings.PIECES_PER_IMAGE)
        thumbnails_already_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                     image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)

        if pieces_already_loaded and thumbnails_already_cached:
             # print(f"图片ID {image_id} 碎片和缩略图已存在内存，跳过加载处理。") # Debug
             return True # 资源已准备好，返回成功


        filepath = self.all_image_files[image_id]
        # print(f"正在处理图片: ID {image_id}, 文件 {os.path.basename(filepath)}") # Debug

        fragments_loaded_from_cache = False
        if not settings.REGENERATE_PIECES: # Only try cache if not regenerating
            fragments_loaded_from_cache = self._load_pieces_from_cache(image_id) # This populates self.pieces_surfaces if successful

        processed_full_image_available = False # 标记是否获取到了处理后的完整图片 Surface (用于缩略图和大图)
        processed_img_pg = None # 初始化为 None

        # 如果需要重新生成，或者从缓存加载碎片失败
        if settings.REGENERATE_PIECES or not fragments_loaded_from_cache:
            # 从原始图片文件处理生成碎片和缩略图
            # print(f"  图片ID {image_id}: { '重新生成' if settings.REGENERATE_PIECES else '缓存加载失败'}，开始裁剪和分割...") # Debug

            try:
                original_img_pg = pygame.image.load(filepath).convert_alpha()
            except pygame.error as e:
                 print(f"错误: Pygame无法加载原始图片 {filepath}: {e}")
                 # 返回 False 标记处理失败
                 return False

            # 处理图片尺寸 (缩放和居中裁剪) 到目标尺寸 (600x1080)
            target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE
            target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE
            target_size = (target_width, target_height)

            processed_img_pg = self._process_image_for_pieces(original_img_pg, target_size)

            # 如果处理后的完整图片有效且尺寸匹配
            if processed_img_pg and processed_img_pg.get_size() == target_size:
                 self.processed_full_images[image_id] = processed_img_pg # 存储处理后的完整图片
                 processed_full_image_available = True

                 # 尝试分割碎片 surface
                 pieces_for_this_image = self._split_image_into_pieces(processed_img_pg)

                 # 如果碎片成功生成且数量正确
                 if pieces_for_this_image and len(pieces_for_this_image) == settings.PIECES_PER_IMAGE:
                     self.pieces_surfaces[image_id] = pieces_for_this_image # 存储碎片 surface 字典
                     # 尝试保存碎片到缓存 (只保存碎片)
                     self._save_pieces_to_cache(image_id)
                 else:
                      print(f"警告: 图片ID {image_id} 碎片分割数量不完整 ({len(pieces_for_this_image) if pieces_for_this_image else 0}/{settings.PIECES_PER_IMAGE})。")
                      # 不完整的碎片不存储到 self.pieces_surfaces
                      # self.pieces_surfaces[image_id] = {} # Ensure no incomplete entry


            else:
                 print(f"警告: 图片ID {image_id} 处理后图片无效或尺寸不符 ({processed_img_pg.get_size() if processed_img_pg else 'None'} vs {target_size})。无法分割碎片。")
                 processed_full_image_available = False # 标记处理后完整图不可用
                 # 此时碎片和缩略图都无法从这里生成


        # 如果碎片已经通过生成或缓存加载到 self.pieces_surfaces 了
        pieces_are_ready = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == settings.PIECES_PER_IMAGE)

        # 检查缩略图是否已经缓存，如果没有且处理后的完整图可用，则生成缩略图并缓存
        thumbnails_already_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                     image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)

        if not thumbnails_already_cached and processed_full_image_available:
            # Processed full image is available, but thumbnails are missing, generate them
            # print(f"  图片ID {image_id}: 生成并缓存缩略图...") # Debug
            try:
                processed_img_pg_for_thumb = self.processed_full_images[image_id] # 获取已缓存的处理后完整图
                thumbnail = pygame.transform.scale(processed_img_pg_for_thumb, (settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT))
                unlit_thumbnail = utils.grayscale_surface(thumbnail) # Generate grayscale version <--- 调用 utils.grayscale_surface
                self.cached_thumbnails[image_id] = thumbnail
                self.cached_unlit_thumbnails[image_id] = unlit_thumbnail
                thumbnails_are_ready = True
            except Exception as e: # 捕获生成缩略图和灰度化过程中的任何异常 (包括 NameError)
                print(f"警告: 图片ID {image_id} 缩略图生成或灰度化失败: {e}.") # Debug
                thumbnails_are_ready = False
                # Clear potential incomplete thumbnail entries
                if image_id in self.cached_thumbnails: del self.cached_thumbnails[image_id]
                if image_id in self.cached_unlit_thumbnails: del self.cached_unlit_thumbnails[image_id]

        elif thumbnails_already_cached:
             # Thumbnails were already in cache
             thumbnails_are_ready = True
        else:
             # Thumbnails were not cached and processed full image wasn't available to generate them
             thumbnails_are_ready = False


        # This image is considered successfully processed only if BOTH pieces AND thumbnails are ready
        final_success = pieces_are_ready and thumbnails_are_ready

        # Note: _update_loaded_count is called externally after batches are processed.

        return final_success # 返回处理是否成功 (碎片和缩略图都已准备)


    def load_next_batch_background(self, batch_size):
        """
        加载并处理下一个批次的未处理图片。
        优先处理高优先级队列中的图片 (存档加载后的未点亮/已点亮图片)。
        返回本批次成功处理 (碎片和缩略图都已就绪) 的图片数量。
        Args:
            batch_size (int): 本次尝试处理的图片数量。

        Returns:
            int: 实际成功处理的图片数量。
        """
        # Check if all images are fully processed
        if self.is_loading_finished():
             # print("后台加载：所有图片已加载完成。") # Debug, avoid spamming
             return 0

        processed_count_this_batch = 0
        batch_processed_attempts = 0 # Counter for how many images we attempted to process in this batch

        # Process images from the high-priority queue first
        while self._high_priority_load_queue and batch_processed_attempts < batch_size:
            image_id = self._high_priority_load_queue.popleft() # Get from high-priority queue

            # Check if this image is still not fully processed (pieces OR thumbnails missing)
            pieces_loaded = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == settings.PIECES_PER_IMAGE)
            thumbnails_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                 image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)

            if not pieces_loaded or not thumbnails_cached:
                 # Process the image
                 success = self._load_and_process_single_image(image_id) # Returns success for pieces AND thumbnails
                 if success:
                     processed_count_this_batch += 1
                     # print(f"  后台加载 (高优先级) 成功处理图片ID {image_id}") # Debug
                 else:
                     print(f"警告: 后台加载 (高优先级) 图片ID {image_id} 处理失败。")
                 batch_processed_attempts += 1 # Count this as one attempt

            # else: print(f"图片ID {image_id} 已在高优先级队列中处理完成，跳过。") # Debug


        # If high-priority queue is empty or batch_size is not met, process from the normal queue
        while self._normal_load_queue and batch_processed_attempts < batch_size:
            image_id = self._normal_load_queue.popleft() # Get from normal queue

            # Check if this image is still not fully processed
            pieces_loaded = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == settings.PIECES_PER_IMAGE)
            thumbnails_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                 image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)


            if not pieces_loaded or not thumbnails_cached:
                 # Process the image
                 success = self._load_and_process_single_image(image_id) # Returns success for pieces AND thumbnails
                 if success:
                     processed_count_this_batch += 1
                     # print(f"  后台加载 (普通优先级) 成功处理图片ID {image_id}") # Debug
                 else:
                     print(f"警告: 后台加载 (普通优先级) 图片ID {image_id} 处理失败。")
                 batch_processed_attempts += 1 # Count this as one attempt

            # else: print(f"图片ID {image_id} 已在普通队列中处理完成，跳过。") # Debug


        # After processing the batch, update the total loaded count
        self._update_loaded_count()
        # print(f"后台加载批次处理完成。已成功处理图片数量更新为: {self._loaded_image_count}/{self._total_image_count}") # Debug

        return processed_count_this_batch # Return the number of images successfully processed in *this batch*


    def _update_loaded_count(self):
         """重新计算并更新 _loaded_image_count (完整加载碎片和缩略图的图片数量)。"""
         loaded_count_now = 0
         for img_id in self.all_image_files:
             pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == settings.PIECES_PER_IMAGE)
             thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                  img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)
             if pieces_loaded and thumbnails_cached:
                 loaded_count_now += 1

         self._loaded_image_count = loaded_count_now


    def is_initial_load_finished(self):
        """检查初始设定的图片数量是否已加载完成 (即前 settings.INITIAL_LOAD_IMAGE_COUNT 张图片的碎片和缩略图是否已准备好)。"""
        all_image_ids = sorted(self.all_image_files.keys())
        # 确定初始应该加载处理的图片ID列表
        initial_load_ids = all_image_ids[:min(settings.INITIAL_LOAD_IMAGE_COUNT, len(all_image_ids))]

        for img_id in initial_load_ids:
             # Check if pieces AND thumbnails are loaded for this image
             pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == settings.PIECES_PER_IMAGE)
             thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                  img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)

             if not pieces_loaded or not thumbnails_cached:
                 # print(f"Initial load check: Image ID {img_id} pieces or thumbnails not loaded/complete.") # Debug
                 return False # Initial load batch is not fully ready

        # print("Initial load batch (pieces and thumbnails) is ready.") # Debug
        return True


    def is_loading_finished(self):
        """检查是否所有扫描到的原始图片都已加载和处理（即全部碎片surface和缩略图已生成）。"""
        # Checks if the number of images with full pieces AND cached thumbnails equals total scanned count
        # print(f"Checking total load status: Loaded {self._loaded_image_count} / Total {self._total_image_count}") # Debug
        return self._loaded_image_count >= self._total_image_count


    def get_loading_progress(self):
         """返回当前加载进度信息，例如 '5/10'。"""
         return f"{self._loaded_image_count}/{self._total_image_count}"

    def get_loading_progress_percentage(self):
         """返回当前加载进度百分比 (0.0 to 1.0)。"""
         if self._total_image_count == 0:
              return 1.0 # No images, consider loaded
         return self._loaded_image_count / self._total_image_count


    def _process_image_for_pieces(self, image_surface_pg, target_size):
        """
        Scales and center crops a Pygame Surface to the target size (600x1080).
        Uses PIL if available for potentially better quality.
        Returns the processed Pygame Surface or None if failed.
        Target size is (IMAGE_LOGIC_COLS * PIECE_SIZE, IMAGE_LOGIC_ROWS * PIECE_SIZE).
        """
        if not PIL_AVAILABLE:
            # print("Warning: PIL not installed, using Pygame for processing.")
            return self._process_image_with_pygame(image_surface_pg, target_size)
        else:
             # print("Using PIL for processing.")
             return self._process_image_with_pil(image_surface_pg, target_size)


    def _process_image_with_pygame(self, image_surface_pg, target_size):
        """使用Pygame进行缩放和裁剪。"""
        img_w, img_h = image_surface_pg.get_size()
        target_w, target_h = target_size # target_w = 600, target_h = 1080

        if img_h == 0 or target_h == 0:
             print("警告: 图像高度或目标高度为0，无法计算比例。")
             return None

        img_aspect = img_w / img_h
        target_aspect = target_w / target_h # Target aspect is 600 / 1080 = 9 / 16

        # 计算缩放后的尺寸
        # Keep original aspect ratio, scale to fit or exceed one target dimension
        if img_aspect > target_aspect: # Original is wider (e.g., 16:9), scale to target height
            scaled_h = target_h
            scaled_w = int(scaled_h * img_aspect)
        else: # Original is taller (e.g., 9:16) or similar aspect, scale to target width
            scaled_w = target_w
            scaled_h = int(scaled_w / img_aspect)

        # Ensure scaled dimensions are valid and large enough for the target area
        if scaled_w < target_w or scaled_h < target_h or scaled_w <= 0 or scaled_h <= 0:
            print(f"警告: Pygame缩放尺寸计算异常，原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}, 缩放 {scaled_w}x{scaled_h}. 返回None.")
            return None


        try:
             # Scale
             scaled_img_pg = pygame.transform.scale(image_surface_pg, (scaled_w, scaled_h))
        except pygame.error as e:
             print(f"警告: Pygame缩放失败: {e}。返回None。")
             return None


        # Calculate crop area
        crop_width = target_w
        crop_height = target_h
        crop_x = (scaled_w - crop_width) // 2
        crop_y = (scaled_h - crop_height) // 2

        # Ensure crop area is valid
        if crop_x < 0 or crop_y < 0 or crop_x + crop_width > scaled_w or crop_y + crop_height > scaled_h:
             print(f"警告: Pygame裁剪区域 ({crop_x},{crop_y},{crop_width},{crop_height}) 超出缩放图片范围 ({scaled_w}x{scaled_h})，返回None。")
             return None

        try:
            # Use Pygame subsurface for cropping and copy
            cropped_img_pg = scaled_img_pg.subsurface((crop_x, crop_y, crop_width, crop_height)).copy()
            return cropped_img_pg
        except ValueError as e:
             print(f"警告: Pygame subsurface 失败: {e}. 返回None。")
             return None


    def _process_image_with_pil(self, image_surface_pg, target_size):
        """使用Pillow进行缩放和裁剪。"""
        if not PIL_AVAILABLE:
             print("错误: PIL未安装，无法使用PIL处理图片。")
             return None # Should not reach here

        try:
            # Convert Pygame Surface to PIL Image
            mode = "RGBA" if image_surface_pg.get_flags() & pygame.SRCALPHA else "RGB"
            try:
                pil_img = Image.frombytes(mode, image_surface_pg.get_size(), pygame.image.tostring(image_surface_pg, mode))
            except Exception as e:
                 print(f"警告: Pygame tostring failed for PIL conversion: {e}. Returning None.")
                 return None # Fail conversion if tostring fails

            img_w, img_h = pil_img.size
            target_w, target_h = target_size # target_w = 600, target_h = 1080

            if img_h == 0 or target_h == 0:
                 print("警告: 图像高度或目标高度为0，无法计算比例。")
                 return None

            img_aspect = img_w / img_h
            target_aspect = target_w / target_h # Target aspect is 600 / 1080 = 9 / 16

            if img_aspect > target_aspect: # Original is wider (e.g., 16:9), scale to target height
                scaled_h = target_h
                scaled_w = int(scaled_h * img_aspect)
            else: # Original is taller (e.g., 9:16) or similar aspect, scale to target width
                scaled_w = target_w
                scaled_h = int(scaled_w / img_aspect)

            # Ensure scaled dimensions are valid and large enough for the target crop
            if scaled_w < target_w or scaled_h < target_h or scaled_w <= 0 or scaled_h <= 0:
                 print(f"警告: PIL缩放尺寸计算异常，原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}, 缩放 {scaled_w}x{scaled_h}. 返回None.")
                 return None

            try:
                 # PIL resize (using a high quality filter like LANCZOS)
                 scaled_pil_img = pil_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            except Exception as e:
                 print(f"警告: PIL缩放失败: {e}. 返回None.")
                 return None


            # Calculate crop area
            crop_width = target_w
            crop_height = target_h
            crop_x = (scaled_w - crop_width) // 2
            crop_y = (scaled_h - crop_height) // 2

            # Ensure crop area is valid
            if crop_x < 0 or crop_y < 0 or crop_x + crop_width > scaled_w or crop_y + crop_height > scaled_h:
                 print(f"警告: PIL裁剪区域 ({crop_x},{crop_y},{crop_width},{crop_height}) 超出缩放图片范围 ({scaled_w}x{scaled_h})，返回None。")
                 return None

            try:
                 cropped_pil_img = scaled_pil_img.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
            except Exception as e:
                 print(f"警告: PIL裁剪失败: {e}. 返回None.")
                 return None


            # Convert PIL Image back to Pygame Surface
            if cropped_pil_img.mode != 'RGBA':
                 cropped_pil_img = cropped_pil_img.convert('RGBA')
            # Use pygame.image.fromstring to create Pygame Surface
            try:
                 pygame_surface = pygame.image.fromstring(cropped_pil_img.tobytes(), cropped_pil_img.size, "RGBA")
                 return pygame_surface
            except Exception as e:
                 print(f"警告: PIL to Pygame conversion failed: {e}. 返回None.")
                 return None

        except Exception as e:
            # Catch any other unexpected exceptions during PIL processing
            print(f"错误: 使用PIL处理图片时发生未知错误: {e}. 返回None.")
            return None


    def _split_image_into_pieces(self, processed_image_surface):
        """
        Splits the processed image into piece surfaces based on logical dimensions (5 cols x 9 rows).
        Returns a dictionary { (row, col): pygame.Surface } or None if splitting fails.
        Expected input processed_image_surface size is (IMAGE_LOGIC_COLS * PIECE_SIZE, IMAGE_LOGIC_ROWS * PIECE_SIZE),
        which is (600, 1080).
        """
        img_w, img_h = processed_image_surface.get_size()
        piece_w, piece_h = settings.PIECE_SIZE, settings.PIECE_SIZE

        expected_w = settings.IMAGE_LOGIC_COLS * piece_w # 5 * 120 = 600
        expected_h = settings.IMAGE_LOGIC_ROWS * piece_h # 9 * 120 = 1080

        if img_w != expected_w or img_h != expected_h:
            # This check theoretically should be handled in _process_image_for_pieces
            print(f"错误: 处理后的图片尺寸 {img_w}x{img_h} 与预期 {expected_w}x{expected_h} 不符。无法分割碎片。")
            return None # Size mismatch, cannot split

        pieces_dict = {} # Store pieces for this image

        # Iterate through the logical grid (rows x cols) to extract pieces
        # Iterate through Rows first (0 to 8), then Columns (0 to 4)
        for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
            for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                x = c * piece_w # Calculate x-coordinate for the piece (Col affects X)
                y = r * piece_h # Calculate y-coordinate for the piece (Row affects Y)

                # Ensure extraction area is within the image bounds
                if x >= 0 and y >= 0 and x + piece_w <= img_w and y + piece_h <= img_h:
                    try:
                         # Extract piece surface (subsurface) and copy it
                         piece_surface = processed_image_surface.subsurface((x, y, piece_w, piece_h)).copy()
                         pieces_dict[(r, c)] = piece_surface # Store piece with its logical (row, col)
                    except ValueError as e:
                         print(f"警告: subsurface extraction for piece r{r}_c{c} failed: {e}. Skipping.")
                    except Exception as e:
                        print(f"警告: Extracting piece r{r}_c{c} encountered unknown error: {e}. Skipping.")
                else:
                     print(f"警告: Extraction area ({x},{y},{piece_w},{piece_h}) for piece r{r}_c{c} out of image bounds ({img_w}x{img_h}), skipping.")

        # Check if the correct number of pieces was successfully generated
        if len(pieces_dict) != settings.PIECES_PER_IMAGE:
             print(f"警告: Actual number of pieces generated ({len(pieces_dict)}) does not equal expected number ({settings.PIECES_PER_IMAGE}).")
             # If the count is incorrect, return None, indicating incomplete splitting
             return None

        return pieces_dict # Return dictionary of successfully split pieces


    def _save_pieces_to_cache(self, image_id):
        """Saves piece surfaces for a given image ID to cache files."""
        if image_id not in self.pieces_surfaces or not self.pieces_surfaces[image_id] or len(self.pieces_surfaces[image_id]) != settings.PIECES_PER_IMAGE:
             # print(f"Warning: No complete pieces for image {image_id} to save to cache.")
             return False # No complete pieces to save

        # print(f"Saving pieces for image {image_id} to cache...") # Debug
        os.makedirs(settings.GENERATED_PIECE_DIR, exist_ok=True)

        success_count = 0
        total_pieces = len(self.pieces_surfaces[image_id])

        # Iterate through the logical grid (rows x cols) to save pieces
        for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
            for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                if (r, c) in self.pieces_surfaces[image_id]:
                    piece_surface = self.pieces_surfaces[image_id][(r, c)]
                    filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                    filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                    try:
                         pygame.image.save(piece_surface, filepath)
                         success_count += 1
                    except pygame.error as e:
                         print(f"警告: 无法保存碎片 {filepath} 到缓存: {e}")
                # else: # Should not happen if pieces_surfaces[image_id] is complete

        # print(f"Image {image_id}: {total_pieces} pieces, {success_count} successfully saved to cache.")
        return success_count == total_pieces # Return True only if all pieces were saved


    def _load_pieces_from_cache(self, image_id):
        """Attempts to load piece surfaces for a given image ID from cache files."""
        # print(f"Attempting to load pieces for image {image_id} from cache...") # Debug
        expected_pieces_count = settings.PIECES_PER_IMAGE # 5x9 = 45

        # Quick check: Do all expected piece files exist?
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
             # print(f"  Image {image_id} cache files incomplete or missing, skipping cache load.") # Debug
             return False # Cache files incomplete or missing, return False

        # If files exist, attempt to load them
        # print(f"  Found all {expected_pieces_count} cache files for image {image_id}, starting load...") # Debug
        potential_pieces_surfaces = {} # Temporary dict to store loaded piece surfaces
        loaded_count = 0
        try:
            # Iterate through the logical grid (rows x cols)
            for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
                for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                    filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                    filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                    piece_surface = pygame.image.load(filepath).convert_alpha()
                    # Check size of loaded piece surface
                    if piece_surface.get_size() != (settings.PIECE_SIZE, settings.PIECE_SIZE):
                         print(f"警告: 缓存碎片文件 {filepath} 尺寸不正确 ({piece_surface.get_size()})。缓存加载失败。")
                         potential_pieces_surfaces = {} # Clear incomplete loaded results
                         return False # Mark load failed
                    potential_pieces_surfaces[(r, c)] = piece_surface
                    loaded_count += 1

            # Check if the correct number of pieces was loaded
            if loaded_count == expected_pieces_count:
                # If loading successful, store the temporary dict in self.pieces_surfaces
                self.pieces_surfaces[image_id] = potential_pieces_surfaces
                # print(f"  Successfully loaded {loaded_count} pieces for image {image_id} from cache.") # Debug
                return True # Load successful
            else:
                # This shouldn't normally happen if quick check passes, but indicates inconsistency
                print(f"警告: Number of pieces loaded from cache for image {image_id} is incomplete. Expected {expected_pieces_count}, loaded {loaded_count}. Cache load failed.") # Debug
                potential_pieces_surfaces = {} # Clear incomplete loaded results
                return False

        except pygame.error as e:
             print(f"警告: Pygame error loading pieces from cache for image {image_id}: {e}. Cache load failed.")
             self.pieces_surfaces[image_id] = {} # Ensure entry is cleared or does not exist
             return False
        except Exception as e:
             print(f"警告: Unknown error loading pieces from cache for image {image_id}: {e}. Cache load failed.")
             self.pieces_surfaces[image_id] = {} # Ensure entry is cleared or does not exist
             return False


    def _initialize_consumption(self):
        """确定第一张要消耗碎片的图片ID，并计算初始填充消耗的碎片数量。"""
        # Based on the keys in self.all_image_files (all scanned images)
        all_image_ids = sorted(self.all_image_files.keys())

        if not all_image_ids:
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             print("警告：没有找到任何图片文件，无法初始化碎片消耗机制！") # Debug
             return

        # The image consumption starts from the image after the initial full images batch
        next_consume_img_index_in_all = settings.INITIAL_FULL_IMAGES_COUNT

        if next_consume_img_index_in_all < len(all_image_ids):
            self.next_image_to_consume_id = all_image_ids[next_consume_img_index_in_all]
            # The number of pieces already consumed from this image for the initial fill
            self.pieces_consumed_from_current_image = settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT

            print(f"Initial piece consumption starts from image ID {self.next_image_to_consume_id}. {self.pieces_consumed_from_current_image} pieces already consumed for initial fill.") # Debug
        else:
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             print("警告：All images used for initial fill or not enough images available for subsequent consumption.") # Debug


    def get_initial_pieces_for_board(self):
        """
        获取用于初始棋盘填充的 Piece 对象列表。
        这些碎片来自初始加载批次中已成功加载/处理的图片。
        """
        initial_pieces_list = []
        # Get IDs of images that have successfully loaded/generated their full set of pieces
        image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])

        if not image_ids_with_pieces:
            print("错误: 初始棋盘填充没有可用的碎片表面。")
            return [] # No images with loaded pieces

        # Determine which loaded images should be used for the initial fill candidates
        all_image_ids_ordered = sorted(self.all_image_files.keys())
        initial_fill_candidates_ids = all_image_ids_ordered[:min(settings.INITIAL_FULL_IMAGES_COUNT + (1 if settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT > 0 else 0), len(all_image_ids_ordered))]
        
        # Filter initial fill candidates to only include those with successfully loaded pieces
        initial_fill_images_with_loaded_pieces = [
            img_id for img_id in initial_fill_candidates_ids
            if img_id in image_ids_with_pieces # Check if the image has successfully loaded pieces
        ]
        
        if not initial_fill_images_with_loaded_pieces:
             print("错误: No piece surfaces available for the images intended for initial fill.")
             return []


        pieces_added_count = 0
        
        # Add pieces for the first INITIAL_FULL_IMAGES_COUNT full images (from the list of loaded initial fill candidates)
        num_full_images_added = 0
        for img_id in initial_fill_images_with_loaded_pieces:
            # Stop if we've added enough full images OR if this image is beyond the range for full images in the original list
            if num_full_images_added >= settings.INITIAL_FULL_IMAGES_COUNT or img_id not in all_image_ids_ordered[:settings.INITIAL_FULL_IMAGES_COUNT]:
                break
                
            # Get all pieces for this image (from the loaded pieces_surfaces)
            # Iterate through the logical grid (rows x cols)
            for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
                for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                    # Ensure piece surface exists (should be true if img_id is in image_ids_with_pieces)
                    if (r, c) in self.pieces_surfaces[img_id]:
                        piece_surface = self.pieces_surfaces[img_id][(r, c)]
                        # Create Piece object, initial grid position is -1,-1, Board will assign later
                        initial_pieces_list.append(Piece(piece_surface, img_id, r, c, -1, -1))
                        pieces_added_count += 1
                    # else: print(f"Error: Piece surface {img_id}_{r}_{c} not found in pieces_surfaces.") # Should not happen

            # Set status for these images to 'unlit'
            if img_id in self.image_status:
                 self.image_status[img_id] = 'unlit'
            else:
                 print(f"Warning: Initial fill image ID {img_id} not in image_status list.") # Debug

            num_full_images_added += 1
            
        # Add pieces from the next image (following the Initial_partial_image_pieces_count rule)
        # This image is the first loaded candidate after the full images
        next_partial_img_index_in_candidates = settings.INITIAL_FULL_IMAGES_COUNT
        if next_partial_img_index_in_candidates < len(initial_fill_images_with_loaded_pieces):
             current_consume_img_id = initial_fill_images_with_loaded_pieces[next_partial_img_index_in_candidates]
             
             # Ensure this image's pieces are successfully loaded (already filtered, but safety check)
             if current_consume_img_id in self.pieces_surfaces and self.pieces_surfaces.get(current_consume_img_id) is not None and len(self.pieces_surfaces[current_consume_img_id]) == settings.PIECES_PER_IMAGE:
                  # print(f"Getting first {settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT} pieces from image {current_consume_img_id} for initial fill.") # Debug

                  piece_count_from_current = 0
                  # Iterate through the logical grid (rows x cols) in order
                  total_piece_index_in_img = 0
                  for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
                      for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                          if piece_count_from_current < settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                              # Ensure piece surface exists
                              if (r, c) in self.pieces_surfaces[current_consume_img_id]:
                                  piece_surface = self.pieces_surfaces[current_consume_img_id][(r, c)]
                                  initial_pieces_list.append(Piece(piece_surface, current_consume_img_id, r, c, -1, -1))
                                  pieces_added_count += 1
                                  piece_count_from_current += 1
                                  # self.pieces_consumed_from_current_image += 1 # This count is handled in _initialize_consumption
                              # else: print(f"Error: Piece surface {current_consume_img_id}_{r}_{c} not found in pieces_surfaces.") # Should not happen
                          else:
                              break # Reached specified count
                          total_piece_index_in_img += 1
                      if piece_count_from_current == settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                          break

                  # Set this image's status to 'unlit'
                  if current_consume_img_id in self.image_status:
                      if self.image_status[current_consume_img_id] == 'unentered':
                          self.image_status[current_consume_img_id] = 'unlit'
                  else:
                       print(f"Warning: Initial partial fill image ID {current_consume_img_id} not in image_status list.") # Debug
             # else: print(f"Warning: Image ID {current_consume_img_id} intended for initial partial fill, but pieces not loaded.") # Debug


        print(f"Total pieces obtained for initial fill: {pieces_added_count}") # Debug
        
        # Check against the expected total number of pieces for the board
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS
        if pieces_added_count > total_required_pieces:
             print(f"Error: Number of initial pieces obtained ({pieces_added_count}) > total board slots ({total_required_pieces})! Truncating list.")
             initial_pieces_list = initial_pieces_list[:total_required_pieces] # Truncate to avoid overflow
        elif pieces_added_count < total_required_pieces:
              print(f"Warning: Number of initial pieces obtained ({pieces_added_count}) < total board slots ({total_required_pieces})! Board will have empty slots.")


        # Randomly shuffle the list of pieces
        import random
        random.shuffle(initial_pieces_list)

        return initial_pieces_list


    def get_next_fill_pieces(self, count):
        """
        Gets the next batch of 'count' new Piece objects to fill empty slots, based on the consumption rules.
        These pieces come from **loaded** (including background loaded) images.
        """
        new_pieces = []
        pieces_needed = count
        # Only get pieces from images that have successfully loaded/generated their full set of pieces
        image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])


        # print(f"Need to fill {pieces_needed} slots...") # Debug

        # If no more images to consume, or pieces for the next image are not loaded
        if self.next_image_to_consume_id is None or self.next_image_to_consume_id not in image_ids_with_pieces:
             # print("Warning: No more loaded images available to provide pieces.") # Debug
             return [] # Return empty list

        # Find the logical index of the current image being consumed (within the list of loaded images)
        try:
            current_img_index_in_loaded = image_ids_with_pieces.index(self.next_image_to_consume_id)
        except ValueError:
             print(f"Error: Current consumption image ID {self.next_image_to_consume_id} not in list of loaded piece images.")
             self.next_image_to_consume_id = None # State error, reset
             return []


        # Loop until enough pieces are obtained or no more loaded images are available
        while pieces_needed > 0 and self.next_image_to_consume_id is not None:
            current_img_id = self.next_image_to_consume_id

            # Ensure pieces surface for the current image is loaded and complete (should be true based on check above, but safe)
            if current_img_id not in self.pieces_surfaces or self.pieces_surfaces.get(current_img_id) is not None and len(self.pieces_surfaces.get(current_img_id, {})) != settings.PIECES_PER_IMAGE:
                print(f"Warning: Pieces surface for current consumption image ID {current_img_id} not loaded or incomplete. Stopping getting new pieces.") # Debug
                self.next_image_to_consume_id = None # No loaded pieces available, stop consumption
                break

            total_pieces_in_current_img = settings.PIECES_PER_IMAGE # 45
            pieces_remaining_in_current_img = total_pieces_in_current_img - self.pieces_consumed_from_current_image

            # Calculate how many pieces to take from the current image
            pieces_to_take_from_current = min(pieces_needed, pieces_remaining_in_current_img)

            # print(f"From image {current_img_id}: {pieces_remaining_in_current_img} remaining, attempting to take {pieces_to_take_from_current} this batch.") # Debug

            if pieces_to_take_from_current > 0:
                # Get pieces from the current image, continuing from the last consumed position (logical order)
                pieces_taken_count = 0
                # Calculate starting logical (row, col) based on self.pieces_consumed_from_current_image
                start_total_index = self.pieces_consumed_from_current_image # Total piece index (0-44)

                # Iterate through the logical grid (rows x cols) to find pieces to take
                current_total_index = 0
                found_start = False # Flag to indicate we've passed the start_total_index
                for r in range(settings.IMAGE_LOGIC_ROWS): # Rows (0 to 8)
                    for c in range(settings.IMAGE_LOGIC_COLS): # Columns (0 to 4)
                         if current_total_index >= start_total_index and pieces_taken_count < pieces_to_take_from_current:
                              found_start = True
                              # Ensure piece surface exists (should be true if image is in pieces_surfaces)
                              if (r, c) in self.pieces_surfaces[current_img_id]: # pieces_surfaces[current_img_id] guaranteed non-None and full
                                  piece_surface = self.pieces_surfaces[current_img_id][(r, c)]
                                  new_pieces.append(Piece(piece_surface, current_img_id, r, c, -1, -1)) # -1,-1 initial grid position
                                  pieces_taken_count += 1
                                  self.pieces_consumed_from_current_image += 1 # Mark as consumed
                                  # print(f"  Obtained piece: Image {current_img_id}, Logical Row {r}, Logical Col {c}") # Debug
                              else:
                                   # This shouldn't normally happen if image ID is in pieces_surfaces and marked as complete
                                   print(f"Error: Logical piece ({r},{c}) for image {current_img_id} surface not found, but image marked as complete.") # Debug
                         current_total_index += 1 # Increment total index regardless of whether piece was taken

                         if pieces_taken_count == pieces_to_take_from_current:
                             break # Reached the number of pieces to take from the current image
                    if pieces_taken_count == pieces_to_take_from_current:
                        break # Reached the number of pieces to take from the current image
                    # If we found the start index, haven't taken enough pieces, and there are more rows
                    if found_start and pieces_taken_count < pieces_to_take_from_current and r < settings.IMAGE_LOGIC_ROWS - 1:
                         pass # Continue to the next row


                pieces_needed -= pieces_taken_count
                # print(f"Actually obtained {pieces_taken_count} pieces from image {current_img_id} this batch. {pieces_needed} still needed.") # Debug


            # Check if pieces from the current image are fully consumed
            # Use >= total_pieces_in_current_img for robustness
            if self.pieces_consumed_from_current_image >= total_pieces_in_current_img:
                # print(f"Pieces for image {current_img_id} are fully consumed.") # Debug
                # Switch to the next image that has loaded pieces
                current_img_index_in_loaded += 1
                # Re-get the list of loaded images, in case background loading added new ones
                image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces[img_id]) == settings.PIECES_PER_IMAGE])

                if current_img_index_in_loaded < len(image_ids_with_pieces):
                    self.next_image_to_consume_id = image_ids_with_pieces[current_img_index_in_loaded]
                    self.pieces_consumed_from_current_image = 0 # Reset consumption count
                    # self.image_status[self.next_image_to_consume_id] = 'unlit' # Status set in _initial_load_images
                    # print(f"Next image ID to consume set to: {self.next_image_to_consume_id}") # Debug
                else:
                    self.next_image_to_consume_id = None # No more loaded images available
                    # print("No more loaded images to consume.") # Debug
                # If switched image and pieces_needed > 0, the loop continues to get from the next image

            # If pieces are still needed but no next loaded image is available
            # This condition is checked in the while loop header: next_image_to_consume_id is not None
            # but explicit check here for clarity:
            # if pieces_needed > 0 and self.next_image_to_consume_id is None:
                 # print(f"Warning: Needed {count} pieces, but no more loaded images available. Only obtained {len(new_pieces)}.") # Debug
                 # break # Exit loop


        # New pieces do not need to be shuffled, they are placed based on the order of empty slots
        return new_pieces

# image_manager.py

# ... 其他代码 ...

    def get_thumbnail(self, image_id):
         """
         从缓存获取指定图片ID的普通缩略图surface，用于图库列表中的已点亮图片。

         Args:
             image_id (int): 图片ID。

         Returns:
             pygame.Surface or None: 缓存的普通缩略图surface，或None如果不存在。
         """
         # 直接从缓存获取普通缩略图
         thumbnail = self.cached_thumbnails.get(image_id)
         if thumbnail is None:
             # print(f"警告: 图片ID {image_id} 的普通缩略图未找到在缓存中。") # Debug, 避免刷屏
             pass # 警告可能在生成时已打印

         return thumbnail # 返回缓存的普通缩略图或None


    def get_unlit_thumbnail(self, image_id):
         """
         从缓存获取指定图片ID的灰度缩略图surface，用于图库列表中的未点亮图片。

         Args:
             image_id (int): 图片ID。

         Returns:
             pygame.Surface or None: 缓存的灰度缩略图surface，或None如果不存在。
         """
         # 直接从缓存获取灰度缩略图
         unlit_thumbnail = self.cached_unlit_thumbnails.get(image_id)
         if unlit_thumbnail is None:
             # print(f"警告: 图片ID {image_id} 的灰度缩略图未找到在缓存中。") # Debug, 避免刷屏
             pass # 警告可能在生成时已打印

         return unlit_thumbnail # 返回缓存的灰度缩略图或None


    def get_full_processed_image(self, image_id):
         """
         从缓存获取指定图片ID的完整处理后surface (缩放裁剪到 600x1080)。
         用于图库大图查看。

         Args:
             image_id (int): 图片ID。

         Returns:
             pygame.Surface or None: 缓存的完整处理后surface，或None如果不存在。
         """
         # 只有当图片的全部碎片和缩略图已成功加载时，其完整处理后的图片才可能在 processed_full_images 中
         # 但为了图库大图显示，即使碎片未加载完，只要完整处理图在缓存，就应该能显示
         # 我们在 _load_and_process_single_image 中处理了获取完整图并缓存的逻辑
         full_image = self.processed_full_images.get(image_id)
         if full_image is None:
             # print(f"警告: 图片ID {image_id} 的完整处理后图片未找到在缓存中。") # Debug, 避免刷屏
             pass # 警告可能在生成时已打印

         return full_image # 返回缓存的完整处理后图片或None

    # ... (后续方法保持不变) ...

    def get_all_entered_pictures_status(self):
        """
        获取所有已“入场”（状态不等于 'unentered'）图片的状态（未点亮/已点亮）和完成时间。
        此列表供图库使用。
        包含一个标志 'is_ready_for_gallery'，用于指示图片的碎片和缩略图是否已准备好。
        """
        status_list = []
        # 确保迭代顺序与图片ID顺序一致
        all_image_ids = sorted(self.all_image_files.keys())
        print(f"图片ID列表: {all_image_ids}") # Debug
        #图片ID列表: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for img_id in all_image_ids:
            print(f"检查图片ID: {img_id}") # Debug
            # 检查图片ID: 1
            # 检查图片ID: 2
            # 检查图片ID: 3
            # 检查图片ID: 4            
            print(f"图片ID {img_id} 的状态: {self.image_status}") # Debug
            status = self.image_status.get(img_id, 'unentered')
            # status = self.image_status.get(img_id, 'lit')
            # 图库应仅显示状态为 'unlit' 或 'lit' 的图片
            # print(f"图片ID {img_id} 的状态: {status2}") # Debug
            print(f"图片ID {img_id} 的状态: {status}") # Debug
            if status in ['unlit', 'lit']:
                status_info = {'id': img_id, 'state': status}
                print(f"图片ID {img_id} 的状态?: {status}") # Debug
                if status == 'lit':
                    # 获取完成时间，若不存在则使用当前时间作为备用（正常情况下不应发生）
                    status_info['completion_time'] = self.completed_times.get(img_id, time.time())
                # 添加一个标志，指示图片的碎片和缩略图是否已加载（图库缩略图/大图查看需要）
                pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == settings.PIECES_PER_IMAGE)
                thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                     img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)
                status_info['is_ready_for_gallery'] = pieces_loaded and thumbnails_cached  # 图库显示/启用图片的标志

                status_list.append(status_info)
        print(f"获取到 {len(status_list)} 张图片的状态信息，其中包括 {sum(1 for s in status_list if s['is_ready_for_gallery'])} 张准备好的图片。") # Debug
        print(f"状态信息示例: {status_list[:5]}") # 打印前5条状态信息以检查其结构和内容 # Debug, 避免刷屏
        # return status_list # 返回图片状态列表，包括 'id', 'state', 'completion_time', 'is_ready_for_gallery'

        return status_list

    def set_image_state(self, image_id, state):
        """
        Sets the completion state for a given image.

        Args:
            image_id (int): Image ID
            state (str): New state ('unentered', 'unlit', 'lit')
        """
        # Only update state if the image ID is known to the ImageManager (scanned file)
        if image_id in self.all_image_files:
            old_status = self.image_status.get(image_id, 'unentered')
            self.image_status[image_id] = state
            # print(f"Image {image_id} status change: {old_status} -> {state}") # Debug
            if state == 'lit' and old_status != 'lit':
                 # If status changes from non-lit to lit, record completion time
                 self.completed_times[image_id] = time.time() # Record completion time
        else:
             print(f"警告: Attempted to set state {state} for unknown image ID {image_id}.")


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
        # Note: self.all_image_files is based on file scan, no need to save.
        # Processed surfaces and cached thumbnails are runtime assets, not saved.
        return state


    def load_state(self, state_data):
        """
        从存档数据加载ImageManager的状态。
        加载完成后，会将所有未点亮和已点亮图片的ID添加到高优先级加载队列。

        Args:
            state_data (dict): 从存档文件中读取的状态字典。
        """
        if not state_data:
            print("警告: ImageManager 尝试从空的存档数据加载状态。")
            return # 没有有效的存档数据，不加载

        print("ImageManager 从存档加载状态...") # Debug

        # 临时存储从存档加载到的状态，以便后续使用
        print(f"state_data 的值为: {state_data}")
        loaded_image_status = state_data.get('image_status', {})
        print(f"从存档数据中获取的 loaded_image_status 的值为: {loaded_image_status}")
        loaded_completed_times = state_data.get('completed_times', {})
        loaded_next_image_to_consume_id = state_data.get('next_image_to_consume_id', None)
        loaded_pieces_consumed = state_data.get('pieces_consumed_from_current_image', 0)

        # --- **关键调试：打印从存档中加载到的 image_status 字典** ---
        print(f"ImageManager: 存档中的 image_status 数据 (原始): {loaded_image_status}") # Debug <-- 修改打印信息


        # --- **关键修改：从存档加载 image_status 并转换为整数键** ---
        # 遍历 ImageManager 扫描到的所有现有图片的整数ID
        self.image_status = {} # Start with an empty dictionary for current status
        loaded_status_count = 0 # Debug counter

        # 遍历扫描到的所有图片的整数 ID
        for img_id in self.all_image_files.keys():
            # 检查存档数据中是否有对应的状态（使用字符串键查找）
            img_id_str = str(img_id) # 获取对应的字符串键
            if img_id_str in loaded_image_status:
                status = loaded_image_status[img_id_str]
                # 检查加载的状态是否是有效的状态
                if status in ['unentered', 'unlit', 'lit']:
                    self.image_status[img_id] = status # <-- **使用整数 ID 存储到 self.image_status**
                    loaded_status_count += 1
                # else: print(f"警告: Image ID {img_id} 在存档中的状态 '{status}' 无效。") # Debug invalid status
            # else: print(f"Debug: Image ID {img_id} 未在存档状态中找到。状态保持为初始化时的 'unentered'。") # Debug missing in save

        # 如果存档数据中包含的图片ID超出了当前扫描到的范围，这些状态将被忽略，这是期望的行为。
        # 反过来，如果当前扫描到的图片ID没有在存档中，它们的状态保持为初始化时的 'unentered'。


        # --- **关键调试：打印加载并过滤后的 image_status 字典** ---
        print(f"ImageManager 从存档加载并过滤后，当前 image_status 包含 {loaded_status_count} 张图片的状态。具体状态如下: {self.image_status}")  # Debug <-- 修改打印信息

        # 确保只加载状态为 lit 的图片的完成时间，且图片ID存在于已加载状态中
        self.completed_times = {} # Start with an empty dictionary for current completed times
        loaded_completed_count = 0 # Debug counter
        # 遍历存档中的 completed_times 字典 (键是字符串)
        for img_id_str, comp_time in loaded_completed_times.items():
            try:
                img_id = int(img_id_str) # 尝试将字符串键转换为整数
                # 检查转换后的整数ID是否存在于当前加载的状态中，并且状态是 'lit'
                if img_id in self.image_status and self.image_status.get(img_id) == 'lit':
                    self.completed_times[img_id] = comp_time # <-- **使用整数 ID 存储完成时间**
                    loaded_completed_count += 1
                # else: print(f"Debug: Completed time for image ID {img_id} in save but not in loaded image_status or status not 'lit'.") # Debug
            except ValueError:
                 print(f"警告: 存档中的 completed_times 键 '{img_id_str}' 不是有效的整数ID。") # Debug invalid key

        print(f"ImageManager 从存档加载了 {loaded_completed_count} 张已点亮图片的完成时间。") # Debug


        # 加载碎片消耗进度
        # Handle potential string or integer ID in save
        loaded_next_id_int = None
        if loaded_next_image_to_consume_id is not None:
             try:
                 loaded_next_id_int = int(loaded_next_image_to_consume_id)
             except ValueError:
                 print(f"警告: 存档中的 next_image_to_consume_id ({loaded_next_image_to_consume_id}) 无法转换为整数。") # Debug

        if loaded_next_id_int is None or loaded_next_id_int in self.all_image_files:
            self.next_image_to_consume_id = loaded_next_id_int # Store as integer
            print(f"ImageManager 从存档加载 next_image_to_consume_id: {self.next_image_to_consume_id}") # Debug
        else:
            print(f"警告: 存档中的 next_image_to_consume_id ({loaded_next_image_to_consume_id}) 不是已知图片ID。重新初始化消耗状态。") # Debug
            self._initialize_consumption() # Re-initialize consumption state based on file scan


        # Ensure loaded consumed_count is within valid range (0 to settings.PIECES_PER_IMAGE)
        if 0 <= loaded_pieces_consumed <= settings.PIECES_PER_IMAGE:
            self.pieces_consumed_from_current_image = loaded_pieces_consumed
            print(f"ImageManager 从存档加载 pieces_consumed_from_current_image: {self.pieces_consumed_from_current_image}") # Debug
        else:
            print(f"警告: 存档中的 pieces_consumed_from_current_image ({loaded_pieces_consumed}) 无效。重新初始化消耗数量。") # Debug
            if self.next_image_to_consume_id is not None:
                 self.pieces_consumed_from_current_image = 0 # Reset to 0 if invalid
            else:
                 self.pieces_consumed_from_current_image = 0


        # === 填充高优先级加载队列 ===
        # 将所有在加载并过滤后状态是 'unlit' 或 'lit' 的图片ID添加到高优先级队列
        # 这些图片需要在游戏启动后优先加载资源，以便尽快在拼盘或图库中显示
        print("填充高优先级加载队列...") # Debug
        self._high_priority_load_queue.clear() # Clear any previous high-priority items

        # Iterate through the populated self.image_status dictionary (which now contains filtered states from the save, keys are integers)
        high_priority_count = 0 # Debug counter
        for img_id, status in self.image_status.items(): # Use the populated self.image_status (keys are integers)
             if status in ['unlit', 'lit']:
                 # Check if this image is NOT already fully processed in the current session's memory
                 # (Unlikely at this stage for these images from save, but safety check)
                 pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == settings.PIECES_PER_IMAGE)
                 thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                      img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)

                 if not pieces_loaded or not thumbnails_cached:
                     # If not fully processed, add to the high-priority queue
                     # Add to the right (end) of the deque
                     self._high_priority_load_queue.append(img_id) # Add integer ID to deque
                     high_priority_count += 1
                     # Ensure it's removed from the normal queue if it was there
                     # Removing integer from normal queue which contains integers
                     if img_id in self._normal_load_queue:
                         try:
                             self._normal_load_queue.remove(img_id)
                         except ValueError:
                             pass # Not in normal queue


        print(f"高优先级加载队列包含 {high_priority_count} 张图片 (需要加载资源)。") # Debug