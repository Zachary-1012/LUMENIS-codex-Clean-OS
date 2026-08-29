# 工具脚本目录

广州太古汇舆情监测系统 - 工具脚本

## 脚本列表

### 1. init_db.py - 初始化数据库
创建所有必需的数据库表和索引，插入默认配置。

```bash
python scripts/init_db.py
```

### 2. backup_db.py - 数据库备份
备份、列出、恢复数据库。

```bash
# 备份数据库
python scripts/backup_db.py backup

# 列出所有备份
python scripts/backup_db.py list

# 恢复数据库
python scripts/backup_db.py restore <backup_name>
```

### 3. check_system.py - 系统检查
检查系统运行状态、数据库、配置文件等。

```bash
python scripts/check_system.py
```

### 4. collect_now.py - 立即采集
触发一次小红书舆情采集。

```bash
# 默认采集（关键词：广州太古汇）
python scripts/collect_now.py

# 指定关键词
python scripts/collect_now.py "广州太古汇 投诉"

# 指定参数
python scripts/collect_now.py "广州太古汇" 5 20
```

### 5. export_report.py - 报告导出
导出日报、周报、月报、年报。

```bash
# 导出日报（Word格式）
python scripts/export_report.py daily

# 导出周报（Excel格式）
python scripts/export_report.py weekly 2026-08-27 excel

# 导出月报
python scripts/export_report.py monthly 2026-08

# 导出年报
python scripts/export_report.py yearly 2026
```

## 使用说明

所有脚本都需要在项目根目录下运行，或者将项目根目录添加到Python路径中。

```bash
cd /path/to/taikoo-monitor
python scripts/<script_name>.py [arguments]
```

## 注意事项

1. 运行脚本前请确保已安装所有依赖（`pip install -r requirements.txt`）
2. 数据库备份会自动保留最近10个备份
3. 采集脚本会检查每日采集次数限制（手动3次/自动9次）
4. 报告导出需要report_engine或daily_report模块
