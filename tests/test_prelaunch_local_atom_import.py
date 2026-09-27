"""Fixture-only repeatable Atom import with exact scope and metric lineage."""

from __future__ import annotations

import json
import sqlite3
import time


def _feed(view_count: int | None, *, include_second: bool = False) -> bytes:
    statistics = (
        f'<media:statistics views="{view_count}" />'
        if view_count is not None else "<media:statistics />"
    )
    second_entry = '''<entry><id>tag:public.example.test,2026:item-2</id>
      <yt:videoId>fixture-video-02</yt:videoId><yt:channelId>fixture-channel-01</yt:channelId>
      <title>Second observed public item</title>
      <link href="https://public.example.test/items/fixture-video-02" />
      <published>2026-09-25T14:02:37+00:00</published>
      <media:group><media:thumbnail url="https://public.example.test/thumb-2.jpg" />
      <media:community><media:statistics views="10" /></media:community></media:group>
      </entry>''' if include_second else ""
    return f'''<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
      <title>Approved fixture feed</title>
      <entry><id>tag:public.example.test,2026:item-1</id>
      <yt:videoId>fixture-video-01</yt:videoId><yt:channelId>fixture-channel-01</yt:channelId>
      <title>Observed public item</title>
      <link href="https://public.example.test/items/fixture-video-01" />
      <published>2026-09-24T14:02:37+00:00</published>
      <media:group><media:thumbnail url="https://public.example.test/thumb.jpg" />
      <media:community>{statistics}</media:community></media:group>
      </entry>{second_entry}</feed>'''.encode()


def test_prelaunch_atom_repeats_without_duplicate_evidence_or_metrics(tmp_path, monkeypatch):
    import database
    import subject_registry
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from lumenis.shared.database.migrations import migrate
    from lumenis.system import security
    from lumenis.system.collector.adapters import secondary_collection as surface
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.adapters.web_atom import AtomAdapter
    from lumenis.system.security import OperationType, PermissionGate, PermissionLevel
    from lumenis.system.security import permission as permission_module

    db_path = tmp_path / "atom.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"isolated-test": "not-a-production-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "isolated-test")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    database.init_db()
    assert migrate() is True

    brand, _ = subject_registry.add_subject({
        "domain_id": "BMP", "subject_type": "brand", "name_en": "Fixture Brand",
        "name_zh": "隔离品牌", "industry": "retail",
    })
    scope = {
        "domain_id": "bmp", "subject_id": None,
        "brand_focus_id": brand["brand_focus_id"], "global_scope": False,
    }
    source_url = "https://public.example.test/feed.atom"
    counts = [1234]
    include_second = [False]
    fetches: list[str] = []
    adapter = AtomAdapter(fetcher=lambda url: (
        fetches.append(url) or PublicResponse(
            url=url, content=_feed(counts[0], include_second=include_second[0]),
            content_type="application/atom+xml", status_code=200,
        )
    ))
    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: adapter)
    monkeypatch.setitem(surface._last_action, "web_atom", 0.0)
    gate = PermissionGate()
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)

    denied = surface.collect_search(
        "web_atom", source_url, max_results=1, scope=scope, actor=None,
        prelaunch_local_import=True,
    )
    assert denied["status"] == "SCOPE_UNAUTHORIZED"
    assert fetches == []

    gate.grant_permission(PermissionLevel.COMMIT)
    resource = surface._prelaunch_public_import_resource(scope, source_url, platform="web_atom")
    gate.grant_approval(
        OperationType.DATA_IMPORT.value, resource=resource, granted_by="fixture_test",
    )

    def collect(view_count: int | None):
        counts[0] = view_count
        monkeypatch.setitem(
            surface._last_action, "web_atom",
            time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1,
        )
        return surface.collect_search(
            "web_atom", source_url, max_results=2, scope=scope, actor=None,
            prelaunch_local_import=True,
        )

    first = collect(1234)
    second = collect(1234)
    assert first["ok"] is True, first
    assert second["ok"] is True, second
    assert first["native_fields_synced"] == second["native_fields_synced"] == 1
    assert first["evidence_recorded"] and second["evidence_recorded"]

    with sqlite3.connect(db_path) as conn:
        note = conn.execute(
            "SELECT note_id, source_platform, product_id, domain_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM notes"
        ).fetchone()
        canonical = conn.execute(
            "SELECT source_id, source_platform, product_id, domain_id, brand_focus_id, "
            "scope_status, scope_evidence_ref, evidence_ref FROM canonical_data"
        ).fetchone()
        first_evidence_id = int(note[6])
        evidence_count_after_repeat = conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records"
        ).fetchone()[0]
        source_row_counts = (
            conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM platform_contents").fetchone()[0],
        )
        native = conn.execute(
            "SELECT platform, platform_content_id, content_type, author_id, view_count, raw_data "
            "FROM platform_contents"
        ).fetchone()
        metric_rows_after_repeat = conn.execute(
            "SELECT raw_json FROM metric_snapshots WHERE entity_type='platform_content' "
            "AND entity_key=?", (f"web_atom:{note[0]}",),
        ).fetchall()
    assert note[1:6] == ("web_atom", "ZBMP", "zbmp", brand["brand_focus_id"], "VERIFIED")
    assert canonical[:6] == (note[0], "web_atom", "ZBMP", "zbmp", brand["brand_focus_id"], "VERIFIED")
    assert canonical[6] == str(first_evidence_id)
    assert canonical[7] in (None, "")
    assert first_evidence_id == int(canonical[6])
    assert evidence_count_after_repeat == 1
    assert source_row_counts == (1, 1, 1)
    assert native[:5] == ("web_atom", note[0], "video", "fixture-channel-01", 1234)
    assert len(metric_rows_after_repeat) == 1

    changed = collect(1250)
    assert changed["ok"] is True, changed
    with sqlite3.connect(db_path) as conn:
        note_after_change = conn.execute(
            "SELECT note_id, scope_evidence_ref FROM notes"
        ).fetchone()
        canonical_after_change = conn.execute(
            "SELECT source_id, scope_evidence_ref FROM canonical_data"
        ).fetchone()
        evidence_columns = [column[1] for column in conn.execute(
            "PRAGMA table_info(app_evidence_records)"
        )]
        native_after_change = conn.execute(
            "SELECT platform_content_id, view_count, raw_data FROM platform_contents"
        ).fetchone()
        metric_rows = conn.execute(
            "SELECT raw_json FROM metric_snapshots WHERE entity_type='platform_content' "
            "AND entity_key=? ORDER BY id", (f"web_atom:{note[0]}",),
        ).fetchall()
    changed_evidence_id = int(note_after_change[1])
    assert note_after_change[0] == canonical_after_change[0] == note[0]
    assert changed_evidence_id == first_evidence_id
    raw_data = json.loads(native_after_change[2])
    observation_evidence_id = int(raw_data["_lumenis_evidence_id"])
    assert observation_evidence_id > first_evidence_id
    with sqlite3.connect(db_path) as conn:
        evidence_row = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (observation_evidence_id,)
        ).fetchone()
    changed_evidence = dict(zip(evidence_columns, evidence_row))
    assert classify_evidence_integrity(changed_evidence)["assurance"] == "writer-authenticated"
    inputs = json.loads(changed_evidence["inputs_json"])
    assert inputs["source_url"] == source_url
    assert inputs["source_ids"] == [note[0]]
    assert inputs["_lumenis_scope"]["brand_focus_id"] == brand["brand_focus_id"]
    assert native_after_change[0:2] == (note[0], 1250)
    assert raw_data["feed_url"] == source_url
    assert raw_data["video_id"] == "fixture-video-01"
    assert len(metric_rows) == 2
    metric_history = [json.loads(row[0]) for row in metric_rows]
    assert [row["view_count"] for row in metric_history] == [1234, 1250]
    assert [row["evidence_id"] for row in metric_history] == [first_evidence_id, observation_evidence_id]
    assert all(row["source_id"] == row["canonical_source_id"] == note[0] for row in metric_history)
    assert all(row["source_url"] == source_url for row in metric_history)
    assert all(row["product_id"] == "ZBMP" and row["domain_id"] == "zbmp" for row in metric_history)
    assert all(row["brand_focus_id"] == brand["brand_focus_id"] for row in metric_history)

    include_second[0] = True
    mixed = collect(1250)
    assert mixed["ok"] is True, mixed
    with sqlite3.connect(db_path) as conn:
        mixed_notes = conn.execute(
            "SELECT note_id, scope_evidence_ref FROM notes ORDER BY note_id"
        ).fetchall()
        mixed_canonical = conn.execute(
            "SELECT source_id, scope_evidence_ref FROM canonical_data ORDER BY source_id"
        ).fetchall()
        mixed_native = conn.execute(
            "SELECT platform_content_id, raw_data FROM platform_contents ORDER BY platform_content_id"
        ).fetchall()
        mixed_metrics = conn.execute(
            "SELECT entity_key, raw_json FROM metric_snapshots "
            "WHERE entity_type='platform_content' ORDER BY id"
        ).fetchall()
    assert len(mixed_notes) == len(mixed_canonical) == len(mixed_native) == 2
    first_mixed_note = next(row for row in mixed_notes if row[0] == note[0])
    second_mixed_note = next(row for row in mixed_notes if row[0] != note[0])
    assert first_mixed_note[1] == str(first_evidence_id)
    assert second_mixed_note[1] != first_mixed_note[1]
    assert [row[1] for row in mixed_canonical] == [row[1] for row in mixed_notes]
    second_native = next(row for row in mixed_native if row[0] == second_mixed_note[0])
    mixed_evidence_id = int(json.loads(second_native[1])["_lumenis_evidence_id"])
    assert int(second_mixed_note[1]) == mixed_evidence_id
    assert sum(row[0] == f"web_atom:{note[0]}" for row in mixed_metrics) == 2
    assert sum(row[0] == f"web_atom:{second_mixed_note[0]}" for row in mixed_metrics) == 1

    missing = collect(None)
    assert missing["ok"] is True, missing
    with sqlite3.connect(db_path) as conn:
        current_view_count = conn.execute(
            "SELECT view_count FROM platform_contents WHERE platform_content_id=?",
            (note[0],),
        ).fetchone()[0]
        metric_count = conn.execute(
            "SELECT COUNT(*) FROM metric_snapshots WHERE entity_type='platform_content' "
            "AND entity_key=?", (f"web_atom:{note[0]}",),
        ).fetchone()[0]
    assert current_view_count is None
    assert metric_count == 2
    assert fetches == [source_url] * 5

    for blocked_url in (
        "https://www.youtube.com/feeds/videos.xml?channel_id=blocked",
        "https://m.youtube.com/feeds/videos.xml?channel_id=blocked",
    ):
        try:
            surface._prelaunch_public_import_resource(scope, blocked_url, platform="web_atom")
        except ValueError:
            pass
        else:
            raise AssertionError("YouTube Atom feeds must remain blocked pending authorized route")
    blocked_fetches: list[str] = []
    blocked = AtomAdapter(fetcher=lambda url: (
        blocked_fetches.append(url) or PublicResponse(
            url=url, content=_feed(1234),
            content_type="application/atom+xml", status_code=200,
        )
    )).search("https://www.youtube.com/feeds/videos.xml?channel_id=blocked")
    assert blocked.status.value == "BLOCKED"
    assert blocked.metadata["blocked_reason"] == "source_policy"
    assert blocked_fetches == []
    with sqlite3.connect(db_path) as conn:
        before_blocked_attempt = (
            conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM web_runs").fetchone()[0],
        )
    blocked_attempt = surface.collect_search(
        "web_atom", "https://www.youtube.com/feeds/videos.xml?channel_id=blocked",
        max_results=1,
    )
    assert blocked_attempt["status"] == "BLOCKED"
    with sqlite3.connect(db_path) as conn:
        after_blocked_attempt = (
            conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM web_runs").fetchone()[0],
        )
    assert after_blocked_attempt == before_blocked_attempt
