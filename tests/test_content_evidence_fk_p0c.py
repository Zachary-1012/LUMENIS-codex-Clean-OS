"""P0-C content evidence parent semantics under enforced foreign keys."""
import sqlite3

import content_generation as content


def _record(parent=None):
    return content.record_evidence(
        content_type="ad_copy",
        input_data={"brand": "LUMENIS"},
        research_context="",
        prompt="test",
        output_text="{}",
        output_json={},
        model="rule",
        provider="rule",
        level="deterministic",
        confidence=1.0,
        latency_ms=0,
        status="success",
        parent_evidence_id=parent,
    )


def test_root_and_child_parent_ids_are_fk_clean(tmp_path):
    content.DB_PATH = str(tmp_path / "content.db")
    content.init_db()

    root_id = _record()
    empty_id = _record("")
    whitespace_id = _record("   ")
    child_id = _record(root_id)

    connection = sqlite3.connect(content.DB_PATH)
    try:
        parents = dict(connection.execute(
            "SELECT evidence_id,parent_evidence_id FROM content_generation_evidence"
        ).fetchall())
        assert parents[root_id] is None
        assert parents[empty_id] is None
        assert parents[whitespace_id] is None
        assert parents[child_id] == root_id
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()


def test_missing_parent_is_rejected(tmp_path):
    content.DB_PATH = str(tmp_path / "content-invalid.db")
    content.init_db()
    try:
        _record("CGE-does-not-exist")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("missing parent evidence must be rejected with FK enabled")
