# -*- coding: utf-8 -*-
"""P1-3 safe_collection 无公害采集契约层测试（纯离线，不联网、不起采集器）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.system.collector.adapters.safe_collection import (
    redact_text, redact_record, sanitize, CollectionHygienePolicy, RateGovernor,
    build_collection_audit, validate_collection_audit, run_offline_pipeline,
    MIN_INTERVAL_FLOOR, AUDIT_SCHEMA,
)


# ---------- PII 脱敏 ----------
def test_redact_text_masks_contact_keeps_price():
    t = "联系我 13812345678 或 zz_test@qq.com，微信 wxabc123，价格 199 元，q号 12345678"
    out, n = redact_text(t)
    assert n == 4
    assert "13812345678" not in out and "zz_test@qq.com" not in out and "wxabc123" not in out
    assert "[REDACTED:phone]" in out and "[REDACTED:email]" in out
    assert "[REDACTED:wechat]" in out and "[REDACTED:qq]" in out
    assert "199" in out  # 普通价格数字不误伤


def test_redact_record_field_and_text_deepcopy_keeps_content_id():
    raw = {"note_id": "n123", "nickname": "小明", "title": "加我 13812345678", "likes": 5}
    clean, marks = redact_record(raw)
    assert clean["note_id"] == "n123"  # 内容标识保留
    assert clean["nickname"] == "[REDACTED:nickname]"
    assert "13812345678" not in clean["title"]
    assert raw["nickname"] == "小明" and "13812345678" in raw["title"]  # 原对象不被改
    assert "nickname" in marks and any(m.startswith("title:text") for m in marks)


def test_sanitize_strips_credential_keys_recursively():
    d = {"cookie": "x", "nested": {"api_key": "k", "ok": 1}, "items": [{"token": "t"}]}
    out = sanitize(d)
    assert out["cookie"] == "[REDACTED:CREDENTIAL]"
    assert out["nested"]["api_key"] == "[REDACTED:CREDENTIAL]" and out["nested"]["ok"] == 1
    assert out["items"][0]["token"] == "[REDACTED:CREDENTIAL]"


# ---------- 策略 ----------
def test_default_policy_is_safe():
    assert CollectionHygienePolicy().is_safe()


def test_pooling_and_public_web_violations():
    p = CollectionHygienePolicy(allow_account_pool=True)
    assert "account_pool_forbidden" in p.validate()
    p2 = CollectionHygienePolicy(deployment_target="public_web", allow_proxy_pool=True)
    errs = p2.validate()
    assert "proxy_pool_forbidden" in errs and "public_web_forbids_pooling_and_write" in errs
    p3 = CollectionHygienePolicy(deployment_target="public_web", write_enabled=True)
    assert "public_web_forbids_pooling_and_write" in p3.validate()
    p4 = CollectionHygienePolicy(min_interval_seconds=MIN_INTERVAL_FLOOR - 0.5)
    assert any("min_interval_below" in e for e in p4.validate())


# ---------- 限速 / 风险信号 ----------
def test_rate_governor_nonblocking_and_caps():
    pol = CollectionHygienePolicy(min_interval_seconds=3.0, daily_cap=200, max_batch=20)
    gov = RateGovernor(pol)
    assert gov.permit(0.0, None) == (True, 0.0)
    ok, wait = gov.permit(1.0, 0.0)
    assert ok is False and 1.9 < wait <= 2.0
    assert gov.permit(3.0, 0.0)[0] is True
    assert gov.within_daily_cap(199, 1) and not gov.within_daily_cap(200, 1)
    assert gov.within_batch(20) and not gov.within_batch(21)


def test_risk_signal_aligned_with_collector_guard():
    gov = RateGovernor(CollectionHygienePolicy())
    assert gov.assess_risk_signal("300012") == "stop"
    assert gov.assess_risk_signal("IP_RISK_OR_300012") == "stop"
    assert gov.assess_risk_signal("captcha") == "stop"
    assert gov.assess_risk_signal("") == "continue"
    assert gov.assess_risk_signal("healthy") == "continue"


# ---------- 审计 ----------
def test_audit_required_fields_and_status():
    pol = CollectionHygienePolicy()
    good = build_collection_audit(keyword="广州太古汇", requested_count=2, returned_count=2,
                                  redacted_count=1, collector_name="x", operator="Zachary",
                                  policy=pol, status="completed", finished_at="2026-09-02T13:40:00",
                                  extra={"cookie": "leak", "note": "ok"})
    assert good["schema"] == AUDIT_SCHEMA and good["audit_id"]
    assert validate_collection_audit(good) == []
    assert good["extra"]["cookie"] == "[REDACTED:CREDENTIAL]"  # 凭证不搭车
    bad = dict(good); bad["status"] = "weird"
    assert any("invalid:status" in e for e in validate_collection_audit(bad))
    # 非人工触发必须给自动化理由
    auto = build_collection_audit(keyword="k", requested_count=1, returned_count=1, redacted_count=0,
                                  collector_name="x", operator="sys", policy=pol, human_triggered=False)
    assert "non_human_triggered_requires_justification" in validate_collection_audit(auto)


# ---------- 离线管线端到端 ----------
def test_offline_pipeline_redacts_and_audits_without_network():
    raws = [
        {"note_id": "a", "nickname": "甲", "content": "电话 13812345678"},
        {"note_id": "b", "nickname": "乙", "content": "正常内容"},
    ]
    pol = CollectionHygienePolicy()
    out = run_offline_pipeline(raws, keyword="广州太古汇", collector_name="rednote",
                               operator="Zachary", policy=pol, now=100.0, last_action_ts=None,
                               finished_at="2026-09-02T13:40:00")
    assert out["allowed"] is True and out["stopped_risk"] == []
    assert len(out["records"]) == 2
    assert out["records"][0]["nickname"] == "[REDACTED:nickname]"
    assert "13812345678" not in out["records"][0]["content"]
    assert out["redacted_total"] >= 2
    assert out["audit"]["status"] == "completed"
    assert out["audit_errors"] == []


def test_offline_pipeline_stops_on_risk_signal_no_redaction():
    raws = [{"note_id": "a", "nickname": "甲"}]
    out = run_offline_pipeline(raws, keyword="k", collector_name="x", operator="Zachary",
                               risk_signals=["300012"], finished_at="t")
    assert out["stopped_risk"] == ["300012"]
    assert out["records"] == []  # 遇风控停止，不产出（也不伪装成正常 0 条，审计状态为 stopped_risk）
    assert out["audit"]["status"] == "stopped_risk"
