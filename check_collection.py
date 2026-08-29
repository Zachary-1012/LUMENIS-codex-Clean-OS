"""检查采集结果和任务状态"""
import sqlite3
import json
import os

conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()

print("=== 数据库笔记统计 ===")
c.execute('SELECT COUNT(*) FROM notes')
print(f"笔记总数: {c.fetchone()[0]}")

c.execute('SELECT MAX(collected_at) FROM notes')
print(f"最新采集时间: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at)=date('now')")
print(f"今日采集笔记: {c.fetchone()[0]}")

print("\n=== 最近5条笔记 ===")
c.execute("SELECT note_id, title, collected_at, sentiment FROM notes ORDER BY collected_at DESC LIMIT 5")
rows = c.fetchall()
for r in rows:
    print(f"  [{r[2]}] {r[3]} | {str(r[1])[:50]}")

print("\n=== 采集计数文件 ===")
if os.path.exists('data/collector_stats.json'):
    with open('data/collector_stats.json', 'r', encoding='utf-8') as f:
        stats = json.load(f)
    print(f"日期: {stats.get('date')}")
    print(f"今日采集次数: {stats.get('manual_runs', 0) + stats.get('auto_runs', 0)}")
    print(f"手动: {stats.get('manual_runs', 0)}, 自动: {stats.get('auto_runs', 0)}")
    print(f"最后采集时间: {stats.get('updated_at')}")

print("\n=== 最新5条采集日志 ===")
try:
    c.execute("SELECT id, status, created_at FROM collection_logs ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    for r in rows:
        print(f"  [{r[2]}] {r[1]} (id={r[0]})")
except Exception as e:
    print(f"  查询失败: {e}")

conn.close()
