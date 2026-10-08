# -*- coding: utf-8 -*-
"""异步任务消费 Worker（TaskQueue 配套，对齐基线 §10 Scheduler/Queue/Worker 的 Worker 层）。

通用消费循环：从 TaskQueue dequeue 到期任务 → 执行 processor → ack/fail（指数退避重试由
task_queue.fail 内置）。采集/事件分析/报告生成等批量任务可入队后由此 Worker 异步消费，
与同步采集互补；生产接入可按 collector 任务类型注册 processor。

用法：
  from lumenis.system.collector.guard.task_queue import TaskQueue
  from lumenis.system.collector.guard.queue_worker import QueueWorker

  def proc(task):
      print(task["task_type"], task["payload"])
      return True

  w = QueueWorker(TaskQueue("data/task_queue.db"), proc)
  w.process_once()          # 单步（测试/定时器）
  w.run(stop_event, sleep=1.0)   # 常驻循环（stop_event 触发退出）
"""
import threading
import time
import uuid


class QueueWorker:
    def __init__(self, queue, processor, max_drain=10, worker_id=None, lease_owner=None):
        self.queue = queue
        self.processor = processor  # fn(task) -> bool（True=成功 ack；False/异常= fail 退避重试）
        self.max_drain = max_drain  # 单轮最多消费数（防长时间独占）
        self.worker_id = worker_id or "worker-" + uuid.uuid4().hex[:12]
        self.lease_owner = lease_owner or self.worker_id

    def process_once(self):
        """消费一个到期任务：成功 ack，失败 fail（task_queue 内部指数退避+上限转 failed）。
        无任务返回 None；有任务返回 (task_id, ok)。"""
        task = self.queue.dequeue(worker_id=self.worker_id, lease_owner=self.lease_owner)
        if task is None:
            return None
        task_id = task["id"]
        # Capture the server-issued attempt receipt before handing the mutable
        # task dict to processor code.
        receipt = {
            "run_id": task.get("run_id"),
            "worker_id": self.worker_id,
            "lease_owner": self.lease_owner,
        }
        if not self.queue.heartbeat(
            task_id, self.worker_id, run_id=receipt["run_id"],
            lease_owner=receipt["lease_owner"],
        ):
            return (task_id, False)
        try:
            ok = self.processor(task)
        except Exception:
            ok = False
        if ok:
            ok = self.queue.ack(task_id, **receipt)
        else:
            self.queue.fail(task_id, error="worker processor failed", **receipt)
        return (task_id, ok)

    def drain(self):
        """尽力消费所有到期任务（最多 max_drain 个）。"""
        done, i = [], 0
        while i < self.max_drain:
            r = self.process_once()
            if r is None:
                break
            done.append(r)
            i += 1
        return done

    def run(self, stop_event=None, sleep=1.0):
        """常驻循环：消费到期任务，空队列 sleep。stop_event 置位即优雅退出。"""
        stop = stop_event if stop_event is not None else threading.Event()
        while not stop.is_set():
            if self.process_once() is None:
                stop.wait(sleep)
        return self.queue.stats()


def collect_processor_factory(collect_fn):
    """采集任务 processor 工厂：task_type 为 collect/collect_keyword 时调用 collect_fn(payload)。

    collect_fn(payload) 返回 True=成功（ack）；抛异常/False=fail 自动退避重试。
    与 collector 同步采集互补：调度器入队关键词采集任务，Worker 异步消费。"""
    def processor(task):
        tt = task.get("task_type", "")
        if tt in ("collect", "collect_keyword"):
            payload = task.get("payload") or {}
            return bool(collect_fn(payload))
        return False  # Unknown work must use the failure/recovery path, never fake success.
    return processor
