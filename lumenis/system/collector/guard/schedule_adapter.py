# -*- coding: utf-8 -*-
"""ScheduleAdapter（P1-A｜六态联动调度器接入层）。

把 RiskEngine 的宏观六态 lifecycle_action（NORMAL/ADAPTIVE/COOLDOWN/FROZEN/RECOVERING/RECOVERED
-> schedule_normal/backoff_interval/pause_until_cooldown/freeze_and_recover/probe_only/ramp_up）
真正消费为采集调度的"停止/放行/降频"决策，联动 Scheduler/Worker/Queue。

三层分工（采集稳定性，基线 §9/§10）：
  CollectorGuard   网络层守卫（should_stop / 重试 / 回退）
  RiskEngine       连续风险分 + 六态熔断（snapshot.lifecycle_action）
  ResourceGuard   资源/效率层四态（本层消费 lifecycle_action，叠加 CPU/RAM/QueueLag 保护）

本层只做确定性裁决，无共享状态，纯函数式，便于测试。

用法：
  from collector_guard.schedule_adapter import should_stop_schedule, advice
  if should_stop_schedule(lifecycle_action):   # cooldown/freeze -> True（停止后续请求）
      ...
"""
from collector_guard.resource_guard import RESOURCE_GUARDED, ResourceGuard

_GUARD = ResourceGuard()

# 六态动作 -> 是否应停止后续采集请求
#   pause_until_cooldown(COOLDOWN) / freeze_and_recover(FROZEN) -> 停止（任务进 Queue 等待）
#   probe_only(RECOVERING) -> 放行单次探测（不停止）
#   backoff_interval(ADAPTIVE) / ramp_up(RECOVERED) / schedule_normal(NORMAL) -> 不停止
_STOP_ACTIONS = {"pause_until_cooldown", "freeze_and_recover"}
_PROBE_ACTION = "probe_only"


def advice(lifecycle_action="schedule_normal", cpu_pct=None, ram_pct=None, queue_lag=0):
    """返回调度建议（ResourceGuard 四态 + 是否停止 + 排队策略）。"""
    d = _GUARD.decide(lifecycle_action, cpu_pct, ram_pct, queue_lag)
    action = lifecycle_action or "schedule_normal"
    stop = action in _STOP_ACTIONS or (
        d["state"] == RESOURCE_GUARDED and d["queue_policy"] in ("backpressure", "queue"))
    if action == _PROBE_ACTION:
        stop = False  # 半开探测放行
    return {
        "lifecycle_action": action,
        "resource_guard_state": d["state"],
        "worker_scale": d["worker_scale"],
        "interval_multiplier": d["interval_multiplier"],
        "queue_policy": d["queue_policy"],
        "allow_new": d["allow_new"] and not stop,
        "should_stop": stop,
    }


def should_stop_schedule(lifecycle_action):
    """六态 -> 是否停止后续采集请求（cooldown/freeze 停止；probe 放行）。"""
    if not lifecycle_action:
        return False
    return advice(lifecycle_action)["should_stop"]


def schedule_state(lifecycle_action):
    """六态 -> ResourceGuard 四态字符串（监控/日志用）。"""
    return advice(lifecycle_action)["resource_guard_state"]


def schedule_sleep_seconds(lifecycle_action=None, base_interval=6.0):
    """动态调度间隔（生产接线）：base × interval_multiplier（ResourceGuard 降频/恢复语义）。

    - schedule_normal(NORMAL)          -> 1.0x（常规频率）
    - backoff_interval(ADAPTIVE)       -> 1.8x（间隔拉长控压，降低采集频率）
    - pause_until_cooldown(COOLDOWN)   -> 4.0x（深度降频，配合 should_stop 排队）
    - freeze_and_recover(FROZEN)       -> 5.0x（冻结深度降频）
    纯函数、无共享状态，供采集主循环在关键词间动态 sleep，服务基线 §9/§10「动态熔断联动」。
    """
    mult = advice(lifecycle_action or "schedule_normal")["interval_multiplier"]
    return max(0.5, float(base_interval) * float(mult))


# DLQ 恢复重放触发态：RECOVERING(probe_only 半开) / RECOVERED(ramp_up 恢复) 后才补采失败任务
_REPLAY_ACTIONS = {"probe_only", "ramp_up"}


def maybe_replay_dlq(lifecycle_action, handler=None, dlq=None, max_items=50):
    """恢复期自动触发 DLQ 失败任务重放（生产接线点，供采集调度在 RECOVERING/RECOVERED 调用）。

    - 非恢复态（NORMAL/ADAPTIVE/COOLDOWN/FROZEN）返回 None，不触发。
    - handler 为空：dry 模式，返回待重放 pending 数量（供调度决策/监控），不实际重放。
    - handler 提供：实际重放，返回 replayed/failed/pending_after。
    - 对齐 baldur 范式：只重放基础设施类失败；业务拒绝永不入队（已在 dlq_replay 保证）。
    """
    if lifecycle_action not in _REPLAY_ACTIONS:
        return None
    if dlq is None:
        from collector_guard.dlq_replay import DeadLetterQueue
        dlq = DeadLetterQueue()
    if handler is None:
        pending = dlq.list_pending()[:max_items]
        return {"replayed": 0, "failed": 0, "pending": len(pending), "dry": True}
    ok, fail = dlq.replay(handler, max_items=max_items)
    return {"replayed": ok, "failed": fail, "pending": dlq.stats()["pending"], "dry": False}


def enqueue_next_round(queue, tasks, priority=5, delay=0):
    """采集调度生产接线：把下一轮采集任务入队（异步生产路径，默认与同步采集互补）。

    tasks: [{task_type, payload}, ...]；入队失败异常向上抛（由调用方决定降级为同步）。
    与 TaskQueue + QueueWorker 构成「Scheduler -> Queue -> Worker」可选异步链路；
    不改变现有同步调度（collect_all），生产接入时按 collect 任务类型注册 processor。
    """
    for t in tasks:
        queue.enqueue(t.get("task_type", "collect"),
                      t.get("payload", {}),
                      priority=t.get("priority", priority),
                      delay=t.get("delay", delay))
    return len(tasks)
