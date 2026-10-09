# -*- coding: utf-8 -*-
"""
LUMENIS SYSTEM Resident Browser launcher
================================================================================
按采集 Contract（xhs_cookie_bridge 单一事实源）幂等拉起香港/国际采集与通用浏览
香港采集与产品内置浏览器分别使用独立 profile：

  XHS_RETINAUT    端口 9223  profile edge-cdp-retinaut    rednote.com      继承系统/海外代理
  GENERAL_BROWSE  端口 9224  系统默认 Chromium 内核，无头运行，使用 browser_surface 的独立 profile

生产采集链只通过 CDP 附着到 9223 香港/国际身份，采集结束不关闭驻场窗口。
9222 内地 profile 保留为诊断/历史凭证隔离资产，但不属于生产驻场计划、不自动启动。
通用浏览实例与采集物理隔离（独立 cookie jar），不混入生产采集身份。

用法（用项目 .venv 的 python 运行）：
  python scripts/start_resident_browsers.py            # 拉起香港采集 + 通用浏览
  python scripts/start_resident_browsers.py --status   # 只看在线状态，不启动
  python scripts/start_resident_browsers.py --account XHS_RETINAUT   # 只起指定身份
  python scripts/start_resident_browsers.py --account GENERAL_BROWSE # 只起通用浏览
"""
import argparse
import io
import json
import os
import sys
import urllib.request
import urllib.parse

# 让脚本在 scripts/ 子目录下也能导入项目根模块
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _load_project_env():
    """Keep the resident child process on the same runtime identity as app.py.

    The production launcher starts this file as a separate Python process, so
    it cannot rely on app.py having already loaded the repository's .env.
    Loading only missing keys preserves explicit service-manager environment
    values while preventing a silent fallback to <repo>/data/monitor.db.
    """
    env_path = os.path.join(_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # Browser availability must not be blocked by an optional local env
        # file; the child will still use explicit process-level settings.
        return


if __name__ == "__main__":
    _load_project_env()

# 仅在脚本作为进程入口时设置 UTF-8 输出；被 pytest/Runtime import 时不得重包
# 宿主输出流，否则会关闭测试捕获器并造成与业务无关的连锁错误。
if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    except Exception:
        pass

import xhs_cookie_bridge as bridge
import cdp_helper

# (逻辑身份, 是否强制直连)。生产仅使用香港/国际 RedNote；内地身份不进入驻场计划。
RESIDENT_PLAN = [
    (bridge.XHS_RETINAUT_NAME, False),
]

def douyin_worker_spec(private_data_dir=None):
    """Return the fixed isolated read-only Douyin worker plan without starting it."""
    from lumenis.adapters.human_browser import readonly_worker_spec
    return readonly_worker_spec("douyin", private_data_dir or bridge.PRIVATE_DATA_DIR)


def x_readonly_worker_spec(private_data_dir=None):
    """Return the fixed, isolated X read-only worker plan without starting it."""
    from lumenis.adapters.human_browser import readonly_worker_spec
    return readonly_worker_spec("x", private_data_dir or bridge.PRIVATE_DATA_DIR)


def _http_json(url, method="GET", timeout=5):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def port_online(port):
    return cdp_helper.is_cdp_port_open(port)


def list_page_hosts(port):
    try:
        targets = _http_json(f"http://127.0.0.1:{port}/json/list")
        return [t.get("url", "") for t in targets if t.get("type") == "page"]
    except Exception:
        return []


def ensure_platform_tab(port, home_url):
    """驻场实例已在线时，若还没有目标平台页则开一个新标签（方便人工登录）；失败不阻断。"""
    host = urllib.parse.urlparse(home_url).netloc
    try:
        pages = list_page_hosts(port)
        if any(host in u for u in pages):
            return "platform_tab_present"
        # Chromium/Edge 新版要求 PUT 打开 /json/new
        try:
            _http_json(f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(home_url, safe='')}",
                       method="PUT", timeout=6)
        except Exception:
            _http_json(f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(home_url, safe='')}",
                       method="GET", timeout=6)
        return "platform_tab_opened"
    except Exception as e:
        return f"platform_tab_skip({type(e).__name__})"


def profile_dir_for(account):
    cookie_path, prof = bridge.ACCOUNT_PROFILES.get(account, (None, None))
    if prof and not os.path.isabs(prof):
        prof = os.path.join(_ROOT, prof)
    return prof


def launch_one(account, direct, status_only=False):
    port = bridge.cdp_port_for(account)
    home = bridge.home_url_for(account)
    prof = profile_dir_for(account)
    row = {"account": account, "port": port, "profile": prof, "home": home,
           "online": False, "direct": direct, "action": "", "pages": [],
           "mode": "BACKGROUND"}

    exact_worker = bool(prof and cdp_helper.is_cdp_profile_running(
        port, prof, headless=True, loopback_only=True, browser="edge"))
    if port_online(port):
        if not exact_worker:
            row["action"] = "port_in_use_unverified"
            return row
        row["online"] = True
        row["action"] = "already_online"
        if not status_only:
            row["action"] += ":" + ensure_platform_tab(port, home)
        row["pages"] = list_page_hosts(port)
        return row

    if status_only:
        row["action"] = "offline"
        return row
    if not prof:
        row["action"] = "profile_unavailable"
        return row

    os.makedirs(prof, exist_ok=True)
    res = cdp_helper.start_cdp_browser(
        port=port,
        profile_dir=prof,
        headless=True,
        loopback_only=True,
        launch_url=home,
        direct_connection=direct,
        browser="edge",
    )
    row["online"] = (res.get("success") is True
                      and cdp_helper.is_cdp_profile_running(
                          port, prof, headless=True, loopback_only=True, browser="edge"))
    row["action"] = "started" if row["online"] else f"failed: {res.get('message')}"
    if row["online"]:
        row["pages"] = list_page_hosts(port)
    return row
def launch_general(status_only=False):
    """Reuse the product browser owner for startup and verified status."""
    import browser_surface

    browser = cdp_helper.system_default_cdp_browser()
    row = {"account": "GENERAL_BROWSE", "port": browser_surface.GENERAL_CDP_PORT,
           "profile": browser_surface._general_profile_dir(browser)
           if browser in {"chrome", "edge"} else None,
           "home": browser_surface.GENERAL_HOME_URL, "browser": browser,
           "online": False, "direct": False, "action": "", "pages": []}
    if status_only:
        row["online"] = browser_surface.general_browser_online()
        row["action"] = "already_online" if row["online"] else "offline_or_unverified"
        if row["online"]:
            row["pages"] = list_page_hosts(row["port"])
        return row
    res = browser_surface.ensure_general_browser()
    row["online"] = res.get("ok") is True and res.get("online") is True
    row["action"] = res.get("action") if row["online"] else f"failed: {res.get('code') or res.get('error') or 'BROWSER_UNAVAILABLE'}"
    if row["online"]:
        row["pages"] = list_page_hosts(row["port"])
    return row


def launch_douyin_readonly(status_only=False):
    """Provision Douyin only through explicit --account; never reuse an unknown port owner."""
    return _launch_readonly_worker(douyin_worker_spec(), status_only=status_only)


def _launch_readonly_worker(worker, *, status_only=False, mode="BACKGROUND",
                            task_id=None, platform=None, browser=None,
                            actor_ref=None):
    """Provision or reuse the exact registered profile in an explicit mode."""
    mode = str(mode or "BACKGROUND").upper()
    if mode not in {"BACKGROUND", "HUMAN_INTERACTIVE"}:
        raise ValueError("BROWSER_MODE_INVALID")
    if mode == "HUMAN_INTERACTIVE":
        from lumenis.adapters.human_browser import _authorize_human_interactive
        task_platform = _authorize_human_interactive(
            platform or worker["account"], task_id or "", actor_ref)
        from lumenis.adapters import collector_service
        if not collector_service.human_browser_lease_owned(task_id or "", task_platform):
            raise PermissionError("HUMAN_INTERACTIVE_BROWSER_LEASE_REQUIRED")
    port_open = port_online(worker["port"])
    headless = mode == "BACKGROUND"
    browser = (cdp_helper.registered_cdp_browser_for_port(
        worker["port"], worker["profile"], headless=headless)
        if port_open else (browser or cdp_helper.system_default_cdp_browser()))
    row = {**worker, "browser": browser, "online": False,
           "port_open": port_open, "action": "", "pages": [], "mode": mode}
    if port_open:
        if browser and cdp_helper.is_cdp_profile_running(
                worker["port"], worker["profile"], headless=headless,
                loopback_only=True, browser=browser):
            row["online"] = True
            row["action"] = "already_online"
        else:
            row["action"] = "port_in_use_unverified"
        return row
    if browser not in {"chrome", "edge"}:
        row["action"] = "unsupported_system_default_browser"
        return row
    if status_only:
        row["action"] = "offline"
        return row

    os.makedirs(worker["profile"], exist_ok=True)
    res = cdp_helper.start_cdp_browser(
        port=worker["port"],
        profile_dir=worker["profile"],
        headless=headless,
        launch_url=worker["home"],
        direct_connection=worker["direct"],
        browser=browser,
        loopback_only=True,
    )
    row["online"] = (res.get("success") is True
                     and cdp_helper.is_cdp_profile_running(
                         worker["port"], worker["profile"], headless=headless,
                         loopback_only=True, browser=browser))
    row["action"] = "started" if row["online"] else f"failed: {res.get('message')}"
    return row

def launch_x_readonly(status_only=False):
    """Provision X only through explicit --account; reject unknown port owners."""
    return _launch_readonly_worker(x_readonly_worker_spec(), status_only=status_only)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default=None, help="只拉起指定逻辑身份；默认全部")
    ap.add_argument("--status", action="store_true", help="只查看在线状态，不启动")
    ap.add_argument("--open-login", action="store_true", help="在指定只读 Worker 打开人工登录页")
    ap.add_argument("--task-id", default=None, help="HUMAN_INTERACTIVE 操作的现有任务身份")
    args = ap.parse_args()

    if args.open_login:
        from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES
        from lumenis.adapters.human_browser import readonly_worker_spec, open_readonly_worker_login
        selected = next((platform for platform, config in PLATFORM_CAPABILITIES.items()
                         if config.get("readonly_worker", {}).get("account") == args.account), None)
        if args.status or selected not in {"instagram", "facebook", "douyin", "x"} or not args.task_id:
            ap.error("--open-login requires a registered account and --task-id")
        row = _launch_readonly_worker(
            readonly_worker_spec(selected), mode="HUMAN_INTERACTIVE",
            task_id=args.task_id, platform=selected)
        if not row["online"]:
            print(json.dumps({"account": args.account, "status": "WORKER_UNAVAILABLE",
                              "reason": row["action"]}, ensure_ascii=False))
            return 1
        print(json.dumps(open_readonly_worker_login(selected, task_id=args.task_id), ensure_ascii=False))
        return 0

    plan = [(a, d) for (a, d) in RESIDENT_PLAN if (not args.account or a == args.account)]
    if args.account == "DOUYIN_READONLY":
        row = launch_douyin_readonly(status_only=args.status)
        print(f"\n● {row['account']}（显式请求的只读抖音驻场实例）")
        print(f"   port={row['port']}  online={row['online']}  browser={row['browser']}")
        print(f"   profile = {row['profile']}")
        print(f"   home    = {row['home']}")
        print(f"   action  = {row['action']}")
        return 0 if row["online"] else 1

    if args.account == "X_READONLY":
        row = launch_x_readonly(status_only=args.status)
        print(f"\n● {row['account']}（显式请求的只读 X 驻场实例）")
        print(f"   port={row['port']}  online={row['online']}  browser={row['browser']}")
        print(f"   profile = {row['profile']}")
        print(f"   home    = {row['home']}")
        print(f"   action  = {row['action']}")
        return 0 if row["online"] else 1

    if args.account and args.account != "GENERAL_BROWSE" and not plan:
        from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES
        from lumenis.adapters.human_browser import readonly_worker_spec
        selected = next((platform for platform, config in PLATFORM_CAPABILITIES.items()
                         if config.get("readonly_worker", {}).get("account") == args.account), None)
        if selected is None:
            print("[FATAL] 未注册的只读浏览器身份")
            return 2
        row = _launch_readonly_worker(readonly_worker_spec(selected), status_only=args.status)
        print(json.dumps({key: row[key] for key in ("account", "port", "online", "action")}, ensure_ascii=False))
        return 0 if row["online"] else 1

    print("=" * 72)
    print(" 序境 LUMENIS · Resident Browser 驻场启动器（香港采集 + 通用浏览）")
    print("=" * 72)
    rows = []
    for account, direct in plan:
        row = launch_one(account, direct, status_only=args.status)
        rows.append(row)
        mode = "直连" if direct else "继承系统代理"
        print(f"\n● {account}")
        print(f"   port={row['port']}  online={row['online']}  网络={mode}")
        print(f"   profile = {row['profile']}")
        print(f"   home    = {row['home']}")
        print(f"   action  = {row['action']}")
        for u in row["pages"][:4]:
            parts = urllib.parse.urlsplit(u)
            print(f"   page    = {parts.scheme}://{parts.hostname or ''}/ [path/query withheld]")

    # 通用浏览实例（默认全部启动，或 --account GENERAL_BROWSE 单独启动）
    if not args.account or args.account == "GENERAL_BROWSE":
        row = launch_general(status_only=args.status)
        rows.append(row)
        mode = "直连" if row["direct"] else "继承系统代理"
        print(f"\n● {row['account']}（平台内置通用浏览）")
        print(f"   port={row['port']}  online={row['online']}  网络={mode}")
        print(f"   profile = {row['profile']}")
        print(f"   home    = {row['home']}")
        print(f"   action  = {row['action']}")
        for u in row["pages"][:4]:
            parts = urllib.parse.urlsplit(u)
            print(f"   page    = {parts.scheme}://{parts.hostname or ''}/ [path/query withheld]")

    print("\n" + "-" * 72)
    ok = all(r["online"] for r in rows)
    print("驻场状态：" + ("全部在线 ✔" if ok else "存在未在线实例，请查看上方 action"))
    for r in rows:
        print(f"  {r['account']:16s} 127.0.0.1:{r['port']}  online={r['online']}")
    print("-" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
