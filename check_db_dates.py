"""检查数据库笔记发布日期分布和负面确认状态"""
import sqlite3

conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()

print("=== 1. 最近10天发布日期分布 ===")
c.execute('SELECT date(publish_date) as pub_date, COUNT(*) as cnt FROM notes WHERE publish_date IS NOT NULL GROUP BY pub_date ORDER BY pub_date DESC LIMIT 10')
rows = c.fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}条")

print("\n=== 2. 近2天发布的笔记 ===")
c.execute('SELECT COUNT(*) FROM notes WHERE date(publish_date) >= date("now", "-1 day")')
print(f"  近2天发布: {c.fetchone()[0]}条")

print("\n=== 3. 负面笔记确认状态 ===")
c.execute('SELECT COUNT(*) FROM notes WHERE sentiment="negative"')
print(f"  负面笔记总数: {c.fetchone()[0]}条")
c.execute('SELECT COUNT(*) FROM notes WHERE sentiment="negative" AND negative_confirmed=1')
print(f"  已二次确认: {c.fetchone()[0]}条")
c.execute('SELECT COUNT(*) FROM notes WHERE sentiment="negative" AND (negative_confirmed=0 OR negative_confirmed IS NULL)')
print(f"  待确认: {c.fetchone()[0]}条")
c.execute('SELECT COUNT(*) FROM notes WHERE sentiment="negative" AND negative_confirmed=2')
print(f"  已驳回: {c.fetchone()[0]}条")

print("\n=== 4. 笔记采集时间 vs 发布时间对比 ===")
c.execute('SELECT date(collected_at) as col_date, date(publish_date) as pub_date, COUNT(*) as cnt FROM notes WHERE publish_date IS NOT NULL GROUP BY col_date, pub_date ORDER BY col_date DESC LIMIT 10')
rows = c.fetchall()
for r in rows:
    print(f"  采集:{r[0]} 发布:{r[1]} 数量:{r[2]}条")

print("\n=== 5. 过期笔记（发布时间早于采集时间7天以上）===")
c.execute('SELECT COUNT(*) FROM notes WHERE publish_date IS NOT NULL AND julianday(collected_at) - julianday(publish_date) > 7')
print(f"  过期笔记数量: {c.fetchone()[0]}条")

conn.close()
