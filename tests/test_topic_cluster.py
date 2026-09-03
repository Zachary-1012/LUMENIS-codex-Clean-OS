# -*- coding: utf-8 -*-
"""Topic 聚类 → 事件标签测试（c-TF-IDF 落地事件摘要）。"""
from scripts.topic_cluster import event_topic_labels, enrich_events_with_labels


def _ev(title, summary, risk_level="low"):
    return {"event_key": title, "title": title, "summary": summary, "risk_level": risk_level}


def test_event_topic_labels_groups_by_risk():
    events = [
        _ev("防晒霜事件", "防晒霜出现过敏反馈，多名用户反映皮肤红肿", "high"),
        _ev("防晒霜召回", "某品牌防晒霜因成分问题被召回", "high"),
        _ev("口红新品", "新色号口红上市，博主推荐", "low"),
    ]
    labels = event_topic_labels(events, group_field="risk_level", top_k=5)
    by_group = {l["group"]: l for l in labels}
    assert "high" in by_group and "low" in by_group
    # high 组主题词应含"防晒"
    assert any("防晒" in w for w, _ in by_group["high"]["words"])


def test_enrich_events_with_labels():
    events = [_ev("保湿面霜测评", "这款保湿面霜补水效果很好，适合干皮")]
    out = enrich_events_with_labels(events, top_k=3)
    assert "topic_label" in out[0]
    assert isinstance(out[0]["topic_label"], str) and out[0]["topic_label"]
    # 不改原对象
    assert "topic_label" not in events[0]


def test_empty_inputs():
    assert event_topic_labels([]) == []
    assert enrich_events_with_labels([]) == []
    assert enrich_events_with_labels([{"title": "", "summary": ""}])[0]["topic_label"] == "未命名主题"
