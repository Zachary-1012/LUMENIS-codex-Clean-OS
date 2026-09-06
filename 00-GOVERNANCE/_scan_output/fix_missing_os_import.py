# -*- coding: utf-8 -*-
"""Fix missing 'import os' in test files modified by path replacer."""
import os, re

ZBC = r'D:\Taikoo-monitor-new'
files_to_fix = [
    'tests/test_ai_channel_flag.py',
    'tests/test_ai_degrade.py',
    'tests/test_compliance_gate.py',
    'tests/test_report_special.py',
    'tests/test_resource_guard.py',
    'tests/test_schedule_adapter.py',
    'tests/test_security_scanner_s2.py',
    'tests/_audit_system.py',
]

fixed = []
for rel in files_to_fix:
    fp = os.path.join(ZBC, rel)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # Already has import os?
    if re.search(r'^import os', content, re.MULTILINE):
        print(f'SKIP (already has import os): {rel}')
        continue

    lines = content.split('\n')
    insert_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^import sys', line):
            insert_idx = i + 1
            break
        if re.match(r'^import ', line) and 'os' not in line:
            insert_idx = i
            break

    if insert_idx is None:
        # Find first non-comment, non-docstring line
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#') and not line.startswith('"') and not line.startswith("'"):
                insert_idx = i
                break

    if insert_idx is not None:
        lines.insert(insert_idx, 'import os')
        content = '\n'.join(lines)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed.append(rel)
        print(f'FIXED: {rel} (inserted import os at line {insert_idx+1})')
    else:
        print(f'FAILED: {rel} (could not find insertion point)')

print(f'\nTotal fixed: {len(fixed)}')

# Verify all compile
import py_compile
for rel in fixed:
    fp = os.path.join(ZBC, rel)
    try:
        py_compile.compile(fp, doraise=True)
        print(f'  COMPILE OK: {rel}')
    except Exception as e:
        print(f'  COMPILE FAIL: {rel}: {e}')
