"""Real isolated original storage/range contracts; no product-quality claim."""
import json
import struct
import zipfile

import pytest

import shared_artifacts as owner
from tests.test_content_project_storage import ACTOR, SCOPE, approve, import_source, media_store, rows  # noqa: F401
from tests.test_local_content_source_routes import local_client  # noqa: F401


def _long_wave(path, size=129 * 1024 * 1024):
    # An owned, silent, valid PCM recording. A sparse local file avoids allocating
    # an entire professional source in the test runner's memory.
    header = (b'RIFF' + struct.pack('<I', size + 36) + b'WAVEfmt '
              + struct.pack('<IHHIIHH', 16, 1, 1, 48000, 96000, 2, 16)
              + b'data' + struct.pack('<I', size))
    with path.open('wb') as target:
        target.write(header)
        target.truncate(size + len(header))


def test_large_original_manifest_range_reopen_and_same_content_reuse(media_store):
    _long_wave(media_store['source'])
    approve(media_store)
    imported = import_source(media_store)
    artifact_id, digest = imported['artifact']['artifact_id'], imported['asset']['sha256']
    _, record, _, package = owner._verified_content_source(artifact_id, actor=ACTOR, **SCOPE)
    assert package.stat().st_size < 65536
    with zipfile.ZipFile(package) as archive:
        assert archive.namelist() == ['source.json']
        metadata = json.loads(archive.read('source.json'))
        assert metadata['schema_version'] == 3
        assert metadata['media_storage']['size_bytes'] == media_store['source'].stat().st_size
    original = owner._content_original_path(digest)
    identity = owner._source_file_identity(original)
    media = owner.open_content_source_media(artifact_id, expected_sha256=digest, actor=ACTOR, **SCOPE)
    assert b''.join(media.iter_bytes(36, 52)) == b'data' + struct.pack('<I', 129 * 1024 * 1024) + b'\x00' * 8
    assert owner.read_content_source_artifact(artifact_id, actor=ACTOR, **SCOPE) == imported
    with owner.resolve_content_source_assets([artifact_id], actor=ACTOR, **SCOPE) as assets:
        linked = assets[0]['path']
        assert linked.stat().st_ino == original.stat().st_ino
        assert assets[0]['asset'].to_dict() == imported['asset']
    assert not linked.exists()
    assert original.is_file() and owner._source_file_identity(original)[:5] == identity[:5]
    assert owner._hash_file(original) == digest
    approve(media_store)
    second = import_source(media_store)
    assert second['artifact']['artifact_id'] != artifact_id
    assert owner._source_file_identity(original)[:5] == identity[:5]
    assert len(rows(media_store)) == 2
    assert record['media_size_bytes'] > 128 * 1024 * 1024
    with pytest.raises(owner.LocalArtifactError, match='STREAM_REQUIRED'):
        owner.read_content_source_media(artifact_id, expected_sha256=digest, actor=ACTOR, **SCOPE)


def test_storage_exhaustion_preserves_source_and_leaves_no_partial(media_store, monkeypatch):
    _long_wave(media_store['source'], size=9 * 1024 * 1024)
    approve(media_store)
    budget = owner.content_media_resource_budget()
    monkeypatch.setattr(owner, 'content_media_resource_budget', lambda: {**budget, 'available_bytes': 0})
    with pytest.raises(owner.LocalArtifactError, match='CONTENT_MEDIA_STORAGE_REQUIRED'):
        import_source(media_store)
    assert rows(media_store) == []
    assert media_store['source'].stat().st_size == 9 * 1024 * 1024 + 44
    assert list(media_store['root'].iterdir()) == []


def test_byte_receipt_accepts_large_exact_size_without_granting_it(boundary):
    from dataclasses import replace
    from tests.test_content_source_import_permission import check, resource
    gate, upload, _ = boundary
    changed = replace(upload, size_bytes=4 * 1024 * 1024 * 1024)
    assert resource(gate, changed) != resource(gate, upload)
    assert check(gate, changed).allowed is False


from tests.test_content_source_import_permission import boundary  # noqa: E402, F401


def test_explicit_proxy_and_waveform_cache_use_original_scope_and_keep_original(media_store):
    approve(media_store)
    original = import_source(media_store)
    artifact_id, digest = original['artifact']['artifact_id'], original['asset']['sha256']
    proxy = owner.prepare_content_source_preview(artifact_id, expected_sha256=digest,
                kind='proxy', actor=ACTOR, **SCOPE)
    assert proxy['preview_only'] is True and proxy['render_source'] == 'immutable_original'
    assert proxy['coverage']['complete'] is True
    opened = owner.open_content_source_media(artifact_id, expected_sha256=digest,
                preview_key=proxy['cache_key'], actor=ACTOR, **SCOPE)
    assert b''.join(opened.iter_bytes(4, 8)) == b'ftyp'
    assert opened.sha256 == proxy['sha256'] and opened.sha256 != digest
    assert owner.prepare_content_source_preview(artifact_id, expected_sha256=digest,
                kind='proxy', actor=ACTOR, **SCOPE) == proxy
    waveform = owner.prepare_content_source_preview(artifact_id, expected_sha256=digest,
                kind='waveform', actor=ACTOR, **SCOPE)
    opened = owner.open_content_source_media(artifact_id, expected_sha256=digest,
                preview_key=waveform['cache_key'], actor=ACTOR, **SCOPE)
    measured = json.loads(b''.join(opened.iter_bytes(0, opened.size_bytes)))
    assert len(measured['levels']) == 3 and measured['levels'][0]['decoded_samples'] > 0
    assert owner._hash_file(media_store['source']) == digest
    with pytest.raises(owner.LocalArtifactError, match='CONTEXT_MISMATCH'):
        owner.open_content_source_media(artifact_id, expected_sha256=digest,
            preview_key=proxy['cache_key'], actor={'id': 2}, **SCOPE)
    assert len(rows(media_store)) == 1


def test_project_package_and_media_head_range_exact_hash_and_context(local_client):
    from tests.test_local_content_source_routes import HEADERS, export_project, imported_audio_project
    client, store, _ = local_client
    saved = export_project(client, imported_audio_project(client, store))
    assert saved.status_code == 200, saved.get_json()
    identity = saved.get_json()['result']['artifact']['artifact_id']
    for kind in ('package', 'media'):
        route = f'/api/experience/content-projects/{identity}/{kind}'
        ordinary = client.get(route, headers=HEADERS)
        assert ordinary.status_code == 200
        context = json.dumps({key: value for key, value in HEADERS.items() if key != 'X-Lumenis-Action'})
        query = {'format': kind, 'context': context}
        head = client.head(route, query_string=query)
        assert head.status_code == 200 and head.data == b''
        assert head.headers['Content-Length'] == str(len(ordinary.data))
        assert head.headers['ETag'] == ordinary.headers['ETag']
        assert head.headers['Accept-Ranges'] == 'bytes'
        assert identity in head.headers['Content-Disposition']
        part = client.get(route, query_string=query, headers={'Range': 'bytes=5-24', 'If-Range': head.headers['ETag']})
        assert part.status_code == 206 and part.data == ordinary.data[5:25]
        assert part.headers['Content-Range'] == f'bytes 5-24/{len(ordinary.data)}'
        stale = client.get(route, query_string=query, headers={'Range': 'bytes=5-24', 'If-Range': '"stale"'})
        assert stale.status_code == 200 and stale.data == ordinary.data
        invalid = client.get(route, query_string=query, headers={'Range': 'bytes=999999999-'})
        assert invalid.status_code == 416
        assert client.head(route, headers={**HEADERS, 'X-Domain-Id': 'CTH', 'X-Product-Id': 'CTH'}).status_code == 403
        assert client.get(route, query_string={**query, 'sha256': '0' * 64}).status_code == 400
