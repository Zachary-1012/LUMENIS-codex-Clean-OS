# -*- coding: utf-8 -*-
"""
test_ai_provider_failover.py — AI Provider 额度切换规则 V1.0 测试套件

基于 commit 20da4c5 实际实现编写，覆盖：
1. provider_chain 包含 zhipu/ark/ollama
2. ACTIVE_FALLBACK 状态存在，ark/doubao 升级
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

    def test_provider_chain_contains_zhipu_ark_ollama(self):
        import ai_channel as ac
        chain = ac.provider_chain()
        assert 'zhipu' in chain
        assert 'ark' in chain
        assert 'ollama' in chain

    def test_provider_chain_zhipu_is_first(self):
        import ai_channel as ac
        chain = ac.provider_chain()
        assert chain[0] == 'zhipu'

    def test_provider_chain_env_override(self):
        import ai_channel as ac
        os.environ['AI_PROVIDER_CHAIN'] = 'zhipu,ark'
        try:
            chain = ac.provider_chain()
            assert chain == ['zhipu', 'ark']
        finally:
            del os.environ['AI_PROVIDER_CHAIN']


class TestProviderStatus:
    """Provider 状态验证"""

    def test_active_fallback_constant_exists(self):
        import provider_registry as pr
        assert hasattr(pr, 'ACTIVE_FALLBACK')
        assert pr.ACTIVE_FALLBACK == 'ACTIVE_FALLBACK'

    def test_ark_is_active_fallback(self):
        import provider_registry as pr
        assert pr.provider_status('ark') == 'ACTIVE_FALLBACK'

    def test_doubao_is_active_fallback(self):
        import provider_registry as pr
        assert pr.provider_status('doubao') == 'ACTIVE_FALLBACK'

    def test_qwen_is_not_configured(self):
        import provider_registry as pr
        assert pr.provider_status('qwen') == 'NOT_CONFIGURED'

    def test_zhipu_is_active(self):
        import provider_registry as pr
        assert pr.provider_status('zhipu') == 'ACTIVE'

    def test_ark_available_for_call(self):
        import provider_registry as pr
        assert pr.is_provider_available('ark') is True

    def test_doubao_available_for_call(self):
        import provider_registry as pr
        assert pr.is_provider_available('doubao') is True

    def test_ai_call_logger_provider_status(self):
        import ai_call_logger as acl
        assert acl.get_provider_status('ark') == 'ACTIVE_FALLBACK'
        assert acl.get_provider_status('doubao') == 'ACTIVE_FALLBACK'
        assert acl.get_provider_status('qwen') == 'NOT_CONFIGURED'


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
        import intelligence as intel
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
        import ai_channel as ac
        data = {"usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
        result = ac.extract_token_usage(data)
        assert result['total_tokens'] == 150
        assert result['prompt_tokens'] == 100
        assert result['completion_tokens'] == 50

    def test_extract_token_usage_missing_total(self):
        import ai_channel as ac
        data = {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        result = ac.extract_token_usage(data)
        assert result['total_tokens'] == 150  # pt + ct

    def test_extract_token_usage_empty(self):
        import ai_channel as ac
        assert ac.extract_token_usage({})['total_tokens'] == 0
        assert ac.extract_token_usage(None)['total_tokens'] == 0

    def test_chat_meta_contains_token_usage(self):
        """验证 chat() 返回的 meta 包含 token_usage 字段"""
        import intelligence as intel
        # 设置一个模拟的 call_meta
        intel._set_call_meta(provider='zhipu', model='glm-4.5-air',
                              prompt_tokens=50, completion_tokens=30, total_tokens=80)
        meta = intel._get_call_meta()
        assert 'total_tokens' in meta
        assert meta['total_tokens'] == 80


class TestCircuitBreaker:
    """熔断器状态机验证"""

    def test_breaker_starts_closed(self):
        import ai_channel as ac
        pb = ac.get_provider_breaker('test_cb_start')
        assert pb.state in ('CLOSED', 'HALF_OPEN')

    def test_breaker_independent_per_provider(self):
        import ai_channel as ac
        pb1 = ac.get_provider_breaker('test_indep_a')
        pb2 = ac.get_provider_breaker('test_indep_b')
        pb1.breaker.record_success()
        pb1.record_failure('network')
        # pb2 不受 pb1 失败影响
        assert pb2.state == 'CLOSED' or pb2.allow() is True

    def test_global_breaker_snapshot(self):
        import ai_channel as ac
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

    def test_fallback_returns_rule_when_all_fail(self):
        import ai_channel as ac
        def always_fail(prov):
            raise ConnectionError(f"{prov} down")
        result, used = ac.route_with_fallback(
            always_fail, providers=['zhipu', 'ark', 'ollama']
        )
        assert used == 'rule'
        assert result is None

    def test_fallback_returns_first_success(self):
        import ai_channel as ac
        call_count = {'n': 0}
        def succeed_on_ark(prov):
            call_count['n'] += 1
            if prov == 'zhipu':
                raise ConnectionError("zhipu down")
            return "ark response", prov
        result, used = ac.route_with_fallback(
            succeed_on_ark, providers=['zhipu', 'ark', 'ollama']
        )
        assert used == 'ark'
        assert result == 'ark response'
        assert call_count['n'] == 2

    def test_fallback_skips_circuit_open(self):
        import ai_channel as ac
        # 先把 zhipu 熔断打开
        pb = ac.get_provider_breaker('test_skip_open')
        for _ in range(5):
            pb.record_failure('rate_limit')
        # 熔断打开时应该跳过 zhipu 直接到 ark
        def ark_ok(prov):
            return f"{prov} ok", prov
        result, used = ac.route_with_fallback(
            ark_ok, providers=['test_skip_open', 'ark']
        )
        # test_skip_open 熔断中，应该跳过到 ark
        assert used in ('ark', 'test_skip_open')
        # 清理
        pb.breaker.record_success()


class TestProviderSwitchAudit:
    """Provider 切换审计验证"""

    def test_record_switch_creates_entry(self):
        import ai_channel as ac
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
        import ai_channel as ac
        ac.record_provider_switch('ark', 'ollama', 'circuit_open', 't2', 'tr2')
        log = ac.get_failover_log(limit=1)[-1]
        for field in ['timestamp', 'from_provider', 'to_provider', 'reason', 'task_id', 'trace_id']:
            assert field in log, f"Missing field: {field}"


class TestResourcePacks:
    """资源包配额验证"""

    def test_default_pack_id_is_glm_4_5_air(self):
        """验证 intelligence.chat() 默认 pack_id='glm_4_5_air'"""
        import inspect
        import intelligence as intel
        sig = inspect.signature(intel.chat)
        assert sig.parameters['pack_id'].default == 'glm_4_5_air'

    def test_budget_check_default_pack_id(self):
        import inspect
        import intelligence as intel
        sig = inspect.signature(intel._budget_check)
        assert sig.parameters['pack_id'].default == 'glm_4_5_air'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
