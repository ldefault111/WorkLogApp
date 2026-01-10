import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import os
import datetime
import threading
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
from PIL import Image, ImageDraw # 用于绘制托盘图标
import pystray # 用于系统托盘

# =================配置与常量=================
DEFAULT_CONFIG = {
    "data_path": "./work_data.json",
    "day_end_hour": 1,
    "pomodoro_work": 25,
    "pomodoro_rest": 5 
}

# 强制设置Matplotlib中文字体，解决乱码
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei'] 
plt.rcParams['axes.unicode_minus'] = False 

class DataManager:
    def __init__(self):
        self.config_file = "wt_config.json"
        self.load_local_config()
        self.ensure_data_file()

    def load_local_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.local_config = json.load(f)
        else:
            self.local_config = {"data_file_path": "work_data.json"}
            self.save_local_config()

    def save_local_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.local_config, f, indent=4)

    def get_data_path(self):
        return self.local_config["data_file_path"]

    def set_data_path(self, path):
        self.local_config["data_file_path"] = path
        self.save_local_config()
        self.ensure_data_file()

    def ensure_data_file(self):
        path = self.get_data_path()
        # 确保数据文件存在，且包含设置
        if not os.path.exists(path):
            init_data = {"settings": DEFAULT_CONFIG, "records": []}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(init_data, f, indent=4)
        else:
            # 兼容性检查：确保settings存在
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "settings" not in data:
                    data["settings"] = DEFAULT_CONFIG
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
            except:
                pass

    def load_data(self):
        try:
            with open(self.get_data_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"settings": DEFAULT_CONFIG, "records": []}

    def save_settings(self, settings_dict):
        data = self.load_data()
        data["settings"].update(settings_dict)
        with open(self.get_data_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def save_record(self, start_dt, end_dt):
        data = self.load_data()
        day_end_hour = data["settings"].get("day_end_hour", 1)
        
        # 逻辑：如果结束时间也在凌晨day_end_hour之前，归属到前一天
        # 这里简化处理：以开始时间判定归属
        if start_dt.hour < day_end_hour:
            effective_date = (start_dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            effective_date = start_dt.strftime("%Y-%m-%d")

        duration = (end_dt - start_dt).total_seconds() / 60.0
        
        # 只有时长大于1分钟才记录（防误触）
        if duration < 0.1: 
            return

        new_record = {
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_min": round(duration, 2),
            "date_belong": effective_date
        }
        data["records"].append(new_record)
        with open(self.get_data_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_today_minutes(self):
        data = self.load_data()
        day_end_hour = data["settings"].get("day_end_hour", 1)
        now = datetime.datetime.now()
        if now.hour < day_end_hour:
            today_str = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            today_str = now.strftime("%Y-%m-%d")
            
        total = 0
        for rec in data["records"]:
            if rec.get("date_belong") == today_str:
                total += rec.get("duration_min", 0)
        return total, today_str, data["settings"]

class StatsWindow:
    def __init__(self, parent, data_manager):
        self.dm = data_manager
        self.window = tk.Toplevel(parent)
        self.window.title("工作数据可视化")
        self.window.geometry("900x700")
        
        # 顶部控制栏
        ctrl_frame = ttk.Frame(self.window)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(ctrl_frame, text="开始日期(YYYY-MM-DD):").pack(side="left")
        self.ent_start = ttk.Entry(ctrl_frame, width=12)
        self.ent_start.pack(side="left", padx=5)
        
        ttk.Label(ctrl_frame, text="结束日期:").pack(side="left")
        self.ent_end = ttk.Entry(ctrl_frame, width=12)
        self.ent_end.pack(side="left", padx=5)
        
        # 默认最近7天
        today = datetime.date.today()
        start_def = today - datetime.timedelta(days=6)
        self.ent_start.insert(0, start_def.strftime("%Y-%m-%d"))
        self.ent_end.insert(0, today.strftime("%Y-%m-%d"))

        ttk.Button(ctrl_frame, text="更新图表", command=self.draw_charts).pack(side="left", padx=10)

        self.canvas_frame = ttk.Frame(self.window)
        self.canvas_frame.pack(fill="both", expand=True)
        
        self.draw_charts()

    def draw_charts(self):
        # 清除旧图
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()

        start_str = self.ent_start.get()
        end_str = self.ent_end.get()
        
        try:
            d_start = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            d_end = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("错误", "日期格式错误，请使用 YYYY-MM-DD")
            return

        data = self.dm.load_data()
        records = data["records"]
        
        daily_stats = defaultdict(float)
        # 生成完整日期序列，防止断层
        curr = d_start
        while curr <= d_end:
            daily_stats[curr.strftime("%Y-%m-%d")] = 0.0
            curr += datetime.timedelta(days=1)

        # 填充数据
        hour_distribution = [0]*24
        
        for r in records:
            r_date = r["date_belong"]
            # 检查是否在范围内
            try:
                r_date_obj = datetime.datetime.strptime(r_date, "%Y-%m-%d").date()
                if d_start <= r_date_obj <= d_end:
                    daily_stats[r_date] += r["duration_min"]
                    
                    # 统计具体时间段分布
                    st_time = datetime.datetime.strptime(r["start_time"], "%Y-%m-%d %H:%M:%S")
                    hour_distribution[st_time.hour] += 1
            except:
                continue

        # 准备绘图数据
        sorted_dates = sorted(daily_stats.keys())
        hours_values = [daily_stats[d]/60.0 for d in sorted_dates]

        # 绘图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), dpi=100)
        plt.subplots_adjust(hspace=0.4) # 调整子图间距
        
        # 图1：每日工作时长
        ax1.bar(sorted_dates, hours_values, color='#4CAF50')
        ax1.set_title(f"{start_str} 至 {end_str} 工作时长统计", fontsize=12)
        ax1.set_ylabel("时长 (小时)")
        ax1.tick_params(axis='x', rotation=30)
        ax1.grid(axis='y', linestyle='--', alpha=0.5)
        
        # 图2：工作开始时间分布
        ax2.bar(range(24), hour_distribution, color='#2196F3')
        ax2.set_title("工作时段分布 (开始工作时间频次)", fontsize=12)
        ax2.set_xlabel("时刻 (0点 - 23点)")
        ax2.set_ylabel("次数")
        ax2.set_xticks(range(0, 25, 2))
        ax2.grid(axis='y', linestyle='--', alpha=0.5)

        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("轻量工作记录器 v2.0")
        self.root.geometry("400x520")
        self.root.resizable(False, False)
        
        # 设置全局字体
        self.default_font = ("Microsoft YaHei", 10)
        self.title_font = ("Microsoft YaHei", 12, "bold")
        self.timer_font = ("Consolas", 32, "bold")
        
        self.dm = DataManager()
        
        # 状态变量
        self.is_working = False
        self.current_start_time = None
        
        # 番茄钟变量
        self.pomodoro_active = False
        self.pomodoro_seconds = 25 * 60
        self.pomodoro_target_work = 25
        self.pomodoro_target_rest = 5
        
        # 初始化读取配置
        self.reload_config()

        self.setup_ui()
        self.update_stats_label()
        
        # 托盘相关
        self.tray_icon = None
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window) # 拦截关闭事件

    def reload_config(self):
        data = self.dm.load_data()
        settings = data.get("settings", DEFAULT_CONFIG)
        self.pomodoro_target_work = settings.get("pomodoro_work", 25)
        self.pomodoro_target_rest = settings.get("pomodoro_rest", 5)
        self.pomodoro_seconds = self.pomodoro_target_work * 60

    def setup_ui(self):
        style = ttk.Style()
        style.configure("TButton", font=self.default_font)
        style.configure("Big.TButton", font=("Microsoft YaHei", 14, "bold"))
        
        # 顶部：今日统计
        self.frame_top = ttk.LabelFrame(self.root, text="今日概览", padding=10)
        self.frame_top.pack(fill="x", padx=10, pady=5)
        
        self.lbl_date = ttk.Label(self.frame_top, text="归属日期: --", font=self.default_font)
        self.lbl_date.pack(anchor="w")
        self.lbl_today_total = ttk.Label(self.frame_top, text="已工作: 0 分钟", font=self.default_font)
        self.lbl_today_total.pack(anchor="w")

        # 中部：工作计时区
        self.frame_main = ttk.Frame(self.root, padding=20)
        self.frame_main.pack(fill="both", expand=True)
        
        ttk.Label(self.frame_main, text="当前工作计时", font=("Microsoft YaHei", 10)).pack()
        self.lbl_current_timer = ttk.Label(self.frame_main, text="00:00:00", font=self.timer_font, foreground="#333")
        self.lbl_current_timer.pack(pady=5)
        
        self.btn_toggle = ttk.Button(self.frame_main, text="开始工作", command=self.toggle_work, style="Big.TButton")
        self.btn_toggle.pack(fill="x", ipady=10, pady=10)

        # 底部：番茄钟
        self.frame_pomo = ttk.LabelFrame(self.root, text="番茄钟 (独立计时)", padding=10)
        self.frame_pomo.pack(fill="x", padx=10, pady=5)
        
        pomo_inner = ttk.Frame(self.frame_pomo)
        pomo_inner.pack(fill="x")
        
        self.lbl_pomo_timer = ttk.Label(pomo_inner, text=f"{self.pomodoro_target_work:02}:00", font=("Consolas", 24))
        self.lbl_pomo_timer.pack(side="left", padx=10)
        
        btn_frame = ttk.Frame(pomo_inner)
        btn_frame.pack(side="right")
        self.btn_pomo = ttk.Button(btn_frame, text="启动番茄", command=self.toggle_pomodoro)
        self.btn_pomo.pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="设置", command=self.open_pomo_settings, width=6).pack(fill="x")

        # 底部提示
        ttk.Label(self.root, text="点击 X 最小化到托盘", font=("Microsoft YaHei", 8), foreground="gray").pack(side="bottom", pady=5)

        # 菜单栏
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="选择同步数据文件...", command=self.change_path)
        file_menu.add_command(label="查看可视化报表", command=self.show_stats)
        file_menu.add_separator()
        file_menu.add_command(label="彻底退出程序", command=self.quit_app)
        menubar.add_cascade(label="菜单", menu=file_menu)
        self.root.config(menu=menubar)

    # ============ 核心逻辑：工作计时 ============
    def toggle_work(self):
        if not self.is_working:
            self.is_working = True
            self.current_start_time = datetime.datetime.now()
            self.btn_toggle.config(text="停止工作 (结算)")
            self.run_work_timer()
        else:
            self.stop_work()

    def stop_work(self):
        if self.is_working:
            self.is_working = False
            end_time = datetime.datetime.now()
            self.dm.save_record(self.current_start_time, end_time)
            self.btn_toggle.config(text="开始工作")
            self.lbl_current_timer.config(text="00:00:00")
            self.update_stats_label()

    def run_work_timer(self):
        if self.is_working:
            delta = datetime.datetime.now() - self.current_start_time
            seconds = int(delta.total_seconds())
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.lbl_current_timer.config(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            self.root.after(1000, self.run_work_timer)

    # ============ 核心逻辑：番茄钟 ============
    def toggle_pomodoro(self):
        if not self.pomodoro_active:
            self.pomodoro_active = True
            self.btn_pomo.config(text="停止/重置")
            self.run_pomodoro()
        else:
            # 停止番茄钟
            self.pomodoro_active = False
            self.btn_pomo.config(text="启动番茄")
            self.reset_pomo_display()

    def run_pomodoro(self):
        if self.pomodoro_active and self.pomodoro_seconds > 0:
            self.pomodoro_seconds -= 1
            mins, secs = divmod(self.pomodoro_seconds, 60)
            self.lbl_pomo_timer.config(text=f"{mins:02}:{secs:02}")
            self.root.after(1000, self.run_pomodoro)
        elif self.pomodoro_active and self.pomodoro_seconds <= 0:
            self.pomodoro_complete()

    def pomodoro_complete(self):
        self.pomodoro_active = False
        self.btn_pomo.config(text="启动番茄")
        self.root.bell()
        # 弹窗必须在主线程
        self.root.deiconify() # 确保窗口弹出
        messagebox.showinfo("番茄钟", "专注时间结束！请休息一下。")
        self.reset_pomo_display()

    def reset_pomo_display(self):
        self.pomodoro_seconds = self.pomodoro_target_work * 60
        self.lbl_pomo_timer.config(text=f"{self.pomodoro_target_work:02}:00")

    def open_pomo_settings(self):
        w_time = simpledialog.askinteger("设置", "工作时长 (分钟):", initialvalue=self.pomodoro_target_work, minvalue=1, maxvalue=120)
        if w_time:
            self.dm.save_settings({"pomodoro_work": w_time})
            self.reload_config()
            self.reset_pomo_display()
            messagebox.showinfo("提示", "设置已保存，下次启动番茄钟生效。")

    def update_stats_label(self):
        mins, date_str, _ = self.dm.get_today_minutes()
        hours = mins / 60.0
        self.lbl_date.config(text=f"归属日期: {date_str}")
        self.lbl_today_total.config(text=f"今日已工作: {hours:.1f} 小时 ({int(mins)} 分钟)")

    def change_path(self):
        path = filedialog.asksaveasfilename(title="选择数据文件", defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if path:
            self.dm.set_data_path(path)
            self.reload_config()
            self.update_stats_label()

    def show_stats(self):
        StatsWindow(self.root, self.dm)

    # ============ 托盘与退出逻辑 ============
    def hide_window(self):
        """点击X时隐藏窗口"""
        self.root.withdraw()
        if not self.tray_icon:
            self.create_tray_icon()

    def create_tray_icon(self):
        # 创建一个简单的图标 (绿色方块)
        image = Image.new('RGB', (64, 64), color=(76, 175, 80))
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill=(255, 255, 255))

        menu = (pystray.MenuItem('显示', self.show_window, default=True),
                pystray.MenuItem('退出', self.quit_app_tray))
        
        self.tray_icon = pystray.Icon("name", image, "工作记录器", menu)
        # 在独立线程运行托盘，否则会阻塞UI
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)
        # 注意：这里不停止tray_icon，保持它在后台

    def quit_app(self):
        """从菜单栏完全退出"""
        self.cleanup()
        self.root.destroy()
        
    def quit_app_tray(self, icon, item):
        """从托盘退出"""
        icon.stop()
        self.root.after(0, self.cleanup_and_destroy)

    def cleanup_and_destroy(self):
        self.cleanup()
        self.root.destroy()

    def cleanup(self):
        # 边界检查：如果正在工作，强制保存
        if self.is_working:
            self.stop_work()
            print("Auto saved on exit.")

if __name__ == "__main__":
    root = tk.Tk()
    # 适配高DPI
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = MainApp(root)
    root.mainloop()