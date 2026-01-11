# 文件名: run.py
import tkinter as tk
from main_ui import MainApp

if __name__ == "__main__":
    # 处理高DPI显示器模糊问题 (Windows 11 必需)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()