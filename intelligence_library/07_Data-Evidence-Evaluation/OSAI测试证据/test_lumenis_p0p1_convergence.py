# -*- coding: utf-8 -*-
"""LUMENIS P0/P1 源码收敛测试 — 唯一真链验证。

覆盖：
1. Canonical Skill Registry（唯一 Skill Truth，S01-S12 IMPLEMENTED / S13-S72 PLANNED）
2. Permission Gate fail-close（异常不允许放行）
3. Evidence 三级状态（NO_EVIDENCE / CREATED / VERIFIED）
4. Evaluation NO_DATA（无真实执行不伪造分数）
5. Trace Parent→Child Span（统一 trace_id 可回溯）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine.canonical_skill_registry import (
    get_canonical_registry, canonical_snapshot, get_canonical_skill)
from osai_engine.permission_gate import PermissionGate
from osai_engine.evidence_chain import (
    EvidenceChainRegistry, EVIDENCE_STATUSES)
from osai_engine.evaluation_contract import (
    no_data_evaluation, EVAL_STATUSES)
from osai_engine.trace_contract import TraceRegistry, Span


class TestCanonicalSkillRegistry(unittest.TestCase):
    """硬问题②：OSAI Skill Manifest/Registry 双 Truth 收敛。"""

    def setUp(self):
        self.reg = get_canonical_registry()

    def test_total_72(self):
        snap = self.reg.snapshot()
        self.assertEqual(snap["total"], 72)

    def test_s01_s12_implemented(self):
        snap = self.reg.snapshot()
        self.assertEqual(snap["implemented_count"], 12)
        impl_ids = snap["implemented_ids"]
        for i in range(1, 13):
            sid = "S%02d" % i
            self.assertIn(sid, impl_ids, "%s must be IMPLEMENTED" % sid)

    def test_s13_s72_planned(self):
        snap = self.reg.snapshot()
        self.assertEqual(snap["planned_count"], 60)
        for i in range(13, 73):
            sid = "S%02d" % i
            skill = self.reg.get_skill(sid)
            self.assertEqual(skill["status"], "PLANNED",
                             "%s must be PLANNED not faked as implemented" % sid)

    def test_no_fake_implementation(self):
        """S13-S72 目录存在不等于已实现。"""
        for i in range(13, 73):
            sid = "S%02d" % i
            self.assertFalse(self.reg.is_implemented(sid),
                             "%s must not be reported as implemented" % sid)

    def test_get_skill_has_required_fields(self):
        s = self.reg.get_skill("S01")
        for field in ("id", "name", "version", "category", "status",
                      "permissions", "type"):
            self.assertIn(field, s)

    def test_snapshot_categories(self):
        snap = self.reg.snapshot()
        self.assertIn("categories", snap)
        self.assertIsInstance(snap["categories"], (list, dict))

    def test_module_singleton_function(self):
        snap = canonical_snapshot()
        self.assertEqual(snap["total"], 72)
        s = get_canonical_skill("S12")
        self.assertEqual(s["id"], "S12")
        self.assertEqual(s["status"], "IMPLEMENTED")


class TestPermissionGateFailClose(unittest.TestCase):
    """硬问题③：Permission Gate 异常必须 fail-close，不允许放行。"""

    def setUp(self):
        self.gate = PermissionGate()

    def test_check_safe_returns_dict(self):
        result = self.gate.check_safe("READ")
        self.assertIn("allowed", result)
        self.assertIn("reason", result)
        self.assertIn("level", result)
        self.assertIn("audit", result)

    def test_read_allowed(self):
        result = self.gate.check_safe("READ")
        self.assertTrue(result["allowed"])

    def test_unknown_level_denied(self):
        result = self.gate.check_safe("NONEXISTENT_LEVEL_XYZ")
        self.assertFalse(result["allowed"])
        self.assertIn("DENY", result["audit"]["result"])

    def test_commit_denied_without_approval(self):
        result = self.gate.check_safe("COMMIT")
        self.assertFalse(result["allowed"])

    def test_push_denied_without_approval(self):
        result = self.gate.check_safe("PUSH")
        self.assertFalse(result["allowed"])

    def test_agent_cannot_exceed_verify(self):
        """Agent 默认上限 VERIFY，HUMAN_APPROVAL/COMMIT/PUSH 必须拒绝。"""
        for level in ("HUMAN_APPROVAL", "COMMIT", "PUSH"):
            result = self.gate.check_safe(level)
            self.assertFalse(result["allowed"],
                             "%s must be denied for agent" % level)

    def test_no_exception_pass_through(self):
        """即使传入异常参数，也不允许抛异常后被 except 吞掉放行。"""
        # None 作为 level 必须返回 deny 而不是抛异常
        result = self.gate.check_safe(None)
        self.assertFalse(result["allowed"])


class TestEvidenceThreeLevelStatus(unittest.TestCase):
    """Evidence 收敛：NO_EVIDENCE → CREATED → VERIFIED。"""

    def test_status_enum_exists(self):
        self.assertEqual(
            EVIDENCE_STATUSES,
            ["NO_EVIDENCE", "EVIDENCE_CREATED", "EVIDENCE_VERIFIED"])

    def test_new_chain_starts_no_evidence(self):
        reg = EvidenceChainRegistry()
        chain = reg.create("task-test-1")
        self.assertEqual(chain.verification_status, "NO_EVIDENCE")

    def test_mark_created(self):
        reg = EvidenceChainRegistry()
        chain = reg.create("task-test-2")
        chain.mark_created(trace_id="T1", skill_id="S01",
                           skill_version="1.0.0", provider="local",
                           model="gpt-oss")
        self.assertEqual(chain.verification_status, "EVIDENCE_CREATED")
        self.assertEqual(chain.trace_ref, "T1")
        self.assertEqual(chain.skill_id, "S01")

    def test_verify_requires_created_first(self):
        reg = EvidenceChainRegistry()
        chain = reg.create("task-test-3")
        with self.assertRaises(ValueError):
            chain.verify()

    def test_full_lifecycle(self):
        reg = EvidenceChainRegistry()
        chain = reg.create("task-test-4")
        chain.add_node("task", "task-4")
        chain.mark_created(trace_id="T4")
        chain.verify(verifier="test", note="unit test verified")
        self.assertEqual(chain.verification_status, "EVIDENCE_VERIFIED")
        built = chain.build()
        self.assertEqual(built["verification_status"], "EVIDENCE_VERIFIED")
        self.assertEqual(built["verified_by"], "test")

    def test_build_contains_trace_fields(self):
        reg = EvidenceChainRegistry()
        chain = reg.create("task-test-5")
        chain.mark_created(trace_id="T5", skill_id="S03",
                           skill_version="1.0.0")
        built = chain.build()
        for field in ("trace_ref", "skill_id", "skill_version",
                      "verification_status"):
            self.assertIn(field, built)


class TestEvaluationNoData(unittest.TestCase):
    """Evaluation 收敛：无真实执行返回 NO_DATA，不伪造分数。"""

    def test_no_data_in_statuses(self):
        self.assertIn("no_data", EVAL_STATUSES)

    def test_no_data_evaluation_structure(self):
        ev = no_data_evaluation("skill", "S99",
                                reason="provider unavailable")
        self.assertEqual(ev["status"], "no_data")
        self.assertIsNone(ev["overall"])
        self.assertEqual(ev["criteria"], {})
        self.assertIsNone(ev["evidence_ref"])
        self.assertIn("provider unavailable", ev["note"])

    def test_no_data_has_id(self):
        ev = no_data_evaluation("task", "T1")
        self.assertTrue(ev["eval_id"].startswith("EVAL-NODATA-"))


class TestTraceParentChild(unittest.TestCase):
    """Trace 收敛：Parent Trace → Child Span 完整回溯。"""

    def test_start_trace(self):
        reg = TraceRegistry()
        tr = reg.start("task-1")
        self.assertIsNotNone(tr.trace_id)
        self.assertIsNone(tr.parent_trace_id)

    def test_child_trace_has_parent(self):
        reg = TraceRegistry()
        parent = reg.start("parent-task")
        child = reg.child_trace(parent.trace_id, "child-task")
        self.assertEqual(child.parent_trace_id, parent.trace_id)

    def test_span_has_span_id_and_layer(self):
        s = Span(actor="skill", action="execute", layer="skill")
        self.assertIsNotNone(s.span_id)
        self.assertEqual(s.layer, "skill")
        self.assertIsNone(s.parent_span_id)

    def test_span_parent_link(self):
        parent_span = Span(actor="agent", action="plan", layer="agent")
        child_span = Span(actor="engine", action="run",
                          layer="engine",
                          parent_span_id=parent_span.span_id)
        self.assertEqual(child_span.parent_span_id, parent_span.span_id)

    def test_full_trace_chain(self):
        """完整链：Agent → Skill → Engine → Provider → Evidence → Evaluation。"""
        reg = TraceRegistry()
        tr = reg.start("task-full")
        layers = ["agent", "skill", "engine", "provider",
                  "evidence", "evaluation"]
        prev_id = None
        for layer in layers:
            s = Span(actor=layer, action="step", layer=layer,
                     parent_span_id=prev_id)
            tr.append(s)
            prev_id = s.span_id
        d = tr.to_dict()
        self.assertEqual(len(d["spans"]), 6)
        # 每个 span 都有 layer 和 span_id
        for s in d["spans"]:
            self.assertIn("span_id", s)
            self.assertIn("layer", s)
            self.assertIn(s["layer"], layers)
        # 后一个 span 的 parent 是前一个
        for i in range(1, 6):
            self.assertEqual(d["spans"][i]["parent_span_id"],
                             d["spans"][i - 1]["span_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
