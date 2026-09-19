# -*- coding: utf-8 -*-
"""Checkpoint：按 平台+关键词 记录断点续采状态（已采 note_id、最后成功时间、滚动页码）。

落 data/collector_guard/<platform>_checkpoint.json；文件损坏自动重置不拖垮主流程；
只存 ID/时间等元数据，不存正文隐私内容。"""
import json
import os
import threading
import time

from lumenis.shared.database.registry import get_data_dir


class Checkpoint:
    def __init__(self, platform, base_dir=None):
        self.platform = re_safe(platform)
        base_dir = base_dir or os.path.join(get_data_dir(), 'collector_guard')
        self.path = os.path.join(base_dir, f'{self.platform}_checkpoint.json')
        self._lock = threading.RLock()
        self._data = self._load()

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, dict):
                d.setdefault('keywords', {})
                return d
        except Exception:
            pass
        return {'platform': self.platform, 'keywords': {}, 'updated_at': 0}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self._data['updated_at'] = time.time()
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception:
            pass  # 断点只影响效率，绝不因落盘失败阻断采集

    def _kw(self, keyword):
        with self._lock:
            k = self._data['keywords'].setdefault(keyword, {
                'seen': [], 'last_success_at': 0, 'scroll_index': 0, 'last_note_id': ''})
            return k

    def is_seen(self, keyword, note_id):
        with self._lock:
            return note_id in set(self._kw(keyword).get('seen', []))

    def mark_seen(self, keyword, note_ids, scroll_index=None):
        with self._lock:
            k = self._kw(keyword)
            seen = set(k.get('seen', []))
            seen.update(x for x in note_ids if x)
            k['seen'] = sorted(seen)[-5000:]  # 控制体积，保留最近 5000
            k['last_success_at'] = time.time()
            if scroll_index is not None:
                k['scroll_index'] = int(scroll_index)
            if note_ids:
                k['last_note_id'] = note_ids[-1]
            self._save()

    def filter_new(self, keyword, note_ids):
        with self._lock:
            seen = set(self._kw(keyword).get('seen', []))
            return [n for n in note_ids if n not in seen]

    def last_success(self, keyword):
        return self._kw(keyword).get('last_success_at', 0)

    def reset(self, keyword=None):
        with self._lock:
            if keyword:
                self._data['keywords'].pop(keyword, None)
            else:
                self._data['keywords'] = {}
            self._save()


def re_safe(name):
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(name))[:40] or 'platform'
