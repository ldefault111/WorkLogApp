import json
import os
import datetime

# 本地指针文件：只存储"真实数据文件在哪里"
# 这样你可以把真实数据放在 OneDrive/Dropbox，而程序通过读取这个文件找到它
LOCAL_POINTER_FILE = "pathCfg.json"

# 新版数据文件的默认结构
DEFAULT_DATA_STRUCTURE = {
    "settings": {
        "day_offset_hour": 1,      # 凌晨4点前算作前一天
        "pomodoro_duration": 25    # 番茄钟默认分钟数
    },
    "records": []                  # 存储工作记录
}

class DataManager:
    def __init__(self):
        # 1. 加载指针，找到真实数据路径
        self.data_file = self._load_local_pointer()
        
        # 2. 加载全部数据到内存 (Settings + Records)
        self.full_data = self._load_or_init_data_file()

    # ===========================
    # 文件与路径管理
    # ===========================
    def _load_local_pointer(self):
        """读取本地指针文件，获取数据文件的绝对路径"""
        default_path = os.path.abspath("./work_data.json")
        
        if os.path.exists(LOCAL_POINTER_FILE):
            try:
                with open(LOCAL_POINTER_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    path = config.get("data_path", default_path)
                    # 如果记录的路径不存在（比如移动了文件夹），回退到默认
                    # 也可以选择不回退，抛出错误，这里暂且回退
                    return path
            except:
                pass
        return default_path

    def save_local_pointer(self, new_path):
        """更新本地指针 (当用户修改数据文件位置时调用)"""
        self.data_file = new_path
        
        # 1. 保存指针文件
        with open(LOCAL_POINTER_FILE, 'w', encoding='utf-8') as f:
            json.dump({"data_path": new_path}, f, indent=4)
            
        # 2. 重新加载或初始化新位置的数据文件
        self.full_data = self._load_or_init_data_file()

    def _load_or_init_data_file(self):
        """加载数据文件，如果不存在则创建新结构"""
        # 确保目录存在
        folder = os.path.dirname(self.data_file)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        if not os.path.exists(self.data_file):
            self._save_file_content(DEFAULT_DATA_STRUCTURE)
            return DEFAULT_DATA_STRUCTURE

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
            # 基础格式校验：确保它是字典且包含必要的key
            # 如果是旧版 List 格式，这里不处理迁移，直接报错或返回空结构(按你要求不写自动迁移)
            if not isinstance(content, dict):
                return DEFAULT_DATA_STRUCTURE
            
            if "settings" not in content:
                content["settings"] = DEFAULT_DATA_STRUCTURE["settings"]
            if "records" not in content:
                content["records"] = []
                
            return content
        except Exception as e:
            print(f"数据加载失败: {e}，使用默认空数据")
            return DEFAULT_DATA_STRUCTURE

    def _save_file_content(self, data):
        """底层保存方法"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    # ===========================
    # 设置 (Settings) 操作
    # ===========================
    def get_setting(self, key, default=None):
        """获取某项设置"""
        return self.full_data.get("settings", {}).get(key, default)

    def update_setting(self, key, value):
        """更新设置并保存到文件"""
        if "settings" not in self.full_data:
            self.full_data["settings"] = {}
        
        self.full_data["settings"][key] = value
        self._save_file_content(self.full_data)

    # ===========================
    # 记录 (Records) 操作
    # ===========================
    def load_records(self):
        """获取记录列表 (只读引用)"""
        return self.full_data.get("records", [])

    def save_record(self, start_dt, end_dt):
        """保存单条记录"""
        duration = (end_dt - start_dt).total_seconds()
        
        # 过滤小于60秒的记录
        if duration < 60:
            print(f"时长过短 ({duration}s)，忽略该记录。")
            return

        new_record = {
            "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration
        }
        
        # 更新内存
        if "records" not in self.full_data:
            self.full_data["records"] = []
        
        self.full_data["records"].append(new_record)
        
        # 写入文件
        self._save_file_content(self.full_data)

    def get_today_total_seconds(self):
        """获取'逻辑今天'的总工作时长(秒)"""
        records = self.load_records()
        today = datetime.date.today()
        
        # 动态获取当前的偏移量设置 (之前是读config，现在读self.data)
        # 注意：这里需要重新获取逻辑日期，因为可能用户刚改了 offset
        
        now = datetime.datetime.now()
        current_logical_today = self.get_logical_date(now)

        total = 0
        for r in records:
            if not isinstance(r, dict): continue # 防御性编程
            
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            
            # 判断这条记录的逻辑日期是否等于今天的逻辑日期
            # 比如：现在是 1月5日 02:00 (offset=4)，逻辑日期是 1月4日
            # 如果记录是 1月5日 01:00，逻辑日期也是 1月4日 -> 匹配成功
            if self.get_logical_date(s_dt) == current_logical_today:
                total += r['duration']
        return total

    # ===========================
    # 核心逻辑算法
    # ===========================
    def get_logical_date(self, dt):
        """
        根据 settings 中的 day_offset_hour 计算逻辑日期
        """
        offset = self.get_setting("day_offset_hour", 4)
        if dt.hour < offset:
            return (dt - datetime.timedelta(days=1)).date()
        return dt.date()

    # ===========================
    # 报表数据接口 (保留原有逻辑，仅调整数据源)
    # ===========================
    def get_week_stats(self, anchor_date):
        start_of_week = anchor_date - datetime.timedelta(days=anchor_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        records = self.load_records()
        daily_hours = [0.0] * 7 
        start_hour_dist = [0] * 24
        
        for r in records:
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            logical_date = self.get_logical_date(s_dt)
            
            if start_of_week <= logical_date <= end_of_week:
                idx = (logical_date - start_of_week).days
                if 0 <= idx <= 6:
                    daily_hours[idx] += r['duration'] / 3600.0
                start_hour_dist[s_dt.hour] += 1
                
        date_str = f"{start_of_week.strftime('%Y-%m-%d')} 至 {end_of_week.strftime('%Y-%m-%d')}"
        return daily_hours, start_hour_dist, date_str

    def get_month_stats_heatmap(self, year, month):
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
        records = self.load_records()
        monthly_hours = [0.0] * 12
        monthly_days_sets = [set() for _ in range(12)]
        start_hour_dist = [0] * 24
        
        for r in records:
            s_dt = datetime.datetime.strptime(r['start'], "%Y-%m-%d %H:%M:%S")
            logical_date = self.get_logical_date(s_dt)
            
            if logical_date.year == year:
                m_idx = logical_date.month - 1
                monthly_hours[m_idx] += r['duration'] / 3600.0
                monthly_days_sets[m_idx].add(logical_date.day)
                start_hour_dist[s_dt.hour] += 1
                
        monthly_days = [len(s) for s in monthly_days_sets]
        return monthly_hours, monthly_days, start_hour_dist