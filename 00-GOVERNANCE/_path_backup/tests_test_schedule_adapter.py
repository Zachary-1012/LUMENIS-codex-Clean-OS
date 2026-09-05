# -*- coding: utf-8 -*-
"""P1-A 六态联动调度器测试：lifecycle_action -> ResourceGuard 四态 -> 停止/放行决策 + collector 接线。"""
import sys

sys.path.insert(0, r"D:\Taikoo-monitor-new")

import pytest

from collector_guard.resource_guard import HIGH_EFFICIENCY, NORMAL, RECOVERY, RESOURCE_GUARDED  # noqa: E402
from collector_guard.schedule_adapter import advice, schedule_state, should_stop_schedule  # noqa: E402


@pytest.mark.parametrize("action,stop", [
    ("schedule_normal", False),
    ("backoff_interval", False),
    ("ramp_up", False),
    ("probe_only", False),          # 半开探测放行
])
def test_non_stop_actions(action, stop):
    assert should_stop_schedule(action) is stop


@pytest.mark.parametrize("action", ["pause_until_cooldown", "freeze_and_recover"])
def test_stop_actions(action):
    assert should_stop_schedule(action) is True


def test_probe_only_never_stops_even_with_resource_pressure():
    a = advice("probe_only", cpu_pct=95, ram_pct=95, queue_lag=500)
    assert a["should_stop"] is False  # 探测必须放行
    assert a["queue_policy"] == "probe_only"


def test_cooldown_advice_blocks_new():
    a = advice("pause_until_cooldown")
    assert a["resource_guard_state"] == RESOURCE_GUARDED
    assert a["allow_new"] is False
    assert a["queue_policy"] in ("backpressure", "queue")


def test_schedule_state_mapping():
    assert schedule_state("pause_until_cooldown") == RESOURCE_GUARDED
    assert schedule_state("ramp_up") == RECOVERY
    assert schedule_state("schedule_normal") == HIGH_EFFICIENCY
    assert schedule_state(None) in (HIGH_EFFICIENCY, NORMAL)


def test_empty_lifecycle_no_stop():
    assert should_stop_schedule(None) is False
    assert should_stop_schedule("") is False


# --- collector._feed_risk_engine 接线冒烟 ---
class _FakeRisk:
    def __init__(self, lifecycle, score=30, band="LOW", should_stop=False):
        self._lifecycle = lifecycle
        self._score = score
        self._band = band
        self._should_stop = should_stop

    def record_failure(self, factor):
        return self._score, self._band, self._band

    def record_success(self):
        return self._score, self._band, self._band

    def snapshot(self):
        return {"lifecycle_action": self._lifecycle, "risk_score": self._score,
                "band": self._band, "should_stop_request": self._should_stop}


def test_feed_risk_engine_schedule_stop(monkeypatch):
    import collector as col

    monkeypatch.setattr(col, "classify_collect_state", lambda **kw: "ok")
    monkeypatch.setattr(col, "_RISK_FACTOR_BY_STATE", {"ok": 1.0})

    results = []
    stop = col._feed_risk_engine(_FakeRisk("freeze_and_recover"), error="", guard_state="ok",
                                 count=5, kw="k", is_core=True, results=results)
    assert stop is True  # ResourceGuard 判定 freeze -> 停止
    assert results and results[-1].get("schedule_state") == RESOURCE_GUARDED


def test_feed_risk_engine_normal_continues(monkeypatch):
    import collector as col

    monkeypatch.setattr(col, "classify_collect_state", lambda **kw: "ok")
    monkeypatch.setattr(col, "_RISK_FACTOR_BY_STATE", {"ok": 1.0})
    results = []
    stop = col._feed_risk_engine(_FakeRisk("schedule_normal", score=10, band="NORMAL"),
                                 error="", guard_state="ok", count=5, kw="k",
                                 is_core=True, results=results)
    assert stop is False  # 正常继续
