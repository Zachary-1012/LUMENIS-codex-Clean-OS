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
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        results = em.search_cases("trend value")
        assert len(results) >= 1
        assert results[0]["evidence_id"] == "ev_001"

    def test_search_cases_no_match(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        results = em.search_cases("zzz_nonexistent_keyword_xyz")
        assert results == []

    def test_get_success_patterns(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        patterns = em.get_success_patterns(limit=10)
        assert len(patterns) >= 1
        assert all(p["authenticity_score"] >= 0.8 for p in patterns)

    def test_get_failure_patterns(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        patterns = em.get_failure_patterns(limit=10)
        assert len(patterns) >= 1
        assert any("error" in p["evidence_type"] for p in patterns)

    def test_get_review_experience(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        reviews = em.get_review_experience(limit=10)
        assert len(reviews) >= 1
        assert reviews[0]["note_id"] == "note_001"

    def test_get_correction_patterns(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        corrections = em.get_correction_patterns(limit=10)
        assert len(corrections) >= 1
        # old_risk=high, new_risk=low → 有修正
        assert corrections[0]["old_risk"] != corrections[0]["new_risk"]

    def test_store_case(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        rec = em.store_case("case:test_001", {"task_id": "t1", "result": "ok"}, outcome="success")
        assert rec is not None
        retrieved = em.retrieve("case:test_001")
        assert retrieved is not None
        assert retrieved.value["result"] == "ok"
        assert retrieved.metadata["outcome"] == "success"

    def test_store_case_persist(self, seeded_db):
        import sqlite3
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        em.store_case("case:persist_test", {"task_id": "t_persist", "data": "x"},
                      outcome="success", persist=True)
        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM ai_task_evidence WHERE evidence_type LIKE 'episodic_%'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_disabled(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=False)
        assert em.search_cases("test") == []
        assert em.get_success_patterns() == []

    def test_stats(self, seeded_db):
        em = EpisodicMemory(db_path=seeded_db, enabled=True)
        s = em.stats()
        assert s["ai_task_evidence_total"] >= 2
        assert s["note_review_history_total"] >= 1
