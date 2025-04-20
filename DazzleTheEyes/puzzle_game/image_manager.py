# image_manager.py
# 负责图片的加载、处理、碎片生成、管理图片状态和提供碎片/完整图资源

import pygame
import settings
import os
import time # 用于记录完成时间
from piece import Piece # <--- 添加这一行！

# 尝试导入 Pillow 库，用于更灵活的图像处理
try:
    from PIL import Image
    # Pillow需要和Pygame兼容的格式，通常是RGB或RGBA
    # 如果PIL加载的图片模式不是'RGB'或'RGBA'，需要转换
    # 还需要确保PIL的图像能转换为Pygame的Surface
    PIL_AVAILABLE = True
except ImportError:
    print("警告: Pillow库未安装。图像处理功能将受限。建议安装: pip install Pillow")
    PIL_AVAILABLE = False


class ImageManager:
    def __init__(self):
        """初始化图像管理器，加载和处理所有原始图片"""
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
        self.next_image_to_consume_id = -1 # 使用图片ID，初始时需要确定第一张可消耗的图片ID
        self.pieces_consumed_from_current_image = 0 # 当前正在消耗的图片已消耗的碎片数量

        self.load_and_process_images() # 初始化时加载和处理所有图片
        self._initialize_consumption() # 初始化碎片消耗机制

    def load_and_process_images(self):
        """加载assets目录下的所有原始图片，进行处理并分割碎片"""
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

                # 加载原始图片 (使用Pygame加载)
                original_img_pg = pygame.image.load(full_path).convert_alpha() # 加载并保持透明度

                # 处理图片尺寸 (缩放和居中裁剪)，使其适合分割成 settings.IMAGE_LOGIC_ROWS x settings.IMAGE_LOGIC_COLS
                # 目标尺寸是 settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE 宽 x settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE 高
                target_width = settings.IMAGE_LOGIC_COLS * settings.PIECE_SIZE # 9 * 120 = 1080
                target_height = settings.IMAGE_LOGIC_ROWS * settings.PIECE_SIZE # 5 * 120 = 600
                target_size = (target_width, target_height)

                processed_img_pg = self._process_image_for_pieces(original_img_pg, target_size)

                self.processed_full_images[image_id] = processed_img_pg # 存储处理后的完整图片 (用于图库大图)
                self.image_status[image_id] = 'unentered' # 初始状态为未入场
                self.pieces_surfaces[image_id] = {} # 为该图片创建一个碎片表面字典

                # 将处理后的图片分割成 settings.IMAGE_LOGIC_ROWS x settings.IMAGE_LOGIC_COLS 个碎片
                self._split_image_into_pieces(image_id, processed_img_pg)

                # 可以选择将生成的碎片保存为文件，方便调试 (可选，暂时不实现)
                # self._save_pieces_to_files(image_id)

            except pygame.error as e:
                print(f"错误: Pygame无法加载或处理图片 {filename}: {e}")
            except Exception as e:
                print(f"错误: 处理图片 {filename} 时发生未知错误: {e}")

        print("所有图片处理完成。") # 调试信息


    def _process_image_for_pieces(self, image_surface_pg, target_size):
        """
        将 Pygame Surface 缩放和居中裁剪到目标尺寸 (target_width, target_height)。
        优先使用 Pygame 的功能，如果需要复杂裁剪且 PIL 可用，可以切换实现。
        """
        img_w, img_h = image_surface_pg.get_size()
        target_w, target_h = target_size

        # 计算原始图片和目标尺寸的宽高比
        img_aspect = img_w / img_h if img_h > 0 else 1 # 避免除以零
        target_aspect = target_w / target_h if target_h > 0 else 1 # 避免除以零

        # 计算缩放后的尺寸
        if img_aspect > target_aspect:
            # 原始图偏宽，按目标高度缩放，宽度会超出，需要裁剪两侧
            scaled_h = target_h
            scaled_w = int(scaled_h * img_aspect)
        else:
            # 原始图偏高或比例接近，按目标宽度缩放，高度会超出或刚好，需要裁剪上下
            scaled_w = target_w
            scaled_h = int(scaled_w / img_aspect)

        # 使用 Pygame 进行缩放
        # Check if scaled size is valid before scaling
        if scaled_w <= 0 or scaled_h <= 0:
            print(f"警告: 缩放尺寸无效 ({scaled_w}x{scaled_h})，跳过图片处理。原始尺寸: {img_w}x{img_h}, 目标尺寸: {target_w}x{target_h}")
            # 返回一个空白的Surface或者None，避免后续错误
            return pygame.Surface(target_size, pygame.SRCALPHA) # 返回一个空的透明Surface


        scaled_img_pg = pygame.transform.scale(image_surface_pg, (scaled_w, scaled_h))

        # 计算裁剪区域
        crop_x = (scaled_w - target_w) // 2
        crop_y = (scaled_h - target_h) // 2

        # 使用 Pygame 的 subsurface 进行裁剪
        # 确保裁剪区域在 scaled_img_pg 范围内
        if crop_x < 0 or crop_y < 0 or crop_x + target_w > scaled_w or crop_y + target_h > scaled_h:
             print(f"警告: 裁剪区域超出缩放图片范围。缩放尺寸: {scaled_w}x{scaled_h}, 裁剪区域: ({crop_x},{crop_y}) {target_w}x{target_h}")
             # 返回一个空白的Surface或者scaled_img_pg的一部分，尽量避免崩溃
             return pygame.Surface(target_size, pygame.SRCALPHA) # 返回一个空的透明Surface


        # subsurface 不会复制像素，而是创建一个视图。copy()可以创建独立的surface
        cropped_img_pg = scaled_img_pg.subsurface((crop_x, crop_y, target_w, target_h)).copy()

        return cropped_img_pg

    # def _process_image_for_pieces_with_pil(self, image_surface_pg, target_size):
    #     """使用Pillow进行更复杂的图像处理 (如果需要)"""
    #     if not PIL_AVAILABLE:
    #         print("错误: PIL未安装，无法使用PIL处理图片。")
    #         return self._process_image_for_pieces(image_surface_pg, target_size) # 回退到Pygame处理

    #     try:
    #         # 将Pygame Surface转换为PIL Image
    #         pil_img = Image.frombytes("RGBA", image_surface_pg.get_size(), pygame.image.tostring(image_surface_pg, "RGBA"))

    #         # PIL的缩放和裁剪逻辑
    #         img_w, img_h = pil_img.size
    #         target_w, target_h = target_size
    #         img_aspect = img_w / img_h
    #         target_aspect = target_w / target_h

    #         if img_aspect > target_aspect:
    #             # 原始图偏宽，按高缩放
    #             scaled_h = target_h
    #             scaled_w = int(scaled_h * img_aspect)
    #         else:
    #             # 原始图偏高，按宽缩放
    #             scaled_w = target_w
    #             scaled_h = int(scaled_w / img_aspect)

    #         # PIL缩放 (使用高质量滤波器)
    #         scaled_pil_img = pil_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS) # 或者 Image.ANTIALIAS

    #         # 居中裁剪
    #         crop_x = (scaled_w - target_w) // 2
    #         crop_y = (scaled_h - target_h) // 2
    #         cropped_pil_img = scaled_pil_img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))

    #         # 将PIL Image转换回Pygame Surface
    #         # 确保模式兼容
    #         if cropped_pil_img.mode != 'RGBA':
    #              cropped_pil_img = cropped_pil_img.convert('RGBA')
    #         pygame_surface = pygame.image.fromstring(cropped_pil_img.tobytes(), cropped_pil_img.size, "RGBA")

    #         return pygame_surface

    #     except Exception as e:
    #         print(f"错误: 使用PIL处理图片失败: {e}")
    #         return self._process_image_for_pieces(image_surface_pg, target_size) # 回退到Pygame处理


    def _split_image_into_pieces(self, image_id, processed_image_surface):
        """将处理好的图片分割成碎片surface并存储"""
        img_w, img_h = processed_image_surface.get_size()
        piece_w, piece_h = settings.PIECE_SIZE, settings.PIECE_SIZE

        # 再次检查处理后的图片尺寸是否符合预期，避免分割错误
        expected_w = settings.IMAGE_LOGIC_COLS * piece_w
        expected_h = settings.IMAGE_LOGIC_ROWS * piece_h
        if img_w != expected_w or img_h != expected_h:
            print(f"警告: 图片ID {image_id} 处理后的尺寸 {img_w}x{img_h} 与预期 {expected_w}x{expected_h} 不符，无法正常分割碎片。")
            # 尝试分割，但可能会出错或生成不完整的碎片
            # return # 如果严格要求，可以直接返回

        for r in range(settings.IMAGE_LOGIC_ROWS):
            for c in range(settings.IMAGE_LOGIC_COLS):
                x = c * piece_w
                y = r * piece_h
                # 确保提取区域在 processed_image_surface 范围内
                if x + piece_w <= img_w and y + piece_h <= img_h:
                    # 从大图 surface 中提取碎片区域
                    # 使用copy()确保每个碎片surface是独立的，避免subsurface的视图问题
                    piece_surface = processed_image_surface.subsurface((x, y, piece_w, piece_h)).copy()
                    self.pieces_surfaces[image_id][(r, c)] = piece_surface
                    # print(f"  生成碎片: 图片{image_id}_行{r}_列{c}") # 调试信息
                else:
                     print(f"警告: 碎片 {image_id}_行{r}_列{c} 的提取区域 ({x},{y},{piece_w},{piece_h}) 超出图片范围 ({img_w}x{img_h})，跳过。")
                     # 可以选择在这里创建一个空白碎片或者占位符

    # def _save_pieces_to_files(self, image_id):
    #     """将生成的碎片 surface 保存为文件 (可选)"""
    #     # 确保碎片输出目录存在
    #     os.makedirs(settings.GENERATED_PIECE_DIR, exist_ok=True)
    #     for (r, c), piece_surface in self.pieces_surfaces[image_id].items():
    #         filepath = os.path.join(settings.GENERATED_PIECE_DIR, f"image_{image_id}_{r}_{c}.png")
    #         pygame.image.save(piece_surface, filepath)


    def _initialize_consumption(self):
        """确定第一张要消耗碎片的图片ID"""
        image_ids = sorted(self.pieces_surfaces.keys())
        if image_ids:
            # 第一张进入拼盘的图片将是 image_ids[0]
            # 但是，初始填充会从 image_ids[0] 开始，直到 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
            # 实际开始消耗的图片是 image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
            if settings.INITIAL_FULL_IMAGES_COUNT < len(image_ids):
                self.next_image_to_consume_id = image_ids[settings.INITIAL_FULL_IMAGES_COUNT]
                # 初始填充时已经从这张图片获取了 settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT 个碎片
                self.pieces_consumed_from_current_image = settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT
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
        image_ids = sorted(self.pieces_surfaces.keys()) # 按ID排序，确保顺序

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
                         # 注意：这里创建Piece对象时，需要传入碎片的surface，而不是piece_surface本身
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
             for r in range(settings.IMAGE_LOGIC_ROWS):
                 for c in range(settings.IMAGE_LOGIC_COLS):
                     if piece_count_from_current < settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                         if (r, c) in self.pieces_surfaces[current_consume_img_id]:
                             piece_surface = self.pieces_surfaces[current_consume_img_id][(r, c)]
                             initial_pieces_list.append(Piece(piece_surface, current_consume_img_id, r, c, -1, -1))
                             pieces_added_count += 1
                             piece_count_from_current += 1
                             # self.pieces_consumed_from_current_image += 1 # 这部分在_initialize_consumption中处理了
                         else:
                              print(f"警告: 图片 {current_consume_img_id} 的碎片 ({r},{c}) 表面不存在，无法创建Piece对象。")
                     else:
                         break # 达到指定数量
                 if piece_count_from_current == settings.INITIAL_PARTIAL_IMAGE_PIECES_COUNT:
                     break

             self.image_status[current_consume_img_id] = 'unlit' # 这张图片现在也是“未点亮”状态
             # self.next_image_to_consume_id 在_initialize_consumption中设置了

        print(f"总共获取了 {pieces_added_count} 个碎片用于初始填充。") # 调试信息
        if pieces_added_count > total_required_pieces:
             print(f"错误: 获取的初始碎片数量 {pieces_added_count} 多于拼盘总槽位 {total_required_pieces}！")
             # 截断列表，只取前144个 (虽然这可能不是你想要的，但可以避免溢出)
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

        print(f"需要填充 {pieces_needed} 个空位...") # 调试信息

        # 如果当前没有需要消耗的图片了
        if self.next_image_to_consume_id is None:
             print("警告: 没有更多图片可供消耗碎片。")
             return []

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

            print(f"从图片 {current_img_id} 剩余 {pieces_remaining_in_current_img} 个，本次尝试获取 {pieces_to_take_from_current} 个。") # 调试信息

            if pieces_to_take_from_current > 0:
                # 从当前图片获取碎片，按照逻辑顺序继续上次消耗的位置
                pieces_taken_count = 0
                # 根据 self.pieces_consumed_from_current_image 计算开始的逻辑 (row, col)
                start_total_index = self.pieces_consumed_from_current_image # 总碎片索引
                # print(f"上次消耗总索引: {start_total_index}") # 调试信息

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
                print(f"本次从图片 {current_img_id} 实际获取了 {pieces_taken_count} 个碎片。还需要 {pieces_needed} 个。") # 调试信息


            # 检查当前图片的碎片是否已消耗完
            if self.pieces_consumed_from_current_image >= total_pieces_in_current_img: # 使用 >= 确保健壮性
                print(f"图片 {current_img_id} 的碎片已消耗完或超出。") # 调试信息
                # 切换到下一张图片
                current_img_index += 1
                if current_img_index < len(image_ids):
                    self.next_image_to_consume_id = image_ids[current_img_index]
                    self.pieces_consumed_from_current_image = 0 # 重置消耗计数
                    self.image_status[self.next_image_to_consume_id] = 'unlit' # 新进入的图片状态变为未点亮
                    print(f"下一张消耗图片ID设置为: {self.next_image_to_consume_id}") # 调试信息
                else:
                    self.next_image_to_consume_id = None # 没有更多图片了
                    print("没有更多图片可供消耗。") # 调试信息
                # 如果切换图片，并且 pieces_needed 仍大于 0，循环会继续，尝试从下一张图片获取

            # 如果还需要碎片，但是已经没有下一张图片了
            if pieces_needed > 0 and self.next_image_to_consume_id is None:
                 print(f"警告: 需要 {count} 个碎片，但没有更多图片可用。最终只获取到 {len(new_pieces)} 个。")
                 break # 没有更多图片了，退出循环


        # 注意：新获取的碎片不需要打乱，它们会根据填充空位的顺序放置到拼盘中。
        return new_pieces

    def get_all_entered_pictures_status(self):
        """获取所有已入场（未点亮或已点亮）图片的ID、状态和完成时间"""
        status_list = []
        # 确保遍历顺序与图片ID一致
        image_ids = sorted(self.image_status.keys())

        for img_id in image_ids:
             status = self.image_status[img_id]
             # 图库中只显示 'unlit' 和 'lit' 状态的图片
             if status in ['unlit', 'lit']:
                status_info = {'id': img_id, 'state': status}
                if status == 'lit':
                    status_info['completion_time'] = self.completed_times.get(img_id, 0) # 获取完成时间，没有则默认为0
                status_list.append(status_info)
        return status_list

    def set_image_state(self, image_id, state):
        """
        设置指定图片的完成状态。

        Args:
            image_id (int): 图片ID
            state (str): 新状态 ('unentered', 'unlit', 'lit')
        """
        if image_id in self.image_status:
            old_status = self.image_status[image_id]
            self.image_status[image_id] = state
            print(f"图片 {image_id} 状态改变: {old_status} -> {state}") # 调试信息
            if state == 'lit' and old_status != 'lit':
                 # 如果状态从非lit变为lit，记录完成时间
                 self.completed_times[image_id] = time.time() # 记录点亮时间

    def get_thumbnail(self, image_id):
         """获取指定图片的缩略图surface，用于图库列表"""
         if image_id in self.processed_full_images:
             full_img = self.processed_full_images[image_id]
             # 从处理后的完整图片生成一个缩放的缩略图
             try:
                thumbnail = pygame.transform.scale(full_img, (settings.GALLERY_THUMBNAIL_WIDTH, settings.GALLERY_THUMBNAIL_HEIGHT))
                # 灰度化处理将在Gallery类中进行，以便Gallery根据图片状态决定是否灰度
                return thumbnail
             except pygame.error as e:
                 print(f"警告: 无法为图片 {image_id} 生成缩略图: {e}")
                 return None # 返回None表示失败
         return None # 图片ID不存在

    def get_full_processed_image(self, image_id):
         """获取指定图片的完整处理后的surface (用于图库大图查看)"""
         return self.processed_full_images.get(image_id) # 如果图片ID不存在，返回None

    # def _grayscale_surface(self, surface):
    #      """将一个Pygame Surface灰度化 (辅助函数)"""
    #      # 简单的灰度化实现 (从 utils.py 移动到这里或保持在 utils 中，取决于哪里更常用)
    #      # Gallery 类需要这个功能来灰度化缩略图
    #      gray_surface = pygame.Surface(surface.get_size(), depth=surface.get_depth())
    #      for x in range(surface.get_width()):
    #          for y in range(surface.get_height()):
    #              r, g, b, a = surface.get_at((x, y))
    #              gray = int(0.2989 * r + 0.5870 * g + 0.1140 * b) # CIE L*a*b* 灰度公式
    #              gray_surface.set_at((x, y), (gray, gray, gray, a))
    #      return gray_surface