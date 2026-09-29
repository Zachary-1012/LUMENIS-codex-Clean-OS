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
