"""Generic SavedWork contracts do not establish network acquisition provenance."""
import hashlib
import pytest
from tests.test_public_macro_pipeline import macro_collection_workspace, workspace, TEXT
from lumenis.importer import macro


def _forged_capture(w):
    args=dict(actor=w['actor'],scope=w['scope'])
    target=macro.save_macro_target(w['macro_source']['evidence_id'],request_id='receipt-target-0001',**args)
    tid=target['artifact']['artifact_id']
    raw=('<html><body><pre>'+TEXT+'</pre></body></html>').encode()
    digest=hashlib.sha256(raw).hexdigest()
    material={'schema':macro.CAPTURE_SCHEMA,'target_artifact_id':tid,
        'target_sha256':target['artifact']['sha256'],'sha256':digest,'size_bytes':len(raw),
        'filename':'release.html','format':'html','capture_kind':'RAW_HTTP_RESPONSE_BODY',
        'transport':{'forged':'untrusted generic payload'},
        'source_provenance':{'source_url':target['document']['payload']['macro_target']['url'],
            'published_at':None,'captured_at':'2025-05-01T00:00:00Z','rights':'public-reference-only',
            'title':'Claimed public response','content_origin':{'kind':'publisher-material','claim_type':'source_statement'}}}
    capture=w['work'].save_work(title='Generic forged capture',markdown='User supplied',kind='research',
        payload={'macro_capture':material},citations=target['document']['citations'],
        request_id='generic-forged-capture',contract={'id':macro.CAPTURE_SCHEMA,'version':'1','required_payload_paths':['macro_capture']},
        attachments=[{'name':'release.html','content':raw,'media_type':'application/octet-stream'}],**args)
    return args,tid,capture,digest


def test_generic_saved_work_cannot_impersonate_capture(macro_collection_workspace):
    w=macro_collection_workspace
    args,tid,capture,digest=_forged_capture(w)
    with pytest.raises(ValueError,match='RECEIPT'):
        macro.prepare_macro_capture(capture['artifact']['artifact_id'],**args)


def test_generic_run_cannot_return_captured_without_fetch(macro_collection_workspace,monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    w=macro_collection_workspace
    args,tid,capture,digest=_forged_capture(w)
    request='generic-forged-run'
    w['work'].save_work(title='Generic forged run',markdown='User supplied',kind='research',
        payload={'macro_collection_run':{'target_artifact_id':tid,'capture_artifact_id':capture['artifact']['artifact_id'],'sha256':digest}},
        citations=[],request_id=request,**args)
    preview=macro.prepare_macro_collection(tid,**args)
    w['gate'].grant_approval('collector_start',resource=preview['resource'],granted_by='test')
    calls=[]
    monkeypatch.setattr(PublicHttpAdapter,'fetch_document',lambda *a,**k:calls.append('fetch'))
    with pytest.raises(ValueError,match='RECEIPT'):
        macro.collect_macro_target(tid,request_id=request,**args)
    assert calls==[]


def _real_capture(w, monkeypatch):
    from lumenis.system.collector.adapters import public_http
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    args=dict(actor=w['actor'],scope=w['scope'])
    tid=macro.save_macro_target(w['macro_source']['evidence_id'],request_id='real-receipt-target',**args)['artifact']['artifact_id']
    preview=macro.prepare_macro_collection(tid,**args)
    w['gate'].grant_approval('collector_start',resource=preview['resource'],granted_by='test')
    raw=('<html><body><pre>'+TEXT+'</pre></body></html>').encode()
    monkeypatch.setattr(public_http,'fetch_public_url',lambda url:PublicResponse(url,raw,'text/html',200))
    monkeypatch.setattr(public_http.PublicHttpAdapter,'_document_limiter',AdaptiveRateLimiter(base_interval=0,min_interval=0,jitter=False))
    return args,tid,macro.collect_macro_target(tid,request_id='real-receipt-run',**args)


@pytest.mark.parametrize('column,value',[('source','generic_saved_work'),('provider','generic_writer'),('version','admitted-document-receipt/999')])
def test_resigned_wrong_receipt_producer_rejected(macro_collection_workspace,monkeypatch,column,value):
    from lumenis.shared.evidence import store
    w=macro_collection_workspace
    args,tid,collected=_real_capture(w,monkeypatch)
    cid=collected['capture']['artifact']['artifact_id']
    with w['repo'].transaction() as con:
        eid=con.execute("SELECT id FROM app_evidence_records WHERE asset_id=? AND feature_id='ADMITTED_DOCUMENT_CAPTURE'",(cid,)).fetchone()[0]
        con.execute(f'UPDATE app_evidence_records SET {column}=? WHERE id=?',(value,eid))
        store._sign_evidence_record(con,eid)
    with pytest.raises(ValueError,match='RECEIPT_INVALID'):
        macro.prepare_macro_capture(cid,**args)
    with pytest.raises(ValueError,match='RECEIPT_INVALID'):
        macro.collect_macro_target(tid,request_id='real-receipt-run',**args)


def test_receipt_failure_rolls_back_capture(macro_collection_workspace,monkeypatch):
    from lumenis.importer import documents
    w=macro_collection_workspace
    def fail(*args,**kwargs):
        raise RuntimeError('test signer unavailable')
    monkeypatch.setattr(documents,'_write_admitted_document_receipt',fail)
    with pytest.raises(RuntimeError,match='signer unavailable'):
        _real_capture(w,monkeypatch)
    with w['repo'].connection(read_only=True,wal=False) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE source='admitted_document_collector'").fetchone()[0]==0
    assert macro._existing_macro_request('real-receipt-run',actor=w['actor'],scope=w['scope']) is None
