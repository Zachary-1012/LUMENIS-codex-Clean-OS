"""Isolated owner regressions for complete, permission-preserving retrieval."""
import json
import sqlite3
from pathlib import Path

import pytest
from tests.test_scoped_source_brief import brief_db, _add_signed
from tests.test_saved_document_workflow import workspace, _source
from tests.test_content_scoped_patterns import client, HEADERS
from tests.test_cth_source_screen_binding import binding
from canonical_data import list_scoped_canonical
from agent_memory.semantic import SemanticMemory
from lumenis.system.security import permission


def _memory(ws):
    from agent_runtime.task_binding import _workspace_binding
    context = {'domain_id': 'cth', 'actor_id': None,
               'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
               'agent_runtime': {'schema_version': 1, 'principal_kind': 'local_workspace',
                                 'principal_ref': 'workspace:local', 'workspace_binding': _workspace_binding()}}
    with ws['repo'].transaction() as con:
        con.execute('CREATE TABLE IF NOT EXISTS ai_task(task_id TEXT PRIMARY KEY,created_by TEXT,context_json TEXT)')
        con.execute('INSERT OR REPLACE INTO ai_task VALUES(?,?,?)', ('memory-task', 'agent_runtime', json.dumps(context)))
    return SemanticMemory(str(ws['root'] / 'isolated.sqlite3'), enabled=True).bind_task('memory-task', None)


def _catalog_source(ws, monkeypatch, asset_id, *, content=None, library='market', scope=None,
                    intended_use='research_reference', rights='owner-approved', identity=None, bind=True):
    import intelligence_library_api as library_api
    from migrations.create_intelligence_assets_table import upgrade
    upgrade(str(ws['root'] / 'isolated.sqlite3'))
    ws['gate'].grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    root = ws['root'] / 'intelligence_library'
    root.mkdir(exist_ok=True)
    monkeypatch.setattr(library_api, '_LIBRARY_ROOT', root)
    monkeypatch.setattr(library_api, 'get_repository', lambda: ws['repo'])
    path = root / (asset_id + '.txt')
    path.write_text(content or 'Original source for ' + asset_id, encoding='utf-8')
    with ws['repo'].transaction() as con:
        con.execute('INSERT INTO intelligence_assets(asset_id,title,sub_library,product,domain,tags,knowledge_status,admission_status,library_path) VALUES(?,?,?,?,?,?,?,?,?)',
            (asset_id, asset_id, library, 'LUMENIS', 'CTH', '["research"]', 'VERIFIED', 'ADMITTED', path.name))
    provenance = {'source_url': 'https://example.org/' + asset_id, 'published_at': None,
                  'captured_at': '2026-10-02T01:00:00Z', 'rights': rights, 'title': asset_id,
                  'intended_use': intended_use,
                  'content_origin': {'kind': 'researcher-note', 'claim_type': 'research_inference',
                                     'research_id': identity or asset_id}}
    args = {'actor': ws['actor'], 'scope': scope or ws['scope'], 'provenance': provenance}
    resource = ws['documents'].document_import_resource(str(path), **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=resource, granted_by='isolated-test')
    source = ws['documents'].import_document(str(path), **args)
    if bind and identity is None and intended_use in {'research_reference', 'report_quote'}:
        preview = library_api.catalog_binding_resource(asset_id, source['evidence_id'], actor=ws['actor'], scope=scope or ws['scope'])
        ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
        library_api.bind_legacy_catalog_asset(asset_id, source['evidence_id'], actor=ws['actor'], scope=scope or ws['scope'])
    return source, path


def test_canonical_predicates_filter_after_full_verification_before_pagination(brief_db):
    with sqlite3.connect(brief_db) as con:
        for index in range(112):
            _add_signed(con, f'{index:03}', subject='SUBJECT-A', title='unrelated')
        con.execute("UPDATE canonical_data SET sentiment='positive',risk_level='low'")
        con.execute("UPDATE canonical_data SET sentiment='negative',risk_level='critical' WHERE source_id IN ('110','111')")
        con.execute("UPDATE canonical_data SET sentiment=NULL,risk_level=NULL WHERE source_id='109'")
        # Most-recent invalid rows must not consume the valid result page.
        con.execute("UPDATE canonical_data SET scope_evidence_ref='missing' WHERE source_id='000'")
        one = list_scoped_canonical(con, product_id='CTH', subject_id='SUBJECT-A', limit=1, sentiment='negative')
        assert one['records'][0]['source_id'] == '110'
        assert one['matched_count'] == 2 and one['unknown_sentiment_count'] == 1
        assert one['scanned_count'] == 112 and one['rejected_count'] == 1 and one['truncated']
        two = list_scoped_canonical(con, product_id='CTH', subject_id='SUBJECT-A', limit=1,
                                   offset=one['next_offset'], risk_levels=['high', 'critical'])
        assert two['records'][0]['source_id'] == '111'
        assert not two['truncated'] and two['unknown_risk_count'] == 1
        with pytest.raises(ValueError):
            list_scoped_canonical(con, product_id='CTH', risk_levels=["high') OR 1=1 --"])


def test_cth_negative_and_risk_screens_find_old_matches_and_report_unknown(brief_db):
    import experience_screens as screens
    with sqlite3.connect(brief_db) as con:
        for index in range(105):
            _add_signed(con, f'{index:03}', subject='SUBJECT-A')
        con.execute("UPDATE canonical_data SET sentiment='positive',risk_level='low'")
        con.execute("UPDATE canonical_data SET sentiment='negative',risk_level='high' WHERE source_id='104'")
        con.execute("UPDATE canonical_data SET sentiment=NULL,risk_level=NULL WHERE source_id='103'")
    negative, risk = screens._build_cth06(binding=binding()), screens._build_cth09(binding=binding())
    assert negative['sections'][1]['rows'][0]['id'] == 'canonical-104'
    assert negative['truth']['unknown_classification_count'] == 1
    assert risk['sections'][1]['items'][0]['id'] == 'canonical-104'
    assert risk['truth']['unknown_risk_count'] == 1


def test_semantic_matches_after_100_and_active_after_20_and_errors_are_not_empty(workspace):
    ws = workspace
    memory = _memory(ws)
    with ws['repo'].transaction() as con:
        for index in range(105):
            _add_signed(con, f'{index:03}', subject='SUBJECT-A', title='Older needle' if index == 104 else 'Other')
        con.execute('CREATE TABLE rule_version_registry(version TEXT,description TEXT,is_active INTEGER,applied_at TEXT)')
        con.executemany('INSERT INTO rule_version_registry VALUES(?,?,?,?)',
            [(str(index), 'rule', index == 0, f'{index:03}') for index in range(25)])
    assert memory.search_assets('needle')[0]['canonical_id'] == 'canonical-104'
    assert memory.get_asset('canonical-104')['canonical_id'] == 'canonical-104'
    assert memory.get_active_rule_version()['version'] == '0'
    assert len(memory.get_rule_history()) == 20
    assert memory.search_assets('does-not-exist') == []
    with ws['repo'].transaction() as con:
        con.execute('DROP TABLE rule_version_registry')
    with pytest.raises(sqlite3.OperationalError):
        memory.get_active_rule_version()
    with ws['repo'].transaction() as con:
        con.execute('DROP TABLE canonical_data')
    with pytest.raises(sqlite3.OperationalError):
        memory.search_assets('needle')


def test_catalog_stable_ids_sub_library_tags_and_reopen(workspace, monkeypatch):
    ws = workspace
    source, _ = _catalog_source(ws, monkeypatch, 'AST-0001')
    memory = _memory(ws)
    assert memory.get_asset('AST-0001')['asset_id'] == 'AST-0001'
    assert memory.get_asset('AST-0001')['source_id'] == source['source_id']
    assert memory.get_asset('AST-0001')['asset_id'] != source['canonical_id']
    assert memory.get_assets_by_library('market')[0]['asset_id'] == 'AST-0001'
    assert memory.search_assets('Original', tags=['research'])[0]['asset_id'] == 'AST-0001'
    assert memory.search_assets('Original', tags=['missing']) == []
    reopened = SemanticMemory(memory.db_path, enabled=True).bind_task('memory-task', None)
    assert reopened.get_asset('AST-0001') == memory.get_asset('AST-0001')
    with ws['repo'].transaction() as con:
        con.execute("UPDATE intelligence_assets SET admission_status='CANDIDATE' WHERE asset_id='AST-0001'")
    assert reopened.get_asset('AST-0001') is None
    assert reopened.last_read_status == 'partial'


def test_forged_research_identity_path_escape_and_original_hash_changes_fail_closed(client, monkeypatch):
    http, ws = client
    first, path = _catalog_source(ws, monkeypatch, 'AST-original', content='Original canonical library source')
    forged, _ = _catalog_source(ws, monkeypatch, 'AST-other', content='Different invented source', identity='AST-original')
    response = http.get('/api/content/research/search?q=Different', headers=HEADERS).get_json()
    assert response['db_results'] == [] and not response['verification_complete']
    response = http.get('/api/content/research/search?q=Original', headers=HEADERS).get_json()
    assert [row['evidence_id'] for row in response['db_results']] == [first['evidence_id']]
    path.write_text('Source changed after admission', encoding='utf-8')
    assert http.get('/api/content/research/search?q=Original', headers=HEADERS).get_json()['db_results'] == []
    with ws['repo'].transaction() as con:
        con.execute('UPDATE intelligence_assets SET library_path=? WHERE asset_id=?', ('../outside.txt', 'AST-original'))
    assert http.get('/api/content/resources', headers=HEADERS).get_json()['data'] == []


def test_same_bytes_never_share_asset_use_or_revocation(client, monkeypatch):
    http, ws = client
    allowed, _ = _catalog_source(ws, monkeypatch, 'AST-allowed', content='Identical bytes')
    denied, _ = _catalog_source(ws, monkeypatch, 'AST-denied', content='Identical bytes', intended_use='internal_draft')
    found = http.get('/api/content/research/search?q=Identical', headers=HEADERS).get_json()
    assert [row['asset_id'] for row in found['db_results']] == ['AST-allowed']
    with ws['repo'].transaction() as con:
        con.execute("UPDATE intelligence_assets SET admission_status='WITHDRAWN' WHERE asset_id='AST-allowed'")
    fresh = ws['app'].test_client()
    found = fresh.get('/api/content/research/search?q=Identical', headers=HEADERS).get_json()
    assert found['db_results'] == [] and found['state'] == 'partial'
    explicit = fresh.get('/api/content/research/search?q=Identical&evidence_id=' + str(denied['evidence_id']), headers=HEADERS)
    assert explicit.status_code >= 400


def test_content_discovers_beyond_8_and_100_with_real_pagination_and_filters(client, monkeypatch):
    http, ws = client
    oldest = _source(ws, filename='oldest.txt', source_url='https://example.org/oldest')[2]
    for index in range(104):
        _source(ws, filename=f'source-{index}.txt', source_url=f'https://example.org/{index}')
    first = http.get('/api/content/research/search?q=Original&limit=100', headers=HEADERS).get_json()
    assert len(first['db_results']) == 100 and first['matched_count'] == 105 and first['has_more']
    second = http.get('/api/content/research/search?q=Original&limit=100&offset=100', headers=HEADERS).get_json()
    assert len(second['db_results']) == 5 and not second['has_more']
    assert oldest['evidence_id'] in {item['evidence_id'] for item in second['db_results']}
    cat, _ = _catalog_source(ws, monkeypatch, 'AST-resources', content='Needle resource', library='video')
    resources = http.get('/api/content/resources?q=Needle&category=video&limit=1', headers=HEADERS).get_json()
    assert resources['count'] == 1 and resources['data'][0]['asset_id'] == 'AST-resources'
    assert http.get('/api/content/resources?q=Missing&category=video', headers=HEADERS).get_json()['data'] == []
    assert http.get('/api/content/resources?q=Needle&category=audio', headers=HEADERS).get_json()['data'] == []
    assert http.get('/api/content/resources?limit=0', headers=HEADERS).status_code == 400


def test_cross_scope_and_generic_canonical_copy_cannot_restore_catalog_source(client, monkeypatch):
    from subject_registry import add_subject
    from canonical_data import CanonicalRecord, persist_canonical
    http, ws = client
    a, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'A', 'name_zh': 'A'})
    b, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'B', 'name_zh': 'B'})
    focused = {**ws['scope'], 'global_scope': False, 'subject_id': a['subject_id']}
    source, _ = _catalog_source(ws, monkeypatch, 'AST-scoped', content='Scoped private source', scope=focused)
    own = {**HEADERS, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': a['subject_id']}
    other = {**own, 'X-Subject-ID': b['subject_id']}
    assert len(http.get('/api/content/research/search?q=Scoped', headers=own).get_json()['db_results']) == 1
    assert http.get('/api/content/research/search?q=Scoped', headers=other).get_json()['db_results'] == []
    memory = _memory(ws)
    with ws['repo'].transaction() as con:
        persist_canonical(con, CanonicalRecord(canonical_id='generic-copy', product_id='CTH', domain_id='cth',
            source_id=source['source_id'], subject_id=a['subject_id'], source_type='note', source_table='notes',
            title='Leaked copy', content='Scoped private source', scope_status='VERIFIED',
            scope_evidence_ref=str(source['evidence_id'])))
        con.execute("UPDATE intelligence_assets SET admission_status='WITHDRAWN' WHERE asset_id='AST-scoped'")
    assert memory.get_canonical('generic-copy') is None
    assert memory.search_assets('Leaked') == []
    assert ws['app'].test_client().get('/api/content/research/search?q=Scoped', headers=own).get_json()['db_results'] == []


def test_storage_error_is_explicit_unavailable_not_successful_empty(client):
    http, ws = client
    with ws['repo'].transaction() as con:
        con.execute('DROP TABLE app_evidence_records')
    response = http.get('/api/content/research/search?q=anything', headers=HEADERS)
    assert response.status_code == 503
    assert response.get_json()['code'] == 'CONTENT_RESEARCH_STORAGE_UNAVAILABLE'


def test_library_http_routes_share_same_authorized_discovery(client, monkeypatch):
    import intelligence_library_api as library_api
    http, ws = client
    monkeypatch.setattr(library_api, '_get_db', lambda: ws['repo'].connect(read_only=True, wal=False))
    ws['app'].register_blueprint(library_api.intelligence_library_bp)
    source, _ = _catalog_source(ws, monkeypatch, 'AST-http', content='Permitted library reference')
    found = http.get('/api/intelligence/library/search?q=Permitted', headers=HEADERS)
    assert found.status_code == 200 and found.get_json()['data'][0]['asset_id'] == 'AST-http'
    detail = http.get('/api/intelligence/library/AST-http', headers=HEADERS)
    assert detail.get_json()['data']['evidence_id'] == source['evidence_id']
    assert http.get('/api/intelligence/library?per_page=1', headers=HEADERS).get_json()['pagination']['total'] == 1
    assert http.get('/api/intelligence/library/stats', headers=HEADERS).get_json()['data']['total'] == 1
    assert http.get('/api/intelligence/library/sub_libraries', headers=HEADERS).get_json()['data'] == [{'name': 'market', 'count': 1}]
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET integrity_digest='tampered' WHERE id=?", (source['evidence_id'],))
    assert ws['app'].test_client().get('/api/intelligence/library/AST-http', headers=HEADERS).status_code == 404
    assert http.get('/api/intelligence/library/search?q=Permitted', headers=HEADERS).get_json()['state'] == 'partial'


def test_original_artifact_deletion_and_scope_revocation_prevent_reopen(client, monkeypatch):
    from subject_registry import add_subject
    http, ws = client
    subject, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Source scope', 'name_zh': '资料范围'})
    scope = {**ws['scope'], 'global_scope': False, 'subject_id': subject['subject_id']}
    source, _ = _catalog_source(ws, monkeypatch, 'AST-revocation', scope=scope)
    headers = {**HEADERS, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': subject['subject_id']}
    assert len(http.get('/api/content/resources', headers=headers).get_json()['data']) == 1
    with ws['repo'].transaction() as con:
        con.execute("DELETE FROM lumenis_shared_artifacts WHERE source_execution_id=?", (source['source_id'],))
    fresh = ws['app'].test_client()
    response = fresh.get('/api/content/resources', headers=headers).get_json()
    assert response['data'] == [] and not response['verification_complete']
    with ws['repo'].transaction() as con:
        con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?", (subject['subject_id'],))
    assert fresh.get('/api/content/resources', headers=headers).status_code >= 400


def test_unknown_catalog_labels_do_not_become_fact_or_borrow_other_domain(client, monkeypatch):
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-labels')
    memory = _memory(ws)
    with ws['repo'].transaction() as con:
        con.execute("UPDATE intelligence_assets SET knowledge_status='PENDING' WHERE asset_id='AST-labels'")
    assert memory.get_asset('AST-labels') is None
    # Research remains source statements; not an admitted fact.
    rows = http.get('/api/content/resources', headers=HEADERS).get_json()['data']
    assert rows[0]['fact_verification'] == 'NOT_VERIFIED'
    with ws['repo'].transaction() as con:
        con.execute("UPDATE intelligence_assets SET knowledge_status='VERIFIED',domain='BMP' WHERE asset_id='AST-labels'")
    assert http.get('/api/content/resources', headers=HEADERS).get_json()['data'] == []


def test_generation_discovery_keeps_exact_source_bindings(client, monkeypatch):
    import content_generation as content
    http, ws = client
    _, _, source = _source(ws)
    def model(system_prompt, user_prompt, level='high'):
        assert 'evidence:' + str(source['evidence_id']) in user_prompt
        return '{"headline":"Original output"}', 'isolated-test', {'model': 'not-a-real-model'}
    monkeypatch.setattr(content, '_call_ai', model)
    response = http.post('/api/content/generate', headers=HEADERS,
                         json={'content_type': 'ad_copy', 'brand': 'Original'})
    assert response.status_code == 200, response.get_json()
    evidence_id = response.get_json()['evidence_id']
    with ws['repo'].connection(read_only=True) as con:
        stored = json.loads(con.execute('SELECT input_json FROM content_generation_evidence WHERE evidence_id=?',
                                       (evidence_id,)).fetchone()[0])
    assert stored['_content_sources'][0]['evidence_id'] == source['evidence_id']
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET integrity_digest='revoked' WHERE id=?", (source['evidence_id'],))
    assert ws['app'].test_client().get('/api/content/evidence/' + evidence_id, headers=HEADERS).status_code == 404


def test_cth_http_paginates_matching_rows_instead_of_100_unrelated(brief_db, monkeypatch):
    from flask import Flask
    import experience_runtime as runtime
    import experience_screens as screens
    with sqlite3.connect(brief_db) as con:
        for index in range(210):
            _add_signed(con, f'{index:03}', subject='SUBJECT-A')
        con.execute("UPDATE canonical_data SET sentiment=CASE WHEN source_id>='105' THEN 'negative' ELSE 'positive' END")
    monkeypatch.setattr(runtime, '_all_builders', lambda: screens.SCREEN_BUILDERS)
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (binding(), None))
    app = Flask(__name__)
    app.register_blueprint(runtime.experience_bp)
    http = app.test_client()
    page = http.get('/api/experience/screen/CTH-06').get_json()
    assert len(page['sections'][1]['rows']) == 100
    assert page['truth']['read']['matched_count'] == 105
    next_page = http.get('/api/experience/screen/CTH-06?offset=100').get_json()
    assert len(next_page['sections'][1]['rows']) == 5
    assert not next_page['truth']['read']['truncated']
    assert next_page['sections'][1]['rows'][-1]['id'] == 'canonical-209'


def test_complete_read_does_not_return_source_withdrawn_mid_scan(brief_db, monkeypatch):
    import canonical_data as canonical
    with sqlite3.connect(brief_db) as con:
        first = _add_signed(con, 'a', subject='SUBJECT-A')
        _add_signed(con, 'b', subject='SUBJECT-A')
        con.execute("UPDATE canonical_data SET sentiment='negative'")
        original = canonical._validate_canonical_scope
        revoked = False
        def withdraw(connection, record):
            nonlocal revoked
            result = original(connection, record)
            if record.source_id == 'b' and not revoked:
                revoked = True
                connection.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (first,))
            return result
        monkeypatch.setattr(canonical, '_validate_canonical_scope', withdraw)
        with pytest.raises((PermissionError, RuntimeError, ValueError)):
            canonical.list_scoped_canonical(con, product_id='CTH', subject_id='SUBJECT-A',
                sentiment='negative', complete=True)


def test_catalog_stats_reverify_earlier_pages_before_return(client, monkeypatch):
    import intelligence_library_api as library_api
    http, ws = client
    monkeypatch.setattr(library_api, '_get_db', lambda: ws['repo'].connect(read_only=True, wal=False))
    ws['app'].register_blueprint(library_api.intelligence_library_bp)
    for name in ['AST-first', 'AST-second', 'AST-newest']:
        _catalog_source(ws, monkeypatch, name)
    original = library_api.discover_research_sources
    def revoke_previous(connection, **kwargs):
        kwargs['limit'] = 1
        result = original(connection, **kwargs)
        if kwargs['offset'] == 2:
            with ws['repo'].transaction() as con:
                con.execute("UPDATE intelligence_assets SET admission_status='WITHDRAWN' WHERE asset_id='AST-newest'")
        return result
    monkeypatch.setattr(library_api, 'discover_research_sources', revoke_previous)
    response = http.get('/api/intelligence/library/stats', headers=HEADERS)
    assert response.status_code >= 400 and response.get_json()['ok'] is False
    assert 'AST-newest' not in response.get_data(as_text=True)


def test_semantic_combined_search_rejects_canonical_withdrawal_during_library_scan(workspace, monkeypatch):
    ws = workspace
    memory = _memory(ws)
    with ws['repo'].transaction() as con:
        first = _add_signed(con, 'earlier', subject='SUBJECT-A', title='Needle')
    _catalog_source(ws, monkeypatch, 'AST-second-stage')
    original = memory._research_assets
    def withdraw_after_canonical(connection, **selectors):
        result = original(connection, **selectors)
        with ws['repo'].transaction() as con:
            con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (first,))
        return result
    monkeypatch.setattr(memory, '_research_assets', withdraw_after_canonical)
    with pytest.raises(PermissionError, match='MEMORY_SOURCE_CHANGED'):
        memory.search_assets('Needle')


def test_explicit_generation_sources_reverify_all_sources_before_model(client, monkeypatch):
    import intelligence_library_api as library
    import content_generation as content
    http, ws = client
    first, _ = _catalog_source(ws, monkeypatch, 'AST-first')
    second, _ = _catalog_source(ws, monkeypatch, 'AST-second')
    original = library.verified_research_source
    changed = False
    def withdraw_first(connection, evidence_id, **kwargs):
        nonlocal changed
        result = original(connection, evidence_id, **kwargs)
        if evidence_id == second['evidence_id'] and not changed:
            changed = True
            with ws['repo'].transaction() as con:
                con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (first['evidence_id'],))
        return result
    monkeypatch.setattr(library, 'verified_research_source', withdraw_first)
    monkeypatch.setattr(content, '_call_ai', lambda *args, **kwargs: pytest.fail('Source invalidation must stop the model'))
    response = http.post('/api/content/generate', headers=HEADERS,
        json={'content_type': 'ad_copy', 'source_evidence_refs': [first['evidence_id'], second['evidence_id']]})
    assert response.status_code >= 400 and response.get_json()['ok'] is False
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM content_generation_evidence').fetchone()[0] == 0


@pytest.mark.parametrize('withdraw_source', [False, True])
def test_source_free_creation_preserves_empty_or_partial_and_unverified_status(client, monkeypatch, withdraw_source):
    import content_generation as content
    http, ws = client
    if withdraw_source:
        _, _, source = _source(ws)
        with ws['repo'].transaction() as con:
            con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (source['evidence_id'],))
    def original_only(system_prompt, user_prompt, level='high'):
        assert '[evidence:' not in user_prompt
        assert '不得编造已核实事实或引用' in user_prompt
        return '{"title":"Original idea","body":"An unverified creative proposal"}', 'isolated-test', {'model': 'not-a-real-model'}
    monkeypatch.setattr(content, '_call_ai', original_only)
    response = http.post('/api/content/generate', headers=HEADERS,
        json={'content_type': 'ad_copy', 'brand': 'Original'})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result['research']['state'] == ('partial' if withdraw_source else 'empty')
    assert result['research']['has_research'] is False
    assert result['research']['fact_verification'] == 'NOT_VERIFIED'
    assert result['research']['verification_complete'] is not withdraw_source
    with ws['repo'].connection(read_only=True) as con:
        row = con.execute('SELECT * FROM content_generation_evidence WHERE evidence_id=?', (result['evidence_id'],)).fetchone()
        inputs = json.loads(row['input_json'])
    assert inputs['_content_research']['state'] == result['research']['state']
    assert not inputs.get('_content_sources') and row['research_context'] == ''
    assert http.get('/api/content/evidence/' + result['evidence_id'], headers=HEADERS).status_code == 200


def test_withdrawn_generation_citations_never_mix_into_new_source_free_draft(client, monkeypatch):
    import content_generation as content
    http, ws = client
    _, _, source = _source(ws)
    prompts = []
    def model(system_prompt, user_prompt, level='high'):
        prompts.append(user_prompt)
        return '{"title":"Independent draft"}', 'isolated-test', {'model': 'not-a-real-model'}
    monkeypatch.setattr(content, '_call_ai', model)
    selected = {'content_type': 'ad_copy', 'source_evidence_refs': [source['evidence_id']]}
    old = http.post('/api/content/generate', headers=HEADERS, json=selected).get_json()
    assert old['ok'] and '[evidence:' + str(source['evidence_id']) in prompts[-1]
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (source['evidence_id'],))
    assert http.get('/api/content/evidence/' + old['evidence_id'], headers=HEADERS).status_code == 404
    regenerated = http.post('/api/content/feedback', headers=HEADERS,
        json={'evidence_id': old['evidence_id'], 'feedback': 'Use the old claim again'})
    assert regenerated.status_code >= 400 and not regenerated.get_json()['ok']
    explicit = http.post('/api/content/generate', headers=HEADERS, json=selected)
    assert explicit.status_code >= 400 and not explicit.get_json()['ok']
    assert len(prompts) == 1
    new = http.post('/api/content/generate', headers=HEADERS, json={'content_type': 'ad_copy'}).get_json()
    assert new['ok'] and new['research']['state'] == 'partial' and not new['research']['has_research']
    assert len(prompts) == 2 and '[evidence:' not in prompts[-1] and 'Original source line' not in prompts[-1]
    with ws['repo'].connection(read_only=True) as con:
        inputs = json.loads(con.execute('SELECT input_json FROM content_generation_evidence WHERE evidence_id=?',
                                       (new['evidence_id'],)).fetchone()[0])
    assert not inputs.get('_content_sources') and 'source_evidence_refs' not in inputs


def test_legacy_catalog_binding_needs_exact_approval_not_claim_or_default_allow(client, monkeypatch):
    import intelligence_library_api as library
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-legacy', bind=False)
    result = http.get('/api/content/resources', headers=HEADERS).get_json()
    assert result['data'] == [] and result['state'] == 'partial'
    assert result['unavailable_reasons'] == {'LIBRARY_PARENT_BINDING_REQUIRED': 1}
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-legacy', source['evidence_id'], **args)
    assert preview['state'] == 'APPROVAL_REQUIRED'
    assert preview['binding']['context']['domain_id'] == 'cth'
    assert preview['binding']['source_version'] == 'document-import/1'
    assert preview['binding']['fact_verification'] == 'NOT_VERIFIED'
    with pytest.raises(PermissionError, match='LIBRARY_BINDING_EXACT_APPROVAL_REQUIRED'):
        library.bind_legacy_catalog_asset('AST-legacy', source['evidence_id'], **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, granted_by='isolated-test')
    with pytest.raises(PermissionError, match='LIBRARY_BINDING_EXACT_APPROVAL_REQUIRED'):
        library.bind_legacy_catalog_asset('AST-legacy', source['evidence_id'], **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
    bound = library.bind_legacy_catalog_asset('AST-legacy', source['evidence_id'], **args)
    assert bound['state'] == 'BOUND' and bound['fact_verification'] == 'NOT_VERIFIED'
    result = http.get('/api/content/resources', headers=HEADERS).get_json()
    assert [row['evidence_id'] for row in result['data']] == [source['evidence_id']]
    with pytest.raises(ValueError, match='LIBRARY_PARENT_BINDING_CONFLICT'):
        library.bind_legacy_catalog_asset('AST-legacy', source['evidence_id'], **args)


def test_same_bytes_forged_catalog_id_cannot_borrow_other_scope_or_original_binding(client, monkeypatch):
    import intelligence_library_api as library
    from subject_registry import add_subject
    http, ws = client
    a, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Catalog A', 'name_zh': 'A'})
    b, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Catalog B', 'name_zh': 'B'})
    scope_a = {**ws['scope'], 'global_scope': False, 'subject_id': a['subject_id']}
    scope_b = {**ws['scope'], 'global_scope': False, 'subject_id': b['subject_id']}
    first, _ = _catalog_source(ws, monkeypatch, 'AST-original-owner', content='Same exact bytes', scope=scope_a,
                               intended_use='report_quote', rights='public-reference-only')
    copy, _ = _catalog_source(ws, monkeypatch, 'AST-copy', content='Same exact bytes', scope=scope_b,
                              identity='AST-original-owner', intended_use='research_reference', rights='owner-approved')
    own = {**HEADERS, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': a['subject_id']}
    other = {**own, 'X-Subject-ID': b['subject_id']}
    assert [r['evidence_id'] for r in http.get('/api/content/resources', headers=own).get_json()['data']] == [first['evidence_id']]
    denied = http.get('/api/content/resources', headers=other).get_json()
    assert denied['data'] == [] and denied['state'] == 'partial'
    assert denied['unavailable_reasons']['LIBRARY_PARENT_BINDING_UNVERIFIED'] == 1
    args = {'actor': ws['actor'], 'scope': scope_b}
    preview = library.catalog_binding_resource('AST-original-owner', copy['evidence_id'], **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
    with pytest.raises(ValueError, match='LIBRARY_PARENT_BINDING_CONFLICT'):
        library.bind_legacy_catalog_asset('AST-original-owner', copy['evidence_id'], **args)
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE feature_id=? AND asset_id=?",
                    (library._BINDING_FEATURE, 'AST-original-owner'))
    assert ws['app'].test_client().get('/api/content/resources', headers=own).get_json()['data'] == []
    assert ws['app'].test_client().get('/api/content/resources', headers=other).get_json()['data'] == []


@pytest.mark.parametrize('change', ['expired', 'revoked', 'catalog', 'source'])
def test_catalog_binding_preparation_cannot_survive_changed_approval_or_parent(client, monkeypatch, change):
    import intelligence_library_api as library
    http, ws = client
    source, path = _catalog_source(ws, monkeypatch, 'AST-pending', bind=False)
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-pending', source['evidence_id'], **args)
    token = ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,
        resource=preview['resource'], duration_minutes=-1 if change == 'expired' else 30, granted_by=preview['caller'])
    if change == 'revoked':
        ws['gate'].revoke_approval(token)
    elif change == 'catalog':
        with ws['repo'].transaction() as con:
            con.execute("UPDATE intelligence_assets SET library_path='renamed.txt' WHERE asset_id='AST-pending'")
        (path.parent / 'renamed.txt').write_bytes(path.read_bytes())
    elif change == 'source':
        with ws['repo'].transaction() as con:
            con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (source['evidence_id'],))
    with pytest.raises((ValueError, PermissionError)):
        library.bind_legacy_catalog_asset('AST-pending', source['evidence_id'], **args)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?', (library._BINDING_FEATURE,)).fetchone()[0] == 0


@pytest.mark.parametrize('change', ['revoke_approval', 'change_original'])
def test_catalog_binding_commit_revalidates_and_rolls_back(client, monkeypatch, change):
    import intelligence_library_api as library
    from lumenis.shared.evidence import store
    http, ws = client
    source, path = _catalog_source(ws, monkeypatch, 'AST-race', bind=False)
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-race', source['evidence_id'], **args)
    token = ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
    original = store.record_evidence
    def changed_during_commit(*args, **kwargs):
        result = original(*args, **kwargs)
        if kwargs.get('feature_id') == library._BINDING_FEATURE:
            if change == 'revoke_approval':
                ws['gate'].revoke_approval(token)
            else:
                path.write_text('Changed during admission', encoding='utf-8')
        return result
    monkeypatch.setattr(store, 'record_evidence', changed_during_commit)
    with pytest.raises((ValueError, PermissionError)):
        library.bind_legacy_catalog_asset('AST-race', source['evidence_id'], **args)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?', (library._BINDING_FEATURE,)).fetchone()[0] == 0


def test_research_identity_without_catalog_association_remains_a_source_reference(client, monkeypatch):
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-unrelated', identity='research-note-independent')
    rows = http.get('/api/content/resources', headers=HEADERS).get_json()['data']
    assert [row['source_id'] for row in rows] == [source['source_id']]
    assert rows[0]['asset_id'] == source['source_id'] and not rows[0]['catalog_bound']
    assert rows[0]['sub_library'] is None and rows[0]['fact_verification'] == 'NOT_VERIFIED'


@pytest.mark.parametrize('change', ['wrong_caller', 'expires_during_final_check'])
def test_catalog_binding_lease_enforces_exact_actor_and_final_expiry(client, monkeypatch, change):
    import intelligence_library_api as library
    from datetime import datetime, timedelta
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-final-grant', bind=False)
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-final-grant', source['evidence_id'], **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'],
        granted_by='another-actor' if change == 'wrong_caller' else preview['caller'])
    if change == 'expires_during_final_check':
        original = library._prepare_catalog_binding
        calls = 0
        def expire_after_verification(*args, **kwargs):
            nonlocal calls
            result = original(*args, **kwargs)
            calls += 1
            if calls == 3:
                class FutureClock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return datetime.now(tz) + timedelta(hours=1)
                monkeypatch.setattr(permission, 'datetime', FutureClock)
            return result
        monkeypatch.setattr(library, '_prepare_catalog_binding', expire_after_verification)
    with pytest.raises(PermissionError, match='INTELLIGENCE_BINDING_LEASE_APPROVAL_REVOKED'):
        library.bind_legacy_catalog_asset('AST-final-grant', source['evidence_id'], **args)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?', (library._BINDING_FEATURE,)).fetchone()[0] == 0


def test_catalog_binding_commit_serializes_concurrent_approval_withdrawal(client, monkeypatch):
    import threading
    import intelligence_library_api as library
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-concurrent', bind=False)
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-concurrent', source['evidence_id'], **args)
    token = ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
    original = library._prepare_catalog_binding
    calls, workers = 0, []
    started, done = threading.Event(), threading.Event()
    def withdraw():
        started.set()
        ws['gate'].revoke_approval(token)
        done.set()
    def contend_after_verification(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 3:
            worker = threading.Thread(target=withdraw)
            workers.append(worker)
            worker.start()
            assert started.wait(1)
            assert not done.wait(0.02), 'Withdrawal must serialize after the held commit lease'
        return result
    monkeypatch.setattr(library, '_prepare_catalog_binding', contend_after_verification)
    bound = library.bind_legacy_catalog_asset('AST-concurrent', source['evidence_id'], **args)
    for worker in workers:
        worker.join(timeout=2)
        assert not worker.is_alive()
    assert done.is_set() and bound['state'] == 'BOUND'
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?', (library._BINDING_FEATURE,)).fetchone()[0] == 1
    assert ws['gate'].get_valid_approval_token(permission.OperationType.DATA_IMPORT.value, preview['resource'], exact=True) is None


def test_library_missing_schema_is_not_an_empty_catalog(client, monkeypatch):
    import intelligence_library_api as library
    http, ws = client
    monkeypatch.setattr(library, '_get_db', lambda: ws['repo'].connect(read_only=True, wal=False))
    ws['app'].register_blueprint(library.intelligence_library_bp)
    _source(ws)
    for url in ['/api/intelligence/library', '/api/intelligence/library/stats']:
        response = http.get(url, headers=HEADERS)
        assert response.status_code == 503
        assert response.get_json()['code'] == 'LIBRARY_SCHEMA_UNAVAILABLE'


@pytest.mark.parametrize('withdraw_after_discovery', [False, True])
def test_podcast_research_uses_one_discovery_with_exact_live_bindings(client, monkeypatch, withdraw_after_discovery):
    import content_generation as content
    http, ws = client
    chosen, _ = _catalog_source(ws, monkeypatch, 'AST-topic', content='Needle topic reference')
    _catalog_source(ws, monkeypatch, 'AST-other-topic', content='Unrelated reference')
    original = content._discover_research
    reads, prompts = [], []
    def discovery(query='', **kwargs):
        result = original(query, **kwargs)
        reads.append(query)
        if withdraw_after_discovery:
            with ws['repo'].transaction() as con:
                con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (chosen['evidence_id'],))
        return result
    monkeypatch.setattr(content, '_discover_research', discovery)
    def model(system_prompt, user_prompt, level='high'):
        prompts.append(user_prompt)
        assert not withdraw_after_discovery, 'Withdrawn prompt references must not reach the model'
        assert 'Needle topic reference' in user_prompt and 'Unrelated reference' not in user_prompt
        return '{"topic":"Original outline"}', 'isolated-test', {'model': 'not-a-real-model'}
    monkeypatch.setattr(content, '_call_ai', model)
    response = http.post('/api/content/podcast-research', headers=HEADERS, json={'topic': 'Needle'})
    assert reads == ['Needle']
    if withdraw_after_discovery:
        assert response.status_code >= 400 and not response.get_json()['ok']
        assert prompts == []
    else:
        assert response.status_code == 200, response.get_json()
        result = response.get_json()
        assert result['research']['query'] == 'Needle' and result['research']['has_research']
        with ws['repo'].connection(read_only=True) as con:
            inputs = json.loads(con.execute('SELECT input_json FROM content_generation_evidence WHERE evidence_id=?',
                                           (result['evidence_id'],)).fetchone()[0])
        assert [row['evidence_id'] for row in inputs['_content_sources']] == [chosen['evidence_id']]


@pytest.mark.parametrize('path', ['/api/content/ad-strategy', '/api/content/brand-report/generate'])
def test_generation_wrappers_expose_partial_and_reject_explicit_withdrawn_sources(client, monkeypatch, path):
    import content_generation as content
    http, ws = client
    _, _, source = _source(ws)
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET integrity_digest='withdrawn' WHERE id=?", (source['evidence_id'],))
    calls = []
    def model(system_prompt, user_prompt, level='high'):
        calls.append(user_prompt)
        assert '[evidence:' not in user_prompt and '待核验' in user_prompt
        return '{"title":"Original proposal"}', 'isolated-test', {'model': 'not-a-real-model'}
    monkeypatch.setattr(content, '_call_ai', model)
    response = http.post(path, headers=HEADERS, json={'brand': 'Original'})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['research']['state'] == 'partial'
    assert response.get_json()['research']['has_research'] is False
    assert response.get_json()['research']['fact_verification'] == 'NOT_VERIFIED'
    denied = http.post(path, headers=HEADERS, json={'brand': 'Original', 'source_evidence_refs': [source['evidence_id']]})
    assert denied.status_code >= 400 and denied.get_json()['ok'] is False
    assert len(calls) == 1


def test_unbound_legacy_catalog_is_unavailable_not_empty(client, monkeypatch):
    import intelligence_library_api as library
    from migrations.create_intelligence_assets_table import upgrade
    http, ws = client
    upgrade(str(ws['root'] / 'isolated.sqlite3'))
    with ws['repo'].transaction() as con:
        con.execute("INSERT INTO intelligence_assets(asset_id,domain,product,admission_status,knowledge_status) VALUES('legacy-unbound','CTH','LUMENIS','ADMITTED','FACT')")
    monkeypatch.setattr(library, '_get_db', lambda: ws['repo'].connect(read_only=True, wal=False))
    ws['app'].register_blueprint(library.intelligence_library_bp)
    result = http.get('/api/intelligence/library', headers=HEADERS).get_json()
    assert result['data'] == []
    assert result['state'] == 'partial' and result['verification_complete'] is False

    assert result['catalog_binding_code'] == 'LIBRARY_PARENT_BINDING_REQUIRED'
    assert 'legacy-unbound' not in json.dumps(result)
    stats = http.get('/api/intelligence/library/stats', headers=HEADERS).get_json()
    assert stats['state'] == 'partial' and stats['verification_complete'] is False
    assert stats['catalog_binding_code'] == 'LIBRARY_PARENT_BINDING_REQUIRED'



def test_catalog_deleted_original_is_partial_not_a_verified_zero(client, monkeypatch):
    import intelligence_library_api as library
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-orphan')
    monkeypatch.setattr(library, '_get_db', lambda: ws['repo'].connect(read_only=True, wal=False))
    ws['app'].register_blueprint(library.intelligence_library_bp)
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM app_evidence_records WHERE id=?', (source['evidence_id'],))
    result = http.get('/api/intelligence/library/stats', headers=HEADERS).get_json()
    assert result['data']['total'] == 0 and result['state'] == 'partial'
    assert not result['verification_complete']
    assert result['unavailable_reasons']['WORK_EVIDENCE_MISSING'] == 1


@pytest.mark.parametrize('database_role', ['user', 'owner'])
def test_catalog_migration_rejects_ordinary_actor_before_reading_legacy_metadata(client, monkeypatch, database_role):
    import intelligence_library_api as library
    from tests.test_bmp09_request_binding import accounts
    from lumenis.shared.reporting.saved_work import authorize_saved_work, _verified_evidence
    http, ws = client
    _catalog_source(ws, monkeypatch, 'AST-other-owner', content='Same bytes', bind=False)
    accounts(ws)
    with ws['repo'].transaction() as con:
        con.execute("UPDATE v4_users SET role=? WHERE id=1", (database_role,))
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','reports',?,?)",
                        [(action, json.dumps({'global': True})) for action in ('read', 'write')])
    actor = {'id': 1, 'role': 'owner'}  # The client role claim must not grant migration.
    actor_ws = {**ws, 'actor': actor}
    copy, _ = _catalog_source(actor_ws, monkeypatch, 'AST-own-copy', content='Same bytes', identity='AST-other-owner')
    with ws['repo'].connection(read_only=True) as con:
        context = authorize_saved_work(actor, ws['scope'], action='write', connection=con)
        assert _verified_evidence(con, copy['evidence_id'], context, actor)['asset_id'] == copy['source_id']
    calls = []
    original = library._catalog_candidate
    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(library, '_catalog_candidate', observed)
    for operation in (library.catalog_binding_resource, library.bind_legacy_catalog_asset):
        with pytest.raises(PermissionError, match='LIBRARY_MIGRATION_AUTHORITY_REQUIRED'):
            operation('AST-other-owner', copy['evidence_id'], actor=actor, scope=ws['scope'])
    assert calls == []


def test_semantic_combined_search_reverifies_original_artifact_after_library_scan(workspace, monkeypatch):
    import shared_artifacts
    from subject_registry import add_subject
    ws = workspace
    subject, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Original', 'name_zh': '原件'})
    focused = {**ws, 'scope': {**ws['scope'], 'global_scope': False, 'subject_id': subject['subject_id']}}
    _, _, source = _source(focused)
    _catalog_source(ws, monkeypatch, 'AST-stage-two')
    memory = _memory(ws)
    assert source['source_id'] in {row['source_id'] for row in memory.search_assets('Original source line')}
    with ws['repo'].connection(read_only=True) as con:
        path = con.execute('SELECT relative_path FROM lumenis_shared_artifacts WHERE source_execution_id=?', (source['source_id'],)).fetchone()[0]
    original = memory._research_assets
    def delete_original(connection, **selectors):
        result = original(connection, **selectors)
        (shared_artifacts.artifact_root() / path).unlink()
        return result
    monkeypatch.setattr(memory, '_research_assets', delete_original)
    with pytest.raises(PermissionError, match='MEMORY_SOURCE_CHANGED'):
        memory.search_assets('Original source')


@pytest.mark.parametrize('audience', ['other_subject', 'other_actor'])
def test_orphaned_foreign_catalog_source_does_not_leak_missing_counts(client, monkeypatch, audience):
    import intelligence_library_api as library
    from subject_registry import add_subject
    from tests.test_bmp09_request_binding import accounts
    http, ws = client
    first, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Mine', 'name_zh': '甲'})
    second, _ = add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Other', 'name_zh': '乙'})
    scope = {**ws['scope'], 'global_scope': False, 'subject_id': second['subject_id']}
    source, _ = _catalog_source(ws, monkeypatch, 'AST-foreign-missing', scope=scope)
    monkeypatch.setattr(library, '_get_db', lambda: ws['repo'].connect(read_only=True, wal=False))
    ws['app'].register_blueprint(library.intelligence_library_bp)
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM app_evidence_records WHERE id=?', (source['evidence_id'],))
    if audience == 'other_subject':
        headers = {**HEADERS, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': first['subject_id']}
    else:
        one, _ = accounts(ws)
        headers = {**HEADERS, **one}
    result = http.get('/api/intelligence/library', headers=headers).get_json()
    assert result['data'] == [] and result['state'] == 'empty'
    assert result['unavailable_count'] == 0 and result['unavailable_reasons'] == {}


@pytest.mark.parametrize('withdrawal', ['transport', 'commit', 'human_approval', 'claimed_principal'])
def test_catalog_migration_owner_admission_is_current_before_any_catalog_read(client, monkeypatch, withdrawal):
    import intelligence_library_api as library
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-owner-check', bind=False)
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-owner-check', source['evidence_id'], **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
    if withdrawal == 'transport':
        ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    elif withdrawal == 'claimed_principal':
        args['actor'] = {'principal_kind': 'local_workspace', 'principal_ref': 'workspace:local', 'role': 'owner'}
    else:
        ws['gate'].revoke_permission(permission.PermissionLevel.COMMIT if withdrawal == 'commit' else permission.PermissionLevel.HUMAN_APPROVAL)
    def unexpected_catalog_read(*args, **kwargs):
        pytest.fail('catalog metadata read before migration authority')
    monkeypatch.setattr(library, '_catalog_candidate', unexpected_catalog_read)
    for operation in (library.catalog_binding_resource, library.bind_legacy_catalog_asset):
        with pytest.raises(PermissionError, match='LIBRARY_MIGRATION_AUTHORITY_REQUIRED'):
            operation('AST-owner-check', source['evidence_id'], **args)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?', (library._BINDING_FEATURE,)).fetchone()[0] == 0


@pytest.mark.parametrize('phase', ['writer_transaction', 'commit_lease'])
def test_catalog_migration_rechecks_controlled_owner_in_transaction_and_lease(client, monkeypatch, phase):
    import intelligence_library_api as library
    http, ws = client
    source, _ = _catalog_source(ws, monkeypatch, 'AST-owner-race', bind=False)
    args = {'actor': ws['actor'], 'scope': ws['scope']}
    preview = library.catalog_binding_resource('AST-owner-race', source['evidence_id'], **args)
    ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=preview['resource'], granted_by=preview['caller'])
    original = library._prepare_catalog_binding
    calls = 0
    def withdraw_before_check(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == (2 if phase == 'writer_transaction' else 3):
            ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
        return original(*args, **kwargs)
    monkeypatch.setattr(library, '_prepare_catalog_binding', withdraw_before_check)
    with pytest.raises(PermissionError, match='LIBRARY_MIGRATION_AUTHORITY_REQUIRED'):
        library.bind_legacy_catalog_asset('AST-owner-race', source['evidence_id'], **args)
    assert calls == (2 if phase == 'writer_transaction' else 3)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?', (library._BINDING_FEATURE,)).fetchone()[0] == 0
