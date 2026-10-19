import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research, BASE, SHARED

URL='/api/experience/saved-work'


def domain_report(ws, domain='CTH', count=1):
    import subject_registry
    from lumenis.importer import documents
    entity,_=subject_registry.add_subject({'domain_id':domain,'subject_type':'company' if domain=='CTH' else 'brand',
        'name_en':'Synthetic reverse adoption','name_zh':'合成反向采用'})
    scope={'domain_id':'cth' if domain=='CTH' else 'zbmp','global_scope':False,
        'subject_id':entity['subject_id'] if domain=='CTH' else None,
        'brand_focus_id':entity['brand_focus_id'] if domain=='BMP' else None}
    headers={**ws.get('auth',{}),'X-Domain-Id':domain,'X-Product-Id':domain,'X-Lumenis-Context-Mode':'FOCUS',
        ('X-Subject-ID' if domain=='CTH' else 'X-Brand-Focus-ID'):scope['subject_id'] or scope['brand_focus_id']}
    rows=[]
    for index in range(count):
        path=ws['root']/f'original-{index}.txt';path.write_text(f'Synthetic original source {index}: revenue 0. Unverified source statement.')
        args={'actor':ws['actor'],'scope':scope,'provenance':{'source_url':None,'published_at':None,
            'captured_at':'2026-10-18T00:00:00Z','rights':'owner-approved','rights_statement':'Synthetic owned test.',
            'title':'Original fixture','source_origin':{'kind':'approved-file','ref':'synthetic-original-'+str(index)},'intended_use':'research_reference'}}
        resource=documents.document_import_resource(str(path),**args)
        ws['gate'].grant_approval('data_import',resource=resource,granted_by='synthetic-owner')
        rows.append(documents.import_document(str(path),**args))
    response=ws['api'].post(BASE+'/generate',headers=headers,json={'source_ids':[r['source_id'] for r in rows],**({'business_question':'Inspect bounded source statements.'} if count<=8 else {})})
    assert response.status_code==200,response.get_json()
    return response.get_json()['result'], rows, headers


def command(ws, job, mode='prepare', request='adopt-domain-report-001', **extra):
    return ws['api'].post(URL,headers=ws.get('shared_headers',SHARED),json={'adopt_source_brief_job_id':job,'request_id':request,'mode':mode,**extra})


@pytest.mark.parametrize('domain',['CTH','BMP'])
def test_explicit_adoption_reopen_revision_and_revocation(research, domain):
    ws=research;report,rows,_=domain_report(ws,domain)
    prepared=command(ws,report['job_id']);assert prepared.status_code==200,prepared.get_json()
    resource=prepared.get_json()['result']['resource']
    assert command(ws,report['job_id'],'save').status_code!=200
    ws['gate'].grant_approval('data_export',resource='*',granted_by='synthetic-owner')
    assert command(ws,report['job_id'],'save').status_code!=200
    ws['gate'].grant_approval('data_export',resource=resource,granted_by='synthetic-owner')
    response=command(ws,report['job_id'],'save');assert response.status_code==200,response.get_json()
    saved=response.get_json()['result'];aid=saved['artifact']['artifact_id']
    assert saved['document']['payload']['domain_report_adoption']['source_count']==1
    assert saved['document']['context']['scope_kind']=='shared_workspace'
    assert command(ws,report['job_id'],'save').get_json()['result']['replayed']
    assert ws['api'].get(URL+'/'+aid,headers=SHARED).status_code==200
    revision=ws['api'].post(URL+'/'+aid+'/revise',headers=SHARED,json={'request_id':'adopt-revise-001',
        'expected_sha256':saved['artifact']['sha256'],'reason':'Add personal interpretation.',
        'edits':[{'pointer':'/markdown','expected':saved['document']['markdown'],'value':saved['document']['markdown']+'\nHuman note.'}]})
    assert revision.status_code==200,revision.get_json()
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM canonical_data WHERE source_id=?',(rows[0]['source_id'],))
    assert ws['api'].get(URL+'/'+aid,headers=SHARED).status_code!=200
    assert command(ws,report['job_id'],'save').status_code!=200


def test_mixed_command_and_binding_spoof_denied(research):
    ws=research;report,_,_=domain_report(ws)
    assert command(ws,report['job_id'],markdown='client replacement').status_code==400
    response=ws['api'].post(URL,headers=SHARED,json={'title':'spoof','markdown':'spoof','kind':'report',
        'payload':{'domain_report_adoption':{}},'citations':[],'request_id':'spoof-adoption-001'})
    assert response.status_code!=200


def test_ninth_undisplayed_source_is_still_guarded(research):
    ws=research;report,rows,_=domain_report(ws,count=9)
    prepared=command(ws,report['job_id']).get_json()['result']
    assert prepared['displayed_citations']==8 and prepared['guarded_source_count']==9
    ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='synthetic-owner')
    response=command(ws,report['job_id'],'save');assert response.status_code==200,response.get_json()
    saved=response.get_json()['result']
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM canonical_data WHERE source_id=?',(rows[8]['source_id'],))
    assert ws['api'].get(URL+'/'+saved['artifact']['artifact_id'],headers=SHARED).status_code!=200
    assert command(ws,report['job_id'],'save').status_code!=200


def test_commit_rechecks_every_source_and_rolls_back_artifact(research,monkeypatch):
    from lumenis.shared.reporting import saved_work
    ws=research;report,rows,_=domain_report(ws,count=9)
    prepared=command(ws,report['job_id']).get_json()['result']
    ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='synthetic-owner')
    with ws['repo'].connection() as con:
        before=con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0]
    original=saved_work._stage_bytes
    def invalidate(con,**kw):
        result=original(con,**kw)
        con.execute('DELETE FROM canonical_data WHERE source_id=?',(rows[8]['source_id'],))
        return result
    monkeypatch.setattr(saved_work,'_stage_bytes',invalidate)
    response=command(ws,report['job_id'],'save')
    assert response.status_code!=200
    with ws['repo'].connection() as con:
        assert con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0]==before


def test_replacement_report_hash_rejects_saved_adoption(research):
    ws=research;report,_,_=domain_report(ws)
    prepared=command(ws,report['job_id']).get_json()['result']
    ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='synthetic-owner')
    saved=command(ws,report['job_id'],'save').get_json()['result']
    with ws['repo'].transaction() as con:
        con.execute("UPDATE daily_reports SET artifact_hash=? WHERE report_id=?",('0'*64,report['job_id']))
    assert ws['api'].get(URL+'/'+saved['artifact']['artifact_id'],headers=SHARED).status_code!=200


from tests.test_independent_growth_real_app import real_app, headers as actor_headers, counts


def test_real_session_foreign_actor_revocation_export_and_fresh_client(real_app):
    from lumenis.auth.service import get_current_user
    ws=real_app
    with ws['app'].test_request_context('/',headers=actor_headers(201)):
        actor=get_current_user(read_only=True)
        assert actor['id']==201
        ws={**ws,'actor':actor,'auth':{'Authorization':actor_headers(201)['Authorization']},
            'shared_headers':actor_headers(201)}
        report,_,_=domain_report(ws)
        prepared=command(ws,report['job_id']);assert prepared.status_code==200,prepared.get_json()
        resource=prepared.get_json()['result']['resource']
        ws['gate'].grant_approval('data_export',resource=resource,granted_by='actor:201')
        result=command(ws,report['job_id'],'save');assert result.status_code==200,result.get_json()
        saved=result.get_json()['result'];aid=saved['artifact']['artifact_id']
    fresh=ws['app'].test_client()
    assert fresh.get(URL+'/'+aid,headers=actor_headers(201)).status_code==200
    before=counts(ws)
    assert fresh.get(URL+'/'+aid,headers=actor_headers(202)).status_code!=200
    assert command({**ws,'shared_headers':actor_headers(202)},report['job_id']).status_code!=200
    assert counts(ws)==before
    exported=fresh.get(URL+'/'+aid+'/export?format=json',headers=actor_headers(201))
    assert exported.status_code==200,exported.get_json()
    assert report['job_id'].encode() in exported.data
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM v4_sessions WHERE user_id=201')
    before=counts(ws)
    assert fresh.get(URL+'/'+aid,headers=actor_headers(201)).status_code!=200
    assert counts(ws)==before


def test_review_revision_never_restores_old_adoption(research):
    ws=research;report,_,scope_headers=domain_report(ws)
    prepared=command(ws,report['job_id']).get_json()['result']
    ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='synthetic-owner')
    saved=command(ws,report['job_id'],'save').get_json()['result']
    route=BASE+'/jobs/'+report['job_id']+'/hypotheses'
    current=ws['api'].get(route,headers=scope_headers).get_json()['result']
    hypothesis=current['analysis']['hypotheses'][0]
    for disposition in ['reject','reinstate']:
        result=ws['api'].post(route+'/review',headers=scope_headers,json={
            'request_id':'reverse-adopt-'+disposition,'expected_revision':current['expected_revision'],
            'hypothesis_id':hypothesis['hypothesis_id'],'disposition':disposition,
            'rationale':'Explicit bounded manual reassessment, no truth claim.',
            'evidence_refs':hypothesis['evidence_refs']})
        assert result.status_code==200,result.get_json()
        current=result.get_json()['result']
        assert ws['api'].get(URL+'/'+saved['artifact']['artifact_id'],headers=SHARED).status_code!=200
    renewed=command(ws,report['job_id'],request='adopt-new-review-001')
    assert renewed.status_code==200,renewed.get_json()
    assert renewed.get_json()['result']['resource']!=prepared['resource']
    assert command(ws,report['job_id'],'save',request='adopt-new-review-001').status_code!=200
    ws['gate'].grant_approval('data_export',resource=renewed.get_json()['result']['resource'],granted_by='synthetic-owner')
    assert command(ws,report['job_id'],'save',request='adopt-new-review-001').status_code==200


def test_approval_revoked_during_stage_rolls_back(research,monkeypatch):
    from lumenis.shared.reporting import saved_work
    ws=research;report,_,_=domain_report(ws)
    prepared=command(ws,report['job_id']).get_json()['result']
    token=ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='synthetic-owner')
    with ws['repo'].connection() as con:
        before=con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0]
    stage=saved_work._stage_bytes
    def revoke(con,**kwargs):
        result=stage(con,**kwargs)
        ws['gate'].revoke_approval(token)
        return result
    monkeypatch.setattr(saved_work,'_stage_bytes',revoke)
    assert command(ws,report['job_id'],'save').status_code!=200
    with ws['repo'].connection() as con:
        assert con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0]==before


@pytest.mark.parametrize('field,value',[('mode',[]),('mode',{}),('request_id',None),('request_id',[]),('request_id',{}),('request_id','x'),('request_id','x'*129)])
def test_invalid_adoption_command_fails_before_source_read(research, monkeypatch, field, value):
    from lumenis.shared.reporting import source_brief_job
    def forbidden(*args,**kwargs):
        pytest.fail('Malformed command must not read reports or prepare approval')
    monkeypatch.setattr(source_brief_job,'_domain_report_adoption_material',forbidden)
    body={'adopt_source_brief_job_id':'job-unknown-001','request_id':'valid-request-001','mode':'prepare',field:value}
    result=research['api'].post(URL,headers=SHARED,json=body)
    assert result.status_code==400,result.get_json()


def test_read_rechecks_undisplayed_source_after_artifact_validation(research, monkeypatch):
    from lumenis.shared.reporting import saved_work
    ws=research;report,rows,_=domain_report(ws,count=9)
    prepared=command(ws,report['job_id']).get_json()['result']
    ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='synthetic-owner')
    saved=command(ws,report['job_id'],'save').get_json()['result'];aid=saved['artifact']['artifact_id']
    original_read=saved_work._read
    armed=[False]
    def read(*args,**kw):
        result=original_read(*args,**kw)
        if args[1]==aid: armed[0]=True
        return result
    original_evidence=saved_work._verified_evidence
    def evidence(*args,**kw):
        result=original_evidence(*args,**kw)
        if armed[0]:
            armed[0]=False
            with ws['repo'].transaction() as con:
                con.execute('DELETE FROM canonical_data WHERE source_id=?',(rows[8]['source_id'],))
        return result
    monkeypatch.setattr(saved_work,'_read',read)
    monkeypatch.setattr(saved_work,'_verified_evidence',evidence)
    result=ws['api'].get(URL+'/'+aid,headers=SHARED)
    assert result.status_code!=200


# Independent staging revocation assertions retained.
@pytest.mark.parametrize('revocation',['session','role'])
def test_real_actor_revoked_after_staging_rolls_back(real_app,monkeypatch,revocation):
    from lumenis.auth.service import get_current_user
    from lumenis.shared.reporting import saved_work
    ws=real_app
    with ws['app'].test_request_context('/',headers=actor_headers(201)):
        actor=get_current_user(read_only=True)
        ws={**ws,'actor':actor,'auth':{'Authorization':actor_headers(201)['Authorization']},'shared_headers':actor_headers(201)}
        report,_,_=domain_report(ws)
        prepared=command(ws,report['job_id']).get_json()['result']
        ws['gate'].grant_approval('data_export',resource=prepared['resource'],granted_by='actor:201')
        before=ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]
        stage=saved_work._stage_bytes
        def revoke(con,**kw):
            result=stage(con,**kw)
            if revocation=='session':con.execute('DELETE FROM v4_sessions WHERE user_id=201')
            else:con.execute("UPDATE v4_users SET role='user' WHERE id=201")
            return result
        monkeypatch.setattr(saved_work,'_stage_bytes',revoke)
        response=command(ws,report['job_id'],'save')
        assert response.status_code!=200,response.get_json()
        assert ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]==before


def test_auth_reader_uses_callers_transaction_without_closing_it(real_app):
    from lumenis.auth.service import get_current_user
    ws=real_app
    with ws['app'].test_request_context('/',headers=actor_headers(201)):
        with ws['repo'].transaction() as con:
            assert get_current_user(read_only=True,connection=con)['id']==201
            con.execute('DELETE FROM v4_sessions WHERE user_id=201')
            assert get_current_user(read_only=True,connection=con) is None
            assert con.execute('SELECT 1').fetchone()[0]==1
        assert get_current_user(read_only=True) is None


def test_auth_external_connection_cannot_request_mutating_mode(real_app):
    from lumenis.auth.service import get_current_user
    ws=real_app
    with ws['app'].test_request_context('/',headers=actor_headers(201)):
        with ws['repo'].transaction() as con:
            with pytest.raises(ValueError,match='READ_ONLY_REQUIRED'):
                get_current_user(connection=con)
            assert con.execute('SELECT 1').fetchone()[0]==1
