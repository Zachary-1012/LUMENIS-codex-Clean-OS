# -*- coding: utf-8 -*-
"""ai_channel 稳固层单测：全部离线纯逻辑，不发起真实网络。"""
import os
import socket
import urllib.request, urllib.error
import pytest

from lumenis.system.ai_gateway import channel as ac


# ---------- 失败分类 ----------
@pytest.mark.parametrize('status,kind,retry', [
    (200, 'ok', False), (401, 'auth', False), (403, 'auth', False),
    (400, 'bad_request', False), (429, 'rate_limit', True),
    (500, 'server', True), (502, 'server', True), (503, 'server', True),
])
def test_classify_status(status, kind, retry):
    k, r = ac.classify_error(status=status)
    assert k == kind and r is retry


def test_classify_network_errors_retryable():
    for e in (urllib.error.URLError('reset'), socket.timeout(), ConnectionResetError(), TimeoutError()):
        k, r = ac.classify_error(exc=e)
        assert r is True and k == 'network'


def test_classify_http_error_uses_code():
    e = urllib.error.HTTPError('u', 401, 'unauth', None, None)
    k, r = ac.classify_error(exc=e)
    assert (k, r) == ('auth', False)


# ---------- 熔断状态机（注入假时钟）----------
def _breaker_with_clock(threshold=3, cooldown=30.0):
    now = [1000.0]
    b = ac.CircuitBreaker(fail_threshold=threshold, cooldown_sec=cooldown, now_func=lambda: now[0])
    return b, now


def test_breaker_opens_after_threshold_and_half_open_recovers():
    b, now = _breaker_with_clock(3, 30)
    assert b.allow_request()
    for _ in range(2):
        b.record_failure('network')
    assert b.state == ac.CircuitBreaker.CLOSED  # 未达阈值
    b.record_failure('server')
    assert b.state == ac.CircuitBreaker.OPEN
    assert b.allow_request() is False            # 冷却未到，快速拒绝
    now[0] += 31
    assert b.allow_request() is True             # 冷却到点，HALF_OPEN 放一个探测
    assert b.state == ac.CircuitBreaker.HALF_OPEN
    b.record_success(12)
    assert b.state == ac.CircuitBreaker.CLOSED and b.consecutive_failures == 0


def test_breaker_half_open_failure_reopens():
    b, now = _breaker_with_clock(1, 10)
    b.record_failure('network')
    assert b.state == ac.CircuitBreaker.OPEN
    now[0] += 11
    b.allow_request()
    assert b.state == ac.CircuitBreaker.HALF_OPEN
    b.record_failure('server')
    assert b.state == ac.CircuitBreaker.OPEN     # 探测失败立即回 OPEN


# ---------- 有限重试 ----------
class _Resp:
    def __init__(self, body): self._b = body
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _ScriptedOpener:
    """按脚本依次抛异常或返回响应。"""
    def __init__(self, script):
        self.script, self.calls = script, 0
    def open(self, req, timeout=None):
        item = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return _Resp(item)


def _http_err(code):
    return urllib.error.HTTPError('u', code, 'e', None, None)


def test_post_retries_then_success():
    op = _ScriptedOpener([_http_err(503), _http_err(500), b'{"ok":1}'])
    succ, fail = [], []
    body, attempts = ac.post_with_retry(
        'http://x', b'{}', {'K': 'v'}, opener=op, sleep=lambda s: None,
        on_success=lambda ms: succ.append(ms), on_failure=lambda k: fail.append(k))
    assert attempts == 3 and op.calls == 3
    assert body == b'{"ok":1}' and len(succ) == 1 and fail == ['server', 'server']


def test_post_auth_fatal_no_retry():
    op = _ScriptedOpener([_http_err(401)])
    with pytest.raises(urllib.error.HTTPError):
        ac.post_with_retry('http://x', b'{}', {}, opener=op, sleep=lambda s: None,
                           on_success=lambda ms: None, on_failure=lambda k: None)
    assert op.calls == 1                          # 鉴权错误只尝试一次


def test_post_hard_attempts_cap():
    op = _ScriptedOpener([_http_err(503)])        # 永远 503
    with pytest.raises(urllib.error.HTTPError):
        ac.post_with_retry('http://x', b'{}', {}, max_attempts=99, opener=op,
                           sleep=lambda s: None,
                           on_success=lambda ms: None, on_failure=lambda k: None)
    assert op.calls <= ac._HARD_MAX_ATTEMPTS      # 硬上限兜底，绝不无限


def test_backoff_capped():
    assert ac._backoff_delay(0, 0.5) == 0.5
    assert ac._backoff_delay(10, 0.5) == ac._MAX_BACKOFF   # 指数增长被封顶


# ---------- 配置自加载 ----------
def test_ensure_env_loads_missing_without_overwrite(tmp_path, monkeypatch):
    p = tmp_path / '.env'
    p.write_text('TEST_CH_NEW=hello\nTEST_CH_KEEP=fromfile\n', encoding='utf-8')
    monkeypatch.setenv('TEST_CH_KEEP', 'fromenv')
    monkeypatch.delenv('TEST_CH_NEW', raising=False)
    ac._ENV_LOADED = False                        # 重置幂等标志以测试逻辑
    ac.ensure_env_loaded(str(p))
    assert os.environ['TEST_CH_NEW'] == 'hello'
    assert os.environ['TEST_CH_KEEP'] == 'fromenv'  # 不覆盖已有环境变量


# ---------- 健康快照 ----------
def test_channel_health_available_flag():
    b, now = _breaker_with_clock(1, 5)
    from lumenis.system.ai_gateway import channel as ai_channel
    orig = ai_channel.breaker
    ai_channel.breaker = b
    try:
        retired = ac.channel_health('zhipu', 'glm-x')
        assert retired['available'] is False
        assert retired['provider'] == 'zhipu'
        assert retired['provider_status'] == 'DISABLED'

        # Legacy compatibility providers remain observable but unavailable.
        h = ac.channel_health('ark', 'doubao-test')
        assert h['available'] is False and h['provider'] == 'ark'
        assert h['provider_status'] == 'LEGACY'
        b.record_failure('network')
        h2 = ac.channel_health('ark', 'doubao-test')
        assert h2['available'] is False and h2['state'] == 'OPEN'
    finally:
        ai_channel.breaker = orig


def test_retired_local_providers_cannot_be_revived_or_probed(monkeypatch):
    from lumenis.system.ai_gateway import providers

    probes = []
    monkeypatch.setattr(providers, '_probe_endpoint', lambda *a, **k: probes.append(a) or True)
    for name in ('ollama', 'lmstudio', 'llama_cpp'):
        providers.set_provider_status(name, providers.ACTIVE)
        assert providers.provider_status(name) == providers.DISABLED

    assert providers.probe_local_providers() == {
        'ollama': providers.DISABLED,
        'lmstudio': providers.DISABLED,
        'llama_cpp': providers.DISABLED,
    }
    assert probes == []
