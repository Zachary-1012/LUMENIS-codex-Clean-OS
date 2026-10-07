# -*- coding: utf-8 -*-
"""ai_channel 多 Provider 故障转移层单测（纯逻辑，不发真实网络请求）"""
import pytest
from lumenis.system.ai_gateway import channel as ac


class TestProviderBreaker:
    def test_independent_breaker(self):
        """不同 Provider 熔断互不影响。"""
        a = ac.get_provider_breaker("test_a")
        b = ac.get_provider_breaker("test_b")
        for _ in range(5):
            a.record_failure("network")
        assert a.state == "OPEN"
        assert b.state == "CLOSED"  # b 不受 a 影响

    def test_breaker_allow_then_recover(self):
        pb = ac.get_provider_breaker("test_recover", fail_threshold=2, cooldown_sec=0.01)
        assert pb.allow() is True
        pb.record_failure("network")
        pb.record_failure("network")
        assert pb.allow() is False  # OPEN
        import time; time.sleep(0.02)
        assert pb.allow() is True  # HALF_OPEN after cooldown
        pb.record_success()
        assert pb.state == "CLOSED"


class TestProviderChain:
    def test_default_chain(self, monkeypatch):
        # Retired local/external providers must never be selected implicitly.
        monkeypatch.delenv("AI_PROVIDER_CHAIN", raising=False)
        assert ac.provider_chain() == []

    def test_custom_chain(self, monkeypatch):
        # A retired first candidate fail-closes the whole explicit chain.
        monkeypatch.setenv("AI_PROVIDER_CHAIN", "zhipu,ark,qwen")
        assert ac.provider_chain() == []


class TestRouteWithFallback:
    def test_primary_success(self, monkeypatch):
        """主通道成功，不调用备用。"""
        calls = []
        def fn(prov):
            calls.append(prov)
            if prov == "mock-primary":
                return "hello from mock-primary", "mock-primary"
            raise RuntimeError("should not reach backup")
        result, used = ac.route_with_fallback(fn, providers=["mock-primary", "mock-backup"])
        assert result == "hello from mock-primary"
        assert used == "mock-primary"
        assert calls == ["mock-primary"]

    def test_fallback_to_backup(self, monkeypatch):
        """主通道失败，自动切备用。"""
        calls = []
        def fn(prov):
            calls.append(prov)
            if prov == "mock-primary":
                raise ConnectionError("mock primary timeout")
            return "backup result", "mock-backup"
        result, used = ac.route_with_fallback(fn, providers=["mock-primary", "mock-backup"])
        assert result == "backup result"
        assert used == "mock-backup"
        assert calls == ["mock-primary", "mock-backup"]

    def test_all_fail_returns_rule(self, monkeypatch):
        """全部失败，返回 (None, 'rule')。"""
        def fn(prov):
            raise ConnectionError(f"{prov} down")
        result, used = ac.route_with_fallback(fn, providers=["mock-primary", "mock-backup"])
        assert result is None
        assert used == "rule"

    def test_breaker_skips_open_provider(self, monkeypatch):
        """熔断中的 Provider 被跳过，不浪费调用。"""
        pb = ac.get_provider_breaker("test_open", fail_threshold=1, cooldown_sec=30)
        pb.record_failure("network")  # 触发 OPEN
        calls = []
        def fn(prov):
            calls.append(prov)
            return "ok", prov
        result, used = ac.route_with_fallback(fn, providers=["test_open", "mock-backup"])
        # test_open 熔断中被跳过，使用模拟备用路由
        assert "test_open" not in calls
        assert used == "mock-backup"

    def test_auth_error_no_fallback(self, monkeypatch):
        """鉴权错误（不可重试）不切下一个 Provider。"""
        calls = []
        def fn(prov):
            calls.append(prov)
            import urllib.error
            raise urllib.error.HTTPError(None, 401, "Unauthorized", None, None)
        result, used = ac.route_with_fallback(fn, providers=["mock-primary", "mock-backup"])
        assert result is None
        assert used == "rule"
        assert calls == ["mock-primary"]  # 只调了主通道，没切备用


class TestSnapshots:
    def test_all_snapshots_observable(self):
        ac.get_provider_breaker("obs_test")
        snaps = ac.all_provider_snapshots()
        assert "obs_test" in snaps
        assert "state" in snaps["obs_test"]
