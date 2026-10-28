"""Native-author data, versions and consumer reads on disposable original owners."""
import sqlite3

from tests.test_collector_transaction_truth import collector_case, URL, GLOBAL_MODE


def test_native_author_fields_counts_canonical_and_cold_read(collector_case, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = collector_case
    calls = []
    followers = {'value':0}
    class DeclaredProfileFixture:
        def author(self,target):
            calls.append(target)
            return CollectionResult(CollectionStatus.SUCCESS,'bilibili',items=[{
                'title':'Explicit profile fixture','content':'Native biography fixture',
                'url':'https://space.bilibili.com/12345','author_id':'12345',
                'raw':{'mid':12345,'follower_count':followers['value'],
                       'following_count':None,'content_count':7}}])
    monkeypatch.setattr(case['surface'],'_get_runtime_adapter',lambda *args:DeclaredProfileFixture())
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    body = {'operator':'human_ui','confirm_read_only':True,'platform':'bilibili',
            'capability':'author','author_id':'https://space.bilibili.com/12345'}
    def post(action,**extra):
        return case['client'].post(URL,headers=GLOBAL_MODE,json={**body,'action':action,**extra})
    resource = post('prepare').get_json()['approval_resource']
    assert post('confirm',confirmed_resource=resource).get_json()['approved']
    monkeypatch.setitem(case['surface']._last_action,'bilibili',0.0)
    first_response = post('run')
    first = first_response.get_json()
    assert first_response.status_code == 200 and first['ok'], first
    assert first['authors'][0]['follower_count'] == 0
    assert first['authors'][0]['following_count'] is None
    assert first['authors'][0]['published_at'] is None
    assert first['canonical_refs'][0]['source_id'] == 'platform-author:bilibili:12345'
    route = '/api/experience/cth/platform-collection/results'
    cold = case['client'].get(route,headers=GLOBAL_MODE,query_string={'evidence_ref':first['author_evidence_ref']})
    assert cold.status_code == 200 and cold.get_json()['authors'] == first['authors']
    followers['value'] = 8
    monkeypatch.setitem(case['surface']._last_action,'bilibili',0.0)
    second = post('run').get_json()
    assert second['authors'][0]['follower_count'] == 8
    old = case['client'].get(route,headers=GLOBAL_MODE,query_string={'evidence_ref':first['author_evidence_ref']})
    assert old.get_json()['authors'][0]['follower_count'] == 0 and len(calls) == 2
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT follower_count,following_count,content_count FROM platform_accounts').fetchone() == (8,None,7)
        snapshots = connection.execute("SELECT likes,comments,collects,shares FROM metric_snapshots WHERE entity_type='platform_account'").fetchall()
        assert snapshots == [(None,None,None,None),(None,None,None,None)]
        connection.execute("UPDATE canonical_data SET scope_status='REJECTED' WHERE source_table='platform_accounts'")
    denied = case['client'].get(route,headers=GLOBAL_MODE,query_string={'evidence_ref':second['author_evidence_ref']})
    assert denied.status_code == 403 and len(calls) == 2
