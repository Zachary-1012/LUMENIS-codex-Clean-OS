# -*- coding: utf-8 -*-
"""
Unit tests for agent_proactive.detector
覆盖：异常检测、风险升级检测、任务阻塞检测、数据缺失检测、
趋势变化检测、无信号场景、严重度排序、模块级函数
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_proactive.detector import (
    SignalDetector, Signal, SignalType, SignalSeverity,
    detect_signals,
)


@pytest.fixture
def detector():
    return SignalDetector()


class TestSignalDataclass:
    def test_default_values(self):
        sig = Signal(signal_type="anomaly", title="test")
        assert sig.signal_id.startswith("sig_")
        assert sig.signal_type == "anomaly"
        assert sig.severity == "info"
        assert sig.evidence_refs == []
        assert sig.detected_at

    def test_to_dict(self):
        sig = Signal(signal_type="anomaly", severity="critical", title="t")
        d = sig.to_dict()
        assert d["signal_type"] == "anomaly"
        assert d["severity"] == "critical"
        assert "signal_id" in d


class TestAnomalyDetection:
    def test_cpu_critical(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"cpu_pct": 95.0}
        })
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.ANOMALY.value
        assert signals[0].severity == SignalSeverity.CRITICAL.value
        assert "CPU" in signals[0].title

    def test_cpu_warning(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"cpu_pct": 80.0}
        })
        assert len(signals) == 1
        assert signals[0].severity == SignalSeverity.WARNING.value

    def test_memory_critical(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"memory_pct": 92.0}
        })
        assert any(s.signal_type == SignalType.ANOMALY.value
                   and "内存" in s.title for s in signals)
        assert signals[0].severity == SignalSeverity.CRITICAL.value

    def test_error_rate_critical(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"error_rate": 0.15}
        })
        assert any("错误率" in s.title for s in signals)
        assert signals[0].severity == SignalSeverity.CRITICAL.value

    def test_latency_warning(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"latency_ms": 3000}
        })
        assert any("延迟" in s.title for s in signals)

    def test_no_anomaly_normal(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"cpu_pct": 30.0, "memory_pct": 40.0,
                               "error_rate": 0.001, "latency_ms": 100}
        })
        assert signals == []


class TestRiskEscalation:
    def test_level_upgrade(self, detector):
        signals = detector.detect_signals({
            "risk_state": {"current_level": "high", "previous_level": "low"}
        })
        assert any(s.signal_type == SignalType.RISK_ESCALATION.value
                   for s in signals)

    def test_level_upgrade_to_critical(self, detector):
        signals = detector.detect_signals({
            "risk_state": {"current_level": "critical", "previous_level": "medium"}
        })
        risk_signals = [s for s in signals
                        if s.signal_type == SignalType.RISK_ESCALATION.value]
        assert any(s.severity == SignalSeverity.CRITICAL.value
                   for s in risk_signals)

    def test_no_escalation_same_level(self, detector):
        signals = detector.detect_signals({
            "risk_state": {"current_level": "low", "previous_level": "low"}
        })
        assert not any(s.signal_type == SignalType.RISK_ESCALATION.value
                       for s in signals)

    def test_escalation_count(self, detector):
        signals = detector.detect_signals({
            "risk_state": {"escalation_count": 5}
        })
        assert any("升级次数" in s.title for s in signals)


class TestTaskBlocked:
    def test_task_stuck_critical(self, detector):
        signals = detector.detect_signals({
            "task_progress": {"task_id": "t1", "status": "running",
                              "stuck_seconds": 900}
        })
        assert any(s.signal_type == SignalType.TASK_BLOCKED.value
                   for s in signals)
        assert signals[0].severity == SignalSeverity.CRITICAL.value

    def test_task_retry_critical(self, detector):
        signals = detector.detect_signals({
            "task_progress": {"task_id": "t2", "retry_count": 8}
        })
        assert any("重试" in s.title for s in signals)

    def test_completed_task_not_blocked(self, detector):
        signals = detector.detect_signals({
            "task_progress": {"task_id": "t3", "status": "completed",
                              "stuck_seconds": 9999}
        })
        assert not any(s.signal_type == SignalType.TASK_BLOCKED.value
                       for s in signals)


class TestDataMissing:
    def test_missing_tables(self, detector):
        signals = detector.detect_signals({
            "data_quality": {"missing_tables": ["notes", "comments"]}
        })
        assert any(s.signal_type == SignalType.DATA_MISSING.value
                   for s in signals)

    def test_null_rate_critical(self, detector):
        signals = detector.detect_signals({
            "data_quality": {"null_rate": 0.6}
        })
        assert any("空率" in s.title for s in signals)

    def test_capture_gap(self, detector):
        signals = detector.detect_signals({
            "data_quality": {"capture_gap_seconds": 7200}
        })
        assert any("断流" in s.title for s in signals)


class TestTrendChange:
    def test_trend_critical(self, detector):
        signals = detector.detect_signals({
            "trend_data": {"metric": "mention_count", "change_pct": 80.0,
                           "direction": "up"}
        })
        assert any(s.signal_type == SignalType.TREND_CHANGE.value
                   for s in signals)
        assert signals[0].severity == SignalSeverity.CRITICAL.value

    def test_trend_warning(self, detector):
        signals = detector.detect_signals({
            "trend_data": {"metric": "sentiment", "change_pct": -30.0,
                           "direction": "down"}
        })
        assert any(s.signal_type == SignalType.TREND_CHANGE.value
                   for s in signals)

    def test_no_trend_small_change(self, detector):
        signals = detector.detect_signals({
            "trend_data": {"metric": "x", "change_pct": 5.0}
        })
        assert signals == []


class TestPerformanceDegrade:
    def test_perf_degrade_critical(self, detector):
        signals = detector.detect_signals({
            "performance": {"current_latency_ms": 3000,
                            "baseline_latency_ms": 1000}
        })
        assert any(s.signal_type == SignalType.PERFORMANCE_DEGRADE.value
                   for s in signals)


class TestBetterPath:
    def test_better_path_signal(self, detector):
        signals = detector.detect_signals({
            "better_path": {"title": "可切换到批量采集",
                            "description": "批量模式效率提升3倍",
                            "source": "optimizer"}
        })
        assert any(s.signal_type == SignalType.BETTER_PATH.value
                   for s in signals)
        assert signals[0].severity == SignalSeverity.INFO.value


class TestNoSignal:
    def test_empty_context(self, detector):
        assert detector.detect_signals({}) == []

    def test_none_context(self, detector):
        assert detector.detect_signals(None) == []

    def test_irrelevant_context(self, detector):
        signals = detector.detect_signals({"foo": "bar", "num": 42})
        assert signals == []


class TestSeveritySorting:
    def test_sorted_descending(self, detector):
        signals = detector.detect_signals({
            "system_metrics": {"cpu_pct": 95.0},   # CRITICAL
            "trend_data": {"metric": "x", "change_pct": 25.0},  # WARNING
            "better_path": {"title": "opt"},       # INFO
        })
        assert len(signals) >= 3
        ranks = [s.severity_rank for s in signals]
        assert ranks == sorted(ranks, reverse=True)


class TestModuleLevelFunction:
    def test_detect_signals_module_fn(self):
        signals = detect_signals({
            "system_metrics": {"cpu_pct": 95.0}
        })
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.ANOMALY.value

    def test_custom_thresholds(self):
        det = SignalDetector(thresholds={"cpu_pct_critical": 50.0})
        signals = det.detect_signals({
            "system_metrics": {"cpu_pct": 55.0}
        })
        assert signals[0].severity == SignalSeverity.CRITICAL.value
