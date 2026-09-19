"""
系统时间节点与响应时间评估工具
对比商用系统标准，找出可能导致崩溃的时间相关问题
"""
import urllib.request
import json
import base64
import time
import os
import sqlite3
from datetime import datetime
from lumenis.shared.database import get_repository

BASE_URL = "http://127.0.0.1:8200"
AUTH = base64.b64encode(b'Zachary:Zachary01').decode()
HEADERS = {'Authorization': f'Basic {AUTH}'}

def api_call(path, timeout=10):
    """调用API并返回响应时间和结果"""
    start = time.time()
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}", headers=HEADERS)
        response = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(response.read())
        elapsed = (time.time() - start) * 1000  # 毫秒
        return True, elapsed, data
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return False, elapsed, str(e)

print("=" * 70)
print("广州太古汇舆情监测系统 - 时间节点与响应时间评估")
print(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================
# 第一部分：API响应时间测量
# ============================================
print("\n【第一部分：API响应时间测量】")
print("-" * 70)

apis_to_test = [
    ("/api/architecture/status", "架构状态"),
    ("/api/system/health/detailed", "系统健康详细"),
    ("/api/settings/config", "设置配置"),
    ("/api/settings/system-info", "系统信息"),
    ("/api/export/preview?period=daily", "日报导出预览"),
    ("/api/export/preview?period=weekly", "周报导出预览"),
    ("/api/pr/cases", "公关案例列表"),
    ("/api/pr/templates", "公关话术模板"),
    ("/api/negative/pending?page=1&page_size=1", "负面确认待处理"),
    ("/api/alerts?unread=1", "告警通知"),
    ("/api/adaptive/status", "自适应引擎状态"),
    ("/api/collector/status", "采集器状态"),
    ("/api/local-ai/status", "本地AI状态"),
    ("/api/ai/providers", "AI提供商列表"),
    ("/api/notes?page=1&page_size=10", "笔记列表(10条)"),
    ("/api/events?page=1&page_size=10", "事件列表(10条)"),
    ("/api/overview", "首页概览"),
    ("/api/stats", "统计数据"),
    ("/api/hot-topics?limit=14", "热门话题"),
    ("/api/risk-alerts", "风险预警"),
]

print(f"{'API路径':<45} {'响应时间(ms)':<12} {'状态':<8} {'商用标准':<10}")
print("-" * 70)

# 商用系统响应时间标准
# <100ms: 优秀
# 100-300ms: 良好
# 300-500ms: 一般
# 500-1000ms: 较差
# >1000ms: 很差，可能导致超时

slow_apis = []
for path, name in apis_to_test:
    ok, elapsed, data = api_call(path, timeout=15)
    if ok:
        if elapsed < 100:
            standard = "✅ 优秀"
        elif elapsed < 300:
            standard = "🟢 良好"
        elif elapsed < 500:
            standard = "🟡 一般"
        elif elapsed < 1000:
            standard = "🟠 较差"
        else:
            standard = "🔴 很差"
            slow_apis.append((name, path, elapsed))
        print(f"{name:<45} {elapsed:<12.0f} {'✅':<8} {standard}")
    else:
        print(f"{name:<45} {'超时':<12} {'❌':<8} 失败")
        slow_apis.append((name, path, 99999))

# ============================================
# 第二部分：系统时间节点配置检查
# ============================================
print("\n\n【第二部分：系统时间节点配置检查】")
print("-" * 70)

# 检查system_config.json中的时间配置
try:
    with open('system_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n1. 采集调度时间点:")
    auto_hours = config.get('collection', {}).get('auto_schedule_hours', [])
    print(f"   自动采集时间点: {auto_hours}")
    print(f"   每日自动采集次数: {len(auto_hours)}次")
    print(f"   采集间隔(平均): {24/len(auto_hours):.1f}小时" if len(auto_hours) > 0 else "")
    print(f"   冷却时间: {config.get('collection', {}).get('cooldown_minutes', 'N/A')}分钟")
    print(f"   商用标准: 每2-4小时一次，冷却15-30分钟")
    
    print("\n2. 报告推送时间:")
    report = config.get('report', {})
    print(f"   日报推送时间: {report.get('daily_push_time', 'N/A')}")
    print(f"   周报推送日: {report.get('weekly_push_day', 'N/A')}")
    print(f"   周报推送时间: {report.get('weekly_push_time', 'N/A')}")
    print(f"   月报推送日: 每月{report.get('monthly_push_day', 'N/A')}号")
    print(f"   商用标准: 日报9-10点，周报周一9-10点")
    
    print("\n3. AI分析配置:")
    ai = config.get('ai', {})
    print(f"   异步分析: {ai.get('async_analysis', 'N/A')}")
    print(f"   每次最大分析数: {ai.get('max_analysis_per_run', 'N/A')}")
    print(f"   商用标准: 异步分析，批量处理，避免阻塞")
    
    print("\n4. 自适应引擎策略:")
    print(f"   正常策略请求间隔: 55秒(已设置)")
    print(f"   商用标准: 2-5秒(高频), 30-60秒(低频防风控)")
    
except Exception as e:
    print(f"读取配置失败: {e}")

# ============================================
# 第三部分：数据库查询性能检查
# ============================================
print("\n\n【第三部分：数据库查询性能检查】")
print("-" * 70)

try:
    conn = get_repository().connect()
    c = conn.cursor()
    
    tables_to_check = [
        ('notes', '笔记表'),
        ('events', '事件表'),
        ('comments', '评论表'),
        ('daily_reports', '日报表'),
    ]
    
    print(f"{'表名':<20} {'记录数':<10} {'COUNT查询(ms)':<15} {'SELECT*(ms)':<15}")
    print("-" * 70)
    
    for table, desc in tables_to_check:
        try:
            # COUNT查询
            start = time.time()
            count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            count_time = (time.time() - start) * 1000
            
            # SELECT * 查询（限制10条）
            start = time.time()
            c.execute(f"SELECT * FROM {table} LIMIT 10").fetchall()
            select_time = (time.time() - start) * 1000
            
            print(f"{desc:<20} {count:<10} {count_time:<15.2f} {select_time:<15.2f}")
        except Exception as e:
            print(f"{desc:<20} 错误: {e}")
    
    conn.close()
except Exception as e:
    print(f"数据库检查失败: {e}")

# ============================================
# 第四部分：时间相关问题分析
# ============================================
print("\n\n【第四部分：时间相关问题分析与崩溃原因推测】")
print("-" * 70)

print("""
可能导致系统崩溃的时间相关问题分析：

1. ⚠️ API响应时间过长
   - 如果某个API响应时间>5秒，可能导致：
     * 前端请求超时，用户反复刷新
     * 服务器线程被长时间占用
     * 多个慢请求堆积，最终耗尽资源
   - 商用标准：95%的API应在500ms内响应

2. ⚠️ 定时任务时间冲突
   - 如果多个定时任务在同一时间执行：
     * 9点：日报生成 + 周报生成 + 邮件推送 + 采集
     * 可能导致CPU/内存峰值，系统崩溃
   - 商用标准：定时任务应错峰执行，间隔至少5分钟

3. ⚠️ 采集间隔与超时设置
   - 采集请求间隔55秒（防风控），但如果单次采集超时设置过短：
     * 采集未完成就被强制终止
     * 残留进程占用资源
   - 商用标准：采集超时应设置为采集预期时间的2-3倍

4. ⚠️ 守护闭环重启等待时间
   - 如果系统崩溃后，守护闭环等待30秒就重启：
     * 前一个进程可能还没完全释放资源
     * 端口未释放，新进程启动失败
   - 商用标准：重启前应确保旧进程完全终止，端口释放

5. ⚠️ 数据库查询性能
   - 如果笔记表数据量大，没有索引：
     * 每次查询都全表扫描，响应时间长
     * 高并发时数据库锁等待，系统卡死
   - 商用标准：常用查询字段必须建索引，查询应<100ms
""")

# ============================================
# 第五部分：优化建议
# ============================================
print("\n【第五部分：优化建议】")
print("-" * 70)

print("""
基于以上分析，建议的优化措施：

1. 🔧 API响应时间优化
   - 对慢API添加缓存（cache_manager.py已有）
   - 大数据量查询分页，避免一次性返回过多数据
   - 复杂计算异步处理，API立即返回

2. 🔧 定时任务错峰执行
   - 日报生成：9:00
   - 邮件推送：9:05
   - 周报生成：周一9:10
   - 采集：避开整点，改为8:05, 10:05等

3. 🔧 采集超时设置
   - 单次采集超时：设置为10分钟（600秒）
   - 详情页抓取超时：30秒
   - 确保采集完成后再终止

4. 🔧 守护闭环优化
   - 重启前：强制杀死所有python进程，等待端口释放
   - 重启后：等待60秒稳定，再检测健康状态
   - 添加重启频率限制：1小时内最多重启5次

5. 🔧 数据库优化
   - 检查notes表的索引（title, publish_time, sentiment, is_negative）
   - 定期清理过期数据或归档
   - 慢查询日志记录

6. 🔧 内存泄漏排查
   - 监控系统运行时的内存增长曲线
   - 检查是否有大对象未释放（如采集结果、报告数据）
   - 考虑添加定时内存清理
""")

print("\n" + "=" * 70)
print("评估完成！建议优先检查慢API和定时任务冲突，这两个最可能导致崩溃。")
print("=" * 70)
