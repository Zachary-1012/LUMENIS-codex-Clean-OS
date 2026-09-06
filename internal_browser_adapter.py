# -*- coding: utf-8 -*-
"""P1-D: 内置浏览器 CDP 统一适配器层（Internal Browser Adapter）

定位：
    在不重写采集器核心逻辑的前提下，为 collector.py / xhs_cdp_collector.py /
    collector_automation.py 的 CDP 连接提供统一包装层，使每次导航经过
    browser_surface.evaluate_navigation() 门禁。

架构：
    采集器 → InternalBrowserAdapter.navigate() → evaluate_navigation() 门禁 → CDP 底层执行
                                                          ↓
                                              need_confirmation → 阻塞等待确认
                                              blocked → 直接拒绝

迁移策略（渐进式，不破坏现有采集）：
    - Phase 1（本文件）：创建适配器层，提供与直连 CDP 兼容的 API
    - Phase 2：collector.py 导航点逐步接入 adapter（标注 MIGRATION_STATUS）
    - Phase 3：xhs_cdp_collector.py / collector_automation.py 接入
    - 底层 9222/9223/9224 保持不变，登录态物理隔离不破坏

安全：
    - 所有外部 URL 导航必须先过 evaluate_navigation
    - 危险协议(javascript:/data:/file:) 一律 blocked
    - strict 模式外部域名返回 need_confirmation，不执行导航
    - 内部主机(127.0.0.1/localhost)直接放行
"""
from __future__ import annotations

import json
import time
import urllib.request as _ur
from typing import Optional

import browser_surface as bs
import internal_browser as ib

# CDP 端口定义（与底层执行器一一对应，不改变）
CDP_PORTS = {
    "xhs_primary": 9222,    # 小红书主号（已登录、持久 Edge）
    "xhs_retinaut": 9223,   # 备用号
    "general": 9224,         # 通用浏览（按需拉起）
}

# 迁移进度追踪（MIGRATION_STATUS）
MIGRATION_STATUS = {
    "collector.py": {
        "status": "phase1_adapter_ready",
        "nav_points_total": 3,   # _search_via_cdp / _ensure_cdp_online / 详情页导航
        "nav_points_migrated": 0,
        "note": "适配器层已就绪，采集器导航点待逐步接入",
    },
    "xhs_cdp_collector.py": {
        "status": "phase1_adapter_ready",
        "nav_points_total": 2,   # collect_human / collect_direct 中的页面导航
        "nav_points_migrated": 0,
        "note": "独立子进程，通过 cdp_url 参数接入适配器",
    },
    "collector_automation.py": {
        "status": "phase1_adapter_ready",
        "nav_points_total": 1,
        "nav_points_migrated": 0,
        "note": "自动化流程导航点待接入",
    },
}


def get_migration_status() -> dict:
    """返回采集器 CDP 迁移进度（供健康检查/前端展示）。"""
    total = sum(v["nav_points_total"] for v in MIGRATION_STATUS.values())
    migrated = sum(v["nav_points_migrated"] for v in MIGRATION_STATUS.values())
    return {
        "ok": True,
        "phase": "phase1_adapter_ready",
        "total_nav_points": total,
        "migrated_nav_points": migrated,
        "progress_pct": round(migrated / max(total, 1) * 100, 1),
        "details": MIGRATION_STATUS,
        "cdp_ports": CDP_PORTS,
    }


def _cdp_http(port: int, path: str, method: str = "GET", timeout: float = 3.0):
    """CDP HTTP 端点调用（底层执行，不经过导航门）。"""
    url = f"http://127.0.0.1:{port}{path}"
    req = _ur.Request(url, method=method)
    with _ur.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def is_cdp_online(port: int, timeout: float = 2.0) -> bool:
    """探测指定 CDP 端口是否在线（不经过导航门，纯健康检查）。"""
    try:
        _cdp_http(port, "/json/version", timeout=timeout)
        return True
    except Exception:
        return False


def navigate(url: str, port: int = 9222, target_id: Optional[str] = None,
             confirmed: bool = False, wait_ms: int = 600) -> dict:
    """统一导航入口：先过 evaluate_navigation 门禁，再执行 CDP 导航。

    Args:
        url: 目标 URL
        port: CDP 端口（9222/9223/9224）
        target_id: 指定标签页，None 取当前第一个 page
        confirmed: 前端是否已确认（need_confirmation 时需带 confirmed=true）
        wait_ms: 导航后等待毫秒数

    Returns:
        {ok, status, gate, target_id, error?}
        status ∈ allowed / blocked / need_confirmation / navigated
    """
    # Step 1: 导航门禁
    gate = bs.evaluate_navigation(url)
    status = gate.get("status", "blocked")

    if status == "blocked":
        return {"ok": False, "status": "blocked", "gate": gate,
                "error": gate.get("reason", "导航被拦截")}

    if status == "need_confirmation" and not confirmed:
        return {"ok": False, "status": "need_confirmation", "gate": gate,
                "error": "需用户确认后方可导航（前端弹窗确认后带 confirmed=true 重试）"}

    # need_confirmation + confirmed=True → 放行执行
    # allowed → 直接执行

    # Step 2: 执行 CDP 导航（复用 browser_surface 的底层 CDP 能力）
    try:
        result = bs.navigate_tab(url, target_id=target_id, port=port, wait_ms=wait_ms)
        if result.get("ok"):
            return {"ok": True, "status": "navigated", "gate": gate,
                    "target_id": result.get("target_id"), "cdp_port": port}
        return {"ok": False, "status": "navigate_failed", "gate": gate,
                "error": result.get("error", "CDP 导航失败")}
    except Exception as e:
        return {"ok": False, "status": "navigate_failed", "gate": gate,
                "error": f"CDP 导航异常: {e}"}


def screenshot(port: int = 9222, target_id: Optional[str] = None,
               quality: int = 60) -> dict:
    """对指定 CDP 端口/标签页截图（不经过导航门，只读操作）。"""
    try:
        result = bs._hybrid_screenshot(target_id=target_id, port=port, quality=quality)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_tabs(port: int = 9222) -> dict:
    """列出指定 CDP 端口的标签页（不经过导航门，只读操作）。"""
    return bs.list_targets(port=port, pages_only=True)


def refresh(port: int = 9222, target_id: Optional[str] = None) -> dict:
    """刷新当前标签页（CDP Page.reload，不经过导航门，因为是同页刷新）。"""
    try:
        ws, chosen = bs._find_tab_ws(port, target_id, timeout=5.0)
        try:
            resp = ib._cdp(ws, "Page.reload", {"ignoreCache": False}, msg_id=1, timeout=8.0)
            return {"ok": True, "target_id": chosen["target_id"], "cdp_port": port}
        finally:
            try:
                ws.close()
            except Exception:
                pass
    except Exception as e:
        return {"ok": False, "error": str(e)}


def switch_tab(port: int = 9222, target_id: str = "") -> dict:
    """切换（激活）指定标签页（CDP /json/activate，不经过导航门）。"""
    if not target_id:
        return {"ok": False, "error": "target_id 为空"}
    return bs.activate_tab(target_id, port=port)


def evaluate_js(port: int = 9222, target_id: Optional[str] = None,
                expression: str = "", timeout: float = 8.0) -> dict:
    """在指定标签页执行 JS（仅用于内置固定表达式，不接受外部任意 JS）。"""
    if not expression:
        return {"ok": False, "error": "expression 为空"}
    try:
        ws, chosen = bs._find_tab_ws(port, target_id, timeout=5.0)
        try:
            resp = ib._cdp(ws, "Runtime.evaluate",
                           {"expression": expression, "returnByValue": True, "timeout": 6000},
                           msg_id=1, timeout=timeout)
            val = resp.get("result", {}).get("result", {}).get("value")
            return {"ok": True, "target_id": chosen["target_id"], "value": val}
        finally:
            try:
                ws.close()
            except Exception:
                pass
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─────────────────────────── 采集器兼容层 ───────────────────────────
# 以下函数提供与采集器现有 CDP 调用兼容的接口，便于逐步迁移。

def collector_navigate(url: str, port: int = 9222, **kwargs) -> dict:
    """采集器导航兼容接口：与直连 CDP 行为一致，但经过导航门。

    采集器迁移时，将直接的 CDP Page.navigate 替换为此函数。
    采集器域名（xiaohongshu.com/rednote.com）在 strict 模式下直接放行。
    """
    return navigate(url, port=port, **kwargs)


def collector_get_state(port: int = 9222) -> dict:
    """采集器状态查询兼容接口：返回当前页面 URL/title/在线状态。"""
    tabs = list_tabs(port)
    if not tabs.get("ok") or not tabs.get("tabs"):
        return {"ok": False, "online": False, "cdp_port": port, "error": tabs.get("error", "无可用标签页")}
    first = tabs["tabs"][0]
    return {
        "ok": True,
        "online": True,
        "cdp_port": port,
        "url": first.get("url", ""),
        "title": first.get("title", ""),
        "target_id": first.get("target_id", ""),
        "tab_count": tabs.get("count", 0),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Internal Browser Adapter - P1-D CDP 统一适配层")
    print("=" * 60)
    print()
    print("迁移状态:")
    status = get_migration_status()
    print(f"  进度: {status['migrated_nav_points']}/{status['total_nav_points']} ({status['progress_pct']}%)")
    for name, detail in status["details"].items():
        print(f"  {name}: {detail['status']} ({detail['nav_points_migrated']}/{detail['nav_points_total']})")
    print()
    print("CDP 端口:")
    for name, port in CDP_PORTS.items():
        online = is_cdp_online(port)
        print(f"  {name}: {port} {'在线' if online else '离线'}")
    print()
    print("导航门禁测试:")
    for test_url in [
        "https://www.xiaohongshu.com",
        "https://www.baidu.com",
        "javascript:alert(1)",
        "http://127.0.0.1:8201",
    ]:
        gate = bs.evaluate_navigation(test_url)
        print(f"  {test_url[:50]:50s} → {gate.get('status')}: {gate.get('reason', '')[:40]}")
