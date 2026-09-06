# -*- coding: utf-8 -*-
"""Test Agent Runtime Adapter end-to-end."""
import sys, json
sys.path.insert(0, r'D:\Taikoo-monitor-new')
from agent_runtime_adapter import get_agent_adapter

adapter = get_agent_adapter()
print('=== Adapter Status ===')
print(json.dumps(adapter.status(), ensure_ascii=False, indent=2))

print('\n=== 1. Create Agent Identity ===')
r1 = adapter.create_agent_identity('test-agent-shardB', permissions=['READ', 'ANALYZE'])
print(json.dumps(r1, ensure_ascii=False, indent=2)[:600])

agent_id = None
if r1.get('connected') and r1.get('identity'):
    agent_id = r1['identity']['identity_id']
    print('Agent ID:', agent_id)

    print('\n=== 2. Delegate (OBO) ===')
    r2 = adapter.delegate('user_test', agent_id, permissions=['READ', 'ANALYZE'], intent='test')
    print(json.dumps(r2, ensure_ascii=False, indent=2)[:500])

    if r2.get('connected') and r2.get('delegation'):
        del_id = r2['delegation']['delegation_id']
        print('Delegation ID:', del_id)

        print('\n=== 3. Check Delegation (READ) ===')
        r3 = adapter.check_delegation(del_id, 'READ')
        print(json.dumps(r3, ensure_ascii=False, indent=2)[:300])

        print('\n=== 4. Check Delegation (DELETE - should deny) ===')
        r3b = adapter.check_delegation(del_id, 'DELETE')
        print(json.dumps(r3b, ensure_ascii=False, indent=2)[:300])

        print('\n=== 5. JIT Elevate ===')
        r4 = adapter.jit_elevate(del_id, ['WRITE'], duration_seconds=60)
        print(json.dumps(r4, ensure_ascii=False, indent=2)[:400])

print('\n=== Audit Log ===')
print('Total audit records:', len(adapter._audit_log))
for a in adapter._audit_log:
    print(' ', a['action'], ':', a['result'], '-', a['reason'][:60])

print('\n=== SUMMARY ===')
checks = [
    ('adapter.available', adapter.available),
    ('create_identity connected', r1.get('connected', False)),
    ('delegate connected', r2.get('connected', False) if agent_id else False),
    ('check READ allowed', r3.get('allowed', False) if agent_id and r2.get('connected') else False),
    ('check DELETE denied', (not r3b.get('allowed', True)) if agent_id and r2.get('connected') else False),
    ('jit elevated', r4.get('status') == 'ELEVATED' if agent_id and r2.get('connected') else False),
    ('audit records > 0', len(adapter._audit_log) > 0),
]
for name, passed in checks:
    status = 'PASS' if passed else 'FAIL'
    print(f'  [{status}] {name}')
passed_count = sum(1 for _, p in checks if p)
print(f'\n{passed_count}/{len(checks)} PASSED')
