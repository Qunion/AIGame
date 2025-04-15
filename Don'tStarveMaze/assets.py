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
        for key, filename in IMAGE_FILES.items():
            path = os.path.join(IMAGE_FOLDER, filename)
            try:
                image = pygame.image.load(path)
                # 优化性能：如果图片没有 alpha 通道，使用 convert()
                # 如果有 alpha 通道（透明度），使用 convert_alpha()
                # 地板和墙壁可能不需要 convert_alpha()，取决于你的图片
                if image.get_alpha() is None and key not in ['wall', 'floor']:
                     image = image.convert()
                else:
                     image = image.convert_alpha()

                # 根据 settings 中的定义调整图片大小
                if 'item' in key or 'food' in key or 'weapon' in key:
                     image = pygame.transform.scale(image, ITEM_IMAGE_SIZE)
                elif 'monster' in key:
                     image = pygame.transform.scale(image, MONSTER_IMAGE_SIZE)
                elif key == 'player':
                     image = pygame.transform.scale(image, PLAYER_IMAGE_SIZE)
                elif key == 'ui_hunger':
                     image = pygame.transform.scale(image, (UI_ICON_SIZE, UI_ICON_SIZE))
                elif key == 'ui_match':
                     image = pygame.transform.scale(image, (UI_MATCH_WIDTH, UI_MATCH_HEIGHT))
                # 可以为其他图片添加缩放逻辑，例如 'exit'

                self.images[key] = image
                print(f"已加载图片: {filename}")
            except pygame.error as e:
                print(f"加载图片 {filename} 时出错: {e}")
                # 提供一个备用的 Surface 对象，防止游戏因缺少图片而崩溃
                size = TILE_SIZE # 默认备用大小
                if 'item' in key or 'food' in key or 'weapon' in key: size = ITEM_IMAGE_SIZE[0]
                elif 'monster' in key: size = MONSTER_IMAGE_SIZE[0]
                elif key == 'player': size = PLAYER_IMAGE_SIZE[0]
                elif key == 'ui_hunger': size = UI_ICON_SIZE
                elif key == 'ui_match': size = UI_MATCH_WIDTH

                # 创建一个纯色方块作为备用图像
                fallback_surf = pygame.Surface((size, size) if key != 'ui_match' else (UI_MATCH_WIDTH, UI_MATCH_HEIGHT)).convert()

                color = GREY # 默认备用颜色
                if key == 'wall': color = DARKGREY
                elif key == 'floor': color = LIGHTGREY
                elif key == 'player': color = WHITE
                elif 'monster' in key: color = RED
                elif 'item' in key: color = YELLOW
                elif 'food' in key: color = GREEN
                elif 'weapon' in key: color = BLUE
                elif key == 'exit': color = YELLOW # 出口备用颜色

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
        return self.images.get(key)

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