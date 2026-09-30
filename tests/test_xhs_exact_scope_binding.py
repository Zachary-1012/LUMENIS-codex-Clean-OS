"""Exact source identity survives XHS Raw -> signed Evidence -> Canonical."""
import json
import os
import sqlite3

import pytest


@pytest.fixture
def scope_db(tmp_path, monkeypatch):
    import database
    import subject_registry

    path = tmp_path / 'scope.db'
    with sqlite3.connect(os.environ['LUMENIS_TEST_SEED_DB']) as seed:
        with sqlite3.connect(path) as con:
            seed.backup(con)
    monkeypatch.setenv('ZBC_DB_PATH', str(path))
    monkeypatch.setattr(database, 'DB_PATH', str(path))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'test': 'isolated-scope-test'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'test')
    entity, _ = subject_registry.add_subject({
        'domain_id': 'CTH', 'subject_type': 'company', 'name_zh': '广州太古汇',
        'name_en': 'Guangzhou Taikoo Hui',
    })
    scope = {'domain_id': 'cth', 'subject_id': entity['subject_id'], 'global_scope': False}
    return path, scope


def test_exact_binding_preserves_unknown_time_rejects_query_only_and_is_idempotent(scope_db):
    import database
    from lumenis.system.collector.adapters.secondary_collection import bind_collected_social_scope
    from lumenis.shared.evidence.store import classify_evidence_integrity

    path, scope = scope_db
    for note_id, title in [('source', '广州太古汇周年活动'), ('query-only', '上海兴业太古汇活动')]:
        database.insert_note({'note_id': note_id, 'title': title, 'source_platform': 'xhs',
                              'source_keyword': '广州太古汇', 'publish_datetime': '',
                              'captured_at': '2026-09-30T10:00:00'})
    call = lambda: bind_collected_social_scope(
        ['source', 'query-only'], scope=scope, platform='xhs', keyword='广州太古汇',
        provider='fixture-only',
    )
    first = call()
    assert first['ok'] and first['verified'] == 1 and first['unassigned'] == 1
    assert first['tenant_location_asserted'] is False
    second = call()
    assert second['evidence_ref'] == first['evidence_ref']
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        raw = con.execute("SELECT * FROM notes WHERE note_id='source'").fetchone()
        canonical = con.execute("SELECT * FROM canonical_data WHERE external_id='source'").fetchone()
        assert raw['scope_status'] == canonical['scope_status'] == 'VERIFIED'
        assert raw['subject_id'] == canonical['subject_id'] == scope['subject_id']
        assert not raw['publish_datetime'] and not canonical['publish_datetime']
        assert raw['captured_at'] == canonical['captured_at'] == '2026-09-30T10:00:00'
        assert con.execute("SELECT scope_status FROM notes WHERE note_id='query-only'").fetchone()[0] == 'UNASSIGNED'
        evidence = dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',
                                    (first['evidence_ref'],)).fetchone())
        assert classify_evidence_integrity(evidence)['verified']
        assert json.loads(evidence['inputs_json'])['source_ids'] == ['source']
        assert con.execute("SELECT COUNT(*) FROM canonical_data WHERE external_id='source'").fetchone()[0] == 1


def test_evidence_failure_never_promotes_raw(scope_db, monkeypatch):
    import database
    from lumenis.system.collector.adapters import secondary_collection as owner

    path, scope = scope_db
    database.insert_note({'note_id': 'failure', 'title': '广州太古汇', 'source_platform': 'xhs'})
    monkeypatch.setattr(owner, '_write_prelaunch_evidence', lambda *args, **kwargs: None)
    result = owner.bind_collected_social_scope(['failure'], scope=scope, platform='xhs',
                                              keyword='广州太古汇', provider='fixture-only')
    assert not result['ok'] and result['status'] == 'SCOPE_EVIDENCE_UNAVAILABLE'
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT scope_status FROM notes WHERE note_id='failure'").fetchone()[0] == 'UNASSIGNED'


def test_rednote_real_persistence_binds_accepted_plan(scope_db):
    import database
    from tests.test_rednote_persistence_unknown_comments import _persist_function
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    path, scope = scope_db
    query = build_acquisition_plan(['广州太古汇']).queries[0]
    result = _persist_function(database)({
        'ok': True, 'notes': [{'note_id': 'cdp-note', 'title': '广州太古汇周年活动',
                             'content': '真实采集路径的合成测试输入', 'comments': None}],
    }, acquisition_query=query)
    assert result['ok'] and result['scope_binding']['verified'] == 1
    with sqlite3.connect(path) as con:
        row = con.execute("SELECT subject_id,source_keyword,comments,likes,collects,shares FROM notes WHERE note_id='cdp-note'").fetchone()
        assert row == (scope['subject_id'], '广州太古汇', None, None, None, None)
