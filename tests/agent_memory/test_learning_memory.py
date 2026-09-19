# -*- coding: utf-8 -*-
"""Learning Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lumenis.shared.learning.memory import (
    LearningMemory, LearningType, LifecycleStage, SampleType,
)


class TestLearningMemory:
    def test_list_feedback_keywords(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        keywords = lm.list_feedback_keywords()
        assert len(keywords) >= 2
        kw_names = [k["keyword"] for k in keywords]
        assert "排队" in kw_names
        assert "服务态度" in kw_names

    def test_get_feedback_keyword(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        kw = lm.get_feedback_keyword("排队")
        assert kw is not None
        assert kw["score"] == 0.9
        assert kw["used_count"] == 5

    def test_record_learning(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.FEEDBACK,
            content={"text": "测试反馈"},
            source="user",
            confidence=0.8,
        )
        assert rec is not None
        assert rec.value["learning_type"] == "feedback"
        assert rec.value["confidence"] == 0.8
        assert rec.value["lifecycle_stage"] == "raw"

    def test_record_feedback(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_feedback("这个分析不准确", context={"task": "test"})
        assert rec is not None
        assert rec.value["content"]["feedback_text"] == "这个分析不准确"
        assert rec.value["source"] == "user"

    def test_record_correction(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_correction(
            original_output="负面",
            corrected_output="中性",
            context={"note_id": "n1"},
        )
        assert rec is not None
        assert rec.value["content"]["original_output"] == "负面"
        assert rec.value["content"]["corrected_output"] == "中性"

    def test_positive_negative_samples(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        lm.add_positive_sample({"text": "good output"})
        lm.add_negative_sample({"text": "bad output"})
        assert len(lm.get_positive_samples()) == 1
        assert len(lm.get_negative_samples()) == 1
        assert lm.get_positive_samples()[0]["sample_type"] == "positive"
        assert lm.get_negative_samples()[0]["sample_type"] == "negative"

    def test_promote_record(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"rule": "test"},
            confidence=0.6,
        )
        assert lm.promote_record(rec.record_id, LifecycleStage.REVIEWED) is True
        retrieved = lm.retrieve(rec.key)
        assert retrieved.value["lifecycle_stage"] == "reviewed"

    def test_promote_record_not_found(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        assert lm.promote_record("nonexistent", LifecycleStage.REVIEWED) is False

    def test_get_promoted_rules(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"rule": "promoted rule"},
        )
        lm.promote_record(rec.record_id, LifecycleStage.PROMOTED)
        promoted = lm.get_promoted_rules()
        assert len(promoted) >= 1

    def test_persist_to_agent_learning_records(self, seeded_db):
        import sqlite3
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        lm.record_learning(
            learning_type=LearningType.FEEDBACK,
            content={"text": "persist test"},
        )
        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM agent_learning_records WHERE learning_type='feedback'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert "persist test" in row["content_json"]

    def test_disabled(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=False)
        assert lm.list_feedback_keywords() == []
        assert lm.record_feedback("test") is None

    def test_stats(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        s = lm.stats()
        assert s["feedback_keywords_total"] >= 2
        assert s["positive_samples"] == 0
        assert s["negative_samples"] == 0
