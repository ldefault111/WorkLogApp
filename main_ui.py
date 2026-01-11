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
        self.root.title("My Work Logger V1.0") 
        # [调整] 高度增加到 460 以容纳底部工具栏
        self.root.geometry("400x520")
        self.root.resizable(False, True)
        
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
        # --- 菜单栏配置 (保留作为备用入口) ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="选项", menu=file_menu)
        file_menu.add_command(label="⚙️ 设置 (路径/习惯)", command=self.open_settings_window)
        #file_menu.add_separator()
        #file_menu.add_command(label="退出程序", command=self.quit_app)

        stats_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="统计", menu=stats_menu)
        stats_menu.add_command(label="打开可视化报表", command=self.open_report)

        # --- 样式配置 ---
        style = ttk.Style()
        style.configure("Big.TLabel", font=("Microsoft YaHei UI", 28, "bold"))
        style.configure("Status.TLabel", font=("Microsoft YaHei UI", 10), foreground="#666")
        style.configure("Info.TLabel", font=("Microsoft YaHei UI", 11, "bold"), foreground="#007ACC")
        style.configure("Action.TButton", font=("Microsoft YaHei UI", 12))
        # 新增样式
        style.configure("Hint.TLabel", font=("Microsoft YaHei UI", 9), foreground="#888888")

        # --- 工作计时区 ---
        frame_work = ttk.LabelFrame(self.root, text="工作记录", padding=20)
        frame_work.pack(fill="x", padx=15, pady=10)
        
        self.lbl_timer = ttk.Label(frame_work, text="00:00:00", style="Big.TLabel", anchor="center")
        self.lbl_timer.pack(fill='x', pady=5)
        
        self.lbl_status = ttk.Label(frame_work, text="当前状态: 空闲", style="Status.TLabel", anchor="center")
        self.lbl_status.pack(fill='x', pady=(0, 5))

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
        
        default_pomo = self.db.get_setting("pomodoro_duration", 25)
        self.var_pomo_mins = tk.IntVar(value=default_pomo)
        
        self.spin_pomo = ttk.Spinbox(input_frame, from_=1, to=120, textvariable=self.var_pomo_mins, width=5)
        self.spin_pomo.pack(side='left', padx=5)
        
        self.btn_pomo = ttk.Button(input_frame, text="启动", command=self.toggle_pomo)
        self.btn_pomo.pack(side='right')

        self.lbl_pomo_timer = ttk.Label(frame_pomo, text="25:00", font=("Consolas", 16), foreground="#888")
        self.lbl_pomo_timer.pack(pady=5)

        # ===========================
        # [新增] 底部工具栏/提示区
        # ===========================
        frame_bottom = ttk.Frame(self.root)
        frame_bottom.pack(fill="x", side="bottom", padx=15, pady=15)

        # 左侧：最小化提示
        # 使用 unicode 符号 ↗ 或 ⨯ 来指代右上角
        lbl_hint = ttk.Label(frame_bottom, text="ℹ️ 提示：点击右上角[×]可最小化至托盘", style="Hint.TLabel")
        lbl_hint.pack(side="left", anchor="center")

        # 右侧：退出按钮
        # 既然是直接退出，可以用个稍微不同的样式，或者普通按钮
        btn_quit = ttk.Button(frame_bottom, text="彻底退出", command=self.quit_app, width=10)
        btn_quit.pack(side="right", anchor="center")


    # ===========================
    # 设置面板逻辑
    # ===========================
    def open_settings_window(self):
        """打开设置窗口 (路径设置与习惯设置分离)"""
        sw = tk.Toplevel(self.root)
        sw.title("程序设置")
        sw.geometry("520x300")
        sw.resizable(False, False)
        sw.grab_set()

        # --- 区域1: 数据文件路径 ---
        lf_path = tk.LabelFrame(sw, text="数据存储位置 (修改即时生效)", padx=15, pady=15)
        lf_path.pack(fill="x", padx=15, pady=15)

        current_path = self.db.data_file
        lbl_path_val = tk.Label(lf_path, text=current_path, fg="#555", bg="#f0f0f0", 
                                wraplength=460, justify="left", relief="sunken", padx=5, pady=5)
        lbl_path_val.pack(fill="x", pady=(0, 10))

        btn_change = tk.Button(lf_path, text="📂 修改/新建 数据文件路径...", 
                               command=lambda: self.change_data_path_logic(sw, lbl_path_val))
        btn_change.pack(anchor="w")

        # --- 区域2: 个人习惯 ---
        lf_pref = tk.LabelFrame(sw, text="个人习惯", padx=15, pady=15)
        lf_pref.pack(fill="x", padx=15, pady=(0, 15))

        f_offset = tk.Frame(lf_pref)
        f_offset.pack(fill="x", pady=5)
        
        tk.Label(f_offset, text="新的一天开始于 (凌晨几点):").pack(side="left")
        
        current_offset = self.db.get_setting("day_offset_hour", 4)
        spin_offset = tk.Spinbox(f_offset, from_=0, to=23, width=5)
        spin_offset.delete(0, "end")
        spin_offset.insert(0, current_offset)
        spin_offset.pack(side="left", padx=(10, 5))

        # 保存按钮
        def save_habit():
            try:
                new_offset = int(spin_offset.get())
                self.db.update_setting("day_offset_hour", new_offset)
                self.update_today_total()
                messagebox.showinfo("已保存", "【个人习惯】设置已更新。")
            except ValueError:
                messagebox.showerror("错误", "请输入有效数字")

        btn_save_habit = ttk.Button(f_offset, text="保存", command=save_habit, width=5)
        btn_save_habit.pack(side="left", padx=5)
        
        tk.Label(f_offset, text="(填4代表凌晨3点仍算作昨天)", fg="gray", font=("", 8)).pack(side="left", padx=5)

    def change_data_path_logic(self, parent_window, label_widget):
        """执行修改路径的逻辑"""
        current_dir = os.path.dirname(self.db.data_file)
        
        new_path = filedialog.asksaveasfilename(
            parent=parent_window,
            title="修改数据文件路径 (选中已有文件 或 输入新文件名)",
            initialdir=current_dir,
            defaultextension=".json",
            initialfile="work_data.json",
            confirmoverwrite=False,
            filetypes=[("JSON Files", "*.json")]
        )
        
        if not new_path:
            return

        try:
            is_new_file = False
            if not os.path.exists(new_path):
                is_new_file = True
            elif os.path.getsize(new_path) == 0:
                is_new_file = True
            
            if is_new_file:
                ans = messagebox.askyesno(
                    "创建新库", 
                    "目标是新文件。\n是否将【当前已有的记录和设置】复制过去？\n\n(选择'否'将创建一个全新的空数据库)",
                    parent=parent_window
                )
                if ans:
                    with open(new_path, 'w', encoding='utf-8') as f:
                        json.dump(self.db.full_data, f, indent=4)
                else:
                    with open(new_path, 'w', encoding='utf-8') as f:
                        empty_data = {"settings": self.db.full_data.get("settings", {}), "records": []}
                        json.dump(empty_data, f, indent=4)
            
            self.db.save_local_pointer(new_path)
            label_widget.config(text=new_path)
            self.update_today_total()
            
            msg = "路径设置成功。" + ("\n(已初始化新文件)" if is_new_file else "\n(已切换至现有数据文件)")
            messagebox.showinfo("成功", msg, parent=parent_window)
            
        except Exception as e:
            messagebox.showerror("失败", f"设置路径失败:\n{e}", parent=parent_window)

    # ===========================
    # 核心工作逻辑
    # ===========================
    def update_today_total(self):
        """刷新今日累计时长"""
        total_sec = self.db.get_today_total_seconds()
        m, s = divmod(total_sec, 60)
        h, m = divmod(m, 60)
        self.lbl_today.config(text=f"今日累计: {int(h)} h {int(m)} min")

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
            #pystray.MenuItem("退出程序", self.quit_app)
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