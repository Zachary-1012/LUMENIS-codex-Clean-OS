from flask import Flask
import pytest

import api_dual_domain as api


class _Connection:
    closed = False

    def close(self):
        self.closed = True


def _snapshot(records, *, subject_id=None, truncated=False, rejected=0, platform_page=None):
    canonical = {
        "records": records,
        "candidate_count": len(records) + rejected + (1 if truncated else 0),
        "scanned_count": len(records) + rejected,
        "rejected_count": rejected,
        "returned_count": len(records),
        "limit": 100,
        "truncated": truncated,
    }
    if platform_page is not None:
        canonical["page"] = platform_page
    return {
        "scope": {
            "mode": "GLOBAL_ALL" if subject_id is None else "FOCUS",
            "domain_id": "cth",
            "product_id": "CTH",
            "subject_id": subject_id,
            "global": subject_id is None,
        },
        "permission_audit_id": "audit-cth-read",
        "canonical": canonical,
    }


def _call(monkeypatch, route, path, snapshot_or_error):
    app = Flask(__name__)
    conn = _Connection()
    monkeypatch.setattr(api, "_get_conn", lambda: conn)
    observed = []

    def read(_conn, **kwargs):
        observed.append(kwargs)
        if kwargs.get("limit", 1) > 100:
            raise api.CTHScopedReadError("INVALID_CTH_READ_LIMIT", 400)
        if isinstance(snapshot_or_error, Exception):
            raise snapshot_or_error
        return snapshot_or_error

    monkeypatch.setattr(api, "read_cth_scoped_canonical", read)
    with app.test_request_context(path):
        response, status = route()
        payload = response.get_json()
    assert conn.closed
    return payload, status, observed


def test_cth_overview_is_canonical_scoped_and_reports_unknown_unread_sources(monkeypatch):
    rows = [
        {
            "canonical_id": "can-a", "product_id": "CTH", "domain_id": "cth",
            "subject_id": "SUBJECT-A", "source_id": "src-a", "scope_status": "VERIFIED",
            "source_platform": "douyin", "title": "真实记录", "sentiment": "positive",
            "risk_level": None, "engagement_likes": 3, "engagement_comments": None,
        },
        {
            "canonical_id": "can-b", "product_id": "CTH", "domain_id": "cth",
            "subject_id": "SUBJECT-B", "source_id": "src-b", "scope_status": "VERIFIED",
            "source_platform": "x", "title": "另一主体", "sentiment": "negative",
            "risk_level": "high", "engagement_likes": None, "engagement_comments": 2,
        },
    ]
    snapshot = _snapshot(rows, truncated=True)
    payload, status, observed = _call(
        monkeypatch, api.cth_overview, "/api/cth/overview", snapshot,
    )

    assert status == 200 and payload["success"]
    assert observed == [{"module": "reports", "limit": 100}]
    data = payload["data"]
    assert data["scope"]["mode"] == "GLOBAL_ALL"
    assert data["scope"]["subject_id"] is None
    assert data["subject_id"] is None
    assert data["total_canonical"] is None
    assert data["total_notes"] is None and data["total_web_mentions"] is None
    assert data["source_tables_state"] == "NOT_READ_OUTSIDE_CANONICAL_OWNER"
    assert data["by_platform"] == {"douyin": 1, "x": 1}
    assert data["by_sentiment"] == {"positive": 1, "negative": 1}
    assert data["by_risk"] == {"high": 1}
    assert data["engagement_summary"]["likes"] == 3
    assert data["engagement_summary"]["comments"] == 2
    assert data["engagement_summary"]["basis"] == "VERIFIED_RETURNED_CANONICAL_ROWS"
    assert all("is_taikoo_verified" not in row for row in data["recent_records"])


def test_cth_events_omit_empty_topics_and_keep_source_lineage(monkeypatch):
    rows = [
        {
            "canonical_id": "can-empty", "product_id": "CTH", "domain_id": "cth",
            "subject_id": "SUBJECT-A", "source_id": "src-empty", "scope_status": "VERIFIED",
            "event_hint": "", "topics": "[]", "title": "no event",
        },
        {
            "canonical_id": "can-event", "product_id": "CTH", "domain_id": "cth",
            "subject_id": "SUBJECT-A", "source_id": "src-event", "scope_status": "VERIFIED",
            "scope_evidence_ref": "evidence-7", "event_hint": "开业活动",
            "topics": "[]", "title": "活动", "source_platform": "weibo",
        },
    ]
    payload, status, observed = _call(
        monkeypatch, api.cth_events, "/api/cth/events", _snapshot(rows, subject_id="SUBJECT-A"),
    )
    assert status == 200 and payload["success"]
    assert observed == [{"module": "reports", "limit": 100}]
    assert payload["data"]["scope"]["mode"] == "FOCUS"
    assert [row["event_id"] for row in payload["data"]["events"]] == ["can-event"]
    event = payload["data"]["events"][0]
    assert event["source_id"] == "src-event"
    assert event["scope_evidence_ref"] == "evidence-7"
    assert event["subject_id"] == "SUBJECT-A"


def test_cth_xhs_uses_scoped_canonical_and_preserves_unknown_metrics(monkeypatch):
    rows = [{
        "canonical_id": "can-xhs", "product_id": "CTH", "domain_id": "cth",
        "subject_id": "SUBJECT-A", "source_id": "note-1", "scope_status": "VERIFIED",
        "source_platform": "xhs", "title": "手工内容", "content": "正文",
        "engagement_likes": None, "engagement_comments": 4,
        "engagement_collects": None, "engagement_shares": None,
    }]
    snapshot = _snapshot(
        rows, subject_id="SUBJECT-A", platform_page={
            "candidate_source_count": 8, "offset": 10, "limit": 25,
            "returned_source_count": 1, "truncated": True,
        },
    )
    payload, status, observed = _call(
        monkeypatch, api.cth_xiaohongshu,
        "/api/cth/xiaohongshu?limit=25&offset=10", snapshot,
    )
    assert status == 200 and payload["success"]
    assert observed == [{
        "module": "content", "limit": 25, "offset": 10, "platform": "xiaohongshu",
    }]
    data = payload["data"]
    assert data["scope"]["subject_id"] == "SUBJECT-A"
    assert data["total_candidates"] == 8 and data["truncated"]
    assert len(data["records"]) == 1
    item = data["records"][0]
    assert item["likes"] is None and item["comments"] == 4
    assert item["note_id"] == "note-1" and item["content"] == "正文"
    assert "is_taikoo_verified" not in item


def test_cth_xhs_rejects_invalid_pagination_and_scope_denial_is_honest(monkeypatch):
    payload, status, observed = _call(
        monkeypatch, api.cth_xiaohongshu,
        "/api/cth/xiaohongshu?limit=999", _snapshot([]),
    )
    assert status == 400 and payload["error"] == "INVALID_CTH_READ_LIMIT"
    assert observed == [{
        "module": "content", "limit": 999, "offset": 0, "platform": "xiaohongshu",
    }]

    denied = api.CTHScopedReadError("CTH_SCOPE_READ_DENIED", 403)
    payload, status, observed = _call(
        monkeypatch, api.cth_overview, "/api/cth/overview", denied,
    )
    assert status == 403 and payload["error"] == "CTH_SCOPE_READ_DENIED"
    assert observed == [{"module": "reports", "limit": 100}]

def test_scoped_reader_calls_permission_and_canonical_owners_with_global_scope(monkeypatch):
    import sqlite3
    from types import SimpleNamespace
    from domain_isolation import DOMAIN_CTH, DomainContext, set_domain_context, clear_domain_context
    from lumenis.auth import service as auth_service
    from lumenis.system.security import permission
    import canonical_data

    connection = sqlite3.connect(":memory:")
    set_domain_context(DomainContext(domain_id=DOMAIN_CTH, product_id="CTH"))
    monkeypatch.setattr(api, "_cth_request_subject", lambda _conn: None)
    monkeypatch.setattr(auth_service, "get_current_user", lambda *, read_only: {"id": 17})
    permission_calls = []
    monkeypatch.setattr(permission, "check_actor_scope_permission", lambda actor, **kwargs: (
        permission_calls.append((actor, kwargs)) or SimpleNamespace(
            verification_state="verified", allowed=True, audit_id="audit-global",
        )
    ))
    canonical_calls = []
    expected = {
        "records": [{"canonical_id": "signed-global", "scope_evidence": {"integrity": {"verified": True}}}],
        "candidate_count": 1, "scanned_count": 1, "rejected_count": 0,
        "returned_count": 1, "limit": 10, "truncated": False,
    }
    monkeypatch.setattr(canonical_data, "list_scoped_canonical", lambda conn, **kwargs: (
        canonical_calls.append((conn, kwargs)) or expected
    ))

    try:
        result = api.read_cth_scoped_canonical(connection, module="reports", limit=10)
    finally:
        clear_domain_context()
        connection.close()

    assert permission_calls[0][0] == {"id": 17}
    assert permission_calls[0][1] == {
        "domain_id": "cth", "action": "read", "module": "reports",
        "subject_id": None, "global_scope": True, "connection": connection,
    }
    assert canonical_calls == [(connection, {
        "product_id": "CTH", "subject_id": None, "limit": 10, "source_ids": None,
    })]
    assert result["scope"] == {
        "mode": "GLOBAL_ALL", "domain_id": "cth", "product_id": "CTH",
        "subject_id": None, "global": True,
    }
    assert result["canonical"] is expected


def test_request_subject_alias_resolution_has_no_implicit_reference_focus(monkeypatch):
    import sqlite3
    from domain_isolation import DOMAIN_CTH, DomainContext, set_domain_context, clear_domain_context
    import subject_registry

    connection = sqlite3.connect(":memory:")
    monkeypatch.setattr(subject_registry, "list_subjects", lambda _domain, *, connection: [{
        "subject_id": "SUBJECT-A", "subject_type": "company",
        "name_en": "Example Group", "name_zh": "示例集团", "keywords": ["Example"],
    }])
    try:
        set_domain_context(DomainContext(domain_id=DOMAIN_CTH, product_id="CTH"))
        assert api._cth_request_subject(connection) is None
        set_domain_context(DomainContext(
            domain_id=DOMAIN_CTH, product_id="CTH", brand_key="示例集团",
        ))
        assert api._cth_request_subject(connection) == "SUBJECT-A"
        set_domain_context(DomainContext(
            domain_id=DOMAIN_CTH, product_id="CTH", subject_id="SUBJECT-B",
        ))
        with pytest.raises(api.CTHScopedReadError, match="CTH_SUBJECT_NOT_FOUND"):
            api._cth_request_subject(connection)
    finally:
        clear_domain_context()
        connection.close()


def test_cth_overview_real_permission_registry_and_signed_canonical(tmp_path, monkeypatch):
    """Exercise the production owners together on one disposable SQLite DB."""
    import json
    from datetime import datetime, timedelta

    from flask import Flask

    import canonical_data
    import subject_registry
    from account.models import ACCOUNT_TABLES_SQL
    from canonical_data import CanonicalRecord, ensure_canonical_table, persist_canonical
    from domain_isolation import clear_domain_context
    from lumenis.auth.service import AUTH_CONFIG
    from lumenis.shared.database import repository
    from lumenis.shared.evidence import store as evidence_store
    from subject_context import init_app

    db_path = tmp_path / "cth-real-scoped-api.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({
        "cth-real-api-test": "disposable-test-only-canonical-signing-key",
    }))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "cth-real-api-test")
    isolated_repository = repository.DatabaseRepository(str(db_path))
    monkeypatch.setattr(repository, "_default_repository", isolated_repository)
    evidence_store.init_evidence_store(str(db_path))

    with isolated_repository.connect() as connection:
        evidence_store.ensure_evidence_schema(connection)
        ensure_canonical_table(connection=connection)
        subject_registry.ensure_schema(connection)
        connection.executescript(ACCOUNT_TABLES_SQL)

        subject_rows = [
            ("SUBJECT-A", "CTH", "company", "North Center", "北区中心",
             "north center", "北区中心", "retail", "[]", "configured"),
            ("SUBJECT-B", "CTH", "company", "South Center", "南区中心",
             "south center", "南区中心", "retail", "[]", "configured"),
        ]
        connection.executemany(
            """INSERT INTO lumenis_subject_registry (
                   subject_id, domain_id, subject_type, name_en, name_zh,
                   name_en_norm, name_zh_norm, industry, keywords_json, status,
                   created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-10-08', '2026-10-08')""",
            subject_rows,
        )

        for source_id, subject_id in (
            ("source-a", "SUBJECT-A"), ("source-b", "SUBJECT-B"),
        ):
            evidence_id = evidence_store.record_evidence(
                connection=connection, source="public_http", project="LUMENIS",
                product="CTH", feature_id="CTH_REAL_SCOPE_API_TEST",
                test_name="signed_canonical_source", result="PASS", status="verified",
                inputs={"source_ids": [source_id]}, outputs={"readable": True},
                domain_id="cth", subject_id=subject_id,
            )
            assert evidence_id > 0
            persist_canonical(connection, CanonicalRecord(
                canonical_id=f"canonical-{source_id}", product_id="CTH", domain_id="cth",
                subject_id=subject_id, scope_status="VERIFIED",
                scope_evidence_ref=str(evidence_id), source_id=source_id,
                external_id=source_id, source_platform="web", title=source_id,
                captured_at="2026-10-08T00:00:00Z",
            ))

        global_token = "test-session-global"
        focus_token = "test-session-focus-a"
        expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        connection.executemany(
            """INSERT INTO v4_users
                   (id, username, password_hash, role, display_name, status)
               VALUES (?, ?, ?, 'user', ?, 'active')""",
            [(101, "global-reader", "test-only", "Global Reader"),
             (102, "focus-reader", "test-only", "Focus Reader")],
        )
        connection.executemany(
            "INSERT INTO v4_sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            [(101, global_token, expires_at), (102, focus_token, expires_at)],
        )
        connection.executemany(
            """INSERT INTO v4_member_authorizations
                   (user_id, product_id, module, action, data_scope, time_range)
               VALUES (?, 'CTH', 'reports', 'read', ?, NULL)""",
            [(101, json.dumps({"global": True})),
             (102, json.dumps({"subject_ids": ["SUBJECT-A"]}))],
        )
        connection.commit()

    app = Flask(__name__)
    app.secret_key = "disposable-test-only"
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    init_app(app)
    app.register_blueprint(api.cth_bp)
    client = app.test_client()

    try:
        client.set_cookie(AUTH_CONFIG["session_cookie_name"], global_token)
        global_response = client.get("/api/cth/overview")
        assert global_response.status_code == 200
        global_payload = global_response.get_json()
        assert global_payload["success"] is True
        assert global_payload["data"]["scope"]["mode"] == "GLOBAL_ALL"
        assert {row["source_id"] for row in global_payload["data"]["recent_records"]} == {
            "source-a", "source-b",
        }
        assert all(row.get("scope_evidence_ref") for row in global_payload["data"]["recent_records"])
        with isolated_repository.connect() as canonical_connection:
            signed_global = canonical_data.list_scoped_canonical(
                canonical_connection, product_id="CTH",
            )
        assert {row["source_id"] for row in signed_global["records"]} == {
            "source-a", "source-b",
        }
        assert all(
            row["scope_evidence"]["integrity"]["verified"] is True
            for row in signed_global["records"]
        )

        client.set_cookie(AUTH_CONFIG["session_cookie_name"], focus_token)
        focus_response = client.get(
            "/api/cth/overview", headers={"X-Subject-Id": "SUBJECT-A"},
        )
        assert focus_response.status_code == 200
        focus_payload = focus_response.get_json()
        assert focus_payload["data"]["scope"] == {
            "mode": "FOCUS", "domain_id": "cth", "product_id": "CTH",
            "subject_id": "SUBJECT-A", "global": False,
        }
        assert [row["source_id"] for row in focus_payload["data"]["recent_records"]] == [
            "source-a",
        ]

        cross_subject_response = client.get(
            "/api/cth/overview", headers={"X-Subject-Id": "SUBJECT-B"},
        )
        assert cross_subject_response.status_code == 403
        assert cross_subject_response.get_json()["error"] == "CTH_SCOPE_READ_DENIED"

        # No selected focus remains GLOBAL; a focused request does not leak into
        # the next request handled by the same Flask test client/thread.
        global_denied = client.get("/api/cth/overview")
        assert global_denied.status_code == 403
        assert global_denied.get_json()["error"] == "CTH_SCOPE_READ_DENIED"
    finally:
        clear_domain_context()
        from subject_context import clear_thread_context
        clear_thread_context()
