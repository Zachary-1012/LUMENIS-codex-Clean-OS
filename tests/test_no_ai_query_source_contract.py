"""Offline Task/SourceBrief contracts over signed synthetic sources.

These are isolated integration tests, not live collection or real-user acceptance.
The CSV is generated here, has no personal data, and is never sent to a model.
Permission, signed Evidence, canonical storage, SourceBrief persistence/readback,
Task execution and verification are the real owners; only AI is trapped.
"""
import hashlib
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ai_task_engine import TaskEngine, TaskStatus, reset_task_engine
from canonical_data import CanonicalRecord, persist_canonical
from lumenis.importer.parser import parse_file
from lumenis.shared.evidence import store as evidence_store
from tests.test_source_brief_job import job_db
from tests.test_source_brief_job_routes import client, GLOBAL, URL


@pytest.fixture
def scoped_query(client, tmp_path, monkeypatch):
    from lumenis.shared.reporting import business_brief
    from lumenis.system.ai_gateway import core as gateway

    api, app, db, entry, gate = client
    import ai_api
    app.register_blueprint(ai_api.bp)
    traps = {}
    for owner, name in ((TaskEngine, '_call_ai_with_fallback'),
                        (gateway, 'run_owned_analysis'), (gateway, 'chat'),
                        (business_brief, '_request_business_inference')):
        trap = Mock(side_effect=AssertionError('BASIC_STATISTICS_MUST_NOT_CALL_AI'))
        monkeypatch.setattr(owner, name, trap)
        traps[name] = trap

    # client supplies one independently signed source with no publication date.
    # Three more distinct sources exercise a real zero, missing value and time.
    raw = (b'source_id,platform,published,likes\n'
           b'no-ai-public-a,web,2026-10-01T10:00:00Z,0\n'
           b'no-ai-public-b,news,2026-10-01T18:00:00Z,\n'
           b'no-ai-public-c,web,,7\n')
    csv_path = tmp_path / 'synthetic-public-sources.csv'
    csv_path.write_bytes(raw)
    parsed = parse_file(str(csv_path))
    assert parsed.tables[0][1:][0][-1] == '0'
    assert parsed.tables[0][1:][1][-1] == ''
    assert parsed.metadata['source_fingerprint'] == hashlib.sha256(raw).hexdigest()
    rows = [dict(zip(parsed.tables[0][0], row)) for row in parsed.tables[0][1:]]
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        for row in rows:
            source_id = row['source_id']
            evidence_id = evidence_store.record_evidence(
                connection=con, source='public_synthetic_csv', project='LUMENIS',
                product='CTH', feature_id='NO_AI_QUERY_CONTRACT', test_name='signed_csv_source',
                result='PASS', status='verified',
                inputs={'source_ids': [source_id], 'csv_sha256': hashlib.sha256(raw).hexdigest()},
                outputs={'row': row}, domain_id='cth', subject_id=entry['subject_id'],
            )
            persist_canonical(con, CanonicalRecord(
                canonical_id='canonical-' + source_id, product_id='CTH', domain_id='cth',
                subject_id=entry['subject_id'], scope_status='VERIFIED',
                scope_evidence_ref=str(evidence_id), source_id=source_id,
                external_id=source_id, source_type='web_mention', source_platform=row['platform'],
                title='Synthetic public source ' + source_id, url='https://example.invalid/' + source_id,
                content=json.dumps(row), publish_datetime=row['published'] or None,
                captured_at='2026-10-18T00:00:00Z',
            ))
            evidence = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (evidence_id,)).fetchone()
            assert evidence_store.verify_evidence_record_integrity(dict(evidence))
        con.commit()
    headers = {**GLOBAL, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': entry['subject_id']}
    response = api.post(URL + '/generate', headers=headers, json={})
    assert response.status_code == 200, response.get_json()
    report = response.get_json()['result']
    assert report['artifact_outcome']['source_count'] == 4
    context = {
        'analysis_operation': 'source_statistics',
        'source_brief_job_id': report['job_id'],
        'source_brief_artifact_hash': report['artifact_outcome']['artifact_hash'],
    }
    reset_task_engine()
    engine = TaskEngine()
    value = SimpleNamespace(api=api, app=app, db=db, gate=gate, headers=headers,
                            report=report, context=context, engine=engine, traps=traps,
                            csv_path=csv_path, raw=raw)
    yield value
    for trap in traps.values():
        trap.assert_not_called()
    assert csv_path.read_bytes() == raw
    reset_task_engine()


def run_scoped_query(source, *, context=None, headers=None, created_by='workspace:local', expect_rejection=False):
    with source.app.test_request_context('/api/ai/tasks', method='POST', headers=source.headers if headers is None else headers, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        created = source.engine.create_task('查一下数据统计', context=source.context if context is None else context,
                                            created_by=created_by)
        try:
            result = source.engine.run_task(created['task_id'])
        except (ValueError, PermissionError, LookupError, RuntimeError) as exc:
            if not expect_rejection:
                raise
            # Rejection is persisted by the real engine; exceptions are not success.
            result = source.engine.get_task(created['task_id'])
            assert result['status'] == TaskStatus.FAILED.value
            assert result['error'] == str(exc)
        return result


def assert_verified_statistics(source, result, *, expected_ai_status='not_requested'):
    assert result['status'] == TaskStatus.SUCCEEDED.value, result
    data = json.loads(result['result_json'])
    output, verified = data['output'], data['verification']
    assert data['task_outcome'] == 'VERIFIED'
    assert verified['verified'] is True and verified['success'] is True
    assert verified['verification_method'] == 'independent_owner_readback'
    assert verified['verification_scope'] == 'SOURCE_BRIEF_SAMPLE_ANALYSIS'
    assert output['ai_required'] is False
    assert output['ai_analysis'] is None and output['ai_analysis_status'] == expected_ai_status
    assert output['base_analysis_status'] == 'completed'
    assert output['artifact_outcome'] == source.report['artifact_outcome']
    counts = output['base_analysis']
    assert counts['input_count'] == counts['unique_source_count'] == 4
    assert counts['duplicate_projection_count'] == 0
    assert counts['platform_counts'] == {'news': 1, 'web': 3}
    assert counts['source_type_counts'] == {'web_mention': 4}
    assert counts['publication_day_counts'] == {'2026-10-01': 2}
    assert counts['publication_time_known_count'] == counts['publication_time_unknown_count'] == 2
    assert counts['publication_time_known_ratio'] == 0.5
    assert counts['denominator'] == 'unique verified sources in this SourceBrief sample'
    assert counts['coverage'] == 'UNKNOWN' and counts['causal_claim'] == 'NOT_ESTABLISHED'
    assert counts['sample'] == source.report['source_brief']['sample']
    assert counts['scope'] == source.report['source_brief']['scope']
    assert output['artifact_outcome']['state'] == 'persisted_and_reopened_verified'
    return data


def test_signed_source_counts_persist_reopen_and_recover_without_ai(scoped_query):
    source = scoped_query
    result = run_scoped_query(source)
    data = assert_verified_statistics(source, result)
    print('VERIFIED_NO_AI_RESULT=' + json.dumps({
        'task_status': result['status'],
        'verification': data['verification']['verification_method'],
        'statistics': data['output']['base_analysis'],
        'artifact': data['output']['artifact_outcome'],
        'ai_calls': {name: trap.call_count for name, trap in source.traps.items()},
        'csv_sha256': hashlib.sha256(source.raw).hexdigest(),
    }, ensure_ascii=False, sort_keys=True))
    with source.app.test_request_context('/api/ai/tasks', method='POST', headers=source.headers, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        fresh_engine = TaskEngine()
        reopened = fresh_engine.get_task(result['task_id'])
        assert reopened['result_json'] == result['result_json']
        assert fresh_engine.run_task(result['task_id'])['result_json'] == result['result_json']
    response = source.app.test_client().get(URL + '/jobs/' + source.report['job_id'], headers=source.headers)
    assert response.status_code == 200
    assert response.get_json()['result']['artifact_outcome'] == data['output']['artifact_outcome']
    with sqlite3.connect(source.db) as con:
        assert con.execute('SELECT COUNT(*) FROM daily_reports').fetchone()[0] == 1
        assert con.execute('SELECT COUNT(*) FROM evaluation_records').fetchone()[0] == 3
        originals = [json.loads(row[0]) for row in con.execute(
            "SELECT content FROM canonical_data WHERE source_id LIKE 'no-ai-public-%' ORDER BY source_id")]
    assert [row['likes'] for row in originals] == ['0', '', '7']


@pytest.mark.parametrize('context', [{}, {'scenario': 'case6'}, {'analysis_operation': 'source_statistics'}])
def test_missing_source_never_succeeds_or_fabricates_zero(scoped_query, context):
    result = run_scoped_query(scoped_query, context=context, expect_rejection=True)
    assert result['status'] == TaskStatus.FAILED.value
    assert result['error'] in {'SCOPED_SOURCE_OWNER_REQUIRED', 'ANALYSIS_SOURCE_BRIEF_REQUIRED',
                               'domain_context_unavailable:DOMAIN_NOT_SELECTED'}
    data = json.loads(result['result_json']) if result.get('result_json') else {}
    output = data.get('output', {})
    assert 'base_analysis' not in output and 'total_count' not in output
    if output:
        assert output['ai_required'] is False and output['business_outcome'] == 'NOT_OBSERVED'
        assert data['verification']['verified'] is False
        assert output['next_action']['path'] == URL + '/start'


@pytest.mark.parametrize('change', ['scope', 'missing_scope', 'actor', 'version', 'signature', 'permission'])
def test_current_source_contract_rejects_changed_authority(scoped_query, change):
    source = scoped_query
    context, headers, created_by = dict(source.context), dict(source.headers), 'workspace:local'
    if change == 'scope':
        headers = GLOBAL
    elif change == 'missing_scope':
        headers = {}
    elif change == 'actor':
        created_by = 'actor:999'
    elif change == 'version':
        context['source_brief_artifact_hash'] = '0' * 64
    elif change == 'signature':
        with sqlite3.connect(source.db) as con:
            con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE feature_id='NO_AI_QUERY_CONTRACT'")
    else:
        from lumenis.system.security.permission import PermissionLevel
        source.gate.revoke_permission(PermissionLevel.ANALYZE)
    result = run_scoped_query(source, context=context, headers=headers, created_by=created_by, expect_rejection=True)
    assert result['status'] == TaskStatus.FAILED.value, result
    expected = {
        'scope': 'SOURCE_BRIEF_SCOPE_MISMATCH',
        'missing_scope': 'DOMAIN_REQUIRED',
        'actor': 'ANALYSIS_TASK_ACTOR_MISMATCH',
        'version': 'ANALYSIS_SOURCE_VERSION_CHANGED',
        'signature': 'Canonical scope Evidence is not signed and verified for this domain',
    }
    if change == 'permission':
        assert result['permission_result'] == 'denied'
        assert 'analyze' in result['error']
    else:
        assert result['error'] == expected[change]
    print('SOURCE_REJECTION', change, result['error'])
    assert not result.get('result_json') or not json.loads(result['result_json'])['verification']['verified']


def test_statistics_preserve_unique_denominator_unknowns_and_true_zero():
    # Pure contract edge: repeated projections of one source count once.
    brief = {'records': [
        {'source_id': 'a', 'source_platform': 'web', 'source_type': 'document', 'publish_datetime': None},
        {'source_id': 'a', 'source_platform': 'web', 'source_type': 'document', 'publish_datetime': None},
        {'source_id': 'b', 'source_platform': None, 'source_type': None, 'publish_datetime': 'invalid'},
    ], 'sample': {'state': 'selected'}, 'scope': {'global': False}}
    result = TaskEngine._source_statistics(brief)
    assert result['input_count'] == 3 and result['unique_source_count'] == 2
    assert result['duplicate_projection_count'] == 1
    assert result['platform_counts'] == {'UNKNOWN': 1, 'web': 1}
    assert result['source_type_counts'] == {'UNKNOWN': 1, 'document': 1}
    assert result['publication_time_known_count'] == 0
    assert result['publication_time_unknown_count'] == 2
    assert result['publication_time_known_ratio'] == 0.0
    assert result['publication_day_counts'] == {}
    assert TaskEngine._source_statistics({**brief, 'records': []})['publication_time_known_ratio'] is None


def test_empty_query_returns_source_owner_next_action_without_fake_counts(scoped_query):
    output = scoped_query.engine._execute_data_query({'context': {}}, 'query_data')
    assert output['status'] == 'unavailable'
    assert output['error'] == 'SCOPED_SOURCE_OWNER_REQUIRED'
    assert output['ai_required'] is False and output['business_outcome'] == 'NOT_OBSERVED'
    assert output['next_action']['path'] == URL + '/start'
    assert 'base_analysis' not in output and 'total_count' not in output


def test_http_source_query_ignores_forged_identity_and_reopens_exact_result(scoped_query):
    source = scoped_query
    response = source.api.post('/api/ai/tasks', headers=source.headers, json={
        'input': '查一下数据统计', 'created_by': 'actor:999',
        'context': {**source.context, 'source_brief_artifact_hash': '0' * 64},
    })
    assert response.status_code == 200, response.get_json()
    task = source.engine.get_task(response.get_json()['task']['task_id'])
    assert task['created_by'] == 'workspace:local'
    assert task['context']['source_brief_artifact_hash'] == source.context['source_brief_artifact_hash']
    task_url = '/api/ai/tasks/' + task['task_id']
    response = source.api.post(task_url + '/run', headers=source.headers, json={})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()['task']
    assert_verified_statistics(source, result)
    fresh = source.app.test_client()
    reopened = fresh.get(task_url, headers=source.headers)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()['task']['result_json'] == result['result_json']
    assert fresh.get(task_url, headers=GLOBAL).status_code == 403
    source.app.config['LUMENIS_OPEN_WORKSPACE'] = False
    assert fresh.get(task_url, headers=source.headers).status_code == 403


def test_unavailable_optional_enhancement_does_not_block_verified_statistics(scoped_query):
    result = run_scoped_query(scoped_query, context={**scoped_query.context, 'ai_enhancement': True})
    data = assert_verified_statistics(scoped_query, result, expected_ai_status='unavailable')
    assert data['output']['ai_analysis_error'] == 'AI_ENHANCEMENT_NOT_ADMITTED_FOR_SOURCE_VERSION'
    assert data['output']['ai_required'] is False
