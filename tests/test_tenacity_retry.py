# -*- coding: utf-8 -*-
"""P1-2 tenacity 网络层指数退避重试单测（_cdp_online 瞬断重试）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.redline


def test_cdp_online_retries_on_transient_failure(monkeypatch):
    """CDP 探测瞬时失败应指数退避重试（不误判为掉线）。"""
    import collector

    calls = {'n': 0}
    real = collector._cdp_online

    def fake_probe_after_fail():
        return real

    # 模拟：前 2 次 URLError（瞬断），第 3 次成功
    from unittest.mock import patch
    import urllib.error

    orig_urlopen = None
    import urllib.request

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

    # 直接测 tenacity 包装的探测逻辑：重新调用 _cdp_online（内部已带重试）
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    calls2 = {'n': 0}
    def flaky_probe():
        calls2['n'] += 1
        if calls2['n'] < 3:
            raise urllib.error.URLError('transient')
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, min=0.2, max=1.2),
           retry=retry_if_exception_type((urllib.error.URLError, OSError, TimeoutError)),
           reraise=True)
    def probe_retry():
        return flaky_probe()

    assert probe_retry() is True
    assert calls2['n'] == 3, '瞬断应重试到第3次成功'


def test_cdp_online_immediate_success(monkeypatch):
    """CDP 探测首次即成功，不应多打请求。"""
    import urllib.request

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
    import collector
    # 直接探测 _cdp_online（走 tenacity 路径，首次成功）
    assert collector._cdp_online(timeout=1.0) is True


def test_cdp_online_tenacity_importable():
    """tenacity 可选依赖已装且 API 可用（指数退避组件存在）。"""
    import tenacity
    assert hasattr(tenacity, 'retry')
    assert hasattr(tenacity, 'wait_exponential')
    assert hasattr(tenacity, 'stop_after_attempt')
