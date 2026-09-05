# -*- coding: utf-8 -*-
"""闭环 Runtime E2E：启动真实 app.py，验证关键 API 存活后停止。"""
import base64
from core.repository_registry import get_repo_root, get_db_path, get_osai_root
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = get_repo_root()
PORT = 8327
BASE = "http://127.0.0.1:%d" % PORT
AUTH = "Basic " + base64.b64encode(b"zbc_e2e:e2e_test_only_2026").decode()

env = dict(os.environ)
env["ZBC_DB_PATH"] = os.path.join(ROOT, "staging", "e2e_loop.db")
env["ZBC_GUARDIAN_ENABLED"] = "0"
env["TAIKOO_AUTH_USER"] = "zbc_e2e"
env["TAIKOO_AUTH_PASSWORD"] = "e2e_test_only_2026"
env["PYTHONIOENCODING"] = "utf-8"

proc = subprocess.Popen(
    [sys.executable, "app.py", "--port", str(PORT), "--host", "127.0.0.1"],
    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def req(path):
    r = urllib.request.Request(BASE + path, headers={"Authorization": AUTH})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}


def main():
    # 等待启动
    alive = False
    for _ in range(40):
        try:
            req("/api/auth/config")
            alive = True
            break
        except Exception:
            time.sleep(1)
    if not alive:
        print("E2E FAIL: app 未启动")
        return 1

    checks = [
        ("/api/auth/config", lambda d: "auth_enabled" in d, False),
        ("/api/stats", lambda d: isinstance(d, dict), False),
        ("/api/ai/status", lambda d: isinstance(d, dict), False),
        ("/api/event-graph/stats", lambda d: isinstance(d, dict), False),
        ("/api/event-graph/events?limit=3", lambda d: isinstance(d, dict) and "events" in d, False),
        # metric-trend 参数门：空库无实体 -> 400 且 error 含 entity_type 即路由+参数校验正常
        ("/api/metric-trend", lambda d: isinstance(d, dict) and "entity_type" in d.get("error", ""), True),
        ("/api/resource-guard", lambda d: isinstance(d, dict), False),
    ]
    failed = []
    for path, pred, expect_400 in checks:
        try:
            st, data = req(path)
            ok = (st == 200 or (expect_400 and st == 400)) and pred(data)
            print("  [%s] %s" % ("OK " if ok else "FAIL", path))
            if not ok:
                failed.append(path)
        except Exception as e:
            print("  [FAIL] %s (%s)" % (path, e))
            failed.append(path)

    print("E2E_RESULT=%s" % ("PASS" if not failed else "FAIL:" + ",".join(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    sys.exit(rc)
