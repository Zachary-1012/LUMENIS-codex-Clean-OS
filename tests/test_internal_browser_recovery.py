# -*- coding: utf-8 -*-
"""内置浏览器恢复回路测试（mock CDP，不依赖驻场浏览器）。"""
import json
import internal_browser as ib


def test_internal_browser_defaults_to_hk_production(monkeypatch):
    """无账号/无显式端口的生产浏览请求不得静默落到大陆诊断端口。"""
    monkeypatch.setattr(ib, "bridge", None)
    assert ib._canonical_account(None) == "XHS_RETINAUT"
    assert ib._port_for(None) == 9223
    assert ib._home_for(None) == "https://www.rednote.com"


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
