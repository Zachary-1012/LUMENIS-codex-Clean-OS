# -*- coding: utf-8 -*-
"""Semantic Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.semantic import SemanticMemory


class TestSemanticMemory:
    def test_search_assets(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        results = sm.search_assets("品牌 营销")
        assert len(results) >= 1
        assert results[0]["asset_id"] == "asset_001"

    def test_search_assets_by_tag(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        results = sm.search_assets("危机", tags=["公关"])
        assert len(results) >= 1
        assert "危机" in results[0]["title"]

    def test_get_asset(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        asset = sm.get_asset("asset_001")
        assert asset is not None
        assert asset["title"] == "太古汇品牌营销策略"
        assert asset["evidence_level"] == "high"

    def test_get_asset_not_found(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assert sm.get_asset("nonexistent") is None

    def test_get_assets_by_library(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        assets = sm.get_assets_by_library("brand_knowledge")
        assert len(assets) >= 1
        assert all(a["sub_library"] == "brand_knowledge" for a in assets)

    def test_get_active_rule_version(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        rule = sm.get_active_rule_version()
        assert rule is not None
        assert rule["is_active"] == 1
        assert rule["version"] == "v1.0"

    def test_get_rule_history(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        history = sm.get_rule_history()
        assert len(history) >= 1

    def test_store_knowledge(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        rec = sm.store_knowledge("know:test", {"fact": "test fact"}, tags=["test"])
        assert rec is not None
        retrieved = sm.retrieve("know:test")
        assert retrieved is not None
        assert retrieved.value["fact"] == "test fact"

    def test_get_knowledge_context(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        ctx = sm.get_knowledge_context("品牌营销")
        assert "语义记忆检索结果" in ctx
        assert "太古汇品牌营销策略" in ctx

    def test_disabled(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=False)
        assert sm.search_assets("test") == []
        assert sm.get_active_rule_version() is None

    def test_stats(self, seeded_db):
        sm = SemanticMemory(db_path=seeded_db, enabled=True)
        s = sm.stats()
        assert s["intelligence_assets_total"] >= 2
        assert s["rule_version_total"] >= 1
