"""Isolated source-only brief projections over signed Canonical fixtures."""
import json
import sqlite3

import pytest

from canonical_data import CanonicalRecord, ensure_canonical_table, persist_canonical
from lumenis.shared.evidence import store as evidence_store
from lumenis.shared.reporting.operational_brief import build_scoped_source_brief


@pytest.fixture
def brief_db(tmp_path, monkeypatch):
    path = tmp_path / "scoped-source-brief.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"brief-test": "ephemeral-disposable-test-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "brief-test")
    with sqlite3.connect(path) as conn:
        evidence_store.ensure_evidence_schema(conn)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                conn.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
        ensure_canonical_table(connection=conn)
    return path


def _add_signed(conn, source_id, *, product="CTH", domain="cth", subject=None, brand=None,
                title="Real source title", url="https://source.example/item/42",
                published="2026-09-28T08:00:00Z", platform="web", source_type="web_mention"):
    evidence_id = evidence_store.record_evidence(
        connection=conn, source="public_http", project="LUMENIS", product=product,
        feature_id="SCOPED_SOURCE_BRIEF_TEST", test_name="signed_source",
        result="PASS", status="verified", inputs={"source_ids": [source_id]},
        outputs={"source_read": True}, domain_id=domain,
        subject_id=subject, brand_focus_id=brand,
    )
    record = CanonicalRecord(
        canonical_id=f"canonical-{source_id}", product_id=product, domain_id=domain,
        subject_id=subject or "", brand_focus_id=brand or "", scope_status="VERIFIED",
        scope_evidence_ref=str(evidence_id), source_id=source_id, external_id=source_id,
        source_type=source_type, source_platform=platform, title=title,
        content="PRIVATE ARTICLE BODY MUST NOT APPEAR", url=url,
        publish_datetime=published or "", captured_at="2026-09-29T10:11:12Z",
        sentiment="positive", risk_level="high",
    )
    persist_canonical(conn, record)
    return evidence_id


def _read_brief(path, **kwargs):
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return build_scoped_source_brief(conn, **kwargs)
    finally:
        conn.close()


def test_cth_global_focus_projection_preserves_source_times_and_safe_links(brief_db):
    with sqlite3.connect(brief_db) as conn:
        _add_signed(conn, "source-a", subject="SUBJECT-A", title="A [source]", platform="web")
        _add_signed(
            conn, "source-b", subject="SUBJECT-B", title="B #source",
            url="https://source.example/item?access_token=private-value", published=None,
            platform="forum",
        )
        conn.commit()

    global_result = _read_brief(
        brief_db, product_id="CTH", global_scope=True, entity_label="Registry CTH",
    )
    focus_result = _read_brief(
        brief_db, product_id="CTH", global_scope=False, entity_label="Subject A",
        subject_id="SUBJECT-A",
    )

    assert global_result["status"] == "PARTIAL"
    assert global_result["truncated"] is False and global_result["withheld"] is True
    assert {row["source_id"] for row in global_result["records"]} == {"source-a", "source-b"}
    assert global_result["coverage"] == global_result["freshness"] == "UNKNOWN"
    assert global_result["collection_state"] == "UNKNOWN"
    assert global_result["sample"]["counts_basis"].startswith("returned verified Canonical records only")
    assert global_result["records"][1]["publish_status"] == "UNKNOWN"
    assert global_result["records"][1]["captured_at"] == "2026-09-29T10:11:12Z"
    assert global_result["records"][1]["source_url"] is None
    assert "access_token" not in global_result["markdown"]
    assert "PRIVATE ARTICLE BODY" not in repr(global_result)
    assert "sentiment" not in repr(global_result) and "risk_level" not in repr(global_result)
    assert "https://source.example/item/42" in global_result["markdown"]
    assert "A \\[source\\]" in global_result["markdown"]
    assert [row["source_id"] for row in focus_result["records"]] == ["source-a"]
    assert focus_result["records"][0]["scope_evidence_ref"] == focus_result["records"][0]["evidence_id"]


def test_zbmp_focus_is_exact_and_hostile_source_labels_are_escaped(brief_db):
    hostile_platform = "web](javascript:alert(1))"
    with sqlite3.connect(brief_db) as conn:
        _add_signed(
            conn, "bmp-a", product="ZBMP", domain="zbmp", brand="BRAND-A",
            title="Title ](javascript:alert(1))", platform=hostile_platform,
        )
        _add_signed(conn, "bmp-b", product="ZBMP", domain="zbmp", brand="BRAND-B")
        conn.commit()

    result = _read_brief(
        brief_db, product_id="ZBMP", global_scope=False, entity_label="BMP Brand A",
        brand_focus_id="BRAND-A",
    )

    assert [row["source_id"] for row in result["records"]] == ["bmp-a"]
    assert "](javascript:" not in result["markdown"]
    assert hostile_platform not in result["markdown"]
    assert "\\]\\(javascript:alert" in result["markdown"] or "\\]" in result["markdown"]


def test_explicit_selection_rejects_ambiguous_identity_before_limit(brief_db):
    with sqlite3.connect(brief_db) as conn:
        _add_signed(conn, "selected", subject="SUBJECT-A")
        columns = [row[1] for row in conn.execute("PRAGMA table_info(canonical_data)")]
        row = list(conn.execute("SELECT * FROM canonical_data").fetchone())
        row[columns.index("canonical_id")] = "duplicate-canonical-identity"
        conn.execute("INSERT INTO canonical_data VALUES (" + ",".join("?" for _ in row) + ")", row)
    with pytest.raises(PermissionError, match="SOURCE_BRIEF_SELECTED_SOURCE_UNAVAILABLE"):
        _read_brief(brief_db, product_id="CTH", global_scope=False, entity_label="Subject A",
                    subject_id="SUBJECT-A", source_ids=["selected"], limit=1)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"product_id": "cth", "global_scope": True, "entity_label": "x"}, ValueError),
        ({"product_id": "CTH", "global_scope": True, "entity_label": "x", "subject_id": "S"}, ValueError),
        ({"product_id": "CTH", "global_scope": False, "entity_label": "x", "brand_focus_id": "B"}, ValueError),
        ({"product_id": "ZBMP", "global_scope": False, "entity_label": "x", "subject_id": "S"}, ValueError),
        ({"product_id": "CTH", "global_scope": True, "entity_label": " "}, ValueError),
    ],
)
def test_invalid_product_focus_or_missing_registry_label_is_rejected(brief_db, kwargs, error):
    with sqlite3.connect(brief_db.as_uri() + "?mode=ro", uri=True) as conn:
        with pytest.raises(error):
            build_scoped_source_brief(conn, **kwargs)


def test_rejected_and_unassigned_evidence_are_withheld_not_emitted(brief_db):
    with sqlite3.connect(brief_db) as conn:
        evidence_id = _add_signed(conn, "tampered", subject="SUBJECT-A")
        conn.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            (json.dumps({"source_ids": ["other-source"]}), evidence_id),
        )
        persist_canonical(conn, CanonicalRecord(
            canonical_id="canonical-unassigned", product_id="CTH", domain_id="cth",
            scope_status="UNASSIGNED", source_id="unassigned", external_id="unassigned",
            title="Must not appear", captured_at="2026-09-29T10:11:12Z",
        ))
        conn.commit()

    result = _read_brief(brief_db, product_id="CTH", global_scope=True, entity_label="Global")
    assert result["records"] == []
    assert result["status"] == "PARTIAL" and result["withheld"] is True
    assert result["sample"]["rejected_count"] == 2
    assert "Must not appear" not in result["markdown"]


def test_invalid_focus_is_empty_but_storage_failure_propagates(brief_db):
    with sqlite3.connect(brief_db) as conn:
        _add_signed(conn, "one", subject="SUBJECT-A")
        conn.commit()
    no_match = _read_brief(
        brief_db, product_id="CTH", global_scope=False,
        entity_label="Other subject", subject_id="SUBJECT-B",
    )
    assert no_match["status"] == "EMPTY" and no_match["records"] == []
    with sqlite3.connect(":memory:") as conn:
        with pytest.raises(sqlite3.OperationalError):
            build_scoped_source_brief(
                conn, product_id="CTH", global_scope=True, entity_label="Global",
            )


def test_readonly_database_reopen_returns_same_projection_and_hash(brief_db):
    with sqlite3.connect(brief_db) as conn:
        _add_signed(conn, "stable", subject="SUBJECT-A", published=None)
        conn.commit()
    request = {"product_id": "CTH", "global_scope": True, "entity_label": "Global"}
    first = _read_brief(brief_db, **request)
    second = _read_brief(brief_db, **request)
    assert first == second
    assert first["records"][0]["publish_datetime"] is None
    assert first["records"][0]["captured_at"] is not None
    assert first["content_hash"]
