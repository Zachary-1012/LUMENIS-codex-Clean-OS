import hashlib
import json
import pytest
from tests.test_saved_document_workflow import workspace

PRIVATE = {"scope_kind": "shared_workspace", "version": 1}


def make_source(ws, private):
    from openpyxl import Workbook
    path = ws['root'] / '原行.xlsx'
    book = Workbook(); sheet = book.active; sheet.title = '第一頁'
    sheet.append(['title', 'flag', 'count', 'missing'])
    sheet.append(['同名', False, 0, None]); sheet.append(['同名', True, 2, None])
    sheet = book.create_sheet('第二頁😀'); sheet.append(['title', 'flag', 'count', 'missing'])
    sheet.append(['真实第二页', False, 0, None]); book.save(path)
    if private:
        result = ws['documents'].save_private_document(str(path), actor=ws['actor'], scope=PRIVATE, request_id='page-private-001')
        ref = result['artifact']['artifact_id']; scope = PRIVATE
        route = '/api/experience/saved-work/' + ref
        version = ref
    else:
        scope = ws['scope']; args = dict(actor=ws['actor'], scope=scope,
            provenance={'published_at': None, 'source_url': 'https://example.org/', 'captured_at': '2026-10-18T00:00:00Z',
                        'rights': 'public-reference-only', 'title': 'Generated original rows'})
        resource = ws['documents'].document_import_resource(str(path), **args)
        ws['gate'].grant_approval('data_import', resource=resource, granted_by='isolated-test')
        result = ws['documents'].import_document(str(path), **args)
        ref = result['evidence_id']; version = result['source_artifact_ref']
        route = '/api/experience/materials/documents/' + str(ref)
    return ref, scope, route, dict(offset=0, limit=2, source_version=version,
                                 source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.mark.parametrize('private', [False, True])
def test_real_all_sheet_pages_are_exact_and_read_only(workspace, private):
    ws = workspace; ref, scope, route, params = make_source(ws, private)
    from lumenis.importer.analyzer import extract_source_rows
    from lumenis.importer.parser import parse_file
    expected = extract_source_rows(parse_file(str(ws['root'] / '原行.xlsx')))
    db = ws['root'] / 'isolated.sqlite3'; before = db.read_bytes()
    read = lambda **kw: ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **{**params, **kw})
    pages = [read(offset=n) for n in range(0, len(expected), 2)]
    rows = [r for page in pages for r in page['source_rows']]
    assert [r['raw_chunk'] for r in rows] == [r.raw_chunk for r in expected]
    assert [r['index'] for r in rows] == list(range(len(expected)))
    assert any(r['source_locator'].get('sheet_name') == '第二頁😀' for r in rows)
    content = json.dumps(rows, ensure_ascii=False)
    assert 'false' in content and 'null' in content and '真实第二页' in content
    values = rows[1]['source_record']['values']
    assert values[1]['value'] is False and type(values[2]['value']) is int and values[2]['value'] == 0 and values[3]['value'] is None
    assert any('0' in r['raw_chunk'] for r in rows)
    assert pages[0]['has_more'] is True and pages[-1]['has_more'] is False
    assert read(offset=len(expected))['source_rows'] == []
    assert read() == read()
    assert db.read_bytes() == before
    import experience_runtime
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    headers = {'X-Lumenis-Workspace-Scope': json.dumps(scope)} if private else {'X-Domain-Id': 'cth', 'X-Lumenis-Context-Mode': 'GLOBAL_ALL'}
    response = ws['app'].test_client().get(route, query_string=params, headers=headers)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['result']['source_rows'] == pages[0]['source_rows']
    assert db.read_bytes() == before


@pytest.mark.parametrize('private', [False, True])
def test_version_hash_and_permission_changes_fail_closed(workspace, private, monkeypatch):
    ws=workspace; ref, scope, route, params=make_source(ws, private)
    read=lambda **kw: ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **{**params, **kw})
    with pytest.raises(ValueError, match='VERSION_CHANGED'): read(source_sha256='0'*64)
    with pytest.raises(ValueError, match='VERSION_CHANGED'): read(source_version='different-artifact')
    # Current workspace authorization is rechecked, not cached by a page token.
    from lumenis.shared.reporting import saved_work
    original = saved_work.authorize_saved_work if private else ws['documents'].authorize
    def deny(*args, **kwargs): raise PermissionError('synthetic-revocation')
    if private: monkeypatch.setattr(saved_work, 'authorize_saved_work', deny)
    else: monkeypatch.setattr(ws['documents'], 'authorize', deny)
    with pytest.raises(PermissionError): read(offset=2)


@pytest.mark.parametrize('params', [
    {'offset': '-1'}, {'offset': '100001'}, {'limit': '0'}, {'limit': '101'},
    {'offset': '١'}, {'limit': '1.0'}, {'offset': '9999999'},
    {'source_sha256': 'bad'}, {'source_version': ''}, {'extra': 'no'},
])
def test_http_invalid_pages(workspace, params):
    ws=workspace; ref, scope, route, valid=make_source(ws, True)
    import experience_runtime
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    response=ws['app'].test_client().get(route, query_string={**valid, **params},
        headers={'X-Lumenis-Workspace-Scope': json.dumps(scope)})
    assert response.status_code == 400, response.get_json()
    assert 'source_rows' not in response.get_json()


def test_duplicate_missing_and_mixed_parameters(workspace):
    ws=workspace; ref, scope, route, params=make_source(ws, True)
    import experience_runtime
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    client=ws['app'].test_client(); headers={'X-Lumenis-Workspace-Scope': json.dumps(scope)}
    cases=[list(params.items())+[('offset','1')], [('offset','0')], list(params.items())+[('selection_start','0')]]
    for query in cases:
        response=client.get(route, query_string=query, headers=headers)
        assert response.status_code == 400, response.get_json()


def test_current_private_revision_withdraws_old_page(workspace):
    ws=workspace; ref, scope, route, params=make_source(ws, True)
    old=ws['work'].reopen_work(ref, actor=ws['actor'], scope=scope)
    ws['work'].save_work(title='Revision', markdown='Current revision.', kind='research',
        payload=old['document']['payload'], citations=[], request_id='page-revision-001',
        actor=ws['actor'], scope=scope, work_id=old['document']['work_id'],
        previous_artifact_id=ref, expected_draft_digest=old['document']['draft_digest'])
    with pytest.raises(PermissionError, match='VERSION_CHANGED'):
        ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **params)


@pytest.mark.parametrize('private', [False, True])
def test_original_bytes_tampered_under_same_artifact_are_rejected(workspace, private):
    ws=workspace; ref, scope, route, params=make_source(ws, private)
    ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **params)
    if private:
        item=ws['work'].read_committed_work(ref, actor=ws['actor'], scope=scope)
        attachment=item['document']['attachments'][0]
        # Resolve the actual original-byte file through existing ART metadata.
        files=list((ws['root']/'artifacts').rglob('*'))
        targets=[p for p in files if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==params['source_sha256']]
    else:
        targets=[p for p in (ws['root']/'artifacts').rglob('*') if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==params['source_sha256']]
    assert targets
    targets[0].write_bytes(b'corrupt original source')
    with pytest.raises((ValueError, PermissionError)):
        ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **params)


@pytest.mark.parametrize('private', [False, True])
def test_real_workspace_revocation_blocks_next_page(workspace, private):
    ws=workspace; ref, scope, route, params=make_source(ws, private)
    ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **params)
    ws['app'].config['LUMENIS_OPEN_WORKSPACE']=False
    with pytest.raises((ValueError, PermissionError)):
        ws['documents'].read_document_source_rows(ref, actor=ws['actor'], scope=scope, **{**params, 'offset':2})
