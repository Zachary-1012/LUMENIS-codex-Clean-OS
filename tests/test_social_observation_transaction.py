"""Real XHS observation binding over isolated Raw/Evidence/Canonical owners."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


TABLES = (
    "notes",
    "canonical_data",
    "app_evidence_records",
    "platform_contents",
    "metric_snapshots",
)
PLATFORM = "xhs"
KEYWORD = "non-identity search context"


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _counts(path: Path) -> dict[str, int]:
    with _connect(path) as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLES
        }


def _counts_on_connection(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in TABLES
    }


def _snapshot(path: Path, note_id: str) -> dict[str, object]:
    with _connect(path) as connection:
        note = connection.execute(
            "SELECT note_id,source_platform,title,content,publish_datetime,captured_at,"
            "likes,comments,collects,shares,product_id,domain_id,subject_id,"
            "scope_status,scope_evidence_ref FROM notes WHERE note_id=?", (note_id,),
        ).fetchone()
        canonical = connection.execute(
            "SELECT source_id,external_id,source_platform,title,content,publish_datetime,"
            "captured_at,engagement_likes,engagement_comments,engagement_collects,"
            "engagement_shares,product_id,domain_id,subject_id,scope_status,"
            "scope_evidence_ref FROM canonical_data WHERE source_id=? AND product_id='CTH'",
            (note_id,),
        ).fetchone()
        native = connection.execute(
            "SELECT platform,platform_content_id,title,content,published_at,like_count,"
            "comment_count,collect_count,share_count,raw_data FROM platform_contents "
            "WHERE platform='xiaohongshu' AND platform_content_id=?", (note_id,),
        ).fetchone()
        evidence = connection.execute(
            "SELECT id,feature_id,inputs_json,outputs_json,integrity_digest,"
            "integrity_algorithm FROM app_evidence_records ORDER BY id"
        ).fetchall()
        metrics = connection.execute(
            "SELECT entity_type,entity_key,likes,comments,collects,shares,raw_json "
            "FROM metric_snapshots ORDER BY id"
        ).fetchall()
    return {
        "note": tuple(note) if note is not None else None,
        "canonical": tuple(canonical) if canonical is not None else None,
        "native": tuple(native) if native is not None else None,
        "evidence": [tuple(row) for row in evidence],
        "metrics": [tuple(row) for row in metrics],
    }


def _platform_metric_history(connection: sqlite3.Connection, content_id: str):
    rows = connection.execute(
        "SELECT raw_json FROM metric_snapshots WHERE entity_type='platform_content' "
        "ORDER BY id"
    ).fetchall()
    return [
        payload for (raw_json,) in rows
        if (payload := json.loads(raw_json)).get("platform_content_id") == content_id
    ]


@pytest.fixture
def social_case(tmp_path, monkeypatch):
    db_path = tmp_path / "social-observation-transaction.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"social-observation-test": "isolated-social-observation-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "social-observation-test")

    import database
    import subject_registry
    from lumenis.shared.database import DatabaseRepository, migrations
    from lumenis.shared.database import repository as repository_module
    from lumenis.shared.evidence import store as evidence_store
    from lumenis.system.collector.adapters import secondary_collection as owner

    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(
        repository_module, "_default_repository", DatabaseRepository(str(db_path)),
    )

    database.init_db()
    assert migrations.migrate(target_version=19) is True
    evidence_store.init_evidence_store(str(db_path))
    with migrations.get_connection() as connection:
        assert migrations.get_current_version(connection) == 19
        assert _counts_on_connection(connection) == {table: 0 for table in TABLES}

    subject, _ = subject_registry.add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_zh": "广州太古汇",
        "name_en": "Guangzhou Taikoo Hui",
        "keywords": ["广州太古汇"],
    })
    scope = {
        "domain_id": "cth",
        "subject_id": subject["subject_id"],
        "brand_focus_id": None,
        "global_scope": False,
    }
    return {
        "db_path": db_path,
        "scope": scope,
        "owner": owner,
        "database": database,
        "subject_registry": subject_registry,
    }


def _capture(
    note_id: str = "hk-social-observation-001",
    *,
    title: str = "广州太古汇春日活动记录",
    content: str = "广州太古汇本周服务体验记录",
    desc: str | None = None,
    likes: int = 17,
    partial_comment_rows: int = 3,
    total_comments: int = 31,
    collects: int = 8,
    shares: int = 4,
) -> dict[str, object]:
    body = content if desc is None else desc
    return {
        "note_id": note_id,
        "user_id": "synthetic-hk-user-01",
        "title": title,
        "content": content,
        "desc": body,
        # XHS publication time is native epoch milliseconds; captured time is separate.
        "time": 1790935200000,
        "liked_count": likes,
        # The current JS contract distinguishes loaded comment rows from post totals.
        "comment_count": partial_comment_rows,
        "total_comment_count": total_comments,
        "collected_count": collects,
        "share_count": shares,
        "url": f"https://www.rednote.com/explore/{note_id}",
    }


def _prepared(case, raw: dict[str, object]) -> dict[str, object]:
    records = case["owner"].prepare_xhs_observations(
        [raw], keyword=KEYWORD, captured_at="2026-10-02T10:00:00+00:00",
    )
    assert len(records) == 1
    record = records[0]
    assert record["source_raw"]["comment_count"] == raw["comment_count"]
    assert record["comment_count"] == raw["total_comment_count"]
    return record


def _note_payload(case, observation: dict[str, object]) -> dict[str, object]:
    from lumenis.system.collector.adapters.multi_platform_import import _to_note_payload
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    canonical = to_canonical_record(observation, platform="xhs")
    payload = _to_note_payload(canonical, observation)
    payload["source_keyword"] = KEYWORD
    payload["matched_keywords"] = KEYWORD
    return payload


def _insert_note(case, observation: dict[str, object], *, connection=None):
    return case["database"].insert_note(
        _note_payload(case, observation), connection=connection,
    )


def _bind(case, observation: dict[str, object], *, scope=None, connection=None):
    return case["owner"].bind_collected_social_scope(
        [str(observation["note_id"])],
        scope=scope or case["scope"],
        platform=PLATFORM,
        keyword=KEYWORD,
        provider="isolated-xhs-source-fixture",
        observations=[observation],
        connection=connection,
    )


def _signed_evidence(path: Path) -> list[tuple[dict[str, object], dict[str, object]]]:
    from lumenis.shared.evidence.store import classify_evidence_integrity

    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT * FROM app_evidence_records ORDER BY id"
        ).fetchall()
    checked = []
    for row in rows:
        record = dict(row)
        integrity = classify_evidence_integrity(record)
        assert integrity["verified"] is True
        assert integrity["assurance"] == "writer-authenticated"
        checked.append((record, integrity))
    return checked


def test_xhs_first_bind_repeat_and_metric_body_refresh_preserve_scope_evidence(social_case):
    case = social_case
    raw_first = _capture()
    first_observation = _prepared(case, raw_first)
    note_id = raw_first["note_id"]
    database = case["database"]

    with database.get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, first_observation, connection=connection)
        first = _bind(case, first_observation, connection=connection)
        assert connection.in_transaction is True

    assert first["ok"] is True, first
    assert first["status"] == "VERIFIED", first
    assert first["verified"] == 1 and first["unassigned"] == 0
    assert first["tenant_location_asserted"] is False
    first_snapshot = _snapshot(case["db_path"], note_id)
    assert _counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 1,
        "platform_contents": 1,
        "metric_snapshots": 1,
    }
    with _connect(case["db_path"]) as connection:
        baseline_history = _platform_metric_history(connection, note_id)
    assert len(baseline_history) == 1
    assert {
        name: baseline_history[0][name]
        for name in ("like_count", "comment_count", "collect_count", "share_count", "view_count")
    } == {
        "like_count": 17, "comment_count": 31, "collect_count": 8,
        "share_count": 4, "view_count": None,
    }
    assert baseline_history[0]["evidence_id"] == first["evidence_ref"]
    original_scope_evidence = first["evidence_ref"]
    assert first_snapshot["note"][-2:] == ("VERIFIED", str(original_scope_evidence))
    assert first_snapshot["canonical"][-2:] == ("VERIFIED", str(original_scope_evidence))
    assert first_snapshot["note"][6:10] == (17, 31, 8, 4)
    assert first_snapshot["canonical"][7:11] == (17, 31, 8, 4)
    assert first_snapshot["native"][5:9] == (17, 31, 8, 4)
    first_evidence = _signed_evidence(case["db_path"])[0][0]
    first_inputs = json.loads(first_evidence["inputs_json"])
    assert first_inputs["_lumenis_scope"]["subject_id"] == case["scope"]["subject_id"]
    assert first_inputs["source_ids"] == [note_id]

    repeated = _bind(case, first_observation)
    assert repeated["ok"] is True, repeated
    assert repeated["evidence_ref"] == original_scope_evidence
    assert repeated["observation_changed"] is False
    assert _snapshot(case["db_path"], note_id) == first_snapshot
    assert _counts(case["db_path"])["app_evidence_records"] == 1

    raw_updated = _capture(
        note_id,
        title="广州太古汇春日活动服务更新",
        content="广州太古汇本周服务体验与客流观察更新",
        likes=29,
        partial_comment_rows=5,
        total_comments=42,
        collects=13,
        shares=7,
    )
    updated_observation = _prepared(case, raw_updated)
    with database.get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, updated_observation, connection=connection)
        updated = _bind(case, updated_observation, connection=connection)
        assert connection.in_transaction is True

    assert updated["ok"] is True, updated
    assert updated["status"] == "VERIFIED", updated
    assert updated["observation_changed"] is True
    assert updated["evidence_ref"] != original_scope_evidence
    after = _snapshot(case["db_path"], note_id)
    assert after["note"][2:4] == (raw_updated["title"], raw_updated["content"])
    assert after["canonical"][3:5] == (raw_updated["title"], raw_updated["content"])
    assert after["native"][2:4] == (raw_updated["title"], raw_updated["desc"])
    assert after["note"][6:10] == (29, 42, 13, 7)
    assert after["canonical"][7:11] == (29, 42, 13, 7)
    assert after["native"][5:9] == (29, 42, 13, 7)
    assert after["note"][-2:] == ("VERIFIED", str(original_scope_evidence))
    assert after["canonical"][-2:] == ("VERIFIED", str(original_scope_evidence))
    assert len(after["evidence"]) == 2
    assert _counts(case["db_path"]) == {
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 2,
        "platform_contents": 1,
        "metric_snapshots": 3,
    }
    note_metric_rows = [row for row in after["metrics"] if row[0] == "note"]
    assert [row[:6] for row in note_metric_rows] == [
        ("note", note_id, 29, 42, 13, 7),
    ]
    with _connect(case["db_path"]) as connection:
        platform_history = _platform_metric_history(connection, note_id)
    assert [
        tuple(row[name] for name in (
            "like_count", "comment_count", "collect_count", "share_count", "view_count",
        ))
        for row in platform_history
    ] == [(17, 31, 8, 4, None), (29, 42, 13, 7, None)]
    assert [row["evidence_id"] for row in platform_history] == [
        original_scope_evidence, updated["evidence_ref"],
    ]

    signed = _signed_evidence(case["db_path"])
    assert [record["id"] for record, _ in signed] == [
        original_scope_evidence, updated["evidence_ref"],
    ]
    updated_inputs = json.loads(signed[-1][0]["inputs_json"])
    assert updated_inputs["_lumenis_scope"]["subject_id"] == case["scope"]["subject_id"]
    assert updated_inputs["source_ids"] == [note_id]
    current_native = json.loads(after["native"][9])
    assert current_native["_lumenis_evidence_id"] == updated["evidence_ref"]
    assert current_native["liked_count"] == 29
    assert current_native["total_comment_count"] == 42


def test_caller_owned_transaction_rolls_back_raw_signed_evidence_canonical_and_native(
    social_case,
):
    case = social_case
    raw = _capture()
    observation = _prepared(case, raw)
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, observation, connection=connection)
        first = _bind(case, observation, connection=connection)
    assert first["ok"] is True, first
    before = _snapshot(case["db_path"], str(raw["note_id"]))
    before_counts = _counts(case["db_path"])
    with _connect(case["db_path"]) as connection:
        before_platform_history = _platform_metric_history(connection, str(raw["note_id"]))
    assert [
        tuple(row[name] for name in (
            "like_count", "comment_count", "collect_count", "share_count", "view_count",
        ))
        for row in before_platform_history
    ] == [(17, 31, 8, 4, None)]

    changed_raw = _capture(
        str(raw["note_id"]),
        title="广州太古汇周末服务刷新",
        content="广州太古汇真实来源内容更新用于事务回滚",
        likes=36,
        total_comments=49,
        collects=15,
        shares=9,
    )
    changed = _prepared(case, changed_raw)
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, changed, connection=connection)
        result = _bind(case, changed, connection=connection)
        assert result["ok"] is True, result
        assert connection.in_transaction is True
        staged = _counts_on_connection(connection)
        assert staged == {
            "notes": 1,
            "canonical_data": 1,
            "app_evidence_records": 2,
            "platform_contents": 1,
            "metric_snapshots": 3,
        }
        staged_history = _platform_metric_history(connection, str(raw["note_id"]))
        assert [
            tuple(row[name] for name in (
                "like_count", "comment_count", "collect_count", "share_count", "view_count",
            ))
            for row in staged_history
        ] == [(17, 31, 8, 4, None), (36, 49, 15, 9, None)]
        connection.rollback()

    assert _counts(case["db_path"]) == before_counts
    assert _snapshot(case["db_path"], str(raw["note_id"])) == before
    with _connect(case["db_path"]) as connection:
        assert _platform_metric_history(connection, str(raw["note_id"])) == before_platform_history


def test_cross_scope_rebind_is_rejected_without_changing_signed_truth(social_case):
    case = social_case
    observation = _prepared(case, _capture())
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, observation, connection=connection)
        first = _bind(case, observation, connection=connection)
    assert first["ok"] is True, first
    before = _snapshot(case["db_path"], str(observation["note_id"]))

    other, _ = case["subject_registry"].add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_zh": "海港广场",
        "name_en": "Harbor Plaza",
    })
    other_scope = {
        "domain_id": "cth",
        "subject_id": other["subject_id"],
        "brand_focus_id": None,
        "global_scope": False,
    }
    result = _bind(case, observation, scope=other_scope)

    assert result["ok"] is False
    assert result["status"] == "SCOPE_CONFLICT", result
    assert _snapshot(case["db_path"], str(observation["note_id"])) == before
    assert _counts(case["db_path"])["app_evidence_records"] == 1


def test_mismatched_stored_body_rejects_before_any_scope_or_evidence_write(social_case):
    case = social_case
    raw = _capture()
    observation = _prepared(case, raw)
    _insert_note(case, observation)
    before_counts = _counts(case["db_path"])
    before = _snapshot(case["db_path"], str(observation["note_id"]))

    mismatched = _prepared(case, _capture(
        str(observation["note_id"]),
        content="广州太古汇来源正文与已存 Raw 不同",
        desc="广州太古汇来源正文与已存 Raw 不同",
    ))
    with pytest.raises(ValueError, match="captured observation does not match the stored source"):
        _bind(case, mismatched)

    assert _counts(case["db_path"]) == before_counts
    assert _snapshot(case["db_path"], str(observation["note_id"])) == before


def test_verified_source_that_loses_exact_mention_is_not_rebound_or_refreshed(social_case):
    case = social_case
    original = _prepared(case, _capture())
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, original, connection=connection)
        first = _bind(case, original, connection=connection)
    assert first["ok"] is True, first

    lost_mention_raw = _capture(
        str(original["note_id"]),
        title="周末城市生活记录",
        content="新版本来源正文不再包含注册主体名称",
        desc="新版本来源正文不再包含注册主体名称",
        likes=33,
        total_comments=45,
    )
    lost_mention = _prepared(case, lost_mention_raw)
    _insert_note(case, lost_mention)
    before = _snapshot(case["db_path"], str(original["note_id"]))
    before_counts = _counts(case["db_path"])

    result = _bind(case, lost_mention)

    assert result["ok"] is False
    assert result["status"] == "SOURCE_SCOPE_REVIEW_REQUIRED", result
    assert result["verified"] == 0
    after = _snapshot(case["db_path"], str(original["note_id"]))
    assert _counts(case["db_path"]) == before_counts
    assert after == before
    assert after["note"][2:4] == (lost_mention_raw["title"], lost_mention_raw["content"])
    assert after["canonical"][3:5] == (
        original["title"], original["content"],
    )
    assert after["note"][-2:] == ("VERIFIED", str(first["evidence_ref"]))
    assert after["canonical"][-2:] == ("VERIFIED", str(first["evidence_ref"]))


def test_signed_observation_hash_mismatch_blocks_native_write_and_rolls_back(
    social_case, monkeypatch,
):
    case = social_case
    observation = _prepared(case, _capture())
    _insert_note(case, observation)
    note_id = str(observation["note_id"])
    before_counts = _counts(case["db_path"])
    before = _snapshot(case["db_path"], note_id)

    from lumenis.shared.database import platform_content
    from lumenis.shared.evidence.store import classify_evidence_integrity

    original_writer = platform_content.persist_verified_platform_records
    staged = []

    def alter_after_evidence_is_signed(records, **kwargs):
        assert kwargs.get("require_observation_proof") is True
        connection = kwargs["connection"]
        evidence_id = kwargs["evidence_id"]
        row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,),
        ).fetchone()
        evidence = dict(row)
        integrity = classify_evidence_integrity(evidence)
        assert integrity["verified"] is True
        assert integrity["assurance"] == "writer-authenticated"
        staged.append(_counts_on_connection(connection))
        altered = [dict(records[0])]
        altered[0]["liked_count"] += 1
        return original_writer(altered, **kwargs)

    monkeypatch.setattr(
        platform_content, "persist_verified_platform_records", alter_after_evidence_is_signed,
    )

    with pytest.raises(ValueError, match="current source observation does not match signed Evidence"):
        _bind(case, observation)

    assert staged == [{
        "notes": 1,
        "canonical_data": 1,
        "app_evidence_records": 1,
        "platform_contents": 0,
        "metric_snapshots": 0,
    }]
    assert _counts(case["db_path"]) == before_counts
    assert _snapshot(case["db_path"], note_id) == before


@pytest.mark.parametrize(
    "keyword,title,content,expected_status",
    [
        (KEYWORD, "广州太古汇春日活动记录", "广州太古汇本周服务体验记录", "SUCCESS"),
        ("广州太古汇", "上海兴业太古汇活动", "来源内容只描述另一地点", "SCOPE_REVIEW_REQUIRED"),
    ],
)
def test_manual_focus_collect_search_uses_native_xhs_items_and_exact_scope(
    social_case, monkeypatch, keyword, title, content, expected_status,
):
    from flask import Flask

    from lumenis.system import security
    from lumenis.system.security import permission
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter

    case = social_case
    owner = case["owner"]
    scope = case["scope"]
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)

    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    raw = _capture(note_id="manual-focus-xhs-001", title=title, content=content)
    raw["desc"] = content

    class FakeXhsBackend:
        calls = []

        def search_xiaohongshu(self, source_keyword, *, max_scroll, output_path=None, max_details=10):
            self.calls.append((source_keyword, max_scroll, output_path, max_details))
            return {
                "notes": [raw], "total": 1, "channel": "isolated_fixture",
                "region": "intl", "collected_at": "2026-10-07T01:00:00+00:00",
            }

    backend = FakeXhsBackend()
    adapter = XiaohongshuAdapter(backend=backend)
    monkeypatch.setattr(owner, "_adapter_health", lambda *a, **kw: {
        "status": "SUCCESS", "ready": True, "can_attempt": True,
    })
    monkeypatch.setattr(owner, "_get_runtime_adapter", lambda *a, **kw: adapter)
    monkeypatch.setattr(owner, "_daily_action_count", lambda *a, **kw: 0)
    monkeypatch.setitem(owner._last_action, "xiaohongshu", 0.0)

    with app.test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = permission.resolve_local_workspace_principal(
            module="collector", action="write",
        )
        _, approval_required = owner._manual_collection_guard(
            principal, scope, "xiaohongshu", keyword, 1, max_scroll=7,
        )
        assert approval_required["status"] == "APPROVAL_REQUIRED"
        gate.grant_approval(
            permission.OperationType.DATA_IMPORT.value,
            resource=approval_required["approval_resource"],
            granted_by="isolated manual FOCUS test",
        )
        result = owner.collect_search(
            "xiaohongshu", keyword, max_results=1, max_scroll=7,
            actor=principal, scope=scope,
        )

    assert backend.calls == [(keyword, 7, None, 10)]
    assert result["status"] == expected_status, result
    assert result["provenance"].get("max_scroll") == 7
    if expected_status == "SUCCESS":
        assert result["ok"] is True
        assert result["scope_status"] == "VERIFIED"
        assert result["refresh_verified"] is True
        assert result["canonical_synced"] == 1
        assert result["native_fields_synced"] == 1
        snapshot = _snapshot(case["db_path"], str(raw["note_id"]))
        assert snapshot["note"][-2] == "VERIFIED"
        assert snapshot["canonical"][-2] == "VERIFIED"
        assert snapshot["native"] is not None
        assert _counts(case["db_path"]) == {
            "notes": 1,
            "canonical_data": 1,
            "app_evidence_records": 1,
            "platform_contents": 1,
            "metric_snapshots": 1,
        }
        evidence = _signed_evidence(case["db_path"])[0][0]
        assert evidence["feature_id"] == "SYSTEM_XIAOHONGSHU_COLLECT"
        assert json.loads(evidence["inputs_json"])["source_ids"] == [str(raw["note_id"])]
    else:
        assert result["ok"] is False
        assert result["entity_mentions"][0]["status"] == "REVIEW_REQUIRED"
        assert _counts(case["db_path"]) == {
            "notes": 0,
            "canonical_data": 0,
            "app_evidence_records": 1,
            "platform_contents": 0,
            "metric_snapshots": 0,
        }
