# -*- coding: utf-8 -*-
"""
XHS 采集旁路桥接层（browser_runtime ↔ xhs_cdp_collector）

【施工标准】先旁路、再切换；默认关闭；未完成真实验证不得标记完成。

本模块是 browser_runtime 接入生产采集链的旁路验证层：
- 使用 PlaywrightAdapter(cdp_url=...) 连接到已运行的 CDP 浏览器
- 复用 xhs_cdp_collector 的人类行为函数（human_search_keyword/scroll_human/...）
- 不修改 xhs_cdp_collector.py，不改变生产采集链
- 通过 Feature Gate 控制（ZBC_BROWSER_RUNTIME_XHS=1 才启用）
- 仅用于旁路验证，生产采集仍走 xhs_cdp_collector.collect_human/collect_direct

接入路径：
browser_runtime.PlaywrightAdapter(cdp_url)
    ↓ 获取 page
xhs_cdp_collector 人类行为函数(page, ...)
    ↓
采集结果（旁路验证用，不入库）
"""
from __future__ import annotations

import os
import time
from typing import Any

# Feature Gate：默认关闭，需显式启用
FEATURE_GATE_ENV = "ZBC_BROWSER_RUNTIME_XHS"


def is_enabled() -> bool:
    """Feature Gate：默认关闭，需 ZBC_BROWSER_RUNTIME_XHS=1 才启用。"""
    return os.environ.get(FEATURE_GATE_ENV, "").strip() == "1"


def _resolve_hk_endpoint(cdp_url: str | None = None) -> tuple[str, str]:
    """Resolve an exact registered HK/International worker; caller URLs are claims only."""
    try:
        import collector
        return collector._resolve_server_cdp_url(
            cdp_url, account="XHS_RETINAUT", region="intl")
    except Exception:  # noqa: BLE001 - SYSTEM owner lookup failure must never use a fallback endpoint.
        return "", "COLLECTOR_WORKER_OWNER_UNAVAILABLE"


def probe_xhs_page(cdp_url: str | None = None,
                    timeout_ms: int = 15000) -> dict[str, Any]:
    """
    旁路探针：使用 browser_runtime.PlaywrightAdapter 连接 CDP，验证小红书页面可访问。

    这是接入生产采集链的第一步验证：确认 PlaywrightAdapter 能正确连接到
    生产采集链使用的 CDP 浏览器，并能操作页面。

    Returns:
        {
            "enabled": bool,           # Feature Gate 状态
            "cdp_connected": bool,     # 是否成功连接 CDP
            "page_url": str,           # 当前页面 URL
            "page_title": str,         # 当前页面标题
            "navigate_ok": bool,       # 导航到小红书是否成功
            "xhs_reachable": bool,     # 小红书页面是否可访问
            "error": str | None,       # 错误信息
            "duration_ms": int,        # 耗时
        }
    """
    result: dict[str, Any] = {
        "enabled": is_enabled(),
        "cdp_connected": False,
        "page_url": "",
        "page_title": "",
        "navigate_ok": False,
        "xhs_reachable": False,
        "error": None,
        "duration_ms": 0,
    }
    if not result["enabled"]:
        result["error"] = f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用"
        return result
    cdp_url, endpoint_error = _resolve_hk_endpoint(cdp_url)
    if endpoint_error:
        result["error"] = endpoint_error
        result["status"] = "UNAVAILABLE"
        return result

    start = time.time()
    adapter = None
    try:
        from lumenis.system.browser.runtime.adapters.playwright_adapter import PlaywrightAdapter
        adapter = PlaywrightAdapter(cdp_url=cdp_url, timeout_ms=timeout_ms)
        health = adapter.health()
        result["cdp_connected"] = health.get("cdp_connected", False)
        result["page_url"] = health.get("url", "")
        result["page_title"] = health.get("title", "")

        if not result["cdp_connected"]:
            result["error"] = f"CDP 连接失败: {health.get('error', 'unknown')}"
            return result

        # 导航到小红书 explore 页
        nav = adapter.navigate("https://www.rednote.com/explore")
        result["navigate_ok"] = nav.get("ok", False)
        result["page_url"] = nav.get("url", result["page_url"])

        # 验证页面可访问（URL 包含 xiaohongshu）
        result["xhs_reachable"] = "rednote.com" in result["page_url"]

        # 复用 xhs_cdp_collector 的人类行为：滚动一次（验证 page 对象兼容）
        try:
            import xhs_cdp_collector as xhs
            page = adapter._page  # 内部访问，旁路验证用
            xhs.scroll_human(page, total_px=600, rounds=1)
            result["human_scroll_ok"] = True
        except Exception as e:
            result["human_scroll_ok"] = False
            result["human_scroll_error"] = str(e)[:200]

    except Exception as e:
        result["error"] = str(e)[:300]
    finally:
        if adapter is not None:
            try:
                adapter.close()
            except Exception:
                pass
        result["duration_ms"] = int((time.time() - start) * 1000)

    return result


def collect_keyword_bypass(keyword: str,
                            cdp_url: str | None = None,
                            max_scroll: int = 2,
                            max_details: int = 3,
                            timeout_ms: int = 20000) -> dict[str, Any]:
    """
    旁路采集验证：使用 browser_runtime.PlaywrightAdapter + xhs_cdp_collector 人类行为函数
    执行一次关键词采集，返回采集结果（不入库，仅用于旁路验证）。

    【注意】这是旁路验证函数，生产采集仍走 xhs_cdp_collector.collect_human/collect_direct。
    本函数复用 xhs_cdp_collector 的底层人类行为函数，但通过 PlaywrightAdapter 获取 page。

    Returns:
        {
            "enabled": bool,
            "keyword": str,
            "cdp_connected": bool,
            "search_ok": bool,
            "notes_found": int,        # 搜索结果中发现的笔记数量
            "details_opened": int,     # 打开的详情页数量
            "collected": list,         # 采集到的笔记摘要
            "error": str | None,
            "duration_ms": int,
        }
    """
    result: dict[str, Any] = {
        "enabled": is_enabled(),
        "keyword": keyword,
        "cdp_connected": False,
        "search_ok": False,
        "notes_found": 0,
        "details_opened": 0,
        "collected": [],
        "error": None,
        "duration_ms": 0,
    }
    if not result["enabled"]:
        result["error"] = f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用"
        return result
    cdp_url, endpoint_error = _resolve_hk_endpoint(cdp_url)
    if endpoint_error:
        result["error"] = endpoint_error
        result["status"] = "UNAVAILABLE"
        return result

    start = time.time()
    adapter = None
    try:
        from lumenis.system.browser.runtime.adapters.playwright_adapter import PlaywrightAdapter
        import xhs_cdp_collector as xhs

        adapter = PlaywrightAdapter(cdp_url=cdp_url, timeout_ms=timeout_ms)
        health = adapter.health()
        result["cdp_connected"] = health.get("cdp_connected", False)
        if not result["cdp_connected"]:
            result["error"] = f"CDP 连接失败: {health.get('error', 'unknown')}"
            return result

        page = adapter._page  # 内部访问，旁路验证用

        # 1. 人类搜索关键词
        xhs.human_search_keyword(page, keyword)
        result["search_ok"] = True
        xhs.human_sleep(1.5, 2.5)

        # 2. 人类滚动加载
        for i in range(max_scroll):
            xhs.scroll_human(page, total_px=800, rounds=1)
            xhs.human_sleep(1.0, 2.0)

        # 3. 统计搜索结果中的笔记卡片
        try:
            note_cards = page.locator("a.note-item, div.note-item, section.note-item").all()
            result["notes_found"] = len(note_cards)
        except Exception:
            # 选择器可能变化，用 page.evaluate 统计
            try:
                result["notes_found"] = page.evaluate(
                    "() => document.querySelectorAll('a[href*=\"/explore/\"], a[href*=\"/search_result/\"]').length"
                )
            except Exception:
                result["notes_found"] = 0

        # 4. 打开前 N 个详情页（人类行为）
        details_to_open = min(max_details, result["notes_found"], 3)
        for i in range(details_to_open):
            try:
                # 点击第 i 个笔记卡片
                cards = page.locator("a.note-item, div.note-item, section.note-item").all()
                if i < len(cards):
                    cards[i].click()
                    xhs.human_sleep(2.0, 3.5)
                    # 人类阅读内容
                    profile = xhs.human_reading_profile()
                    xhs.human_consume_detail(page, profile, depth=0.3)
                    result["details_opened"] += 1
                    # 记录笔记摘要
                    try:
                        title = page.title()
                        url = page.url
                        result["collected"].append({"title": title[:80], "url": url[:120]})
                    except Exception:
                        pass
                    # 返回搜索结果
                    page.go_back()
                    xhs.human_sleep(1.0, 2.0)
            except Exception as e:
                result.setdefault("detail_errors", []).append(str(e)[:150])
                continue

    except Exception as e:
        result["error"] = str(e)[:300]
    finally:
        if adapter is not None:
            try:
                adapter.close()
            except Exception:
                pass
        result["duration_ms"] = int((time.time() - start) * 1000)

    return result


# 模块自检
if __name__ == "__main__":
    import json
    print("=== XHS 采集旁路桥接层自检 ===")
    print(f"Feature Gate: {is_enabled()} (env {FEATURE_GATE_ENV})")
    if is_enabled():
        print("\n--- probe_xhs_page ---")
        probe = probe_xhs_page()
        print(json.dumps(probe, ensure_ascii=False, indent=2))
    else:
        print(f"未启用，设置环境变量 {FEATURE_GATE_ENV}=1 后运行自检")
