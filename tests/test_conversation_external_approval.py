"""Real conversation SQLite + existing exact Gateway; synthetic identity/transport only."""
import json
import sqlite3
import pytest
from tests.test_user_api_consent_binding import runtime, select, transport

@pytest.fixture
def client(runtime, monkeypatch, tmp_path):
    app, api, gate, actor = runtime
    from lumenis.ai_hub import conversations as owner, routes
    path = tmp_path / 'conversations.sqlite3'
    monkeypatch.setenv('ZBC_DB_PATH', str(path))
    def connect():
        con = sqlite3.connect(path); con.row_factory = sqlite3.Row; return con
    monkeypatch.setattr(owner, '_connect', connect)
    with connect() as con:
        con.execute('BEGIN'); owner.ensure_schema(con)
    app.register_blueprint(routes.ai_bp, url_prefix='/v4')
    select(api)
    return app, api, gate, actor, path


def prepared(client, text='ordinary user question'):
    app, api, gate, actor, path=client
    row=api.post('/v4/ai/conversations',json={'title':'test'}).get_json()['conversation']
    root='/v4/ai/conversations/'+row['conversation_id']
    user=api.post(root+'/turns',json={'text':text,'idempotency_key':'user-1','expected_revision':row['revision']}).get_json()
    url=root+'/turns/'+user['turn']['turn_id']+'/respond'
    first=api.post(url,json={'idempotency_key':'preview','expected_revision':user['revision']})
    assert first.status_code==200,first.json
    result=first.json
    assert result['turn']['state']=='unavailable'
    assert result['turn']['content']['code']=='USER_API_APPROVAL_REQUIRED'
    p=result['approval_request']
    confirmation={'confirmed':True,'confirmation_id':p['confirmation_id'],'resource':p['resource']}
    args={'idempotency_key':'confirmed','expected_revision':result['revision'],'retry_confirmed':True,'external_approval':confirmation}
    return url,args,p,result


def test_exact_approval_single_send_and_idempotent_replay(client,monkeypatch):
    app,api,gate,actor,path=client
    url,args,p,first=prepared(client)
    calls=transport(monkeypatch)
    response=api.post(url,json=args)
    assert response.status_code==200,response.json
    assert response.json['turn']['state']=='completed',response.json
    assert len(calls)==1 and json.loads(calls[0].data)==p['request']
    replay=api.post(url,json=args)
    assert replay.json['idempotent_hit'] is True and len(calls)==1
    with sqlite3.connect(path) as con:
        stored=' '.join(x[0] for x in con.execute('SELECT content_json FROM ai_conversation_turns'))
    assert p['confirmation_id'] not in stored and 'synthetic-test-secret' not in stored
    # New attempt with already consumed consent cannot send twice.
    again={**args,'idempotency_key':'again','expected_revision':response.json['revision']}
    denied=api.post(url,json=again)
    assert denied.json['turn']['state']=='unavailable' and len(calls)==1


def test_missing_approval_never_sends_and_preview_key_cannot_change(client,monkeypatch):
    app,api,*_=client;url,args,p,first=prepared(client)
    calls=transport(monkeypatch)
    missing={k:v for k,v in args.items() if k!='external_approval'}
    preview=api.post(url,json=missing)
    assert preview.json['turn']['state']=='unavailable' and preview.json['approval_request']
    changed=api.post(url,json={**args,'idempotency_key':'preview'})
    assert changed.status_code==409 and calls==[]


@pytest.mark.parametrize('mutation',['actor','payload','model','withdrawn','cross_conversation','resource','confirmation'])
def test_confirmation_binding_mutations_fail_without_transport(client,monkeypatch,mutation):
    app,api,gate,actor,path=client;url,args,p,first=prepared(client)
    calls=transport(monkeypatch)
    if mutation=='actor': actor['id']=18
    elif mutation=='payload':
        with sqlite3.connect(path) as con:
            con.execute("UPDATE ai_conversation_turns SET content_json=? WHERE origin_kind='user_input'",(json.dumps({'text':'changed question','source_kind':'user_authored'}),))
    elif mutation=='model': select(api,model='new-model')
    elif mutation=='withdrawn':
        from lumenis.system.security import permission
        gate.revoke_permission(permission.PermissionLevel.ANALYZE)
    elif mutation=='cross_conversation':
        other_url,other_args,_,_=prepared(client)
        url=other_url;args={**other_args,'external_approval':args['external_approval']}
    elif mutation=='resource': args['external_approval']['resource']='different'
    elif mutation=='confirmation': args['external_approval']['confirmation_id']='different'
    result=api.post(url,json=args)
    assert result.status_code in (200,403),result.json
    if result.status_code==200: assert result.json['turn']['state'] in ('unavailable','failed'),result.json
    assert calls==[]


def test_confirmation_needs_explicit_retry_and_interrupt_rejects_approval(client,monkeypatch):
    app,api,*_=client;url,args,p,first=prepared(client)
    calls=transport(monkeypatch)
    result=api.post(url,json={**args,'retry_confirmed':False})
    assert result.status_code==400 and calls==[]
    result=api.post(url,json={**args,'operation':'interrupt','confirmed':True})
    assert result.status_code==400 and calls==[]
