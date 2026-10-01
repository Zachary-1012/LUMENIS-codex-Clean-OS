from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify

from lumenis.system.runtime.workspace_host import WorkspaceHost, register_workspace_host


def _write_build(root: Path, *, include_hashed_asset: bool = False) -> Path:
    build = root / "build" / "web"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text(
        '<!doctype html><title>LUMENIS Workspace</title>', encoding="utf-8"
    )
    (build / "main.dart.js").write_text("console.log('workspace');", encoding="utf-8")
    (build / "flutter_bootstrap.js").write_text("// bootstrap", encoding="utf-8")
    (build / "assets" / "AssetManifest.json").write_text("{}", encoding="utf-8")
    if include_hashed_asset:
        (build / "assets" / "font-0123456789abcdef.woff2").write_bytes(b"font")
    return build


def _app(build_dir: Path) -> Flask:
    app = Flask(__name__)
    register_workspace_host(app, build_dir)

    @app.get("/api/ping")
    def api_ping():
        return jsonify(ok=True, owner="product-core")

    return app


def test_workspace_document_and_asset_routes_are_same_origin(tmp_path: Path):
    client = _app(_write_build(tmp_path)).test_client()

    root = client.get("/workspace")
    deep_link = client.get("/workspace/CTH-01/CTH-02")
    trailing_deep_link = client.get("/workspace/CTH-01/")
    asset = client.get("/main.dart.js")
    bootstrap = client.get("/flutter_bootstrap.js")
    nested_asset = client.get("/workspace/assets/AssetManifest.json")

    assert [
        response.status_code
        for response in (root, deep_link, trailing_deep_link, asset, nested_asset)
    ] == [
        200,
        200,
        200,
        200,
        200,
    ]
    assert root.data.startswith(b"<!doctype html>")
    assert deep_link.data == root.data
    assert trailing_deep_link.data == root.data
    assert asset.mimetype == "text/javascript"
    assert nested_asset.get_json() == {}
    assert root.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert asset.headers["Cache-Control"] == "max-age=0, must-revalidate"
    assert bootstrap.headers["Cache-Control"] == "max-age=0, must-revalidate"


def test_missing_artifact_is_an_honest_unavailable_state(tmp_path: Path):
    build = tmp_path / "build" / "web"
    build.mkdir(parents=True)
    client = _app(build).test_client()

    response = client.get("/workspace")

    assert response.status_code == 503
    assert response.get_json() == {
        "ok": False,
        "error": "workspace_build_unavailable",
        "message": "Web Workspace build artifact is unavailable",
    }


def test_missing_asset_and_directory_never_fall_back_to_index(tmp_path: Path):
    client = _app(_write_build(tmp_path)).test_client()

    missing_asset = client.get("/workspace/assets/missing.js")
    directory = client.get("/workspace/assets")

    assert missing_asset.status_code == 404
    assert missing_asset.get_json()["error"] == "workspace_asset_not_found"
    assert directory.status_code == 404
    assert directory.get_json()["error"] == "workspace_asset_not_found"


def test_path_traversal_is_rejected_and_api_routes_are_not_shadowed(tmp_path: Path):
    client = _app(_write_build(tmp_path)).test_client()

    traversal = client.get("/workspace/%2e%2e/%2e%2e/secrets.txt")
    api = client.get("/api/ping")

    assert traversal.status_code == 404
    assert api.status_code == 200
    assert api.get_json() == {"ok": True, "owner": "product-core"}


def test_asset_fallback_preserves_api_methods_and_never_serves_reserved_files(tmp_path: Path):
    build = _write_build(tmp_path)
    (build / 'api').mkdir()
    (build / 'api' / 'action').write_text('must not be served', encoding='utf-8')
    app = _app(build)
    calls = []

    @app.post('/api/action')
    def action():
        calls.append('action')
        return jsonify(ok=True)

    client = app.test_client()
    for method in ('GET', 'HEAD'):
        response = client.open('/api/action', method=method)
        assert response.status_code == 405
        assert set(response.headers['Allow'].replace(' ', '').split(',')) == {'POST', 'OPTIONS'}
    assert client.get('/api/missing').status_code == 404
    assert client.get('/API/action').status_code == 404
    assert calls == []
    assert client.post('/api/action').get_json() == {'ok': True}
    assert calls == ['action']


def test_hashed_assets_receive_immutable_cache_policy(tmp_path: Path):
    client = _app(_write_build(tmp_path, include_hashed_asset=True)).test_client()

    response = client.get("/assets/font-0123456789abcdef.woff2")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_existing_source_map_is_served_only_as_an_artifact_file(tmp_path: Path):
    build = _write_build(tmp_path)
    client = _app(build).test_client()

    absent = client.get("/main.dart.js.map")
    (build / "main.dart.js.map").write_text("{}", encoding="utf-8")
    present = client.get("/main.dart.js.map")

    assert absent.status_code == 404
    assert present.status_code == 200
    assert present.data == b"{}"


def test_workspace_host_keeps_no_directory_listing_contract(tmp_path: Path):
    build = _write_build(tmp_path)
    host = WorkspaceHost(build)

    assert host._safe_artifact_path("../index.html") is None
    assert host._safe_artifact_path("%2e%2e/index.html") is None
    assert host._safe_artifact_path("%252e%252e/index.html") is None
    assert host._safe_artifact_path("assets\\AssetManifest.json") is None


def test_unhashed_bootstrap_revalidates_and_new_build_changes_etag(tmp_path: Path):
    build = _write_build(tmp_path)
    client = _app(build).test_client()

    first = client.get("/flutter_bootstrap.js")
    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "max-age=0, must-revalidate"
    etag = first.headers["ETag"]
    unchanged = client.get("/flutter_bootstrap.js", headers={"If-None-Match": etag})
    assert unchanged.status_code == 304

    (build / "flutter_bootstrap.js").write_text("// replacement build", encoding="utf-8")
    changed = client.get("/flutter_bootstrap.js", headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert changed.data == b"// replacement build"
    assert changed.headers["ETag"] != etag
