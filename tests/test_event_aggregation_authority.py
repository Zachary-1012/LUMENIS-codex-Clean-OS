# -*- coding: utf-8 -*-
"""P0-1 事件聚合唯一权威收口测试。

背景：旧受保护名 aggregate_events() 重构时更名为 reprocess.build_cross_platform_events，
基线 grep 旧名误判 MISSING（对账 GAP-P0-01）。本测试锁定：
1) aggregate_events 是转发到唯一权威的兼容入口（不再另写一套口径）；
2) 全仓事件聚合实现只有 reprocess 一处（单一 Owner）；
3) 风险事实来自数据（risk_score 取 max / 负面计数），AI 关闭照样聚合、不改写风险。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reprocess  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_protected_alias_forwards_to_single_authority(monkeypatch):
    sentinel = [{"event_key": "x"}]
    captured = {}

    def fake_build(limit=100):
        captured["limit"] = limit
        return sentinel

    monkeypatch.setattr(reprocess, "build_cross_platform_events", fake_build)
    # 兼容名必须转发到同一权威，且透传 limit，不产生第二份结果
    assert reprocess.aggregate_events(limit=7) is sentinel
    assert captured["limit"] == 7


def test_single_owner_across_codebase():
    owner_files = []
    protected_alias_files = []
    skip = (".venv", "__pycache__", "backups", "_backup", "archive", "tests", ".trae")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                text = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "def build_cross_platform_events" in text:
                owner_files.append(os.path.relpath(fp, ROOT))
            if "def aggregate_events" in text:
                protected_alias_files.append(os.path.relpath(fp, ROOT))
    # 唯一实现只在 reprocess.py
    assert owner_files == ["reprocess.py"], owner_files
    # 受保护兼容名也只在 reprocess.py（同一文件内，非第二套实现）
    assert protected_alias_files == ["reprocess.py"], protected_alias_files


def test_risk_fact_comes_from_data_not_ai(monkeypatch):
    # 上游 get_notes 只应取 verified=1 的笔记（主体硬过滤后的输入）
    seen_query = {}

    def fake_get_notes(query, limit, offset):
        seen_query.update(query)
        return [
            {"event_hint": "方所闭店", "title": "方所撤场讨论一", "topics": ["闭店"],
             "publish_date": "2026-08-20", "sentiment": "negative", "risk_score": 70},
            {"event_hint": "方所闭店", "title": "方所撤场讨论二", "topics": ["闭店"],
             "publish_date": "2026-08-21", "sentiment": "neutral", "risk_score": 20},
        ]

    captured = {}

    def fake_get_web(limit, verified):
        return []

    def fake_upsert(event):
        captured.update(event)
        return 1

    monkeypatch.setattr(reprocess.db, "get_notes", fake_get_notes)
    monkeypatch.setattr(reprocess.db, "get_web_mentions", fake_get_web)
    monkeypatch.setattr(reprocess.db, "upsert_event", fake_upsert)
    monkeypatch.setattr(reprocess.db, "link_event_mentions", lambda *a, **k: None)
    # AI 关闭：摘要返回空、ai_enabled=False —— 聚合仍须成功且风险来自数据
    monkeypatch.setattr(reprocess.intelligence, "summarize_event", lambda e, m: {})
    monkeypatch.setattr(reprocess.intelligence, "ai_enabled", lambda: False)

    made = reprocess.build_cross_platform_events()
    assert seen_query.get("verified") is True
    assert len(made) == 1
    # risk 取两条 max=70 → high；mention_count=2；未被 AI 空结果改写
    assert captured["risk_score"] == 70
    assert captured["risk_level"] == "high"
    assert captured["mention_count"] == 2
