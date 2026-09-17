# -*- coding: utf-8 -*-
"""
Zachary OS AI · Z-Brand-Core 驻场浏览器（Resident Browser）统一启动器
================================================================================
按采集 Contract（xhs_cookie_bridge 单一事实源）幂等拉起香港/国际采集与通用浏览
两个物理隔离的 Edge CDP 驻场实例，人工在各自窗口登录一次后 profile 长期复用：

  XHS_RETINAUT    端口 9223  profile edge-cdp-retinaut    rednote.com      继承系统/海外代理
  GENERAL_BROWSE  端口 9224  profile edge-cdp-general     bing.com         直连(平台内置通用浏览)

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

# 通用浏览实例（平台内置浏览器，与采集物理隔离，独立 cookie jar）
GENERAL_BROWSER = {
    "account": "GENERAL_BROWSE",
    "port": 9224,
    "profile": os.path.join(_ROOT, "edge-cdp-general"),
    "home": "https://www.bing.com",
    "direct": True,
}


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
           "online": port_online(port), "direct": direct, "action": "", "pages": []}

    if row["online"]:
        row["action"] = "already_online"
        if not status_only:
            row["action"] += ":" + ensure_platform_tab(port, home)
        row["pages"] = list_page_hosts(port)
        return row

    if status_only:
        row["action"] = "offline"
        return row

    os.makedirs(prof, exist_ok=True)
    res = cdp_helper.start_cdp_browser(
        port=port,
        profile_dir=prof,
        launch_url=home,
        direct_connection=direct,
        browser="edge",
    )
    row["online"] = port_online(port)
    row["action"] = "started" if res.get("success") else f"failed: {res.get('message')}"
    row["pages"] = list_page_hosts(port)
    return row


def launch_general(status_only=False):
    """通用浏览实例（9224）：独立 profile、直连、与采集物理隔离。幂等复用。"""
    g = GENERAL_BROWSER
    row = {"account": g["account"], "port": g["port"], "profile": g["profile"],
           "home": g["home"], "online": port_online(g["port"]),
           "direct": g["direct"], "action": "", "pages": []}
    if row["online"]:
        row["action"] = "already_online"
        row["pages"] = list_page_hosts(g["port"])
        return row
    if status_only:
        row["action"] = "offline"
        return row
    os.makedirs(g["profile"], exist_ok=True)
    res = cdp_helper.start_cdp_browser(
        port=g["port"], profile_dir=g["profile"],
        launch_url=g["home"], direct_connection=g["direct"], browser="edge",
    )
    row["online"] = port_online(g["port"])
    row["action"] = "started" if res.get("success") else f"failed: {res.get('message')}"
    row["pages"] = list_page_hosts(g["port"])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default=None, help="只拉起指定逻辑身份；默认全部")
    ap.add_argument("--status", action="store_true", help="只查看在线状态，不启动")
    args = ap.parse_args()

    plan = [(a, d) for (a, d) in RESIDENT_PLAN if (not args.account or a == args.account)]
    if args.account and args.account != "GENERAL_BROWSE" and not plan:
        print(f"[FATAL] 未知身份 {args.account}；可选：{[a for a,_ in RESIDENT_PLAN] + ['GENERAL_BROWSE']}")
        return 2

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
            print(f"   page    = {u[:80]}")

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
            print(f"   page    = {u[:80]}")

    print("\n" + "-" * 72)
    ok = all(r["online"] for r in rows)
    print("驻场状态：" + ("全部在线 ✔" if ok else "存在未在线实例，请查看上方 action"))
    for r in rows:
        print(f"  {r['account']:16s} 127.0.0.1:{r['port']}  online={r['online']}")
    print("-" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
