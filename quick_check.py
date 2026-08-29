"""快速检查系统状态"""
import sqlite3
import os

print("=== 1. 今天采集的笔记 ===")
conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at)='2026-08-28'")
print(f"  今天采集笔记数: {c.fetchone()[0]}")
c.execute("SELECT note_id, title, collected_at FROM notes WHERE date(collected_at)='2026-08-28' ORDER BY collected_at DESC LIMIT 5")
rows = c.fetchall()
for r in rows:
    print(f"    {r[2]} | {str(r[1])[:40]}")

print("\n=== 2. 笔记总数和最新采集 ===")
c.execute("SELECT COUNT(*) FROM notes")
print(f"  笔记总数: {c.fetchone()[0]}")
c.execute("SELECT MAX(collected_at) FROM notes")
print(f"  最新采集: {c.fetchone()[0]}")

print("\n=== 3. Zachary机器人相关文件 ===")
files = [
    'static/js/zachary_robot_enhanced.js',
    'static/js/zachary_robot.js',
    'static/css/zachary_robot.css',
    'static/js/nomi_global_drag.js',
]
for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  ✅ {f} ({size} bytes)")
    else:
        print(f"  ❌ {f} 不存在")

print("\n=== 4. base.html中Zachary引用 ===")
with open('templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()
if 'zachary' in content.lower():
    print("  ✅ base.html中有Zachary相关引用")
else:
    print("  ⚠️ base.html中没有Zachary相关引用")

if 'zachary_robot_enhanced.js' in content:
    print("  ✅ 引用了zachary_robot_enhanced.js")
else:
    print("  ⚠️ 没有引用zachary_robot_enhanced.js")

conn.close()
print("\n检查完成")
