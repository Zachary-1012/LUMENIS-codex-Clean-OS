import sqlite3
conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()

# 检查表结构
tables = ['web_topics', 'web_events', 'weekly_events', 'notification_logs', 'notification_config']
for table in tables:
    print(f"\n=== {table} 表结构 ===")
    try:
        c.execute(f"PRAGMA table_info({table})")
        columns = c.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        c.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  数据量: {c.fetchone()[0]} 条")
    except Exception as e:
        print(f"  错误: {e}")

conn.close()
