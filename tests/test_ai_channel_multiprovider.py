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
        monkeypatch.delenv("AI_PROVIDER_CHAIN", raising=False)
        chain = ac.provider_chain()
        assert chain == ["zhipu", "ark", "ollama"]

    def test_custom_chain(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER_CHAIN", "zhipu,ark,qwen")
        assert ac.provider_chain() == ["zhipu", "ark", "qwen"]


class TestRouteWithFallback:
    def test_primary_success(self):
        """主通道成功，不调用备用。"""
        calls = []
        def fn(prov):
            calls.append(prov)
            if prov == "zhipu":
                return "hello from zhipu", "zhipu"
            raise RuntimeError("should not reach backup")
        result, used = ac.route_with_fallback(fn, providers=["zhipu", "ark"])
        assert result == "hello from zhipu"
        assert used == "zhipu"
        assert calls == ["zhipu"]

    def test_fallback_to_backup(self):
        """主通道失败，自动切备用。"""
        calls = []
        def fn(prov):
            calls.append(prov)
            if prov == "zhipu":
                raise ConnectionError("zhipu timeout")
            return "backup result", "ark"
        result, used = ac.route_with_fallback(fn, providers=["zhipu", "ark"])
        assert result == "backup result"
        assert used == "ark"
        assert calls == ["zhipu", "ark"]

    def test_all_fail_returns_rule(self):
        """全部失败，返回 (None, 'rule')。"""
        def fn(prov):
            raise ConnectionError(f"{prov} down")
        result, used = ac.route_with_fallback(fn, providers=["zhipu", "ark"])
        assert result is None
        assert used == "rule"

    def test_breaker_skips_open_provider(self):
        """熔断中的 Provider 被跳过，不浪费调用。"""
        pb = ac.get_provider_breaker("test_open", fail_threshold=1, cooldown_sec=30)
        pb.record_failure("network")  # 触发 OPEN
        calls = []
        def fn(prov):
            calls.append(prov)
            return "ok", prov
        result, used = ac.route_with_fallback(fn, providers=["test_open", "zhipu"])
        # test_open 熔断中被跳过，直接用 zhipu
        assert "test_open" not in calls
        assert used == "zhipu"

    def test_auth_error_no_fallback(self):
        """鉴权错误（不可重试）不切下一个 Provider。"""
        calls = []
        def fn(prov):
            calls.append(prov)
            import urllib.error
            raise urllib.error.HTTPError(None, 401, "Unauthorized", None, None)
        result, used = ac.route_with_fallback(fn, providers=["zhipu", "ark"])
        assert result is None
        assert used == "rule"
        assert calls == ["zhipu"]  # 只调了主通道，没切备用


class TestSnapshots:
    def test_all_snapshots_observable(self):
        ac.get_provider_breaker("obs_test")
        snaps = ac.all_provider_snapshots()
        assert "obs_test" in snaps
        assert "state" in snaps["obs_test"]
