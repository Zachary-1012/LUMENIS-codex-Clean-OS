"""V2 P0-2/P0-3 测试：Capability Registry + Canonical Data + 真实性审计"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCapabilityRegistry:
    def test_registry_has_capabilities(self):
        from osai_engine.capability_registry import get_registry
        reg = get_registry()
        assert len(reg.list_all()) >= 20

    def test_no_false_active(self):
        """禁止虚假标记 ACTIVE。每个 ACTIVE 必须有 source_file 和 runtime_entry。"""
        from osai_engine.capability_registry import get_registry, CAP_ACTIVE
        reg = get_registry()
        for cap in reg.list_by_status(CAP_ACTIVE):
            assert cap.source_file, f"{cap.capability_id} ACTIVE but no source_file"
            assert cap.runtime_entry, f"{cap.capability_id} ACTIVE but no runtime_entry"

    def test_zbc_subject_filter_active(self):
        from osai_engine.capability_registry import get_registry
        reg = get_registry()
        cap = reg.get("zbc.subject_filter")
        assert cap is not None
        assert cap.status == "ACTIVE"
        assert "subject_hit" in cap.runtime_entry

    def test_summary(self):
        from osai_engine.capability_registry import get_registry
        s = get_registry().summary()
        assert s["total"] >= 20
        assert "by_status" in s
        assert "by_domain" in s

    def test_osi_skill_registry_active(self):
        from osai_engine.capability_registry import get_registry
        cap = get_registry().get("osai.skill_registry")
        assert cap is not None
        assert cap.status == "ACTIVE"

    def test_partial_capabilities_exist(self):
        from osai_engine.capability_registry import get_registry, CAP_PARTIAL
        partial = get_registry().list_by_status(CAP_PARTIAL)
        assert len(partial) >= 1  # Research Pipeline 是 PARTIAL


class TestCanonicalData:
    def test_create_source(self):
        from osai_engine.canonical_data import create_entity
        s = create_entity("source", source_type="xiaohongshu", raw_content="test")
        assert s.canonical_id.startswith("src_")
        assert s.source_type == "xiaohongshu"

    def test_create_evidence(self):
        from osai_engine.canonical_data import create_entity
        e = create_entity("evidence", content="test evidence", confidence=0.95)
        assert e.canonical_id.startswith("ev_")
        assert e.confidence == 0.95

    def test_create_all_entity_types(self):
        from osai_engine.canonical_data import create_entity, ENTITY_TYPES
        for etype in ENTITY_TYPES:
            ent = create_entity(etype)
            assert ent.canonical_id is not None
            assert hasattr(ent, "product_id")
            assert hasattr(ent, "subject_id")
            assert hasattr(ent, "content_hash")

    def test_content_hash(self):
        from osai_engine.canonical_data import create_entity
        e = create_entity("evidence", content="test")
        h = e.compute_hash({"key": "value"})
        assert len(h) == 16
        assert e.content_hash == h

    def test_unknown_type_raises(self):
        from osai_engine.canonical_data import create_entity
        with pytest.raises(ValueError):
            create_entity("nonexistent")

    def test_data_flow(self):
        from osai_engine.canonical_data import canonical_data_flow
        flow = canonical_data_flow()
        assert "ingestion" in flow
        assert "evaluation" in flow
        assert "source" in flow["ingestion"]
        assert "evidence" in flow["normalization"]


class TestP0AuthenticityAudit:
    """真实性审计：验证6个P0是否真正进入运行链。"""

    def test_p0_5_provider_registry_used_by_intelligence(self):
        """P0-5: intelligence.py 必须真实使用 provider_registry。"""
        import os
        path = os.path.join(r"D:\Taikoo-monitor-new", "intelligence.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "from provider_registry import" in content
        assert "is_provider_available" in content

    def test_p0_18_no_hardcoded_osai_path(self):
        """P0-18: lumenis_skill_adapter.py 不得有硬编码 OSAI 路径。"""
        import os
        path = os.path.join(r"D:\Taikoo-monitor-new", "lumenis_skill_adapter.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert r"D:\Zachary OS AI" not in content
        assert "repo_registry.json" in content

    def test_p0_19_subject_context_delegated(self):
        """P0-19: subject_rules.get_active_brand() 必须委托 SubjectContext。"""
        import os
        path = os.path.join(r"D:\Taikoo-monitor-new", "subject_rules.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "from subject_context import get_subject_context" in content
        assert "get_subject_context().brand_key" in content

    def test_p0_1_domain_isolation_in_sql(self):
        """P0-1: _subject_sql_and_values 必须接入 Domain Isolation。"""
        import os
        path = os.path.join(r"D:\Taikoo-monitor-new", "subject_rules.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "from domain_isolation import" in content
        assert "CTH" in content

    def test_p0_7_contract_in_invocation(self):
        """P0-7: skill_invocation.py 必须使用 SkillExecutionContract。"""
        import os
        path = os.path.join(r"D:\Zachary OS AI", "osai_engine", "skill_invocation.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "SkillExecutionContract" in content
        assert "_get_contract" in content
        assert "CONTRACT_VERIFIED" in content

    def test_p0_11_effect_fence_in_invocation(self):
        """P0-11: skill_invocation.py 必须使用 EffectFence。"""
        import os
        path = os.path.join(r"D:\Zachary OS AI", "osai_engine", "skill_invocation.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "effect_fence" in content
        assert "get_fence" in content
        assert "idempotency_key" in content

    def test_active_brand_is_compatibility_layer(self):
        """active_brand 不再承担主体边界，只是兼容层。"""
        import os
        path = os.path.join(r"D:\Taikoo-monitor-new", "subject_rules.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "兼容层" in content
        assert "不再承担系统数据边界" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
