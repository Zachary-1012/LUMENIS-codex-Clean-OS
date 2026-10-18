"""Synthetic layouts; live public PDF verification lives outside test fixtures."""
import json
import pytest
from lumenis.importer import financial
from lumenis.importer.financial_tables import parse_regional_statement, parse_opendart_json, opendart_request_config
from tests.test_saved_document_workflow import workspace
from lumenis.system.security import permission

TEXT='''EXAMPLE HOLDINGS LIMITED
(Incorporated in Hong Kong with limited liability)
(Stock Code: 01234)
Consolidated Statement of Profit or Loss
For the year ended 31st December 2024
2024 2023
Note HK$M HK$M
Revenue 2 1,234 987
Administrative and selling expenses (12) (10)
Advertising expenses — 0
'''

def parse(text=TEXT):
    return parse_regional_statement(text,[{'unit':'pdf_page','index':4,'start':0,'end':len(text)}],exchange='HKEX',filing_id='fixture')


def test_automatic_statement_has_period_currency_scale_page_and_no_sga_relabel():
    r=parse(); assert len(r['facts'])==6
    assert r['facts'][0]['value']=='1234000000'
    assert r['facts'][0]['locator']['page']==4
    assert r['facts'][0]['period_start']=='2024-01-01'
    assert r['facts'][2]['metric']=='selling_general_admin_expense'
    assert r['facts'][2]['value']=='-12000000'
    assert r['facts'][4]['value'] is None
    assert r['facts'][5]['value']=='0'
    assert not any(x['metric']=='marketing_expense' for x in r['facts'])

@pytest.mark.parametrize('old,new,reason',[
    ('For the year ended 31st December 2024','Report 2024','PERIOD_HEADER_AMBIGUOUS'),
    ('HK$M HK$M','USD HKD','CURRENCY_SCALE_AMBIGUOUS'),
    ('(Stock Code: 01234)','(Unknown identity)','FILING_ENTITY_UNRESOLVED'),
    ('2024 2023','2024 2023 2022','PERIOD_HEADER_AMBIGUOUS'),
])
def test_ambiguity_is_candidate_not_invented_value(old,new,reason):
    r=parse(TEXT.replace(old,new));assert r['facts']==[]
    assert all(x['reason']==reason for x in r['candidates'])


def test_extra_column_not_mistaken_for_note_or_growth():
    r=parse(TEXT.replace('Revenue 2 1,234 987','Revenue 2 1,234 987 25%'))
    assert not any(x['metric']=='revenue' for x in r['facts'])
    assert r['candidates'][0]['reason']=='UNSUPPORTED_OR_AMBIGUOUS_VALUE_COLUMNS'


def test_half_year_never_becomes_quarter():
    r=parse(TEXT.replace('year ended 31st December','six months ended 30th June'))
    assert all(x['period_kind']=='half_year' and x['period_end'].endswith('06-30') for x in r['facts'])


def test_chinese_statement_explicit_year_currency_and_scale():
    text='示例股份有限公司\n证券代码：600001\n合并利润表\n2024年度 2023年度\n单位：万元 币种：人民币\n营业收入 100 90\n销售费用 10 8'
    r=parse_regional_statement(text,[],exchange='SSE',filing_id='fixture-cn')
    assert r['facts'][0]['value']=='1000000'
    assert r['facts'][2]['metric']=='selling_expense'
    assert r['facts'][0]['filing_entity']['identifier']=='600001'


def dart(**changes):
    row={'corp_code':'00123456','rcept_no':'20250814000123','fs_div':'CFS','sj_div':'IS',
         'account_nm':'매출액','thstrm_dt':'2025.01.01 ~ 2025.06.30','reprt_code':'11012',
         'thstrm_amount':'10','thstrm_add_amount':'25','currency':'KRW'}
    row.update(changes)
    return json.dumps({'status':'000','list':[row]}).encode()


def test_opendart_current_amount_uses_current_dates_cumulative_stays_unbound():
    r=parse_opendart_json(dart()); f=r['facts'][0]
    assert f['value']=='10' and f['period_kind']=='half_year'
    assert r['candidates'][0]['reason']=='ACCUMULATED_PERIOD_NOT_EXPLICIT'
    assert r['candidates'][0]['value_literal']=='25'
    assert r['candidates'][0]['period_start'] is None
    assert f['filing_entity']['name'] is None
    assert f['locator']['pointer']=='/list/0/thstrm_amount'
    assert parse_opendart_json(dart(thstrm_dt='제 13 기'))['facts']==[]
    assert parse_opendart_json(dart(thstrm_amount=None))['facts']==[]
    assert parse_opendart_json(dart(thstrm_add_amount=None))['facts'][0]['value']=='10'
    assert parse_opendart_json(dart(currency=''))['facts']==[]

@pytest.mark.parametrize('status,reason',[('010','INVALID_CREDENTIAL'),('013','NO_DATA'),('020','RATE_LIMITED'),('800','MAINTENANCE')])
def test_opendart_errors_and_secret_free_config(status,reason):
    assert parse_opendart_json(json.dumps({'status':status}).encode())['missing'][0]['reason']==reason
    c=opendart_request_config(corp_code='00123456',bsns_year='2025',reprt_code='11012')
    assert c['status']=='MISSING_CREDENTIAL' and 'crtfc_key' not in c['query']


def test_existing_importer_savedwork_revisions_replay_and_source_integrity(workspace,monkeypatch):
    w=workspace;monkeypatch.setattr(financial,'get_repository',lambda:w['repo'])
    path=w['root']/'regional.txt';path.write_text(TEXT)
    args={'actor':w['actor'],'scope':w['scope'],'provenance':{'source_url':'https://www1.hkexnews.hk/listedco/example.txt',
          'published_at':None,'captured_at':'2026-10-17T00:00:00Z','rights':'owner-approved','content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'},'title':'Synthetic regional statement'}}
    resource=w['documents'].document_import_resource(str(path),**args)
    w['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=resource,granted_by='isolated-test')
    source=w['documents'].import_document(str(path),**args)
    opts={'actor':w['actor'],'scope':w['scope'],'format':'regional-statement'}
    result=financial.analyze_financial_source(source['evidence_id'],**opts)
    assert len(result['facts'])==6 and result['source']['retained_input_bytes_verified']
    saved=financial.save_financial_analysis(source['evidence_id'],request_id='regional-source-001',**opts)
    again=financial.save_financial_analysis(source['evidence_id'],request_id='regional-source-001',**opts)
    assert again['replayed']
    revised=financial.save_financial_analysis(source['evidence_id'],request_id='regional-source-002',
        work_id=saved['document']['work_id'],previous_artifact_id=saved['artifact']['artifact_id'],**opts)
    assert revised['document']['version']==2
    assert w['work'].reopen_work(saved['artifact']['artifact_id'],actor=w['actor'],scope=w['scope'])['document']['version']==1
    assert w['documents'].reopen_imported_source(source['evidence_id'],actor=w['actor'],scope=w['scope'])['content']==path.read_bytes()


def test_mixed_currency_columns_and_malformed_grouping_are_not_normalized():
    assert parse(TEXT.replace('HK$M HK$M','HK$M USD million'))['facts']==[]
    r=parse(TEXT.replace('1,234','1,23'))
    assert not any(f['metric']=='revenue' for f in r['facts'])


def test_regional_capture_uses_original_owner_and_exact_approval(workspace,monkeypatch):
    from subject_registry import ensure_schema
    from reportlab.pdfgen.canvas import Canvas
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.adapters.public_source import PublicResponse,PublicSourceError
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    w=workspace;monkeypatch.setattr(financial,'get_repository',lambda:w['repo'])
    monkeypatch.setattr(public_http.PublicHttpAdapter,'_document_limiter',AdaptiveRateLimiter(base_interval=0,min_interval=0,jitter=False))
    with w['repo'].transaction() as con:
        ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,created_at,updated_at) VALUES ('REG','CTH','company','EXAMPLE HOLDINGS LIMITED','示例公司','example holdings limited','示例公司','2026-01-01','2026-01-01')")
    w['scope']={'domain_id':'cth','subject_id':'REG','brand_focus_id':None,'global_scope':False}
    path=w['root']/'fixture.pdf'
    def pdf(text):
        c=Canvas(str(path));obj=c.beginText(30,800)
        for line in text.splitlines():obj.textLine(line.replace('—','-'))
        c.drawText(obj);c.save();return path.read_bytes()
    raw=pdf(TEXT)
    args={'actor':w['actor'],'scope':w['scope']}
    prov={'source_url':'https://www.hkexnews.hk/listedco/fixture.pdf','published_at':None,
          'captured_at':'2026-10-17T00:00:00Z','rights':'owner-approved','title':'Synthetic PDF',
          'content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}}
    resource=w['documents'].document_import_resource(str(path),provenance=prov,**args)
    w['gate'].grant_approval('data_import',resource=resource,granted_by='isolated-test')
    source=w['documents'].import_document(str(path),provenance=prov,**args)
    target=financial.save_financial_target(source['evidence_id'],format='regional-statement',request_id='regional-target-001',**args)
    tid=target['artifact']['artifact_id'];preview=financial.prepare_financial_collection(tid,**args)
    calls=[]
    def fetch(url):
        calls.append(url);return PublicResponse(url=url,requested_url=url,content=raw,content_type='application/pdf',status_code=200)
    monkeypatch.setattr(public_http,'fetch_public_url',fetch)
    with pytest.raises(PermissionError):financial.collect_financial_target(tid,request_id='regional-run-001',**args)
    assert calls==[]
    token=w['gate'].grant_approval('collector_start',resource=preview['resource'],granted_by='isolated-test')
    capture=financial.collect_financial_target(tid,request_id='regional-run-001',**args)
    cid=capture['capture']['artifact']['artifact_id']
    assert capture['capture']['document']['payload']['financial_capture']['filename']=='filing.pdf'
    w['gate'].grant_approval('data_import',resource=capture['import_preview']['resource'],granted_by='isolated-test')
    imported=financial.import_financial_capture(cid,**args)
    assert imported['analysis']['facts'][0]['value']=='1234000000'
    assert financial.collect_financial_target(tid,request_id='regional-run-001',**args)['replayed']
    assert w['documents'].reopen_imported_source(imported['source']['evidence_id'],**args)['content']==raw
    raw=pdf(TEXT.replace('01234','01235'))
    with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):
        financial.collect_financial_target(tid,request_id='regional-wrong-issuer',**args)
    w['gate'].revoke_approval(token)
    with pytest.raises(PermissionError):financial.collect_financial_target(tid,request_id='regional-run-001',**args)


def test_identity_review_is_scoped_literal_latest_and_revocable(workspace,monkeypatch):
    from subject_registry import ensure_schema
    w=workspace;monkeypatch.setattr(financial,'get_repository',lambda:w['repo'])
    with w['repo'].transaction() as con:
        ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,created_at,updated_at) VALUES ('REG','CTH','company','EXAMPLE HOLDINGS LIMITED','示例公司','example holdings limited','示例公司','2026-01-01','2026-01-01')")
    scope={'domain_id':'cth','subject_id':'REG','brand_focus_id':None,'global_scope':False}
    args={'actor':w['actor'],'scope':scope}
    path=w['root']/'identity.txt';path.write_text(TEXT)
    prov={'source_url':'https://www.hkexnews.hk/listedco/fixture.pdf','published_at':None,
          'captured_at':'2026-10-17T00:00:00Z','rights':'owner-approved','title':'Synthetic identity',
          'content_origin':{'kind':'self-authored','claim_type':'synthetic_sample'}}
    resource=w['documents'].document_import_resource(str(path),provenance=prov,**args)
    w['gate'].grant_approval('data_import',resource=resource,granted_by='isolated-test')
    source=w['documents'].import_document(str(path),provenance=prov,**args)
    entity={'name':'EXAMPLE HOLDINGS LIMITED','scheme':'HKEX-StockCode','identifier':'01234'}
    options={'entity':entity,'name_span':{'start':0,'end':len(entity['name'])},
             'identifier_span':{'start':TEXT.index('01234'),'end':TEXT.index('01234')+5},'reviewed':True,'review_note':'Synthetic reviewer check.'}
    with pytest.raises(ValueError,match='IDENTIFIER_INVALID'):
        financial.save_financial_identity_review(source['evidence_id'],**dict(options,entity=dict(entity,identifier='Revenue')),request_id='identity-bad-001',**args)
    review=financial.save_financial_identity_review(source['evidence_id'],**options,request_id='identity-test-001',**args)
    rid=review['artifact']['artifact_id']
    replay=financial.save_financial_identity_review(source['evidence_id'],**options,request_id='identity-test-001',**args)
    assert replay['replayed'] and replay['artifact']['artifact_id']==rid
    forged=w['work'].save_work(title='Generic copied review',markdown='User-supplied metadata.',kind='research',
        payload=review['document']['payload'],citations=review['document']['citations'],
        contract=review['document']['contract'],request_id='identity-forged-001',**args)
    assert w['work'].reopen_work(forged['artifact']['artifact_id'],**args)['document']['payload']==review['document']['payload']
    with pytest.raises(ValueError,match='OWNER_RECEIPT_REQUIRED'):
        financial.read_financial_identity_review(forged['artifact']['artifact_id'],entity,**args)
    assert financial.read_financial_identity_review(rid,entity,**args)['independent_legal_verification']=='NOT_VERIFIED'
    with w['repo'].connection(read_only=True,wal=False) as con:
        receipt=dict(con.execute('SELECT * FROM app_evidence_records WHERE source=? AND asset_id=?',
                                (financial.IDENTITY_REVIEW_SCHEMA,rid)).fetchone())
    binding=json.loads(receipt['inputs_json'])['review_binding']
    assert binding['artifact_id']==rid and binding['artifact_sha256']==review['artifact']['sha256']
    assert binding['context']==w['work'].authorize(w['actor'],scope,action='read')
    assert binding['version']==1 and binding['work_id']==review['document']['work_id']
    assert binding['review_sha256']==w['work']._digest(review['document']['payload']['financial_identity_review'])
    with w['repo'].transaction() as con:
        con.execute('UPDATE app_evidence_records SET inputs_json=? WHERE id=?',('{}',receipt['id']))
    with pytest.raises(ValueError,match='OWNER_RECEIPT_REQUIRED'):
        financial.read_financial_identity_review(rid,entity,**args)
    with w['repo'].transaction() as con:
        con.execute('UPDATE app_evidence_records SET inputs_json=? WHERE id=?',(receipt['inputs_json'],receipt['id']))
    assert financial.read_financial_identity_review(rid,entity,**args)['identifier_verification']=='SOURCE_BACKED_HUMAN_REVIEW'
    with pytest.raises(ValueError,match='ENTITY_MISMATCH'):
        financial.read_financial_identity_review(rid,dict(entity,identifier='01235'),**args)
    revoke=financial.save_financial_identity_review(source['evidence_id'],**dict(options,reviewed=False,review_note='Retract association.'),
        request_id='identity-test-002',work_id=review['document']['work_id'],previous_artifact_id=rid,**args)
    with pytest.raises(ValueError,match='SUPERSEDED'):
        financial.read_financial_identity_review(rid,entity,**args)
    with pytest.raises(ValueError,match='ENTITY_MISMATCH'):
        financial.read_financial_identity_review(revoke['artifact']['artifact_id'],entity,**args)


@pytest.mark.parametrize('boundary', [
    'Notes to the financial statements\nParent company only\n2022 2021\nUSD thousand USD thousand',
    '2022 2021\nHK$M HK$M',
    'USD thousand USD thousand',
    '母公司利润表\n单位：万元 币种：人民币',
])
def test_later_table_context_never_inherits_primary_metadata(boundary):
    text = TEXT + '\n' + boundary + '\nRevenue 7 8\n'
    result = parse(text)
    assert len(result['facts']) == 6
    assert len(result['candidates']) == 1
    candidate = result['candidates'][0]
    assert candidate['reason'] == 'TABLE_CONTEXT_CHANGED_REVIEW_REQUIRED'
    assert text[candidate['locator']['start']:candidate['locator']['end']].strip() == 'Revenue 7 8'
    assert candidate['locator']['page'] == 4


def test_independently_headed_primary_tables_keep_their_own_periods_and_pages():
    second = TEXT.replace('2024', '2022').replace('2023', '2021').replace('1,234', '432')
    text = TEXT + '\n' + second
    for pages in [[], [dict(unit='pdf_page', index=1, start=0, end=len(TEXT)),
                       dict(unit='pdf_page', index=2, start=len(TEXT)+1, end=len(text))]]:
        result = parse_regional_statement(text,pages,exchange='HKEX',filing_id='bounded-tables')
        assert len(result['facts']) == 12 and not result['candidates']
        assert result['facts'][0]['period_start'] == '2024-01-01'
        assert result['facts'][6]['period_start'] == '2022-01-01'
        assert result['facts'][6]['value'] == '432000000'
        if pages:
            assert result['facts'][6]['locator']['page'] == 2


def test_unheaded_continuation_rows_are_locatable_review_candidates():
    tail='Advertising expenses 12 11\n'
    result = parse_regional_statement(TEXT+tail,
        [dict(unit='pdf_page',index=1,start=0,end=len(TEXT)),
         dict(unit='pdf_page',index=2,start=len(TEXT),end=len(TEXT+tail))],
        exchange='HKEX',filing_id='continuation')
    assert len(result['facts']) == 6
    assert result['candidates'][0]['reason'] == 'PRIMARY_STATEMENT_CONTEXT_NOT_VERIFIED'
    assert result['candidates'][0]['locator']['page'] == 2


def test_parent_scope_in_primary_header_is_not_consolidated_fact():
    result=parse(TEXT.replace('2024 2023','Parent company only\n2024 2023'))
    assert not result['facts']
    assert all(x['reason']=='TABLE_CONTEXT_CHANGED_REVIEW_REQUIRED' for x in result['candidates'])


@pytest.mark.parametrize('boundary', [
    'Segment information', 'Notes on the financial statements', 'Parent entity only',
    'USD thousand USD thousand', 'CHF million CHF million', '单位：万元',
    'HK$M HK$M', '2022 2021',
])
def test_context_before_first_supported_metric_cannot_skip_unknown_table_rows(boundary):
    header=TEXT[:TEXT.index('Revenue 2')]
    text=header+'Cost of sales 80 70\n'+boundary+'\nRevenue 7 8\n'
    result=parse(text)
    assert not result['facts']
    assert len(result['candidates'])==1
    c=result['candidates'][0]
    assert c['status']=='REVIEW_REQUIRED'
    assert text[c['locator']['start']:c['locator']['end']].strip()=='Revenue 7 8'
    assert c['locator']['context_boundary_start'] <= text.index(boundary, len(header))


def test_unknown_numeric_row_without_changed_context_preserves_valid_primary_metadata():
    result=parse(TEXT.replace('Revenue 2', 'Cost of sales 80 70\nRevenue 2'))
    assert len(result['facts'])==6 and not result['candidates']


@pytest.mark.parametrize('currency_unit', [
    '单位：万元 币种：人民币', '币种：人民币 单位：万元',
    '单位：万元\n币种：人民币', '币种：人民币\n单位：万元',
])
def test_chinese_initial_currency_scale_order_is_not_a_context_change(currency_unit):
    text='工程测试股份有限公司\n证券代码：600000\n合并利润表\n2024年度 2023年度\n'+currency_unit+'\n营业收入 100 90\n'
    result=parse_regional_statement(text,[],exchange='SSE',filing_id='engineering-chinese-order')
    assert [f['value'] for f in result['facts']]==['1000000','900000']
    assert all(f['unit']=='CNY' for f in result['facts'])
    assert not result['candidates']


def test_opendart_quarter_and_accumulated_amounts_are_not_conflated():
    result=parse_opendart_json(dart(thstrm_dt='2025.07.01 ~ 2025.09.30',reprt_code='11014',
                                   thstrm_amount='300',thstrm_add_amount='900'))
    fact=result['facts'][0]
    assert (fact['value'],fact['period_start'],fact['period_kind'])==('300','2025-07-01','quarter')
    assert result['candidates'][0]['value_literal']=='900'
    assert result['candidates'][0]['period_end'] is None
    assert parse_opendart_json(dart(thstrm_amount='—'))['facts'][0]['value'] is None
    assert parse_opendart_json(dart(thstrm_amount='0'))['facts'][0]['value']=='0'


def test_registered_entity_scope_never_matches_nulls_or_wrong_domain(workspace,monkeypatch):
    import subject_registry
    w=workspace;monkeypatch.setattr(financial,'get_repository',lambda:w['repo'])
    with w['repo'].transaction() as con:
        subject_registry.ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,created_at,updated_at) VALUES ('selected','CTH','company','Selected issuer','主体','selected issuer','主体','2026-01-01','2026-01-01')")
    row={'subject_id':'other','brand_focus_id':None,'domain_id':'CTH',
         'name_en':'Example issuer','name_zh':'示例'}
    original_list=subject_registry.list_subjects
    # Inject anomalous rows only into this owner read; Permission keeps its real registry.
    monkeypatch.setattr(subject_registry,'list_subjects',lambda *a,**k:
        [row] if k.get('connection') is not None else original_list(*a,**k))
    entity={'name':'Example issuer'}
    scoped=dict(w['scope'],subject_id='selected',global_scope=False)
    assert financial.match_registered_entity(entity,actor=w['actor'],scope=scoped)['status']=='MISSING'
    row['subject_id']='selected'
    assert financial.match_registered_entity(entity,actor=w['actor'],scope=scoped)['status']=='EXACT_NAME_CANDIDATE'
    row['domain_id']='BMP'
    assert financial.match_registered_entity(entity,actor=w['actor'],scope=scoped)['status']=='MISSING'
    assert financial.match_registered_entity(entity,actor=w['actor'],scope=w['scope'])['status']=='MISSING'
    row['domain_id']='CTH'
    assert financial.match_registered_entity(entity,actor=w['actor'],scope=w['scope'])['status']=='EXACT_NAME_CANDIDATE'
