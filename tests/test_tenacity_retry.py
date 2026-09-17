# -*- coding: utf-8 -*-
"""P1-2 tenacity 网络层指数退避重试单测（显式远程 worker）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.redline

REMOTE_WORKER = "https://browser-worker.example:9223"


def test_cdp_online_retries_on_transient_failure(monkeypatch):
    """已配置 worker 的 CDP 探测瞬时失败应指数退避重试。"""
    import urllib.error
    import urllib.request
    import collector

    calls = {'n': 0}

    class _FakeResponse:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def flaky_urlopen(req, timeout=None):
        calls['n'] += 1
        if calls['n'] < 3:
            raise urllib.error.URLError('transient')
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, 'urlopen', flaky_urlopen)
    assert collector._cdp_online(timeout=1.0, cdp_url=REMOTE_WORKER) is True
    assert calls['n'] == 3, '瞬断应重试到第3次成功'


def test_cdp_online_immediate_success(monkeypatch):
    """已配置 worker 首次探测成功时不应多打请求。"""
    import urllib.request
    import collector

    calls = {'n': 0}

    class _FakeResponse:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def ok_urlopen(req, timeout=None):
        calls['n'] += 1
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, 'urlopen', ok_urlopen)
    assert collector._cdp_online(timeout=1.0, cdp_url=REMOTE_WORKER) is True
    assert calls['n'] == 1


def test_cdp_online_without_endpoint_fails_closed_without_network(monkeypatch):
    """没有显式 worker 时必须直接 False，不能偷偷探测 localhost。"""
    import urllib.request
    import collector

    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setattr(collector, 'CDP_URL', '')

    def fail_if_called(*args, **kwargs):
        raise AssertionError('未配置 worker 时不应发送网络请求')

    monkeypatch.setattr(urllib.request, 'urlopen', fail_if_called)
    assert collector._cdp_online(timeout=1.0) is False


def test_cdp_online_tenacity_importable():
    """tenacity 可选依赖已装且 API 可用（指数退避组件存在）。"""
    import tenacity
    assert hasattr(tenacity, 'retry')
    assert hasattr(tenacity, 'wait_exponential')
    assert hasattr(tenacity, 'stop_after_attempt')
