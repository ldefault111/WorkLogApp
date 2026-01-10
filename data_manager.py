import json
import os
import datetime
from pathlib import Path

# 默认配置
DEFAULT_CONFIG = {
    "data_path": "./work_data.json",  # 数据文件路径 (可修改为OneDrive路径)
    "day_offset_hour": 4,             # 凌晨4点前算作前一天
    "pomodoro_duration": 25           # 番茄钟默认分钟数
}

class DataManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.data_file = self.config["data_path"]
        self._ensure_data_file()

    # ===========================
    # 基础文件操作
    # ===========================
    def _load_config(self):
        """加载配置文件，不存在则创建默认"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"配置加载失败: {e}，使用默认配置")
            return DEFAULT_CONFIG

    def _ensure_data_file(self):
        """确保数据文件存在"""
        # 如果路径包含文件夹，确保文件夹存在
        folder = os.path.dirname(self.data_file)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
            
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def load_records(self):
        """读取所有工作记录"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save_record(self, start_dt, end_dt):
        """保存单条记录 (增加小于1分钟不保存的逻辑)"""
        duration = (end_dt - start_dt).total_seconds()
        
        # --- 新增逻辑: 过滤小于60秒的记录 ---
        if duration < 60:
            print(f"时长过短 ({duration}s)，忽略该记录。")
            return
        # ----------------------------------

        records = self.load_records()
        new_record = {
            "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration
        }
        records.append(new_record)
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4)

    def get_today_total_seconds(self):
        """获取'逻辑今天'的总工作时长(秒)"""
        records = self.load_records()
        today = datetime.date.today()
        total = 0
        for r in records:
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            # 使用逻辑日期 (比如凌晨2点仍算作昨天)
            if self.get_logical_date(s_dt) == today:
                total += r['duration']
        return total
            
    # ===========================
    # 核心逻辑算法
    # ===========================
    def get_logical_date(self, dt):
        """
        获取逻辑日期。
        如果 day_offset_hour = 4 (凌晨4点)，
        那么 2023-01-02 03:00:00 归属于 2023-01-01
        """
        offset = self.config.get("day_offset_hour", 0)
        # 如果当前小时 < 偏移量，说明属于前一天，日期减1
        if dt.hour < offset:
            return (dt - datetime.timedelta(days=1)).date()
        return dt.date()

    def get_start_hour_bucket(self, dt):
        """获取开始时间的时间段 (0-23)"""
        return dt.hour

    # ===========================
    # 报表数据接口
    # ===========================
    def get_week_stats(self, anchor_date):
        """
        获取指定周的统计数据
        :param anchor_date: 该周任意一天的日期对象
        :return: (daily_hours, start_hour_dist, week_range_str)
        """
        # 1. 计算周范围 (周一到周日)
        start_of_week = anchor_date - datetime.timedelta(days=anchor_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        records = self.load_records()
        
        # 初始化数据容器
        # daily_hours: [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
        daily_hours = [0.0] * 7 
        # start_hour_dist: [0点次数, 1点次数, ... 23点次数]
        start_hour_dist = [0] * 24
        
        for r in records:
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            # 使用逻辑日期判断归属
            logical_date = self.get_logical_date(s_dt)
            
            # 过滤：是否在本周范围内
            if start_of_week <= logical_date <= end_of_week:
                # 累加时长
                idx = (logical_date - start_of_week).days
                if 0 <= idx <= 6:
                    daily_hours[idx] += r['duration'] / 3600.0
                
                # 统计开始时间点 (直接用物理时间的hour，还是逻辑时间的hour？通常作息统计用物理时间更直观)
                # 这里我们统计物理开始时间，看用户习惯几点坐到电脑前
                start_hour_dist[s_dt.hour] += 1
                
        date_str = f"{start_of_week.strftime('%Y-%m-%d')} 至 {end_of_week.strftime('%Y-%m-%d')}"
        return daily_hours, start_hour_dist, date_str

    def get_month_stats_heatmap(self, year, month):
        """
        获取月度日历热力图数据
        :return: { day_int: hours_float }
        """
        records = self.load_records()
        month_data = {}
        
        for r in records:
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            logical_date = self.get_logical_date(s_dt)
            
            if logical_date.year == year and logical_date.month == month:
                day = logical_date.day
                month_data[day] = month_data.get(day, 0) + (r['duration'] / 3600.0)
                
        return month_data

    def get_year_stats(self, year):
        """
        获取年度统计数据
        :return: (monthly_hours, monthly_days, start_hour_dist)
        """
        records = self.load_records()
        
        # 初始化
        # 12个月的数据
        monthly_hours = [0.0] * 12
        monthly_days_sets = [set() for _ in range(12)] # 用set去重，计算工作天数
        start_hour_dist = [0] * 24
        
        for r in records:
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            logical_date = self.get_logical_date(s_dt)
            
            if logical_date.year == year:
                m_idx = logical_date.month - 1 # 0-11
                
                # 累加时长
                monthly_hours[m_idx] += r['duration'] / 3600.0
                # 记录工作天 (用于统计每月工作了几天)
                monthly_days_sets[m_idx].add(logical_date.day)
                # 累加开始时间分布
                start_hour_dist[s_dt.hour] += 1
                
        # 将 set 转换为 int 数量
        monthly_days = [len(s) for s in monthly_days_sets]
        
        return monthly_hours, monthly_days, start_hour_dist

# --- 调试代码 (直接运行此文件可测试逻辑) ---
if __name__ == "__main__":
    # 模拟测试
    dm = DataManager()
    print(f"当前配置: {dm.config}")
    
    # 模拟插入一条跨天数据 (凌晨1点工作，应该算作前一天)
    now = datetime.datetime.now()
    # 假设现在是凌晨 01:00
    fake_start = now.replace(hour=1, minute=0, second=0)
    fake_end = now.replace(hour=3, minute=0, second=0)
    
    print(f"物理时间: {fake_start}, 逻辑归属日期: {dm.get_logical_date(fake_start)}")
    
    # 获取本周数据测试
    h, d, s = dm.get_week_stats(datetime.date.today())
    print(f"本周时长分布: {h}")
    print(f"开始时间分布: {d}")