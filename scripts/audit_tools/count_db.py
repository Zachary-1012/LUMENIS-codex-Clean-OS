import sqlite3
c = sqlite3.connect(r"D:\Taikoo-monitor-new\data\monitor.db")
tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table' order by name")]
print("表总数:", len(tabs))
tot = 0
for t in tabs:
    try:
        n = c.execute('select count(*) from "' + t + '"').fetchone()[0]
        tot += n
        if n > 0:
            print(f"{n:>8}  {t}")
    except Exception as e:
        print("ERR", t, e)
print("全库总行数:", tot)
