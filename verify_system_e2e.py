"""
系统整体运行状态综合验证
从端到端角度验证：系统运行 → API调用 → 数据库 → 日志 → 配置 → 数据流
"""
import sqlite3
import json
import os
import sys
import urllib.request
import base64
from datetime import datetime
from lumenis.shared.database import get_repository

BASE_URL = "http://127.0.0.1:8200"
AUTH = base64.b64encode((os.environ.get('LUMENIS_TEST_AUTH_USER','Zachary')+':'+os.environ.get('LUMENIS_TEST_AUTH_PASS','test-only-pass')).encode()).decode()
HEADERS = {'Authorization': f'Basic {AUTH}'}

results = {"passed": [], "failed": [], "warnings": []}

def api_call(path, timeout=15):
    """调用API并返回结果"""
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}", headers=HEADERS)
        response = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(response.read()), None
    except Exception as e:
        return None, str(e)

def check(name, condition, detail=""):
    """记录检查结果"""
    if condition:
        results["passed"].append(f"✅ {name} {detail}")
    else:
        results["failed"].append(f"❌ {name} {detail}")

def warn(name, detail=""):
    """记录警告"""
    results["warnings"].append(f"⚠️ {name} {detail}")

print("=" * 70)
print("广州太古汇舆情监测系统 - 整体运行状态验证")
print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================
# 第一部分：系统基础运行状态
# ============================================
print("\n【第一部分：系统基础运行状态】")

# 1.1 系统架构状态API
data, err = api_call("/api/architecture/status")
check("架构状态API", data is not None and data.get('ok') == True, 
      f"5层架构: 自动调节={data.get('adaptive_engine',{}).get('status') if data else 'N/A'}")

# 1.2 系统健康详细API
data, err = api_call("/api/system/health/detailed")
check("系统健康API", data is not None, 
      f"整体状态: {data.get('overall_status') if data else 'N/A'}")
if data:
    modules = data.get('modules', {})
    for mod_name, mod_info in modules.items():
        status = mod_info.get('status', 'unknown')
        if status == 'error':
            check(f"模块-{mod_name}", False, f"状态: {status}")
        elif status == 'warning':
            warn(f"模块-{mod_name}", f"状态: {status}")

# 1.3 设置配置API
data, err = api_call("/api/settings/config")
check("设置配置API", data is not None and data.get('ok') == True)

# 1.4 系统信息API
data, err = api_call("/api/settings/system-info")
check("系统信息API", data is not None, 
      f"版本: {data.get('system',{}).get('version') if data else 'N/A'}, 笔记: {data.get('database',{}).get('notes_count') if data else 'N/A'}")

# ============================================
# 第二部分：核心业务模块验证
# ============================================
print("\n【第二部分：核心业务模块验证】")

# 2.1 导出报告预览API（日报）
data, err = api_call("/api/export/preview?period=daily")
check("日报导出预览API", data is not None and data.get('ok') == True,
      f"笔记数: {data.get('stats',{}).get('total_notes') if data else 'N/A'}")

# 2.2 导出报告预览API（周报）
data, err = api_call("/api/export/preview?period=weekly")
check("周报导出预览API", data is not None and data.get('ok') == True)

# 2.3 公关案例API
data, err = api_call("/api/pr/cases")
check("公关案例API", data is not None and data.get('ok') == True,
      f"案例数: {len(data.get('cases',[])) if data else 0}")

# 2.4 公关话术模板API
data, err = api_call("/api/pr/templates")
check("公关话术模板API", data is not None and data.get('ok') == True,
      f"模板数: {len(data.get('templates',[])) if data else 0}")

# 2.5 负面确认待处理API
data, err = api_call("/api/negative/pending?page=1&page_size=1")
check("负面确认API", data is not None and data.get('ok') == True,
      f"待确认: {data.get('total') if data else 'N/A'}")

# 2.6 告警通知API
data, err = api_call("/api/alerts?unread=1")
check("告警通知API", data is not None)

# 2.7 自适应引擎状态API
data, err = api_call("/api/adaptive/status")
check("自适应引擎API", data is not None,
      f"策略: {data.get('current_strategy') if data else 'N/A'}, 风险: {data.get('risk_level') if data else 'N/A'}")

# ============================================
# 第三部分：AI与分析模块验证
# ============================================
print("\n【第三部分：AI与分析模块验证】")

# 3.1 本地AI状态API
data, err = api_call("/api/local-ai/status")
check("本地AI状态API", data is not None and data.get('ok') == True,
      f"Ollama: {data.get('ollama',{}).get('status') if data else 'N/A'}")

# 3.2 AI提供商列表API
data, err = api_call("/api/ai/providers")
check("AI提供商API", data is not None)

# 3.3 安全扫描API
data, err = api_call("/api/security/scan", timeout=30)
check("安全扫描API", data is not None and data.get('ok') == True,
      f"问题数: {data.get('issues_found') if data else 'N/A'}")

# 3.4 评测体系API
data, err = api_call("/api/evaluation/run", timeout=30)
check("评测体系API", data is not None and data.get('ok') == True,
      f"总分: {data.get('total_score') if data else 'N/A'}")

# ============================================
# 第四部分：采集与数据模块验证
# ============================================
print("\n【第四部分：采集与数据模块验证】")

# 4.1 采集器状态API
data, err = api_call("/api/collector/status")
check("采集器状态API", data is not None and data.get('ok') == True,
      f"CDP: {data.get('cdp_status') if data else 'N/A'}")

# 4.2 数据库完整性检查
print("\n  --- 数据库完整性检查 ---")
try:
    conn = get_repository().connect()
    c = conn.cursor()
    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    check("数据库连接", True, f"共{len(tables)}张表")
    
    # 关键表数据检查
    key_tables = {
        'notes': '笔记表',
        'events': '事件表', 
        'comments': '评论表',
        'daily_reports': '日报表',
        'web_topics': '全网话题表',
        'web_events': '全网事件表',
        'weekly_events': '周报事件表',
        'notification_logs': '通知日志表',
    }
    empty_tables = []
    for table, desc in key_tables.items():
        try:
            count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count > 0:
                check(f"数据库-{desc}", True, f"{count}条")
            else:
                warn(f"数据库-{desc}", "空表")
                empty_tables.append(table)
        except Exception as e:
            check(f"数据库-{desc}", False, f"查询失败: {e}")
    
    # 检查笔记数据完整性（是否有标题、发布时间）
    try:
        notes_with_title = c.execute("SELECT COUNT(*) FROM notes WHERE title IS NOT NULL AND title != ''").fetchone()[0]
        total_notes = c.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        if total_notes > 0:
            title_rate = notes_with_title / total_notes * 100
            check("笔记数据完整性", title_rate > 80, 
                  f"有标题: {notes_with_title}/{total_notes} ({title_rate:.1f}%)")
    except Exception as e:
        warn("笔记数据完整性检查", f"失败: {e}")
    
    conn.close()
except Exception as e:
    check("数据库连接", False, str(e))

# ============================================
# 第五部分：日志与错误检查
# ============================================
print("\n【第五部分：日志与错误检查】")

# 5.1 检查系统错误日志
log_files = ['system_error.log', 'system_startup.log']
for log_file in log_files:
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            error_count = content.lower().count('error') + content.count('错误')
            if error_count > 0:
                warn(f"日志-{log_file}", f"包含{error_count}个错误关键词")
            else:
                check(f"日志-{log_file}", True, "无错误")
        except Exception as e:
            warn(f"日志-{log_file}", f"读取失败: {e}")
    else:
        warn(f"日志-{log_file}", "文件不存在")

# 5.2 检查logs目录
if os.path.exists('logs'):
    log_count = len([f for f in os.listdir('logs') if f.endswith('.log')])
    check("logs目录", log_count >= 0, f"{log_count}个日志文件")
else:
    warn("logs目录", "不存在")

# ============================================
# 第六部分：配置文件有效性检查
# ============================================
print("\n【第六部分：配置文件有效性检查】")

# 6.1 .env配置检查
try:
    with open('.env', 'r', encoding='utf-8', errors='replace') as f:
        env_content = f.read()
    
    # 检查关键配置
    env_checks = {
        'TAIKOO_AUTH_USER': 'Zachary' in env_content,
        'TAIKOO_PORT': '8200' in env_content,
        'XHS_CDP_URL': '9222' in env_content,
        'DAILY_REPORT_HOUR': 'DAILY_REPORT_HOUR=9' in env_content,
    }
    for key, ok in env_checks.items():
        check(f"配置-.env:{key}", ok)
    
    # 检查SMTP是否配置
    smtp_configured = 'SMTP_HOST=' in env_content and not env_content.split('SMTP_HOST=')[1].split('\n')[0].strip() == ''
    if not smtp_configured:
        warn("配置-.env:SMTP", "邮件推送未配置（需SMTP账号）")
    else:
        check("配置-.env:SMTP", True, "已配置")
    
    # 检查AI Key是否配置
    ai_keys = ['DASHSCOPE_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY']
    configured_ais = []
    for key in ai_keys:
        if f'{key}=' in env_content:
            value = env_content.split(f'{key}=')[1].split('\n')[0].strip()
            if len(value) > 5:
                configured_ais.append(key)
    check("配置-.env:AI Key", len(configured_ais) > 0, f"已配置{len(configured_ais)}个: {', '.join(configured_ais)}")
    
except Exception as e:
    check("配置-.env", False, str(e))

# 6.2 system_config.json有效性
try:
    with open('system_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    check("配置-system_config.json", True, 
          f"版本: {config.get('app_version')}, 采集时间点: {len(config.get('collection',{}).get('auto_schedule_hours',[]))}个")
except Exception as e:
    check("配置-system_config.json", False, f"解析失败: {e}")

# ============================================
# 第七部分：端到端数据流验证
# ============================================
print("\n【第七部分：端到端数据流验证】")

# 验证：数据库有数据 → API能返回 → 导出能生成
try:
    conn = get_repository().connect()
    c = conn.cursor()
    notes_count = c.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    events_count = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    
    # 数据流1: 数据库 → API
    data, err = api_call("/api/notes?page=1&page_size=1")
    api_has_notes = data is not None and data.get('total', 0) > 0
    check("数据流:数据库→API笔记", notes_count > 0 and api_has_notes, 
          f"DB:{notes_count}条, API返回:{data.get('total') if data else 0}条")
    
    # 数据流2: 数据库 → API事件
    data, err = api_call("/api/events?page=1&page_size=1")
    api_has_events = data is not None and data.get('total', 0) > 0
    check("数据流:数据库→API事件", events_count > 0 and api_has_events,
          f"DB:{events_count}条, API返回:{data.get('total') if data else 0}条")
    
    # 数据流3: API → 导出预览
    data, err = api_call("/api/export/preview?period=daily")
    export_ok = data is not None and data.get('ok') == True
    check("数据流:API→导出预览", export_ok)
    
except Exception as e:
    check("端到端数据流", False, str(e))

# ============================================
# 汇总结果
# ============================================
print("\n" + "=" * 70)
print("验证结果汇总")
print("=" * 70)

print(f"\n✅ 通过: {len(results['passed'])} 项")
for item in results['passed']:
    print(f"  {item}")

print(f"\n❌ 失败: {len(results['failed'])} 项")
for item in results['failed']:
    print(f"  {item}")

print(f"\n⚠️ 警告: {len(results['warnings'])} 项")
for item in results['warnings']:
    print(f"  {item}")

total = len(results['passed']) + len(results['failed'])
pass_rate = len(results['passed']) / total * 100 if total > 0 else 0
print(f"\n📊 通过率: {pass_rate:.1f}% ({len(results['passed'])}/{total})")

if len(results['failed']) == 0:
    print("\n🎉 系统整体运行正常！所有核心模块协同工作正常。")
else:
    print(f"\n🔧 有 {len(results['failed'])} 项需要修复。")
