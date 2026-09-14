"""Regression tests for nullable content-generation evidence ancestry."""

import sqlite3

import content_generation as generation


def _record_kwargs(parent=None):
    return {
        "content_type": "ad_copy",
        "input_data": {"brand": "test"},
        "research_context": "local test evidence",
        "prompt": "test prompt",
        "output_text": "test output",
        "output_json": {"body": "test"},
        "model": "local-test",
        "provider": "local_rule",
        "level": "low",
        "confidence": 0.5,
        "latency_ms": 1,
        "status": "success",
        "parent_evidence_id": parent,
    }


def test_blank_parent_is_stored_as_null(tmp_path, monkeypatch):
    db_path = tmp_path / "content.db"
    monkeypatch.setattr(generation, "DB_PATH", str(db_path))

    generation.init_db()
    evidence_id = generation.record_evidence(**_record_kwargs(parent="  "))

    with sqlite3.connect(db_path) as conn:
        parent = conn.execute(
            "SELECT parent_evidence_id FROM content_generation_evidence WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()[0]

    assert parent is None

def test_init_db_repairs_historical_blank_parent(tmp_path, monkeypatch):
    db_path = tmp_path / "content.db"
    monkeypatch.setattr(generation, "DB_PATH", str(db_path))

    generation.init_db()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO content_generation_evidence
               (evidence_id, content_type, input_json, prompt, parent_evidence_id, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("CGE-HISTORICAL-BLANK", "ad_copy", "{}", "legacy", ""),
        )
        conn.commit()

    generation.init_db()

    with sqlite3.connect(db_path) as conn:
        parent = conn.execute(
            "SELECT parent_evidence_id FROM content_generation_evidence WHERE evidence_id=?",
            ("CGE-HISTORICAL-BLANK",),
        ).fetchone()[0]

    assert parent is None
