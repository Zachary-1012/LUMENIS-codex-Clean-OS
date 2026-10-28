"""Native response fixtures exercise normal Source/Canonical product consumers."""
import json
import sqlite3
from unittest.mock import Mock

from tests.test_collector_transaction_truth import collector_case, URL, GLOBAL_MODE


def test_zhihu_full_bodies_typed_identities_and_global_native_comments(collector_case, monkeypatch):
    from lumenis.system.collector.adapters.zhihu import ZhihuAdapter
    import requests
    case = collector_case
    adapter = ZhihuAdapter()
    monkeypatch.setattr(case['surface'],'_get_runtime_adapter',lambda platform:adapter)
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    calls = []
    full_body = 'Declared original native body fixture with useful complete source text. '*8
    def get(url,**options):
        calls.append(url)
        if '/comment_v5/' in url:
            payload = {'data':[{'id':'901','content':'Native root fixture','child_comment_count':1,
                'like_count':None,'child_comments':[{'id':'902','content':'Returned reply fixture',
                                                  'like_count':0,'reply_to_comment_id':'901'}]}],
                       'paging':{'is_end':True,'next':''}}
        else:
            kind = 'article' if '/articles/' in url else 'answer'
            payload = {'id':123,'type':kind,'question':{'id':77,'title':'Native source fixture'},
                'title':'Native article fixture','content':'<p>'+full_body+'</p>',
                'excerpt':'This excerpt must not replace the actual body.', 'created_time':1700000000,
                'created':1700000000,'voteup_count':None,'comment_count':0,
                'author':{'id':'native-hash','url_token':'native-handle','name':'Native author'}}
        return Mock(status_code=200,json=lambda:payload)
    monkeypatch.setattr(requests,'get',get)
    def execute(body):
        common = {'operator':'human_ui','confirm_read_only':True,**body}
        prepared = case['client'].post(URL,headers=GLOBAL_MODE,json={**common,'action':'prepare'}).get_json()
        confirmed = case['client'].post(URL,headers=GLOBAL_MODE,json={**common,'action':'confirm',
            'confirmed_resource':prepared['approval_resource']}).get_json()
        assert confirmed.get('approved'), confirmed
        monkeypatch.setitem(case['surface']._last_action,'zhihu',0.0)
        response = case['client'].post(URL,headers=GLOBAL_MODE,json={**common,'action':'run',
            **({'request_id':'declared-global-comments'} if common.get('capability')=='comments' else {})})
        assert response.status_code == 200 and response.get_json()['ok'], response.get_json()
        return response.get_json()
    answer = execute({'platform':'zhihu','capability':'detail',
                      'content_id':'https://www.zhihu.com/question/77/answer/123'})
    article = execute({'platform':'zhihu','capability':'detail','content_id':'https://zhuanlan.zhihu.com/p/123'})
    assert answer['items'][0]['source_id'] == '123'
    assert article['items'][0]['source_id'] == 'zhihu:article:123'
    assert answer['items'][0]['body_state'] == 'PLATFORM_BODY'
    assert answer['items'][0]['body_preview'] == full_body.strip()
    assert answer['items'][0]['metrics']['likes'] is None and answer['items'][0]['metrics']['comments'] == 0
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 2
        assert set(connection.execute('SELECT platform_content_id,content FROM platform_contents').fetchall()) == {
            ('123',full_body.strip()),('zhihu:article:123',full_body.strip())}
    page = execute({'capability':'comments','source_id':article['items'][0]['source_id'],
                    'max_results':20,'include_replies':False})
    assert [item['platform_comment_id'] for item in page['comments']] == ['901','902']
    assert page['comments'][1]['parent_comment_id'] == '901'
    assert page['comments'][0]['likes'] is None and page['comments'][1]['likes'] == 0
    with sqlite3.connect(case['db_path']) as connection:
        signed = connection.execute('SELECT inputs_json FROM app_evidence_records WHERE id=?',
            (int(page['page_ref'].split(':')[1]),)).fetchone()
        parent = json.loads(signed[0])['parent']
        assert parent['scope']['global_scope'] is True and parent['scope_evidence_ref'] == ''
        assert parent['source_observation_evidence_ref'] == article['evidence_ref']
    cold = case['client'].get('/api/experience/cth/platform-collection/results',headers=GLOBAL_MODE,
        query_string={'evidence_ref':'app_evidence_records:'+article['evidence_ref']})
    assert cold.status_code == 200 and cold.get_json()['items'][0]['source_id'] == 'zhihu:article:123'
    assert len(calls) == 3
