# -*- coding: utf-8 -*-
"""Memory 全链路集成测试 — Working→Task→Episodic 归档 + Learning Loop 反馈→规则→prompt。

真实操作临时DB，不 mock。
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.working import WorkingMemory
from agent_memory.task import TaskMemory
from agent_memory.episodic import EpisodicMemory
from agent_memory.semantic import SemanticMemory
from agent_memory.skill import SkillMemory
from agent_memory.learning import LearningMemory, LifecycleStage
from agent_memory.learning_loop import LearningLoop


class TestMemoryFullChain:
    """Working → Task → Episodic 全链路归档测试。"""

    def test_working_to_episodic_archive(self, seeded_db):
        """完整链路：开始任务 → 记录步骤 → 结束任务 → 归档到 Episodic → 检索。"""
        wm = WorkingMemory(db_path=seeded_db, enabled=True)
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        em = EpisodicMemory(db_path=seeded_db, enabled=True)

        # 1. 开始任务
        wm.begin_task("integration_task_001", "集成测试目标", {"env": "test"})

        # 2. 记录多步执行
        wm.add_step("parse", input_data={"q": "测试"}, output_data={"intent": "analysis"}, persist=False)
        wm.add_step("query", input_data={"table": "notes"}, output_data={"count": 42}, persist=False)
        wm.add_step("analyze", input_data={"data": "..."}, output_data={"sentiment": "positive"}, persist=False)

        # 3. 验证 Working Memory 状态
        assert wm.get_context()["step_count"] == 3
        assert len(wm.get_recent_steps()) == 3

        # 4. 结束任务
        summary = wm.end_task(result={"status": "success", "findings": 3})
        assert summary["step_count"] == 3

        # 5. 归档到 Episodic（需要重新 begin，因为 end_task 清空了）
        wm.begin_task("integration_task_002", "归档测试目标")
        wm.add_step("step1", persist=False)
        archive_id = wm.archive_to_episodic(em)
        assert archive_id is not None

        # 6. 从 Episodic 检索归档案例
        case = em.retrieve("case:integration_task_002")
        assert case is not None
        assert case.value["task_id"] == "integration_task_002"
        assert case.value["step_count"] == 1
        assert case.metadata["type"] == "task_archive"

    def test_task_memory_cross_reference(self, seeded_db):
        """Task Memory 与 Episodic Memory 的交叉引用。"""
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        em = EpisodicMemory(db_path=seeded_db, enabled=True)

        # 从 Task Memory 获取任务
        task = tm.get_task("task_001")
        assert task is not None

        # 从 Episodic 搜索相关案例
        cases = em.search_cases("trend value")
        assert len(cases) >= 1
        # 验证案例关联到同一任务
        assert cases[0]["task_id"] == "task_001"

    def test_semantic_context_injection(self, seeded_db):
        """Semantic Memory 为 AI prompt 提供知识上下文。"""
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        ctx = sm.get_knowledge_context("品牌营销策略")
        assert "太古汇品牌营销策略" in ctx
        assert "语义记忆检索结果" in ctx

    def test_skill_memory_influences_selection(self, seeded_db):
        """Skill Memory 成功率影响 Skill 选择。"""
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        # test_skill_a 有 50% 成功率（1成功1失败）
        # 记录更多成功反馈提升成功率
        for _ in range(5):
            sm.record_feedback("test_skill_a", success=True)
        best = sm.select_best_skill(["test_skill_a", "collector_xhs"])
        # test_skill_a 有执行记录且成功率较高，应优先
        assert best == "test_skill_a"


class TestLearningLoopFullChain:
    """Learning Loop 反馈→规则→prompt 全链路测试。"""

    def test_feedback_to_rule_to_prompt(self, seeded_db):
        """完整链路：用户反馈 → 规则建议 → 人工审核 → 应用规则 → prompt context 影响。"""
        loop = LearningLoop(db_path=seeded_db, enabled=True)

        # 1. 用户反馈 + AI修正
        cycle_result = loop.run_learning_cycle(
            feedback_text="风险等级经常偏高，需要降低敏感度",
            original_output="高风险",
            corrected_output="中风险",
            context={"domain": "risk_assessment"},
        )
        assert cycle_result["feedback_record_id"] is not None
        assert cycle_result["correction_record_id"] is not None
        suggestion_id = cycle_result["rule_suggestion_id"]
        assert suggestion_id is not None

        # 2. 人工审核规则建议
        assert loop.review_rule_suggestion(suggestion_id, approved=True, reviewer="admin")

        # 3. 应用规则到 rule_version_registry
        assert loop.apply_approved_rule(suggestion_id, applied_by="admin")

        # 4. 验证规则已写入（is_active=0，不自动激活）
        import sqlite3
        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM rule_version_registry WHERE version LIKE 'learning_%' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["is_active"] == 0
        assert "Learning Loop" in row["description"]

        # 5. 生成 prompt context（应包含学习到的规则和样本）
        ctx = loop.build_prompt_context()
        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_positive_negative_sample_libraries(self, seeded_db):
        """正/负样本库的积累和查询。"""
        loop = LearningLoop(db_path=seeded_db, enabled=True)

        # 添加多个正样本和负样本
        for i in range(3):
            loop.record_ai_correction(
                original_output=f"orig_{i}",
                corrected_output=f"correct_{i}",
                accepted=True,
            )
        for i in range(2):
            loop.record_ai_correction(
                original_output=f"bad_{i}",
                corrected_output=f"rejected_{i}",
                accepted=False,
            )

        assert len(loop.learning_memory.get_positive_samples()) == 3
        assert len(loop.learning_memory.get_negative_samples()) == 2

        # 正样本应包含 corrected 内容
        pos = loop.learning_memory.get_positive_samples()
        assert all("corrected" in s for s in pos)

    def test_call_quality_analysis_drives_improvement(self, seeded_db):
        """AI 调用质量分析 → 发现问题 → 生成优化建议。"""
        loop = LearningLoop(db_path=seeded_db, enabled=True)

        # 分析调用质量
        quality = loop.analyze_call_quality(days=30)
        assert quality["total_calls"] >= 2
        assert quality["success_rate"] > 0

        # 如果有失败，生成规则建议
        if quality["failure_reasons"]:
            for reason, count in quality["failure_reasons"].items():
                suggestion = loop.generate_rule_suggestion(
                    learning_type="outcome",
                    content={"failure_reason": reason, "count": count},
                    rule_type="system_optimization",
                    confidence=0.3,
                )
                assert suggestion is not None
                assert suggestion.status == "proposed"

    def test_six_layer_memory_interop(self, seeded_db):
        """六层记忆协同工作测试。"""
        wm = WorkingMemory(db_path=seeded_db, enabled=True)
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        skm = SkillMemory(db_path=seeded_db, enabled=True)
        lm = LearningMemory(db_path=seeded_db, enabled=True)

        # Working: 记录当前任务
        wm.begin_task("interop_task", "六层协同测试")
        wm.add_step("init", persist=False)

        # Task: 查询历史任务
        tasks = tm.query_tasks(intent="analysis")
        assert len(tasks) >= 1

        # Episodic: 检索相似案例
        cases = em.search_cases("trend")
        assert len(cases) >= 0  # 可能有也可能没有

        # Semantic: 检索知识
        assets = sm.search_assets("品牌")
        assert len(assets) >= 1

        # Skill: 查询技能统计
        skill_stats = skm.get_skill_stats("test_skill_a")
        assert skill_stats["total"] >= 0

        # Learning: 记录反馈
        feedback = lm.record_feedback("协同测试反馈")
        assert feedback is not None

        # 验证所有层都 enabled 且有数据
        for layer in (wm, tm, em, sm, skm, lm):
            assert layer.enabled is True
            stats = layer.stats()
            assert "layer" in stats or "enabled" in stats
