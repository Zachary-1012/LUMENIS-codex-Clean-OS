# -*- coding: utf-8 -*-
"""采集 Guard 合规增强：jitter + Retry-After 感知（对标 Scrapling AutoThrottle / polite scraper 五习惯）。
纯增强、不改语义：默认 jitter=True（可关），retry_after 仅在调用方提供时生效。"""
import random
import time
from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
from lumenis.system.collector.guard.analyzer import ResponseAnalyzer
from lumenis.system.collector.guard.state import CollectState


def test_wait_slot_jitter_bounds():
    """jitter 应在 [0.7, 1.3] * interval 区间内，且 sleep 被真实调用。"""
    l = AdaptiveRateLimiter(base_interval=10.0, min_interval=5.0, jitter=True)
    slept = []
    l.wait_slot(sleep=lambda s: slept.append(s))
    assert len(slept) == 1
    got = slept[0]
    assert 10.0 * 0.7 - 1e-6 <= got <= 10.0 * 1.3 + 1e-6, got


def test_jitter_disabled_no_randomization():
    """jitter=False 时保持原固定间隔，回归旧行为。"""
    l = AdaptiveRateLimiter(base_interval=10.0, min_interval=5.0, jitter=False)
    slept = []
    l.wait_slot(sleep=lambda s: slept.append(s))
    assert slept == [10.0]


def test_retry_after_overrides_cooldown():
    """on_failure(retry_after=...) 时冷却时长取 max(退避, retry_after)。"""
    l = AdaptiveRateLimiter(base_interval=10.0, fail_threshold=1, cooldown_seconds=600, jitter=False)
    t0 = time.time()
    l.on_failure(retry_after=120)
    cd = l.remaining_cooldown()
    # 退避 600*2^0=600 > 120，故仍 600
    assert 595 <= cd <= 605, cd


def test_retry_after_longer_wins():
    """retry_after 大于默认退避时，遵循服务端指示。"""
    l = AdaptiveRateLimiter(base_interval=10.0, fail_threshold=1, cooldown_seconds=600, jitter=False)
    l.on_failure(retry_after=3600)  # 服务端要求 1h，远超 30min 封顶
    cd = l.remaining_cooldown()
    assert cd > 3500, cd


def test_retry_after_invalid_ignored():
    """非法 retry_after 应被静默忽略，不影响退避。"""
    l = AdaptiveRateLimiter(base_interval=10.0, fail_threshold=1, cooldown_seconds=600, jitter=False)
    t0 = time.time()
    l.on_failure(retry_after="abc")
    cd = l.remaining_cooldown()
    assert 595 <= cd <= 605, cd


def test_analyzer_returns_retry_after_on_429():
    """classify(429, retry_after=...) 应在结果中回填 retry_after。"""
    r = ResponseAnalyzer.classify(429, '', retry_after=45)
    assert r['state'] == CollectState.WARNING
    assert r.get('retry_after') == 45


def test_analyzer_no_retry_after_when_absent():
    """未提供 retry_after 时结果不含该键（兼容旧行为）。"""
    r = ResponseAnalyzer.classify(429, '')
    assert 'retry_after' not in r
