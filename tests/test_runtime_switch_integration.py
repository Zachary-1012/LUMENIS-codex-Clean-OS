# -*- coding: utf-8 -*-
"""RuntimeSwitch 接线 E2E 验证：证明 collector 接线协议可安全接入生产。

不依赖 collector.py（巡检在途），用模拟采集循环验证：
  is_enabled() and not is_dry_run() -> 才真正发请求
  disabled -> 请求数=0（运维总闸覆盖自动化）
  dry_run  -> 请求数=0 但决策记录完整（演练，记录 would-have）
"""
import pytest

from collector_guard.runtime_switch import RuntimeSwitch


def make_collector(sw):
    """模拟采集循环（对齐 docs/RUNTIME-SWITCH.md 接线指引）。"""
    sent = []
    would_have = []

    def collect_one(kw):
        if sw.is_enabled() and not sw.is_dry_run():
            sent.append(kw)          # 真正发起采集请求
            return {"kw": kw, "sent": True}
        would_have.append({"kw": kw, "state": sw.status()["state"]})  # 记录 would-have
        return {"kw": kw, "sent": False}
    return collect_one, sent, would_have


@pytest.fixture
def sw(tmp_path):
    return RuntimeSwitch(state_path=str(tmp_path / "s.json"),
                         audit_path=str(tmp_path / "a.jsonl"))


def test_enabled_sends_requests(sw):
    collect, sent, _ = make_collector(sw)
    r = collect("A")
    assert r["sent"] is True and sent == ["A"]


def test_kill_switch_suppresses_all(sw):
    collect, sent, _ = make_collector(sw)
    sw.set_enabled(False, reason="incident", actor="ops")
    r1 = collect("A")
    r2 = collect("B")
    assert r1["sent"] is False and r2["sent"] is False
    assert sent == []  # 总闸覆盖自动化，一个请求都不发


def test_dry_run_evaluates_but_does_not_act(sw):
    collect, sent, would_have = make_collector(sw)
    sw.set_dry_run(True)
    r = collect("A")
    assert r["sent"] is False and sent == []
    assert len(would_have) == 1
    assert would_have[0]["kw"] == "A" and would_have[0]["state"] == "DRY_RUN"


def test_recover_after_disable(sw):
    collect, sent, _ = make_collector(sw)
    sw.set_enabled(False, reason="maintenance")
    collect("A")
    assert sent == []
    sw.set_enabled(True, confirm=True)
    collect("B")
    assert sent == ["B"]  # 重新启用后恢复发请求
