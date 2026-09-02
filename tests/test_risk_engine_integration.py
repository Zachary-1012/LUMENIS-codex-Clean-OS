# -*- coding: utf-8 -*-
"""RiskEngine 接入 collector 主链路（P1-4）集成测试。

覆盖：
- Feature Flag 开关（TAIKOO_RISK_ENGINE）
- 关闭时 _feed_risk_engine 恒 False，不改变原链路行为
- 成功/空结果 -> record_success（风险分衰减/不触发熔断）
- NETWORK_ERROR -> 累积风险分，达到档位后熔断
- BLOCKED/CAPTCHA/AUTH_REQUIRED -> 硬信号一次熔断
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import collector
from collector_guard.risk_engine import RiskEngine


@pytest.fixture(autouse=True)
def _clean_risk_singleton():
    collector._XHS_RISK = None
    yield
    collector._XHS_RISK = None


class TestRiskEngineFeatureFlag:
    def test_default_enabled(self, monkeypatch):
        monkeypatch.delenv("TAIKOO_RISK_ENGINE", raising=False)
        collector._XHS_RISK = None
        eng = collector._get_xhs_risk_engine()
        assert isinstance(eng, RiskEngine)

    def test_disabled_returns_none(self, monkeypatch):
        monkeypatch.setenv("TAIKOO_RISK_ENGINE", "0")
        collector._XHS_RISK = None
        assert collector._get_xhs_risk_engine() is None

    def test_disabled_lowercase_false(self, monkeypatch):
        monkeypatch.setenv("TAIKOO_RISK_ENGINE", "false")
        collector._XHS_RISK = None
        assert collector._get_xhs_risk_engine() is None


class TestFeedRiskEngineNoOpWhenDisabled:
    def test_none_risk_always_false(self):
        assert collector._feed_risk_engine(None, error="", guard_state="", count=5,
                                           kw="测试", is_core=True, results=[]) is False
        assert collector._feed_risk_engine(None, error="IP_RISK", guard_state="", count=0,
                                           kw="测试", is_core=True, results=[]) is False


class TestFeedRiskEngineSuccess:
    def test_success_decays_score(self):
        risk = RiskEngine()
        risk.record_failure("http_error")  # 先抬分
        score_before = risk.snapshot()["risk_score"]
        assert score_before > 0
        stop = collector._feed_risk_engine(risk, error="", guard_state="", count=8,
                                           kw="太古汇", is_core=True, results=[])
        assert stop is False
        assert risk.snapshot()["risk_score"] < score_before

    def test_empty_no_error_is_not_risk(self):
        risk = RiskEngine()
        stop = collector._feed_risk_engine(risk, error="", guard_state="", count=0,
                                           kw="太古汇", is_core=True, results=[])
        assert stop is False
        # EMPTY（真实无内容）不加风险分，保持 0
        assert risk.snapshot()["risk_score"] == 0


class TestFeedRiskEngineNetworkAccumulation:
    def test_network_error_accumulates_to_cooldown(self):
        risk = RiskEngine()
        results = []
        for _ in range(6):  # 每次 http_error=10，累计到 60（THROTTLED），再继续到 70+（COOLDOWN）
            stop = collector._feed_risk_engine(risk, error="timeout", guard_state="", count=0,
                                               kw="太古汇", is_core=True, results=results)
            if stop:
                break
        snap = risk.snapshot()
        assert snap["risk_score"] >= 70
        assert snap["band"] in ("COOLDOWN", "CIRCUIT_OPEN")
        assert len(results) == 1  # 熔断记录一条


class TestFeedRiskEngineHardSignals:
    def test_blocked_immediate_circuit_open(self):
        risk = RiskEngine()
        results = []
        stop = collector._feed_risk_engine(risk, error="IP_RISK_OR_300012", guard_state="", count=0,
                                           kw="太古汇", is_core=True, results=results)
        assert stop is True
        assert results[0]["risk_band"] == "CIRCUIT_OPEN"

    def test_captcha_immediate_circuit_open(self):
        risk = RiskEngine()
        results = []
        stop = collector._feed_risk_engine(risk, error="NEED_VERIFY", guard_state="", count=0,
                                           kw="太古汇", is_core=True, results=results)
        assert stop is True
        assert results[0]["risk_band"] == "CIRCUIT_OPEN"

    def test_auth_required_immediate_circuit_open(self):
        risk = RiskEngine()
        results = []
        stop = collector._feed_risk_engine(risk, error="login failed", guard_state="", count=0,
                                           kw="太古汇", is_core=True, results=results)
        assert stop is True
        assert results[0]["risk_band"] == "CIRCUIT_OPEN"

    def test_hard_signal_respects_guard_state(self):
        # guard 已标 BLOCKED（如 COOLDOWN）时同样走硬信号
        risk = RiskEngine()
        results = []
        stop = collector._feed_risk_engine(risk, error="", guard_state="COOLDOWN", count=0,
                                           kw="太古汇", is_core=True, results=results)
        assert stop is True


class TestRiskEngineHalfOpenRecovery:
    """熔断恢复闭环（学习 pybreaker：OPEN→冷却→HALF_OPEN 试探→成功闭合/失败重熔）。"""

    def test_tripped_blocks_before_cooldown(self):
        risk = RiskEngine(reset_timeout=300)
        risk.record_failure("security_page")  # 硬信号一次熔断
        snap = risk.snapshot()
        assert snap["band"] == "CIRCUIT_OPEN"
        assert snap["should_stop_request"] is True
        assert snap["half_open"] is False
        assert snap["cooldown_remaining_s"] > 0

    def test_half_open_after_cooldown_elapsed(self):
        import time as _t
        risk = RiskEngine(reset_timeout=10)
        risk.record_failure("security_page")
        # 模拟冷却时间已过：把熔断时刻回拨
        risk.opened_at = _t.time() - 11
        snap = risk.snapshot()
        assert snap["half_open"] is True
        assert snap["band"] == "HALF_OPEN"
        assert snap["should_stop_request"] is False  # 放行一次探测

    def test_half_open_success_fully_closes(self):
        import time as _t
        risk = RiskEngine(reset_timeout=10)
        risk.record_failure("security_page")
        risk.opened_at = _t.time() - 11
        assert risk.snapshot()["half_open"] is True
        score, band, _ = risk.record_success()  # 探测成功
        assert band == "NORMAL"
        assert score == 0
        assert risk.opened_at is None
        assert risk.half_open is False
        assert risk.snapshot()["should_stop_request"] is False

    def test_half_open_failure_retrips(self):
        import time as _t
        risk = RiskEngine(reset_timeout=10)
        risk.record_failure("security_page")
        first_opened = risk.opened_at
        risk.opened_at = _t.time() - 11
        assert risk.snapshot()["half_open"] is True
        # 半开期探测又失败 -> 重新熔断，冷却计时刷新
        risk.record_failure("http_error")
        assert risk.half_open is False
        assert risk._last_band in ("COOLDOWN", "CIRCUIT_OPEN")
        assert risk.opened_at >= first_opened
        assert risk.snapshot()["should_stop_request"] is True

    def test_half_open_requires_threshold_successes(self):
        import time as _t
        risk = RiskEngine(reset_timeout=10, half_open_success_threshold=2)
        risk.record_failure("security_page")
        risk.opened_at = _t.time() - 11
        assert risk.snapshot()["half_open"] is True
        _, band1, _ = risk.record_success()
        assert band1 == "HALF_OPEN"  # 第一次成功仍半开
        _, band2, _ = risk.record_success()
        assert band2 == "NORMAL"     # 达阈值才完全闭合
