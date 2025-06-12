# FILENAME: input_dialog.py
#
# 使用 tkinter 创建一个非阻塞的、可从外部控制的输入对话框。

import tkinter as tk
import threading
import queue

class Dialog(tk.Toplevel):
    """一个非阻塞的、可通过队列通信的对话框"""
    def __init__(self, parent, q, title, prompt):
        super().__init__(parent)
        self.queue = q
        self.withdraw() # 先隐藏
        
        # --- 窗口属性 ---
        self.title(title)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.bind("<Return>", self._on_ok)
        self.bind("<Escape>", self._on_closing)

        # --- 控件 ---
        tk.Label(self, text=prompt, anchor="w").pack(padx=15, pady=(10, 5), fill="x")
        self.entry = tk.Entry(self, width=50)
        self.entry.pack(padx=15, pady=5, fill="x")
        self.entry.focus_set()

        btn_frame = tk.Frame(self)
        ok_btn = tk.Button(btn_frame, text="确定", command=self._on_ok, width=10, default=tk.ACTIVE)
        ok_btn.pack(side=tk.RIGHT, padx=5)
        cancel_btn = tk.Button(btn_frame, text="取消", command=self._on_closing, width=10)
        cancel_btn.pack(side=tk.RIGHT)
        btn_frame.pack(padx=15, pady=(5, 10), fill="x")

        # --- 定位并显示 ---
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - (self.winfo_width() / 2)
        y = parent.winfo_rooty() + (parent.winfo_height() / 3) - (self.winfo_height() / 2)
        self.geometry(f"+{int(x)}+{int(y)}")
        self.deiconify() # 显示窗口

    def _on_ok(self, event=None):
        self.queue.put(self.entry.get())

    def _on_closing(self, event=None):
        self.queue.put(None)

class TkinterThread(threading.Thread):
    """在独立线程中运行 tkinter 主循环"""
    def __init__(self, title, prompt):
        super().__init__()
        self.q = queue.Queue()
        self.title = title
        self.prompt = prompt
        self.root = None
        self.dialog = None
        self.daemon = True # 确保主程序退出时此线程也退出

    def run(self):
        self.root = tk.Tk()
        self.root.withdraw() # 隐藏根窗口
        self.dialog = Dialog(self.root, self.q, self.title, self.prompt)
        self.root.mainloop()

    def get_result(self):
        try:
            return self.q.get_nowait()
        except queue.Empty:
            return "NO_RESULT_YET"

    def close(self):
        if self.root:
            self.root.quit()

def ask_string_non_blocking(title, prompt):
    """启动一个非阻塞的输入对话框线程"""
    thread = TkinterThread(title, prompt)
    thread.start()
    return thread