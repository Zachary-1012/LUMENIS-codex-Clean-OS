# -*- coding: utf-8 -*-
"""AI Budget prompt-cache 可观测测试。"""
import os

from scripts.ai_budget import record, summary


def _tmp_log(tmp_path, monkeypatch):
    import scripts.ai_budget as m
    monkeypatch.setattr(m, "LOG", str(tmp_path / "ai-budget.jsonl"))
    monkeypatch.setattr(m, "QUOTA", str(tmp_path / "quota.json"))
    # 写一个空 quota
    import json
    json.dump({"provider": "zhipu", "resources": []}, open(str(tmp_path / "quota.json"), "w", encoding="utf-8"))


def test_record_with_cache_fields(tmp_path, monkeypatch):
    _tmp_log(tmp_path, monkeypatch)
    record("zhipu", "glm-4.7", "summarize", True, 1.2, 1000,
           in_tokens=800, out_tokens=200, cache_hit=True)
    record("zhipu", "glm-4.7", "classify", True, 0.8, 500,
           in_tokens=400, out_tokens=100, cache_hit=False)
    s = summary()
    assert s["total_calls"] == 2
    assert s["cache"]["known"] == 2
    assert s["cache"]["hit"] == 1
    assert s["cache"]["hit_rate"] == 0.5
    assert s["cache"]["in_tokens"] == 1200
    assert s["cache"]["out_tokens"] == 300


def test_record_backward_compatible(tmp_path, monkeypatch):
    _tmp_log(tmp_path, monkeypatch)
    record("zhipu", "glm-4.7", "task", True, 0.5, 100)  # 无 cache 字段
    s = summary()
    assert s["total_calls"] == 1
    assert s["cache"]["known"] == 0  # 无 cache 信息不误报
    assert s["cache"]["hit_rate"] is None
