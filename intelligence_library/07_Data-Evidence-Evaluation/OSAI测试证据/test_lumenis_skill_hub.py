# -*- coding: utf-8 -*-
"""PHASE 3 V1.1 — Skill Hub 综合测试。

覆盖：
- Skill Manifest 验证 / 规范化 / 加载
- S01-S12 Canonical Manifest
- Skill Selector 推荐
- Skill Invocation 调用链
- GitHub Skill Sync
- Cross-Core Skill（OSAI → ZBC Consumer）
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import (skill_manifest, skill_selector, skill_invocation,
                         skill_sync, skill_registry)
from osai_engine.skill_manifest import (
    validate_manifest, normalize_manifest, build_s01_s12_manifests,
    SKILL_TYPES, SKILL_CATEGORIES, SKILL_STATUSES, REQUIRED_FIELDS,
)
from osai_engine.skill_selector import SkillSelector, WORKSPACE_CATEGORIES
from osai_engine.skill_invocation import SkillInvoker, SkillInvocation, INVOCATION_STATUSES
from osai_engine.skill_sync import GitHubSkillSync, SYNC_STATUSES


# ============ Manifest 测试 ============

class TestSkillManifest:
    def test_constants_complete(self):
        assert len(SKILL_TYPES) == 7
        assert len(SKILL_CATEGORIES) == 11
        assert len(SKILL_STATUSES) == 7
        assert "ENGINEERING" in SKILL_CATEGORIES
        assert "KOS" in SKILL_CATEGORIES
        assert "SYSTEM" in SKILL_TYPES

    def test_validate_valid_manifest(self):
        m = normalize_manifest({
            "id": "TEST01", "name": "Test Skill", "version": "1.0.0",
            "category": "ENGINEERING", "type": "SYSTEM",
            "description": "test", "permissions": ["READ"],
        })
        v = validate_manifest(m)
        assert v["valid"] is True
        assert v["errors"] == []

    def test_validate_missing_required(self):
        v = validate_manifest({"id": "X"})
        assert v["valid"] is False
        assert len(v["errors"]) > 0

    def test_validate_invalid_category(self):
        m = normalize_manifest({
            "id": "T1", "name": "T", "category": "INVALID",
            "type": "SYSTEM", "description": "t", "permissions": ["READ"],
        })
        v = validate_manifest(m)
        assert v["valid"] is False
        assert any("category" in e for e in v["errors"])

    def test_normalize_defaults(self):
        m = normalize_manifest({"id": "T1", "name": "T", "category": "ENGINEERING",
                                "type": "SYSTEM", "description": "t", "permissions": ["READ"]})
        assert m["version"] == "0.1.0"
        assert m["status"] == "DRAFT"
        assert "created_at" in m
        assert "updated_at" in m
        assert isinstance(m["permissions"], list)

    def test_s01_s12_manifests_valid(self):
        manifests = build_s01_s12_manifests()
        assert len(manifests) == 12
        for m in manifests:
            v = validate_manifest(m)
            assert v["valid"], f"{m['id']} invalid: {v['errors']}"

    def test_s01_s12_ids_unique(self):
        manifests = build_s01_s12_manifests()
        ids = [m["id"] for m in manifests]
        assert len(ids) == len(set(ids))

    def test_s01_s12_all_system_type(self):
        manifests = build_s01_s12_manifests()
        for m in manifests:
            assert m["type"] == "SYSTEM"
            assert m["status"] == "ENABLED"

    def test_manifest_no_hardcoded_model_warning(self):
        m = normalize_manifest({
            "id": "T1", "name": "T", "category": "ENGINEERING", "type": "SYSTEM",
            "description": "t", "permissions": ["READ"],
            "execution": {"model": "gpt-4"},
        })
        v = validate_manifest(m)
        assert any("model" in w for w in v["warnings"])


# ============ Selector 测试 ============

class TestSkillSelector:
    def setup_method(self):
        self.registry = skill_registry.SkillRegistry()
        self.selector = SkillSelector(self.registry)

    def test_selector_init(self):
        assert self.selector.registry is not None

    def test_select_returns_list(self):
        result = self.selector.select("test task", workspace="engineering")
        assert isinstance(result, list)

    def test_select_max_results(self):
        result = self.selector.select("audit code", workspace="engineering", max_results=3)
        assert len(result) <= 3

    def test_select_has_score(self):
        result = self.selector.select("git audit", workspace="engineering")
        if result:
            assert "score" in result[0]
            assert "skill_id" in result[0]
            assert "reason" in result[0]

    def test_workspace_categories(self):
        assert "engineering" in WORKSPACE_CATEGORIES
        assert "production" in WORKSPACE_CATEGORIES
        assert "intelligence" in WORKSPACE_CATEGORIES

    def test_permission_filter(self):
        result = self.selector.select("test", workspace="engineering",
                                      permissions=["READ"])
        # READ-only 用户应该能看到只读 Skill
        assert isinstance(result, list)

    def test_explain_structure(self):
        exp = self.selector.explain("audit git repository", workspace="engineering")
        assert "task" in exp
        assert "workspace_categories" in exp
        assert "intent_matched" in exp
        assert "recommendations" in exp


# ============ Invocation 测试 ============

class TestSkillInvocation:
    def test_invocation_init(self):
        inv = SkillInvocation("test task", "S01", workspace="engineering")
        assert inv.invocation_id.startswith("INV-")
        assert inv.task_id.startswith("TASK-")
        assert inv.trace_id.startswith("TRACE-")
        assert inv.status == "PENDING"
        assert inv.skill_id == "S01"

    def test_invocation_to_dict(self):
        inv = SkillInvocation("test", "S01")
        d = inv.to_dict()
        required = ["invocation_id", "task_id", "trace_id", "skill_id",
                    "skill_version", "workspace", "status"]
        for key in required:
            assert key in d

    def test_invocation_statuses(self):
        assert "SUCCESS" in INVOCATION_STATUSES
        assert "BLOCKED" in INVOCATION_STATUSES
        assert "FAILED" in INVOCATION_STATUSES

    def test_invoker_init(self):
        invoker = SkillInvoker()
        assert invoker.max_skill_chain == 3
        assert invoker.invocation_timeout == 120
        assert invoker.invocations == []

    def test_invoker_invoke_returns_dict(self):
        invoker = SkillInvoker()
        result = invoker.invoke("test", "S01", workspace="engineering")
        assert "invocation_id" in result
        assert "status" in result
        assert result["skill_id"] == "S01"

    def test_invoker_invoke_produces_trace(self):
        invoker = SkillInvoker()
        result = invoker.invoke("test", "S01")
        assert result["trace_id"].startswith("TRACE-")

    def test_invoker_chain_limit(self):
        invoker = SkillInvoker(max_skill_chain=2)
        results = invoker.invoke_chain("test", ["S01", "S02", "S03"])
        assert len(results) <= 2

    def test_invoker_snapshot(self):
        invoker = SkillInvoker()
        invoker.invoke("test", "S01")
        snap = invoker.snapshot()
        assert "total_invocations" in snap
        assert snap["total_invocations"] >= 1


# ============ Sync 测试 ============

class TestSkillSync:
    def setup_method(self):
        self.sync = GitHubSkillSync()

    def test_sync_init(self):
        assert os.path.isdir(self.sync.manifest_dir)

    def test_sync_save_and_load(self):
        m = normalize_manifest({
            "id": "TESTSAVE", "name": "Test Save", "category": "ENGINEERING",
            "type": "CUSTOM", "description": "test", "permissions": ["READ"],
        })
        path = self.sync.save_manifest(m)
        assert os.path.isfile(path)
        loaded = self.sync.load_manifest("TESTSAVE")
        assert loaded is not None
        assert loaded["id"] == "TESTSAVE"
        # 清理
        self.sync.delete_manifest("TESTSAVE")

    def test_sync_list_manifests(self):
        ids = self.sync.list_manifests()
        assert "S01" in ids
        assert "S12" in ids
        assert len(ids) >= 12

    def test_sync_statuses(self):
        assert "SYNCED" in SYNC_STATUSES
        assert "CONFLICT" in SYNC_STATUSES
        assert "UPDATE_AVAILABLE" in SYNC_STATUSES

    def test_sync_snapshot(self):
        snap = self.sync.snapshot()
        assert "manifest_count" in snap
        assert "repo_sha" in snap
        assert "branch" in snap
        assert snap["manifest_count"] >= 12

    def test_sync_diff_nonexistent(self):
        result = self.sync.diff_manifest("NONEXISTENT")
        assert result["status"] == "NOT_FOUND"

    def test_sync_invalid_manifest_rejected(self):
        with pytest.raises(ValueError):
            self.sync.save_manifest({"id": "", "name": ""})


# ============ Cross-Core 测试 ============

class TestCrossCoreSkill:
    def test_osai_skill_registry_accessible(self):
        """OSAI Skill Registry 可被外部访问。"""
        reg = skill_registry.SkillRegistry()
        snap = reg.snapshot()
        assert "catalog" in snap
        assert len(snap["catalog"]) >= 12

    def test_skill_contract_has_permissions(self):
        """每个 Skill 声明权限。"""
        reg = skill_registry.SkillRegistry()
        catalog = reg.snapshot()["catalog"]
        for skill in catalog:
            assert "permissions" in skill or "permission_level" in skill

    def test_zbc_consumer_adapter_exists(self):
        """ZBC 侧有 Capability Adapter 消费 OSAI Skill。"""
        zbc_path = r"D:\Taikoo-monitor-new\contracts\lumenis_adapter.py"
        assert os.path.isfile(zbc_path)
        with open(zbc_path, encoding="utf-8") as f:
            content = f.read()
        assert "permission_gate_snapshot" in content or "repository_registry" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
