# image_manager.py
# 负责图片的加载、处理、碎片生成、管理图片状态和提供碎片/完整图资源

from operator import truediv
import pygame
import settings
import os
import time
import math # 用于计算加载进度百分比
import collections # 导入 collections 模块用于 deque
from piece import Piece # Piece 类可能在 ImageManager 中创建实例，所以需要导入
import utils # 导入工具函数模块

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    print("警告: Pillow库未安装。部分图像处理功能可能受限。建议安装: pip install Pillow")
    PIL_AVAILABLE = False


class ImageManager:
    def __init__(self, game):
        """
        初始化图像管理器。扫描图片文件，建立加载队列，执行初始加载批次，并设置初始图片状态。

        Args:
            game (Game): Game实例，用于在加载时显示加载界面 (可选)。
        """
        self.game = game # 持有Game实例的引用

        self.image_status = {} # 存储每张图片的状态 {id: 'unentered' / 'unlit' / 'lit'} - 必须在扫描前初始化

        # 存储所有原始图片文件的信息 {id: filepath}
        self.all_image_files = {} # {image_id: full_filepath}
        # 存储每张图片的逻辑尺寸 {id: (logic_cols, logic_rows)}
        self.image_logic_dims = {}
        self._scan_image_files() # 扫描图片文件，获取所有图片ID、路径和逻辑尺寸 (现在 self.image_status 已经存在)

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

        # 跟踪碎片消耗进度 (用于填充空位)
        self.next_image_to_consume_id = None # 当前正在消耗碎片的图片ID
        self.pieces_consumed_from_current_image = 0 # 当前正在消耗的图片已消耗的碎片数量
        self._current_consume_img_total_pieces = 0 # 当前正在消耗的图片的总碎片数量


        # === 初始化时填充加载队列 ===
        self._populate_load_queues()


        # 执行初始加载批次 (从队列中取前 settings.INITIAL_LOAD_IMAGE_COUNT 个处理)
        # 这会在 Board 初始化前完成，确保 Board 需要的碎片可用
        self._process_initial_load_batch(settings.INITIAL_LOAD_IMAGE_COUNT)

        # 初始化碎片消耗机制，基于**所有**扫描到的有效图片ID列表
        # 如果加载了存档状态，load_state 会覆盖这些值
        self._initialize_consumption()


        print(f"ImageManager 初始化完成。总图片文件数: {self._total_image_count}，初始加载成功图片数: {self._loaded_image_count}") # 调试信息


    def _scan_image_files(self):
        """扫描 assets 目录，找到所有符合 image_N.png 命名规则的图片文件路径和ID，并初始化状态。获取每张图片的逻辑尺寸。"""
        image_files = [f for f in os.listdir(settings.ASSETS_DIR) if f.startswith("image_") and f.endswith(".png")]
        # 按图片ID排序
        image_files.sort(key=lambda f: int(os.path.splitext(f)[0].replace("image_", "")))

        for filename in image_files:
            try:
                # 从文件名中提取图片ID (整数)
                image_id = int(os.path.splitext(filename)[0].replace("image_", ""))
                full_path = os.path.join(settings.ASSETS_DIR, filename)
                # print(f"扫描到图片文件: {filename} (ID: {image_id})") # Debug

                # === 获取并存储每张图片的逻辑尺寸 ===
                if image_id in settings.IMAGE_LOGIC_DIMS:
                    logic_c, logic_r = settings.IMAGE_LOGIC_DIMS[image_id]
                    # 验证逻辑尺寸是否有效 (非负)
                    if logic_c > 0 and logic_r > 0:
                        self.all_image_files[image_id] = full_path
                        self.image_logic_dims[image_id] = (logic_c, logic_r)
                        # print(f"图片ID {image_id} 逻辑尺寸: {logic_c}x{logic_r}") # Debug
                    else:
                         print(f"警告: ImageManager: _scan_image_files: 图片ID {image_id} 在 IMAGE_LOGIC_DIMS 中的逻辑尺寸 ({logic_c},{logic_r}) 无效。忽略此图片。")
                         # 如果逻辑尺寸无效，不添加到 all_image_files，后续不会处理
                         continue # 跳过处理该无效图片
                else:
                     print(f"警告: ImageManager: _scan_image_files: 图片ID {image_id} 未在 IMAGE_LOGIC_DIMS 中配置逻辑尺寸。忽略此图片。")
                     # 如果未配置，不添加到 all_image_files，后续不会处理
                     continue # 跳过处理该未配置图片


                # 所有扫描到的图片初始状态都是 'unentered'
                if image_id not in self.image_status: # 避免重复扫描时覆盖状态
                    self.image_status[image_id] = 'unentered'

            except ValueError:
                print(f"警告: ImageManager: _scan_image_files: 文件名格式不正确，无法提取图片ID: {filename}")
            except Exception as e:
                print(f"警告: ImageManager: _scan_image_files: 扫描文件 {filename} 时发生错误: {e}")

        self._total_image_count = len(self.all_image_files) # 更新总图片数量为有效图片数量
        print(f"ImageManager: 扫描并验证了 {self._total_image_count} 张原始图片文件 (根据 IMAGE_LOGIC_DIMS 配置)。") # Debug


    def _populate_load_queues(self):
        """初始化填充加载队列，包含所有有效图片ID。"""
        # 获取所有有效图片ID（已在 _scan_image_files 中过滤无效的）
        all_image_ids_ordered = sorted(self.all_image_files.keys())

        # 最初，所有图片的ID都进入普通加载队列
        # 高优先级队列在加载存档状态时填充
        self._normal_load_queue.extend(all_image_ids_ordered)
        print(f"ImageManager: 初始普通加载队列填充完成， {len(self._normal_load_queue)} 张图片进入普通队列。") # Debug


    def _process_initial_load_batch(self, count):
        """从加载队列中处理前 'count' 张图片，用于游戏启动时的初始加载批次。"""
        print(f"ImageManager: 正在处理初始加载批次前 {count} 张图片...") # Debug
        processed_count = 0
        # 从加载队列（优先高优先级）中处理最多 'count' 张图片
        for _ in range(count):
            image_id = None
            # 先从高优先级队列获取
            if self._high_priority_load_queue:
                image_id = self._high_priority_load_queue.popleft()
            # 如果高优先级队列为空，再从普通队列获取
            elif self._normal_load_queue:
                image_id = self._normal_load_queue.popleft()

            if image_id is None:
                break # 所有队列都空了

            # 加载并处理单张图片，包括缓存加载和资源生成 (会更新内部缓存字典)
            # 无论处理是否成功，_load_and_process_single_image 都会尝试加载或生成资源
            self._load_and_process_single_image(image_id)

            # Update processed_count_this_batch? Not needed here, _update_loaded_count handles total.

        # 在整个初始加载批次处理完后，更新已加载计数
        self._update_loaded_count()
        # print(f"ImageManager: 初始加载批次处理完成。") # Debug


    # 替换 _load_and_process_single_image 方法 (使用动态逻辑尺寸)
    def _load_and_process_single_image(self, image_id):
        """
        加载、处理单张原始图片，生成碎片surface，保存到缓存，并生成缩略图缓存。
        如果缓存存在且不重新生成，则从缓存加载。根据图片的逻辑尺寸进行处理。
        这个方法负责确保给定图片ID的碎片和缩略图都已加载到内存缓存。
        这个方法会更新内部缓存字典。它**不**更新 _loaded_image_count，由调用方在批次处理后统一调用 _update_loaded_count。
        Args:
            image_id (int): 要处理的图片ID。

        Returns:
            bool: True 如果成功加载或生成了该图片的全部碎片surface和缩略图，否则返回 False。
        """
        # 确保图片ID有效且已配置逻辑尺寸
        if image_id not in self.all_image_files or image_id not in self.image_logic_dims:
             print(f"警告: ImageManager: _load_and_process_single_image: 图片ID {image_id} 文件或逻辑尺寸配置缺失，无法加载和处理。") # Debug
             return False

        img_logic_c, img_logic_r = self.image_logic_dims[image_id] # Get logic dims
        pieces_per_this_image = img_logic_c * img_logic_r # <-- **关键：动态计算碎片总数**

        # 检查碎片和缩略图是否都已经成功加载/生成并缓存在内存中
        pieces_already_loaded = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == pieces_per_this_image) # <-- 使用动态总数
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

        # Calculate target size based on dynamic logic dimensions and fixed piece size
        target_width = img_logic_c * settings.PIECE_WIDTH
        target_height = img_logic_r * settings.PIECE_HEIGHT
        target_size = (target_width, target_height)


        # If regenerating or cache failed, process from source image file
        if settings.REGENERATE_PIECES or not fragments_loaded_from_cache:
            # From source image file, process to get pieces and thumbnails
            # print(f"  图片ID {image_id}: { '重新生成' if settings.REGENERATE_PIECES else '缓存加载失败'}，开始裁剪和分割...") # Debug

            try:
                original_img_pg = pygame.image.load(filepath).convert_alpha()
            except pygame.error as e:
                 print(f"错误: ImageManager: _load_and_process_single_image: Pygame无法加载原始图片 {filepath}: {e}") # Debug
                 return False # 加载原始图失败，标记处理失败

            # Process image size (scale and center crop) to calculated target_size
            processed_img_pg = self._process_image_for_pieces(original_img_pg, target_size)

            # If processing successful and dimensions match target
            if processed_img_pg and processed_img_pg.get_size() == target_size:
                 self.processed_full_images[image_id] = processed_img_pg # Store processed full image
                 processed_full_image_available = True

                 # Attempt to split into pieces based on dynamic logic dimensions
                 pieces_for_this_image = self._split_image_into_pieces(processed_img_pg, img_logic_r, img_logic_c) # Pass logic dims

                 # If pieces are successfully generated and correct count
                 if pieces_for_this_image and len(pieces_for_this_image) == pieces_per_this_image: # <-- 使用动态总数
                     self.pieces_surfaces[image_id] = pieces_for_this_image # Store piece surfaces

                     # Generate and cache thumbnails from the processed full image
                     try:
                         processed_img_pg_for_thumb = self.processed_full_images[image_id] # Get the available processed image
                         # === 计算缩略图尺寸，根据其逻辑尺寸比例 ===
                         thumb_width = settings.GALLERY_THUMBNAIL_WIDTH
                         # Calculate height based on its own logical ratio and the fixed thumbnail width
                         # Avoid division by zero if logic_c is 0, though _scan_image_files should prevent this
                         thumb_height = int(thumb_width * (img_logic_r / img_logic_c)) if img_logic_c > 0 else settings.GALLERY_THUMBNAIL_WIDTH # Fallback height

                         thumbnail = pygame.transform.scale(processed_img_pg_for_thumb, (thumb_width, thumb_height))
                         unlit_thumbnail = utils.grayscale_surface(thumbnail) # Generate grayscale version
                         self.cached_thumbnails[image_id] = thumbnail
                         self.cached_unlit_thumbnails[image_id] = unlit_thumbnail

                         # Attempt to save pieces to cache (only saves pieces, not thumbnails)
                         self._save_pieces_to_cache(image_id)

                         success = True # Pieces AND thumbnails successfully generated

                     except Exception as e: # Catch any exception during thumbnail generation/grayscaling
                          print(f"警告: ImageManager: _load_and_process_single_image: 图片ID {image_id} 缩略图生成或灰度化失败: {e}.") # Debug
                          success = False # Thumbnail generation failed
                          # Clear potential incomplete thumbnail entries
                          if image_id in self.cached_thumbnails: del self.cached_thumbnails[image_id]
                          if image_id in self.cached_unlit_thumbnails: del self.cached_unlit_thumbnails[image_id]

                 else:
                      print(f"警告: ImageManager: _load_and_process_single_image: 图片ID {image_id} 碎片分割数量不完整 ({len(pieces_for_this_image) if pieces_for_this_image else 0}/{pieces_per_this_image})。") # Debug
                      # Do not store incomplete pieces in self.pieces_surfaces
                      # self.pieces_surfaces[image_id] = {} # Ensure no incomplete entry
                      success = False # Pieces incomplete


            else:
                 print(f"警告: ImageManager: _load_and_process_single_image: 图片ID {image_id} 处理后图片无效或尺寸不符 ({processed_img_pg.get_size() if processed_img_pg else 'None'} vs {target_size})。") # Debug
                 processed_full_image_available = False # Mark processed full image unavailable
                 success = False # Processing failed


        elif fragments_loaded_from_cache:
             # If cache loading was successful for pieces, pieces are in self.pieces_surfaces[image_id]
             # Now, generate and cache thumbnails if they are missing
             thumbnails_already_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                          image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)

             if not thumbnails_already_cached:
                  # Need to load the full image to generate thumbnails
                  if image_id not in self.processed_full_images or not self.processed_full_images.get(image_id):
                       # print(f"  图片ID {image_id}: 从缓存加载碎片成功，需要处理原始图 {os.path.basename(filepath)} 用于图库完整图和缩略图。") # Debug
                       try:
                          original_img_pg = pygame.image.load(filepath).convert_alpha()
                          target_width = img_logic_c * settings.PIECE_WIDTH
                          target_height = img_logic_r * settings.PIECE_HEIGHT
                          processed_img_pg = self._process_image_for_pieces(original_img_pg, (target_width, target_height)) # Process again to get the full processed image
                          if processed_img_pg and processed_img_pg.get_size() == (target_width, target_height):
                              self.processed_full_images[image_id] = processed_img_pg # Store processed full image
                          else:
                               print(f"警告: ImageManager: _load_and_process_single_image: 处理图片 {filepath} 用于图库完整图/缩略图时返回无效 Surface 或尺寸不符。") # Debug
                               processed_img_pg = None # Mark as invalid
                       except pygame.error as e:
                           print(f"错误: ImageManager: _load_and_process_single_image: Pygame无法加载原始图片 {filepath} 用于图库完整图/缩略图: {e}.") # Debug
                           processed_img_pg = None # Mark as invalid
                       except Exception as e:
                           print(f"错误: ImageManager: _load_and_process_single_image: 处理图片 {filepath} 用于图库完整图/缩略图时发生未知错误: {e}.") # Debug
                           processed_img_pg = None # Mark as invalid
                  else:
                       # Full processed image already exists in cache
                       processed_img_pg = self.processed_full_images[image_id]

                  # If processed full image is available, generate thumbnails
                  if processed_img_pg:
                       try:
                           # Thumbnail size calculation uses GALLERY_THUMBNAIL_WIDTH and this image's logical ratio
                           thumb_width = settings.GALLERY_THUMBNAIL_WIDTH
                           # Calculate height based on its own logical ratio and the fixed thumbnail width
                           thumb_height = int(thumb_width * (img_logic_r / img_logic_c)) if img_logic_c > 0 else settings.GALLERY_THUMBNAIL_WIDTH # Fallback height

                           thumbnail = pygame.transform.scale(processed_img_pg, (thumb_width, thumb_height))
                           unlit_thumbnail = utils.grayscale_surface(thumbnail)
                           self.cached_thumbnails[image_id] = thumbnail
                           self.cached_unlit_thumbnails[image_id] = unlit_thumbnail
                           success = True # Pieces were loaded from cache, AND thumbnails were generated
                           thumbnails_are_ready =True # Redundant variable, success handles overall state
                       except Exception as e: # Catch any exception during thumbnail generation/grayscaling
                          print(f"警告: ImageManager: _load_and_process_single_image: 图片ID {image_id} 缩略图生成或灰度化失败: {e}.") # Debug
                          success = False
                          thumbnails_are_ready = False
                          if image_id in self.cached_thumbnails: del self.cached_thumbnails[image_id]
                          if image_id in self.cached_unlit_thumbnails: del self.cached_unlit_thumbnails[image_id]

                  else:
                       # Processed full image was needed for thumbnails but wasn't available/couldn't be generated
                       print(f"警告: ImageManager: _load_and_process_single_image: 无法获取完整处理后图片用于图片ID {image_id} 的缩略图生成。") # Debug
                       success = False # Pieces loaded from cache, but thumbnails failed
                       pieces_are_ready = True # Redundant variable, success handles overall state


             else:
                  # Pieces were loaded from cache, AND thumbnails were already cached
                  success = True # All assets for this image are ready in memory/cache
                  pieces_are_ready = True # Redundant variable, success handles overall state


        # This image is considered successfully processed only if BOTH pieces AND thumbnails are ready
        # final_success = pieces_are_ready and thumbnails_are_ready # Redundant variable, success handles overall state
        final_success = success

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
             return 0

        processed_count_this_batch = 0
        batch_processed_attempts = 0 # Counter for how many images we attempted to process in this batch

        # Process images from the high-priority queue first
        high_priority_list = list(self._high_priority_load_queue) # Make a list to iterate without modifying deque while processing
        for image_id in high_priority_list: # Iterate over a copy
            if batch_processed_attempts >= batch_size: break # Stop if batch size reached

            # Check if this image is still not fully processed (pieces OR thumbnails missing)
            # Get logic dims and dynamic total pieces
            if image_id not in self.image_logic_dims:
                 print(f"警告: 后台加载 (高优先级): 图片ID {image_id} 逻辑尺寸缺失，跳过处理。") # Debug
                 # Remove this invalid ID from the high-priority queue (needs deque manipulation)
                 # Find index and remove, or process from deque one by one
                 # Let's process one by one from deque directly below

                 continue # Skip this image

            img_logic_c, img_logic_r = self.image_logic_dims[image_id] # Get logic dims
            pieces_per_this_image = img_logic_c * img_logic_r # Dynamic total pieces

            pieces_loaded = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == pieces_per_this_image)
            thumbnails_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                 image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)


            if not pieces_loaded or not thumbnails_cached:
                 # Process the image
                 # Take from deque before processing
                 processed_image_id = self._high_priority_load_queue.popleft() # Get from high-priority queue
                 if processed_image_id != image_id: # Should not happen if processing in order
                     print(f"内部警告: ImageManager: 高优先级队列处理顺序不一致。预期ID {image_id}, 实际ID {processed_image_id}") # Debug
                     # Put it back if needed, or handle error
                     self._high_priority_load_queue.appendleft(processed_image_id) # Put it back at the front
                     continue # Skip this iteration


                 success = self._load_and_process_single_image(image_id) # Returns success for pieces AND thumbnails
                 if success:
                     processed_count_this_batch += 1
                     # print(f"  后台加载 (高优先级) 成功处理图片ID {image_id}") # Debug
                 else:
                     print(f"警告: 后台加载 (高优先级) 图片ID {image_id} 处理失败。")
                     # If processing failed, maybe add it back to the *end* of the queue or a failed queue?
                     # For simplicity, let's just print warning and leave it out for now. It might get processed later if added back to normal queue or similar.
                 batch_processed_attempts += 1 # Count this as one attempt

            else: # Already fully loaded, just remove from high-priority queue
                 # Use a try-except in case it was removed by another process/thread (unlikely here but safer)
                 try:
                     self._high_priority_load_queue.remove(image_id)
                     # print(f"Debug: 图片ID {image_id} 已在高优先级队列中处理完成，从队列移除。") # Debug
                 except ValueError:
                      pass # Already removed


        # If high-priority queue is empty or batch_size is not met, process from the normal queue
        normal_priority_list = list(self._normal_load_queue) # Make a list to iterate without modifying deque while processing
        for image_id in normal_priority_list: # Iterate over a copy
             if batch_processed_attempts >= batch_size: break # Stop if batch size reached

             # Check if this image is still not fully processed
             # Get logic dims and dynamic total pieces
             if image_id not in self.image_logic_dims:
                 print(f"警告: 后台加载 (普通优先级): 图片ID {image_id} 逻辑尺寸缺失，跳过处理。") # Debug
                 # Remove this invalid ID from the normal queue
                 try:
                      self._normal_load_queue.remove(image_id)
                 except ValueError:
                      pass
                 continue # Skip this image


             img_logic_c, img_logic_r = self.image_logic_dims[image_id] # Get logic dims
             pieces_per_this_image = img_logic_c * img_logic_r # Dynamic total pieces

             pieces_loaded = (image_id in self.pieces_surfaces and self.pieces_surfaces.get(image_id) is not None and len(self.pieces_surfaces.get(image_id, {})) == pieces_per_this_image)
             thumbnails_cached = (image_id in self.cached_thumbnails and self.cached_thumbnails.get(image_id) is not None and
                                  image_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(image_id) is not None)

             if not pieces_loaded or not thumbnails_cached:
                 # Process the image
                 # Take from deque before processing
                 processed_image_id = self._normal_load_queue.popleft() # Get from normal queue
                 if processed_image_id != image_id: # Should not happen if processing in order
                     print(f"内部警告: ImageManager: 普通优先级队列处理顺序不一致。预期ID {image_id}, 实际ID {processed_image_id}") # Debug
                     self._normal_load_queue.appendleft(processed_image_id) # Put it back at the front
                     continue # Skip this iteration

                 success = self._load_and_process_single_image(image_id) # Returns success for pieces AND thumbnails
                 if success:
                     processed_count_this_batch += 1
                     # print(f"  后台加载 (普通优先级) 成功处理图片ID {image_id}") # Debug
                 else:
                     print(f"警告: 后台加载 (普通优先级) 图片ID {image_id} 处理失败。")
                 batch_processed_attempts += 1 # Count this as one attempt

             else: # Already fully loaded, just remove from normal queue
                 # Use a try-except in case it was removed by another process/thread (unlikely here but safer)
                 try:
                     self._normal_load_queue.remove(image_id)
                     # print(f"Debug: 图片ID {image_id} 已在普通队列中处理完成，从队列移除。") # Debug
                 except ValueError:
                      pass # Already removed


        # After processing the batch, update the total loaded count
        self._update_loaded_count()
        # print(f"后台加载批次处理完成。已成功处理图片数量更新为: {self._loaded_image_count}/{self._total_image_count}") # Debug

        return processed_count_this_batch # Return the number of images successfully processed in *this batch*


    def _update_loaded_count(self):
         """重新计算并更新 _loaded_image_count (完整加载碎片和缩略图的图片数量)。"""
         loaded_count_now = 0
         for img_id in self.all_image_files:
             # Get logic dims for this image to check against total pieces
             if img_id in self.image_logic_dims:
                 img_logic_c, img_logic_r = self.image_logic_dims[img_id]
                 pieces_per_this_image = img_logic_c * img_logic_r # Dynamic total pieces

                 # === 修正：判断碎片是否加载完成时使用动态计算的碎片总数 ===
                 pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == pieces_per_this_image)
                 thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                      img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)
                 if pieces_loaded and thumbnails_cached:
                     loaded_count_now += 1

             # else: print(f"警告: 图片ID {img_id} 逻辑尺寸配置缺失，未计入加载总数。") # Debug


         self._loaded_image_count = loaded_count_now


    def is_initial_load_finished(self):
        """检查初始设定的图片数量是否已加载完成 (即前 settings.INITIAL_LOAD_IMAGE_COUNT 张图片的碎片和缩略图是否已准备好)。"""
        all_image_ids = sorted(self.all_image_files.keys())
        # 确定初始应该加载处理的图片ID列表
        initial_load_ids = all_image_ids[:min(settings.INITIAL_LOAD_IMAGE_COUNT, len(all_image_ids))]

        for img_id in initial_load_ids:
             # Check if pieces AND thumbnails are loaded for this image
             if img_id in self.image_logic_dims: # Ensure logic dims exist
                 img_logic_c, img_logic_r = self.image_logic_dims[img_id]
                 pieces_per_this_image = img_logic_c * img_logic_r # Dynamic total pieces

                 # === 修正：判断碎片是否加载完成时使用动态计算的碎片总数 ===
                 pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == pieces_per_this_image)
                 thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                      img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)

                 if not pieces_loaded or not thumbnails_cached:
                     # print(f"Initial load check: Image ID {img_id} pieces or thumbnails not loaded/complete.") # Debug
                     return False # Initial load batch is not fully ready
             else:
                  # If a required image for initial load is missing logic dims, treat as not loaded
                  print(f"警告: ImageManager: 图片ID {img_id} 需要初始加载，但逻辑尺寸配置缺失。") # Debug
                  return False


        # print("Initial load batch (pieces and thumbnails) is ready.") # Debug
        return True


    def is_high_priority_queue_empty(self):
        """检查高优先级加载队列是否为空。用于存档加载后的状态切换条件。"""
        return not self._high_priority_load_queue # 如果队列为空，返回True


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

    # 重新提供 _process_image_with_pil 方法
    def _process_image_with_pil(self, image_surface_pg, target_size):
        """使用Pillow进行最短边匹配缩放和居中裁剪到目标尺寸。"""
        if not PIL_AVAILABLE:
             print("错误: PIL未安装，无法使用PIL处理图片。")
             return None # Should not reach here

        try:
            # Convert Pygame Surface to PIL Image
            mode = "RGBA" if image_surface_pg.get_flags() & pygame.SRCALPHA else "RGB"
            try:
                pil_img = Image.frombytes(mode, image_surface_pg.get_size(), pygame.image.tostring(image_surface_pg, mode))
            except Exception as e:
                 print(f"警告: PIL转换失败: {e}. 返回None.")
                 return None # Fail conversion if tostring fails

            img_w, img_h = pil_img.size
            target_w, target_h = target_size # target_w = logic_c * piece_w, target_h = logic_r * piece_height

            if img_w <= 0 or img_h <= 0 or target_w <= 0 or target_h <= 0:
                 print(f"警告: PIL裁剪：图像尺寸或目标尺寸无效。原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}. 返回None.")
                 return None


            # Calculate scale factor to match the *shortest* edge and cover the target
            scale_factor = max(target_w / img_w, target_h / img_h)

            # Calculate scaled dimensions
            scaled_w = int(img_w * scale_factor)
            scaled_h = int(img_h * scale_factor)

            # Ensure scaled dimensions are valid and large enough for the target area
            # Note: PIL resize does not guarantee exact integer dimensions after scaling,
            # but crop can handle minor floating point differences.
            # Basic check for scale factor validity
            if scale_factor <= 0:
                 print(f"警告: PIL裁剪：缩放因子 ({scale_factor}) 无效。原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}. 返回None.")
                 return None


            try:
                 # PIL resize (using a high quality filter like LANCZOS)
                 # Use tuple for size
                 scaled_pil_img = pil_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            except Exception as e:
                 print(f"警告: PIL缩放失败: {e}. 返回None.")
                 return None


            # Calculate crop area
            crop_width = target_w
            crop_height = target_h
            crop_x = (scaled_pil_img.size[0] - crop_width) // 2 # Use scaled_pil_img.size[0] instead of scaled_w for precision
            crop_y = (scaled_pil_img.size[1] - crop_height) // 2 # Use scaled_pil_img.size[1] instead of scaled_h for precision

            # Ensure crop area is valid
            if crop_x < 0 or crop_y < 0 or crop_x + crop_width > scaled_pil_img.size[0] or crop_y + crop_height > scaled_pil_img.size[1]:
                 print(f"警告: PIL裁剪区域 ({crop_x},{crop_y},{crop_width},{crop_height}) 超出缩放图片范围 ({scaled_pil_img.size[0]}x{scaled_pil_img.size[1]})，返回None。")
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

    # 重新提供 _process_image_for_pieces 方法 (实现最短边匹配裁剪)
    def _process_image_for_pieces(self, image_surface_pg, target_size):
        """
        将 Pygame Surface 缩放和居中裁剪到目标尺寸。
        实现最短边匹配后裁剪。使用 PIL 如果可用。
        Returns the processed Pygame Surface or None if failed.
        target_size is (logic_cols * piece_width, logic_rows * piece_height).
        """
        if not PIL_AVAILABLE:
            print("警告: PIL未安装，使用Pygame进行处理。ImageManager._process_image_for_pieces可能无法正确执行最短边匹配裁剪。")
            # Fallback to Pygame's simple scale+center_crop, which might not be "shortest edge match"
            # For now, let's try to implement shortest edge match with Pygame too.
            return self._process_image_with_pygame_shortest_edge(image_surface_pg, target_size) # Use a new Pygame specific implementation
            # return None # Or return None to indicate failure without PIL


        # === 使用PIL实现最短边匹配裁剪 ===
        try:
            # Convert Pygame Surface to PIL Image
            mode = "RGBA" if image_surface_pg.get_flags() & pygame.SRCALPHA else "RGB"
            try:
                pil_img = Image.frombytes(mode, image_surface_pg.get_size(), pygame.image.tostring(image_surface_pg, mode))
            except Exception as e:
                 print(f"警告: PIL转换失败: {e}. 返回None.")
                 return None # Fail conversion if tostring fails

            img_w, img_h = pil_img.size
            target_w, target_h = target_size # target_w = logic_c * piece_w, target_h = logic_r * piece_height

            if img_w <= 0 or img_h <= 0 or target_w <= 0 or target_h <= 0:
                 print(f"警告: PIL裁剪：图像尺寸或目标尺寸无效。原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}. 返回None.")
                 return None


            # Calculate scale factor to match the *shortest* edge and cover the target
            scale_factor = max(target_w / img_w, target_h / img_h)

            # Calculate scaled dimensions
            scaled_w = int(img_w * scale_factor)
            scaled_h = int(img_h * scale_factor)

            # Ensure scaled dimensions are valid and large enough for the target area
            if scaled_w < target_w or scaled_h < target_h or scaled_w <= 0 or scaled_h <= 0:
                 print(f"警告: PIL裁剪：缩放尺寸 ({scaled_w}x{scaled_h}) 小于目标尺寸 ({target_w}x{target_h})。原始 {img_w}x{img_h}. 返回None.")
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


    # 新增 Pygame 实现的最短边匹配裁剪方法
    def _process_image_with_pygame_shortest_edge(self, image_surface_pg, target_size):
        """
        使用Pygame进行最短边匹配缩放和居中裁剪。
        将 Pygame Surface 缩放并居中裁剪到 target_size。
        这是在 PIL 不可用时的备用方法。

        Args:
            image_surface_pg (pygame.Surface): 需要处理的原始图片 Surface。
            target_size (tuple): 目标尺寸 (target_width, target_height)。

        Returns:
            pygame.Surface or None: 处理后的 Pygame Surface，或 None 如果失败。
        """
        img_w, img_h = image_surface_pg.get_size()
        target_w, target_h = target_size

        # 检查尺寸是否有效
        if img_w <= 0 or img_h <= 0 or target_w <= 0 or target_h <= 0:
             print(f"警告: Pygame裁剪：图像尺寸或目标尺寸无效。原始 {img_w}x{img_h}, 目标 {target_w}x{target_h}. 返回None.")
             return None

        # 计算原始图片和目标尺寸的宽高比
        # img_aspect = img_w / img_h # Not directly used in this approach
        # target_aspect = target_w / target_h # Not directly used in this approach

        # Calculate scale factor to match the *shortest* edge and cover the target
        # The factor should be max(target_w / img_w, target_h / img_h)
        scale_factor = max(target_w / img_w, target_h / img_h)

        # Calculate scaled dimensions
        scaled_w = int(img_w * scale_factor)
        scaled_h = int(img_h * scale_factor)

        # Ensure scaled dimensions are valid and large enough for the target area
        if scaled_w < target_w or scaled_h < target_h or scaled_w <= 0 or scaled_h <= 0:
             print(f"警告: Pygame裁剪：缩放尺寸 ({scaled_w}x{scaled_h}) 小于目标尺寸 ({target_w}x{target_h})。原始 {img_w}x{img_h}. 返回None.")
             return None


        try:
             # 使用 Pygame 进行缩放
             scaled_img_pg = pygame.transform.scale(image_surface_pg, (scaled_w, scaled_h))
        except pygame.error as e:
             print(f"警告: Pygame缩放失败: {e}。返回None。")
             return None


        # 计算裁剪区域
        crop_width = target_w
        crop_height = target_h
        # 计算裁剪起始点，使其居中
        crop_x = (scaled_w - crop_width) // 2
        crop_y = (scaled_h - crop_height) // 2

        # Ensure crop area is valid (non-negative start, and end within scaled image bounds)
        # This check might be redundant if scale factor calculation is correct, but safer
        if crop_x < 0 or crop_y < 0 or crop_x + crop_width > scaled_w or crop_y + crop_height > scaled_h:
             print(f"警告: Pygame裁剪区域 ({crop_x},{crop_y},{crop_width},{crop_height}) 超出缩放图片范围 ({scaled_w}x{scaled_h})，返回None。")
             return None

        try:
            # 使用 Pygame subsurface 进行裁剪，并复制以获得独立的 surface
            cropped_img_pg = scaled_img_pg.subsurface((crop_x, crop_y, crop_width, crop_height)).copy()
            return cropped_img_pg
        except ValueError as e:
             print(f"警告: Pygame subsurface 失败: {e}. 返回None。")
             return None
        except Exception as e:
            print(f"警告: Pygame裁剪时发生未知错误: {e}. 返回None。")
            return None


    def _split_image_into_pieces(self, processed_image_surface, logic_rows, logic_cols):
        """
        将处理好的图片分割成碎片surface并返回字典。

        Args:
            processed_image_surface (pygame.Surface): 已缩放和裁剪到目标尺寸的完整图片 Surface。
                                                     预期尺寸为 (logic_cols * piece_width, logic_rows * piece_height)。
            logic_rows (int): 图片的逻辑行数。
            logic_cols (int): 图片的逻辑列数。

        Returns:
            dict: { (row, col): pygame.Surface } 形式的碎片字典，或 None (如果分割失败或尺寸不匹配)。
        """
        img_w, img_h = processed_image_surface.get_size()
        piece_w, piece_h = settings.PIECE_WIDTH, settings.PIECE_HEIGHT # <-- 使用 PIECE_WIDTH/HEIGHT

        expected_w = logic_cols * piece_w
        expected_h = logic_rows * piece_h

        if img_w != expected_w or img_h != expected_h:
            print(f"错误: ImageManager: _split_image_into_pieces: 处理后的图片尺寸 {img_w}x{img_h} 与预期 {expected_w}x{expected_h} 不符。无法分割碎片。")
            return None # Size mismatch, cannot split

        pieces_dict = {} # Store pieces for this image

        # Iterate through the logical grid (rows x cols) to extract pieces
        for r in range(logic_rows): # Iterate through rows
            for c in range(logic_cols): # Iterate through columns
                x = c * piece_w # Calculate x-coordinate for the piece (Col affects X)
                y = r * piece_h # Calculate y-coordinate for the piece (Row affects Y)

                # Ensure extraction area is within the image bounds
                if x >= 0 and y >= 0 and x + piece_w <= img_w and y + piece_h <= img_h:
                    try:
                         # Extract piece surface (subsurface) and copy it
                         piece_surface = processed_image_surface.subsurface((x, y, piece_w, piece_h)).copy()
                         pieces_dict[(r, c)] = piece_surface # Store piece with its logical (row, col)
                    except ValueError as e:
                         print(f"警告: ImageManager: _split_image_into_pieces: subsurface extraction for piece r{r}_c{c} failed: {e}. Skipping.")
                    except Exception as e:
                        print(f"警告: ImageManager: _split_image_into_pieces: Extracting piece r{r}_c{c} encountered unknown error: {e}. Skipping.")
                else:
                     print(f"警告: ImageManager: _split_image_into_pieces: Extraction area ({x},{y},{piece_w},{piece_h}) for piece r{r}_c{c} out of image bounds ({img_w}x{img_h}), skipping.")

        # Check if the correct number of pieces was successfully generated
        expected_pieces_count = logic_rows * logic_cols # <-- Dynamic expected count
        if len(pieces_dict) != expected_pieces_count:
             print(f"警告: ImageManager: _split_image_into_pieces: Actual number of pieces generated ({len(pieces_dict)}) does not equal expected number ({expected_pieces_count}).")
             # If the count is incorrect, return None, indicating incomplete splitting
             return None

        return pieces_dict # Return dictionary of successfully split pieces


    # 替换 _save_pieces_to_cache 方法 (使用动态逻辑尺寸)
    def _save_pieces_to_cache(self, image_id):
        """将指定图片的碎片 surface 保存为缓存文件。"""
        # 确保图片ID有效且已配置逻辑尺寸
        if image_id not in self.image_logic_dims:
            print(f"警告: ImageManager: _save_pieces_to_cache: 图片ID {image_id} 逻辑尺寸配置缺失，无法保存碎片。")
            return False

        img_logic_c, img_logic_r = self.image_logic_dims[image_id]
        pieces_per_this_image = img_logic_c * img_logic_r

        if image_id not in self.pieces_surfaces or not self.pieces_surfaces[image_id] or len(self.pieces_surfaces[image_id]) != pieces_per_this_image:
             # print(f"警告: ImageManager: _save_pieces_to_cache: 没有图片 {image_id} 的完整碎片可以保存到缓存。") # Debug
             return False # No complete pieces to save

        # print(f"Saving pieces for image {image_id} to cache...") # Debug
        os.makedirs(settings.GENERATED_PIECE_DIR, exist_ok=True)

        success_count = 0
        total_pieces = len(self.pieces_surfaces[image_id])

        # Iterate through the logical grid (rows x cols) to save pieces
        for r in range(img_logic_r): # Use dynamic logic_rows
            for c in range(img_logic_c): # Use dynamic logic_cols
                if (r, c) in self.pieces_surfaces[image_id]:
                    piece_surface = self.pieces_surfaces[image_id][(r, c)]
                    filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                    filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                    try:
                         pygame.image.save(piece_surface, filepath)
                         success_count += 1
                    except pygame.error as e:
                         print(f"警告: ImageManager: _save_pieces_to_cache: 无法保存碎片 {filepath} 到缓存: {e}")
                # else: # Should not happen if pieces_surfaces[image_id] is complete

        # print(f"Image {image_id}: {total_pieces} pieces, {success_count} successfully saved to cache.")
        return success_count == total_pieces # Return True only if all pieces were saved


    # 替换 _load_pieces_from_cache 方法 (使用动态逻辑尺寸)
    def _load_pieces_from_cache(self, image_id):
        """尝试从缓存文件加载指定图片ID的碎片 surface。"""
        # 确保图片ID有效且已配置逻辑尺寸
        if image_id not in self.image_logic_dims:
            print(f"警告: ImageManager: _load_pieces_from_cache: 图片ID {image_id} 逻辑尺寸配置缺失，无法从缓存加载。")
            return False

        img_logic_c, img_logic_r = self.image_logic_dims[image_id]
        expected_pieces_count = img_logic_c * img_logic_r # Dynamic expected count

        # print(f"Attempting to load {expected_pieces_count} pieces for image {image_id} from cache...") # Debug

        # Quick check: Do all expected piece files exist?
        all_files_exist_quick_check = True
        # Iterate through the logical grid (rows x cols)
        for r in range(img_logic_r): # Use dynamic logic_rows
            for c in range(img_logic_c): # Use dynamic logic_cols
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
            for r in range(img_logic_r): # Use dynamic logic_rows
                for c in range(img_logic_c): # Use dynamic logic_cols
                    filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                    filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                    piece_surface = pygame.image.load(filepath).convert_alpha()
                    # Check size of loaded piece surface against fixed piece size
                    if piece_surface.get_size() != (settings.PIECE_WIDTH, settings.PIECE_HEIGHT): # <-- Use PIECE_WIDTH/HEIGHT
                         print(f"警告: ImageManager: _load_pieces_from_cache: 缓存碎片文件 {filepath} 尺寸不正确 ({piece_surface.get_size()})。预期 {settings.PIECE_WIDTH}x{settings.PIECE_HEIGHT}。缓存加载失败。")
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
                print(f"警告: ImageManager: _load_pieces_from_cache: 从缓存加载图片 {image_id} 的碎片数量不完整。预期 {expected_pieces_count}，实际加载 {loaded_count}。缓存加载失败。") # Debug
                potential_pieces_surfaces = {} # Clear incomplete loaded results
                return False

        except pygame.error as e:
             print(f"警告: ImageManager: _load_pieces_from_cache: Pygame error loading pieces from cache for image {image_id}: {e}. Cache load failed.")
             self.pieces_surfaces[image_id] = {} # Ensure entry is cleared or does not exist
             return False
        except Exception as e:
             print(f"警告: ImageManager: _load_pieces_from_cache: Unknown error loading pieces from cache for image {image_id}: {e}. Cache load failed.")
             self.pieces_surfaces[image_id] = {} # Ensure entry is cleared or does not exist
             return False


    # 替换 _initialize_consumption 方法 (根据动态逻辑尺寸计算)
    def _initialize_consumption(self):
        """
        确定第一张要消耗碎片的图片ID，并计算初始填充消耗的碎片数量。
        基于所有扫描到的有效图片ID列表，模拟初始填充消耗。
        """
        all_image_ids_ordered = sorted(self.all_image_files.keys()) # 获取所有有效图片ID并排序

        if not all_image_ids_ordered:
             # 如果没有扫描到任何有效图片，初始化消耗状态为 None
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             self._current_consume_img_total_pieces = 0
             print("警告：ImageManager: 没有找到任何有效图片文件，无法初始化碎片消耗机制！") # 调试信息
             return

        # 实际的碎片消耗（用于后续动态填充）应该从 Board 初始填充后剩余的图片和碎片开始。
        # 这里模拟初始填充，计算其使用了多少图片和碎片。

        # 获取初始可放置区域配置（点亮数量为 0 时）以确定需要初始填充的槽位数
        initial_playable_config = settings.PLAYABLE_AREA_CONFIG.get(0)
        if initial_playable_config is None:
             # 如果缺少初始配置，这是致命错误
             print("致命错误: ImageManager: settings.PLAYABLE_AREA_CONFIG 缺少点亮数量 0 的配置。无法初始化碎片消耗。") # 调试信息
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             self._current_consume_img_total_pieces = 0
             # Game 将处理致命错误，但在这里设置安全状态
             return


        initial_playable_area_slots = initial_playable_config['cols'] * initial_playable_config['rows'] # 初始可放置区域的总槽位数

        pieces_used_in_initial_fill_simulation = 0 # 模拟过程中已消耗的碎片总数计数器
        current_img_index_in_all = 0 # 跟踪当前模拟消耗到的图片在有序图片列表中的索引
        last_img_id_used_in_sim = None # 模拟过程中最后消耗碎片的图片ID

        print(f"ImageManager: 初始化消耗：模拟初始填充 ({initial_playable_area_slots} 槽位)...") # 调试信息

        # 模拟按顺序消耗图片碎片，直到填满初始可放置区域槽位数
        while pieces_used_in_initial_fill_simulation < initial_playable_area_slots and current_img_index_in_all < len(all_image_ids_ordered):
            current_img_id = all_image_ids_ordered[current_img_index_in_all]

            # 获取当前考虑图片的逻辑尺寸和总碎片数
            if current_img_id not in self.image_logic_dims:
                 # 如果图片逻辑尺寸缺失（按理说不应该发生，因为 _scan_image_files 已过滤）
                 print(f"内部警告: ImageManager: 图片ID {current_img_id} 在初始化消耗模拟时逻辑尺寸缺失。跳过。") # 调试信息
                 current_img_index_in_all += 1
                 continue # 跳过此图片

            img_logic_c, img_logic_r = self.image_logic_dims[current_img_id]
            pieces_per_this_image = img_logic_c * img_logic_r

            # 计算从当前图片需要多少碎片来填满剩余的初始槽位
            pieces_to_take_from_this_image = min(initial_playable_area_slots - pieces_used_in_initial_fill_simulation, pieces_per_this_image)

            # print(f"   simulating: taking {pieces_to_take_from_this_image} from Image {current_img_id} (total {pieces_per_this_image})...") # 调试信息

            pieces_used_in_initial_fill_simulation += pieces_to_take_from_this_image # 累加到总消耗
            last_img_id_used_in_sim = current_img_id # 记录当前图片为最后消耗的图片

            # 如果当前图片碎片被完全使用（即取出的数量等于其总数）
            if pieces_to_take_from_this_image == pieces_per_this_image:
                 current_img_index_in_all += 1 # 模拟继续，下一轮考虑列表中的下一张图片
            # 如果模拟在当前图片内部完成（未完全用完当前图片碎片），循环条件会停止，current_img_index_in_all 保持指向当前图片。


        # 根据模拟结果确定实际的碎片消耗起点状态。
        # 下一次实际消耗的图片 ID (self.next_image_to_consume_id) 应该是模拟过程中最后消耗碎片的图片 (last_img_id_used_in_sim)。
        # 已消耗的数量 (self.pieces_consumed_from_current_image) 是从这张图片中在模拟过程中取出的碎片数量。

        if last_img_id_used_in_sim is not None:
             self.next_image_to_consume_id = last_img_id_used_in_sim

             # 计算从最后消耗的图片 (last_img_id_used_in_sim) 中取出的碎片数量。
             # 这是总消耗 (pieces_used_in_initial_fill_simulation) 减去在它之前的图片消耗的总数。
             index_of_last_img = all_image_ids_ordered.index(last_img_id_used_in_sim) # 获取最后消耗图片的索引
             total_pieces_before_last_img = sum(self.image_logic_dims[all_image_ids_ordered[i]][0] * self.image_logic_dims[all_image_ids_ordered[i]][1]
                                                for i in range(index_of_last_img) if all_image_ids_ordered[i] in self.image_logic_dims) # 累加最后消耗图片之前所有图片的碎片总数

             self.pieces_consumed_from_current_image = pieces_used_in_initial_fill_simulation - total_pieces_before_last_img

             # 获取下一次实际消耗图片（即 last_img_id_used_in_sim）的总碎片数
             img_logic_c, img_logic_r = self.image_logic_dims.get(self.next_image_to_consume_id, (0,0)) # 安全获取逻辑尺寸
             self._current_consume_img_total_pieces = img_logic_c * img_logic_r # 动态总数

             print(f"ImageManager: 初始化消耗结束。下一次从图片ID {self.next_image_to_consume_id} 开始消耗，已从此图片消耗 {self.pieces_consumed_from_current_image}/{self._current_consume_img_total_pieces} 个碎片 (模拟初始填充消耗)。") # 调试信息

             # === 修正：移除错误的“恰好完全消耗”判断和提前移动下一张图片的逻辑 ===
             # 只有当 pieces_consumed_from_current_image *正好等于* _current_consume_img_total_pieces 时，
             # 才意味着当前图片消耗完毕，下一次应该从下一张图片开始。
             # 这个判断应该留到 get_next_fill_pieces 中处理，当从当前图片取完碎片后，再决定是否移动到下一张图片。
             # 初始化时只需设置正确的起点。

        else: # 模拟过程中没有消耗任何碎片（例如，初始可放置区域槽位为 0）
             # 实际消耗从有序图片列表的第一张开始，已消耗 0。
             if all_image_ids_ordered:
                 self.next_image_to_consume_id = all_image_ids_ordered[0]
                 self.pieces_consumed_from_current_image = 0
                 # 获取第一张图片的总碎片数
                 first_img_logic_c, first_img_logic_r = self.image_logic_dims.get(self.next_image_to_consume_id, (0,0))
                 self._current_consume_img_total_pieces = first_img_logic_c * first_img_logic_r
                 print(f"ImageManager: 初始化消耗：从第一张图片ID {self.next_image_to_consume_id} 开始，已消耗 0 个。") # 调试信息
             else:
                 # 仍然没有可用的图片
                 self.next_image_to_consume_id = None
                 self.pieces_consumed_from_current_image = 0
                 self._current_consume_img_total_pieces = 0
                 print("警告：ImageManager: 没有找到任何有效图片文件，无法初始化碎片消耗机制！") # 调试信息


        # Note: If loading from save, load_state will overwrite these values.


    # 替换 get_initial_pieces_for_board 方法 (根据初始可放置区域数量获取碎片)
    def get_initial_pieces_for_board(self, total_required_pieces):
        """
        获取用于初始 Board 填充的 Piece 对象列表。
        获取数量等于初始可放置区域的总槽位数 (total_required_pieces)。
        这些碎片来自 ImageManager 按顺序提供的图片，但仅限于那些碎片已成功加载的图片。
        返回的数量可能少于 total_required_pieces，如果 ImageManager 没有足够已加载的碎片。

        Args:
            total_required_pieces (int): 初始 Board 填充需要多少个碎片。

        Returns:
            list: 新创建的 Piece 对象列表。
        """
        total_required_pieces = max(0, total_required_pieces) # Ensure non-negative count
        initial_pieces_list = []
        # 获取已成功加载/生成全部碎片的图片ID列表，并按ID排序
        # === 修正：判断碎片是否加载完成时使用动态计算的碎片总数 ===
        image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and img_id in self.image_logic_dims and len(self.pieces_surfaces.get(img_id, {})) == self.image_logic_dims.get(img_id, (1,1))[0] * self.image_logic_dims.get(img_id, (1,1))[1]])

        if not image_ids_with_pieces:
            print("错误: ImageManager: 初始 Board 填充没有可用的碎片表面。")
            return [] # 没有图片碎片可用于填充

        # 获取所有有效图片ID的有序列表，用于确定图片消耗顺序
        all_image_ids_ordered = sorted(self.all_image_files.keys())

        print(f"ImageManager: 初始填充需要 {total_required_pieces} 个碎片 (来自初始可放置区域大小)。") # Debug
        print(f"ImageManager: 当前有 {len(image_ids_with_pieces)} 张图片已加载完整碎片，可供初始填充使用。") # Debug

        pieces_added_count = 0 # 计数器：已添加到 initial_pieces_list 的碎片数量
        img_index = 0 # 索引：当前正在从所有图片列表中考虑的图片ID的索引

        # 从已加载碎片的图片列表中按顺序获取碎片，直到达到所需的数量或没有更多已加载碎片
        # Note: We iterate through `all_image_ids_ordered` to maintain the intended consumption order,
        # but only take pieces if the image is in `image_ids_with_pieces`.
        while pieces_added_count < total_required_pieces and img_index < len(all_image_ids_ordered):
            current_img_id = all_image_ids_ordered[img_index] # 获取当前图片ID

            # 检查此图片是否已成功加载碎片
            if current_img_id in image_ids_with_pieces:
                img_logic_c, img_logic_r = self.image_logic_dims[current_img_id] # 获取逻辑尺寸
                pieces_per_this_image = img_logic_c * img_logic_r # 动态计算总碎片数

                # 计算从此图片需要获取的碎片数量
                # 取所需总数与此图片总碎片数的最小值 (初始填充逻辑不会考虑 ImageManager 的消耗进度)
                pieces_to_take_from_this_image = min(total_required_pieces - pieces_added_count, pieces_per_this_image)

                # 遍历逻辑网格以获取碎片 (按逻辑顺序 0,0 -> 0,1 -> ... -> 1,0 -> ...)
                taken_from_this_img_count = 0 # 计数器：从此图片已获取的碎片数量
                total_piece_index = 0 # Total piece index within this image (0 to pieces_per_this_image - 1)
                for r in range(img_logic_r):
                    for c in range(img_logic_c):
                         if taken_from_this_img_count < pieces_to_take_from_this_image:
                              # Convert logical (r, c) to a single index
                              # This is pieces_per_this_image * r + c in row-major order,
                              # but we just need to take the first `pieces_to_take_from_this_image` pieces in logical order.
                              # So, we just check if the current piece index (`total_piece_index`) is within the count to take.
                              if (r, c) in self.pieces_surfaces[current_img_id]: # 确保碎片 surface 存在
                                   piece_surface = self.pieces_surfaces[current_img_id][(r, c)]
                                   # 创建 Piece 对象，初始网格位置 -1,-1，Board 之后分配
                                   initial_pieces_list.append(Piece(piece_surface, current_img_id, r, c, -1, -1))
                                   pieces_added_count += 1 # 增加总已添加碎片计数
                                   taken_from_this_img_count += 1 # 增加从此图片获取的碎片计数
                              # else: print(f"Error: Piece surface {current_img_id}_{r}_{c} not found in pieces_surfaces.") # Should not happen if image in pieces_surfaces

                         total_piece_index += 1 # Increment regardless

                         if taken_from_this_img_count == pieces_to_take_from_this_image:
                             break # 从此图片已获取足够数量
                    if taken_from_this_img_count == pieces_to_take_from_this_image: break # 从此图片已获取足够数量


                # 设置此图片的状态为 'unlit' (如果之前是 'unentered')，因为它已经被用于填充 Board
                if current_img_id in self.image_status and self.image_status[current_img_id] == 'unentered':
                     self.image_status[current_img_id] = 'unlit'

                img_index += 1 # 移动到下一张图片（即使当前图片碎片未全部取完，也从下一张开始，逻辑与之前一致）
            else:
                 # 图片ID存在于all_image_files，但碎片处理失败或未加载
                 # print(f"警告: ImageManager: 图片ID {current_img_id} 文件存在但碎片处理失败，无法用于初始填充。跳过。") # Debug
                 img_index += 1 # 移动到下一张图片


        if pieces_added_count != total_required_pieces:
             print(f"警告: ImageManager: 获取的初始碎片数量 {pieces_added_count} 与初始可放置区域总槽位 {total_required_pieces} 不匹配。")

        # Randomly shuffle the list of pieces
        import random
        random.shuffle(initial_pieces_list)

        return initial_pieces_list


    # 替换 get_next_fill_pieces 方法 (根据动态逻辑尺寸计算和消耗进度)
    def get_next_fill_pieces(self, count):
        """
        获取下一批指定数量的新 Piece 对象用于填充空位。
        这些碎片来自 ImageManager 按消耗进度提供的图片。
        只提供碎片已成功加载完成的图片。

        Args:
            count (int): 需要获取的碎片数量。

        Returns:
            list: 新创建的 Piece 对象列表，数量为 count 或更少 (如果碎片不足)。
        """
        new_pieces = []
        pieces_needed = count
        # Get IDs of images that have successfully loaded/generated their full set of pieces, sorted by ID
        image_ids_with_pieces = sorted([img_id for img_id in self.all_image_files.keys() if img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and img_id in self.image_logic_dims and len(self.pieces_surfaces.get(img_id, {})) == self.image_logic_dims.get(img_id, (1,1))[0] * self.image_logic_dims.get(img_id, (1,1))[1]])

        all_image_ids_ordered = sorted(self.all_image_files.keys()) # Get all valid image IDs in order

        print(f"ImageManager: get_next_fill_pieces: 需要填充 {pieces_needed} 个空位。当前消耗状态: 图片ID {self.next_image_to_consume_id}, 已消耗 {self.pieces_consumed_from_current_image}/{self._current_consume_img_total_pieces}.") # Debug

        # If there are no more images to consume at all
        if self.next_image_to_consume_id is None:
             print("警告: ImageManager: get_next_fill_pieces: 没有更多图片可供消耗碎片。") # Debug
             return [] # Return empty list


        # Loop until enough pieces are obtained or no more *usable* images are available
        while pieces_needed > 0:
            current_img_id = self.next_image_to_consume_id

            # === 检查当前应该消耗的图片是否已完全加载碎片 ===
            if current_img_id not in image_ids_with_pieces:
                 # If the pieces for the current consumption image are NOT loaded
                 print(f"警告: ImageManager: get_next_fill_pieces: 图片ID {current_img_id} 的碎片尚未加载完成。跳过此图片，寻找下一张可用图片。") # Debug
                 # Need to find the next usable loaded image *after* the current one in the ordered list
                 current_img_index_in_all = all_image_ids_ordered.index(current_img_id) if current_img_id in all_image_ids_ordered else len(all_image_ids_ordered) # Get index, default to end if not found
                 found_next_usable = False
                 for next_idx in range(current_img_index_in_all + 1, len(all_image_ids_ordered)): # Search from the one *after* current
                      img_id = all_image_ids_ordered[next_idx]
                      # Check if this image is in image_ids_with_pieces (fully loaded)
                      if img_id in image_ids_with_pieces:
                           self.next_image_to_consume_id = img_id # Update current consumption image
                           self.pieces_consumed_from_current_image = 0 # Start from beginning of this new image
                           # Update total pieces for the new current image
                           next_img_logic_c, next_img_logic_r = self.image_logic_dims.get(self.next_image_to_consume_id, (0,0))
                           self._current_consume_img_total_pieces = next_img_logic_c * next_img_logic_r
                           print(f"ImageManager: get_next_fill_pieces: 下一个消耗图片ID设置为 (跳过未加载): {self.next_image_to_consume_id}") # Debug
                           found_next_usable = True
                           break # Found the next usable image

                 if not found_next_usable:
                      # No more usable images with loaded pieces in the sequence
                      print("警告: ImageManager: get_next_fill_pieces: 没有更多已加载的图片可供消耗碎片。") # Debug
                      self.next_image_to_consume_id = None # Stop consumption
                      self.pieces_consumed_from_current_image = 0
                      self._current_consume_img_total_pieces = 0
                      break # Exit while loop (no more pieces can be provided)

                 else:
                      # Found the next usable image, the loop will continue with the new current_img_id in the next iteration
                      continue # Go to the next iteration of the while loop to process the newly set next_image_to_consume_id

            # If we reach here, current_img_id is valid AND its pieces are loaded.

            # Get dynamic total pieces for current image (already updated when next_image_to_consume_id was set or initialized)
            # img_logic_c, img_logic_r = self.image_logic_dims[current_img_id]
            # self._current_consume_img_total_pieces = img_logic_c * img_logic_r # Already set

            pieces_remaining_in_current_img = self._current_consume_img_total_pieces - self.pieces_consumed_from_current_image

            # Calculate how many pieces to take from the current image
            pieces_to_take_from_current = min(pieces_needed, pieces_remaining_in_current_img)

            print(f"ImageManager: get_next_fill_pieces: 从图片 {current_img_id} 获取碎片。剩余 {pieces_remaining_in_current_img}, 本批次尝试获取 {pieces_to_take_from_current}.") # Debug

            if pieces_to_take_from_current > 0:
                # Get pieces from the current image, continuing from the last consumed position (logical order)
                pieces_taken_count = 0
                # Calculate starting logical (row, col) based on self.pieces_consumed_from_current_image
                start_total_index = self.pieces_consumed_from_current_image # Total piece index (0-total_pieces-1)

                # Iterate through the logical grid (rows x cols) to find pieces to take
                current_total_index = 0
                # Get logic dims for iteration
                img_logic_c, img_logic_r = self.image_logic_dims[current_img_id]
                # Iterate logical rows and columns based on current image's logic dims
                for r in range(img_logic_r):
                    for c in range(img_logic_c):
                         # Check if this piece's total index is within the range we need to take this batch
                         if current_total_index >= start_total_index and pieces_taken_count < pieces_to_take_from_current:
                              # Ensure piece surface exists (should be true if image is in pieces_surfaces)
                              if (r, c) in self.pieces_surfaces[current_img_id]:
                                  piece_surface = self.pieces_surfaces[current_img_id][(r, c)]
                                  # Create Piece object, initial grid position is -1,-1, Board will assign later
                                  new_pieces.append(Piece(piece_surface, current_img_id, r, c, -1, -1))
                                  pieces_taken_count += 1
                                  # print(f"  Obtained piece: Image {current_img_id}, Logical Row {r}, Logical Col {c}") # Debug
                              else:
                                   print(f"错误: ImageManager: Logical piece ({r},{c}) for image {current_img_id} surface not found, but image marked as complete.") # Debug
                         current_total_index += 1 # Increment total index regardless of whether piece was taken

                         if pieces_taken_count == pieces_to_take_from_current:
                             break # Reached the number of pieces to take from the current image
                    if pieces_taken_count == pieces_to_take_from_current:
                        break # Reached the number of pieces to take from the current image


                pieces_needed -= pieces_taken_count
                self.pieces_consumed_from_current_image += pieces_taken_count # Update consumption count AFTER taking pieces this batch
                print(f"ImageManager: get_next_fill_pieces: 从图片 {current_img_id} 实际获取了 {pieces_taken_count} 个碎片。已从此图片消耗 {self.pieces_consumed_from_current_image}/{self._current_consume_img_total_pieces}。还需 {pieces_needed} 个。") # Debug


            # Check if pieces from the current image are fully consumed *after* taking pieces this batch
            if self.pieces_consumed_from_current_image >= self._current_consume_img_total_pieces:
                # print(f"ImageManager: Pieces for image {current_img_id} are fully consumed.") # Debug
                # Move to the next image in the all_image_files sequence
                all_image_ids_ordered = sorted(self.all_image_files.keys())
                try:
                    current_img_index_in_all = all_image_ids_ordered.index(current_img_id) # Get current index
                    next_img_index_in_all = current_img_index_in_all + 1
                    if next_img_index_in_all < len(all_image_ids_ordered):
                        self.next_image_to_consume_id = all_image_ids_ordered[next_img_index_in_all]
                        self.pieces_consumed_from_current_image = 0 # Reset consumption count
                        # Update total pieces for the new current image
                        next_img_logic_c, next_img_logic_r = self.image_logic_dims.get(self.next_image_to_consume_id, (0,0))
                        self._current_consume_img_total_pieces = next_img_logic_c * next_img_logic_r
                        print(f"ImageManager: get_next_fill_pieces: 图片 {current_img_id} 消耗完毕，下一个消耗图片ID设置为: {self.next_image_to_consume_id} (总碎片: {self._current_consume_img_total_pieces}).") # Debug

                        # After moving to the next image, we still need to check if *that* image's pieces are loaded in the next loop iteration.
                        # The check at the start of the while loop handles skipping if needed.

                    else:
                        self.next_image_to_consume_id = None # No more images in sequence
                        self.pieces_consumed_from_current_image = 0
                        self._current_consume_img_total_pieces = 0
                        print("ImageManager: get_next_fill_pieces: 所有图片都已消耗完毕。") # Debug

                except ValueError:
                     # Current image ID not in all_image_files? This should not happen.
                     print(f"内部错误: ImageManager: get_next_fill_pieces: 当前消耗的图片ID {current_img_id} 不在所有图片列表中。") # Debug
                     self.next_image_to_consume_id = None # State error, stop consumption
                     self.pieces_consumed_from_current_image = 0
                     self._current_consume_img_total_pieces = 0
                     break # Exit while loop


            # If pieces are still needed and next_image_to_consume_id is not None, the while loop continues.


        # New pieces do not need to be shuffled, they are placed based on the order of empty slots
        # (This happens in Board.fill_new_pieces)
        print(f"ImageManager: get_next_fill_pieces: 填充请求完成，提供了 {len(new_pieces)} 个碎片。") # Debug
        return new_pieces

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
         从缓存获取指定图片ID的完整处理后surface (缩放裁剪到目标碎片尺寸对应的图片尺寸)。
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
        # print(f"图片ID列表: {all_image_ids}") # Debug/

        for img_id in all_image_ids:
            # print(f"检查图片ID: {img_id}") # Debug
            status = self.image_status.get(img_id, 'unentered')
            # 图库应仅显示状态为 'unlit' 或 'lit' 的图片
            # print(f"图片ID {img_id} 的状态: {status}") # Debug
            if status in ['unlit', 'lit']:
                status_info = {'id': img_id, 'state': status}
                if status == 'lit':
                    # 获取完成时间，若不存在则使用当前时间作为备用（正常情况下不应发生）
                    status_info['completion_time'] = self.completed_times.get(img_id, time.time())

                # 添加一个标志，指示图片的碎片和缩略图是否已加载（图库缩略图/大图查看需要）
                # === 修正：判断碎片是否加载完成时使用动态计算的碎片总数 ===
                img_logic_c, img_logic_r = self.image_logic_dims.get(img_id, (0,0)) # Get logic dims safely
                pieces_per_this_image = img_logic_c * img_logic_r # Dynamic total pieces

                pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == pieces_per_this_image)
                thumbnails_cached = (img_id in self.cached_thumbnails and self.cached_thumbnails.get(img_id) is not None and
                                     img_id in self.cached_unlit_thumbnails and self.cached_unlit_thumbnails.get(img_id) is not None)
                status_info['is_ready_for_gallery'] = pieces_loaded and thumbnails_cached  # 图库显示/启用图片的标志

                status_list.append(status_info)
        # print(f"获取到 {len(status_list)} 张图片的状态信息，其中包括 {sum(1 for s in status_list if s['is_ready_for_gallery'])} 张准备好的图片。") # Debug
        # print(f"状态信息示例: {status_list[:5]}") # 打印前5条状态信息以检查其结构和内容 # Debug, 避免刷屏
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
            'next_image_to_consume_id': self.next_image_to_consume_id, # 存储下一个要消耗碎片的图片ID (整数或None)
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
        # print(f"state_data 的值为: {state_data}") # Debug
        loaded_image_status = state_data.get('image_status', {})
        # print(f"从存档数据中获取的 loaded_image_status 的值为: {loaded_image_status}") # Debug
        loaded_completed_times = state_data.get('completed_times', {})
        loaded_next_image_to_consume_id = state_data.get('next_image_to_consume_id', None)
        loaded_pieces_consumed = state_data.get('pieces_consumed_from_current_image', 0)

        # --- 关键调试：打印从存档中加载到的 image_status 字典 ---
        print(f"ImageManager: 存档中的 image_status 数据 (原始): {loaded_image_status}") # Debug


        # --- 关键修改：从存档加载 image_status 并转换为整数键 ---
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
                    self.image_status[img_id] = status # <-- 使用整数 ID 存储到 self.image_status
                    loaded_status_count += 1
                # else: print(f"警告: Image ID {img_id} 在存档中的状态 '{status}' 无效。") # Debug invalid status
            # else: print(f"Debug: Image ID {img_id} 未在存档状态中找到。状态保持为初始化时的 'unentered'。") # Debug missing in save

        # 如果存档数据中包含的图片ID超出了当前扫描到的范围，这些状态将被忽略，这是期望的行为。
        # 反过来，如果当前扫描到的图片ID没有在存档中，它们的状态保持为初始化时的 'unentered'。


        # --- 关键调试：打印加载并过滤后的 image_status 字典 ---
        print(f"ImageManager 从存档加载并过滤后，当前 image_status 包含 {loaded_status_count} 张图片的状态。具体状态如下: {self.image_status}")  # Debug

        # 确保只加载状态为 lit 的图片的完成时间，且图片ID存在于已加载状态中
        self.completed_times = {} # Start with an empty dictionary for current completed times
        loaded_completed_count = 0 # Debug counter
        # 遍历存档中的 completed_times 字典 (键是字符串)
        for img_id_str, comp_time in loaded_completed_times.items():
            try:
                img_id = int(img_id_str) # 尝试将字符串键转换为整数
                # 检查转换后的整数ID是否存在于当前加载的状态中，并且状态是 'lit'
                if img_id in self.image_status and self.image_status.get(img_id) == 'lit':
                    self.completed_times[img_id] = comp_time # <-- 使用整数 ID 存储完成时间
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

        # Ensure the loaded next_image_to_consume_id is a valid image ID
        if loaded_next_id_int is not None and loaded_next_id_int in self.all_image_files:
            self.next_image_to_consume_id = loaded_next_id_int # Store as integer
            # Update total pieces for the current consumption image based on loaded ID
            img_logic_c, img_logic_r = self.image_logic_dims.get(self.next_image_to_consume_id, (0,0)) # Get logic dims safely
            self._current_consume_img_total_pieces = img_logic_c * img_logic_r # Use dynamic total
            print(f"ImageManager 从存档加载 next_image_to_consume_id: {self.next_image_to_consume_id} (总碎片: {self._current_consume_img_total_pieces})") # Debug
            print(f"ImageManager: 初始化消耗结束。下一次从图片ID {self.next_image_to_consume_id} 开始消耗，已从此图片消耗 {self.pieces_consumed_from_current_image}/{self._current_consume_img_total_pieces} 个碎片 (模拟初始填充消耗)。") # Debug
        else:
            print(f"警告: 存档中的 next_image_to_consume_id ({loaded_next_image_to_consume_id}) 无效。重新初始化消耗状态。") # Debug
            self._initialize_consumption() # Re-initialize consumption state based on file scan


        # Ensure loaded pieces consumed count is valid for the *current* consumption image (using the newly set _current_consume_img_total_pieces)
        if 0 <= loaded_pieces_consumed <= self._current_consume_img_total_pieces:
            self.pieces_consumed_from_current_image = loaded_pieces_consumed
            print(f"ImageManager 从存档加载 pieces_consumed_from_current_image: {self.pieces_consumed_from_current_image}") # Debug
        else:
            print(f"警告: 存档中的 pieces_consumed_from_current_image ({loaded_pieces_consumed}) 对于图片ID {self.next_image_to_consume_id} 无效 (总碎片 {self._current_consume_img_total_pieces})。重置为0。") # Debug
            self.pieces_consumed_from_current_image = 0 # Reset to 0 if invalid or inconsistent


        # === 填充高优先级加载队列 ===
        # 将所有在加载并过滤后状态是 'unlit' 或 'lit' 的图片ID添加到高优先级队列
        # 这些图片需要在游戏启动后优先加载资源，以便尽快在拼盘或图库中显示
        print("填充高优先级加载队列...") # Debug
        self._high_priority_load_queue.clear() # Clear any previous high-priority items
        self._normal_load_queue.clear() # Also clear normal queue and repopulate based on current status below

        # Repopulate normal queue with all image IDs first
        all_image_ids_ordered = sorted(self.all_image_files.keys())
        self._normal_load_queue.extend(all_image_ids_ordered)
        print(f"ImageManager: 重新填充普通加载队列， {len(self._normal_load_queue)} 张图片进入普通队列。") # Debug


        # Iterate through the populated self.image_status dictionary (which now contains filtered states from the save, keys are integers)
        high_priority_count = 0 # Debug counter
        for img_id, status in self.image_status.items(): # Use the populated self.image_status (keys are integers)
             if status in ['unlit', 'lit']:
                 # Check if this image is NOT already fully processed in the current session's memory
                 # (Unlikely at this stage for these images from save, but safety check)
                 # === 修正：判断碎片是否加载完成时使用动态计算的碎片总数 ===
                 img_logic_c, img_logic_r = self.image_logic_dims.get(img_id, (0,0)) # Get logic dims safely
                 pieces_per_this_image = img_logic_c * img_logic_r # Dynamic total pieces

                 pieces_loaded = (img_id in self.pieces_surfaces and self.pieces_surfaces.get(img_id) is not None and len(self.pieces_surfaces.get(img_id, {})) == pieces_per_this_image)
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
