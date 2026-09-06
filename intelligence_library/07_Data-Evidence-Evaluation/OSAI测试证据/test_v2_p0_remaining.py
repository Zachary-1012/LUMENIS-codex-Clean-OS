"""V2 P0-4/6/8/10/12/14/15/16/17 综合测试"""
import sys
import pytest
import tempfile
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestP0_4_EvidenceGraph:
    def test_create_nodes_and_edges(self):
        from osai_engine.evidence_graph import EvidenceGraph
        g = EvidenceGraph()
        src = g.add_node("source", canonical_id="src_1", label="test source")
        ev = g.add_node("evidence", canonical_id="ev_1", label="test evidence")
        g.add_edge(src.node_id, ev.node_id, "derived_from")
        assert g.summary()["nodes"] == 2
        assert g.summary()["edges"] == 1

    def test_trace_to_source(self):
        from osai_engine.evidence_graph import EvidenceGraph
        g = EvidenceGraph()
        src = g.add_node("source", label="root")
        ev = g.add_node("evidence", label="mid")
        dec = g.add_node("decision", label="leaf")
        g.add_edge(ev.node_id, src.node_id, "derived_from")
        g.add_edge(dec.node_id, ev.node_id, "derived_from")
        sources = g.trace_to_source(dec.node_id)
        assert len(sources) == 1
        assert sources[0].label == "root"


class TestP0_8_TraceEvaluation:
    def test_evaluate_good_trace(self):
        from osai_engine.trace_evaluation import TraceEvaluator
        ev = TraceEvaluator()
        result = ev.evaluate({
            "trace_id": "t1",
            "spans": [
                {"status": "completed", "latency_ms": 100, "type": "skill"},
                {"status": "completed", "latency_ms": 200, "type": "evidence"},
                {"status": "completed", "latency_ms": 50, "type": "evaluation"},
            ],
        })
        assert result.grade in ("EXCELLENT", "GOOD", "FAIR")
        assert result.metrics.completed_spans == 3
        assert result.metrics.evidence_nodes == 1

    def test_evaluate_failed_trace(self):
        from osai_engine.trace_evaluation import TraceEvaluator
        ev = TraceEvaluator()
        result = ev.evaluate({
            "trace_id": "t2",
            "spans": [
                {"status": "failed", "latency_ms": 100, "type": "skill"},
                {"status": "failed", "latency_ms": 200, "type": "engine"},
            ],
        })
        assert result.metrics.has_error is True
        assert "no evidence" in result.issues or result.metrics.evidence_nodes == 0


class TestP0_10_Checkpoint:
    def test_save_and_resume(self):
        from osai_engine.checkpoint_resume import CheckpointManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(storage_dir=tmpdir)
            mgr.save("task_1", step=3, total_steps=10, state="RUNNING", data={"x": 1})
            prog = mgr.progress("task_1")
            assert prog["progress"] == 30.0
            resume = mgr.resume("task_1")
            assert resume["resumable"] is True
            assert resume["from_step"] == 3

    def test_completed_not_resumable(self):
        from osai_engine.checkpoint_resume import CheckpointManager
        mgr = CheckpointManager()
        mgr.save("task_2", step=10, total_steps=10, state="COMPLETED")
        resume = mgr.resume("task_2")
        assert resume["resumable"] is False


class TestP0_12_AgentIdentity:
    def test_identity_chain(self):
        from osai_engine.agent_identity import IdentityRegistry
        reg = IdentityRegistry()
        user = reg.create_identity("user", "testuser", permissions=["READ", "WRITE"])
        agent = reg.create_identity("agent", "agent-1",
                                    parent_identity=user.identity_id,
                                    permissions=["READ"])
        chain = reg.get_chain(agent.identity_id)
        assert len(chain) == 2
        assert chain[0].identity_type == "user"

    def test_permission_inheritance(self):
        from osai_engine.agent_identity import IdentityRegistry
        reg = IdentityRegistry()
        user = reg.create_identity("user", "u", permissions=["ALL"])
        agent = reg.create_identity("agent", "a", parent_identity=user.identity_id)
        assert reg.check_permission(agent.identity_id, "COMMIT") is True

    def test_audit_log(self):
        from osai_engine.agent_identity import IdentityRegistry
        reg = IdentityRegistry()
        agent = reg.create_identity("agent", "a")
        rec = reg.audit(agent.identity_id, "invoke", "skill_1", "ALLOW")
        assert rec.result == "ALLOW"
        assert len(reg.get_audit_trail()) == 1


class TestP0_14_OBO_JIT:
    def test_delegation(self):
        from osai_engine.agent_identity import IdentityRegistry
        from osai_engine.obo_jit import DelegationManager
        reg = IdentityRegistry()
        user = reg.create_identity("user", "u", permissions=["READ", "EXECUTE"])
        agent = reg.create_identity("agent", "a", parent_identity=user.identity_id,
                                    permissions=["READ"])
        mgr = DelegationManager(reg)
        ctx = mgr.delegate(user.identity_id, agent.identity_id,
                          permissions=["EXECUTE"], intent="run skill")
        check = mgr.check_delegation(ctx.delegation_id, "EXECUTE")
        assert check["allowed"] is True

    def test_jit_elevation(self):
        from osai_engine.agent_identity import IdentityRegistry
        from osai_engine.obo_jit import DelegationManager
        reg = IdentityRegistry()
        user = reg.create_identity("user", "u", permissions=["ALL"])
        agent = reg.create_identity("agent", "a", parent_identity=user.identity_id,
                                    permissions=["READ"])
        mgr = DelegationManager(reg)
        ctx = mgr.delegate(user.identity_id, agent.identity_id, permissions=["READ"])
        elevated = mgr.jit_elevate(ctx.delegation_id, ["COMMIT"], duration_seconds=60)
        assert elevated.jit_elevation is True
        assert "COMMIT" in elevated.permissions

    def test_execution_attribution(self):
        from osai_engine.agent_identity import IdentityRegistry
        from osai_engine.obo_jit import DelegationManager
        reg = IdentityRegistry()
        user = reg.create_identity("user", "u", permissions=["ALL"])
        agent = reg.create_identity("agent", "a", parent_identity=user.identity_id)
        mgr = DelegationManager(reg)
        ctx = mgr.delegate(user.identity_id, agent.identity_id, permissions=["EXECUTE"])
        attr = mgr.attribute_execution(ctx.delegation_id, "invoke_skill", "S01", "success")
        assert attr.initiated_by == user.identity_id
        assert attr.executed_by == agent.identity_id


class TestP0_15_DecisionActionOutcome:
    def test_full_dao_chain(self):
        from osai_engine.decision_action_outcome import DecisionActionOutcomeEngine
        engine = DecisionActionOutcomeEngine()
        decision = engine.create_decision("test decision", "do something", decided_by="human")
        result = engine.execute(
            decision, action_type="test_action", action_title="run test",
            parameters={"x": 1},
            executor=lambda params: {"status": "success", "metrics": {"time": 0.1}},
        )
        assert result.status == "COMPLETED"
        assert result.outcome is not None
        assert result.evaluation is not None
        assert result.action.status == "completed"

    def test_permission_blocked(self):
        from osai_engine.decision_action_outcome import DecisionActionOutcomeEngine
        engine = DecisionActionOutcomeEngine()
        decision = engine.create_decision("d", "c")
        result = engine.execute(
            decision, action_type="x", action_title="y",
            permission_check=lambda: (False, "not allowed"),
        )
        assert result.status == "BLOCKED"


class TestP0_16_ProductionEvidence:
    def test_create_and_verify(self):
        from production_evidence_contract import ProductionEvidenceContract
        c = ProductionEvidenceContract()
        ev = c.create_evidence("subject_rule_change", "test", {"words": ["x"]},
                               ai_assisted=True)
        assert ev.status == "CREATED"
        c.verify(ev.evidence_id, verified_by="rule")
        assert ev.status == "VERIFIED"

    def test_ai_protected_requires_human(self):
        from production_evidence_contract import ProductionEvidenceContract
        c = ProductionEvidenceContract()
        ev = c.create_evidence("subject_rule_change", "t", {}, ai_assisted=True)
        c.verify(ev.evidence_id)
        assert c.require_human_approval(ev.evidence_id) is True
        check = c.can_execute_production_change(ev.evidence_id)
        assert check["allowed"] is False
        c.approve(ev.evidence_id)
        check2 = c.can_execute_production_change(ev.evidence_id)
        assert check2["allowed"] is True


class TestP0_17_UIRealityAudit:
    def test_audit_page_with_api(self):
        from ui_data_audit import UIRealityAuditor
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = os.path.join(tmpdir, "templates")
            os.makedirs(tdir)
            with open(os.path.join(tdir, "test.html"), "w", encoding="utf-8") as f:
                f.write('<script>fetch("/api/data")</script>')
            auditor = UIRealityAuditor(tdir, tmpdir)
            status = auditor.audit_page("p1", "Test", "/test", "test.html")
            assert status.connection_status == "CONNECTED"

    def test_audit_page_with_fake_data(self):
        from ui_data_audit import UIRealityAuditor
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = os.path.join(tmpdir, "templates")
            os.makedirs(tdir)
            with open(os.path.join(tdir, "fake.html"), "w", encoding="utf-8") as f:
                f.write('<div>sample_data = [1,2,3]</div>')
            auditor = UIRealityAuditor(tdir, tmpdir)
            status = auditor.audit_page("p2", "Fake", "/fake", "fake.html")
            assert status.connection_status == "UI_ONLY"
            assert len(status.fake_data_indicators) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
