"""An image import/reopen keeps actual dimensions and no fabricated duration."""
import hashlib
import json
import re
import struct
import zlib

import pytest

from tests.test_local_content_source_routes import local_client, media_store, HEADERS, confirm
from shared_artifacts import resolve_content_source_assets, _source_asset_metadata_is_valid
from lumenis.system.security import permission as p


def _png(width=8, height=4):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + b'\x80\x20\x10' * width) * height)) + chunk(b'IEND', b''))


def test_image_import_reopen_bytes_dimensions_and_scope(local_client):
    api, _store, app = local_client
    payload = _png()
    url = '/api/experience/content-sources?filename=brief.png'
    initial = api.post(url, headers=HEADERS, data=payload, content_type='application/octet-stream')
    assert initial.status_code == 403, initial.get_json()
    assert confirm(api, initial.get_json()['confirmation']['confirmation_id']).status_code == 200
    imported = api.post(url, headers=HEADERS, data=payload, content_type='application/octet-stream')
    assert imported.status_code == 201, imported.get_json()
    result = imported.get_json()['result']
    asset, ref = result['asset'], result['artifact']['artifact_id']
    assert asset['duration_sec'] is None and asset['media_kind'] == 'image'
    assert asset['width'] == 8 and asset['height'] == 4
    assert asset['sha256'] == hashlib.sha256(payload).hexdigest()
    assert asset['rights_status'] == 'unknown'
    reopened = api.get('/api/experience/content-sources/' + ref, headers=HEADERS)
    assert reopened.get_json()['result']['asset'] == asset
    with app.test_request_context('/', headers=HEADERS, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = p.resolve_local_workspace_principal(module='content', action='read')
        with resolve_content_source_assets([ref], actor=actor, domain_id='zbmp', global_scope=True) as inputs:
            assert inputs[0]['path'].read_bytes() == payload
            assert inputs[0]['asset'].to_dict() == asset
    denied = api.get('/api/experience/content-sources/' + ref,
                     headers={**HEADERS, 'X-Domain-Id': 'CTH', 'X-Product-Id': 'CTH'})
    assert denied.status_code == 403


@pytest.mark.parametrize('changed', [{'duration_sec': 1}, {'width': 0}, {'width': True},
                                    {'height': 10000000}, {'rights_status': 'licensed'}])
def test_image_metadata_cannot_invent_duration_dimensions_or_rights(changed):
    from shared_artifacts import _ImageSourceAsset
    asset = _ImageSourceAsset('image.png', 'a' * 64, 8, 4).to_dict()
    assert _source_asset_metadata_is_valid(asset, 'image.png')
    assert not _source_asset_metadata_is_valid({**asset, **changed}, 'image.png')


@pytest.mark.parametrize('large_image', [False, True])
def test_report_job_analyzes_imported_image_reopens_signed_result_and_never_replays(local_client, monkeypatch, large_image):
    from canonical_data import ensure_canonical_table
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation.recorder import init_db
    from lumenis.shared.evidence import store as evidence_store
    from lumenis.system.ai_gateway import core

    api, store, app = local_client
    # The import-only fixture uses DB_WRITE for every route. Use the actual
    # operation resolver when exercising the reporting route in this test.
    import ast
    from pathlib import Path
    tree = ast.parse(Path('app.py').read_text(encoding='utf-8-sig'))
    resolver = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == '_pg_resolve_operation_type')
    namespace = {'OperationType': p.OperationType, 're': re}
    exec(compile(ast.Module(body=[resolver], type_ignores=[]), 'app.py', 'exec'), namespace)
    monkeypatch.setitem(app.before_request_funcs[None][0].__globals__, '_pg_resolve_operation_type',
                        namespace['_pg_resolve_operation_type'])
    with store['repository'].connect() as con:
        ensure_canonical_table(connection=con)
        apply_business_schema(con)
        evidence_store.ensure_evidence_schema(con)
        columns = {row[1] for row in con.execute('PRAGMA table_info(app_evidence_records)')}
        for name, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f' DEFAULT {default}' if default != 'NULL' else ''
                con.execute(f'ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}')
    init_db()
    payload = _png(1200, 1200) if large_image else _png()
    url = '/api/experience/content-sources?filename=brief.png'
    pending = api.post(url, headers=HEADERS, data=payload, content_type='application/octet-stream')
    assert confirm(api, pending.get_json()['confirmation']['confirmation_id']).status_code == 200
    imported = api.post(url, headers=HEADERS, data=payload, content_type='application/octet-stream')
    ref = imported.get_json()['result']['artifact']['artifact_id']
    monkeypatch.setattr(core, 'vision_chat', lambda *args, **kwargs: (None, 'ollama_error'))
    failed_response = api.post('/api/experience/reports/source-brief/generate', headers=HEADERS,
                               json={'image_source_ref': ref})
    assert failed_response.status_code == 200, failed_response.get_json()
    failed = failed_response.get_json()['result']
    assert failed['multimodal']['state'] == 'unavailable'
    assert failed['multimodal']['real_input_bound'] is False
    assert failed['requested_image_source_ref'] == ref
    calls = []

    def vision(system, user, image, **kwargs):
        import base64
        calls.append(kwargs)
        observed = base64.b64decode(image)
        if large_image:
            assert observed.startswith(b'\xff\xd8\xff') and observed != payload
        else:
            assert observed == payload
        assert kwargs['local_only'] is True
        return json.dumps({'visible_facts': ['A uniform reddish image.'],
                           'unverifiable': ['No brand can be identified.'],
                           'business_implications': []}), 'ollama'

    monkeypatch.setattr(core, 'vision_chat', vision)
    response = api.post('/api/experience/reports/source-brief/generate', headers=HEADERS,
                        json={'retry_media_job_id': failed['job_id']})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()['result']
    assert result['multimodal']['state'] == 'complete', result['multimodal']
    assert result['multimodal']['real_input_bound'] is True
    assert result['multimodal']['input_content_sha256'] == hashlib.sha256(payload).hexdigest()
    assert result['multimodal']['image_preprocessing'] == ('fit-1024-jpeg/1' if large_image else 'unchanged')
    assert result['multimodal']['evidence_ref'].startswith('app_evidence_records:')
    assert result['review_status'] == 'HUMAN_PENDING'
    assert result['retry_of_job_id'] == failed['job_id']
    assert api.get('/api/experience/reports/source-brief/jobs/' + failed['job_id'],
                   headers=HEADERS).get_json()['result'] == failed
    assert api.post('/api/experience/reports/source-brief/generate', headers=HEADERS,
                    json={'retry_media_job_id': result['job_id']}).status_code == 400
    assert {r['metric_name']: r['status'] for r in result['evaluation']['records']} == {
        'report_artifact_integrity': 'pass', 'source_evidence_grounding': 'unknown',
        'multimodal_analysis_integrity': 'pass',
    }
    reopened = api.get('/api/experience/reports/source-brief/jobs/' + result['job_id'], headers=HEADERS)
    assert reopened.get_json()['result'] == result
    retried = api.post('/api/experience/reports/source-brief/generate', headers=HEADERS,
                       json={'resume_job_id': result['job_id']})
    assert retried.get_json()['result'] == result
    assert len(calls) == 1
    denied = api.get('/api/experience/reports/source-brief/jobs/' + result['job_id'],
                     headers={**HEADERS, 'X-Domain-Id': 'CTH', 'X-Product-Id': 'CTH'})
    assert denied.status_code == 403
    evidence_id = int(result['multimodal']['evidence_ref'].split(':')[1])
    with store['repository'].connect() as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (evidence_id,))
    tampered = api.get('/api/experience/reports/source-brief/jobs/' + result['job_id'], headers=HEADERS)
    assert tampered.status_code != 200
