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
        # 采集准确度质量门（COLLECTION_ACCURACY_GATE_v1）：9项指标计数器
        self._quality = {
            'total_notes': 0,        # 总笔记数
            'valid_content': 0,      # 有效内容数（有title或content）
            'subject_hit': 0,        # 主体命中数（subject_hit_cdp=True）
            'subject_unknown': 0,    # 主体未判定数（subject_hit_cdp=None）
            'duplicate': 0,          # 重复数（note_id已存在）
            'author_resolved': 0,    # 作者解析数（有author_id）
            'timestamp_complete': 0, # 时间完整数（有publish_date）
            'engagement_complete': 0,# 互动完整数（likes+comments+collects+shares>0）
            'evidence_complete': 0,  # 证据完整数（有url和captured_at）
        }
        self._seen_nids = set()  # 用于重复检测

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

    def record_quality(self, notes, seen_nids=None):
        """采集准确度质量门：统计单次采集结果的9项完整性指标（COLLECTION_ACCURACY_GATE_v1）。"""
        if not notes:
            return
        with self._lock:
            for n in notes:
                if not isinstance(n, dict):
                    continue
                self._quality['total_notes'] += 1
                nid = n.get('note_id', '')
                if n.get('title') or n.get('content'):
                    self._quality['valid_content'] += 1
                sh = n.get('subject_hit_cdp')
                if sh is True:
                    self._quality['subject_hit'] += 1
                elif sh is None:
                    self._quality['subject_unknown'] += 1
                if nid:
                    if nid in self._seen_nids or (seen_nids and nid in seen_nids):
                        self._quality['duplicate'] += 1
                    else:
                        self._seen_nids.add(nid)
                if n.get('author_id'):
                    self._quality['author_resolved'] += 1
                if n.get('publish_date'):
                    self._quality['timestamp_complete'] += 1
                if (n.get('likes', 0) or n.get('comments', 0) or
                        n.get('collects', 0) or n.get('shares', 0)):
                    self._quality['engagement_complete'] += 1
                if n.get('url') and n.get('captured_at'):
                    self._quality['evidence_complete'] += 1

    @property
    def quality_metrics(self):
        """采集准确度9项质量门指标（比率，0-1）。"""
        with self._lock:
            t = max(1, self._quality['total_notes'])
            q = self._quality
            return {
                'fetch_success_rate': round(self.success_rate, 4),
                'valid_content_rate': round(q['valid_content'] / t, 4),
                'subject_precision': round(q['subject_hit'] / max(1, t - q['subject_unknown']), 4),
                'duplicate_rate': round(q['duplicate'] / t, 4),
                'author_resolution_rate': round(q['author_resolved'] / t, 4),
                'timestamp_completeness': round(q['timestamp_complete'] / t, 4),
                'engagement_completeness': round(q['engagement_complete'] / t, 4),
                'evidence_completeness': round(q['evidence_complete'] / t, 4),
                'total_notes': q['total_notes'],
                'subject_hit': q['subject_hit'],
                'subject_unknown': q['subject_unknown'],
            }

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
                'quality': self.quality_metrics,
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
