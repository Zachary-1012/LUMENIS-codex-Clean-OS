"""Synthetic contract tests, never reported as real financial time series."""
import copy
import json
import pytest
from tests.test_saved_document_workflow import workspace
from lumenis.importer import financial
from lumenis.system.security import permission


@pytest.fixture(autouse=True)
def isolated_document_limiter(monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    limiter = AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False)
    monkeypatch.setattr(PublicHttpAdapter, '_document_limiter', limiter)


def sec():
    def value(val, start='2024-01-01', end='2024-03-31', filed='2024-05-01', accn='0000000001-24-000001'):
        return dict(val=val,start=start,end=end,filed=filed,accn=accn,form='10-Q')
    return {'cik':1,'entityName':'Synthetic Holding Inc.', 'facts':{'us-gaap':{
        'AdvertisingExpense':{'units':{'USD':[value(10),value(12,filed='2024-06-01',accn='0000000001-24-000002'),
            value(25,end='2024-06-30',filed='2024-08-01')], 'EUR':[value(9)]}},
        'SellingGeneralAndAdministrativeExpense':{'units':{'USD':[value(40)]}},
        'Revenues':{'units':{'USD':[value(100)]}}}}}


def test_sec_units_cumulative_revisions_and_sga_are_not_collapsed():
    result=financial.parse_sec_json(json.dumps(sec()).encode())
    facts=result['facts']
    assert len(facts)==6
    assert {f['unit'] for f in facts}=={'USD','EUR'}
    assert facts[2]['period_kind']=='half_year'
    assert any(f['metric']=='selling_general_admin_expense' for f in facts)
    assert any(f['metric']=='marketing_expense' for f in result['missing'])
    entity=result['filing_entity']
    old=financial.select_quarterly_series(facts,metric='advertising_expense',unit='USD',filing_entity=entity,as_of='2024-05-31')
    new=financial.select_quarterly_series(facts,metric='advertising_expense',unit='USD',filing_entity=entity,as_of='2024-10-01')
    assert old['periods'][0]['value']=='10'
    assert new['periods'][0]['value']=='12'
    assert len(new['periods'])==1 and new['status']=='INSUFFICIENT'
    assert financial.select_quarterly_series(facts,metric='advertising_expense',unit='CNY',filing_entity=entity,as_of='2024-10-01')['periods']==[]


@pytest.mark.parametrize('change', [lambda d:d['facts']['us-gaap']['AdvertisingExpense']['units']['USD'][0].update(val=float('nan')),
    lambda d:d['facts']['us-gaap']['AdvertisingExpense']['units']['USD'][0].update(start='2025-01-01'),
    lambda d:d.update(cik='not-cik'), lambda d:d['facts']['us-gaap']['AdvertisingExpense']['units']['USD'][0].update(accn='missing')])
def test_invalid_sec(change):
    data=sec();change(data)
    with pytest.raises(ValueError):financial.parse_sec_json(json.dumps(data).encode())


def test_duplicate_json_keys_fail_closed():
    with pytest.raises(ValueError,match='DUPLICATE'):
        financial.parse_sec_json(b'{"cik":1,"cik":2}')


XML=b'''<xbrli:xbrl xmlns:ex="urn:synthetic" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us="http://fasb.org/us-gaap/2024" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="SEC-CIK">1</xbrli:identifier><xbrli:segment><xbrldi:explicitMember dimension="ex:Region">ex:North</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:unit id="u"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit><us:AdvertisingExpense contextRef="c" unitRef="u">12</us:AdvertisingExpense><us:Revenues contextRef="c" unitRef="u" xsi:nil="true"/></xbrli:xbrl>'''


def test_xbrl_dimensions_nil_and_entity_safety():
    result=financial.parse_xbrl_instance(XML,filing_id='fixture-1')
    assert result['facts'][0]['disclosure_scope']=='dimensioned'
    assert result['facts'][0]['dimensions']=={'{urn:synthetic}Region':'{urn:synthetic}North'}
    assert result['facts'][1]['value'] is None and result['facts'][1]['status']=='MISSING'
    with pytest.raises(ValueError,match='EXTERNAL_ENTITY'):
        financial.parse_xbrl_instance(b'<!DOCTYPE x [<!ENTITY ext SYSTEM "file:///etc/passwd">]>'+XML,filing_id='x')
    with pytest.raises(ValueError,match='CONTEXT_OR_UNIT'):
        financial.parse_xbrl_instance(XML.replace(b'unitRef="u"',b'unitRef="unknown"'),filing_id='x')


def annotation(text):
    return {'metric':'advertising_expense','value':12000000,'value_literal':'12','scale':1000000,
        'unit':'USD','period_start':'2024-01-01','period_end':'2024-12-31',
        'filing_entity':{'name':'Synthetic Holding Inc.','scheme':'SEC-CIK','identifier':'0000000001'},
        'filing_id':'fixture-2024','filed':'2025-02-01','form':'10-K','disclosure_scope':'filing_entity',
        'statement_basis':'notes; caller reviewed','start':0,'end':len(text)}


def test_disclosure_requires_retained_numeric_literal_and_scale():
    text='Advertising expense USD 12 million for 2024.'
    row=annotation(text)
    assert financial.parse_disclosures(text,[row])['facts'][0]['value']=='12000000'
    with pytest.raises(ValueError,match='VALUE_NOT_IN_SOURCE'):
        financial.parse_disclosures('No disclosed financial values.',[dict(row,end=28)])
    with pytest.raises(ValueError,match='SCALE_MISMATCH'):
        financial.parse_disclosures(text,[dict(row,value=14)])


def test_spend_proxy_range_and_missing():
    assert financial.spend_proxy()['status']=='MISSING'
    common=dict(period_start='2024-01-01',period_end='2024-03-31',channel='search',entity='synthetic')
    rate=dict(common,lower=10,upper=20,currency='USD',basis='CPM',source_ref='evidence:1')
    exposure=dict(common,value=10000,basis='impressions',source_ref='evidence:2')
    probability=dict(lower=.5,upper=.8,source_ref='evidence:3')
    assert financial.spend_proxy(rate=rate,exposure=exposure,probability=probability)['interval']==['50.0','160.0']
    with pytest.raises(ValueError,match='MEASURE_MISMATCH'):
        financial.spend_proxy(rate=rate,exposure=dict(exposure,basis='clicks'),probability=probability)
    with pytest.raises(ValueError,match='SCOPE_MISMATCH'):
        financial.spend_proxy(rate=rate,exposure=dict(exposure,entity='subsidiary'),probability=probability)


def test_existing_owner_save_replay_revise_search_and_restart(workspace, monkeypatch):
    monkeypatch.setattr(financial,'get_repository',lambda:workspace['repo'])
    path=workspace['root']/'synthetic-sec.json'; path.write_text(json.dumps(sec()))
    args=dict(actor=workspace['actor'],scope=workspace['scope'],provenance={
        'source_url':'https://www.sec.gov/Archives/synthetic-test-only', 'published_at':None,
        'captured_at':'2026-10-17T00:00:00Z','rights':'public-reference-only','title':'Synthetic SEC fixture',
        'content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}})
    resource=workspace['documents'].document_import_resource(str(path),**args)
    workspace['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='isolated-test')
    source=workspace['documents'].import_document(str(path),**args)
    params=dict(actor=workspace['actor'],scope=workspace['scope'],request_id='financial-test-0001')
    saved=financial.save_financial_analysis(source['evidence_id'],**params)
    assert saved['document']['payload']['financial']['source']['claim_type']=='synthetic_sample'
    assert saved['document']['payload']['financial']['source']['original_filing_bytes_verified'] is False
    assert financial.save_financial_analysis(source['evidence_id'],**params)['replayed']
    artifact_id=saved['artifact']['artifact_id']
    revised=financial.save_financial_analysis(source['evidence_id'],**dict(params,request_id='financial-test-0002'),
        work_id=saved['document']['work_id'],previous_artifact_id=artifact_id)
    assert revised['document']['version']==2
    assert workspace['work'].reopen_work(artifact_id,actor=workspace['actor'],scope=workspace['scope'])['document']['version']==1
    # Close and recreate repository objects: persistence must not depend on memory.
    from lumenis.shared.database import DatabaseRepository
    fresh=DatabaseRepository(str(workspace['root']/'isolated.sqlite3'))
    monkeypatch.setattr(workspace['work'],'get_repository',lambda:fresh)
    reopened=workspace['work'].reopen_work(revised['artifact']['artifact_id'],actor=workspace['actor'],scope=workspace['scope'])
    assert reopened['document']['payload']['financial']['facts']==saved['document']['payload']['financial']['facts']
    assert workspace['work'].search_work(actor=workspace['actor'],scope=workspace['scope'],query='advertising_expense')['items']
    with pytest.raises(Exception):
        financial.save_financial_analysis(source['evidence_id'],**dict(params,actor='untrusted'))


def test_xbrl_utf16_entity_bypass_rejected():
    malicious='<!DOCTYPE x [<!ENTITY ext "expanded">]><x/>'
    with pytest.raises(ValueError,match='EXTERNAL_ENTITY'):
        financial.parse_xbrl_instance(malicious.encode('utf-16'),filing_id='fixture')


def test_qualitative_footfall_not_numeric():
    text='Footfall increased significantly.'
    row=dict(annotation(text),metric='footfall_description',value=text,value_literal=text,scale=1,unit='text')
    fact=financial.parse_disclosures(text,[row])['facts'][0]
    assert fact['status']=='QUALITATIVE' and fact['numeric_value'] is None


def test_registry_exact_name_candidate_never_substring_or_child(workspace, monkeypatch):
    monkeypatch.setattr(financial,'get_repository',lambda:workspace['repo'])
    from subject_registry import ensure_schema
    with workspace['repo'].transaction() as con:
        ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,created_at,updated_at) VALUES ('SYN','CTH','company','Synthetic Holding Inc.','合成控股','synthetic holding inc.','合成控股','2026-01-01','2026-01-01')")
    args=dict(actor=workspace['actor'],scope=workspace['scope'])
    exact=financial.match_registered_entity({'name':'Synthetic Holding Inc.'},**args)
    assert exact['status']=='EXACT_NAME_CANDIDATE' and exact['allocation']=='FILING_ENTITY_ONLY'
    assert exact['identifier_verification']=='NOT_VERIFIED'
    assert financial.match_registered_entity({'name':'Synthetic Holding Inc. Mall'},**args)['status']=='MISSING'


def test_noncontiguous_quarters_not_ready():
    facts=[]
    for year in (2020,2021,2023):
        for q in range(1,5):
            end={1:'03-31',2:'06-30',3:'09-30',4:'12-31'}[q]
            facts.append(financial._fact(metric='revenue',concept='test',value=q,unit='USD',start=f'{year}-{3*q-2:02}-01',end=f'{year}-{end}',entity={'name':'test'},filing_id='test',filed='2025-01-01',form='10-Q',locator={}))
    series=financial.select_quarterly_series(facts,metric='revenue',unit='USD',filing_entity={'name':'test'},as_of='2026-01-01')
    assert series['status']=='INSUFFICIENT' and series['reason']=='NON_CONTIGUOUS_QUARTERS'


def test_xml_original_retained_in_same_document_owner(workspace, monkeypatch):
    monkeypatch.setattr(financial,'get_repository',lambda:workspace['repo'])
    path=workspace['root']/'synthetic.xbrl'; path.write_bytes(XML)
    args=dict(actor=workspace['actor'],scope=workspace['scope'],provenance={
        'source_url':'https://www.sec.gov/Archives/synthetic-test-only','published_at':None,
        'captured_at':'2026-10-17T00:00:00Z','rights':'public-reference-only','title':'Synthetic XBRL fixture',
        'content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}})
    resource=workspace['documents'].document_import_resource(str(path),**args)
    workspace['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='isolated-test')
    source=workspace['documents'].import_document(str(path),**args)
    analyzed=financial.analyze_financial_source(source['evidence_id'],actor=workspace['actor'],scope=workspace['scope'],format='xbrl-instance',filing_id='fixture-xml')
    assert analyzed['facts'][0]['value']=='12'
    assert workspace['documents'].reopen_imported_source(source['evidence_id'],actor=workspace['actor'],scope=workspace['scope'])['content']==XML


def test_xbrl_qnames_currency_prefix_rebinding_and_ratios():
    alternate=XML.replace(b'iso4217:',b'money:').replace(b'xmlns:iso4217=',b'xmlns:money=')
    assert financial.parse_xbrl_instance(alternate,filing_id='x')['facts'][0]['currency']=='USD'
    wrong=XML.replace(b'http://www.xbrl.org/2003/iso4217',b'urn:custom-currency')
    fact=financial.parse_xbrl_instance(wrong,filing_id='x')['facts'][0]
    assert fact['currency'] is None and fact['unit']=='{urn:custom-currency}USD'
    rebound=XML.replace(b'<xbrli:measure>',b'<xbrli:measure xmlns:iso4217="urn:custom-local">')
    assert financial.parse_xbrl_instance(rebound,filing_id='x')['facts'][0]['currency'] is None
    pure=XML.replace(b'iso4217:USD',b'xbrli:pure')
    assert financial.parse_xbrl_instance(pure,filing_id='x')['facts'][0]['unit']=='pure'
    ratio=XML.replace(b'<xbrli:measure>iso4217:USD</xbrli:measure>',b'<xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator></xbrli:divide>')
    fact=financial.parse_xbrl_instance(ratio,filing_id='x')['facts'][0]
    assert fact['unit']=='USD/shares' and fact['currency'] is None
    evil=XML.replace(b'http://fasb.org/us-gaap/2024',b'http://fasb.org/us-gaap/2024.attacker.example')
    assert financial.parse_xbrl_instance(evil,filing_id='x')['facts']==[]


@pytest.mark.parametrize('value',['0e-999999999','1e-999999999','1e999999999','NaN','Infinity'])
def test_decimal_exponent_and_nonfinite_denial_of_service(value):
    with pytest.raises(ValueError,match='NUMBER_INVALID'):
        financial._number(value)


@pytest.fixture
def acquisition_workspace(workspace,monkeypatch):
    monkeypatch.setattr(financial,'get_repository',lambda:workspace['repo'])
    from subject_registry import ensure_schema
    with workspace['repo'].transaction() as con:
        ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,created_at,updated_at) VALUES ('SYN','CTH','company','Synthetic Holding Inc.','合成控股','synthetic holding inc.','合成控股','2026-01-01','2026-01-01')")
    workspace['scope']={'domain_id':'cth','subject_id':'SYN','brand_focus_id':None,'global_scope':False}
    path=workspace['root']/'identity.json';path.write_text(json.dumps(sec()))
    args=dict(actor=workspace['actor'],scope=workspace['scope'],provenance={
        'source_url':'https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json','published_at':None,
        'captured_at':'2026-10-17T00:00:00Z','rights':'public-reference-only','title':'Synthetic filing identity',
        'content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}})
    resource=workspace['documents'].document_import_resource(str(path),**args)
    workspace['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='isolated-test')
    workspace['identity']=workspace['documents'].import_document(str(path),**args)
    return workspace


def test_registered_target_http_fixture_capture_update_replay_and_import(acquisition_workspace,monkeypatch):
    """Owned localhost server plus explicitly injected adapter seam, not SEC access.

    The production safe transport has no localhost exception; separate tests
    retain that denial. Only this test substitutes its network boundary.
    """
    import threading
    import urllib.request
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.adapters.public_source import PublicResponse
    ws=acquisition_workspace
    payload={'cik':1,'entityName':'Synthetic Holding Inc.','taxonomy':'us-gaap','tag':'AdvertisingExpense',
        'units':{'USD':[{'val':10,'start':'2024-01-01','end':'2024-03-31','accn':'0000000001-24-000001','filed':'2024-05-01','form':'10-Q'}]}}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            raw=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    calls=[]
    def owned_fixture(url):
        calls.append(url)
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/fixture',timeout=2) as response:
            return PublicResponse(url=url,content=response.read(),content_type='application/json',status_code=200,requested_url=url)
    monkeypatch.setattr(public_http,'fetch_public_url',owned_fixture)
    args=dict(actor=ws['actor'],scope=ws['scope'])
    try:
        target=financial.save_financial_target(ws['identity']['evidence_id'],request_id='financial-target-0001',**args)
        tid=target['artifact']['artifact_id'];prepared=financial.prepare_financial_collection(tid,**args)
        with pytest.raises(PermissionError,match='EXACT_APPROVAL'):
            financial.collect_financial_target(tid,request_id='financial-run-0001',**args)
        assert calls==[]
        token=ws['gate'].grant_approval('collector_start',resource=prepared['resource'],granted_by='isolated-test')
        collected=financial.collect_financial_target(tid,request_id='financial-run-0001',**args)
        assert collected['state']=='CAPTURED' and len(calls)==1
        replayed=financial.collect_financial_target(tid,request_id='financial-run-0001',**args)
        assert replayed['replayed'] and len(calls)==1
        again=financial.collect_financial_target(tid,request_id='financial-run-0002',**args)
        assert again['capture']['artifact']['artifact_id']==collected['capture']['artifact']['artifact_id']
        cid=collected['capture']['artifact']['artifact_id']
        with pytest.raises(PermissionError,match='IMPORT_EXACT'):
            financial.import_financial_capture(cid,**args)
        ws['gate'].grant_approval('data_import',resource=collected['import_preview']['resource'],granted_by='isolated-test')
        imported=financial.import_financial_capture(cid,**args)
        assert imported['analysis']['facts'][0]['value']=='10'
        assert financial.import_financial_capture(cid,**args)['source']['replayed']
        payload['units']['USD'][0].update(val=12,accn='0000000001-24-000002',filed='2024-06-01')
        amended=financial.collect_financial_target(tid,request_id='financial-run-0003',**args)
        assert amended['capture']['artifact']['artifact_id']!=cid
        assert financial.import_financial_capture(cid,**args)['analysis']['facts'][0]['value']=='10'
        payload['cik']=2
        with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):
            financial.collect_financial_target(tid,request_id='financial-run-wrong',**args)
        ws['gate'].revoke_approval(token)
        with pytest.raises(PermissionError,match='EXACT_APPROVAL'):
            financial.collect_financial_target(tid,request_id='financial-run-0001',**args)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)


def test_production_public_transport_does_not_allow_local_fixture():
    from lumenis.system.collector.adapters.public_source import fetch_public_url,PublicSourceError
    with pytest.raises(PublicSourceError):
        fetch_public_url('http://127.0.0.1:18466/fixture')


def test_acquisition_rechecks_revocation_after_network_and_failure_creates_no_success(acquisition_workspace,monkeypatch):
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.adapters.public_source import PublicResponse,PublicSourceError
    ws=acquisition_workspace;args=dict(actor=ws['actor'],scope=ws['scope'])
    target=financial.save_financial_target(ws['identity']['evidence_id'],request_id='financial-cancel-target-001',**args)
    tid=target['artifact']['artifact_id'];prepared=financial.prepare_financial_collection(tid,**args)
    token=ws['gate'].grant_approval('collector_start',resource=prepared['resource'],granted_by='isolated-test')
    def cancelled(url):
        ws['gate'].revoke_approval(token)
        return PublicResponse(url=url,content=json.dumps(sec()).encode(),content_type='application/json',status_code=200)
    monkeypatch.setattr(public_http,'fetch_public_url',cancelled)
    with pytest.raises(PermissionError,match='EXACT_APPROVAL'):
        financial.collect_financial_target(tid,request_id='financial-cancel-run-001',**args)
    assert financial._existing_request('financial-cancel-run-001',**args) is None
    ws['gate'].grant_approval('collector_start',resource=prepared['resource'],granted_by='isolated-test')
    def failed(url):raise PublicSourceError('synthetic timeout')
    monkeypatch.setattr(public_http,'fetch_public_url',failed)
    result=financial.collect_financial_target(tid,request_id='financial-failed-run-001',**args)
    assert result['state']=='UNAVAILABLE' and result['source_saved'] is False
    assert financial._existing_request('financial-failed-run-001',**args) is None


@pytest.mark.parametrize('content_type,size,status',[('text/html',4,200),('application/json',2*1024*1024+1,200),('application/json',4,403)])
def test_public_document_method_rejects_bad_transport_envelopes(content_type,size,status):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse,PublicSourceError
    adapter=PublicHttpAdapter(fetcher=lambda url:PublicResponse(url=url,content=b'x'*size,content_type=content_type,status_code=status))
    with pytest.raises(PublicSourceError):adapter.fetch_document('https://example.com/file',allowed_content_types=('application/json',))


def test_document_limiter_cooldown_and_wait_reauthorization(monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse, PublicSourceError
    from types import SimpleNamespace
    from lumenis.system.collector.guard import rate_limiter
    clock = SimpleNamespace(wall=1000.0, mono=1000.0)
    monkeypatch.setattr(rate_limiter, 'time', SimpleNamespace(time=lambda: clock.wall, monotonic=lambda: clock.mono))
    calls=[]
    adapter=PublicHttpAdapter(fetcher=lambda url: calls.append(url) or PublicResponse(url=url,content=b'{}',content_type='application/json',status_code=200))
    adapter._document_limiter.force_pause(cooldown_seconds=60)
    with pytest.raises(PublicSourceError,match='cooling down'):
        adapter.fetch_document('https://example.com/a',allowed_content_types=('application/json',))
    assert not calls
    adapter._document_limiter.on_success()
    # A sibling success must not clear an unelapsed force_pause (rate-v2).
    assert adapter._document_limiter.remaining_cooldown() == 60
    assert not adapter._document_limiter.can_run()
    clock.wall += 60
    clock.mono += 60
    assert adapter._document_limiter.can_run()
    # Exercise the real reservation/wake loop, not a no-op wait replacement.
    adapter._document_limiter.interval = 1.0
    wait_slot = adapter._document_limiter.wait_slot
    waits = []
    def elapsed_sleep(seconds):
        waits.append(seconds)
        clock.wall += seconds
        clock.mono += seconds
    monkeypatch.setattr(adapter._document_limiter, 'wait_slot', lambda: wait_slot(sleep=elapsed_sleep))
    def revoked():
        assert waits == [1.0] and clock.mono == 1061.0
        raise PermissionError('approval revoked while waiting')
    with pytest.raises(PermissionError,match='revoked'):
        adapter.fetch_document('https://example.com/a',allowed_content_types=('application/json',),before_fetch=revoked)
    assert not calls


def test_financial_collection_rechecks_exact_approval_after_real_limiter_wait(acquisition_workspace, monkeypatch):
    from types import SimpleNamespace
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.guard import rate_limiter
    ws = acquisition_workspace
    args = dict(actor=ws['actor'], scope=ws['scope'])
    target = financial.save_financial_target(ws['identity']['evidence_id'], request_id='financial-wait-target-001', **args)
    tid = target['artifact']['artifact_id']
    prepared = financial.prepare_financial_collection(tid, **args)
    token = ws['gate'].grant_approval('collector_start', resource=prepared['resource'], granted_by='isolated-test')
    clock = SimpleNamespace(wall=1000.0, mono=1000.0)
    monkeypatch.setattr(rate_limiter, 'time', SimpleNamespace(time=lambda: clock.wall, monotonic=lambda: clock.mono))
    limiter = public_http.PublicHttpAdapter._document_limiter
    limiter.interval = 1.0
    wait_slot = limiter.wait_slot
    waits, fetched = [], []
    def withdraw_during_wait(seconds):
        waits.append(seconds)
        clock.wall += seconds
        clock.mono += seconds
        assert ws['gate'].revoke_approval(token)
    monkeypatch.setattr(limiter, 'wait_slot', lambda: wait_slot(sleep=withdraw_during_wait))
    def forbidden_fetch(url):
        fetched.append(url)
        raise AssertionError('revoked collection must not reach transport')
    monkeypatch.setattr(public_http, 'fetch_public_url', forbidden_fetch)
    with pytest.raises(PermissionError, match='EXACT_APPROVAL'):
        financial.collect_financial_target(tid, request_id='financial-wait-run-001', **args)
    assert waits == [1.0]
    assert not fetched
    assert financial._existing_request('financial-wait-run-001', **args) is None
