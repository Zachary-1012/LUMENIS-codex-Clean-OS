# -*- coding: utf-8 -*-
"""RiskEngine 宏观生命周期六态映射测试（UNIFIED-BASELINE §10）。

验证内部风险分档 → 对外六态的映射、Scheduler/Worker 联动动作、半开恢复叙事 RECOVERING→RECOVERED→NORMAL。
内部既有 band/state/should_stop 行为不变（零减配）。
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from collector_guard.risk_engine import RiskEngine, LIFECYCLE_ACTIONS  # noqa: E402


def test_initial_normal():
    e = RiskEngine()
    assert e.lifecycle_state() == "NORMAL"
    assert e.lifecycle_action() == "schedule_normal"
    snap = e.snapshot()
    assert snap["lifecycle"] == "NORMAL" and snap["lifecycle_action"] == "schedule_normal"
    # 既有字段仍在（零减配）
    for k in ("risk_score", "band", "state", "should_stop_request", "half_open", "cooldown_remaining_s"):
        assert k in snap


def test_throttled_is_adaptive():
    e = RiskEngine()
    e.record_failure("abnormal_response")          # +15 WATCH
    e.record_failure("abnormal_response")          # 连续失败 +15+20 -> 50 THROTTLED
    assert e._last_band == "THROTTLED"
    assert e.lifecycle_state() == "ADAPTIVE"
    assert e.lifecycle_action() == "backoff_interval"


def test_rate_limited_is_cooldown():
    e = RiskEngine()
    e.record_failure("rate_limited")               # 硬信号 -> COOLDOWN
    assert e._last_band == "COOLDOWN"
    assert e.lifecycle_state() == "COOLDOWN"
    assert e.lifecycle_action() == "pause_until_cooldown"


def test_security_page_is_frozen():
    e = RiskEngine()
    e.record_failure("security_page")              # 硬信号 -> CIRCUIT_OPEN
    assert e._last_band == "CIRCUIT_OPEN"
    assert e.lifecycle_state() == "FROZEN"
    assert e.lifecycle_action() == "freeze_and_recover"
    assert e.snapshot()["should_stop_request"] is True


def test_cooldown_elapsed_enters_recovering():
    e = RiskEngine(reset_timeout=300)
    e.record_failure("security_page")              # FROZEN
    # 把熔断时刻往前拨超过冷却时间 -> 半开探测
    e.opened_at = time.time() - 301
    snap = e.snapshot()
    assert snap["half_open"] is True
    assert e.lifecycle_state() == "RECOVERING"
    assert e.lifecycle_action() == "probe_only"


def test_half_open_success_then_recovered_then_normal():
    e = RiskEngine(reset_timeout=300, half_open_success_threshold=1, recovered_window_s=10)
    e.record_failure("security_page")
    e.opened_at = time.time() - 301
    e.snapshot()                                   # 进入 RECOVERING
    assert e.lifecycle_state() == "RECOVERING"
    e.record_success()                             # 半开探测成功，闭合
    assert e.lifecycle_state() == "RECOVERED"
    assert e.lifecycle_action() == "ramp_up"
    # 超过观察窗口回到稳态 NORMAL
    e.recovered_at = time.time() - 11
    assert e.lifecycle_state() == "NORMAL"


def test_new_failure_exits_recovered():
    e = RiskEngine(recovered_window_s=999)
    e.recovered_at = time.time()                   # 人工置为刚恢复
    assert e.lifecycle_state() == "RECOVERED"
    e.record_failure("rate_limited")               # 新风险
    assert e.recovered_at is None
    assert e.lifecycle_state() == "COOLDOWN"


def test_all_six_states_have_actions():
    for st in ("NORMAL", "ADAPTIVE", "COOLDOWN", "FROZEN", "RECOVERING", "RECOVERED"):
        assert st in LIFECYCLE_ACTIONS
