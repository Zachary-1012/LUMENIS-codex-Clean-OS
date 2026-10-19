"""Existing SavedWork note lifecycle; real SQLite/Artifact/Permission, no AI."""
import copy
import hashlib
import uuid
import pytest
from tests.test_saved_document_workflow import workspace, _source
from tests.test_shared_work_owner_routes import route_workspace, WORKS
from tests.test_growth_research_shared import research, SHARED, upload


def body(text='Remember to check the totals.', **extra):
    return dict(title='Workspace note', markdown='client preview is not authoritative', kind='note',
        payload={'note':{'schema':'lumenis.workspace-note/v1','blocks':[{'id':'b1','type':'user_text','text':text}]}},
        citations=[],request_id='note-'+uuid.uuid4().hex,**extra)


def post(ws,data):
    return ws['api'].post(WORKS,headers=SHARED,json=data)


def create(ws,data=None):
    result=post(ws,data or body());assert result.status_code==200,result.get_json()
    return result.get_json()['result']


def excerpt(ws):
    aid=upload(ws)
    item=ws['api'].get(WORKS+'/'+aid,headers=SHARED).get_json()['result']
    text=item['document']['markdown']
    return {'id':'q1','type':'quoted_excerpt','text':text,'source':{'type':'saved_work','artifact_id':aid,
        'sha256':item['artifact']['sha256'],'version':item['document']['version'],'start':0,'end':len(text)}},item


def test_save_reopen_search_revision_undo_export_and_new_client(research):
    ws=research;draft=body();first=create(ws,draft);ref=first['artifact']['artifact_id'];doc=first['document']
    assert doc['kind']=='note' and 'not verified facts' in doc['markdown']
    assert post(ws,draft).get_json()['result']['replayed'] is True
    def revise(item,old,new,rid):
        return ws['api'].post(WORKS+'/'+item['artifact']['artifact_id']+'/revise',headers=SHARED,json={
            'request_id':rid,'expected_sha256':item['artifact']['sha256'],'reason':'Explicit user edit/undo',
            'edits':[{'pointer':'/payload/note/blocks/0/text','expected':old,'value':new}]})
    changed=revise(first,'Remember to check the totals.','Call the supplier.','note-revise-001')
    assert changed.status_code==200,changed.get_json()
    second=changed.get_json()['result'];assert second['document']['version']==2
    assert revise(first,'Remember to check the totals.','Stale overwrite','note-stale-001').status_code==409
    undone=revise(second,'Call the supplier.','Remember to check the totals.','note-undo-001')
    assert undone.status_code==200,undone.get_json();latest=undone.get_json()['result']
    assert latest['document']['version']==3
    client=ws['app'].test_client()
    reopened=client.get(WORKS+'/'+latest['artifact']['artifact_id'],headers=SHARED)
    assert reopened.status_code==200 and reopened.get_json()['result']['document']['payload']['note']==doc['payload']['note']
    found=client.get(WORKS,headers=SHARED,query_string={'kind':'note','query':'supplier'})
    assert found.status_code==200 and found.get_json()['result']['items']
    for fmt in ['json','md','txt','docx','pdf','xlsx']:
        exported=client.get(WORKS+'/'+latest['artifact']['artifact_id']+'/export',headers=SHARED,query_string={'format':fmt})
        assert exported.status_code==200,exported.get_json()
        assert hashlib.sha256(exported.data).hexdigest()==exported.headers['X-Content-SHA256']
    assert client.get(WORKS+'/'+ref,headers=SHARED).status_code==200


def test_excerpt_and_summary_keep_user_input_and_live_source(research):
    quoted,source=excerpt(research);draft=body();draft['payload']['note']['blocks'] += [quoted,
        {'id':'s1','type':'derived_summary','text':'A user-supplied AI summary remains unverified.','input_block_ids':['b1','q1']}]
    item=create(research,draft);md=item['document']['markdown']
    assert 'Remember to check' in md and 'Source excerpt' in md and 'AI summary · user-supplied, unverified' in md
    with research['repo'].transaction() as con:
        con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source['artifact']['artifact_id'],))
    assert research['api'].get(WORKS+'/'+item['artifact']['artifact_id'],headers=SHARED).status_code!=200
    assert research['api'].get(WORKS+'/'+item['artifact']['artifact_id']+'/export',headers=SHARED).status_code!=200
    assert post(research,draft).status_code!=200


@pytest.mark.parametrize('bad',['hash','quote','version','scope','summary','type','recursive'])
def test_forged_or_invalid_note_rejected_without_write(research,bad):
    block,source=excerpt(research);draft=body();draft['payload']['note']['blocks'].append(block)
    if bad=='hash':block['source']['sha256']='0'*64
    if bad=='quote':block['text']='invented quote'
    if bad=='version':block['source']['version']=99
    if bad=='scope':block['source']['scope']={'scope_kind':'shared_workspace','version':1}
    if bad=='summary':draft['payload']['note']['blocks'].append({'id':'s','type':'derived_summary','text':'fake','input_block_ids':['missing']})
    if bad=='type':block['type']='verified_fact'
    if bad=='recursive':
        other=create(research);block['source'].update(artifact_id=other['artifact']['artifact_id'],sha256=other['artifact']['sha256'])
    with research['repo'].connection(read_only=True,wal=False) as con:before=con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]
    response=post(research,draft);assert response.status_code in {400,403,409},response.get_json()
    with research['repo'].connection(read_only=True,wal=False) as con:assert con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]==before


def test_source_new_version_invalidates_current_note_but_keeps_source_history(research):
    quoted,source=excerpt(research);draft=body();draft['payload']['note']['blocks'].append(quoted);note=create(research,draft)
    doc=source['document'];updated={k:copy.deepcopy(doc[k]) for k in ('title','markdown','kind','payload','citations')}
    updated.update(request_id='source-new-version',work_id=doc['work_id'],previous_artifact_id=source['artifact']['artifact_id'],expected_draft_digest=doc['draft_digest'])
    response=post(research,updated);assert response.status_code==200,response.get_json()
    assert research['api'].get(WORKS+'/'+note['artifact']['artifact_id'],headers=SHARED).status_code!=200
    assert research['api'].get(WORKS+'/'+source['artifact']['artifact_id'],headers=SHARED).status_code==200
    current=response.get_json()['result'];quoted['source'].update(artifact_id=current['artifact']['artifact_id'],sha256=current['artifact']['sha256'],version=2)
    draft['request_id']='new-note-explicit-rebind';assert post(research,draft).status_code==200

from tests.test_independent_growth_real_app import real_app, headers, counts

@pytest.mark.parametrize('change',['session','role','inactive'])
def test_actual_session_owner_scope_revocation_and_no_implicit_tasks(real_app,change):
    ws=real_app;before=counts(ws)
    assert ws['api'].post(WORKS,headers=SHARED,json=body()).status_code in {401,403}
    result=ws['api'].post(WORKS,headers=headers(201),json=body())
    assert result.status_code==200,result.get_json();ref=result.get_json()['result']['artifact']['artifact_id']
    after=counts(ws)
    assert after['lumenis_shared_artifacts']==before['lumenis_shared_artifacts']+1
    assert all(after[k]==before[k] for k in ['daily_reports','ai_task','evaluation_records'])
    assert ws['api'].get(WORKS+'/'+ref,headers=headers(201)).status_code==200
    assert ws['api'].get(WORKS+'/'+ref,headers=headers(202)).status_code in {400,401,403,404}
    foreign=ws['api'].get(WORKS,headers=headers(202),query_string={'kind':'note'})
    assert foreign.status_code==200 and not foreign.get_json()['result']['items']
    from tests.test_source_brief_job_routes import GLOBAL
    assert ws['api'].get(WORKS+'/'+ref,headers={**GLOBAL,'Authorization':headers(201)['Authorization']}).status_code!=200
    assert counts(ws)==after
    with ws['repo'].transaction() as con:
        if change=='session':con.execute('DELETE FROM v4_sessions WHERE user_id=201')
        elif change=='role':con.execute("UPDATE v4_users SET role='user' WHERE id=201")
        else:con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
    assert ws['app'].test_client().get(WORKS+'/'+ref,headers=headers(201)).status_code in {401,403}
    assert counts(ws)==after


def test_note_source_deleted_inside_commit_callback_rolls_back_note(research):
    quoted,source=excerpt(research);draft=body();draft['payload']['note']['blocks'].append(quoted)
    with research['repo'].connection(read_only=True,wal=False) as con:before=con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]
    def delete_source(con,*args):con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source['artifact']['artifact_id'],))
    from lumenis.shared.reporting import saved_work
    with pytest.raises(saved_work.SavedWorkError):
        saved_work.save_work(**draft,actor=research['actor'],scope={'scope_kind':'shared_workspace','version':1},before_commit=delete_source)
    with research['repo'].connection(read_only=True,wal=False) as con:assert con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]==before


def test_actual_domain_evidence_excerpt_is_bound_to_original_bytes(workspace):
    ws=workspace;_,_,source=_source(ws)
    with ws['repo'].connection(read_only=True,wal=False) as con:
        evidence=ws['work']._verified_evidence(con,source['evidence_id'],ws['work'].authorize_saved_work(ws['actor'],ws['scope'],action='read'),ws['actor'])
    quote='Original source line';draft=body();draft['citations']=[{'evidence_id':source['evidence_id'],'start':0,'end':len(quote),'quote':quote}]
    draft['payload']['note']['blocks'].append({'id':'q1','type':'quoted_excerpt','text':quote,'source':{
        'type':'evidence','citation_index':0,'version':evidence['version'],'sha256':evidence['content_hash']}})
    item=ws['work'].save_work(**draft,actor=ws['actor'],scope=ws['scope'])
    assert item['document']['citations'][0]['quote']==quote
    with ws['repo'].transaction() as con:con.execute('DELETE FROM app_evidence_records WHERE id=?',(source['evidence_id'],))
    with pytest.raises(ws['work'].SavedWorkError):ws['work'].reopen_work(item['artifact']['artifact_id'],actor=ws['actor'],scope=ws['scope'])


def test_restart_reopens_committed_note_without_memory_or_ai(research):
    import subprocess,sys,json
    note=create(research);aid=note['artifact']['artifact_id']
    program='''import sys,json
sys.path[:0]=json.loads(sys.argv[1])
from flask import Flask
from lumenis.system.security import permission
from lumenis.shared.reporting import saved_work
app=Flask(__name__);app.config['LUMENIS_OPEN_WORKSPACE']=True
permission.get_permission_gate().grant_permission(permission.PermissionLevel.COMMIT)
with app.test_request_context('/',headers={'Host':'localhost'},environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
 actor=permission.resolve_local_workspace_principal(module='reports',action='read')
 item=saved_work.reopen_work(sys.argv[2],actor=actor,scope={'scope_kind':'shared_workspace','version':1})
 print(json.dumps({'version':item['document']['version'],'note':item['document']['payload']['note']}))
'''
    process=subprocess.run([sys.executable,'-c',program,json.dumps(sys.path),aid],capture_output=True,text=True,timeout=30)
    assert process.returncode==0,process.stdout+process.stderr
    actual=json.loads(process.stdout.strip().splitlines()[-1])
    assert actual=={'version':1,'note':note['document']['payload']['note']}


def test_concurrent_note_revisions_exactly_one_commits(research):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    first=create(research);barrier=Barrier(2)
    def save(index):
        with research['app'].test_request_context('/',headers={'Host':'localhost'},environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
            from lumenis.system.security import permission
            from lumenis.shared.reporting import saved_work
            actor=permission.resolve_local_workspace_principal(module='reports',action='write')
            barrier.wait()
            try:
                return saved_work.revise_work(first['artifact']['artifact_id'],actor=actor,scope={'scope_kind':'shared_workspace','version':1},
                    request_id='note-concurrent-'+str(index),expected_sha256=first['artifact']['sha256'],reason='Explicit concurrent edit',
                    edits=[{'pointer':'/payload/note/blocks/0/text','expected':'Remember to check the totals.','value':'Edit '+str(index)}])
            except saved_work.SavedWorkError as exc:return str(exc)
    with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(save,[1,2]))
    assert len([r for r in results if isinstance(r,dict)])==1,results
    assert [r for r in results if isinstance(r,str)]==['WORK_REVISION_CONFLICT']
