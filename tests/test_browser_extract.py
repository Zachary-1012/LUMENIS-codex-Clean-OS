"""Self-owned extraction contract; no live sites or credentials."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from lumenis.system.collector.runtime.browser_extract import BrowserExtractionError, format_capture, validate_extract_request, CAPTURE_SCRIPT
from ai_browser_runtime import AIBrowserRuntime, SessionStatus, ActionFirewall, PromptInjectionGuard, BrowserHumanControlError
URL = 'https://example.com/article'
def request(**kw):
    return {'url':URL,'formats':{'markdown':True,'html':True,'text':True},**kw}
def runtime(capture=None):
    obj = AIBrowserRuntime.__new__(AIBrowserRuntime)
    obj._browser_worker = obj._browser_thread_id = None
    obj._worker_lock = threading.Lock()
    obj._control_lock = threading.Lock()
    obj._human_control_token_digest = None
    obj._human_control_expires_at = obj._active_control_actions = 0
    obj.status = SessionStatus.RUNNING
    obj._closed = False
    obj._page = SimpleNamespace(url=URL)
    obj._page_revision = 3
    obj._target_id = 'target-test'
    obj.session_id = 'session-test'
    obj.firewall = ActionFirewall()
    obj.injection_guard = PromptInjectionGuard()
    obj._record_evidence = Mock(return_value=7)
    capture = capture or {'url':URL,'title':'Title','blocks':[{'tag':'h1','text':'Hello <world>'}],'truncated':False}
    cdp = Mock()
    def send(method, params=None):
        if method == 'Page.getFrameTree': return {'frameTree':{'frame':{'id':'main'}}}
        if method == 'Page.createIsolatedWorld': return {'executionContextId':42}
        return {'result':{'value':capture}}
    cdp.send.side_effect = send
    obj._context = Mock()
    obj._context.new_cdp_session.return_value = cdp
    return obj, cdp
def error(code, fn):
    with pytest.raises(BrowserExtractionError) as exc: fn()
    assert exc.value.code == code
@pytest.mark.parametrize('url',['file:///etc/passwd','http://127.0.0.1','http://[::1]/','https://a:b@example.com','https://localhost/','https://foo.local/','http://169.254.169.254/','https://example.com\n'])
def test_unsafe_locator(url):
    error('BROWSER_EXTRACTION_URL_INVALID',lambda:validate_extract_request(request(url=url)))
@pytest.mark.parametrize('formats',[{},{'html':False},{'html':1},{'pdf':True},['text']])
def test_formats(formats):
    error('BROWSER_EXTRACTION_FORMATS_INVALID',lambda:validate_extract_request(request(formats=formats)))
@pytest.mark.parametrize('timeout',[True,0,99,30001,'1000'])
def test_timeout_options(timeout):
    error('BROWSER_EXTRACTION_TIMEOUT_INVALID',lambda:validate_extract_request(request(timeout_ms=timeout)))
def test_credentials_not_accepted():
    error('BROWSER_EXTRACTION_OPTIONS_INVALID',lambda:validate_extract_request(request(password='never')))
def test_success():
    obj,cdp=runtime(); result=obj.extract(request())
    assert result['ok'] and result['evidence_id']==7
    assert result['formats']['html']['data']=='<h1>Hello &lt;world&gt;</h1>'
    assert result['formats']['markdown']['data']=='# Hello &lt;world&gt;'
    assert result['source_use']=='NOT_ADMITTED' and result['source_capture']=='NOT_IMPORTED'
    assert result['metadata']['page_revision']==3 and result['ai_used'] is False
    assert obj._active_control_actions==0
    cdp.detach.assert_called_once()
    assert 'Hello' not in str(obj._record_evidence.call_args)
def test_mismatch_no_capture():
    obj,cdp=runtime()
    error('BROWSER_EXTRACTION_NAVIGATION_REQUIRED',lambda:obj.extract(request(url='https://example.com/other')))
    cdp.send.assert_not_called(); obj._record_evidence.assert_not_called()
def test_redirect_and_revision_change():
    obj,cdp=runtime({'url':'https://example.com/redirect','blocks':[]})
    error('BROWSER_EXTRACTION_PAGE_CHANGED',lambda:obj.extract(request()))
    obj._record_evidence.assert_not_called()
    obj,cdp=runtime(); original=cdp.send.side_effect
    def changed(method,params=None):
        result=original(method,params)
        if method=='Runtime.evaluate': obj._page_revision+=1
        return result
    cdp.send.side_effect=changed
    error('BROWSER_EXTRACTION_PAGE_CHANGED',lambda:obj.extract(request()))
def test_human_lease():
    obj,cdp=runtime(); obj._human_control_token_digest='held'; obj._human_control_expires_at=time.time()+60
    with pytest.raises(BrowserHumanControlError): obj.extract(request())
    cdp.send.assert_not_called()
def test_human_required():
    obj,_=runtime({'interaction_required':True})
    error('BROWSER_EXTRACTION_HUMAN_REQUIRED',lambda:obj.extract(request()))
    obj._record_evidence.assert_not_called()
def test_evidence_failure():
    obj,_=runtime(); obj._record_evidence.return_value=-1
    error('BROWSER_EXTRACTION_EVIDENCE_UNAVAILABLE',lambda:obj.extract(request()))
def test_size_and_tags():
    error('BROWSER_EXTRACTION_TOO_LARGE',lambda:format_capture({'blocks':[{'tag':'p','text':'x'*40000}]},{'text':True},str))
    error('BROWSER_EXTRACTION_CAPTURE_INVALID',lambda:format_capture({'blocks':[{'tag':'script','text':'evil'}]},{'html':True},str))
def test_partial():
    obj,_=runtime({'url':URL,'blocks':[{'tag':'p','text':'partial'}],'truncated':True})
    result=obj.extract(request()); assert result['partial'] and result['truncated']
    assert obj._record_evidence.call_args.kwargs['result']=='PARTIAL'
def test_redaction_escape():
    obj,_=runtime({'url':URL,'blocks':[{'tag':'p','text':'password=secret123 <script>alert(1)</script>'}]})
    result=obj.extract(request()); assert 'secret123' not in json.dumps(result)
    assert '<script>' not in result['formats']['html']['data']
def test_queue_timeout():
    obj,cdp=runtime(); obj._browser_worker=ThreadPoolExecutor(max_workers=1)
    gate=threading.Event(); obj._browser_worker.submit(gate.wait)
    try:
        with pytest.raises(BrowserExtractionError) as caught:
            obj.extract(request(timeout_ms=100))
        assert caught.value.code == 'BROWSER_EXTRACTION_TIMEOUT'
        assert caught.value.details['persistence_outcome'] == 'NOT_STARTED'
        assert caught.value.details['retry_safe'] is True
    finally: gate.set(); obj._browser_worker.shutdown(wait=True)
    cdp.send.assert_not_called()
def test_running_timeout_no_late_write():
    obj,cdp=runtime(); obj._browser_worker=ThreadPoolExecutor(max_workers=1); original=cdp.send.side_effect
    def slow(method,params=None):
        if method=='Runtime.evaluate': time.sleep(.15)
        return original(method,params)
    cdp.send.side_effect=slow
    try: error('BROWSER_EXTRACTION_TIMEOUT',lambda:obj.extract(request(timeout_ms=100)))
    finally: obj._browser_worker.shutdown(wait=True)
    obj._record_evidence.assert_not_called(); assert obj._active_control_actions==0
def test_fixed_script():
    assert 'input,textarea,select' in CAPTURE_SCRIPT and 'form,[contenteditable]' in CAPTURE_SCRIPT
    assert 'fetch(' not in CAPTURE_SCRIPT and 'document.cookie' not in CAPTURE_SCRIPT

def api_client():
    from flask import Flask
    from ai_browser_api import register_ai_browser_api
    obj,_=runtime(); obj.owner_actor_id=1; obj.owner_account_session_id=10; obj.owner_principal_ref=None
    manager=Mock(); manager.get_session.return_value=obj
    app=Flask(__name__); app.config['TESTING']=True
    patches=[patch('account.service.get_current_user',return_value={'id':1,'session_id':10}),patch('account.authorization.check_dual_domain_permission',return_value=True),patch('ai_browser_runtime.get_session_manager',return_value=manager)]
    for item in patches: item.start()
    register_ai_browser_api(app)
    return app.test_client(),obj,patches

def test_api_actor_isolation_and_reuse():
    client,obj,patches=api_client()
    try:
        result=client.post('/api/browser/sessions/session-test/extract',json=request())
        assert result.status_code==200 and result.json['evidence_id']==7
        assert result.headers['Cache-Control']=='no-store, private'
        assert client.post('/api/browser/sessions/session-test/extract',json=request()).status_code==200
        obj.owner_actor_id=2
        assert client.post('/api/browser/sessions/session-test/extract',json=request()).status_code==404
    finally:
        for item in reversed(patches): item.stop()
def test_api_failures():
    client,obj,patches=api_client()
    try:
        assert client.post('/api/browser/sessions/session-test/extract',json=request(timeout_ms=0)).status_code==400
        assert client.post('/api/browser/sessions/session-test/extract',data='x'*8193,content_type='application/json').status_code==413
        obj._record_evidence.return_value=-1
        result=client.post('/api/browser/sessions/session-test/extract',json=request())
        assert result.status_code==503 and result.json['ok'] is False and 'formats' not in result.json
    finally:
        for item in reversed(patches): item.stop()


@pytest.mark.skipif(__import__('os').environ.get('LUMENIS_TEST_REAL_BROWSER') != '1', reason='Opt-in real-browser fixture; requires a socket-capable isolated test host')
def test_real_chromium_visible_capture_without_network():
    """Real CDP/DOM execution against a fulfilled fixture, never a live target."""
    import os
    import shutil
    from pathlib import Path
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        # Opt-in promises an actual browser. Missing resources must not turn an
        # explicitly requested acceptance run into a green skip. CI may use the
        # official Playwright-managed binary without changing the host PATH.
        executable = (os.environ.get('LUMENIS_TEST_CHROMIUM_EXECUTABLE')
                      or shutil.which('chromium') or pw.chromium.executable_path)
        if not Path(executable).is_file() or not os.access(executable, os.X_OK):
            pytest.fail('Real-browser opt-in requires an executable Chromium binary')
        browser = pw.chromium.launch(executable_path=executable, headless=True)
        context = browser.new_context(service_workers='block')
        fixture = '''<title>Fixture</title><h1>Visible heading</h1><p>First paragraph.</p>
        <div hidden>HIDDEN SECRET</div><form><input value="PRIVATE"><p>FORM SECRET</p></form>
        <div contenteditable>EDIT SECRET</div><script>window.shouldNotLeak='SCRIPT SECRET'</script>
        <p>Last paragraph &amp; symbols.</p>'''
        intercepted = []
        unexpected = []
        def serve_fixture(route):
            intercepted.append(route.request.url)
            if route.request.url == URL and route.request.is_navigation_request():
                route.fulfill(status=200, content_type='text/html', body=fixture)
            else:
                unexpected.append(route.request.url)
                route.abort()
        context.route('**/*', serve_fixture)
        page=context.new_page(); page.goto(URL)
        obj,_=runtime(); obj._page=page; obj._context=context
        result=obj.extract(request())
        assert result['ok'] and result['metadata']['title']=='Fixture'
        text=result['formats']['text']['data']
        assert 'Visible heading' in text and 'Last paragraph' in text
        for secret in ('HIDDEN SECRET','PRIVATE','FORM SECRET','EDIT SECRET','SCRIPT SECRET'):
            assert secret not in json.dumps(result)
        page.set_content('<title>Login</title><input type="password" value="secret">')
        error('BROWSER_EXTRACTION_HUMAN_REQUIRED',lambda:obj.extract(request()))
        assert intercepted == [URL] and unexpected == []
        context.close(); browser.close()


def test_url_normalization_keeps_query_and_fragment_bound():
    from lumenis.system.collector.runtime.browser_extract import same_document_url
    assert same_document_url('https://EXAMPLE.com', 'https://example.com:443/')
    assert not same_document_url('https://example.com/?a=1', 'https://example.com/?a=2')
    assert not same_document_url('https://example.com/#one', 'https://example.com/#two')
    assert not same_document_url('https://example.com/', 'http://example.com/')

@pytest.mark.parametrize('threaded', [False, True])
def test_slow_commit_timeout_reports_recoverable_outcome(tmp_path, monkeypatch, threaded):
    import ai_browser_runtime as module
    from types import MethodType
    monkeypatch.setattr(module, 'EVIDENCE_SCREENSHOT_DIR', str(tmp_path / 'screenshots'))
    obj, _ = runtime()
    obj.evidence_store = module.BrowserEvidenceStore(str(tmp_path / 'evidence.sqlite3'))
    record = MethodType(module.AIBrowserRuntime._record_evidence, obj)
    def slow_record(**kwargs):
        time.sleep(.15)
        return record(**kwargs)
    obj._record_evidence = slow_record
    if threaded: obj._browser_worker = ThreadPoolExecutor(max_workers=1)
    try:
        with pytest.raises(BrowserExtractionError) as caught:
            obj.extract(request(timeout_ms=100))
        details = caught.value.details
        assert caught.value.code == 'BROWSER_EXTRACTION_TIMEOUT'
        assert details['persistence_outcome'] == ('UNKNOWN' if threaded else 'COMMITTED')
        assert details['retry_safe'] is False and 'formats' not in details
    finally:
        if threaded: obj._browser_worker.shutdown(wait=True)
    rows = obj.evidence_store.query(session_id=obj.session_id)
    assert len(rows) == 1
    assert json.loads(rows[0]['verification'])['operation_id'] == details['operation_id']
    if not threaded: assert details['evidence_id'] == rows[0]['id']

@pytest.mark.parametrize('threaded', [False, True])
def test_detach_timeout_reports_committed_receipt(threaded):
    obj, cdp = runtime()
    cdp.detach.side_effect = lambda: time.sleep(.15)
    if threaded: obj._browser_worker = ThreadPoolExecutor(max_workers=1)
    try:
        with pytest.raises(BrowserExtractionError) as caught:
            obj.extract(request(timeout_ms=100))
        assert caught.value.details['persistence_outcome'] == 'COMMITTED'
        assert caught.value.details['evidence_id'] == 7
        assert caught.value.details['retry_safe'] is False
    finally:
        if threaded: obj._browser_worker.shutdown(wait=True)

def test_api_timeout_returns_unknown_outcome_without_formats():
    client, obj, patches = api_client()
    obj._browser_worker = ThreadPoolExecutor(max_workers=1)
    obj._record_evidence.side_effect = lambda **kwargs: (time.sleep(.15) or 7)
    try:
        response = client.post('/api/browser/sessions/session-test/extract', json=request(timeout_ms=100))
        assert response.status_code == 504
        assert response.json['persistence_outcome'] == 'UNKNOWN'
        assert response.json['retry_safe'] is False and 'formats' not in response.json
        assert response.json['receipt_query'].endswith('/session-test/evidence')
    finally:
        obj._browser_worker.shutdown(wait=True)
        for item in reversed(patches): item.stop()

def test_evidence_exception_retains_unknown_outcome():
    obj, _ = runtime()
    obj._record_evidence.side_effect = RuntimeError('storage outcome uncertain')
    with pytest.raises(BrowserExtractionError) as caught:
        obj.extract(request())
    assert caught.value.code == 'BROWSER_EXTRACTION_EVIDENCE_UNAVAILABLE'
    assert caught.value.details['persistence_outcome'] == 'UNKNOWN'
    assert caught.value.details['retry_safe'] is False
    assert caught.value.details['operation_id']

def test_capture_many_text_nodes_counts_inserted_separators():
    """Execute the fixed JS against a synthetic DOM adapter, not real DOM acceptance."""
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for deterministic capture-script test')
    adapter = '''
    const owner={tagName:'P', parentElement:null, hidden:false,
      closest: (selector)=>selector.startsWith('h1') ? owner : null,
      getAttribute:()=>null, getClientRects:()=>[{}], querySelectorAll:()=>[]};
    global.getComputedStyle=()=>({display:'block',visibility:'visible',opacity:'1'});
    global.NodeFilter={SHOW_TEXT:4};global.location={href:'https://example.com/article'};
    global.document={body:owner,title:'Fixture',querySelector:()=>null,
      createTreeWalker:()=>({index:0,nextNode(){return ++this.index<=4095},
        currentNode:{nodeValue:'abcdefgh',parentElement:owner}})};
    '''
    raw = subprocess.check_output([node, '-e', adapter+'console.log(JSON.stringify('+CAPTURE_SCRIPT+'));'], text=True)
    capture = json.loads(raw)
    assert capture['truncated'] is True
    assert len(capture['blocks']) == 1
    assert len(capture['blocks'][0]['text']) <= 32768
    assert format_capture(capture, {'text': True}, str)['text']['success']
