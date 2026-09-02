# -*- coding: utf-8 -*-
"""存量数据质量审计（DataQualityGate 应用；只读，零风险）。

对 data/monitor.db 的 notes/events 跑数据质量门，输出通过率与失败字段分布，
发现存量坏数据（空标题/非法风险级/日期格式错等），为写入门接线提供基线。

用法：
  python scripts/quality_audit.py [--db data/monitor.db] [--limit 500]
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data_quality_gate import DataQualityGate  # noqa: E402

# notes 表字段 -> note 契约字段
_NOTE_MAP = {"title": "title", "url": "url", "risk_level": "risk_level",
             "publish_date": "publish_date"}


def _audit(gate, conn, table, map_fields, contract, limit):
    cols = ",".join(map_fields.keys())
    rows = conn.execute("SELECT %s FROM %s WHERE %s IS NOT NULL LIMIT ?"
                        % (cols, table, "id" if table == "events" else "id"),
                        (limit,)).fetchall()
    total = len(rows)
    passed = 0
    err_fields = {}
    err_samples = []
    for row in rows:
        rec = {f: row[i] for i, f in enumerate(map_fields.keys())}
        res = gate.validate(contract, rec)
        if res["valid"]:
            passed += 1
            continue
        for e in res["errors"]:
            f = e["field"]
            err_fields[f] = err_fields.get(f, 0) + 1
            if len(err_samples) < 5:
                err_samples.append("%s.%s=%r" % (e["rule"], f, rec.get(f)))
    return {"table": table, "total": total, "passed": passed,
            "failed": total - passed, "pass_rate": round(passed / total * 100, 1) if total else 0,
            "error_fields": err_fields, "samples": err_samples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "monitor.db"))
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    gate = DataQualityGate()
    conn = sqlite3.connect(args.db)
    report = {"db": args.db, "contracts": gate.list_contracts(), "tables": []}
    report["tables"].append(_audit(gate, conn, "notes", _NOTE_MAP, "note", args.limit))
    # events 用存量兼容契约 event_db（DB 无 event_type 列）
    report["tables"].append(_audit(gate, conn, "events",
                                   {"risk_level": "risk_level", "event_date": "event_date"},
                                   "event_db", args.limit))
    conn.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))
    # 退出码：无 error 字段 0，有则 1（供门控）
    bad = any(t["error_fields"] for t in report["tables"])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
