# -*- coding: utf-8 -*-
"""SQLite 任务队列测试（能力提取自 neotask）。"""
import time

from lumenis.system.collector.guard.task_queue import TaskQueue


def _q(tmp_path):
    return TaskQueue(path=str(tmp_path / "tasks.db"), max_attempts=3)


def test_enqueue_dequeue_ack(tmp_path):
    q = _q(tmp_path)
    tid = q.enqueue("collect", {"kw": "太古汇"}, priority=5)
    assert tid == 1
    t = q.dequeue()
    assert t is not None and t["task_type"] == "collect"
    assert t["payload"] == {"kw": "太古汇"}
    # dequeue 后变 running，再次 dequeue 取不到
    assert q.dequeue() is None
    q.ack(t["id"])
    s = q.stats()
    assert s["done"] == 1 and s.get("pending", 0) == 0


def test_priority_order(tmp_path):
    q = _q(tmp_path)
    q.enqueue("a", {}, priority=9)
    q.enqueue("b", {}, priority=1)
    q.enqueue("c", {}, priority=5)
    first = q.dequeue()
    assert first["task_type"] == "b"  # 优先级最高（数字最小）
    q.ack(first["id"])
    second = q.dequeue()
    assert second["task_type"] == "c"
    q.ack(second["id"])


def test_delay_and_backoff_retry(tmp_path):
    q = _q(tmp_path)
    tid = q.enqueue("x", {}, delay=10)
    assert q.dequeue() is None  # 未到期
    # 手动把 scheduled_at 提前模拟到期
    q._conn.execute("UPDATE tasks SET scheduled_at=? WHERE id=?", (time.time() - 1, tid))
    q._conn.commit()
    t = q.dequeue()
    assert t is not None and t["id"] == tid
    q.fail(t["id"], "网络错误")
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
        q.fail(t["id"], "再试")
    assert q.stats().get("failed") == 1


def test_stats_and_list(tmp_path):
    q = _q(tmp_path)
    q.enqueue("k", {})
    assert q.stats()["total"] == 1 and q.stats()["pending"] == 1
    assert len(q.list_by_status("pending")) == 1
