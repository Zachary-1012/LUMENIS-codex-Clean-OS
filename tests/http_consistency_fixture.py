"""Owned loopback HTTP over synthetic Shared Database; never attach to a service."""

import json
import threading
import urllib.error
import urllib.request

import pytest
from werkzeug.serving import make_server

from tests import test_udip_consistency as udip
from tests.test_udip_consistency import REPORT_DATE, SCOPE

env = udip.env


@pytest.fixture
def http_scope(env, monkeypatch, tmp_path):
    import app as core
    import subject_registry
    from lumenis.system.security import permission

    cm, daily, repository = env
    with repository.transaction() as con:
        subject_registry.ensure_schema(con)
        con.execute(
            """INSERT INTO lumenis_subject_registry
            (subject_id,brand_focus_id,domain_id,subject_type,name_en,name_zh,
             name_en_norm,name_zh_norm,industry,keywords_json,status,created_at,updated_at)
             VALUES (?,NULL,'CTH','company','UDIP Synthetic','UDIP合成主体',
             'udip synthetic','udip合成主体','retail','[]','configured',?,?)""",
            (SCOPE["subject_id"], REPORT_DATE, REPORT_DATE),
        )
        con.execute("""CREATE TABLE IF NOT EXISTS brand_industry_monitor (
            id INTEGER PRIMARY KEY, brand_name TEXT, industry TEXT,
            negative_count INTEGER, positive_count INTEGER)""")
        con.executemany(
            """INSERT INTO brand_industry_monitor
            (brand_name,industry,negative_count,positive_count) VALUES (?,?,?,?)""",
            [
                ("Synthetic A", "retail", 2, 0),
                ("Synthetic B", "retail", 0, 3),
                ("Synthetic C", "services", 1, 1),
                ("Synthetic D", "services", 0, 0),
            ],
        )
    # A real server-opened local workspace issues the sealed principal. Do not
    # mock actor/scope decisions or retrieve credentials from public metadata.
    monkeypatch.setitem(core.app.config, "LUMENIS_OPEN_WORKSPACE", True)
    monkeypatch.setattr(core, "AUTH_USER", "")
    monkeypatch.setattr(core, "AUTH_PASSWORD", "")
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    gate = permission.PermissionGate(
        audit_log_path=str(tmp_path / "permission-audit.jsonl")
    )
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(core.db, "get_repository", lambda: repository)
    server = make_server("127.0.0.1", 0, core.app)
    thread = threading.Thread(
        target=server.serve_forever, name="synthetic-http-consistency"
    )
    thread.start()
    headers = {
        "X-Domain-Id": "CTH",
        "X-Product-Id": "CTH",
        "X-Lumenis-Context-Mode": "FOCUS",
        "X-Subject-ID": SCOPE["subject_id"],
    }

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(path, *, context=True):
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}" + path, headers=headers if context else {}
        )
        try:
            with opener.open(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            with response:
                return response.code, json.load(response)

    try:
        status, meta = get("/api/auth/config", context=False)
        assert status == 200 and meta["ok"] is True and "auth_header" not in meta
        yield {
            "get": get,
            "app": core.app,
            "repository": repository,
            "daily": daily,
            "cm": cm,
            "date": REPORT_DATE,
            "scope": SCOPE,
            "headers": headers,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive(), "Owned loopback server did not stop"
