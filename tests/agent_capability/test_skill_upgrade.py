# -*- coding: utf-8 -*-
"""Skill 升级为 Capability 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_capability.skill_upgrade import (
    CapabilityRegistry, CapabilityMetadata, CapabilityStatus,
)
from agent_capability.router import ToolRiskLevel, ToolPermissionLevel


class TestCapabilityMetadata:
    def test_success_rate(self):
        cap = CapabilityMetadata(
            capability_id="cap.test", name="test",
            usage_count=10, success_count=7, failure_count=3,
        )
        assert cap.success_rate == 0.7

    def test_success_rate_no_usage(self):
        cap = CapabilityMetadata(capability_id="cap.test", name="test")
        assert cap.success_rate == 0.0

    def test_to_dict(self):
        cap = CapabilityMetadata(
            capability_id="cap.test", name="test",
            risk_level=ToolRiskLevel.HIGH,
            permission_level=ToolPermissionLevel.WRITE,
            status=CapabilityStatus.ENABLED,
        )
        d = cap.to_dict()
        assert d["capability_id"] == "cap.test"
        assert d["risk_level"] == "HIGH"
        assert d["permission_level"] == "write"
        assert d["status"] == "enabled"
        assert "success_rate" in d

    def test_to_tool_definition(self):
        cap = CapabilityMetadata(
            capability_id="cap.test", name="测试工具", description="测试",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询词"},
                    "limit": {"type": "integer", "description": "数量", "default": 10},
                },
                "required": ["query"],
            },
            risk_level=ToolRiskLevel.LOW,
            permission_level=ToolPermissionLevel.READ,
            status=CapabilityStatus.ENABLED,
            tags=["test", "query"],
        )
        tool = cap.to_tool_definition()
        assert tool.tool_id == "cap.test"
        assert tool.name == "测试工具"
        assert len(tool.params) == 2
        assert tool.params[0].name == "query"
        assert tool.params[0].required is True
        assert tool.params[1].name == "limit"
        assert tool.params[1].default == 10
        assert tool.enabled is True


class TestCapabilityRegistry:
    def test_load_from_skills_registry(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        count = reg.load_from_skills_registry()
        assert count >= 2
        # 验证加载的 Capability
        cap = reg.get_capability("cap.test_skill_a")
        assert cap is not None
        assert cap.name == "测试技能A"
        assert cap.source_skill_id == "test_skill_a"

    def test_load_from_skills_registry_disabled_skill(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        reg.load_from_skills_registry()
        cap = reg.get_capability("cap.collector_xhs")
        assert cap is not None
        assert cap.status == CapabilityStatus.DISABLED

    def test_load_from_skills_registry_twice(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        count1 = reg.load_from_skills_registry()
        count2 = reg.load_from_skills_registry()
        assert count1 == count2  # 第二次不重复加载

    def test_infer_security_level_collection(self):
        risk, perm, approval = CapabilityRegistry._infer_security_level(
            "collector_xhs", {})
        assert risk == ToolRiskLevel.HIGH
        assert perm == ToolPermissionLevel.WRITE
        assert approval is True

    def test_infer_security_level_report(self):
        risk, perm, approval = CapabilityRegistry._infer_security_level(
            "report_generator", {})
        assert risk == ToolRiskLevel.MEDIUM
        assert perm == ToolPermissionLevel.ANALYZE
        assert approval is False

    def test_infer_security_level_default(self):
        risk, perm, approval = CapabilityRegistry._infer_security_level(
            "unknown_skill", {})
        assert risk == ToolRiskLevel.LOW
        assert perm == ToolPermissionLevel.READ
        assert approval is False

    def test_register_capability(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        cap = CapabilityMetadata(
            capability_id="cap.custom", name="自定义", description="test",
            status=CapabilityStatus.ENABLED,
        )
        assert reg.register_capability(cap) is True
        assert reg.get_capability("cap.custom") is not None

    def test_list_capabilities(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        reg.load_from_skills_registry()
        all_caps = reg.list_capabilities()
        assert len(all_caps) >= 2
        enabled = reg.list_capabilities(status=CapabilityStatus.ENABLED)
        assert len(enabled) >= 1
        assert all(c.status == CapabilityStatus.ENABLED for c in enabled)

    def test_update_usage_stats(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        reg.load_from_skills_registry()
        cap_id = "cap.test_skill_a"
        reg.update_usage_stats(cap_id, success=True, duration_ms=100)
        reg.update_usage_stats(cap_id, success=False, duration_ms=200)
        cap = reg.get_capability(cap_id)
        assert cap.usage_count == 2
        assert cap.success_count == 1
        assert cap.failure_count == 1
        assert cap.success_rate == 0.5
        assert cap.avg_duration_ms > 0

    def test_to_tool_definitions(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        reg.load_from_skills_registry()
        tools = reg.to_tool_definitions()
        # 只有 enabled 的才会导出
        assert len(tools) >= 1
        assert all(t.enabled for t in tools)

    def test_register_to_router(self, seeded_db):
        from agent_capability.router import CapabilityRouter
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        reg.load_from_skills_registry()
        router = CapabilityRouter(enabled=True)
        initial_count = len(router.list_tools())
        count = reg.register_to_router(router)
        assert count >= 1
        assert len(router.list_tools()) == initial_count + count

    def test_disabled(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=False)
        assert reg.load_from_skills_registry() == 0
        cap = CapabilityMetadata(capability_id="cap.x", name="x")
        assert reg.register_capability(cap) is False

    def test_stats(self, seeded_db):
        reg = CapabilityRegistry(db_path=seeded_db, enabled=True)
        reg.load_from_skills_registry()
        s = reg.stats()
        assert s["total_capabilities"] >= 2
        assert s["enabled_capabilities"] >= 1
        assert s["loaded_from_db"] is True
        assert "by_category" in s
