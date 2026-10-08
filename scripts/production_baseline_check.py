# -*- coding: utf-8 -*-
"""P0-A 生产安全基线检查（UNIFIED-BASELINE §四 施工规则的统一安全门）。

仅在当前任务确需运行/数据基线且已具备相应授权时使用；不作为每次修改的固定步骤：
  Git → Runtime → Data(含一致性备份) → Rollback → Evidence；历史 tests 字段不执行、不计 PASS
只读为主；唯一写操作：① sqlite 一致性备份到 staging/baseline-backups/
② Evidence JSON 写到 staging/baseline-evidence/（均已 gitignore，绝不入库、不碰生产库内容）。

用法：
  python scripts/production_baseline_check.py            # 实际基线核验（不执行测试套件）
  python scripts/production_baseline_check.py --full     # 已停用；明确拒绝旧测试参数
退出码：全部硬检查通过=0，存在 FAIL=1。
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BACKUP_DIR = os.path.join(ROOT, "staging", "baseline-backups")
EVIDENCE_DIR = os.path.join(ROOT, "staging", "baseline-evidence")
# 生产核心表（缺任一即 Data FAIL）
CORE_TABLES = ["notes", "events", "daily_reports", "web_mentions", "metric_snapshots"]
# 关键蓝图（注册缺失即 Runtime FAIL）
CORE_BLUEPRINTS = ["data_query", "collection", "evidence_api", "system_health"]


def _safe_rel(path, start=ROOT):
    """跨盘符时 relpath 会抛 ValueError，回退绝对路径（Windows C:/D: 盘场景）。"""
    try:
        return os.path.relpath(path, start)
    except ValueError:
        return os.path.abspath(path)


def _git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except Exception as e:  # noqa: BLE001
        return 999, "", str(e)


def check_git(report):
    seg = {"name": "git", "checks": {}}
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    rc1, head, _ = _git("rev-parse", "HEAD")
    rc2, subject, _ = _git("log", "-1", "--pretty=%s")
    rc3, status, _ = _git("status", "--porcelain")
    rc4, upstream, _ = _git("rev-list", "--left-right", "--count", "HEAD...origin/main")
    dirty = [ln for ln in status.splitlines() if ln.strip()]
    seg["checks"]["branch"] = {"ok": rc == 0, "value": branch}
    seg["checks"]["head"] = {"ok": rc1 == 0, "value": head[:12], "subject": subject}
    seg["checks"]["tracks_origin"] = {"ok": rc4 == 0, "value": upstream or "no-upstream"}
    # 未提交不算硬失败（巡检进程会并行改），但必须显式列出
    seg["checks"]["clean_tree"] = {"ok": True, "value": f"{len(dirty)} uncommitted entries",
                                   "details": dirty[:30]}
    seg["rollback_candidate"] = None
    rc5, prev, _ = _git("log", "-1", "--pretty=%H %s", "HEAD~1")
    if rc5 == 0:
        seg["rollback_candidate"] = prev
    seg["ok"] = all(c["ok"] for c in seg["checks"].values())
    report["git"] = seg
    return seg["ok"]


def check_runtime(report):
    seg = {"name": "runtime", "checks": {}}
    try:
        t0 = time.time()
        import app as flask_app  # noqa: E402
        import_ms = round((time.time() - t0) * 1000)
        rules = list(flask_app.app.url_map.iter_rules())
        bp_prefixes = sorted({r.endpoint.split(".")[0] for r in rules if "." in r.endpoint})
        seg["checks"]["import_app"] = {"ok": True, "value": f"{import_ms}ms"}
        seg["checks"]["route_count"] = {"ok": len(rules) > 300, "value": len(rules)}
        missing = [b for b in CORE_BLUEPRINTS if not any(e.startswith(b + ".") for e in
                   (r.endpoint for r in rules))]
        seg["checks"]["core_blueprints"] = {"ok": not missing,
                                            "value": "all present" if not missing else f"missing {missing}"}
        # 关键新能力端点
        ep = {r.endpoint for r in rules}
        cap = ["data_query.api_metric_trend"]
        miss_cap = [c for c in cap if c not in ep]
        seg["checks"]["capability_endpoints"] = {"ok": not miss_cap,
                                                 "value": "ok" if not miss_cap else f"missing {miss_cap}"}
        seg["blueprints"] = bp_prefixes
        seg["ok"] = all(c["ok"] for c in seg["checks"].values())
    except Exception as e:  # noqa: BLE001
        seg["ok"] = False
        seg["fatal"] = repr(e)
    report["runtime"] = seg
    return seg["ok"]


def check_data(report, do_backup=True):
    seg = {"name": "data", "checks": {}}
    import database as db  # noqa: E402
    path = db.DB_PATH
    seg["db_path"] = path
    if not os.path.exists(path):
        seg["ok"] = False
        seg["fatal"] = "db file missing"
        report["data"] = seg
        return False
    con = sqlite3.connect(path, timeout=30)
    try:
        integ = con.execute("PRAGMA integrity_check").fetchone()[0]
        seg["checks"]["integrity"] = {"ok": integ == "ok", "value": integ}
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        miss_t = [t for t in CORE_TABLES if t not in tables]
        seg["checks"]["core_tables"] = {"ok": not miss_t,
                                        "value": "all present" if not miss_t else f"missing {miss_t}"}
        counts = {}
        for t in CORE_TABLES:
            if t in tables:
                counts[t] = con.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        seg["row_counts"] = counts
        # WAL 模式确认（并发安全）
        journal = con.execute("PRAGMA journal_mode").fetchone()[0]
        seg["checks"]["journal_mode"] = {"ok": journal.lower() in ("wal",), "value": journal}
    finally:
        con.close()

    backup_path = None
    if do_backup:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"monitor-baseline-{ts}.db")
        src = sqlite3.connect(path, timeout=30)
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)  # 在线一致性备份（WAL 安全，不锁生产）
        finally:
            dst.close()
            src.close()
        seg["checks"]["backup"] = {"ok": os.path.exists(backup_path),
                                   "value": _safe_rel(backup_path),
                                   "bytes": os.path.getsize(backup_path)}
    seg["backup_path"] = backup_path
    seg["ok"] = all(c["ok"] for c in seg["checks"].values())
    report["data"] = seg
    return seg["ok"]


def check_tests(report, full=False):
    """Preserve the historical report field without collecting/executing suites."""
    report["tests"] = {
        "name": "tests", "status": "NOT_REQUIRED_BY_PO_POLICY", "ok": None,
        "executed": False, "historical_failures_preserved": True,
        "reason": "PO-20261008-REAL-OUTCOME-POLICY-C1-RESUME",
    }
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="历史参数；现行 PO 策略禁止测试套件执行")
    ap.add_argument("--no-backup", action="store_true", help="跳过 DB 备份")
    args = ap.parse_args()
    if args.full:
        ap.error("--full suite execution is prohibited by current Product Owner policy")

    report = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": "full" if args.full else "fast"}
    results = {
        "git": check_git(report),
        "runtime": check_runtime(report),
        "data": check_data(report, do_backup=not args.no_backup),

    }
    check_tests(report)  # Historical non-required field; never part of PASS calculation.
    # Rollback 信息已在 git 段；Evidence 落盘
    report["overall"] = "PASS" if all(results.values()) else "FAIL"
    report["segment_results"] = results
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    ev_path = os.path.join(EVIDENCE_DIR, f"baseline-{ts}.json")
    with open(ev_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    for k, ok in results.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {k}")
    print(f"[----] evidence: {_safe_rel(ev_path)}")
    rb = report.get("git", {}).get("rollback_candidate")
    if rb:
        print(f"[----] rollback point (HEAD~1): {rb}")
        print("       rollback cmd: git reset --hard HEAD~1  (仅在需要时人工执行)")
    print("=" * 60)
    print(f"OVERALL: {report['overall']}")
    sys.exit(0 if report["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
