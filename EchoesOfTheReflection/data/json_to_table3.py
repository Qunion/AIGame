import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog


def json_to_table(json_file_path, xlsx_file_path):
    try:
        # 读取 JSON 文件
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # 处理空 JSON 数据
        if not data:
            return "JSON 数据为空。"

        # 自动识别表头字段
        header_fields = set()
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    header_fields.update(item.keys())
        elif isinstance(data, dict):
            for value in data.values():
                if isinstance(value, dict):
                    header_fields.update(value.keys())
        header_fields = sorted(header_fields)

        rows = []
        if isinstance(data, list):
            for item in data:
                row = []
                for field in header_fields:
                    row.append(item.get(field, ""))
                rows.append(row)
        elif isinstance(data, dict):
            for key, value in data.items():
                row = [key]
                for field in header_fields:
                    row.append(value.get(field, ""))
                rows.append(row)

        # 再次检查列数是否一致
        if rows:
            actual_columns = len(rows[0])
            if actual_columns != len(header_fields):
                # 重新生成表头
                header_fields = [f"Column_{i}" for i in range(actual_columns)]

        df = pd.DataFrame(rows, columns=header_fields)

        # 将数据框写入 XLSX 文件
        df.to_excel(xlsx_file_path, index=False)
        return f"成功将 JSON 数据转换为表格并写入 {xlsx_file_path}。"
    except FileNotFoundError:
        return f"未找到 JSON 文件: {json_file_path}"
    except json.JSONDecodeError:
        return "无法解析 JSON 数据，请检查数据格式。"
    except Exception as e:
        return f"发生未知错误: {e}"


def select_json_file():
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    json_entry.delete(0, tk.END)
    json_entry.insert(0, file_path)


def select_xlsx_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    xlsx_entry.delete(0, tk.END)
    xlsx_entry.insert(0, file_path)


def convert_json_to_table():
    json_file_path = json_entry.get()
    xlsx_file_path = xlsx_entry.get()
    result = json_to_table(json_file_path, xlsx_file_path)
    result_label.config(text=result)
    if "成功" not in result:
        result_label.config(fg="red")
    else:
        result_label.config(fg="green")


# 创建主窗口
root = tk.Tk()
root.title("JSON 转 XLSX 工具")

# 创建并布局组件
json_label = tk.Label(root, text="选择 JSON 文件:")
json_label.pack(pady=5)

json_entry = tk.Entry(root, width=50)
json_entry.pack(pady=5)

json_button = tk.Button(root, text="选择文件", command=select_json_file)
json_button.pack(pady=5)

xlsx_label = tk.Label(root, text="选择保存的 XLSX 文件:")
xlsx_label.pack(pady=5)

xlsx_entry = tk.Entry(root, width=50)
xlsx_entry.pack(pady=5)

xlsx_button = tk.Button(root, text="选择文件", command=select_xlsx_file)
xlsx_button.pack(pady=5)

convert_button = tk.Button(root, text="转换", command=convert_json_to_table)
convert_button.pack(pady=20)

result_label = tk.Label(root, text="", fg="black")
result_label.pack(pady=10)

# 运行主循环
root.mainloop()