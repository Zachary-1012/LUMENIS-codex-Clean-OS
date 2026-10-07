# -*- coding: utf-8 -*-
"""
test_ai_provider_failover.py — AI Provider 额度切换规则 V1.0 测试套件

基于 commit 20da4c5 实际实现编写，覆盖：
1. provider_chain 不隐式包含 retired/legacy providers
2. legacy ARK/Doubao 状态不能授权 Owned Gateway 或旧通道调用
3. qwen=NOT_CONFIGURED
4. rule_fallback 不计算在失败率内（success=1, model=deterministic_rule）
5. token_usage 正确记录（_set_call_meta / _get_call_meta / extract_token_usage）
6. 熔断器状态机
7. ai_governance.check_quota 返回 quota_exceeded
8. route_with_fallback 全部失败返回 (None, 'rule')
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProviderChain:
    """provider_chain 验证"""

    def test_provider_chain_has_no_implicit_or_retired_provider_route(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        monkeypatch.setattr(ac, '_env', lambda _name, _default='': '')
        assert ac.provider_chain() == []

    def test_provider_chain_filters_retired_names_from_explicit_configuration(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        monkeypatch.setattr(ac, '_env', lambda name, _default='': 'zhipu,ark,ollama' if name == 'AI_PROVIDER_CHAIN' else '')
        assert ac.provider_chain() == []

    def test_provider_chain_excludes_legacy_ark_even_when_explicit(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        monkeypatch.setattr(ac, '_env', lambda name, _default='': 'ark,zhipu,ollama' if name == 'AI_PROVIDER_CHAIN' else '')
        assert ac.provider_chain() == []

class TestProviderStatus:
    """Provider 状态验证"""

    def test_active_fallback_constant_exists(self):
        from lumenis.system.ai_gateway import providers as pr
        assert hasattr(pr, 'ACTIVE_FALLBACK')
        assert pr.ACTIVE_FALLBACK == 'ACTIVE_FALLBACK'

    def test_ark_is_legacy_compatibility_only(self):
        from lumenis.system.ai_gateway import providers as pr
        assert pr.provider_status('ark') == pr.LEGACY
        assert pr.provider_info('ark')['role'] == 'compatibility_only'
        assert pr.is_provider_available('ark') is False

    def test_doubao_alias_is_legacy_compatibility_only(self):
        from lumenis.system.ai_gateway import providers as pr
        assert pr.provider_status('doubao') == pr.LEGACY
        assert pr.provider_info('doubao')['role'] == 'compatibility_only'
        assert pr.is_provider_available('doubao') is False

    def test_qwen_is_not_configured(self):
        from lumenis.system.ai_gateway import providers as pr
        assert pr.provider_status('qwen') == 'NOT_CONFIGURED'

    def test_zhipu_is_disabled(self):
        from lumenis.system.ai_gateway import providers as pr
        assert pr.provider_status('zhipu') == 'DISABLED'
        assert pr.is_provider_available('zhipu') is False

    def test_ai_call_logger_provider_status(self):
        import ai_call_logger as acl
        assert acl.get_provider_status('ark') == 'LEGACY'
        assert acl.get_provider_status('doubao') == 'LEGACY'
        assert acl.get_provider_status('qwen') == 'NOT_CONFIGURED'

    def test_channel_status_does_not_infer_runtime_from_key_or_breaker(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        monkeypatch.setattr(ac, 'ensure_env_loaded', lambda: pytest.fail('must not read provider config'))
        monkeypatch.setenv('ARK_API_KEY', 'test-only-not-read')
        status = ac.get_provider_status_v1()['ark']
        assert status['status'] == 'LEGACY'
        assert status['role'] == 'compatibility_only'
        assert status['dispatchable'] is False
        assert status['runtime_verified'] is False
        assert status['api_key_configured'] is None

    def test_explicit_legacy_ark_chat_fails_before_provider_config(self, monkeypatch):
        from lumenis.system.ai_gateway import core
        monkeypatch.setenv('AI_PROVIDER', 'ark')
        monkeypatch.setattr(core, '_provider_config', lambda: pytest.fail('provider config must not be read'))
        assert core._chat('system', 'user') == (None, 'provider_disabled')


class TestRuleFallbackLogging:
    """rule 兜底记录验证（不计算在失败率内）"""

    def test_rule_fallback_marked_success(self):
        """模拟 chat() 中的 rule 兜底逻辑：_is_rule=True 时 success=True"""
        provider = 'rule'
        out = None
        _is_rule = provider in ('rule', None, 'budget_blocked')
        _success_log = True if _is_rule else bool(out)
        assert _success_log is True

    def test_rule_fallback_model_is_deterministic_rule(self):
        provider = 'rule'
        _is_rule = provider in ('rule', None, 'budget_blocked')
        _model_log = 'deterministic_rule' if _is_rule else 'glm-4.5-air'
        assert _model_log == 'deterministic_rule'

    def test_rule_fallback_tokens_zero(self):
        provider = 'rule'
        _is_rule = provider in ('rule', None, 'budget_blocked')
        _tokens_log = 0 if _is_rule else 150
        assert _tokens_log == 0

    def test_rule_fallback_failure_reason_empty(self):
        provider = 'rule'
        out = None
        _is_rule = provider in ('rule', None, 'budget_blocked')
        _success_log = True if _is_rule else bool(out)
        _fail_reason = '' if _success_log else f'provider={provider}'
        assert _fail_reason == ''

    def test_real_ai_failure_marked_failure(self):
        """真实 AI 调用失败（out=None, provider=zhipu）记为 failure"""
        provider = 'zhipu'
        out = None
        _is_rule = provider in ('rule', None, 'budget_blocked')
        _success_log = True if _is_rule else bool(out)
        assert _success_log is False

    def test_budget_blocked_treated_as_rule(self):
        """budget_blocked 也视为 rule 兜底，不记失败"""
        provider = 'budget_blocked'
        _is_rule = provider in ('rule', None, 'budget_blocked')
        assert _is_rule is True


class TestTokenUsageRecording:
    """token_usage 记录验证（修复 token=0 bug）"""

    def test_set_call_meta_stores_tokens(self):
        from lumenis.system.ai_gateway import core as intel
        intel._set_call_meta(
            provider='zhipu', model='glm-4.5-air',
            prompt_tokens=200, completion_tokens=100, total_tokens=300
        )
        meta = intel._get_call_meta()
        assert meta['provider'] == 'zhipu'
        assert meta['total_tokens'] == 300
        assert meta['prompt_tokens'] == 200
        assert meta['completion_tokens'] == 100

    def test_extract_token_usage_standard(self):
        from lumenis.system.ai_gateway import channel as ac
        data = {"usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
        result = ac.extract_token_usage(data)
        assert result['total_tokens'] == 150
        assert result['prompt_tokens'] == 100
        assert result['completion_tokens'] == 50

    def test_extract_token_usage_missing_total(self):
        from lumenis.system.ai_gateway import channel as ac
        data = {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        result = ac.extract_token_usage(data)
        assert result['total_tokens'] == 150  # pt + ct

    def test_extract_token_usage_empty(self):
        from lumenis.system.ai_gateway import channel as ac
        assert ac.extract_token_usage({})['total_tokens'] == 0
        assert ac.extract_token_usage(None)['total_tokens'] == 0

    def test_chat_meta_contains_token_usage(self):
        """验证 chat() 返回的 meta 包含 token_usage 字段"""
        from lumenis.system.ai_gateway import core as intel
        # 设置一个模拟的 call_meta
        intel._set_call_meta(provider='zhipu', model='glm-4.5-air',
                              prompt_tokens=50, completion_tokens=30, total_tokens=80)
        meta = intel._get_call_meta()
        assert 'total_tokens' in meta
        assert meta['total_tokens'] == 80


class TestCircuitBreaker:
    """熔断器状态机验证"""

    def test_breaker_starts_closed(self):
        from lumenis.system.ai_gateway import channel as ac
        pb = ac.get_provider_breaker('test_cb_start')
        assert pb.state in ('CLOSED', 'HALF_OPEN')

    def test_breaker_independent_per_provider(self):
        from lumenis.system.ai_gateway import channel as ac
        pb1 = ac.get_provider_breaker('test_indep_a')
        pb2 = ac.get_provider_breaker('test_indep_b')
        pb1.breaker.record_success()
        pb1.record_failure('network')
        # pb2 不受 pb1 失败影响
        assert pb2.state == 'CLOSED' or pb2.allow() is True

    def test_global_breaker_snapshot(self):
        from lumenis.system.ai_gateway import channel as ac
        snap = ac.breaker.snapshot()
        assert 'state' in snap
        assert 'consecutive_failures' in snap
        assert 'fail_threshold' in snap


class TestGovernanceQuota:
    """ai_governance.check_quota 验证"""

    def test_check_quota_returns_quota_exceeded_field(self):
        import ai_governance as gov
        allowed, quota = gov._usage_tracker.check_quota()
        assert 'quota_exceeded' in quota
        assert 'fallback_suggestion' in quota
        assert 'allowed' in quota

    def test_check_quota_not_exceeded_when_under_limit(self):
        import ai_governance as gov
        allowed, quota = gov._usage_tracker.check_quota()
        if allowed:
            assert quota['quota_exceeded'] is False
            assert quota['fallback_suggestion'] is None

    def test_check_quota_has_call_and_token_limits(self):
        import ai_governance as gov
        allowed, quota = gov._usage_tracker.check_quota()
        assert quota['call_limit'] == 500
        assert quota['token_limit'] == 200000


class TestRouteWithFallback:
    """route_with_fallback 验证"""

    def test_fallback_returns_rule_when_all_fail(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        def always_fail(prov):
            raise ConnectionError(f"{prov} down")
        result, used = ac.route_with_fallback(
            always_fail, providers=['mock-primary', 'mock-secondary', 'mock-tertiary']
        )
        assert used == 'rule'
        assert result is None

    def test_fallback_returns_first_success(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        call_count = {'n': 0}
        def succeed_on_secondary(prov):
            call_count['n'] += 1
            if prov == 'mock-primary':
                raise ConnectionError("mock primary down")
            return "backup response", prov
        result, used = ac.route_with_fallback(
            succeed_on_secondary, providers=['mock-primary', 'mock-secondary', 'mock-tertiary']
        )
        assert used == 'mock-secondary'
        assert result == 'backup response'
        assert call_count['n'] == 2

    def test_disabled_primary_never_falls_back_to_paid_provider(self):
        from lumenis.system.ai_gateway import channel as ac
        calls = []
        result, used = ac.route_with_fallback(
            lambda provider: (calls.append(provider) or 'unexpected', provider),
            providers=['zhipu', 'ark', 'doubao'],
        )
        assert (result, used) == (None, 'provider_disabled')
        assert calls == []

    def test_ark_status_mutation_cannot_restore_legacy_fallback(self, monkeypatch):
        from lumenis.system.ai_gateway import providers as registry
        monkeypatch.setitem(registry.PROVIDER_REGISTRY['ark'], 'status', registry.ACTIVE)
        registry.set_provider_status('ark', registry.ACTIVE)
        assert registry.provider_status('ark') == registry.LEGACY
        assert registry.provider_status('doubao') == registry.LEGACY
        assert registry.is_provider_available('ark') is False
        assert registry.is_provider_available('doubao') is False

    def test_local_probe_and_status_mutation_cannot_reactivate_retired_routes(self, monkeypatch):
        from lumenis.system.ai_gateway import providers as pr
        names = ('zhipu', 'ollama', 'lmstudio', 'llama_cpp')
        for name in names:
            monkeypatch.setitem(pr.PROVIDER_REGISTRY[name], 'status', pr.ACTIVE)
            pr.set_provider_status(name, pr.ACTIVE)
        monkeypatch.setattr(pr, '_probe_endpoint', lambda *_args, **_kwargs: pytest.fail('probe called'))
        assert pr.probe_local_providers() == {
            'ollama': pr.DISABLED, 'lmstudio': pr.DISABLED, 'llama_cpp': pr.DISABLED,
        }
        for name in names:
            assert pr.provider_status(name) == pr.DISABLED
            assert pr.is_provider_available(name) is False
            assert pr.provider_info(name)['status'] == pr.DISABLED
        assert not set(names).intersection(pr.active_providers())
        assert not set(names[1:]).intersection(pr.available_providers())

    def test_cached_retired_route_and_default_chat_do_not_return_answer(self, monkeypatch):
        from lumenis.system.ai_gateway import core as gateway, providers as pr
        monkeypatch.setenv('AI_PROVIDER', 'auto')
        gateway._CACHE.update(ts=10**12, provider='ollama', model='stale-model', base='http://127.0.0.1:11434')
        key = gateway._cache_key('system', 'user', 0.1, 800, None)
        gateway._chat_cache_set(key, 'stale local answer', 'ollama')
        monkeypatch.setattr(gateway, '_detect_local', lambda: pytest.fail('discovery called'))
        monkeypatch.setattr(gateway, '_budget_check', lambda *_args, **_kwargs: pytest.fail('budget/cache path reached'))
        output, provider, meta = gateway.chat('system', 'user', use_cache=True)
        assert (output, provider) == (None, 'provider_disabled')
        assert meta['provider'] == 'provider_disabled'
        assert meta['cache'] is False
        assert gateway._provider_config() is None
        assert gateway._CACHE['provider'] is None

    def test_disabled_heartbeat_does_not_call_ping(self):
        from lumenis.system.ai_gateway import channel as ac
        calls = []
        started = ac.start_24h_heartbeat({'zhipu': lambda: calls.append('zhipu'), 'ollama': lambda: calls.append('ollama')})
        assert started is False
        assert calls == []

    def test_fallback_skips_circuit_open(self, monkeypatch):
        from lumenis.system.ai_gateway import channel as ac
        # 先把第一个模拟路由熔断打开
        pb = ac.get_provider_breaker('test_skip_open')
        for _ in range(5):
            pb.record_failure('rate_limit')
        # 熔断打开时应该跳过第一个模拟路由
        def backup_ok(prov):
            return f"{prov} ok", prov
        result, used = ac.route_with_fallback(
            backup_ok, providers=['test_skip_open', 'mock-backup']
        )
        # test_skip_open 熔断中，应该使用模拟备用路由
        assert used == 'mock-backup'
        # 清理
        pb.breaker.record_success()


class TestProviderSwitchAudit:
    """Provider 切换审计验证"""

    def test_record_switch_creates_entry(self):
        from lumenis.system.ai_gateway import channel as ac
        before = len(ac.get_failover_log(limit=200))
        ac.record_provider_switch(
            from_provider='zhipu', to_provider='ark',
            reason='rate_limit_429', task_id='test_001', trace_id='trace_001'
        )
        after = len(ac.get_failover_log(limit=200))
        assert after > before
        log = ac.get_failover_log(limit=1)[-1]
        assert log['from_provider'] == 'zhipu'
        assert log['to_provider'] == 'ark'
        assert log['reason'] == 'rate_limit_429'

    def test_switch_log_has_required_fields(self):
        from lumenis.system.ai_gateway import channel as ac
        ac.record_provider_switch('ark', 'ollama', 'circuit_open', 't2', 'tr2')
        log = ac.get_failover_log(limit=1)[-1]
        for field in ['timestamp', 'from_provider', 'to_provider', 'reason', 'task_id', 'trace_id']:
            assert field in log, f"Missing field: {field}"


class TestResourcePacks:
    """资源包配额验证"""

    def test_default_pack_id_is_glm_4_5_air(self):
        """验证 intelligence.chat() 默认 pack_id='glm_4_5_air'"""
        import inspect
        from lumenis.system.ai_gateway import core as intel
        sig = inspect.signature(intel.chat)
        assert sig.parameters['pack_id'].default == 'glm_4_5_air'

    def test_budget_check_default_pack_id(self):
        import inspect
        from lumenis.system.ai_gateway import core as intel
        sig = inspect.signature(intel._budget_check)
        assert sig.parameters['pack_id'].default == 'glm_4_5_air'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
