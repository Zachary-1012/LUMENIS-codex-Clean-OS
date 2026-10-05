"""Real Collector source-to-truth transaction checks on a disposable v19 DB."""
from __future__ import annotations

import json
import importlib.util
import sqlite3
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from flask import Flask


URL = "/api/experience/cth/platform-collection/search"
SOURCE_URL = "https://public.example.test/registered-venue.atom"
REGISTERED_NAME = "Registered Harbor Venue Holdings"
FOCUS_MODE = {
    "X-Domain-Id": "CTH",
    "X-Product-Id": "CTH",
    "X-Lumenis-Context-Mode": "FOCUS",
}
GLOBAL_MODE = {
    "X-Domain-Id": "CTH",
    "X-Product-Id": "CTH",
    "X-Lumenis-Context-Mode": "GLOBAL_ALL",
}
REQUEST = {
    "operator": "human",
    "confirm_read_only": True,
    "platform": "web_atom",
    "keyword": SOURCE_URL,
    "max_results": 1,
}
PIPELINE_TABLES = (
    "notes", "canonical_data", "app_evidence_records",
    "platform_contents", "metric_snapshots",
)


def _feed(view_count: int, source_name: str = REGISTERED_NAME) -> bytes:
    return f'''<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
      <title>Approved public fixture feed</title>
      <entry>
        <id>tag:public.example.test,2026:registered-venue-1</id>
        <yt:videoId>fixture-video-01</yt:videoId>
        <yt:channelId>fixture-channel-01</yt:channelId>
        <title>{source_name} public update</title>
        <link href="https://public.example.test/items/registered-venue-1" />
        <published>2026-10-01T08:00:00Z</published>
        <summary>Public source material for {source_name}.</summary>
        <media:group><media:community>
          <media:statistics views="{view_count}" />
        </media:community></media:group>
      </entry>
    </feed>'''.encode("utf-8")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _pipeline_counts(path: Path) -> dict[str, int]:
    with _connect(path) as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in PIPELINE_TABLES
        }


def _snapshot(case) -> dict[str, object]:
    with _connect(case["db_path"]) as connection:
        note = connection.execute(
            "SELECT note_id, source_platform, title, content, url, publish_datetime, "
            "source_keyword, matched_keywords, scope_status, scope_evidence_ref "
            "FROM notes ORDER BY note_id LIMIT 1"
        ).fetchone()
        canonical = connection.execute(
            "SELECT source_id, source_platform, title, content, url, publish_datetime, "
            "scope_status, scope_evidence_ref FROM canonical_data ORDER BY source_id LIMIT 1"
        ).fetchone()
        native = connection.execute(
            "SELECT platform, platform_content_id, title, content, view_count, raw_data, "
            "last_collected_at FROM platform_contents ORDER BY platform_content_id LIMIT 1"
        ).fetchone()
        metrics = connection.execute(
            "SELECT raw_json FROM metric_snapshots WHERE entity_type='platform_content' "
            "ORDER BY id"
        ).fetchall()
    return {
        "note": tuple(note) if note is not None else None,
        "canonical": tuple(canonical) if canonical is not None else None,
        "native": tuple(native) if native is not None else None,
        "metrics": [json.loads(row[0]) for row in metrics],
    }


def _global_snapshot(case) -> dict[str, object]:
    """Read the five persisted owners without assuming GLOBAL has a Subject."""
    with _connect(case["db_path"]) as connection:
        note = connection.execute(
            "SELECT * FROM notes ORDER BY note_id LIMIT 1"
        ).fetchone()
        canonical = connection.execute(
            "SELECT * FROM canonical_data ORDER BY source_id LIMIT 1"
        ).fetchone()
        native = connection.execute(
            "SELECT platform, platform_content_id, title, content, view_count, raw_data, "
            "last_collected_at FROM platform_contents ORDER BY platform_content_id LIMIT 1"
        ).fetchone()
        evidence = connection.execute(
            "SELECT * FROM app_evidence_records ORDER BY id"
        ).fetchall()
        metrics = connection.execute(
            "SELECT entity_type, entity_key, raw_json FROM metric_snapshots ORDER BY id"
        ).fetchall()
    return {
        "note": dict(note) if note is not None else None,
        "canonical": dict(canonical) if canonical is not None else None,
        "native": tuple(native) if native is not None else None,
        "evidence": [dict(row) for row in evidence],
        "metrics": [
            (row["entity_type"], row["entity_key"], json.loads(row["raw_json"]))
            for row in metrics
        ],
    }


@pytest.fixture
def collector_case(tmp_path, monkeypatch):
    """Bind every persistence owner to a fresh v19 temp DB and real PermissionGate."""
    db_path = tmp_path / "collector-transaction.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"collector-transaction-test": "isolated-test-signing-key-only"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "collector-transaction-test")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)

    import database
    import experience_runtime
    import subject_registry
    from lumenis.shared.database import migrations
    from lumenis.shared.evidence import store as evidence_store
    from lumenis.system import security
    from lumenis.system.collector.adapters import secondary_collection as surface
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.adapters.web_atom import AtomAdapter
    from lumenis.system.security import permission

    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)

    database.init_db()
    assert migrations.migrate(target_version=19) is True
    evidence_store.init_evidence_store(str(db_path))
    with migrations.get_connection() as connection:
        assert migrations.get_current_version(connection) == 19
        assert {name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in PIPELINE_TABLES} == {name: 0 for name in PIPELINE_TABLES}
    backups = list((tmp_path / "backups").glob("before_migration_v0_to_v19.db"))
    assert backups and all(path.parent == tmp_path / "backups" for path in backups)

    subject, _ = subject_registry.add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_en": REGISTERED_NAME,
        "name_zh": "注册港湾商业主体",
        "industry": "retail",
    })
    scope = {
        "domain_id": "cth",
        "subject_id": subject["subject_id"],
        "brand_focus_id": None,
        "global_scope": False,
    }
    focus_headers = {**FOCUS_MODE, "X-Subject-ID": subject["subject_id"]}

    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)

    views = {"value": 1234}
    source_name = {"value": REGISTERED_NAME}
    fetches: list[str] = []

    def fetch_public_source(url: str) -> PublicResponse:
        fetches.append(url)
        return PublicResponse(
            url=url,
            content=_feed(views["value"], source_name["value"]),
            content_type="application/atom+xml",
            status_code=200,
        )

    adapter = AtomAdapter(fetcher=fetch_public_source)
    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: adapter)
    run_logs: list[dict[str, object]] = []
    monkeypatch.setattr(
        surface, "_write_run_log",
        lambda *args, **kwargs: run_logs.append({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setitem(surface._last_action, "web_atom", 0.0)

    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(experience_runtime.experience_bp)
    client = app.test_client()

    def reset_rate_limit():
        monkeypatch.setitem(
            surface._last_action,
            "web_atom",
            time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1,
        )

    return {
        "db_path": db_path,
        "client": client,
        "gate": gate,
        "surface": surface,
        "permission": permission,
        "scope": scope,
        "focus_headers": focus_headers,
        "views": views,
        "source_name": source_name,
        "fetches": fetches,
        "run_logs": run_logs,
        "reset_rate_limit": reset_rate_limit,
    }


def _post(case, *, headers=None):
    case["reset_rate_limit"]()
    return case["client"].post(
        URL,
        headers=headers or case["focus_headers"],
        json=REQUEST,
    )


def _grant_exact_approval(case, *, headers=None) -> str:
    from lumenis.system.security import OperationType

    response = _post(case, headers=headers)
    assert response.status_code == 403, response.get_json()
    body = response.get_json()
    assert body["status"] == "APPROVAL_REQUIRED", body
    assert isinstance(body.get("approval_resource"), str)
    return case["gate"].grant_approval(
        OperationType.DATA_IMPORT.value,
        resource=body["approval_resource"],
        granted_by="explicit isolated transaction test",
    )


def _approve_and_collect_once(case, *, headers=None):
    _grant_exact_approval(case, headers=headers)
    response = _post(case, headers=headers)
    body = response.get_json()
    assert response.status_code == 200, body
    assert body["ok"] is True, body
    assert body["status"] == "SUCCESS", body
    return body


def test_flask_workspace_collection_is_idempotent_and_metric_refresh_keeps_scope_refs(
    collector_case,
):
    case = collector_case
    first_denial = _post(case)
    assert first_denial.status_code == 403
    assert first_denial.get_json()["status"] == "APPROVAL_REQUIRED"
    assert case["fetches"] == []

    case["gate"].grant_approval(
        "data_import",
        resource=first_denial.get_json()["approval_resource"],
        granted_by="explicit isolated transaction test",
    )
    first = _post(case).get_json()
    assert first["ok"] is True, first
    assert first["refresh_verified"] is True, first
    assert first["scope_status"] == "VERIFIED"
    assert first["canonical_synced"] == first["native_fields_synced"] == 1
    assert first["evidence_recorded"] is True
    assert first["entity_mentions"][0]["status"] == "EXACT_NAME_MENTION"
    assert first["entity_mentions"][0]["matched_names"] == [REGISTERED_NAME.casefold()]
    assert len(case["fetches"]) == 1

    first_snapshot = _snapshot(case)
    first_note = first_snapshot["note"]
    first_canonical = first_snapshot["canonical"]
    assert first_note is not None and first_canonical is not None
    note_id = first_note[0]
    original_scope_ref = first_note[-1]
    assert first_note[-2:] == ("VERIFIED", original_scope_ref)
    assert first_canonical[-2:] == ("VERIFIED", original_scope_ref)
    assert first_snapshot["native"][4] == 1234

    repeated = _post(case).get_json()
    assert repeated["ok"] is True, repeated
    assert repeated["refresh_verified"] is True, repeated
    repeated_snapshot = _snapshot(case)
    assert len(case["fetches"]) == 2
    assert _pipeline_counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 1,
        "platform_contents": 1,
        "metric_snapshots": 1,
    }
    assert repeated_snapshot["metrics"] == first_snapshot["metrics"]

    case["views"]["value"] = 1250
    changed = _post(case).get_json()
    assert changed["ok"] is True, changed
    assert changed["refresh_verified"] is True, changed
    assert changed["canonical_synced"] == changed["native_fields_synced"] == 1
    changed_snapshot = _snapshot(case)
    assert len(case["fetches"]) == 3

    note_after = changed_snapshot["note"]
    canonical_after = changed_snapshot["canonical"]
    native_after = changed_snapshot["native"]
    assert note_after[0] == first_note[0] == note_id
    assert note_after[-1] == original_scope_ref
    assert canonical_after[0] == first_canonical[0] == note_id
    assert canonical_after[-1] == original_scope_ref
    assert note_after[1:8] == first_note[1:8]
    assert canonical_after[1:6] == first_canonical[1:6]
    assert native_after[4] == 1250

    observation = json.loads(native_after[5])
    changed_evidence_id = observation["_lumenis_evidence_id"]
    first_observation_id = json.loads(first_snapshot["native"][5])["_lumenis_evidence_id"]
    assert changed_evidence_id > first_observation_id
    with _connect(case["db_path"]) as connection:
        evidence_row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (changed_evidence_id,),
        ).fetchone()
        metric_rows = connection.execute(
            "SELECT raw_json FROM metric_snapshots WHERE entity_type='platform_content' "
            "AND entity_key=? ORDER BY id", (f"web_atom:{note_id}",),
        ).fetchall()
    from lumenis.shared.evidence.store import classify_evidence_integrity

    integrity = classify_evidence_integrity(dict(evidence_row))
    assert integrity["verified"] is True
    assert integrity["assurance"] == "writer-authenticated"
    assert len(changed_snapshot["metrics"]) == 2
    metric_history = [json.loads(row[0]) for row in metric_rows]
    assert [item["view_count"] for item in metric_history] == [1234, 1250]
    assert [item["evidence_id"] for item in metric_history] == [
        first_observation_id, changed_evidence_id,
    ]
    assert all(item["source_id"] == item["canonical_source_id"] == note_id
               for item in metric_history)
    assert _pipeline_counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 2,
        "platform_contents": 1,
        "metric_snapshots": 2,
    }


def test_evidence_insert_then_raise_rolls_back_every_collector_owner(
    collector_case, monkeypatch,
):
    case = collector_case
    _grant_exact_approval(case)
    from lumenis.shared.evidence import store as evidence_store

    original_writer = evidence_store.record_evidence
    staged = []

    def insert_then_raise(*args, **kwargs):
        evidence_id = original_writer(*args, **kwargs)
        connection = kwargs.get("connection")
        assert connection is not None and connection.in_transaction
        staged.append((evidence_id, _pipeline_counts_on_connection(connection)))
        raise RuntimeError("injected post-insert Evidence writer failure")

    monkeypatch.setattr(evidence_store, "record_evidence", insert_then_raise)
    baseline = _pipeline_counts(case["db_path"])
    response = _post(case)
    result = response.get_json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["status"] == "EVIDENCE_WRITE_FAILED", result
    assert staged and staged[0][1]["notes"] == 1
    assert staged[0][1]["canonical_data"] == 0
    assert staged[0][1]["app_evidence_records"] == 1
    assert staged[0][1]["platform_contents"] == staged[0][1]["metric_snapshots"] == 0
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert "evidence_ref" not in result
    assert _pipeline_counts(case["db_path"]) == baseline


def test_revoked_exact_approval_after_native_stage_rolls_back_all_truth(
    collector_case, monkeypatch,
):
    case = collector_case
    token = _grant_exact_approval(case)
    from lumenis.shared.database import platform_content

    original_writer = platform_content.persist_verified_platform_records
    staged = []

    def persist_then_revoke(*args, **kwargs):
        result = original_writer(*args, **kwargs)
        connection = kwargs.get("connection")
        assert connection is not None and connection.in_transaction
        staged.append(_pipeline_counts_on_connection(connection))
        case["gate"].revoke_approval(token)
        return result

    monkeypatch.setattr(
        platform_content, "persist_verified_platform_records", persist_then_revoke,
    )
    baseline = _pipeline_counts(case["db_path"])
    response = _post(case)
    result = response.get_json()

    assert response.status_code == 403
    assert result["status"] == "APPROVAL_REQUIRED", result
    assert staged and all(staged[0][table] == 1 for table in PIPELINE_TABLES)
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert "evidence_ref" not in result
    assert _pipeline_counts(case["db_path"]) == baseline


def test_canonical_only_verified_identity_blocks_before_raw_import(collector_case):
    case = collector_case
    _approve_and_collect_once(case)
    before = _snapshot(case)
    note_id = before["note"][0]
    with _connect(case["db_path"]) as connection:
        connection.execute("DELETE FROM notes WHERE note_id=?", (note_id,))
    baseline = _pipeline_counts(case["db_path"])

    result = _post(case).get_json()

    assert result["ok"] is False
    assert result["status"] == "SCOPE_CONFLICT", result
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert _pipeline_counts(case["db_path"]) == baseline
    after = _snapshot(case)
    assert after["note"] is None
    assert after["canonical"] == before["canonical"]
    assert after["native"] == before["native"]


def test_global_import_rejects_mismatched_raw_canonical_scope_refs_before_write(
    collector_case,
):
    case = collector_case
    _approve_and_collect_once(case)
    before = _snapshot(case)
    note_id = before["note"][0]
    global_headers = GLOBAL_MODE
    _grant_exact_approval(case, headers=global_headers)
    with _connect(case["db_path"]) as connection:
        connection.execute(
            "UPDATE canonical_data SET scope_evidence_ref='999999' WHERE source_id=?",
            (note_id,),
        )
    baseline = _pipeline_counts(case["db_path"])
    preflight_snapshot = _snapshot(case)

    result = _post(case, headers=global_headers).get_json()

    assert result["ok"] is False
    assert result["status"] == "SCOPE_CONFLICT", result
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert _pipeline_counts(case["db_path"]) == baseline
    assert _snapshot(case) == preflight_snapshot


def test_native_writer_injected_connection_remains_owned_by_caller(collector_case):
    case = collector_case
    _approve_and_collect_once(case)
    before = _snapshot(case)
    note_id = before["note"][0]
    observation = json.loads(before["native"][5])
    evidence_id = observation["_lumenis_evidence_id"]

    from lumenis.shared.database import get_repository, platform_content

    connection = get_repository().connect(timeout=10)
    try:
        connection.execute("BEGIN IMMEDIATE")
        written = platform_content.persist_verified_platform_records(
            [observation],
            platform="web_atom",
            note_ids=[note_id],
            evidence_id=evidence_id,
            scope=case["scope"],
            connection=connection,
        )
        assert written == 1
        assert connection.in_transaction is True
        connection.rollback()
    finally:
        connection.close()

    assert _pipeline_counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 1,
        "platform_contents": 1,
        "metric_snapshots": 1,
    }
    assert _snapshot(case) == before


def test_global_manual_import_keeps_native_observations_unassigned_and_refreshes_truth(
    collector_case,
):
    case = collector_case
    token = _grant_exact_approval(case, headers=GLOBAL_MODE)
    assert token
    assert case["fetches"] == []

    first_response = _post(case, headers=GLOBAL_MODE)
    first = first_response.get_json()
    assert first_response.status_code == 200, first
    assert first["ok"] is True, first
    assert first["status"] == "SUCCESS", first
    assert first["scope_status"] == "UNASSIGNED", first
    assert first["canonical_synced"] == first["native_fields_synced"] == 1
    assert first["evidence_recorded"] is True
    assert len(case["fetches"]) == 1

    first_snapshot = _global_snapshot(case)
    note = first_snapshot["note"]
    canonical = first_snapshot["canonical"]
    native = first_snapshot["native"]
    assert note is not None and canonical is not None and native is not None
    source_id = note["note_id"]
    assert first["entity_mentions"] == []
    for row in (note, canonical):
        assert row["product_id"] == "CTH"
        assert row["domain_id"] == "cth"
        assert row["subject_id"] in (None, "")
        assert row["brand_focus_id"] in (None, "")
        assert row["scope_status"] == "UNASSIGNED"
        assert row["scope_evidence_ref"] in (None, "")
    evidence_id = int(first["evidence_ref"])
    assert str(canonical["evidence_ref"]) == str(evidence_id)
    assert native[:5] == ("web_atom", source_id, f"{REGISTERED_NAME} public update",
                          f"Public source material for {REGISTERED_NAME}.", 1234)
    native_observation = json.loads(native[5])
    assert native_observation["_lumenis_evidence_id"] == evidence_id
    assert native_observation["video_id"] == "fixture-video-01"
    assert native_observation["channel_id"] == "fixture-channel-01"
    assert native_observation["entry_id"] == "tag:public.example.test,2026:registered-venue-1"
    assert native_observation["media_statistics"] == {"views": "1234"}
    assert native_observation["source_raw"]["video_id"] == "fixture-video-01"
    assert native_observation["source_raw"]["channel_id"] == "fixture-channel-01"

    from lumenis.shared.evidence.store import classify_evidence_integrity

    first_evidence = first_snapshot["evidence"][0]
    integrity = classify_evidence_integrity(first_evidence)
    assert integrity["verified"] is True
    assert integrity["assurance"] == "writer-authenticated"
    inputs = json.loads(first_evidence["inputs_json"])
    global_scope = inputs["_lumenis_scope"]
    assert global_scope["global"] is True
    assert global_scope["domain_id"] == "cth"
    assert global_scope["product_id"] == "CTH"
    assert global_scope.get("subject_id") in (None, "")
    assert global_scope.get("brand_focus_id") in (None, "")
    assert inputs["source_ids"] == [source_id]
    assert [item["source_id"] for item in inputs["source_observations"]] == [source_id]

    repeated_response = _post(case, headers=GLOBAL_MODE)
    repeated = repeated_response.get_json()
    assert repeated_response.status_code == 200, repeated
    assert repeated["ok"] is True, repeated
    assert repeated["scope_status"] == "UNASSIGNED", repeated
    repeated_snapshot = _global_snapshot(case)
    assert len(case["fetches"]) == 2
    assert _pipeline_counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 1,
        "platform_contents": 1,
        "metric_snapshots": 1,
    }
    assert repeated_snapshot["evidence"][0]["id"] == evidence_id
    assert repeated_snapshot["metrics"] == first_snapshot["metrics"]
    for row_name in ("note", "canonical"):
        row = repeated_snapshot[row_name]
        assert row["scope_status"] == "UNASSIGNED"
        assert row["scope_evidence_ref"] in (None, "")
        assert row["subject_id"] in (None, "")
        assert row["brand_focus_id"] in (None, "")

    case["views"]["value"] = 1250
    changed_response = _post(case, headers=GLOBAL_MODE)
    changed = changed_response.get_json()
    assert changed_response.status_code == 200, changed
    assert changed["ok"] is True, changed
    assert changed["scope_status"] == "UNASSIGNED", changed
    assert changed["canonical_synced"] == changed["native_fields_synced"] == 1
    changed_snapshot = _global_snapshot(case)
    assert len(case["fetches"]) == 3
    assert changed_snapshot["note"]["note_id"] == source_id
    assert changed_snapshot["native"][4] == 1250
    changed_observation = json.loads(changed_snapshot["native"][5])
    changed_evidence_id = changed_observation["_lumenis_evidence_id"]
    assert changed_evidence_id > evidence_id
    assert len(changed_snapshot["evidence"]) == 2
    assert {row["id"] for row in changed_snapshot["evidence"]} == {
        evidence_id, changed_evidence_id,
    }
    assert [row[2]["view_count"] for row in changed_snapshot["metrics"]] == [1234, 1250]
    assert [row[2]["evidence_id"] for row in changed_snapshot["metrics"]] == [
        evidence_id, changed_evidence_id,
    ]
    for row_name in ("note", "canonical"):
        row = changed_snapshot[row_name]
        assert row["scope_status"] == "UNASSIGNED"
        assert row["scope_evidence_ref"] in (None, "")
        assert row["subject_id"] in (None, "")
        assert row["brand_focus_id"] in (None, "")
    changed_integrity = classify_evidence_integrity(
        next(row for row in changed_snapshot["evidence"] if row["id"] == changed_evidence_id)
    )
    assert changed_integrity["verified"] is True
    assert changed_integrity["assurance"] == "writer-authenticated"
    assert _pipeline_counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 2,
        "platform_contents": 1,
        "metric_snapshots": 2,
    }


def test_global_approval_revoked_after_native_stage_rolls_back_all_truth_and_runlog(
    collector_case, monkeypatch,
):
    case = collector_case
    token = _grant_exact_approval(case, headers=GLOBAL_MODE)
    from lumenis.shared.database import platform_content

    original_writer = platform_content.persist_unassigned_platform_records
    staged = []

    def persist_then_revoke(*args, **kwargs):
        result = original_writer(*args, **kwargs)
        connection = kwargs.get("connection")
        assert connection is not None and connection.in_transaction
        staged.append(_pipeline_counts_on_connection(connection))
        case["gate"].revoke_approval(token)
        return result

    monkeypatch.setattr(
        platform_content, "persist_unassigned_platform_records", persist_then_revoke,
    )
    baseline = _pipeline_counts(case["db_path"])
    response = _post(case, headers=GLOBAL_MODE)
    result = response.get_json()

    assert response.status_code == 403
    assert result["status"] == "APPROVAL_REQUIRED", result
    assert staged and all(staged[0][table] == 1 for table in PIPELINE_TABLES)
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert "evidence_ref" not in result
    assert _pipeline_counts(case["db_path"]) == baseline
    assert case["run_logs"] == []


def test_all_unmatched_review_evidence_revocation_rolls_back_all_truth_and_runlog(
    collector_case, monkeypatch,
):
    case = collector_case
    case["source_name"]["value"] = "Unrelated Coastal Newsroom"
    token = _grant_exact_approval(case)
    from lumenis.shared.evidence import store as evidence_store

    original_writer = evidence_store.record_evidence
    staged = []

    def insert_then_revoke(*args, **kwargs):
        evidence_id = original_writer(*args, **kwargs)
        connection = kwargs.get("connection")
        assert connection is not None and connection.in_transaction
        row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,),
        ).fetchone()
        staged.append((evidence_id, _pipeline_counts_on_connection(connection), dict(row)))
        case["gate"].revoke_approval(token)
        return evidence_id

    monkeypatch.setattr(evidence_store, "record_evidence", insert_then_revoke)
    baseline = _pipeline_counts(case["db_path"])
    response = _post(case)
    result = response.get_json()

    assert response.status_code == 403
    assert result["status"] == "APPROVAL_REQUIRED", result
    assert staged and staged[0][1]["app_evidence_records"] == 1
    assert staged[0][1]["notes"] == staged[0][1]["canonical_data"] == 0
    assert staged[0][1]["platform_contents"] == staged[0][1]["metric_snapshots"] == 0
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert "evidence_ref" not in result
    assert _pipeline_counts(case["db_path"]) == baseline
    assert case["run_logs"] == []


def test_all_unmatched_review_evidence_insert_then_raise_is_classified_and_rolled_back(
    collector_case, monkeypatch,
):
    case = collector_case
    case["source_name"]["value"] = "Unrelated Coastal Newsroom"
    _grant_exact_approval(case)
    from lumenis.shared.evidence import store as evidence_store

    original_writer = evidence_store.record_evidence
    staged = []

    def insert_then_raise(*args, **kwargs):
        evidence_id = original_writer(*args, **kwargs)
        connection = kwargs.get("connection")
        assert connection is not None and connection.in_transaction
        row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,),
        ).fetchone()
        staged.append((evidence_id, _pipeline_counts_on_connection(connection), dict(row)))
        raise RuntimeError("injected all-review Evidence writer failure")

    monkeypatch.setattr(evidence_store, "record_evidence", insert_then_raise)
    baseline = _pipeline_counts(case["db_path"])
    response = _post(case)
    result = response.get_json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["status"] == "EVIDENCE_WRITE_FAILED", result
    assert staged and staged[0][1]["app_evidence_records"] == 1
    assert staged[0][1]["notes"] == staged[0][1]["canonical_data"] == 0
    assert staged[0][1]["platform_contents"] == staged[0][1]["metric_snapshots"] == 0
    from lumenis.shared.evidence.store import classify_evidence_integrity

    integrity = classify_evidence_integrity(staged[0][2])
    assert integrity["verified"] is True
    assert integrity["assurance"] == "writer-authenticated"
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == result["native_fields_synced"] == 0
    assert result["evidence_recorded"] is False
    assert "evidence_ref" not in result
    assert _pipeline_counts(case["db_path"]) == baseline


def test_permitted_all_unmatched_review_persists_only_signed_review_evidence(
    collector_case,
):
    case = collector_case
    case["source_name"]["value"] = "Unrelated Coastal Newsroom"
    _grant_exact_approval(case)

    response = _post(case)
    result = response.get_json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["status"] == "SCOPE_REVIEW_REQUIRED", result
    assert result["error_type"] == "SOURCE_ENTITY_IDENTITY_UNCONFIRMED"
    assert result["review_pending_count"] == 1
    assert result["imported"] == result["updated"] == 0
    assert result["canonical_synced"] == 0
    assert result["evidence_recorded"] is True
    assert result["evidence_ref"]
    assert result.get("scope_status") != "VERIFIED"
    assert _pipeline_counts(case["db_path"]) == {
        "notes": 0,
        "canonical_data": 0,
        "app_evidence_records": 1,
        "platform_contents": 0,
        "metric_snapshots": 0,
    }

    with _connect(case["db_path"]) as connection:
        evidence_row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?",
            (int(result["evidence_ref"]),),
        ).fetchone()
    record = dict(evidence_row)
    from lumenis.shared.evidence.store import classify_evidence_integrity

    integrity = classify_evidence_integrity(record)
    assert integrity["verified"] is True
    assert integrity["assurance"] == "writer-authenticated"
    inputs = json.loads(record["inputs_json"])
    outputs = json.loads(record["outputs_json"])
    assert inputs["_lumenis_scope"]["subject_id"] == case["scope"]["subject_id"]
    assert inputs["source_ids"] == []
    assert len(inputs["unassigned_review_candidates"]) == 1
    assert inputs["unassigned_review_candidates"][0]["content_id"] == result[
        "entity_mentions"
    ][0]["source_id"]
    assert result["entity_mentions"][0]["status"] == "REVIEW_REQUIRED"
    assert outputs["notes_inserted"] == 0
    assert outputs["notes_updated"] == 0


def _pipeline_counts_on_connection(connection) -> dict[str, int]:
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in PIPELINE_TABLES
    }


def test_noncritical_run_log_failure_preserves_committed_source_result(collector_case, monkeypatch):
    case = collector_case
    _grant_exact_approval(case)
    def fail_log(*args, **kwargs):
        raise RuntimeError("isolated audit log unavailable")
    monkeypatch.setattr(case["surface"], "_write_run_log", fail_log)
    response = _post(case)
    result = response.get_json()
    assert response.status_code == 200
    assert result["ok"] is True and result["status"] == "SUCCESS"
    assert result["refresh_verified"] is True and result["run_log_recorded"] is False
    assert all(count == 1 for count in _pipeline_counts(case["db_path"]).values())


def test_collect_now_uses_shared_database_and_fails_closed_without_quota_state(monkeypatch, capsys):
    source = Path(__file__).resolve().parents[1] / "scripts" / "collect_now.py"
    spec = importlib.util.spec_from_file_location("isolated_collect_now", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Connection:
        def execute(self, sql, *_args):
            assert "sqlite_master" in sql
            return SimpleNamespace(fetchone=lambda: None)

    class DatabaseModule(ModuleType):
        @staticmethod
        def get_db():
            class Context:
                def __enter__(self):
                    return Connection()

                def __exit__(self, *_args):
                    return False
            return Context()

    monkeypatch.setitem(sys.modules, "database", DatabaseModule("database"))
    monkeypatch.setattr(
        sqlite3, "connect",
        lambda *_args, **_kwargs: pytest.fail("collect_now must not open a raw SQLite connection"),
    )

    assert module.collect_now("registered term") is False
    assert "已阻止请求" in capsys.readouterr().out


def test_note_ingestion_keeps_missing_analysis_unknown_and_preserves_existing_result(collector_case):
    case = collector_case
    import database as db

    def read_analysis(note_id):
        connection = _connect(case["db_path"])
        try:
            row = connection.execute(
                "SELECT sentiment,sentiment_score,risk_level,risk_score,data_quality_score "
                "FROM notes WHERE note_id=?",
                (note_id,),
            ).fetchone()
            return tuple(row)
        finally:
            connection.close()

    note = {
        "note_id": "unclassified-xhs-note", "source_platform": "xhs",
        "title": "广州太古汇 observed source", "content": "Raw source body",
        "url": "https://public.example.test/unclassified-xhs-note",
        "data_quality_status": "unknown", "data_quality_score": None,
        "is_taikoo_verified": 1,
    }

    db.insert_note(note)
    with db.get_db() as connection:
        connection.execute("UPDATE notes SET topics=? WHERE note_id=?",
                           (json.dumps(["registered topic"], ensure_ascii=False), note["note_id"]))
    assert read_analysis(note["note_id"]) == ("unknown", None, "unknown", None, None)
    stats = db.get_stats()
    assert stats["unknown_sentiment"] == 1 and stats["unknown_risk"] == 1
    topic = next(item for item in db.get_hot_topics() if item["topic"] == "registered topic")
    assert topic["sentiment"] == "unknown"
    assert topic["unknown"] == 1 and topic["neutral"] == 0

    assert db.update_note_analysis(note["note_id"], {"status": "UNAVAILABLE"}) is False
    assert db.update_note_analysis(note["note_id"], {
        "status": "COMPLETED", "sentiment": "positive", "sentiment_score": 0.8,
        "risk_level": "low", "risk_score": 2, "summary": "Reviewed analysis",
        "topics": ["retail"], "ai_provider": "owned",
    }) is True
    db.insert_note({**note, "title": "Source refreshed"})

    assert read_analysis(note["note_id"]) == ("positive", 0.8, "low", 2, None)
