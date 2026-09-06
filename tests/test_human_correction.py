# -*- coding: utf-8 -*-
"""
人工修正可追溯测试（P0 红线）
================================
验证：
1. human_corrections 表存在且结构完整
2. 修正记录包含：修正前原始值、修正后新值、修正人、修正时间、修正原因
3. 不直接覆盖原始字段
4. 修正可查询、可撤销
5. apply_corrections_to_record 返回修正视图，不修改原始记录

运行: .venv\\Scripts\\python.exe -m pytest tests/test_human_correction.py -v
"""
import os
import sys
import json
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from human_correction import (
    record_correction, get_corrections, revert_correction,
    apply_corrections_to_record, ensure_correction_table,
    CORRECTION_TABLE,
)


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    ensure_correction_table(path)
    yield path
    os.unlink(path)


class TestRecordCorrection:
    """验证修正记录。"""

    def test_record_basic_correction(self, tmp_db):
        result = record_correction(
            tmp_db,
            field_name="sentiment",
            original_value="neutral",
            corrected_value="negative",
            corrected_by="admin",
            correction_reason="人工复核确认为负面",
            canonical_id="can_test_001",
        )
        assert result["correction_id"] is not None
        assert result["field_name"] == "sentiment"
        assert result["original_value"] == "neutral"
        assert result["corrected_value"] == "negative"
        assert result["corrected_by"] == "admin"
        assert result["correction_reason"] == "人工复核确认为负面"
        assert result["correction_time"] is not None
        assert result["status"] == "active"

    def test_record_requires_field_name(self, tmp_db):
        with pytest.raises(ValueError, match="field_name"):
            record_correction(tmp_db, field_name="", original_value="a",
                              corrected_value="b", corrected_by="admin")

    def test_record_requires_corrected_by(self, tmp_db):
        with pytest.raises(ValueError, match="corrected_by"):
            record_correction(tmp_db, field_name="sentiment", original_value="a",
                              corrected_value="b", corrected_by="")

    def test_record_with_source_id(self, tmp_db):
        result = record_correction(
            tmp_db,
            field_name="risk_level",
            original_value="low",
            corrected_value="high",
            corrected_by="reviewer1",
            correction_reason="涉及投诉",
            source_id="note_123",
            source_table="notes",
        )
        assert result["source_id"] == "note_123"
        assert result["source_table"] == "notes"

    def test_record_complex_values(self, tmp_db):
        """修正值可以是复杂类型（dict/list）。"""
        original = {"topics": ["a", "b"], "score": 0.5}
        corrected = {"topics": ["a", "b", "c"], "score": 0.8}
        result = record_correction(
            tmp_db, field_name="topics",
            original_value=original, corrected_value=corrected,
            corrected_by="admin", canonical_id="can_complex_001",
        )
        assert result["original_value"] == original
        assert result["corrected_value"] == corrected


class TestGetCorrections:
    """验证修正查询。"""

    def test_query_by_canonical_id(self, tmp_db):
        record_correction(tmp_db, field_name="sentiment", original_value="neutral",
                          corrected_value="negative", corrected_by="admin",
                          canonical_id="can_query_001")
        record_correction(tmp_db, field_name="risk_level", original_value="low",
                          corrected_value="medium", corrected_by="admin",
                          canonical_id="can_query_001")
        corrections = get_corrections(tmp_db, canonical_id="can_query_001")
        assert len(corrections) == 2
        fields = {c["field_name"] for c in corrections}
        assert "sentiment" in fields
        assert "risk_level" in fields

    def test_query_by_field_name(self, tmp_db):
        record_correction(tmp_db, field_name="sentiment", original_value="a",
                          corrected_value="b", corrected_by="admin",
                          canonical_id="c1")
        record_correction(tmp_db, field_name="risk_level", original_value="c",
                          corrected_value="d", corrected_by="admin",
                          canonical_id="c1")
        sent_corrections = get_corrections(tmp_db, field_name="sentiment")
        assert len(sent_corrections) == 1
        assert sent_corrections[0]["field_name"] == "sentiment"

    def test_active_only_filter(self, tmp_db):
        record_correction(tmp_db, field_name="sentiment", original_value="a",
                          corrected_value="b", corrected_by="admin", canonical_id="c1")
        # 默认只返回 active
        all_c = get_corrections(tmp_db, canonical_id="c1", active_only=True)
        assert len(all_c) == 1
        assert all_c[0]["status"] == "active"


class TestRevertCorrection:
    """验证修正撤销。"""

    def test_revert_correction(self, tmp_db):
        result = record_correction(tmp_db, field_name="sentiment", original_value="a",
                                   corrected_value="b", corrected_by="admin", canonical_id="c1")
        cid = result["correction_id"]
        revert_result = revert_correction(tmp_db, cid, "admin2", "修正有误")
        assert revert_result["status"] == "reverted"
        assert revert_result["reverted_by"] == "admin2"

        # 查询时 active_only 不返回已撤销的
        active = get_corrections(tmp_db, canonical_id="c1", active_only=True)
        assert len(active) == 0
        # 全部查询可以看到
        all_c = get_corrections(tmp_db, canonical_id="c1", active_only=False)
        assert len(all_c) == 1
        assert all_c[0]["status"] == "reverted"


class TestApplyCorrections:
    """验证 apply_corrections_to_record 不修改原始记录。"""

    def test_apply_returns_new_dict(self, tmp_db):
        record_correction(
            tmp_db, field_name="sentiment",
            original_value="neutral", corrected_value="negative",
            corrected_by="admin", canonical_id="can_apply_001",
        )
        original = {"canonical_id": "can_apply_001", "sentiment": "neutral",
                    "content": "原始内容"}
        corrected = apply_corrections_to_record(tmp_db, original)
        # 原始 dict 不变
        assert original["sentiment"] == "neutral"
        # 返回的 dict 有修正后的值
        assert corrected["sentiment"] == "negative"
        assert corrected["content"] == "原始内容"
        # 有修正元数据
        assert "_correction_sentiment" in corrected
        assert corrected["_correction_sentiment"]["original"] == "neutral"
        assert corrected["_correction_sentiment"]["corrected_by"] == "admin"

    def test_no_corrections_returns_copy(self, tmp_db):
        original = {"canonical_id": "no_corr", "sentiment": "neutral"}
        result = apply_corrections_to_record(tmp_db, original)
        assert result == original
        assert result is not original  # 是副本


class TestCorrectionTableSchema:
    """验证表结构完整。"""

    def test_table_has_required_columns(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        try:
            columns = {row[1] for row in con.execute(f"PRAGMA table_info({CORRECTION_TABLE})").fetchall()}
            required = {"correction_id", "canonical_id", "source_id", "field_name",
                        "original_value", "corrected_value", "corrected_by",
                        "correction_reason", "correction_time", "status"}
            assert required.issubset(columns), f"缺少列: {required - columns}"
        finally:
            con.close()

    def test_original_value_preserved(self, tmp_db):
        """修正前原始值必须完整保存。"""
        record_correction(
            tmp_db, field_name="title",
            original_value="原始标题很长很重要",
            corrected_value="修正后的标题",
            corrected_by="admin", canonical_id="c1",
        )
        corrections = get_corrections(tmp_db, canonical_id="c1")
        assert corrections[0]["original_value"] == "原始标题很长很重要"
