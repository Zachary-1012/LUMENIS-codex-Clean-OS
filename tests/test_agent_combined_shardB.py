# -*- coding: utf-8 -*-
"""Test Agent Runtime Adapter - combined flow (single subprocess for stateful ops).

Shard B Team 9. Verifies Identity → Delegation → OBO → JIT in one OSAI process.
Per-call subprocess is stateless by design (same pattern as skill adapter);
combined script proves the full chain works inside OSAI runtime.
"""
import sys, json, subprocess, os

OSAI_ROOT = r"D:\Zachary OS AI"
PYTHON = r"D:\Taikoo-monitor-new\.venv\Scripts\python.exe"

COMBINED_SCRIPT = """
import json, sys
sys.path.insert(0, '.')
from osai_engine.agent_identity import get_identity_registry
from osai_engine.obo_jit import DelegationManager

reg = get_identity_registry()
dm = DelegationManager(reg)

# 1. Create user identity
user = reg.create_identity('user', 'test-user-shardB', permissions=['ALL'])
# 2. Create agent identity (parent = user)
agent = reg.create_identity('agent', 'test-agent-shardB',
    parent_identity=user.identity_id, permissions=['READ', 'ANALYZE'])
# 3. Delegate (OBO)
del_ctx = dm.delegate(user.identity_id, agent.identity_id,
    permissions=['READ', 'ANALYZE'], intent='shardB-test', task_id='TASK-shardB')
# 4. Check delegation (READ should allow)
check_read = dm.check_delegation(del_ctx.delegation_id, 'READ')
# 5. Check delegation (DELETE should deny - not in scope)
check_delete = dm.check_delegation(del_ctx.delegation_id, 'DELETE')
# 6. JIT elevate (add WRITE for 60s)
jit = dm.jit_elevate(del_ctx.delegation_id, ['WRITE'], duration_seconds=60)
# 7. Check after JIT (WRITE should now allow)
check_write_after = dm.check_delegation(del_ctx.delegation_id, 'WRITE') if jit else None
# 8. Identity chain
chain = reg.get_chain(agent.identity_id)
# 9. Attribute execution
attr = dm.attribute_execution(del_ctx.delegation_id, 'skill_execute',
    'S01', 'SUCCESS', evidence_id='ev-test-shardB')

result = {
    'user_identity': user.to_dict(),
    'agent_identity': agent.to_dict(),
    'identity_chain': [i.to_dict() for i in chain],
    'delegation': del_ctx.to_dict(),
    'check_read': check_read,
    'check_delete': check_delete,
    'jit_elevation': jit.to_dict() if jit else None,
    'check_write_after_jit': check_write_after,
    'execution_attribution': attr.to_dict() if attr else None,
    'agent_separate_from_user': user.identity_id != agent.identity_id,
    'agent_separate_from_task': agent.identity_id != 'TASK-shardB',
}
print(json.dumps(result, ensure_ascii=False))
"""

def run_combined():
    result = subprocess.run(
        [PYTHON, "-c", COMBINED_SCRIPT],
        cwd=OSAI_ROOT, capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONPATH": OSAI_ROOT},
    )
    if result.returncode != 0:
        print("ERROR:", result.stderr[:500])
        return None
    return json.loads(result.stdout)

print("=" * 60)
print("Agent Identity + Delegation + OBO + JIT Combined Test")
print("=" * 60)

data = run_combined()
if data is None:
    print("FAILED: could not run combined script")
    sys.exit(1)

checks = []
def check(name, passed, detail=""):
    checks.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}: {detail}")

print("\n--- Identity Separation (Agent != User != Task) ---")
check("Agent != User identity", data["agent_separate_from_user"],
      f"user={data['user_identity']['identity_id'][:16]}..., agent={data['agent_identity']['identity_id'][:16]}...")
check("Agent != Task", data["agent_separate_from_task"], "")
check("Identity chain has 2+ nodes", len(data["identity_chain"]) >= 2,
      f"chain length={len(data['identity_chain'])}")
check("Agent parent = User", data["agent_identity"]["parent_identity"] == data["user_identity"]["identity_id"], "")

print("\n--- Delegation / OBO ---")
check("Delegation created", data["delegation"]["delegation_id"] is not None,
      f"del_id={data['delegation']['delegation_id'][:16]}...")
check("Delegation valid", data["delegation"]["valid"] == True, "")
check("Delegator = User", data["delegation"]["delegator"] == data["user_identity"]["identity_id"], "")
check("Delegate = Agent", data["delegation"]["delegate"] == data["agent_identity"]["identity_id"], "")

print("\n--- Permission Check (fail-close) ---")
check("READ allowed (in scope)", data["check_read"]["allowed"] == True,
      f"reason={data['check_read'].get('reason','')}")
check("DELETE denied (not in scope)", data["check_delete"]["allowed"] == False,
      f"reason={data['check_delete'].get('reason','')}")

print("\n--- JIT Elevation ---")
check("JIT elevate succeeded", data["jit_elevation"] is not None and data["jit_elevation"]["jit_elevation"] == True, "")
check("JIT has expiry", data["jit_elevation"]["expires_at"] > 0,
      f"expires_at={data['jit_elevation']['expires_at']}")
check("WRITE in permissions after JIT", "WRITE" in data["jit_elevation"]["permissions"],
      f"perms={data['jit_elevation']['permissions']}")

print("\n--- Execution Attribution ---")
check("Attribution recorded", data["execution_attribution"] is not None, "")
if data["execution_attribution"]:
    check("Attribution initiated_by = User",
          data["execution_attribution"]["initiated_by"] == data["user_identity"]["identity_id"], "")
    check("Attribution executed_by = Agent",
          data["execution_attribution"]["executed_by"] == data["agent_identity"]["identity_id"], "")
    check("Attribution has evidence_id",
          data["execution_attribution"]["evidence_id"] == "ev-test-shardB", "")

print("\n" + "=" * 60)
passed = sum(1 for _, p, _ in checks if p)
total = len(checks)
print(f"Combined Agent Test: {passed}/{total} PASSED")
print("=" * 60)
for name, p, detail in checks:
    if not p:
        print(f"  FAILED: {name} — {detail}")
sys.exit(0 if passed == total else 1)
