# FILENAME: data_manager.py

import json
import os

USER_DATA_FILE = "mind_spark_user_data.json"
DEFAULT_DATA_FILE = "neurons.json"

class DataManager:
    def __init__(self):
        self.default_groups = [
            {"name": "默认组", "neurons": ["思维", "火花", "你好", "世界"]}
        ]

    def load_neuron_groups(self):
        """
        加载神经元组。
        加载顺序: 用户本地存储 -> 项目内置 a.json -> 硬编码默认值
        """
        # 1. 尝试从用户本地存储加载
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data and isinstance(data, list):
                        return data
            except (json.JSONDecodeError, IOError):
                print(f"警告: 无法解析用户数据文件 {USER_DATA_FILE}")

        # 2. 尝试从项目内置的 neurons.json 加载
        if os.path.exists(DEFAULT_DATA_FILE):
            try:
                with open(DEFAULT_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data and isinstance(data, list):
                        return data
            except (json.JSONDecodeError, IOError):
                print(f"警告: 无法解析默认数据文件 {DEFAULT_DATA_FILE}")

        # 3. 使用硬编码的默认值
        return self.default_groups

    def save_neuron_groups(self, groups):
        """将神经元组数据保存到用户本地文件"""
        try:
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(groups, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"错误: 无法保存用户数据到 {USER_DATA_FILE}: {e}")