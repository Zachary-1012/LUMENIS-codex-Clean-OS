import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_kos_scoped_execution import _registered, _approve_call


def test_professional_private_configuration_metrics_and_reopen(workspace):
    import kos_professional as owner
    import kos_ops
    ws=workspace;scope=_registered(ws);common={'actor':ws['actor'],'scope':scope,'platform':'xiaohongshu','account_id':'synthetic-account'}
    configured=_approve_call(ws,lambda:owner.configure_scoped_account(**common,enabled=True,account_name='Own test',request_id='professional-config-001'))
    assert configured['auth_status']=='UNKNOWN' and configured['platform_connection']=='NOT_VERIFIED'
    rows=[{'metric_date':'2026-10-17','likes':0,'views':None,'follower_gain':-2}]
    imported=_approve_call(ws,lambda:owner.import_scoped_metrics(**common,metrics=rows,request_id='professional-metrics-001'))
    assert imported['external_effect']=='not_performed'
    result=owner.read_scoped_metrics(**common)
    assert result['metrics'][0]['likes']==0 and result['metrics'][0]['views'] is None
    assert result['metrics'][0]['impressions'] is None and result['metrics'][0]['official_verification']=='NOT_VERIFIED'
    assert owner.import_scoped_metrics(**common,metrics=rows,request_id='professional-metrics-001')['replayed']
    _approve_call(ws,lambda:owner.configure_scoped_account(**common,enabled=False,request_id='professional-config-002',expected_version=1))
    assert owner.read_scoped_accounts(actor=ws['actor'],scope=scope)['accounts'][0]['state']=='LOCAL_DISABLED'
    assert len(owner.read_scoped_metrics(**common)['metrics'])==1
    with pytest.raises(ValueError,match='DISABLED'):
        owner.import_scoped_metrics(**common,metrics=rows,request_id='professional-metrics-002',expected_version=1)
    assert len(owner.read_scoped_metrics(**common)['versions'])==1


def test_professional_rejects_fake_verified_source_and_nan():
    import kos_professional as owner
    with pytest.raises(ValueError,match='ORIGIN'):
        owner.validate_private_payload('professional_metrics',{'platform':'x','account_id':'a','metrics':[],'source_kind':'OFFICIAL_VERIFIED'})
    with pytest.raises(ValueError,match='NUMBER'):
        owner.validate_private_payload('professional_metrics',{'platform':'x','account_id':'a','source_kind':'USER_DECLARED','metrics':[{'metric_date':'2026-10-17','likes':float('nan')}]})
