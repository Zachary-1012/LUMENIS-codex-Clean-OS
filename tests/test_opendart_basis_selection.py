import json
import pytest
from lumenis.importer import financial
from lumenis.importer.financial_tables import parse_opendart_json, opendart_request_config
from tests.test_regional_financial_intake import dart
from tests.test_saved_document_workflow import workspace
from lumenis.system.security import permission


def mixed():
    rows = [json.loads(dart(fs_div=b,thstrm_amount=v))['list'][0] for b,v in [('OFS','20.25'),('CFS','10.125')]]
    return json.dumps({'status':'000','list':rows}).encode()

@pytest.mark.parametrize('basis,value,index',[('CFS','10.125',1),('OFS','20.25',0)])
def test_selection_filters_facts_candidates_keeps_source_indices(basis,value,index):
    raw=mixed(); r=parse_opendart_json(raw,fs_div=basis)
    assert len(r['facts'])==1 and r['facts'][0]['value']==value
    assert r['facts'][0]['dimensions']=={'financial_statement_basis':basis}
    assert r['facts'][0]['locator']['pointer']==f'/list/{index}/thstrm_amount'
    assert all(x['locator']['pointer'].startswith(f'/list/{index}/') for x in r['candidates'])
    assert r['selected_fs_div']==basis and r['excluded_basis_rows']==1
    assert mixed()==raw

def test_default_agrees_with_request_descriptor():
    config=opendart_request_config(corp_code='00123456',bsns_year='2025',reprt_code='11012')
    assert parse_opendart_json(mixed())['selected_fs_div']==config['selected_fs_div']=='CFS'
    assert 'fs_div' not in config['query']

@pytest.mark.parametrize('basis',[None,'','BOTH','cfs',True,[],{}])
def test_unknown_selection_fails_closed(basis):
    with pytest.raises(ValueError,match='FINANCIAL_DART_BASIS_INVALID'): parse_opendart_json(mixed(),fs_div=basis)

@pytest.mark.parametrize('basis',[None,'','UNKNOWN'])
def test_unknown_source_basis_still_fails_closed(basis):
    with pytest.raises(ValueError,match='FINANCIAL_DART_IDENTITY_INVALID'): parse_opendart_json(dart(fs_div=basis))

def test_no_matching_basis_honest_empty_and_error_status_retained():
    r=parse_opendart_json(dart(fs_div='OFS'),fs_div='CFS')
    assert r['facts']==[] and r['candidates']==[] and r['excluded_basis_rows']==1 and r['missing']
    r=parse_opendart_json(b'{"status":"013"}',fs_div='OFS')
    assert r['selected_fs_div']=='OFS' and r['missing'][0]['reason']=='NO_DATA'

@pytest.mark.parametrize('value,expected',[('—',None),('0','0'),('(10.25)','-10.25')])
def test_selected_values_remain_exact_and_unknown_distinct(value,expected):
    r=parse_opendart_json(dart(fs_div='OFS',thstrm_amount=value),fs_div='OFS')
    assert r['facts'][0]['value']==expected and r['facts'][0]['unit']=='KRW'


def test_owner_save_replay_conflict_revision_and_original_bytes(workspace,monkeypatch):
    w=workspace;monkeypatch.setattr(financial,'get_repository',lambda:w['repo'])
    path=w['root']/'financial.json';path.write_bytes(mixed())
    args=dict(actor=w['actor'],scope=w['scope'],provenance={'source_url':'https://opendart.fss.or.kr/fixture.json',
        'published_at':None,'captured_at':'2026-10-17T00:00:00Z','rights':'owner-approved',
        'content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'},'title':'Synthetic mixed-basis response'})
    resource=w['documents'].document_import_resource(str(path),**args)
    w['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='isolated-test')
    source=w['documents'].import_document(str(path),**args)
    opts=dict(actor=w['actor'],scope=w['scope'],format='opendart-json',fs_div='OFS')
    r=financial.analyze_financial_source(source['evidence_id'],**opts)
    assert r['facts'][0]['value']=='20.25' and r['selected_fs_div']=='OFS'
    assert financial.analyze_financial_source(source['evidence_id'],**{k:v for k,v in opts.items() if k!='fs_div'})['selected_fs_div']=='CFS'
    for invalid in (None, '', 'BOTH', True, [], {}):
        with pytest.raises(ValueError,match='FINANCIAL_DART_BASIS_INVALID'):
            financial.analyze_financial_source(source['evidence_id'],**dict(opts,fs_div=invalid))
    with pytest.raises(ValueError,match='FINANCIAL_DART_BASIS_FORMAT_INVALID'):
        financial.analyze_financial_source(source['evidence_id'],**dict(opts,format='sec-companyfacts'))
    a=financial.save_financial_analysis(source['evidence_id'],request_id='basis-request-001',**opts)
    assert financial.save_financial_analysis(source['evidence_id'],request_id='basis-request-001',**opts)['replayed']
    with pytest.raises(ValueError):
        financial.save_financial_analysis(source['evidence_id'],request_id='basis-request-001',**dict(opts,fs_div='CFS'))
    b=financial.save_financial_analysis(source['evidence_id'],request_id='basis-request-002',work_id=a['document']['work_id'],
        previous_artifact_id=a['artifact']['artifact_id'],**dict(opts,fs_div='CFS'))
    assert b['document']['version']==2
    assert w['documents'].reopen_imported_source(source['evidence_id'],actor=w['actor'],scope=w['scope'])['content']==mixed()

@pytest.mark.parametrize('save',[False,True])
def test_http_owner_forwards_basis_without_new_route(monkeypatch,save):
    import experience_runtime as runtime
    import lumenis_app_api
    body=dict(evidence_id='fixture',format='opendart-json',fs_div='OFS')
    if save: body['request_id']='basis-http-001'
    monkeypatch.setattr(lumenis_app_api,'_internal_pitch_body',lambda:body)
    monkeypatch.setattr(runtime,'_content_source_same_origin',lambda:True)
    monkeypatch.setattr(runtime,'_shared_work_actor_scope',lambda _:('fixture-actor',{'fixture':True}))
    monkeypatch.setattr(runtime,'_shared_work_response',lambda fn:fn())
    monkeypatch.setattr(financial,'save_financial_analysis' if save else 'analyze_financial_source',lambda **kw:kw)
    assert runtime._financial_material_response(save=save)['fs_div']=='OFS'
