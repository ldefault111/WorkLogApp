import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict

# =================配置与常量=================
DEFAULT_CONFIG = {
    "data_path": "./work_data.json", # 默认在当前目录，后续可修改为同步盘路径
    "day_end_hour": 1,               # 凌晨1点前算作前一天
    "pomodoro_work": 25,             # 分钟
    "pomodoro_rest": 5               # 分钟
}

class DataManager:
    def __init__(self):
        self.config_file = "wt_config.json" # 保存本地配置（主要是数据文件路径）
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
        if not os.path.exists(path):
            init_data = {"settings": DEFAULT_CONFIG, "records": []}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(init_data, f, indent=4)

    def load_data(self):
        try:
            with open(self.get_data_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {"settings": DEFAULT_CONFIG, "records": []}

    def save_record(self, start_dt, end_dt):
        data = self.load_data()
        
        # 计算归属日期
        day_end_hour = data["settings"].get("day_end_hour", 0)
        check_dt = start_dt
        if start_dt.hour < day_end_hour:
            effective_date = (start_dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            effective_date = start_dt.strftime("%Y-%m-%d")

        duration = (end_dt - start_dt).total_seconds() / 60.0 # 分钟

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
        """获取今日（考虑跨天逻辑）已工作总分钟数"""
        data = self.load_data()
        day_end_hour = data["settings"].get("day_end_hour", 0)
        
        now = datetime.datetime.now()
        if now.hour < day_end_hour:
            today_str = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            today_str = now.strftime("%Y-%m-%d")
            
        total = 0
        for rec in data["records"]:
            if rec.get("date_belong") == today_str:
                total += rec.get("duration_min", 0)
        return total, today_str

class StatsWindow:
    def __init__(self, parent, data_manager):
        self.dm = data_manager
        self.window = tk.Toplevel(parent)
        self.window.title("工作数据可视化")
        self.window.geometry("800x600")
        self.draw_charts()

    def draw_charts(self):
        data = self.dm.load_data()
        records = data["records"]
        
        if not records:
            ttk.Label(self.window, text="暂无数据").pack(pady=20)
            return

        # 数据处理：近7天数据
        daily_stats = defaultdict(float)
        all_dates = sorted(list(set(r["date_belong"] for r in records)))
        
        for r in records:
            daily_stats[r["date_belong"]] += r["duration_min"]

        # 只取最近7个有数据的日子（或者逻辑上的最近7天，这里简单处理）
        dates = all_dates[-7:]
        hours = [daily_stats[d]/60.0 for d in dates] # 转换为小时

        # 绘图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 5), dpi=100)
        
        # 图1：每日工作时长（柱状图）
        ax1.bar(dates, hours, color='#4CAF50')
        ax1.set_title("最近工作时长 (小时)")
        ax1.tick_params(axis='x', rotation=20)
        
        # 图2：工作时段分布 (散点图/热力图简化版 - 这里用小时分布直方图)
        start_hours = []
        for r in records:
            dt = datetime.datetime.strptime(r["start_time"], "%Y-%m-%d %H:%M:%S")
            start_hours.append(dt.hour)
            
        ax2.hist(start_hours, bins=range(0, 25), color='#2196F3', alpha=0.7, rwidth=0.8)
        ax2.set_title("工作开始时间分布 (0-24点)")
        ax2.set_xticks(range(0, 25, 2))

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("轻量工作记录器")
        self.root.geometry("350x450")
        self.root.resizable(False, False)
        
        self.dm = DataManager()
        
        # 状态变量
        self.is_working = False
        self.current_start_time = None
        self.timer_id = None
        
        # 番茄钟变量
        self.pomodoro_active = False
        self.pomodoro_seconds = 25 * 60
        self.pomodoro_mode = "WORK" # WORK or REST

        self.setup_ui()
        self.update_stats_label()

    def setup_ui(self):
        # 样式
        style = ttk.Style()
        style.configure("Big.TButton", font=("Helvetica", 12))
        
        # 顶部：今日统计
        self.frame_top = ttk.LabelFrame(self.root, text="今日概览", padding=10)
        self.frame_top.pack(fill="x", padx=10, pady=5)
        
        self.lbl_date = ttk.Label(self.frame_top, text="日期: --")
        self.lbl_date.pack(anchor="w")
        self.lbl_today_total = ttk.Label(self.frame_top, text="今日已工作: 0 分钟")
        self.lbl_today_total.pack(anchor="w")

        # 中部：主控区
        self.frame_main = ttk.Frame(self.root, padding=20)
        self.frame_main.pack(fill="both", expand=True)
        
        self.lbl_current_timer = ttk.Label(self.frame_main, text="00:00:00", font=("Consolas", 30))
        self.lbl_current_timer.pack(pady=10)
        
        self.btn_toggle = ttk.Button(self.frame_main, text="开始工作", command=self.toggle_work, style="Big.TButton")
        self.btn_toggle.pack(fill="x", ipady=10)

        # 底部：番茄钟
        self.frame_pomo = ttk.LabelFrame(self.root, text="番茄钟 (25min)", padding=10)
        self.frame_pomo.pack(fill="x", padx=10, pady=5)
        
        self.lbl_pomo_timer = ttk.Label(self.frame_pomo, text="25:00", font=("Consolas", 20))
        self.lbl_pomo_timer.pack(side="left", padx=10)
        
        self.btn_pomo = ttk.Button(self.frame_pomo, text="启动番茄", command=self.toggle_pomodoro)
        self.btn_pomo.pack(side="right")

        # 菜单栏
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="选择数据保存路径 (同步文件夹)", command=self.change_path)
        file_menu.add_command(label="查看统计报表", command=self.show_stats)
        menubar.add_cascade(label="选项", menu=file_menu)
        self.root.config(menu=menubar)

    def toggle_work(self):
        if not self.is_working:
            # 开始工作
            self.is_working = True
            self.current_start_time = datetime.datetime.now()
            self.btn_toggle.config(text="停止工作")
            self.run_timer()
        else:
            # 停止工作
            self.is_working = False
            end_time = datetime.datetime.now()
            self.dm.save_record(self.current_start_time, end_time)
            self.btn_toggle.config(text="开始工作")
            self.lbl_current_timer.config(text="00:00:00")
            self.update_stats_label()

    def run_timer(self):
        if self.is_working:
            delta = datetime.datetime.now() - self.current_start_time
            # 格式化 timedelta
            seconds = int(delta.total_seconds())
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.lbl_current_timer.config(text=time_str)
            self.root.after(1000, self.run_timer)

    def update_stats_label(self):
        mins, date_str = self.dm.get_today_minutes()
        hours = mins / 60.0
        self.lbl_date.config(text=f"归属日期: {date_str}")
        self.lbl_today_total.config(text=f"今日已工作: {hours:.1f} 小时 ({int(mins)} 分钟)")

    # ============ 番茄钟逻辑 ============
    def toggle_pomodoro(self):
        if not self.pomodoro_active:
            self.pomodoro_active = True
            self.btn_pomo.config(text="停止番茄")
            self.run_pomodoro()
        else:
            self.pomodoro_active = False
            self.btn_pomo.config(text="启动番茄")
            # 重置时间
            self.pomodoro_seconds = 25 * 60
            self.lbl_pomo_timer.config(text="25:00")

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
        # 播放提示音 (Windows系统)
        self.root.bell() 
        messagebox.showinfo("番茄钟", "时间到！请休息一下或开始工作。")
        # 简单的重置逻辑，实际可扩展为自动进入休息时间
        self.pomodoro_seconds = 25 * 60 
        self.lbl_pomo_timer.config(text="25:00")

    def change_path(self):
        path = filedialog.asksaveasfilename(
            title="选择数据文件保存位置 (建议选在同步文件夹内)",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if path:
            self.dm.set_data_path(path)
            self.update_stats_label()
            messagebox.showinfo("成功", f"数据文件已指向: {path}")

    def show_stats(self):
        StatsWindow(self.root, self.dm)

if __name__ == "__main__":
    root = tk.Tk()
    # 尝试设置Windows高DPI感知，防止模糊
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = MainApp(root)
    root.mainloop()