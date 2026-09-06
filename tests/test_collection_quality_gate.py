# -*- coding: utf-8 -*-
"""
采集五步质量门禁测试（P0 红线）
==================================
验证：Source→Raw→Dedup→Subject Filter→Canonical 五步校验
1. 每步输入校验→处理→输出校验→失败记录
2. 失败不静默丢弃，记录状态+原因+原始数据引用
3. 质量日志可查询

运行: .venv\\Scripts\\python.exe -m pytest tests/test_collection_quality_gate.py -v
"""
import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from collection_quality_gate import (
    CollectionQualityGate, GateResult, CollectionGateResult,
    ensure_quality_log_table, get_quality_logs,
    QUALITY_LOG_TABLE, STEP_SOURCE, STEP_RAW, STEP_DEDUP,
    STEP_SUBJECT, STEP_CANONICAL, VALID_PLATFORMS,
)
from canonical_data import CanonicalRecord, ensure_canonical_table


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    ensure_quality_log_table(path)
    ensure_canonical_table(path)
    yield path
    os.unlink(path)


class TestSourceValidation:
    """Step 1: Source 校验。"""

    def test_valid_source_passes(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r = gate.validate_source({}, "xiaohongshu", "http://example.com",
                                 {"author_id": "u1", "author_name": "test"})
        assert r.passed is True

    def test_empty_url_fails(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r = gate.validate_source({}, "xiaohongshu", "", {"author_id": "u1"})
        assert r.passed is False
        assert "URL" in r.reason

    def test_invalid_platform_fails(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r = gate.validate_source({}, "unknown_platform", "http://x.com", {"author_id": "u1"})
        assert r.passed is False
        assert "非法平台" in r.reason

    def test_missing_author_fails(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r = gate.validate_source({}, "xiaohongshu", "http://x.com", {})
        assert r.passed is False
        assert "账号" in r.reason


class TestRawValidation:
    """Step 2: Raw 校验。"""

    def test_valid_raw_passes(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r, ch = gate.validate_raw({"title": "test", "content": "content"})
        assert r.passed is True
        assert ch != ""

    def test_empty_title_and_content_fails(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r, ch = gate.validate_raw({"title": "", "content": ""})
        assert r.passed is False
        assert ch == ""

    def test_content_only_passes(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r, ch = gate.validate_raw({"title": "", "content": "some content"})
        assert r.passed is True
        assert ch != ""

    def test_title_only_passes(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r, ch = gate.validate_raw({"title": "some title", "content": ""})
        assert r.passed is True


class TestDedupValidation:
    """Step 3: Dedup 校验。"""

    def test_new_content_not_duplicate(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        con = sqlite3.connect(tmp_db)
        try:
            r, decision = gate.validate_dedup(con, "hash123", "xiaohongshu")
            assert r.passed is True
            assert decision == "new"
        finally:
            con.close()

    def test_empty_hash_fails(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        con = sqlite3.connect(tmp_db)
        try:
            r, decision = gate.validate_dedup(con, "", "xiaohongshu")
            assert r.passed is False
            assert decision == "error"
        finally:
            con.close()


class TestSubjectValidation:
    """Step 4: Subject Filter 校验。"""

    def test_subject_hit(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r, decision = gate.validate_subject({
            "title": "广州太古汇探店体验",
            "content": "今天去了太古汇",
            "source_keyword": "太古汇",
        })
        assert r.passed is True
        assert decision in ("hit", "miss")

    def test_subject_miss(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        r, decision = gate.validate_subject({
            "title": "今天天气真好",
            "content": "出去散步",
            "source_keyword": "",
        })
        assert r.passed is True  # miss 不阻断，仅标记


class TestCanonicalValidation:
    """Step 5: Canonical 校验。"""

    def test_valid_record_passes(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        rec = CanonicalRecord(
            canonical_id="can_test_001",
            title="test", content="content",
            source_platform="xiaohongshu",
        )
        rec.compute_hash()
        r = gate.validate_canonical(rec)
        assert r.passed is True

    def test_missing_canonical_id_fails(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        rec = CanonicalRecord(title="test", source_platform="xhs")
        rec.canonical_id = ""
        r = gate.validate_canonical(rec)
        assert r.passed is False
        assert "canonical_id" in r.reason


class TestFullPipeline:
    """完整五步门禁测试。"""

    def test_full_pipeline_pass(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        rec = CanonicalRecord(
            canonical_id="can_full_001",
            title="广州太古汇探店",
            content="今天去太古汇体验很好",
            source_platform="xiaohongshu",
            url="http://example.com/1",
        )
        rec.compute_hash()
        raw = {"title": "广州太古汇探店", "content": "今天去太古汇体验很好",
               "url": "http://example.com/1", "source_keyword": "太古汇"}
        result = gate.validate(
            raw, "xiaohongshu", "http://example.com/1",
            {"author_id": "u1", "author_name": "test"},
            canonical_record=rec,
        )
        assert result.passed is True
        assert len(result.results) == 5
        assert result.content_hash != ""
        assert result.dedup_decision == "new"

    def test_full_pipeline_fail_at_source(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        result = gate.validate(
            {"title": "test"}, "xiaohongshu", "",
            {"author_id": "u1"},
        )
        assert result.passed is False
        assert result.failed_step == STEP_SOURCE
        assert len(result.results) == 1  # 只执行到第一步

    def test_failure_logged(self, tmp_db):
        """失败必须记录到日志表。"""
        gate = CollectionQualityGate(tmp_db)
        gate.validate(
            {"title": "test"}, "xiaohongshu", "",
            {"author_id": "u1"},
        )
        logs = get_quality_logs(tmp_db, step=STEP_SOURCE)
        assert len(logs) >= 1
        fail_logs = [l for l in logs if l["status"] == "fail"]
        assert len(fail_logs) >= 1
        assert "URL" in fail_logs[0]["reason"]

    def test_all_steps_logged_on_success(self, tmp_db):
        """成功时五步都有日志记录。"""
        gate = CollectionQualityGate(tmp_db)
        rec = CanonicalRecord(
            canonical_id="can_log_001",
            title="test", content="content",
            source_platform="xiaohongshu", url="http://x.com/1",
        )
        rec.compute_hash()
        gate.validate(
            {"title": "test", "content": "content", "url": "http://x.com/1"},
            "xiaohongshu", "http://x.com/1",
            {"author_id": "u1"},
            canonical_record=rec,
        )
        logs = get_quality_logs(tmp_db, run_id=gate.run_id)
        steps_logged = {l["step"] for l in logs}
        assert STEP_SOURCE in steps_logged
        assert STEP_RAW in steps_logged
        assert STEP_DEDUP in steps_logged
        assert STEP_SUBJECT in steps_logged
        assert STEP_CANONICAL in steps_logged

    def test_result_to_dict(self, tmp_db):
        gate = CollectionQualityGate(tmp_db)
        rec = CanonicalRecord(
            canonical_id="can_dict_001",
            title="test", content="content",
            source_platform="xhs", url="http://x.com/1",
        )
        rec.compute_hash()
        result = gate.validate(
            {"title": "test", "content": "content"},
            "xhs", "http://x.com/1", {"author_id": "u1"},
            canonical_record=rec,
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert len(d["steps"]) == 5
