# -*- coding: utf-8 -*-
"""Skill Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.skill import SkillMemory


class TestSkillMemory:
    def test_list_skills(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        skills = sm.list_skills()
        assert len(skills) >= 2
        skill_ids = [s["skill_id"] for s in skills]
        assert "test_skill_a" in skill_ids
        assert "collector_xhs" in skill_ids

    def test_list_skills_by_status(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        enabled = sm.list_skills(status="enabled")
        assert len(enabled) >= 1
        assert all(s["status"] == "enabled" for s in enabled)

    def test_get_skill(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        skill = sm.get_skill("test_skill_a")
        assert skill is not None
        assert skill["name"] == "测试技能A"

    def test_get_skill_not_found(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        assert sm.get_skill("nonexistent") is None

    def test_get_skill_stats(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        stats = sm.get_skill_stats("test_skill_a")
        assert stats["total"] == 2
        assert stats["success"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["failed"] == 1

    def test_get_skill_stats_no_executions(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        stats = sm.get_skill_stats("collector_xhs")
        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_all_skill_stats(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        all_stats = sm.get_all_skill_stats()
        assert len(all_stats) >= 2

    def test_get_recent_executions(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        execs = sm.get_recent_executions(skill_id="test_skill_a")
        assert len(execs) == 2

    def test_record_feedback(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        assert sm.record_feedback("new_skill", success=True, duration_ms=100) is True
        assert sm.record_feedback("new_skill", success=False, duration_ms=200) is True
        cache = sm._success_cache["new_skill"]
        assert cache["total"] == 2
        assert cache["success"] == 1
        assert cache["rate"] == 0.5

    def test_select_best_skill(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        # test_skill_a 有 50% 成功率，nonexistent 无记录
        best = sm.select_best_skill(["test_skill_a", "nonexistent_skill"])
        assert best == "test_skill_a"

    def test_select_best_skill_empty(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        assert sm.select_best_skill([]) is None

    def test_disabled(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=False)
        assert sm.list_skills() == []
        assert sm.get_skill_stats("test_skill_a")["total"] == 0

    def test_stats(self, seeded_db):
        sm = SkillMemory(db_path=seeded_db, enabled=True)
        s = sm.stats()
        assert s["skills_registry_total"] >= 2
        assert s["skill_executions_total"] >= 2
