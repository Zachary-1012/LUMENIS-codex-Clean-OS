"""Exact, human-approved Douyin import through the existing prelaunch owners."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone

import pytest


@pytest.mark.parametrize("domain", ["CTH", "BMP"])
def test_douyin_manual_import_requires_exact_approval_and_binds_native_evidence(
    tmp_path, monkeypatch, domain,
):
    import database
    import subject_registry
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from lumenis.system import security
    from lumenis.system.collector.adapters import secondary_collection as surface
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    from lumenis.system.security import OperationType, PermissionGate, PermissionLevel
    from lumenis.system.security import permission as permission_module

    db_path = tmp_path / f"{domain.lower()}-douyin.sqlite3"
    seed_path = os.environ["LUMENIS_TEST_SEED_DB"]
    with sqlite3.connect(f"file:{seed_path}?mode=ro", uri=True) as source_db:
        with sqlite3.connect(db_path) as target_db:
            source_db.backup(target_db)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"p0-test": "isolated-test-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "p0-test")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        baseline_evidence = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]

    entity, _ = subject_registry.add_subject({
        "domain_id": domain, "subject_type": "brand" if domain == "BMP" else "company",
        "name_en": f"{domain} Douyin scope fixture", "name_zh": "隔离验收", "industry": "retail",
    })
    scope = {
        "domain_id": "bmp" if domain == "BMP" else "cth",
        "subject_id": None if domain == "BMP" else entity["subject_id"],
        "brand_focus_id": entity["brand_focus_id"] if domain == "BMP" else None,
        "global_scope": False,
    }
    keyword = "approved exact Douyin query"
    raw = {
        "aweme_id": "7342000000000000001", "aweme_type": 0,
        "author_id": "fixture-author-id", "sec_uid": "fixture-sec-uid",
        "nickname": "Fixture Creator", "create_time": 1757000000,
        "digg_count": 19, "comment_count": 3, "share_count": 2,
        "collect_count": None,
    }
    item = {
        "platform_content_id": raw["aweme_id"], "title": "Fixture post",
        "content": "Fixture content", "url": "https://www.douyin.com/video/7342000000000000001",
        "author_id": raw["author_id"], "author_nickname": raw["nickname"],
        "publish_datetime": "2025-09-04T00:00:00Z", "likes": 19,
        "comments": 3, "shares": 2, "collects": None, "raw": raw,
    }
    calls = []
    class FixtureAdapter:
        def search(self, query, *, max_results):
            calls.append((query, max_results))
            return CollectionResult(
                status=CollectionStatus.SUCCESS, platform="douyin", items=[item],
                raw_count=1, metadata={"provider": "fixture_only", "source": "fixture"},
            )
    adapter = FixtureAdapter()
    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: adapter)
    monkeypatch.setattr(surface, "_adapter_health", lambda *_args, **_kwargs: {
        "status": "READY", "ready": True, "can_attempt": True,
    })
    monkeypatch.setitem(surface._last_action, "douyin", 0.0)
    gate = PermissionGate()
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)

    denied = surface.collect_search(
        "douyin", keyword, max_results=1, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    assert denied["status"] == "SCOPE_UNAUTHORIZED"
    assert calls == []

    gate.grant_permission(PermissionLevel.COMMIT)
    resource = surface._prelaunch_douyin_manual_import_resource(scope, keyword, platform="douyin")
    gate.grant_approval(
        OperationType.DATA_IMPORT.value, resource=resource, granted_by="explicit_fixture_approval",
    )
    first = surface.collect_search(
        "douyin", keyword, max_results=1, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    monkeypatch.setitem(surface._last_action, "douyin", time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1)
    second = surface.collect_search(
        "douyin", keyword, max_results=1, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    assert first["ok"] is True, first
    assert second["ok"] is True, second
    assert first["canonical_synced"] == second["canonical_synced"] == 1
    assert first["native_fields_synced"] == second["native_fields_synced"] == 1
    assert first["evidence_recorded"] and second["evidence_recorded"]

    with sqlite3.connect(db_path) as conn:
        initial_scope_evidence_ref = conn.execute(
            "SELECT scope_evidence_ref FROM notes WHERE note_id=?", (raw["aweme_id"],),
        ).fetchone()[0]
        conn.execute(
            "UPDATE canonical_data SET sentiment='negative', risk_level='high' WHERE external_id=?",
            (raw["aweme_id"],),
        )
        conn.commit()
    item.update({"title": "Changed fixture post", "content": "Changed source content", "likes": 27})
    raw["desc"] = "Changed source content"
    raw["digg_count"] = 27
    monkeypatch.setitem(surface._last_action, "douyin", time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1)
    changed = surface.collect_search(
        "douyin", keyword, max_results=1, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    monkeypatch.setitem(surface._last_action, "douyin", time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1)
    unchanged = surface.collect_search(
        "douyin", keyword, max_results=1, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    assert changed["ok"] is True, changed
    assert unchanged["ok"] is True, unchanged
    assert changed["refresh_verified"] is unchanged["refresh_verified"] is True
    assert changed["canonical_synced"] == unchanged["canonical_synced"] == 1
    assert changed["native_fields_synced"] == unchanged["native_fields_synced"] == 1
    assert changed["evidence_recorded"] and unchanged["evidence_recorded"]
    assert len(calls) == 4

    product, domain_id = ("ZBMP", "zbmp") if domain == "BMP" else ("CTH", "cth")
    entity_id = entity["brand_focus_id"] if domain == "BMP" else entity["subject_id"]
    with sqlite3.connect(db_path) as conn:
        note = conn.execute(
            "SELECT product_id,domain_id,subject_id,brand_focus_id,scope_status,scope_evidence_ref,publish_datetime,captured_at,title,content "
            "FROM notes WHERE note_id=?", (raw["aweme_id"],),
        ).fetchone()
        canonical = conn.execute(
            "SELECT product_id,domain_id,subject_id,brand_focus_id,scope_status,scope_evidence_ref,title,content,sentiment,risk_level "
            "FROM canonical_data WHERE external_id=?", (raw["aweme_id"],),
        ).fetchone()
        native = conn.execute(
            "SELECT raw_data FROM platform_contents WHERE platform='douyin' AND platform_content_id=?",
            (raw["aweme_id"],),
        ).fetchone()
        evidence_rows = conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='PRELAUNCH_DOUYIN_COLLECT'"
        ).fetchone()[0]
        evidence = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (note[5],),
        ).fetchone()
        evidence_columns = [column[1] for column in conn.execute(
            "PRAGMA table_info(app_evidence_records)")]
    assert note[:5] == (product, domain_id,
                         None if domain == "BMP" else entity_id,
                         entity_id if domain == "BMP" else None, "VERIFIED")
    assert tuple(value or None for value in canonical[:6]) == tuple(value or None for value in note[:6])
    expected_published_at = datetime.fromtimestamp(
        raw["create_time"], tz=timezone.utc,
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    assert note[6] == expected_published_at
    assert note[7] and note[6] != note[7]
    assert note[5] == initial_scope_evidence_ref
    assert note[8:10] == ("Changed fixture post", "Changed source content")
    assert canonical[6:8] == ("Changed fixture post", "Changed source content")
    assert canonical[8:10] == ("negative", "high")
    assert evidence_rows == 2
    assert classify_evidence_integrity(dict(zip(evidence_columns, evidence))) ["assurance"] == "writer-authenticated"
    native_data = json.loads(native[0])
    assert native_data["aweme_id"] == raw["aweme_id"]
    assert type(native_data["create_time"]) is int
    assert native_data["create_time"] == raw["create_time"]
    assert native_data["sec_uid"] == raw["sec_uid"]
    assert native_data["digg_count"] == 27
    assert native_data["comment_count"] == 3
    assert native_data["share_count"] == 2
    assert native_data["collect_count"] is None
    latest_evidence_id = native_data["_lumenis_evidence_id"]
    assert latest_evidence_id != note[5]
    with sqlite3.connect(db_path) as conn:
        latest_evidence = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (latest_evidence_id,),
        ).fetchone()
        assert conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='PRELAUNCH_DOUYIN_COLLECT'"
        ).fetchone()[0] == 2
    assert classify_evidence_integrity(
        dict(zip(evidence_columns, latest_evidence))
    )["assurance"] == "writer-authenticated"
    assert first["publish_authority"] == "human_manual_only"
    assert first["product_owner"] == domain
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0] == baseline_evidence + 2

    with pytest.raises(PermissionError):
        surface.collect_search(
            "douyin", keyword, max_results=1, scope=scope, actor=None,
            operator="auto", prelaunch_local_import=True,
        )
    monkeypatch.setitem(surface._last_action, "douyin", time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1)
    rejected = surface.collect_search(
        "douyin", keyword, max_results=1, scope=scope, actor=None,
        operator="prelaunch_maintenance", prelaunch_local_import=True,
    )
    assert rejected["status"] == "SCOPE_UNAUTHORIZED"
    assert len(calls) == 4


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), 10**100])
def test_invalid_douyin_unix_timestamp_fails_explicitly(value):
    from lumenis.system.collector.adapters.multi_platform_import import (
        _normalize_douyin_publish_datetime,
    )

    with pytest.raises(ValueError, match="Douyin create_time"):
        _normalize_douyin_publish_datetime(value)


def test_douyin_iso_publish_time_is_preserved():
    from lumenis.system.collector.adapters.multi_platform_import import (
        _normalize_douyin_publish_datetime,
    )

    assert _normalize_douyin_publish_datetime("2025-09-04T22:13:20Z") == "2025-09-04T22:13:20Z"


def test_douyin_missing_publish_time_stays_empty_without_capture_fallback():
    from lumenis.system.collector.adapters.multi_platform_import import _to_note_payload

    payload = _to_note_payload(
        {"platform": "douyin", "published_at": None},
        {"create_time": None, "captured_at": "2026-09-28T00:00:00Z"},
    )
    assert payload["publish_datetime"] == ""
    assert payload["captured_at"] == "2026-09-28T00:00:00Z"


def test_douyin_uid_survives_when_source_does_not_supply_sec_uid():
    from lumenis.system.collector.adapters.multi_platform_import import _to_note_payload
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    raw = {"platform": "douyin", "aweme_id": "7342000000000000001",
           "author_id": "62187533122", "create_time": 1757000000}
    payload = _to_note_payload(to_canonical_record(raw, "douyin"), raw)
    assert payload["author_id"] == "62187533122"
    assert "sec_uid" not in raw
    assert raw["create_time"] == 1757000000
