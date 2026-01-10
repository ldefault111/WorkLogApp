import tkinter as tk
from tkinter import ttk
import datetime
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# ==========================================
# 全局绘图设置
# ==========================================
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 9

class ReportWindow(tk.Toplevel):
    def __init__(self, parent, db_handler):
        super().__init__(parent)
        self.title("工作效能分析报表 (V3.2)")
        self.geometry("1000x800")
        self.db = db_handler
        
        # --- 修复核心：状态解耦 ---
        today = datetime.date.today()
        # 1. 周视图状态：锚定到本周一
        self.view_week_date = today - datetime.timedelta(days=today.weekday())
        # 2. 月视图状态：锚定到本月1号
        self.view_month_date = today.replace(day=1)
        # 3. 年视图状态：锚定到今年1月1号
        self.view_year_date = today.replace(month=1, day=1)

        self._setup_ui()

    def _setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab Frames
        self.tab_week = ttk.Frame(self.notebook)
        self.tab_month = ttk.Frame(self.notebook)
        self.tab_year = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_week, text='📊 周工作统计')
        self.notebook.add(self.tab_month, text='📅 月度日历')
        self.notebook.add(self.tab_year, text='📈 年度概览')

        self._init_week_tab()
        self._init_month_tab()
        self._init_year_tab()

    # =========================================================================
    # 1. 周报表
    # =========================================================================
    def _init_week_tab(self):
        # 顶部控制
        ctrl_frame = ttk.Frame(self.tab_week)
        ctrl_frame.pack(fill='x', pady=5)
        ttk.Button(ctrl_frame, text="<< 上一周", command=lambda: self._change_week(-1)).pack(side='left', padx=10)
        self.lbl_week_range = ttk.Label(ctrl_frame, text="Loading...", font=("Microsoft YaHei", 10, "bold"))
        self.lbl_week_range.pack(side='left', expand=True)
        ttk.Button(ctrl_frame, text="下一周 >>", command=lambda: self._change_week(1)).pack(side='right', padx=10)

        # 绘图初始化
        self.fig_week = Figure(figsize=(8, 6), dpi=100)
        self.fig_week.subplots_adjust(hspace=0.4, top=0.9, bottom=0.1)
        self.ax_week_daily = self.fig_week.add_subplot(211)
        self.ax_week_hourly = self.fig_week.add_subplot(212)

        self.canvas_week = FigureCanvasTkAgg(self.fig_week, master=self.tab_week)
        self.canvas_week.get_tk_widget().pack(fill='both', expand=True)
        
        self._update_week_chart()

    def _change_week(self, offset):
        self.view_week_date += datetime.timedelta(weeks=offset)
        self._update_week_chart()

    def _update_week_chart(self):
        # 使用独立的 view_week_date
        daily_hours, start_dist, date_str = self.db.get_week_stats(self.view_week_date)
        self.lbl_week_range.config(text=date_str)

        # 上图
        ax1 = self.ax_week_daily
        ax1.clear()
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        bars = ax1.bar(days, daily_hours, color='#5D9CEC', width=0.6)
        ax1.bar_label(bars, fmt='%.1f h', padding=2)
        ax1.set_title("本周每日工作时长", fontsize=11)
        ax1.set_ylabel("小时")
        ax1.set_ylim(0, max(max(daily_hours), 1) * 1.2)

        # 下图
        ax2 = self.ax_week_hourly
        ax2.clear()
        hours_x = list(range(24))
        bars2 = ax2.bar(hours_x, start_dist, color='#FFB86C', width=0.8)
        ax2.bar_label(bars2, fmt='%d', padding=2, labels=[str(x) if x>0 else '' for x in start_dist])
        ax2.set_title("本周工作开始时间点分布", fontsize=11)
        ax2.set_xticks(hours_x)
        ax2.set_xticklabels([f"{h}" if h%2==0 else "" for h in hours_x], fontsize=8)
        
        self.canvas_week.draw()

    # =========================================================================
    # 2. 月报表
    # =========================================================================
    def _init_month_tab(self):
        ctrl_frame = ttk.Frame(self.tab_month)
        ctrl_frame.pack(fill='x', pady=5)
        ttk.Button(ctrl_frame, text="<< 上一月", command=lambda: self._change_month(-1)).pack(side='left', padx=10)
        self.lbl_month_title = ttk.Label(ctrl_frame, text="Loading...", font=("Microsoft YaHei", 10, "bold"))
        self.lbl_month_title.pack(side='left', expand=True)
        ttk.Button(ctrl_frame, text="下一月 >>", command=lambda: self._change_month(1)).pack(side='right', padx=10)

        self.fig_month = Figure(figsize=(8, 6), dpi=100)
        self.ax_month = self.fig_month.add_subplot(111)
        self.canvas_month = FigureCanvasTkAgg(self.fig_month, master=self.tab_month)
        self.canvas_month.get_tk_widget().pack(fill='both', expand=True)

        self._update_month_chart()

    def _change_month(self, offset):
        # 使用独立的 view_month_date
        y = self.view_month_date.year
        m = self.view_month_date.month + offset
        if m > 12:
            y += 1; m = 1
        elif m < 1:
            y -= 1; m = 12
        self.view_month_date = datetime.date(y, m, 1)
        self._update_month_chart()

    def _update_month_chart(self):
        year, month = self.view_month_date.year, self.view_month_date.month
        self.lbl_month_title.config(text=f"{year}年 {month}月 工作概览")

        data_map = self.db.get_month_stats_heatmap(year, month)
        cal = calendar.monthcalendar(year, month)

        ax = self.ax_month
        ax.clear()
        ax.set_axis_off()

        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        for i, w in enumerate(weekdays):
            ax.text(i, 7, w, ha='center', va='center', weight='bold', color='#555')

        for r_idx, week in enumerate(cal):
            y_pos = 6 - r_idx
            for c_idx, day in enumerate(week):
                if day == 0: continue
                
                hours = data_map.get(day, 0)
                if hours == 0:
                    bg_color = '#F5F5F5'; txt_color = '#BBB'
                elif hours < 4:
                    bg_color = '#C8E6C9'; txt_color = '#000'
                else:
                    bg_color = '#4CAF50'; txt_color = '#FFF'

                rect = plt.Rectangle((c_idx-0.45, y_pos-0.45), 0.9, 0.9, color=bg_color, ec='#DDD')
                ax.add_patch(rect)
                ax.text(c_idx-0.35, y_pos+0.3, str(day), fontsize=9, color=txt_color)
                
                if hours > 0:
                    ax.text(c_idx, y_pos-0.1, f"{hours:.1f}h", ha='center', va='center', 
                            fontsize=10, weight='bold', color=txt_color)

        ax.set_xlim(-0.5, 6.5); ax.set_ylim(0, 8)
        self.canvas_month.draw()

    # =========================================================================
    # 3. 年报表 (修复双轴Ghosting问题)
    # =========================================================================
    def _init_year_tab(self):
        ctrl_frame = ttk.Frame(self.tab_year)
        ctrl_frame.pack(fill='x', pady=5)
        ttk.Button(ctrl_frame, text="<< 上一年", command=lambda: self._change_year(-1)).pack(side='left', padx=10)
        self.lbl_year_title = ttk.Label(ctrl_frame, text="Loading...", font=("Microsoft YaHei", 10, "bold"))
        self.lbl_year_title.pack(side='left', expand=True)
        ttk.Button(ctrl_frame, text="下一年 >>", command=lambda: self._change_year(1)).pack(side='right', padx=10)

        self.fig_year = Figure(figsize=(8, 6), dpi=100)
        self.fig_year.subplots_adjust(hspace=0.4, top=0.9, bottom=0.1)
        
        # --- 修复核心：初始化时创建双轴，而不是在update里创建 ---
        self.ax_year_hours = self.fig_year.add_subplot(211) # 左轴
        self.ax_year_days = self.ax_year_hours.twinx()    # 右轴 (只创建这一次!)
        
        self.ax_year_dist = self.fig_year.add_subplot(212)  # 下方子图

        self.canvas_year = FigureCanvasTkAgg(self.fig_year, master=self.tab_year)
        self.canvas_year.get_tk_widget().pack(fill='both', expand=True)
        
        self._update_year_chart()

    def _change_year(self, offset):
        # 使用独立的 view_year_date
        y = self.view_year_date.year + offset
        self.view_year_date = self.view_year_date.replace(year=y)
        self._update_year_chart()

    def _update_year_chart(self):
        year = self.view_year_date.year
        self.lbl_year_title.config(text=f"{year} 年度工作总结")
        
        m_hours, m_days, start_dist = self.db.get_year_stats(year)
        months = [f"{i}月" for i in range(1, 13)]
        x = np.arange(len(months))
        width = 0.35

        # --- 上图：更新数据而不是新建轴 ---
        
        # 1. 清空当前内容
        self.ax_year_hours.clear()
        self.ax_year_days.clear()

        # 2. 重新绘制左轴 (总时长)
        bars1 = self.ax_year_hours.bar(x - width/2, m_hours, width, label='总时长(h)', color='#4FC3F7')
        self.ax_year_hours.set_ylabel('总时长 (小时)', color='#0277BD')
        self.ax_year_hours.tick_params(axis='y', labelcolor='#0277BD')
        self.ax_year_hours.bar_label(bars1, fmt='%.0f', padding=2, color='#0277BD', fontsize=8)
        
        # 设置X轴 (只需要在主轴设置一次)
        self.ax_year_hours.set_xticks(x)
        self.ax_year_hours.set_xticklabels(months)
        self.ax_year_hours.set_title(f"{year}年 月度效率对比 (时长 vs 天数)")

        # 3. 重新绘制右轴 (天数)
        bars2 = self.ax_year_days.bar(x + width/2, m_days, width, label='工作天数(d)', color='#FF9800')
        self.ax_year_days.set_ylabel('出勤天数 (天)', color='#EF6C00')
        self.ax_year_days.tick_params(axis='y', labelcolor='#EF6C00')
        self.ax_year_days.set_ylim(0, 32)
        self.ax_year_days.bar_label(bars2, fmt='%d', padding=2, color='#EF6C00', fontsize=8)

        # --- 下图：分布 ---
        self.ax_year_dist.clear()
        hours_x = list(range(24))
        bars3 = self.ax_year_dist.bar(hours_x, start_dist, color='#9575CD', width=0.8)
        self.ax_year_dist.bar_label(bars3, fmt='%d', padding=2, labels=[str(x) if x>0 else '' for x in start_dist])
        self.ax_year_dist.set_title(f"{year}年 全年工作习惯", fontsize=11)
        self.ax_year_dist.set_xticks(hours_x)
        self.ax_year_dist.set_xticklabels([str(h) if h%2==0 else "" for h in hours_x], fontsize=8)

        self.canvas_year.draw()

# 测试入口
if __name__ == "__main__":
    from data_manager import DataManager
    root = tk.Tk()
    root.withdraw()
    dm = DataManager()
    app = ReportWindow(root, dm)
    root.mainloop()