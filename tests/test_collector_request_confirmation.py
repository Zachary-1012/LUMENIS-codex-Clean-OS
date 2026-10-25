"""Manual product confirmation with real Permission and disposable source owners."""
import copy

import pytest

from tests.test_collector_transaction_truth import collector_case, REQUEST, URL
from tests.test_collector_comment_pages import comments_case


def post(case, action, request=None, **extra):
    return case['client'].post(URL, headers=case['focus_headers'],
        json={**(request or REQUEST), 'action': action, **extra})


def test_preview_confirm_normal_source_run_and_changed_request(collector_case):
    case = collector_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    preview = post(case, 'prepare')
    assert preview.status_code == 200
    prepared = preview.get_json()
    assert prepared['status'] == 'CONFIRMATION_REQUIRED'
    assert not prepared['network_attempted'] and not case['fetches']
    assert not case['gate']._approvals
    changed = post(case, 'confirm', {**REQUEST, 'max_results': 2},
        confirmed_resource=prepared['approval_resource'])
    assert changed.status_code == 403 and changed.get_json()['code'] == 'COLLECTION_CONFIRMATION_CHANGED'
    assert not case['gate']._approvals and not case['fetches']
    confirmed = post(case, 'confirm', confirmed_resource=prepared['approval_resource'])
    assert confirmed.status_code == 200 and confirmed.get_json()['approved']
    assert len(case['gate']._approvals) == 1 and not case['fetches']
    result = post(case, 'run')
    assert result.status_code == 200 and result.get_json()['ok']
    assert len(case['fetches']) == 1


@pytest.mark.parametrize('permission', ['COMMIT', 'HUMAN_APPROVAL'])
def test_confirmation_cannot_grant_after_current_permission_withdrawal(collector_case, permission):
    case = collector_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    prepared = post(case, 'prepare').get_json()
    case['gate'].revoke_permission(getattr(case['permission'].PermissionLevel, permission))
    result = post(case, 'confirm', confirmed_resource=prepared['approval_resource'])
    assert result.status_code == 403
    assert not case['gate']._approvals and not case['fetches']


def test_search_approval_cannot_be_reused_for_detail(collector_case):
    case = collector_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    prepared = post(case, 'prepare').get_json()
    assert post(case, 'confirm', confirmed_resource=prepared['approval_resource']).status_code == 200
    with case['client'].application.test_request_context('/', headers=case['focus_headers'],
            environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = case['permission'].resolve_local_workspace_principal(module='collector', action='write')
        _, denied = case['surface']._manual_collection_guard(actor, case['scope'],
            REQUEST['platform'], REQUEST['keyword'], REQUEST['max_results'], capability='detail')
    assert denied['status'] == 'APPROVAL_REQUIRED' and not case['fetches']


def test_comments_preview_uses_admitted_parent_and_confirmation_rejects_scope_replacement(comments_case):
    case = comments_case
    case['gate']._approvals.clear()
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    request = {'operator': 'human_ui', 'confirm_read_only': True, 'capability': 'comments',
               'source_id': case['source_id'], 'max_results': 20, 'include_replies': False}
    prepared = post(case, 'prepare', request).get_json()
    assert prepared['request']['platform'] == 'xiaohongshu'
    assert prepared['request']['source_url'].endswith(case['source_id'])
    assert not case['gate']._approvals and not case['calls']
    replaced = copy.deepcopy(request)
    replaced['include_replies'] = True
    assert post(case, 'confirm', replaced, confirmed_resource=prepared['approval_resource']).status_code == 403
    assert not case['gate']._approvals
    assert post(case, 'confirm', request, confirmed_resource=prepared['approval_resource']).get_json()['approved']


def test_detail_preview_and_run_use_identical_credential_free_identity(comments_case):
    case = comments_case
    case['gate']._approvals.clear()
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    request = {'operator': 'human', 'confirm_read_only': True, 'capability': 'detail',
               'platform': 'xhs', 'content_id': 'https://www.rednote.com/explore/' + case['source_id']}
    prepared = post(case, 'prepare', request).get_json()
    assert prepared['request']['max_results'] == 1
    assert post(case, 'confirm', request, confirmed_resource=prepared['approval_resource']).get_json()['approved']


@pytest.mark.parametrize('reason,status', [
    ('COLLECTOR_IDENTITY_NOT_VERIFIED', 'SESSION_EXPIRED'),
    ('COLLECTOR_IDENTITY_MISMATCH', 'BLOCKED'),
    ('COLLECTOR_IDENTITY_UNAVAILABLE', 'PROVIDER_UNAVAILABLE'),
])
def test_worker_identity_failure_keeps_actionable_safe_reason(reason, status):
    from types import SimpleNamespace
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter
    backend = SimpleNamespace(search_xiaohongshu=lambda *a, **kw: {
        'notes': [], 'total': 0, 'error': 'CDP_EXCEPTION: ' + reason})
    result = XiaohongshuAdapter(backend=backend).search('explicit source query')
    assert result.status.value == status
    assert result.metadata['error_type'] == reason and not result.ok
