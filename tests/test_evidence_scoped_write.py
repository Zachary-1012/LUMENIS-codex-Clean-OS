"""Storage-write contract for exact Evidence scope; uses disposable SQLite files."""
import json
import sqlite3

import pytest

from lumenis.shared.database import DatabaseRepository
from lumenis.shared.evidence import store


@pytest.fixture
def evidence_db(tmp_path, monkeypatch):
    path = tmp_path / "scoped-evidence.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"scoped-write-test": "isolated-scoped-write-secret"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "scoped-write-test")
    repository = DatabaseRepository(str(path))
    monkeypatch.setattr(store, "get_repository", lambda: repository)
    store.init_evidence_store(str(path))
    with sqlite3.connect(path) as conn:
        store.ensure_evidence_schema(conn)
    return path


@pytest.mark.parametrize(
    "product,domain_id,scope_args,expected",
    [
        (
            "CTH",
            "cth",
            {"subject_id": "SUBJ-1"},
            {
                "domain_id": "cth",
                "product_id": "CTH",
                "global": False,
                "subject_id": "SUBJ-1",
            },
        ),
        (
            "CTH",
            "CTH",
            {"global_scope": True},
            {"domain_id": "cth", "product_id": "CTH", "global": True},
        ),
        (
            "BMP",
            "BMP",
            {"brand_focus_id": "BRAND-1"},
            {
                "domain_id": "zbmp",
                "product_id": "ZBMP",
                "global": False,
                "brand_focus_id": "BRAND-1",
            },
        ),
        (
            "ZBMP",
            "zbmp",
            {"global_scope": True},
            {"domain_id": "zbmp", "product_id": "ZBMP", "global": True},
        ),
    ],
)
def test_scoped_writer_stores_exact_scope(
    evidence_db, product, domain_id, scope_args, expected
):
    record_id = store.record_evidence(
        source="fixture",
        product=product,
        feature_id="SCOPED-WRITE",
        inputs={"source_id": "fixture-1"},
        domain_id=domain_id,
        **scope_args,
    )

    assert record_id > 0
    with sqlite3.connect(evidence_db) as conn:
        row = conn.execute(
            "SELECT inputs_json, domain_id, product_id "
            "FROM app_evidence_records WHERE id=?",
            (record_id,),
        ).fetchone()

    assert json.loads(row[0]) == {
        "source_id": "fixture-1",
        "_lumenis_scope": expected,
    }
    assert row[1:] == (expected["domain_id"], expected["product_id"])


def test_scoped_reader_isolates_focus_global_and_unassigned_rows(evidence_db):
    def write(product, domain_id=None, **scope):
        return store.record_evidence(
            source="fixture",
            product=product,
            feature_id="SCOPED-READ",
            inputs={"source_id": "fixture"},
            domain_id=domain_id,
            **scope,
        )

    subject_one = write("CTH", "cth", subject_id="SUBJ-1")
    subject_two = write("CTH", "cth", subject_id="SUBJ-2")
    cth_global = write("CTH", "cth", global_scope=True)
    brand_one = write("BMP", "zbmp", brand_focus_id="BRAND-1")
    bmp_global = write("BMP", "zbmp", global_scope=True)
    legacy = write("CTH")
    assert all(record_id > 0 for record_id in (
        subject_one, subject_two, cth_global, brand_one, bmp_global, legacy
    ))

    def ids(**scope):
        return [row["id"] for row in store.query_scoped_evidence(**scope)]

    assert ids(product="CTH", domain_id="cth", subject_id="SUBJ-1") == [subject_one]
    assert ids(product="CTH", domain_id="CTH", subject_id="SUBJ-2") == [subject_two]
    assert ids(product="CTH", domain_id="cth", global_scope=True) == [cth_global]
    assert ids(product="BMP", domain_id="bmp", brand_focus_id="BRAND-1") == [brand_one]
    assert ids(product="ZBMP", domain_id="zbmp", global_scope=True) == [bmp_global]


def test_scoped_reader_skips_malformed_metadata_before_pagination(evidence_db):
    first = store.record_evidence(
        product="CTH", domain_id="cth", subject_id="SUBJ-1", feature_id="READ"
    )
    second = store.record_evidence(
        product="CTH", domain_id="cth", subject_id="SUBJ-1", feature_id="READ"
    )
    malformed = store.record_evidence(
        product="CTH", domain_id="cth", subject_id="SUBJ-1", feature_id="READ"
    )
    with sqlite3.connect(evidence_db) as conn:
        conn.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            ("{not-json", malformed),
        )

    scope = {"product": "CTH", "domain_id": "cth", "subject_id": "SUBJ-1"}
    assert [r["id"] for r in store.query_scoped_evidence(**scope, limit=1)] == [second]
    assert [r["id"] for r in store.query_scoped_evidence(**scope, limit=1, offset=1)] == [first]


@pytest.mark.parametrize(
    "scope",
    [
        {"product": "CTH", "domain_id": "cth"},
        {"product": "CTH", "domain_id": "cth", "subject_id": "SUBJ", "global_scope": True},
        {"product": "BMP", "domain_id": "cth", "brand_focus_id": "BRAND"},
        {"product": "CTH", "domain_id": "cth", "subject_id": "SUBJ", "limit": 0},
        {"product": "CTH", "domain_id": "cth", "subject_id": "SUBJ", "offset": -1},
    ],
)
def test_scoped_reader_rejects_missing_or_invalid_scope(evidence_db, scope):
    with pytest.raises(ValueError):
        store.query_scoped_evidence(**scope)


def test_legacy_unscoped_writer_keeps_inputs_and_leaves_scope_unassigned(evidence_db):
    record_id = store.record_evidence(
        source="fixture",
        product="CTH",
        feature_id="LEGACY-WRITE",
        inputs={"legacy": True},
    )
    list_input_id = store.record_evidence(
        source="fixture",
        product="CTH",
        feature_id="LEGACY-LIST-INPUT",
        inputs=["legacy", "input"],
    )

    assert record_id > 0
    assert list_input_id > 0
    with sqlite3.connect(evidence_db) as conn:
        rows = conn.execute(
            "SELECT id, inputs_json, domain_id, product_id "
            "FROM app_evidence_records WHERE id IN (?, ?) ORDER BY id",
            (record_id, list_input_id),
        ).fetchall()

    assert json.loads(rows[0][1]) == {"legacy": True}
    assert rows[0][2:] == (None, None)
    assert json.loads(rows[1][1]) == ["legacy", "input"]
    assert rows[1][2:] == (None, None)


@pytest.mark.parametrize(
    "product,domain_id,scope_args",
    [
        ("CTH", "cth", {"subject_id": "SUBJ-1", "global_scope": True}),
        ("CTH", "cth", {"brand_focus_id": "BRAND-1"}),
        ("BMP", "bmp", {"subject_id": "SUBJ-1"}),
        ("BMP", "cth", {"brand_focus_id": "BRAND-1"}),
        ("CTH", "", {"subject_id": "SUBJ-1"}),
        ("CTH", "cth", {"subject_id": "SUBJ-1", "global_scope": 1}),
    ],
)
def test_invalid_or_mismatched_scope_is_rejected(
    evidence_db, product, domain_id, scope_args
):
    with pytest.raises(ValueError):
        store.record_evidence(
            source="fixture",
            product=product,
            feature_id="INVALID-SCOPE",
            inputs={"source_id": "fixture-1"},
            domain_id=domain_id,
            **scope_args,
        )

    with sqlite3.connect(evidence_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='INVALID-SCOPE'"
        ).fetchone()[0]
    assert count == 0


@pytest.mark.parametrize(
    "inputs",
    [
        ["not", "an", "object"],
        "_not_an_object",
        {"_lumenis_scope": {"domain_id": "cth", "global": True}},
        {"unsupported": object()},
        {"not_finite": float("nan")},
    ],
)
def test_scoped_writer_rejects_malformed_or_reserved_inputs(evidence_db, inputs):
    with pytest.raises(ValueError):
        store.record_evidence(
            source="fixture",
            product="CTH",
            feature_id="INVALID-INPUTS",
            inputs=inputs,
            domain_id="cth",
            subject_id="SUBJ-1",
        )


def test_reserved_scope_metadata_is_never_accepted_as_legacy_authority(evidence_db):
    with pytest.raises(ValueError):
        store.record_evidence(
            source="fixture",
            product="CTH",
            feature_id="RESERVED-LEGACY-INPUT",
            inputs={"_lumenis_scope": {"domain_id": "cth", "global": True}},
        )


@pytest.mark.parametrize("missing_column", ["domain_id", "product_id", "inputs_json"])
def test_scoped_write_refuses_incomplete_schema_without_scope_loss(
    tmp_path, monkeypatch, missing_column
):
    path = tmp_path / f"missing-{missing_column}.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    repository = DatabaseRepository(str(path))
    monkeypatch.setattr(store, "get_repository", lambda: repository)
    columns = ["source TEXT", "feature_id TEXT", "metric_name TEXT", "metric_value TEXT"]
    for required in ("domain_id TEXT", "product_id TEXT", "inputs_json TEXT"):
        if required.split()[0] != missing_column:
            columns.append(required)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE app_evidence_records (id INTEGER PRIMARY KEY, "
            + ", ".join(columns)
            + ")"
        )

    failed_id = store.record_evidence(
        source="fixture",
        product="CTH",
        feature_id="SCHEMA-MISSING-SCOPE",
        inputs={"source_id": "fixture-1"},
        domain_id="cth",
        subject_id="SUBJ-1",
    )
    assert failed_id == -1

    legacy_id = store.record_evidence(
        source="fixture",
        product="CTH",
        feature_id="LEGACY-ON-OLD-SCHEMA",
        inputs={"legacy": True},
    )
    assert legacy_id > 0
    with sqlite3.connect(path) as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        if "inputs_json" in columns:
            rows = conn.execute(
                "SELECT feature_id, inputs_json FROM app_evidence_records ORDER BY id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT feature_id FROM app_evidence_records ORDER BY id"
            ).fetchall()
    if missing_column == "inputs_json":
        assert rows == [("LEGACY-ON-OLD-SCHEMA",)]
    else:
        assert rows == [
            ("LEGACY-ON-OLD-SCHEMA", json.dumps({"legacy": True}))
        ]


def test_failed_scoped_write_replays_only_after_scope_storage_exists(tmp_path, monkeypatch):
    path = tmp_path / "scoped-replay.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"scoped-replay-test": "isolated-scoped-replay-secret"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "scoped-replay-test")
    repository = DatabaseRepository(str(path))
    monkeypatch.setattr(store, "get_repository", lambda: repository)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE app_evidence_records ("
            "id INTEGER PRIMARY KEY, source TEXT, feature_id TEXT, "
            "metric_name TEXT, metric_value TEXT, inputs_json TEXT, domain_id TEXT)"
        )
        conn.execute(
            "CREATE TABLE runtime_guardian_dlq ("
            "id INTEGER PRIMARY KEY, dlq_id TEXT, worker_id TEXT, run_id TEXT, "
            "task_type TEXT, payload TEXT, error TEXT, error_type TEXT, "
            "attempts INTEGER, max_attempts INTEGER, status TEXT, created_at TEXT, "
            "updated_at TEXT, domain_id TEXT, product_id TEXT, "
            "last_attempt_at TEXT, resolved_at TEXT)"
        )

    assert store.record_evidence(
        source="fixture",
        product="CTH",
        feature_id="SCOPED-REPLAY",
        inputs={"source_id": "fixture-1"},
        domain_id="cth",
        subject_id="SUBJ-1",
    ) == -1
    first = store.replay_failed_evidence()
    assert first["succeeded"] == 0
    assert first["failed"] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0] == 0
        assert conn.execute(
            "SELECT status FROM runtime_guardian_dlq"
        ).fetchone()[0] == "PENDING"
        conn.execute("ALTER TABLE app_evidence_records ADD COLUMN product_id TEXT")
        store.ensure_evidence_schema(conn)

    second = store.replay_failed_evidence()
    assert second["succeeded"] == 1
    assert second["failed"] == 0
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT domain_id, product_id, inputs_json FROM app_evidence_records"
        ).fetchone()
        assert row[0:2] == ("cth", "CTH")
        assert json.loads(row[2])["_lumenis_scope"]["subject_id"] == "SUBJ-1"
        assert conn.execute(
            "SELECT status FROM runtime_guardian_dlq"
        ).fetchone()[0] == "RESOLVED"
