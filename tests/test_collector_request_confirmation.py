"""Manual product confirmation with real Permission and disposable source owners."""
import copy
import sqlite3

import pytest

from tests.test_collector_transaction_truth import (
    admit_registered_subject_for_isolated_collector,
    collector_case as collector_case,
    REQUEST,
    URL,
)
from tests.test_collector_comment_pages import comments_case as comments_case


@pytest.fixture(autouse=True)
def _admit_registered_subject_for_request_confirmation(request):
    case = request.getfixturevalue("collector_case")
    admit_registered_subject_for_isolated_collector(case)


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


def test_publication_window_is_confirmed_and_applied_to_native_time(collector_case):
    case = collector_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    source = {**REQUEST, 'publication_since': '2026-10-01', 'publication_until': '2026-10-01'}
    prepared = post(case, 'prepare', source).get_json()
    assert prepared['request']['publication_since'] == '2026-10-01'
    assert prepared['request']['publication_until'] == '2026-10-01'
    assert not prepared['network_attempted'] and not case['fetches']

    changed = {**source, 'publication_since': '2026-10-02', 'publication_until': '2026-10-02'}
    rejected = post(case, 'confirm', changed, confirmed_resource=prepared['approval_resource'])
    assert rejected.status_code == 403 and rejected.get_json()['code'] == 'COLLECTION_CONFIRMATION_CHANGED'
    assert not case['gate']._approvals and not case['fetches']

    confirmed = post(case, 'confirm', source, confirmed_resource=prepared['approval_resource'])
    assert confirmed.status_code == 200 and confirmed.get_json()['approved']
    result = post(case, 'run', source).get_json()
    assert result['ok'] and result['canonical_synced'] == 1
    window = result['publication_window']
    assert window['state'] == 'APPLIED'
    assert window['transport_filter_state'] == 'NOT_APPLIED_BY_REGISTERED_ADAPTER'
    assert window['within_window_count'] == 1 and window['outside_window_count'] == 0
    assert window['reviews'][0]['status'] == 'CANDIDATE_IN_REQUESTED_PUBLICATION_WINDOW'
    assert window['reviews'][0]['native_publication_normalized'] == 'Thu, 01 Oct 2026 08:00:00 +0000'
    assert len(case['fetches']) == 1


def test_publication_window_excludes_outside_candidates_from_canonical(collector_case):
    case = collector_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    source = {**REQUEST, 'publication_since': '2026-10-02', 'publication_until': '2026-10-02'}
    prepared = post(case, 'prepare', source).get_json()
    assert post(case, 'confirm', source,
        confirmed_resource=prepared['approval_resource']).get_json()['approved']
    result = post(case, 'run', source).get_json()
    assert result['ok'] and result['status'] == 'NO_NEW_DATA'
    assert result['error_type'] == 'NO_MATCHING_OBSERVATIONS'
    assert result['publication_window']['state'] == 'NO_MATCHING_OBSERVATIONS'
    assert result['publication_window']['outside_window_count'] == 1
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT note_id FROM notes').fetchall() == [
            (case['subject_operation_note_id'],)
        ]
        assert connection.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 0


def test_unknown_native_publication_time_remains_review_only(collector_case, monkeypatch):
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.adapters.web_atom import AtomAdapter
    from tests.test_collector_transaction_truth import _feed

    case = collector_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    body = _feed(1234).replace(
        b'<published>2026-10-01T08:00:00Z</published>', b'')
    adapter = AtomAdapter(fetcher=lambda url: PublicResponse(
        url=url, content=body, content_type='application/atom+xml', status_code=200))
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _platform: adapter)
    source = {**REQUEST, 'publication_since': '2026-10-01', 'publication_until': '2026-10-02'}
    prepared = post(case, 'prepare', source).get_json()
    assert post(case, 'confirm', source,
        confirmed_resource=prepared['approval_resource']).get_json()['approved']
    result = post(case, 'run', source).get_json()
    assert not result['ok'] and result['error_type'] == 'PUBLICATION_TIME_REVIEW_REQUIRED'
    assert result['publication_window']['state'] == 'REVIEW_REQUIRED'
    assert result['publication_window']['review_required_count'] == 1
    assert result['publication_window']['reviews'][0]['status'] == 'REVIEW_REQUIRED_NATIVE_PUBLICATION_TIME_UNKNOWN'
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT note_id FROM notes').fetchall() == [
            (case['subject_operation_note_id'],)
        ]
        assert connection.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 0


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


@pytest.fixture
def selected_provider_case(collector_case,monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult,CollectionStatus,AccessClass
    from tests.test_collector_transaction_truth import REGISTERED_NAME
    case=collector_case
    calls=[]
    video='vid00000001'
    class Adapter:
        def health_check(self,**options):
            calls.append(('health',dict(options)))
            return CollectionResult(CollectionStatus.SUCCESS,'youtube',metadata={**options,'network_attempted':False})
        def result(self,kind,value,options):
            calls.append((kind,dict(options)))
            backend='youtube_public_browser' if options.get('public_transport')=='browser' else 'youtube_public_document'
            metadata={**options,'provider':backend,'provider_mode':options.get('provider_mode','public')}
            if kind=='comments':
                pending=case.get('selection_comment_pages') and options.get('cursor') is None
                return CollectionResult(CollectionStatus.SUCCESS,'youtube',comments=[{
                    'platform_comment_id':'native-comment-1','parent_content_id':video,
                    'content':'Permitted fixture comment','author_id':'native-commenter','likes':0}],
                    raw_count=1,metadata={**metadata,'pagination':{'request_cursor':options.get('cursor'),
                        'next_cursor':{'page':2,'transport':options['public_transport']} if pending else None,'exhausted':not pending}},
                    attempted_backend=backend,attempted_access_class=AccessClass.Z0_PUBLIC)
            if kind=='author':
                items=[{'platform_content_id':value,'author_id':value,'title':'Native author',
                    'url':'https://www.youtube.com/channel/'+value,'raw':{'channel_id':value}}]
            else:
                items=[{'platform_content_id':video,'title':REGISTERED_NAME+' source',
                    'content':REGISTERED_NAME+' fixture native body','url':'https://www.youtube.com/watch?v='+video,
                    'raw':{'video_id':video,'channel_id':'UC'+'a'*22,'title':REGISTERED_NAME+' source',
                           'description':REGISTERED_NAME+' fixture native body','view_count':None}}]
            return CollectionResult(CollectionStatus.SUCCESS,'youtube',items=items,raw_count=len(items),metadata=metadata,
                attempted_backend=backend,attempted_access_class=AccessClass.Z0_PUBLIC)
        def search(self,value,**options): return self.result('search',value,options)
        def detail(self,value,**options): return self.result('detail',value,options)
        def author(self,value,**options): return self.result('author',value,options)
        def author_posts(self,value,**options): return self.result('author_posts',value,options)
        def comments(self,value,**options): return self.result('comments',value,options)
    monkeypatch.setattr(case['surface'],'_get_runtime_adapter',lambda platform:Adapter())
    case.update(selection_calls=calls,selection_video=video)
    return case


def test_provider_and_transport_confirmation_cannot_be_reused_for_another_route(selected_provider_case,monkeypatch):
    case=selected_provider_case
    source={'operator':'human','confirm_read_only':True,'platform':'youtube','keyword':'permitted fixture',
            'max_results':1,'provider_mode':'public','public_transport':'http'}
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    prepared=post(case,'prepare',source).get_json()
    assert prepared['status'] == 'CONFIRMATION_REQUIRED'
    assert prepared['approval_resource']
    changed={**source,'public_transport':'browser'}
    changed_prepared=post(case,'prepare',changed)
    assert changed_prepared.status_code == 200, changed_prepared.get_json()
    changed_payload=changed_prepared.get_json()
    assert changed_payload['status'] == 'CONFIRMATION_REQUIRED'
    assert changed_payload['approval_resource']!=prepared['approval_resource']
    assert post(case,'confirm',changed,confirmed_resource=prepared['approval_resource']).status_code==403
    assert post(case,'confirm',source,confirmed_resource=prepared['approval_resource']).get_json()['approved']
    assert post(case,'run',changed).get_json()['status']=='APPROVAL_REQUIRED'
    assert not case['selection_calls']
    monkeypatch.setitem(case['surface']._last_action,'youtube',0.0)
    result=post(case,'run',source).get_json()
    assert result['ok'],result
    assert all(options.get('public_transport')=='http' and options.get('provider_mode')=='public'
               for _,options in case['selection_calls'])


@pytest.mark.parametrize('capability',['detail','author','author_posts','comments'])
def test_direct_capabilities_forward_exact_selected_transport(selected_provider_case,monkeypatch,capability):
    case=selected_provider_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    source={'operator':'human','confirm_read_only':True,'platform':'youtube','keyword':'permitted fixture',
            'max_results':1,'provider_mode':'public','public_transport':'http'}
    if capability=='comments':
        prepared=post(case,'prepare',source).get_json()
        assert post(case,'confirm',source,confirmed_resource=prepared['approval_resource']).get_json()['approved']
        assert post(case,'run',source).get_json()['ok']
        source={'operator':'human','confirm_read_only':True,'source_id':case['selection_video'],'max_results':1,
                'request_id':'source-comments-route-001'}
    elif capability=='detail':
        source.pop('keyword');source.pop('max_results')
        source['content_id']=case['selection_video']
    else:
        source.pop('keyword')
        source['author_id']='UC'+'a'*22
    source.update(capability=capability,provider_mode='public',public_transport='browser')
    confirmation={k:v for k,v in source.items() if k!='request_id'}
    prepared=post(case,'prepare',confirmation).get_json()
    assert post(case,'confirm',confirmation,confirmed_resource=prepared['approval_resource']).get_json()['approved']
    case['selection_calls'].clear()
    monkeypatch.setitem(case['surface']._last_action,'youtube',0.0)
    result=post(case,'run',source).get_json()
    assert result['ok'],result
    actual=[options for kind,options in case['selection_calls'] if kind==capability]
    assert actual and actual[0]['public_transport']=='browser' and actual[0]['provider_mode']=='public'


def test_korean_native_projection_keeps_measured_zero_and_missing_fields():
    from lumenis.system.collector.adapters.secondary_collection import _native_record,_normalize_author_target
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record
    for platform,prefix in [('naver','blog:actual:1'),('daum','tistory:actual:1')]:
        native=_native_record({'platform_content_id':prefix,'likes':0,'comments':None,'shares':0,'views':None,
            'raw':{'native_content_id':prefix,'native_kind':'blog' if platform=='naver' else 'tistory'}},platform,'actual','2026-10-26T00:00:00Z')
        canonical=to_canonical_record(native,platform)
        assert canonical['content_id']==prefix and canonical['like_count']==0 and canonical['comment_count'] is None
        assert canonical['share_count']==0 and native['views'] is None and canonical['published_at'] is None
    assert _normalize_author_target('naver','https://blog.naver.com/actual')=='actual'
    assert _normalize_author_target('daum','https://actual.tistory.com/')=='actual'
    assert _normalize_author_target('linkedin','https://www.linkedin.com/company/actual/')=='company:actual'
    with pytest.raises(ValueError):
        _normalize_author_target('naver','https://cafe.naver.com/community')


def test_comment_receipt_cannot_cross_explicit_transport(selected_provider_case,monkeypatch):
    case=selected_provider_case
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    source={'operator':'human','confirm_read_only':True,'platform':'youtube','keyword':'permitted fixture',
            'max_results':1,'provider_mode':'public','public_transport':'http'}
    prepared=post(case,'prepare',source).get_json()
    assert post(case,'confirm',source,confirmed_resource=prepared['approval_resource']).get_json()['approved']
    monkeypatch.setitem(case['surface']._last_action,'youtube',0.0)
    result=post(case,'run',source).get_json()
    assert result['ok'],result
    comments={'operator':'human','confirm_read_only':True,'capability':'comments','source_id':case['selection_video'],
              'max_results':1,'provider_mode':'public','public_transport':'http'}
    prepared=post(case,'prepare',comments).get_json()
    assert post(case,'confirm',comments,confirmed_resource=prepared['approval_resource']).get_json()['approved']
    case['selection_comment_pages']=True
    monkeypatch.setitem(case['surface']._last_action,'youtube',0.0)
    page=post(case,'run',{**comments,'request_id':'route-bound-comment-page'}).get_json()
    assert page['page_ref'] and page['continuation']
    changed={**comments,'public_transport':'browser'}
    prepared=post(case,'prepare',changed).get_json()
    assert post(case,'confirm',changed,confirmed_resource=prepared['approval_resource']).get_json()['approved']
    case['selection_calls'].clear()
    monkeypatch.setitem(case['surface']._last_action,'youtube',0.0)
    denied=post(case,'run',{**changed,'request_id':'route-bound-comment-page','continuation':page['continuation']})
    assert denied.status_code in {400,403} and not case['selection_calls']
