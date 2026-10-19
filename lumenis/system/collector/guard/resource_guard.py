# -*- coding: utf-8 -*-
"""ResourceGuard（P0-G｜Maximum Efficiency Mode 统一资源守卫层）。

把 RiskEngine 的宏观六态 lifecycle_action 消费为「效率-保护」四态调度建议，
并叠加系统资源指标（CPU/RAM/Queue Lag）做 Backpressure→Recovery 保护，防止系统跑崩。

四态：
  NORMAL            常规满载调度
  HIGH-EFFICIENCY   资源充足时提升并发/吞吐（不超安全阈值）
  RESOURCE-GUARDED  熔断联动或资源超阈值 → 降并发、拉长间隔、排队/背压
  RECOVERY          正在恢复（半开/冷却结束）→ 逐步回满，观察窗口内保持警惕

映射（lifecycle_action → 四态）：
  schedule_normal   -> NORMAL（资源充足时可升级 HIGH-EFFICIENCY）
  backoff_interval  -> HIGH-EFFICIENCY（适度并行，靠间隔拉长控压）
  pause_until_cooldown / freeze_and_recover -> RESOURCE-GUARDED
  probe_only        -> RESOURCE-GUARDED（仅放单探测）
  ramp_up           -> RECOVERY

资源保护：CPU/RAM/QueueLag 超过阈值时，无论 lifecycle 为何，强制 RESOURCE-GUARDED。
纯函数式 + 可注入指标，便于单测；不持有线程，无共享状态。

用法：
  guard = ResourceGuard()
  decision = guard.decide(lifecycle_action='backoff_interval', cpu_pct=70, ram_pct=80, queue_lag=150)
"""
from typing import Dict, Optional
import math

# 四态
NORMAL = "NORMAL"
HIGH_EFFICIENCY = "HIGH-EFFICIENCY"
RESOURCE_GUARDED = "RESOURCE-GUARDED"
RECOVERY = "RECOVERY"

# lifecycle_action -> (四态, worker_scale, interval_multiplier, queue_policy)
_ACTION_TABLE = {
    "schedule_normal": (NORMAL, 1.0, 1.0, "drain"),
    "backoff_interval": (HIGH_EFFICIENCY, 0.7, 1.8, "drain"),
    "pause_until_cooldown": (RESOURCE_GUARDED, 0.3, 4.0, "backpressure"),
    "freeze_and_recover": (RESOURCE_GUARDED, 0.2, 5.0, "queue"),
    "probe_only": (RESOURCE_GUARDED, 0.1, 5.0, "probe_only"),
    "ramp_up": (RECOVERY, 0.6, 1.4, "drain"),
}


class ResourceGuard:
    def __init__(self, cpu_high: float = 80.0, ram_high: float = 85.0,
                 queue_lag_high: int = 200, max_worker_scale: float = 1.1,
                 probe_worker_scale: float = 0.1):
        self.cpu_high = cpu_high
        self.ram_high = ram_high
        self.queue_lag_high = queue_lag_high
        self.max_worker_scale = max_worker_scale  # HIGH-EFFICIENCY 上限，绝不无上限并发
        self.probe_worker_scale = probe_worker_scale

    def _resources_exceeded(self, cpu_pct, ram_pct, queue_lag) -> Optional[str]:
        if cpu_pct is not None and cpu_pct >= self.cpu_high:
            return f"cpu={cpu_pct:.0f}%>={self.cpu_high:.0f}%"
        if ram_pct is not None and ram_pct >= self.ram_high:
            return f"ram={ram_pct:.0f}%>={self.ram_high:.0f}%"
        if queue_lag is not None and queue_lag >= self.queue_lag_high:
            return f"queue_lag={queue_lag}>={self.queue_lag_high}"
        return None

    def decide(self, lifecycle_action: str = "schedule_normal",
               cpu_pct: Optional[float] = None, ram_pct: Optional[float] = None,
               queue_lag: Optional[int] = None) -> Dict:
        known_action = isinstance(lifecycle_action, str) and lifecycle_action in _ACTION_TABLE
        state, wscale, imult, qpol = _ACTION_TABLE.get(
            lifecycle_action if known_action else "freeze_and_recover")
        def valid(value, maximum=None):
            return (type(value) in (int, float) and value >= 0
                    and (maximum is None or value <= maximum) and math.isfinite(value))
        metrics_valid = (valid(cpu_pct, 100), valid(ram_pct, 100),
                         type(queue_lag) is int and queue_lag >= 0)
        observed = all(metrics_valid)
        cpu_pct = cpu_pct if metrics_valid[0] else None
        ram_pct = ram_pct if metrics_valid[1] else None
        queue_lag = queue_lag if metrics_valid[2] else None
        reason = f"lifecycle={lifecycle_action}"

        if not known_action:
            reason += " + unknown_lifecycle"
        if not observed:
            reason += " + resource_observation_incomplete"
            if state == HIGH_EFFICIENCY:
                state = NORMAL

        exceeded = self._resources_exceeded(cpu_pct, ram_pct, queue_lag)
        if exceeded:
            # 资源超阈值：无论 lifecycle 如何，强制保护（但 probe_only 仍保留最小探测）
            state = RESOURCE_GUARDED
            if qpol == "probe_only":
                wscale = self.probe_worker_scale
            else:
                wscale = min(wscale, 0.3)
                imult = max(imult, 3.0)
                if qpol not in {"queue", "probe_only"}:
                    qpol = "backpressure"
            reason += f" + resource_guard({exceeded})"

        # HIGH-EFFICIENCY：资源充足才允许接近满载的更高并发，且有上限
        if state == NORMAL and observed and known_action:
            state = HIGH_EFFICIENCY
            wscale = min(self.max_worker_scale, 1.1)
            reason += " -> high_efficiency"
        elif state == HIGH_EFFICIENCY and wscale < 0.7:
            wscale = 0.7  # 高效应至少保持适度并行

        return {
            "state": state,
            "worker_scale": round(wscale, 2),
            "interval_multiplier": round(imult, 2),
            "queue_policy": qpol,
            "allow_new": qpol in ("drain", "backpressure"),
            "reason": reason,
            "resource_observation_complete": observed,
        }

    def snapshot(self, lifecycle_action: str = "schedule_normal",
                 cpu_pct: Optional[float] = None, ram_pct: Optional[float] = None,
                 queue_lag: Optional[int] = None) -> Dict:
        d = self.decide(lifecycle_action, cpu_pct, ram_pct, queue_lag)
        return {
            "lifecycle_action": lifecycle_action,
            "resource_guard_state": d["state"],
            "resource_guard_decision": d,
            "thresholds": {"cpu_high": self.cpu_high, "ram_high": self.ram_high,
                           "queue_lag_high": self.queue_lag_high},
        }
