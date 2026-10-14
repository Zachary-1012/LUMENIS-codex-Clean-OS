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
    return (_load('lumenis.shared.reporting.export_api'),
            _load('lumenis.system.ai_gateway.channel'))


def test_legacy_report_facade_uses_the_current_authorized_scope(env, monkeypatch):
    """The compatibility entry must delegate to the current scoped report builder."""
    er, _ = env
    actor = object()
    scope = {'domain_id': 'cth', 'product_id': 'CTH', 'subject_id': 'SUBJECT-A',
             'brand_focus_id': None, 'global_scope': False}
    report = {'summary': {'total': 1}, 'scope': scope}
    calls = []
    monkeypatch.setattr(er, '_request_report_scope',
                        lambda action='read': (actor, scope, [], None))
    monkeypatch.setattr(er, '_build_report',
                        lambda kind, start, end, **kwargs:
                        (calls.append((kind, start, end, kwargs['actor'], kwargs['scope']))
                         or (kind, start, end, report, 1, [], [])))
    monkeypatch.setattr(er, '_verify_report_source_use', lambda *_args: 1)

    result = er.generate_report_data('daily', '2026-10-02')

    assert result == report
    assert calls == [('daily', '2026-10-02', '2026-10-02', actor, scope)]


def test_breaker_open_halfopen_recover():
    """阶段九 b) 熔断状态迁移: 失败->OPEN, 冷却->HALF_OPEN, 成功->CLOSED"""
    from lumenis.system.ai_gateway.channel import CircuitBreaker
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
    from lumenis.system.ai_gateway.channel import classify_error
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
