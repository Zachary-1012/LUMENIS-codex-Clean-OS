from copy import deepcopy

import pytest

from lumenis.system.collector import acquisition_plan as planner
from lumenis.system.collector.adapters import secondary_collection as entry


@pytest.fixture(autouse=True)
def isolated_business_task_store(tmp_path, monkeypatch):
    from lumenis.system.collector.guard import task_queue
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', str(tmp_path/'business-tasks.db'))


def rows():
    return [{'subject_id': 'SUBJ-NIKE', 'subject_type': 'brand', 'domain_id': 'BMP', 'brand_focus_id': 'BRAND-NIKE', 'registry_id': 'BRAND-NIKE',
             'name_en': 'Nike', 'name_zh': '耐克', 'status': 'active'}]


def requests(platforms=('douyin', 'x')):
    return [{'domain_id': 'BMP', 'scope_key': 'BRAND-NIKE', 'aliases': ['Nike'],
             'purpose': '中国新品与消费者反馈', 'dimension': 'market_activity',
             'platforms': list(platforms), 'geography_terms': ['中国'], 'topic_terms': ['新品', '联名']}]


def prepare(monkeypatch, platforms=('douyin', 'x')):
    monkeypatch.setattr(entry, '_business_batch_binding',
                        lambda actor, scopes, operator, auth: {'identity': {'actor_id': 101}, 'scopes': scopes, 'operator': operator})
    monkeypatch.setattr(entry, '_manual_collection_guard', lambda *a, **k: (a[1], None))
    real = planner.build_acquisition_plan
    monkeypatch.setattr(planner, 'build_acquisition_plan',
                        lambda *args, **kwargs: real(*args, registry_loader=rows, **kwargs))
    return requests(platforms)


def test_one_platform_challenge_preserves_pending_work_and_rotates_others(monkeypatch):
    reqs = prepare(monkeypatch)
    calls = []
    def collect(platform, keyword, **kwargs):
        calls.append((platform, keyword, kwargs))
        return {'ok': platform == 'x', 'status': 'SUCCESS' if platform == 'x' else 'NEED_VERIFY'}
    monkeypatch.setattr(entry, 'collect_search', collect)
    scope = {'domain_id': 'bmp', 'global_scope': True, 'brand_focus_id': None, 'subject_id': None}
    result = entry.collect_business_queries(reqs, actor={'id': 101}, scopes={'bmp': scope})
    assert [call[0] for call in calls] == ['douyin', 'x', 'x']
    assert len(result['deferred_queries']) == 2
    assert result['status'] == 'PARTIAL' and result['continuation_required'] is True
    assert all(call[2]['scope'] is scope for call in calls)
    assert all(call[2]['business_query'].business_context['native_scope_bound'] is False for call in calls)
    assert result['coverage_complete'] is False
    first_checkpoint = result['checkpoint']
    calls.clear()
    monkeypatch.setattr(entry, 'collect_search', lambda p, k, **kw: calls.append((p,k)) or {'ok': True, 'status': 'SUCCESS'})
    resumed = entry.collect_business_queries(reqs, actor={'id': 101}, scopes={'bmp': scope}, checkpoint=first_checkpoint)
    assert [call[0] for call in calls] == ['douyin', 'douyin']
    assert resumed['status'] == 'BATCH_COMPLETED'
    assert len(resumed['checkpoint']['completed_query_keys']) == 4


def test_missing_actor_and_unknown_platform_do_not_fake_success(monkeypatch):
    reqs = prepare(monkeypatch, ('tiktok',))
    monkeypatch.setattr(entry, 'collect_search', lambda *a, **k: pytest.fail('unsupported route executed'))
    denied = entry.collect_business_queries(reqs)
    assert denied['status'] == 'AUTH_REQUIRED' and denied['network_attempted'] is False
    result = entry.collect_business_queries(reqs, actor={'id': 101}, scopes={'bmp': {'domain_id': 'bmp', 'global_scope': True}})
    assert result['status'] == 'PARTIAL'
    assert result['runs'][0]['result']['status'] == 'NOT_SUPPORTED'
    assert result['deferred_queries'] and result['checkpoint']['completed_query_keys'] == []


def test_changed_task_rejects_stale_checkpoint_before_new_sources(monkeypatch):
    reqs = prepare(monkeypatch)
    monkeypatch.setattr(entry, 'collect_search', lambda *a, **k: pytest.fail('source effect before cursor validation'))
    with pytest.raises(planner.AcquisitionPlanError):
        entry.collect_business_queries(reqs, actor={'id': 101}, checkpoint={'input_fingerprint': 'old', 'completed_query_keys': []})


def test_native_period_and_task_review_preserve_raw_literals_and_null_metrics():
    reqs = requests(('douyin',))
    reqs[0]['publication_since'] = '2026-01-01'
    query = planner.build_acquisition_plan(business_requests=reqs, registry_loader=rows).queries[0]
    records = [
        {'content_id': 'dy:current', 'url': 'https://www.douyin.com/video/1', 'content': 'Nike 中国 新品',
         'create_time': 1788105600, 'digg_count': 0, 'play_count': None},
        {'content_id': 'dy:old', 'url': 'https://www.douyin.com/video/2', 'content': 'Nike 中国 新品', 'create_time': 1730000000},
        {'content_id': 'dy:unknown', 'url': 'https://www.douyin.com/video/3', 'content': 'Nike 中国 新品', 'create_time': None},
    ]
    before = deepcopy(records)
    result = entry._business_source_reviews(records, query, '2026-10-04T00:00:00+00:00')
    assert [row['status'] for row in result] == ['CANDIDATE_TASK_RELEVANT', 'OUTSIDE_REQUESTED_PUBLICATION_PERIOD', 'REVIEW_REQUIRED']
    assert records == before and records[0]['digg_count'] == 0 and records[0]['play_count'] is None
    assert all(row['admitted'] is False for row in result)


def test_batch_limit_is_continuable_instead_of_a_world_cutoff(monkeypatch):
    reqs = prepare(monkeypatch)
    monkeypatch.setattr(entry, 'collect_search', lambda *a, **k: {'ok': True, 'status': 'SUCCESS'})
    scope = {'bmp': {'domain_id': 'bmp', 'global_scope': True}}
    first = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope, max_queries=2)
    assert first['query_plan']['total_queries'] == 4 and len(first['runs']) == 2
    assert first['next_cursor'] is not None and first['continuation_required'] is True
    second = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope, max_queries=2,
                                           continuation=first['next_cursor'], checkpoint=first['checkpoint'])
    assert len(second['runs']) == 2 and second['next_cursor'] is None
    assert len(second['checkpoint']['completed_query_keys']) == 4


def test_different_business_context_cannot_be_attached_to_another_platform():
    query = planner.build_acquisition_plan(business_requests=requests(('douyin',)), registry_loader=rows).queries[0]
    with pytest.raises(ValueError):
        entry.collect_search('x', query.keyword, business_query=query)


def test_unissued_actor_and_cross_domain_scope_are_rejected():
    with pytest.raises(PermissionError, match='AUTH_REQUIRED'):
        entry._business_batch_binding(object(), {'cth': {'domain_id': 'cth', 'global_scope': True}}, 'human', None)
    with pytest.raises(PermissionError, match='QUERY_CALLER_SCOPE_MISMATCH'):
        entry._business_batch_binding({'id': 101}, {'cth': {'domain_id': 'bmp', 'global_scope': True}}, 'human', None)


def test_first_response_crash_recovers_same_server_task_without_repeating_completed_queries(monkeypatch, tmp_path):
    from lumenis.system.collector.guard import task_queue
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', str(tmp_path/'recovery.db'))
    reqs = prepare(monkeypatch, ('x',))
    scope = {'bmp': {'domain_id': 'bmp', 'global_scope': True}}
    calls = []
    def interrupted(platform, keyword, **kwargs):
        calls.append(keyword)
        if len(calls) == 2:
            raise RuntimeError('simulated process interruption before first response')
        return {'ok': True, 'status': 'SUCCESS'}
    monkeypatch.setattr(entry, 'collect_search', interrupted)
    with pytest.raises(RuntimeError):
        entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
    q = task_queue.TaskQueue()
    assert q.stats()['total'] == 1
    with q._conn:
        q._conn.execute('UPDATE tasks SET scheduled_at=0')
    q.close()
    monkeypatch.setattr(entry, 'collect_search', lambda p, k, **kw: calls.append(k) or {'ok': True, 'status': 'SUCCESS'})
    recovered = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
    assert recovered['ok'] is True
    assert calls.count(calls[0]) == 1
    assert len(recovered['checkpoint']['completed_query_keys']) == 2
    again = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
    assert again == entry._historical_business_result(recovered) and len(calls) == 3
    assert again['cached'] is True and again['refresh_performed'] is False
    assert again['result_freshness'] == 'HISTORICAL_TASK_RESULT'
    refreshed = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope, request_id='explicit-new-refresh')
    assert refreshed['ok'] is True and refreshed['checkpoint']['task_id'] != recovered['checkpoint']['task_id']
    assert len(calls) == 5


def test_terminal_failed_batch_returns_failure_and_never_reexecutes(monkeypatch, tmp_path):
    from lumenis.system.collector.guard import task_queue
    reqs = prepare(monkeypatch, ('x',))
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise RuntimeError('owned fixture transient failure')
    monkeypatch.setattr(entry, 'collect_search', fail)
    scope = {'bmp': {'domain_id': 'bmp', 'global_scope': True}}
    for _ in range(3):
        with pytest.raises(RuntimeError):
            entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
        q = task_queue.TaskQueue()
        with q._conn:
            q._conn.execute('UPDATE tasks SET scheduled_at=0')
        q.close()
    result = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
    assert result['status'] == 'FAILED' and result['attempts'] == 3
    assert result['new_collection_requires_new_request_id'] is True
    assert len(calls) == 3


def test_verified_native_partial_resumes_same_task_and_old_receipts_never_refetch(monkeypatch):
    reqs = prepare(monkeypatch, ('x',))
    calls = []
    def collect(platform, keyword, **kwargs):
        calls.append(kwargs['operation_key'])
        if len(calls) == 1:
            return {'ok': False, 'status': 'PARTIAL_COMMITTED',
                'source_status': 'PARTIAL_ACQUISITION_PENDING', 'native_continuation_verified': True,
                'new_collection_required': False, 'task_commit_evidence_ref': 'app_evidence_records:1'}
        return {'ok': True, 'status': 'SUCCESS'}
    monkeypatch.setattr(entry, 'collect_search', collect)
    scope = {'bmp': {'domain_id': 'bmp', 'global_scope': True}}
    first = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
    assert not first['ok'] and first['native_continuation_required'] is True
    assert first['continuation_required'] and not first['new_collection_requires_new_request_id']
    repeated = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope)
    assert repeated['cached'] and len(calls) == 1
    continued = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope,
        checkpoint=first['checkpoint'])
    assert continued['ok'] and continued['checkpoint']['task_id'] == first['checkpoint']['task_id']
    assert len(calls) == 3 and calls[1] == calls[0] + ':native:1'
    assert len(set(calls)) == 3
    old = entry.collect_business_queries(reqs, actor={'id': 101}, scopes=scope,
        checkpoint=first['checkpoint'])
    assert old['cached'] and old['refresh_performed'] is False and len(calls) == 3


@pytest.mark.parametrize('fault', ['none', 'identity', 'persisted', 'run', 'host', 'terminal', 'complete'])
def test_native_resume_requires_original_owner_metadata_and_saved_pointer(monkeypatch, tmp_path, fault):
    from lumenis.system.collector.guard import checkpoint
    monkeypatch.setattr(checkpoint, 'get_data_dir', lambda: str(tmp_path))
    fingerprint = 'a' * 64
    descriptor = {'task_binding': fingerprint, 'keyword': 'allowed isolated query',
        'source_host': 'www.rednote.com', 'raw_path': str(tmp_path / 'never-opened.json'),
        'raw_sha256': 'b' * 64, 'identity_fingerprint': 'c' * 64, 'run_id': 'isolated-run',
        'pending_note_ids': ['d' * 24], 'complete': False, 'terminal_error': False,
        'pagination_exhausted': False, 'continuation_required': True}
    metadata = {'continuation_persisted': True, 'checkpoint_identity_verified': True,
        'continuation': {'identity_verified': True, 'continuation_required': True,
            'keyword': descriptor['keyword'], 'source_host': descriptor['source_host'],
            'checkpoint_run_id': descriptor['run_id']}}
    if fault == 'identity':
        metadata['checkpoint_identity_verified'] = False
    elif fault == 'persisted':
        metadata['continuation_persisted'] = False
    elif fault == 'run':
        metadata['continuation']['checkpoint_run_id'] = 'another-run'
    elif fault == 'host':
        metadata['continuation']['source_host'] = 'unapproved.example'
    elif fault == 'terminal':
        descriptor['terminal_error'] = True
    elif fault == 'complete':
        descriptor['complete'] = True
    assert checkpoint.Checkpoint('xhs').save_operational_resume(descriptor['keyword'], fingerprint, descriptor)
    assert entry._verified_native_resume('xiaohongshu', descriptor['keyword'], fingerprint, metadata) is (fault == 'none')
    assert not entry._verified_native_resume('x', descriptor['keyword'], fingerprint, metadata)


def test_native_resume_finishes_current_query_page_before_advancing_query_cursor(monkeypatch):
    reqs = prepare(monkeypatch, ('x',))
    calls = []
    def collect(platform, keyword, **kwargs):
        calls.append((keyword, kwargs['operation_key']))
        if len(calls) == 1:
            return {'ok': False, 'status': 'PARTIAL_COMMITTED',
                'source_status': 'PARTIAL_ACQUISITION_PENDING', 'native_continuation_verified': True,
                'new_collection_required': False, 'task_commit_evidence_ref': 'app_evidence_records:1'}
        return {'ok': True, 'status': 'SUCCESS'}
    monkeypatch.setattr(entry, 'collect_search', collect)
    args = {'actor': {'id': 101}, 'scopes': {'bmp': {'domain_id': 'bmp', 'global_scope': True}}, 'max_queries': 1}
    first = entry.collect_business_queries(reqs, **args)
    assert first['query_plan']['next_cursor'] is not None
    assert first['native_continuation_required'] and first['next_cursor'] is None
    second = entry.collect_business_queries(reqs, **args,
        checkpoint=first['checkpoint'], continuation=first['next_cursor'])
    assert second['ok'] and not second['native_continuation_required'] and second['next_cursor'] is not None
    assert calls[0][0] == calls[1][0] and calls[1][1] == calls[0][1] + ':native:1'
    final = entry.collect_business_queries(reqs, **args,
        checkpoint=second['checkpoint'], continuation=second['next_cursor'])
    assert final['ok'] and not final['continuation_required'] and len(calls) == 3
    assert final['checkpoint']['task_id'] == first['checkpoint']['task_id']
    assert calls[2][0] != calls[0][0]
