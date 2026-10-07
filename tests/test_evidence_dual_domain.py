# -*- coding: utf-8 -*-
"""
Evidence 双域追溯测试（ZBC V2.0）
==================================
覆盖：
  1. 每条证据携带 domain_id/product_id/task_id/trace_id/evidence_id 等
  2. 证据命名空间按域隔离（同表 domain_id 区分）
  3. 查询时默认按当前域过滤
  4. Raw→Normalized→Rule→AI→Evidence→Final→Report 链路 trace_id 关联
  5. 域身份不丢失
"""
import os
import sys
import uuid
import pytest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.shared.evidence.chain import (
    EvidenceStore, CanonicalDataStore, LifecycleTracker, EvidenceChain,
    init_db, list_evidence_by_domain, get_evidence_domain_summary,
)


@pytest.fixture
def temp_db():
    """每个测试使用独立的临时数据库，避免污染生产数据。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


class TestEvidenceDomainFields:
    """验证证据携带域身份字段。"""

    def test_evidence_has_domain_id(self, temp_db):
        store = EvidenceStore(temp_db)
        ev, is_new = store.add_evidence(
            source_type="xhs_note",
            source_url="https://xhslink.com/test1",
            raw_content="测试太古汇内容",
            domain_id="cth",
            product_id="CTH",
            task_id="task_001",
            trace_id="trace_001",
        )
        assert ev.domain_id == "cth"
        assert ev.product_id == "CTH"
        assert ev.task_id == "task_001"
        assert ev.trace_id == "trace_001"
        assert ev.evidence_id.startswith("ev_")

    def test_evidence_has_full_trace_fields(self, temp_db):
        store = EvidenceStore(temp_db)
        ev, _ = store.add_evidence(
            source_type="weibo",
            source_url="https://weibo.com/test",
            raw_content="测试内容",
            domain_id="zbmp",
            product_id="ZBMP",
            task_id="task_002",
            trace_id="trace_002",
            evaluation_id="eval_001",
            final_decision="negative",
            rule_id="rule_sentiment_v1",
            ai_call_id="ai_call_001",
            source_id="wb_12345",
        )
        assert ev.domain_id == "zbmp"
        assert ev.product_id == "ZBMP"
        assert ev.evaluation_id == "eval_001"
        assert ev.final_decision == "negative"
        assert ev.rule_id == "rule_sentiment_v1"
        assert ev.ai_call_id == "ai_call_001"
        assert ev.source_id == "wb_12345"
        assert ev.captured_at  # 非空

    def test_cth_and_zbmp_evidence_coexist(self, temp_db):
        """CTH 和 ZBMP 证据存储在同一表但 domain_id 区分。"""
        store = EvidenceStore(temp_db)
        store.add_evidence(
            source_type="xhs", source_url="url1", raw_content="CTH内容",
            domain_id="cth", product_id="CTH",
        )
        store.add_evidence(
            source_type="xhs", source_url="url2", raw_content="ZBMP内容",
            domain_id="zbmp", product_id="ZBMP",
        )
        assert store.count() == 2

    def test_list_evidence_by_domain_filter(self, temp_db):
        """按域查询只返回对应域的证据。"""
        store = EvidenceStore(temp_db)
        store.add_evidence(
            source_type="xhs", source_url="url_cth", raw_content="CTH",
            domain_id="cth", product_id="CTH",
        )
        store.add_evidence(
            source_type="xhs", source_url="url_zbmp", raw_content="ZBMP",
            domain_id="zbmp", product_id="ZBMP",
        )
        cth_evidence = store.list_evidence(domain_id="cth")
        zbmp_evidence = store.list_evidence(domain_id="zbmp")
        assert len(cth_evidence) == 1
        assert len(zbmp_evidence) == 1
        assert cth_evidence[0].domain_id == "cth"
        assert zbmp_evidence[0].domain_id == "zbmp"


class TestEvidenceChainDomainTraceability:
    """验证端到端证据链的域身份追溯。"""

    def test_capture_and_canonicalize_domain(self, temp_db):
        chain = EvidenceChain(temp_db)
        result = chain.capture_and_canonicalize(
            source_type="xhs_note",
            source_url="https://xhslink.com/test",
            raw_content="太古汇探店内容",
            normalized_content="太古汇探店",
            subject_hit=True,
            sentiment="positive",
            risk_level="low",
            domain_id="cth",
            product_id="CTH",
            task_id="task_003",
            trace_id="trace_003",
            evaluation_id="eval_003",
            final_decision="approved",
            rule_id="rule_v1",
            ai_call_id="ai_003",
        )
        ev = result["evidence"]
        assert ev.domain_id == "cth"
        assert ev.product_id == "CTH"
        assert ev.task_id == "task_003"
        assert ev.trace_id == "trace_003"
        assert result["task_id"] == "task_003"
        assert result["trace_id"] == "trace_003"
        assert result["evaluation_id"] == "eval_003"
        assert len(result["tracking_ids"]) >= 2  # EVIDENCE + CANONICAL_DATA

    def test_lifecycle_tracking_preserves_trace_id(self, temp_db):
        """生命周期追踪中 trace_id 关联不丢失。"""
        chain = EvidenceChain(temp_db)
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        result = chain.capture_and_canonicalize(
            source_type="xhs", source_url="url", raw_content="test",
            domain_id="cth", product_id="CTH",
            task_id="task_x", trace_id=trace_id,
        )
        lineage = chain.trace_lineage(result["evidence"].evidence_id)
        assert lineage["evidence_id"] == result["evidence"].evidence_id
        # 生命周期阶段中应包含 trace_id
        for stage in lineage["lifecycle_stages"]:
            assert stage["trace_id"] == trace_id

    def test_zbmp_evidence_chain(self, temp_db):
        chain = EvidenceChain(temp_db)
        result = chain.capture_and_canonicalize(
            source_type="weibo", source_url="url_zbmp", raw_content="品牌分析",
            domain_id="zbmp", product_id="ZBMP",
            task_id="task_zbmp", trace_id="trace_zbmp",
        )
        assert result["evidence"].domain_id == "zbmp"
        assert result["evidence"].product_id == "ZBMP"


class TestEvidenceDomainQuery:
    """验证域查询便捷函数。"""

    def test_list_evidence_by_domain(self, temp_db):
        store = EvidenceStore(temp_db)
        store.add_evidence(
            source_type="xhs", source_url="u1", raw_content="c1",
            domain_id="cth", product_id="CTH",
        )
        store.add_evidence(
            source_type="xhs", source_url="u2", raw_content="c2",
            domain_id="zbmp", product_id="ZBMP",
        )
        cth_list = list_evidence_by_domain(temp_db, domain_id="cth")
        assert len(cth_list) == 1
        assert cth_list[0]["domain_id"] == "cth"

    def test_get_evidence_domain_summary(self, temp_db):
        store = EvidenceStore(temp_db)
        store.add_evidence(
            source_type="xhs", source_url="u1", raw_content="c1",
            domain_id="cth", product_id="CTH",
        )
        store.add_evidence(
            source_type="xhs", source_url="u2", raw_content="c2",
            domain_id="cth", product_id="CTH",
        )
        store.add_evidence(
            source_type="xhs", source_url="u3", raw_content="c3",
            domain_id="zbmp", product_id="ZBMP",
        )
        summary = get_evidence_domain_summary(temp_db)
        assert summary["total"] == 3
        assert "cth" in summary["domains_present"]
        assert "zbmp" in summary["domains_present"]
        by_domain = {d["domain_id"]: d["cnt"] for d in summary["by_domain"]}
        assert by_domain.get("cth") == 2
        assert by_domain.get("zbmp") == 1


class TestEvidenceImmutability:
    """验证证据不可变性在双域下仍生效。"""

    def test_immutable_fields_listed(self):
        assert "domain_id" in EvidenceStore.IMMUTABLE_FIELDS
        assert "product_id" in EvidenceStore.IMMUTABLE_FIELDS
        assert "raw_content" in EvidenceStore.IMMUTABLE_FIELDS
        assert "content_hash" in EvidenceStore.IMMUTABLE_FIELDS

    def test_hash_dedup_works_per_domain(self, temp_db):
        """相同内容在同一域去重。"""
        store = EvidenceStore(temp_db)
        ev1, new1 = store.add_evidence(
            source_type="xhs", source_url="url", raw_content="重复内容",
            domain_id="cth", product_id="CTH",
        )
        ev2, new2 = store.add_evidence(
            source_type="xhs", source_url="url2", raw_content="重复内容",
            domain_id="cth", product_id="CTH",
        )
        assert new1 is True
        assert new2 is False
        assert ev1.evidence_id == ev2.evidence_id

    def test_identical_content_does_not_dedupe_across_domain_or_scope(self, temp_db):
        store = EvidenceStore(temp_db)
        cth, cth_new = store.add_evidence(
            source_type="web", source_url="same-url", raw_content="same text",
            domain_id="cth", product_id="CTH", subject_scope="GLOBAL / ALL",
        )
        bmp, bmp_new = store.add_evidence(
            source_type="web", source_url="same-url", raw_content="same text",
            domain_id="zbmp", product_id="BMP", subject_scope="GLOBAL / ALL",
        )
        focused, focused_new = store.add_evidence(
            source_type="web", source_url="same-url", raw_content="same text",
            domain_id="cth", product_id="CTH", subject_scope="SUBJECT-1",
        )

        assert cth_new and bmp_new and focused_new
        assert cth.evidence_id != bmp.evidence_id
        assert cth.evidence_id != focused.evidence_id
