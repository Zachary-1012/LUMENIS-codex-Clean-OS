"""Compatibility API must use the canonical transaction and exact caller scope."""
from types import SimpleNamespace

import pytest

import app as api
from lumenis.system.collector import acquisition_plan
from lumenis.system.collector.adapters import secondary_collection


@pytest.fixture
def harness(monkeypatch):
    scope = {'domain_id': 'cth', 'subject_id': 'CTH-A',
             'brand_focus_id': None, 'global_scope': False}
    actor = object()
    rows = [dict(subject_id='CTH-' + key, domain_id='CTH', subject_type='company',
                 name_en='Mall ' + key, name_zh='商场' + key, keywords=['Mall ' + key],
                 status='configured') for key in ('A', 'B')]
    build = acquisition_plan.build_acquisition_plan
    monkeypatch.setattr(acquisition_plan, 'build_acquisition_plan',
        lambda *args, **kw: build(*args, **kw, registry_loader=lambda: rows))
    monkeypatch.setattr(api, '_collect_request_context', lambda action: (actor, scope, 'account:7'))
    monkeypatch.setattr(api, 'collect_tasks', {})
    monkeypatch.setattr(api.xhs_cookie_bridge, 'is_user_paused', lambda: False)
    monkeypatch.setattr(secondary_collection, '_manual_collection_guard', lambda *a, **kw: (scope, None))
    # Run the real copied-request worker inline; no platform/browser/network/DB effects.
    class InlineThread:
        def __init__(self, target, **kw): self.target = target
        def start(self): self.target()
    monkeypatch.setattr(api.threading, 'Thread', InlineThread)
    calls = []
    def collect(platform, keyword, **kwargs):
        calls.append((platform, keyword, kwargs))
        return {'ok': True, 'status': 'SUCCESS', 'imported': 1,
                'evidence_ref': 'evidence:fixture', 'canonical_synced': 1,
                'details': [{'private_raw': 'must not leave adapter'}]}
    monkeypatch.setattr(secondary_collection, 'collect_search', collect)
    def forbidden(*a, **kw):
        pytest.fail('compatibility route bypassed the canonical collector')
    monkeypatch.setattr(api.db, 'insert_note', forbidden)
    monkeypatch.setattr(api.collector, 'collect_all', forbidden)
    monkeypatch.setattr(api.reprocess, 'analyze_note_row', forbidden)
    return SimpleNamespace(scope=scope, actor=actor, calls=calls)


def post(body=None):
    with api.app.test_request_context('/api/collect', method='POST', json=body or {
            'operator': 'human_ui', 'confirm_read_only': True, 'keywords': ['Mall A']}):
        result = api.api_collect()
        return result if isinstance(result, tuple) else (result, 200)


def test_normal_result_uses_exact_canonical_scope_and_does_not_claim_analysis(harness):
    response, status = post()
    assert status == 200
    task = api.collect_tasks[response.get_json()['task_id']]
    assert task['status'] == 'done'
    assert task['analysis_status'] == 'NOT_RUN'
    assert task['resume_supported'] is False
    assert harness.calls
    for platform, _, kwargs in harness.calls:
        assert platform == 'xiaohongshu'
        assert kwargs['actor'] is harness.actor
        assert kwargs['scope'] == harness.scope
    assert 'private_raw' not in str(task)
    assert task['runs'][0]['evidence_ref'] == 'evidence:fixture'
    assert task['runs'][0]['canonical_synced'] == 1


def test_focus_without_keywords_cannot_collect_other_registered_subjects(harness):
    response, status = post({'operator': 'human', 'confirm_read_only': True})
    assert status == 200
    assert harness.calls
    assert all(call[2]['scope'] == harness.scope for call in harness.calls)
    assert all(item['subject_id'] == 'CTH-A' for item in response.get_json()['query_plan']['queries'])


def test_denial_creates_no_task_and_does_not_collect(harness, monkeypatch):
    monkeypatch.setattr(secondary_collection, '_manual_collection_guard',
        lambda *a, **kw: (None, {'ok': False, 'status': 'APPROVAL_REQUIRED'}))
    response, status = post()
    assert status == 403
    assert response.get_json()['status'] == 'APPROVAL_REQUIRED'
    assert api.collect_tasks == {}
    assert harness.calls == []


def test_global_collection_keeps_global_source_scope_not_planned_entity(harness):
    harness.scope.update(subject_id=None, global_scope=True)
    response, status = post()
    assert status == 200
    task = api.collect_tasks[response.get_json()['task_id']]
    assert task['status'] == 'done'
    assert harness.calls
    assert all(call[2]['scope']['global_scope'] is True for call in harness.calls)
    assert all(call[2]['scope']['subject_id'] is None for call in harness.calls)


def test_pause_is_not_success(harness, monkeypatch):
    monkeypatch.setattr(api.xhs_cookie_bridge, 'is_user_paused', lambda: True)
    response, _ = post()
    task = api.collect_tasks[response.get_json()['task_id']]
    assert task['status'] == 'paused'
    assert harness.calls == []
    assert not api._collect_lock.locked()


def test_explicit_scroll_depth_is_bound_in_admission_and_execution(harness, monkeypatch):
    admitted = []
    def guard(*args, **kwargs):
        admitted.append(kwargs['max_scroll'])
        return harness.scope, None
    monkeypatch.setattr(secondary_collection, '_manual_collection_guard', guard)
    response, status = post({'operator': 'human', 'confirm_read_only': True,
                            'keywords': ['Mall A'], 'max_scroll': 7})
    assert status == 200
    assert admitted and all(depth == 7 for depth in admitted)
    assert all(call[2]['max_scroll'] == 7 for call in harness.calls)
    assert api.collect_tasks[response.get_json()['task_id']]['max_scroll'] == 7


def test_blocked_source_remains_blocked_without_fake_counts(harness, monkeypatch):
    monkeypatch.setattr(secondary_collection, 'collect_search',
        lambda *a, **kw: {'ok': False, 'status': 'AUTH_REQUIRED'})
    response, _ = post()
    task = api.collect_tasks[response.get_json()['task_id']]
    assert task['status'] == 'blocked'
    assert task['code'] == 'AUTH_REQUIRED'
    assert 'imported' not in task['runs'][0]
    assert not api._collect_lock.locked()


def test_polling_requires_same_fresh_scope_and_actor(harness, monkeypatch):
    response, _ = post()
    task_id = response.get_json()['task_id']
    with api.app.test_request_context('/api/collect/status/' + task_id):
        visible, code = api.api_collect_status(task_id)
        assert code == 200
        assert '_owner' not in visible.get_json()['task']
    monkeypatch.setattr(api, '_collect_request_context',
        lambda action: (harness.actor, harness.scope, 'account:8'))
    with api.app.test_request_context('/api/collect/status/' + task_id):
        _, code = api.api_collect_status(task_id)
        assert code == 404
        assert api.api_collect_tasks().get_json()['tasks'] == []


@pytest.mark.parametrize('body,status', [
    ({'operator': 'ai', 'confirm_read_only': True}, 403),
    ({'operator': 'human'}, 400),
    ({'operator': 'human', 'confirm_read_only': True, 'actor': 7}, 400),
])
def test_explicit_manual_contract_required(harness, body, status):
    _, actual = post(body)
    assert actual == status
    assert not harness.calls
