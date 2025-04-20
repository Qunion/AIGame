# image_manager.py
# 负责图片的加载、处理、碎片生成、管理图片状态和提供碎片/完整图资源

import pygame
import settings
import os
import time # 用于记录完成时间
from piece import Piece # 导入Piece类

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
        初始化图像管理器，加载和处理所有原始图片。

        Args:
            game (Game): Game实例，用于在加载时显示加载界面。
        """
        self.game = game # 持有Game实例的引用

        # 存储加载和处理后的原始图片表面 {id: pygame.Surface}
        # 这些是处理成适合分割为 5x9 比例后的完整图，用于图库大图显示
        self.processed_full_images = {}
        # 存储生成的碎片表面 {id: { (row, col): pygame.Surface }}
        self.pieces_surfaces = {}
        # 存储每张图片的状态 {id: 'unentered' / 'unlit' / 'lit'}
        self.image_status = {}
        # 存储已点亮图片的完成时间 {id: timestamp} # 用于图库排序
        self.completed_times = {}

        # 跟踪下一批需要从哪张图片取碎片
        self.next_image_to_consume_id = -1
        self.pieces_consumed_from_current_image = 0

        self.load_and_process_images() # 初始化时加载和处理所有图片
        self._initialize_consumption() # 初始化碎片消耗机制

    def load_and_process_images(self):
        """
        加载assets目录下的所有原始图片，进行处理或从缓存加载碎片。
        并处理成适合分割成 settings.IMAGE_LOGIC_ROWS x settings.IMAGE_LOGIC_COLS 的完整图
        """
        # 扫描 assets 目录，找到所有符合 image_N.png 命名规则的图片
        image_files = [f for f in os.listdir(settings.ASSETS_DIR) if f.startswith("image_") and f.endswith(".png")]
        image_files.sort(key=lambda x: int(x.replace("image_", "").replace(".png", ""))) # 确保按图片ID排序

        print(f"找到 {len(image_files)} 张原始图片。") # 调试信息

        for filename in image_files:
            try:
                # 从文件名中提取图片ID
                image_id = int(filename.replace("image_", "").replace(".png", ""))
                full_path = os.path.join(settings.ASSETS_DIR, filename)

                print(f"正在处理图片: {filename} (ID: {image_id})") # 调试信息

                # 尝试从缓存加载碎片
                fragments_loaded_from_cache = self._load_pieces_from_cache(image_id)

                if settings.REGENERATE_PIECES or not fragments_loaded_from_cache:
                    # 如果需要重新生成，或者从缓存加载失败
                    print(f"  { '重新生成' if settings.REGENERATE_PIECES else '缓存不存在或加载失败'}，开始裁剪和分割碎片...") # 调试信息

                    # 加载原始图片 (使用Pygame加载)
                    original_img_pg = pygame.image.load(full_path).convert_alpha() # 加载并保持透明度

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
                if image_id not in self.processed_full_images:
                     # 如果只从缓存加载碎片，我们需要一个完整的surface用于图库大图
                     # 简单的方法是重新加载原始图并处理，或者从碎片重新拼合 (后者复杂)
                     # 这里选择重新加载和处理用于图库显示
                     print(f"  从缓存加载碎片，但需要处理原始图 {filename} 用于图库完整图。") # 调试信息
                     original_img_pg = pygame.image.load(full_path).convert_alpha()
                     target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE
                     target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE
                     processed_img_pg = self._process_image_for_pieces(original_img_pg, (target_width, target_height))
                     self.processed_full_images[image_id] = processed_img_pg


                self.image_status[image_id] = 'unentered' # 初始状态为未入场 (ImageManager管理的图片状态)

                # TODO: 在图片处理过程中更新加载界面显示 (通过Game实例调用)
                # self.game.update_loading_screen(f"加载图片 {image_id}...")


            except pygame.error as e:
                print(f"错误: Pygame无法加载或处理图片 {filename}: {e}")
            except Exception as e:
                print(f"错误: 处理图片 {filename} 时发生未知错误: {e}")

        print("所有图片处理完成。") # 调试信息


    def _process_image_for_pieces(self, image_surface_pg, target_size):
        """
        将 Pygame Surface 缩放和居中裁剪到目标尺寸 (target_width, target_height)。
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
             # 如果缩放失败，尝试返回原始Surface (可能尺寸不匹配)
             # 或者返回一个空白Surface
             return pygame.Surface(target_size, pygame.SRCALPHA)


        crop_x = (scaled_w - target_w) // 2
        crop_y = (scaled_h - target_h) // 2

        if crop_x < 0 or crop_y < 0 or crop_x + target_w > scaled_w or crop_y + target_h > scaled_h:
             print(f"警告: 裁剪区域超出缩放图片范围。缩放尺寸: {scaled_w}x{scaled_h}, 裁剪区域: ({crop_x},{crop_y}) {target_w}x{target_h}")
             # 返回一个空白的Surface或者 scaled_img_pg 的一部分
             # 尝试返回一个从 (0,0) 开始的 target_size 大小的子Surface
             return scaled_img_pg.subsurface((0, 0, min(scaled_w, target_w), min(scaled_h, target_h))).copy()


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
            # 继续尝试分割，但可能有问题

        self.pieces_surfaces[image_id] = {} # 初始化碎片字典

        for r in range(settings.IMAGE_LOGIC_ROWS):
            for c in range(settings.IMAGE_LOGIC_COLS):
                x = c * piece_w
                y = r * piece_h
                # 确保提取区域在 processed_image_surface 范围内
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

        print(f"正在保存图片 {image_id} 的碎片到缓存...") # 调试信息
        # 确保碎片输出目录存在
        os.makedirs(settings.GENERATED_PIECE_DIR, exist_ok=True)

        success_count = 0
        for (r, c), piece_surface in self.pieces_surfaces[image_id].items():
            # 使用 settings 中定义的命名格式构建文件路径
            filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
            filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
            try:
                 pygame.image.save(piece_surface, filepath)
                 success_count += 1
            except pygame.error as e:
                 print(f"警告: 无法保存碎片 {filepath} 到缓存: {e}")
        print(f"图片 {image_id} 共有 {len(self.pieces_surfaces[image_id])} 个碎片，成功保存 {success_count} 个到缓存。")


    def _load_pieces_from_cache(self, image_id):
        """尝试从缓存文件加载指定图片的碎片"""
        print(f"尝试从缓存加载图片 {image_id} 的碎片...") # 调试信息
        expected_pieces_count = settings.PIECES_PER_IMAGE # 5x9 = 45

        # 检查是否所有预期的碎片文件都存在
        all_files_exist = True
        potential_pieces_surfaces = {} # 临时存储加载的碎片surface
        loaded_count = 0

        for r in range(settings.IMAGE_LOGIC_ROWS):
            for c in range(settings.IMAGE_LOGIC_COLS):
                 filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                 filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                 if not os.path.exists(filepath):
                     all_files_exist = False
                     # print(f"  缓存文件不存在: {filepath}") # 调试信息，如果文件多会刷屏
                     break # 只要有一个文件不存在就说明缓存不完整，无需继续检查和加载本图片的其他碎片
            if not all_files_exist:
                 break # 外层循环也停止检查

        if all_files_exist:
             print(f"  找到图片 {image_id} 的所有 {expected_pieces_count} 个缓存文件，开始加载...") # 调试信息
             try:
                for r in range(settings.IMAGE_LOGIC_ROWS):
                    for c in range(settings.IMAGE_LOGIC_COLS):
                        filename = settings.PIECE_FILENAME_FORMAT.format(image_id, r, c)
                        filepath = os.path.join(settings.GENERATED_PIECE_DIR, filename)
                        piece_surface = pygame.image.load(filepath).convert_alpha() # 加载碎片surface
                        # 可以在这里检查加载的surface尺寸是否正确 (settings.PIECE_SIZE)
                        if piece_surface.get_size() != (settings.PIECE_SIZE, settings.PIECE_SIZE):
                             print(f"警告: 缓存碎片文件 {filepath} 尺寸不正确 ({piece_surface.get_size()})。")
                             # 可以选择跳过这个碎片，或者标记加载失败
                             all_files_exist = False # 标记加载失败
                             break # 碎片有问题，标记加载失败并退出内层循环
                        potential_pieces_surfaces[(r, c)] = piece_surface
                        loaded_count += 1
                    if not all_files_exist: break # 退出外层循环

                if all_files_exist and loaded_count == expected_pieces_count:
                    # 如果所有文件都加载成功且数量正确
                    self.pieces_surfaces[image_id] = potential_pieces_surfaces
                    print(f"  成功从缓存加载图片 {image_id} 的 {loaded_count} 个碎片。") # 调试信息
                    return True # 加载成功
                else:
                    print(f"警告: 从缓存加载图片 {image_id} 的碎片数量不完整或文件有问题。预期 {expected_pieces_count}，实际加载 {loaded_count}。") # 调试信息
                    self.pieces_surfaces[image_id] = {} # 清空已加载的部分，避免使用不完整的数据
                    return False # 加载失败

             except pygame.error as e:
                 print(f"警告: 从缓存加载图片 {image_id} 的碎片时发生Pygame错误: {e}. 标记加载失败。")
                 self.pieces_surfaces[image_id] = {} # 清空
                 return False
             except Exception as e:
                 print(f"警告: 从缓存加载图片 {image_id} 的碎片时发生未知错误: {e}. 标记加载失败。")
                 self.pieces_surfaces[image_id] = {} # 清空
                 return False
        else:
            print(f"  图片 {image_id} 的缓存文件不完整或不存在。") # 调试信息
            return False # 缓存文件不完整或不存在

    def _initialize_consumption(self):
        """确定第一张要消耗碎片的图片ID"""
        image_ids = sorted(self.pieces_surfaces.keys())
        if image_ids:
            # 初始填充会从 image_ids[0] 开始，直到 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
            # 实际开始消耗的图片是 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
            if settings.INITIAL_FULL_IMAGES_COUNT < len(image_ids):
                self.next_image_to_consume_id = image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
                # 初始填充时已经从这张图片获取了 settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个碎片
                self.pieces_consumed_from_current_image = settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT
                # 确保当前要消耗的图片状态是 'unlit'
                if self.next_image_to_consume_id in self.image_status:
                     self.image_status[self.next_image_to_consume_id] = 'unlit'

                print(f"初始化碎片消耗：从图片ID {self.next_image_to_consume_id} 开始消耗，已消耗 {self.pieces_consumed_from_current_image} 个碎片 (用于初始填充)。") # 调试信息
            else:
                 # 如果总图片数量不足以进行初始填充，或者刚好等于完整填充的数量
                 self.next_image_to_consume_id = None
                 self.pieces_consumed_from_current_image = 0
                 print("警告：没有更多图片可供后续消耗。") # 调试信息
        else:
            self.next_image_to_consume_id = None
            self.pieces_consumed_from_current_image = 0
            print("警告：没有找到任何图片碎片！") # 调试信息


    def get_initial_pieces_for_board(self):
        """
        获取游戏开始时需要填充到拼盘的 Piece 对象列表。
        包含前 INITIAL_FULL_IMAGES_COUNT 张完整图片的所有碎片，
        以及下一张图片的前 INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个碎片。
        """
        initial_pieces_list = []
        image_ids = sorted(self.pieces_surfaces.keys()) # 按ID排序，确保顺序，这些是成功加载或生成的图片

        if not image_ids:
            print("错误: 没有图片碎片可供初始化。")
            return [] # 没有图片直接返回空列表

        # 计算总共需要多少碎片来填满拼盘
        total_required_pieces = settings.BOARD_COLS * settings.BOARD_ROWS # 16 * 9 = 144

        pieces_added_count = 0
        img_index = 0

        # 添加前 INITIAL_FULL_IMAGES_COUNT 张完整图片的碎片
        while img_index < settings.INITIAL_FULL_IMAGES_COUNT and img_index < len(image_ids):
            img_id = image_ids[img_index]
            print(f"正在获取图片 {img_id} 的所有碎片 ({settings.PIECES_PER_IMAGE} 个) 用于初始填充。") # 调试信息
            for r in range(settings.IMAGE_LOGIC_ROWS):
                for c in range(settings.IMAGE_LOGIC_COLS):
                     if (r, c) in self.pieces_surfaces[img_id]: # 确保碎片surface存在
                         piece_surface = self.pieces_surfaces[img_id][(r, c)]
                         # 创建Piece对象，初始网格位置先填 -1,-1，Board后续会随机分配
                         initial_pieces_list.append(Piece(piece_surface, img_id, r, c, -1, -1))
                         pieces_added_count += 1
                     else:
                         print(f"警告: 图片 {img_id} 的碎片 ({r},{c}) 表面不存在，无法创建Piece对象。")
            self.image_status[img_id] = 'unlit' # 这几张图片现在是“未点亮”状态
            img_index += 1

        # 添加下一张图片的碎片 (遵循规则：从下一张图片取前 INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个)
        # 这张图片将是 image_ids[img_index]
        if img_index < len(image_ids):
             current_consume_img_id = image_ids[img_index]

             print(f"正在从图片 {current_consume_img_id} 获取前 {settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT} 个碎片用于初始填充。") # 调试信息

             piece_count_from_current = 0
             # 按照逻辑顺序 (行优先，列优先) 获取碎片
             # 这里要确保从第0个碎片开始取 INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个
             total_piece_index_in_img = 0
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
             # self.next_image_to_consume_id 和 self.pieces_consumed_from_current_image
             # 在_initialize_consumption中设置了，这里只是获取碎片，不改变消耗状态


        print(f"总共获取了 {pieces_added_count} 个碎片用于初始填充。") # 调试信息
        if pieces_added_count > total_required_pieces:
             print(f"错误: 获取的初始碎片数量 {pieces_added_count} 多于拼盘总槽位 {total_required_pieces}！")
             # 截断列表，只取前144个
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
        遵循Image_4剩余+Image_5部分的规则。

        Args:
            count (int): 需要获取的碎片数量 (通常是45，即settings.PIECES_PER_IMAGE)

        Returns:
            list: 新创建的 Piece 对象列表，数量为 count 或更少 (如果碎片不足)
        """
        new_pieces = []
        pieces_needed = count
        image_ids = sorted(self.pieces_surfaces.keys()) # 按ID排序

        # print(f"需要填充 {pieces_needed} 个空位...") # 调试信息

        # 如果当前没有需要消耗的图片了
        if self.next_image_to_consume_id is None:
             # print("警告: 没有更多图片可供消耗碎片。")
             return [] # 返回空列表

        # 找到当前正在消耗的图片的逻辑索引
        try:
            # 找到 current_consume_img_id 在 sorted image_ids 中的位置
            current_img_index = image_ids.index(self.next_image_to_consume_id)
        except ValueError:
             print(f"错误: 当前消耗的图片ID {self.next_image_to_consume_id} 不在已加载图片列表中。")
             self.next_image_to_consume_id = None # 状态异常，重置
             return []


        # 循环直到获取足够碎片或没有更多图片
        while pieces_needed > 0 and self.next_image_to_consume_id is not None:
            current_img_id = self.next_image_to_consume_id
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
                             if (r, c) in self.pieces_surfaces[current_img_id]: # 确保碎片表面存在
                                 piece_surface = self.pieces_surfaces[current_img_id][(r, c)]
                                 new_pieces.append(Piece(piece_surface, current_img_id, r, c, -1, -1)) # -1,-1 表示待分配位置
                                 pieces_taken_count += 1
                                 self.pieces_consumed_from_current_image += 1 # 标记已消耗数量
                                 # print(f"  获取碎片: 图片{current_img_id}_行{r}_列{c}") # 调试信息
                             else:
                                  print(f"警告: 图片 {current_img_id} 的碎片 ({r},{c}) 表面不存在，跳过。")
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
                # 切换到下一张图片
                current_img_index += 1
                if current_img_index < len(image_ids):
                    self.next_image_to_consume_id = image_ids[current_img_index]
                    self.pieces_consumed_from_current_image = 0 # 重置消耗计数
                    self.image_status[self.next_image_to_consume_id] = 'unlit' # 新进入的图片状态变为未点亮
                    # print(f"下一张消耗图片ID设置为: {self.next_image_to_consume_id}") # 调试信息
                else:
                    self.next_image_to_consume_id = None # 没有更多图片了
                    # print("没有更多图片可供消耗。") # 调试信息
                # 如果切换图片，并且 pieces_needed 仍大于 0，循环会继续，尝试从下一张图片获取

            # 如果还需要碎片，但是已经没有下一张图片了
            if pieces_needed > 0 and self.next_image_to_consume_id is None:
                 # print(f"警告: 需要 {count} 个碎片，但没有更多图片可用。最终只获取到 {len(new_pieces)} 个。")
                 break # 没有更多图片了，退出循环


        # 注意：新获取的碎片不需要打乱，它们会根据填充空位的顺序放置到拼盘中。
        return new_pieces

    def get_all_entered_pictures_status(self):
        """获取所有已入场（未点亮或已点亮）图片的ID、状态和完成时间"""
        status_list = []
        # 确保遍历顺序与图片ID一致
        # 只需要处理 ImageManager 已经加载或生成了碎片的图片
        image_ids_with_pieces = sorted(self.pieces_surfaces.keys())


        for img_id in image_ids_with_pieces:
             status = self.image_status.get(img_id, 'unentered') # 从状态字典获取，如果不存在默认为unentered
             # 图库中只显示 'unlit' 和 'lit' 状态的图片
             if status in ['unlit', 'lit']:
                status_info = {'id': img_id, 'state': status}
                if status == 'lit':
                    status_info['completion_time'] = self.completed_times.get(img_id, 0) # 获取完成时间，没有则默认为0
                status_list.append(status_info)

        # 可能需要将未入场但存在碎片图片的也加入列表（如果设计要求图库显示所有图片状态的话）
        # 目前需求是只显示已入场，所以上面过滤是正确的。

        return status_list

    def set_image_state(self, image_id, state):
        """
        设置指定图片的完成状态。

        Args:
            image_id (int): 图片ID
            state (str): 新状态 ('unentered', 'unlit', 'lit')
        """
        # 只有当 image_id 在 ImageManager 已知的图片列表中才更新状态
        if image_id in self.pieces_surfaces:
            old_status = self.image_status.get(image_id, 'unentered')
            self.image_status[image_id] = state
            print(f"图片 {image_id} 状态改变: {old_status} -> {state}") # 调试信息
            if state == 'lit' and old_status != 'lit':
                 # 如果状态从非lit变为lit，记录完成时间
                 self.completed_times[image_id] = time.time() # 记录点亮时间
        else:
             print(f"警告: 尝试设置未知图片ID {image_id} 的状态为 {state}。")


    def get_thumbnail(self, image_id):
         """获取指定图片的缩略图surface，用于图库列表"""
         if image_id in self.processed_full_images:
             full_img = self.processed_full_images[image_id]
             # 从处理后的完整图片生成一个缩放的缩略图
             try:
                thumbnail = pygame.transform.scale(full_img, (settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT))
                # 灰度化处理将在Gallery类中进行
                return thumbnail
             except pygame.error as e:
                 print(f"警告: 无法为图片 {image_id} 生成缩略图: {e}")
                 return None # 返回None表示失败
         # 如果 processed_full_images 不存在 (例如加载缓存碎片时没有生成完整图)，可以尝试从碎片拼合，但这比较复杂
         # 或者返回一个占位符
         print(f"警告: 无法获取图片 {image_id} 的完整处理后图片，无法生成缩略图。")
         return None


    def get_full_processed_image(self, image_id):
         """获取指定图片的完整处理后的surface (用于图库大图查看)"""
         return self.processed_full_images.get(image_id) # 如果图片ID不存在，返回None


    # def _grayscale_surface(self, surface): ... (辅助函数，通常放在utils或Gallery中)