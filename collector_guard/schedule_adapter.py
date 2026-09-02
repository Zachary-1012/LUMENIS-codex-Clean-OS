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
