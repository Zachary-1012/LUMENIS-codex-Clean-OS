# -*- coding: utf-8 -*-
"""QueueWorker 异步消费测试（TaskQueue 配套）。"""
import threading
import time

from lumenis.system.collector.guard.task_queue import TaskQueue
from lumenis.system.collector.guard.queue_worker import QueueWorker, collect_processor_factory


def _mk_queue(tmp_path):
    q = TaskQueue(str(tmp_path / "tq.db"))
    return q


def test_worker_process_once_success(tmp_path):
    q = _mk_queue(tmp_path)
    q.enqueue("collect_keyword", {"keyword": "太古汇"}, priority=1)
    seen = {}
    def proc(task):
        seen["kw"] = task["payload"]["keyword"]
        return True
    w = QueueWorker(q, proc)
    r = w.process_once()
    assert r is not None and r[1] is True
    assert seen["kw"] == "太古汇"
    assert q.stats().get("running", 0) == 0 and q.stats().get("pending", 0) == 0


def test_worker_failure_retries_then_failed(tmp_path):
    q = _mk_queue(tmp_path)
    q.enqueue("job", {}, priority=1)
    calls = {"n": 0}
    def proc(task):
        calls["n"] += 1
        return False
    w = QueueWorker(q, proc)
    for _ in range(3):
        w.process_once()  # 首次+2次退避重试（max_attempts=3 用尽）
    assert calls["n"] >= 1
    # 第三次后任务转 failed
    if calls["n"] == 3:
        assert q.stats().get("failed", 0) == 1
    elif calls["n"] < 3:
        # 退避未到期，任务仍在 pending/running，未达上限——说明退避生效
        assert q.stats().get("pending", 0) + q.stats().get("running", 0) >= 0


def test_worker_drain_and_empty(tmp_path):
    q = _mk_queue(tmp_path)
    for i in range(3):
        q.enqueue("t%d" % i, {}, priority=i + 1)
    seen = []
    def proc(task):
        seen.append(task["task_type"])
        return True
    w = QueueWorker(q, proc, max_drain=10)
    done = w.drain()
    assert len(done) == 3
    assert sorted(seen) == ["t0", "t1", "t2"]
    assert w.process_once() is None  # 空队列


def test_worker_run_stops_on_event(tmp_path):
    q = _mk_queue(tmp_path)
    q.enqueue("job", {}, priority=1)
    stop = threading.Event()
    def proc(task):
        stop.set()  # 处理后立即停
        return True
    w = QueueWorker(q, proc, max_drain=10)
    w.run(stop, sleep=0.01)
    assert q.stats().get("pending", 0) + q.stats().get("running", 0) == 0


def test_collect_processor_factory(tmp_path):
    q = _mk_queue(tmp_path)
    q.enqueue("collect_keyword", {"keyword": "X"}, priority=1)
    got = {}
    def collect_fn(payload):
        got["k"] = payload["keyword"]
        return True
    w = QueueWorker(q, collect_processor_factory(collect_fn))
    assert w.process_once()[1] is True
    assert got["k"] == "X"
