# -*- coding: utf-8 -*-
"""Fix canonical_data.py hardcoded db path in __main__ block."""
import py_compile

fp = r'D:\Taikoo-monitor-new\canonical_data.py'
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix line 819 (0-indexed 818)
for i, line in enumerate(lines):
    if 'db = r"D:\\Taikoo-monitor-new\\data\\monitor.db"' in line or 'db = r"D:\Taikoo-monitor-new\data\monitor.db"' in line:
        lines[i] = '    from core.repository_registry import get_db_path\n    db = get_db_path()\n'
        print(f'Fixed line {i+1}: {line.strip()}')
        break

with open(fp, 'w', encoding='utf-8') as f:
    f.writelines(lines)

py_compile.compile(fp, doraise=True)
print('COMPILE OK')

# Verify
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()
if 'Taikoo-monitor-new\\data\\monitor.db' in content or 'Taikoo-monitor-new\data\monitor.db' in content:
    print('WARNING: hardcoded path still present')
else:
    print('VERIFIED: no hardcoded db path in canonical_data.py')
