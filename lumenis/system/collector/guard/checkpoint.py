# -*- coding: utf-8 -*-
"""Checkpoint：按 平台+关键词 记录断点续采状态（已采 note_id、最后成功时间、滚动页码）。

落 data/collector_guard/<platform>_checkpoint.json；文件损坏自动重置不拖垮主流程；
只存 ID/时间等元数据，不存正文隐私内容。"""
import json
import os
import re
import threading
import time
from copy import deepcopy

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
            return True
        except Exception:
            return False  # 断点只影响效率，绝不因落盘失败阻断采集

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
            return self._save()

    def seen_ids(self, keyword):
        """Return an immutable snapshot of the IDs already recorded for a key."""
        if not isinstance(keyword, str) or not keyword:
            return ()
        with self._lock:
            entry = self._data.get('keywords', {}).get(keyword)
            if not isinstance(entry, dict):
                return ()
            seen = entry.get('seen', ())
            if not isinstance(seen, (list, tuple)):
                return ()
            return tuple(note_id for note_id in seen if isinstance(note_id, str))

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

    @staticmethod
    def _valid_task_binding(task_binding):
        return (isinstance(task_binding, str)
                and re.fullmatch(r'[0-9a-f]{64}', task_binding) is not None)

    def get_operational_resume(self, keyword, task_binding):
        """Return only this exact task/query's private raw-checkpoint descriptor."""
        if not isinstance(keyword, str) or not keyword or not self._valid_task_binding(task_binding):
            return None
        with self._lock:
            entry = self._data.get('keywords', {}).get(keyword)
            if not isinstance(entry, dict):
                return None
            descriptors = entry.get('operational_resume')
            if not isinstance(descriptors, dict):
                return None
            descriptor = descriptors.get(task_binding)
            return deepcopy(descriptor) if isinstance(descriptor, dict) else None

    def save_operational_resume(self, keyword, task_binding, descriptor):
        """Persist a bounded metadata-only continuation pointer, never note content."""
        if (not isinstance(keyword, str) or not keyword
                or not self._valid_task_binding(task_binding)
                or not isinstance(descriptor, dict)):
            return False
        pending_ids = descriptor.get('pending_note_ids')
        if (descriptor.get('task_binding') != task_binding
                or descriptor.get('keyword') != keyword
                or descriptor.get('source_host') != 'www.rednote.com'
                or not isinstance(descriptor.get('raw_path'), str)
                or not isinstance(descriptor.get('raw_sha256'), str)
                or re.fullmatch(r'[0-9a-f]{64}', descriptor['raw_sha256']) is None
                or not isinstance(descriptor.get('identity_fingerprint'), str)
                or re.fullmatch(r'[0-9a-f]{64}', descriptor['identity_fingerprint']) is None
                or not isinstance(descriptor.get('run_id'), str)
                or not descriptor['run_id']
                or not isinstance(pending_ids, list)
                or any(not isinstance(note_id, str)
                       or re.fullmatch(r'[0-9a-fA-F]{24}', note_id) is None
                       for note_id in pending_ids)
                or type(descriptor.get('complete')) is not bool
                or type(descriptor.get('terminal_error')) is not bool
                or type(descriptor.get('continuation_required')) is not bool
                or (descriptor.get('pagination_exhausted') is not False
                    and descriptor.get('pagination_exhausted') is not None)
                or (descriptor.get('captured_at') is not None
                    and (not isinstance(descriptor.get('captured_at'), str)
                         or len(descriptor['captured_at']) > 80))):
            return False
        safe = {
            'task_binding': task_binding,
            'keyword': keyword,
            'source_host': 'www.rednote.com',
            'identity_fingerprint': descriptor['identity_fingerprint'],
            'raw_path': descriptor['raw_path'],
            'raw_sha256': descriptor['raw_sha256'],
            'run_id': descriptor['run_id'],
            'complete': descriptor['complete'],
            'terminal_error': descriptor['terminal_error'],
            'pending_note_ids': list(pending_ids),
            'pagination_exhausted': False,
            'continuation_required': descriptor['continuation_required'],
            'captured_at': descriptor.get('captured_at'),
            'updated_at': time.time(),
        }
        with self._lock:
            entry = self._kw(keyword)
            descriptors = entry.setdefault('operational_resume', {})
            if not isinstance(descriptors, dict):
                return False
            descriptors[task_binding] = safe
            return self._save()


def re_safe(name):
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(name))[:40] or 'platform'
