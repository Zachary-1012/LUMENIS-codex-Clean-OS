"""Synthetic engineering cases; public original acceptance is a separate receipt."""
import copy
import pytest
from lumenis.importer import macro
from lumenis.system.security import permission
from tests.test_saved_document_workflow import workspace

URL='https://www.stats.gov.cn/english/PressRelease/202504/t20250425_1959459.html'
TEXT='''Total Retail Sales of Consumer Goods in March 2025
2025-04-17 10:00
In March, the total retail sales of consumer goods reached 4,094.0 billion yuan.
From January to March, the total retail sales of consumer goods reached 12,467.1 billion yuan.
'''
CPI='''Consumer Price Index for January 2025
2025-02-10 09:30
In January 2025, the national consumer price index (CPI) decreased by 0.5 percent year on year.
'''


def test_nbs_retains_exact_month_cumulative_units_and_native_time():
    result=macro.parse_nbs_release(TEXT,source_url=URL)
    assert [f['value'] for f in result['facts']]==['4094000000000.0','12467100000000.0']
    assert [f['period_kind'] for f in result['facts']]==['month','cumulative']
    assert result['facts'][0]['publication_timezone']=='UNKNOWN'
    assert result['facts'][0]['published_literal']=='2025-04-17 10:00'
    assert result['facts'][0]['unit']=='CNY' and result['facts'][0]['region']=='CN-national'
    assert macro.parse_nbs_release(CPI,source_url=URL)['facts'][0]['value']=='-0.5'
    assert macro.parse_nbs_release(CPI.replace('0.5','0'),source_url=URL)['facts'][0]['value']=='-0'


@pytest.mark.parametrize('url',[URL.replace('www.stats.gov.cn','evil.example'),URL.replace('https','http'),URL+'?key=secret',URL+'#fragment',URL.replace('/english/','/other/'),URL.replace('www.stats.gov.cn','www.stats.gov.cn.evil.example')])
def test_official_source_rejects_other_hosts_and_unbounded_urls(url):
    with pytest.raises(ValueError,match='MACRO_OFFICIAL'):macro.parse_nbs_release(TEXT,source_url=url)


def test_ambiguity_never_selects_first_number_or_invents_missing_month():
    assert macro.parse_nbs_release(TEXT+'\n'+CPI,source_url=URL)['facts']==[]
    assert macro.parse_nbs_release(TEXT+'\nIn March, the total retail sales of consumer goods reached 2 billion yuan.',source_url=URL)['facts']==[]
    assert macro.parse_nbs_release(TEXT.replace('reached','were'),source_url=URL)['facts']==[]
    assert len(macro.parse_nbs_release(TEXT.replace('4,094.0','4,09.0'),source_url=URL)['facts'])==1


def _facts():
    facts=macro.parse_nbs_release(TEXT,source_url=URL)['facts']
    for f in facts:f.update(captured_at='2025-04-20T00:00:00Z',source_ref={'evidence_id':'one'})
    return facts


def select(facts,**changes):
    options=dict(region='CN-national',metric='retail_sales',periods=['2025-Q1'],as_of='2025-04-21T00:00:00Z');options.update(changes)
    return macro.align_quarters(facts,**options)


def test_quarter_exact_total_no_interpolation_geography_or_vintage_leak():
    facts=_facts();r=select(facts)
    assert r['state']=='AVAILABLE' and r['periods'][0]['aggregation']=='explicit-reported-quarter-total'
    assert r['periods'][0]['value']=='12467100000000.0'
    assert select(facts[:1])['state']=='INSUFFICIENT'
    assert select(facts,region='CN-Shanghai')['periods'][0]['reason']=='REGION_UNAVAILABLE'
    assert select(facts,as_of='2025-04-19T00:00:00Z')['state']=='INSUFFICIENT'
    revised=copy.deepcopy(facts[-1]);revised.update(value='1',captured_at='2025-05-01T00:00:00Z')
    assert select(facts+[revised])['periods'][0]['value']=='12467100000000.0'
    assert select(facts+[revised],as_of='2025-05-02T00:00:00Z')['periods'][0]['value']=='1'
    revised['captured_at']=facts[-1]['captured_at']
    assert select(facts+[revised])['periods'][0]['reason']=='CONFLICTING_CAPTURE_VINTAGES'


def test_cpi_mean_never_claims_quarter_inflation():
    facts=[]
    for month,next_month,value in [('January','February','0'),('February','March','0.6'),('March','April','0.9')]:
        text=CPI.replace('January',month).replace('2025-02-10',{'January':'2025-02-10','February':'2025-03-10','March':'2025-04-10'}[month]).replace('decreased','increased').replace('0.5',value)
        fact=macro.parse_nbs_release(text,source_url=URL)['facts'][0]
        fact.update(captured_at='2025-04-20T00:00:00Z',source_ref={'evidence_id':month});facts.append(fact)
    r=select(facts,metric='cpi_yoy_percent')
    assert r['periods'][0]['value']=='0.5'
    assert r['periods'][0]['aggregation']=='arithmetic-mean-monthly-yoy-percent'
    assert select(facts[:2],metric='cpi_yoy_percent')['state']=='INSUFFICIENT'


def test_saved_source_revision_replay_scope_and_original_integrity(workspace,monkeypatch):
    w=workspace;monkeypatch.setattr(macro,'get_repository',lambda:w['repo'])
    path=w['root']/'macro.txt';path.write_text(TEXT)
    provenance={'source_url':URL,'captured_at':'2025-04-20T00:00:00Z','published_at':None,'rights':'owner-approved','title':'Synthetic national release','content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}}
    args=dict(actor=w['actor'],scope=w['scope'],provenance=provenance)
    resource=w['documents'].document_import_resource(str(path),**args)
    w['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='isolated-test')
    source=w['documents'].import_document(str(path),**args)
    opts=dict(actor=w['actor'],scope=w['scope'],selection=dict(region='CN-national',metric='retail_sales',periods=['2025-Q1','2025-Q2'],as_of='2025-05-01T00:00:00Z'))
    ids=[source['evidence_id']]
    analyzed=macro.analyze_macro_sources(ids,**opts)
    assert analyzed['quarterly_control']['periods'][0]['state']=='AVAILABLE'
    assert analyzed['sources'][0]['capture_mode']=='file_import'
    assert analyzed['sources'][0]['declared_provider']=='NBS'
    assert analyzed['sources'][0]['origin_verification']=='NOT_INDEPENDENTLY_VERIFIED'
    assert analyzed['sources'][0]['official_network_acquisition']=='UNKNOWN'
    assert analyzed['quarterly_control']['availability_basis']=='PERIOD_REGION_UNIT_DEFINITION_COVERAGE_ONLY'
    assert analyzed['quarterly_control']['origin_verification']=='NOT_INDEPENDENTLY_VERIFIED'
    assert analyzed['quarterly_control']['periods'][1]['value'] is None
    saved=macro.save_macro_analysis(ids,request_id='macro-save-0001',**opts)
    assert macro.save_macro_analysis(ids,request_id='macro-save-0001',**opts)['replayed']
    revised=macro.save_macro_analysis(ids,request_id='macro-save-0002',work_id=saved['document']['work_id'],previous_artifact_id=saved['artifact']['artifact_id'],**opts)
    assert revised['document']['version']==2
    assert w['work'].reopen_work(saved['artifact']['artifact_id'],actor=w['actor'],scope=w['scope'])['document']['version']==1
    assert w['documents'].reopen_imported_source(ids[0],actor=w['actor'],scope=w['scope'])['content']==path.read_bytes()
    with w['repo'].connection(read_only=True,wal=False) as con:
        assert con.execute('SELECT count(*) FROM canonical_data WHERE source_id=?',(source['source_id'],)).fetchone()[0]==1
    with pytest.raises(Exception):macro.analyze_macro_sources(ids,actor='forged',scope=w['scope'])


def test_unknown_capture_timezone_stays_missing_and_asof_requires_offset():
    facts=_facts()
    for fact in facts:fact['captured_at']='2025-04-20 10:00:00'
    assert select(facts)['state']=='INSUFFICIENT'
    with pytest.raises(ValueError,match='OFFSET_REQUIRED'):select(facts,as_of='2025-04-21')


def test_bad_periods_and_unsupported_metric_reject():
    for change in ({'periods':['2025-Q5']},{'periods':['2025-Q1','2025-Q1']},{'periods':[]},{'metric':'brand_revenue'}):
        with pytest.raises(ValueError):select(_facts(),**change)


def test_source_revoked_before_save_creates_no_report(workspace,monkeypatch):
    w=workspace;monkeypatch.setattr(macro,'get_repository',lambda:w['repo'])
    path=w['root']/'macro.txt';path.write_text(TEXT)
    args=dict(actor=w['actor'],scope=w['scope'],provenance={'source_url':URL,'captured_at':'2025-04-20T00:00:00Z','published_at':None,'rights':'owner-approved','title':'Synthetic','content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}})
    resource=w['documents'].document_import_resource(str(path),**args)
    w['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='test')
    source=w['documents'].import_document(str(path),**args)
    original=w['work'].save_work
    def withdraw(**kwargs):
        w['app'].config['LUMENIS_OPEN_WORKSPACE']=False
        return original(**kwargs)
    monkeypatch.setattr(w['work'],'save_work',withdraw)
    before=w['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]
    with pytest.raises(Exception):macro.save_macro_analysis([source['evidence_id']],actor=w['actor'],scope=w['scope'],request_id='macro-revocation-001')
    assert w['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]==before


@pytest.fixture
def macro_collection_workspace(workspace,monkeypatch):
    w=workspace;monkeypatch.setattr(macro,'get_repository',lambda:w['repo'])
    from subject_registry import ensure_schema
    with w['repo'].transaction() as con:
        ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,created_at,updated_at) VALUES ('MAC','CTH','company','Macro Company','宏观企业','macro company','宏观企业','2026-01-01','2026-01-01')")
    w['scope']={'domain_id':'cth','subject_id':'MAC','brand_focus_id':None,'global_scope':False}
    path=w['root']/'source.txt';path.write_text(TEXT)
    args=dict(actor=w['actor'],scope=w['scope'],provenance={'source_url':URL,'captured_at':'2025-04-20T00:00:00Z','published_at':None,'rights':'owner-approved','title':'Synthetic','content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}})
    resource=w['documents'].document_import_resource(str(path),**args)
    w['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='test')
    w['macro_source']=w['documents'].import_document(str(path),**args)
    return w


def test_macro_collection_reuses_original_capture_owner_and_exact_permissions(macro_collection_workspace,monkeypatch):
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    w=macro_collection_workspace;args=dict(actor=w['actor'],scope=w['scope'])
    target=macro.save_macro_target(w['macro_source']['evidence_id'],request_id='macro-target-0001',**args)
    tid=target['artifact']['artifact_id'];prepared=macro.prepare_macro_collection(tid,**args)
    calls=[];raw=('<html><body><article><pre>'+TEXT+'</pre></article></body></html>').encode()
    def fetch(url):calls.append(url);return PublicResponse(url,raw,'text/html',200)
    monkeypatch.setattr(public_http,'fetch_public_url',fetch)
    monkeypatch.setattr(public_http.PublicHttpAdapter,'_document_limiter',AdaptiveRateLimiter(base_interval=0,min_interval=0,jitter=False))
    with pytest.raises(PermissionError,match='EXACT_APPROVAL'):macro.collect_macro_target(tid,request_id='macro-run-0001',**args)
    assert calls==[]
    token=w['gate'].grant_approval('collector_start',resource=prepared['resource'],granted_by='test')
    collected=macro.collect_macro_target(tid,request_id='macro-run-0001',**args)
    assert collected['state']=='CAPTURED' and len(calls)==1
    cid=collected['capture']['artifact']['artifact_id']
    assert macro.collect_macro_target(tid,request_id='macro-run-0001',**args)['replayed'] and len(calls)==1
    assert macro.collect_macro_target(tid,request_id='macro-run-0002',**args)['capture']['artifact']['artifact_id']==cid
    with pytest.raises(PermissionError,match='IMPORT_EXACT_APPROVAL'):macro.import_macro_capture(cid,**args)
    preview=macro.prepare_macro_capture(cid,**args)
    w['gate'].grant_approval('data_import',resource=preview['resource'],granted_by='test')
    imported=macro.import_macro_capture(cid,**args)
    assert imported['state']=='IMPORTED' and len(imported['analysis']['facts'])==2
    assert w['documents'].reopen_imported_source(imported['source']['evidence_id'],**args)['content']==raw
    assert macro.import_macro_capture(cid,**args)['source']['replayed']
    w['gate'].revoke_approval(token)
    with pytest.raises(PermissionError,match='EXACT_APPROVAL'):macro.collect_macro_target(tid,request_id='macro-run-0001',**args)


def test_macro_wrong_period_and_inflight_revocation_create_no_capture(macro_collection_workspace,monkeypatch):
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    w=macro_collection_workspace;args=dict(actor=w['actor'],scope=w['scope'])
    tid=macro.save_macro_target(w['macro_source']['evidence_id'],request_id='macro-target-0001',**args)['artifact']['artifact_id']
    prepared=macro.prepare_macro_collection(tid,**args)
    monkeypatch.setattr(public_http.PublicHttpAdapter,'_document_limiter',AdaptiveRateLimiter(base_interval=0,min_interval=0,jitter=False))
    token=w['gate'].grant_approval('collector_start',resource=prepared['resource'],granted_by='test')
    monkeypatch.setattr(public_http,'fetch_public_url',lambda url:PublicResponse(url,('<pre>'+TEXT.replace('March','February')+'</pre>').encode(),'text/html',200))
    with pytest.raises(ValueError,match='PERIOD_OR_METRIC'):macro.collect_macro_target(tid,request_id='macro-wrong-period',**args)
    assert macro._existing_macro_request('macro-wrong-period',**args) is None
    def revoke(url):
        w['gate'].revoke_approval(token)
        return PublicResponse(url,('<pre>'+TEXT+'</pre>').encode(),'text/html',200)
    monkeypatch.setattr(public_http,'fetch_public_url',revoke)
    with pytest.raises(PermissionError,match='EXACT_APPROVAL'):macro.collect_macro_target(tid,request_id='macro-revoked-run',**args)
    assert macro._existing_macro_request('macro-revoked-run',**args) is None


MCT_QUARTER_URL='https://zwgk.mct.gov.cn/zfxxgkml/tjxx/202504/t20250423_959574.html'
MCT_HOLIDAY_URL='https://www.mct.gov.cn/whzx/whyw/202502/t20250205_958229.htm'
BEIJING_URL='https://sw.beijing.gov.cn/phone/zwxx/swxx/202504/t20250408_4059470.html'
MCT_QUARTER='''2025年一季度国内出游数据情况
发布时间：2025年04月23日
根据国内出游抽样调查统计结果，2025年一季度，国内出游人次1.25亿。
2025年一季度，国内居民出游总花费0.50万亿元。
'''
MCT_HOLIDAY='''2025年春节假期文化和旅游市场情况
发布时间：2025-02-05 14:28
经文化和旅游部数据中心测算，春节假期8天，全国国内出游0.01亿人次，同比增长1%；国内出游总花费2.00亿元。
'''
BEIJING='''清明假期本市消费市场活跃有序
发布时间：2025-04-08
2025年清明假期，假期三天，全市60个重点商圈客流量12.3万人次。
'''


def test_mct_quarter_and_holiday_are_different_statistics():
    q=macro.parse_macro_release(MCT_QUARTER,source_url=MCT_QUARTER_URL)['facts']
    assert [f['value'] for f in q]==['125000000.00','500000000000.00']
    assert all(f['period_kind']=='quarter' and f['period_start']=='2025-01-01' for f in q)
    h=macro.parse_macro_release(MCT_HOLIDAY,source_url=MCT_HOLIDAY_URL)['facts']
    assert all(f['period_start'] is None and f['period_end'] is None and f['duration_days']==8 for f in h)
    assert h[0]['unit']=='person_trips' and 'not-unique-persons' in h[0]['definition']
    for f in q+h:f.update(captured_at='2025-05-01T00:00:00Z',source_ref={'evidence_id':1})
    selection=dict(region='CN-national',metric='domestic_tourism_trips',periods=['2025-Q1'],as_of='2025-05-02T00:00:00Z')
    assert macro.align_quarters(q+h,**selection)['periods'][0]['value']=='125000000.00'
    assert macro.align_quarters(h,**selection)['periods'][0]['reason']=='HOLIDAY_TOTAL_NOT_QUARTER'
    assert macro.align_quarters(q+h,**dict(selection,region='CN-Beijing'))['state']=='INSUFFICIENT'
    assert macro.parse_macro_release(MCT_QUARTER.replace('根据国内出游抽样调查统计结果','其他情况'),source_url=MCT_QUARTER_URL)['facts']==[]


def test_beijing_scope_is_monitored_visits_not_unique_city_population():
    facts=macro.parse_macro_release(BEIJING,source_url=BEIJING_URL)['facts']
    assert len(facts)==1
    fact=facts[0]
    assert fact['value']=='123000.0' and fact['unit']=='person_visits'
    assert fact['region']=='CN-Beijing' and fact['coverage']['district_count']==60
    assert fact['period_label']=='2025-清明' and fact['period_start'] is None
    fact.update(captured_at='2025-05-01T00:00:00Z',source_ref={'evidence_id':1})
    assert macro.align_quarters(facts,region='CN-Beijing',metric='monitored_district_footfall',periods=['2025-Q2'],as_of='2025-05-02T00:00:00Z')['periods'][0]['reason']=='HOLIDAY_TOTAL_NOT_QUARTER'
    assert macro.parse_macro_release(BEIJING.replace('万人次','万人'),source_url=BEIJING_URL)['facts']==[]
    assert macro.parse_macro_release(BEIJING.replace('三天','五天'),source_url=BEIJING_URL)['facts']==[]
    with pytest.raises(ValueError):macro.parse_macro_release(MCT_QUARTER.replace('2025年04月23日','2025年01月01日'),source_url=MCT_QUARTER_URL)


def test_macro_supported_provider_does_not_guess_other_regions_or_paths():
    for url in (MCT_QUARTER_URL.replace('zwgk.mct.gov.cn','evil.mct.gov.cn'),BEIJING_URL.replace('beijing','shanghai'),MCT_HOLIDAY_URL+'?access_token=x'):
        with pytest.raises(ValueError,match='OFFICIAL'):macro.parse_macro_release(MCT_HOLIDAY,source_url=url)
    with pytest.raises(ValueError,match='NBS'):macro.parse_nbs_release(TEXT,source_url=MCT_QUARTER_URL)


def test_refresh_rejects_population_definition_change_even_same_period():
    parsed=macro.parse_macro_release(BEIJING,source_url=BEIJING_URL)
    target={'url':BEIJING_URL,'source_periods':[(None,None,'2025-清明')],
        'source_metrics':['monitored_district_footfall'],'source_dimensions':macro._source_dimensions(parsed['facts'])}
    raw=('<pre>'+BEIJING.replace('60个','61个')+'</pre>').encode()
    with pytest.raises(ValueError,match='PERIOD_OR_METRIC'):
        macro._validate_macro_response(raw,target)
    assert macro.parse_macro_release(MCT_QUARTER.replace('一季度','上半年'),source_url=MCT_QUARTER_URL)['facts']==[]
