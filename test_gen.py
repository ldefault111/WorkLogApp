import json
import os
import datetime
import random

def generate_mock_data():
    # 1. 定义新结构
    data = {
        "settings": {
            "day_offset_hour": 4,      # 设置凌晨4点算新一天
            "pomodoro_duration": 25
        },
        "records": []
    }

    # 2. 生成最近 14 天的数据
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)
    
    current_day = start_date
    while current_day <= end_date:
        # 每天生成 2-4 条记录
        num_records = random.randint(2, 4)
        
        for _ in range(num_records):
            # 随机开始时间：从早上9点到凌晨2点(次日)
            # 模拟跨天逻辑：如果在凌晨 01:00 工作，应该属于 logical_date 的前一天
            
            # 基础时间：当天上午9点
            base_time = datetime.datetime.combine(current_day, datetime.time(9, 0))
            
            # 随机增加 0 ~ 18小时 (即 09:00 ~ 次日 03:00)
            start_dt = base_time + datetime.timedelta(hours=random.randint(0, 18), minutes=random.randint(0, 59))
            
            # 持续时间 25分钟 ~ 2小时
            duration_minutes = random.randint(25, 120)
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
            
            record = {
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration_minutes * 60
            }
            data["records"].append(record)
        
        current_day += datetime.timedelta(days=1)

    # 3. 写入数据文件 work_data.json
    filename = "work_data.json"
    abs_path = os.path.abspath(filename)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"[成功] 已生成测试数据: {filename}")
    print(f"       包含记录数: {len(data['records'])}")
    print(f"       设置 Day Offset: {data['settings']['day_offset_hour']}")

    # 4. 写入指针文件 app_pointer.json
    pointer_file = "app_pointer.json"
    with open(pointer_file, 'w', encoding='utf-8') as f:
        json.dump({"data_path": abs_path}, f, indent=4)
    print(f"[成功] 已生成指针文件: {pointer_file}")
    print(f"       指向: {abs_path}")

if __name__ == "__main__":
    generate_mock_data()