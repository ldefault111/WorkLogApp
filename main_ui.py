import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import threading
import sys
import json
import os
from PIL import Image, ImageDraw
import pystray

from data_manager import DataManager
from chart_engine import ReportWindow

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("My Work Timer V3.4")
        self.root.geometry("400x420")
        self.root.resizable(False, False)
        
        # 1. 加载数据管理器
        self.db = DataManager()
        
        # 2. 状态变量
        self.is_working = False
        self.start_time = None
        self.pomo_running = False
        self.pomo_remaining = 0
        
        self._setup_ui()
        self._setup_tray()
        
        # 启动时刷新一次今日时长
        self.update_today_total()
        
        # 拦截关闭事件 -> 最小化
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

    def _setup_ui(self):
        # --- 菜单栏配置 ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 1. 文件菜单 (新增)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="设置数据文件位置...", command=self.set_data_path)
        file_menu.add_separator()
        file_menu.add_command(label="退出程序", command=self.quit_app)

        # 2. 统计菜单
        stats_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="统计", menu=stats_menu)
        stats_menu.add_command(label="打开可视化报表", command=self.open_report)

        # --- 样式配置 ---
        style = ttk.Style()
        style.configure("Big.TLabel", font=("Microsoft YaHei UI", 28, "bold"))
        style.configure("Status.TLabel", font=("Microsoft YaHei UI", 10), foreground="#666")
        style.configure("Info.TLabel", font=("Microsoft YaHei UI", 11, "bold"), foreground="#007ACC")
        style.configure("Action.TButton", font=("Microsoft YaHei UI", 12))

        # --- 工作计时区 ---
        frame_work = ttk.LabelFrame(self.root, text="工作记录", padding=20)
        frame_work.pack(fill="x", padx=15, pady=10)
        
        self.lbl_timer = ttk.Label(frame_work, text="00:00:00", style="Big.TLabel", anchor="center")
        self.lbl_timer.pack(fill='x', pady=5)
        
        self.lbl_status = ttk.Label(frame_work, text="当前状态: 空闲", style="Status.TLabel", anchor="center")
        self.lbl_status.pack(fill='x', pady=(0, 5))

        # [修改] 今日累计时长
        self.lbl_today = ttk.Label(frame_work, text="今日累计: 0 h 0 min", style="Info.TLabel", anchor="center")
        self.lbl_today.pack(fill='x', pady=(0, 10))
        
        self.btn_work = ttk.Button(frame_work, text="开始工作", style="Action.TButton", command=self.toggle_work)
        self.btn_work.pack(fill='x', ipady=5)

        # --- 番茄钟区 ---
        frame_pomo = ttk.LabelFrame(self.root, text="番茄专注", padding=15)
        frame_pomo.pack(fill="x", padx=15, pady=5)
        
        input_frame = ttk.Frame(frame_pomo)
        input_frame.pack(fill='x', pady=5)
        
        ttk.Label(input_frame, text="时长(分钟):").pack(side='left')
        self.var_pomo_mins = tk.IntVar(value=self.db.config.get("pomodoro_duration", 25))
        self.spin_pomo = ttk.Spinbox(input_frame, from_=1, to=120, textvariable=self.var_pomo_mins, width=5)
        self.spin_pomo.pack(side='left', padx=5)
        
        self.btn_pomo = ttk.Button(input_frame, text="启动", command=self.toggle_pomo)
        self.btn_pomo.pack(side='right')

        self.lbl_pomo_timer = ttk.Label(frame_pomo, text="25:00", font=("Consolas", 16), foreground="#888")
        self.lbl_pomo_timer.pack(pady=5)

    # ===========================
    # 新增功能逻辑
    # ===========================
    def set_data_path(self):
        """设置数据文件路径 (支持选择现有文件 或 新建文件)"""
        # 获取当前路径作为默认打开位置
        current_path = os.path.abspath(self.db.data_file)
        current_dir = os.path.dirname(current_path)
        
        # 使用 asksaveasfilename，这样用户可以在对话框里输入新文件名
        # confirmoverwrite=False 表示如果你选了已有文件，不会弹窗提示"是否覆盖"，因为我们只是想选中它
        path = filedialog.asksaveasfilename(
            title="选择现有数据文件 或 输入文件名新建",
            initialdir=current_dir,
            defaultextension=".json",
            confirmoverwrite=False, 
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if path:
            try:
                # === 关键逻辑：如果是新文件，先初始化为 空列表 [] ===
                if not os.path.exists(path):
                    with open(path, 'w', encoding='utf-8') as f:
                        # 这里写入 [] 确保符合你强调的列表格式
                        json.dump([], f, indent=4)
                    print(f"已创建新数据文件: {path}")

                # 1. 更新内存配置
                self.db.config["data_path"] = path
                self.db.data_file = path
                
                # 2. 写入配置文件 (config.json)
                with open(self.db.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.db.config, f, indent=4)
                
                # 3. 刷新数据
                # 因为重新加载了文件，界面上的今日时间需要重置/重算
                self.update_today_total()
                
                messagebox.showinfo("设置成功", f"数据文件路径已更新为:\n{path}\n\n如果是新文件，已自动初始化。")
                
            except Exception as e:
                messagebox.showerror("设置失败", f"无法创建或读取文件:\n{e}")

    def update_today_total(self):
        """[修改] 刷新今日累计时长 (x h x min)"""
        total_sec = self.db.get_today_total_seconds()
        m, s = divmod(total_sec, 60)
        h, m = divmod(m, 60)
        self.lbl_today.config(text=f"今日累计: {int(h)} h {int(m)} min")

    # ===========================
    # 核心工作逻辑
    # ===========================
    def toggle_work(self):
        if not self.is_working:
            self.is_working = True
            self.start_time = datetime.datetime.now()
            self.btn_work.config(text="停止工作")
            self.lbl_status.config(text=f"工作中 (自 {self.start_time.strftime('%H:%M')})", foreground="#4CAF50")
            self._run_work_timer()
        else:
            self.stop_and_save()

    def stop_and_save(self):
        if self.is_working:
            self.is_working = False
            end_time = datetime.datetime.now()
            
            self.db.save_record(self.start_time, end_time)
            
            self.btn_work.config(text="开始工作")
            self.lbl_status.config(text="已停止，记录已保存", foreground="#666")
            self.lbl_timer.config(text="00:00:00")
            
            self.update_today_total()

    def _run_work_timer(self):
        if self.is_working:
            delta = datetime.datetime.now() - self.start_time
            total_seconds = int(delta.total_seconds())
            h, rem = divmod(total_seconds, 3600)
            m, s = divmod(rem, 60)
            self.lbl_timer.config(text=f"{h:02d}:{m:02d}:{s:02d}")
            self.root.after(1000, self._run_work_timer)

    # ===========================
    # 番茄钟逻辑
    # ===========================
    def toggle_pomo(self):
        if not self.pomo_running:
            # 自动联动工作记录
            if not self.is_working:
                self.toggle_work()
            
            try:
                mins = int(self.var_pomo_mins.get())
            except:
                mins = 25
            
            self.pomo_remaining = mins * 60
            self.pomo_running = True
            self.btn_pomo.config(text="取消")
            self.spin_pomo.config(state='disabled')
            self._run_pomo_timer()
        else:
            self.stop_pomo(completed=False)

    def stop_pomo(self, completed=True):
        self.pomo_running = False
        self.btn_pomo.config(text="启动")
        self.spin_pomo.config(state='normal')
        
        if completed:
            self.lbl_pomo_timer.config(text="完成!", foreground="#4CAF50")
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            messagebox.showinfo("番茄钟", "专注时间结束！休息一下！")
            self.root.attributes("-topmost", False)
        else:
            self.lbl_pomo_timer.config(text="00:00", foreground="#888")

    def _run_pomo_timer(self):
        if self.pomo_running and self.pomo_remaining > 0:
            self.pomo_remaining -= 1
            m, s = divmod(self.pomo_remaining, 60)
            self.lbl_pomo_timer.config(text=f"{m:02d}:{s:02d}", foreground="#FF5722")
            self.root.after(1000, self._run_pomo_timer)
        elif self.pomo_running and self.pomo_remaining <= 0:
            self.stop_pomo(completed=True)

    # ===========================
    # 辅助与托盘
    # ===========================
    def open_report(self):
        ReportWindow(self.root, self.db)

    def create_icon(self):
        image = Image.new('RGB', (64, 64), color=(76, 175, 80))
        dc = ImageDraw.Draw(image)
        dc.ellipse((10, 10, 54, 54), fill='white')
        dc.text((22, 20), "W", fill=(76, 175, 80))
        return image

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("显示主界面", self.show_window, default=True),
            pystray.MenuItem("退出程序", self.quit_app)
        )
        self.icon = pystray.Icon("WorkTimer", self.create_icon(), "Work Timer", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon=None, item=None):
        """完全退出程序"""
        if self.is_working:
            end_time = datetime.datetime.now()
            self.db.save_record(self.start_time, end_time)
        
        if hasattr(self, 'icon'):
            self.icon.stop()
        
        self.root.after(0, self.root.destroy)
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()