"""Scoped prelaunch import integration against the disposable v18 database."""
from __future__ import annotations

import json
import sqlite3
import os
import time

import pytest


@pytest.mark.parametrize("domain,platform", [
    ("CTH", "public_http"), ("BMP", "public_http"),
])
def test_public_prelaunch_import_binds_exact_scope_and_repeats_idempotently(
    tmp_path, monkeypatch, domain, platform,
):
    import database
    import subject_registry
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from lumenis.system import security
    from lumenis.system.collector.adapters import secondary_collection as surface
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.security import OperationType, PermissionGate, PermissionLevel
    from lumenis.system.security import permission as permission_module

    db_path = tmp_path / f"{domain.lower()}-{platform}.sqlite3"
    seed_path = os.environ["LUMENIS_TEST_SEED_DB"]
    with sqlite3.connect(f"file:{seed_path}?mode=ro", uri=True) as source_db:
        with sqlite3.connect(db_path) as target_db:
            source_db.backup(target_db)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"p0-test": "isolated-test-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "p0-test")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        evidence_columns = {row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")}
        note_columns = {row[1] for row in conn.execute("PRAGMA table_info(notes)")}
        baseline_evidence_count = conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records"
        ).fetchone()[0]
    assert {"domain_id", "product_id", "integrity_digest"} <= evidence_columns
    assert {"scope_status", "scope_evidence_ref"} <= note_columns

    entity, _ = subject_registry.add_subject({
        "domain_id": domain, "subject_type": "brand" if domain == "BMP" else "company",
        "name_en": f"{domain} exact scope test", "name_zh": "隔离验收", "industry": "retail",
    })
    scope = {
        "domain_id": "bmp" if domain == "BMP" else "cth",
        "subject_id": None if domain == "BMP" else entity["subject_id"],
        "brand_focus_id": entity["brand_focus_id"] if domain == "BMP" else None,
        "global_scope": False,
    }
    source = (
        "https://public.example.test/feed.xml"
        if platform == "web_atom" else "https://public.example.test/article"
    )
    html = b"<html><head><title>Public item</title></head><body>Observed public source.</body></html>"
    atom = b'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Brand feed</title>
      <entry><id>tag:example.test,2026:item-1</id><title>Public item</title>
      <link href="https://public.example.test/items/1"/><updated>2026-09-27T00:00:00Z</updated>
      <content>Observed public source.</content></entry></feed>'''
    payload = {"content": atom if platform == "web_atom" else html}
    content_type = "application/atom+xml" if platform == "web_atom" else "text/html"
    fetches = []
    response = lambda url: fetches.append(url) or PublicResponse(
        url=url, content=payload["content"], content_type=content_type, status_code=200,
    )
    if platform == "web_atom":
        from lumenis.system.collector.adapters.web_atom import AtomAdapter
        adapter = AtomAdapter(fetcher=response)
    else:
        from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
        adapter = PublicHttpAdapter(fetcher=response)
    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: adapter)
    monkeypatch.setitem(surface._last_action, platform, 0.0)
    def obsolete_daily_quota(*_args):
        raise AssertionError("default collection must not read an obsolete daily quota")
    monkeypatch.setattr(surface, "_daily_action_count", obsolete_daily_quota)
    gate = PermissionGate()
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)

    denied = surface.collect_search(
        platform, source, max_results=1, scope=scope, actor=None,
        prelaunch_local_import=True,
    )
    assert denied["status"] == "SCOPE_UNAUTHORIZED"
    assert fetches == []

    gate.grant_permission(PermissionLevel.COMMIT)
    resource = surface._prelaunch_public_import_resource(scope, source)
    gate.grant_approval(
        OperationType.DATA_IMPORT.value, resource=resource, granted_by="explicit_integration_test",
    )
    first = surface.collect_search(
        platform, source, max_results=1, scope=scope, actor=None,
        prelaunch_local_import=True,
    )
    # Exercise a second allowed manual cycle without sleeping or weakening
    # the production rate policy.
    monkeypatch.setitem(
        surface._last_action, platform,
        time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1,
    )
    second = surface.collect_search(
        platform, source, max_results=1, scope=scope, actor=None,
        prelaunch_local_import=True,
    )
    assert first["ok"] is True, first
    assert second["ok"] is True, second
    assert first["canonical_synced"] == second["canonical_synced"] == 1
    assert first["evidence_recorded"] and second["evidence_recorded"]
    assert len(fetches) == 2

    if platform == "public_http":
        with sqlite3.connect(db_path) as conn:
            note_before = conn.execute(
                "SELECT note_id, scope_evidence_ref, publish_datetime "
                "FROM notes WHERE url=?", (source,),
            ).fetchone()
            assert note_before is not None
            conn.execute(
                "UPDATE canonical_data SET sentiment='negative', risk_level='high' "
                "WHERE source_id=?", (note_before[0],),
            )
            conn.commit()

        payload["content"] = (
            b"<html><head><title>Changed title</title></head>"
            b"<body><article>Changed source body.</article></body></html>"
        )
        monkeypatch.setitem(
            surface._last_action, platform,
            time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1,
        )
        changed = surface.collect_search(
            platform, source, max_results=1, scope=scope, actor=None,
            prelaunch_local_import=True,
        )
        monkeypatch.setitem(
            surface._last_action, platform,
            time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1,
        )
        unchanged = surface.collect_search(
            platform, source, max_results=1, scope=scope, actor=None,
            prelaunch_local_import=True,
        )
        assert changed["ok"] is True, changed
        assert changed["refresh_verified"] is True, changed
        assert unchanged["ok"] is True, unchanged
        assert unchanged["refresh_verified"] is True, unchanged
        assert changed["product_owner"] == unchanged["product_owner"] == domain
        assert len(fetches) == 4

    with sqlite3.connect(db_path) as conn:
        note = conn.execute(
            "SELECT note_id, product_id, domain_id, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM notes WHERE url=?", (source,)
        ).fetchone()
        assert note is not None
        canonical = conn.execute(
            "SELECT external_id, product_id, domain_id, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM canonical_data WHERE external_id=?",
            (note[0],),
        ).fetchone()
        evidence = conn.execute(
            "SELECT id, product_id, domain_id, inputs_json FROM app_evidence_records WHERE id=?",
            (int(note[6]),),
        ).fetchone()
        evidence_count = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]
        if platform == "public_http":
            refreshed_note = conn.execute(
                "SELECT title, content, captured_at, publish_datetime, scope_evidence_ref "
                "FROM notes WHERE note_id=?", (note[0],),
            ).fetchone()
            refreshed_canonical = conn.execute(
                "SELECT title, content, captured_at, publish_datetime, scope_evidence_ref, "
                "sentiment, risk_level FROM canonical_data WHERE source_id=?", (note[0],),
            ).fetchone()
            native = conn.execute(
                "SELECT raw_data FROM platform_contents "
                "WHERE platform=? AND platform_content_id=?", (platform, note[0]),
            ).fetchone()
    expected_domain = "zbmp" if domain == "BMP" else "cth"
    expected_product = "ZBMP" if domain == "BMP" else "CTH"
    expected_identity = entity["brand_focus_id"] if domain == "BMP" else entity["subject_id"]
    assert note[1:6] == (expected_product, expected_domain,
                         None if domain == "BMP" else expected_identity,
                         expected_identity if domain == "BMP" else None, "VERIFIED")
    assert canonical[:3] == note[:3]
    assert (canonical[3] or None) == (note[3] or None)
    assert (canonical[4] or None) == (note[4] or None)
    assert canonical[5:] == note[5:]
    assert evidence[1:3] == (expected_product, expected_domain)
    inputs = json.loads(evidence[3])
    assert inputs["source_ids"] == [note[0]]
    assert inputs["_lumenis_scope"]["domain_id"] == expected_domain
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence[0],)
        ).fetchone()
        columns = [c[1] for c in conn.execute("PRAGMA table_info(app_evidence_records)")]
    assert classify_evidence_integrity(dict(zip(columns, row)))["assurance"] == "writer-authenticated"
    assert int(note[6]) == evidence[0]
    assert evidence_count == baseline_evidence_count + (2 if platform == "public_http" else 1)
    if platform == "public_http":
        assert changed["evidence_recorded"] is True
        assert unchanged["evidence_recorded"] is True
        assert refreshed_note[0:2] == ("Changed title", "Changed source body.")
        assert refreshed_note[2]
        assert refreshed_note[3] in (None, "")
        assert refreshed_note[4] == note_before[1]
        assert refreshed_canonical[0:2] == refreshed_note[0:2]
        assert refreshed_canonical[2]
        assert refreshed_canonical[3] in (None, "")
        assert refreshed_canonical[4] == note_before[1]
        assert refreshed_canonical[5:] == ("negative", "high")
        native_observation = json.loads(native[0])
        assert native_observation["content"] == "Changed source body."
        assert native_observation["_lumenis_evidence_id"] != int(note_before[1])
        observation_id = native_observation["_lumenis_evidence_id"]
        with sqlite3.connect(db_path) as conn:
            observation = conn.execute(
                "SELECT * FROM app_evidence_records WHERE id=?", (observation_id,),
            ).fetchone()
            observation_columns = [
                column[1] for column in conn.execute("PRAGMA table_info(app_evidence_records)")
            ]
        assert classify_evidence_integrity(
            dict(zip(observation_columns, observation))
        )["assurance"] == "writer-authenticated"

    other, _ = subject_registry.add_subject({
        "domain_id": domain, "subject_type": "brand" if domain == "BMP" else "company",
        "name_en": f"{domain} conflicting scope test", "name_zh": "隔离冲突验收",
        "industry": "retail",
    })
    conflicting_scope = {
        "domain_id": scope["domain_id"],
        "subject_id": other["subject_id"] if domain == "CTH" else None,
        "brand_focus_id": other["brand_focus_id"] if domain == "BMP" else None,
        "global_scope": False,
    }
    conflicting_resource = surface._prelaunch_public_import_resource(conflicting_scope, source)
    gate.grant_approval(
        OperationType.DATA_IMPORT.value, resource=conflicting_resource,
        granted_by="explicit_integration_test",
    )
    monkeypatch.setitem(
        surface._last_action, platform,
        time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1,
    )
    conflict = surface.collect_search(
        platform, source, max_results=1, scope=conflicting_scope, actor=None,
        prelaunch_local_import=True,
    )
    assert conflict["ok"] is False
    assert conflict["status"] == "SCOPE_CONFLICT"
    with sqlite3.connect(db_path) as conn:
        after = conn.execute(
            "SELECT product_id, domain_id, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM notes WHERE note_id=?", (note[0],)
        ).fetchone()
    assert after == note[1:7]
