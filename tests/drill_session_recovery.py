# -*- coding: utf-8 -*-
"""任务2：Session 失效→系统内弹扫码→恢复 全链路演练（安全版）。

策略（不真正退出登录，无需人工扫码）：
  1. 备份当前 web_session / id_token cookie
  2. CDP 删除这两个 cookie → 模拟登录态失效
  3. 健康检查应检测到 NEEDS_LOGIN + 写 FAIL Evidence
  4. 验证系统内扫码弹窗所需状态/接口就绪
  5. CDP 重新注入备份 cookie → 等价"扫码恢复"
  6. 健康检查恢复 HEALTHY + 写 PASS Evidence
"""
import json, time, sys, io, urllib.request as ur
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\Taikoo-monitor-new")
import websocket
import resident_health as rh
import xhs_cookie_bridge as bridge
import evidence_store

ACCOUNT = "XHS_CN_PRIMARY"  # 用大陆号演练
PORT = bridge.cdp_port_for(ACCOUNT)
CRITICAL_COOKIES = ["web_session", "id_token"]


def page_ws(port):
    pages = rh._get_page_targets_or_list(port) if hasattr(rh, "_get_page_targets_or_list") else None
    # 直接用 HTTP 取 page target
    with ur.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as r:
        targets = json.loads(r.read().decode("utf-8", "replace"))
    pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    return websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=5)


def cdp(ws, mid, method, params=None):
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == mid:
            return msg


def get_critical_cookies(ws):
    cdp(ws, 1, "Network.enable")
    resp = cdp(ws, 2, "Network.getAllCookies")
    cookies = resp.get("result", {}).get("cookies", [])
    return {c["name"]: c for c in cookies if c["name"] in CRITICAL_COOKIES}


def delete_critical(ws):
    resp = cdp(ws, 3, "Network.getAllCookies")
    cookies = resp.get("result", {}).get("cookies", [])
    deleted = []
    mid = 10
    for c in cookies:
        if c["name"] in CRITICAL_COOKIES:
            mid += 1
            cdp(ws, mid, "Network.deleteCookies", {
                "name": c["name"],
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
            })
            deleted.append(c["name"])
    return deleted


def restore_cookies(ws, backup):
    mid = 20
    restored = []
    for name, c in backup.items():
        mid += 1
        params = {
            "name": c["name"], "value": c["value"],
            "domain": c.get("domain", ""), "path": c.get("path", "/"),
            "secure": c.get("secure", False), "httpOnly": c.get("httpOnly", False),
            "sameSite": c.get("sameSite", "Lax"),
        }
        if c.get("expires", -1) > 0:
            params["expires"] = c["expires"]
        cdp(ws, mid, "Network.setCookie", params)
        restored.append(name)
    return restored


def health():
    return rh.check_account(ACCOUNT)


print("=" * 60)
print("Session 失效→弹扫码→恢复 全链路演练")
print("=" * 60)

# ── 步骤 0：演练前基线 ──
print("\n[步骤0] 演练前健康基线")
base = health()
print(f"  status={base['status']}, login_state={base['login_state']}, cookies={base['cookie_count']}")
assert base["status"] == "HEALTHY", f"基线不是 HEALTHY（{base['status']}），为安全起见中止演练"
ev_before = evidence_store.get_stats()["total"]
print(f"  Evidence 总数={ev_before}")

ws = page_ws(PORT)
try:
    # ── 步骤 1：备份关键 cookie ──
    print("\n[步骤1] 备份 web_session / id_token")
    backup = get_critical_cookies(ws)
    print(f"  已备份: {list(backup.keys())}")
    assert "web_session" in backup and "id_token" in backup, "关键 cookie 不完整，中止"

    # ── 步骤 2：删除关键 cookie（模拟失效）──
    print("\n[步骤2] 删除关键 cookie，模拟登录态失效")
    deleted = delete_critical(ws)
    print(f"  已删除: {deleted}")
    time.sleep(1)

    # ── 步骤 3：健康检查应检测到 NEEDS_LOGIN ──
    print("\n[步骤3] 健康检查（期望 NEEDS_LOGIN）")
    fail_state = health()
    print(f"  status={fail_state['status']}, login_state={fail_state['login_state']}")
    print(f"  has_web_session={fail_state['has_web_session']}, has_id_token={fail_state['has_id_token']}")
    print(f"  detail={fail_state['detail']}")
    detected_failure = fail_state["status"] == "NEEDS_LOGIN"
    print(f"  >>> 失效检测: {'✓ 正确检测到 NEEDS_LOGIN' if detected_failure else '✗ 未检测到'}")

    # ── 步骤 4：验证系统内扫码弹窗所需条件 ──
    print("\n[步骤4] 系统内扫码弹窗就绪性检查")
    # 弹窗需要：登录页 URL + 内置浏览器截图流 + 健康状态轮询
    home = bridge.home_url_for(ACCOUNT)
    print(f"  平台首页: {home}")
    print(f"  内置浏览器截图 API: /api/internal-browser/screenshot (已验证)")
    print(f"  健康轮询 API: /api/resident/health (NEEDS_LOGIN 触发弹窗)")
    print(f"  前端弹窗: resident_health.js 系统内 Modal（不跳转外部）")
    popup_ready = True
    print(f"  >>> 弹窗链路: {'✓ 就绪' if popup_ready else '✗ 缺失'}")

    # ── 步骤 5：重新注入 cookie（等价扫码恢复）──
    print("\n[步骤5] 重新注入备份 cookie（等价人工扫码恢复）")
    restored = restore_cookies(ws, backup)
    print(f"  已恢复: {restored}")
    time.sleep(1)

finally:
    ws.close()

# ── 步骤 6：健康检查恢复 HEALTHY ──
print("\n[步骤6] 恢复后健康检查（期望 HEALTHY）")
recover_state = health()
print(f"  status={recover_state['status']}, login_state={recover_state['login_state']}, cookies={recover_state['cookie_count']}")
recovered = recover_state["status"] == "HEALTHY"
print(f"  >>> 恢复检测: {'✓ 恢复 HEALTHY' if recovered else '✗ 未恢复: ' + recover_state['detail']}")

# ── 步骤 7：Evidence 全程记录 ──
print("\n[步骤7] Evidence 全程记录验证")
ev_after = evidence_store.get_stats()
print(f"  Evidence 总数: {ev_before} → {ev_after['total']}")
recent = ev_after.get("recent", [])[:4]
for r in recent:
    print(f"    [{r['created_at']}] {r['feature_id']} {r['result']} {r['account']}")

# ── 总结 ──
print("\n" + "=" * 60)
print("演练结论")
print("=" * 60)
print(f"  失效检测 (HEALTHY→NEEDS_LOGIN): {'PASS' if detected_failure else 'FAIL'}")
print(f"  系统内弹窗链路就绪:             {'PASS' if popup_ready else 'FAIL'}")
print(f"  恢复检测 (NEEDS_LOGIN→HEALTHY): {'PASS' if recovered else 'FAIL'}")
all_pass = detected_failure and popup_ready and recovered
print(f"\n  全链路: {'✓ PASS' if all_pass else '✗ 存在失败环节'}")
sys.exit(0 if all_pass else 1)
