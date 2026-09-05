# -*- coding: utf-8 -*-
"""Fix OSAI repository_registry.py - remove bad import and fix win_default."""
fp = r'D:\Zachary OS AI\osai_engine\repository_registry.py'

with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove bad import line
bad_import = 'from core.repository_registry import get_repo_root, get_db_path, get_osai_root\n'
content = content.replace(bad_import, '')

# 2. Fix win_default - revert to original hardcoded fallback with clear comment
old_line = 'win_default = get_repo_root()'
new_line = 'win_default = r"D:\\Taikoo-monitor-new"  # dev-machine fallback; use ZBC_ROOT env var in production'
content = content.replace(old_line, new_line)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed OSAI repository_registry.py')

# Verify
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print('--- imports (lines 15-20) ---')
for i, line in enumerate(lines[14:20], 15):
    print(f'{i}: {line.rstrip()}')
print('--- _default_root (lines 30-36) ---')
for i, line in enumerate(lines[29:36], 30):
    print(f'{i}: {line.rstrip()}')

# Verify it compiles
import py_compile
try:
    py_compile.compile(fp, doraise=True)
    print('\n[OK] File compiles successfully')
except py_compile.PyCompileError as e:
    print(f'\n[FAIL] Compile error: {e}')
