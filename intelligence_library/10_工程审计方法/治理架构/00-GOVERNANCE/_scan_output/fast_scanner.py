#!/usr/bin/env python3
"""Fast Shard D Scanner - Phase 1: Hardcoded Paths + Functions"""
import os, re, json, csv, sys
from collections import defaultdict

ZBC_ROOT = r'D:\Taikoo-monitor-new'
OSAI_ROOT = r'D:\Zachary OS AI'
OUT_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE', '_scan_output')
os.makedirs(OUT_DIR, exist_ok=True)

# Aggressive skip - only production code dirs matter
SKIP_DIRS = {
    '.venv', 'node_modules', '.git', '__pycache__', '.pytest_cache',
    '99-ARCHIVE', 'archive', 'backups', 'logs', 'data', '_shots',
    '_video_frames', '_ref_frames', '_pitch_dump', '_u', '.ollama',
    '.trae', '.trae-cn', '.vscode', '.skills-router', '序境',
    'dist', 'build', '.next', '.nuxt', 'static', 'templates',
    'nodejs', 'docker', 'deployment', 'dependencies', 'deliverables',
    'staging', 'tools', 'scripts', '2026-08-30', '2026-09-01',
    'v4_upgrade', 'ref_gpt_v2', 'podcast', 'proxy_pool',
    'edge-cdp-general', 'edge-cdp-newaccount', 'edge-cdp-profile',
    'edge-cdp-retinaut', 'account_keepalive', 'browser_runtime',
    'collector_guard', 'collector_v2', 'ad_intelligence', 'evaluation',
    'report_export', 'platform_adapters', 'migrations', 'alembic',
    'tests', '00-GOVERNANCE', '02-ARCHITECTURE', 'docs', 'audit',
}

CODE_EXTS = {'.py'}
CONFIG_EXTS = {'.py', '.json', '.yaml', '.yml', '.ini', '.cfg', '.toml', '.md', '.html', '.js'}

HARDCODED_PATTERNS = [
    (r'D:\Taikoo-monitor-new', 'ZBC_ROOT'),
    (r'D:\Zachary OS AI', 'OSAI_ROOT'),
    (r'C:\Users\28049', 'HOME_ROOT'),
]

def walk_files(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in exts:
                yield os.path.join(dirpath, fn)

def read_lines(fp):
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            return f.readlines()
    except:
        return []

# === PHASE 1: HARDCODED PATHS ===
print("=== PHASE 1: HARDCODED PATH SCAN ===")
hp_results = []
for root, label in [(ZBC_ROOT, 'ZBC'), (OSAI_ROOT, 'OSAI')]:
    for fp in walk_files(root, CONFIG_EXTS):
        rel = os.path.relpath(fp, root)
        for i, line in enumerate(read_lines(fp), 1):
            for pat, name in HARDCODED_PATTERNS:
                if pat in line:
                    hp_results.append({
                        'repo': label, 'file': rel, 'line': i,
                        'pattern': name, 'content': line.strip()[:200],
                    })

# Dedup
seen = set()
hp_unique = []
for r in hp_results:
    key = (r['repo'], r['file'], r['line'], r['pattern'])
    if key not in seen:
        seen.add(key)
        hp_unique.append(r)

print(f"Hardcoded path occurrences: {len(hp_unique)}")
hp_by_file = defaultdict(list)
for r in hp_unique:
    hp_by_file[r['repo'] + '/' + r['file']].append(r)
print(f"Unique files: {len(hp_by_file)}")
for f, hits in sorted(hp_by_file.items()):
    print(f"  [{hits[0]['repo']}] {f} ({len(hits)} hits)")
    for h in hits[:3]:
        print(f"    L{h['line']}: {h['content'][:100]}")

with open(os.path.join(OUT_DIR, 'hardcoded_paths_raw.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['repo','file','line','pattern','content'])
    w.writeheader()
    for r in hp_unique:
        w.writerow(r)

# === PHASE 2: FUNCTIONS ===
print("\n=== PHASE 2: FUNCTION SCAN ===")
functions = []
for root, label in [(ZBC_ROOT, 'ZBC'), (OSAI_ROOT, 'OSAI')]:
    for fp in walk_files(root, CODE_EXTS):
        rel = os.path.relpath(fp, root)
        lines = read_lines(fp)
        if not lines:
            continue
        classes = []
        for i, line in enumerate(lines):
            m = re.match(r'^class\s+(\w+)', line)
            if m:
                classes.append((i+1, m.group(1)))
        for i, line in enumerate(lines):
            m = re.match(r'^(\s*)def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*([\w\[\], ]+))?\s*:', line)
            if m:
                indent = len(m.group(1))
                fname = m.group(2)
                args = m.group(3)[:200]
                ret = (m.group(4) or '').strip()
                is_method = indent > 0
                parent_class = ''
                if is_method:
                    for cls_line, cls_name in reversed(classes):
                        if cls_line <= i+1:
                            parent_class = cls_name
                            break
                docstring = ''
                for j in range(i+1, min(i+4, len(lines))):
                    dm = re.match(r'\s*"""(.+?)"""', lines[j])
                    if dm:
                        docstring = dm.group(1)[:150]
                        break
                    dm = re.match(r"\s*'''(.+?)'''", lines[j])
                    if dm:
                        docstring = dm.group(1)[:150]
                        break
                functions.append({
                    'repo': label, 'file': rel, 'line': i+1,
                    'class': parent_class, 'function': fname,
                    'is_method': is_method, 'args': args,
                    'return': ret, 'docstring': docstring,
                })

print(f"Total functions: {len(functions)}")
by_repo = defaultdict(int)
by_file = defaultdict(int)
for f in functions:
    by_repo[f['repo']] += 1
    by_file[f['repo'] + '/' + f['file']] += 1
print(f"By repo: {dict(by_repo)}")
print(f"Unique py files: {len(by_file)}")

with open(os.path.join(OUT_DIR, 'functions_raw.json'), 'w', encoding='utf-8') as f:
    json.dump(functions, f, ensure_ascii=False)

# === PHASE 3: CROSS-REPO IMPORTS ===
print("\n=== PHASE 3: CROSS-REPO IMPORT SCAN ===")
cross_results = []
for root, label in [(ZBC_ROOT, 'ZBC'), (OSAI_ROOT, 'OSAI')]:
    for fp in walk_files(root, CODE_EXTS):
        rel = os.path.relpath(fp, root)
        for i, line in enumerate(read_lines(fp), 1):
            s = line.strip()
            if re.match(r'^(import|from)\s+', s):
                # ZBC -> OSAI
                if label == 'ZBC' and re.search(r'\b(osai|zachary_os|intelligence_core|lumenis_os)\b', s, re.I):
                    cross_results.append({'from': 'ZBC', 'to': 'OSAI', 'file': rel, 'line': i, 'content': s[:200]})
                # OSAI -> ZBC
                if label == 'OSAI' and re.search(r'\b(zbc|taikoo|monitor_new|xujing_core|subject_rules)\b', s, re.I):
                    cross_results.append({'from': 'OSAI', 'to': 'ZBC', 'file': rel, 'line': i, 'content': s[:200]})
            # Runtime path refs (sys.path.insert, subprocess, etc.)
            if any(kw in s for kw in ['sys.path', 'subprocess', 'Popen', 'run(']):
                for pat, name in HARDCODED_PATTERNS:
                    if pat in s:
                        cross_results.append({'from': label, 'to': name, 'file': rel, 'line': i, 'content': s[:200], 'type': 'runtime_ref'})

print(f"Cross-repo references: {len(cross_results)}")
for r in cross_results:
    print(f"  [{r['from']}->{r['to']}] {r['file']}:{r['line']} {r['content'][:100]}")

with open(os.path.join(OUT_DIR, 'cross_repo_imports_raw.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['from','to','file','line','content','type'])
    w.writeheader()
    for r in cross_results:
        w.writerow(r)

# === PHASE 4: ACTIVE_BRAND ===
print("\n=== PHASE 4: ACTIVE_BRAND SCAN ===")
ab_results = []
for fp in walk_files(ZBC_ROOT, CODE_EXTS):
    rel = os.path.relpath(fp, ZBC_ROOT)
    for i, line in enumerate(read_lines(fp), 1):
        if 'active_brand' in line:
            ab_results.append({'file': rel, 'line': i, 'content': line.strip()[:200]})

print(f"active_brand references: {len(ab_results)}")
ab_by_file = defaultdict(int)
for r in ab_results:
    ab_by_file[r['file']] += 1
for f, c in sorted(ab_by_file.items()):
    print(f"  {f}: {c}")

with open(os.path.join(OUT_DIR, 'active_brand_raw.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['file','line','content'])
    w.writeheader()
    for r in ab_results:
        w.writerow(r)

# === PHASE 5: ROUTES ===
print("\n=== PHASE 5: ROUTE SCAN ===")
route_results = []
for fp in walk_files(ZBC_ROOT, CODE_EXTS):
    rel = os.path.relpath(fp, ZBC_ROOT)
    for i, line in enumerate(read_lines(fp), 1):
        m = re.search(r'@(?:app|bp|blueprint|api|main)\.(?:route|get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', line)
        if m:
            route_results.append({'file': rel, 'line': i, 'path': m.group(1), 'content': line.strip()[:150]})

print(f"Routes: {len(route_results)}")
with open(os.path.join(OUT_DIR, 'routes_raw.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['file','line','path','content'])
    w.writeheader()
    for r in route_results:
        w.writerow(r)

print("\n=== ALL SCANS COMPLETE ===")
print(f"Hardcoded: {len(hp_unique)} | Functions: {len(functions)} | Cross-repo: {len(cross_results)} | active_brand: {len(ab_results)} | Routes: {len(route_results)}")
