# -*- coding: utf-8 -*-
"""DLQ 恢复重放生产接线测试（schedule_adapter.maybe_replay_dlq）。"""
import pytest

from collector_guard.dlq_replay import DeadLetterQueue
from collector_guard.schedule_adapter import maybe_replay_dlq


@pytest.fixture
def dlq(tmp_path):
    return DeadLetterQueue(path=str(tmp_path / "dlq.jsonl"), max_attempts=3)


def test_non_recovery_state_no_replay(dlq):
    # NORMAL/ADAPTIVE/COOLDOWN/FROZEN 都不触发
    for action in ("schedule_normal", "backoff_interval",
                   "pause_until_cooldown", "freeze_and_recover"):
        assert maybe_replay_dlq(action, dlq=dlq) is None


def test_recovering_dry_returns_pending(dlq):
    dlq.enqueue("kw1", error="net_err")
    dlq.enqueue("kw2", error="login_err")
    r = maybe_replay_dlq("probe_only", dlq=dlq)  # RECOVERING 半开，无 handler = dry
    assert r is not None and r["dry"] is True
    assert r["pending"] == 2
    assert r["replayed"] == 0
    # dry 不消耗任务
    assert dlq.stats()["pending"] == 2


def test_recovered_replays_with_handler(dlq):
    dlq.enqueue("ok_kw", error="e1")
    dlq.enqueue("bad_kw", error="e2")

    def handler(kw, ctx):
        if kw == "bad_kw":
            raise RuntimeError("still failing")
        return kw

    r = maybe_replay_dlq("ramp_up", handler=handler, dlq=dlq)  # RECOVERED 恢复
    assert r["dry"] is False
    assert r["replayed"] == 1
    assert r["failed"] == 1
    assert r["pending"] == 1  # bad_kw 仍 pending（未超 max_attempts，不丢）


def test_empty_dlq_recovered(dlq):
    r = maybe_replay_dlq("ramp_up", handler=lambda kw, ctx: kw, dlq=dlq)
    assert r["replayed"] == 0 and r["pending"] == 0


def test_schedule_sleep_seconds():
    from collector_guard.schedule_adapter import schedule_sleep_seconds
    # NORMAL -> 1.0x
    assert schedule_sleep_seconds("schedule_normal", 6.0) == 6.0
    # ADAPTIVE -> 1.8x 降频
    assert schedule_sleep_seconds("backoff_interval", 6.0) == 10.8
    # COOLDOWN/FROZEN -> 深度降频
    assert schedule_sleep_seconds("pause_until_cooldown", 6.0) == 24.0
    assert schedule_sleep_seconds("freeze_and_recover", 6.0) == 30.0
    # None -> 默认 NORMAL 1x；下限保护
    assert schedule_sleep_seconds(None, 6.0) == 6.0
    assert schedule_sleep_seconds("schedule_normal", 0.1) >= 0.5
