from copy import deepcopy

import pytest

from lumenis.system.collector import acquisition_plan as planner
from lumenis.system.collector.adapters import secondary_collection as entry


def rows():
    return [{'subject_id': 'SUBJ-NIKE', 'subject_type': 'brand', 'domain_id': 'BMP', 'brand_focus_id': 'BRAND-NIKE', 'registry_id': 'BRAND-NIKE',
             'name_en': 'Nike', 'name_zh': '耐克', 'status': 'active'}]


def requests(platforms=('douyin', 'x')):
    return [{'domain_id': 'BMP', 'scope_key': 'BRAND-NIKE', 'aliases': ['Nike'],
             'purpose': '中国新品与消费者反馈', 'dimension': 'market_activity',
             'platforms': list(platforms), 'geography_terms': ['中国'], 'topic_terms': ['新品', '联名']}]


def prepare(monkeypatch, platforms=('douyin', 'x')):
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
    result = entry.collect_business_queries(reqs, actor=object(), scopes={'bmp': scope})
    assert [call[0] for call in calls] == ['douyin', 'x', 'x']
    assert len(result['deferred_queries']) == 2
    assert result['status'] == 'PARTIAL' and result['continuation_required'] is True
    assert all(call[2]['scope'] is scope for call in calls)
    assert all(call[2]['business_query'].business_context['native_scope_bound'] is False for call in calls)
    assert result['coverage_complete'] is False
    first_checkpoint = result['checkpoint']
    calls.clear()
    monkeypatch.setattr(entry, 'collect_search', lambda p, k, **kw: calls.append((p,k)) or {'ok': True, 'status': 'SUCCESS'})
    resumed = entry.collect_business_queries(reqs, actor=object(), scopes={'bmp': scope}, checkpoint=first_checkpoint)
    assert [call[0] for call in calls] == ['douyin', 'douyin']
    assert resumed['status'] == 'BATCH_COMPLETED'
    assert len(resumed['checkpoint']['completed_query_keys']) == 4


def test_missing_actor_and_unknown_platform_do_not_fake_success(monkeypatch):
    reqs = prepare(monkeypatch, ('tiktok',))
    monkeypatch.setattr(entry, 'collect_search', lambda *a, **k: pytest.fail('unsupported route executed'))
    denied = entry.collect_business_queries(reqs)
    assert denied['status'] == 'AUTH_REQUIRED' and denied['network_attempted'] is False
    result = entry.collect_business_queries(reqs, actor=object(), scopes={'bmp': {'domain_id': 'bmp', 'global_scope': True}})
    assert result['status'] == 'PARTIAL'
    assert result['runs'][0]['result']['status'] == 'NOT_SUPPORTED'
    assert result['deferred_queries'] and result['checkpoint']['completed_query_keys'] == []


def test_changed_task_rejects_stale_checkpoint_before_new_sources(monkeypatch):
    reqs = prepare(monkeypatch)
    monkeypatch.setattr(entry, 'collect_search', lambda *a, **k: pytest.fail('source effect before cursor validation'))
    with pytest.raises(planner.AcquisitionPlanError):
        entry.collect_business_queries(reqs, actor=object(), checkpoint={'input_fingerprint': 'old', 'completed_query_keys': []})


def test_native_period_and_task_review_preserve_raw_literals_and_null_metrics():
    query = planner.build_acquisition_plan(business_requests=requests(('douyin',)), registry_loader=rows).queries[0]
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
    first = entry.collect_business_queries(reqs, actor=object(), scopes=scope, max_queries=2)
    assert first['query_plan']['total_queries'] == 4 and len(first['runs']) == 2
    assert first['next_cursor'] is not None and first['continuation_required'] is True
    second = entry.collect_business_queries(reqs, actor=object(), scopes=scope, max_queries=2,
                                           continuation=first['next_cursor'], checkpoint=first['checkpoint'])
    assert len(second['runs']) == 2 and second['next_cursor'] is None
    assert len(second['checkpoint']['completed_query_keys']) == 4


def test_different_business_context_cannot_be_attached_to_another_platform():
    query = planner.build_acquisition_plan(business_requests=requests(('douyin',)), registry_loader=rows).queries[0]
    with pytest.raises(ValueError):
        entry.collect_search('x', query.keyword, business_query=query)
