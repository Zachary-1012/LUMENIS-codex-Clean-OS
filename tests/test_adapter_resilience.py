# -*- coding: utf-8 -*-
"""阶段4b：lumenis.adapters 韧性增强层单测（纯标准库、tmp 隔离、不触网、不改主采集链）。

覆盖 base 的熔断器/令牌桶/指标/safe_collect 不抛，以及 dual_pool 的 Cookie/Proxy 状态机、
300012 直接冷却、池选择摘除、DualPoolManager 凭证与风控回调。
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.adapters.base import (  # noqa: E402
    CircuitBreaker, RateLimiter, AdapterMetrics, BaseAdapter, AdapterResult,
    AdapterCacheContext,
)
from lumenis.adapters.dual_pool import (  # noqa: E402
    CookieItem, ProxyItem, CookieStatus, ProxyStatus,
    CookiePool, ProxyPool, DualPoolManager,
)
from lumenis.adapters.registry import AdapterRegistry  # noqa: E402


# ---------- 全局：压掉生产 retry sleep（单测不真等12秒） ----------
@pytest.fixture(autouse=True)
def _patch_sleep_for_tests(monkeypatch):
    """safe_collect 重试循环会 time.sleep(retry_delay*(attempt+1))，
    生产配置 retry_delay=2/max_retries=3 累计真睡12秒。
    单测里把 base.time.sleep 压成 no-op，重试逻辑仍被验证，只是不等。"""
    import lumenis.adapters.base as _base
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


class _QueryAdapter(BaseAdapter):
    platform_name = 'query-test'

    def __init__(self):
        super().__init__()
        self.fail_queries = set()

    def search(self, keyword, max_results=20):
        if keyword in self.fail_queries:
            return AdapterResult(success=False, error='backend unavailable')
        if keyword == 'query-a':
            return AdapterResult(
                success=True,
                notes=[self._make_note(title='A result', content='private A data')],
            )
        if keyword == 'query-recovered':
            return AdapterResult(
                success=True,
                notes=[self._make_note(title='Fresh result', content='fresh data')],
            )
        return AdapterResult(success=False, error='backend unavailable')


_CACHE_CONTEXT = AdapterCacheContext(
    actor_id='actor-1', scope='workspace-1', task_id='task-1',
    source_version='source-v1',
)


def test_failed_different_query_never_reuses_previous_success():
    adapter = _QueryAdapter()
    prior = adapter.collect('query-a')
    failed = adapter.collect('query-b')

    assert prior.success and prior.notes[0].content == 'private A data'
    assert failed.success is False
    assert failed.notes == []
    assert 'backend unavailable' in failed.error


def test_scoped_cache_fallback_requires_exact_complete_identity():
    adapter = _QueryAdapter()
    prior = adapter.collect('query-a', cache_context=_CACHE_CONTEXT)
    adapter.fail_queries.add('query-a')
    fallback = adapter.collect('query-a', cache_context=_CACHE_CONTEXT)

    assert prior.success
    assert fallback.success
    assert fallback.notes == prior.notes
    assert fallback.error.startswith('缓存降级:')


@pytest.mark.parametrize(
    'changed_context',
    [
        AdapterCacheContext('actor-2', 'workspace-1', 'task-1', 'source-v1'),
        AdapterCacheContext('actor-1', 'workspace-2', 'task-1', 'source-v1'),
        AdapterCacheContext('actor-1', 'workspace-1', 'task-2', 'source-v1'),
        AdapterCacheContext('actor-1', 'workspace-1', 'task-1', 'source-v2'),
        AdapterCacheContext('actor-1', '', 'task-1', 'source-v1'),
    ],
)
def test_scoped_cache_fallback_rejects_changed_or_incomplete_identity(changed_context):
    adapter = _QueryAdapter()
    assert adapter.collect('query-a', cache_context=_CACHE_CONTEXT).success
    adapter.fail_queries.add('query-a')

    failed = adapter.collect('query-a', cache_context=changed_context)

    assert failed.success is False
    assert failed.notes == []


@pytest.mark.parametrize(
    ('keyword', 'max_results'),
    [('query-b', 20), ('query-a', 5)],
)
def test_scoped_cache_fallback_rejects_changed_query_or_limit(keyword, max_results):
    adapter = _QueryAdapter()
    assert adapter.collect('query-a', max_results=20,
                           cache_context=_CACHE_CONTEXT).success
    adapter.fail_queries.add('query-a')

    failed = adapter.collect(keyword, max_results=max_results,
                             cache_context=_CACHE_CONTEXT)

    assert failed.success is False
    assert failed.notes == []


def test_unscoped_success_invalidates_prior_scoped_cache_and_live_success_recovers():
    adapter = _QueryAdapter()
    assert adapter.collect('query-a', cache_context=_CACHE_CONTEXT).success
    # An unscoped request must not leave a previous scoped cache eligible.
    assert adapter.collect('query-a').success
    adapter.fail_queries.add('query-a')
    failed = adapter.collect('query-a', cache_context=_CACHE_CONTEXT)
    assert failed.success is False and failed.notes == []

    recovered = adapter.collect('query-recovered', cache_context=_CACHE_CONTEXT)
    assert recovered.success
    assert [note.content for note in recovered.notes] == ['fresh data']


def test_registry_forwards_complete_cache_context_to_existing_adapter():
    adapter = _QueryAdapter()
    registry = AdapterRegistry()
    registry._adapters = {'query-test': adapter}

    live = registry.search_all(
        'query-a', 20, ['query-test'], cache_context=_CACHE_CONTEXT,
    )['query-test']
    adapter.fail_queries.add('query-a')
    merged, status = registry.search_all_with_status(
        'query-a', 20, ['query-test'], cache_context=_CACHE_CONTEXT,
    )

    assert live.success
    assert [note.content for note in merged] == ['private A data']
    assert status[0]['state'] == 'SUCCESS'
    assert status[0]['error'].startswith('缓存降级:')


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
