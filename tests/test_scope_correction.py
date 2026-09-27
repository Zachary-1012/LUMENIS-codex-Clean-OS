"""Focused exact-scope correction checks using only a disposable SQLite DB."""
from __future__ import annotations

import json
import sqlite3

import pytest


SOURCE_IDS = [
    "7563830274112359737",
    "7566484323726101775",
    "7679739125724925227",
]
SUBJECT_ID = "SUBJ-CORRECTION-FIXTURE"
ACTOR = "owner:scope-review"
REASON = "Search query named a different venue; exact post text was reviewed."


@pytest.fixture
def correction_db(tmp_path, monkeypatch):
    path = tmp_path / "scope-correction.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"scope-test": "disposable-scope-test-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "scope-test")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)

    from canonical_data import ensure_canonical_table, ensure_canonical_scope_columns
    from lumenis.shared.evidence import store as evidence_store

    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE lumenis_subject_registry (
                subject_id TEXT PRIMARY KEY, brand_focus_id TEXT UNIQUE,
                domain_id TEXT NOT NULL, status TEXT NOT NULL
            );
            INSERT INTO lumenis_subject_registry VALUES
                ('SUBJ-CORRECTION-FIXTURE', NULL, 'CTH', 'configured');
            CREATE TABLE notes (
                note_id TEXT PRIMARY KEY, title TEXT, content TEXT, body TEXT,
                url TEXT, source_platform TEXT, source_keyword TEXT,
                publish_date TEXT, publish_datetime TEXT, captured_at TEXT,
                collected_at TEXT, product_id TEXT, domain_id TEXT,
                subject_id TEXT, brand_focus_id TEXT,
                scope_status TEXT DEFAULT 'UNASSIGNED', scope_evidence_ref TEXT,
                likes INTEGER, comments INTEGER, collects INTEGER, shares INTEGER
            );
            CREATE TABLE platform_contents (
                platform TEXT NOT NULL, platform_content_id TEXT NOT NULL,
                raw_data TEXT NOT NULL, PRIMARY KEY(platform, platform_content_id)
            );
        """)
        evidence_store.ensure_evidence_schema(conn)
        evidence_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        for column, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if column not in evidence_columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                conn.execute(
                    f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}"
                )
        ensure_canonical_table(connection=conn)
        ensure_canonical_scope_columns(conn)
        for source_id in SOURCE_IDS:
            conn.execute(
                "INSERT INTO notes (note_id,title,content,body,url,source_platform,"
                "source_keyword,publish_date,publish_datetime,captured_at,collected_at,"
                "product_id,domain_id,subject_id,brand_focus_id,scope_status,scope_evidence_ref,"
                "likes,comments,collects,shares) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (source_id, f"Title {source_id}", f"Body {source_id}", f"Body {source_id}",
                 f"https://www.douyin.com/video/{source_id}", "douyin", "深圳万象城",
                 "2026-09-28", "2026-09-28T01:00:00Z", "2026-09-28T02:00:00Z",
                 "2026-09-28T02:00:00Z", "CTH", "cth", None, None,
                 "UNASSIGNED", "", 7, 2, None, 1),
            )
            conn.execute(
                "INSERT INTO platform_contents VALUES (?,?,?)",
                ("douyin", source_id, json.dumps({
                    "aweme_id": source_id, "desc": f"Body {source_id}",
                    "create_time": 1780000000, "digg_count": 7,
                    "_lumenis_evidence_id": 0,
                }, sort_keys=True)),
            )
        original_ref = evidence_store.record_evidence(
            source="collector", project="LUMENIS", product="CTH",
            feature_id="FIXTURE_COLLECTION", result="PASS", status="verified",
            inputs={"source_ids": SOURCE_IDS}, outputs={"source_read": True},
            domain_id="cth", subject_id=SUBJECT_ID, connection=conn,
        )
        assert type(original_ref) is int and original_ref > 0
        from lumenis.adapters.persist import persist_existing_note_scope
        assert persist_existing_note_scope(
            conn, SOURCE_IDS, product_id="CTH", domain_id="cth",
            subject_id=SUBJECT_ID, scope_evidence_ref=original_ref,
        ) == len(SOURCE_IDS)
        for source_id in SOURCE_IDS:
            conn.execute(
                "UPDATE platform_contents SET raw_data=? WHERE platform=? AND platform_content_id=?",
                (json.dumps({
                    "aweme_id": source_id, "desc": f"Body {source_id}",
                    "create_time": 1780000000, "digg_count": 7,
                    "_lumenis_evidence_id": original_ref,
                }, sort_keys=True), "douyin", source_id),
            )
        conn.commit()
    return {"path": path, "original_ref": original_ref}


def _scope_call_args(original_ref):
    return {
        "platform": "douyin", "product_id": "CTH", "domain_id": "cth",
        "expected_subject_id": SUBJECT_ID, "expected_brand_focus_id": None,
        "expected_scope_evidence_ref": original_ref, "reason": REASON,
        "actor": ACTOR,
    }


def _approved_gate(monkeypatch, resource=None):
    from lumenis.system import security
    from lumenis.system.security import OperationType, PermissionGate, PermissionLevel
    from lumenis.system.security import permission as permission_module

    gate = PermissionGate()
    gate.grant_permission(PermissionLevel.COMMIT)
    if resource:
        gate.grant_approval(
            OperationType.DATA_IMPORT.value, resource=resource, granted_by=ACTOR,
        )
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    return gate


def _state(path):
    with sqlite3.connect(path) as conn:
        raw = conn.execute(
            "SELECT note_id,title,content,publish_datetime,captured_at,likes,comments,"
            "collects,shares,subject_id,brand_focus_id,scope_status,scope_evidence_ref "
            "FROM notes ORDER BY note_id"
        ).fetchall()
        canonical = conn.execute(
            "SELECT external_id,title,content,publish_datetime,captured_at,engagement_likes,"
            "engagement_comments,engagement_collects,engagement_shares,subject_id,"
            "brand_focus_id,scope_status,scope_evidence_ref FROM canonical_data "
            "ORDER BY external_id"
        ).fetchall()
        native = conn.execute(
            "SELECT platform_content_id,raw_data FROM platform_contents ORDER BY platform_content_id"
        ).fetchall()
        evidence = conn.execute(
            "SELECT * FROM app_evidence_records ORDER BY id"
        ).fetchall()
        columns = [row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")]
    return raw, canonical, native, evidence, columns


def test_scope_correction_denial_then_signed_idempotent_unassignment_and_refresh_fence(
    correction_db, tmp_path, monkeypatch,
):
    from lumenis.adapters import persist
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from lumenis.system.security import OperationType

    path, original_ref = correction_db["path"], correction_db["original_ref"]
    before = _state(path)
    denied_gate = _approved_gate(monkeypatch)
    with sqlite3.connect(path) as conn:
        with pytest.raises(PermissionError, match="exact DATA_IMPORT approval"):
            persist.correct_existing_note_scope_to_unassigned(
                conn, SOURCE_IDS, **_scope_call_args(original_ref),
            )
        assert _state(path)[:4] == before[:4]

    resource = persist.scope_correction_approval_resource(
        **_scope_call_args(original_ref), source_ids=SOURCE_IDS,
    )
    gate = _approved_gate(monkeypatch, resource)
    with sqlite3.connect(path) as conn:
        first = persist.correct_existing_note_scope_to_unassigned(
            conn, SOURCE_IDS, **_scope_call_args(original_ref),
        )
        conn.commit()
    assert first["corrected"] == len(SOURCE_IDS)
    assert first["idempotent"] is False
    assert denied_gate.get_audit_log()
    assert gate.get_audit_log()

    after_first = _state(path)
    assert len(after_first[3]) == len(before[3]) + 1
    assert after_first[0] == [
        (*row[:9], None, None, "UNASSIGNED", "") for row in before[0]
    ]
    assert after_first[1] == [
        (*row[:9], "", "", "UNASSIGNED", "") for row in before[1]
    ]
    old_evidence_id = original_ref
    assert after_first[3][old_evidence_id - 1] == before[3][old_evidence_id - 1]
    correction_row = after_first[3][-1]
    correction = dict(zip(after_first[4], correction_row))
    assert correction["feature_id"] == "SCOPE_CORRECTION"
    assert classify_evidence_integrity(correction)["assurance"] == "writer-authenticated"
    correction_inputs = json.loads(correction["inputs_json"])
    assert correction_inputs["source_ids"] == sorted(SOURCE_IDS)
    assert correction_inputs["scope_correction"]["expected_scope_evidence_ref"] == original_ref
    assert correction_inputs["scope_correction"]["target_scope_status"] == "UNASSIGNED"
    assert correction_inputs["scope_correction"]["permission_resource"] == resource
    for _source_id, raw_data in after_first[2]:
        payload = json.loads(raw_data)
        assert payload["_lumenis_evidence_id"] == original_ref
        assert payload["_lumenis_scope_correction_ref"] == first["evidence_id"]

    with sqlite3.connect(path) as conn:
        repeated = persist.correct_existing_note_scope_to_unassigned(
            conn, SOURCE_IDS, **_scope_call_args(original_ref),
        )
        assert repeated == {"corrected": 0, "evidence_id": first["evidence_id"], "idempotent": True}
        from lumenis.adapters.persist import persist_existing_note_scope
        from lumenis.shared.database.scope import ScopeValidationError
        with pytest.raises((ScopeValidationError, ValueError), match="corrected|restore"):
            persist_existing_note_scope(
                conn, SOURCE_IDS, product_id="CTH", domain_id="cth",
                subject_id=SUBJECT_ID, scope_evidence_ref=original_ref,
            )
        conn.rollback()
    assert len(_state(path)[3]) == len(before[3]) + 1


def test_scope_correction_append_and_raw_canonical_native_writes_roll_back_together(
    correction_db, monkeypatch,
):
    from canonical_data import persist_scope_correction as real_canonical_writer
    from lumenis.adapters import persist

    path, original_ref = correction_db["path"], correction_db["original_ref"]
    resource = persist.scope_correction_approval_resource(
        **_scope_call_args(original_ref), source_ids=SOURCE_IDS,
    )
    _approved_gate(monkeypatch, resource)
    before = _state(path)
    calls = 0

    def fail_after_one_canonical_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("fixture canonical failure after Evidence append")
        return real_canonical_writer(*args, **kwargs)

    monkeypatch.setattr("canonical_data.persist_scope_correction", fail_after_one_canonical_write)
    with sqlite3.connect(path) as conn:
        with pytest.raises(RuntimeError, match="after Evidence append"):
            persist.correct_existing_note_scope_to_unassigned(
                conn, SOURCE_IDS, **_scope_call_args(original_ref),
            )
        conn.rollback()
    assert calls == 2
    assert _state(path) == before


def test_direct_canonical_upsert_cannot_restore_a_corrected_scope(
    correction_db, monkeypatch,
):
    from canonical_data import note_to_canonical, persist_canonical
    from lumenis.adapters import persist

    path, original_ref = correction_db["path"], correction_db["original_ref"]
    resource = persist.scope_correction_approval_resource(
        **_scope_call_args(original_ref), source_ids=SOURCE_IDS,
    )
    _approved_gate(monkeypatch, resource)
    with sqlite3.connect(path) as conn:
        result = persist.correct_existing_note_scope_to_unassigned(
            conn, SOURCE_IDS, **_scope_call_args(original_ref),
        )
        conn.commit()
    assert result["corrected"] == len(SOURCE_IDS)

    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT * FROM notes WHERE note_id=?", (SOURCE_IDS[0],)).fetchone()
        columns = [column[1] for column in conn.execute("PRAGMA table_info(notes)")]
        record = note_to_canonical(dict(zip(columns, row)), product_id="CTH")
        record.subject_id = SUBJECT_ID
        record.scope_status = "VERIFIED"
        record.scope_evidence_ref = str(original_ref)
        with pytest.raises(ValueError, match="corrected"):
            persist_canonical(conn, record)
