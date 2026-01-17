# ⏳ My Work Logger (V1.1)

一个基于 Python (Tkinter) 开发的个人工作时长记录与番茄钟工具。
支持跨天工时统计、数据可视化报表、托盘最小化以及灵活的数据存储路径设置。

注：程序自用，没做完整测试，也没写说明文档

## ✨ 功能特性

- V1.1新增：周统计总时长
- 工作计时: 记录工作开始与结束时间，自动计算时长。
- 番茄专注: 内置番茄钟功能，专注结束后弹窗提醒。
- 智能跨天逻辑: 支持自定义“新的一天”开始时间（例如：凌晨 4 点前的记录仍归为前一天）。
- 数据可视化: 内置图表引擎，可查看周统计、月度热力图、年度统计等。
- 数据存储：数据存储为 JSON 格式，支持自定义数据文件路径，**不支持读写锁和多端同步修改**
- Tray 托盘集成：支持最小化到系统托盘，后台静默运行。
- 高 DPI 适配: 支持 Windows 10/11 高分屏，界面清晰不模糊。

## TODO
- 数据可视化界面大小与边框不一致需要拖动才能完整显示

## 🛠️ 安装与运行

### 1. 环境要求
- Python 3.8+
- Windows (建议 10 或 11)

### 2. 安装依赖
在项目根目录下打开终端，运行：
```bash
pip install -r requirements.txt
```
### 3. 运行程序
```bash
python run.py
```

## 📦 如何打包 (生成 .exe)
如果你想生成一个独立的 .exe 文件发给朋友或在没有 Python 的电脑上运行：
```bash
pyinstaller -F -w -n "WorkLogger" -i icon.ico run.py
```
打包完成后，可执行文件位于 dist/ 文件夹内。

## 📂 目录结构说明
run.py: 程序启动入口。

main_ui.py: 主界面 UI 逻辑与交互。

data_manager.py: 数据读写、存储逻辑与设置管理。

chart_engine.py: 报表与图表生成引擎。

work_data.json: (自动生成) 存储所有工作记录和用户习惯设置。

pathCfg.json: (自动生成) 用于定位数据文件的指针。

*test_gen.py：生成测试数据

*main.py：版本V0.1，单文件即可实现功能，但有bug

## 👨‍💻 开发者信息
Core Developer & Architect: Gemini 3 Pro (AI Model by Google)

Human Prompt Engineer & Product Owner: [ldefault111]

"Code written by AI, guided by Human Intelligence."

---
License: MIT
