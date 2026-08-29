"""检查采集器运行情况"""
import sqlite3
import json
import os

conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()

print("=== 1. 笔记总数和最新采集 ===")
c.execute("SELECT COUNT(*) FROM notes")
print(f"  笔记总数: {c.fetchone()[0]}")

c.execute("SELECT MAX(collected_at) FROM notes")
print(f"  最新采集时间: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at)=date('now','localtime')")
print(f"  今日采集笔记: {c.fetchone()[0]}")

print("\n=== 2. 最近10条笔记 ===")
c.execute("SELECT note_id, title, collected_at, publish_date, sentiment FROM notes ORDER BY collected_at DESC LIMIT 10")
rows = c.fetchall()
for r in rows:
    print(f"  [{r[2]}] {r[4]} | publish={r[3]} | {str(r[1])[:40]}")

print("\n=== 3. collection_logs最新20条 ===")
try:
    c.execute("SELECT id, keyword, notes_count, status, error_msg, started_at, finished_at FROM collection_logs ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    for r in rows:
        error = str(r[4])[:50] if r[4] else ''
        print(f"  id={r[0]} kw={r[1]} count={r[2]} status={r[3]} start={r[5]} error={error}")
except Exception as e:
    print(f"  查询失败: {e}")

print("\n=== 4. 采集计数文件 ===")
if os.path.exists('data/collector_stats.json'):
    with open('data/collector_stats.json', 'r', encoding='utf-8') as f:
        stats = json.load(f)
    print(f"  日期: {stats.get('date')}")
    print(f"  今日采集: {stats.get('manual_runs',0)+stats.get('auto_runs',0)}次 (手动{stats.get('manual_runs',0)}/自动{stats.get('auto_runs',0)})")
    print(f"  最后更新: {stats.get('updated_at')}")
else:
    print("  采集计数文件不存在")

print("\n=== 5. 检查笔记正文情况 ===")
c.execute("SELECT COUNT(*) FROM notes WHERE content IS NOT NULL AND content != ''")
print(f"  有正文的笔记: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM notes WHERE content IS NULL OR content = ''")
print(f"  无正文的笔记: {c.fetchone()[0]}")

conn.close()
print("\n检查完成")
