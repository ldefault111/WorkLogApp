import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import threading
import sys
from PIL import Image, ImageDraw
import pystray

from data_manager import DataManager
from chart_engine import ReportWindow

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("My Work Timer V3.3")
        self.root.geometry("400x420") # 稍微调高一点高度以容纳新标签
        self.root.resizable(False, False)
        
        self.db = DataManager()
        
        self.is_working = False
        self.start_time = None
        self.pomo_running = False
        self.pomo_remaining = 0
        
        self._setup_ui()
        self._setup_tray()
        
        # 启动时刷新一次今日时长
        self.update_today_total()
        
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

    def _setup_ui(self):
        # 菜单
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        stats_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="统计报表", menu=stats_menu)
        stats_menu.add_command(label="打开可视化报表", command=self.open_report)

        # 样式
        style = ttk.Style()
        style.configure("Big.TLabel", font=("Microsoft YaHei UI", 28, "bold"))
        style.configure("Status.TLabel", font=("Microsoft YaHei UI", 10), foreground="#666")
        style.configure("Info.TLabel", font=("Microsoft YaHei UI", 11, "bold"), foreground="#007ACC") # 新样式
        style.configure("Action.TButton", font=("Microsoft YaHei UI", 12))

        # --- 区域1: 工作计时 ---
        frame_work = ttk.LabelFrame(self.root, text="工作记录", padding=20)
        frame_work.pack(fill="x", padx=15, pady=10)
        
        self.lbl_timer = ttk.Label(frame_work, text="00:00:00", style="Big.TLabel", anchor="center")
        self.lbl_timer.pack(fill='x', pady=5)
        
        self.lbl_status = ttk.Label(frame_work, text="当前状态: 空闲", style="Status.TLabel", anchor="center")
        self.lbl_status.pack(fill='x', pady=(0, 5))

        # [新增] 今日累计时长
        self.lbl_today = ttk.Label(frame_work, text="今日累计: 0.0h", style="Info.TLabel", anchor="center")
        self.lbl_today.pack(fill='x', pady=(0, 10))
        
        self.btn_work = ttk.Button(frame_work, text="开始工作", style="Action.TButton", command=self.toggle_work)
        self.btn_work.pack(fill='x', ipady=5)

        # --- 区域2: 番茄钟 ---
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

    def update_today_total(self):
        """刷新今日累计时长"""
        total_sec = self.db.get_today_total_seconds()
        hours = total_sec / 3600.0
        self.lbl_today.config(text=f"今日累计: {hours:.1f} 小时")

    # ===========================
    # 工作逻辑
    # ===========================
    def toggle_work(self):
        if not self.is_working:
            # 开始工作
            self.is_working = True
            self.start_time = datetime.datetime.now()
            self.btn_work.config(text="停止工作")
            self.lbl_status.config(text=f"工作中 (自 {self.start_time.strftime('%H:%M')})", foreground="#4CAF50")
            self._run_work_timer()
        else:
            # 停止工作
            self.stop_and_save()

    def stop_and_save(self):
        if self.is_working:
            self.is_working = False
            end_time = datetime.datetime.now()
            
            # 保存数据
            self.db.save_record(self.start_time, end_time)
            
            # UI重置
            self.btn_work.config(text="开始工作")
            self.lbl_status.config(text="已停止，记录已保存", foreground="#666")
            self.lbl_timer.config(text="00:00:00")
            
            # 停止工作时，强制停止番茄钟（可选逻辑，根据你之前的需求，这里可以不强制，但通常下班了番茄钟也没必要跑了）
            # 如果你想保留番茄钟继续跑，注释掉下面这行
            # self.stop_pomo(completed=False) 
            
            # 刷新今日统计
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
            # --- 修复逻辑: 自动触发开始工作 ---
            if not self.is_working:
                print("番茄钟触发自动工作记录...")
                self.toggle_work()
            # -------------------------------
            
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
        """停止番茄钟内部逻辑"""
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
    # 辅助功能
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
        if self.is_working:
            end_time = datetime.datetime.now()
            # 退出时也使用带过滤的 save_record
            self.db.save_record(self.start_time, end_time)
        self.icon.stop()
        self.root.after(0, self.root.destroy)
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()