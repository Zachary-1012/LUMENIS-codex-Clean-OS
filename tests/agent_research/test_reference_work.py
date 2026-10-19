"""Isolated real SavedWork owner lifecycle, synthetic references only."""
import json
import pytest
from flask import Flask
from lumenis.shared.database import DatabaseRepository
from lumenis.system.security import permission
from agent_research.reference_assets import match_rule_references
from agent_research.reference_work import adopt_reference_asset, revise_reference_work, read_reference_work, list_reference_work


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('ZBC_DB_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'artifacts'))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'test': 'isolated-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'test')
    monkeypatch.setattr(permission, '_TESTING_BYPASS_ENABLED', False)
    import shared_artifacts
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work
    from lumenis.importer import documents
    repo = DatabaseRepository(str(tmp_path / 'test.sqlite3'))
    for module in (shared_artifacts, store, saved_work, documents):
        monkeypatch.setattr(module, 'get_repository', lambda: repo)
    shared_artifacts.ensure_artifact_table()
    store.init_evidence_store(str(tmp_path / 'test.sqlite3'))
    with repo.transaction() as con:
        store.ensure_evidence_schema(con)
    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission, 'get_permission_gate', lambda: gate)
    app = Flask(__name__)
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = permission.resolve_local_workspace_principal(module='reports', action='write')
        yield {'actor': actor, 'scope': {'scope_kind': 'shared_workspace', 'version': 1}, 'repo': repo, 'gate': gate, 'app': app}


def args(workspace):
    return {k: workspace[k] for k in ('actor', 'scope')}


def test_scenario_adopt_edit_reopen_and_stale_reference(workspace):
    a = args(workspace)
    first = adopt_reference_asset('scenarios:indie_game_sea', request_id='scenario-first',
                                  edits={'inputs': {'budget': 250, 'budget_currency': 'USD'}, 'goal': 'Test 20 interviews'}, **a)
    ref = first['reference']
    read = read_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], **a)
    body = read['document']['payload']['research_reference']
    assert body['current']['inputs']['budget'] == 250
    assert body['original']['data']['inputs']['budget'] == 0
    assert body['current']['goal'] == 'Test 20 interviews'
    assert body['classification'] == 'synthetic_sample' and body['license'] == 'UNKNOWN'
    second = revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='scenario-second', edits={'work': {'title': 'Revised'}}, **a)
    assert second['reference']['version'] == 2
    with pytest.raises(ValueError, match='REFERENCE_NEEDS_REVISION'):
        read_reference_work(ref['artifact_id'], **a)
    historical = read_reference_work(ref['artifact_id'], require_current=False, **a)
    assert historical['current_status'] == 'needs_revision'
    assert historical['document']['payload']['research_reference']['current']['work']['title'] != 'Revised'


def test_reference_withdraw_restore_preserves_old_bytes(workspace):
    a = args(workspace)
    first = adopt_reference_asset('markets:US', request_id='market-first', **a)
    ref = first['reference']
    withdrawn = revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='market-withdraw', operation='withdraw', **a)
    with pytest.raises(ValueError, match='REFERENCE_WITHDRAWN'):
        read_reference_work(ref['artifact_id'], **a)
    wr = withdrawn['reference']
    restored = revise_reference_work(wr['artifact_id'], expected_sha256=wr['sha256'], request_id='market-restore', operation='restore', **a)
    assert restored['reference']['version'] == 3
    assert read_reference_work(restored['reference']['artifact_id'], **a)['current_status'] == 'active'
    with pytest.raises(ValueError, match='REFERENCE_NEEDS_REVISION'):
        read_reference_work(ref['artifact_id'], **a)


def test_wrong_hash_scope_actor_and_stale_cas_rejected(workspace):
    a = args(workspace)
    first = adopt_reference_asset('markets:CN', request_id='negative-first', **a)
    ref = first['reference']
    with pytest.raises(ValueError, match='REFERENCE_HASH_MISMATCH'):
        read_reference_work(ref['artifact_id'], expected_sha256='0' * 64, **a)
    with pytest.raises((ValueError, PermissionError)):
        read_reference_work(ref['artifact_id'], actor={'user_id': 'forged'}, scope=a['scope'])
    with pytest.raises((ValueError, PermissionError)):
        read_reference_work(ref['artifact_id'], actor=a['actor'], scope={'domain_id': 'cth', 'subject_id': None, 'brand_focus_id': None, 'global_scope': True})
    second = revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='negative-second', edits={'data': {'name': 'Declared correction'}}, **a)
    with pytest.raises(ValueError, match='REFERENCE_NEEDS_REVISION'):
        revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='negative-stale', edits={'data': {'name': 'Stale'}}, **a)
    assert read_reference_work(second['reference']['artifact_id'], **a)['document']['version'] == 2


def test_reference_retry_and_pagination(workspace):
    a = args(workspace)
    one = adopt_reference_asset('markets:CN', request_id='retry-reference', **a)
    again = adopt_reference_asset('markets:CN', request_id='retry-reference', **a)
    assert one['reference'] == again['reference']
    adopt_reference_asset('markets:US', request_id='pagination-second', **a)
    first = list_reference_work(limit=1, **a)
    assert first['has_more']
    second = list_reference_work(limit=1, cursor=first['next_cursor'], **a)
    assert first['items'][0]['reference'] != second['items'][0]['reference']


def test_rule_match_is_structured_uncertain_and_date_bound():
    us = match_rule_references(content='广告 disclosure 付费推广', regions=['north_america'])
    assert all(r['reference']['data'].get('country') in ('US', None, '') or r['reference']['data'].get('jurisdiction') == 'Global' for r in us['items'])
    cn = match_rule_references(content='广告 推广', regions=['CN'], as_of='2000-01-01')
    rule = next(r for r in cn['items'] if r['reference']['code'] == 'CN-AD-DISC-001')
    assert rule['date_status'] == 'BEFORE_DECLARED_START'
    assert rule['current_legal_validity'] == 'UNKNOWN' and rule['required_action'] is None
    unknown = match_rule_references(content='广告')
    assert all(r['date_status'] == r['region_status'] == 'UNKNOWN' for r in unknown['items'])
    assert match_rule_references(content='no-matching-term')['legal_clearance'] is None
    with pytest.raises(ValueError):
        match_rule_references(content='x', regions=['wrong'])


def test_revision_retry_and_scope_permission_revocation(workspace):
    a = args(workspace)
    first = adopt_reference_asset('markets:JP', request_id='replay-original', **a)
    ref = first['reference']
    params = dict(expected_sha256=ref['sha256'], request_id='replay-updated', edits={'data': {'name': 'Declared label'}}, **a)
    revised = revise_reference_work(ref['artifact_id'], **params)
    replay = revise_reference_work(ref['artifact_id'], **params)
    assert replay['reference'] == revised['reference'] and replay['replayed'] is True
    workspace['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    with pytest.raises((ValueError, PermissionError)):
        adopt_reference_asset('markets:KR', request_id='denied-adopt', **a)


def test_signed_library_adoption_discovery_and_revision_invalidation(workspace):
    from intelligence_library_api import adopt_reference_library_asset, read_reference_library_source, discover_reference_library_sources
    a = args(workspace)
    saved = adopt_reference_library_asset('rules:CN-PIPL-001', request_id='library-adopt-one', **a)
    assert saved['knowledge_status'] == 'REFERENCE' and saved['evidence_level'] == 'RAW'
    assert saved['rights'] == saved['license'] == 'UNKNOWN'
    assert saved['fact_verification'] == 'NOT_VERIFIED' and saved['canonical'] is False
    assert saved['source_provenance']['original_date'] == '2021-11-01'
    assert read_reference_library_source(saved['binding_evidence_id'], **a)['reference'] == saved['reference']
    json.dumps(saved)  # HTTP response contains no raw bytes or private filesystem paths.
    found = discover_reference_library_sources(query='CN-PIPL', **a)
    assert found['verification_complete'] and len(found['items']) == 1
    ref = saved['reference']
    changed = revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'],
                                   request_id='library-revision', edits={'data': {'description': 'User-declared correction'}}, **a)
    with pytest.raises(ValueError, match='REFERENCE_NEEDS_REVISION'):
        read_reference_library_source(saved['binding_evidence_id'], **a)
    after = discover_reference_library_sources(query='CN-PIPL', **a)
    assert len(after['items']) == 1 and after['items'][0]['reference'] == changed['reference']
    ref2 = changed['reference']
    revise_reference_work(ref2['artifact_id'], expected_sha256=ref2['sha256'],
                          request_id='library-withdrawal', operation='withdraw', **a)
    assert discover_reference_library_sources(query='CN-PIPL', **a)['items'] == []


def test_library_signature_tampering_and_foreign_actor_are_rejected(workspace):
    from intelligence_library_api import adopt_reference_library_asset, read_reference_library_source, discover_reference_library_sources
    a = args(workspace)
    saved = adopt_reference_library_asset('platforms:github', request_id='library-tamper', **a)
    with pytest.raises((ValueError, PermissionError)):
        read_reference_library_source(saved['binding_evidence_id'], actor={'user_id': 'forged'}, scope=a['scope'])
    with workspace['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET collection_metadata='{}' WHERE id=?", (saved['binding_evidence_id'],))
    with pytest.raises(ValueError, match='REFERENCE_BINDING_UNAVAILABLE'):
        read_reference_library_source(saved['binding_evidence_id'], **a)
    with pytest.raises(ValueError, match='REFERENCE_BINDING_UNAVAILABLE'):
        read_reference_work(saved['reference']['artifact_id'], **a)
    found = discover_reference_library_sources(**a)
    assert found['items'] == [] and found['verification_complete'] is False


def test_library_pagination_continues_across_historical_versions(workspace):
    from intelligence_library_api import adopt_reference_library_asset, discover_reference_library_sources
    a = args(workspace)
    one = adopt_reference_library_asset('markets:EU', request_id='page-library-one', **a)
    ref = one['reference']
    revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='page-library-revision', edits={'data': {'name': 'User label'}}, **a)
    adopt_reference_library_asset('markets:GB', request_id='page-library-two', **a)
    cursor, items, visited = None, [], set()
    while True:
        page = discover_reference_library_sources(limit=1, cursor=cursor, **a)
        items.extend(page['items'])
        if not page['has_more']:
            break
        cursor = page['next_cursor']
        assert cursor and cursor not in visited
        visited.add(cursor)
    assert len(items) == 2 and {item['asset_id'] for item in items} == {'markets:EU', 'markets:GB'}


def test_reference_edit_cannot_grant_license_or_change_original_provenance(workspace):
    a = args(workspace)
    for edits in ({'license': 'CC0'}, {'data': {'rights': 'owner-approved'}}, {'data': {'effective_date': '2099-01-01'}}):
        with pytest.raises(ValueError, match='REFERENCE_'):
            adopt_reference_asset('markets:US', request_id='forbidden-edit', edits=edits, **a)


def test_latest_version_is_not_truncated_at_one_hundred(workspace):
    a = args(workspace)
    first = adopt_reference_asset('markets:KR', request_id='many-versions-first', **a)
    latest = first
    for version in range(2, 103):
        ref = latest['reference']
        latest = revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'],
                                       request_id=f'many-versions-{version:04d}', edits={'data': {'name': f'Declared revision {version}'}}, **a)
    assert latest['reference']['version'] == 102
    historical = read_reference_work(first['reference']['artifact_id'], require_current=False, **a)
    assert historical['current_reference'] == latest['reference']
    with pytest.raises(ValueError, match='REFERENCE_NEEDS_REVISION'):
        read_reference_work(first['reference']['artifact_id'], **a)


def test_concurrent_update_cas_and_binding_failure_are_atomic(workspace, monkeypatch):
    from lumenis.shared.reporting import saved_work
    import intelligence_library_api as library
    a = args(workspace)
    first = adopt_reference_asset('markets:SEA', request_id='atomic-first', **a)
    ref = first['reference']
    original_save = saved_work.save_work
    injected = []
    def race(**kwargs):
        if kwargs['request_id'] == 'atomic-stale' and not injected:
            injected.append(True)
            revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='atomic-winner',
                                  edits={'data': {'name': 'Winner'}}, **a)
        return original_save(**kwargs)
    monkeypatch.setattr(saved_work, 'save_work', race)
    with pytest.raises(ValueError, match='REFERENCE_NEEDS_REVISION'):
        revise_reference_work(ref['artifact_id'], expected_sha256=ref['sha256'], request_id='atomic-stale',
                              edits={'data': {'name': 'Loser'}}, **a)
    current = read_reference_work(ref['artifact_id'], require_current=False, **a)['current_reference']
    assert current['version'] == 2
    def failed_binding(*args, **kwargs):
        raise RuntimeError('injected-binding-failure')
    monkeypatch.setattr(library, '_write_reference_work_binding', failed_binding)
    with pytest.raises(RuntimeError, match='injected-binding-failure'):
        revise_reference_work(current['artifact_id'], expected_sha256=current['sha256'], request_id='atomic-binding-failure',
                              edits={'data': {'name': 'Never committed'}}, **a)
    assert read_reference_work(current['artifact_id'], **a)['current_reference'] == current
    with workspace['repo'].connection(read_only=True) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='INTELLIGENCE_REFERENCE_WORK_BINDING'").fetchone()[0] == 2


@pytest.mark.parametrize('region', [None, {}, [], 4])
def test_invalid_rule_region_element_is_a_validation_error(region):
    with pytest.raises(ValueError, match='UNKNOWN_REFERENCE_REGION'):
        match_rule_references(content='广告', regions=[region])
