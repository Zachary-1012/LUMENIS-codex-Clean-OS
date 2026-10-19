import copy
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_independent_growth_real_app import real_app, headers, counts
from test_domain_report_shared_adoption import domain_report
URL='/api/experience/saved-work'


def setup_material(ws):
    from lumenis.auth.service import get_current_user
    from lumenis.importer.documents import locate_quote
    actor=get_current_user(read_only=True)
    ws={**ws,'actor':actor,'auth':{'Authorization':headers(201)['Authorization']}}
    report,rows,_=domain_report(ws)
    raw_scope=report['source_brief']['scope']
    scope={'domain_id':'cth','subject_id':raw_scope['subject_id'],'brand_focus_id':None,'global_scope':False}
    citation=locate_quote(rows[0]['evidence_id'],actor=actor,scope=scope,start=0,end=9)['citation']
    claims=[{'claim_id':'explicit-claim','text':'This invented assertion is not proved by this quotation.', 'citations':[citation]}]
    return ws,claims,rows


def verify(ws,claims,**extra):
    return ws['api'].post(URL,headers=headers(201),json={'verify_fact_wall_claims':claims,**extra})


def save(ws,verified,request_id='factwall-save-001'):
    return ws['api'].post(URL,headers=headers(201),json={'title':'Claim review','markdown':'Human draft, claims unverified.',
        'kind':'research','payload':{'fact_wall':verified['fact_wall']},'citations':verified['citations'],'request_id':request_id})


def test_exact_verify_is_read_only_then_explicit_save_reopen_export(real_app):
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,rows=setup_material(ws)
        before=counts(ws)
        result=verify(ws,claims);assert result.status_code==200,result.get_json()
        assert counts(ws)==before
        value=result.get_json()['result'];claim=value['fact_wall']['claims'][0]
        assert claim['claim_status']=='UNKNOWN' and claim['machine_semantic_assessment']=='NOT_PERFORMED'
        assert value['fact_wall']['claim_assessment_authority']=='HUMAN_ONLY'
        assert claim['source_checks'][0]['quote_binding']=='EXACT_SOURCE_TEXT'
        assert claim['source_checks'][0]['claim_relation']=='NOT_ASSESSED'
        result=save(ws,value);assert result.status_code==200,result.get_json()
        saved=result.get_json()['result'];aid=saved['artifact']['artifact_id']
    fresh=ws['app'].test_client()
    assert fresh.get(URL+'/'+aid,headers=headers(201)).status_code==200
    assert fresh.get(URL+'/'+aid+'/export?format=json',headers=headers(201)).status_code==200
    assert fresh.get(URL+'/'+aid,headers=headers(202)).status_code!=200
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(rows[0]['source_artifact_ref'],))
    assert fresh.get(URL+'/'+aid,headers=headers(201)).status_code!=200
    assert fresh.get(URL+'/'+aid+'/export?format=json',headers=headers(201)).status_code!=200


@pytest.mark.parametrize('bad',['mixed','quote','status','pin'])
def test_forged_claim_or_save_flags_cannot_bypass_original_owner(real_app,bad):
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,_=setup_material(ws);before=counts(ws)
        if bad=='mixed':
            result=verify(ws,claims,markdown='implicit save?')
        elif bad=='quote':
            claims[0]['citations'][0]['quote']='fabricated';result=verify(ws,claims)
        else:
            value=verify(ws,claims).get_json()['result']
            claim=value['fact_wall']['claims'][0]
            if bad=='status':claim['claim_status']='FACT'
            else:claim['source_checks'][0]['evidence_version']='forged-version'
            result=save(ws,value)
        assert result.status_code!=200,result.get_json()
        assert counts(ws)==before


def test_session_revocation_during_claim_save_rolls_back(real_app,monkeypatch):
    from lumenis.shared.reporting import saved_work
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,_=setup_material(ws);value=verify(ws,claims).get_json()['result'];before=counts(ws)
        stage=saved_work._stage_bytes
        def revoke(con,**kw):
            result=stage(con,**kw);con.execute('DELETE FROM v4_sessions WHERE user_id=201');return result
        monkeypatch.setattr(saved_work,'_stage_bytes',revoke)
        assert save(ws,value).status_code!=200
        assert counts(ws)==before


def test_human_judgment_stays_human_and_revision_uses_cas(real_app):
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,_=setup_material(ws)
        claims[0]['human_judgment']={'status':'SUPPORTED','note':'My explicit human assessment, not model verification.'}
        result=verify(ws,claims);assert result.status_code==200,result.get_json()
        value=result.get_json()['result'];claim=value['fact_wall']['claims'][0]
        assert claim['assessment_origin']=='EXPLICIT_HUMAN_JUDGMENT'
        assert claim['machine_semantic_assessment']=='NOT_PERFORMED'
        saved=save(ws,value).get_json()['result'];aid=saved['artifact']['artifact_id']
        edits=[{'pointer':'/markdown','expected':saved['document']['markdown'],'value':'Human review amended; no automated truth verdict.'}]
        payload={'request_id':'factwall-revision-001','expected_sha256':saved['artifact']['sha256'],'reason':'Clarify wording.','edits':edits}
        updated=ws['api'].post(URL+'/'+aid+'/revise',headers=headers(201),json=payload)
        assert updated.status_code==200,updated.get_json()
        new=updated.get_json()['result'];assert new['document']['version']==2
        assert new['document']['payload']['fact_wall']==value['fact_wall']
        stale={**payload,'request_id':'factwall-stale-revision'}
        assert ws['api'].post(URL+'/'+aid+'/revise',headers=headers(201),json=stale).status_code!=200
        read=ws['api'].get(URL+'/'+new['artifact']['artifact_id'],headers=headers(201))
        assert read.status_code==200,read.get_json()


def test_verify_cross_actor_and_anonymous_cannot_read_quote(real_app):
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,_=setup_material(ws);before=counts(ws)
        for h in [headers(202), {'X-Lumenis-Workspace-Scope':'{"scope_kind":"shared_workspace","version":1}'}]:
            response=ws['api'].post(URL,headers=h,json={'verify_fact_wall_claims':claims})
            assert response.status_code!=200,response.get_json()
            assert claims[0]['citations'][0]['quote'] not in response.get_data(as_text=True)
        assert counts(ws)==before


# Independent genuine source-withdrawal regression, original assertions.
@pytest.mark.parametrize('change',['deleted_original','deleted_evidence'])
def test_verify_source_revoked_during_source_checks_rejects_stale_verified_response(real_app,monkeypatch,change):
    from lumenis.shared.evidence import api
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,rows=setup_material(ws)
        check=api._fact_wall_source_check
        changed=[]
        def revoke(con,citation,context,actor):
            result=check(con,citation,context,actor)
            if not changed:
                changed.append(True)
                with ws['repo'].transaction() as write:
                    if change=='deleted_original':write.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(rows[0]['source_artifact_ref'],))
                    else:write.execute('DELETE FROM app_evidence_records WHERE id=?',(rows[0]['evidence_id'],))
            return result
        monkeypatch.setattr(api,'_fact_wall_source_check',revoke)
        response=verify(ws,claims)
        assert changed
        assert response.status_code!=200,response.get_json()



def test_removed_derived_canonical_does_not_erase_retained_original_reference(real_app):
    ws=real_app
    with ws['app'].test_request_context('/',headers=headers(201)):
        ws,claims,rows=setup_material(ws)
        with ws['repo'].transaction() as c:c.execute('DELETE FROM canonical_data WHERE source_id=?',(rows[0]['source_id'],))
        response=verify(ws,claims)
        assert response.status_code==200,response.get_json()
        c=response.get_json()['result']['fact_wall']['claims'][0]
        assert c['claim_status']=='UNKNOWN'
        assert c['source_checks'][0]['claim_relation']=='NOT_ASSESSED'
