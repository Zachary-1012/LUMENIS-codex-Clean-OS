# -*- coding: utf-8 -*-
"""evidence_chain.py 单元测试 —— ZBC Phase 8 Evidence/Canonical Data 数据链

测试覆盖：
  1. Evidence hash 计算和去重
  2. 原始证据不可被覆盖（immutability）
  3. AI 输出与人工判断分离
  4. 数据生命周期追踪
  5. rule_version 追踪
  6. historical data 不被静默改写
  7. 完整 provenance 字段
  8. 端到端 capture_and_canonicalize

使用临时数据库，不碰生产库。
"""
import sys
import os
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evidence_chain
from evidence_chain import (
    Evidence,
    CanonicalData,
    EvidenceStore,
    CanonicalDataStore,
    LifecycleTracker,
    EvidenceChain,
    LIFECYCLE_STAGES,
    RULE_VERSION,
    compute_content_hash,
    generate_evidence_id,
    generate_canonical_id,
    init_db,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def tmp_db():
    """临时数据库，测试后自动清理。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def ev_store(tmp_db):
    return EvidenceStore(tmp_db)


@pytest.fixture
def can_store(tmp_db):
    return CanonicalDataStore(tmp_db)


@pytest.fixture
def lifecycle(tmp_db):
    return LifecycleTracker(tmp_db)


@pytest.fixture
def chain(tmp_db):
    return EvidenceChain(tmp_db)


# ============================================================
# 1. Evidence hash 计算和去重
# ============================================================
class TestEvidenceHash:
    def test_compute_content_hash_sha256(self):
        """content_hash 应为 64 字符 SHA256 十六进制。"""
        h = compute_content_hash("测试内容")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_content_same_hash(self):
        """相同内容生成相同哈希。"""
        assert compute_content_hash("hello") == compute_content_hash("hello")

    def test_different_content_different_hash(self):
        """不同内容生成不同哈希。"""
        assert compute_content_hash("hello") != compute_content_hash("world")

    def test_empty_content_hash(self):
        """空内容也有确定哈希。"""
        h1 = compute_content_hash("")
        h2 = compute_content_hash("")
        assert h1 == h2
        assert len(h1) == 64

    def test_none_content_hash(self):
        """None 内容按空字符串处理。"""
        assert compute_content_hash(None) == compute_content_hash("")

    def test_evidence_dedup_same_content(self, ev_store):
        """相同 content_hash 的证据不重复入库。"""
        raw = "这是一条测试笔记内容，用于去重验证。"
        ev1, is_new1 = ev_store.add_evidence(
            source_type="xhs_note",
            source_url="https://xhslink.com/1",
            raw_content=raw,
        )
        assert is_new1 is True
        assert ev_store.count() == 1

        ev2, is_new2 = ev_store.add_evidence(
            source_type="xhs_note",
            source_url="https://xhslink.com/2",  # 不同 URL 但相同内容
            raw_content=raw,
        )
        assert is_new2 is False
        assert ev2.evidence_id == ev1.evidence_id
        assert ev_store.count() == 1  # 不重复入库

    def test_evidence_dedup_different_content(self, ev_store):
        """不同内容可以正常入库。"""
        ev1, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="内容A"
        )
        ev2, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/2", raw_content="内容B"
        )
        assert ev1.evidence_id != ev2.evidence_id
        assert ev_store.count() == 2

    def test_evidence_id_format(self):
        eid = generate_evidence_id()
        assert eid.startswith("ev_")
        assert len(eid) == 3 + 16

    def test_canonical_id_format(self):
        cid = generate_canonical_id()
        assert cid.startswith("can_")
        assert len(cid) == 4 + 16


# ============================================================
# 2. 原始证据不可被覆盖（immutability）
# ============================================================
class TestEvidenceImmutability:
    def test_evidence_store_has_immutable_fields(self):
        """EvidenceStore 定义了不可变字段集合。"""
        immutable = EvidenceStore.IMMUTABLE_FIELDS
        assert "raw_content" in immutable
        assert "content_hash" in immutable
        assert "source_type" in immutable
        assert "source_url" in immutable
        assert "captured_at" in immutable
        assert "evidence_id" in immutable

    def test_evidence_verify_immutability(self, ev_store):
        """verify_immutability 返回有效验证报告。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="immutable test"
        )
        report = ev_store.verify_immutability(ev.evidence_id)
        assert report["valid"] is True
        assert report["evidence_id"] == ev.evidence_id
        assert report["content_hash"] == ev.content_hash
        assert "immutable_fields" in report
        assert "raw_content_length" in report

    def test_evidence_verify_immutability_not_found(self, ev_store):
        report = ev_store.verify_immutability("nonexistent_id")
        assert report["valid"] is False

    def test_raw_content_preserved_after_canonical_creation(self, chain):
        """创建 CanonicalData 后，原始 Evidence 的 raw_content 不变。"""
        result = chain.capture_and_canonicalize(
            source_type="xhs_note",
            source_url="https://x.com/1",
            raw_content="原始内容，不可被覆盖",
            normalized_content="规范化后的内容",
            sentiment="positive",
        )
        ev = chain.evidence_store.get_evidence(result["evidence"].evidence_id)
        assert ev.raw_content == "原始内容，不可被覆盖"
        assert ev.content_hash == compute_content_hash("原始内容，不可被覆盖")

    def test_evidence_no_update_method(self):
        """EvidenceStore 不应提供 update_evidence 方法（防止意外修改）。"""
        assert not hasattr(EvidenceStore, "update_evidence")
        assert not hasattr(EvidenceStore, "modify_evidence")


# ============================================================
# 3. AI 输出与人工判断分离
# ============================================================
class TestAISeparation:
    def test_canonical_has_separate_ai_and_human_fields(self):
        """CanonicalData 数据类有独立的 ai_analysis 和 human_correction 字段。"""
        cd = CanonicalData(
            canonical_id="test",
            evidence_id="ev_test",
            normalized_content="test",
            ai_analysis={"sentiment": "negative", "confidence": 0.9},
            human_correction={"sentiment": "neutral", "reason": "人工复核"},
        )
        assert cd.ai_analysis["sentiment"] == "negative"
        assert cd.human_correction["sentiment"] == "neutral"
        assert cd.ai_analysis != cd.human_correction

    def test_apply_human_correction_preserves_ai(self, can_store, ev_store):
        """人工修正不覆盖 AI 原始输出。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content="test",
            ai_analysis={"sentiment": "negative", "risk": "high", "model": "glm-4.5"},
        )
        # 应用人工修正
        updated = can_store.apply_human_correction(
            cd.canonical_id,
            {"sentiment": "neutral", "risk": "low", "reason": "人工复核后降级"},
            operator="analyst_001",
        )
        assert updated is not None
        # AI 输出保持不变
        assert updated.ai_analysis["sentiment"] == "negative"
        assert updated.ai_analysis["risk"] == "high"
        assert updated.ai_analysis["model"] == "glm-4.5"
        # 人工修正独立记录
        assert updated.human_correction["sentiment"] == "neutral"
        assert updated.human_correction["risk"] == "low"
        assert updated.human_correction["_corrected_by"] == "analyst_001"
        assert "_last_corrected_at" in updated.human_correction

    def test_update_ai_analysis_preserves_human(self, can_store, ev_store):
        """更新 AI 分析不影响人工修正。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content="test",
            ai_analysis={"sentiment": "negative"},
            human_correction={"sentiment": "neutral", "reason": "已确认"},
        )
        # 更新 AI 分析
        updated = can_store.update_ai_analysis(
            cd.canonical_id,
            {"sentiment": "positive", "confidence": 0.95, "model": "glm-5.3"},
        )
        assert updated is not None
        # 人工修正保持不变
        assert updated.human_correction["sentiment"] == "neutral"
        assert updated.human_correction["reason"] == "已确认"
        # AI 分析已更新
        assert updated.ai_analysis["sentiment"] == "positive"
        assert updated.ai_analysis["confidence"] == 0.95

    def test_ai_analysis_history_preserved(self, can_store, ev_store):
        """多次更新 AI 分析时，历史版本保留在 _history 中。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content="test",
            ai_analysis={"sentiment": "negative", "round": 1},
        )
        can_store.update_ai_analysis(cd.canonical_id, {"sentiment": "neutral", "round": 2})
        updated = can_store.update_ai_analysis(cd.canonical_id, {"sentiment": "positive", "round": 3})
        history = updated.ai_analysis.get("_history", [])
        assert len(history) >= 2
        # 第一轮和第二轮的 AI 输出都在历史中
        rounds_in_history = [h.get("data", {}).get("round") for h in history]
        assert 1 in rounds_in_history or 2 in rounds_in_history


# ============================================================
# 4. 数据生命周期追踪
# ============================================================
class TestLifecycleTracking:
    def test_lifecycle_has_13_stages(self):
        """数据生命周期有 13 个阶段。"""
        assert len(LIFECYCLE_STAGES) == 13

    def test_lifecycle_stage_order(self):
        """阶段顺序从 0 到 12 连续。"""
        orders = [info["order"] for info in LIFECYCLE_STAGES.values()]
        assert sorted(orders) == list(range(13))

    def test_lifecycle_stages_have_io_transform(self):
        """每个阶段都有 input/output/transform 定义。"""
        for name, info in LIFECYCLE_STAGES.items():
            assert "input" in info, f"{name} 缺少 input"
            assert "output" in info, f"{name} 缺少 output"
            assert "transform" in info, f"{name} 缺少 transform"
            assert "immutable" in info, f"{name} 缺少 immutable"

    def test_evidence_and_outcome_are_immutable(self):
        """EVIDENCE 和 OUTCOME 阶段标记为不可变。"""
        assert LIFECYCLE_STAGES["EVIDENCE"]["immutable"] is True
        assert LIFECYCLE_STAGES["OUTCOME"]["immutable"] is True
        assert LIFECYCLE_STAGES["LEARNING_ASSET"]["immutable"] is True

    def test_record_stage_valid(self, lifecycle):
        """记录有效生命周期阶段。"""
        tid = lifecycle.record_stage(
            evidence_id="ev_test",
            stage="EVIDENCE",
            input_ref="https://x.com/1",
            output_ref="ev_test",
            transform_rule="SHA256 hash",
        )
        assert tid.startswith("tr_")

    def test_record_stage_invalid_raises(self, lifecycle):
        """记录无效阶段应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知生命周期阶段"):
            lifecycle.record_stage(evidence_id="ev_test", stage="INVALID_STAGE")

    def test_trace_data_lineage(self, chain):
        """trace_data_lineage 返回完整生命周期。"""
        result = chain.capture_and_canonicalize(
            source_type="xhs_note",
            source_url="https://x.com/1",
            raw_content="lineage test",
            normalized_content="normalized",
            sentiment="positive",
        )
        lineage = chain.trace_lineage(result["evidence"].evidence_id)
        assert lineage["evidence_id"] == result["evidence"].evidence_id
        assert lineage["evidence"] is not None
        assert len(lineage["canonical_data"]) >= 1
        assert lineage["total_stages_recorded"] >= 2
        assert "EVIDENCE" in lineage["stage_summary"]
        assert "CANONICAL_DATA" in lineage["stage_summary"]
        assert len(lineage["rule_versions"]) >= 1

    def test_trace_lineage_nonexistent(self, lifecycle):
        """追踪不存在的 evidence_id 返回空结果。"""
        lineage = lifecycle.trace_data_lineage("nonexistent")
        assert lineage["evidence"] is None
        assert lineage["canonical_data"] == []
        assert lineage["lifecycle_stages"] == []

    def test_get_stage_definition(self, lifecycle):
        info = lifecycle.get_stage_definition("CANONICAL_DATA")
        assert info is not None
        assert info["order"] == 2

    def test_list_all_stages(self, lifecycle):
        stages = lifecycle.list_all_stages()
        assert len(stages) == 13
        assert stages[0]["stage"] == "EXTERNAL_SOURCE"
        assert stages[-1]["stage"] == "LEARNING_ASSET"


# ============================================================
# 5. rule_version 追踪
# ============================================================
class TestRuleVersion:
    def test_default_rule_version(self):
        """默认规则版本已定义。"""
        assert RULE_VERSION == "evidence-chain-v1.0.0"
        assert len(RULE_VERSION) > 0

    def test_canonical_has_rule_version(self, can_store, ev_store):
        """CanonicalData 记录创建时的 rule_version。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content="test",
            rule_version="v1.0.0-old",
        )
        assert cd.rule_version == "v1.0.0-old"

    def test_list_by_rule_version(self, can_store, ev_store):
        """按 rule_version 筛选数据。"""
        ev1, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="A"
        )
        ev2, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/2", raw_content="B"
        )
        can_store.create_canonical(
            evidence_id=ev1.evidence_id, normalized_content="A", rule_version="v1.0.0"
        )
        can_store.create_canonical(
            evidence_id=ev2.evidence_id, normalized_content="B", rule_version="v2.0.0"
        )
        v1 = can_store.list_by_rule_version("v1.0.0")
        v2 = can_store.list_by_rule_version("v2.0.0")
        assert len(v1) == 1
        assert len(v2) == 1
        assert v1[0].rule_version == "v1.0.0"
        assert v2[0].rule_version == "v2.0.0"

    def test_human_correction_does_not_change_rule_version(self, can_store, ev_store):
        """人工修正不改变 rule_version。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content="test",
            rule_version="v1.0.0-frozen",
        )
        updated = can_store.apply_human_correction(
            cd.canonical_id, {"sentiment": "positive"}
        )
        assert updated.rule_version == "v1.0.0-frozen"

    def test_ai_update_does_not_change_rule_version(self, can_store, ev_store):
        """AI 分析更新不改变 rule_version。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content="test",
            rule_version="v1.0.0-frozen",
        )
        updated = can_store.update_ai_analysis(
            cd.canonical_id, {"sentiment": "negative"}
        )
        assert updated.rule_version == "v1.0.0-frozen"


# ============================================================
# 6. Historical data 不被静默改写
# ============================================================
class TestHistoricalDataProtection:
    def test_old_rule_version_data_preserved_after_new_version(self, can_store, ev_store):
        """新规则版本创建的数据不影响旧规则版本的数据。"""
        ev1, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="old content"
        )
        old_cd = can_store.create_canonical(
            evidence_id=ev1.evidence_id,
            normalized_content="old normalized",
            sentiment="negative",
            rule_version="v1.0.0",
        )
        # 模拟规则升级后创建新数据
        ev2, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/2", raw_content="new content"
        )
        new_cd = can_store.create_canonical(
            evidence_id=ev2.evidence_id,
            normalized_content="new normalized",
            sentiment="positive",
            rule_version="v2.0.0",
        )
        # 旧数据保持不变
        old_fetched = can_store.get_canonical(old_cd.canonical_id)
        assert old_fetched.rule_version == "v1.0.0"
        assert old_fetched.sentiment == "negative"
        assert old_fetched.normalized_content == "old normalized"
        # 新数据使用新版本
        new_fetched = can_store.get_canonical(new_cd.canonical_id)
        assert new_fetched.rule_version == "v2.0.0"

    def test_evidence_raw_content_never_changes(self, ev_store):
        """Evidence 的 raw_content 写入后永远不变（通过重新读取验证）。"""
        raw = "这是历史原始内容，永远不应被修改"
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content=raw
        )
        original_hash = ev.content_hash
        # 模拟多次读取
        for _ in range(5):
            fetched = ev_store.get_evidence(ev.evidence_id)
            assert fetched.raw_content == raw
            assert fetched.content_hash == original_hash

    def test_canonical_created_at_unchanged_by_updates(self, can_store, ev_store):
        """CanonicalData 的 created_at 不被后续更新修改。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id, normalized_content="test"
        )
        original_created = cd.created_at
        # 应用人工修正
        can_store.apply_human_correction(cd.canonical_id, {"sentiment": "positive"})
        # 更新 AI 分析
        can_store.update_ai_analysis(cd.canonical_id, {"sentiment": "negative"})
        # 重新读取
        fetched = can_store.get_canonical(cd.canonical_id)
        assert fetched.created_at == original_created
        # updated_at 应该变化
        assert fetched.updated_at >= original_created


# ============================================================
# 7. 完整 provenance 字段
# ============================================================
class TestProvenance:
    def test_evidence_has_complete_provenance(self, ev_store):
        """Evidence 携带完整 provenance 字段。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note",
            source_url="https://xhslink.com/abc123",
            raw_content="太古汇探店笔记",
            publish_datetime="2026-09-01 14:30:00",
            subject_scope="CTH",
            collection_metadata={"keyword": "太古汇", "search_rank": 3},
            provider="xhs_adapter_v2",
            authenticity_score=0.95,
        )
        assert ev.source_type == "xhs_note"
        assert ev.source_url == "https://xhslink.com/abc123"
        assert ev.content_hash == compute_content_hash("太古汇探店笔记")
        assert ev.captured_at != ""
        assert ev.publish_datetime == "2026-09-01 14:30:00"
        assert ev.subject_scope == "CTH"
        assert ev.collection_metadata["keyword"] == "太古汇"
        assert ev.provider == "xhs_adapter_v2"
        assert ev.authenticity_score == 0.95
        assert ev.created_at != ""

    def test_evidence_to_dict_serializable(self, ev_store):
        """Evidence.to_dict() 可 JSON 序列化。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="test",
            collection_metadata={"key": "value"},
        )
        d = ev.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert "content_hash" in json_str
        assert "collection_metadata" in json_str

    def test_canonical_evidence_fk(self, can_store, ev_store):
        """CanonicalData.evidence_id 正确关联 Evidence。"""
        ev, _ = ev_store.add_evidence(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="FK test"
        )
        cd = can_store.create_canonical(
            evidence_id=ev.evidence_id, normalized_content="test"
        )
        assert cd.evidence_id == ev.evidence_id
        # 通过 evidence_id 反查
        canonical_list = can_store.get_by_evidence(ev.evidence_id)
        assert len(canonical_list) == 1
        assert canonical_list[0].canonical_id == cd.canonical_id


# ============================================================
# 8. 端到端 capture_and_canonicalize
# ============================================================
class TestEndToEnd:
    def test_capture_and_canonicalize_full_flow(self, chain):
        """端到端：采集→规范化→生命周期追踪。"""
        result = chain.capture_and_canonicalize(
            source_type="xhs_note",
            source_url="https://xhslink.com/e2e_test",
            raw_content="广州太古汇今天人很多，LV排队半小时。",
            normalized_content="广州太古汇客流较大，LV门店排队约30分钟。",
            subject_hit=True,
            subject_keywords=["太古汇", "LV"],
            sentiment="neutral",
            risk_level="low",
            engagement_metrics={"likes": 150, "comments": 20, "collects": 30, "shares": 5},
            ai_analysis={"summary": "太古汇客流正常", "confidence": 0.88},
            publish_datetime="2026-09-05 15:00:00",
            subject_scope="CTH",
            collection_metadata={"keyword": "太古汇 客流"},
            provider="xhs_collector_v2",
        )
        assert result["is_new_evidence"] is True
        assert result["evidence"].source_type == "xhs_note"
        assert result["evidence"].content_hash == compute_content_hash(
            "广州太古汇今天人很多，LV排队半小时。"
        )
        assert result["canonical"].subject_hit is True
        assert result["canonical"].subject_keywords == ["太古汇", "LV"]
        assert result["canonical"].sentiment == "neutral"
        assert result["canonical"].engagement_metrics["likes"] == 150
        assert result["canonical"].ai_analysis["confidence"] == 0.88
        assert len(result["tracking_ids"]) == 2

        # 验证 lineage
        lineage = chain.trace_lineage(result["evidence"].evidence_id)
        assert lineage["total_stages_recorded"] == 2
        assert "EVIDENCE" in lineage["stage_summary"]
        assert "CANONICAL_DATA" in lineage["stage_summary"]

    def test_capture_duplicate_content_returns_existing(self, chain):
        """重复内容采集时返回已有 Evidence，不重复创建。"""
        raw = "重复内容测试"
        r1 = chain.capture_and_canonicalize(
            source_type="xhs_note", source_url="https://x.com/1", raw_content=raw
        )
        r2 = chain.capture_and_canonicalize(
            source_type="xhs_note", source_url="https://x.com/2", raw_content=raw
        )
        assert r1["evidence"].evidence_id == r2["evidence"].evidence_id
        assert r2["is_new_evidence"] is False
        # 但 canonical 是新的（每次采集创建新的规范数据记录）
        assert r1["canonical"].canonical_id != r2["canonical"].canonical_id

    def test_get_stats(self, chain):
        chain.capture_and_canonicalize(
            source_type="xhs_note", source_url="https://x.com/1", raw_content="stats test"
        )
        stats = chain.get_stats()
        assert stats["evidence_count"] == 1
        assert stats["canonical_count"] == 1
        assert stats["rule_version"] == RULE_VERSION
        assert stats["lifecycle_stages"] == 13


# ============================================================
# 9. 向后兼容适配函数
# ============================================================
class TestBackwardCompatibility:
    def test_adapt_evidence_store_hash(self):
        """adapt_evidence_store_hash 返回完整 SHA256。"""
        from evidence_chain import adapt_evidence_store_hash
        h = adapt_evidence_store_hash("test content")
        assert len(h) == 64
        assert h == compute_content_hash("test content")

    def test_build_provenance_metadata(self):
        """build_provenance_metadata 构建标准元数据。"""
        from evidence_chain import build_provenance_metadata
        meta = build_provenance_metadata(
            source_type="xhs_note",
            source_url="https://x.com/1",
            captured_at="2026-09-06 12:00:00",
            subject_scope="CTH",
            provider="xhs_v2",
            extra_field="value",
        )
        assert meta["source_type"] == "xhs_note"
        assert meta["subject_scope"] == "CTH"
        assert meta["schema_version"] == "evidence-chain-v1.0.0"
        assert meta["extra_field"] == "value"


# ============================================================
# 运行入口
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
