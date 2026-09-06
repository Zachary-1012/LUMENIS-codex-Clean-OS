# -*- coding: utf-8 -*-
"""ZBC/LUMENIS P1 Skill 体系完善 — 综合测试（43 tests）"""
import json, os, sys, unittest
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


class TestSkillRegistryAdapter(unittest.TestCase):
    def test_builtin_skills_have_product_domain(self):
        from skill_registry import get_skill_registry
        reg = get_skill_registry()
        for s in reg.list_all():
            self.assertTrue(hasattr(s, 'product'))
            self.assertIn(s.product, ("SYSTEM", "ZBMP", "CTH", "SHARED"))
    def test_registry_stats(self):
        from skill_registry import get_skill_registry
        self.assertGreater(get_skill_registry().stats()["total"], 0)


class TestSkillExecutionChain(unittest.TestCase):
    def test_permission_allows_read(self):
        from skill_execution_chain import check_permission, SkillExecutionContext, ActionType, SkillRuntimeInfo
        ctx = SkillExecutionContext(skill_id="t", action_type=ActionType.READ)
        self.assertTrue(check_permission(ctx, "user", SkillRuntimeInfo(skill_id="t", enabled=True, product="SYSTEM"))["allowed"])
    def test_permission_denies_disabled(self):
        from skill_execution_chain import check_permission, SkillExecutionContext, ActionType, SkillRuntimeInfo
        ctx = SkillExecutionContext(skill_id="t", action_type=ActionType.READ)
        r = check_permission(ctx, "owner", SkillRuntimeInfo(skill_id="t", enabled=False, product="SYSTEM"))
        self.assertFalse(r["allowed"]); self.assertEqual(r["code"], "SKILL_DISABLED")
    def test_cross_domain_denied(self):
        from skill_execution_chain import check_permission, SkillExecutionContext, ActionType, SkillRuntimeInfo
        ctx = SkillExecutionContext(skill_id="t", action_type=ActionType.READ, product="ZBMP")
        r = check_permission(ctx, "user", SkillRuntimeInfo(skill_id="t", enabled=True, product="CTH"))
        self.assertFalse(r["allowed"]); self.assertEqual(r["code"], "CROSS_DOMAIN_DENIED")
    def test_cross_domain_allowed_with_auth(self):
        from skill_execution_chain import check_permission, SkillExecutionContext, ActionType, SkillRuntimeInfo
        ctx = SkillExecutionContext(skill_id="t", action_type=ActionType.READ, product="ZBMP")
        r = check_permission(ctx, "user", SkillRuntimeInfo(skill_id="t", enabled=True, product="CTH", cross_domain_allowed=["ZBMP"]))
        self.assertTrue(r["allowed"])
    def test_firewall_allows_read(self):
        from skill_execution_chain import action_firewall, SkillExecutionContext, ActionType
        self.assertTrue(action_firewall(SkillExecutionContext(action_type=ActionType.READ))["allowed"])
    def test_firewall_denies_push(self):
        from skill_execution_chain import action_firewall, SkillExecutionContext, ActionType
        r = action_firewall(SkillExecutionContext(action_type=ActionType.PUSH))
        self.assertFalse(r["allowed"])
    def test_firewall_restricts_write(self):
        from skill_execution_chain import action_firewall, SkillExecutionContext, ActionType
        r = action_firewall(SkillExecutionContext(action_type=ActionType.WRITE))
        self.assertTrue(r["allowed"]); self.assertEqual(r["decision"], "RESTRICTED")
    def test_effect_fence_write(self):
        from skill_execution_chain import effect_fence, SkillExecutionContext, ActionType
        r = effect_fence(SkillExecutionContext(action_type=ActionType.WRITE))
        self.assertTrue(r["writes_production"]); self.assertFalse(r["auto_admit"])
    def test_state_machine(self):
        from skill_execution_chain import transition_state, SkillState
        self.assertTrue(transition_state(SkillState.REGISTERED, SkillState.ENABLED)[0])
        self.assertFalse(transition_state(SkillState.REGISTERED, SkillState.RUNNING)[0])
    def test_full_chain_read(self):
        from skill_execution_chain import run_execution_chain, ActionType, SkillRuntimeInfo, ExecutionStatus
        ctx = run_execution_chain("zbc.skill_registry_snapshot", "test", action_type=ActionType.READ,
                                   user_role="owner", skill_info=SkillRuntimeInfo(skill_id="x", enabled=True, product="SYSTEM"))
        self.assertEqual(ctx.status, ExecutionStatus.COMPLETED)
        self.assertIsNotNone(ctx.firewall_result)
    def test_full_chain_rejects_push(self):
        from skill_execution_chain import run_execution_chain, ActionType, SkillRuntimeInfo, ExecutionStatus
        ctx = run_execution_chain("zbc.skill_registry_snapshot", "push", action_type=ActionType.PUSH,
                                   user_role="user", skill_info=SkillRuntimeInfo(skill_id="x", enabled=True, product="SYSTEM"))
        self.assertEqual(ctx.status, ExecutionStatus.REJECTED)
    def test_executions_table(self):
        from skill_execution_chain import ensure_skill_executions_table, query_executions
        ensure_skill_executions_table()
        self.assertIsInstance(query_executions(limit=5), list)
    def test_light_status(self):
        from skill_execution_chain import get_skills_light_status
        self.assertGreater(len(get_skills_light_status()), 0)


class TestP2MemoryGovernance(unittest.TestCase):
    def test_states_enum(self):
        from p2_memory_governance import MemoryState
        for s in ["RAW", "OBSERVATION", "CANDIDATE", "VALIDATED", "GENERALIZABLE", "ADMITTED", "CONFLICT", "REVOKED"]:
            self.assertIn(s, [x.value for x in MemoryState])
    def test_lifecycle(self):
        from p2_memory_governance import MemoryGovernor, MemoryRecord, MemoryState
        g = MemoryGovernor(); g.register(MemoryRecord(memory_id="t1", content="x"))
        for s in [MemoryState.OBSERVATION, MemoryState.CANDIDATE, MemoryState.VALIDATED, MemoryState.GENERALIZABLE, MemoryState.ADMITTED]:
            self.assertTrue(g.transition("t1", s)["success"])
    def test_invalid_transition(self):
        from p2_memory_governance import MemoryGovernor, MemoryRecord, MemoryState
        g = MemoryGovernor(); g.register(MemoryRecord(memory_id="t2", content="x"))
        self.assertFalse(g.transition("t2", MemoryState.VALIDATED)["success"])
    def test_revoke(self):
        from p2_memory_governance import MemoryGovernor, MemoryRecord
        g = MemoryGovernor(); r = MemoryRecord(memory_id="t3", content="x"); g.register(r)
        self.assertTrue(g.revoke("t3", "test")["success"])
        self.assertNotIn(r, g.get_active())
    def test_conflict(self):
        from p2_memory_governance import MemoryGovernor, MemoryRecord, MemoryState
        g = MemoryGovernor(); g.register(MemoryRecord(memory_id="t4", content="x"))
        g.transition("t4", MemoryState.CANDIDATE)
        self.assertTrue(g.mark_conflict("t4", ["other"])["success"])


class TestP2ActionFirewall(unittest.TestCase):
    def test_read_allowed(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        self.assertTrue(validate_action(ActionRequest(identity="a", intent="r", tool="t", parameters={}, target="l", action=AgentAction.READ, user_role="user")).allowed)
    def test_push_denied(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        self.assertFalse(validate_action(ActionRequest(identity="a", intent="p", tool="g", parameters={}, target="o", action=AgentAction.PUSH, user_role="user")).allowed)
    def test_write_user_denied(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        self.assertFalse(validate_action(ActionRequest(identity="a", intent="w", tool="d", parameters={}, target="l", action=AgentAction.WRITE, user_role="user")).allowed)
    def test_write_owner_restricted(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        r = validate_action(ActionRequest(identity="o", intent="w", tool="d", parameters={}, target="l", action=AgentAction.WRITE, user_role="owner"))
        self.assertTrue(r.allowed); self.assertEqual(r.decision, "RESTRICTED")
    def test_sensitive_params(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        self.assertFalse(validate_action(ActionRequest(identity="a", intent="r", tool="d", parameters={"password": "x"}, target="l", action=AgentAction.READ, user_role="owner")).allowed)
    def test_deploy_requires_approval(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        r = validate_action(ActionRequest(identity="o", intent="d", tool="d", parameters={}, target="s", action=AgentAction.DEPLOY, user_role="owner"))
        self.assertFalse(r.allowed); self.assertEqual(r.decision, "APPROVAL_REQUIRED"); self.assertTrue(r.requires_approval)
    def test_prod_db_write_hard_denied(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        r = validate_action(ActionRequest(identity="o", intent="w", tool="d", parameters={}, target="production_db", action=AgentAction.WRITE, user_role="owner"))
        self.assertFalse(r.allowed); self.assertIn("production", r.reason.lower())
    def test_prod_db_deploy_hard_denied(self):
        from p2_action_firewall import validate_action, ActionRequest, AgentAction
        r = validate_action(ActionRequest(identity="o", intent="d", tool="d", parameters={}, target="prod_db", action=AgentAction.DEPLOY, user_role="owner"))
        self.assertFalse(r.allowed)
    def test_execution_chain_p2_integration(self):
        from skill_execution_chain import run_execution_chain, ActionType, SkillRuntimeInfo, ExecutionStatus
        ctx = run_execution_chain("zbc.skill_registry_snapshot", "p2 test", action_type=ActionType.READ,
                                   user_role="owner", skill_info=SkillRuntimeInfo(skill_id="x", enabled=True, product="SYSTEM"))
        self.assertEqual(ctx.status, ExecutionStatus.COMPLETED)
        self.assertIsNotNone(ctx.firewall_result)


class TestP2ShadowReplay(unittest.TestCase):
    def test_identical(self):
        from p2_shadow_replay import shadow_compare, ComparisonResult
        self.assertEqual(shadow_compare("c1", {}, lambda x: {"v": 1}, lambda x: {"v": 1}).comparison, ComparisonResult.IDENTICAL)
    def test_different(self):
        from p2_shadow_replay import shadow_compare, ComparisonResult
        self.assertEqual(shadow_compare("c2", {}, lambda x: {"v": 1}, lambda x: {"v": 2}).comparison, ComparisonResult.DIFFERENT)
    def test_new_only(self):
        from p2_shadow_replay import shadow_compare, ComparisonResult
        self.assertEqual(shadow_compare("c3", {}, lambda x: 1/0, lambda x: {"v": 1}).comparison, ComparisonResult.NEW_ONLY)
    def test_replay_batch(self):
        from p2_shadow_replay import replay_batch
        r = replay_batch([{"case_id": f"c{i}", "input": {}} for i in range(3)], lambda x: {"v": 1}, lambda x: {"v": 1})
        self.assertEqual(r["total"], 3); self.assertEqual(r["pass_rate"], 1.0)


class TestP2FaultInjection(unittest.TestCase):
    def test_not_active(self):
        from p2_fault_injection import FaultInjector, FaultType
        self.assertFalse(FaultInjector().simulate_osai_unavailable().injected)
    def test_osai_unavailable(self):
        from p2_fault_injection import FaultInjector, FaultType
        i = FaultInjector(); i.enable(FaultType.OSAI_UNAVAILABLE)
        r = i.simulate_osai_unavailable(); self.assertTrue(r.injected); self.assertFalse(r.response["connected"])
    def test_cookie_expired(self):
        from p2_fault_injection import FaultInjector, FaultType
        i = FaultInjector(); i.enable(FaultType.COOKIE_EXPIRED)
        self.assertTrue(i.simulate_cookie_expired().injected)
    def test_db_locked(self):
        from p2_fault_injection import FaultInjector, FaultType
        i = FaultInjector(); i.enable(FaultType.DB_LOCKED)
        self.assertTrue(i.simulate_db_locked().injected)
    def test_run_with_fault(self):
        from p2_fault_injection import FaultInjector, FaultType
        i = FaultInjector(); i.enable(FaultType.OSAI_UNAVAILABLE)
        calls = []
        r = i.run_with_fault(lambda: calls.append(1) or {"ok": True}, FaultType.OSAI_UNAVAILABLE)
        self.assertTrue(r["fault_injected"]); self.assertEqual(len(calls), 0)
    def test_run_without_fault(self):
        from p2_fault_injection import FaultInjector, FaultType
        i = FaultInjector()
        r = i.run_with_fault(lambda: {"ok": True}, FaultType.OSAI_UNAVAILABLE)
        self.assertFalse(r["fault_injected"]); self.assertEqual(r["original_result"], {"ok": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)
