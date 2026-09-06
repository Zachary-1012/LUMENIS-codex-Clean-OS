#!/usr/bin/env python3
r"""Hardcoded Path Replacer — Shard D / Team 1

Replaces hardcoded absolute paths in .py files with Repository Registry calls
or dynamic resolution. Production files use core.repository_registry.
Test files use os.path.dirname-based dynamic resolution (since they may not
have core on sys.path yet).

Safe replacement patterns:
  1. r"D:\Taikoo-monitor-new" standalone → get_repo_root()  [production]
  2. r'D:\Taikoo-monitor-new\data\monitor.db' → get_db_path()  [production]
  3. sys.path.insert(0, r"D:\Taikoo-monitor-new") → dynamic  [tests]
  4. os.chdir(r"D:\Taikoo-monitor-new") → os.chdir(get_repo_root())  [production]
  5. os.path.join(r"D:\Taikoo-monitor-new", ...) → os.path.join(get_repo_root(), ...)
  6. r"D:\Zachary OS AI" → get_osai_root() or dynamic
  7. r"C:\Users\28049\..." → os.path.expanduser("~") based

Does NOT modify:
  - .md, .json, .yaml, .toml, .bat, .ps1 files (documented in audit only)
  - Files in 00-GOVERNANCE/_scan_output/ (our own tools)
  - String literals that are clearly documentation/comments
"""
import os, re, csv, shutil
from datetime import datetime

ZBC_ROOT = r'D:\Taikoo-monitor-new'
OSAI_ROOT = r'D:\Zachary OS AI'
OUT_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE')
BACKUP_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE', '_path_backup')
os.makedirs(BACKUP_DIR, exist_ok=True)

SKIP_DIRS = {'.venv', 'node_modules', '.git', '__pycache__', '.pytest_cache',
             '99-ARCHIVE', 'archive', 'backups', 'logs', 'data',
             '.ollama', '.trae', '.trae-cn', '.vscode', '.skills-router',
             '序境', 'dist', 'build', '_scan_output', 'static', 'nodejs',
             'docker', 'migrations', 'alembic', 'templates'}

ZBC_PAT = r'D:\Taikoo-monitor-new'
OSAI_PAT = r'D:\Zachary OS AI'
HOME_PAT = r'C:\Users\28049'

audit_log = []


def is_test_file(filepath):
    """Check if file is in a tests/ directory or starts with test_."""
    norm = filepath.replace('\\', '/').lower()
    return '/tests/' in norm or '/test_' in norm or norm.endswith('/test.py')


def is_production_file(filepath):
    """Check if file is production code (not test, not script, not docs)."""
    norm = filepath.replace('\\', '/').lower()
    if is_test_file(filepath):
        return False
    if '/scripts/' in norm or '/docs/' in norm or '/00-governance/' in norm:
        return False
    if '/tools/' in norm or '/audit/' in norm:
        return False
    return True


def add_registry_import(content, filepath):
    """Add 'from core import repository_registry' import if not present.

    Only for production files. Returns modified content.
    """
    if 'from core import' in content or 'from core.repository_registry' in content:
        return content
    # Find first import line and add after it
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if re.match(r'^(import|from)\s+', line):
            insert_idx = i + 1
            break
    if insert_idx == 0:
        # No imports found, insert after module docstring
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#') and not line.startswith('"') and not line.startswith("'"):
                insert_idx = i
                break
    lines.insert(insert_idx, 'from core.repository_registry import get_repo_root, get_db_path, get_osai_root')
    return '\n'.join(lines)


def replace_in_file(filepath, repo_label):
    """Replace hardcoded paths in a single .py file. Returns (modified, replacements)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return False, 0, str(e)

    original = content
    replacements = 0
    rel_path = os.path.relpath(filepath, ZBC_ROOT if repo_label == 'ZBC' else OSAI_ROOT)

    # Determine replacement strategy
    prod = is_production_file(rel_path)
    test = is_test_file(rel_path)

    # Pattern 1: sys.path.insert(0, r"D:\Taikoo-monitor-new") — test files
    if test:
        # For test files in tests/, use dynamic resolution
        new_pat = r'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))'
        content, n = re.subn(
            r'sys\.path\.insert\(\s*0\s*,\s*[rR]?["\']' + re.escape(ZBC_PAT) + r'["\']\s*\)',
            new_pat, content
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'sys.path.insert',
                             'replacement': 'dynamic dirname', 'count': n})

        # OSAI test files: sys.path.insert(0, r"D:\Zachary OS AI")
        new_pat_osai = r'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))'
        content, n = re.subn(
            r'sys\.path\.insert\(\s*0\s*,\s*[rR]?["\']' + re.escape(OSAI_PAT) + r'["\']\s*\)',
            new_pat_osai, content
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'sys.path.insert OSAI',
                             'replacement': 'dynamic dirname', 'count': n})

    # Pattern 2: standalone r"D:\Taikoo-monitor-new" assignment — production
    if prod:
        # base = r"D:\Taikoo-monitor-new" → base = get_repo_root()
        content, n = re.subn(
            r'=\s*[rR]?["\']' + re.escape(ZBC_PAT) + r'["\']\s*$',
            '= get_repo_root()', content, flags=re.MULTILINE
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'standalone ZBC root',
                             'replacement': 'get_repo_root()', 'count': n})

        # ROOT = r"D:\Taikoo-monitor-new" → ROOT = get_repo_root()
        content, n = re.subn(
            r'^(ROOT|ZBC|base|repo_root|PROJECT_ROOT)\s*=\s*[rR]?["\']' + re.escape(ZBC_PAT) + r'["\']',
            r'\1 = get_repo_root()', content, flags=re.MULTILINE
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'ROOT assignment',
                             'replacement': 'get_repo_root()', 'count': n})

        # sqlite3.connect(r'D:\Taikoo-monitor-new\data\monitor.db') → get_db_path()
        content, n = re.subn(
            r'["\']' + re.escape(ZBC_PAT + r'\\data\\monitor.db') + r'["\']',
            'get_db_path()', content
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'db path',
                             'replacement': 'get_db_path()', 'count': n})

        # os.chdir(r"D:\Taikoo-monitor-new") → os.chdir(get_repo_root())
        content, n = re.subn(
            r'os\.chdir\(\s*[rR]?["\']' + re.escape(ZBC_PAT) + r'["\']\s*\)',
            'os.chdir(get_repo_root())', content
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'os.chdir',
                             'replacement': 'get_repo_root()', 'count': n})

        # os.path.join(r"D:\Taikoo-monitor-new", ...) → os.path.join(get_repo_root(), ...)
        content, n = re.subn(
            r'os\.path\.join\(\s*[rR]?["\']' + re.escape(ZBC_PAT) + r'["\']',
            'os.path.join(get_repo_root()', content
        )
        replacements += n
        if n > 0:
            audit_log.append({'file': rel_path, 'repo': repo_label, 'type': 'os.path.join',
                             'replacement': 'get_repo_root()', 'count': n})

    # Add registry import for production files that were modified
    if prod and replacements > 0 and 'get_repo_root()' in content:
        content = add_registry_import(content, filepath)

    # Write back if modified
    if content != original:
        # Backup
        backup_path = os.path.join(BACKUP_DIR, rel_path.replace('\\', '_').replace('/', '_'))
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(filepath, backup_path)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, replacements, None

    return False, 0, None


# === MAIN ===
print("=== Hardcoded Path Replacer ===")
print(f"ZBC: {ZBC_ROOT}")
print(f"OSAI: {OSAI_ROOT}")

total_modified = 0
total_replacements = 0
modified_files = []

for root, label in [(ZBC_ROOT, 'ZBC'), (OSAI_ROOT, 'OSAI')]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith('.py'):
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root)

            # Skip our own scan tools
            if '_scan_output' in rel or 'build_feature_registry' in rel:
                continue

            modified, count, error = replace_in_file(fp, label)
            if modified:
                total_modified += 1
                total_replacements += count
                modified_files.append(rel)
                print(f"  MODIFIED [{label}] {rel} ({count} replacements)")
            elif error:
                print(f"  ERROR [{label}] {rel}: {error}")

print(f"\n=== RESULTS ===")
print(f"Files modified: {total_modified}")
print(f"Total replacements: {total_replacements}")
print(f"Modified files:")
for f in modified_files:
    print(f"  {f}")

# Save audit log
audit_path = os.path.join(OUT_DIR, 'hardcoded_path_audit.csv')
with open(audit_path, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['file', 'repo', 'type', 'replacement', 'count'])
    w.writeheader()
    for entry in audit_log:
        w.writerow(entry)
print(f"\nAudit log saved: {audit_path}")
print(f"Backups saved in: {BACKUP_DIR}")
