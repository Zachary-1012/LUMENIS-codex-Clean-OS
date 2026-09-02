# -*- coding: utf-8 -*-
"""
Zachary OS AI · Z-Brand-Core 双身份驻场浏览器（Resident Browser）统一启动器
================================================================================
按双子星库 Contract（xhs_cookie_bridge 单一事实源）幂等拉起两个物理隔离的
Edge CDP 驻场实例，人工在各自窗口登录一次后 profile 长期复用、长期驻场：

  XHS_CN_PRIMARY  端口 9222  profile edge-cdp-newaccount  xiaohongshu.com  直连(不走系统代理)
  XHS_RETINAUT    端口 9223  profile edge-cdp-retinaut    rednote.com      继承系统/海外代理

采集链只通过 CDP 附着到对应端口，采集结束不关闭驻场窗口。

用法（用项目 .venv 的 python 运行）：
  python scripts/start_resident_browsers.py            # 拉起全部驻场实例并确保平台页打开
  python scripts/start_resident_browsers.py --status   # 只看在线状态，不启动
  python scripts/start_resident_browsers.py --account XHS_RETINAUT   # 只起指定身份
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

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

import xhs_cookie_bridge as bridge
import cdp_helper

# (逻辑身份, 是否强制直连)。大陆主号直连保证国内站稳定；香港 rednote 继承系统/海外代理。
RESIDENT_PLAN = [
    (bridge.XHS_CN_PRIMARY_NAME, True),
    (bridge.XHS_RETINAUT_NAME, False),
]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default=None, help="只拉起指定逻辑身份；默认全部")
    ap.add_argument("--status", action="store_true", help="只查看在线状态，不启动")
    args = ap.parse_args()

    plan = [(a, d) for (a, d) in RESIDENT_PLAN if (not args.account or a == args.account)]
    if args.account and not plan:
        print(f"[FATAL] 未知身份 {args.account}；可选：{[a for a,_ in RESIDENT_PLAN]}")
        return 2

    print("=" * 72)
    print(" Zachary OS AI · Resident Browser 双身份驻场启动器")
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

    print("\n" + "-" * 72)
    ok = all(r["online"] for r in rows)
    print("驻场状态：" + ("全部在线 ✔" if ok else "存在未在线实例，请查看上方 action"))
    for r in rows:
        print(f"  {r['account']:16s} 127.0.0.1:{r['port']}  online={r['online']}")
    print("-" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
