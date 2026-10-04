"""GLOBAL native observations remain explicitly unassigned and evidence-bound."""
from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest


PLATFORM = "web_atom"
NOTE_ID = "atom-source-001"


def _connect(path):
    return sqlite3.connect(str(path), timeout=10)


@pytest.fixture
def observation_case(tmp_path, monkeypatch):
    db_path = tmp_path / "unassigned-platform-observations.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"unassigned-observation-test": "isolated-unassigned-observation-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "unassigned-observation-test")

    import database
    from lumenis.shared.database import DatabaseRepository, migrations
    from lumenis.shared.database import repository as repository_module
    from lumenis.shared.evidence import store as evidence_store

    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(
        repository_module, "_default_repository", DatabaseRepository(str(db_path)),
    )
    database.init_db()
    assert migrations.migrate(target_version=19) is True
    evidence_store.init_evidence_store(str(db_path))
    with migrations.get_connection() as connection:
        assert migrations.get_current_version(connection) == 19
        for table in ("notes", "canonical_data", "app_evidence_records", "platform_contents", "metric_snapshots"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    return {"db_path": db_path, "database": database, "evidence_store": evidence_store}


def _record(*, view_count=0, include_view=True):
    record = {
        "content_id": NOTE_ID,
        "title": "Atom source title",
        "content": "Atom source body",
        "url": "https://example.test/items/atom-source-001",
        "published_at": "2026-09-30T12:00:00Z",
        "source_extra": {"retained": ["original", 7]},
        "cookie": "must-not-persist",
        "access_token": "must-not-persist",
    }
    if include_view:
        record["view_count"] = view_count
    return record


def _scope(domain="cth", **overrides):
    value = {"domain_id": domain, "global_scope": True, "subject_id": None, "brand_focus_id": None}
    value.update(overrides)
    return value


def _seed_unassigned_rows(
    case, source_id=NOTE_ID, *, platform=PLATFORM, canonical_status="UNASSIGNED",
):
    domain = "zbmp" if case.get("domain") == "bmp" else "cth"
    product = "ZBMP" if domain == "zbmp" else "CTH"
    with _connect(case["db_path"]) as connection:
        connection.execute(
            "INSERT INTO notes (note_id, source_platform, product_id, domain_id, "
            "subject_id, brand_focus_id, scope_status, scope_evidence_ref) "
            "VALUES (?, ?, ?, ?, NULL, NULL, 'UNASSIGNED', NULL)",
            (source_id, platform, product, domain),
        )
        connection.execute(
            "INSERT INTO canonical_data (canonical_id, product_id, domain_id, source_id, "
            "external_id, source_type, source_platform, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref) "
            "VALUES (?, ?, ?, ?, ?, 'note', ?, NULL, NULL, ?, NULL)",
            (f"canonical:{source_id}", product, domain, source_id, source_id,
             platform, canonical_status),
        )


def _proof(records, platform=PLATFORM):
    from lumenis.shared.database.platform_content import _stable_observation
    from lumenis.system.collector.adapters.secondary_collection import _credential_free_observations

    return [{
        "source_id": record["content_id"],
        "platform": platform,
        "observation_sha256": hashlib.sha256(json.dumps(
            _stable_observation(_credential_free_observations(dict(record))),
            ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest(),
    } for record in records]


def _evidence(case, records, *, platform=PLATFORM, domain="cth", source_ids=None, proof=None):
    product = "ZBMP" if domain == "bmp" else "CTH"
    return case["evidence_store"].record_evidence(
        source="collector", project="LUMENIS", product=product,
        feature_id="GLOBAL_PLATFORM_OBSERVATION", result="PASS", status="verified",
        inputs={
            "platform": platform,
            "source_ids": list(source_ids if source_ids is not None else [record["content_id"] for record in records]),
            "source_observations": list(proof if proof is not None else _proof(records, platform)),
        },
        domain_id="zbmp" if domain == "bmp" else "cth", global_scope=True,
    )


def _persist(case, records, evidence_id, *, platform=PLATFORM, scope=None, connection=None):
    from lumenis.shared.database.platform_content import persist_unassigned_platform_records

    return persist_unassigned_platform_records(
        records, platform=platform, note_ids=[record["content_id"] for record in records],
        evidence_id=evidence_id, scope=scope or _scope(), connection=connection,
    )


def test_global_records_persist_native_truth_sanitize_raw_and_append_only_known_metrics(observation_case):
    case = observation_case
    _seed_unassigned_rows(case)
    original = _record(view_count=0)
    snapshot_input = json.loads(json.dumps(original))
    evidence_id = _evidence(case, [original])

    assert _persist(case, [original], evidence_id) == 1
    assert original == snapshot_input
    with _connect(case["db_path"]) as connection:
        native = connection.execute(
            "SELECT platform_content_id, view_count, like_count, comment_count, raw_data, "
            "first_collected_at FROM platform_contents WHERE platform=? AND platform_content_id=?",
            (PLATFORM, NOTE_ID),
        ).fetchone()
        metric_count = connection.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]
        note_scope = connection.execute(
            "SELECT scope_status, subject_id, brand_focus_id FROM notes WHERE note_id=?", (NOTE_ID,),
        ).fetchone()
        canonical_scope = connection.execute(
            "SELECT scope_status, subject_id, brand_focus_id FROM canonical_data WHERE source_id=?", (NOTE_ID,),
        ).fetchone()
    raw = json.loads(native[4])
    assert native[:4] == (NOTE_ID, 0, None, None)
    assert native[5]
    assert metric_count == 1
    assert raw["source_extra"] == {"retained": ["original", 7]}
    assert "cookie" not in raw and "access_token" not in raw
    assert raw["_lumenis_evidence_id"] == evidence_id
    assert note_scope == canonical_scope == ("UNASSIGNED", None, None)
    from lumenis.shared.database.platform_content import platform_records_changed
    assert platform_records_changed([original], platform=PLATFORM) is False

    first_collected_at = native[5]
    same_evidence = _evidence(case, [original])
    assert _persist(case, [original], same_evidence) == 1
    with _connect(case["db_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0] == 1
        assert connection.execute(
            "SELECT first_collected_at FROM platform_contents WHERE platform=? AND platform_content_id=?",
            (PLATFORM, NOTE_ID),
        ).fetchone()[0] == first_collected_at

    changed = _record(view_count=4)
    changed_evidence = _evidence(case, [changed])
    assert _persist(case, [changed], changed_evidence) == 1
    unknown = _record(include_view=False)
    unknown_evidence = _evidence(case, [unknown])
    assert _persist(case, [unknown], unknown_evidence) == 1
    with _connect(case["db_path"]) as connection:
        history_rows = connection.execute(
            "SELECT entity_type, entity_key, raw_json FROM metric_snapshots ORDER BY id"
        ).fetchall()
        final_native = connection.execute(
            "SELECT view_count, first_collected_at, raw_data FROM platform_contents "
            "WHERE platform=? AND platform_content_id=?", (PLATFORM, NOTE_ID),
        ).fetchone()
    assert len({(row[0], row[1]) for row in history_rows}) == 1
    assert history_rows[0][0] == "platform_content"
    assert history_rows[0][1].endswith(f":{NOTE_ID}")
    assert [json.loads(row[2])["view_count"] for row in history_rows] == [0, 4, None]
    assert final_native[0] is None
    assert final_native[1] == first_collected_at
    assert "view_count" not in json.loads(final_native[2])


@pytest.mark.parametrize("scope", [
    {"domain_id": "cth", "global_scope": 1, "subject_id": None, "brand_focus_id": None},
    {"domain_id": "other", "global_scope": True, "subject_id": None, "brand_focus_id": None},
    {"domain_id": "cth", "global_scope": True, "subject_id": "SUBJECT-1", "brand_focus_id": None},
])
def test_invalid_global_scope_is_rejected_before_persistence(observation_case, scope):
    case = observation_case
    _seed_unassigned_rows(case)
    record = _record()
    evidence_id = _evidence(case, [record])
    with pytest.raises(ValueError):
        _persist(case, [record], evidence_id, scope=scope)
    with _connect(case["db_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM platform_contents").fetchone()[0] == 0


def test_source_ids_and_observation_hash_are_mandatory_exact_and_signed(observation_case):
    case = observation_case
    _seed_unassigned_rows(case)
    record = _record()
    wrong_hash = _proof([record])
    wrong_hash[0]["observation_sha256"] = "0" * 64
    for evidence_id in (
        _evidence(case, [record], source_ids=["different-id"]),
        _evidence(case, [record], proof=wrong_hash),
    ):
        with pytest.raises(ValueError):
            _persist(case, [record], evidence_id)
    tampered = _evidence(case, [record])
    with _connect(case["db_path"]) as connection:
        connection.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            (json.dumps({"platform": PLATFORM, "source_ids": [NOTE_ID]}), tampered),
        )
    with pytest.raises(ValueError, match="writer-authenticated"):
        _persist(case, [record], tampered)
    with _connect(case["db_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM platform_contents").fetchone()[0] == 0


def test_evidence_domain_mismatch_and_any_assigned_canonical_row_are_denied(observation_case):
    case = observation_case
    record = _record()
    _seed_unassigned_rows(case)
    wrong_domain = _evidence(case, [record], domain="bmp")
    with pytest.raises(ValueError, match="GLOBAL scope"):
        _persist(case, [record], wrong_domain)
    with _connect(case["db_path"]) as connection:
        connection.execute(
            "UPDATE canonical_data SET scope_status='VERIFIED', subject_id='SUBJECT-1' WHERE source_id=?",
            (NOTE_ID,),
        )
    correct_scope_evidence = _evidence(case, [record])
    with pytest.raises(ValueError, match="unassigned GLOBAL identity"):
        _persist(case, [record], correct_scope_evidence)
    with _connect(case["db_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM platform_contents").fetchone()[0] == 0


def test_caller_transaction_owns_rollback_for_unassigned_write(observation_case):
    case = observation_case
    _seed_unassigned_rows(case)
    record = _record(view_count=3)
    evidence_id = _evidence(case, [record])
    with _connect(case["db_path"]) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert _persist(case, [record], evidence_id, connection=connection) == 1
        assert connection.in_transaction is True
        assert connection.execute("SELECT COUNT(*) FROM platform_contents").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0] == 1
        connection.rollback()
    with _connect(case["db_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM platform_contents").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0] == 0
        assert connection.execute("SELECT scope_status FROM notes WHERE note_id=?", (NOTE_ID,)).fetchone()[0] == "UNASSIGNED"


@pytest.mark.parametrize(("platform", "record", "expected"), [
    (
        "xiaohongshu",
        {
            "content_id": "xhs-published-001", "note_id": "xhs-published-001",
            "title": "XHS timestamp", "desc": "source body", "time": 1790935200000,
            "captured_at": "2030-01-01T00:00:00Z", "updated_at": "2031-01-01T00:00:00Z",
        },
        "2026-10-02T10:00:00+00:00",
    ),
    (
        "bilibili",
        {
            "content_id": "BV1xx411c7mD", "bvid": "BV1xx411c7mD",
            "title": "Bilibili timestamp", "description": "source body", "pubdate": 1790935200,
            "captured_at": "2030-01-01T00:00:00Z", "updated_at": "2031-01-01T00:00:00Z",
        },
        "2026-10-02T10:00:00+00:00",
    ),
    (
        "instagram",
        {
            "content_id": "instagram-001", "media_id": "instagram-001",
            "title": "Instagram timestamp", "caption": "source body", "taken_at": 1790935200,
            "captured_at": "2030-01-01T00:00:00Z", "updated_at": "2031-01-01T00:00:00Z",
        },
        None,
    ),
])
def test_native_publication_units_are_normalized_only_in_native_view(
    observation_case, platform, record, expected,
):
    from lumenis.shared.database.platform_content import persist_unassigned_platform_records

    case = observation_case
    source_id = record["content_id"]
    _seed_unassigned_rows(case, source_id, platform=platform)
    original = json.loads(json.dumps(record))
    evidence_id = _evidence(case, [record], platform=platform)
    assert persist_unassigned_platform_records(
        [record], platform=platform, note_ids=[source_id], evidence_id=evidence_id,
        scope=_scope(),
    ) == 1
    with _connect(case["db_path"]) as connection:
        published_at, raw_data = connection.execute(
            "SELECT published_at, raw_data FROM platform_contents "
            "WHERE platform=? AND platform_content_id=?", (platform, source_id),
        ).fetchone()
    assert published_at == expected
    stored = json.loads(raw_data)
    assert stored == original | {"_lumenis_evidence_id": evidence_id}
    for key in ("time", "pubdate", "taken_at"):
        if key in original:
            assert stored[key] == original[key]
    assert record == original


@pytest.mark.parametrize(("record", "expected"), [
    (
        {"content_id": "no-published-001", "title": "Updated only", "content": "body",
         "updated_at": "2026-09-30T12:00:00Z", "captured_at": "2026-10-01T00:00:00Z"},
        None,
    ),
    (
        {"content_id": "yearless-001", "title": "Yearless", "content": "body",
         "published_at": "Sep 14", "updated_at": "2026-09-30T12:00:00Z",
         "captured_at": "2026-10-01T00:00:00Z"},
        None,
    ),
    (
        {"content_id": "explicit-publish-datetime-001", "title": "Explicit fallback",
         "content": "body", "updated_at": "2026-09-30T12:00:00Z",
         "publish_datetime": "2026-09-29T10:15:00Z"},
        "2026-09-29T10:15:00Z",
    ),
])
def test_only_valid_native_or_explicit_publish_datetime_sets_publication(
    observation_case, record, expected,
):
    case = observation_case
    source_id = record["content_id"]
    _seed_unassigned_rows(case, source_id, platform=PLATFORM)
    original = json.loads(json.dumps(record))
    evidence_id = _evidence(case, [record])
    assert _persist(case, [record], evidence_id) == 1
    with _connect(case["db_path"]) as connection:
        published_at, raw_data = connection.execute(
            "SELECT published_at, raw_data FROM platform_contents "
            "WHERE platform=? AND platform_content_id=?", (PLATFORM, source_id),
        ).fetchone()
    assert published_at == expected
    assert json.loads(raw_data) == original | {"_lumenis_evidence_id": evidence_id}
    assert record == original
