"""Isolated context/ranking regressions, never real model or product acceptance."""
from dataclasses import replace

import pytest

from agent_memory.retrieval import (
    bm25,
    cross_encoder_rank,
    dense_cosine,
    lexical_search,
    reciprocal_rank_fusion,
)
from lumenis.ai_hub.context_pack import budget_owned_request, conversation_pack


def _rows(count=100):
    return [{'turn_id': str(index), 'revision': 1, 'role': 'user',
             'content': {'text': ('constraint: do not spend; budget 100; ' if index < 30 else 'follow up ') + str(index)}}
            for index in range(count)]


def test_long_history_keeps_thirty_early_constraints_complete_and_tracks_human_correction():
    rows = _rows()
    history, coverage = conversation_pack(rows)
    assert len(history) == 100 and history[0]['content'] == rows[0]['content']['text']
    assert coverage['history_turns_omitted'] == 0 and not coverage['token_budget_verified']
    context = {'turn_id': 'correction', 'content': {'value': {
        'goal': 'current task', 'constraints': ['do not spend', 'new budget is 80'],
        'draft': 'human writing must survive', 'decisions': ['deny publishing'], 'excluded_turn_ids': ['0']}}}
    corrected, receipt = conversation_pack(rows, context_turn=context)
    assert len(corrected) == 100 and corrected[0]['content'] == rows[1]['content']['text']
    assert 'human writing must survive' in corrected[-1]['content']
    assert receipt['history_turns_omitted'] == 1 and receipt['coverage'][0]['included'] is False
    assert receipt['context_pack_sha256'] != coverage['context_pack_sha256']
    assert rows == _rows(), 'A derived pack must never mutate the original transcript'


def test_forgetting_original_invalidates_its_derived_replies_and_legacy_unknowns():
    rows = [
        {'turn_id': 'original', 'sequence': 1, 'revision': 1, 'role': 'user',
         'origin_kind': 'user_input', 'content': {'text': 'withdrawn input'}},
        {'turn_id': 'reply', 'sequence': 2, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'quotes withdrawn input', 'in_reply_to': 'original'}},
        {'turn_id': 'legacy', 'sequence': 3, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'unknown historical dependency'}},
        {'turn_id': 'new', 'sequence': 4, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'new allowed writing',
            'context_accounting': {'coverage': [{'turn_id': 'original', 'included': False}]}}},
    ]
    state = {'turn_id': 'correction', 'content': {'value': {
        'goal': 'corrected task', 'constraints': [], 'draft': '', 'decisions': [],
        'excluded_turn_ids': ['original']}}}
    history, receipt = conversation_pack(rows, context_turn=state)
    assert [turn['content'] for turn in history[:-1]] == ['new allowed writing']
    assert [item['reason'] for item in receipt['coverage'][:3]] == [
        'explicit_human_correction_or_forget', 'derived_from_excluded_input',
        'legacy_output_dependency_unknown_after_excluded_input']


def test_lexical_bm25_multilingual_and_no_invented_neural_retrieval():
    assert bm25('car', ['scar unrelated', 'car car exact'])[0][0] == 1
    assert [index for index, _ in bm25('car', ['scar unrelated', 'car exact'])] == [1]
    for query, docs in [('品牌营销', ['库存管理', '品牌营销方案']),
                        ('한국어', ['English', '한국어 문서']), ('café', ['CAFE', 'CAFÉ'])]:
        assert bm25(query, docs)[0][0] == 1
    found, report = lexical_search('car', [{'text': 'scar'}, {'text': 'car'}], limit=30)
    assert found == [{'text': 'car'}]
    assert report['dense'] == 'BLOCKED_MODEL_NOT_ADMITTED' and not report['neural_retrieval_performed']


def test_unadmitted_retrieval_never_calls_legacy_embedding_or_text_model(monkeypatch):
    from lumenis.system.ai_gateway import core
    def forbidden(*args, **kwargs):
        pytest.fail('Lexical fallback must never probe a retired or unrelated model')
    monkeypatch.setattr(core, 'local_embeddings', forbidden)
    monkeypatch.setattr(core, 'run_owned_analysis', forbidden)
    rows, report = lexical_search('brand', [{'text': 'brand research'}], limit=5)
    assert rows == [{'text': 'brand research'}]
    capability = report['gateway_capabilities']
    assert capability['model_execution'] == 'NOT_RUN'
    assert capability['embedding']['code'] == 'OWNED_EMBEDDING_EXECUTOR_NOT_BOUND'
    assert capability['cross_encoder']['code'] == 'OWNED_RERANKER_EXECUTOR_NOT_BOUND'


def test_dense_and_rrf_are_separate_and_cross_encoder_receives_bounded_candidates():
    lexical = [(1, 1000.0), (0, 20.0)]
    dense = dense_cosine([1, 0], [[1, 0], [0, 1], [-1, 0]])
    assert [index for index, _ in dense] == [0, 1, 2]
    fused = reciprocal_rank_fusion(lexical, dense)
    assert fused == reciprocal_rank_fusion([(1, .001), (0, .0001)], dense)
    calls = []
    def synthetic_scores(pairs):
        calls.extend(pairs)
        return [0.1, 0.9]
    ranked = cross_encoder_rank('q', ['A', 'B', 'C'], fused, synthetic_scores, candidate_limit=2)
    assert len(calls) == 2 and ranked[0][0] == fused[1][0]
    with pytest.raises(ValueError, match='VECTOR_INVALID'):
        dense_cosine([1, 0], [[float('nan'), 0]])
    with pytest.raises(ValueError, match='RERANK_RESULT_INVALID'):
        cross_encoder_rank('q', ['A'], [(0, 1)], lambda _: [True])


def test_owned_context_uses_runtime_measurement_preserves_required_and_executes_exact_request(monkeypatch):
    from lumenis.system.ai_gateway import core, owned_service
    from tests.test_owned_service import _request
    request = _request(user_payload='required human draft; no spending; do not replay effect')
    measured_requests, calls = [], []
    def synthetic_measure(candidate):
        measured_requests.append(candidate)
        return {'ok': True, 'fits': len(candidate.user_payload) < 110,
                'prompt_tokens': len(candidate.user_payload), 'binding_sha256': 'a' * 64,
                'count_method': 'synthetic_unit_counter_not_real_tokenizer'}
    def synthetic_generate(candidate, **kwargs):
        calls.append((candidate, kwargs))
        return {'ok': True, 'status': 'COMPLETED'}
    monkeypatch.setattr(owned_service, 'measure_owned_request', synthetic_measure)
    monkeypatch.setattr(owned_service, 'run_owned_request', synthetic_generate)
    result = core.run_owned_analysis(request=request, context_sections=[{'name': 'optional', 'text': 'x' * 300}])
    assert result['ok'] and len(calls) == 1
    assert calls[0][0] == measured_requests[-1] == request
    assert calls[0][1]['expected_binding_sha256'] == 'a' * 64
    assert result['context_accounting']['omitted_sections'][0]['name'] == 'optional'
    too_large = budget_owned_request(replace(request, user_payload='required' * 100))
    assert too_large['code'] == 'CONTEXT_REQUIRED_INPUT_EXCEEDS_MODEL_BUDGET'
    assert len(calls) == 1
    assert budget_owned_request(request, is_cancelled=lambda: True)['code'] == 'CONTEXT_CANCELLED'


def test_owned_context_missing_runtime_never_estimates_tokens_or_generates():
    from lumenis.system.ai_gateway import owned_service
    from tests.test_owned_service import _request
    # No runtime is installed/admitted by this isolated test.
    assert not owned_service._SLOTS
    packed = budget_owned_request(_request())
    assert not packed['ok'] and packed['code'] == 'OWNED_SERVICE_EXECUTOR_NOT_BOUND'
    assert 'prompt_tokens' not in packed['measurement']


def test_chat_consumer_keeps_complete_selected_history_and_fails_without_silent_cut(monkeypatch):
    from lumenis.ai_hub import service
    from lumenis.system.ai_gateway import user_api_adapter
    monkeypatch.setattr(user_api_adapter, 'is_selected', lambda: False)
    monkeypatch.setattr(service, 'status', lambda: {'state': 'synthetic', 'model_id': None})
    monkeypatch.setattr(service, 'record_learning', lambda *args: None)
    captured = []
    def synthetic_analysis(prompt, kind):
        captured.append(prompt)
        return {'ok': True, 'status': 'COMPLETED', 'provider': 'owned', 'analysis': 'synthetic'}
    monkeypatch.setattr(service, '_run_owned', synthetic_analysis)
    history = [{'role': 'user', 'content': str(index) + ' full text ' * 100} for index in range(8)]
    assert service.chat('continue', history=history)['ok']
    assert all(row['content'] in captured[0] for row in history)
    blocked = service.chat('continue', history=[{'role': 'user', 'content': 'x' * 33000}])
    assert blocked['code'] == 'CONVERSATION_CONTEXT_EXCEEDS_TRANSPORT_LIMIT'
    assert len(captured) == 1 and blocked['generation_performed'] is False
