"""Primary Hong Kong XHS persistence → Evidence/Canonical regression tests.

These tests use synthetic notes, an OS temporary SQLite database, and a mocked
search result. They never read local cookies or contact Xiaohongshu/RedNote.
"""
import json
import sqlite3


def _init_temp_database(tmp_path, monkeypatch):
    import database

    db_path = tmp_path / "lumenis-lineage-test.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(db_path))
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    database.init_db()
    return db_path


def _stub_primary_sync(monkeypatch, bridge, note):
    monkeypatch.setattr(bridge, "collection_policy_gate", lambda **_kwargs: {"ok": True})
    monkeypatch.setattr(bridge, "select_account", lambda _account: (True, "test account"))
    monkeypatch.setattr(bridge, "cookie_configured", lambda: True)
    monkeypatch.setattr(bridge, "is_test_mode", lambda: True)
    monkeypatch.setattr(
        bridge,
        "_run_search",
        lambda keyword, _max_scroll: {
            "state": "SUCCESS",
            "total": 1,
            "notes": [dict(note)],
            "error": "",
        },
    )
    monkeypatch.setattr(bridge, "_write_collection_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bridge.ai_analyzer, "verify_taikoo_location", lambda *_args: (True, "rule verified"))
    monkeypatch.setattr(bridge, "_get_current_user_id", lambda: None)
    monkeypatch.setattr(bridge.network_adaptive, "report_collection_result", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bridge.network_adaptive, "get_network_status", lambda: {})
    monkeypatch.setattr(bridge.network_adaptive, "get_adaptive_settings", lambda: {})
    monkeypatch.setattr(bridge.cache_manager, "create_snapshot", lambda: {"success": True})
    monkeypatch.setattr(bridge.cache_manager, "get_cache_status", lambda: {})
    monkeypatch.setattr(bridge, "clear_circuit", lambda: None)

    class NoopThread:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(bridge.threading, "Thread", NoopThread)


def _sample_note():
    return {
        "note_id": "hk-test-note-001",
        "title": "香港测试笔记标题",
        "content": "仅供自动化测试使用的合成内容。",
        "url": "https://www.rednote.com/explore/hk-test-note-001",
        "author_nickname": "测试作者",
        "publish_datetime": "2026-09-14 09:10:00",
        "captured_at": "2026-09-15 10:11:12",
        "likes": 17,
        "comments": None,
        "collects": 3,
        "shares": None,
    }


def test_primary_hk_sync_writes_note_evidence_canonical_and_trace(tmp_path, monkeypatch):
    db_path = _init_temp_database(tmp_path, monkeypatch)
    import xhs_cookie_bridge as bridge

    _stub_primary_sync(monkeypatch, bridge, _sample_note())
    result = bridge.sync(
        keywords=["广州太古汇"],
        max_scroll=1,
        account=bridge.XHS_RETINAUT_NAME,
    )

    assert result["ok"] is True
    assert result["task_state"] == "SUCCESS"
    assert result["inserted"] == 1

    with sqlite3.connect(db_path) as conn:
        note = conn.execute(
            "SELECT note_id, captured_at, publish_datetime FROM notes WHERE note_id=?",
            ("hk-test-note-001",),
        ).fetchone()
        evidence = conn.execute(
            "SELECT evidence_id, source_url, source_id, provider, captured_at, publish_datetime, collection_metadata "
            "FROM zbc_evidence WHERE source_id=?",
            ("hk-test-note-001",),
        ).fetchone()
        canonical = conn.execute(
            "SELECT canonical_id, source_id, source_platform, captured_at, publish_datetime, engagement_comments "
            "FROM canonical_data WHERE source_id=?",
            ("hk-test-note-001",),
        ).fetchone()

        assert note == (
            "hk-test-note-001",
            "2026-09-15 10:11:12",
            "2026-09-14 09:10:00",
        )
        assert evidence is not None
        assert evidence[1:6] == (
            "https://www.rednote.com/explore/hk-test-note-001",
            "hk-test-note-001",
            "xhs_cookie_bridge",
            "2026-09-15 10:11:12",
            "2026-09-14 09:10:00",
        )
        metadata = json.loads(evidence[6])
        assert metadata["source_platform"] == "xhs"
        assert metadata["source_keyword"] == "广州太古汇"
        assert metadata["captured_at"] == "2026-09-15 10:11:12"
        assert canonical[1:] == (
            "hk-test-note-001",
            "xhs",
            "2026-09-15 10:11:12",
            "2026-09-14 09:10:00",
            None,
        )

        chain_canonical = conn.execute(
            "SELECT evidence_id, normalized_content, subject_hit, engagement_metrics "
            "FROM zbc_canonical_data WHERE evidence_id=?",
            (evidence[0],),
        ).fetchone()
        assert chain_canonical is not None
        assert chain_canonical[1] == "香港测试笔记标题 仅供自动化测试使用的合成内容。"
        assert chain_canonical[2] == 1
        assert json.loads(chain_canonical[3])["comments"] is None

        stages = {
            row[0]
            for row in conn.execute(
                "SELECT stage FROM zbc_lifecycle_tracking WHERE evidence_id=?",
                (evidence[0],),
            ).fetchall()
        }
        assert {"EVIDENCE", "CANONICAL_DATA"}.issubset(stages)


def test_primary_note_survives_evidence_sidewrite_failure(tmp_path, monkeypatch):
    db_path = _init_temp_database(tmp_path, monkeypatch)
    import lumenis.shared.evidence as evidence
    import xhs_cookie_bridge as bridge

    def fail_lineage(*_args, **_kwargs):
        raise sqlite3.OperationalError("injected temporary-store failure")

    # The bridge imports the canonical package API at call time. Patch that
    # public owner surface to inject the same non-fatal side-write failure.
    monkeypatch.setattr(evidence, "capture_note_lineage", fail_lineage)
    _stub_primary_sync(monkeypatch, bridge, _sample_note())
    result = bridge.sync(
        keywords=["广州太古汇"],
        max_scroll=1,
        account=bridge.XHS_RETINAUT_NAME,
    )

    assert result["ok"] is True
    assert result["inserted"] == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM notes WHERE note_id=?", ("hk-test-note-001",)
        ).fetchone()[0] == 1
