import sqlite3
SRC = r"D:\Taikoo-staging-ui\staging\monitor.staging.db"
con = sqlite3.connect(SRC)

def cols(t):
    return [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]

print("===== notes 发布时间字段可用性（趋势按发布日的前提）=====")
print("notes列:", [c for c in cols("notes") if "publish" in c or "collect" in c or "time" in c or "date" in c])
for f in ["publish_datetime","publish_date","collected_at","captured_at"]:
    try:
        total=con.execute('select count(*) from notes').fetchone()[0]
        nonnull=con.execute(f'select count(*) from notes where "{f}" is not null and "{f}"<>""').fetchone()[0]
        print(f"  {f}: 非空 {nonnull}/{total}")
    except Exception as e:
        print(f"  {f}: 无此列 {str(e)[:40]}")
print("  按发布日分组示例(前10):")
try:
    for r in con.execute("select substr(coalesce(publish_datetime,publish_date),1,10) d, count(*) c from notes group by d order by d desc limit 10"):
        print("   ", r)
except Exception as e:
    print("   ERR", e)

print("\n===== 话题端监测（topic_*）结构与用户任务 =====")
for t in ["topic_campaigns","topic_campaign_topics","topic_campaign_notes","topic_campaign_snapshots"]:
    print(f"\n[{t}] 列:", cols(t))
    n=con.execute(f'select count(*) from "{t}"').fetchone()[0]
    print(f"行数={n}")
    if t in ("topic_campaigns","topic_campaign_topics") and n:
        for row in con.execute(f'select * from "{t}" limit 10'):
            print("   ", tuple(str(x)[:40] for x in row))
con.close()
