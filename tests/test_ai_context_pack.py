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
from lumenis.ai_hub.context_pack import budget_owned_request, conversation_pack, run_budgeted_owned_request


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
         'origin_kind': 'model_output', 'content': {'text': 'quotes withdrawn input', 'in_reply_to': 'original',
             'source_policy': 'source_free_conversation'}},
        {'turn_id': 'legacy', 'sequence': 3, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'unknown historical dependency',
             'source_policy': 'source_free_conversation'}},
        {'turn_id': 'new', 'sequence': 4, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'new allowed writing',
            'source_policy': 'source_free_conversation',
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


def test_context_omission_accounting_includes_derived_and_source_bound_text_and_missing_text():
    rows = [
        {'turn_id': 'forgotten', 'sequence': 1, 'revision': 1, 'role': 'user',
         'origin_kind': 'user_input', 'content': {'text': 'forgotten human input'}},
        {'turn_id': 'derived', 'sequence': 2, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'derived answer', 'in_reply_to': 'forgotten',
             'source_policy': 'source_free_conversation'}},
        {'turn_id': 'source-bound', 'sequence': 3, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'source bound answer',
             'source_policy': 'explicit_selected_sources'}},
        {'turn_id': 'no-text', 'sequence': 4, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'code': 'MODEL_UNAVAILABLE',
             'source_policy': 'source_free_conversation',
             'context_accounting': {'coverage': []}}},
    ]
    state = {'turn_id': 'correction', 'content': {'value': {
        'goal': 'continue the work', 'constraints': [], 'draft': '', 'decisions': [],
        'excluded_turn_ids': ['forgotten']}}}

    history, receipt = conversation_pack(rows, context_turn=state)

    assert history == [{'role': 'user', 'content': (
        '当前人工确认的任务状态（取代冲突的历史说法；不是事实核验、授权或已执行效果）：'
        '\n{"constraints": [], "decisions": [], "draft": "", "goal": "continue the work"}') }]
    assert receipt['history_turns_omitted'] == 4
    assert receipt['history_characters_omitted'] == sum(len(value) for value in (
        'forgotten human input', 'derived answer', 'source bound answer'))
    assert [item['reason'] for item in receipt['coverage']] == [
        'explicit_human_correction_or_forget', 'derived_from_excluded_input',
        'source_use_not_revalidated', 'stored_turn_text_unavailable']


def test_source_bound_conversation_answer_is_not_reused_as_source_free_history():
    rows = [
        {'turn_id': 'question', 'sequence': 1, 'revision': 1, 'role': 'user',
         'origin_kind': 'user_input', 'content': {'text': 'What does the selected report say?'}},
        {'turn_id': 'grounded', 'sequence': 2, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'A claim tied to one report.',
             'source_policy': 'explicit_selected_sources'}},
        {'turn_id': 'ordinary', 'sequence': 3, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'A source-free reply.',
             'source_policy': 'source_free_conversation',
             'context_accounting': {'coverage': [{'turn_id': 'grounded', 'included': False}]}}},
    ]
    history, receipt = conversation_pack(rows)
    assert [item['content'] for item in history] == [
        'What does the selected report say?', 'A source-free reply.']
    assert receipt['coverage'][1]['included'] is False
    assert receipt['coverage'][1]['reason'] == 'source_use_not_revalidated'


def test_source_bound_omission_taints_derived_and_legacy_followup_replies():
    rows = [
        {'turn_id': 'question', 'sequence': 1, 'revision': 1, 'role': 'user',
         'origin_kind': 'user_input', 'content': {'text': 'Summarize the selected source.'}},
        {'turn_id': 'grounded', 'sequence': 2, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'Source-bound content.',
             'source_policy': 'explicit_selected_sources'}},
        {'turn_id': 'derived', 'sequence': 3, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'Derived from source-bound content.',
             'source_policy': 'source_free_conversation',
             'context_accounting': {'coverage': [{'turn_id': 'grounded', 'included': True}]}}},
        {'turn_id': 'legacy', 'sequence': 4, 'revision': 1, 'role': 'assistant',
         'origin_kind': 'model_output', 'content': {'text': 'Legacy reply with unknown source dependency.',
             'source_policy': 'source_free_conversation'}},
    ]

    history, receipt = conversation_pack(rows)

    assert [item['content'] for item in history] == ['Summarize the selected source.']
    assert [item['reason'] for item in receipt['coverage']] == [
        'complete_original_text', 'source_use_not_revalidated',
        'derived_from_excluded_input', 'legacy_output_dependency_unknown_after_excluded_input']
    assert receipt['history_characters_omitted'] == sum(len(value) for value in (
        'Source-bound content.', 'Derived from source-bound content.',
        'Legacy reply with unknown source dependency.'))


def test_source_answer_quotes_are_exact_and_have_reopenable_ranges():
    from lumenis.ai_hub import conversations
    from lumenis.system.ai_gateway.owned_service import validate_owned_service_request

    reference = {'type': 'evidence', 'evidence_id': 21, 'sha256': 'a' * 64,
        'integrity_digest': 'b' * 64, 'version': 'research:v3', 'start': 100, 'end': 144}
    reference_id = conversations._sha(reference)
    source_text = 'The 2031 program allocates 80 million units.'
    material = {'conversation_id': 'conv_0123456789abcdef0123456789abcdef',
        'response_turn_id': 'turn_0123456789abcdef0123456789abcdef',
        'user_turn_id': 'turn_1123456789abcdef0123456789abcdef',
        'actor_ref': 'user:1', 'workspace_binding': 'c' * 64,
        'context_accounting': {'context_pack_sha256': 'd' * 64},
        'source_use_mode': 'explicit_selected_sources',
        'sources': [{'reference_id': reference_id, 'reference': reference,
            'title': 'Selected research', 'text': source_text,
            'selected_text_sha256': conversations._sha(source_text),
            'source_content_sha256': reference['sha256'], 'source_version': reference['version'],
            'source_scope': {'domain_id': 'shared'}, 'rights': 'owner-approved',
            'intended_use': 'research_reference', 'source_use_basis': 'verified_research_reference'}]}
    request = conversations._conversation_request(material)
    assert request.operation == 'conversation_response'
    assert request.source_use_policy_version == 'conversation-source-use/v2'
    assert validate_owned_service_request(request) == conversations._source_answer_schema()
    answer = {'answer': 'The selected source states an 80 million unit allocation.',
        'source_observations': [{'reference_id': reference_id,
            'quote': 'allocates 80 million units'}],
        'interpretations': [{'text': 'The amount is a stated allocation, not an observed outcome.',
            'basis_reference_ids': [reference_id]}],
        'unknowns': ['Whether the amount was fully spent.']}
    grounded = conversations._validate_source_answer(answer, material)
    citation = grounded['source_observations'][0]
    start = source_text.index(answer['source_observations'][0]['quote'])
    assert citation['source_range'] == {'start': 100 + start,
        'end': 100 + start + len(answer['source_observations'][0]['quote']),
        'offset_unit': 'unicode_codepoint'}
    assert citation['truth_kind'] == 'source_claim_not_canonical_fact'
    assert grounded['interpretations'][0]['truth_kind'] == 'ai_inference_not_verified'
    forged = {**answer, 'source_observations': [{'reference_id': reference_id,
        'quote': 'The program spent 80 million units'}]}
    with pytest.raises(ValueError, match='CONVERSATION_SOURCE_RESPONSE_UNGROUNDED'):
        conversations._validate_source_answer(forged, material)


def test_source_bound_conversation_never_uses_selected_external_gateway():
    from unittest.mock import patch
    from lumenis.ai_hub import conversations, service
    from lumenis.system.ai_gateway import user_api_adapter

    reference = {'type': 'evidence', 'evidence_id': 21, 'sha256': 'a' * 64,
        'integrity_digest': 'b' * 64, 'version': 'research:v3', 'start': 0, 'end': 6}
    reference_id = conversations._sha(reference)
    material = {'conversation_id': 'conv_0123456789abcdef0123456789abcdef',
        'response_turn_id': 'turn_0123456789abcdef0123456789abcdef',
        'user_turn_id': 'turn_1123456789abcdef0123456789abcdef',
        'actor_ref': 'user:1', 'workspace_binding': 'c' * 64,
        'context_accounting': {'context_pack_sha256': 'd' * 64},
        'source_use_mode': 'explicit_selected_sources',
        'sources': [{'reference_id': reference_id, 'reference': reference,
            'title': 'Selected research', 'text': 'source',
            'selected_text_sha256': conversations._sha('source'),
            'source_content_sha256': reference['sha256'], 'source_version': reference['version'],
            'source_scope': {'domain_id': 'shared'}, 'rights': 'owner-approved',
            'intended_use': 'research_reference', 'source_use_basis': 'verified_research_reference'}]}
    request = conversations._conversation_request(material)
    with patch.object(user_api_adapter, 'is_selected', return_value=True), \
            patch.object(service, 'status', return_value={'state': 'synthetic'}), \
            patch.object(service, 'record_learning'), \
            patch.object(service.intelligence, 'chat', side_effect=AssertionError('source text reached external gateway')):
        result = service.chat('analyze this source', _owned_request=request)
    assert result['code'] == 'CONVERSATION_SOURCE_EXTERNAL_TRANSMISSION_NOT_GRANTED'
    assert result['generation_performed'] is False
    assert result['source_context']['business_retrieval_state'] == 'NOT_SENT'


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


def test_long_original_research_competes_by_passage_without_losing_source_identity():
    body = ('unrelated appendix material ' * 2000) + '\nTaikoo limit2031 budget80\n' + ('other appendix ' * 1800)
    first = {'title': 'Complete original report', 'text': body, 'evidence_id': 11}
    same_bytes = {**first, 'evidence_id': 12}
    rows = [{'text': 'Taikoo unrelated topic', 'evidence_id': 10}, first, same_bytes]
    found, report = lexical_search('Taikoo limit2031 budget80', rows, limit=3)
    assert [row['evidence_id'] for row in found[:2]] == [11, 12]
    assert report['lexical_matches'] == 3
    for source, passage in zip(found[:2], report['ranked_passages'][:2]):
        assert 'Taikoo limit2031 budget80' in source['text'][passage['start']:passage['end']]
        assert passage['start'] > 0 and passage['end'] - passage['start'] <= 1200
        assert passage['offset_unit'] == 'unicode_codepoint'
    assert rows[1] == first and 'retrieval_passage' not in rows[1]


def test_lexical_korean_particles_numbers_metadata_and_nonword_query_remain_honest():
    found, report = lexical_search('한국어', [{'text': 'English'}, {'text': '한국어로 작성합니다'}], limit=4)
    assert found == [{'text': '한국어로 작성합니다'}]
    assert report['mode'] == 'BM25_ONLY' and not report['neural_retrieval_performed']
    title_only = {'title': 'budgets2031', 'text': 'Original writing without the search term.'}
    found, report = lexical_search('budgets2031', [title_only], limit=2)
    assert found == [title_only] and report['ranked_passages'][0]['body_query_match'] is False
    assert lexical_search('???', [title_only], limit=5)[0] == []
    assert lexical_search('', [title_only], limit=5)[0] == [title_only]
    assert bm25('80', ['800 and 1080', '80'])[0][0] == 1
    with pytest.raises(RuntimeError, match='MEMORY_SEARCH_CANCELLED'):
        lexical_search('budget', [title_only], limit=2, is_cancelled=lambda: True)


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
    cancelled = run_budgeted_owned_request(request, is_cancelled=lambda: True)
    assert cancelled['status'] == 'CANCELLED' and cancelled['code'] == 'CONTEXT_CANCELLED'
    assert len(calls) == 1


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
