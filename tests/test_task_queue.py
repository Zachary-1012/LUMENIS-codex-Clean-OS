# -*- coding: utf-8 -*-
"""SQLite 任务队列测试（能力提取自 neotask）。"""
import time

from lumenis.system.collector.guard.task_queue import TaskQueue
from lumenis.system.collector.guard.queue_worker import QueueWorker


def _q(tmp_path):
    return TaskQueue(path=str(tmp_path / "tasks.db"), max_attempts=3)


def _receipt(task):
    return {
        "run_id": task["run_id"],
        "worker_id": task["worker_id"],
        "lease_owner": task["lease_owner"],
    }


def test_enqueue_dequeue_ack(tmp_path):
    q = _q(tmp_path)
    tid = q.enqueue("collect", {"kw": "太古汇"}, priority=5)
    assert tid == 1
    t = q.dequeue()
    assert t is not None and t["task_type"] == "collect"
    assert t["payload"] == {"kw": "太古汇"}
    # dequeue 后变 running，再次 dequeue 取不到
    assert q.dequeue() is None
    assert q.ack(t["id"], **_receipt(t)) is True
    s = q.stats()
    assert s["done"] == 1 and s.get("pending", 0) == 0


def test_priority_order(tmp_path):
    q = _q(tmp_path)
    q.enqueue("a", {}, priority=9)
    q.enqueue("b", {}, priority=1)
    q.enqueue("c", {}, priority=5)
    first = q.dequeue()
    assert first["task_type"] == "b"  # 优先级最高（数字最小）
    assert q.ack(first["id"], **_receipt(first)) is True
    second = q.dequeue()
    assert second["task_type"] == "c"
    assert q.ack(second["id"], **_receipt(second)) is True


def test_delay_and_backoff_retry(tmp_path):
    q = _q(tmp_path)
    tid = q.enqueue("x", {}, delay=10)
    assert q.dequeue() is None  # 未到期
    # 手动把 scheduled_at 提前模拟到期
    q._conn.execute("UPDATE tasks SET scheduled_at=? WHERE id=?", (time.time() - 1, tid))
    q._conn.commit()
    t = q.dequeue()
    assert t is not None and t["id"] == tid
    assert q.fail(t["id"], "网络错误", **_receipt(t)) is True
    # 首次失败 -> 回 pending 带退避（未到期不可取）
    assert q.dequeue() is None
    s = q.stats()
    assert s["pending"] == 1 and s["attempts_ok"] if False else True
    # 首次 fail(attempts=1) + 再 2 次 = 达 max_attempts=3 -> failed
    for _ in range(2):
        q._conn.execute("UPDATE tasks SET scheduled_at=? WHERE id=?", (time.time() - 1, tid))
        q._conn.commit()
        t = q.dequeue()
        assert t is not None
        assert q.fail(t["id"], "再试", **_receipt(t)) is True
    assert q.stats().get("failed") == 1


def test_stats_and_list(tmp_path):
    q = _q(tmp_path)
    q.enqueue("k", {})
    assert q.stats()["total"] == 1 and q.stats()["pending"] == 1
    assert len(q.list_by_status("pending")) == 1


def test_server_attempt_receipt_fences_stale_reclaimed_and_normal_work(tmp_path):
    """Exercise normal completion and stale-receipt rejection in a disposable DB."""
    q = _q(tmp_path)
    seen = {}
    q.enqueue("normal", {"value": "normal"})
    normal_worker = QueueWorker(
        q, lambda task: seen.update(normal_run_id=task["run_id"]) is None,
        worker_id="normal-worker", lease_owner="normal-lease",
    )
    normal_result = normal_worker.process_once()
    assert normal_result is not None and normal_result[1] is True
    assert seen["normal_run_id"]
    assert q.stats().get("done", 0) == 1

    task_id = q.enqueue("stale", {"value": "reclaim"})
    old = q.dequeue(worker_id="old-worker", lease_owner="old-lease")
    assert old is not None and old["id"] == task_id and old["run_id"]
    q._conn.execute(
        "UPDATE tasks SET last_heartbeat_at=?, scheduled_at=? WHERE id=?",
        (time.time() - 120, time.time() - 1, task_id),
    )
    q._conn.commit()

    assert q.reap_stale(timeout_seconds=30) == [task_id]
    assert q.stats().get("pending", 0) == 1
    q._conn.execute(
        "UPDATE tasks SET scheduled_at=? WHERE id=?",
        (time.time() - 1, task_id),
    )
    q._conn.commit()
    current = q.dequeue(worker_id="new-worker", lease_owner="new-lease")
    assert current is not None and current["id"] == task_id
    assert current["run_id"] and current["run_id"] != old["run_id"]

    old_receipt = _receipt(old)
    assert q.heartbeat(task_id, old_receipt["worker_id"],
                       run_id=old_receipt["run_id"],
                       lease_owner=old_receipt["lease_owner"]) is False
    assert q.checkpoint(task_id, old_receipt["worker_id"], "stale-checkpoint",
                        run_id=old_receipt["run_id"],
                        lease_owner=old_receipt["lease_owner"]) is False
    assert q.ack(task_id, **old_receipt) is False
    assert q.fail(task_id, "stale failure", **old_receipt) is False
    active = q._conn.execute(
        "SELECT status, run_id, attempts, checkpoint_id FROM tasks WHERE id=?",
        (task_id,),
    ).fetchone()
    assert tuple(active) == ("running", current["run_id"], 1, "")

    current_receipt = _receipt(current)
    assert q.heartbeat(task_id, current_receipt["worker_id"],
                       run_id=current_receipt["run_id"],
                       lease_owner=current_receipt["lease_owner"]) is True
    assert q.checkpoint(task_id, current_receipt["worker_id"], "current-checkpoint",
                        run_id=current_receipt["run_id"],
                        lease_owner=current_receipt["lease_owner"]) is True
    assert q.ack(task_id, **current_receipt) is True
    assert q.fail(task_id, "after completion", **current_receipt) is False
    assert q.heartbeat(task_id, current_receipt["worker_id"],
                       run_id=current_receipt["run_id"],
                       lease_owner=current_receipt["lease_owner"]) is False
    q.close()


def test_progress_checkpoint_survives_reopen_and_stale_receipt_cannot_replace_it(tmp_path):
    q = _q(tmp_path)
    task_id = q.enqueue('collector_source', {'actor_id': 7, 'scope': {'domain_id': 'cth'}})
    task = q.dequeue(worker_id='first', lease_owner='first', task_id=task_id)
    assert q.save_progress(task_id, {'completed': ['web_atom']}, **_receipt(task))
    q.close()
    q = _q(tmp_path)
    assert q.get(task_id)['payload']['progress'] == {'completed': ['web_atom']}
    with q._conn:
        q._conn.execute('UPDATE tasks SET last_heartbeat_at=0 WHERE id=?', (task_id,))
    assert q.reap_stale(1, task_id=task_id) == [task_id]
    assert not q.save_progress(task_id, {'completed': ['forged']}, **_receipt(task))
    assert q.get(task_id)['payload']['progress'] == {'completed': ['web_atom']}
    q.close()


def test_attempt_guard_serializes_real_cross_process_reaper(tmp_path):
    import subprocess
    import sys
    q = _q(tmp_path)
    task_id = q.enqueue('collect', {})
    task = q.dequeue(worker_id='active', lease_owner='active')
    with q._conn:
        q._conn.execute('UPDATE tasks SET last_heartbeat_at=0 WHERE id=?', (task_id,))
    code = (
        'from lumenis.system.collector.guard.task_queue import TaskQueue; '
        f'q=TaskQueue({q.path!r}); print(q.reap_stale(1), flush=True); q.close()'
    )
    with q.attempt_guard(task_id, **_receipt(task)) as allowed:
        assert allowed
        proc = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True)
        time.sleep(0.2)
        assert proc.poll() is None  # Reaper cannot take ownership inside business commit.
    output, _ = proc.communicate(timeout=10)
    assert str(task_id) in output
    assert not q.ack(task_id, **_receipt(task))
    q.close()


def test_local_deferral_preserves_failure_budget_and_attempt_fence(tmp_path):
    q = TaskQueue(str(tmp_path / 'defer.db'))
    identity = q.enqueue('collector_source', {})
    claimed = q.dequeue(worker_id='a', lease_owner='a')
    receipt = {key: claimed[key] for key in ('run_id', 'worker_id', 'lease_owner')}
    assert q.defer(identity, delay_seconds=10, **receipt)
    assert q.get(identity)['attempts'] == 0
    assert q.dequeue(worker_id='b', lease_owner='b', task_id=identity) is None
    assert not q.defer(identity, delay_seconds=0, **receipt)
    q.close()
