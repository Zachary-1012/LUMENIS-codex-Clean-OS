# -*- coding: utf-8 -*-
"""OSAI AI/Skill/Agent module call relationship matrix (Shard B Team 8/9).

Traces real import relationships between OSAI modules.
Categories: AI Provider, Skill Execution, Agent Identity, Permission/Security,
Evidence/Trace, Orchestration, Runtime.
"""
import os, re, json

OSAI = r"D:\Zachary OS AI\osai_engine"

# Modules in scope (AI/Skill/Agent related)
MODULES = {
    # AI Provider / Engine
    "ai_gateway": "AI Provider Gateway",
    "llm": "LLM Interface",
    "engine_runtime": "Engine Runtime (AI execution)",
    "context_runtime": "Context Builder",
    "research": "Research Pipeline",
    "research_pipeline": "Research Pipeline v2",
    # Skill Registry / Execution
    "skill_registry": "Skill Registry (legacy)",
    "canonical_skill_registry": "Canonical Skill Registry (truth)",
    "skill_invocation": "Skill Invocation (main chain)",
    "skill_execution_contract": "Skill Execution Contract",
    "skill_manifest": "Skill Manifest",
    "skill_selector": "Skill Selector",
    "skill_sync": "Skill Sync",
    # Agent / Identity
    "agent": "Agent Core",
    "agent_identity": "Agent Identity Registry",
    "agent_integration": "Agent Integration",
    "orchestrator": "Orchestrator",
    "harness_runtime": "Harness Runtime",
    "engineering_loop": "Engineering Loop",
    "delegation": "Delegation (legacy)",
    "obo_jit": "OBO/JIT Delegation",
    # Permission / Security
    "permission_gate": "Permission Gate",
    "permission_contract": "Permission Contract",
    "action_firewall": "Action Firewall",
    "effect_fence": "Effect Fence / Idempotency",
    "release_safety": "Release Safety",
    "runtime_guardian": "Runtime Guardian",
    # Evidence / Trace / Evaluation
    "evidence": "Evidence (legacy)",
    "evidence_chain": "Evidence Chain (persistence)",
    "evidence_graph": "Evidence Graph",
    "observability": "Observability / Trace",
    "trace_evaluation": "Trace Evaluation",
    "evaluation_contract": "Evaluation Contract",
    "decision_action_outcome": "Decision→Action→Outcome",
    "contract_persistence": "Contract Persistence",
    "learning_record_contract": "Learning Record Contract",
    # Canonical / Config
    "canonical_data": "Canonical Data Models",
    "capability_registry": "Capability Registry",
    "config": "OSAI Config",
    "rules": "Rules Engine",
    "tools": "Tools Registry",
    "impact_analysis": "Impact Analysis",
    "memory_lifecycle": "Memory Lifecycle",
    "lifecycle_contract": "Lifecycle Contract",
    "task_contract": "Task Contract",
    "runtime_contract": "Runtime Contract",
    "trace_contract": "Trace Contract",
    "ui_state_contract": "UI State Contract",
    "repository_contract": "Repository Contract",
    "repository_registry": "Repository Registry",
    "browser_capability": "Browser Capability",
    "browser_executor": "Browser Executor",
}

def parse_imports(filepath):
    """Extract osai_engine imports from a module file."""
    imports = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Match: from osai_engine.xxx import / from .xxx import / from osai_engine import (xxx, yyy)
        for m in re.finditer(r'from\s+(?:osai_engine\.)?\.?(\w+)\s+import', content):
            mod = m.group(1)
            if mod in MODULES:
                imports.add(mod)
        for m in re.finditer(r'from\s+osai_engine\s+import\s+\(([^)]+)\)', content, re.DOTALL):
            for name in re.findall(r'(\w+)', m.group(1)):
                if name in MODULES:
                    imports.add(name)
        for m in re.finditer(r'import\s+osai_engine\.(\w+)', content):
            if m.group(1) in MODULES:
                imports.add(m.group(1))
    except Exception:
        pass
    return imports

# Build adjacency matrix
matrix = {}
for mod_name in MODULES:
    filepath = os.path.join(OSAI, mod_name + ".py")
    if os.path.exists(filepath):
        deps = parse_imports(filepath)
        matrix[mod_name] = sorted(deps)
    else:
        matrix[mod_name] = []

# Categorize
categories = {
    "AI Provider/Engine": ["ai_gateway", "llm", "engine_runtime", "context_runtime", "research", "research_pipeline"],
    "Skill Registry/Execution": ["skill_registry", "canonical_skill_registry", "skill_invocation",
                                   "skill_execution_contract", "skill_manifest", "skill_selector", "skill_sync"],
    "Agent/Identity": ["agent", "agent_identity", "agent_integration", "orchestrator", "harness_runtime",
                        "engineering_loop", "delegation", "obo_jit"],
    "Permission/Security": ["permission_gate", "permission_contract", "action_firewall", "effect_fence",
                             "release_safety", "runtime_guardian"],
    "Evidence/Trace/Eval": ["evidence", "evidence_chain", "evidence_graph", "observability", "trace_evaluation",
                              "evaluation_contract", "decision_action_outcome", "contract_persistence",
                              "learning_record_contract"],
    "Canonical/Config/Runtime": ["canonical_data", "capability_registry", "config", "rules", "tools",
                                   "impact_analysis", "memory_lifecycle", "lifecycle_contract", "task_contract",
                                   "runtime_contract", "trace_contract", "ui_state_contract",
                                   "repository_contract", "repository_registry", "browser_capability",
                                   "browser_executor"],
}

# Print report
print("=" * 70)
print("OSAI AI/Skill/Agent Module Call Relationship Matrix (Shard B)")
print("=" * 70)
print(f"Total modules in scope: {len(MODULES)}")
print(f"Modules with files: {sum(1 for m in MODULES if os.path.exists(os.path.join(OSAI, m+'.py')))}")
total_deps = sum(len(v) for v in matrix.values())
print(f"Total import edges: {total_deps}")

for cat, mods in categories.items():
    print(f"\n--- {cat} ---")
    for mod in mods:
        deps = matrix.get(mod, [])
        status = "FILE_EXISTS" if os.path.exists(os.path.join(OSAI, mod + ".py")) else "MISSING"
        print(f"  {mod:30s} [{status:12s}] deps({len(deps)}): {', '.join(deps) if deps else '(none)'}")

# Key integration checks
print("\n" + "=" * 70)
print("KEY INTEGRATION CHECKS (real call chain verification)")
print("=" * 70)

checks = [
    ("skill_invocation imports action_firewall", "action_firewall" in matrix.get("skill_invocation", [])),
    ("skill_invocation imports effect_fence", "effect_fence" in matrix.get("skill_invocation", [])),
    ("skill_invocation imports permission_gate", "permission_gate" in matrix.get("skill_invocation", [])),
    ("skill_invocation imports evidence_chain", "evidence_chain" in matrix.get("skill_invocation", [])),
    ("skill_invocation imports engine_runtime", "engine_runtime" in matrix.get("skill_invocation", [])),
    ("skill_invocation imports observability", "observability" in matrix.get("skill_invocation", [])),
    ("skill_invocation imports skill_execution_contract", "skill_execution_contract" in matrix.get("skill_invocation", [])),
    ("obo_jit imports agent_identity", "agent_identity" in matrix.get("obo_jit", [])),
    ("decision_action_outcome imports effect_fence", "effect_fence" in matrix.get("decision_action_outcome", [])),
    ("decision_action_outcome imports canonical_data", "canonical_data" in matrix.get("decision_action_outcome", [])),
    ("engine_runtime imports ai_gateway or llm", any(x in matrix.get("engine_runtime", []) for x in ("ai_gateway", "llm"))),
    ("canonical_skill_registry has no circular import to skill_invocation",
     "skill_invocation" not in matrix.get("canonical_skill_registry", [])),
]

for name, passed in checks:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")

passed_count = sum(1 for _, p in checks if p)
print(f"\nIntegration checks: {passed_count}/{len(checks)} PASSED")

# Save JSON
output = {
    "modules": MODULES,
    "import_matrix": matrix,
    "categories": categories,
    "integration_checks": {name: passed for name, passed in checks},
}
outpath = r"D:\Taikoo-monitor-new\00-GOVERNANCE\osai_module_call_graph_shardB.json"
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {outpath}")
