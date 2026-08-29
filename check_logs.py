"""检查采集日志表结构和详细结果"""
import sqlite3

conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()

print("=== collection_logs表结构 ===")
c.execute("PRAGMA table_info(collection_logs)")
columns = c.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n=== 最新10条采集日志 ===")
try:
    c.execute("SELECT * FROM collection_logs ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    col_names = [desc[0] for desc in c.description]
    for row in rows:
        row_dict = dict(zip(col_names, row))
        print(f"  id={row_dict.get('id')} status={row_dict.get('status')} keyword={row_dict.get('keyword','')[:20]}")
        if row_dict.get('message'):
            print(f"    message: {str(row_dict['message'])[:100]}")
except Exception as e:
    print(f"  查询失败: {e}")

print("\n=== collector_quality_log表结构 ===")
try:
    c.execute("PRAGMA table_info(collector_quality_log)")
    columns = c.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    print("\n=== 最新5条质量日志 ===")
    c.execute("SELECT * FROM collector_quality_log ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    col_names = [desc[0] for desc in c.description]
    for row in rows:
        row_dict = dict(zip(col_names, row))
        print(f"  {row_dict}")
except Exception as e:
    print(f"  查询失败: {e}")

conn.close()
