"""Original text ranges through existing import/conversation owners; no model."""
from tests.test_ai_conversation_owner import (
    conversation_sources, conversation_client, agent_client, skill_client,
    _search_sources, _source_context_body,
)


def test_late_original_source_passage_is_selected_saved_revised_and_reopened(conversation_sources):
    ws = conversation_sources
    target = 'revision2031 香港预算80，2031-11-14不得擅自发布；한국어 원문 유지。'
    text = ('Earlier original material and ordinary records.\n' * 400) + target + ('\nLater appendix.' * 160)
    made = ws['save'](text, title='Original professional writing')
    import shared_artifacts
    original_file = shared_artifacts.artifact_file_path(made['document']['attachments'][0]['artifact_id'])
    # The fixture writes through the host text-file API, so on Windows the
    # original file contains CRLF. Offsets refer to those retained codepoints.
    retained_text = original_file.read_bytes().decode('utf-8')
    result = _search_sources(ws, query='revision2031')
    source = result['records'][0]
    reference = source['reference']
    assert reference['start'] > 0 and target in source['text']
    assert source['text'] == retained_text[reference['start']:reference['end']]
    assert source['passage']['start'] == reference['start']
    assert reference['artifact_id'] == made['artifact']['artifact_id']
    assert result['retrieval']['preview_policy'] == 'ranked_original_passage/v1'
    assert result['retrieval']['mode'] == 'BM25_ONLY' and result['model_execution'] == 'NOT_RUN'
    body = _source_context_body(ws['row']['revision'], [reference])
    saved = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=body)
    assert saved.status_code == 200, saved.get_json()
    revised = {**body, 'value': {**body['value'], 'draft': 'Human revision retains budget80 and the selected original.'},
               'expected_revision': saved.get_json()['revision'], 'idempotency_key': 'revise-with-original-range'}
    response = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=revised)
    assert response.status_code == 200, response.get_json()
    reopened = ws['app'].test_client().get(ws['root'] + '/context', headers=ws['headers']).get_json()
    assert reopened['context']['content']['value'] == revised['value']
    assert reopened['source_references'][0]['reference'] == reference
    assert reopened['source_references'][0]['text'] == source['text']
    assert reopened['source_references'][0]['model_source_use'] == 'NOT_GRANTED'
