"""Synthetic HTTP acquisition, real original owners and ordinary purpose consent."""
import json

from tests.test_collector_public_original import collector_case, test_manual_public_response_has_reopenable_exact_original as _seed_public_original


def test_public_source_purpose_consent_research_citations_versions_and_revocation(collector_case,monkeypatch,tmp_path):
    import shared_artifacts
    import intelligence_library_api as library
    from lumenis.importer import documents
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.evidence import store
    from lumenis.system.security import permission
    case=collector_case
    repository=DatabaseRepository(str(case['db_path']))
    for module in (library,documents,saved_work,shared_artifacts,store):
        monkeypatch.setattr(module,'get_repository',lambda:repository)
    case['client'].application.register_blueprint(library.intelligence_library_bp)
    _seed_public_original(case,monkeypatch,tmp_path)
    with repository.connection(read_only=True,wal=False) as con:
        row=dict(con.execute("SELECT * FROM app_evidence_records WHERE feature_id='COLLECTED_SOURCE'").fetchone())
    metadata=json.loads(row['collection_metadata']);evidence_id=row['id']
    endpoint=f'/api/intelligence/library/public-sources/{evidence_id}/source-use'
    declaration={'rights':'public-reference-only','statement':'Explicit isolated declaration for research and brief quotation.'}
    def use(purpose,mode='prepare',**extra):
        return case['client'].post(endpoint,headers=case['focus_headers'],json={
            'mode':mode,'purpose':purpose,'rights_declaration':declaration,**extra})
    def grant(purpose):
        response=use(purpose);assert response.status_code==200,response.get_json()
        prepared=response.get_json()['result'];assert not prepared['source_use_granted']
        confirmed=use(purpose,'confirm',confirmed=True,confirmed_resource=prepared['resource'])
        assert confirmed.status_code==200,confirmed.get_json()
        assert confirmed.get_json()['result']['source_use_granted']
        return prepared
    with case['client'].application.test_request_context('/',headers={**case['focus_headers'],'Host':'localhost'},
            environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
        actor=permission.resolve_local_workspace_principal(module='reports',action='write')
        context=saved_work.authorize(actor,case['scope'],action='read')
        with repository.connection(read_only=True,wal=False) as con:
            try:
                library.verified_research_source(con,evidence_id,actor=actor,context=context)
            except saved_work.SavedWorkError as exc:
                assert str(exc)=='PUBLIC_SOURCE_USE_APPROVAL_REQUIRED'
            else:
                raise AssertionError('Collection approval cannot grant public SourceUse')
    research=grant('research_reference')
    with case['client'].application.test_request_context('/',headers={**case['focus_headers'],'Host':'localhost'},
            environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
        actor=permission.resolve_local_workspace_principal(module='reports',action='write')
        context=saved_work.authorize(actor,case['scope'],action='read')
        with repository.connection(read_only=True,wal=False) as con:
            source=library.verified_research_source(con,evidence_id,actor=actor,context=context)
            assert source['rights']=='UNKNOWN' and source['truth_kind']=='source_reference'
            try:
                documents.locate_quote(evidence_id,actor=actor,scope=case['scope'],start=0,end=20)
            except saved_work.SavedWorkError as exc:
                assert str(exc)=='PUBLIC_SOURCE_USE_APPROVAL_REQUIRED'
            else:
                raise AssertionError('Research purpose cannot grant quote purpose')
    quote_grant=grant('quote_reference')
    quote=source['text'][:40]
    body={'title':'Research with preserved public original','markdown':'Source statement: '+quote,
          'kind':'research','payload':{'question':'What does this official page actually state?'},
          'citations':[{'evidence_id':evidence_id,'start':0,'end':len(quote),'quote':quote}],
          'request_id':'public-research-save-0001'}
    works='/api/experience/saved-work'
    response=case['client'].post(works,headers=case['focus_headers'],json=body)
    assert response.status_code==200,response.get_json()
    first=response.get_json()['result'];ref=first['artifact']['artifact_id']
    revised=case['client'].post(works+'/'+ref+'/revise',headers=case['focus_headers'],json={
        'request_id':'public-research-revise-0002','expected_sha256':first['artifact']['sha256'],
        'reason':'Keep the source limitation visible','edits':[{'pointer':'/payload/question',
            'expected':body['payload']['question'],'value':'Which page statements still need independent corroboration?'}]})
    assert revised.status_code==200,revised.get_json()
    second=revised.get_json()['result'];assert second['document']['version']==2
    current=works+'/'+second['artifact']['artifact_id']
    assert case['client'].get(current,headers=case['focus_headers']).status_code==200
    assert case['client'].get(works+'/'+ref,headers=case['focus_headers']).status_code==200
    assert case['client'].get(current+'/export?format=md',headers=case['focus_headers']).status_code==200
    revoked=use('quote_reference','revoke',confirmed=True,
        **{key:quote_grant[key] for key in ('source_fingerprint','body_sha256','source_version')})
    assert revoked.status_code==200,revoked.get_json()
    assert case['client'].get(current,headers=case['focus_headers']).status_code!=200
    assert case['client'].get(current+'/export?format=md',headers=case['focus_headers']).status_code!=200
    grant('quote_reference')
    assert case['client'].get(current,headers=case['focus_headers']).status_code==200
    # Purpose approval never rewrites or replaces the original Source Evidence.
    with repository.connection(read_only=True,wal=False) as con:
        after=dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(evidence_id,)).fetchone())
    assert after==row and metadata['provenance']['rights']['status']=='UNREVIEWED'
    assert research['source_fingerprint']==quote_grant['source_fingerprint']
