"""Shared Evidence generic schema and additive migration contracts."""
import json
import sqlite3

from lumenis.shared.evidence import store


def _record_and_assert_query_and_stats():
    record_id = store.record_evidence(
        source="integration",
        project="LUMENIS",
        product="CTH",
        feature_id="EVIDENCE-SCHEMA-01",
        asset_id="fixture-asset",
        commit_sha="abc123",
        version="test",
        env="isolated",
        level="feature",
        test_name="canonical owner contract",
        result="PASS",
        inputs={"subject": "fixture"},
        outputs={"verified": True},
        expected="record is queryable",
        actual="record persisted",
        account="fixture-account",
        duration_ms=12,
        raw_content="synthetic evidence only",
    )
    assert record_id > 0

    rows = store.query_evidence(
        project="LUMENIS",
        product="CTH",
        feature_id="EVIDENCE-SCHEMA-01",
        level="feature",
        result="PASS",
        account="fixture-account",
        env="isolated",
    )
    assert len(rows) == 1
    assert rows[0]["id"] == record_id
    assert rows[0]["actual"] == "record persisted"
    assert rows[0]["inputs_json"] == '{"subject": "fixture"}'
    assert rows[0]["outputs_json"] == '{"verified": true}'

    stats = store.get_stats()
    assert stats["total"] >= 1
    assert stats["by_result"]["PASS"] >= 1
    assert stats["by_level"]["feature"] >= 1
    assert stats["by_account"]["fixture-account"] >= 1
    assert any(row["id"] == record_id for row in stats["recent"])


def test_fresh_evidence_store_supports_generic_write_query_and_stats(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh-evidence.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    store.init_evidence_store(str(db_path))

    _record_and_assert_query_and_stats()


def test_legacy_evidence_table_migrates_additively_without_changing_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy-evidence.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE app_evidence_records (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               source TEXT NOT NULL DEFAULT 'xhs_app',
               capture_mode TEXT NOT NULL DEFAULT 'screenshot',
               captured_at TEXT,
               topic TEXT,
               metric_name TEXT NOT NULL,
               metric_value TEXT NOT NULL,
               evidence_hash TEXT,
               evidence_path TEXT,
               parse_confidence REAL DEFAULT 1.0,
               verified_by TEXT,
               verified_at TEXT,
               status TEXT NOT NULL DEFAULT 'pending',
               notes TEXT,
               created_at TEXT NOT NULL,
               updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """INSERT INTO app_evidence_records
               (source, capture_mode, captured_at, topic, metric_name, metric_value,
                evidence_hash, status, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "legacy-fixture", "manual", "2026-09-01 12:00:00", "subject",
                "legacy metric", "7", "legacy-hash", "confirmed", "keep this row",
                "2026-09-01 12:00:00", "2026-09-01 12:00:00",
            ),
        )
        before = conn.execute(
            """SELECT id, source, capture_mode, captured_at, topic, metric_name,
                      metric_value, evidence_hash, status, notes, created_at, updated_at
                 FROM app_evidence_records WHERE id=1"""
        ).fetchone()

    store.init_evidence_store(str(db_path))

    with sqlite3.connect(db_path) as conn:
        after = conn.execute(
            """SELECT id, source, capture_mode, captured_at, topic, metric_name,
                      metric_value, evidence_hash, status, notes, created_at, updated_at
                 FROM app_evidence_records WHERE id=1"""
        ).fetchone()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")}
    assert after == before
    assert {
        "project", "product", "feature_id", "level", "result", "account", "env",
        "actual", "inputs_json", "outputs_json", "duration_ms", "content_hash",
        "subject_scope", "collection_metadata", "provider", "domain_id", "product_id",
    } <= columns

    _record_and_assert_query_and_stats()

    with sqlite3.connect(db_path) as conn:
        legacy = conn.execute(
            "SELECT metric_name, metric_value, status, notes FROM app_evidence_records WHERE id=1"
        ).fetchone()
    assert legacy == ("legacy metric", "7", "confirmed", "keep this row")


def test_invalid_replay_json_is_dead_lettered_and_does_not_block_queue(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "evidence-replay-dlq.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE app_evidence_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL
            );
            CREATE TABLE runtime_guardian_dlq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dlq_id TEXT, worker_id TEXT, run_id TEXT, task_type TEXT,
                payload TEXT, error TEXT, error_type TEXT, attempts INTEGER,
                max_attempts INTEGER, status TEXT, created_at TEXT,
                updated_at TEXT, last_attempt_at TEXT, resolved_at TEXT,
                domain_id TEXT, product_id TEXT
            );
            """
        )
        conn.executemany(
            """INSERT INTO runtime_guardian_dlq
               (dlq_id, task_type, payload, attempts, max_attempts, status)
               VALUES (?, 'evidence_write', ?, 0, 5, 'PENDING')""",
            [
                ("bad-json", "{broken"),
                (
                    "valid-row",
                    json.dumps({
                        "source": "test",
                        "metric_name": "m",
                        "metric_value": "v",
                    }),
                ),
            ],
        )

    from lumenis.shared.database import DatabaseRepository

    repository = DatabaseRepository(str(db_path))
    monkeypatch.setattr(store, "get_repository", lambda: repository)

    first = store.replay_failed_evidence(limit=1)
    with sqlite3.connect(db_path) as conn:
        bad = conn.execute(
            "SELECT status, attempts, error FROM runtime_guardian_dlq WHERE dlq_id='bad-json'"
        ).fetchone()
    assert first["replayed"] == 1
    assert first["failed"] == 1
    assert first["remaining"] == 1
    assert bad[0] == "DEAD_LETTER"
    assert bad[1] == 1
    assert "invalid evidence replay JSON" in bad[2]

    second = store.replay_failed_evidence(limit=1)
    assert second["replayed"] == 1
    assert second["succeeded"] == 1
    assert second["remaining"] == 0
    with sqlite3.connect(db_path) as conn:
        valid = conn.execute(
            "SELECT status, attempts FROM runtime_guardian_dlq WHERE dlq_id='valid-row'"
        ).fetchone()
        evidence = conn.execute(
            "SELECT source, metric_name, metric_value FROM app_evidence_records"
        ).fetchone()
    assert valid == ("RESOLVED", 1)
    assert evidence == ("test", "m", "v")
