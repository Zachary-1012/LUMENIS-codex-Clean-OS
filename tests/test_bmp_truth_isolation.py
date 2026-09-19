"""BMP canonical truth-boundary regression tests.

These tests use an OS temporary SQLite database and deliberately place a CTH
row beside a ZBMP row.  BMP APIs and Experience must only expose the ZBMP
canonical slice; authors, notes, and web_mentions are not brand truth.
"""

import json
import sqlite3

from canonical_data import CanonicalRecord, ensure_canonical_table, persist_canonical


def _seed_domain_rows(db_path):
    ensure_canonical_table(str(db_path))
    con = sqlite3.connect(str(db_path))
    try:
        persist_canonical(
            con,
            CanonicalRecord(
                canonical_id="CAN-CTH-ISOLATION",
                product_id="CTH",
                domain_id="cth",
                subject_id="GUANGZHOU_TAIKOO_HUI",
                title="CTH PRIVATE TRUTH",
                content="CTH_PRIVATE_CONTENT_MUST_NOT_LEAK",
                source_platform="xhs",
                captured_at="2026-09-17 09:00:00",
            ),
        )
        persist_canonical(
            con,
            CanonicalRecord(
                canonical_id="CAN-ZBMP-ISOLATION",
                product_id="ZBMP",
                domain_id="zbmp",
                title="ZBMP evidence",
                content="ZBMP_PUBLIC_CONTENT",
                source_id="xhs-note-1",
                source_type="note",
                source_table="notes",
                source_platform="xhs",
                sentiment="negative",
                risk_level="high",
                risk_score=8,
                engagement_likes=None,
                engagement_comments=12,
                captured_at="2026-09-17 10:00:00",
                evidence_ref="EV-ZBMP-ISOLATION",
            ),
        )
        con.commit()
    finally:
        con.close()


def test_zbmp_snapshot_filters_cth_and_does_not_infer_brands(tmp_path, monkeypatch):
    db_path = tmp_path / "bmp-isolation.db"
    _seed_domain_rows(db_path)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    from api_dual_domain import get_zbmp_product_snapshot

    snapshot = get_zbmp_product_snapshot()
    assert snapshot["data_state"] == "READY"
    assert snapshot["total_records"] == 1
    assert snapshot["canonical_records"][0]["canonical_id"] == "CAN-ZBMP-ISOLATION"
    assert snapshot["canonical_records"][0]["evidence_ref"] == "EV-ZBMP-ISOLATION"
    assert snapshot["brands"] == []
    blob = json.dumps(snapshot, ensure_ascii=False)
    assert "CTH_PRIVATE_CONTENT_MUST_NOT_LEAK" not in blob
    assert "GUANGZHOU_TAIKOO_HUI" not in blob


def test_zbmp_api_and_experience_use_same_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "bmp-api-isolation.db"
    _seed_domain_rows(db_path)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    from api_dual_domain import get_zbmp_product_snapshot
    from experience_screens import _build_bmp01

    snapshot = get_zbmp_product_snapshot()
    screen = _build_bmp01()
    assert screen["truth"]["canonical_count"] == snapshot["total_records"] == 1
    assert screen["truth"]["data_state"] == "READY"
    assert screen["truth"]["domain_id"] == "zbmp"
    assert screen["truth"]["product_id"] == "ZBMP"
    risk_section = next(s for s in screen["sections"] if s["type"] == "risks")
    assert risk_section["items"][0]["evidence"] == "EV-ZBMP-ISOLATION"
    blob = json.dumps(screen, ensure_ascii=False)
    assert "CTH_PRIVATE_CONTENT_MUST_NOT_LEAK" not in blob
    assert "GUANGZHOU_TAIKOO_HUI" not in blob


def test_zbmp_missing_canonical_table_is_not_collected(tmp_path, monkeypatch):
    db_path = tmp_path / "bmp-empty.db"
    sqlite3.connect(str(db_path)).close()
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    from api_dual_domain import get_zbmp_product_snapshot

    snapshot = get_zbmp_product_snapshot()
    assert snapshot["data_state"] == "NOT_COLLECTED"
    assert snapshot["total_records"] == 0
    assert snapshot["brands"] == []
    con = sqlite3.connect(str(db_path))
    try:
        assert con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='canonical_data'"
        ).fetchone() is None
    finally:
        con.close()
