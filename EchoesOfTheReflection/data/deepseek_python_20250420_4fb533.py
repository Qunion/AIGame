import json
import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
from collections.abc import MutableMapping

class JSONTableConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON/表格双向转换工具 v2.0")
        
        # 初始化界面组件
        self.create_widgets()
        
        # 文件路径变量
        self.json_to_table_paths = {"input": "", "output": ""}
        self.table_to_json_paths = {"input": "", "output": ""}

    def create_widgets(self):
        # 创建主容器
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # JSON转表格区域
        ttk.Label(main_frame, text="【JSON转表格】", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, pady=5)
        
        ttk.Label(main_frame, text="JSON文件:").grid(row=1, column=0, padx=5, pady=2)
        self.json_entry = ttk.Entry(main_frame, width=40)
        self.json_entry.grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="选择文件", command=lambda: self.select_file(self.json_entry, "JSON文件", [("JSON文件", "*.json")])).grid(row=1, column=2)

        ttk.Label(main_frame, text="保存路径:").grid(row=2, column=0, padx=5, pady=2)
        self.excel_entry = ttk.Entry(main_frame, width=40)
        self.excel_entry.grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="选择路径", command=lambda: self.select_file(self.excel_entry, "Excel文件", [("Excel文件", "*.xlsx")], save=True)).grid(row=2, column=2)

        ttk.Button(main_frame, text="开始转换 →", command=self.convert_json_to_table).grid(row=3, column=1, pady=5)

        # 分割线
        ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, columnspan=3, pady=10, sticky='ew')

        # 表格转JSON区域
        ttk.Label(main_frame, text="【表格转JSON】", font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=3, pady=5)
        
        ttk.Label(main_frame, text="Excel文件:").grid(row=6, column=0, padx=5, pady=2)
        self.excel_input_entry = ttk.Entry(main_frame, width=40)
        self.excel_input_entry.grid(row=6, column=1, padx=5)
        ttk.Button(main_frame, text="选择文件", command=lambda: self.select_file(self.excel_input_entry, "Excel文件", [("Excel文件", "*.xlsx")])).grid(row=6, column=2)

        ttk.Label(main_frame, text="保存路径:").grid(row=7, column=0, padx=5, pady=2)
        self.json_output_entry = ttk.Entry(main_frame, width=40)
        self.json_output_entry.grid(row=7, column=1, padx=5)
        ttk.Button(main_frame, text="选择路径", command=lambda: self.select_file(self.json_output_entry, "JSON文件", [("JSON文件", "*.json")], save=True)).grid(row=7, column=2)

        ttk.Button(main_frame, text="开始转换 →", command=self.convert_table_to_json).grid(row=8, column=1, pady=5)

        # 状态栏
        self.status = ttk.Label(main_frame, text="就绪", foreground="gray")
        self.status.grid(row=9, column=0, columnspan=3, pady=10)

    def select_file(self, entry_widget, title, filetypes, save=False):
        """通用文件选择方法"""
        if save:
            path = filedialog.asksaveasfilename(title=title, filetypes=filetypes)
        else:
            path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    @staticmethod
    def json_to_table(json_data, explode_arrays=True, separator='_', null_value='NaN'):
        """增强版JSON转表格逻辑"""
        def recursive_flatten(d, parent_key='', sep='_'):
            """递归展平嵌套结构，处理列表中的字典"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, MutableMapping):
                    items.extend(recursive_flatten(v, new_key, sep).items())
                elif isinstance(v, list):
                    for i, elem in enumerate(v):
                        if isinstance(elem, (dict, list)):
                            items.extend(recursive_flatten(
                                {f"{new_key}_item{i}": elem}, sep=sep
                            ).items())
                        else:
                            items.append((f"{new_key}_item{i}", elem))
                else:
                    items.append((new_key, v))
            return dict(items)

        # 统一数据格式
        data = [json_data] if isinstance(json_data, dict) else json_data
        
        # 展平所有结构（修复这里的关键参数）
        flattened = []
        for item in data:
            flat_item = recursive_flatten(item, sep=separator)  # 关键修复点
            flattened.append(flat_item)

        # 创建DataFrame并处理类型
        df = pd.DataFrame(flattened)
        
        # 处理列表型数据
        if explode_arrays:
            list_cols = [col for col in df.columns if df[col].apply(
                lambda x: isinstance(x, list)).any()]
            for col in list_cols:
                df = df.explode(col)

        # 增强的空值处理
        df = df.replace([None], null_value)
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].where(pd.notnull(df[col]), null_value)
        
        return df.reset_index(drop=True)

    def convert_json_to_table(self):
        """增强文件类型处理"""
        try:
            input_path = self.json_entry.get()
            output_path = self.excel_entry.get()
            
            if not input_path.lower().endswith('.json'):
                raise ValueError("输入文件必须是JSON格式")
                
            with open(input_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            df = self.json_to_table(json_data)
            
            # 自动识别引擎
            if output_path.lower().endswith('.xlsx'):
                engine = 'openpyxl'
            elif output_path.lower().endswith('.xls'):
                engine = 'xlwt'
            else:
                raise ValueError("不支持的Excel格式")
            
            df.to_excel(output_path, index=False, engine=engine)
            self.status.config(text="转换成功！", foreground="green")
        except Exception as e:
            self.status.config(text=f"错误: {str(e)}", foreground="red")

    @staticmethod
    def table_to_json(df, separator='_'):
        """智能嵌套重建"""
        def build_nested_structure(row):
            result = {}
            for full_key, value in row.items():
                if pd.isna(value):
                    continue
                keys = full_key.split(separator)
                current = result
                for key in keys[:-1]:
                    if '_item' in key and key.split('_item')[0] in current:
                        base_key, idx = key.split('_item')
                        idx = int(idx)
                        if idx >= len(current[base_key]):
                            current[base_key].append({})
                        current = current[base_key][idx]
                    else:
                        if key not in current:
                            current[key] = {} if '_item' not in keys[keys.index(key)+1] else []
                        current = current[key]
                last_key = keys[-1]
                if '_item' in last_key:
                    base_key, idx = last_key.split('_item')
                    idx = int(idx)
                    if base_key not in current:
                        current[base_key] = []
                    while len(current[base_key]) <= idx:
                        current[base_key].append(None)
                    current[base_key][idx] = value
                else:
                    current[last_key] = value
            return result
        
        return [build_nested_structure(row) for _, row in df.iterrows()]

    def convert_table_to_json(self):
        """表格转JSON处理"""
        try:
            input_path = self.excel_input_entry.get()
            output_path = self.json_output_entry.get()
            
            if not input_path or not output_path:
                raise ValueError("请先选择输入文件和输出路径")
            
            df = pd.read_excel(input_path)
            json_data = self.table_to_json(df)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            self.status.config(text="表格转JSON成功！", foreground="green")
        except Exception as e:
            self.status.config(text=f"错误: {str(e)}", foreground="red")

if __name__ == "__main__":
    pd.set_option('future.no_silent_downcasting', True)
    root = tk.Tk()
    root.geometry("600x450")
    app = JSONTableConverter(root)
    root.mainloop()