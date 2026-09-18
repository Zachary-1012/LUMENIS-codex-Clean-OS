# -*- coding: utf-8 -*-
"""Canonical Capability V1 阶段八/九: 生产路径 DUAL RUN + 稳定性验证 (offline)
阶段八: Shared Reporting export/KOS 生产路径与 canonical 同源（无算法分叉）:
  a) Shared export_api.generate_report_data 情感分桶 == canonical_metrics 直算（同一有效舆情集合）
阶段九: 熔断/恢复/回滚能力:
  b) CircuitBreaker 连续失败->OPEN, 冷却->HALF_OPEN, 成功->CLOSED
  c) classify_error: URLError 可重试, 鉴权致命, 未知异常保守不重试
"""
import os
import sys
import time
import importlib
import subprocess

import pytest

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ['ZBC_DB_PATH']


def _load(name):
    for k in list(sys.modules):
        if k == name or k.startswith(name + '.'):
            del sys.modules[k]
    sys.path.insert(0, ZBC)
    return importlib.import_module(name)


@pytest.fixture(scope='module')
def env():
    os.environ['ZBC_DB_PATH'] = DB
    return _load('lumenis.shared.reporting.export_api'), _load('ai_channel')


def _is_valid_yuqing(n):
    """复现 Shared export_api 内部有效舆情过滤（剔除重复/噪音）"""
    try:
        if int(n.get('is_duplicate') or 0) == 1:
            return False
    except (TypeError, ValueError):
        pass
    if (n.get('noise_type') or '').strip():
        return False
    return True


def test_export_sentiment_matches_canonical(env):
    """阶段八 a) Shared export_api 情感分桶 == canonical 直算（同一有效舆情集合）"""
    er, _ = env
    cm = _load('canonical_metrics')
    d = er.generate_report_data('daily')
    summ = d.get('summary', {}) if isinstance(d, dict) else {}
    # 复现 export 的 notes 集合（filter_notes_by_period 第一元素 + 有效舆情过滤）
    raw = er.filter_notes_by_period('daily')
    if isinstance(raw, tuple):
        raw = raw[0]
    notes = [n for n in raw if _is_valid_yuqing(n)]
    canon = cm.sentiment_count(notes)
    assert summ.get('positive') == canon.get('positive'), \
        f'pos: export={summ.get("positive")} canon={canon.get("positive")}'
    assert summ.get('negative') == canon.get('negative'), \
        f'neg: export={summ.get("negative")} canon={canon.get("negative")}'
    assert summ.get('neutral') == canon.get('neutral'), \
        f'neu: export={summ.get("neutral")} canon={canon.get("neutral")}'


def test_breaker_open_halfopen_recover():
    """阶段九 b) 熔断状态迁移: 失败->OPEN, 冷却->HALF_OPEN, 成功->CLOSED"""
    from ai_channel import CircuitBreaker
    cb = CircuitBreaker(fail_threshold=3, cooldown_sec=0.8)
    for _ in range(3):
        cb.record_failure()
    assert cb.snapshot()['state'] == 'OPEN'
    time.sleep(1.0)
    assert cb.allow_request() is True
    assert cb.snapshot()['state'] == 'HALF_OPEN'
    cb.record_success()
    assert cb.snapshot()['state'] == 'CLOSED'


def test_classify_error_retry_policy():
    """阶段九 c) 分类重试: 网络可重试, 鉴权致命, 未知保守"""
    import urllib.error
    from ai_channel import classify_error
    _, r1 = classify_error(urllib.error.URLError('refused'))
    assert r1 is True
    class _AuthErr(Exception):
        def __init__(self):
            super().__init__('401')
            self.response = type('R', (), {'status_code': 401})()
    _, r2 = classify_error(_AuthErr())
    assert r2 is False
    _, r3 = classify_error(Exception('unknown'))
    assert r3 is False


def test_git_rollback_path_reachable():
    """阶段九 d) git 回滚路径可达（HEAD~1 可解析）"""
    r = subprocess.run(['git', 'rev-parse', 'HEAD~1'], cwd=ZBC, capture_output=True, text=True)
    assert r.returncode == 0, 'HEAD~1 not resolvable'