# -*- coding: utf-8 -*-
"""DLQ+恢复重放 测试（研究自 baldur DLQ-replay 范式落地）。"""
import json
import os

import pytest

from collector_guard.dlq_replay import DeadLetterQueue


@pytest.fixture
def dlq(tmp_path):
    return DeadLetterQueue(path=str(tmp_path / "dlq.jsonl"), max_attempts=3)


def test_enqueue_and_pending(dlq):
    tid = dlq.enqueue("广州太古汇", error="security_page", context={"run": 1})
    assert tid
    pending = dlq.list_pending()
    assert len(pending) == 1
    assert pending[0]["keyword"] == "广州太古汇"
    assert pending[0]["status"] == "pending"


def test_business_rejection_not_enqueued(dlq):
    tid = dlq.enqueue("k", error="user_paused", is_business_rejection=True)
    assert tid is None
    assert dlq.list_pending() == []


def test_ack_marks_done(dlq):
    tid = dlq.enqueue("k", error="e")
    assert dlq.ack(tid) is True
    assert dlq.list_pending() == []
    assert dlq.stats()["done"] == 1
    assert dlq.stats()["pending"] == 0
    # 幂等：重复 ack 不重复计数
    assert dlq.ack(tid) is False


def test_fail_retry_dead_after_max(dlq):
    tid = dlq.enqueue("k", error="e")
    dlq.fail_retry(tid, "err1")
    dlq.fail_retry(tid, "err2")
    dlq.fail_retry(tid, "err3")  # 达 max_attempts=3
    assert dlq.list_pending() == []
    assert dlq.stats()["dead"] == 1
    assert dlq.stats()["pending"] == 0


def test_replay_success_and_failure(dlq):
    dlq.enqueue("ok_kw", error="e1")
    dlq.enqueue("bad_kw", error="e2")

    def handler(kw, ctx):
        if kw == "bad_kw":
            raise RuntimeError("still failing")
        return kw

    ok, fail = dlq.replay(handler)
    assert (ok, fail) == (1, 1)
    s = dlq.stats()
    assert s["done"] == 1
    # bad_kw 初始 attempts=1，一次重放失败 -> attempts=2 < max_attempts=3，仍 pending（不丢）
    assert s["dead"] == 0
    assert s["pending"] == 1


def test_persistence_across_instances(tmp_path):
    p = str(tmp_path / "dlq.jsonl")
    d1 = DeadLetterQueue(path=p)
    tid = d1.enqueue("持久化", error="e")
    d2 = DeadLetterQueue(path=p)
    assert len(d2.list_pending()) == 1
    assert d2.list_pending()[0]["task_id"] == tid


def test_stats_empty(dlq):
    assert dlq.stats() == {"total": 0, "pending": 0, "done": 0, "dead": 0}
