"""Scope and lineage tests for the legacy notes compatibility projection."""
import json
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def scoped_notes_app(tmp_path, monkeypatch):
    from flask import Flask

    import database
    import subject_registry
    from account.models import ACCOUNT_TABLES_SQL
    from canonical_data import CanonicalRecord, ensure_canonical_table, persist_canonical
    from lumenis.auth.service import AUTH_CONFIG
    from lumenis.shared.database import repository
    from lumenis.shared.database.business_schema import ensure_business_scope_storage
    from lumenis.shared.evidence import store as evidence_store
    from subject_context import init_app

    path = tmp_path / "scoped-legacy-notes.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({
        "legacy-notes-test": "disposable-only-canonical-signing-key",
    }))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "legacy-notes-test")
    isolated_repository = repository.DatabaseRepository(str(path))
    monkeypatch.setattr(repository, "_default_repository", isolated_repository)
    evidence_store.init_evidence_store(str(path))
    database.init_db()

    with isolated_repository.connect() as connection:
        evidence_store.ensure_evidence_schema(connection)
        ensure_business_scope_storage(connection)
        ensure_canonical_table(connection=connection)
        subject_registry.ensure_schema(connection)
        connection.executescript(ACCOUNT_TABLES_SQL)
        connection.executemany(
            """INSERT INTO lumenis_subject_registry (
                   subject_id, domain_id, subject_type, name_en, name_zh,
                   name_en_norm, name_zh_norm, industry, keywords_json, status,
                   created_at, updated_at
               ) VALUES (?, 'CTH', 'company', ?, ?, ?, ?, 'retail', '[]', 'configured',
                         '2026-10-08', '2026-10-08')""",
            [
                ("SUBJECT-A", "North Center", "北区中心", "north center", "北区中心"),
                ("SUBJECT-B", "South Center", "南区中心", "south center", "南区中心"),
            ],
        )
        now = datetime.now()
        for source_id, subject_id, title in (
            ("note-a1", "SUBJECT-A", "A newest"),
            ("note-a2", "SUBJECT-A", "A older"),
            ("note-b1", "SUBJECT-B", "B secret"),
        ):
            database.insert_note({
                "note_id": source_id, "title": title, "content": "scoped test content",
                "publish_date": now.strftime("%Y-%m-%d"),
                "source_platform": "xhs", "sentiment": "negative",
                "risk_level": "high", "likes": None, "comments": 2,
                "collects": None, "shares": None,
            }, connection=connection)
            evidence_id = evidence_store.record_evidence(
                connection=connection, source="public_http", project="LUMENIS",
                product="CTH", feature_id="CTH_LEGACY_NOTE_SCOPE_TEST",
                test_name="canonical_note_projection_binding", result="PASS",
                status="verified", inputs={"source_ids": [source_id]},
                outputs={"authorized": True}, domain_id="cth", subject_id=subject_id,
            )
            connection.execute(
                "UPDATE notes SET subject_id=?,scope_status='VERIFIED',scope_evidence_ref=? WHERE note_id=?",
                (subject_id, str(evidence_id), source_id),
            )
            persist_canonical(connection, CanonicalRecord(
                canonical_id=f"canonical-{source_id}", product_id="CTH",
                domain_id="cth", subject_id=subject_id, scope_status="VERIFIED",
                scope_evidence_ref=str(evidence_id), source_id=source_id,
                external_id=source_id, source_type="note", source_table="notes",
                source_platform="xhs", title=title, content="canonical capture",
                captured_at=now.isoformat(), raw_ref=json.dumps(
                    {"table": "notes", "note_id": source_id}, separators=(",", ":"),
                ),
            ))

        global_token = "legacy-notes-global-reader"
        focus_token = "legacy-notes-focus-reader"
        expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        connection.executemany(
            """INSERT INTO v4_users
                   (id, username, password_hash, role, display_name, status)
               VALUES (?, ?, 'test-only', 'user', ?, 'active')""",
            [(201, "legacy-global", "Global Reader"), (202, "legacy-focus", "Focus Reader")],
        )
        connection.executemany(
            "INSERT INTO v4_sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            [(201, global_token, expires_at), (202, focus_token, expires_at)],
        )
        connection.executemany(
            """INSERT INTO v4_member_authorizations
                   (user_id, product_id, module, action, data_scope, time_range)
               VALUES (?, 'CTH', 'content', 'read', ?, NULL)""",
            [(201, json.dumps({"global": True})),
             (202, json.dumps({"subject_ids": ["SUBJECT-A"]}))],
        )
        connection.executemany(
            """INSERT INTO v4_member_authorizations
                   (user_id, product_id, module, action, data_scope, time_range)
               VALUES (?, 'CTH', 'reports', 'read', ?, NULL)""",
            [(201, json.dumps({"global": True})),
             (202, json.dumps({"subject_ids": ["SUBJECT-A"]}))],
        )
        connection.commit()

    app = Flask(__name__)
    app.secret_key = "disposable-test-only"
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    init_app(app)
    import data_query_api
    data_query_api.register_data_query_api(app)
    return app.test_client(), AUTH_CONFIG["session_cookie_name"], global_token, focus_token


def _scope_headers(subject_id=None, domain="cth"):
    headers = {"X-Domain-Id": domain}
    if subject_id is not None:
        headers["X-Subject-Id"] = subject_id
    return headers


def test_scoped_legacy_note_pagination_keeps_signed_source_lineage(scoped_notes_app):
    client, cookie_name, global_token, _ = scoped_notes_app
    client.set_cookie(cookie_name, global_token)

    first = client.get("/api/notes?page=1&per_page=1", headers=_scope_headers())
    second = client.get("/api/notes?page=2&per_page=1", headers=_scope_headers())
    assert first.status_code == second.status_code == 200
    first_payload, second_payload = first.get_json(), second.get_json()
    assert first_payload["scope"]["mode"] == "GLOBAL_ALL"
    assert first_payload["total"] == 3
    assert first_payload["notes"][0]["note_id"] != second_payload["notes"][0]["note_id"]
    lineage = first_payload["notes"][0]["canonical_source"]
    assert lineage["canonical_id"].startswith("canonical-")
    assert lineage["scope_status"] == "VERIFIED"
    assert lineage["scope_evidence_ref"]
    assert lineage["field_origin"].startswith("legacy_note_projection")


def test_focus_and_exact_note_id_do_not_cross_subjects(scoped_notes_app):
    client, cookie_name, _, focus_token = scoped_notes_app
    client.set_cookie(cookie_name, focus_token)

    response = client.get("/api/notes?page=1&per_page=10",
                          headers=_scope_headers("SUBJECT-A"))
    assert response.status_code == 200
    assert {row["note_id"] for row in response.get_json()["notes"]} == {"note-a1", "note-a2"}

    foreign_id = client.get("/api/notes?note_id=note-b1",
                            headers=_scope_headers("SUBJECT-A"))
    assert foreign_id.status_code == 200
    assert foreign_id.get_json()["notes"] == []
    assert foreign_id.get_json()["data_state"] == "NOT_COLLECTED"


def test_unselected_and_bmp_legacy_reads_fail_honestly(scoped_notes_app):
    client, cookie_name, global_token, _ = scoped_notes_app
    client.set_cookie(cookie_name, global_token)
    no_domain = client.get("/api/notes")
    assert no_domain.status_code == 400
    assert no_domain.get_json()["code"] == "DOMAIN_SELECTION_REQUIRED"

    bmp = client.get("/api/notes", headers=_scope_headers(domain="bmp"))
    assert bmp.status_code == 409
    assert bmp.get_json()["code"] == "LEGACY_CTH_DATA_UNAVAILABLE_FOR_SELECTED_DOMAIN"


def test_stats_keep_unknown_metrics_unknown(scoped_notes_app):
    client, cookie_name, global_token, _ = scoped_notes_app
    client.set_cookie(cookie_name, global_token)
    response = client.get("/api/stats", headers=_scope_headers())
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["stats"]["total"] == 3
    assert payload["stats"]["total_likes"] is None
    assert payload["stats"]["total_engagements"] is None


def test_later_note_page_and_scoped_aggregate_are_not_capped_at_1000(scoped_notes_app):
    client, cookie_name, global_token, _ = scoped_notes_app
    client.set_cookie(cookie_name, global_token)

    import database
    from canonical_data import CanonicalRecord, persist_canonical
    from lumenis.shared.evidence import store as evidence_store

    bulk_ids = [f"bulk-note-{index:04d}" for index in range(1102)]
    now = datetime.now()
    with database.get_db() as connection:
        evidence_id = evidence_store.record_evidence(
            connection=connection, source="public_http", project="LUMENIS",
            product="CTH", feature_id="CTH_LEGACY_NOTE_SCOPE_TEST",
            test_name="large_canonical_note_projection_binding", result="PASS",
            status="verified", inputs={"source_ids": bulk_ids},
            outputs={"authorized": True}, domain_id="cth", subject_id="SUBJECT-A",
        )
        for index, source_id in enumerate(bulk_ids):
            published = (now - timedelta(days=10_000 - index)).strftime("%Y-%m-%d")
            database.insert_note({
                "note_id": source_id, "title": source_id,
                "content": "large page binding", "publish_date": published,
                "source_platform": "xhs", "sentiment": "neutral",
                "risk_level": "low", "likes": 1, "comments": 1,
                "collects": 1, "shares": 1,
            }, connection=connection)
            persist_canonical(connection, CanonicalRecord(
                canonical_id=f"canonical-{source_id}", product_id="CTH",
                domain_id="cth", subject_id="SUBJECT-A", scope_status="VERIFIED",
                scope_evidence_ref=str(evidence_id), source_id=source_id,
                external_id=source_id, source_type="note", source_table="notes",
                source_platform="xhs", title=source_id, content="signed capture",
                captured_at=now.isoformat(), raw_ref=json.dumps(
                    {"table": "notes", "note_id": source_id}, separators=(",", ":"),
                ),
            ))

    page = client.get("/api/notes?page=1001&per_page=1", headers=_scope_headers())
    assert page.status_code == 200
    payload = page.get_json()
    assert payload["page"] == 1001
    assert payload["total"] is None
    assert payload["truncated"] is True
    assert payload["data_state"] == "PARTIAL"
    assert len(payload["notes"]) == 1
    assert payload["notes"][0]["note_id"].startswith("bulk-note-")
    assert payload["notes"][0]["canonical_source"]["scope_evidence_ref"]

    stats = client.get("/api/stats", headers=_scope_headers())
    assert stats.status_code == 200
    assert stats.get_json()["stats"]["total"] == 1105


def test_active_event_count_uses_only_exact_scoped_canonical_note_ids(scoped_notes_app):
    import database

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with pytest.raises(ValueError, match="SCOPE_REQUIRED"):
        database.upsert_event({"event_key": "unscoped", "title": "must be rejected"})
    for subject, source_id in (("SUBJECT-A", "note-a1"), ("SUBJECT-B", "note-b1")):
        scope = {"domain_id": "cth", "subject_id": subject,
                 "brand_focus_id": None, "global_scope": False}
        exact = database._normalize_event_scope(scope, allow_global=False)
        database.upsert_event({
            "event_key": database._event_scope_token(exact) + ".event", "title": subject + " event",
            "first_seen": now, "last_seen": now, "status": "active", "risk_level": "low",
        }, scope=scope, mentions=[{"source_type": "note", "source_id": source_id}])

    assert database.get_active_event_count_for_canonical_source_ids(
        ["note-a1"], since=now[:10],
    ) == 1
    assert database.get_active_event_count_for_canonical_source_ids(
        ["note-b1"], since=now[:10],
    ) == 1
    assert database.get_active_event_count_for_canonical_source_ids(
        [], since=now[:10],
    ) is None
