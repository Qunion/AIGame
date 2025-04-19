# src/save_manager.py
import json
import os

class SaveManager:
    """管理游戏进度保存和加载"""

    def __init__(self, save_file_path):
        """初始化保存管理器"""
        self.save_file_path = save_file_path

    def save_game(self, game_state: dict):
        """保存游戏状态到文件"""
        try:
            with open(self.save_file_path, 'w', encoding='utf-8') as f:
                json.dump(game_state, f, indent=4)
            print("游戏进度已保存。")
        except IOError as e:
            print(f"警告：无法保存游戏进度到 {self.save_file_path}: {e}")

    def load_game(self) -> dict | None:
        """从文件加载游戏状态"""
        if not os.path.exists(self.save_file_path):
            print("未找到保存文件。")
            return None

        try:
            with open(self.save_file_path, 'r', encoding='utf-8') as f:
                game_state = json.load(f)
            print("游戏进度已加载。")
            return game_state
        except (IOError, json.JSONDecodeError) as e:
            print(f"警告：无法加载游戏进度从 {self.save_file_path}: {e}")
            # TODO: 可以备份损坏的保存文件
            return None