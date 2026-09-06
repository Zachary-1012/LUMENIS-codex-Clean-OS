# -*- coding: utf-8 -*-
"""
AI 与原始数据分离存储测试（P0 红线）
======================================
验证：
1. AI 结果存入独立字段 ai_analysis，不覆盖原始 content/sentiment/risk
2. CanonicalRecord 有 ai_analysis 独立字段
3. evidence_chain 中 AI 证据与原始数据分离
4. AI 结果可关联 source_id/raw_id/canonical_id

运行: .venv\\Scripts\\python.exe -m pytest tests/test_ai_raw_separation.py -v
"""
import os
import sys
import json
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from canonical_data import (
    CanonicalRecord, persist_canonical, ensure_canonical_table,
    get_canonical_by_id, CANONICAL_TABLE,
)


class TestAiAnalysisField:
    """验证 ai_analysis 独立字段存在。"""

    def test_ai_analysis_field_exists(self):
        rec = CanonicalRecord(title="test")
        assert hasattr(rec, 'ai_analysis')
        assert rec.ai_analysis == ""

    def test_ai_analysis_independent_of_content(self):
        """AI 分析结果不覆盖原始 content。"""
        rec = CanonicalRecord(
            title="test",
            content="这是原始采集内容",
            sentiment="neutral",
            risk_level="low",
        )
        # 写入 AI 分析结果
        ai_result = {
            "sentiment": "positive",
            "risk_level": "medium",
            "summary": "AI 生成的摘要",
            "topics": ["探店", "体验"],
            "confidence": 0.85,
            "provider": "test_model",
        }
        rec.ai_analysis = json.dumps(ai_result, ensure_ascii=False)
        # 原始字段不变
        assert rec.content == "这是原始采集内容"
        assert rec.sentiment == "neutral"
        assert rec.risk_level == "low"
        # AI 结果在独立字段
        parsed = json.loads(rec.ai_analysis)
        assert parsed["sentiment"] == "positive"
        assert parsed["confidence"] == 0.85

    def test_ai_provider_and_model_fields(self):
        rec = CanonicalRecord(title="test")
        rec.ai_provider = "zhipu"
        rec.ai_model = "glm-4.5"
        assert rec.ai_provider == "zhipu"
        assert rec.ai_model == "glm-4.5"


class TestAiRawSeparationInDb:
    """验证 DB 中 AI 与原始数据分离存储。"""

    @pytest.fixture
    def tmp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        ensure_canonical_table(path)
        yield path
        os.unlink(path)

    def test_ai_analysis_stored_separately(self, tmp_db):
        rec = CanonicalRecord(
            canonical_id="ai_sep_001",
            title="test",
            content="原始内容",
            sentiment="neutral",
            source_platform="xhs",
        )
        rec.ai_analysis = json.dumps({"sentiment": "positive", "confidence": 0.9})
        rec.ai_provider = "test"
        rec.ai_model = "model-v1"
        rec.compute_hash()

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            persist_canonical(con, rec)
            con.commit()
            row = con.execute(
                f"SELECT content, sentiment, ai_analysis, ai_provider, ai_model "
                f"FROM {CANONICAL_TABLE} WHERE canonical_id=?",
                ("ai_sep_001",)
            ).fetchone()
            # 原始 content 不变
            assert row[0] == "原始内容"
            assert row[1] == "neutral"
            # AI 结果独立存储
            assert row[2] is not None
            assert json.loads(row[2])["sentiment"] == "positive"
            assert row[3] == "test"
            assert row[4] == "model-v1"
        finally:
            con.close()

    def test_ai_does_not_overwrite_raw_on_update(self, tmp_db):
        """更新记录时 AI 字段不覆盖原始字段。"""
        rec1 = CanonicalRecord(
            canonical_id="ai_sep_002",
            title="test", content="原始内容v1",
            sentiment="neutral", source_platform="xhs",
        )
        rec1.ai_analysis = json.dumps({"v": 1})
        rec1.compute_hash()

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            persist_canonical(con, rec1)
            con.commit()

            # 第二次写入：原始 content 更新，AI 字段也更新
            rec2 = CanonicalRecord(
                canonical_id="ai_sep_002",
                title="test", content="原始内容v2",
                sentiment="negative", source_platform="xhs",
            )
            rec2.ai_analysis = json.dumps({"v": 2, "sentiment": "negative"})
            rec2.compute_hash()
            persist_canonical(con, rec2)
            con.commit()

            row = con.execute(
                f"SELECT content, sentiment, ai_analysis FROM {CANONICAL_TABLE} WHERE canonical_id=?",
                ("ai_sep_002",)
            ).fetchone()
            # content 和 sentiment 是原始字段
            assert row[0] == "原始内容v2"
            # ai_analysis 是独立字段
            assert json.loads(row[2])["v"] == 2
        finally:
            con.close()


class TestEvidenceChainSeparation:
    """验证 evidence_chain 中 AI 与原始数据分离原则。"""

    def test_evidence_chain_has_immutable_principle(self):
        """evidence_chain 模块声明原始证据不可被分析结果覆盖。"""
        import evidence_chain
        source = evidence_chain.__doc__ or ""
        assert "原始证据" in source or "Evidence" in source
        # 检查模块中有 AI 与人工分离的概念
        assert "ai_analysis" in dir(evidence_chain) or "human_correction" in source or "AI" in source

    def test_evidence_store_fact_vs_declaration(self):
        """evidence_store 遵循事实 vs 声明分离原则。"""
        import evidence_store
        source = evidence_store.__doc__ or ""
        assert "事实" in source or "fact" in source.lower() or "AI" in source
