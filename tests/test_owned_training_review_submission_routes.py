
"""Actual canonical review HTTP composition against disposable signed Evidence."""
import json
import sqlite3
import pytest
from lumenis.shared.learning import training_review
from lumenis.shared.evidence import store
from lumenis.system.security import permission as p
from tests.test_owned_training_review_resource_routes import route, counts, GLOBAL, URL
from tests.test_owned_training_review import strict_permission, review_db

SUBMIT = "/api/experience/owned-training/review-submissions"
EXPORT = "/api/experience/owned-training/review-exports"

def _confirmed(route):
    client, app, gate, body, path = route
    gate.grant_permission(p.PermissionLevel.COMMIT)
    gate.grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    preview = client.post(URL, headers=GLOBAL, json=body).get_json()
    return {"material":body,"confirm":True,"confirmed_resource":preview["resource"]}

def test_normal_confirm_submit_export_and_exact_retry(route):
    client, _, gate, _, path = route
    body=_confirmed(route);before=counts(path)
    first=client.post(SUBMIT,headers=GLOBAL,json=body)
    assert first.status_code==200,first.get_json()
    result=first.get_json()
    assert result['state']=='recorded' and not result['training_started']
    assert not result['execution_approval_issued']
    assert all(t.revoked for t in gate._approvals.values())
    second=client.post(SUBMIT,headers=GLOBAL,json=body)
    assert second.status_code==200 and second.get_json()['state']=='already_recorded'
    assert second.get_json()['review_evidence_ref']==result['review_evidence_ref']
    assert counts(path)==(before[0]+2,before[1])
    export=client.post(EXPORT,headers=GLOBAL,json={'review_evidence_refs':[result['review_evidence_ref']]})
    assert export.status_code==200,export.get_json()
    actual=export.get_json()['records'][0]
    assert actual['reviewer_approved_target']==body['material']['proposed_target']
    assert actual['source_evidence_refs']==body['material']['source_evidence_refs']
    assert actual['rights_ref']==result['rights_evidence_ref']
    assert actual['reviewer_approval_ref']==result['review_evidence_ref']
    assert export.get_json()['training_started'] is False

@pytest.mark.parametrize('mutation',['confirmation','target','scope','authority','extra_identity'])
def test_pending_changed_material_scope_or_authority_never_writes(route,mutation):
    client,_,gate,_,path=route;body=_confirmed(route);before=counts(path)
    headers=GLOBAL
    if mutation=='confirmation':body['confirm']=False
    elif mutation=='target':body['material']['proposed_target']+=' changed'
    elif mutation=='scope':headers={**GLOBAL,'X-Domain-Id':'BMP','X-Product-Id':'ZBMP'}
    elif mutation=='authority':gate.revoke_permission(p.PermissionLevel.HUMAN_APPROVAL)
    else:body['actor_id']=1
    assert client.post(SUBMIT,headers=headers,json=body).status_code in (400,403)
    assert counts(path)==before and all(t.revoked for t in gate._approvals.values())

def test_final_target_write_revocation_rolls_back_both_rows(route,monkeypatch):
    client,_,gate,_,path=route;body=_confirmed(route);before=counts(path)
    original=store.record_evidence
    def revoke(**kwargs):
        result=original(**kwargs)
        if kwargs.get('feature_id')=='OWNED_TRAINING_TARGET_REVIEW':
            for token in list(gate._approvals):gate.revoke_approval(token)
        return result
    monkeypatch.setattr(store,'record_evidence',revoke)
    response=client.post(SUBMIT,headers=GLOBAL,json=body)
    assert response.status_code==403,response.get_json()
    assert counts(path)==before and all(t.revoked for t in gate._approvals.values())

def test_late_export_scope_revocation_prevents_return_and_restore_is_exact(route,monkeypatch):
    from lumenis.shared.learning import training_cases
    client,_,gate,_,path=route;body=_confirmed(route)
    result=client.post(SUBMIT,headers=GLOBAL,json=body).get_json();before=counts(path)
    original=training_cases._record
    def revoke(*args,**kwargs):
        result=original(*args,**kwargs);gate.revoke_permission(p.PermissionLevel.VERIFY);return result
    monkeypatch.setattr(training_cases,'_record',revoke)
    response=client.post(EXPORT,headers=GLOBAL,json={'review_evidence_refs':[result['review_evidence_ref']]})
    assert response.status_code==403 and 'records' not in response.get_json()
    assert counts(path)==before
    monkeypatch.setattr(training_cases,'_record',original);gate.grant_permission(p.PermissionLevel.VERIFY)
    assert client.post(EXPORT,headers=GLOBAL,json={'review_evidence_refs':[result['review_evidence_ref']]}).status_code==200

@pytest.mark.parametrize('headers,remote',[
    ({'Origin':'https://example.invalid'},'127.0.0.1'),
    ({'X-Actor-ID':'1'},'127.0.0.1'), ({},'192.0.2.2'),
])
def test_confirmation_cannot_accept_remote_csrf_or_client_actor(route,headers,remote):
    client,_,gate,_,path=route;body=_confirmed(route);before=counts(path)
    response=client.post(SUBMIT,headers={**GLOBAL,**headers},json=body,environ_overrides={'REMOTE_ADDR':remote})
    assert response.status_code==401,response.get_json()
    assert counts(path)==before and all(t.revoked for t in gate._approvals.values())
