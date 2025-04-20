import os
import tkinter as tk
from tkinter import filedialog, messagebox


def rename_files():
    folder_path = folder_var.get()
    names_file_path = names_file_var.get()

    # 检查输入是否有效
    if not folder_path or not names_file_path:
        messagebox.showerror("错误", "请选择文件夹和名字列表文件！")
        return

    if not os.path.exists(folder_path) or not os.path.exists(names_file_path):
        messagebox.showerror("错误", "所选文件夹或名字列表文件不存在，请重新选择！")
        return

    try:
        # 读取名字列表文件
        with open(names_file_path, 'r', encoding='utf-8') as f:
            names = [line.strip() for line in f.readlines() if line.strip()]

        # 获取文件夹中的所有文件
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

        if len(files) > len(names):
            messagebox.showerror("错误", "名字列表中的名字数量少于文件夹中的文件数量，请补充名字列表！")
            return

        # 依次重命名文件
        for i, file in enumerate(files):
            old_file_path = os.path.join(folder_path, file)
            file_extension = os.path.splitext(file)[1]
            new_file_name = names[i] + file_extension
            new_file_path = os.path.join(folder_path, new_file_name)
            os.rename(old_file_path, new_file_path)

        messagebox.showinfo("成功", "文件重命名成功！")
    except Exception as e:
        messagebox.showerror("错误", f"重命名过程中出现错误：{str(e)}")


def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)


def select_names_file():
    names_file = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
    if names_file:
        names_file_var.set(names_file)


# 创建主窗口
root = tk.Tk()
root.title("文件重命名工具")

# 变量
folder_var = tk.StringVar()
names_file_var = tk.StringVar()

# 文件夹选择
tk.Label(root, text="选择文件夹：").grid(row=0, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=folder_var, width=50).grid(row=0, column=1, padx=10, pady=5)
tk.Button(root, text="选择", command=select_folder).grid(row=0, column=2, padx=10, pady=5)

# 名字列表文件选择
tk.Label(root, text="选择名字列表文件：").grid(row=1, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=names_file_var, width=50).grid(row=1, column=1, padx=10, pady=5)
tk.Button(root, text="选择", command=select_names_file).grid(row=1, column=2, padx=10, pady=5)

# 重命名按钮
tk.Button(root, text="开始重命名", command=rename_files).grid(row=2, column=1, padx=10, pady=20)

# 运行主循环
root.mainloop()
    