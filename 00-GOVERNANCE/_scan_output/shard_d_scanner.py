#!/usr/bin/env python3
"""Shard D Comprehensive Source Scanner - Hardcoded Paths, Functions, Imports, active_brand"""
import os, re, json, csv, sys
from collections import defaultdict

# === CONFIG ===
ZBC_ROOT = r'D:\Taikoo-monitor-new'
OSAI_ROOT = r'D:\Zachary OS AI'
GGI_ROOT = r'D:\global-growth-intelligence'
HOME_ROOT = r'C:\Users\28049'
OUT_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE', '_scan_output')
os.makedirs(OUT_DIR, exist_ok=True)

SKIP_DIRS = {'.venv', 'node_modules', '.git', '__pycache__', '.pytest_cache',
             '99-ARCHIVE', 'archive', 'backups', 'logs', 'data', '_shots',
             '_video_frames', '_ref_frames', '_pitch_dump', '_u', '.ollama',
             '.trae', '.trae-cn', '.vscode', '.skills-router', '序境',
             'dist', 'build', '.next', '.nuxt', 'migrations', 'alembic',
             'static', 'templates', 'nodejs', 'docker', 'deployment',
             'dependencies', 'deliverables', 'staging', 'tools', 'scripts',
             '2026-08-30', '2026-09-01', 'v4_upgrade', 'ref_gpt_v2',
             'podcast', 'proxy_pool', 'edge-cdp-general', 'edge-cdp-newaccount',
             'edge-cdp-profile', 'edge-cdp-retinaut', 'account_keepalive',
             'browser_runtime', 'collector_guard', 'collector_v2',
             'ad_intelligence', 'evaluation', 'report_export', 'platform_adapters'}

CODE_EXTS = {'.py'}
ALL_EXTS = {'.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.yml',
            '.ini', '.cfg', '.toml', '.md', '.sh', '.bat', '.ps1', '.sql'}

HARDCODED_PATTERNS = [
    (r'D:\\Taikoo-monitor-new', 'ZBC_ROOT'),
    (r'D:\\Zachary OS AI', 'OSAI_ROOT'),
    (r'C:\\Users\\28049', 'HOME_ROOT'),
]

def should_skip(dirpath):
    parts = set(dirpath.split(os.sep))
    return bool(parts & SKIP_DIRS)

def scan_files(root, exts):
    """Yield (filepath, relpath) for all matching files."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in exts:
                fp = os.path.join(dirpath, fn)
                rel = os.path.relpath(fp, root)
                yield fp, rel

def read_file(fp):
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            return f.readlines()
    except:
        return None

# === 1. HARDCODED PATH SCAN ===
def scan_hardcoded_paths():
    print("=== HARDCODED PATH SCAN ===")
    results = []
    roots = [
        (ZBC_ROOT, 'ZBC'),
        (OSAI_ROOT, 'OSAI'),
        (HOME_ROOT, 'HOME'),
    ]
    for root, label in roots:
        for fp, rel in scan_files(root, ALL_EXTS):
            lines = read_file(fp)
            if not lines:
                continue
            for i, line in enumerate(lines, 1):
                for pat, name in HARDCODED_PATTERNS:
                    if pat in line:
                        results.append({
                            'repo': label,
                            'file': rel,
                            'line': i,
                            'pattern': name,
                            'content': line.strip()[:200],
                            'abs_path': fp,
                        })
    # Deduplicate
    seen = set()
    unique = []
    for r in results:
        key = (r['abs_path'], r['line'], r['pattern'])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    print(f"Total hardcoded path occurrences: {len(unique)}")
    by_file = defaultdict(list)
    for r in unique:
        by_file[r['abs_path']].append(r)
    print(f"Unique files: {len(by_file)}")
    
    # Save CSV
    csv_path = os.path.join(OUT_DIR, 'hardcoded_paths_raw.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['repo','file','line','pattern','content'])
        w.writeheader()
        for r in unique:
            w.writerow({k: r[k] for k in ['repo','file','line','pattern','content']})
    print(f"Saved: {csv_path}")
    
    # Print summary by file
    for fp, hits in sorted(by_file.items()):
        print(f"  {fp} ({len(hits)} hits)")
    
    return unique

# === 2. FUNCTION DEFINITION SCAN (for Feature Registry) ===
def scan_functions():
    print("\n=== FUNCTION DEFINITION SCAN ===")
    functions = []
    roots = [
        (ZBC_ROOT, 'ZBC'),
        (OSAI_ROOT, 'OSAI'),
    ]
    for root, label in roots:
        for fp, rel in scan_files(root, CODE_EXTS):
            lines = read_file(fp)
            if not lines:
                continue
            content = ''.join(lines)
            # Find class definitions
            classes = []
            for i, line in enumerate(lines):
                m = re.match(r'^class\s+(\w+)', line)
                if m:
                    classes.append((i+1, m.group(1)))
            # Find function/method definitions
            for i, line in enumerate(lines):
                m = re.match(r'^(\s*)def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?\s*:', line)
                if m:
                    indent = len(m.group(1))
                    fname = m.group(2)
                    args = m.group(3)
                    ret = m.group(4) or ''
                    # Determine if method (inside class)
                    is_method = indent > 0
                    parent_class = ''
                    if is_method:
                        for cls_line, cls_name in reversed(classes):
                            if cls_line <= i+1:
                                parent_class = cls_name
                                break
                    # Get docstring (next non-empty line)
                    docstring = ''
                    for j in range(i+1, min(i+5, len(lines))):
                        dm = re.match(r'\s*"""(.+?)"""', lines[j])
                        if dm:
                            docstring = dm.group(1)[:150]
                            break
                        dm = re.match(r"\s*'''(.+?)'''", lines[j])
                        if dm:
                            docstring = dm.group(1)[:150]
                            break
                    functions.append({
                        'repo': label,
                        'file': rel,
                        'line': i+1,
                        'class': parent_class,
                        'function': fname,
                        'is_method': is_method,
                        'args': args[:200],
                        'return': ret,
                        'docstring': docstring,
                    })
    
    print(f"Total functions found: {len(functions)}")
    by_repo = defaultdict(int)
    by_file = defaultdict(int)
    for f in functions:
        by_repo[f['repo']] += 1
        by_file[f['file']] += 1
    print(f"By repo: {dict(by_repo)}")
    print(f"Unique Python files: {len(by_file)}")
    
    # Save JSON
    json_path = os.path.join(OUT_DIR, 'functions_raw.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(functions, f, ensure_ascii=False, indent=1)
    print(f"Saved: {json_path}")
    
    return functions

# === 3. CROSS-REPO IMPORT SCAN ===
def scan_cross_repo_imports():
    print("\n=== CROSS-REPO IMPORT SCAN ===")
    results = []
    
    # Scan ZBC for OSAI imports
    for fp, rel in scan_files(ZBC_ROOT, CODE_EXTS):
        lines = read_file(fp)
        if not lines:
            continue
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^(import|from)\s+', stripped):
                # Check for osai, zachary, intelligence core references
                if re.search(r'\b(osai|zachary_os|intelligence_core|lumenis_os)\b', stripped, re.I):
                    results.append({
                        'from_repo': 'ZBC',
                        'to_repo': 'OSAI',
                        'file': rel,
                        'line': i,
                        'content': stripped[:200],
                    })
                if re.search(r'\b(zbc|taikoo|monitor_new)\b', stripped, re.I):
                    # Self-reference or cross to ZBC from ZBC (normal)
                    pass
    
    # Scan OSAI for ZBC imports
    for fp, rel in scan_files(OSAI_ROOT, CODE_EXTS):
        lines = read_file(fp)
        if not lines:
            continue
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^(import|from)\s+', stripped):
                if re.search(r'\b(zbc|taikoo|monitor_new|xujing_core)\b', stripped, re.I):
                    results.append({
                        'from_repo': 'OSAI',
                        'to_repo': 'ZBC',
                        'file': rel,
                        'line': i,
                        'content': stripped[:200],
                    })
    
    # Also scan for subprocess/sys.path manipulations that reference other repos
    for root, label in [(ZBC_ROOT, 'ZBC'), (OSAI_ROOT, 'OSAI')]:
        for fp, rel in scan_files(root, CODE_EXTS):
            lines = read_file(fp)
            if not lines:
                continue
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if 'sys.path' in stripped or 'subprocess' in stripped or 'Popen' in stripped:
                    for pat, name in HARDCODED_PATTERNS:
                        if pat in stripped:
                            results.append({
                                'from_repo': label,
                                'to_repo': name,
                                'file': rel,
                                'line': i,
                                'content': stripped[:200],
                                'type': 'runtime_path_ref',
                            })
    
    print(f"Total cross-repo references: {len(results)}")
    for r in results:
        print(f"  [{r['from_repo']}->{r.get('to_repo','?')}] {r['file']}:{r['line']} {r['content'][:100]}")
    
    csv_path = os.path.join(OUT_DIR, 'cross_repo_imports_raw.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['from_repo','to_repo','file','line','content','type'])
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"Saved: {csv_path}")
    
    return results

# === 4. ACTIVE_BRAND USAGE SCAN ===
def scan_active_brand():
    print("\n=== ACTIVE_BRAND USAGE SCAN ===")
    results = []
    for fp, rel in scan_files(ZBC_ROOT, CODE_EXTS):
        lines = read_file(fp)
        if not lines:
            continue
        for i, line in enumerate(lines, 1):
            if 'active_brand' in line:
                results.append({
                    'file': rel,
                    'line': i,
                    'content': line.strip()[:200],
                })
    print(f"Total active_brand references: {len(results)}")
    by_file = defaultdict(int)
    for r in results:
        by_file[r['file']] += 1
    for f, c in sorted(by_file.items()):
        print(f"  {f}: {c}")
    
    csv_path = os.path.join(OUT_DIR, 'active_brand_raw.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['file','line','content'])
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"Saved: {csv_path}")
    return results

# === 5. ROUTE/API SCAN (Flask/FastAPI) ===
def scan_routes():
    print("\n=== ROUTE/API SCAN ===")
    results = []
    for fp, rel in scan_files(ZBC_ROOT, CODE_EXTS):
        lines = read_file(fp)
        if not lines:
            continue
        for i, line in enumerate(lines, 1):
            # Flask routes
            m = re.search(r'@(?:app|bp|blueprint|api)\.(?:route|get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', line)
            if m:
                results.append({
                    'file': rel,
                    'line': i,
                    'method': 'route',
                    'path': m.group(1),
                    'content': line.strip()[:150],
                })
    print(f"Total routes found: {len(results)}")
    csv_path = os.path.join(OUT_DIR, 'routes_raw.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['file','line','method','path','content'])
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"Saved: {csv_path}")
    return results

# === MAIN ===
if __name__ == '__main__':
    print(f"Output dir: {OUT_DIR}")
    print(f"ZBC: {ZBC_ROOT}")
    print(f"OSAI: {OSAI_ROOT}")
    print()
    
    hp = scan_hardcoded_paths()
    funcs = scan_functions()
    cross = scan_cross_repo_imports()
    ab = scan_active_brand()
    routes = scan_routes()
    
    print("\n=== SCAN COMPLETE ===")
    print(f"Hardcoded paths: {len(hp)}")
    print(f"Functions: {len(funcs)}")
    print(f"Cross-repo refs: {len(cross)}")
    print(f"active_brand refs: {len(ab)}")
    print(f"Routes: {len(routes)}")
