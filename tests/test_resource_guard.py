# -*- coding: utf-8 -*-
"""P0-G ResourceGuard 四态单测：lifecycle_action 消费 + 资源阈值保护 + 上限约束。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from lumenis.system.collector.guard.resource_guard import (  # noqa: E402
    HIGH_EFFICIENCY,
    NORMAL,
    RECOVERY,
    RESOURCE_GUARDED,
    ResourceGuard,
)


@pytest.fixture
def guard():
    return ResourceGuard()


def test_normal_to_high_efficiency(guard):
    d = guard.decide("schedule_normal")
    assert d["state"] == HIGH_EFFICIENCY
    assert d["allow_new"] is True
    assert d["worker_scale"] <= guard.max_worker_scale  # 有上限


def test_backoff_interval_adaptive(guard):
    d = guard.decide("backoff_interval")
    assert d["state"] == HIGH_EFFICIENCY
    assert d["interval_multiplier"] >= 1.5


def test_cooldown_guards(guard):
    d = guard.decide("pause_until_cooldown")
    assert d["state"] == RESOURCE_GUARDED
    assert d["queue_policy"] == "backpressure"
    assert d["worker_scale"] < 0.5


def test_freeze_queues(guard):
    d = guard.decide("freeze_and_recover")
    assert d["state"] == RESOURCE_GUARDED
    assert d["queue_policy"] == "queue"


def test_probe_only_minimal(guard):
    d = guard.decide("probe_only")
    assert d["state"] == RESOURCE_GUARDED
    assert d["queue_policy"] == "probe_only"
    assert d["worker_scale"] <= 0.1


def test_ramp_up_recovery(guard):
    d = guard.decide("ramp_up")
    assert d["state"] == RECOVERY
    assert d["worker_scale"] < 1.0  # 逐步回满


def test_cpu_over_threshold_forces_guard(guard):
    d = guard.decide("schedule_normal", cpu_pct=95, ram_pct=40, queue_lag=0)
    assert d["state"] == RESOURCE_GUARDED
    assert "cpu=95%" in d["reason"]


def test_ram_over_threshold(guard):
    d = guard.decide("backoff_interval", cpu_pct=40, ram_pct=92)
    assert d["state"] == RESOURCE_GUARDED


def test_queue_lag_backpressure(guard):
    d = guard.decide("schedule_normal", cpu_pct=40, ram_pct=40, queue_lag=500)
    assert d["state"] == RESOURCE_GUARDED
    assert d["queue_policy"] == "backpressure"


def test_snapshot_includes_thresholds(guard):
    s = guard.snapshot("ramp_up", cpu_pct=50, ram_pct=50, queue_lag=10)
    assert s["resource_guard_state"] == RECOVERY
    assert s["thresholds"]["cpu_high"] == 80.0
