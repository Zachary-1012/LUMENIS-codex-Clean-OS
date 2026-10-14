# -*- coding: utf-8 -*-
"""P0-1 事件聚合唯一权威收口测试。

背景：旧受保护名 aggregate_events() 重构时更名为 reprocess.build_cross_platform_events，
基线 grep 旧名误判 MISSING（对账 GAP-P0-01）。本测试锁定：
1) aggregate_events 是转发到唯一权威的兼容入口（不再另写一套口径）；
2) 全仓事件聚合实现只有 reprocess 一处（单一 Owner）；
3) 风险事实来自数据（risk_score 取 max / 负面计数），AI 关闭照样聚合、不改写风险。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reprocess  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_protected_alias_forwards_scope_to_single_authority(monkeypatch):
    sentinel = [{"event_key": "x"}]
    scope = {"domain_id": "cth", "subject_id": "SUBJECT-1",
             "brand_focus_id": None, "global_scope": False}
    captured = {}

    def fake_build(limit=100, *, scope=None):
        captured["limit"] = limit
        captured["scope"] = scope
        return sentinel

    monkeypatch.setattr(reprocess, "build_cross_platform_events", fake_build)
    # The compatibility alias must preserve both limits and the exact scope.
    assert reprocess.aggregate_events(limit=7, scope=scope) is sentinel
    assert captured["limit"] == 7
    assert captured["scope"] is scope


def test_single_owner_across_codebase():
    owner_files = []
    protected_alias_files = []
    skip = (".venv", "__pycache__", "backups", "_backup", "archive", "tests", ".trae")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                text = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "def build_cross_platform_events" in text:
                owner_files.append(os.path.relpath(fp, ROOT))
            if "def aggregate_events" in text:
                protected_alias_files.append(os.path.relpath(fp, ROOT))
    # 唯一实现只在 reprocess.py
    assert owner_files == ["reprocess.py"], owner_files
    # 受保护兼容名也只在 reprocess.py（同一文件内，非第二套实现）
    assert protected_alias_files == ["reprocess.py"], protected_alias_files


def test_event_writer_refuses_missing_scope_only():
    with pytest.raises(ValueError, match="SCOPE_REQUIRED"):
        reprocess.build_cross_platform_events()


def test_full_refresh_takes_shared_snapshot_before_mutating_stages(monkeypatch):
    from lumenis.shared.database import migrations

    scope = {"domain_id": "cth", "subject_id": "SUBJECT-REFRESH",
             "brand_focus_id": None, "global_scope": False}
    steps = []
    backup_path = "isolated-refresh-backup.db"
    monkeypatch.setattr(migrations, "backup_database",
                        lambda: (steps.append("backup") or backup_path))
    monkeypatch.setattr(reprocess.intelligence, "ai_enabled", lambda: False)
    monkeypatch.setattr(reprocess, "reprocess_notes",
                        lambda *args, **kwargs: (steps.append("notes") or {"status": "COMPLETED"}))
    monkeypatch.setattr(reprocess, "discover_web",
                        lambda *args, **kwargs: (steps.append("web") or {"status": "COMPLETED"}))
    monkeypatch.setattr(reprocess, "build_cross_platform_events",
                        lambda *args, **kwargs: (steps.append("events") or {"status": "COMPLETED"}))

    result = reprocess.full_refresh(scope=scope)

    assert steps == ["backup", "notes", "web", "events"]
    assert result["status"] == "COMPLETED"
    assert result["backup"] == backup_path


def test_full_refresh_blocks_every_write_when_shared_snapshot_fails(monkeypatch):
    from lumenis.shared.database import migrations

    scope = {"domain_id": "cth", "subject_id": "SUBJECT-REFRESH",
             "brand_focus_id": None, "global_scope": False}
    monkeypatch.setattr(migrations, "backup_database",
                        lambda: (_ for _ in ()).throw(OSError("snapshot unavailable")))
    monkeypatch.setattr(reprocess.intelligence, "ai_enabled", lambda: False)
    for name in ("reprocess_notes", "discover_web", "build_cross_platform_events"):
        monkeypatch.setattr(reprocess, name,
                            lambda *args, _name=name, **kwargs:
                            pytest.fail(f"{_name} must not run before backup"))

    result = reprocess.full_refresh(scope=scope)

    assert result["status"] == "BLOCKED_BACKUP_FAILED"
    assert result["backup"] is None
    assert result["backup_error"] == "DATABASE_BACKUP_FAILED"
    assert result["notes"]["status"] == result["web"]["status"] == "NOT_RUN"
    assert result["events"]["status"] == "NOT_RUN"


def test_function_registry_reads_only_verified_scope_sources():
    import function_registry

    scope = {"product_id": "CTH", "domain_id": "cth", "subject_id": "SUBJECT-A",
             "brand_focus_id": None, "global_scope": False}
    calls = []

    class ScopedReader:
        def get_scoped_event_source_rows(self, received_scope, *, limit, source_types):
            calls.append(("notes", received_scope, source_types))
            return {"state": "AVAILABLE", "truncated": False, "sources": [
                {"source_id": "note-1", "title": "Service disruption", "content": "Verified note"}
            ]}

        def get_scoped_events(self, *, limit, scope):
            calls.append(("events", scope))
            return {"state": "AVAILABLE", "truncated": False, "events": [
                {"event_key": "event-1", "title": "Service disruption", "summary": "Verified event"}
            ]}

        def get_notes(self, *_args, **_kwargs):
            raise AssertionError("unscoped note reader must not be called")

        def get_events(self, *_args, **_kwargs):
            raise AssertionError("unscoped event reader must not be called")

    result = function_registry.search_targets("service disruption", ScopedReader(), 8, scope=scope)
    assert [item["source_id"] for item in result["notes"]] == ["note-1"]
    assert [item["event_key"] for item in result["events"]] == ["event-1"]
    assert result["meta"]["notes_state"] == result["meta"]["events_state"] == "AVAILABLE"
    assert calls == [("notes", scope, ["note"]), ("events", scope)]


def test_function_registry_marks_business_sources_unavailable_without_scope():
    import function_registry

    class ScopeRequiredReader:
        def get_scoped_event_source_rows(self, *_args, **_kwargs):
            raise AssertionError("reader must not receive an unverified scope")

        def get_scoped_events(self, *_args, **_kwargs):
            raise AssertionError("reader must not receive an unverified scope")

        def get_notes(self, *_args, **_kwargs):
            raise AssertionError("unscoped note reader must not be called")

        def get_events(self, *_args, **_kwargs):
            raise AssertionError("unscoped event reader must not be called")

    result = function_registry.search_targets("数据分析", ScopeRequiredReader(), 8)
    assert result["notes"] == []
    assert result["events"] == []
    assert result["meta"]["notes_state"] == "SOURCE_SCOPE_UNAVAILABLE"
    assert result["meta"]["events_state"] == "SOURCE_SCOPE_UNAVAILABLE"
    assert result["functions"]


@pytest.fixture
def signed_scoped_event_sources(tmp_path, monkeypatch):
    """Use a disposable DB with writer-authenticated source and Canonical Evidence."""
    import json
    from datetime import datetime

    import database
    from canonical_data import (
        CanonicalRecord,
        ensure_canonical_table,
        persist_canonical,
    )
    from lumenis.shared.database import repository
    from lumenis.shared.database.business_schema import ensure_business_scope_storage
    from lumenis.shared.evidence import store as evidence_store

    db_path = tmp_path / "scoped-event-aggregation.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({
        "scoped-event-test": "isolated-scoped-event-signing-key",
    }))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "scoped-event-test")
    isolated_repository = repository.DatabaseRepository(str(db_path))
    monkeypatch.setattr(repository, "_default_repository", isolated_repository)
    evidence_store.init_evidence_store(str(db_path))
    database.init_db()

    with isolated_repository.connect() as connection:
        evidence_store.ensure_evidence_schema(connection)
        ensure_business_scope_storage(connection)
        ensure_canonical_table(connection=connection)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for source_id, subject_id in (("scope-note-a", "SUBJECT-A"),
                                      ("scope-note-b", "SUBJECT-B")):
            database.insert_note({
                "note_id": source_id, "title": "Same observed event",
                "content": "The same public report appears in two independently scoped records.",
                "url": f"https://example.invalid/{source_id}", "publish_date": now[:10],
                "source_platform": "x", "sentiment": "negative", "risk_level": "medium",
                "likes": 0, "comments": 0, "collects": 0, "shares": 0,
                "event_hint": "A service disruption was reported",
            }, connection=connection)
            evidence_id = evidence_store.record_evidence(
                connection=connection, source="public_http", project="LUMENIS",
                product="CTH", domain_id="cth", subject_id=subject_id,
                feature_id="SCOPED_EVENT_WRITER_REGRESSION",
                test_name="canonical_source_scope_binding", result="PASS", status="verified",
                inputs={"source_ids": [source_id]}, outputs={"scope_admitted": True},
            )
            connection.execute(
                "UPDATE notes SET subject_id=?,scope_status='VERIFIED',scope_evidence_ref=? WHERE note_id=?",
                (subject_id, str(evidence_id), source_id),
            )
            persist_canonical(connection, CanonicalRecord(
                canonical_id=f"canonical-{source_id}", product_id="CTH", domain_id="cth",
                subject_id=subject_id, scope_status="VERIFIED", scope_evidence_ref=str(evidence_id),
                source_id=source_id, external_id=source_id, source_type="note", source_table="notes",
                source_platform="x", title="Same observed event", content="Signed canonical source",
                captured_at=now, publish_datetime=now[:10],
                raw_ref=json.dumps({"table": "notes", "note_id": source_id}, separators=(",", ":")),
            ))
        connection.commit()

    return isolated_repository


def test_scoped_writer_creates_updates_and_separates_global_focuses(signed_scoped_event_sources):
    import database

    global_scope = {"domain_id": "cth", "subject_id": None, "brand_focus_id": None,
                    "global_scope": True}
    first = reprocess.build_cross_platform_events(scope=global_scope)
    assert first["status"] == "COMPLETED"
    assert len(first["events"]) == 2

    persisted = database.get_scoped_events(10, scope=global_scope, include_sources=True)
    assert persisted["state"] == "AVAILABLE"
    assert len(persisted["events"]) == 2
    assert {event["subject_id"] for event in persisted["events"]} == {"SUBJECT-A", "SUBJECT-B"}
    assert all(event["mention_count"] == 1 and event["source_count"] == 1
               and len(event["sources"]) == 1 for event in persisted["events"])

    second = reprocess.build_cross_platform_events(scope=global_scope)
    assert second["status"] == "COMPLETED"
    persisted_again = database.get_scoped_events(10, scope=global_scope, include_sources=True)
    assert len(persisted_again["events"]) == 2
    assert {event["event_key"] for event in persisted_again["events"]} == {
        event["event_key"] for event in persisted["events"]
    }
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM events")[0] == 2
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM event_mentions")[0] == 2


def test_truncated_source_read_does_not_replace_persisted_event_mentions(
        signed_scoped_event_sources, monkeypatch):
    import database

    global_scope = {
        "product_id": "CTH", "domain_id": "cth", "subject_id": None,
        "brand_focus_id": None, "global_scope": True,
    }
    complete = reprocess.build_cross_platform_events(scope=global_scope)
    assert complete["status"] == "COMPLETED"

    with signed_scoped_event_sources.connect() as connection:
        before_events = connection.execute(
            "SELECT id,event_key,summary,mention_count,source_count "
            "FROM events ORDER BY id"
        ).fetchall()
        before_mentions = connection.execute(
            "SELECT event_id,source_type,source_id "
            "FROM event_mentions ORDER BY event_id,source_type,source_id"
        ).fetchall()
    assert before_events and before_mentions

    real_read = database.get_scoped_event_source_rows
    partial_rows = real_read(
        global_scope, limit=10, source_types=("note", "web_mention")
    )["sources"][:1]
    monkeypatch.setattr(
        database, "get_scoped_event_source_rows",
        lambda *_args, **_kwargs: {
            "sources": partial_rows, "truncated": True, "rejected_count": 0,
        },
    )
    monkeypatch.setattr(
        database, "upsert_event",
        lambda *_args, **_kwargs: pytest.fail(
            "truncated source coverage must not persist partial event mentions"
        ),
    )

    result = reprocess.build_cross_platform_events(scope=global_scope)

    assert result["status"] == "PARTIAL"
    assert result["events"] == []
    assert result["truncated"] is True
    assert result["persistence_status"] == "NOT_RUN_INCOMPLETE_SOURCE_READ"
    with signed_scoped_event_sources.connect() as connection:
        after_events = connection.execute(
            "SELECT id,event_key,summary,mention_count,source_count "
            "FROM events ORDER BY id"
        ).fetchall()
        after_mentions = connection.execute(
            "SELECT event_id,source_type,source_id "
            "FROM event_mentions ORDER BY event_id,source_type,source_id"
        ).fetchall()
    assert after_events == before_events
    assert after_mentions == before_mentions


def test_function_registry_search_uses_verified_note_and_event_sources(signed_scoped_event_sources):
    import database
    import function_registry

    scope = {"product_id": "CTH", "domain_id": "cth", "subject_id": None,
             "brand_focus_id": None, "global_scope": True}
    reprocess.build_cross_platform_events(scope=scope)

    result = function_registry.search_targets(
        "same observed event", database, 8, scope=scope
    )
    assert {note["source_id"] for note in result["notes"]} == {"scope-note-a", "scope-note-b"}
    assert len(result["events"]) == 2
    assert result["meta"]["notes_state"] == "AVAILABLE"
    assert result["meta"]["events_state"] == "AVAILABLE"


def test_scoped_writer_rejects_foreign_source_and_missing_scope_evidence(signed_scoped_event_sources):
    import database

    subject_a = {"product_id": "CTH", "domain_id": "cth", "subject_id": "SUBJECT-A", "brand_focus_id": None,
                 "global_scope": False}
    before = signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM events")[0]
    with pytest.raises(ValueError, match="EVENT_SOURCE_SCOPE_MISMATCH"):
        database.upsert_event({
            "event_key": f"{database._event_scope_token(subject_a)}.foreign-source",
            "title": "Must not cross scope", "first_seen": "2026-10-14", "last_seen": "2026-10-14",
        }, scope=subject_a, mentions=[{"source_type": "note", "source_id": "scope-note-b"}])
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM events")[0] == before
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM event_mentions")[0] == 0

    with signed_scoped_event_sources.transaction() as connection:
        connection.execute("UPDATE notes SET scope_evidence_ref=NULL WHERE note_id='scope-note-a'")
    with pytest.raises(ValueError, match="SOURCE_SCOPE_EVIDENCE_REQUIRED"):
        database.upsert_event({
            "event_key": f"{database._event_scope_token(subject_a)}.missing-evidence",
            "title": "Must not write without source Evidence", "first_seen": "2026-10-14",
            "last_seen": "2026-10-14",
        }, scope=subject_a, mentions=[{"source_type": "note", "source_id": "scope-note-a"}])
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM events")[0] == before
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM event_mentions")[0] == 0


def test_scoped_writer_rolls_back_event_and_evidence_when_mention_insert_fails(
        signed_scoped_event_sources):
    import sqlite3

    import database

    subject_a = {"product_id": "CTH", "domain_id": "cth", "subject_id": "SUBJECT-A",
                 "brand_focus_id": None, "global_scope": False}
    with signed_scoped_event_sources.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER fail_scoped_event_mention BEFORE INSERT ON event_mentions "
            "BEGIN SELECT RAISE(ABORT, 'isolated transaction recovery check'); END"
        )
    events_before = signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM events")[0]
    evidence_before = signed_scoped_event_sources.query_one(
        "SELECT COUNT(*) FROM app_evidence_records")[0]

    with pytest.raises(sqlite3.IntegrityError, match="isolated transaction recovery check"):
        database.upsert_event({
            "event_key": f"{database._event_scope_token(subject_a)}.rollback-check",
            "title": "Transaction rollback check", "first_seen": "2026-10-14",
            "last_seen": "2026-10-14",
        }, scope=subject_a, mentions=[{"source_type": "note", "source_id": "scope-note-a"}])

    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM events")[0] == events_before
    assert signed_scoped_event_sources.query_one("SELECT COUNT(*) FROM event_mentions")[0] == 0
    assert signed_scoped_event_sources.query_one(
        "SELECT COUNT(*) FROM app_evidence_records")[0] == evidence_before
