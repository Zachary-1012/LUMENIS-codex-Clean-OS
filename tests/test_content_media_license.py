"""Isolated real media/HTTP license-declaration continuity; not legal or UI acceptance."""
import hashlib
import io
import json
import zipfile

import pytest

import shared_artifacts as artifacts
from tests.test_content_project_storage import media_store, rows  # noqa: F401
from tests.test_local_content_source_routes import local_client, SHARED_HEADERS, export_shared_project  # noqa: F401


def declaration(store, license_id="CC-BY-4.0"):
    # Synthetic fixture, not a claim about any upstream recording or person's voice.
    evidence = "Isolated test creator declares this generated tone under " + license_id
    return {"schema_version": 1, "object_kind": "media_asset", "license_id": license_id,
            "license_url": artifacts._MEDIA_LICENSE_URLS[license_id],
            "source_url": "https://example.invalid/isolated-tone", "source_version": "fixture-v1",
            "asset_sha256": hashlib.sha256(store["source"].read_bytes()).hexdigest(),
            "creator": "Isolated test creator", "title": "Generated test tone",
            "notice": "Synthetic fixture only", "changes": "",
            "evidence_text": evidence, "evidence_sha256": hashlib.sha256(evidence.encode()).hexdigest()}


def upload(client, store, value):
    headers = dict(SHARED_HEADERS)
    if value is not None:
        headers["X-Lumenis-Media-License"] = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)
    return client.post("/api/experience/content-sources?filename=" + store["source"].name, headers=headers,
                       data=store["source"].read_bytes(), content_type="application/octet-stream")


def approve(client, pending, confirmed=True):
    return client.post("/api/experience/content-source-confirmations/" + pending["confirmation"]["confirmation_id"],
                       headers=SHARED_HEADERS, json={"confirmed": confirmed})


def import_declared(client, store, value):
    pending = upload(client, store, value)
    assert pending.status_code == 403, pending.get_json()
    assert pending.get_json()["media_license"] == value
    assert pending.get_json()["confirmation"]["license_metadata_sha256"] == artifacts._media_license_digest(value)
    assert approve(client, pending.get_json()).status_code == 200
    imported = upload(client, store, value)
    assert imported.status_code == 201, imported.get_json()
    assert imported.get_json()["evidence_recorded"] is True
    return imported.get_json()["result"]


def project(client, store, imported, previous=None, timeline=None):
    from lumenis.shared.content_creation.video_editing import Timeline, fingerprint_local_media
    if timeline is None:
        asset = fingerprint_local_media(store["source"])
        timeline = Timeline.from_assets([asset]).add_audio_track("music", audio_role="bgm")
        timeline = timeline.add_clip(asset.asset_id, track_id="music", source_in=.1, source_out=.4)
    payload = {"asset_refs": [imported["artifact"]["artifact_id"]], "timeline": timeline.to_dict(), "output_kind": "audio"}
    if previous:
        payload["previous_artifact_id"] = previous
    response = export_shared_project(client, payload)
    assert response.status_code == 200, response.get_json()
    aid = response.get_json()["result"]["artifact"]["artifact_id"]
    detail = client.get(f"/api/experience/content-projects/{aid}", headers=SHARED_HEADERS)
    assert detail.status_code == 200, detail.get_json()
    package = client.get(detail.get_json()["package_url"], headers=SHARED_HEADERS)
    assert package.status_code == 200
    with zipfile.ZipFile(io.BytesIO(package.data)) as archive:
        result = {name: archive.read(name) for name in archive.namelist()}
    return aid, timeline, result, package.data, detail.get_json()["package_url"]


@pytest.mark.parametrize("license_id", ["CC0-1.0", "CC-BY-4.0"])
def test_declared_license_http_import_reopen_revision_credits(local_client, license_id):
    client, store, app = local_client
    value = declaration(store, license_id)
    imported = import_declared(client, store, value)
    sid = imported["artifact"]["artifact_id"]
    reopened = app.test_client().get(f"/api/experience/content-sources/{sid}", headers=SHARED_HEADERS)
    assert reopened.status_code == 200
    assert reopened.get_json()["result"] == imported
    assert imported["rights_state"] == imported["asset"]["rights_status"] == "unknown"
    assert imported["license_verification_state"] == "declared_not_independently_verified"
    pid, timeline, files, first_bytes, url = project(client, store, imported)
    credits = json.loads(files["credits.json"])
    saved = json.loads(files["project.json"])
    assert saved["media_credits"] == credits
    assert credits["sources"][0]["media_license"] == value
    assert credits["sources"][0]["artifact_sha256"] == imported["artifact"]["sha256"]
    assert credits["sources"][0]["actual_timeline_uses"][0]["clip"]["source_in"] == .1
    assert "not independently verified" in files["credits.txt"].decode()
    assert value["creator"] in files["credits.txt"].decode()
    revised = timeline.add_audio_track("second", audio_role="bgm")
    _, _, newer, _, _ = project(app.test_client(), store, imported, pid, revised)
    assert json.loads(newer["credits.json"])["timeline_version"] > credits["timeline_version"]
    assert client.get(url, headers=SHARED_HEADERS).data == first_bytes


def test_changed_declaration_requires_new_confirmation_and_preserves_source(local_client):
    client, store, _ = local_client
    value = declaration(store)
    pending = upload(client, store, value).get_json()
    assert approve(client, pending).status_code == 200
    changed = {**value, "source_version": "fixture-v2", "notice": "Corrected notice"}
    denied = upload(client, store, changed)
    assert denied.status_code == 403
    assert rows(store) == []
    original = upload(client, store, value)
    assert original.status_code == 201, original.get_json()
    original = original.get_json()["result"]
    assert approve(client, denied.get_json(), False).status_code == 200
    assert approve(client, denied.get_json()).status_code == 403
    newer = import_declared(client, store, changed)
    assert newer["artifact"]["artifact_id"] != original["artifact"]["artifact_id"]
    sid = original["artifact"]["artifact_id"]
    assert client.get(f"/api/experience/content-sources/{sid}", headers=SHARED_HEADERS).get_json()["result"] == original
    _, _, old_files, _, _ = project(client, store, original)
    _, _, new_files, _, _ = project(client, store, newer)
    assert json.loads(old_files["credits.json"])["sources"][0]["media_license"]["source_version"] == "fixture-v1"
    assert json.loads(new_files["credits.json"])["sources"][0]["media_license"]["source_version"] == "fixture-v2"


@pytest.mark.parametrize("change", [
    {"schema_version": True}, {"object_kind": "model"}, {"object_kind": "personal_voice_consent"},
    {"license_id": "MIT"}, {"creator": ""}, {"source_version": " "}, {"extra": True},
    {"source_url": "https://example.invalid/file?token=secret"},
    {"source_url": "https://name:password@example.invalid/file"}, {"source_url": "file:///tmp/file"},
    {"source_url": "https://example.invalid/\\nfile"}, {"asset_sha256": "0" * 64},
    {"evidence_sha256": "0" * 64}, {"evidence_text": "changed"},
    {"notice": "x" * 17000}, {"title": " padded "},
])
def test_invalid_declaration_never_approves_or_persists(local_client, change):
    client, store, _ = local_client
    response = upload(client, store, {**declaration(store), **change})
    assert response.status_code in (400, 403), response.get_json()
    assert "confirmation" not in response.get_json()
    assert rows(store) == []


@pytest.mark.parametrize("raw", ["", "null", "[]", '{"schema_version":1,"schema_version":1}', "NaN", "{" * 1000])
def test_malformed_header_denies(local_client, raw):
    client, store, _ = local_client
    response = upload(client, store, raw)
    assert response.status_code in (400, 403), response.get_json()
    assert rows(store) == []


def test_legacy_unknown_source_keeps_original_envelope(local_client):
    client, store, _ = local_client
    pending = upload(client, store, None).get_json()
    assert "license_metadata_sha256" not in pending["confirmation"]
    assert approve(client, pending).status_code == 200
    result = upload(client, store, None).get_json()["result"]
    assert set(result) == {"artifact", "asset"}
    _, _, files, _, _ = project(client, store, result)
    assert "credits.json" not in files
    assert "media_credits" not in json.loads(files["project.json"])


def test_header_does_not_allow_python_or_duplicate_key_evaluation(media_store):
    raw = json.dumps(declaration(media_store))
    with pytest.raises(artifacts.LocalArtifactError):
        artifacts.parse_media_license_header(raw[:-1] + ', "title": "other"}')
    with pytest.raises(artifacts.LocalArtifactError):
        artifacts.parse_media_license_header(raw.replace('Generated test tone', '\\ud800'))


def test_legacy_approval_cannot_authorize_declared_license(local_client):
    client, store, _ = local_client
    pending = upload(client, store, None).get_json()
    assert approve(client, pending).status_code == 200
    assert upload(client, store, declaration(store)).status_code == 403
    assert rows(store) == []
    assert upload(client, store, None).status_code == 201


@pytest.mark.parametrize("target", ["declaration", "media", "state", "unknown_key"])
def test_source_manifest_tampering_rejected_even_with_updated_outer_hash(local_client, target):
    client, store, _ = local_client
    imported = import_declared(client, store, declaration(store))
    aid = imported["artifact"]["artifact_id"]
    record = artifacts._artifact_record(aid)
    path = store["root"] / record["relative_path"]
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    metadata = json.loads(files["source.json"])
    if target == "declaration":
        metadata["media_license"]["creator"] = "Forged creator"
    elif target == "media":
        data = bytearray(files["voice.wav"]); data[-1] ^= 1; files["voice.wav"] = bytes(data)
    elif target == "state":
        metadata["rights_state"] = "commercial_allowed"
    else:
        metadata["unexpected"] = True
    files["source.json"] = artifacts._json_bytes(metadata)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with store["repository"].connect() as conn:
        conn.execute("UPDATE lumenis_shared_artifacts SET sha256=?,size_bytes=? WHERE artifact_id=?",
                     (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, aid))
    response = client.get(f"/api/experience/content-sources/{aid}", headers=SHARED_HEADERS)
    assert response.status_code != 200


def test_export_failure_leaves_prior_credits_and_output_intact(local_client, monkeypatch):
    client, store, _ = local_client
    imported = import_declared(client, store, declaration(store))
    aid, timeline, _, original, url = project(client, store, imported)
    old_rows = rows(store)
    import lumenis.shared.content_creation.rendering as rendering
    def cancelled(*args, **kwargs):
        raise artifacts.LocalArtifactError("CONTENT_EXPORT_PERMISSION_DENIED")
    monkeypatch.setattr(rendering, "render_timeline", cancelled)
    response = export_shared_project(client, {
        "asset_refs": [imported["artifact"]["artifact_id"]],
        "timeline": timeline.add_audio_track("new", audio_role="bgm").to_dict(),
        "output_kind": "audio", "previous_artifact_id": aid,
    })
    assert response.status_code != 200
    assert rows(store) == old_rows
    assert client.get(url, headers=SHARED_HEADERS).data == original


def test_real_loopback_http_and_independent_process_reopen(local_client):
    """Real socket transport and a fresh interpreter, with synthetic media input."""
    import os
    import subprocess
    import sys
    import threading
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from werkzeug.serving import make_server
    client, store, app = local_client
    class Response:
        def __init__(self, response):
            self.status_code = response.code
            self.data = response.read()
        def get_json(self):
            return json.loads(self.data)
    server = make_server("127.0.0.1", 0, app)
    class SocketClient:
        def call(self, path, *, method="GET", headers=None, data=None, json=None, content_type=None):
            headers = dict(headers or {})
            if json is not None:
                data = __import__("json").dumps(json).encode(); headers["Content-Type"] = "application/json"
            if content_type:
                headers["Content-Type"] = content_type
            req = Request(f"http://127.0.0.1:{server.server_port}" + path, data=data, headers=headers, method=method)
            try:
                with urlopen(req, timeout=30) as response:
                    return Response(response)
            except HTTPError as response:
                return Response(response)
        def post(self, path, **kwargs):
            return self.call(path, method="POST", **kwargs)
        def get(self, path, **kwargs):
            return self.call(path, **kwargs)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        client = SocketClient()
        imported = import_declared(client, store, declaration(store))
        aid, _, files, _, _ = project(client, store, imported)
        code = '''import json,sys
from flask import Flask
from lumenis.system.security.permission import resolve_local_workspace_principal
from shared_artifacts import read_content_source_artifact, read_content_project
app=Flask(__name__); app.config['LUMENIS_OPEN_WORKSPACE']=True
with app.test_request_context('/',environ_base={'REMOTE_ADDR':'127.0.0.1'},headers={'Host':'localhost'}):
 actor=resolve_local_workspace_principal(module='content',action='read')
 scope={'scope_kind':'shared_workspace','version':1}
 source=read_content_source_artifact(sys.argv[1],actor=actor,shared_workspace_scope=scope)
 project=read_content_project(sys.argv[2],actor=actor,shared_workspace_scope=scope)
 print(json.dumps({'source':source,'project':project}))
'''
        env = dict(os.environ, ZBC_DB_PATH=str(store["source"].parent / "media-store.sqlite3"),
                   ZBC_ARTIFACT_DIR=str(store["root"]))
        result = subprocess.run([sys.executable, "-c", code, imported["artifact"]["artifact_id"], aid],
                                env=env, text=True, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        reopened = json.loads(result.stdout.strip().splitlines()[-1])
        assert reopened["source"] == imported
        assert reopened["project"]["project"]["media_credits"] == json.loads(files["credits.json"])
    finally:
        server.shutdown(); thread.join(timeout=10); server.server_close()
        assert not thread.is_alive()


@pytest.mark.parametrize("target", ["omit_credits", "change_credit", "change_source_pin"])
def test_export_reopen_revalidates_credits_against_source(local_client, target):
    client, store, _ = local_client
    imported = import_declared(client, store, declaration(store))
    aid, _, files, _, _ = project(client, store, imported)
    saved = json.loads(files["project.json"])
    if target == "omit_credits":
        files.pop("credits.txt")
        saved["delivery_manifest"].pop("credits.txt")
    elif target == "change_credit":
        files["credits.txt"] = b"All rights granted without attribution\n"
        saved["delivery_manifest"]["credits.txt"] = {
            "sha256": hashlib.sha256(files["credits.txt"]).hexdigest(), "size_bytes": len(files["credits.txt"])}
    else:
        saved["media_credits"]["sources"][0]["artifact_sha256"] = "0" * 64
    files["project.json"] = artifacts._json_bytes(saved)
    record = artifacts._artifact_record(aid)
    path = store["root"] / record["relative_path"]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with store["repository"].connect() as conn:
        conn.execute("UPDATE lumenis_shared_artifacts SET sha256=?,size_bytes=? WHERE artifact_id=?",
                     (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, aid))
    assert client.get(f"/api/experience/content-projects/{aid}", headers=SHARED_HEADERS).status_code != 200
    assert client.get(f"/api/experience/content-projects/{aid}/package", headers=SHARED_HEADERS).status_code != 200
