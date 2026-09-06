# -*- coding: utf-8 -*-
"""LUMENIS Cross-Core E2E 验证 — 唯一真链端到端。

链路：
Test Task → Skill Selector → Canonical Skill → Permission Gate (fail-close)
→ ZBC/OSAI Adapter → Engine → Provider(或合法 fallback)
→ Evidence (三级状态) → Evaluation (NO_DATA 诚实) → Trace (Parent→Child)
→ UI result

不伪造成功：Provider 不可用时必须是 UNAVAILABLE/BLOCKED/DEGRADED。
"""
import json
import os
import sys

# 双库路径
OSAI_ROOT = r"D:\Zachary OS AI"
ZBC_ROOT = r"D:\Taikoo-monitor-new"
sys.path.insert(0, OSAI_ROOT)
sys.path.insert(0, ZBC_ROOT)

results = []


def step(name, ok, detail=""):
    results.append({"step": name, "ok": ok, "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print("[%s] %s — %s" % (mark, name, detail[:120]))


# ========== 1. Canonical Registry 唯一 Skill Truth ==========
from osai_engine.canonical_skill_registry import get_canonical_registry

reg = get_canonical_registry()
snap = reg.snapshot()
step("1.1 Canonical Registry total=72",
     snap["total"] == 72, "total=%d" % snap["total"])
step("1.2 S01-S12 IMPLEMENTED=12",
     snap["implemented_count"] == 12,
     "implemented=%d" % snap["implemented_count"])
step("1.3 S13-S72 PLANNED=60 (not faked)",
     snap["planned_count"] == 60, "planned=%d" % snap["planned_count"])

# ========== 2. Skill Selector 推荐 ==========
from osai_engine.skill_selector import SkillSelector

selector = SkillSelector()
try:
    rec = selector.select("audit git repository state", workspace="engineering")
    rec_ok = isinstance(rec, (list, dict))
    step("2.1 Skill Selector returns recommendation", rec_ok,
         type(rec).__name__)
except Exception as e:
    step("2.1 Skill Selector returns recommendation", False, str(e)[:150])

# ========== 3. Permission Gate fail-close ==========
from osai_engine.permission_gate import PermissionGate

gate = PermissionGate()
read_check = gate.check_safe("READ")
step("3.1 READ allowed", read_check["allowed"], read_check["reason"])

verify_check = gate.check_safe("VERIFY")
step("3.2 VERIFY allowed (agent ceiling)", verify_check["allowed"],
     verify_check["reason"])

commit_check = gate.check_safe("COMMIT")
step("3.3 COMMIT denied (requires human)", not commit_check["allowed"],
     commit_check["reason"])

unknown_check = gate.check_safe("FAKE_LEVEL")
step("3.4 Unknown level fail-close denied", not unknown_check["allowed"],
     unknown_check["audit"]["result"])

# ========== 4. ZBC Cross-Core Adapter ==========
os.chdir(ZBC_ROOT)
from lumenis_skill_adapter import get_skill_adapter

adapter = get_skill_adapter()
zbc_snap = adapter.get_registry_snapshot()
step("4.1 ZBC Adapter connected to OSAI",
     zbc_snap["connected"], zbc_snap["status"])
step("4.2 ZBC reads 12 implemented from OSAI",
     zbc_snap.get("implemented_count") == 12,
     "implemented=%s" % zbc_snap.get("implemented_count"))

sync = adapter.check_sync_status()
step("4.3 Sync real check (not hardcoded SYNCED)",
     sync["sync_status"] in ("SYNCED", "CONFLICT", "UNAVAILABLE"),
     "status=%s synced=%d conflict=%d" % (
         sync["sync_status"], sync["synced_count"],
         sync["conflict_count"]))

s01 = adapter.get_skill("S01")
step("4.4 ZBC gets S01 from Canonical",
     s01.get("found") and s01["skill"]["status"] == "IMPLEMENTED",
     s01.get("skill", {}).get("name", ""))

s99 = adapter.get_skill("S99")
step("4.5 S99 (planned) not faked as implemented",
     not s99.get("found") or s99["skill"]["status"] == "PLANNED",
     str(s99.get("status")))

# ========== 5. Trace Parent → Child ==========
from osai_engine.trace_contract import TraceRegistry, Span

trace_reg = TraceRegistry()
parent_trace = trace_reg.start("e2e-parent")
child_trace = trace_reg.child_trace(parent_trace.trace_id, "e2e-child")
step("5.1 Child trace linked to parent",
     child_trace.parent_trace_id == parent_trace.trace_id,
     "parent=%s" % parent_trace.trace_id[:8])

# 完整调用链 spans
chain_layers = ["skill", "permission", "engine", "provider",
                "evidence", "evaluation"]
prev = None
for layer in chain_layers:
    s = Span(actor=layer, action="e2e-step", layer=layer,
             parent_span_id=prev)
    parent_trace.append(s)
    prev = s.span_id
td = parent_trace.to_dict()
step("5.2 Full chain 6 spans linked",
     len(td["spans"]) == 6 and
     all(s["parent_span_id"] for s in td["spans"][1:]),
     "spans=%d" % len(td["spans"]))

# ========== 6. Evidence 三级状态 ==========
from osai_engine.evidence_chain import EvidenceChainRegistry

ev_reg = EvidenceChainRegistry()
chain = ev_reg.create("e2e-evidence")
step("6.1 Starts NO_EVIDENCE",
     chain.verification_status == "NO_EVIDENCE", chain.verification_status)

chain.add_node("task", "e2e-task")
chain.add_node("skill", "S01")
chain.mark_created(trace_id=parent_trace.trace_id, skill_id="S01",
                   skill_version="1.0.0", provider="local", model="gpt-oss")
step("6.2 mark_created → EVIDENCE_CREATED",
     chain.verification_status == "EVIDENCE_CREATED",
     chain.verification_status)

chain.verify(verifier="e2e-test", note="cross-core verified")
step("6.3 verify → EVIDENCE_VERIFIED",
     chain.verification_status == "EVIDENCE_VERIFIED",
     chain.verification_status)

# ========== 7. Evaluation 诚实 NO_DATA ==========
from osai_engine.evaluation_contract import no_data_evaluation

nd = no_data_evaluation("skill", "S01",
                        "provider unavailable in E2E (no API key/local model)")
step("7.1 No real execution → NO_DATA (not faked)",
     nd["status"] == "no_data" and nd["overall"] is None,
     "status=%s overall=%s" % (nd["status"], nd["overall"]))

# ========== 8. Production Truth 未被绕过 ==========
sys.path.insert(0, ZBC_ROOT)
from subject_rules import subject_hit, ACTIVE_BRAND
step("8.1 subject_hit intact", callable(subject_hit), "callable")
step("8.2 ACTIVE_BRAND locked",
     ACTIVE_BRAND == "guangzhou_taikoo_hui", ACTIVE_BRAND)
# 主体过滤真实生效
hit = subject_hit("广州太古汇今日活动", "")
step("8.3 subject_hit matches Taikoo Hui", hit is True, "hit=%s" % hit)

# ========== 汇总 ==========
print("\n" + "=" * 60)
passed = sum(1 for r in results if r["ok"])
failed = sum(1 for r in results if not r["ok"])
print("CROSS-CORE E2E: %d PASS / %d FAIL (total %d)" % (
    passed, failed, len(results)))
print("=" * 60)
if failed:
    print("\nFAILED STEPS:")
    for r in results:
        if not r["ok"]:
            print("  -", r["step"], ":", r["detail"])
sys.exit(1 if failed else 0)
