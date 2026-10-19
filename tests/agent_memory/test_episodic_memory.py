# -*- coding: utf-8 -*-
"""Episodic Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.episodic import EpisodicMemory


class TestEpisodicMemory:
    def test_search_cases(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.search_cases("trend value") == []

    def test_search_cases_no_match(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        results = em.search_cases("zzz_nonexistent_keyword_xyz")
        assert results == []

    def test_get_success_patterns(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.get_success_patterns() == []  # Evidence confidence is not business success.

    def test_get_failure_patterns(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.get_failure_patterns() == []

    def test_get_review_experience(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.get_review_experience() == []

    def test_get_correction_patterns(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.get_correction_patterns() == []

    def test_store_case(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        rec = em.store_case("case:test_001", {"task_id": "t1", "result": "ok"}, outcome="success")
        assert rec is not None
        retrieved = em.retrieve("case:test_001")
        assert retrieved is not None
        assert retrieved.value["result"] == "ok"
        assert retrieved.metadata["outcome"] == "success"

    def test_store_case_persist(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.store_case("case:unbound", {"task_id": "task_001"}, persist=True) is None
        import sqlite3
        with sqlite3.connect(seeded_db) as con:
            assert con.execute("SELECT COUNT(*) FROM ai_task_evidence WHERE evidence_type LIKE 'episodic_%'").fetchone()[0] == 0

    def test_disabled(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=False)
        assert em.search_cases("test") == []
        assert em.get_success_patterns() == []

    def test_stats(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        assert em.stats()["visible_evidence_count"] == 0
