"""
Comprehensive source code reference scanner for 25 empty tables.
Scans all .py, .sql, .html, .js, .md files for table references.
Categorizes: INSERT/REPLACE (Producer), SELECT/UPDATE (Consumer), bare references.
"""
import os, re, json
from collections import defaultdict

ROOT = r'D:\Taikoo-monitor-new'
EXCLUDE_DIRS = {'.venv', '__pycache__', 'node_modules', '.git', '.pytest_cache',
                '.trae', '.trae-cn', '.skills-router', '_pitch_dump', '_ref_frames',
                '_shots', '_u', '_video_frames', '序境', '99-ARCHIVE', 'archive',
                'backups', 'logs', 'staging', 'deliverables', 'data'}

TABLES = ['ai_filter_log','alert_records','app_evidence_records','auth_recovery_tasks',
          'brand_knowledge','case_deep_analysis','collection_logs','collector_quality_log',
          'event_graph_events','event_graph_relations','event_insights','event_mentions',
          'events','feedback_keywords','note_comments','note_review_history',
          'podcast_ai_runs','podcast_entities','professional_accounts','professional_metrics',
          'swire_notes','token_stat','topic_campaign_notes','v4_audit_logs','v4_login_attempts']

# File extensions to scan
SCAN_EXT = {'.py', '.sql', '.html', '.js', '.md', '.yaml', '.yml', '.json', '.ini', '.cfg', '.toml'}

def should_skip(path):
    parts = path.replace(ROOT, '').split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
    return False

def collect_files():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in SCAN_EXT:
                files.append(os.path.join(dirpath, fn))
    return files

def scan_file(filepath):
    """Return dict of table -> list of (line_no, line_text, category)"""
    results = defaultdict(list)
    rel = os.path.relpath(filepath, ROOT)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        return results
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        for tbl in TABLES:
            # Match whole word table name
            pattern = r'\b' + re.escape(tbl) + r'\b'
            if re.search(pattern, line_lower):
                # Categorize
                cat = 'REFERENCE'
                if re.search(r'\b(insert|replace)\b.*\binto\b', line_lower) or re.search(r'\binsert\s+or\b', line_lower):
                    cat = 'PRODUCER'
                elif re.search(r'\b(select|update|delete)\b', line_lower):
                    if 'from' in line_lower or 'update' in line_lower:
                        cat = 'CONSUMER'
                # Also check if it's in a multi-line SQL - look at context
                results[tbl].append({
                    'file': rel,
                    'line': i,
                    'category': cat,
                    'text': line.strip()[:200]
                })
    return results

def main():
    print("Collecting files...")
    files = collect_files()
    print(f"Scanning {len(files)} files...")
    
    all_results = defaultdict(list)
    for fp in files:
        res = scan_file(fp)
        for tbl, refs in res.items():
            all_results[tbl].extend(refs)
    
    # Also do multi-line SQL detection: check if table appears in execute() calls
    # that span multiple lines
    print("Multi-line SQL context scan...")
    ml_results = defaultdict(list)
    for fp in files:
        rel = os.path.relpath(fp, ROOT)
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue
        for tbl in TABLES:
            pattern = r'\b' + re.escape(tbl) + r'\b'
            for m in re.finditer(pattern, content, re.IGNORECASE):
                # Get surrounding context (200 chars before/after)
                start = max(0, m.start() - 200)
                end = min(len(content), m.end() + 200)
                ctx = content[start:end].replace('\n', ' ')
                # Determine if INSERT/SELECT/UPDATE in context
                ctx_lower = ctx.lower()
                cat = 'REFERENCE'
                if re.search(r'\b(insert|replace)\b.*\binto\b', ctx_lower):
                    cat = 'PRODUCER'
                elif re.search(r'\b(select|update)\b.*\b(from|set)\b', ctx_lower):
                    cat = 'CONSUMER'
                # Find line number
                line_no = content[:m.start()].count('\n') + 1
                ml_results[tbl].append({
                    'file': rel,
                    'line': line_no,
                    'category': cat,
                    'context': ctx.strip()[:300]
                })
    
    # Merge: prefer multi-line context results
    final = {}
    for tbl in TABLES:
        refs = ml_results.get(tbl, [])
        # Deduplicate by file+line
        seen = set()
        unique = []
        for r in refs:
            key = (r['file'], r['line'])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        final[tbl] = unique
    
    # Summary
    print("\n=== SUMMARY ===")
    for tbl in TABLES:
        refs = final[tbl]
        producers = [r for r in refs if r['category'] == 'PRODUCER']
        consumers = [r for r in refs if r['category'] == 'CONSUMER']
        others = [r for r in refs if r['category'] == 'REFERENCE']
        files_set = set(r['file'] for r in refs)
        print(f"\n{tbl}: {len(refs)} refs in {len(files_set)} files | PRODUCER={len(producers)} CONSUMER={len(consumers)} OTHER={len(others)}")
        if producers:
            print(f"  Producers:")
            for r in producers[:5]:
                print(f"    {r['file']}:{r['line']} - {r['context'][:120]}")
        if consumers:
            print(f"  Consumers:")
            for r in consumers[:5]:
                print(f"    {r['file']}:{r['line']} - {r['context'][:120]}")
        if others and not producers and not consumers:
            print(f"  References:")
            for r in others[:5]:
                print(f"    {r['file']}:{r['line']} - {r['context'][:120]}")
    
    # Save full results
    out = os.path.join(ROOT, 'audit', 'source_refs.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to {out}")

if __name__ == '__main__':
    main()
