"""Real Flask/SQLite owners with a deterministic CDP fixture, not live-browser E2E."""
import json
from types import MethodType
from unittest.mock import Mock

from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_browser_extract import runtime, request, URL

HEADERS = {'X-Domain-Id': 'CTH', 'X-Lumenis-Context-Mode': 'GLOBAL_ALL'}


def test_extract_evidence_save_failure_retry_and_reopen(route_workspace, monkeypatch):
    import ai_browser_runtime as browser
    from ai_browser_api import register_ai_browser_api
    ws = route_workspace
    obj, _ = runtime()
    obj.owner_actor_id = obj.owner_account_session_id = None
    obj.owner_principal_ref = ws['actor'].principal_ref
    monkeypatch.setattr('account.service.get_current_user', lambda: None)
    monkeypatch.setattr(browser, 'EVIDENCE_SCREENSHOT_DIR', str(ws['root'] / 'screenshots'))
    obj.evidence_store = browser.BrowserEvidenceStore(str(ws['root'] / 'isolated.sqlite3'))
    obj._record_evidence = MethodType(browser.AIBrowserRuntime._record_evidence, obj)
    obj.engine_label = 'isolated-fixture'
    obj.task_binding_status = 'UNBOUND'
    obj.task_id = obj.run_id = None
    obj.idle_timeout = 600
    obj.max_lifetime = 3600
    manager = Mock()
    def create_fixture_session(**options):
        assert options['owner_principal_ref'] == ws['actor'].principal_ref
        assert options['user_data_dir'] is None and options['cdp_port'] == 9224
        return obj
    manager.create_session.side_effect = create_fixture_session
    def fixture_navigation(url, **kwargs):
        # Browser process only is a fixture; actual browser navigation is separately BLOCKED.
        obj._page.url = url
        return browser.ActionExecutionResult(success=True, action='navigate', result=browser.ActionResult.PASS)
    obj.navigate = fixture_navigation
    manager.get_session.side_effect = lambda sid: obj if sid == obj.session_id else None
    monkeypatch.setattr(browser, 'get_session_manager', lambda: manager)
    register_ai_browser_api(ws['app'])
    api = ws['api']
    created = api.post('/api/browser/sessions', headers=HEADERS, json={})
    assert created.status_code == 200, created.json
    assert created.json['session_id'] == obj.session_id
    navigated = api.post('/api/browser/sessions/session-test/navigate', headers=HEADERS, json={'url': URL})
    assert navigated.status_code == 200 and navigated.json['ok'], navigated.json
    response = api.post('/api/browser/sessions/session-test/extract', headers=HEADERS, json=request())
    assert response.status_code == 200, response.json
    extraction = response.json
    rows = obj.evidence_store.query(session_id=obj.session_id, action='extract')
    assert len(rows) == 1 and rows[0]['id'] == extraction['evidence_id']
    assert rows[0]['after_state_hash'] and rows[0]['result'] == 'PASS'
    assert 'Hello' not in json.dumps(rows)
    assert ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0] == 0
    body = {'title': 'Fixture browser research', 'kind': 'research',
            'markdown': extraction['formats']['markdown']['data'], 'citations': [],
            'request_id': 'browser-extract-note-0001',
            'payload': {'browser_note': {'schema': 'lumenis.browser-session-note/v1',
                'source_capture': extraction['source_capture'], 'source_use': extraction['source_use'],
                'source_verification': 'NOT_VERIFIED', 'task_binding': 'UNBOUND',
                'locator': extraction['metadata'], 'browser_evidence_id': extraction['evidence_id']}}}
    # Owner validation rejects invalid save without losing extraction or committing an artifact.
    failed = api.post('/api/experience/saved-work', headers=HEADERS, json={**body, 'kind': 'unsupported-kind'})
    assert failed.status_code == 400, failed.json
    assert ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0] == 0
    saved = api.post('/api/experience/saved-work', headers=HEADERS, json=body)
    assert saved.status_code == 200, saved.json
    artifact = saved.json['result']['artifact']['artifact_id']
    reopened = api.get('/api/experience/saved-work/' + artifact, headers=HEADERS)
    assert reopened.status_code == 200, reopened.json
    document = reopened.json['result']['document']
    assert document['markdown'] == body['markdown']
    assert document['payload']['browser_note'] == body['payload']['browser_note']
    assert document['citations'] == []
    assert document['payload']['browser_note']['source_use'] == 'NOT_ADMITTED'
    # Persisted evidence remains readable through a fresh owner instance.
    restarted = browser.BrowserEvidenceStore(str(ws['root'] / 'isolated.sqlite3'))
    assert restarted.query(session_id=obj.session_id)[0]['id'] == extraction['evidence_id']


def test_selected_capture_saved_and_cold_reopened_with_original_locator(workspace, monkeypatch):
    """Real persistence; temporary capture never substitutes for admitted Source."""
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.reporting import saved_work
    ws=workspace
    obj,_=runtime()
    import ai_browser_runtime as browser
    monkeypatch.setattr(browser,'EVIDENCE_SCREENSHOT_DIR',str(ws['root']/'screenshots'))
    obj.evidence_store=browser.BrowserEvidenceStore(str(ws['root']/'isolated.sqlite3'))
    obj._record_evidence=MethodType(browser.AIBrowserRuntime._record_evidence,obj)
    result=obj.capture_command({'command':'preview','request_id':'save-capture-0001',**request()})
    selected=obj.capture_command({'command':'select','capture_id':result['capture_id'],
                                 'block_id':'b0','start':0,'end':5})
    marker={'schema':'lumenis.browser-session-note/v1',
            'source_capture':'NOT_IMPORTED','source_use':'NOT_ADMITTED',
            'source_verification':'NOT_VERIFIED','task_binding':'UNBOUND',
            'locator':selected['metadata'], 'selection':selected['selection']['locator'],
            'browser_evidence_id':selected['evidence_id']}
    args={'title':'Selected browser research','kind':'research',
          'markdown':selected['selection']['markdown'],'payload':{'browser_note':marker},
          'citations':[],'request_id':'selected-work-save-0001','actor':ws['actor'],'scope':ws['scope']}
    saved=saved_work.save_work(**args)
    replay=saved_work.save_work(**args)
    assert replay['replayed'] and replay['artifact']['artifact_id']==saved['artifact']['artifact_id']
    artifact=saved['artifact']['artifact_id']
    # Drop all component state and read through a newly instantiated DB repository.
    obj._capture_previews.clear()
    cold_repository=DatabaseRepository(str(ws['root']/'isolated.sqlite3'))
    monkeypatch.setattr(saved_work,'get_repository',lambda:cold_repository)
    cold=saved_work.reopen_work(artifact,actor=ws['actor'],scope=ws['scope'])
    assert cold['document']['markdown']=='Hello'
    assert cold['document']['payload']['browser_note']==marker
    assert cold['document']['citations']==[]
    assert marker['locator']['url']==URL and marker['selection']['exact']=='Hello'
    assert marker['source_use']=='NOT_ADMITTED'
    cold_evidence=browser.BrowserEvidenceStore(str(ws['root']/'isolated.sqlite3'))
    rows=cold_evidence.query(session_id=obj.session_id,action='extract')
    assert len(rows)==1 and rows[0]['id']==selected['evidence_id']
from tests.test_saved_document_workflow import workspace

def test_browser_note_unverified(workspace):
 w=workspace
 marker={'schema':'lumenis.browser-session-note/v1','source_capture':'NOT_IMPORTED','source_use':'NOT_ADMITTED','source_verification':'NOT_VERIFIED','task_binding':'UNBOUND','locator':{'url':'https://example.com/forged','page_revision':999,'captured_at':'2026-01-01'},'selection':{'block_id':'b0','start':0,'end':6,'exact':'FORGED'},'browser_evidence_id':999999}
 result=w['work'].save_work(title='Synthetic audit note',kind='research',markdown='FORGED',payload={'browser_note':marker},citations=[],request_id='audit-forged-0001',actor=w['actor'],scope=w['scope'])
 reopened=w['work'].reopen_work(result['artifact']['artifact_id'],actor=w['actor'],scope=w['scope'])
 assert reopened['document']['payload']['browser_note']==marker
 print('Forged marker without any BrowserEvidence accepted and reopened')


def test_forged_note_does_not_supply_formal_citation(workspace):
    import pytest
    w = workspace
    with pytest.raises(w['work'].SavedWorkError) as caught:
        w['work'].save_work(title='Unverified reference', kind='research', markdown='FORGED',
            payload={'browser_note': {'browser_evidence_id': 999999}},
            citations=[{'evidence_id': 999999, 'start': 0, 'end': 6, 'quote': 'FORGED'}],
            request_id='formal-forged-0001', actor=w['actor'], scope=w['scope'])
    assert str(caught.value) == 'WORK_EVIDENCE_MISSING'


def _snapshot_fixture(ws, monkeypatch):
    import ai_browser_runtime as browser
    obj, _ = runtime({'url':URL,'blocks':[{'tag':'p','text':'中😀文 first'}, {'tag':'p','text':'second repeated'}]})
    obj.owner_actor_id = obj.owner_account_session_id = None
    obj.owner_principal_ref = ws['actor'].principal_ref
    monkeypatch.setattr(browser,'EVIDENCE_SCREENSHOT_DIR',str(ws['root']/'screenshots'))
    obj.evidence_store = browser.BrowserEvidenceStore(str(ws['root']/'isolated.sqlite3'))
    obj._record_evidence = MethodType(browser.AIBrowserRuntime._record_evidence,obj)
    capture = obj.capture_command({'command':'preview','request_id':'source-preview-0001',**request()})
    args = dict(actor=ws['actor'], scope=ws['scope'], capture_id=capture['capture_id'],
        request_id='source-admit-0001', rights='public-reference-only', intended_use='report_quote',
        rights_statement='Explicit synthetic fixture; no live publisher rights established.')
    return obj, capture, args


def _admitted_snapshot(ws, monkeypatch):
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    obj, capture, args = _snapshot_fixture(ws, monkeypatch)
    prepared = admit_browser_snapshot(obj, **args, prepare=True)
    token = ws['gate'].grant_approval('data_import',resource=prepared['resource'],granted_by='isolated-fixture')
    source = admit_browser_snapshot(obj, **args)
    return obj, capture, args, source, token


def _source_use_args(ws, source):
    return dict(actor=ws['actor'],scope=ws['scope'],source_evidence_ref=source['source_evidence_ref'],
        source_fingerprint=source['snapshot_sha256'],body_sha256=source['body_sha256'],
        source_version=source['source_version'],purpose='quote_reference')


def _approve_source_use(ws, source):
    with ws['repo'].connection() as con:
        decision=ws['gate'].prepare_browser_snapshot_use(**_source_use_args(ws,source),connection=con)
    assert decision.allowed, decision.reason
    return ws['gate'].grant_approval('collector_source_read',resource=decision.resource,granted_by='isolated-fixture')


def test_formal_snapshot_admit_quote_cold_reopen_and_revoke(workspace, monkeypatch):
    import pytest
    from lumenis.shared.database import DatabaseRepository
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    ws=workspace
    obj,capture,args,source,import_token=_admitted_snapshot(ws,monkeypatch)
    assert source['original_resource_sha256'] is None and source['canonical_ref'] is None
    with pytest.raises(ws['work'].SavedWorkError,match='BROWSER_SOURCE_USE_APPROVAL_REQUIRED'):
        ws['documents'].locate_quote(source['evidence_id'],actor=ws['actor'],scope=ws['scope'],start=1,end=2)
    use_token=_approve_source_use(ws,source)
    citation=ws['documents'].locate_quote(source['evidence_id'],actor=ws['actor'],scope=ws['scope'],start=1,end=2)['citation']
    assert citation['quote']=='😀'
    saved=ws['work'].save_work(title='Snapshot quote',kind='research',markdown='😀',payload={},citations=[citation],
        request_id='snapshot-note-0001',actor=ws['actor'],scope=ws['scope'])
    obj._capture_previews.clear()
    assert admit_browser_snapshot(obj,**args)['replayed']
    cold=DatabaseRepository(str(ws['root']/'isolated.sqlite3'))
    monkeypatch.setattr(ws['work'],'get_repository',lambda:cold)
    monkeypatch.setattr(ws['documents'],'get_repository',lambda:cold)
    reopened=ws['work'].reopen_work(saved['artifact']['artifact_id'],actor=ws['actor'],scope=ws['scope'])
    assert reopened['document']['citations'][0]['quote']=='😀'
    assert ws['gate'].revoke_approval(use_token)
    with pytest.raises(ws['work'].SavedWorkError,match='BROWSER_SOURCE_USE_APPROVAL_REQUIRED'):
        ws['work'].reopen_work(saved['artifact']['artifact_id'],actor=ws['actor'],scope=ws['scope'])
    _approve_source_use(ws,source)
    assert ws['work'].reopen_work(saved['artifact']['artifact_id'],actor=ws['actor'],scope=ws['scope'])
    assert ws['gate'].revoke_approval(import_token)
    with pytest.raises(ws['work'].SavedWorkError,match='IMPORT_APPROVAL_REQUIRED'):
        admit_browser_snapshot(obj,**args)


def test_snapshot_requires_exact_import_and_has_no_implicit_rights(workspace,monkeypatch):
    import pytest
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    ws=workspace;obj,cap,args=_snapshot_fixture(ws,monkeypatch)
    with pytest.raises(ws['work'].SavedWorkError,match='IMPORT_APPROVAL_REQUIRED'):
        admit_browser_snapshot(obj,**args)
    ws['gate'].grant_approval('data_import',resource=None,granted_by='isolated-fixture')
    with pytest.raises(ws['work'].SavedWorkError,match='IMPORT_APPROVAL_REQUIRED'):
        admit_browser_snapshot(obj,**args)
    with pytest.raises(ws['work'].SavedWorkError,match='ADMISSION_INVALID'):
        admit_browser_snapshot(obj,**{**args,'rights':'UNKNOWN'},prepare=True)
    assert ws['repo'].query_one("SELECT count(*) FROM app_evidence_records WHERE source='collector'")[0]==0


def test_snapshot_revocation_before_commit_rolls_back_evidence_and_files(workspace,monkeypatch):
    import pytest
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    ws=workspace;obj,cap,args=_snapshot_fixture(ws,monkeypatch)
    prepared=admit_browser_snapshot(obj,**args,prepare=True)
    token=ws['gate'].grant_approval('data_import',resource=prepared['resource'],granted_by='isolated-fixture')
    original=ws['work']._stage_bytes
    def revoke(*a,**kw):
        result=original(*a,**kw)
        ws['gate'].revoke_approval(token)
        return result
    monkeypatch.setattr(ws['work'],'_stage_bytes',revoke)
    with pytest.raises(ws['work'].SavedWorkError,match='IMPORT_APPROVAL_REQUIRED'):
        admit_browser_snapshot(obj,**args)
    assert ws['repo'].query_one("SELECT count(*) FROM app_evidence_records WHERE source='collector'")[0]==0
    assert ws['repo'].query_one("SELECT count(*) FROM lumenis_shared_artifacts")[0]==0
    assert not list((ws['root']/'artifacts').glob('*.json'))


def test_snapshot_request_conflict_and_current_session_owner(workspace,monkeypatch):
    import pytest
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    ws=workspace;obj,cap,args,source,token=_admitted_snapshot(ws,monkeypatch)
    with pytest.raises(ws['work'].SavedWorkError,match='REQUEST_CONFLICT'):
        admit_browser_snapshot(obj,**{**args,'rights_statement':'changed'})
    obj.owner_principal_ref='workspace:other'
    with pytest.raises(ws['work'].SavedWorkError,match='OWNER_MISMATCH'):
        admit_browser_snapshot(obj,**args)


def test_snapshot_new_permission_gate_requires_fresh_use_approval(workspace,monkeypatch):
    import pytest
    from lumenis.system.security import permission
    ws=workspace;obj,cap,args,source,token=_admitted_snapshot(ws,monkeypatch)
    _approve_source_use(ws,source)
    fresh=permission.PermissionGate();fresh.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission,'get_permission_gate',lambda:fresh)
    ws['gate']=fresh
    with pytest.raises(ws['work'].SavedWorkError,match='USE_APPROVAL_REQUIRED'):
        ws['documents'].locate_quote(source['evidence_id'],actor=ws['actor'],scope=ws['scope'],start=0,end=1)
    _approve_source_use(ws,source)
    assert ws['documents'].locate_quote(source['evidence_id'],actor=ws['actor'],scope=ws['scope'],start=0,end=1)['citation']['quote']=='中'


def test_snapshot_two_requests_one_durable_source(workspace,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    ws=workspace;obj,cap,args=_snapshot_fixture(ws,monkeypatch)
    prepared=admit_browser_snapshot(obj,**args,prepare=True)
    ws['gate'].grant_approval('data_import',resource=prepared['resource'],granted_by='isolated-fixture')
    def run():
        with ws['app'].test_request_context('/',headers={'Host':'localhost'},environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
            return admit_browser_snapshot(obj,**args)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda _:run(),range(2)))
    assert outcomes[0]['evidence_id']==outcomes[1]['evidence_id']
    assert sum(not x['replayed'] for x in outcomes)==1
    assert ws['repo'].query_one("SELECT count(*) FROM app_evidence_records WHERE feature_id='COLLECTED_SOURCE'")[0]==1
    assert ws['repo'].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='collected_source'")[0]==1


def test_snapshot_commit_acknowledgement_failure_preserves_durable_bytes(workspace,monkeypatch):
    import pytest
    from contextlib import contextmanager
    from lumenis.shared import database
    from lumenis.system.collector.adapters.secondary_collection import admit_browser_snapshot
    from lumenis.system.collector.runtime.browser_extract import BrowserExtractionError
    ws=workspace;obj,cap,args=_snapshot_fixture(ws,monkeypatch)
    prepared=admit_browser_snapshot(obj,**args,prepare=True)
    ws['gate'].grant_approval('data_import',resource=prepared['resource'],granted_by='isolated-fixture')
    original=ws['repo']
    class Connection:
        def __init__(self,con): self.con=con
        def __getattr__(self,name): return getattr(self.con,name)
        def commit(self):
            self.con.commit()
            raise RuntimeError('injected acknowledgement failure')
    original_transaction = original.transaction
    @contextmanager
    def transaction():
        with original_transaction() as con: yield Connection(con)
    monkeypatch.setattr(original, 'transaction', transaction)
    monkeypatch.setattr(database,'get_repository',lambda:original)
    # The Permission scope reader requires a real SQLite connection. Inject only
    # at final commit, retaining actual scope checks with the underlying handle.
    import lumenis.system.collector.adapters.secondary_collection as collector
    admit=collector._browser_import_admitted
    monkeypatch.setattr(collector,'_browser_import_admitted',lambda actor,scope,resource,connection=None:
        admit(actor,scope,resource,connection=getattr(connection,'con',connection)))
    with pytest.raises(BrowserExtractionError) as caught:
        admit_browser_snapshot(obj,**args)
    assert caught.value.code=='BROWSER_SOURCE_COMMIT_UNKNOWN'
    monkeypatch.setattr(original,'transaction',original_transaction)
    assert admit_browser_snapshot(obj,**args)['replayed']
    assert ws['repo'].query_one("SELECT count(*) FROM app_evidence_records WHERE feature_id='COLLECTED_SOURCE'")[0]==1


def test_source_api_preparation_import_and_current_use(workspace,monkeypatch):
    import ai_browser_runtime as browser
    from ai_browser_api import register_ai_browser_api
    ws=workspace;obj,cap,args=_snapshot_fixture(ws,monkeypatch)
    import subject_registry
    with ws['repo'].transaction() as con: subject_registry.ensure_schema(con)
    monkeypatch.setattr('account.service.get_current_user',lambda:None)
    manager=Mock();manager.get_session.side_effect=lambda sid:obj if sid==obj.session_id else None
    monkeypatch.setattr(browser,'get_session_manager',lambda:manager)
    register_ai_browser_api(ws['app'])
    api=ws['app'].test_client();url='/api/browser/sessions/'+obj.session_id+'/capture'
    body={k:v for k,v in args.items() if k not in ('actor','scope')}
    prepared=api.post(url,headers=HEADERS,json={'command':'source_prepare',**body})
    assert prepared.status_code==200,prepared.json
    ws['gate'].grant_approval('data_import',resource=prepared.json['resource'],granted_by='isolated-fixture')
    imported=api.post(url,headers=HEADERS,json={'command':'source_import',**body})
    assert imported.status_code==200,imported.json
    source=imported.json
    use={k:v for k,v in _source_use_args(ws,source).items() if k not in ('actor','scope')}
    prepared_use=api.post(url,headers=HEADERS,json={'command':'source_use_prepare',**use})
    assert prepared_use.status_code==200,prepared_use.json
    assert prepared_use.json['source_use']=='NOT_ADMITTED'
    obj.owner_principal_ref='workspace:other'
    denied=api.post(url,headers=HEADERS,json={'command':'source_use_prepare',**use})
    assert denied.status_code==404
