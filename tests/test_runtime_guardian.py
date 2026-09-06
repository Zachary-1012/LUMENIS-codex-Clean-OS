import time

from collector_guard.dlq_replay import DeadLetterQueue
from collector_guard.queue_worker import collect_processor_factory
from collector_guard.runtime_guardian import RuntimeGuardian
from collector_guard.task_queue import TaskQueue


def test_runtime_guardian_records_lease_heartbeat_and_checkpoint(tmp_path):
    queue = TaskQueue(str(tmp_path / "tasks.db"))
    task_id = queue.enqueue("collect_keyword", {"keyword": "太古汇"})
    guardian = RuntimeGuardian(queue, lambda task: True, worker_id="worker-a",
                               audit_path=str(tmp_path / "audit.jsonl"))
    task = queue.dequeue(worker_id="worker-a", lease_owner="worker-a", run_id="run-1")
    assert task["id"] == task_id
    assert guardian.heartbeat(task_id) is True
    assert guardian.checkpoint(task_id, "page-2") is True
    row = queue.list_by_status("running")[0]
    assert row["worker_id"] == "worker-a"
    assert row["checkpoint_id"] == "page-2"


def test_runtime_guardian_reaps_stale_worker_and_audits_recovery(tmp_path):
    queue = TaskQueue(str(tmp_path / "tasks.db"), max_attempts=1)
    task_id = queue.enqueue("collect_keyword", {"keyword": "太古汇"})
    queue.dequeue(worker_id="dead-worker", lease_owner="dead-worker", run_id="run-dead")
    queue._conn.execute("UPDATE tasks SET last_heartbeat_at=? WHERE id=?", (time.time() - 60, task_id))
    queue._conn.commit()
    dlq = DeadLetterQueue(str(tmp_path / "dlq.jsonl"))
    audit = tmp_path / "audit.jsonl"
    guardian = RuntimeGuardian(queue, lambda task: True, heartbeat_timeout=1, dlq=dlq,
                               audit_path=str(audit))
    events = guardian.reap()
    assert events[0]["task_id"] == task_id
    assert events[0]["status"] == "DEAD_LETTER"
    assert queue.stats()["failed"] == 1
    assert dlq.stats()["pending"] == 1
    assert "STALE_WORKER_RECOVERED" in audit.read_text(encoding="utf-8")


def test_unknown_collect_task_is_not_acknowledged_as_success(tmp_path):
    queue = TaskQueue(str(tmp_path / "tasks.db"), max_attempts=1)
    queue.enqueue("unknown", {})
    guardian = RuntimeGuardian(queue, collect_processor_factory(lambda payload: True), worker_id="worker-a",
                               audit_path=str(tmp_path / "audit.jsonl"))
    assert guardian.process_once()[1] is False
    assert queue.stats()["failed"] == 1
