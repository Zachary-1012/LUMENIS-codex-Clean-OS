# -*- coding: utf-8 -*-
"""Zachary OS AI · Resident Browser Health Monitor（驻场浏览器运行时健康监控）

双身份独立健康检查 + 自动恢复 + 状态持久化。三层探测：
  L1 端口存活  — socket 连接 CDP 调试端口（0.5s）
  L2 CDP 连通  — HTTP /json/version + WebSocket ping/pong（标杆：cdp-connect-kit endpoint uptime）
  L3 登录态有效 — CDP Network.getAllCookies 检查 web_session+id_token 存在 + 当前页 URL 非登录重定向

状态分级：
  HEALTHY        三层全通过
  NEEDS_LOGIN    端口+CDP 正常但登录态失效（需人工扫码，不自动恢复）
  CDP_DEGRADED   端口通但 CDP HTTP/WS 异常（尝试重连，不行则重启）
  DOWN           端口不通（自动调用统一驻场启动器拉起）

标杆参考：llm-browser-agent(24/7常驻CDP)、chrome-cdp-manager(autoReconnect退避)、
pagerunner(profile持久化Daemon)、better-agent-browser(heartbeat+crash restart+orphan reclaim)、
cdp-connect-kit(endpoint uptime健康指标)、harness-browser(per-profile user-data-dir)。

Contract：仅读取 xhs_cookie_bridge 的身份/端口/profile 单一事实源，不重复定义；
恢复动作委托 scripts/start_resident_browsers.py（幂等），不自行拼浏览器启动参数。
"""
from __future__ import annotations
import json, os, socket, subprocess, threading, time, urllib.request as ur
from datetime import datetime
from typing import Any

import xhs_cookie_bridge as bridge

ROOT = os.path.dirname(os.path.abspath(__file__))
HEALTH_FILE = os.path.join(ROOT, "data", "resident_health.json")
RESIDENT_LAUNCHER = os.path.join(ROOT, "scripts", "start_resident_browsers.py")
VENV_PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")

# 自动恢复上限：同一身份连续恢复超过此次数后标记 UNRECOVERABLE，避免崩溃循环
MAX_AUTO_RECOVERIES = 3
# 恢复后等待浏览器就绪的宽限（秒）
RECOVER_GRACE_SEC = 8

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _check_port(port: int, timeout: float = 0.5) -> bool:
    """L1：TCP 端口存活探测。"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False


def _check_cdp_http(port: int, timeout: float = 1.5) -> dict[str, Any] | None:
    """L2a：CDP HTTP /json/version 探测，返回 version 信息或 None。"""
    try:
        with ur.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _check_cdp_ws(port: int, timeout: float = 2.0) -> bool:
    """L2b：CDP WebSocket 连接 + Browser.getVersion ping，验证控制面可用。"""
    try:
        import websocket
        ver = _check_cdp_http(port, timeout=1.0)
        if not ver or "webSocketDebuggerUrl" not in ver:
            return False
        ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=timeout)
        ws.send(json.dumps({"id": 1, "method": "Browser.getVersion"}))
        resp = json.loads(ws.recv())
        ws.close()
        return resp.get("id") == 1 and "result" in resp
    except Exception:
        return False


def _cdp_get_cookies(port: int, timeout: float = 3.0) -> list[dict]:
    """L3：通过 CDP Browser-level WebSocket 调用 Network.getAllCookies，返回 cookie 列表（不打印值）。"""
    try:
        import websocket
        ver = _check_cdp_http(port, timeout=1.0)
        if not ver:
            return []
        ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=timeout)
        ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        resp = json.loads(ws.recv())
        ws.close()
        return resp.get("result", {}).get("cookies", [])
    except Exception:
        return []


def _cdp_page_urls(port: int, timeout: float = 2.0) -> list[str]:
    """L3：通过 CDP HTTP /json/list 获取所有 page target 的当前 URL。"""
    try:
        with ur.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=timeout) as r:
            targets = json.loads(r.read().decode("utf-8", "replace"))
        return [t.get("url", "") for t in targets if t.get("type") == "page"]
    except Exception:
        return []


def _login_keywords(account: str) -> tuple[str, ...]:
    """该身份平台的登录页/未登录重定向 URL 关键词（用于判断是否被踢到登录页）。"""
    if account == bridge.XHS_RETINAUT_NAME:
        return ("login", "signin", "register", "/explore?source=404")
    return ("login", "signin", "register", "/explore?source=404")


def check_account(account: str) -> dict[str, Any]:
    """对单个逻辑身份执行三层健康检查，返回结构化结果（不含 cookie 值）。"""
    port = bridge.cdp_port_for(account)
    home = bridge.home_url_for(account)
    result: dict[str, Any] = {
        "account": account,
        "cdp_port": port,
        "home_url": home,
        "checked_at": _now_iso(),
        "port_alive": False,
        "cdp_http_ok": False,
        "cdp_ws_ok": False,
        "login_state": "unknown",
        "has_web_session": False,
        "has_id_token": False,
        "cookie_count": 0,
        "page_urls": [],
        "status": "DOWN",
        "detail": "",
    }

    # L1 端口
    result["port_alive"] = _check_port(port)
    if not result["port_alive"]:
        result["status"] = "DOWN"
        result["detail"] = f"CDP 端口 {port} 不可达"
        return result

    # L2 CDP HTTP + WS
    ver = _check_cdp_http(port)
    result["cdp_http_ok"] = ver is not None
    if ver:
        result["browser_version"] = ver.get("Browser", "")
    result["cdp_ws_ok"] = _check_cdp_ws(port)
    if not result["cdp_http_ok"] or not result["cdp_ws_ok"]:
        result["status"] = "CDP_DEGRADED"
        result["detail"] = f"端口通但 CDP 控制面异常(http={result['cdp_http_ok']},ws={result['cdp_ws_ok']})"
        return result

    # L3 登录态
    cookies = _cdp_get_cookies(port)
    result["cookie_count"] = len(cookies)
    cookie_names = {c.get("name", "") for c in cookies}
    result["has_web_session"] = "web_session" in cookie_names
    result["has_id_token"] = "id_token" in cookie_names
    result["page_urls"] = _cdp_page_urls(port)[:5]

    login_redirect = any(
        any(kw in (u or "").lower() for kw in _login_keywords(account))
        for u in result["page_urls"]
    )

    if result["has_web_session"] and result["has_id_token"] and not login_redirect:
        result["status"] = "HEALTHY"
        result["login_state"] = "logged_in"
        result["detail"] = "驻场在线且登录态有效"
    elif not result["has_web_session"] or not result["has_id_token"]:
        result["status"] = "NEEDS_LOGIN"
        result["login_state"] = "logged_out"
        missing = []
        if not result["has_web_session"]:
            missing.append("web_session")
        if not result["has_id_token"]:
            missing.append("id_token")
        result["detail"] = f"驻场在线但登录态失效，缺：{','.join(missing)}；需人工扫码登录"
    else:
        result["status"] = "NEEDS_LOGIN"
        result["login_state"] = "login_redirect"
        result["detail"] = "驻场在线但页面被重定向到登录页，需人工扫码登录"

    return result


def check_all() -> dict[str, Any]:
    """检查所有双身份，返回汇总结果。"""
    accounts = [bridge.XHS_CN_PRIMARY_NAME, bridge.XHS_RETINAUT_NAME]
    results = {a: check_account(a) for a in accounts}
    summary = {
        "checked_at": _now_iso(),
        "total": len(accounts),
        "healthy": sum(1 for r in results.values() if r["status"] == "HEALTHY"),
        "needs_login": sum(1 for r in results.values() if r["status"] == "NEEDS_LOGIN"),
        "degraded": sum(1 for r in results.values() if r["status"] == "CDP_DEGRADED"),
        "down": sum(1 for r in results.values() if r["status"] == "DOWN"),
        "accounts": results,
    }
    _persist(summary)
    return summary


def recover_account(account: str, force: bool = False) -> dict[str, Any]:
    """自动恢复单个身份：DOWN/CDP_DEGRADED 时调用统一驻场启动器拉起；NEEDS_LOGIN 不自动恢复。

    返回恢复结果。连续恢复超过 MAX_AUTO_RECOVERIES 次后标记 UNRECOVERABLE。
    """
    with _lock:
        state = _load_state()
        rec = state.setdefault("recoveries", {}).setdefault(account, {"count": 0, "last_at": None, "last_result": None})

        # 先检查当前状态
        current = check_account(account)
        if current["status"] == "HEALTHY" and not force:
            return {"account": account, "action": "noop", "reason": "already HEALTHY", "current": current}
        if current["status"] == "NEEDS_LOGIN" and not force:
            return {"account": account, "action": "noop", "reason": "NEEDS_LOGIN 需人工扫码，不自动恢复", "current": current}

        if rec["count"] >= MAX_AUTO_RECOVERIES and not force:
            return {"account": account, "action": "blocked", "reason": f"连续恢复已达上限 {MAX_AUTO_RECOVERIES}，标记 UNRECOVERABLE 需人工介入", "current": current}

        # 调用统一驻场启动器（幂等）
        try:
            proc = subprocess.run(
                [VENV_PY, RESIDENT_LAUNCHER, "--account", account],
                capture_output=True, text=True, timeout=30, cwd=ROOT,
            )
            ok = proc.returncode == 0
            rec["count"] += 1
            rec["last_at"] = _now_iso()
            rec["last_result"] = {"returncode": proc.returncode, "stdout_tail": proc.stdout[-300:], "stderr_tail": proc.stderr[-200:]}
            _persist_state(state)

            if ok:
                time.sleep(RECOVER_GRACE_SEC)
                after = check_account(account)
                if after["status"] == "HEALTHY":
                    rec["count"] = 0  # 恢复成功，重置计数
                    _persist_state(state)
                return {"account": account, "action": "recovered", "launcher_ok": True, "after": after}
            return {"account": account, "action": "recover_failed", "launcher_ok": False, "stderr": proc.stderr[-300:], "current": current}
        except subprocess.TimeoutExpired:
            rec["count"] += 1
            rec["last_at"] = _now_iso()
            rec["last_result"] = {"error": "timeout"}
            _persist_state(state)
            return {"account": account, "action": "recover_timeout", "current": current}
        except Exception as e:
            return {"account": account, "action": "recover_error", "error": f"{type(e).__name__}: {e}", "current": current}


def recover_all(force: bool = False) -> dict[str, Any]:
    """恢复所有非 HEALTHY 身份。"""
    accounts = [bridge.XHS_CN_PRIMARY_NAME, bridge.XHS_RETINAUT_NAME]
    return {a: recover_account(a, force=force) for a in accounts}


def _load_state() -> dict:
    try:
        if os.path.exists(HEALTH_FILE):
            with open(HEALTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _persist_state(state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _persist(summary: dict) -> None:
    """把 check_all 结果合并写入状态文件（保留 recoveries 历史）。"""
    state = _load_state()
    state["last_check"] = summary
    state["last_check_at"] = summary.get("checked_at")
    _persist_state(state)


def status(use_cache: bool = False) -> dict[str, Any]:
    """查询健康状态。use_cache=True 时只读上次持久化结果，不实时探测。"""
    if use_cache:
        state = _load_state()
        return state.get("last_check", {"error": "no cached health data, run check_all first"})
    return check_all()


# ── CLI 入口：python resident_health.py [--check] [--recover] [--account X] [--json] ──
if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    do_recover = "--recover" in args
    do_check = "--check" in args or not do_recover
    account = None
    if "--account" in args:
        idx = args.index("--account")
        if idx + 1 < len(args):
            account = args[idx + 1]
    as_json = "--json" in args

    if do_check:
        if account:
            out = check_account(account)
        else:
            out = check_all()
        if as_json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            if "accounts" in out:
                print(f"=== Resident Health @ {out['checked_at']} ===")
                print(f"  healthy={out['healthy']} needs_login={out['needs_login']} degraded={out['degraded']} down={out['down']}")
                for a, r in out["accounts"].items():
                    print(f"  [{r['status']:14s}] {a:16s} port={r['cdp_port']} ws={r['cdp_ws_ok']} login={r['login_state']} cookies={r['cookie_count']} :: {r['detail']}")
            else:
                print(f"  [{out['status']:14s}] {out['account']} port={out['cdp_port']} ws={out['cdp_ws_ok']} login={out['login_state']} cookies={out['cookie_count']} :: {out['detail']}")

    if do_recover:
        if account:
            res = recover_account(account)
        else:
            res = recover_all()
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
