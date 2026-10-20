# -*- coding: utf-8 -*-
"""DataQualityGate 测试（研究自 OpenDQV write-time enforcement 落地）。"""
import pytest

from data_quality_gate import DataQualityGate


@pytest.fixture
def gate():
    return DataQualityGate()


def test_contracts_loaded(gate):
    names = gate.list_contracts()
    assert "note" in names and "event" in names and "topic_snapshot" in names


def test_valid_note_passes(gate):
    res = gate.validate("note", {
        "title": "测试笔记",
        "url": "https://www.xiaohongshu.com/explore/abc",
        "risk_level": "low",
        "publish_date": "2026-08-31 10:00:00",
    })
    assert res["valid"] is True and res["errors"] == []


def test_invalid_note_rejected(gate):
    res = gate.validate("note", {
        "title": "",
        "url": "not-a-url",
        "publish_date": "bad-date",
    })
    assert res["valid"] is False
    fields = {e["field"] for e in res["errors"]}
    assert "title" in fields and "url" in fields and "publish_date" in fields


def test_publish_time_missing_is_distinct_from_invalid(gate):
    record = {"title": "Official release", "url": "https://example.com/release",
              "risk_level": "low"}
    missing = gate.validate("note", record)
    assert missing["valid"] is False
    assert missing["errors"] == []
    assert [item["field"] for item in missing["missing"]] == ["publish_date"]
    quality = gate.enrich_quality_record("note", record)
    assert quality["data_quality_status"] == "missing"
    assert "publish_date" in quality["data_quality_errors"]

    invalid = gate.validate("note", {**record, "publish_date": "not-a-date"})
    assert invalid["valid"] is False
    assert invalid["missing"] == []
    assert [item["field"] for item in invalid["errors"]] == ["publish_date"]
    assert gate.enrich_quality_record("note", {**record, "publish_date": "not-a-date"})[
        "data_quality_status"] == "error"


@pytest.mark.parametrize("publish_date", [
    "2026-09-23T16:41:24.000Z",
    "2026-09-23T16:41:24.123+08:00",
])
def test_fractional_iso_publish_time_with_timezone_is_valid(gate, publish_date):
    record = {"title": "Official release", "url": "https://example.com/release",
              "risk_level": "low", "publish_date": publish_date}
    result = gate.validate("note", record)
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["missing"] == []
    assert gate.enrich_quality_record("note", record)["data_quality_status"] == "ok"


@pytest.mark.parametrize("publish_date", [
    "2026-02-30T16:41:24.000Z",
    "2026-09-23T16:41:24.000+08:99",
])
def test_invalid_fractional_iso_publish_time_is_rejected(gate, publish_date):
    result = gate.validate("note", {
        "title": "Official release",
        "url": "https://example.com/release",
        "publish_date": publish_date,
    })
    assert result["valid"] is False
    assert result["missing"] == []
    assert [item["field"] for item in result["errors"]] == ["publish_date"]


def test_atom_rfc2822_publish_time_is_valid(gate):
    record = {"title": "Official Atom item", "url": "https://example.com/item",
              "risk_level": "low", "publish_date": "Thu, 24 Sep 2026 14:02:37 +0000"}
    assert gate.validate("note", record)["valid"] is True
    assert gate.enrich_quality_record("note", record)["data_quality_status"] == "ok"


def test_warning_severity_does_not_block(gate):
    # risk_level=unknown -> warning（不阻止），title 正常
    res = gate.validate("note", {
        "title": "ok",
        "url": "https://example.com/a",
        "risk_level": "unknown",
        "publish_date": "2026-08-31 10:00:00",
    })
    assert res["valid"] is True
    assert len(res["warnings"]) == 1
    assert res["warnings"][0]["field"] == "risk_level"


def test_unknown_contract(gate):
    res = gate.validate("nope", {})
    assert res["valid"] is False
    assert res["errors"][0]["rule"] == "_contract"
    assert res["errors"][0]["field"] is None
    assert res["errors"][0]["severity"] == "error"


def test_fix_031_unknown_contract_enrichment_keeps_structured_issue(tmp_path):
    """FIX-031: unknown contract errors have no field but still enrich safely."""
    gate = DataQualityGate(str(tmp_path / "empty-contracts"))
    quality = gate.enrich_quality_record("missing-contract", {})

    assert quality["data_quality_status"] == "error"
    assert quality["data_quality_score"] == 90
    assert quality["data_quality_errors"] == (
        "_contract.-:未知契约: missing-contract"
    )


def test_fix_031_database_exposes_unknown_contract_quality_issue(monkeypatch):
    """FIX-031: unknown contract remains a soft note write and reaches its caller."""
    import sqlite3

    import data_quality_gate
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_business_schema(connection)
    real_gate = DataQualityGate()

    class UnknownContractGate:
        def enrich_quality_record(self, _contract_name, record):
            return real_gate.enrich_quality_record("missing-contract", record)

    monkeypatch.setattr(data_quality_gate, "DataQualityGate", UnknownContractGate)
    note = {"note_id": "fix-031-unknown-contract", "title": "Synthetic note"}
    try:
        row_id, inserted = database.insert_note(note, connection=connection)
        row = connection.execute(
            "SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            (note["note_id"],),
        ).fetchone()
        assert row_id > 0 and inserted is True
        assert row["data_quality_status"] == "error"
        assert row["data_quality_score"] == 90
        assert note["data_quality_errors"] == (
            "_contract.-:未知契约: missing-contract"
        )
    finally:
        connection.close()


def test_fix_031_database_keeps_soft_write_and_surfaces_exception(caplog, monkeypatch):
    """FIX-031: unexpected gate failures stay soft and their cause is visible."""
    import sqlite3

    import data_quality_gate
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_business_schema(connection)

    class BrokenGate:
        def enrich_quality_record(self, _contract_name, _record):
            raise RuntimeError("synthetic gate failure")

    monkeypatch.setattr(data_quality_gate, "DataQualityGate", BrokenGate)
    note = {"note_id": "fix-031-soft-failure", "title": "Synthetic note"}
    try:
        row_id, inserted = database.insert_note(note, connection=connection)
        row = connection.execute(
            "SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            (note["note_id"],),
        ).fetchone()
        assert row_id > 0 and inserted is True
        assert row["data_quality_status"] == "error"
        assert row["data_quality_score"] is None
        assert note["data_quality_errors"] == (
            "_enrichment.-:RuntimeError: synthetic gate failure"
        )
        assert "synthetic gate failure" in caplog.text
    finally:
        connection.close()


def test_fix_031_enrichment_failure_replaces_stale_quality_success(
    caplog, monkeypatch,
):
    """FIX-031: a failed refresh must not leave stale ok/100 state on an existing note."""
    import sqlite3

    import data_quality_gate
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_business_schema(connection)
    note_id = "fix-031-refresh-failure"
    try:
        row_id, inserted = database.insert_note(
            {
                "note_id": note_id,
                "title": "Known-good title",
                "url": "https://example.test/article",
                "publish_date": "2026-10-20",
                "risk_level": "low",
            },
            connection=connection,
        )
        assert row_id > 0 and inserted is True
        before = connection.execute(
            "SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            (note_id,),
        ).fetchone()
        assert tuple(before) == ("ok", 100)

        class BrokenGate:
            def enrich_quality_record(self, _contract_name, _record):
                raise RuntimeError("synthetic refresh failure")

        monkeypatch.setattr(data_quality_gate, "DataQualityGate", BrokenGate)
        refreshed = {"note_id": note_id, "title": "Updated title"}
        row_id, inserted = database.insert_note(refreshed, connection=connection)
        row = connection.execute(
            "SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            (note_id,),
        ).fetchone()

        assert row_id > 0 and inserted is False
        assert tuple(row) == ("error", None)
        assert refreshed["data_quality_errors"] == (
            "_enrichment.-:RuntimeError: synthetic refresh failure"
        )
        assert "synthetic refresh failure" in caplog.text
    finally:
        connection.close()


def test_event_allowed_values(gate):
    ok = gate.validate("event", {"event_type": "propagation_event", "risk_level": "low"})
    assert ok["valid"] is True
    bad = gate.validate("event", {"event_type": "bogus", "risk_level": "low"})
    assert bad["valid"] is False


def test_batch_unique_topic(gate):
    recs = [{"topic": "广州太古汇", "snapshot_date": "2026-08-31 10:00:00"},
            {"topic": "广州太古汇", "snapshot_date": "2026-08-31 11:00:00"}]
    results = gate.validate_batch("topic_snapshot", recs)
    assert results[0]["valid"] is True
    assert results[1]["valid"] is False
    assert any(e["rule"] == "unique" for e in results[1]["errors"])


def test_batch_unique_values_are_isolated_by_field(gate):
    gate._contracts["cross_field_unique"] = {
        "version": "test",
        "rules": [
            {"name": "account_unique", "type": "unique", "field": "account"},
            {"name": "email_unique", "type": "unique", "field": "email"},
        ],
    }

    results = gate.validate_batch("cross_field_unique", [
        {"account": "shared", "email": "first@example.invalid"},
        {"account": "other", "email": "shared"},
        {"account": "shared", "email": "second@example.invalid"},
    ])

    assert [result["valid"] for result in results] == [True, True, False]
    assert results[2]["errors"] == [{
        "rule": "unique", "field": "account",
        "message": "批内重复: shared", "severity": "error",
    }]


def test_unknown_rules_return_structured_diagnostics(gate):
    gate._contracts["unknown_warning"] = {
        "version": "test",
        "rules": [{"name": "future_check", "type": "future_check", "field": "value"}],
    }
    warning = gate.validate("unknown_warning", {"value": "x"})
    assert warning["valid"] is True
    assert warning["warnings"] == [{
        "rule": "future_check", "field": "value",
        "message": "未知规则类型: future_check", "severity": "warning",
    }]

    gate._contracts["unknown_error"] = {
        "version": "test",
        "rules": [{"name": "required_future_check", "type": "future_check",
                   "field": "value", "severity": "error"}],
    }
    error = gate.validate("unknown_error", {"value": "x"})
    assert error["valid"] is False
    assert error["errors"][0]["rule"] == "required_future_check"
    assert error["errors"][0]["field"] == "value"
    assert error["errors"][0]["severity"] == "error"

    gate._contracts["malformed_rule_type"] = {
        "version": "test",
        "rules": [{"name": "malformed_type", "type": ["future_check"],
                   "field": "value", "severity": "error"}],
    }
    malformed = gate.validate("malformed_rule_type", {"value": "x"})
    assert malformed["valid"] is False
    assert malformed["errors"][0]["rule"] == "malformed_type"
    assert malformed["errors"][0]["message"] == "未知规则类型: ['future_check']"


def test_fix_031_false_condition_skips_unknown_error_rule(gate):
    gate._contracts["conditional_unknown_rule"] = {
        "version": "test",
        "rules": [{
            "name": "video_only_future_rule",
            "type": "future_check",
            "field": "content",
            "severity": "error",
            "condition": {"field": "media_type", "equals": "video"},
        }],
    }

    text_record = gate.validate("conditional_unknown_rule", {
        "media_type": "text", "content": "plain text",
    })
    video_record = gate.validate("conditional_unknown_rule", {
        "media_type": "video", "content": "video text",
    })

    assert text_record["valid"] is True
    assert text_record["errors"] == []
    assert video_record["valid"] is False
    assert video_record["errors"][0]["rule"] == "video_only_future_rule"
    assert video_record["errors"][0]["severity"] == "error"


@pytest.mark.parametrize("value", ["not-a-number", float("nan"), float("inf"), float("-inf")])
def test_numeric_rules_return_structured_errors_for_illegal_values(gate, value):
    gate._contracts["finite_number"] = {
        "version": "test",
        "rules": [{"name": "score_min", "type": "min", "field": "score",
                   "min": 0, "severity": "error"}],
    }

    result = gate.validate("finite_number", {"score": value})

    assert result["valid"] is False
    assert result["errors"] == [{
        "rule": "score_min", "field": "score", "message": "数值非法", "severity": "error",
    }]


def test_invalid_numeric_rule_parameters_are_diagnosed(gate):
    gate._contracts["invalid_numeric_rule"] = {
        "version": "test",
        "rules": [{"name": "score_range", "type": "range", "field": "score",
                   "min": 0, "max": "not-a-number", "severity": "error"}],
    }

    result = gate.validate("invalid_numeric_rule", {"score": 5})

    assert result["valid"] is False
    assert result["errors"] == [{
        "rule": "score_range", "field": "score",
        "message": "规则参数非法: range", "severity": "error",
    }]


def test_fix_031_integer_bounds_above_float_precision_remain_exact(gate):
    gate._contracts["large_integer_bounds"] = {
        "version": "test",
        "rules": [
            {"name": "large_min", "type": "min", "field": "lower",
             "min": 9007199254740993, "severity": "error"},
            {"name": "large_max", "type": "max", "field": "upper",
             "max": 9007199254740995, "severity": "error"},
        ],
    }

    result = gate.validate("large_integer_bounds", {
        "lower": 9007199254740992,
        "upper": 9007199254740996,
    })

    assert result["valid"] is False
    assert {item["rule"] for item in result["errors"]} == {"large_min", "large_max"}


def test_unique_rule_without_field_returns_structured_error(gate):
    gate._contracts["invalid_unique_rule"] = {
        "version": "test",
        "rules": [{"name": "missing_unique_field", "type": "unique"}],
    }

    result = gate.validate_batch("invalid_unique_rule", [{}])[0]

    assert result["valid"] is False
    assert result["errors"] == [{
        "rule": "missing_unique_field", "field": None,
        "message": "唯一性规则缺少有效字段", "severity": "error",
    }]


def test_condition_rule_skip(gate):
    # condition 仅当条件字段等于值时应用（用 note 契约无 condition，验证不报错）
    res = gate.validate("note", {})
    assert res["valid"] is False  # title/url 错误，日期缺失单独标记


def test_enrich_quality_record(gate):
    # 合法记录 -> ok/100
    r = gate.enrich_quality_record("note", {
        "title": "ok", "url": "https://x.com/a", "risk_level": "low",
        "publish_date": "2026-08-31"})
    assert r["data_quality_status"] == "ok" and r["data_quality_score"] == 100
    # 缺 title/url/date -> error，分数降低，摘要含明细
    r2 = gate.enrich_quality_record("note", {})
    assert r2["data_quality_status"] == "error"
    assert r2["data_quality_score"] < 100
    assert "title" in r2["data_quality_errors"]


def test_insert_note_quality_soft_gate(tmp_path, monkeypatch):
    """写入门软门：未传 status 时自动标记；有显式 status 时保留。"""
    import os
    import database
    db = str(tmp_path / "qgate.db")
    monkeypatch.setenv("ZBC_DB_PATH", db)
    database.init_db()
    # 合法记录 -> 自动 ok 标记
    nid1 = "qgate_ok_001"
    database.insert_note({"note_id": nid1, "title": "测试笔记", "url": "https://x.com/1",
                          "publish_date": "2026-08-31", "risk_level": "low"})
    with database.get_db() as c:
        r1 = c.execute("SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?", (nid1,)).fetchone()
    assert r1[0] == "ok" and r1[1] == 100
    # 缺字段 -> warning/error 标记（软门不拒绝写入）
    nid2 = "qgate_warn_001"
    database.insert_note({"note_id": nid2, "title": "缺url", "publish_date": ""})
    with database.get_db() as c:
        r2 = c.execute("SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?", (nid2,)).fetchone()
    assert r2[0] in ("warning", "error") and r2[1] < 100
    # 显式传 status 保留（调用方覆盖）
    nid3 = "qgate_explicit_001"
    database.insert_note({"note_id": nid3, "title": "explicit", "url": "https://x.com/3",
                          "publish_date": "2026-08-31", "risk_level": "low",
                          "data_quality_status": "custom", "data_quality_score": 55})
    with database.get_db() as c:
        r3 = c.execute("SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?", (nid3,)).fetchone()
    assert r3[0] == "custom" and r3[1] == 55
