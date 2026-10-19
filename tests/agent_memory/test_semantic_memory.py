# -*- coding: utf-8 -*-
"""Semantic Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.semantic import SemanticMemory


class TestSemanticMemory:
    def test_search_assets(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.search_assets("品牌 营销") == []

    def test_search_assets_by_tag(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.search_assets("危机", tags=["公关"]) == []

    def test_get_asset(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_asset("asset_001") is None

    def test_get_asset_not_found(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_asset("nonexistent") is None

    def test_get_assets_by_library(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_assets_by_library("brand_knowledge") == []

    def test_get_active_rule_version(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_active_rule_version() is None

    def test_get_rule_history(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_rule_history() == []

    def test_store_knowledge(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        rec = sm.store_knowledge("know:test", {"fact": "test fact"}, tags=["test"])
        assert rec is not None
        retrieved = sm.retrieve("know:test")
        assert retrieved is not None
        assert retrieved.value["fact"] == "test fact"

    def test_get_knowledge_context(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_knowledge_context("品牌营销") == ""

    def test_disabled(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=False)
        assert sm.search_assets("test") == []
        assert sm.get_active_rule_version() is None

    def test_stats(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.stats()["visible_canonical_count"] == 0
