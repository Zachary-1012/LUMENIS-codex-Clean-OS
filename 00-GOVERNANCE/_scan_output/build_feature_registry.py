#!/usr/bin/env python3
"""Feature Registry Generator — Shard D / Team 1

Reads functions_raw.json (2653 functions from real source scan),
maps each to one of 50 product domains, groups into Features,
assigns F-XXXX IDs, determines evidence-based Status,
outputs feature_registry.csv + feature_registry.md.

Status rules (evidence-based, no fake upgrades):
  PLANNED     = file/function exists but is stub, TODO, or no real logic
  IMPLEMENTED = function has real body (not just pass/raise NotImplementedError)
  INTEGRATED  = function is called by app.py routes or main entry points
  TESTED      = has corresponding test file in tests/
  VERIFIED    = test passes + evidence of runtime operation (requires manual confirmation)
  RELEASED    = in production release (requires release evidence)
  OPERATING   = confirmed running in production (requires ops evidence)

This generator marks IMPLEMENTED/INTEGRATED/TESTED based on code evidence.
VERIFIED/RELEASED/OPERATING require external evidence and are NOT auto-assigned.
"""
import os, re, json, csv
from collections import defaultdict

ZBC_ROOT = r'D:\Taikoo-monitor-new'
SCAN_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE', '_scan_output')
OUT_DIR = os.path.join(ZBC_ROOT, '00-GOVERNANCE')

# Load functions
with open(os.path.join(SCAN_DIR, 'functions_raw.json'), 'r', encoding='utf-8') as f:
    all_functions = json.load(f)

# Load routes for integration detection
routes = []
routes_csv = os.path.join(SCAN_DIR, 'routes_raw.csv')
if os.path.exists(routes_csv):
    with open(routes_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        routes = list(reader)

# ---------------------------------------------------------------------------
# Domain mapping: file path patterns -> domain ID
# Ordered by specificity (first match wins)
# ---------------------------------------------------------------------------
DOMAIN_MAP = [
    # Domain 09: Schema / Function Registry (this module itself)
    (r'core[\\/]repository_registry', '09', 'Schema/Function Registry', 'Repository Registry'),
    (r'00-GOVERNANCE', '09', 'Schema/Function Registry', 'Governance Registry'),
    # Domain 25: AI Provider / Gateway
    (r'ai_gateway|ai_provider|provider_registry|lumenis_gateway|ai_channel', '25', 'AI Provider/Gateway', 'AI Gateway'),
    (r'intelligence\.py|ai_engine', '25', 'AI Provider/Gateway', 'AI Engine'),
    # Domain 26: AI Analyzer / AI Filter
    (r'ai_analyzer|ai_filter|sentiment|emotion_analy|content_analy', '26', 'AI Analyzer/Filter', 'AI Analyzer'),
    # Domain 27: AI Learning / Feedback
    (r'ai_learning|feedback|learning_asset|ai_feedback', '27', 'AI Learning/Feedback', 'AI Learning'),
    # Domain 39: Evidence
    (r'evidence', '39', 'Evidence', 'Evidence Management'),
    # Domain 40: Evaluation
    (r'evaluation|eval_', '40', 'Evaluation', 'Evaluation'),
    # Domain 41: Trace / Observability
    (r'trace|observability|tracing|otel', '41', 'Trace/Observability', 'Trace'),
    # Domain 34: Permission
    (r'permission|auth_center|auth_recovery', '34', 'Permission', 'Permission/Auth'),
    # Domain 48: Security / Audit
    (r'security|audit|compliance|csrf|xss|sqli', '48', 'Security/Audit', 'Security'),
    # Domain 35: Action Firewall
    (r'action_firewall|firewall', '35', 'Action Firewall', 'Action Firewall'),
    # Domain 36: Effect Fence
    (r'effect_fence', '36', 'Effect Fence', 'Effect Fence'),
    # Domain 37: Agent Identity
    (r'agent_identity', '37', 'Agent Identity', 'Agent Identity'),
    # Domain 38: Delegation / OBO / JIT
    (r'delegation|obo_|jit_|on_behalf', '38', 'Delegation/OBO/JIT', 'Delegation'),
    # Domain 30: Agent
    (r'agent', '30', 'Agent', 'Agent Runtime'),
    # Domain 28: Skill Registry
    (r'skill_registry|skill_hub', '28', 'Skill Registry', 'Skill Registry'),
    # Domain 29: Skill Execution
    (r'skill_exec|skill_run|skill_engine', '29', 'Skill Execution', 'Skill Execution'),
    # Domain 31: Orchestrator
    (r'orchestrat', '31', 'Orchestrator', 'Orchestrator'),
    # Domain 32: Engineering Loop
    (r'engineering_loop|eng_loop|self_heal|auto_fix', '32', 'Engineering Loop', 'Engineering Loop'),
    # Domain 33: Harness
    (r'harness', '33', 'Harness', 'Harness'),
    # Domain 42: Checkpoint / Resume / Recovery
    (r'checkpoint|resume|recovery|reaper|dlq', '42', 'Checkpoint/Resume/Recovery', 'Recovery'),
    # Domain 43: Memory / Learning Asset
    (r'memory|learning_asset', '43', 'Memory/Learning Asset', 'Memory'),
    # Domain 18: KOS
    (r'kos', '18', 'KOS', 'KOS Management'),
    # Domain 19: KOL
    (r'kol', '19', 'KOL', 'KOL Management'),
    # Domain 20: KOC
    (r'koc', '20', 'KOC', 'KOC Management'),
    # Domain 13: Risk Engine
    (r'risk_engine|risk_', '13', 'Risk Engine', 'Risk Engine'),
    # Domain 14: Alert
    (r'alert|warning|notify_center', '14', 'Alert', 'Alert/Notification'),
    # Domain 24: Notification
    (r'notification|notif_', '24', 'Notification', 'Notification'),
    # Domain 10: Event
    (r'event_engine|event_center|aggregate_events|event_', '10', 'Event', 'Event Management'),
    # Domain 11: Event Graph
    (r'event_graph|event_relation', '11', 'Event Graph', 'Event Graph'),
    # Domain 12: Case / Public Opinion
    (r'case_|public_opinion|opinion_center|case_ai', '12', 'Case/Public Opinion', 'Case Management'),
    # Domain 21: Campaign / Topic
    (r'campaign|topic_|topic_center|marketing', '21', 'Campaign/Topic', 'Campaign/Topic'),
    # Domain 22: Report
    (r'report_|daily_report|weekly_report|monthly_report|report_center|build_daily', '22', 'Report', 'Report Generation'),
    # Domain 23: Import / Export
    (r'import_|export_|report_export', '23', 'Import/Export', 'Import/Export'),
    # Domain 15: Metric / Statistics
    (r'metric|statistic|stats_', '15', 'Metric/Statistics', 'Metrics/Stats'),
    # Domain 16: Dashboard
    (r'dashboard|overview|home_', '16', 'Dashboard', 'Dashboard'),
    # Domain 17: Search / Filter
    (r'search|filter_|note_search', '17', 'Search/Filter', 'Search/Filter'),
    # Domain 03: 数据采集
    (r'collector|crawl_|spider|scrape|fetch_', '03', 'Data Collection', 'Collector'),
    # Domain 04: 数据源 / Source Library
    (r'source_|source_lib|platform_adapter|adapter_', '04', 'Source Library', 'Source/Adapter'),
    # Domain 44: Browser / CDP / Login
    (r'browser|cdp|playwright|login_|cookie|session_', '44', 'Browser/CDP/Login', 'Browser/CDP'),
    # Domain 06: Subject Filter / Dedup
    (r'subject_|dedup|duplicate', '06', 'Subject Filter/Dedup', 'Subject Filter/Dedup'),
    # Domain 07: Data Quality
    (r'quality|data_quality|qos', '07', 'Data Quality', 'Data Quality'),
    # Domain 08: Canonical Data
    (r'canonical|normalize|standardize', '08', 'Canonical Data', 'Canonical/Normalize'),
    # Domain 05: Raw Data
    (r'raw_|raw_data', '05', 'Raw Data', 'Raw Data'),
    # Domain 47: DB / Migration
    (r'migration|alembic|db_init|schema_|models\.py', '47', 'DB/Migration', 'DB/Migration'),
    # Domain 46: API
    (r'api_|routes|blueprint|endpoint', '46', 'API', 'API/Routes'),
    # Domain 45: Frontend / UI / UX
    (r'templates|static|frontend|ui_|ux_', '45', 'Frontend/UI/UX', 'Frontend/UI'),
    # Domain 49: CI/CD / Release
    (r'\.github|ci_|cd_|release_|deploy', '49', 'CI/CD/Release', 'CI/CD/Release'),
    # Domain 50: Production Runtime
    (r'runtime|health|smoke|prod_|production', '50', 'Production Runtime', 'Production Runtime'),
    # Domain 02: Repository / Runtime / Environment
    (r'config|environment|env_|settings', '02', 'Repository/Runtime/Environment', 'Config/Environment'),
    # Domain 01: Product / Domain / Subject (catch-all for brand/product)
    (r'brand_|product_|profile_|subject_rules', '01', 'Product/Domain/Subject', 'Product/Subject'),
    # Domain 12 fallback: app.py main routes (public opinion core)
    (r'app\.py', '12', 'Case/Public Opinion', 'Main Application'),
]

DEFAULT_DOMAIN = ('01', 'Product/Domain/Subject', 'Product/Subject')


def map_domain(filepath):
    """Map a file path to a domain. First matching pattern wins."""
    fp = filepath.replace('/', '\\').lower()
    for pattern, did, dname, fname in DOMAIN_MAP:
        if re.search(pattern, fp, re.IGNORECASE):
            return did, dname, fname
    return DEFAULT_DOMAIN


# ---------------------------------------------------------------------------
# Function body analysis: is it a stub or real implementation?
# ---------------------------------------------------------------------------
def is_stub_function(filepath, line_num):
    """Check if a function is a stub (pass, raise NotImplementedError, TODO)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        return False  # can't determine, assume real

    # Read next 10 lines after function definition
    body_lines = []
    for i in range(line_num, min(line_num + 15, len(lines))):
        body_lines.append(lines[i])

    body = ''.join(body_lines)

    # Check for stub patterns
    stub_indicators = [
        r'^\s*pass\s*$',
        r'raise\s+NotImplementedError',
        r'#\s*TODO',
        r'#\s*FIXME',
        r'#\s*STUB',
        r'"""\s*TODO',
    ]
    for pat in stub_indicators:
        if re.search(pat, body, re.MULTILINE):
            # But if there's also real code (not just the stub), it's not a stub
            # Check if body has any real statements
            real_code = re.search(r'^\s*(?!pass|raise|#|"""|\'\'\'|return\s+None|return\s*$)\S+', body, re.MULTILINE)
            if not real_code:
                return True
    return False


# ---------------------------------------------------------------------------
# Test detection: does a test file exist for this module?
# ---------------------------------------------------------------------------
def has_tests(filepath):
    """Check if there's a test file for this module."""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    test_dir = os.path.join(ZBC_ROOT, 'tests')
    if not os.path.isdir(test_dir):
        return False
    for fn in os.listdir(test_dir):
        if fn.endswith('.py') and basename in fn:
            return True
    # Also check for test_ prefix patterns
    module_name = basename.replace('.py', '')
    for fn in os.listdir(test_dir):
        if fn.endswith('.py') and module_name in fn:
            return True
    return False


# ---------------------------------------------------------------------------
# Integration detection: is this function called by app.py or routes?
# ---------------------------------------------------------------------------
def is_integrated(filepath, func_name):
    """Check if function is imported/called by app.py or main route files."""
    if not func_name:
        return False
    # Check app.py
    app_path = os.path.join(ZBC_ROOT, 'app.py')
    if os.path.isfile(app_path):
        try:
            with open(app_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if func_name in content:
                return True
        except:
            pass
    # Check route files
    routes_dir = os.path.join(ZBC_ROOT, 'routes')
    if os.path.isdir(routes_dir):
        for fn in os.listdir(routes_dir):
            if fn.endswith('.py'):
                try:
                    with open(os.path.join(routes_dir, fn), 'r', encoding='utf-8', errors='ignore') as f:
                        if func_name in f.read():
                            return True
                except:
                    pass
    return False


# ---------------------------------------------------------------------------
# Build Feature Registry
# ---------------------------------------------------------------------------
print("Building Feature Registry...")
print(f"Total functions: {len(all_functions)}")

# Group functions by file
functions_by_file = defaultdict(list)
for func in all_functions:
    functions_by_file[func['repo'] + '|' + func['file']].append(func)

print(f"Unique files: {len(functions_by_file)}")

# Build features: one feature per file (or per class if file has multiple classes)
features = []
feature_counter = 0

def _add_feature(fid, did, dname, feature_name, filepath, repo, funcs, abs_path):
    """Helper to add a feature to the registry."""
    # Determine status
    real_funcs = [f for f in funcs if not is_stub_function(abs_path, f['line'])]
    stub_funcs = [f for f in funcs if is_stub_function(abs_path, f['line'])]

    if not real_funcs and stub_funcs:
        status = 'PLANNED'
    elif real_funcs:
        # Check integration
        integrated = any(is_integrated(abs_path, f['function']) for f in real_funcs[:5])
        tested = has_tests(abs_path)
        if tested and integrated:
            status = 'TESTED'
        elif integrated:
            status = 'INTEGRATED'
        else:
            status = 'IMPLEMENTED'
    else:
        status = 'PLANNED'

    # Collect function names
    func_names = [f['function'] for f in funcs]
    func_str = '; '.join(func_names[:10])
    if len(func_names) > 10:
        func_str += f' ... (+{len(func_names)-10} more)'

    # DB/API/Frontend detection from file path
    has_db = any(kw in filepath.lower() for kw in ['db', 'model', 'database', 'sqlite', 'sql'])
    has_api = any(kw in filepath.lower() for kw in ['route', 'api', 'endpoint', 'app.py'])
    has_frontend = any(kw in filepath.lower() for kw in ['template', 'static', 'frontend', 'ui'])

    features.append({
        'Feature ID': fid,
        'Domain': f"{did} {dname}",
        'Feature': feature_name,
        'Function': func_str,
        'File': filepath,
        'Repo': repo,
        'Caller': '',  # would need call graph analysis
        'Callee': '',
        'Input': '',
        'Output': '',
        'DB': 'Yes' if has_db else 'No',
        'API': 'Yes' if has_api else 'No',
        'Frontend': 'Yes' if has_frontend else 'No',
        'Permission': '',
        'Agent-AI': '',
        'Evidence': f"Source scan: {len(funcs)} functions, {len(real_funcs)} real, {len(stub_funcs)} stubs",
        'Evaluation': '',
        'Test': 'Yes' if has_tests(abs_path) else 'No',
        'Runtime': '',
        'Status': status,
        'Risk': '',
        'Owner': 'Shard-D/Team1',
        'Version': '1.0',
    })


# Re-run to populate features (the helper was defined after first loop, need to rebuild)
features = []
feature_counter = 0

for file_key, funcs in sorted(functions_by_file.items()):
    repo, filepath = file_key.split('|', 1)
    abs_path = os.path.join(ZBC_ROOT, filepath) if repo == 'ZBC' else os.path.join(r'D:\Zachary OS AI', filepath)
    did, dname, feature_base_name = map_domain(filepath)

    classes_in_file = defaultdict(list)
    standalone_funcs = []
    for func in funcs:
        if func.get('class'):
            classes_in_file[func['class']].append(func)
        else:
            standalone_funcs.append(func)

    if len(classes_in_file) > 1:
        for cls_name, cls_funcs in sorted(classes_in_file.items()):
            feature_counter += 1
            fid = f"F-{feature_counter:04d}"
            _add_feature(fid, did, dname, f"{feature_base_name} - {cls_name}", filepath, repo, cls_funcs, abs_path)
        if standalone_funcs:
            feature_counter += 1
            fid = f"F-{feature_counter:04d}"
            _add_feature(fid, did, dname, f"{feature_base_name} - Module Functions", filepath, repo, standalone_funcs, abs_path)
    else:
        feature_counter += 1
        fid = f"F-{feature_counter:04d}"
        _add_feature(fid, did, dname, f"{feature_base_name} - {os.path.basename(filepath)}", filepath, repo, funcs, abs_path)

print(f"\nTotal features: {len(features)}")

# Status distribution
status_dist = defaultdict(int)
domain_dist = defaultdict(int)
for f in features:
    status_dist[f['Status']] += 1
    domain_dist[f['Domain']] += 1

print(f"\nStatus distribution:")
for s, c in sorted(status_dist.items()):
    print(f"  {s}: {c}")

print(f"\nDomain distribution (top 20):")
for d, c in sorted(domain_dist.items(), key=lambda x: -x[1])[:20]:
    print(f"  {d}: {c}")

# ---------------------------------------------------------------------------
# Output CSV
# ---------------------------------------------------------------------------
FIELDS = ['Feature ID','Domain','Feature','Function','File','Repo','Caller','Callee',
          'Input','Output','DB','API','Frontend','Permission','Agent-AI','Evidence',
          'Evaluation','Test','Runtime','Status','Risk','Owner','Version']

csv_path = os.path.join(OUT_DIR, 'feature_registry.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
    w.writeheader()
    for feat in features:
        w.writerow(feat)
print(f"\nSaved CSV: {csv_path}")

# ---------------------------------------------------------------------------
# Output Markdown
# ---------------------------------------------------------------------------
md_path = os.path.join(OUT_DIR, 'feature_registry.md')
with open(md_path, 'w', encoding='utf-8') as f:
    f.write("# 序境 / ZBC Feature Registry\n\n")
    f.write(f"> Generated: 2026-09-06 | Shard D / Team 1 | Source: real code scan\n")
    f.write(f"> Total Features: {len(features)} | Total Functions: {len(all_functions)}\n\n")

    f.write("## Status Distribution\n\n")
    f.write("| Status | Count |\n|---|---|\n")
    for s in ['PLANNED','IMPLEMENTED','INTEGRATED','TESTED','VERIFIED','RELEASED','OPERATING']:
        f.write(f"| {s} | {status_dist.get(s, 0)} |\n")
    f.write("\n")

    f.write("## Domain Distribution\n\n")
    f.write("| Domain | Count |\n|---|---|\n")
    for d, c in sorted(domain_dist.items()):
        f.write(f"| {d} | {c} |\n")
    f.write("\n")

    f.write("## Feature Registry (Full)\n\n")
    f.write("| ID | Domain | Feature | File | Funcs | Status | Test | Evidence |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for feat in features:
        func_count = feat['Function'].count(';') + 1 if feat['Function'] else 0
        f.write(f"| {feat['Feature ID']} | {feat['Domain']} | {feat['Feature'][:60]} | {feat['File'][:50]} | {func_count} | {feat['Status']} | {feat['Test']} | {feat['Evidence'][:50]} |\n")

print(f"Saved MD: {md_path}")
print("\n=== FEATURE REGISTRY GENERATION COMPLETE ===")
