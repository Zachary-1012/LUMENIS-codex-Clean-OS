# -*- coding: utf-8 -*-
"""
采集编排流水线冒烟：后台任务 → 六态 → 入库(web_mentions/web_runs/web_sources) → 健康中心
仅跑免登平台，避免真人浏览器/风控。手动触发：
.venv\\Scripts\\python.exe tests\\test_collect_pipeline.py
"""
import sys, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from v4_upgrade.adapters import registry, register_default_adapters
from v4_upgrade.adapters import collector_service as cs
from v4_upgrade.adapters.persist import get_conn

register_default_adapters()
print("platforms:", registry.list_platforms())

con = get_conn()
before = con.execute("SELECT COUNT(*) FROM web_mentions").fetchone()[0]
con.close()

tid = cs.start_collect("广州太古汇", ["sogou_search"], 10)
print("task:", tid)
for _ in range(40):
    t = cs.get_task(tid)
    print(f"  status={t['status']} {t['done']}/{t['total']}")
    if t["status"] == "finished":
        break
    time.sleep(1.5)

t = cs.get_task(tid)
print("\n=== per-platform ===")
for p, s in t["per_platform"].items():
    print(f"  {p}: state={s['state']} fetched={s['fetched']} "
          f"inserted={s['inserted']} updated={s['updated']} err={s['error'][:40]}")
print(f"total fetched={t['total_fetched']} inserted={t['total_inserted']}")

con = get_conn()
after = con.execute("SELECT COUNT(*) FROM web_mentions").fetchone()[0]
print("\nweb_mentions:", before, "->", after, "(+%d)" % (after - before))
print("\n=== latest web_runs ===")
for r in con.execute("SELECT adapter,fetched,accepted,rejected,error,finished_at FROM web_runs ORDER BY id DESC LIMIT 3"):
    print(" ", tuple(r))
print("\n=== web_sources sogou ===")
for r in con.execute("SELECT source_key,last_success_at,last_error,item_count FROM web_sources WHERE source_key='sogou_search'"):
    print(" ", tuple(r))
con.close()

print("\n=== health (sogou_search) ===")
for h in cs.get_health():
    if h["platform"] == "sogou_search":
        print(" ", h)
