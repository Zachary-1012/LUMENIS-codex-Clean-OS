"""Read-only conveniences on the existing SavedWork API and owner."""
import copy
import uuid
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace,WORKS
from tests.test_growth_research_shared import research,SHARED
from tests.test_independent_growth_real_app import real_app,headers,counts


def save(ws,text='first 😀中文\nrepeated\nrepeated\n',parent=None,headers_=SHARED):
    body={'title':'Continue this work','markdown':text,'kind':'research','payload':{'user_text':text},'citations':[], 'request_id':'convenience-'+uuid.uuid4().hex}
    if parent:body.update(work_id=parent['document']['work_id'],previous_artifact_id=parent['artifact']['artifact_id'],expected_draft_digest=parent['document']['draft_digest'])
    response=ws['api'].post(WORKS,headers=headers_,json=body)
    assert response.status_code==200,response.get_json()
    return response.get_json()['result']


def read(ws,item,**query):return ws['api'].get(WORKS+'/'+item['artifact']['artifact_id'],headers=SHARED,query_string=query)


def test_latest_search_pages_resume_only_current_and_cursor_is_bound(research):
    first=save(research);second=save(research,'current only',first);other=save(research,'other')
    seen=[];cursor=None
    for _ in range(5):
        query={'latest_only':'true','limit':1}
        if cursor:query['cursor']=cursor
        response=research['api'].get(WORKS,headers=SHARED,query_string=query)
        assert response.status_code==200,response.get_json();page=response.get_json()['result']
        for item in page['items']:
            seen.append(item['artifact']['artifact_id'])
            assert item['resume']['expected_sha256']==item['artifact']['sha256']
            assert item['resume']['execution']=='not_started'
        cursor=page['next_cursor']
        if not cursor:break
        assert research['api'].get(WORKS,headers=SHARED,query_string={'cursor':cursor,'limit':1}).status_code==400
    assert set(seen)=={second['artifact']['artifact_id'],other['artifact']['artifact_id']} and len(seen)==2
    assert not research['api'].get(WORKS,headers=SHARED,query_string={'latest_only':'true','query':'first'}).get_json()['result']['items']
    assert research['api'].get(WORKS,headers=SHARED,query_string={'query':'first'}).get_json()['result']['items']


def test_selection_unicode_preview_explicit_save_reopen_and_stale_denial(research):
    item=save(research);before=counts(research)
    response=read(research,item,selection_start=6,selection_end=9)
    assert response.status_code==200,response.get_json();preview=response.get_json()['result']
    assert preview['state']=='preview_not_saved' and preview['offset_unit']=='unicode_codepoint'
    assert preview['save_draft']['payload']['note']['blocks'][0]['text']=='😀中文'
    assert counts(research)==before
    draft=preview['save_draft'];draft['request_id']='selection-explicit-save'
    saved=research['api'].post(WORKS,headers=SHARED,json=draft)
    assert saved.status_code==200,saved.get_json()
    assert saved.get_json()['result']['document']['kind']=='note'
    updated=save(research,'updated source',item)
    assert read(research,item,selection_start=0,selection_end=5).status_code==409
    assert read(research,updated,selection_start=0,selection_end=7).status_code==200
    assert read(research,saved.get_json()['result']).status_code!=200


def test_comparison_same_work_order_no_change_and_no_write(research):
    first=save(research);second=save(research,'first 😀中文\nchanged\nrepeated\n',first);before=counts(research)
    response=read(research,second,compare_to=first['artifact']['artifact_id'])
    assert response.status_code==200,response.get_json();view=response.get_json()['result']
    assert view['changed'] and view['target_is_current'] and view['execution']=='not_started'
    markdown=next(x for x in view['changes'] if x['pointer']=='/markdown')
    assert '-repeated' in markdown['unified_diff'] and '+changed' in markdown['unified_diff']
    assert markdown['before']==first['document']['markdown']
    same=read(research,second,compare_to=second['artifact']['artifact_id']).get_json()['result']
    assert not same['changed'] and same['changes']==[]
    assert counts(research)==before
    other=save(research,'different work')
    assert read(research,second,compare_to=other['artifact']['artifact_id']).status_code==400


@pytest.mark.parametrize('query',[{'latest_only':'yes'},{'latest_only':'1'},{'latest_only':'true','actor_id':'201'}])
def test_search_strict_inputs(research,query):
    assert research['api'].get(WORKS,headers=SHARED,query_string=query).status_code==400


@pytest.mark.parametrize('query',[{'selection_start':'-1','selection_end':'3'}, {'selection_start':'0'},
 {'selection_start':'0','selection_end':'999999'}, {'selection_start':'0','selection_end':'0'},
 {'selection_start':'０','selection_end':'3'}, {'selection_start':'0','selection_end':'2','compare_to':'anything'},
 {'compare_to':''}, [('selection_start','0'),('selection_start','1'),('selection_end','2')]])
def test_preview_strict_inputs_no_writes(research,query):
    item=save(research);before=counts(research)
    response=research['api'].get(WORKS+'/'+item['artifact']['artifact_id'],headers=SHARED,query_string=query)
    assert response.status_code==400,response.get_json();assert counts(research)==before


def test_real_sessions_isolation_and_revocation_for_every_convenience(real_app):
    ws=real_app;first=save(ws,headers_=headers(201));second=save(ws,'new',first,headers_=headers(201));before=counts(ws)
    path=WORKS+'/'+second['artifact']['artifact_id']
    for h in [SHARED,headers(202)]:
        for query in [{'selection_start':0,'selection_end':2},{'compare_to':first['artifact']['artifact_id']}]:
            response=ws['api'].get(path,headers=h,query_string=query)
            assert response.status_code in {400,401,403,404},response.get_json()
    foreign=ws['api'].get(WORKS,headers=headers(202),query_string={'latest_only':'true'}).get_json()['result']
    assert not foreign['items']
    own=ws['api'].get(WORKS,headers=headers(201),query_string={'latest_only':'true'}).get_json()['result']
    assert len(own['items'])==1
    assert counts(ws)==before
    with ws['repo'].transaction() as con:con.execute('DELETE FROM v4_sessions WHERE user_id=201')
    assert ws['api'].get(WORKS,headers=headers(201),query_string={'latest_only':'true'}).status_code in {401,403}
    assert ws['api'].get(path,headers=headers(201),query_string={'compare_to':first['artifact']['artifact_id']}).status_code in {401,403}
    assert counts(ws)==before


def test_comparison_cannot_reveal_revoked_old_source_when_new_note_is_readable(research):
    from tests.test_workspace_notes import excerpt,body,create
    block,source=excerpt(research);draft=body();draft['payload']['note']['blocks'].append(block)
    first=create(research,draft)
    with research['repo'].transaction() as con:con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source['artifact']['artifact_id'],))
    clean=body('Only my own reminder remains.',work_id=first['document']['work_id'],
        previous_artifact_id=first['artifact']['artifact_id'],expected_draft_digest=first['document']['draft_digest'])
    second=create(research,clean)
    assert read(research,second).status_code==200
    before=counts(research)
    denied=read(research,second,compare_to=first['artifact']['artifact_id'])
    assert denied.status_code!=200,denied.get_json()
    result=research['api'].get(WORKS,headers=SHARED,query_string={'latest_only':'true','kind':'note'})
    assert result.status_code==200,result.get_json()
    assert [x['artifact']['artifact_id'] for x in result.get_json()['result']['items']]==[second['artifact']['artifact_id']]
    assert counts(research)==before


def test_resume_rechecks_new_revision_before_return_instead_of_returning_stale(research,monkeypatch):
    from lumenis.shared.reporting import saved_work
    first=save(research);original=saved_work.authorize_saved_work;triggered=[]
    def authorize(actor,scope,*,action,connection=None):
        result=original(actor,scope,action=action,connection=connection)
        # The public list's post-scan authorization is outside its first reader.
        if action=='read' and connection is None and not triggered:
            triggered.append('armed')
        elif action=='read' and connection is None and triggered==['armed']:
            triggered.append('changed')
            save(research,'concurrent next revision',first)
        return result
    monkeypatch.setattr(saved_work,'authorize_saved_work',authorize)
    response=research['api'].get(WORKS,headers=SHARED,query_string={'latest_only':'true'})
    # The HTTP adapter itself also authorizes: whichever read sees the change,
    # it must return only the new revision or an explicit conflict, never old.
    assert response.status_code in {200,409},response.get_json()
    if response.status_code==200:
        assert all(x['artifact']['artifact_id']!=first['artifact']['artifact_id'] for x in response.get_json()['result']['items'])


def test_latest_does_not_fall_back_to_readable_older_version_when_current_source_revoked(research):
    from tests.test_workspace_notes import excerpt,body,create
    first=create(research,body('Original user note'))
    block,source=excerpt(research)
    newer=body('Current with source',work_id=first['document']['work_id'],previous_artifact_id=first['artifact']['artifact_id'],expected_draft_digest=first['document']['draft_digest'])
    newer['payload']['note']['blocks'].append(block);create(research,newer)
    with research['repo'].transaction() as con:con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source['artifact']['artifact_id'],))
    result=research['api'].get(WORKS,headers=SHARED,query_string={'kind':'note','latest_only':'true'})
    assert result.status_code==200,result.get_json();view=result.get_json()['result']
    assert not view['items'] and view['verification_complete'] is False
    assert read(research,first).status_code==200
