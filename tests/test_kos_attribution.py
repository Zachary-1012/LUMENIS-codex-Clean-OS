# -*- coding: utf-8 -*-
"""Scoped KOS attribution behavior with an isolated temporary database."""
import sqlite3

import pytest

import kos_attribution as ka


SCOPE = {
    "domain_id": "zbmp",
    "subject_id": None,
    "brand_focus_id": "BRAND-1",
    "global_scope": False,
}


@pytest.fixture
def scoped_notes_db(tmp_path, monkeypatch):
    path = tmp_path / "kos-attribution-isolated.sqlite"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE notes (
        note_id TEXT PRIMARY KEY, author_id TEXT, author_nickname TEXT,
        likes INTEGER, comments INTEGER, collects INTEGER, shares INTEGER,
        publish_datetime TEXT, source_platform TEXT, product_id TEXT,
        domain_id TEXT, scope_status TEXT, brand_focus_id TEXT, subject_id TEXT,
        scope_evidence_ref TEXT
    )""")
    conn.executemany(
        "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("n1", "kos_a", "KOS A", 100, 20, 30, 5, "2026-08-01", "xiaohongshu",
             "ZBMP", "zbmp", "VERIFIED", "BRAND-1", None, "ev-1"),
            ("n2", "kos_b", "KOS B", 20, 4, 8, 1, "2026-08-02", "xiaohongshu",
             "ZBMP", "zbmp", "VERIFIED", "BRAND-1", None, "ev-2"),
            ("n3", "kos_other", "Other", 900, 90, 90, 90, "2026-08-03", "xiaohongshu",
             "ZBMP", "zbmp", "VERIFIED", "BRAND-2", None, "ev-3"),
        ],
    )
    conn.commit()
    conn.close()

    def connect():
        result = sqlite3.connect(str(path))
        result.row_factory = sqlite3.Row
        return result

    monkeypatch.setattr(ka, "_conn", connect)
    monkeypatch.setattr(ka, "load_attribution_config", lambda: {
        "attribution_weights": {"time_weight_coeff": 0.5, "time_weight_range": 1.0},
        "platform_weights": {"xiaohongshu": {
            "likes": 1.0, "comments": 1.0, "collects": 1.0, "shares": 1.0,
        }},
        "config_status": "isolated-test-config",
    })

    import reprocess

    def canonical_ids(scope, *, source_ids=None, limit=5000, connection=None, **_kwargs):
        assert scope["brand_focus_id"] == "BRAND-1"
        if source_ids is None:
            return ["n1", "n2"][:limit]
        return list(dict.fromkeys(source_ids))[:limit]

    monkeypatch.setattr(reprocess, "_canonical_source_ids", canonical_ids)
    return path


def test_author_attribution_waits_for_scoped_event_evidence():
    result = ka.calculate_attribution("kos_a", "Test Brand", scope=SCOPE)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["code"] == "EVENT_SCOPE_EVIDENCE_REQUIRED"


def test_attribution_requires_explicit_brand_scope():
    result = ka.calculate_multi_touch_attribution(["n1"], "Test Brand")
    assert result["ok"] is False
    assert result["code"] == "SCOPE_REQUIRED"


def test_multi_touch_uses_only_canonical_notes_in_selected_brand(scoped_notes_db):
    result = ka.calculate_multi_touch_attribution(["n1", "n2"], "Test Brand", scope=SCOPE)
    assert result["ok"] is True
    assert result["brand_focus_id"] == "BRAND-1"
    assert result["total_notes"] == 2
    assert result["total_kos"] == 2
    assert sum(row["attribution_pct"] for row in result["attribution"]) == pytest.approx(100.0)


def test_multi_touch_rejects_note_outside_selected_brand(scoped_notes_db):
    result = ka.calculate_multi_touch_attribution(["n1", "n3"], "Test Brand", scope=SCOPE)
    assert result["ok"] is False
    assert result["status"] == "denied"
    assert result["code"] == "CANONICAL_NOTE_SCOPE_CHANGED"
