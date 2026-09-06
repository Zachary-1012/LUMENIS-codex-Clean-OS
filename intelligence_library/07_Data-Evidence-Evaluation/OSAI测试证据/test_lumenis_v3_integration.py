# -*- coding: utf-8 -*-
"""V3 风险修复测试：Agent Identity Integration + Local Browser Executor。

覆盖：
    - AgentIdentityContext 创建/Identity Chain/Delegation
    - Skill/Tool/Browser Identity 记录
    - 权限检查与撤销
    - IdentityAwareAgentWrapper 执行
    - LocalBrowserExecutor 只读操作
    - 禁止操作拦截
    - 高风险操作默认禁用
    - 全量兼容性（不破坏现有 274 测试）
"""
import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine.agent_integration import (
    AgentIdentityContext, IdentityAwareAgentWrapper,
    create_agent_context, get_agent_context, identity_integration_snapshot,
)
from osai_engine.browser_executor import LocalBrowserExecutor, get_browser_executor
from osai_engine.browser_capability import FORBIDDEN_ACTIONS


class TestAgentIdentityContext(unittest.TestCase):
    """AgentIdentityContext 基础功能。"""

    def setUp(self):
        self.ctx = AgentIdentityContext(
            "user@lumenis", "orchestrator", "code_audit",
            permissions=["READ", "AUDIT", "ANALYZE"]
        )

    def test_context_creation(self):
        self.assertEqual(self.ctx.user_identity, "user@lumenis")
        self.assertEqual(self.ctx.agent_identity, "orchestrator")
        self.assertTrue(self.ctx.is_active())
        self.assertIn("AIC-", self.ctx.context_id)

    def test_identity_chain_has_user_and_agent(self):
        chain = self.ctx.get_identity_chain()
        identities = [n["identity"] for n in chain]
        self.assertIn("user@lumenis", identities)
        self.assertIn("orchestrator", identities)

    def test_add_skill(self):
        node = self.ctx.add_skill("S03", ["READ", "AUDIT"], "code_analysis")
        self.assertEqual(node["identity"], "S03")
        self.assertEqual(node["parent_identity"], "orchestrator")
        self.assertIn("READ", node["permission"])

    def test_add_skill_permission_truncation(self):
        # Skill 请求 PATCH_PREVIEW，但 Agent 只有 READ/AUDIT/ANALYZE
        node = self.ctx.add_skill("S06", ["READ", "PATCH_PREVIEW"], "patch")
        self.assertNotIn("PATCH_PREVIEW", node["permission"])
        self.assertIn("READ", node["permission"])

    def test_add_tool(self):
        node = self.ctx.add_tool("ast_parser", "S03", ["READ"])
        self.assertEqual(node["identity"], "ast_parser")
        self.assertEqual(node["parent_identity"], "S03")

    def test_add_browser_capability_allowed(self):
        result = self.ctx.add_browser_capability("read", "S03")
        self.assertTrue(result["allowed"])

    def test_add_browser_capability_forbidden(self):
        result = self.ctx.add_browser_capability("follow", "S03")
        self.assertFalse(result["allowed"])
        self.assertIn("FORBIDDEN", result["reason"])

    def test_record_execution(self):
        exec_record = self.ctx.record_execution("S03", "analyze", {"files": 10})
        self.assertEqual(exec_record["status"], "SUCCESS")
        self.assertEqual(exec_record["action"], "analyze")

    def test_check_permission(self):
        self.assertTrue(self.ctx.check_permission("READ"))
        self.assertFalse(self.ctx.check_permission("COMMIT"))
        self.assertFalse(self.ctx.check_permission("PUSH"))

    def test_revoke(self):
        self.ctx.revoke("user cancelled")
        self.assertFalse(self.ctx.is_active())

    def test_audit_trail(self):
        self.ctx.add_skill("S01", ["READ"])
        self.ctx.record_execution("S01", "scan", {})
        trail = self.ctx.get_audit_trail()
        self.assertGreater(len(trail), 0)

    def test_to_dict(self):
        d = self.ctx.to_dict()
        self.assertEqual(d["user_identity"], "user@lumenis")
        self.assertEqual(d["agent_identity"], "orchestrator")
        self.assertIn("identity_chain", d)
        self.assertIn("delegation_status", d)
        self.assertEqual(d["delegation_status"], "ACTIVE")


class TestIdentityAwareAgentWrapper(unittest.TestCase):
    """Identity 感知 Agent Wrapper。"""

    def test_wrapper_execution_success(self):
        def mock_agent(task="", identity_context=None, **kwargs):
            return {"task_done": True, "task": task}

        wrapper = IdentityAwareAgentWrapper(mock_agent, "test_agent")
        result = wrapper.execute("user@test", "test_task")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["task_done"], True)
        self.assertIn("identity_summary", result)
        self.assertEqual(result["identity_summary"]["agent_identity"], "test_agent")

    def test_wrapper_execution_failure(self):
        def failing_agent(task="", **kwargs):
            raise RuntimeError("simulated failure")

        wrapper = IdentityAwareAgentWrapper(failing_agent, "failing_agent")
        result = wrapper.execute("user@test", "fail_task")
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("simulated failure", result["error"])

    def test_wrapper_list_contexts(self):
        def mock_agent(**kwargs):
            return {}

        wrapper = IdentityAwareAgentWrapper(mock_agent, "ctx_agent")
        wrapper.execute("u1", "t1")
        wrapper.execute("u2", "t2")
        contexts = wrapper.list_contexts()
        self.assertEqual(len(contexts), 2)


class TestLocalBrowserExecutor(unittest.TestCase):
    """LocalBrowserExecutor 基础功能。"""

    def setUp(self):
        self.executor = LocalBrowserExecutor()

    def test_executor_creation(self):
        self.assertIn("LBE-", self.executor.execution_id)
        self.assertEqual(len(self.executor.get_history()), 0)

    def test_forbidden_action_blocked(self):
        for action in ["follow", "like", "comment", "publish", "logout"]:
            result = self.executor.execute(action, ["READ", "ADMIN"])
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("FORBIDDEN_ACTION", result["error"])

    def test_upload_disabled_by_default(self):
        result = self.executor.execute("upload", ["READ"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("disabled", result["error"].lower())

    def test_execute_disabled_by_default(self):
        result = self.executor.execute("execute", ["READ"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("disabled", result["error"].lower())

    def test_click_not_implemented(self):
        result = self.executor.execute("click", ["READ", "INTERACT"])
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")

    def test_input_not_implemented(self):
        result = self.executor.execute("input", ["READ", "INTERACT"])
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")

    def test_navigate_no_url(self):
        result = self.executor.execute("navigate", ["READ"], {})
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("No URL", result["error"])

    def test_navigate_file_url_blocked(self):
        result = self.executor.execute("navigate", ["READ"], {"url": "file:///etc/passwd"})
        self.assertEqual(result["status"], "BLOCKED")

    def test_search_no_query(self):
        result = self.executor.execute("search", ["READ"], {})
        self.assertEqual(result["status"], "FAILED")

    def test_read_without_navigate(self):
        result = self.executor.execute("read", ["READ"])
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("No page loaded", result["error"])

    def test_snapshot(self):
        snap = self.executor.snapshot()
        self.assertEqual(snap["executor_type"], "LocalBrowserExecutor")
        self.assertIn("capabilities", snap)
        self.assertIn("forbidden_actions", snap)
        self.assertEqual(len(snap["forbidden_actions"]), len(FORBIDDEN_ACTIONS))

    def test_global_singleton(self):
        e1 = get_browser_executor()
        e2 = get_browser_executor()
        self.assertIs(e1, e2)


class TestIntegrationSnapshot(unittest.TestCase):
    """集成层快照。"""

    def test_snapshot_structure(self):
        snap = identity_integration_snapshot()
        self.assertIn("active_contexts", snap)
        self.assertIn("total_contexts", snap)
        self.assertIn("identity_registry", snap)
        self.assertIn("delegation_manager", snap)
        self.assertIn("browser_registry", snap)

    def test_create_and_get_context(self):
        ctx = create_agent_context("u1", "a1", "t1")
        retrieved = get_agent_context(ctx.context_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.agent_identity, "a1")

    def test_get_nonexistent_context(self):
        self.assertIsNone(get_agent_context("AIC-nonexistent"))


class TestV3IntegrationCompatibility(unittest.TestCase):
    """V3 集成层不破坏现有模块。"""

    def test_agent_identity_still_works(self):
        from osai_engine.agent_identity import IdentityChain
        chain = IdentityChain("user", "test")
        self.assertEqual(len(chain.get_chain()), 1)

    def test_delegation_still_works(self):
        from osai_engine.delegation import DelegationContext
        d = DelegationContext("u", "a", {}, "t", ["READ"])
        d.approve("u")
        self.assertTrue(d.is_active())

    def test_browser_capability_still_works(self):
        from osai_engine.browser_capability import get_browser_registry
        reg = get_browser_registry()
        self.assertIsNotNone(reg.snapshot())

    def test_skill_modules_still_importable(self):
        from osai_engine import skill_manifest, skill_selector, skill_invocation, skill_sync
        self.assertTrue(hasattr(skill_manifest, "validate_manifest"))
        self.assertTrue(hasattr(skill_selector, "get_selector"))
        self.assertTrue(hasattr(skill_invocation, "get_invoker"))
        self.assertTrue(hasattr(skill_sync, "get_skill_sync"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
