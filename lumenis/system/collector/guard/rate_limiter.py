# -*- coding: utf-8 -*-
"""AdaptiveRateLimiter：动态限速（不硬编码固定频率）。

策略（对应健康→降频→延长冷却→熔断→健康检查→逐步恢复）：
- 成功：间隔 ×0.9 向最小间隔逐步恢复（不低于 min_interval）。
- 失败：间隔 ×2 指数退避，最高封顶 base × MAX_BACKOFF_FACTOR(16)。
- 连续失败达到阈值（默认 3）：进入冷却 cooldown_seconds（默认随失败次数增长，封顶 30min）。
- 冷却期内 wait() 会阻塞到可试探；冷却结束先放行一次“健康检查”，成功才继续恢复。
线程安全；数值可由 env / 构造参数覆盖，历史 30min/20min/9 次等仅作初始参考，不是永久真理。
"""
import os
import math
import random
import threading
import time
from .state import CollectState


class AdaptiveRateLimiter:
    MAX_BACKOFF_FACTOR = 16

    def __init__(self, base_interval=None, min_interval=None, max_interval=None,
                 fail_threshold=3, cooldown_seconds=600, enabled=True, jitter=True):
        self.base_interval = float(base_interval if base_interval is not None
                                   else os.getenv('GUARD_BASE_INTERVAL', '20'))
        self.min_interval = float(min_interval if min_interval is not None
                                  else os.getenv('GUARD_MIN_INTERVAL', '8'))
        self.max_interval = float(max_interval if max_interval is not None
                                  else self.base_interval * self.MAX_BACKOFF_FACTOR)
        self.fail_threshold = int(fail_threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self.enabled = enabled
        self.jitter = bool(jitter)
        self._lock = threading.RLock()
        self.interval = self.base_interval
        self.consecutive_fail = 0
        self.cooldown_until = 0.0
        self._server_not_before = 0.0
        self._server_not_before_monotonic = 0.0
        self._next_slot_monotonic = 0.0
        self._last_release_monotonic = None
        self._local_not_before_monotonic = 0.0
        self.state = CollectState.HEALTHY
        self.last_state_change = time.time()

    # ---- 内部状态更新 ----
    def on_success(self):
        if not self.enabled:
            return CollectState.HEALTHY
        with self._lock:
            if self.remaining_cooldown() > 0:
                return self.state  # A sibling success cannot cancel an active pause.
            self.consecutive_fail = 0
            # 逐步恢复：每次成功向 min 收敛 10%
            self.interval = max(self.min_interval, self.interval * 0.9)
            if self.state in (CollectState.COOLDOWN, CollectState.WARNING, CollectState.PAUSED):
                self._set_state(CollectState.HEALTHY)
            self.cooldown_until = 0.0
            return self.state

    def on_failure(self, force_cooldown=False, retry_after=None):
        if not self.enabled:
            return self.state
        with self._lock:
            # A real server deadline applies even before the local failure threshold.
            if retry_after is not None:
                try:
                    seconds = float(retry_after)
                    if math.isfinite(seconds) and seconds > 0:
                        self._server_not_before = max(self._server_not_before, time.time() + seconds)
                        self._server_not_before_monotonic = max(self._server_not_before_monotonic, time.monotonic() + seconds)
                except (TypeError, ValueError):
                    pass
            self.consecutive_fail += 1
            self.interval = min(self.max_interval, max(self.interval * 2, self.base_interval * 2 ** 0))
            if force_cooldown or self.consecutive_fail >= self.fail_threshold:
                # 冷却时长随连续失败次数增长，封顶 30min；服务端 Retry-After 指示更长时优先遵循
                grow = min(self.cooldown_seconds * (2 ** min(30, max(0, self.consecutive_fail - self.fail_threshold))),
                           30 * 60)
                if retry_after:
                    try:
                        retry_seconds = float(retry_after)
                        if math.isfinite(retry_seconds) and retry_seconds > 0:
                            grow = max(grow, retry_seconds)
                    except (TypeError, ValueError):
                        pass
                self.cooldown_until = max(self.cooldown_until, time.time() + grow)
                self._local_not_before_monotonic = max(self._local_not_before_monotonic, time.monotonic() + grow)
                self._set_state(CollectState.COOLDOWN)
            elif self.state == CollectState.HEALTHY:
                self._set_state(CollectState.WARNING)
            return self.state

    def force_pause(self, state=CollectState.PAUSED, cooldown_seconds=None):
        """外部（Auth/验证码/IP 风险）要求显式暂停一段时间。"""
        with self._lock:
            secs = float(cooldown_seconds if cooldown_seconds is not None else self.cooldown_seconds)
            self.cooldown_until = max(self.cooldown_until, time.time() + secs)
            self._local_not_before_monotonic = max(self._local_not_before_monotonic, time.monotonic() + secs)
            self._set_state(state)

    def _set_state(self, st):
        if st != self.state:
            self.state = st
            self.last_state_change = time.time()

    # ---- 查询 / 等待 ----
    def remaining_cooldown(self, now=None):
        now = now if now is not None else time.time()
        with self._lock:
            mono = time.monotonic()
            local = (self._local_not_before_monotonic - mono if self._local_not_before_monotonic
                     else self.cooldown_until - now)
            server = (self._server_not_before_monotonic - mono if self._server_not_before_monotonic
                      else self._server_not_before - now)
            return max(0.0, local, server)

    def can_run(self):
        if not self.enabled:
            return True
        with self._lock:
            return self.remaining_cooldown() <= 0

    def wait_slot(self, sleep=time.sleep, cancelled=None):
        """Reserve a distinct slot on this limiter; never jitter a server deadline.

        Sharing must be performed by the existing account/platform Owner. This
        object does not discover accounts, share credentials or change limits.
        A cancelled reservation is left as a safe gap, never reassigned early.
        """
        if cancelled is not None and cancelled():
            raise InterruptedError("COLLECTOR_WAIT_CANCELLED")
        if not self.enabled:
            return 0.0
        with self._lock:
            now = time.monotonic()
            interval = self.interval
            if self.jitter:
                interval *= random.uniform(0.7, 1.3)
            deadline = max(now + self.remaining_cooldown(),
                           max(now, self._next_slot_monotonic) + interval)
            self._next_slot_monotonic = deadline
            wait = max(0.0, deadline - now)
        total_wait = 0.0
        while True:
            if cancelled is not None and cancelled():
                raise InterruptedError("COLLECTOR_WAIT_CANCELLED")
            if wait > 0:
                sleep(wait)
                total_wait += wait
            if cancelled is not None and cancelled():
                raise InterruptedError("COLLECTOR_WAIT_CANCELLED")
            with self._lock:
                now = time.monotonic()
                actual_floor = (self._last_release_monotonic + interval
                                if self._last_release_monotonic is not None else deadline)
                wait = max(0.0, deadline - now, actual_floor - now,
                           self.remaining_cooldown())
                if wait <= 0:
                    self._last_release_monotonic = now
                    return total_wait

    def snapshot(self):
        with self._lock:
            return {
                'state': self.state, 'state_label': CollectState.label(self.state),
                'interval': round(self.interval, 2), 'base_interval': self.base_interval,
                'consecutive_fail': self.consecutive_fail,
                'remaining_cooldown': round(self.remaining_cooldown(), 1),
                'fail_threshold': self.fail_threshold,
                'jitter': self.jitter,
            }
