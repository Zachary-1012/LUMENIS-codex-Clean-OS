"""Fixture-only X import through the exact human-approved prelaunch path."""
from __future__ import annotations

import json
import os
import sqlite3
import time

import pytest


@pytest.mark.parametrize("domain", ["CTH", "BMP"])
def test_x_manual_import_requires_exact_approval_and_keeps_tweet_identity(
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

    db_path = tmp_path / f"{domain.lower()}-x.sqlite3"
    seed_path = os.environ["LUMENIS_TEST_SEED_DB"]
    with sqlite3.connect(f"file:{seed_path}?mode=ro", uri=True) as source_db:
        with sqlite3.connect(db_path) as target_db:
            source_db.backup(target_db)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"x-fixture": "isolated-test-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "x-fixture")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    from lumenis.shared.database import migrations
    from lumenis.shared.evidence import store as evidence_store
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(tmp_path / "backups"))
    database.init_db()
    assert migrations.migrate(target_version=19) is True
    evidence_store.init_evidence_store(str(db_path))
    with sqlite3.connect(db_path) as conn:
        evidence_columns = {column[1] for column in conn.execute(
            "PRAGMA table_info(app_evidence_records)"
        )}
        assert {"domain_id", "product_id", "integrity_digest"} <= evidence_columns

    entity, _ = subject_registry.add_subject({
        "domain_id": domain, "subject_type": "brand" if domain == "BMP" else "company",
        "name_en": f"X Fixture Entity {domain}", "name_zh": "X隔离主体", "industry": "retail",
    })
    scope = {
        "domain_id": "bmp" if domain == "BMP" else "cth",
        "subject_id": None if domain == "BMP" else entity["subject_id"],
        "brand_focus_id": entity["brand_focus_id"] if domain == "BMP" else None,
        "global_scope": False,
    }
    keyword = "exact approved X query"
    good_id = "1970091400000000001"
    review_id = "1970091400000000002"
    good_raw = {
        "tweet_id": good_id, "screen_name": "fixture_handle",
        "created_at": "2026-09-27T12:00:00Z", "favorite_count": 11,
        "reply_count": 2, "retweet_count": 3, "quote_count": 1,
    }
    items = [
        {
            "platform_content_id": good_id,
            "title": f"X Fixture Entity {domain} update",
            "content": "A public fixture post naming the registered entity.",
            "url": f"https://x.com/fixture_handle/status/{good_id}",
            "author_id": "123456789", "author_nickname": "Fixture handle",
            "publish_datetime": good_raw["created_at"], "likes": 11,
            "comments": 2, "shares": 3, "raw": good_raw,
        },
        {
            "platform_content_id": review_id,
            "title": "Unrelated public post",
            "content": "No registered entity name appears in this source text.",
            "url": f"https://x.com/other_handle/status/{review_id}",
            "author_id": "987654321", "author_nickname": "Other handle",
            "publish_datetime": "2026-09-27T12:01:00Z", "likes": 4,
            "comments": 0, "shares": 1,
            "raw": {"tweet_id": review_id, "screen_name": "other_handle"},
        },
    ]
    calls = []

    class FixtureAdapter:
        def search(self, query, *, max_results):
            calls.append((query, max_results))
            return CollectionResult(
                status=CollectionStatus.SUCCESS, platform="x", items=items,
                raw_count=len(items), metadata={"provider": "fixture_only", "source": "fixture"},
            )

    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: FixtureAdapter())
    monkeypatch.setattr(surface, "_adapter_health", lambda *_args, **_kwargs: {
        "status": "READY", "ready": True, "can_attempt": True,
    })
    monkeypatch.setitem(surface._last_action, "x", 0.0)
    gate = PermissionGate()
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)

    # X is not exposed through the ordinary or maintenance route, and a denied
    # exact manual request cannot reach the adapter.
    ordinary = surface.collect_search("x", keyword, max_results=2)
    assert ordinary["status"] == "AUTH_REQUIRED"
    denied = surface.collect_search(
        "x", keyword, max_results=2, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    assert denied["status"] == "SCOPE_UNAUTHORIZED"
    maintenance = surface.collect_search(
        "x", keyword, max_results=2, scope=scope, actor=None,
        operator="prelaunch_maintenance", prelaunch_local_import=True,
    )
    assert maintenance["status"] == "SCOPE_UNAUTHORIZED"
    with pytest.raises(PermissionError):
        surface.collect_search(
            "x", keyword, max_results=2, scope=scope, actor=None,
            operator="auto", prelaunch_local_import=True,
        )
    assert calls == []

    gate.grant_permission(PermissionLevel.COMMIT)
    resource = surface._prelaunch_manual_import_resource(scope, keyword, platform="x")
    gate.grant_approval(
        OperationType.DATA_IMPORT.value, resource=resource, granted_by="explicit_fixture_approval",
    )
    mismatched_query = surface.collect_search(
        "x", keyword + " changed", max_results=2, scope=scope, actor=None,
        operator="human", prelaunch_local_import=True,
    )
    assert mismatched_query["status"] == "SCOPE_UNAUTHORIZED"
    assert calls == []

    def collect():
        monkeypatch.setitem(surface._last_action, "x", time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1)
        return surface.collect_search(
            "x", keyword, max_results=2, scope=scope, actor=None,
            operator="human", prelaunch_local_import=True,
        )

    first = collect()
    second = collect()
    assert first["status"] == second["status"] == "PARTIAL_SCOPE_REVIEW_REQUIRED"
    assert first["ok"] is second["ok"] is False
    assert first["canonical_synced"] == second["canonical_synced"] == 1
    assert first["review_pending_count"] == second["review_pending_count"] == 1
    assert first["evidence_recorded"] and second["evidence_recorded"]
    assert first["publish_authority"] == "human_manual_only"
    assert len(calls) == 2

    entity_id = entity["brand_focus_id"] if domain == "BMP" else entity["subject_id"]
    product, domain_id = ("ZBMP", "zbmp") if domain == "BMP" else ("CTH", "cth")
    with sqlite3.connect(db_path) as conn:
        notes = conn.execute(
            "SELECT note_id,product_id,domain_id,subject_id,brand_focus_id,scope_status,"
            "scope_evidence_ref,publish_datetime,captured_at FROM notes WHERE source_platform='x'"
        ).fetchall()
        canonical = conn.execute(
            "SELECT external_id,product_id,domain_id,subject_id,brand_focus_id,scope_status "
            "FROM canonical_data WHERE source_platform='x'"
        ).fetchall()
        native = conn.execute(
            "SELECT platform_content_id,author_id,view_count,raw_data FROM platform_contents "
            "WHERE platform='x' ORDER BY platform_content_id"
        ).fetchall()
        evidence = conn.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id='PRELAUNCH_X_COLLECT' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        evidence_columns = [column[1] for column in conn.execute("PRAGMA table_info(app_evidence_records)")]
        source_counts = (
            conn.execute("SELECT COUNT(*) FROM notes WHERE source_platform='x'").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM canonical_data WHERE source_platform='x'").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM platform_contents WHERE platform='x'").fetchone()[0],
        )
    assert len(notes) == len(canonical) == len(native) == 1
    assert notes[0][0] == canonical[0][0] == native[0][0] == good_id
    assert notes[0][1:6] == (product, domain_id,
                              None if domain == "BMP" else entity_id,
                              entity_id if domain == "BMP" else None, "VERIFIED")
    assert tuple(value or None for value in canonical[0][1:]) == tuple(
        value or None for value in notes[0][1:6]
    )
    assert notes[0][6] and notes[0][7] != notes[0][8]
    assert source_counts == (1, 1, 1)
    native_raw = json.loads(native[0][3])
    assert native_raw["tweet_id"] == good_id
    assert native_raw["quote_count"] == 1
    assert native_raw["favorite_count"] == 11
    assert native_raw["reply_count"] == 2
    assert native_raw["retweet_count"] == 3
    assert native_raw["_lumenis_evidence_id"]
    evidence_data = dict(zip(evidence_columns, evidence))
    assert classify_evidence_integrity(evidence_data)["assurance"] == "writer-authenticated"
    evidence_inputs = json.loads(evidence_data["inputs_json"])
    assert evidence_inputs["source_ids"] == [good_id]
    candidates = evidence_inputs["unassigned_review_candidates"]
    assert [candidate["content_id"] for candidate in candidates] == [review_id]
    assert candidates[0]["title"] == "Unrelated public post"
    assert candidates[0]["content_id"] == review_id
