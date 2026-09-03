# -*- coding: utf-8 -*-
"""GuardMetrics：线程安全的采集指标（成功率、平均/分位延迟、近期结果），仅内存，可选落盘。

持久化（P0-E 采集性能可观测）：可选 persist_path；非热路径调用 persist() 限频落盘，
不阻塞 record() 采集热路径。落盘文件为 data/metrics/collector-metrics.jsonl（每行一个快照）。"""
import json
import os
import threading
import time
from collections import deque


class GuardMetrics:
    def __init__(self, window=200, persist_path=None, persist_every_sec=60):
        self._lock = threading.RLock()
        self._lat = deque(maxlen=window)
        self._ok = deque(maxlen=window)   # 1/0
        self.total = 0
        self.success = 0
        self.failure = 0
        self.last_success_at = 0.0
        self.last_failure_at = 0.0
        self.last_error = ''
        self._persist_path = persist_path
        self._persist_every_sec = persist_every_sec
        self._last_persist_ts = 0.0

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

    def persist(self):
        """限频落盘当前快照到 jsonl（非热路径调用，默认 60s 一次）。失败静默，不抛异常。"""
        with self._lock:
            now = time.time()
            if not self._persist_path or (now - self._last_persist_ts) < self._persist_every_sec:
                return False
            self._last_persist_ts = now
            row = dict(self.snapshot())
            row['ts'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now))
        try:
            d = os.path.dirname(self._persist_path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self._persist_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            return True
        except Exception:
            return False
