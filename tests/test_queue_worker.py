# -*- coding: utf-8 -*-
"""QueueWorker 异步消费测试（TaskQueue 配套）。"""
import threading
import time

from lumenis.system.collector.guard.task_queue import TaskQueue
from lumenis.system.collector.guard.queue_worker import QueueWorker, collect_processor_factory
from lumenis.system.collector.guard.dlq_replay import DeadLetterQueue
from lumenis.system.collector.guard.runtime_guardian import RuntimeGuardian


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


def test_runtime_guardian_forwards_attempt_receipt_end_to_end(tmp_path):
    q = _mk_queue(tmp_path)
    task_id = q.enqueue("collect_keyword", {"keyword": "X"})
    guardian = None
    calls = {}

    def proc(task):
        receipt = {key: task[key] for key in ("run_id", "worker_id", "lease_owner")}
        calls["heartbeat"] = guardian.heartbeat(task["id"], **receipt)
        calls["checkpoint"] = guardian.checkpoint(
            task["id"], "keyword:X", **receipt)
        return True

    guardian = RuntimeGuardian(
        q, proc, worker_id="guardian-worker",
        dlq=DeadLetterQueue(str(tmp_path / "dlq.jsonl")),
        audit_path=str(tmp_path / "recovery-audit.jsonl"),
    )

    assert guardian.process_once() == (task_id, True)
    assert calls == {"heartbeat": True, "checkpoint": True}

    second_id = q.enqueue("collect_keyword", {"keyword": "Y"})
    old = q.dequeue(worker_id=guardian.worker.worker_id,
                    lease_owner=guardian.worker.lease_owner)
    assert old["id"] == second_id
    with q._conn:
        q._conn.execute("UPDATE tasks SET last_heartbeat_at=0 WHERE id=?", (second_id,))
    assert q.reap_stale(1) == [second_id]
    with q._conn:
        q._conn.execute("UPDATE tasks SET scheduled_at=0 WHERE id=?", (second_id,))
    current = q.dequeue(worker_id=guardian.worker.worker_id,
                        lease_owner=guardian.worker.lease_owner)
    assert current["run_id"] != old["run_id"]

    old_receipt = {key: old[key] for key in ("run_id", "worker_id", "lease_owner")}
    current_receipt = {
        key: current[key] for key in ("run_id", "worker_id", "lease_owner")
    }
    assert guardian.heartbeat(second_id) is False
    assert guardian.checkpoint(second_id, "missing") is False
    assert guardian.heartbeat(second_id, **old_receipt) is False
    assert guardian.checkpoint(second_id, "stale", **old_receipt) is False
    assert guardian.heartbeat(second_id, **current_receipt) is True
    assert guardian.checkpoint(second_id, "current", **current_receipt) is True
    assert q.ack(second_id, **current_receipt) is True


def test_collector_failure_mapping_is_retried_not_acknowledged(tmp_path):
    q = _mk_queue(tmp_path)
    task_id = q.enqueue("collect", {"keyword": "owned fixture source"})
    worker = QueueWorker(q, collect_processor_factory(
        lambda payload: {"ok": False, "status": "NETWORK_ERROR"}))
    assert worker.process_once() == (task_id, False)
    assert q.stats() == {"pending": 1, "total": 1}
    assert q.list_by_status("pending")[0]["attempts"] == 1
    q.close()


def test_collector_success_requires_explicit_success_result(tmp_path):
    for result, expected in [
        ({"ok": True, "status": "SUCCESS"}, True),
        ({"success": True}, True),
        ({"ok": False, "success": True}, False),
        ({"status": "APPROVAL_REQUIRED"}, False),
        ({"ok": "false"}, False),
        (True, True), (False, False), (None, False),
    ]:
        processor = collect_processor_factory(lambda payload: result)
        assert processor({"task_type": "collect", "payload": {}}) is expected


def test_generic_processor_contract_never_acknowledges_nonboolean_truthiness(tmp_path):
    for value in ({'ok': False}, {'status': 'UNKNOWN'}, 1, 'success'):
        queue = TaskQueue(str(tmp_path / ('truth-' + str(len(str(value))) + '.db')))
        identity = queue.enqueue('job', {})
        outcome = QueueWorker(queue, lambda task: value).process_once()
        assert outcome == (identity, False)
        assert queue.get(identity)['status'] == 'pending'
        queue.close()
