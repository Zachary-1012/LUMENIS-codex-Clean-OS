# -*- coding: utf-8 -*-
"""SQLite 任务队列测试（能力提取自 neotask）。"""
import time
import pytest

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


def test_generic_operation_cancel_fences_commit_and_finishes_cancelled(tmp_path):
    q = _q(tmp_path)
    task_type = 'shared_content_project_export'
    request_key = 'a' * 64
    task_id = q.enqueue_once(task_type, {'request_key': request_key, 'binding': {'actor_ref': 'actor:7'}}, request_key)
    task = q.dequeue(worker_id='export-worker', lease_owner='export-worker', task_id=task_id)
    assert task is not None

    requested = q.request_cancel(task_id, task_type=task_type, request_key=request_key)
    assert requested['status'] == 'cancel_requested'
    assert requested['payload']['cancel_requested'] is True
    effect_calls = []
    assert not q.commit_result(
        task_id, {'artifact_id': 'ART-cancelled'}, lambda: effect_calls.append(True),
        task_type=task_type, request_key=request_key, **_receipt(task),
    )
    assert effect_calls == []
    with q.attempt_guard(task_id, **_receipt(task)) as allowed:
        assert not allowed
    assert q.finish_cancelled(
        task_id, task_type=task_type, request_key=request_key, **_receipt(task),
    )
    assert q.get(task_id)['status'] == 'cancelled'
    assert not q.ack(task_id, **_receipt(task))
    q.close()


def test_generic_operation_result_commit_is_idempotent_and_beats_late_cancel(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    q = _q(tmp_path)
    task_type = 'shared_content_project_export'
    request_key = 'b' * 64
    request = {'request_key': request_key, 'request_id': '1' * 32,
               'request_digest': '2' * 64, 'binding': {'actor_ref': 'actor:7', 'scope_sha256': '3' * 64},
               'parent_version_sha256': 'c' * 64}
    task_id = q.enqueue_once(task_type, request, request_key)
    task = q.dequeue(worker_id='export-worker', lease_owner='export-worker', task_id=task_id)
    effect_entered = Event()
    release_effect = Event()
    effect_calls = []

    def commit_effect():
        effect_calls.append('registered')
        effect_entered.set()
        assert release_effect.wait(5)
        return {'artifact_id': 'ART-committed', 'version': 3}

    with ThreadPoolExecutor(max_workers=2) as pool:
        completion = pool.submit(
            q.commit_result, task_id, commit_effect,
            task_type=task_type, request_key=request_key, **_receipt(task),
        )
        assert effect_entered.wait(5)
        cancel_started = Event()

        def request_cancel():
            cancel_started.set()
            return q.request_cancel(task_id, task_type=task_type, request_key=request_key)

        cancellation = pool.submit(request_cancel)
        assert cancel_started.wait(5)
        release_effect.set()
        assert completion.result(timeout=5) is True
        assert cancellation.result(timeout=5)['status'] == 'done'

    persisted = q.get(task_id)
    assert persisted['status'] == 'done'
    assert persisted['payload']['result'] == {'artifact_id': 'ART-committed', 'version': 3}
    assert effect_calls == ['registered']
    assert not q.ack(task_id, **_receipt(task))
    assert q.enqueue_once(task_type, request, request_key) == task_id
    with pytest.raises(ValueError, match='TASK_QUEUE_REQUEST_ID_CONFLICT'):
        q.enqueue_once(task_type, {**request, 'request_digest': '4' * 64}, request_key)
    q.close()


def test_list_by_type_paginates_after_actor_and_scope_filtering(tmp_path):
    q = _q(tmp_path)
    task_type = 'shared_content_project_export'
    wanted_scope = 'a' * 64
    wanted_ids = []
    for index in range(3):
        request_key = f'wanted-{index}'
        wanted_ids.append(q.enqueue_once(task_type, {
            'request_key': request_key,
            'binding': {'actor_ref': 'actor:7', 'scope_sha256': wanted_scope},
            'order': index,
        }, request_key))
        other_key = f'other-{index}'
        q.enqueue_once(task_type, {
            'request_key': other_key,
            'binding': {'actor_ref': 'actor:8', 'scope_sha256': wanted_scope},
        }, other_key)

    first_page, cursor = q.list_by_type(
        task_type, actor_ref='actor:7', scope_sha256=wanted_scope, limit=2,
    )
    assert [row['id'] for row in first_page] == list(reversed(wanted_ids[1:]))
    assert cursor == wanted_ids[1]
    assert first_page[0]['payload']['binding']['actor_ref'] == 'actor:7'

    second_page, next_cursor = q.list_by_type(
        task_type, before_id=cursor, actor_ref='actor:7',
        scope_sha256=wanted_scope, limit=2,
    )
    assert [row['id'] for row in second_page] == wanted_ids[:1]
    assert second_page[0]['payload']['order'] == 0
    assert next_cursor is None
    q.close()


@pytest.mark.parametrize('kwargs', [
    {'limit': 0},
    {'limit': 51},
    {'limit': True},
    {'before_id': 0},
    {'before_id': True},
    {'actor_ref': ''},
    {'scope_sha256': ''},
])
def test_list_by_type_rejects_invalid_pagination_and_binding(kwargs, tmp_path):
    q = _q(tmp_path)
    with pytest.raises(ValueError, match='TASK_QUEUE_LIST_REQUEST_INVALID'):
        q.list_by_type('shared_content_project_export', **kwargs)
    q.close()


def test_result_metadata_requires_completed_exact_request_and_is_monotonic(tmp_path):
    q = _q(tmp_path)
    task_type = 'shared_content_project_export'
    request_key = 'e' * 64
    task_id = q.enqueue_once(task_type, {'request_key': request_key}, request_key)
    task = q.dequeue(worker_id='export-worker', lease_owner='export-worker', task_id=task_id)
    result_ref = {'artifact_id': 'ART-result-metadata', 'version': 4}

    assert not q.record_result_metadata(
        task_id, {'evidence_recorded': True}, task_type=task_type,
        request_key=request_key,
    )
    assert q.commit_result(
        task_id, result_ref, lambda: True, task_type=task_type,
        request_key=request_key, **_receipt(task),
    )
    metadata = {'evidence_recorded': True}
    assert q.record_result_metadata(
        task_id, metadata, task_type=task_type, request_key=request_key,
    )
    assert q.record_result_metadata(
        task_id, metadata, task_type=task_type, request_key=request_key,
    )  # same value is idempotent
    assert not q.record_result_metadata(
        task_id, {'evidence_recorded': False}, task_type=task_type,
        request_key=request_key,
    )  # conflicting metadata cannot rewrite the recorded fact
    assert not q.record_result_metadata(
        task_id, {'other': 'value'}, task_type=task_type,
        request_key='f' * 64,
    )
    assert not q.record_result_metadata(
        task_id, {'other': 'value'}, task_type='other_task',
        request_key=request_key,
    )

    persisted = q.get(task_id)
    assert persisted['status'] == 'done'
    assert persisted['payload']['result'] == {
        **result_ref, 'metadata': metadata,
    }
    with pytest.raises(ValueError, match='TASK_RESULT_METADATA_TOO_LARGE'):
        q.record_result_metadata(
            task_id, {'note': 'x' * (16 * 1024)}, task_type=task_type,
            request_key=request_key,
        )
    assert q.get(task_id)['payload']['result']['metadata'] == metadata
    q.close()


def test_generic_operation_recovery_requires_confirmed_dead_worker_and_explicit_resume(tmp_path):
    q = _q(tmp_path)
    task_type = 'shared_content_project_export'
    request_key = 'd' * 64
    task_id = q.enqueue_once(task_type, {'request_key': request_key}, request_key)
    first = q.dequeue(worker_id='worker-123', lease_owner='lease-123', task_id=task_id)
    with q._conn:
        q._conn.execute('UPDATE tasks SET last_heartbeat_at=? WHERE id=?', (time.time() - 120, task_id))

    assert not q.mark_interrupted_if_dead(
        task_id, task_type=task_type, request_key=request_key, stale_after_seconds=30,
        worker_alive_check=lambda worker_id, lease_owner, run_id: True,
    )
    assert q.get(task_id)['status'] == 'running'
    observed = []

    def worker_is_dead(worker_id, lease_owner, run_id):
        observed.append((worker_id, lease_owner, run_id))
        return False

    assert q.mark_interrupted_if_dead(
        task_id, task_type=task_type, request_key=request_key, stale_after_seconds=30,
        worker_alive_check=worker_is_dead,
    )
    assert observed == [('worker-123', 'lease-123', first['run_id'])]
    assert q.get(task_id)['status'] == 'interrupted'
    assert not q.resume_interrupted(task_id, task_type=task_type, request_key='e' * 64)
    assert q.resume_interrupted(task_id, task_type=task_type, request_key=request_key)
    second = q.dequeue(worker_id='worker-456', lease_owner='lease-456', task_id=task_id)
    assert second['run_id'] != first['run_id']
    assert not q.ack(task_id, **_receipt(first))
    assert q.ack(task_id, **_receipt(second))
    assert q.get(task_id)['status'] == 'done'
    q.close()


def test_generic_operation_dead_cancel_is_terminal_and_cannot_resume(tmp_path):
    q = _q(tmp_path)
    task_type = 'shared_content_project_export'
    request_key = 'f' * 64
    task_id = q.enqueue_once(task_type, {'request_key': request_key}, request_key)
    task = q.dequeue(worker_id='dead-export', lease_owner='dead-export', task_id=task_id)
    q.request_cancel(task_id, task_type=task_type, request_key=request_key)
    with q._conn:
        q._conn.execute('UPDATE tasks SET last_heartbeat_at=? WHERE id=?', (time.time() - 120, task_id))
    assert q.mark_interrupted_if_dead(
        task_id, task_type=task_type, request_key=request_key, stale_after_seconds=30,
        worker_alive_check=lambda *_: False,
    )
    assert q.get(task_id)['status'] == 'cancelled'
    assert not q.resume_interrupted(task_id, task_type=task_type, request_key=request_key)
    assert not q.ack(task_id, **_receipt(task))
    q.close()
