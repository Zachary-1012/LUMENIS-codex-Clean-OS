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
    assert res["valid"] is False  # 缺 title/url/date 都 error


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
