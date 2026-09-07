# -*- coding: utf-8 -*-
"""Learning Loop 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.learning_loop import LearningLoop, RuleSuggestion
from agent_memory.learning import LifecycleStage


class TestLearningLoop:
    def test_record_user_feedback(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        rec_id = loop.record_user_feedback("分析结果需要更详细", related_task_id="task_001")
        assert rec_id is not None

    def test_record_ai_correction_accepted(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        rec_id = loop.record_ai_correction(
            original_output="负面",
            corrected_output="中性",
            context={"note_id": "n1"},
            accepted=True,
        )
        assert rec_id is not None
        # 正样本库应有记录
        assert len(loop.learning_memory.get_positive_samples()) == 1

    def test_record_ai_correction_rejected(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        rec_id = loop.record_ai_correction(
            original_output="正面",
            corrected_output="负面",
            accepted=False,
        )
        assert rec_id is not None
        assert len(loop.learning_memory.get_negative_samples()) == 1

    def test_generate_rule_suggestion(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        suggestion = loop.generate_rule_suggestion(
            learning_type="correction",
            content={"pattern": "risk overestimation"},
            rule_type="risk",
            confidence=0.6,
        )
        assert suggestion is not None
        assert suggestion.rule_type == "risk"
        assert suggestion.status == "proposed"
        assert len(loop._rule_suggestions) == 1

    def test_review_rule_suggestion_approve(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        s = loop.generate_rule_suggestion("test", {"x": 1}, confidence=0.5)
        assert loop.review_rule_suggestion(s.suggestion_id, approved=True, reviewer="tester")
        updated = next(x for x in loop._rule_suggestions if x.suggestion_id == s.suggestion_id)
        assert updated.status == "approved"
        assert updated.reviewed_by == "tester"

    def test_review_rule_suggestion_reject(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        s = loop.generate_rule_suggestion("test", {"x": 1})
        assert loop.review_rule_suggestion(s.suggestion_id, approved=False)
        updated = next(x for x in loop._rule_suggestions if x.suggestion_id == s.suggestion_id)
        assert updated.status == "rejected"

    def test_apply_approved_rule(self, seeded_db):
        import sqlite3
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        s = loop.generate_rule_suggestion("correction", {"rule": "new"}, rule_type="general")
        loop.review_rule_suggestion(s.suggestion_id, approved=True)
        ok = loop.apply_approved_rule(s.suggestion_id, applied_by="tester")
        assert ok is True
        # 验证写入了 rule_version_registry
        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM rule_version_registry WHERE version LIKE 'learning_%'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["is_active"] == 0  # 不自动激活

    def test_apply_unapproved_rule_fails(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        s = loop.generate_rule_suggestion("test", {"x": 1})
        # 未 review，直接 apply 应失败
        ok = loop.apply_approved_rule(s.suggestion_id)
        assert ok is False

    def test_list_rule_suggestions(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        loop.generate_rule_suggestion("t1", {"a": 1})
        loop.generate_rule_suggestion("t2", {"b": 2})
        all_s = loop.list_rule_suggestions()
        assert len(all_s) == 2
        proposed = loop.list_rule_suggestions(status="proposed")
        assert len(proposed) == 2

    def test_analyze_call_quality(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        quality = loop.analyze_call_quality(days=30)
        assert quality["total_calls"] >= 2
        assert quality["success_count"] >= 1
        assert "success_rate" in quality
        assert "failure_reasons" in quality
        assert "timeout" in quality["failure_reasons"]

    def test_build_prompt_context(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        # 添加正样本
        loop.record_ai_correction("orig", "corrected", accepted=True)
        ctx = loop.build_prompt_context()
        assert isinstance(ctx, str)
        # 应包含关注关键词
        assert "关注关键词" in ctx or "参考正样本" in ctx or "已验证学习规则" in ctx

    def test_run_learning_cycle(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        result = loop.run_learning_cycle(
            feedback_text="风险等级判断偏高",
            original_output="高风险",
            corrected_output="中风险",
            context={"note_id": "n1"},
        )
        assert result["feedback_record_id"] is not None
        assert result["correction_record_id"] is not None
        assert "rule_suggestion_id" in result
        assert result["rule_suggestion_status"] == "proposed (requires human review)"
        assert result["prompt_context_updated"] is True

    def test_disabled(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=False)
        assert loop.record_user_feedback("test") is None
        result = loop.run_learning_cycle("test")
        assert result["enabled"] is False

    def test_stats(self, seeded_db):
        loop = LearningLoop(db_path=seeded_db, enabled=True)
        loop.generate_rule_suggestion("t1", {"a": 1})
        s = loop.stats()
        assert s["enabled"] is True
        assert s["rule_suggestions_total"] == 1
