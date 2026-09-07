# -*- coding: utf-8 -*-
"""阶段4b：v4_upgrade.adapters 韧性增强层单测（纯标准库、tmp 隔离、不触网、不改主采集链）。

覆盖 base 的熔断器/令牌桶/指标/safe_collect 不抛，以及 dual_pool 的 Cookie/Proxy 状态机、
300012 直接冷却、池选择摘除、DualPoolManager 凭证与风控回调。
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v4_upgrade.adapters.base import (  # noqa: E402
    CircuitBreaker, RateLimiter, AdapterMetrics, BaseAdapter, AdapterResult,
)
from v4_upgrade.adapters.dual_pool import (  # noqa: E402
    CookieItem, ProxyItem, CookieStatus, ProxyStatus,
    CookiePool, ProxyPool, DualPoolManager,
)


# ---------- 全局：压掉生产 retry sleep（单测不真等12秒） ----------
@pytest.fixture(autouse=True)
def _patch_sleep_for_tests(monkeypatch):
    """safe_collect 重试循环会 time.sleep(retry_delay*(attempt+1))，
    生产配置 retry_delay=2/max_retries=3 累计真睡12秒。
    单测里把 base.time.sleep 压成 no-op，重试逻辑仍被验证，只是不等。"""
    import v4_upgrade.adapters.base as _base
    monkeypatch.setattr(_base.time, 'sleep', lambda *_a, **_k: None)
    yield


# ---------- CircuitBreaker ----------
def test_circuit_opens_after_threshold_and_half_opens():
    cb = CircuitBreaker(threshold=3, reset_seconds=1)
    assert cb.allow()
    cb.record_failure(); cb.record_failure()
    assert cb.state == 'closed' and cb.allow()       # 未达阈值仍放行
    cb.record_failure()
    assert cb.state == 'open' and cb.allow() is False  # 达阈值熔断
    cb.last_fail_time = time.time() - 2               # 模拟冷却已过
    assert cb.allow() and cb.state == 'half_open'      # 半开试探
    cb.record_success()
    assert cb.state == 'closed' and cb.fail_count == 0


# ---------- RateLimiter ----------
def test_rate_limiter_burst_then_block():
    rl = RateLimiter(rate_per_minute=0, burst=2)  # 速率0：不补充令牌
    assert rl.try_acquire() and rl.try_acquire()
    assert rl.try_acquire() is False              # 突发耗尽即限流


# ---------- AdapterMetrics ----------
def test_metrics_aggregation():
    m = AdapterMetrics()
    m.record_call(True, 0.1)
    m.record_call(True, 0.3)
    m.record_call(False, 0.2, error='boom', circuit_open=True)
    assert m.total_calls == 3 and m.success_count == 2 and m.failure_count == 1
    assert m.success_rate == round(2 / 3 * 100, 1)
    assert m.circuit_open_count == 1 and m.avg_duration > 0
    d = m.to_dict()
    assert {'total_calls', 'success_rate', 'circuit_open_count'} <= set(d)


# ---------- safe_collect 永不抛 ----------
class _BoomAdapter(BaseAdapter):
    platform_name = 'boom'
    def search(self, keyword, max_results=20):
        raise RuntimeError('network down')


def test_safe_collect_never_raises():
    a = _BoomAdapter()
    res = a.safe_collect('kw')
    assert isinstance(res, AdapterResult) and res.success is False and 'network down' in res.error


# ---------- Cookie / Proxy 状态机 ----------
def test_cookie_300012_immediate_cooldown_then_recover():
    c = CookieItem(id='c1', platform='xhs', cookie_data={'a': 1}, cooldown_seconds=300)
    c.mark_failed('300012 风控')
    assert c.status == CookieStatus.COOLDOWN and c.is_available() is False
    c.cooldown_until = time.time() - 1           # 冷却到期
    assert c.is_available() and c.status == CookieStatus.HEALTHY


def test_cookie_failures_escalate_and_success_reset():
    c = CookieItem(id='c2', platform='xhs', cookie_data={}, max_fail=3)
    c.mark_failed(); assert c.status == CookieStatus.SUSPECT
    c.mark_failed(); c.mark_failed()
    assert c.status == CookieStatus.FAILED and c.is_available() is False
    c.status = CookieStatus.SUSPECT
    c.mark_success(); assert c.status == CookieStatus.HEALTHY and c.fail_count == 0


def test_proxy_failure_cooldown_and_failed():
    p = ProxyItem(id='p1', url='http://1.2.3.4:8080', max_fail=3, cooldown_seconds=120)
    p.mark_failed()
    assert p.status == ProxyStatus.COOLDOWN and p.is_available() is False
    for _ in range(2):
        p.mark_failed()
    assert p.status == ProxyStatus.FAILED


# ---------- 池：tmp 隔离 ----------
def test_cookie_pool_add_get_and_evict(tmp_path):
    pool = CookiePool(cookie_dir=str(tmp_path / 'cookies'))
    cid = pool.add_cookie('xhs', {'web_session': 'x'}, cookie_id='x1')
    got = pool.get_cookie('xhs')
    assert got is not None and got.id == cid
    pool.mark_cookie_result(cid, False, reason='300012')  # 直接冷却
    assert pool.get_cookie('xhs') is None                # 冷却期摘除
    stats = pool.get_stats('xhs')
    assert stats['xhs']['total'] == 1


def test_dual_pool_manager_credentials_and_callback(tmp_path):
    hits = []
    mgr = DualPoolManager(cookie_dir=str(tmp_path / 'ck'), proxy_list=[],
                          risk_callback=lambda **kw: hits.append(kw))
    mgr.cookie_pool.add_cookie('xhs', {'k': 1}, cookie_id='z1')
    cred = mgr.get_credentials('xhs')
    assert cred['has_cookie'] is True and cred['has_proxy'] is False
    mgr.report_result('xhs', cookie_id='z1', success=False, reason='blocked')
    assert len(hits) == 1 and hits[0]['reason'] == 'blocked'   # 风控回调被触发
    hc = mgr.health_check()
    assert isinstance(hc, dict)
