"""Disposable source/comment/Evidence transactions; no live platform acceptance."""
import copy
import json
import sqlite3
from pathlib import Path

import pytest

from tests.test_collector_transaction_truth import (
    admit_registered_subject_for_isolated_collector,
    collector_case,
    REGISTERED_NAME,
)


@pytest.fixture
def comments_case(collector_case, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = collector_case
    admit_registered_subject_for_isolated_collector(case)
    entry = case['surface']
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(Path(case['db_path']).parent / 'comment-artifacts'))
    import shared_artifacts
    shared_artifacts.ensure_artifact_table()
    source_id = 'f' * 24
    source_url = 'https://www.rednote.com/explore/' + source_id
    calls = []
    class DeclaredPageFixture:
        def detail(self, target, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, 'xhs', items=[{
                'note_id': source_id, 'title': REGISTERED_NAME + ' comment parent fixture',
                'content': REGISTERED_NAME + ' original permitted body', 'url': source_url,
                'source_platform': 'xhs', 'liked_count': 0, 'comment_count': None,
                'detail_fetched': True, 'detail_identity_verified': True}], raw_count=1,
                metadata={'source': 'www.rednote.com', 'source_platform': 'xhs'})
        def comments(self, target, **kwargs):
            calls.append(copy.deepcopy(kwargs))
            cursor = kwargs.get('cursor')
            values = ([{'platform_comment_id': 'root-native', 'content': 'First source statement',
                        'likes': None, 'parent_content_id': source_id},
                       {'platform_comment_id': 'inline-reply', 'parent_comment_id': 'root-native',
                        'content': 'Already returned reply', 'likes': 0, 'parent_content_id': source_id}]
                      if cursor is None else
                      [{'platform_comment_id': 'later-native', 'content': 'Second page source statement',
                        'likes': 0, 'parent_content_id': source_id}])
            return CollectionResult(CollectionStatus.SUCCESS, 'xhs', comments=values, raw_count=len(values),
                metadata={'source': 'www.rednote.com', 'pagination': {'request_cursor': cursor,
                    'next_cursor': {'page': 2} if cursor is None else None,
                    'exhausted': cursor is not None, 'page_complete': True,
                    'replies_complete': True, 'coverage_scope': 'EXPLICIT_ENGINEERING_PAGE_FIXTURE'}})
    adapter = DeclaredPageFixture()
    monkeypatch.setattr(entry, '_get_runtime_adapter', lambda *a: adapter)
    monkeypatch.setattr(entry, '_adapter_health', lambda *a, **k: {'status': 'SUCCESS', 'can_attempt': True})
    with case['client'].application.test_request_context('/', headers=case['focus_headers'],
            environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = case['permission'].resolve_local_workspace_principal(module='collector', action='write')
        request = dict(actor=actor, scope=case['scope'])
        blocked = entry.collect_detail('xhs', source_id, **request)
        case['gate'].grant_approval('data_import', resource=blocked['approval_resource'], granted_by='isolated parent fixture')
        monkeypatch.setitem(entry._last_action, 'xiaohongshu', 0.0)
        assert entry.collect_detail('xhs', source_id, **request)['ok']
        arguments = {**request, 'request_id': 'comment-page-fixture-01'}
        blocked = entry.collect_comments(source_id, **arguments)
        assert blocked['status'] == 'APPROVAL_REQUIRED' and not calls
        case['gate'].grant_approval('data_import', resource=blocked['approval_resource'], granted_by='isolated comments fixture')
        case.update(entry=entry, adapter=adapter, actor=actor, arguments=arguments,
                    source_id=source_id, calls=calls)
        yield case


def collect(case, monkeypatch, **extra):
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    return case['entry'].collect_comments(case['source_id'], **case['arguments'], **extra)


def test_real_comment_projection_paging_null_reply_and_signed_replay(comments_case, monkeypatch):
    case = comments_case
    first = collect(case, monkeypatch)
    assert first['status'] == 'COMMENTS_PARTIAL' and first['coverage_state'] == 'PARTIAL'
    assert first['persistence']['inserted'] == 2
    assert first['comments'][0]['likes'] is None
    assert first['comments'][1]['parent_comment_id'] == 'root-native'
    replay = collect(case, monkeypatch)
    assert replay['commit_reconciled'] and not replay['network_attempted'] and len(case['calls']) == 1
    second = collect(case, monkeypatch, continuation=first['continuation'])
    assert second['status'] == 'SUCCESS' and second['continuation'] is None and len(case['calls']) == 2
    assert case['calls'][1]['cursor'] == {'page': 2}
    duplicate = collect(case, monkeypatch, continuation=first['continuation'])
    assert duplicate['commit_reconciled'] and len(case['calls']) == 2
    terminal = collect(case, monkeypatch, continuation={'page_ref': second['page_ref']})
    assert terminal['cached'] and len(case['calls']) == 2
    reader = case['entry'].read_collected_comments
    immutable = reader(case['source_id'], actor=case['actor'], scope=case['scope'], page_ref=first['page_ref'])
    assert immutable['comments'] == first['comments'] and immutable['immutable']
    seen, before = [], None
    while True:
        page = reader(case['source_id'], actor=case['actor'], scope=case['scope'], limit=1, before=before)
        seen.extend(page['comments'])
        before = page['next_cursor']
        if before is None:
            break
    assert {item['platform_comment_id'] for item in seen} == {'root-native', 'inline-reply', 'later-native'}
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM note_comments').fetchone()[0] == 3
        assert connection.execute('SELECT likes FROM note_comments WHERE content=?', ('First source statement',)).fetchone()[0] is None
        assert connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_NATIVE_COMMENTS'").fetchone()[0] == 2


@pytest.mark.parametrize('fault', ['cursor_loop', 'parent_mismatch', 'unidentified', 'cursor_ignored'])
def test_comment_native_identity_and_cursor_failures_are_honest(comments_case, monkeypatch, fault):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = comments_case
    original = case['adapter'].comments
    def bad(target, **kwargs):
        result = original(target, **kwargs)
        if fault == 'cursor_loop':
            result.metadata['pagination']['next_cursor'] = kwargs.get('cursor')
            result.metadata['pagination']['exhausted'] = False
        elif fault == 'parent_mismatch':
            result.comments[0]['parent_content_id'] = 'foreign-note'
        elif fault == 'unidentified':
            result.comments[0]['platform_comment_id'] = None
        elif kwargs.get('cursor'):
            result.metadata['pagination']['request_cursor'] = None
        return result
    monkeypatch.setattr(case['adapter'], 'comments', bad)
    if fault == 'parent_mismatch':
        with pytest.raises(ValueError, match='PARENT_IDENTITY_MISMATCH'):
            collect(case, monkeypatch)
        return
    first = collect(case, monkeypatch)
    if fault == 'unidentified':
        assert first['persistence']['unidentified'] == 1
        assert first['comments'][0]['identity_state'] == 'NATIVE_ID_NOT_OBSERVED'
    elif fault == 'cursor_loop':
        # No source cursor is invented to escape a non-progressing provider.
        assert first['continuation'] is None and first['coverage_state'] == 'PARTIAL'
    else:
        with pytest.raises(ValueError, match='CURSOR_NOT_CONSUMED'):
            collect(case, monkeypatch, continuation=first['continuation'])


def test_comment_projection_helper_joins_caller_transaction_and_preserves_rollback(comments_case):
    import database
    case = comments_case
    connection = sqlite3.connect(case['db_path'])
    connection.execute('BEGIN IMMEDIATE')
    result = database.upsert_note_comments(case['source_id'], [{'comment_id': 'isolated-comment-key',
        'content': 'transaction rollback', 'likes': None, 'parent_comment_id': 'native-parent'}], connection=connection)
    assert result['inserted'] == 1
    connection.rollback()
    assert connection.execute('SELECT COUNT(*) FROM note_comments').fetchone()[0] == 0
    connection.close()


def test_comment_source_revision_keeps_historical_page_but_fences_continuation(comments_case, monkeypatch):
    case = comments_case
    first = collect(case, monkeypatch)
    original = case['adapter'].detail
    def revised(target, **kwargs):
        result = original(target, **kwargs)
        result.items[0]['content'] += ' Explicit source revision.'
        return result
    monkeypatch.setattr(case['adapter'], 'detail', revised)
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    assert case['entry'].collect_detail('xhs', case['source_id'], actor=case['actor'],
        scope=case['scope'], operation_key='source-revision-explicit')['ok']
    reader = case['entry'].read_collected_comments
    historical = reader(case['source_id'], actor=case['actor'], scope=case['scope'], page_ref=first['page_ref'])
    assert historical['comments'] == first['comments']
    assert historical['source_version_state'] == 'RECORDED_SOURCE_VERSION'
    latest = reader(case['source_id'], actor=case['actor'], scope=case['scope'])
    assert {item['source_version_state'] for item in latest['comments']} == {'RECORDED_SOURCE_VERSION'}
    with pytest.raises(PermissionError, match='COMMENT_PAGE_CONTEXT_CHANGED'):
        collect(case, monkeypatch, continuation=first['continuation'])
    assert len(case['calls']) == 1


def test_comment_atomic_receipt_failure_rolls_back_observations_and_page(comments_case, monkeypatch):
    case = comments_case
    original = case['entry']._task_commit_receipt
    def fail_on_write(connection, binding, result=None):
        if result is not None:
            raise RuntimeError('isolated receipt write fault')
        return original(connection, binding)
    monkeypatch.setattr(case['entry'], '_task_commit_receipt', fail_on_write)
    with pytest.raises(RuntimeError, match='isolated receipt write fault'):
        collect(case, monkeypatch)
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM note_comments').fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_NATIVE_COMMENTS'").fetchone()[0] == 0
    import shared_artifacts
    assert not list(shared_artifacts.artifact_root().glob('ART-*.json'))


def test_failed_comment_page_retains_originals_and_retries_same_native_cursor(comments_case, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionStatus
    case = comments_case
    original = case['adapter'].comments
    attempt = {'number': 0}
    def interrupted(target, **kwargs):
        result = original(target, **kwargs)
        attempt['number'] += 1
        if attempt['number'] == 1:
            result.status = CollectionStatus.COLLECT_ERROR
            result.metadata['pagination']['page_complete'] = False
        return result
    monkeypatch.setattr(case['adapter'], 'comments', interrupted)
    first = collect(case, monkeypatch)
    assert first['status'] == 'COLLECT_ERROR' and first['recovery_required']
    assert first['persistence']['inserted'] == 2 and first['continuation']
    resumed = collect(case, monkeypatch, continuation=first['continuation'])
    assert resumed['status'] == 'COMMENTS_PARTIAL' and case['calls'][1].get('cursor') is None
    assert resumed['persistence']['updated'] == 2
    final = collect(case, monkeypatch, continuation=resumed['continuation'])
    assert final['status'] == 'SUCCESS' and len(case['calls']) == 3
    historical = case['entry'].read_collected_comments(case['source_id'], actor=case['actor'],
        scope=case['scope'], page_ref=first['page_ref'])
    assert historical['comments'] == first['comments']


def test_comment_page_signature_and_current_actor_are_rechecked(comments_case, monkeypatch):
    case = comments_case
    first = collect(case, monkeypatch)
    reader = case['entry'].read_collected_comments
    with pytest.raises(PermissionError, match='COMMENT_SOURCE_NOT_AUTHORIZED'):
        reader(case['source_id'], actor={'id': -999}, scope=case['scope'], page_ref=first['page_ref'])
    with sqlite3.connect(case['db_path']) as connection:
        row = connection.execute('SELECT outputs_json FROM app_evidence_records WHERE id=?',
                                 (first['evidence_ref'],)).fetchone()
        outputs = json.loads(row[0])
        outputs['result']['comments'][0]['content'] = 'Tampered source body'
        connection.execute('UPDATE app_evidence_records SET outputs_json=? WHERE id=?',
                           (json.dumps(outputs), first['evidence_ref']))
    with pytest.raises(PermissionError, match='COMMENT_PAGE_RECEIPT_UNVERIFIED'):
        reader(case['source_id'], actor=case['actor'], scope=case['scope'], page_ref=first['page_ref'])
    with pytest.raises(PermissionError, match='COMMENT_OBSERVATION_UNVERIFIED'):
        reader(case['source_id'], actor=case['actor'], scope=case['scope'])


@pytest.mark.parametrize('successful', [False, True])
def test_failed_unobserved_count_is_null_and_observed_empty_page_is_zero(comments_case, monkeypatch, successful):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = comments_case
    result = CollectionResult(CollectionStatus.NO_NEW_DATA if successful else CollectionStatus.PROVIDER_UNAVAILABLE,
        'xhs', comments=[], metadata={'pagination': {'exhausted': True if successful else None,
            'page_complete': successful, 'replies_complete': True if successful else None}})
    monkeypatch.setattr(case['adapter'], 'comments', lambda *args, **kwargs: result)
    page = collect(case, monkeypatch)
    assert page['comments'] == []
    assert page['observed_count'] == (0 if successful else None)
    assert page['native_identity_count'] == (0 if successful else None)
    assert page['status'] == ('SUCCESS' if successful else 'PROVIDER_UNAVAILABLE')


def test_top_level_comment_scope_does_not_require_unrequested_reply_totals(comments_case, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = comments_case
    result = CollectionResult(CollectionStatus.SUCCESS, 'xhs', comments=[{
        'platform_comment_id': 'top-level-only', 'content': 'Observed top level statement',
        'parent_content_id': case['source_id']}], metadata={'pagination': {
            'request_cursor': None, 'next_cursor': None, 'exhausted': True,
            'page_complete': True, 'coverage_scope': 'EXPLICIT_TOP_LEVEL_FIXTURE'}})
    monkeypatch.setattr(case['adapter'], 'comments', lambda *args, **kwargs: result)
    page = collect(case, monkeypatch)
    assert page['status'] == 'SUCCESS'
    assert page['coverage_state'] == 'COMPLETE_FOR_DECLARED_SCOPE'
    assert page['requested_reply_scope'] == 'TOP_LEVEL_ONLY'
    assert page['reply_coverage_state'] == 'NOT_REQUESTED'
    assert page['replies_complete'] is None


def test_explicit_incomplete_provider_page_cannot_be_marked_success_when_exhausted(comments_case, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = comments_case
    result = CollectionResult(CollectionStatus.SUCCESS, 'xhs', comments=[{
        'platform_comment_id': 'incomplete-provider-page', 'content': 'Observed partial page statement',
        'parent_content_id': case['source_id']}], metadata={'pagination': {
            'request_cursor': None, 'next_cursor': None, 'exhausted': True,
            'page_complete': False, 'coverage_scope': 'EXPLICIT_INCOMPLETE_PAGE_FIXTURE'}})
    monkeypatch.setattr(case['adapter'], 'comments', lambda *args, **kwargs: result)
    page = collect(case, monkeypatch)
    assert page['status'] == 'COMMENTS_PARTIAL'
    assert page['coverage_state'] == 'PARTIAL'
    assert page['pagination_exhausted'] is True
    assert page['recovery_required'] is True
    assert page['partial_reason'] == 'PAGE_COMPLETION_NOT_ESTABLISHED'
    assert page['continuation'] == {'page_ref': page['page_ref']}


def test_requested_reply_scope_without_provider_completion_stays_unknown(comments_case, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = comments_case
    case['arguments']['include_replies'] = True
    blocked = case['entry'].collect_comments(case['source_id'], **case['arguments'])
    assert blocked['status'] == 'APPROVAL_REQUIRED'
    case['gate'].grant_approval('data_import', resource=blocked['approval_resource'],
                                granted_by='isolated reply-scope fixture')
    result = CollectionResult(CollectionStatus.SUCCESS, 'xhs', comments=[{
        'platform_comment_id': 'reply-scope-unknown', 'content': 'Observed statement',
        'parent_content_id': case['source_id']}], metadata={'pagination': {
            'request_cursor': None, 'next_cursor': None, 'exhausted': True,
            'page_complete': True, 'coverage_scope': 'EXPLICIT_UNKNOWN_REPLY_FIXTURE'}})
    monkeypatch.setattr(case['adapter'], 'comments', lambda *args, **kwargs: result)
    page = collect(case, monkeypatch)
    assert page['status'] == 'COMMENTS_PARTIAL'
    assert page['coverage_state'] == 'PARTIAL'
    assert page['requested_reply_scope'] == 'INCLUDE_REPLIES'
    assert page['reply_coverage_state'] == 'UNKNOWN'
    assert page['replies_complete'] is None
    assert page['partial_reason'] == 'REPLY_COVERAGE_NOT_ESTABLISHED'


def test_comment_original_artifact_same_page_cold_read_and_distinct_page_identity(comments_case, monkeypatch):
    case = comments_case
    first = collect(case, monkeypatch)
    assert first['original_source']['status'] == 'PRESERVED'
    entry = case['entry']
    original = entry.read_comment_page_original(first['page_ref'], actor=case['actor'], scope=case['scope'])
    assert original['source_id'] == 'comment-page:' + str(first['evidence_ref'])
    assert original['parent_source_id'] == case['source_id']
    assert original['source_version'] == 'collector-native-comments/2'
    assert original['document']['observations'] == first['comments']
    assert original['document']['rights']['allowed_uses'] == []
    assert original['document']['body'] == 'First source statement\n\nAlready returned reply'
    for segment in original['document']['body_segments']:
        assert original['document']['body'][segment['start']:segment['end']] == first['comments'][segment['comment_index']]['content']
    second = collect(case, monkeypatch, continuation=first['continuation'])
    later = entry.read_comment_page_original(second['page_ref'], actor=case['actor'], scope=case['scope'])
    assert later['source_id'] != original['source_id'] and later['sha256'] != original['sha256']
    reread = entry.read_comment_page_original(first['page_ref'], actor=case['actor'], scope=case['scope'])
    assert reread['raw'] == original['raw'] and reread['document'] == original['document']
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_NATIVE_COMMENTS'").fetchone()[0] == 2


@pytest.mark.parametrize('fault', ['bytes', 'registry_binding', 'parent_withdrawal'])
def test_comment_original_rejects_changed_bytes_binding_and_current_parent_withdrawal(comments_case, monkeypatch, fault):
    import shared_artifacts
    case = comments_case
    page = collect(case, monkeypatch)
    original = case['entry'].read_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])
    if fault == 'bytes':
        path = shared_artifacts.artifact_root() / original['source_artifact']['relative_path']
        path.write_bytes(original['raw'] + b' ')
    else:
        with sqlite3.connect(case['db_path']) as connection:
            if fault == 'registry_binding':
                connection.execute('UPDATE lumenis_shared_artifacts SET source_execution_id=? WHERE artifact_id=?',
                    ('comment-page:foreign', original['source_artifact']['artifact_id']))
            else:
                connection.execute("UPDATE canonical_data SET scope_status='UNASSIGNED' WHERE source_id=?", (case['source_id'],))
    with pytest.raises((ValueError, LookupError, PermissionError)):
        case['entry'].read_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])


def test_noncritical_comment_artifact_failure_preserves_primary_observations(comments_case, monkeypatch):
    from lumenis.shared.reporting import saved_work
    case = comments_case
    original_stage = saved_work._stage_bytes
    def fail(*args, **kwargs):
        raise OSError('isolated original storage fault')
    monkeypatch.setattr(saved_work, '_stage_bytes', fail)
    page = collect(case, monkeypatch)
    assert page['ok'] and page['persistence']['inserted'] == 2
    assert page['original_source']['status'] == 'UNAVAILABLE'
    assert case['entry'].read_collected_comments(case['source_id'], actor=case['actor'], scope=case['scope'],
        page_ref=page['page_ref'])['comments'] == page['comments']
    with pytest.raises(LookupError, match='COMMENT_ORIGINAL_ARTIFACT_UNAVAILABLE'):
        case['entry'].read_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])
    with sqlite3.connect(case['db_path']) as connection:
        before = connection.execute('SELECT inputs_json,outputs_json,collection_metadata FROM app_evidence_records WHERE id=?',
                                    (page['evidence_ref'],)).fetchone()
    monkeypatch.setattr(saved_work, '_stage_bytes', original_stage)
    recovered = case['entry'].recover_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])
    assert not recovered['network_attempted'] and not recovered['evidence_rewritten']
    assert recovered['source_id'] == 'comment-page:' + str(page['evidence_ref'])
    assert recovered['document']['observations'] == page['comments'] and len(case['calls']) == 1
    repeated = case['entry'].recover_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])
    assert repeated['replayed'] and repeated['source_artifact'] == recovered['source_artifact']
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT inputs_json,outputs_json,collection_metadata FROM app_evidence_records WHERE id=?',
                                  (page['evidence_ref'],)).fetchone() == before
        assert connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_NATIVE_COMMENTS'").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts WHERE kind='collected_source'").fetchone()[0] == 1
