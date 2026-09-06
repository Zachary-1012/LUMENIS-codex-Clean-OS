# -*- coding: utf-8 -*-
"""V3 增量层测试 — Identity + Delegation + Browser Capability + Research Pipeline。

覆盖：
- Agent Identity Chain
- Delegation Context（授权/撤销/过期/scope）
- Browser Capability Registry（最小权限/禁止操作）
- Research Pipeline（研究→抽象→设计→实现，禁复制代码）
- 与现有系统兼容（不破坏 232 测试）
"""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import (agent_identity, delegation, browser_capability,
                         research_pipeline, skill_manifest)
from osai_engine.agent_identity import IdentityChain, IdentityNode, IdentityRegistry, IDENTITY_TYPES
from osai_engine.delegation import DelegationContext, DelegationManager, DELEGATION_STATUSES
from osai_engine.browser_capability import (BrowserCapabilityRegistry, BROWSER_CAPABILITIES,
                                             FORBIDDEN_ACTIONS)
from osai_engine.research_pipeline import (ResearchPipeline, ResearchRecord,
                                            RESEARCH_STAGES, ALLOWED_EXTRACTION_TYPES,
                                            FORBIDDEN_EXTRACTION_TYPES)


# ============ Agent Identity 测试 ============

class TestAgentIdentity:
    def test_identity_types(self):
        assert len(IDENTITY_TYPES) == 6
        assert "USER" in IDENTITY_TYPES
        assert "AGENT" in IDENTITY_TYPES
        assert "SKILL" in IDENTITY_TYPES
        assert "TOOL" in IDENTITY_TYPES
        assert "BROWSER" in IDENTITY_TYPES

    def test_identity_node_creation(self):
        node = IdentityNode("AGENT", "orchestrator", "user@lumenis",
                            ["READ", "AUDIT"], intent="code_audit")
        assert node.identity_type == "AGENT"
        assert node.identity == "orchestrator"
        assert node.parent_identity == "user@lumenis"
        assert node.node_id.startswith("ID-")

    def test_invalid_identity_type(self):
        with pytest.raises(ValueError):
            IdentityNode("INVALID", "test")

    def test_identity_chain_creation(self):
        chain = IdentityChain("user@lumenis", user_intent="audit")
        assert chain.workflow_id.startswith("WF-")
        assert chain.user_node.identity == "user@lumenis"
        assert len(chain.nodes) == 1  # 只有 User

    def test_identity_chain_full(self):
        """完整 Identity Chain: User → Agent → Skill → Tool → Execution。"""
        chain = IdentityChain("user@lumenis", user_intent="code_audit")
        agent = chain.add_agent("orchestrator", ["READ", "AUDIT"])
        skill = chain.add_skill("S03", agent.identity, ["READ"])
        tool = chain.add_tool("ast_parser", skill.identity, ["READ"])
        execution = chain.record_execution(tool.identity, "parse_file",
                                           {"files": 10}, "SUCCESS")

        assert len(chain.nodes) == 4  # User + Agent + Skill + Tool
        assert execution["execution_id"].startswith("EXEC-")
        assert execution["status"] == "SUCCESS"
        assert len(chain.execution_records) == 1
        assert len(chain.audit_trail) > 0

    def test_identity_chain_permission_check(self):
        chain = IdentityChain("user@lumenis")
        chain.add_agent("orchestrator", ["READ", "AUDIT"])
        assert chain.check_permission("orchestrator", "READ") is True
        assert chain.check_permission("orchestrator", "COMMIT") is False
        assert chain.check_permission("nonexistent", "READ") is False

    def test_identity_registry(self):
        reg = IdentityRegistry()
        reg.register("AGENT", "orchestrator", ["READ", "AUDIT"])
        assert reg.get("orchestrator") is not None
        assert reg.get("nonexistent") is None
        snap = reg.snapshot()
        assert snap["total"] == 1
        assert snap["by_type"]["AGENT"] == 1


# ============ Delegation 测试 ============

class TestDelegation:
    def test_delegation_creation(self):
        ctx = DelegationContext("user@lumenis", "orchestrator",
                                scope={"allowed_actions": ["read"]},
                                intent="audit", permissions=["READ", "AUDIT"],
                                duration_seconds=600)
        assert ctx.delegation_id.startswith("DEL-")
        assert ctx.status == "PENDING"
        assert ctx.user_identity == "user@lumenis"
        assert ctx.agent_identity == "orchestrator"

    def test_delegation_approve(self):
        ctx = DelegationContext("user", "agent", {}, "test", ["READ"])
        assert ctx.approve() is True
        assert ctx.status == "ACTIVE"
        assert ctx.is_active() is True

    def test_delegation_deny(self):
        ctx = DelegationContext("user", "agent", {}, "test", ["READ"])
        assert ctx.deny("not allowed") is True
        assert ctx.status == "DENIED"
        assert ctx.is_active() is False

    def test_delegation_revoke(self):
        ctx = DelegationContext("user", "agent", {}, "test", ["READ"])
        ctx.approve()
        assert ctx.revoke("user revoked") is True
        assert ctx.status == "REVOKED"
        assert ctx.is_active() is False

    def test_delegation_expiry(self):
        ctx = DelegationContext("user", "agent", {}, "test", ["READ"],
                                duration_seconds=0.01)
        ctx.approve()
        time.sleep(0.02)
        assert ctx.is_active() is False
        assert ctx.status == "EXPIRED"

    def test_delegation_scope_check(self):
        ctx = DelegationContext("user", "agent",
                                scope={"allowed_actions": ["read", "inspect"]},
                                intent="test", permissions=["READ"])
        ctx.approve()
        assert ctx.check_scope("read") is True
        assert ctx.check_scope("delete") is False

    def test_delegation_execute(self):
        ctx = DelegationContext("user", "agent",
                                scope={"allowed_actions": ["read", "inspect"]},
                                intent="test", permissions=["READ", "EXECUTE"])
        ctx.approve()
        result = ctx.execute("S01", "read", result={"data": "test"})
        assert result is not None
        assert result["status"] == "SUCCESS"
        assert len(ctx.execution_log) > 0

    def test_delegation_execute_blocked_when_inactive(self):
        ctx = DelegationContext("user", "agent", {}, "test", ["READ"])
        # 未 approve
        result = ctx.execute("S01", "read")
        assert result is None

    def test_delegation_manager(self):
        mgr = DelegationManager()
        ctx1 = mgr.create("user1", "agent1", {}, "test", ["READ"])
        ctx2 = mgr.create("user2", "agent2", {}, "test", ["READ"])
        ctx1.approve()
        assert len(mgr.list_active()) == 1
        assert mgr.get(ctx1.delegation_id) is not None
        snap = mgr.snapshot()
        assert snap["total"] == 2
        assert snap["active"] == 1

    def test_no_impersonation(self):
        """Delegation 必须记录 user 和 agent 分离，禁止 Impersonation。"""
        ctx = DelegationContext("real_user", "agent", {}, "test", ["READ"])
        ctx.approve()
        d = ctx.to_dict()
        assert d["user_identity"] == "real_user"
        assert d["agent_identity"] == "agent"
        assert d["user_identity"] != d["agent_identity"]


# ============ Browser Capability 测试 ============

class TestBrowserCapability:
    def test_default_capabilities(self):
        reg = BrowserCapabilityRegistry()
        snap = reg.snapshot()
        assert snap["total_capabilities"] == 9
        assert "open" in BROWSER_CAPABILITIES
        assert "execute" in BROWSER_CAPABILITIES

    def test_forbidden_actions(self):
        assert "follow" in FORBIDDEN_ACTIONS
        assert "like" in FORBIDDEN_ACTIONS
        assert "comment" in FORBIDDEN_ACTIONS
        assert "publish" in FORBIDDEN_ACTIONS

    def test_forbidden_action_blocked(self):
        reg = BrowserCapabilityRegistry()
        assert reg.is_forbidden("follow") is True
        result = reg.can_execute("follow", ["READ", "ADMIN"])
        assert result["allowed"] is False
        assert result["reason"] == "FORBIDDEN_ACTION"

    def test_capability_permission_check(self):
        reg = BrowserCapabilityRegistry()
        # read 需要 READ 权限
        assert reg.can_execute("read", ["READ"])["allowed"] is True
        assert reg.can_execute("read", [])["allowed"] is False
        # execute 需要 ADMIN 权限
        assert reg.can_execute("execute", ["READ"])["allowed"] is False

    def test_disabled_capability(self):
        reg = BrowserCapabilityRegistry()
        # upload 默认禁用
        assert reg.is_enabled("upload") is False
        result = reg.can_execute("upload", ["WRITE"])
        assert result["allowed"] is False
        assert result["reason"] == "CAPABILITY_DISABLED"

    def test_enable_disable(self):
        reg = BrowserCapabilityRegistry()
        assert reg.disable("open") is True
        assert reg.is_enabled("open") is False
        assert reg.enable("open") is True
        assert reg.is_enabled("open") is True

    def test_execute_with_executor(self):
        reg = BrowserCapabilityRegistry()
        result = reg.execute("read", ["READ"],
                             executor=lambda ctx: {"content": "test page"})
        assert result["status"] == "SUCCESS"
        assert result["output"]["content"] == "test page"

    def test_execute_no_executor(self):
        reg = BrowserCapabilityRegistry()
        result = reg.execute("read", ["READ"])
        assert result["status"] == "NO_EXECUTOR"
        assert "executor not injected" in result["error"]

    def test_read_only_defaults(self):
        """open/navigate/search/read/click/input 默认为只读。"""
        reg = BrowserCapabilityRegistry()
        for cap_id in ["open", "navigate", "search", "read", "click", "input"]:
            cap = reg.get(cap_id)
            assert cap.read_only is True, f"{cap_id} should be read_only"

    def test_skill_browser_decoupled(self):
        """Browser Capability 通过 Registry 调用，不写死在 Skill 中。"""
        reg = BrowserCapabilityRegistry()
        # Skill 只需要知道 capability_id，不需要知道 Browser 实现
        result = reg.execute("navigate", ["READ"],
                             context={"url": "https://example.com"})
        assert result["capability"] == "navigate"
        assert result["permission"] == "READ"


# ============ Research Pipeline 测试 ============

class TestResearchPipeline:
    def test_research_stages(self):
        assert len(RESEARCH_STAGES) == 9
        assert "DISCOVERY" in RESEARCH_STAGES
        assert "ACCEPTED" in RESEARCH_STAGES
        assert "REJECTED" in RESEARCH_STAGES

    def test_allowed_extraction_types(self):
        assert "architecture_pattern" in ALLOWED_EXTRACTION_TYPES
        assert "protocol_standard" in ALLOWED_EXTRACTION_TYPES
        assert "security_principle" in ALLOWED_EXTRACTION_TYPES

    def test_forbidden_extraction_types(self):
        assert "source_code" in FORBIDDEN_EXTRACTION_TYPES
        assert "proprietary_algorithm" in FORBIDDEN_EXTRACTION_TYPES

    def test_research_record_creation(self):
        rec = ResearchRecord("microsoft/entra-agentid", "github",
                             "Agent ID OBO", url="https://github.com/...")
        assert rec.research_id.startswith("RES-")
        assert rec.stage == "DISCOVERY"
        assert rec.review_status == "PENDING"

    def test_add_allowed_extraction(self):
        rec = ResearchRecord("test", "github", "Test")
        ext = rec.add_extraction("architecture_pattern", "identity chain",
                                 notes="absorb architecture only")
        assert ext["extraction_id"].startswith("EXT-")
        assert len(rec.extractions) == 1

    def test_add_forbidden_extraction(self):
        rec = ResearchRecord("test", "github", "Test")
        with pytest.raises(ValueError):
            rec.add_extraction("source_code", "copy paste code")

    def test_license_check(self):
        rec = ResearchRecord("test", "github", "Test")
        rec.check_license("MIT", True, "can use architecture ideas")
        assert rec.license_check is not None
        assert rec.license_check["can_use"] is True

    def test_stage_advancement(self):
        rec = ResearchRecord("test", "github", "Test")
        assert rec.advance_stage("STUDY") is True
        assert rec.stage == "STUDY"
        assert rec.advance_stage("ABSTRACTION") is True
        # 不能回退
        assert rec.advance_stage("DISCOVERY") is False

    def test_review_approve(self):
        rec = ResearchRecord("test", "github", "Test")
        rec.advance_stage("STUDY")
        rec.advance_stage("ABSTRACTION")
        rec.advance_stage("DESIGN")
        rec.advance_stage("IMPLEMENTATION")
        rec.advance_stage("TESTING")
        rec.advance_stage("REVIEW")
        assert rec.review(True, "reviewer", "good") is True
        assert rec.review_status == "APPROVED"
        assert rec.stage == "ACCEPTED"

    def test_validate_no_code_copying(self):
        pipeline = ResearchPipeline()
        rec = pipeline.create_research("test", "github", "Test")
        rec.check_license("MIT", True)
        rec.add_extraction("architecture_pattern", "test pattern")
        result = pipeline.validate_no_code_copying(rec.research_id)
        assert result["valid"] is True

    def test_validate_no_license_fails(self):
        pipeline = ResearchPipeline()
        rec = pipeline.create_research("test", "github", "Test")
        result = pipeline.validate_no_code_copying(rec.research_id)
        assert result["valid"] is False
        assert "No license check" in result["issues"][0]

    def test_pipeline_snapshot(self):
        pipeline = ResearchPipeline()
        pipeline.create_research("test1", "github", "Test 1")
        pipeline.create_research("test2", "docs", "Test 2")
        snap = pipeline.snapshot()
        assert snap["total_research"] == 2
        assert "by_stage" in snap


# ============ 兼容性测试 ============

class TestV3Compatibility:
    def test_existing_skill_manifest_still_works(self):
        """V3 增量层不破坏现有 Skill Manifest。"""
        manifests = skill_manifest.build_s01_s12_manifests()
        assert len(manifests) == 12
        for m in manifests:
            v = skill_manifest.validate_manifest(m)
            assert v["valid"] is True

    def test_manifest_has_identity_policy(self):
        """V3 新增 identity_policy/audit_policy 字段。"""
        m = skill_manifest.normalize_manifest({
            "id": "T1", "name": "T", "category": "ENGINEERING",
            "type": "SYSTEM", "description": "t", "permissions": ["READ"],
        })
        assert "identity_policy" in m
        assert "audit_policy" in m
        assert m["identity_policy"]["requires_delegation"] is True
        assert m["identity_policy"]["impersonation_allowed"] is False

    def test_osai_package_has_39_modules(self):
        import osai_engine
        assert len(osai_engine.__all__) == 39
        for mod in ["agent_identity", "delegation", "browser_capability",
                    "research_pipeline"]:
            assert hasattr(osai_engine, mod)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
