"""Isolated private professional-account history parity; no platform calls."""
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_kos_scoped_execution import _registered, _approve_call


@pytest.fixture
def professional(workspace):
    import kos_professional as owner
    ws=workspace
    scope=_registered(ws)
    common={'actor':ws['actor'],'scope':scope,'platform':'xiaohongshu','account_id':'account-a'}
    _approve_call(ws,lambda:owner.configure_scoped_account(**common,enabled=True,request_id='config-start-001'))
    return owner,ws,common


def test_incremental_dates_retain_history_and_replace_exact_day(professional):
    owner,ws,args=professional
    first=[{'metric_date':'2026-10-16','likes':4,'views':90}]
    second=[{'metric_date':'2026-10-17','likes':8}]
    for version,rows in enumerate((first,second)):
        _approve_call(ws,lambda:owner.import_scoped_metrics(**args,metrics=rows,request_id=f'metrics-day-{version:03}',expected_version=version))
    result=owner.read_scoped_metrics(**args)
    assert {r['metric_date']:r['likes'] for r in result['metrics']}=={'2026-10-16':4,'2026-10-17':8}
    assert len(owner.read_scoped_metrics(**args,start_date='2026-10-16',end_date='2026-10-16')['metrics'])==1
    changed=[{'metric_date':'2026-10-16','likes':0,'views':None}]
    _approve_call(ws,lambda:owner.import_scoped_metrics(**args,metrics=changed,request_id='metrics-correction-003',expected_version=2))
    recovered=owner.read_scoped_metrics(**args)
    day1=next(r for r in recovered['metrics'] if r['metric_date']=='2026-10-16')
    assert day1['likes']==0 and day1['views'] is None and day1['version']==3
    assert len(recovered['metrics'])==2 and len(recovered['versions'])==3
    assert owner.import_scoped_metrics(**args,metrics=changed,request_id='metrics-correction-003',expected_version=2)['replayed']
    assert owner.read_scoped_metrics(**args)['metrics']==recovered['metrics']


def test_old_account_is_not_evicted_by_200_newer_versions(professional):
    owner,ws,args=professional
    second={**args,'account_id':'account-b'}
    for version in range(201):
        _approve_call(ws,lambda:owner.configure_scoped_account(**second,enabled=version%2==0,request_id=f'config-repeated-{version:03}',expected_version=version))
    rows=owner.read_scoped_accounts(actor=args['actor'],scope=args['scope'])['accounts']
    assert {r['account_id'] for r in rows}=={'account-a','account-b'}
    assert next(r for r in rows if r['account_id']=='account-b')['version']==201


def test_full_history_has_explicit_resource_limit_and_unchanged_default(professional, monkeypatch):
    import kos_ops
    owner,ws,args=professional
    for version in range(3):
        _approve_call(ws,lambda:owner.import_scoped_metrics(**args,metrics=[{'metric_date':f'2026-10-{version+1:02}','likes':version}],request_id=f'budget-metrics-{version:03}',expected_version=version))
    assert len(kos_ops.read_scoped_operations(actor=args['actor'],scope=args['scope'],operation='professional_metrics',limit=2)['items'])==2
    monkeypatch.setattr(kos_ops,'_SCOPED_HISTORY_MAX_ROWS',2)
    with pytest.raises(kos_ops.ScopedOperationHistoryLimitError,match='RESOURCE_LIMIT'):
        owner.read_scoped_metrics(**args)
    monkeypatch.setattr(kos_ops,'_SCOPED_HISTORY_MAX_ROWS',10000)
    monkeypatch.setattr(kos_ops,'_SCOPED_HISTORY_MAX_BYTES',1)
    with pytest.raises(kos_ops.ScopedOperationHistoryLimitError,match='RESOURCE_LIMIT'):
        owner.read_scoped_metrics(**args)
    with pytest.raises(ValueError,match='HISTORY_MODE'):
        kos_ops.read_scoped_operations(actor=args['actor'],scope=args['scope'],complete_history='true')


def test_metric_date_before_hundred_versions_is_retained(professional):
    from datetime import date,timedelta
    owner,ws,args=professional
    for version in range(102):
        row={'metric_date':(date(2026,1,1)+timedelta(days=version)).isoformat(),'likes':version}
        _approve_call(ws,lambda:owner.import_scoped_metrics(**args,metrics=[row],request_id=f'long-metrics-{version:03}',expected_version=version))
    result=owner.read_scoped_metrics(**args,start_date='2026-01-01',end_date='2026-01-01')
    assert len(result['metrics'])==1 and result['metrics'][0]['likes']==0
    assert len(result['versions'])==102


def test_older_chain_tamper_and_scope_isolation(professional):
    import json
    from subject_registry import add_subject
    owner,ws,args=professional
    for version in range(2):
        _approve_call(ws,lambda:owner.import_scoped_metrics(**args,metrics=[{'metric_date':f'2026-10-{version+1:02}','likes':version+2}],request_id=f'tamper-metrics-{version:03}',expected_version=version))
    brand=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Other scope','name_zh':'其他范围'})[0]
    other={**args,'scope':{**args['scope'],'brand_focus_id':brand['brand_focus_id']}}
    assert owner.read_scoped_metrics(**other)['metrics']==[]
    with ws['repo'].transaction() as con:
        record=con.execute("SELECT id,note FROM kos_operations WHERE action='scoped_professional_metrics' ORDER BY id LIMIT 1").fetchone()
        value=json.loads(record['note']);value['payload']['metrics'][0]['likes']=999
        con.execute('UPDATE kos_operations SET note=? WHERE id=?',(json.dumps(value),record['id']))
    with pytest.raises(ValueError,match='INTEGRITY_FAILED'):
        owner.read_scoped_metrics(**args)


def test_real_http_incremental_approval_reopen_and_revocation(professional, monkeypatch):
    import json,threading,urllib.request,urllib.error,os
    from pathlib import Path
    from werkzeug.serving import make_server
    from lumenis.system.security import permission
    import kos_routes,kos_ops
    owner,ws,args=professional
    ws['app'].register_blueprint(kos_routes.kos_bp)
    ws['gate'].grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    server=make_server('127.0.0.1',0,ws['app'])
    thread=threading.Thread(target=server.serve_forever);thread.start()
    headers={'Content-Type':'application/json','X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':'HCG-SUBJECT'}
    receipts=[]
    def invoke(path,payload=None):
        request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/kos/'+path,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
        try:
            with urllib.request.urlopen(request,timeout=10) as response:
                status,data=response.status,json.load(response)
        except urllib.error.HTTPError as response:
            status,data=response.code,json.load(response)
        receipts.append({'path':path,'status':status,'write':payload is not None})
        return status,data
    last=None
    try:
        for version in range(2):
            payload={'platform':'xiaohongshu','account_id':'account-a','metrics':[{'metric_date':f'2026-10-{version+1:02}','likes':version+3}],'request_id':f'http-metrics-{version:03}','expected_version':version}
            status,needed=invoke('professional/import',payload)
            assert status==403 and needed['code']=='KOS_OPERATION_APPROVAL_REQUIRED'
            assert invoke('approvals/confirm',{'challenge':needed['challenge'],'confirm':True})[0]==200
            status,result=invoke('professional/import',payload)
            assert status==200 and result['external_effect']=='not_performed'
            last=payload
        status,reopened=invoke('professional/metrics?platform=xiaohongshu&account_id=account-a')
        assert status==200 and len(reopened['metrics'])==2
        assert invoke('professional/import',last)[1]['replayed']
        assert invoke('professional/metrics?platform=xiaohongshu&account_id=account-a&start_date=2026-10-01&end_date=2026-10-01')[1]['metrics'][0]['likes']==3
        monkeypatch.setattr(kos_ops,'_SCOPED_HISTORY_MAX_ROWS',1)
        status,limited=invoke('professional/metrics?platform=xiaohongshu&account_id=account-a')
        assert status==503 and limited['code']=='KOS_OPERATION_HISTORY_RESOURCE_LIMIT' and 'metrics' not in limited
        monkeypatch.setattr(kos_ops,'_SCOPED_HISTORY_MAX_ROWS',10000)
        ws['repo'].execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id='HCG-SUBJECT'")
        assert invoke('professional/metrics?platform=xiaohongshu&account_id=account-a')[0]>=400
        ws['repo'].execute("UPDATE lumenis_subject_registry SET status='active' WHERE subject_id='HCG-SUBJECT'")
        assert invoke('professional/metrics?platform=xiaohongshu&account_id=account-a')[1]['metrics']==reopened['metrics']
    finally:
        server.shutdown();thread.join(timeout=10);server.server_close()
        assert not thread.is_alive()
    if os.environ.get('LUMENIS_VALIDATION_ROOT'):
        Path(os.environ['LUMENIS_VALIDATION_ROOT'],'results/professional-http-receipts.json').write_text(json.dumps(receipts,indent=2))
