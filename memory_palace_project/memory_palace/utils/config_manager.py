import json
import os
import logging
from .constants import SETTINGS_FILE_PATH

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, settings_path=SETTINGS_FILE_PATH):
        self.settings_path = settings_path
        self.config = self._load_config()

    def _load_config(self):
        default_config = { # 提供一些基础默认值，以防文件不存在或部分缺失
            "debug_mode": False,
            "logging_level": "INFO",
            "window": {
                "default_width": 1024,
                "default_height": 768,
            }
            # ...更多默认值...
        }
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 可以选择性地合并默认配置，以确保所有键都存在
                    # default_config.update(loaded_config) # 简单覆盖
                    # 或者更复杂的深度合并
                    return loaded_config # 假设文件总是完整的
            else:
                logger.warning(f"Settings file not found at {self.settings_path}. Using default config and attempting to create file.")
                self._save_config(default_config) # 尝试创建默认配置文件
                return default_config
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.settings_path}. Using default config.")
            return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using default config.")
            return default_config

    def _save_config(self, config_data):
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True) # 确保目录存在
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Config saved to {self.settings_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")


    def get_setting(self, key, default_value=None):
        """获取配置项，支持点分路径 (e.g., 'window.default_width')"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else: # 如果路径中的某个部分不是字典，则无法继续查找
                    return default_value
            return value
        except KeyError:
            return default_value

    def set_setting(self, key, value):
        """设置配置项，支持点分路径，并保存"""
        keys = key.split('.')
        d = self.config
        for k in keys[:-1]:
            d = d.setdefault(k, {}) # 如果路径不存在则创建
        if keys:
            d[keys[-1]] = value
            self._save_config(self.config) # 保存更改
        else: # 如果key为空或无效
            logger.warning(f"Attempted to set setting with invalid key: {key}")