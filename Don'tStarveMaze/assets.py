import pygame
import os
from settings import *
from typing import Optional # 导入需要用到的类型提示

class AssetManager:
    def __init__(self):
        """初始化资源管理器，加载所有图片和音效。"""
        self.images = {}          # 存储加载的图片 Surface 对象
        self.sounds = {}          # 存储加载的音效 Sound 对象
        self.default_font = None  # 存储默认字体对象
        self.load_assets()        # 调用加载函数
        self.load_font()          # 加载字体

    def load_assets(self):
        """加载所有在 settings.py 中定义的图片和音效。"""
        print("正在加载资源...")
        # 加载图片
        # --- 动态构建图片加载列表 ---
        files_to_load = IMAGE_FILES.copy() # 复制基础图片字典

        # 添加地形图片
        for i in range(1, NUM_BIOMES + 1):
            floor_key = f'floor_{i}'
            wall_key = f'wall_{i}'
            files_to_load[floor_key] = f'{BIOME_FLOOR_BASENAME}{i}.png'
            files_to_load[wall_key] = f'{BIOME_WALL_BASENAME}{i}.png'

        # 添加杂草图片
        for weed_base_name in WEED_FILES:
             files_to_load[weed_base_name] = f'{weed_base_name}.png'
        # --- 结束动态构建 ---


        # --- 开始加载 ---
        for key, filename in files_to_load.items(): # 使用新的完整列表
            path = os.path.join(IMAGE_FOLDER, filename)
            try:
                image = pygame.image.load(path)
                # 优化性能：如果图片没有 alpha 通道，使用 convert()
                # 如果有 alpha 通道（透明度），使用 convert_alpha()
                # 地板和墙壁可能不需要 convert_alpha()，取决于你的图片
                if image.get_alpha() is None and 'floor' not in key and 'wall' not in key:
                     image = image.convert()
                else:
                     image = image.convert_alpha()

                # --- 调整大小 ---
                target_size = None # 默认不缩放
                if 'item' in key or 'food' in key or 'weapon' in key and 'sword' in key: # weapon_sword_...
                    target_size = ITEM_IMAGE_SIZE
                elif 'monster' in key:
                    target_size = MONSTER_IMAGE_SIZE
                elif key == 'player':
                    target_size = PLAYER_IMAGE_SIZE
                elif key == 'ui_hunger':
                    target_size = (UI_ICON_SIZE, UI_ICON_SIZE)
                elif key == 'ui_match':
                    target_size = (UI_MATCH_WIDTH, UI_MATCH_HEIGHT)
                elif key in WEED_FILES: # 检查是否是杂草文件
                     target_size = WEED_IMAGE_SIZE
                # 地形瓦片默认使用 TILE_SIZE x TILE_SIZE，通常不需要缩放，除非图片源尺寸不同
                # elif 'floor' in key or 'wall' in key:
                #      if image.get_width() != TILE_SIZE or image.get_height() != TILE_SIZE:
                #           target_size = (TILE_SIZE, TILE_SIZE)

                if target_size:
                    image = pygame.transform.scale(image, target_size)
                # --- 结束调整大小 ---

                self.images[key] = image
                print(f"已加载图片: {filename} (Key: {key})")
            except pygame.error as e:
                print(f"加载图片 {filename} 时出错: {e}")
                # 提供一个备用的 Surface 对象，防止游戏因缺少图片而崩溃
                # 确定备用图像的大小
                fallback_size = TILE_SIZE # 默认为瓦片大小
                if target_size: fallback_size = target_size[0] # 如果有目标大小，用目标大小
                elif key == 'ui_match': fallback_size = UI_MATCH_WIDTH # 特殊处理火柴UI

                # 创建一个纯色方块作为备用图像
                fallback_surf = pygame.Surface((fallback_size, fallback_size) if key != 'ui_match' else (UI_MATCH_WIDTH, UI_MATCH_HEIGHT)).convert()
                # ... (备用颜色逻辑不变) ...
                color = GREY
                if 'wall' in key: color = DARKGREY
                elif 'floor' in key: color = LIGHTGREY
                elif key == 'player': color = WHITE
                elif 'monster' in key: color = RED
                elif 'item' in key: color = YELLOW
                elif 'food' in key: color = GREEN
                elif 'weapon' in key: color = BLUE
                elif key == 'exit': color = YELLOW
                elif key in WEED_FILES: color = (34, 139, 34) # 深绿色作为杂草备用

                fallback_surf.fill(color)
                self.images[key] = fallback_surf
                print(f"使用了 {filename} 的备用图像。")


        # 加载音效
        if pygame.mixer.get_init(): # 检查混音器是否已初始化
            for key, filename in SOUND_FILES.items():
                path = os.path.join(SOUND_FOLDER, filename)
                try:
                    # 背景音乐通常使用 music 模块加载，这里只记录路径，在主程序中加载
                    if key == 'background':
                        pass # 在 main.py 中使用 pygame.mixer.music.load()
                    else:
                        sound = pygame.mixer.Sound(path)
                        self.sounds[key] = sound
                        print(f"已加载音效: {filename}")
                except pygame.error as e:
                    print(f"加载音效 {filename} 时出错: {e}")
                    self.sounds[key] = None # 将失败的音效标记为 None
                except FileNotFoundError:
                    print(f"未找到音效文件: {filename}")
                    self.sounds[key] = None
        else:
            print("Pygame 混音器未初始化。跳过音效加载。")

    def load_font(self):
        """加载字体文件。"""
        try:
            self.default_font = pygame.font.Font(FONT_NAME, UI_FONT_SIZE)
            print(f"已加载字体: {FONT_NAME}")
        except IOError:
             print(f"找不到字体 {FONT_NAME}，将使用 Pygame 默认字体。")
             # 提供一个备用字体
             self.default_font = pygame.font.Font(None, UI_FONT_SIZE) # Pygame 的默认字体

    def get_image(self, key: str) -> pygame.Surface:
        """获取已加载的图片 Surface 对象。如果 key 不存在或加载失败，返回 None 或备用图像。"""
        img = self.images.get(key)
        if img is None:
            print(f"警告：尝试获取未加载的图片资源 '{key}'")
            # 返回一个小的透明方块或者别的默认图像？
            fallback = pygame.Surface((TILE_SIZE // 2, TILE_SIZE // 2), pygame.SRCALPHA)
            fallback.fill((255, 0, 255, 100)) # 半透明洋红色块表示错误
            return fallback
        return img

    def get_sound(self, key: str) -> Optional[pygame.mixer.Sound]:
        """获取已加载的音效 Sound 对象。如果 key 不存在或加载失败，返回 None。"""
        return self.sounds.get(key)

    def play_sound(self, key: str, loops: int = 0, volume: float = 1.0):
        """播放指定 key 的音效。"""
        sound = self.get_sound(key)
        if sound and pygame.mixer.get_init(): # 确保音效存在且混音器可用
            sound.set_volume(volume) # 设置音量
            sound.play(loops=loops) # 播放音效，loops=-1 表示无限循环

    def play_music(self, key: str, loops: int = -1, volume: float = 0.5):
        """播放指定 key 的背景音乐。"""
        if pygame.mixer.get_init():
            path = os.path.join(SOUND_FOLDER, SOUND_FILES.get(key, "")) # 获取音乐文件路径
            if os.path.exists(path):
                 try:
                     pygame.mixer.music.load(path)       # 加载音乐文件
                     pygame.mixer.music.set_volume(volume) # 设置音量
                     pygame.mixer.music.play(loops=loops) # 播放音乐，loops=-1 表示无限循环
                     print(f"正在播放背景音乐: {SOUND_FILES.get(key)}")
                 except pygame.error as e:
                     print(f"播放音乐 {SOUND_FILES.get(key)} 时出错: {e}")
            else:
                 print(f"未找到音乐文件: {path}")

    def stop_music(self):
        """停止播放背景音乐。"""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()   # 停止播放
            pygame.mixer.music.unload() # 卸载音乐文件，释放资源

    def get_font(self, size: int = UI_FONT_SIZE) -> pygame.font.Font:
        """获取指定大小的字体对象。"""
        # 允许方便地获取不同大小的字体，如果需要的话
        try:
            return pygame.font.Font(FONT_NAME, size)
        except IOError:
             # 如果指定字体找不到，回退到默认字体（但可能大小不对）
             return pygame.font.Font(None, size)