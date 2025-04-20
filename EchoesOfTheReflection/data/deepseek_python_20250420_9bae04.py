import json
import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
from collections.abc import MutableMapping

class JSONTableConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON/表格双向转换工具 v2.0")
        
        # 初始化界面
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

    def convert_json_to_table(self):
        """处理JSON转表格的转换"""
        try:
            input_path = self.json_entry.get()
            output_path = self.excel_entry.get()
            
            if not input_path or not output_path:
                raise ValueError("请先选择输入文件和输出路径")
            
            with open(input_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            df = self.json_to_table(json_data)
            df.to_excel(output_path, index=False)
            
            self.status.config(text="JSON转表格成功！", foreground="green")
        except Exception as e:
            self.status.config(text=f"错误: {str(e)}", foreground="red")

    def convert_table_to_json(self):
        """处理表格转JSON的转换"""
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

    @staticmethod
    def json_to_table(json_data, explode_arrays=True, separator='_', null_value='NaN'):
        """JSON转表格核心逻辑"""
        if isinstance(json_data, dict):
            data = [json_data]
        else:
            data = json_data

        flattened = []
        for item in data:
            flat_item = JSONTableConverter.flatten(item, separator=separator)
            flattened.append(flat_item)

        df = pd.DataFrame(flattened)
        
        if explode_arrays:
            list_columns = [col for col in df.columns if df[col].apply(lambda x: isinstance(x, list)).any()]
            for col in list_columns:
                df = df.explode(col).reset_index(drop=True)

        df.fillna(null_value, inplace=True)
        return df

    @staticmethod
    def flatten(d, parent_key='', separator='_'):
        """递归展平嵌套字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{separator}{k}" if parent_key else k
            if isinstance(v, MutableMapping):
                items.extend(JSONTableConverter.flatten(v, new_key, separator).items())
            elif isinstance(v, list):
                for i, elem in enumerate(v):
                    if isinstance(elem, (dict, list)):
                        items.extend(JSONTableConverter.flatten({f"{new_key}_{i}": elem}, separator=separator).items())
                    else:
                        items.append((new_key, v))
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def table_to_json(df, separator='_'):
        """表格转JSON核心逻辑"""
        data = []
        for _, row in df.iterrows():
            current_dict = {}
            for col_name, value in row.items():
                keys = col_name.split(separator)
                current_level = current_dict
                for key in keys[:-1]:
                    if key not in current_level:
                        current_level[key] = {}
                    current_level = current_level[key]
                last_key = keys[-1]
                current_level[last_key] = value if pd.notnull(value) else None
            data.append(current_dict)
        return data

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x450")
    app = JSONTableConverter(root)
    root.mainloop()