# -*- coding: utf-8 -*-
"""GuardMetrics：线程安全的采集指标（成功率、平均/分位延迟、近期结果），仅内存，可选落盘。"""
import threading
import time
from collections import deque


class GuardMetrics:
    def __init__(self, window=200):
        self._lock = threading.RLock()
        self._lat = deque(maxlen=window)
        self._ok = deque(maxlen=window)   # 1/0
        self.total = 0
        self.success = 0
        self.failure = 0
        self.last_success_at = 0.0
        self.last_failure_at = 0.0
        self.last_error = ''

    def record(self, ok, latency=0.0, error=''):
        with self._lock:
            self.total += 1
            self._ok.append(1 if ok else 0)
            try:
                self._lat.append(float(latency or 0.0))
            except Exception:
                pass
            if ok:
                self.success += 1
                self.last_success_at = time.time()
            else:
                self.failure += 1
                self.last_failure_at = time.time()
                self.last_error = str(error)[:160]

    @property
    def success_rate(self):
        with self._lock:
            if not self._ok:
                return 1.0
            return sum(self._ok) / len(self._ok)

    @property
    def avg_latency(self):
        with self._lock:
            return (sum(self._lat) / len(self._lat)) if self._lat else 0.0

    def snapshot(self):
        with self._lock:
            lats = sorted(self._lat)
            p = lambda q: (lats[min(len(lats) - 1, int(len(lats) * q))] if lats else 0.0)
            return {
                'total': self.total, 'success': self.success, 'failure': self.failure,
                'success_rate': round(self.success_rate, 4),
                'avg_latency': round(self.avg_latency, 3),
                'p95_latency': round(p(0.95), 3),
                'last_success_at': self.last_success_at,
                'last_failure_at': self.last_failure_at,
                'last_error': self.last_error,
            }
