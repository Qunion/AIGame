# FILENAME: input_dialog.py
#
# 使用 tkinter 创建一个原生的输入对话框，以完美支持系统输入法。

import tkinter as tk
from tkinter import simpledialog

def ask_string(title, prompt):
    """
    弹出一个输入对话框并返回用户输入的字符串。
    
    Args:
        title (str): 对话框的标题。
        prompt (str): 对话框内的提示信息。

    Returns:
        str or None: 用户输入的字符串，如果用户取消则返回 None。
    """
    # 创建一个隐藏的根窗口，这样主对话框就不会附带一个多余的 tk 窗口
    root = tk.Tk()
    root.withdraw()
    
    # 设置对话框使其总在最前
    root.attributes("-topmost", True)
    
    # 弹出 simpledialog
    user_input = simpledialog.askstring(title, prompt, parent=root)
    
    # 销毁根窗口
    root.destroy()
    
    return user_input