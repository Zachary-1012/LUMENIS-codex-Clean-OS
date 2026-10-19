"""HTTP binding with real local session, importer, source, evaluation and Evidence."""
import ast
import re
import uuid
from pathlib import Path
import pytest
from flask import request, jsonify
from tests.test_growth_learning_exchange import workspace, journey
from lumenis.shared.learning import contribution as owner
from lumenis.system.security import permission as p

URL = '/api/experience/reports/source-brief/learning'

@pytest.fixture
def http(journey, monkeypatch):
    import experience_runtime
    import lumenis.auth.service
    from lumenis.system import security
    j = journey
    monkeypatch.setattr(lumenis.auth.service, 'get_current_user', lambda: None)
    monkeypatch.setattr(security, 'get_permission_gate', lambda: j['gate'])
    app = j['app']
    app.register_blueprint(experience_runtime.experience_bp)
    tree = ast.parse(Path('app.py').read_text(encoding='utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'_pg_resolve_operation_type', '_permission_gate_write_check'}]
    for n in nodes: n.decorator_list = []
    ns = dict(request=request, jsonify=jsonify, re=re, OperationType=p.OperationType,
              _PG_WRITE_METHODS={'POST','PUT','PATCH','DELETE'}, _PG_BYPASS_PATHS=set(), _pg=j['gate'])
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'app.py','exec'), ns)
    app.before_request(ns['_permission_gate_write_check'])
    headers = {'X-Domain-Id':'CTH','X-Product-Id':'CTH','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':j['common']['expected_scope']['subject_id']}
    return j, app.test_client(), headers


def post(http, obj, action, *, approve=True):
    j, api, headers = http
    if approve:
        op = p.OperationType.DATA_IMPORT if action=='receive_local' else p.OperationType.CONFIG_MODIFY
        j['gate'].grant_approval(op.value,resource=owner.approval_resource(obj['id'],action,obj['revision']),granted_by=j['common']['actor_id'])
    body = dict(expected_revision=obj['revision'],submission_id=str(uuid.uuid4()))
    if obj['kind']=='candidate': body['notes']='Source-limited human review.'
    return api.post(f"{URL}/{'candidates' if obj['kind']=='candidate' else 'outbox'}/{obj['id']}/{action}",headers=headers,json=body)


def test_http_local_session_complete_chain_and_reopen(http):
    j,api,h=http
    created=api.post(URL+'/candidates',headers=h,json=dict(job_id=j['report']['job_id'],review_id=j['review']['review_id'],submission_id=str(uuid.uuid4())))
    assert created.status_code==200,created.get_json()
    obj=created.get_json()['result']
    for action in ('review','validate','adopt','withdraw','restore','validate'):
        r=post(http,obj,action)
        assert r.status_code==200,r.get_json()
        obj=r.get_json()['result']
    r=api.post(f"{URL}/candidates/{obj['id']}/enqueue",headers=h,json=dict(expected_revision=obj['revision'],submission_id=str(uuid.uuid4()),receiver=owner.LOCAL_REPO))
    assert r.status_code==200,r.get_json()
    out=r.get_json()['result']
    for action in ('stage','receive_local'):
        r=post(http,out,action)
        assert r.status_code==200,r.get_json()
        out=r.get_json()['result']
    assert out['transport']=='ACKNOWLEDGED' and not out['remote_delivery_proven']
    assert j['app'].test_client().get(f"{URL}/outbox/{out['id']}",headers=h).get_json()['result']==out


def test_http_scope_spoof_approval_and_public_receipt_denied(http):
    j,api,h=http
    obj=j['candidate']
    assert post(http,obj,'review',approve=False).status_code!=200
    cross={**h,'X-Lumenis-Context-Mode':'GLOBAL_ALL'}
    assert api.get(f"{URL}/candidates/{obj['id']}",headers=cross).status_code!=200
    payload=dict(job_id=j['report']['job_id'],review_id=j['review']['review_id'],submission_id=str(uuid.uuid4()),actor_id='other')
    assert api.post(URL+'/candidates',headers=h,json=payload).status_code!=200
    assert api.post(f"{URL}/outbox/{obj['id']}/receipt",headers=h,json={'receipt_evidence_ref':'forged'}).status_code!=200
    j['app'].config['LUMENIS_OPEN_WORKSPACE']=False
    assert api.get(f"{URL}/candidates/{obj['id']}",headers=h).status_code!=200


def test_http_cas_and_current_source_revocation(http):
    j,api,h=http
    obj=j['candidate']
    first=post(http,obj,'review')
    assert first.status_code==200,first.get_json()
    stale=post(http,obj,'review')
    assert stale.status_code!=200
    assert api.get(URL+'/candidates',headers=h).status_code==200
    with j['repo'].transaction() as con:
        con.execute('DELETE FROM canonical_data WHERE source_id=?',(j['source']['source_id'],))
    assert api.get(f"{URL}/candidates/{obj['id']}",headers=h).status_code!=200
    assert post(http,first.get_json()['result'],'validate').status_code!=200

from tests.test_independent_growth_real_app import real_app, headers, private_source, BASE


def test_real_authenticated_shared_session_learning_receiver_and_cross_actor(real_app):
    ws=real_app
    ws['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    api=ws['api']; h=headers(201)
    source=private_source(ws)
    r=api.post(BASE+'/generate',headers=h,json={'source_ids':[source]})
    assert r.status_code==200,r.get_json()
    job=r.get_json()['result']['job_id']
    r=api.post(BASE+'/jobs/'+job+'/reviews',headers=h,json=dict(submission_id=str(uuid.uuid4()),decision='request_changes',notes='Keep uncertainty explicit.'))
    assert r.status_code==200,r.get_json()
    review=r.get_json()['review']['review_id']
    r=api.post(URL+'/candidates',headers=h,json=dict(job_id=job,review_id=review,submission_id=str(uuid.uuid4())))
    assert r.status_code==200,r.get_json()
    candidate=r.get_json()['result']
    assert api.get(f"{URL}/candidates/{candidate['id']}",headers=headers(202)).status_code!=200
    pair=({**ws,'common':{'actor_id':'actor:201'}},api,h)
    for action in ('review','validate','adopt','withdraw','restore','validate'):
        r=post(pair,candidate,action)
        assert r.status_code==200,r.get_json()
        candidate=r.get_json()['result']
    r=api.post(f"{URL}/candidates/{candidate['id']}/enqueue",headers=h,json=dict(expected_revision=candidate['revision'],submission_id=str(uuid.uuid4()),receiver=owner.LOCAL_REPO))
    assert r.status_code==200,r.get_json()
    out=r.get_json()['result']
    for action in ('stage','receive_local'):
        r=post(pair,out,action)
        assert r.status_code==200,r.get_json()
        out=r.get_json()['result']
    assert out['transport']=='ACKNOWLEDGED' and not out['remote_delivery_proven']
    assert ws['app'].test_client().get(f"{URL}/outbox/{out['id']}",headers=h).get_json()['result']==out
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM v4_sessions WHERE user_id=201')
    assert api.get(f"{URL}/outbox/{out['id']}",headers=h).status_code!=200
