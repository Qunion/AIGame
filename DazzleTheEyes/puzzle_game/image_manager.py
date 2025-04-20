# image_manager.py
# 负责图片的加载、处理、碎片生成、管理图片状态和提供碎片/完整图资源

import pygame
import settings
import os
import time
from piece import Piece

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    print("警告: Pillow库未安装。部分图像处理功能可能受限。建议安装: pip install Pillow")
    PIL_AVAILABLE = False


class ImageManager:
    def __init__(self, game):
        """
        初始化图像管理器。仅加载图片列表，但不立即处理所有图片。
        只在需要时处理或从缓存加载。

        Args:
            game (Game): Game实例，用于在加载时显示加载界面 (可选)。
        """
        self.game = game # 持有Game实例的引用

        # 存储所有原始图片文件的信息 {id: filepath}
        self.all_image_files = {} # {image_id: full_filepath}
        self._scan_image_files() # 扫描图片文件，获取所有图片ID和路径

        # 存储加载和处理后的原始图片表面 {id: pygame.Surface}
        self.processed_full_images = {}
        # 存储生成的碎片表面 {id: { (row, col): pygame.Surface }}
        self.pieces_surfaces = {}
        # 存储每张图片的状态 {id: 'unentered' / 'unlit' / 'lit'}
        self.image_status = {} # {image_id: status}
        # 存储已点亮图片的完成时间 {id: timestamp} # 用于图库排序
        self.completed_times = {}

        # 跟踪图片加载进度
        self._loaded_image_count = 0 # 已完成加载和处理的图片数量
        self._total_image_count = len(self.all_image_files) # 总共找到的图片数量

        # 跟踪下一批需要从哪张图片取碎片
        self.next_image_to_consume_id = -1 # 初始化时确定
        self.pieces_consumed_from_current_image = 0 # 初始化时确定

        # 初始化时，只加载和处理前 INITIAL_LOAD_IMAGE_COUNT 张图片
        self._initial_load_images(settings.INITIAL_LOAD_IMAGE_COUNT)

        # 初始化碎片消耗机制，基于已加载的图片
        self._initialize_consumption()


    def _scan_image_files(self):
        """扫描 assets 目录，找到所有符合 image_N.png 命名规则的图片文件路径和ID"""
        image_files = [f for f in os.listdir(settings.ASSETS_DIR) if f.startswith("image_") and f.endswith(".png")]
        image_files.sort(key=lambda x: int(x.replace("image_", "").replace(".png", ""))) # 确保按图片ID排序

        for filename in image_files:
            try:
                image_id = int(filename.replace("image_", "").replace(".png", ""))
                full_path = os.path.join(settings.ASSETS_DIR, filename)
                self.all_image_files[image_id] = full_path
                self.image_status[image_id] = 'unentered' # 所有扫描到的图片初始状态都是未入场
            except ValueError:
                print(f"警告: 文件名格式不正确，无法提取图片ID: {filename}")
            except Exception as e:
                print(f"警告: 扫描文件 {filename} 时发生错误: {e}")

        self._total_image_count = len(self.all_image_files) # 更新总图片数量
        print(f"扫描到 {self._total_image_count} 张原始图片。") # 调试信息


    def _initial_load_images(self, count):
        """初始化时加载和处理前 'count' 张图片"""
        image_ids = sorted(self.all_image_files.keys()) # 按ID排序
        images_to_load_ids = image_ids[:count] # 取前 count 个图片ID

        print(f"初始化加载前 {len(images_to_load_ids)} 张图片...") # 调试信息

        for image_id in images_to_load_ids:
             self._load_and_process_single_image(image_id) # 调用处理单张图片的方法

        self._loaded_image_count = len(images_to_load_ids) # 更新已加载数量


    def _load_and_process_single_image(self, image_id):
        """
        加载、处理单张原始图片，生成碎片，并保存到缓存。
        如果缓存存在且不需要重新生成，则从缓存加载。
        """
        if image_id not in self.all_image_files:
             print(f"警告: 图片ID {image_id} 文件路径未知，无法加载和处理。")
             return # 文件路径未知，跳过

        filepath = self.all_image_files[image_id]
        print(f"正在处理图片: ID {image_id}, 文件 {os.path.basename(filepath)}") # 调试信息

        # 尝试从缓存加载碎片
        fragments_loaded_from_cache = self._load_pieces_from_cache(image_id)

        if settings.REGENERATE_PIECES or not fragments_loaded_from_cache:
            # 如果需要重新生成，或者从缓存加载失败
            print(f"  { '重新生成' if settings.REGENERATE_PIECES else '缓存不存在或加载失败'}，开始裁剪和分割碎片...") # 调试信息

            # 加载原始图片 (使用Pygame加载)
            try:
                original_img_pg = pygame.image.load(filepath).convert_alpha() # 加载并保持透明度
            except pygame.error as e:
                 print(f"错误: Pygame无法加载原始图片 {filepath}: {e}")
                 return # 加载失败，跳过该图片

            # 处理图片尺寸 (缩放和居中裁剪)
            target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE # 9 * 120 = 1080
            target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE # 5 * 120 = 600
            target_size = (target_width, target_height)

            processed_img_pg = self._process_image_for_pieces(original_img_pg, target_size)

            self.processed_full_images[image_id] = processed_img_pg # 存储处理后的完整图片 (用于图库大图)
            self.pieces_surfaces[image_id] = {} # 清空或初始化碎片表面字典

            # 将处理后的图片分割成碎片 surface
            self._split_image_into_pieces(image_id, processed_img_pg)

            # 保存生成的碎片到缓存文件
            self._save_pieces_to_cache(image_id)

        # 如果从缓存加载成功，processed_full_images 也需要一个完整图用于图库
        # 在上面的 if/else 逻辑中，如果执行了裁剪流程 processed_full_images 会被填充
        # 如果只从缓存加载， processed_full_images[image_id] 可能还不存在，需要加载处理用于图库
        if image_id not in self.processed_full_images:
             print(f"  从缓存加载碎片，需要处理原始图 {os.path.basename(filepath)} 用于图库完整图。") # 调试信息
             try:
                original_img_pg = pygame.image.load(filepath).convert_alpha()
                target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE
                target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE
                processed_img_pg = self._process_image_for_pieces(original_img_pg, (target_width, target_height))
                self.processed_full_images[image_id] = processed_img_pg
             except pygame.error as e:
                 print(f"错误: Pygame无法加载原始图片 {filepath} 用于图库完整图: {e}")
             except Exception as e:
                 print(f"错误: 处理图片 {filepath} 用于图库完整图时发生未知错误: {e}")


        # 图片状态在扫描时已初始化为 'unentered'
        # self.image_status[image_id] = 'unentered' # 这一行不需要在这里，扫描时统一设置


    def load_next_batch_background(self, batch_size):
        """
        在后台按批次加载和处理未加载的图片。
        只处理 ImageManager 知道文件路径但碎片surface尚未加载的图片。

        Args:
            batch_size (int): 本次尝试加载处理的图片数量。

        Returns:
            int: 实际完成加载和处理的图片数量。
        """
        if self.is_loading_finished():
             # print("所有图片已加载完成。") # 调试信息，避免刷屏
             return 0 # 全部加载完成了

        image_ids_to_load = sorted(self.all_image_files.keys()) # 所有图片ID，按顺序
        loaded_this_batch = 0
        processed_count = 0

        # 找到下一张未加载的图片ID
        # 从所有图片ID中找到第一个不在 self.pieces_surfaces 键中的图片ID
        next_unloaded_image_id = None
        for img_id in image_ids_to_load:
            if img_id not in self.pieces_surfaces:
                next_unloaded_image_id = img_id
                break

        if next_unloaded_image_id is None:
             # 理论上 is_loading_finished() 应该已经返回 True 了
             # print("没有找到未加载的图片。")
             self._loaded_image_count = self._total_image_count # 确保计数正确
             return 0


        # 从找到的未加载图片ID开始，加载 batch_size 数量的图片
        start_index = image_ids_to_load.index(next_unloaded_image_id)
        images_for_this_batch_ids = image_ids_to_load[start_index : start_index + batch_size]

        # print(f"后台加载：正在加载图片ID列表: {images_for_this_batch_ids}") # 调试信息

        for image_id in images_for_this_batch_ids:
            if image_id not in self.pieces_surfaces: # 双重检查，确保是未加载的
                self._load_and_process_single_image(image_id) # 加载处理单张图片
                # 如果成功加载处理 (碎片 surfaces 已存在)，更新计数
                if image_id in self.pieces_surfaces and self.pieces_surfaces[image_id]:
                     self._loaded_image_count += 1
                     processed_count += 1
                     print(f"  后台加载完成图片ID {image_id} ({self._loaded_image_count}/{self._total_image_count})") # 调试信息
                else:
                     print(f"警告: 后台加载图片ID {image_id} 失败，碎片 surface 不存在。") # 调试信息


        # TODO: 如果加载画面需要更新进度，可以在这里通知Game实例
        # if self.game and hasattr(self.game, 'update_loading_progress'):
        #      self.game.update_loading_progress(self._loaded_image_count, self._total_image_count)

        return processed_count


    def is_loading_finished(self):
        """检查是否所有原始图片都已加载和处理（即碎片surface已生成）。"""
        return self._loaded_image_count >= self._total_image_count


    def _process_image_for_pieces(self, image_surface_pg, target_size):
        """
        将 Pygame Surface 缩放和居中裁剪到目标尺寸。
        """
        img_w, img_h = image_surface_pg.get_size()
        target_w, target_h = target_size

        img_aspect = img_w / img_h if img_h > 0 else 1
        target_aspect = target_w / target_h if target_h > 0 else 1

        if img_aspect > target_aspect:
            scaled_h = target_h
            scaled_w = int(scaled_h * img_aspect)
        else:
            scaled_w = target_w
            scaled_h = int(scaled_w / img_aspect)

        if scaled_w <= 0 or scaled_h <= 0:
            print(f"警告: 缩放尺寸无效 ({scaled_w}x{scaled_h})，跳过图片处理。")
            return pygame.Surface(target_size, pygame.SRCALPHA)

        try:
             scaled_img_pg = pygame.transform.scale(image_surface_pg, (scaled_w, scaled_h))
        except pygame.error as e:
             print(f"警告: Pygame缩放失败: {e}。尝试返回原始Surface。")
             return pygame.Surface(target_size, pygame.SRCALPHA) # 返回一个空的透明Surface


        crop_x = (scaled_w - target_w) // 2
        crop_y = (scaled_h - target_h) // 2

        if crop_x < 0 or crop_y < 0 or crop_x + target_w > scaled_w or crop_y + target_h > scaled_h:
             print(f"警告: 裁剪区域超出缩放图片范围。缩放尺寸: {scaled_w}x{scaled_h}, 裁剪区域: ({crop_x},{crop_y}) {target_w}x{target_h}")
             return pygame.Surface(target_size, pygame.SRCALPHA) # 返回一个空的透明Surface


        try:
            cropped_img_pg = scaled_img_pg.subsurface((crop_x, crop_y, target_w, target_h)).copy()
            return cropped_img_pg
        except ValueError as e:
             print(f"警告: Pygame subsurface 失败: {e}. 尝试返回一个空白Surface。")
             return pygame.Surface(target_size, pygame.SRCALPHA)


    def _split_image_into_pieces(self, image_id, processed_image_surface):
        """将处理好的图片分割成碎片surface并存储"""
        img_w, img_h = processed_image_surface.get_size()
        piece_w, piece_h = settings.PIECE_SIZE, settings.PIECE_SIZE

        expected_w = settings.IMAGE_LOGIC_COLS * piece_w
        expected_h = settings.IMAGE_LOGIC_ROWS * piece_h
        if img_w != expected_w or img_h != expected_h:
            print(f"警告: 图片ID {image_id} 处理后的尺寸 {img_w}x{img_h} 与预期 {expected_w}x{expected_h} 不符。分割碎片可能不完整。")

        self.pieces_surfaces[image_id] = {} # 初始化碎片字典

        for r in range(settings.IMAGE_LOGIC_ROWS):
            for c in range(settings.IMAGE_LOGIC_COLS):
                x = c * piece_w
                y = r * piece_h
                if x + piece_w <= img_w and y + piece_h <= img_h:
                    try:
                         piece_surface = processed_image_surface.subsurface((x, y, piece_w, piece_h)).copy()
                         self.pieces_surfaces[image_id][(r, c)] = piece_surface
                    except ValueError as e:
                         print(f"警告: subsurface 提取碎片 {image_id}_r{r}_c{c} 失败: {e}. 跳过。")
                else:
                     print(f"警告: 碎片 {image_id}_r{r}_c{c} 的提取区域 ({x},{y},{piece_w},{piece_h}) 超出图片范围 ({img_w}x{img_h})，跳过。")


    def _save_pieces_to_cache(self, image_id):
        """将指定图片的碎片 surface 保存为文件缓存"""
        if image_id not in self.pieces_surfaces or not self.pieces_surfaces[image_id]:
             print(f"警告: 没有图片 {image_id} 的碎片可以保存到缓存。")
             return

        # print(f"正在保存图片 {image_id} 的碎片到缓存...") # 调试信息
        os.makedirs(settings.GENERATED_PIECE_DIR, exist_ok=True)

        success_count = 0
        for (r, c), piece_surface in self.pieces_surfaces[image_id].items():
            filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
            filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
            try:
                 pygame.image.save(piece_surface, filepath)
                 success_count += 1
            except pygame.error as e:
                 print(f"警告: 无法保存碎片 {filepath} 到缓存: {e}")
        # print(f"图片 {image_id} 共有 {len(self.pieces_surfaces[image_id])} 个碎片，成功保存 {success_count} 个到缓存。")


    def _load_pieces_from_cache(self, image_id):
        """尝试从缓存文件加载指定图片的碎片"""
        # print(f"尝试从缓存加载图片 {image_id} 的碎片...") # 调试信息
        expected_pieces_count = settings.PIECES_PER_IMAGE # 5x9 = 45

        # 检查是否所有预期的碎片文件都存在
        all_files_exist = True
        for r in range(settings.IMAGE_LOGIC_ROWS):
            for c in range(settings.IMAGE_LOGIC_COLS):
                 filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                 filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                 if not os.path.exists(filepath):
                     all_files_exist = False
                     break
            if not all_files_exist: break

        if all_files_exist:
             # print(f"  找到图片 {image_id} 的所有 {expected_pieces_count} 个缓存文件，开始加载...") # 调试信息
             potential_pieces_surfaces = {} # 临时存储加载的碎片surface
             loaded_count = 0
             try:
                for r in range(settings.IMAGE_LOGIC_ROWS):
                    for c in range(settings.IMAGE_LOGIC_COLS):
                        filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                        filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                        piece_surface = pygame.image.load(filepath).convert_alpha()
                        if piece_surface.get_size() != (settings.PIECE_SIZE, settings.PIECE_SIZE):
                             print(f"警告: 缓存碎片文件 {filepath} 尺寸不正确 ({piece_surface.get_size()})。")
                             all_files_exist = False # 标记加载失败
                             break
                        potential_pieces_surfaces[(r, c)] = piece_surface
                        loaded_count += 1
                    if not all_files_exist: break

                if all_files_exist and loaded_count == expected_pieces_count:
                    self.pieces_surfaces[image_id] = potential_pieces_surfaces
                    # print(f"  成功从缓存加载图片 {image_id} 的 {loaded_count} 个碎片。") # 调试信息
                    return True # 加载成功
                else:
                    print(f"警告: 从缓存加载图片 {image_id} 的碎片数量不完整或文件有问题。预期 {expected_pieces_count}，实际加载 {loaded_count}。") # 调试信息
                    self.pieces_surfaces[image_id] = {}
                    return False

             except pygame.error as e:
                 print(f"警告: 从缓存加载图片 {image_id} 的碎片时发生Pygame错误: {e}. 标记加载失败。")
                 self.pieces_surfaces[image_id] = {}
                 return False
             except Exception as e:
                 print(f"警告: 从缓存加载图片 {image_id} 的碎片时发生未知错误: {e}. 标记加载失败。")
                 self.pieces_surfaces[image_id] = {}
                 return False
        else:
            # print(f"  图片 {image_id} 的缓存文件不完整或不存在。") # 调试信息
            return False


    def _initialize_consumption(self):
        """确定第一张要消耗碎片的图片ID"""
        # 这里只需要基于 self.all_image_files 的键来计算
        all_image_ids = sorted(self.all_image_files.keys())

        if not all_image_ids:
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             print("警告：没有找到任何图片文件！") # 调试信息
             return

        # 初始填充会从 image_ids[0] 开始，直到 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
        # 实际开始消耗的图片是 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
        if settings.INITIAL_FULL_IMAGES_COUNT < len(all_image_ids):
            self.next_image_to_consume_id = all_image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
            # 初始填充时已经从这张图片获取了 settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个碎片
            self.pieces_consumed_from_current_image = settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT
            # 确保当前要消耗的图片状态是 'unlit' (如果它在已加载列表中)
            # if self.next_image_to_consume_id in self.image_status:
            #      self.image_status[self.next_image_to_consume_id] = 'unlit'

            print(f"初始化碎片消耗：从图片ID {self.next_image_to_consume_id} 开始消耗，已消耗 {self.pieces_consumed_from_current_image} 个碎片 (用于初始填充)。") # 调试信息
        else:
             self.next_image_to_consume_id = None
             self.pieces_consumed_from_current_image = 0
             print("警告：没有更多图片可供后续消耗。") # 调试信息


    def get_initial_pieces_for_board(self):
        """
        获取游戏开始时需要填充到拼盘的 Piece 对象列表。
        这些碎片来自已初始加载的图片。
        """
        initial_pieces_list = []
        # 这里应该只考虑已成功加载碎片 surface 的图片
        image_ids_with_pieces = sorted(self.pieces_surfaces.keys())

        if not image_ids_with_pieces:
            print("错误: 没有图片碎片表面可供初始化 Board。")
            return [] # 没有图片直接返回空列表

        # 计算总共需要多少碎片来填满拼盘
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS # 16 * 9 = 144

        pieces_added_count = 0
        img_index = 0 # 跟踪已加载碎片的图片索引

        # 添加前 INITIAL_FULL_IMAGES_COUNT 张完整图片的碎片 (从已加载碎片的列表中取)
        while img_index < settings.INITIAL_FULL_IMAGES_COUNT and img_index < len(image_ids_with_pieces):
            img_id = image_ids_with_pieces[img_index]
            # print(f"正在获取已加载图片 {img_id} 的所有碎片 ({settings.PIECES_PER_IMAGE} 个) 用于初始填充。") # 调试信息
            if img_id in self.pieces_surfaces: # 确保碎片表面集合存在
                for r in range(settings.IMAGE_LOGIC_ROWS):
                    for c in range(settings.IMAGE_LOGIC_COLS):
                         if (r, c) in self.pieces_surfaces[img_id]: # 确保碎片surface存在
                             piece_surface = self.pieces_surfaces[img_id][(r, c)]
                             # 创建Piece对象，初始网格位置先填 -1,-1，Board后续会随机分配
                             initial_pieces_list.append(Piece(piece_surface, img_id, r, c, -1, -1))
                             pieces_added_count += 1
                         else:
                             print(f"警告: 已加载图片 {img_id} 的碎片 ({r},{c}) 表面不存在，无法创建Piece对象。")
                self.image_status[img_id] = 'unlit' # 这几张图片现在是“未点亮”状态
            else:
                 print(f"警告: 已加载碎片列表中的图片ID {img_id} 在 self.pieces_surfaces 中不存在。")
            img_index += 1

        # 添加下一张图片的碎片 (从已加载碎片列表中取)
        # 这张图片将是 image_ids_with_pieces[img_index]
        if img_index < len(image_ids_with_pieces):
             current_consume_img_id = image_ids_with_pieces[img_index]

             # print(f"正在从已加载图片 {current_consume_img_id} 获取前 {settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT} 个碎片用于初始填充。") # 调试信息

             piece_count_from_current = 0
             # 按照逻辑顺序 (行优先，列优先) 获取碎片
             total_piece_index_in_img = 0
             if current_consume_img_id in self.pieces_surfaces: # 确保碎片表面集合存在
                 for r in range(settings.IMAGE_LOGIC_ROWS):
                     for c in range(settings.IMAGE_LOGIC_COLS):
                         if piece_count_from_current < settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                             if (r, c) in self.pieces_surfaces[current_consume_img_id]:
                                 piece_surface = self.pieces_surfaces[current_consume_img_id][(r, c)]
                                 initial_pieces_list.append(Piece(piece_surface, current_consume_img_id, r, c, -1, -1))
                                 pieces_added_count += 1
                                 piece_count_from_current += 1
                             else:
                                  print(f"警告: 图片 {current_consume_img_id} 的逻辑碎片 ({r},{c}) 表面不存在，无法创建Piece对象。")
                         else:
                             break # 达到指定数量
                         total_piece_index_in_img += 1
                     if piece_count_from_current == settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                         break

                 self.image_status[current_consume_img_id] = 'unlit' # 这张图片现在也是“未点亮”状态
             else:
                  print(f"警告: 已加载碎片列表中的图片ID {current_consume_img_id} 在 self.pieces_surfaces 中不存在。")


        print(f"总共获取了 {pieces_added_count} 个碎片用于初始填充。") # 调试信息
        if pieces_added_count > total_required_pieces:
             print(f"错误: 获取的初始碎片数量 {pieces_added_count} 多于拼盘总槽位 {total_required_pieces}！")
             initial_pieces_list = initial_pieces_list[:total_required_pieces]
        elif pieces_added_count < total_required_pieces:
              print(f"警告: 获取的初始碎片数量 {pieces_added_count} 少于拼盘总槽位 {total_required_pieces}！拼盘将有空位。")


        # 将列表随机打乱
        import random
        random.shuffle(initial_pieces_list)

        return initial_pieces_list


    def get_next_fill_pieces(self, count):
        """
        根据填充规则，获取下一批指定数量的新 Piece 对象用于填充空位。
        这些碎片来自已加载（包括后台加载）的图片。
        """
        new_pieces = []
        pieces_needed = count
        image_ids = sorted(self.pieces_surfaces.keys()) # 按ID排序，这些是已成功加载或处理的图片

        # print(f"需要填充 {pieces_needed} 个空位...") # 调试信息

        # 如果当前没有需要消耗的图片了，或者下一张图片碎片还未加载完成
        if self.next_image_to_consume_id is None or self.next_image_to_consume_id not in self.pieces_surfaces:
             # print("警告: 没有更多已加载的图片可供消耗碎片。")
             return [] # 返回空列表

        # 找到当前正在消耗的图片的逻辑索引 (在所有已加载碎片的图片ID列表中)
        try:
            image_ids_with_pieces = sorted(self.pieces_surfaces.keys())
            current_img_index = image_ids_with_pieces.index(self.next_image_to_consume_id)
        except ValueError:
             print(f"错误: 当前消耗的图片ID {self.next_image_to_consume_id} 不在已加载碎片图片列表中。")
             self.next_image_to_consume_id = None # 状态异常，重置
             return []


        # 循环直到获取足够碎片或没有更多已加载的图片
        while pieces_needed > 0 and self.next_image_to_consume_id is not None:
            current_img_id = self.next_image_to_consume_id

            # 确保当前图片的碎片 surface 已经加载
            if current_img_id not in self.pieces_surfaces or not self.pieces_surfaces[current_img_id]:
                print(f"警告: 当前消耗图片ID {current_img_id} 的碎片 surface 尚未加载或不存在。停止获取新碎片。")
                self.next_image_to_consume_id = None # 没有已加载的碎片可用，停止消耗
                break

            total_pieces_in_current_img = settings.PIECES_PER_IMAGE # 45
            pieces_remaining_in_current_img = total_pieces_in_current_img - self.pieces_consumed_from_current_image

            # 计算从当前图片可以获取多少碎片
            pieces_to_take_from_current = min(pieces_needed, pieces_remaining_in_current_img)

            # print(f"从图片 {current_img_id} 剩余 {pieces_remaining_in_current_img} 个，本次尝试获取 {pieces_to_take_from_current} 个。") # 调试信息

            if pieces_to_take_from_current > 0:
                # 从当前图片获取碎片，按照逻辑顺序继续上次消耗的位置
                pieces_taken_count = 0
                # 根据 self.pieces_consumed_from_current_image 计算开始的逻辑 (row, col)
                start_total_index = self.pieces_consumed_from_current_image # 总碎片索引

                # 遍历逻辑碎片位置，找到要取的碎片
                current_total_index = 0
                for r in range(settings.IMAGE_LOGIC_ROWS):
                    for c in range(settings.IMAGE_LOGIC_COLS):
                        if current_total_index >= start_total_index and pieces_taken_count < pieces_to_take_from_current:
                             # 确保碎片表面存在
                             if (r, c) in self.pieces_surfaces[current_img_id]:
                                 piece_surface = self.pieces_surfaces[current_img_id][(r, c)]
                                 new_pieces.append(Piece(piece_surface, current_img_id, r, c, -1, -1)) # -1,-1 表示待分配位置
                                 pieces_taken_count += 1
                                 self.pieces_consumed_from_current_image += 1 # 标记已消耗数量
                                 # print(f"  获取碎片: 图片{current_img_id}_行{r}_列{c}") # 调试信息
                             else:
                                  print(f"警告: 图片 {current_img_id} 的逻辑碎片 ({r},{c}) 表面不存在，跳过。")
                        current_total_index += 1 # 无论是否存在，计数器都前进，以保持逻辑顺序

                        if pieces_taken_count == pieces_to_take_from_current:
                            break # 达到本次从当前图片取碎片的数量
                    if pieces_taken_count == pieces_to_take_from_current:
                        break # 达到本次从当前图片取碎片的数量

                pieces_needed -= pieces_taken_count
                # print(f"本次从图片 {current_img_id} 实际获取了 {pieces_taken_count} 个碎片。还需要 {pieces_needed} 个。") # 调试信息


            # 检查当前图片的碎片是否已消耗完
            if self.pieces_consumed_from_current_image >= total_pieces_in_current_img: # 使用 >= 确保健壮性
                # print(f"图片 {current_img_id} 的碎片已消耗完或超出。") # 调试信息
                # 切换到下一张已加载碎片的图片
                current_img_index += 1
                image_ids_with_pieces = sorted(self.pieces_surfaces.keys()) # 重新获取已加载列表
                if current_img_index < len(image_ids_with_pieces):
                    self.next_image_to_consume_id = image_ids_with_pieces[current_img_index]
                    self.pieces_consumed_from_current_image = 0 # 重置消耗计数
                    # self.image_status[self.next_image_to_consume_id] = 'unlit' # 新进入的图片状态变为未点亮 (已经在get_initial_pieces_for_board处理了)
                    print(f"下一张消耗图片ID设置为: {self.next_image_to_consume_id}") # 调试信息
                else:
                    self.next_image_to_consume_id = None # 没有更多已加载的图片了
                    print("没有更多已加载图片可供消耗。") # 调试信息
                # 如果切换图片，并且 pieces_needed 仍大于 0，循环会继续，尝试从下一张图片获取

            # 如果还需要碎片，但是已经没有下一张已加载的图片了
            if pieces_needed > 0 and self.next_image_to_consume_id is None:
                 # print(f"警告: 需要 {count} 个碎片，但没有更多已加载图片可用。最终只获取到 {len(new_pieces)} 个。")
                 break # 没有更多已加载图片了，退出循环


        # 注意：新获取的碎片不需要打乱，它们会根据填充空位的顺序放置到拼盘中。
        return new_pieces

    # TODO: 添加一个方法用于在后台加载中更新加载进度信息 (可选)
    # def get_loading_progress(self):
    #      """返回当前加载进度信息，例如 '3/10'"""
    #      return f"{self._loaded_image_count}/{self._total_image_count}"


    def get_all_entered_pictures_status(self):
        """获取所有已入场（未点亮或已点亮）图片的ID、状态和完成时间"""
        status_list = []
        # 确保遍历顺序与图片ID一致
        # 只处理 ImageManager 已经加载或生成了碎片的图片
        image_ids_with_pieces = sorted(self.pieces_surfaces.keys())


        for img_id in image_ids_with_pieces:
             # 如果图片ID在 image_status 中存在，则使用其状态，否则默认为 'unentered'
             status = self.image_status.get(img_id, 'unentered')
             # 图库中只显示 'unlit' 和 'lit' 状态的图片
             if status in ['unlit', 'lit']:
                status_info = {'id': img_id, 'state': status}
                if status == 'lit':
                    status_info['completion_time'] = self.completed_times.get(img_id, 0) # 获取完成时间，没有则默认为0
                status_list.append(status_info)

        # TODO: 如果需要图库显示所有图片状态，包括未入场，需要调整这里的过滤逻辑

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
            # print(f"图片 {image_id} 状态改变: {old_status} -> {state}") # 调试信息
            if state == 'lit' and old_status != 'lit':
                 # 如果状态从非lit变为lit，记录完成时间
                 self.completed_times[image_id] = time.time() # 记录点亮时间
        else:
             print(f"警告: 尝试设置未知图片ID {image_id} 的状态为 {state}。")


    def get_thumbnail(self, image_id):
         """获取指定图片的缩略图surface，用于图库列表"""
         if image_id in self.processed_full_images:
             full_img = self.processed_full_images[image_id]
             try:
                thumbnail = pygame.transform.scale(full_img, (settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT))
                return thumbnail
             except pygame.error as e:
                 print(f"警告: 无法为图片 {image_id} 生成缩略图: {e}")
                 return None
         # 如果 processed_full_images 不存在，可以尝试从碎片拼合，或者返回一个占位符
         print(f"警告: 无法获取图片 {image_id} 的完整处理后图片，无法生成缩略图。")
         return None


    def get_full_processed_image(self, image_id):
         """获取指定图片的完整处理后的surface (用于图库大图查看)"""
         return self.processed_full_images.get(image_id) # 如果图片ID不存在，返回None

    # def _grayscale_surface(self, surface): ...