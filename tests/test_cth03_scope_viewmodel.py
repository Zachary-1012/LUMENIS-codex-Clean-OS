"""Route/Projection tests; signed source verification is tested in Canonical."""
from types import SimpleNamespace
import sqlite3

import pytest
from flask import Flask


def _record(subject="SUBJ-A"):
    return {
        "canonical_id": "can-1", "subject_id": subject, "title": "Source title",
        "content": "Source text", "publish_datetime": "", "captured_at": "2026-09-29",
        "source_platform": "public_http", "canonical_url": "https://example.com/article",
        "url": "", "quality_status": "missing",
        "scope_evidence": {
            "id": 7, "source_id": "raw-1",
            "stored_scope": {"product_id": "CTH", "domain_id": "cth", "subject_id": subject},
            "integrity": {"integrity_version": 2, "verified": True,
                          "lineage_verified": True, "algorithm": "hmac-sha256",
                          "assurance": "writer-authenticated", "digest": "a" * 64},
        },
    }


@pytest.fixture
def stream_client(tmp_path, monkeypatch):
    path = tmp_path / "projection.sqlite3"
    sqlite3.connect(path).close()
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    import canonical_data
    import experience_runtime as runtime
    import experience_screens as screens
    import lumenis.auth.service as auth
    import subject_registry

    state = {"records": [_record()], "rejected_count": 0, "truncated": False,
             "failure": False, "reads": []}

    def read_rows(con, *, product_id, subject_id, limit):
        state["reads"].append((product_id, subject_id, limit))
        if state["failure"]:
            raise sqlite3.OperationalError("sensitive database detail")
        rows = [row for row in state["records"] if subject_id is None or row["subject_id"] == subject_id]
        scanned = len(rows) + state["rejected_count"]
        return {"records": rows, "returned_count": len(rows), "scanned_count": scanned,
                "candidate_count": scanned + int(state["truncated"]), "limit": limit,
                "rejected_count": state["rejected_count"], "truncated": state["truncated"]}

    monkeypatch.setattr(canonical_data, "list_scoped_canonical", read_rows)
    monkeypatch.setattr(runtime, "_all_builders", lambda: {"CTH-03": screens._build_cth03})
    monkeypatch.setattr(screens, "_platform_collection_section", lambda **_: {"type": "platforms", "items": []})
    monkeypatch.setattr(auth, "get_current_user", lambda: None)
    monkeypatch.setattr(subject_registry, "get_subject_by_id", lambda domain, subject: (
        {"subject_type": "company", "subject_id": subject} if domain == "CTH" and subject == "SUBJ-A" else None
    ))
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(runtime.experience_bp)
    return app.test_client(), state


def _table(payload):
    return next(section for section in payload["sections"] if section["type"] == "table")


def test_global_focus_return_preserve_row_provenance_without_account_or_fake_metrics(stream_client, monkeypatch):
    client, state = stream_client
    import lumenis.auth.service as auth
    monkeypatch.setattr(auth, "get_current_user", lambda: pytest.fail("local read initialized account"))
    state["records"].append(_record("SUBJ-B"))
    headers = {"X-Lumenis-Context-Mode": "FOCUS", "X-Domain-Id": "CTH", "X-Subject-ID": "SUBJ-A"}
    global_view = client.get("/api/experience/screen/CTH-03").get_json()
    focused = client.get("/api/experience/screen/CTH-03", headers=headers).get_json()
    returned = client.get("/api/experience/screen/CTH-03").get_json()
    assert len(_table(global_view)["rows"]) == len(_table(returned)["rows"]) == 2
    assert state["reads"] == [("CTH", None, 100), ("CTH", "SUBJ-A", 100), ("CTH", None, 100)]
    binding = focused["focus_binding"]
    assert binding["subject_id"] == "SUBJ-A" and binding["read_allowed"]
    assert binding["contract"] == "lumenis.scope-read-binding.v1"
    assert "projection" not in binding and "evidence_lineage" not in binding
    rows = _table(focused)["rows"]
    assert len(rows) == 1 and rows[0]["subject_id"] == "SUBJ-A"
    row = rows[0]
    assert row["date"] is None and row["captured_at"] == "2026-09-29"
    assert row["sentiment"] is None and row["risk"] is None
    assert row["projection"]["evidence"]["evidence_id"] == "7"
    assert row["projection"]["stored_scope"]["global"] is False
    assert focused["truth"]["data_state"] == "partial"
    kpis = next(section for section in focused["sections"] if section["type"] == "kpis")
    assert all(item["value"] is None for item in kpis["items"])


@pytest.mark.parametrize(("headers", "opened", "expected"), [
    ({"X-Lumenis-Context-Mode": "FOCUS", "X-Domain-Id": "BMP", "X-Subject-ID": "SUBJ-A"}, True, 400),
    ({"X-Lumenis-Context-Mode": "FOCUS", "X-Domain-Id": "CTH", "X-Subject-ID": "SUBJ-MISSING"}, True, 404),
    ({"Origin": "https://example.com"}, True, 401),
    ({"Authorization": "Bearer invalid-test-only"}, True, 401),
    ({}, False, 401),
])
def test_invalid_or_revoked_reads_do_not_read_canonical(stream_client, headers, opened, expected):
    client, state = stream_client
    client.application.config["LUMENIS_OPEN_WORKSPACE"] = opened
    response = client.get("/api/experience/screen/CTH-03", headers=headers)
    assert response.status_code == expected
    assert state["reads"] == []
    assert "sections" not in response.get_json()


def test_actor_module_denial_is_not_replaced_by_local_access(stream_client, monkeypatch):
    client, state = stream_client
    import lumenis.auth.service as auth
    import lumenis.system.security.permission as permission
    calls = []
    monkeypatch.setattr(auth, "get_current_user", lambda: {"id": 11})
    def deny(actor, **scope):
        calls.append(scope)
        return SimpleNamespace(verification_state="verified", allowed=False)
    monkeypatch.setattr(permission, "check_actor_scope_permission", deny)
    response = client.get("/api/experience/screen/CTH-03", headers={"Authorization": "Bearer test-only"})
    assert response.status_code == 403 and state["reads"] == []
    assert calls[0]["module"] == "commercial_realtime_stream" and calls[0]["global_scope"]


def test_storage_failure_is_sanitized_and_retry_recovers(stream_client):
    client, state = stream_client
    state["failure"] = True
    failed = client.get("/api/experience/screen/CTH-03")
    assert failed.status_code == 503
    assert failed.get_json()["code"] == "SCOPED_DATA_UNAVAILABLE"
    assert "sensitive database detail" not in failed.get_data(as_text=True)
    assert "trace" not in failed.get_json() and "sections" not in failed.get_json()
    state["failure"] = False
    assert len(_table(client.get("/api/experience/screen/CTH-03").get_json())["rows"]) == 1


@pytest.mark.parametrize(("records", "rejected", "truncated", "expected"), [
    ([], 0, False, "notcollected"), ([], 1, False, "blocked"),
    ([_record()], 0, True, "ready"),
])
def test_missing_rejected_and_bounded_streams_remain_distinct(stream_client, records, rejected, truncated, expected):
    client, state = stream_client
    state.update(records=records, rejected_count=rejected, truncated=truncated)
    payload = client.get("/api/experience/screen/CTH-03").get_json()
    assert _table(payload)["state"] == expected
    assert payload["truth"]["rejected_count"] == rejected
    assert payload["truth"]["truncated"] is truncated
    assert payload["truth"]["coverage"] == "NOT_VERIFIED"
