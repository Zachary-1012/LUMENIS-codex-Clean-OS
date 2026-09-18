#!/usr/bin/env python3
"""Batch hardcoded path cleanup - uses core.repository_registry.
Scans production .py files, replaces hardcoded absolute paths with registry calls.
Conservative: only replaces unambiguous patterns, reports rest for manual review.
"""
import os, re, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)

SKIP_DIRS = {'.venv', 'node_modules', '.git', '__pycache__', '.pytest_cache',
             '99-ARCHIVE', 'archive', 'backups', 'logs', 'data', '.ollama',
             '.trae', '.trae-cn', '.vscode', '序境', 'dist', 'build',
             '_shots', '_video_frames', '_ref_frames', '_pitch_dump', '_u',
             'nodejs', 'docker', '00-GOVERNANCE/_scan_output', 'docs',
             'static', 'migrations', 'alembic'}

# Production dirs to scan (root .py files + key module dirs)
SCAN_DIRS = ['', 'collector_v2', 'platform_adapters', 'browser_runtime',
             'account_keepalive', 'collector_guard', 'report_export',
             'evaluation', 'audit', 'config', 'contracts', 'core',
             'ad_intelligence', 'proxy_pool', 'edge-cdp-general',
             'edge-cdp-newaccount', 'edge-cdp-profile', 'edge-cdp-retinaut',
             'ref_gpt_v2', 'lumenis']

PATTERNS = [
    (r'D:\\Taikoo-monitor-new', 'ZBC'),
    (r'D:\\Zachary OS AI', 'OSAI'),
    (r'C:\\Users\\28049', 'HOME'),
]

def is_production_file(filepath):
    """Check if file is production code (not test/script/temp/archive)."""
    rel = os.path.relpath(filepath, REPO_ROOT)
    parts = rel.replace('\\', '/').split('/')
    # Skip tests
    if 'tests' in parts or 'test' in parts[0]:
        return False
    # Skip temp files starting with _
    basename = os.path.basename(filepath)
    if basename.startswith('_') and basename.endswith('.py'):
        return False
    # Skip scripts dir (dev tools)
    if 'scripts' in parts:
        return False
    # Skip scan output
    if '_scan_output' in parts:
        return False
    return True

def scan_file(filepath):
    """Scan a file for hardcoded paths, return list of (line_no, line, pattern)."""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return results
    for i, line in enumerate(lines, 1):
        for pat, name in PATTERNS:
            if pat in line:
                results.append((i, line.rstrip(), name))
    return results

def safe_replace(filepath, matches):
    """Attempt safe replacement of hardcoded paths. Returns (replaced_count, skipped)."""
    replaced = 0
    skipped = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return 0, len(matches)

    original = content
    has_import = 'from core.repository_registry import' in content or 'import core.repository_registry' in content

    # Pattern 1: r"D:\Taikoo-monitor-new\data\monitor.db" -> get_db_path()
    content = re.sub(
        r'r["\']D:\\Taikoo-monitor-new\\data\\monitor\.db["\']',
        'get_db_path()', content)
    content = re.sub(
        r'["\']D:\\Taikoo-monitor-new\\data\\monitor\.db["\']',
        'get_db_path()', content)

    # Pattern 2: r"D:\Taikoo-monitor-new\data\..." -> os.path.join(get_data_dir(), "...")
    def repl_data(m):
        sub = m.group(1).replace('\\', '/').strip('/')
        if sub:
            return f'os.path.join(get_data_dir(), "{sub}")'
        return 'get_data_dir()'
    content = re.sub(
        r'r["\']D:\\Taikoo-monitor-new\\data\\([^"\']*)["\']',
        repl_data, content)

    # Pattern 3: r"D:\Taikoo-monitor-new\..." -> os.path.join(get_repo_root(), "...")
    def repl_root(m):
        sub = m.group(1).replace('\\', '/').strip('/')
        if sub:
            return f'os.path.join(get_repo_root(), "{sub}")'
        return 'get_repo_root()'
    content = re.sub(
        r'r["\']D:\\Taikoo-monitor-new\\([^"\']*)["\']',
        repl_root, content)
    content = re.sub(
        r'["\']D:\\Taikoo-monitor-new\\([^"\']*)["\']',
        repl_root, content)

    # Pattern 4: D:\Zachary OS AI\... -> get_osai_root() based
    def repl_osai(m):
        sub = m.group(1).replace('\\', '/').strip('/')
        if sub:
            return f'os.path.join(get_osai_root(), "{sub}")'
        return 'get_osai_root()'
    content = re.sub(
        r'r["\']D:\\Zachary OS AI\\([^"\']*)["\']',
        repl_osai, content)

    # Add import if we made replacements and no existing import
    if content != original and not has_import:
        # Find first import line or shebang
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_idx = i
                break
            if i > 20:
                break
        lines.insert(insert_idx, 'from core.repository_registry import get_repo_root, get_data_dir, get_db_path, get_osai_root')
        content = '\n'.join(lines)

    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            replaced = len(matches)
        except:
            skipped = len(matches)
    else:
        skipped = len(matches)

    return replaced, skipped

def main():
    print("=" * 70)
    print("BATCH HARDCODED PATH CLEANUP")
    print("=" * 70)

    all_files = []
    for scan_dir in SCAN_DIRS:
        target = os.path.join(REPO_ROOT, scan_dir) if scan_dir else REPO_ROOT
        if not os.path.isdir(target):
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                if fn.endswith('.py'):
                    fp = os.path.join(root, fn)
                    if is_production_file(fp):
                        all_files.append(fp)

    print(f"Scanning {len(all_files)} production .py files...")

    total_matches = 0
    files_with_issues = []
    for fp in all_files:
        matches = scan_file(fp)
        if matches:
            rel = os.path.relpath(fp, REPO_ROOT)
            files_with_issues.append((fp, rel, matches))
            total_matches += len(matches)

    print(f"\nFound {total_matches} hardcoded path occurrences in {len(files_with_issues)} files:")
    for fp, rel, matches in files_with_issues:
        print(f"\n  {rel}:")
        for line_no, line, pat in matches[:5]:
            print(f"    L{line_no} [{pat}]: {line[:100]}")
        if len(matches) > 5:
            print(f"    ... and {len(matches)-5} more")

    # Attempt replacement
    print("\n" + "=" * 70)
    print("ATTEMPTING SAFE REPLACEMENT...")
    print("=" * 70)
    total_replaced = 0
    total_skipped = 0
    for fp, rel, matches in files_with_issues:
        # Skip repository_registry.py itself (legitimate fallback)
        if 'repository_registry' in rel:
            print(f"  SKIP {rel} (registry itself - legitimate fallbacks)")
            total_skipped += len(matches)
            continue
        r, s = safe_replace(fp, matches)
        total_replaced += r
        total_skipped += s
        status = "REPLACED" if r > 0 else "SKIPPED"
        print(f"  {status} {rel}: {r} replaced, {s} skipped")

    print(f"\n{'='*70}")
    print(f"RESULT: {total_replaced} replaced, {total_skipped} skipped/legitimate")
    print(f"{'='*70}")

    # Verify: re-scan
    print("\nVERIFICATION - re-scanning production files:")
    remaining = 0
    for fp, rel, _ in files_with_issues:
        if 'repository_registry' in rel:
            continue
        matches = scan_file(fp)
        if matches:
            remaining += len(matches)
            print(f"  REMAINING {rel}: {len(matches)} occurrences")
    if remaining == 0:
        print("  ALL PRODUCTION HARDCODED PATHS CLEARED!")
    else:
        print(f"  {remaining} remaining (need manual review)")

if __name__ == '__main__':
    main()
