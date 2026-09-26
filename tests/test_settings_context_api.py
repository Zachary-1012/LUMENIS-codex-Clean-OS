import json
import sqlite3
from contextlib import contextmanager

import pytest
from flask import Flask


@pytest.fixture
def context_client(tmp_path, monkeypatch):
    db_path = tmp_path / "settings-context.sqlite3"

    def connect_test_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def database_test_context():
        conn = connect_test_db()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    import account.authorization as authorization
    import account.models as account_models
    import database
    import lumenis.auth.service as auth_service
    import subject_registry

    monkeypatch.setattr(authorization, "get_db", connect_test_db)
    monkeypatch.setattr(account_models, "get_db", connect_test_db)
    monkeypatch.setattr(database, "get_db", database_test_context)

    with connect_test_db() as conn:
        conn.executescript(
            """
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                module TEXT NOT NULL,
                action TEXT NOT NULL,
                data_scope TEXT,
                time_range TEXT,
                granted_by INTEGER,
                created_at TEXT,
                updated_at TEXT
            );
            INSERT INTO v4_users (id, role, status) VALUES
                (1, 'user', 'active'), (2, 'user', 'active');
            """
        )
        subject_registry.ensure_schema(conn)

    cth, _ = subject_registry.add_subject({
        "domain_id": "CTH", "subject_type": "company",
        "name_en": "Luohu MixC", "name_zh": "罗湖深圳万象城",
    })
    bmp, _ = subject_registry.add_subject({
        "domain_id": "BMP", "subject_type": "brand",
        "name_en": "North Star Brand", "name_zh": "北辰品牌",
    })
    with connect_test_db() as conn:
        conn.executemany(
            """INSERT INTO v4_member_authorizations
               (user_id, product_id, module, action, data_scope)
               VALUES (?, ?, 'subject_registry', 'read', ?)""",
            [
                (1, "CTH", json.dumps({"subject_ids": [cth["subject_id"]]})),
                (1, "ZBMP", json.dumps({"brand_focus_ids": [bmp["brand_focus_id"]]})),
            ],
        )

    actor = {"user": None}
    monkeypatch.setattr(auth_service, "get_current_user", lambda: actor["user"])

    from lumenis_app_api import domain_api_bp

    app = Flask(__name__)
    app.secret_key = "isolated-context-test-key"
    app.register_blueprint(domain_api_bp)
    return app.test_client(), actor, cth, bmp, connect_test_db


def test_settings_context_defaults_global_and_clear_returns_global(context_client):
    client, actor, _cth, _bmp, _connect = context_client
    actor["user"] = {"id": 1, "role": "user"}

    default = client.get(
        "/api/settings/context",
        headers={"X-Lumenis-Context-Mode": "GLOBAL_ALL"},
    )
    assert default.status_code == 200
    body = default.get_json()
    assert body["ok"] is True
    assert body["contract"] == "lumenis.context.v1"
    assert body["selection_only"] is True
    assert body["context"]["mode"] == "GLOBAL_ALL"
    assert body["context"]["subject_id"] is None

    cleared = client.delete("/api/settings/context")
    assert cleared.status_code == 200
    assert cleared.get_json()["context"]["mode"] == "GLOBAL_ALL"


@pytest.mark.parametrize("domain_id", ["CTH", "BMP"])
def test_settings_context_focus_is_typed_and_matches_flutter_headers(
    context_client, domain_id
):
    client, actor, cth, bmp, _connect = context_client
    actor["user"] = {"id": 1, "role": "user"}
    entry = cth if domain_id == "CTH" else bmp
    subject_id = entry["subject_id"]

    selected = client.put(
        "/api/settings/context",
        json={"mode": "FOCUS", "domain_id": domain_id, "subject_id": subject_id},
    )
    assert selected.status_code == 200
    context = selected.get_json()["context"]
    assert context["mode"] == "FOCUS"
    assert context["domain_id"] == domain_id
    assert context["subject_id"] == subject_id
    if domain_id == "CTH":
        assert context["resource_type"] == "SUBJECT"
        assert context["brand_focus_id"] is None
    else:
        assert context["resource_type"] == "BRAND_FOCUS"
        assert context["brand_focus_id"] == entry["brand_focus_id"]

    restored = client.get(
        "/api/settings/context",
        headers={
            "X-Lumenis-Context-Mode": "FOCUS",
            "X-Domain-Id": domain_id,
            "X-Subject-ID": subject_id,
        },
    )
    assert restored.status_code == 200
    assert restored.get_json()["context"] == context


def test_settings_context_rejects_invalid_or_unregistered_focus_without_global_fallback(
    context_client,
):
    client, actor, _cth, _bmp, _connect = context_client
    actor["user"] = {"id": 1, "role": "user"}

    invalid = client.put(
        "/api/settings/context",
        json={"mode": "FOCUS", "domain_id": "SYSTEM", "subject_id": "x"},
    )
    assert invalid.status_code == 400
    assert invalid.get_json()["ok"] is False

    missing = client.put(
        "/api/settings/context",
        json={"mode": "FOCUS", "domain_id": "CTH", "subject_id": "SUBJ-MISSING"},
    )
    assert missing.status_code == 404
    assert missing.get_json()["ok"] is False

    mismatched_global = client.get(
        "/api/settings/context",
        headers={
            "X-Lumenis-Context-Mode": "GLOBAL_ALL",
            "X-Domain-Id": "CTH",
            "X-Subject-ID": "SUBJ-MISSING",
        },
    )
    assert mismatched_global.status_code == 400


def test_settings_context_rejects_unauthenticated_and_out_of_scope_focus(context_client):
    client, actor, cth, _bmp, _connect = context_client
    unauthenticated = client.put(
        "/api/settings/context",
        json={"mode": "FOCUS", "domain_id": "CTH", "subject_id": cth["subject_id"]},
    )
    assert unauthenticated.status_code == 401

    actor["user"] = {"id": 2, "role": "user"}
    denied = client.put(
        "/api/settings/context",
        json={"mode": "FOCUS", "domain_id": "CTH", "subject_id": cth["subject_id"]},
    )
    assert denied.status_code == 403
    assert denied.get_json()["code"] == "SUBJECT_SCOPE_DENIED"


def test_context_selection_is_read_only_and_does_not_touch_registry(context_client):
    client, actor, cth, _bmp, connect = context_client
    actor["user"] = {"id": 1, "role": "user"}
    with connect() as conn:
        before = conn.execute(
            "SELECT COUNT(*) FROM lumenis_subject_registry"
        ).fetchone()[0]

    selected = client.put(
        "/api/settings/context",
        json={"mode": "FOCUS", "domain_id": "CTH", "subject_id": cth["subject_id"]},
    )
    assert selected.status_code == 200
    client.delete("/api/settings/context")

    with connect() as conn:
        after = conn.execute(
            "SELECT COUNT(*) FROM lumenis_subject_registry"
        ).fetchone()[0]
    assert after == before
