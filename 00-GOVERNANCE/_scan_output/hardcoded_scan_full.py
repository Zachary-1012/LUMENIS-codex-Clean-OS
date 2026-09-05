#!/usr/bin/env python3
"""Hardcoded path scan - minimal skipping, production code only"""
import os, re, csv
from collections import defaultdict

ZBC_ROOT = r'D:\Taikoo-monitor-new'
OSAI_ROOT = r'D:\Zachary OS AI'
OUT_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE', '_scan_output')

# Minimal skip - only non-code dirs
SKIP_DIRS = {
    '.venv', 'node_modules', '.git', '__pycache__', '.pytest_cache',
    '99-ARCHIVE', 'archive', 'backups', 'logs', 'data',
    '.ollama', '.trae', '.trae-cn', '.vscode', '.skills-router',
    '序境', 'dist', 'build', '.next', '.nuxt',
    '_shots', '_video_frames', '_ref_frames', '_pitch_dump', '_u',
    'static', 'nodejs', 'docker',
}

SCAN_EXTS = {'.py', '.json', '.yaml', '.yml', '.ini', '.cfg', '.toml', '.html', '.js', '.sh', '.bat', '.ps1'}

PATTERNS = [
    (r'D:\Taikoo-monitor-new', 'ZBC_ROOT'),
    (r'D:\Zachary OS AI', 'OSAI_ROOT'),
    (r'C:\Users\28049', 'HOME_ROOT'),
]

def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SCAN_EXTS:
                yield os.path.join(dirpath, fn)

results = []
for root, label in [(ZBC_ROOT, 'ZBC'), (OSAI_ROOT, 'OSAI')]:
    for fp in walk_files(root):
        rel = os.path.relpath(fp, root)
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except:
            continue
        for i, line in enumerate(lines, 1):
            for pat, name in PATTERNS:
                if pat in line:
                    results.append({
                        'repo': label, 'file': rel, 'line': i,
                        'pattern': name, 'ext': os.path.splitext(fp)[1].lower(),
                        'content': line.strip()[:200],
                    })

# Dedup
seen = set()
unique = []
for r in results:
    key = (r['repo'], r['file'], r['line'], r['pattern'])
    if key not in seen:
        seen.add(key)
        unique.append(r)

print(f"Total occurrences: {len(unique)}")
by_file = defaultdict(list)
for r in unique:
    by_file[r['repo'] + '|' + r['file']].append(r)
print(f"Unique files: {len(by_file)}")

# Count by repo and ext
by_repo = defaultdict(int)
by_ext = defaultdict(int)
py_files = []
for r in unique:
    by_repo[r['repo']] += 1
    by_ext[r['ext']] += 1
    if r['ext'] == '.py':
        py_files.append(r)

print(f"\nBy repo: {dict(by_repo)}")
print(f"By ext: {dict(by_ext)}")
print(f"\nPython files with hardcoded paths ({len(set(r['repo']+'|'+r['file'] for r in py_files))} files):")
py_by_file = defaultdict(list)
for r in py_files:
    py_by_file[r['repo'] + '|' + r['file']].append(r)
for f, hits in sorted(py_by_file.items()):
    print(f"  {f} ({len(hits)} hits)")
    for h in hits[:3]:
        print(f"    L{h['line']}: {h['content'][:120]}")

# Save full CSV
csv_path = os.path.join(OUT_DIR, 'hardcoded_paths_full.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['repo','file','line','pattern','ext','content'])
    w.writeheader()
    for r in unique:
        w.writerow(r)
print(f"\nSaved: {csv_path}")
