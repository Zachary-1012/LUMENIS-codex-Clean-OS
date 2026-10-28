# -*- coding: utf-8 -*-
"""
tests/test_ai_evaluation.py — ZBC Phase 7 AI Evaluation 体系测试

覆盖：
1. AI 调用追踪记录（log_call / @log_ai_call 装饰器）
2. Evaluation 指标计算（准确率 / 替代率 / 修正率 / 置信度分布 / 失败率 / 回退率 / 延迟 / token）
3. AI 不替代主体过滤（subject_hit 优先于 AI）
4. Provider fallback（退役路线 fail closed；active mock routes retain fallback）
5. 人工修正反馈闭环

所有测试使用临时 SQLite 数据库，不触碰生产库；不执行真实 AI 调用（全部 mock）。
"""
import json
import os
import sys
import time
from unittest.mock import patch, MagicMock

import pytest

import ai_call_logger as acl
from lumenis.shared.evaluation import ai as aev
from lumenis.shared.database.repository import DatabaseRepository


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """每个测试函数使用独立的临时 SQLite 数据库。"""
    db_file = tmp_path / 'test_ai_eval.db'
    repository = DatabaseRepository(str(db_file))
    # Explicitly inject one temp repository into both database consumers. This
    # keeps production default resolution dynamic and the tests hermetic.
    monkeypatch.setattr(acl, 'get_repository', lambda: repository)
    monkeypatch.setattr(aev, 'get_repository', lambda: repository)
    acl.init_db()
    return str(db_file)


def _seed_calls(test_db, calls):
    """向测试库批量写入调用记录。"""
    conn = acl.get_repository().connect()
    conn.executescript(acl._SCHEMA)
    for c in calls:
        conn.execute(
            """INSERT INTO ai_call_logs
               (provider, model, prompt_version, input_hash, output,
                confidence, rule_result, final_result, human_correction,
                latency_ms, token_usage, failure_reason, success)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                c.get('provider', 'zhipu'),
                c.get('model', 'glm-4.5-air'),
                c.get('prompt_version', ''),
                c.get('input_hash', ''),
                c.get('output', ''),
                c.get('confidence', 0.0),
                c.get('rule_result', ''),
                c.get('final_result', ''),
                c.get('human_correction', ''),
                c.get('latency_ms', 0),
                c.get('token_usage', 0),
                c.get('failure_reason', ''),
                1 if c.get('success', True) else 0,
            ),
        )
    conn.commit()
    conn.close()


def _typed_conversation_request(turn_suffix='a'):
    from lumenis.ai_hub import conversations
    turn_id = 'turn_' + turn_suffix * 32
    material = {
        'conversation_id': 'conv_' + 'c' * 32,
        'response_turn_id': turn_id,
        'user_turn_id': 'turn_' + 'b' * 32,
        'actor_ref': 'actor:synthetic-evaluation-user',
        'workspace_binding': 'a' * 64,
        'scope': dict(conversations._SCOPE),
        'question': 'PRIVATE_EVALUATION_QUESTION_7e29',
        'history': [{'role': 'user', 'content': 'PRIVATE_EVALUATION_HISTORY_3a10'}],
        'context_accounting': {'context_pack_sha256': 'd' * 64},
        'source_use_mode': 'source_free',
    }
    return conversations._conversation_request(material)


def _completed_owned_result(request, *, attempt_id='attempt_' + '1' * 32):
    from lumenis.system.ai_gateway.owned_service import owned_service_request_digest
    return {
        'ok': True, 'status': 'COMPLETED', 'code': 'OWNED_INFERENCE_COMPLETED',
        'provider': 'owned', 'attempt_id': attempt_id, 'run_id': 'synthetic-run-1',
        'request_digest': owned_service_request_digest(request),
        'operation': request.operation, 'domain_id': request.domain_id, 'scope': request.scope,
        'input_revision_sha256': request.input_revision_sha256,
        'source_binding_sha256': request.source_binding_sha256,
        'real_input_bound': True, 'model_id': 'synthetic-owned-cpu',
        'model_revision': 'synthetic-rev-1', 'runtime_sha256': 'e' * 64,
        'executor_sha256': 'f' * 64, 'text': 'PRIVATE_EVALUATION_OUTPUT_5c31',
        'prompt_tokens': 9, 'completion_tokens': 4, 'total_tokens': 13,
    }


# ============================================================
# 1. AI 调用追踪记录
# ============================================================
class TestAICallLogger:
    def test_log_call_success(self, test_db):
        log_id = acl.log_call(
            provider='zhipu', model='glm-4.5-air',
            prompt_version='v1-sentiment',
            input_hash='abc123', output='{"sentiment":"positive"}',
            confidence=0.85, latency_ms=1200, token_usage=150,
            success=True,
        )
        assert log_id is not None
        assert log_id > 0

    def test_log_call_failure(self, test_db):
        log_id = acl.log_call(
            provider='zhipu', model='glm-4.5-air',
            failure_reason='ConnectionError: timeout',
            success=False, latency_ms=5000,
        )
        assert log_id is not None
        rows = acl.query_calls(success=False)
        assert len(rows) >= 1
        assert rows[0]['failure_reason'] == 'ConnectionError: timeout'

    def test_log_call_bypass_on_db_error(self, test_db, monkeypatch):
        """日志写入失败时绝不抛出异常（旁路原则）。"""
        def _boom(*args, **kwargs):
            raise RuntimeError('simulated db failure')
        monkeypatch.setattr(acl, '_get_conn', _boom)
        # 不应抛出
        result = acl.log_call(provider='zhipu', output='test')
        assert result is None

    def test_compute_input_hash_deterministic(self):
        h1 = acl.compute_input_hash('system', 'user', 'level')
        h2 = acl.compute_input_hash('system', 'user', 'level')
        assert h1 == h2
        h3 = acl.compute_input_hash('system', 'different', 'level')
        assert h1 != h3

    def test_log_ai_call_decorator_success(self, test_db):
        @acl.log_ai_call(provider='zhipu', model='glm-4.5-air', prompt_version='test-v1')
        def fake_ai(text):
            return {'reply': f'processed: {text}', 'confidence': 0.9, 'provider': 'zhipu'}

        result = fake_ai('hello')
        assert result['reply'] == 'processed: hello'
        rows = acl.query_calls(provider='zhipu')
        assert len(rows) >= 1
        assert rows[0]['success'] == 1
        assert 'processed: hello' in rows[0]['output']

    def test_log_ai_call_decorator_failure_reraises(self, test_db):
        @acl.log_ai_call(provider='zhipu', prompt_version='test-fail')
        def failing_ai():
            raise ValueError('AI exploded')

        with pytest.raises(ValueError, match='AI exploded'):
            failing_ai()
        # 失败应被记录
        rows = acl.query_calls(success=False)
        assert len(rows) >= 1
        assert 'AI exploded' in rows[0]['failure_reason']

    def test_log_ai_call_decorator_with_extractors(self, test_db):
        @acl.log_ai_call(
            provider='zhipu',
            extract_output=lambda r: r.get('text', ''),
            extract_confidence=lambda r: r.get('score', 0),
            extract_tokens=lambda r: r.get('tokens', 0),
        )
        def custom_ai():
            return {'text': 'custom output', 'score': 0.75, 'tokens': 200}

        custom_ai()
        rows = acl.query_calls()
        assert rows[0]['output'] == 'custom output'
        assert abs(rows[0]['confidence'] - 0.75) < 0.01
        assert rows[0]['token_usage'] == 200

    def test_query_calls_filtering(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'output': 'ok1'},
            {'provider': 'zhipu', 'success': False, 'output': '', 'failure_reason': 'err'},
            {'provider': 'ollama', 'success': True, 'output': 'ok2'},
        ])
        zhipu_rows = acl.query_calls(provider='zhipu')
        assert len(zhipu_rows) == 2
        success_rows = acl.query_calls(success=True)
        assert all(r['success'] == 1 for r in success_rows)

    def test_get_stats(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'latency_ms': 100, 'token_usage': 50, 'confidence': 0.8},
            {'provider': 'zhipu', 'success': True, 'latency_ms': 300, 'token_usage': 150, 'confidence': 0.6},
            {'provider': 'zhipu', 'success': False, 'latency_ms': 5000, 'failure_reason': 'timeout'},
        ])
        stats = acl.get_stats(provider='zhipu')
        assert stats['total'] == 3
        assert stats['success_count'] == 2
        assert stats['failure_count'] == 1
        assert abs(stats['failure_rate'] - 1/3) < 0.01
        assert stats['total_tokens'] == 200

    def test_provider_status_registry(self):
        assert acl.get_provider_status('zhipu') == 'DISABLED'
        assert acl.get_provider_status('ark') == 'DISABLED'
        assert acl.get_provider_status('ollama') == 'DISABLED'
        assert acl.get_provider_status('nonexistent') == 'UNKNOWN'


# ============================================================
# 2. Evaluation 指标计算
# ============================================================
class TestAIEvaluation:
    def test_evaluate_empty_db(self, test_db):
        result = aev.evaluate_ai_quality()
        assert result['total_calls'] == 0
        assert result['ai_accuracy'] is None
        assert result['rule_agreement_rate'] is None
        assert result['state'] == 'NO_SAMPLES'
        assert result['fallback_rate'] is None

    def test_evaluate_ai_accuracy(self, test_db):
        # 3 条可对比记录：2 条 AI 与规则一致，1 条不一致
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True,
             'rule_result': '{"sentiment":"positive"}',
             'output': '{"sentiment":"positive"}',
             'final_result': '{"sentiment":"positive"}'},
            {'provider': 'zhipu', 'success': True,
             'rule_result': '{"sentiment":"negative"}',
             'output': '{"sentiment":"negative"}',
             'final_result': '{"sentiment":"negative"}'},
            {'provider': 'zhipu', 'success': True,
             'rule_result': '{"sentiment":"neutral"}',
             'output': '{"sentiment":"positive"}',
             'final_result': '{"sentiment":"neutral"}'},
        ])
        result = aev.evaluate_ai_quality()
        assert result['total_calls'] == 3
        assert abs(result['ai_accuracy'] - 2/3) < 0.01

    def test_evaluate_ai_replacement_rate(self, test_db):
        # final_result 等于 AI output = AI 被采用
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True,
             'rule_result': '{"sentiment":"neutral"}',
             'output': '{"sentiment":"positive"}',
             'final_result': '{"sentiment":"positive"}'},  # AI 替代
            {'provider': 'zhipu', 'success': True,
             'rule_result': '{"sentiment":"negative"}',
             'output': '{"sentiment":"negative"}',
             'final_result': '{"sentiment":"negative"}'},  # 一致，不算替代
        ])
        result = aev.evaluate_ai_quality()
        # 只有 1 条 AI 结果与规则不同且被采用
        assert result['ai_replacement_rate'] <= 0.5

    def test_evaluate_human_correction_rate(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'human_correction': '修正为负面'},
            {'provider': 'zhipu', 'success': True, 'human_correction': ''},
            {'provider': 'zhipu', 'success': True, 'human_correction': ''},
            {'provider': 'zhipu', 'success': True, 'human_correction': ''},
        ])
        result = aev.evaluate_ai_quality()
        assert result['human_correction_rate'] is None
        assert result['human_correction_count'] == 1
        assert result['human_correction_state'] == 'REVIEW_DENOMINATOR_NOT_RECORDED'
        assert result['human_review_coverage']['reviewed_calls'] is None

    def test_evaluate_confidence_distribution(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'confidence': 0.2},   # low
            {'provider': 'zhipu', 'success': True, 'confidence': 0.5},   # medium
            {'provider': 'zhipu', 'success': True, 'confidence': 0.9},   # high
            {'provider': 'zhipu', 'success': True, 'confidence': 0.85},  # high
        ])
        result = aev.evaluate_ai_quality()
        dist = result['confidence_distribution']
        assert abs(dist['low'] - 0.25) < 0.01
        assert abs(dist['medium'] - 0.25) < 0.01
        assert abs(dist['high'] - 0.5) < 0.01

    def test_evaluate_provider_failure_rate(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True},
            {'provider': 'zhipu', 'success': True},
            {'provider': 'zhipu', 'success': False, 'failure_reason': 'timeout'},
            {'provider': 'ollama', 'success': True},
            {'provider': 'ollama', 'success': False, 'failure_reason': 'conn refused'},
        ])
        result = aev.evaluate_ai_quality()
        pfr = result['provider_failure_rate']
        assert abs(pfr['zhipu'] - 1/3) < 0.01
        assert abs(pfr['ollama'] - 0.5) < 0.01

    def test_evaluate_fallback_rate(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True},
            {'provider': 'rule', 'success': True},
            {'provider': 'local_rule', 'success': True},
            {'provider': 'zhipu', 'success': True},
        ])
        result = aev.evaluate_ai_quality()
        assert abs(result['fallback_rate'] - 0.5) < 0.01

    def test_evaluate_latency_stats(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'latency_ms': 100},
            {'provider': 'zhipu', 'success': True, 'latency_ms': 200},
            {'provider': 'zhipu', 'success': True, 'latency_ms': 300},
            {'provider': 'zhipu', 'success': True, 'latency_ms': 5000},
        ])
        result = aev.evaluate_ai_quality()
        lat = result['latency']
        assert lat['avg_ms'] == 1400  # (100+200+300+5000)/4
        assert lat['max_ms'] == 5000
        assert lat['p50_ms'] >= 200

    def test_evaluate_token_cost(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'token_usage': 100},
            {'provider': 'zhipu', 'success': True, 'token_usage': 300},
        ])
        result = aev.evaluate_ai_quality()
        assert result['token_cost']['total_tokens'] == 400
        assert result['token_cost']['avg_tokens'] == 200

    def test_record_rule_vs_ai(self, test_db):
        log_id = aev.record_rule_vs_ai(
            provider='zhipu', model='glm-4.5-air',
            rule_result='{"sentiment":"neutral"}',
            ai_result='{"sentiment":"positive"}',
            final_result='{"sentiment":"neutral"}',  # 规则优先
            confidence=0.6, prompt_version='v1-sentiment',
            latency_ms=800, token_usage=120,
        )
        assert log_id is not None
        rows = acl.query_calls()
        assert rows[0]['rule_result'] == '{"sentiment":"neutral"}'
        assert rows[0]['final_result'] == '{"sentiment":"neutral"}'

    def test_results_match_json(self):
        assert aev._results_match(
            '{"sentiment":"positive","risk_level":"low"}',
            '{"sentiment":"positive","risk_level":"low","extra":"ignored"}'
        ) is True
        assert aev._results_match(
            '{"sentiment":"positive"}',
            '{"sentiment":"negative"}'
        ) is False

    def test_results_match_text(self):
        assert aev._results_match('hello world', 'hello  world') is True
        assert aev._results_match('hello', 'world') is False

    def test_evaluate_provider_health(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'latency_ms': 100},
            {'provider': 'zhipu', 'success': True, 'latency_ms': 200},
            {'provider': 'ark', 'success': False, 'latency_ms': 5000, 'failure_reason': 'disabled'},
        ])
        health = aev.evaluate_provider_health()
        assert 'zhipu' in health
        assert health['zhipu']['status'] == 'HEALTHY'
        assert health['ark']['failure_rate'] == 1.0
        assert health['ark']['status'] in ('UNHEALTHY', 'DEGRADED')

    def test_generate_evaluation_report(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'confidence': 0.8,
             'rule_result': '{"sentiment":"positive"}',
             'output': '{"sentiment":"positive"}',
             'final_result': '{"sentiment":"positive"}',
             'latency_ms': 100, 'token_usage': 50},
        ])
        report = aev.generate_evaluation_report()
        assert 'AI 质量评估报告' in report
        assert '总调用次数' in report
        assert 'AI与规则一致率（非独立正确率）: 100.0%' in report
        assert 'AI 准确率:' not in report


# ============================================================
# 3. AI 不替代主体过滤
# ============================================================
class TestAINotReplacingRules:
    def test_subject_hit_before_ai(self):
        """验证 subject_hit() 是独立的确定性函数，不依赖 AI。"""
        from subject_rules import subject_hit as unfocused_hit, subject_hit_for_brand
        from functools import partial
        assert unfocused_hit(title='广州太古汇探店') is False
        subject_hit = partial(subject_hit_for_brand, brand_key='guangzhou_taikoo_hui')
        # Explicit Guangzhou focus, never inferred from unbound text
        # 广州太古汇应命中
        assert subject_hit(title='广州太古汇探店', body='', content='') is True
        # 上海太古汇应被排除
        assert subject_hit(title='上海太古汇', body='', content='') is False
        # 无关内容不命中
        assert subject_hit(title='今天天气真好', body='', content='') is False

    def test_ai_analyzer_subject_filter_constant(self):
        """ai_analyzer 模块声明主体过滤在 AI 之前。"""
        import ai_analyzer
        assert hasattr(ai_analyzer, 'SUBJECT_FILTER_BEFORE_AI')
        assert ai_analyzer.SUBJECT_FILTER_BEFORE_AI is True
        assert ai_analyzer.MODULE_STATUS == 'RULES_ENGINE_PRIMARY'
        assert ai_analyzer.AI_ROLE == 'AUXILIARY_ONLY'

    def test_ai_filter_subject_first(self):
        """ai_filter 模块声明主体过滤是第一道关。"""
        import ai_filter
        assert hasattr(ai_filter, 'SUBJECT_FILTER_FIRST')
        assert ai_filter.SUBJECT_FILTER_FIRST is True
        assert ai_filter.AI_ROLE == 'SECONDARY_REVIEW_ONLY'

    def test_ai_filter_rule_layer_before_ai(self):
        """ai_filter.ai_secondary_review 中规则层（质量/去重/垃圾）在 AI 调用之前。"""
        import ai_filter
        # 营销内容应被规则层直接拒绝，不调用 AI
        note = {
            'title': '加微信代购最低价',
            'content': '加v xxx 代购 全网最低 扫码',
            'likes': 0, 'comments': 0,
        }
        with patch('ai_filter.intelligence') as mock_intel:
            mock_intel.ai_enabled.return_value = True
            result = ai_filter.ai_secondary_review(note)
        assert result['status'] == 'rejected'
        assert result['provider'] == 'rule'  # 规则层拒绝，未走 AI
        mock_intel.chat.assert_not_called()  # AI 未被调用

    def test_verify_ai_not_replacing_rules_empty(self, test_db):
        """无样本不能当作安全验证通过。"""
        result = aev.verify_ai_not_replacing_rules()
        assert result['passed'] is False
        assert result['state'] == 'UNKNOWN'

    def test_verify_ai_not_replacing_rules_with_data(self, test_db):
        """规则优先的数据应通过验证。"""
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True,
             'rule_result': '{"sentiment":"neutral"}',
             'output': '{"sentiment":"positive"}',
             'final_result': '{"sentiment":"neutral"}'},  # final = rule
        ])
        result = aev.verify_ai_not_replacing_rules()
        assert 'checks' in result
        assert isinstance(result['passed'], bool)

    def test_subject_filter_calls_not_ai_replaced(self, test_db):
        """主体过滤相关调用（prompt_version 含 subject）的 AI 替代率应为 0。"""
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'prompt_version': 'subject-filter-v1',
             'rule_result': '{"relevance":"relevant"}',
             'output': '{"relevance":"relevant"}',
             'final_result': '{"relevance":"relevant"}'},
        ])
        result = aev.verify_ai_not_replacing_rules()
        # 找到 subject 检查项
        subject_check = [c for c in result['checks']
                         if c['name'] == 'subject_filter_not_ai_replaced']
        assert len(subject_check) == 1
        assert subject_check[0]['passed'] is True

# ============================================================
# 4. Provider Fallback
# ============================================================
class TestProviderFallback:
    def test_provider_chain_default(self, monkeypatch):
        """No implicit chain is synthesized from retired-provider metadata."""
        from lumenis.system.ai_gateway import channel
        monkeypatch.setattr(channel, '_env', lambda name, _default='': '')
        assert channel.provider_chain() == []
        assert channel.full_fallback_chain() == []

    def test_route_with_fallback_all_fail(self):
        """选中已退役路由时 fail closed，且不启动任何后备通道。"""
        from lumenis.system.ai_gateway import channel

        def always_fail(provider):
            raise ConnectionError(f'{provider} unavailable')

        result, used = channel.route_with_fallback(always_fail, providers=['zhipu', 'ark'])
        assert result is None
        assert used == 'provider_disabled'

    def test_route_with_fallback_primary_success(self):
        """退役主 Provider 不调用传输回调，也不偷偷切换备用。"""
        from lumenis.system.ai_gateway import channel

        call_order = []

        def mock_call(provider):
            call_order.append(provider)
            return f'result from {provider}', provider

        result, used = channel.route_with_fallback(mock_call, providers=['zhipu', 'ark'])
        assert result is None
        assert used == 'provider_disabled'
        assert call_order == []

    def test_route_with_fallback_active_secondary_takes_over(self, monkeypatch):
        """Synthetic active providers retain the normal mocked fallback path."""
        from lumenis.system.ai_gateway import channel
        from lumenis.system.ai_gateway import providers
        primary = 'synthetic_primary'
        secondary = 'synthetic_secondary'
        for name in (primary, secondary):
            monkeypatch.setitem(
                providers.PROVIDER_REGISTRY,
                name,
                {'status': providers.ACTIVE, 'role': 'test_only'},
            )
            monkeypatch.setitem(
                channel._PROVIDER_BREAKERS, name, channel.ProviderBreaker(name),
            )

        call_order = []

        def mock_call(provider):
            call_order.append(provider)
            if provider == primary:
                raise ConnectionError('synthetic primary unavailable')
            return f'result from {provider}', provider

        result, used = channel.route_with_fallback(
            mock_call, providers=[primary, secondary],
        )
        assert (result, used) == (f'result from {secondary}', secondary)
        assert call_order == [primary, secondary]

    def test_intelligence_local_fallback_path(self, monkeypatch):
        """显式选择退役本地模型时不探测、不调用、也不规则伪成功。"""
        from lumenis.system.ai_gateway import core as intelligence
        monkeypatch.setenv('AI_PROVIDER', 'ollama')
        calls = []
        with patch.object(intelligence, '_provider_config', side_effect=lambda: calls.append('config')):
            with patch.object(intelligence, '_detect_local', side_effect=lambda: calls.append('discover')):
                with patch('urllib.request.urlopen', side_effect=lambda *a, **k: calls.append('urlopen')):
                    result, provider = intelligence._chat('sys', 'user')
        assert (result, provider) == (None, 'provider_disabled')
        assert calls == []

    def test_intelligence_cloud_fallback_to_rule(self, monkeypatch):
        """显式选择退役智谱时不探测、不请求，也不改报规则成功。"""
        from lumenis.system.ai_gateway import core as intelligence
        from lumenis.system.ai_gateway import channel
        monkeypatch.setenv('AI_PROVIDER', 'zhipu')
        calls = []
        with patch.object(intelligence, '_provider_config', side_effect=lambda: calls.append('config')):
            with patch.object(channel, 'route_with_fallback', side_effect=lambda *a, **k: calls.append('route')):
                with patch.object(intelligence, '_detect_local', side_effect=lambda: calls.append('discover')):
                    with patch('urllib.request.urlopen', side_effect=lambda *a, **k: calls.append('urlopen')):
                        result, provider = intelligence._chat('sys', 'user')
        assert (result, provider) == (None, 'provider_disabled')
        assert calls == []


# ============================================================
# 5. Owned Gateway execution and conversation feedback binding
# ============================================================
class TestOwnedGatewayEvaluationBinding:
    def test_ai_hub_service_writes_the_gateway_result_to_evaluation(self, test_db, monkeypatch):
        from lumenis.ai_hub import context_pack, service
        from lumenis.system.ai_gateway import user_api_adapter
        request = _typed_conversation_request()
        result = _completed_owned_result(request)
        monkeypatch.setattr(service.freg, 'search_function_metadata', lambda *args, **kwargs: [])
        monkeypatch.setattr(service, 'status', lambda: {'state': 'BOUND', 'model_id': 'synthetic-owned-cpu'})
        monkeypatch.setattr(service, 'record_learning', lambda *args, **kwargs: None)
        monkeypatch.setattr(context_pack, 'run_budgeted_owned_request',
            lambda *args, **kwargs: dict(result))
        monkeypatch.setattr(user_api_adapter, 'is_selected', lambda: False)

        response = service.chat('PRIVATE_EVALUATION_QUESTION_7e29', _owned_request=request,
                                _include_evaluation_ref=True)
        assert response['ok'] is True
        assert response['provider'] == 'owned'
        assert response['owned_provenance']['evaluation_call_ref'].startswith('ai-call:v1:')
        row = acl.query_calls(provider='owned')[0]
        assert row['success'] == 1
        assert row['input_text'] == '' and row['output'] == ''
        assert 'PRIVATE_EVALUATION_QUESTION_7e29' not in row['system_result']
        assert 'PRIVATE_EVALUATION_OUTPUT_5c31' not in row['system_result']

    def test_completed_call_is_hash_only_and_context_exclusion_is_actor_bound(self, test_db):
        request = _typed_conversation_request()
        result = _completed_owned_result(request)
        evaluation_ref = aev.record_owned_gateway_execution(request, result, latency_ms=37)
        assert evaluation_ref and evaluation_ref.startswith('ai-call:v1:')

        rows = acl.query_calls(provider='owned')
        assert len(rows) == 1
        row = rows[0]
        assert row['success'] == 1
        assert row['input_text'] == '' and row['output'] == ''
        assert row['input_hash'] == request.input_revision_sha256
        assert row['output_hash']
        payload = json.loads(row['system_result'])
        assert payload['state'] == 'COMPLETED'
        assert payload['generation_performed'] is True
        assert payload['binding']['conversation_id'] == request.job_id
        assert payload['binding']['turn_id'] == request.request_id.split(':', 1)[0]
        assert 'PRIVATE_EVALUATION_QUESTION_7e29' not in row['system_result']
        assert 'PRIVATE_EVALUATION_HISTORY_3a10' not in row['system_result']
        assert 'PRIVATE_EVALUATION_OUTPUT_5c31' not in row['system_result']

        connection = aev._conn()
        try:
            connection.execute('BEGIN IMMEDIATE')
            args = {'scope': request.scope, 'conversation_id': request.job_id,
                    'turn_id': request.request_id.split(':', 1)[0]}
            assert aev.record_conversation_turn_exclusion(connection, evaluation_ref,
                actor_ref='actor:wrong-user', **args) == 'NOT_LINKED'
            assert aev.record_conversation_turn_exclusion(connection, evaluation_ref,
                actor_ref=request.actor_ref, **args) == 'RECORDED'
            assert aev.record_conversation_turn_exclusion(connection, evaluation_ref,
                actor_ref=request.actor_ref, **args) == 'ALREADY_RECORDED'
            connection.commit()
        finally:
            connection.close()

        quality = aev.evaluate_ai_quality(provider='owned')
        assert quality['success_count'] == 1
        assert quality['failure_count'] == 0
        assert quality['conversation_context_exclusion_count'] == 1
        assert quality['human_correction_count'] == 0

    def test_not_bound_budget_cancelled_and_runtime_failure_remain_distinct(self, test_db):
        from lumenis.system.ai_gateway.owned_service import owned_service_request_digest
        outcomes = [
            (_typed_conversation_request('a'), 'UNAVAILABLE', 'OWNED_SERVICE_EXECUTOR_NOT_BOUND', None),
            (_typed_conversation_request('b'), 'BLOCKED', 'CONTEXT_REQUIRED_INPUT_EXCEEDS_MODEL_BUDGET', None),
            (_typed_conversation_request('f'), 'CANCELLED', 'OWNED_SERVICE_CANCELLED', None),
            (_typed_conversation_request('c'), 'CANCELLED', 'OWNED_SERVICE_CANCELLED',
             'attempt_' + '2' * 32),
            (_typed_conversation_request('d'), 'ERROR', 'OWNED_RUNTIME_EXECUTION_FAILED',
             'attempt_' + '3' * 32),
        ]
        for request, status, code, attempt_id in outcomes:
            result = {'ok': False, 'status': status, 'code': code,
                      'request_digest': owned_service_request_digest(request),
                      'provider': 'owned'}
            if attempt_id:
                result['attempt_id'] = attempt_id
            aev.record_owned_gateway_execution(request, result, latency_ms=5)
        unverified = _typed_conversation_request('e')
        unverified_result = _completed_owned_result(unverified, attempt_id='')
        aev.record_owned_gateway_execution(unverified, unverified_result, latency_ms=5)

        quality = aev.evaluate_ai_quality(provider='owned')
        assert quality['success_count'] == 0
        assert quality['failure_count'] == 1
        assert quality['cancelled_count'] == 2
        assert quality['cancelled_before_generation_count'] == 1
        assert quality['not_executed_count'] == 3
        assert quality['not_executed_states'] == {
            'NOT_BOUND': 1, 'BUDGET_BLOCKED': 1, 'UNVERIFIED_COMPLETION': 1}
        assert quality['execution_counts'] == {
            'attempted': 2, 'completed': 0, 'failed': 1,
            'cancelled': 2, 'cancelled_before_generation': 1,
            'not_executed': 3,
            'not_executed_states': {
                'NOT_BOUND': 1, 'BUDGET_BLOCKED': 1, 'UNVERIFIED_COMPLETION': 1},
        }
        assert quality['provider_failure_rate']['owned'] == 1.0

    def test_provider_health_rates_only_actual_generation_outcomes(self, test_db):
        from lumenis.system.ai_gateway.owned_service import owned_service_request_digest
        cases = [
            (_typed_conversation_request('1'), 'UNAVAILABLE',
             'OWNED_SERVICE_EXECUTOR_NOT_BOUND', None),
            (_typed_conversation_request('2'), 'BLOCKED',
             'CONTEXT_REQUIRED_INPUT_EXCEEDS_MODEL_BUDGET', None),
            (_typed_conversation_request('3'), 'CANCELLED',
             'OWNED_SERVICE_CANCELLED', None),
            (_typed_conversation_request('4'), 'CANCELLED',
             'OWNED_SERVICE_CANCELLED', 'attempt_' + '4' * 32),
            (_typed_conversation_request('5'), 'ERROR',
             'OWNED_RUNTIME_EXECUTION_FAILED', 'attempt_' + '5' * 32),
        ]
        for request, status, code, attempt_id in cases:
            result = {'ok': False, 'status': status, 'code': code,
                      'request_digest': owned_service_request_digest(request),
                      'provider': 'owned'}
            if attempt_id:
                result['attempt_id'] = attempt_id
            aev.record_owned_gateway_execution(request, result, latency_ms=12)
        completed = _typed_conversation_request('6')
        aev.record_owned_gateway_execution(completed,
            _completed_owned_result(completed, attempt_id='attempt_' + '6' * 32),
            latency_ms=30)

        health = aev.evaluate_provider_health()['owned']
        assert health['total'] == 6
        assert health['attempted'] == 3
        assert health['success'] == 1 and health['failure'] == 1
        assert health['known_outcomes'] == 2 and health['failure_rate'] == 0.5
        assert health['cancelled'] == 2
        assert health['cancelled_before_generation'] == 1
        assert health['not_executed'] == 2
        assert health['not_executed_states'] == {'NOT_BOUND': 1, 'BUDGET_BLOCKED': 1}
        assert health['avg_latency_ms'] == 21

        report = aev.generate_evaluation_report()
        assert '实际执行尝试: 3' in report
        assert '执行后取消: 1' in report
        assert '执行前取消: 1' in report
        assert '未执行（未绑定/预算/权限等）: 2' in report
        assert '取消=2 未执行=2' in report


# ============================================================
# 6. 人工修正反馈闭环
# ============================================================
class TestHumanCorrection:
    def test_submit_human_correction(self, test_db):
        log_id = acl.log_call(provider='zhipu', output='{"sentiment":"positive"}', success=True)
        ok = aev.submit_human_correction(log_id, correction='实际为负面，用户投诉服务态度')
        assert ok is True
        rows = acl.query_calls()
        assert rows[0]['human_correction'] == '实际为负面，用户投诉服务态度'

    def test_submit_correction_with_result(self, test_db):
        log_id = acl.log_call(
            provider='zhipu', output='{"sentiment":"positive"}',
            final_result='{"sentiment":"positive"}', success=True,
        )
        ok = aev.submit_human_correction(
            log_id,
            correction='误判，应为负面',
            corrected_result='{"sentiment":"negative"}',
        )
        assert ok is True
        rows = acl.query_calls()
        assert rows[0]['human_correction'] == '误判，应为负面'
        assert rows[0]['final_result'] == '{"sentiment":"negative"}'

    def test_get_correction_feedback(self, test_db):
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'output': 'A',
             'human_correction': '修正1', 'rule_result': 'R1', 'final_result': 'F1'},
            {'provider': 'zhipu', 'success': True, 'output': 'B', 'human_correction': ''},
            {'provider': 'zhipu', 'success': True, 'output': 'C',
             'human_correction': '修正2', 'rule_result': 'R2', 'final_result': 'F2'},
        ])
        feedback = aev.get_correction_feedback()
        assert len(feedback) == 2
        assert any(f['human_correction'] == '修正1' for f in feedback)
        assert any(f['human_correction'] == '修正2' for f in feedback)

    def test_correction_affects_evaluation_metrics(self, test_db):
        """人工修正后，human_correction_rate 应反映在评估指标中。"""
        _seed_calls(test_db, [
            {'provider': 'zhipu', 'success': True, 'human_correction': '修正A'},
            {'provider': 'zhipu', 'success': True, 'human_correction': ''},
        ])
        result = aev.evaluate_ai_quality()
        assert result['human_correction_rate'] is None
        assert result['human_correction_count'] == 1
        assert result['human_correction_state'] == 'REVIEW_DENOMINATOR_NOT_RECORDED'
        assert result['human_review_coverage']['reviewed_calls'] is None

    def test_correction_closes_feedback_loop(self, test_db):
        """完整闭环：AI 调用 → 记录 → 人工修正 → 可查询 → 用于评估。"""
        # 1. AI 调用记录
        log_id = aev.record_rule_vs_ai(
            provider='zhipu', model='glm-4.5-air',
            rule_result='{"sentiment":"neutral"}',
            ai_result='{"sentiment":"positive"}',
            final_result='{"sentiment":"positive"}',  # 暂时采用 AI
            confidence=0.55,
        )
        # 2. 人工修正
        aev.submit_human_correction(
            log_id,
            correction='AI 误判，规则正确，应为 neutral',
            corrected_result='{"sentiment":"neutral"}',
        )
        # 3. 查询修正记录
        feedback = aev.get_correction_feedback()
        assert len(feedback) == 1
        assert feedback[0]['id'] == log_id
        # 4. 评估指标反映修正
        quality = aev.evaluate_ai_quality()
        assert quality['human_correction_rate'] is None
        assert quality['human_correction_count'] == 1
        assert quality['human_review_coverage']['reviewed_calls'] is None
        assert quality['human_correction_state'] == 'REVIEW_DENOMINATOR_NOT_RECORDED'


# ============================================================
# 6. 模块状态标记完整性
# ============================================================
class TestModuleStatusMarkers:
    def test_all_ai_modules_have_status(self):
        """所有核心 AI 模块都应有 MODULE_STATUS 标记。"""
        modules = [
            'ai_analyzer', 'ai_filter', 'ai_governance',
            'ai_resource_packs',
            'lumenis.system.ai_gateway.channel',
            'lumenis.system.ai_gateway.core',
        ]
        for mod_name in modules:
            import importlib
            mod = importlib.import_module(mod_name)
            assert hasattr(mod, 'MODULE_STATUS'), f'{mod_name} missing MODULE_STATUS'
            allowed_statuses = (
                'ACTIVE', 'ACTIVE_PRIMARY', 'ACTIVE_FALLBACK',
                'LEGACY', 'LEGACY_PARTIAL', 'RULES_ENGINE_PRIMARY',
            )
            if mod_name in {'local_ai_client', 'ai_resource_packs'}:
                assert mod.MODULE_STATUS == 'DISABLED'
            else:
                assert mod.MODULE_STATUS in allowed_statuses, (
                    f'{mod_name} has invalid MODULE_STATUS: {mod.MODULE_STATUS}'
                )

    def test_central_gateway_policy(self):
        """intelligence 作为中央网关应声明 Provider 策略。"""
        from lumenis.system.ai_gateway import core as intelligence
        from lumenis.system.ai_gateway import providers
        assert intelligence.MODULE_STATUS == 'ACTIVE_PRIMARY'
        assert intelligence.AI_ROLE == 'CENTRAL_GATEWAY'
        assert 'owned-only' in intelligence.PROVIDER_POLICY.lower()
        for provider in providers.RETIRED_PROVIDERS:
            assert providers.provider_status(provider) == providers.DISABLED
            assert providers.is_provider_available(provider) is False
            assert intelligence._selected_provider_disabled(provider) is True
        assert providers.is_provider_available('unregistered-provider') is False
        assert providers.provider_status('zhipu') == providers.DISABLED
        assert providers.provider_status('ollama') == providers.DISABLED

    def test_shared_learning_owner_is_current(self):
        """Operation learning remains available through the Shared owner."""
        from lumenis.shared import learning

        assert callable(learning.get_learning_status)
        assert callable(learning.record_operation)


def test_evaluation_query_failure_is_unknown_not_zero_or_pass(test_db, monkeypatch):
    def fail():
        raise RuntimeError('isolated query failure')
    monkeypatch.setattr(aev, '_conn', fail)
    result = aev.evaluate_ai_quality()
    assert result['state'] == 'UNAVAILABLE' and result['total_calls'] is None
    assert result['ai_accuracy'] is None
    verification = aev.verify_ai_not_replacing_rules()
    assert verification['state'] == 'UNKNOWN' and verification['passed'] is False


def test_actual_subject_replacement_is_detected_with_sqlite_rows(test_db):
    _seed_calls(test_db, [{'provider': 'owned', 'success': True,
                          'prompt_version': 'subject-filter-v1', 'rule_result': 'deny',
                          'output': 'allow', 'final_result': 'allow'}])
    result = aev.verify_ai_not_replacing_rules()
    check = next(x for x in result['checks'] if x['name'] == 'subject_filter_not_ai_replaced')
    assert check['value'] == 1 and check['passed'] is False
    assert result['state'] == 'FAIL'


def test_missing_metric_samples_do_not_become_measured_zero(test_db):
    _seed_calls(test_db, [{'provider': 'owned', 'success': True,
                          'output': 'text', 'confidence': None,
                          'latency_ms': None, 'token_usage': None}])
    result = aev.evaluate_ai_quality()
    assert result['ai_accuracy'] is None and result['ai_replacement_rate'] is None
    assert all(v is None for v in result['confidence_distribution'].values())
    assert result['latency']['avg_ms'] is None and result['token_cost']['total_tokens'] is None
    assert result['sample_counts']['rule_comparisons'] == 0


def test_empty_evaluation_report_discloses_unknown_and_no_accuracy_claim(test_db):
    report = aev.generate_evaluation_report()
    assert '未知／未测量' in report and 'UNKNOWN' in report
    assert '非独立正确率' in report
    assert 'AI 准确率:' not in report


def test_recorder_external_transaction_rollback_and_connection_lifetime(tmp_path, monkeypatch):
    import sqlite3
    from lumenis.shared.evaluation import recorder
    path=tmp_path/'external.sqlite'
    recorder.init_db(str(path))
    connection=sqlite3.connect(path);connection.row_factory=sqlite3.Row
    connection.execute('BEGIN IMMEDIATE')
    def unexpected(*args,**kwargs):raise AssertionError('must not open another connection')
    monkeypatch.setattr(recorder,'_get_connection',unexpected)
    recorder.record_evaluation('ai','external_test',.3,.8,.5,source='ordinary',connection=connection)
    assert connection.in_transaction
    assert connection.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]==1
    connection.rollback()
    assert connection.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]==0
    assert connection.execute('SELECT 42').fetchone()[0]==42
    connection.close()


def test_recorder_external_connection_requires_transaction_and_no_db_path(tmp_path):
    import sqlite3
    from lumenis.shared.evaluation import recorder
    path=tmp_path/'external.sqlite';recorder.init_db(str(path))
    con=sqlite3.connect(path);con.row_factory=sqlite3.Row
    with pytest.raises(ValueError,match='active transaction'):
        recorder.record_evaluation('ai','test',1.,.8,.5,connection=con)
    con.execute('BEGIN')
    with pytest.raises(ValueError,match='db_path'):
        recorder.record_evaluation('ai','test',1.,.8,.5,connection=con,db_path=str(path))
    assert con.in_transaction
    con.rollback();con.close()


def test_recorder_external_error_does_not_rollback_or_close(tmp_path):
    import sqlite3
    from lumenis.shared.evaluation import recorder
    path=tmp_path/'missing-schema.sqlite';con=sqlite3.connect(path);con.row_factory=sqlite3.Row
    con.execute('BEGIN')
    con.execute('CREATE TABLE unrelated(value)');con.execute('INSERT INTO unrelated VALUES(7)')
    with pytest.raises(sqlite3.OperationalError):
        recorder.record_evaluation('ai','test',1.,.8,.5,connection=con)
    assert con.in_transaction and con.execute('SELECT value FROM unrelated').fetchone()[0]==7
    assert con.execute("SELECT count(*) FROM sqlite_master WHERE name='evaluation_records'").fetchone()[0]==0
    con.rollback();con.close()


def test_recorder_default_connection_behavior_preserved(tmp_path):
    from lumenis.shared.evaluation import recorder
    path=str(tmp_path/'default.sqlite');recorder.init_db(path)
    r=recorder.record_evaluation('ai','ordinary',.5,.8,.3,db_path=path)
    assert recorder.get_evaluation_record(r.evaluation_id,db_path=path)['status']=='warn'
