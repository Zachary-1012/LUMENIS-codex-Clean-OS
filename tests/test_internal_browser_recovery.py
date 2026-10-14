# -*- coding: utf-8 -*-
"""内置浏览器恢复回路测试（mock CDP，不依赖驻场浏览器）。"""
import json
from types import SimpleNamespace

import pytest

import internal_browser as ib


def test_internal_browser_defaults_to_hk_identity_but_requires_registered_worker(monkeypatch):
    """默认逻辑身份保留；没有注册的后台 Worker 时不得猜测端口。"""
    monkeypatch.setattr(ib, "bridge", None)
    assert ib._canonical_account(None) == "XHS_RETINAUT"
    with pytest.raises(RuntimeError, match="BROWSER_WORKER_ENDPOINT_UNAVAILABLE"):
        ib._port_for(None)
    assert ib._home_for(None) == "https://www.rednote.com"


def test_generic_internal_browser_operations_resolve_background_worker_only(monkeypatch):
    """通用操作只解析 headless Worker，不得接管 HUMAN_INTERACTIVE 租约。"""
    calls = []

    def cdp_port_for(account, *, headless=True):
        calls.append((account, headless))
        if headless is True:
            return 9477
        return None

    monkeypatch.setattr(
        ib,
        "bridge",
        SimpleNamespace(
            _canonical_account_name=lambda account: account or "XHS_RETINAUT",
            cdp_port_for=cdp_port_for,
            home_url_for=lambda _account: "https://www.rednote.com",
        ),
    )
    assert ib._port_for("XHS_RETINAUT") == 9477
    assert calls == [("XHS_RETINAUT", True)]


def test_generic_internal_browser_does_not_fall_back_to_human_worker(monkeypatch):
    """只有 HUMAN_INTERACTIVE Worker 在线时，通用内部操作仍应不可用。"""
    calls = []

    def cdp_port_for(account, *, headless=True):
        calls.append((account, headless))
        return 9444 if headless is False else None

    monkeypatch.setattr(
        ib,
        "bridge",
        SimpleNamespace(cdp_port_for=cdp_port_for),
    )
    with pytest.raises(RuntimeError, match="BROWSER_WORKER_ENDPOINT_UNAVAILABLE"):
        ib._port_for("XHS_RETINAUT")
    assert calls == [("XHS_RETINAUT", True)]


def test_internal_browser_state_reports_missing_worker_without_raising(monkeypatch):
    """Capability/state callers get an honest unavailable record, not HTTP 500."""
    monkeypatch.setattr(
        ib,
        "bridge",
        SimpleNamespace(
            _canonical_account_name=lambda account: account or "XHS_RETINAUT",
            cdp_port_for=lambda _account, *, headless=True: None,
            home_url_for=lambda _account: "https://www.rednote.com",
        ),
    )

    state = ib.get_state("XHS_RETINAUT")

    assert state["status"] == "unavailable"
    assert state["online"] is False
    assert state["cdp_port"] is None
    assert state["error_type"] == "RuntimeError"


def test_internal_browser_adapter_preserves_account_through_nested_cdp_calls(monkeypatch):
    import browser_surface as bs
    import internal_browser_adapter as adapter

    port = 9477
    account = "XHS_RETINAUT"
    resolved = []
    nested = []

    def resolve_endpoint(requested_account, requested_port=None):
        resolved.append((requested_account, requested_port))
        return port

    class FakeWebSocket:
        def close(self):
            pass

    ws = FakeWebSocket()
    chosen = {"target_id": "registered-tab"}
    monkeypatch.setattr(bs, "_resolve_port", resolve_endpoint)
    monkeypatch.setattr(bs, "evaluate_navigation", lambda _url: {"status": "allowed"})
    monkeypatch.setattr(
        bs,
        "navigate_tab",
        lambda *_args, **kwargs: nested.append(("navigate", kwargs.get("account")))
        or {"ok": True, "target_id": "registered-tab"},
    )
    monkeypatch.setattr(
        bs,
        "_hybrid_screenshot",
        lambda **kwargs: nested.append(("screenshot", kwargs.get("account")))
        or {"ok": True},
    )
    monkeypatch.setattr(
        bs,
        "list_targets",
        lambda **kwargs: nested.append(("list", kwargs.get("account")))
        or {"ok": True, "tabs": [], "count": 0},
    )
    monkeypatch.setattr(
        bs,
        "_find_tab_ws",
        lambda *_args, **kwargs: nested.append(("find", kwargs.get("account")))
        or (ws, chosen),
    )
    monkeypatch.setattr(
        bs,
        "activate_tab",
        lambda *_args, **kwargs: nested.append(("activate", kwargs.get("account")))
        or {"ok": True},
    )
    monkeypatch.setattr(ib, "_cdp", lambda *_args, **_kwargs: {"result": {"result": {"value": "ok"}}})

    assert adapter.navigate("https://www.xiaohongshu.com", port=port)["ok"] is True
    assert adapter.screenshot(port=port)["ok"] is True
    assert adapter.list_tabs(port=port)["ok"] is True
    assert adapter.refresh(port=port)["ok"] is True
    assert adapter.switch_tab(port=port, target_id="registered-tab")["ok"] is True
    assert adapter.evaluate_js(port=port, target_id="registered-tab", expression="document.title")["ok"] is True

    assert resolved == [(account, port)] * 6
    assert nested == [
        ("navigate", account),
        ("screenshot", account),
        ("list", account),
        ("find", account),
        ("activate", account),
        ("find", account),
    ]


def test_internal_browser_adapter_general_port_keeps_no_platform_identity(monkeypatch):
    import browser_surface as bs
    import internal_browser_adapter as adapter

    resolved = []
    listed = []
    activated = []

    def resolve_endpoint(account, port=None):
        resolved.append((account, port))
        if account is not None:
            raise PermissionError("platform identity cannot use general browser")
        assert port == adapter.CDP_PORTS["general"]
        return port

    monkeypatch.setattr(bs, "_resolve_port", resolve_endpoint)
    monkeypatch.setattr(
        bs,
        "list_targets",
        lambda **kwargs: listed.append(kwargs) or {"ok": True, "tabs": [], "count": 0},
    )
    monkeypatch.setattr(
        bs,
        "activate_tab",
        lambda *_args, **kwargs: activated.append(kwargs) or {"ok": True},
    )

    result = adapter.list_tabs(port=adapter.CDP_PORTS["general"])
    switched = adapter.switch_tab(port=adapter.CDP_PORTS["general"], target_id="general-tab")
    rejected = adapter.list_tabs(port=adapter.CDP_PORTS["general"], account="XHS_RETINAUT")

    assert result["ok"] is True
    assert listed == [{"port": adapter.CDP_PORTS["general"], "pages_only": True, "account": None}]
    assert switched["ok"] is True
    assert activated == [{"port": adapter.CDP_PORTS["general"], "account": None}]
    assert rejected["ok"] is False
    assert resolved == [(None, adapter.CDP_PORTS["general"]),
                        (None, adapter.CDP_PORTS["general"]),
                        ("XHS_RETINAUT", adapter.CDP_PORTS["general"])]


def test_internal_browser_tabs_route_does_not_inject_xhs_for_explicit_general_port(monkeypatch):
    from flask import Flask
    import internal_browser_adapter as adapter

    observed = []
    monkeypatch.setattr(
        adapter,
        "list_tabs",
        lambda **kwargs: observed.append(kwargs) or {"ok": True, "tabs": [], "count": 0},
    )
    app = Flask(__name__)
    ib.register_internal_browser(app)

    response = app.test_client().get(f"/api/internal-browser/tabs?port={adapter.CDP_PORTS['general']}")

    assert response.status_code == 200
    assert observed == [{"port": adapter.CDP_PORTS["general"], "account": None}]


def test_internal_browser_navigate_route_passes_resolved_account_to_adapter(monkeypatch):
    from flask import Flask
    import internal_browser_adapter as adapter

    observed = []
    monkeypatch.setattr(ib, "_port_for", lambda account: 9477 if account == "XHS_RETINAUT" else None)
    monkeypatch.setattr(
        adapter,
        "navigate",
        lambda url, **kwargs: observed.append((url, kwargs)) or {"ok": True, "status": "navigated"},
    )
    app = Flask(__name__)
    ib.register_internal_browser(app)

    response = app.test_client().post(
        "/api/internal-browser/navigate",
        json={"url": "https://www.xiaohongshu.com/explore", "account": "XHS_RETINAUT"},
    )

    assert response.status_code == 200
    assert observed == [("https://www.xiaohongshu.com/explore", {
        "port": 9477,
        "confirmed": False,
        "account": "XHS_RETINAUT",
    })]


def _patch(monkeypatch, **kwargs):
    """mock 掉依赖驻场浏览器的函数，返回可注入行为的 dict。"""
    calls = {"click": [], "type": [], "evaluate": [], "navigate": [], "scroll": []}

    def fake_click(account, x, y, button="left"):
        calls["click"].append((x, y))
        if kwargs.get("click_ok") is False:
            raise RuntimeError("click 失败")
        return {"ok": True, "x": x, "y": y}

    def fake_type(account, text):
        calls["type"].append(text)
        return {"ok": True, "length": len(text)}

    def fake_evaluate(account, expr):
        calls["evaluate"].append(expr)
        val = kwargs.get("eval_value")
        if callable(val):
            val = val(expr)
        return {"ok": True, "value": val}

    def fake_navigate(account, url):
        calls["navigate"].append(url)
        if kwargs.get("navigate_ok") is False:
            # 首次失败、后续成功（模拟"重规划后恢复"）
            if len(calls["navigate"]) == 1:
                return {"ok": False, "error": "导航失败"}
            return {"ok": True, "url": url}
        return {"ok": True, "url": url}

    def fake_scroll(account, delta_y=400):
        calls["scroll"].append(delta_y)
        return {"ok": True, "scroll_y": 400}

    monkeypatch.setattr(ib, "click_at", fake_click)
    monkeypatch.setattr(ib, "type_text", fake_type)
    monkeypatch.setattr(ib, "evaluate", fake_evaluate)
    monkeypatch.setattr(ib, "navigate", fake_navigate)
    monkeypatch.setattr(ib, "scroll_page", fake_scroll)
    return calls


def test_find_element_invalid_selector(monkeypatch):
    """非法 selector（含 JS 注入字符）拒绝。"""
    calls = _patch(monkeypatch, eval_value=None)
    r = ib.find_element("XHS_CN_PRIMARY", "input');alert(1);//")
    assert r["ok"] is False
    assert "非法字符" in r["error"]
    assert calls["evaluate"] == [], "非法 selector 不应发起 JS 求值"


def test_find_element_not_found(monkeypatch):
    """元素不存在 → 返回未找到。"""
    _patch(monkeypatch, eval_value='{"found":false}')
    r = ib.find_element("XHS_CN_PRIMARY", ".search-box")
    assert r["ok"] is False
    assert "未找到" in r["error"]


def test_find_element_found(monkeypatch):
    """元素存在且可见 → 返回中心坐标。"""
    _patch(monkeypatch, eval_value='{"found":true,"x":100,"y":50,"visible":true}')
    r = ib.find_element("XHS_CN_PRIMARY", ".btn-search")
    assert r["ok"] is True
    assert r["x"] == 100 and r["y"] == 50


def test_click_selector_success(monkeypatch):
    """click_selector 成功：定位→点击→trace 记录一次尝试。"""
    calls = _patch(monkeypatch, eval_value='{"found":true,"x":100,"y":50,"visible":true}')
    r = ib.click_selector("XHS_CN_PRIMARY", ".btn-search", retry=2)
    assert r["ok"] is True
    assert calls["click"] == [(100, 50)]
    assert r["trace"][0]["action"] == "click_selector"
    assert r["trace"][0]["ok"] is True


def test_click_selector_retry_then_fail(monkeypatch):
    """click_selector 元素始终找不到 → 重试 N 次后失败，trace 记录每次尝试。"""
    _patch(monkeypatch, eval_value='{"found":false}')
    r = ib.click_selector("XHS_CN_PRIMARY", ".missing", retry=2, retry_delay=0)
    assert r["ok"] is False
    assert len(r["trace"]) == 3  # retry=2 → 3 次尝试
    assert all(t["ok"] is False for t in r["trace"])


def test_type_into_success(monkeypatch):
    """type_into 成功：定位→点击聚焦→输入。"""
    calls = _patch(monkeypatch, eval_value='{"found":true,"x":10,"y":20,"visible":true}')
    r = ib.type_into("XHS_CN_PRIMARY", "input[name=q]", "太古汇", retry=1)
    assert r["ok"] is True
    assert calls["click"] == [(10, 20)]
    assert calls["type"] == ["太古汇"]


def test_browser_task_trace_and_budget(monkeypatch):
    """browser_task：步骤 trace 完整；步骤预算超限时停止并标记 skipped。"""
    _patch(monkeypatch,
           eval_value='{"found":true,"x":5,"y":5,"visible":true}')
    steps = [
        {"action": "navigate", "url": "https://www.xiaohongshu.com"},
        {"action": "click", "selector": ".search"},
        {"action": "type", "selector": "input", "text": "太古汇"},
        {"action": "wait", "seconds": 0},
        {"action": "scroll", "delta_y": 200},
        {"action": "bad_action"},
    ]
    r = ib.browser_task("XHS_CN_PRIMARY", steps, max_steps=4, total_timeout=10)
    assert len(r["trace"]) == 5  # 4 执行 + 1 skipped（预算截断）
    assert r["trace"][-1]["skipped"] is True
    assert r["trace"][-1]["reason"] == "步骤预算超限"
    assert r["ok_steps"] == 4
    assert r["ok"] is True  # 4 成功 + 1 跳过 = 全部 accounted


def test_browser_task_all_ok(monkeypatch):
    """browser_task 全部步骤成功：ok=True，ok_steps=步骤数。"""
    _patch(monkeypatch,
           eval_value='{"found":true,"x":5,"y":5,"visible":true}')
    steps = [
        {"action": "navigate", "url": "https://www.xiaohongshu.com"},
        {"action": "click", "selector": ".search"},
        {"action": "type", "selector": "input", "text": "太古汇"},
        {"action": "scroll", "delta_y": 200},
    ]
    r = ib.browser_task("XHS_CN_PRIMARY", steps, max_steps=10, total_timeout=10)
    assert r["ok"] is True
    assert r["ok_steps"] == 4
    assert len(r["trace"]) == 4


def test_browser_task_unknown_action(monkeypatch):
    """browser_task 未知 action：该步骤 ok=False，整体 ok=False。"""
    _patch(monkeypatch)
    r = ib.browser_task("XHS_CN_PRIMARY", [{"action": "nope"}], max_steps=5, total_timeout=10)
    assert r["ok"] is False
    assert r["trace"][0]["ok"] is False
    assert "未知 action" in r["trace"][0]["detail"]


def test_browser_task_navigate_fail_continues(monkeypatch):
    """browser_task 导航失败：该步骤失败但任务继续，整体按失败计。"""
    _patch(monkeypatch, navigate_ok=False)
    steps = [
        {"action": "navigate", "url": "https://www.xiaohongshu.com/explore"},
        {"action": "navigate", "url": "https://www.xiaohongshu.com/search"},
    ]
    r = ib.browser_task("XHS_CN_PRIMARY", steps, max_steps=5, total_timeout=10)
    assert len(r["trace"]) == 2
    assert r["trace"][0]["ok"] is False
    assert r["trace"][1]["ok"] is True
    assert r["ok"] is False
