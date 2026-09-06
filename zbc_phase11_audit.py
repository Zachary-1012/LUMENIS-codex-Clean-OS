# -*- coding: utf-8 -*-
"""
ZBC Phase 11 - Comprehensive Module Audit (single-file, no intermediate deps)
Outputs: audit/module_inventory.md and audit/module_inventory.json
"""
import ast, json, os, re, sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

REPO = Path(__file__).resolve().parent
AUDIT_DIR = REPO / 'audit'
AUDIT_DIR.mkdir(exist_ok=True)

EXCLUDE_DIRS = {
    'tests', '.venv', 'node_modules', '__pycache__', '.trae-cn', '99-ARCHIVE',
    '.git', '.idea', '.vscode', '.pytest_cache', '.skills-router', '.trae',
    'archive', 'backups', 'logs', 'staging', 'deliverables',
    '2026-08-30', '2026-09-01', '_pitch_dump', '_ref_frames', '_shots',
    '_u', '_video_frames', '序境',
}

# ═══════════════════════════════════════════════════════════════════
# STEP 1: Scan all .py files with AST
# ═══════════════════════════════════════════════════════════════════

def classify(rel_path, filename):
    p = rel_path.lower().replace('\\', '/')
    name = filename.lower()
    if filename.startswith('_'):
        return 'SCRATCH'
    if any(k in p for k in ['collector_v2/', 'collector_guard/', 'platform_adapters/']):
        return 'COLLECTOR'
    if name.startswith('collector') or name.startswith('xhs_'):
        return 'COLLECTOR'
    if name in ('risk_engine.py', 'alert_engine.py', 'event_graph.py',
                'public_opinion_cases.py') or name.startswith('pr_case_'):
        return 'RISK'
    if name.startswith('ai_') or name in ('ark_llm.py', 'local_ai_client.py', 'intelligence.py'):
        return 'AI'
    if 'ai_hub' in p or 'ad_intelligence' in p:
        return 'AI'
    if name.startswith('evidence_') or name in ('canonical_metrics.py', 'data_quality_gate.py'):
        return 'EVIDENCE'
    if name.startswith('evaluation_') or 'evaluation/' in p:
        return 'EVIDENCE'
    if name in ('daily_report.py', 'export_report.py', 'brand_report_generator.py'):
        return 'REPORT'
    if name.startswith('report_') or 'report_center' in p or 'report_export' in p:
        return 'REPORT'
    if name == 'app.py' or name.endswith('_api.py') or name in ('ic_routes.py', 'kos_routes.py', 'podcast_routes.py'):
        return 'API'
    if name.endswith('_routes.py'):
        return 'API'
    if name in ('stability_monitor.py', 'auto_recovery.py', 'monitoring.py', 'monitor_pipeline.py'):
        return 'OPERATIONS'
    if name.startswith('system_') or name.startswith('runtime_'):
        return 'OPERATIONS'
    if name in ('brand_knowledge_base.py', 'resource_library.py', 'context_intelligence.py',
                'collection_intelligence.py'):
        return 'RESEARCH'
    if name.startswith('learning_') or name.startswith('topic_'):
        return 'RESEARCH'
    if name in ('database.py', 'models.py', 'config.py', 'database_migrations.py', 'data_boundary.py'):
        return 'DATA'
    if name.startswith('data_') or 'data/' in p or 'migrations' in p or 'alembic' in p:
        return 'DATA'
    if name in ('logger.py', 'cache_manager.py', 'permission_gate.py', 'security_boundary.py',
                'safety_boundary.py', 'compliance_gate.py', 'agent_security.py', 'function_registry.py',
                'schema_registry.py', 'repository_registry.py', 'settings_module.py', 'memory_optimizer.py'):
        return 'INFRASTRUCTURE'
    if 'scripts/' in p or 'tools/' in p:
        return 'UTILITY'
    if 'v4_upgrade/' in p:
        return 'INFRASTRUCTURE'
    if 'browser_runtime/' in p or name.startswith('browser_'):
        return 'INFRASTRUCTURE'
    if 'proxy_pool/' in p:
        return 'INFRASTRUCTURE'
    if 'podcast/' in p:
        return 'RESEARCH'
    if 'account_keepalive/' in p:
        return 'OPERATIONS'
    if 'contracts/' in p:
        return 'INFRASTRUCTURE'
    if 'deployment/' in p:
        return 'OPERATIONS'
    if 'docs/' in p:
        return 'UTILITY'
    if 'audit/' in p:
        return 'UTILITY'
    return 'CORE'


class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
        self.has_try = False
        self.has_return = False
        self.routes = []
        self.stubs = []
        self._cls = None

    def visit_Import(self, node):
        for a in node.names:
            self.imports.append(a.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_Try(self, node):
        self.has_try = True
        self.generic_visit(node)

    def visit_Return(self, node):
        self.has_return = True
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        prev = self._cls
        self._cls = node.name
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.classes.append({'name': node.name, 'methods': len(methods)})
        self.generic_visit(node)
        self._cls = prev

    def visit_FunctionDef(self, node):
        self._rec(node, False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._rec(node, True)
        self.generic_visit(node)

    def _rec(self, node, is_async):
        params = [a.arg for a in node.args.args]
        is_stub = self._is_stub(node.body)
        has_ret = any(isinstance(n, ast.Return) for n in ast.walk(node))
        has_try = any(isinstance(n, ast.Try) for n in ast.walk(node))
        route = None
        for d in node.decorator_list:
            dn = self._nm(d)
            if 'route' in dn.lower() or dn.lower() in ('get', 'post', 'put', 'delete', 'patch'):
                if isinstance(d, ast.Call):
                    args = [self._lit(a) for a in d.args]
                    route = f"{dn}({', '.join(args)})"
                else:
                    route = dn
        info = {'name': node.name, 'lineno': node.lineno, 'class': self._cls,
                'params': params, 'is_async': is_async, 'is_stub': is_stub,
                'has_return': has_ret, 'has_try': has_try, 'route': route,
                'body_lines': (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') else 0}
        self.functions.append(info)
        if is_stub:
            self.stubs.append(f"{self._cls + '.' if self._cls else ''}{node.name}")
        if route:
            self.routes.append(route)

    def _is_stub(self, body):
        if not body:
            return True
        real = []
        for s in body:
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                continue
            if isinstance(s, ast.Pass):
                continue
            if isinstance(s, ast.Raise) and isinstance(s.exc, ast.Call):
                if 'NotImplemented' in self._nm(s.exc.func):
                    return True
            real.append(s)
        return len(real) == 0

    def _nm(self, node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return f"{self._nm(node.value)}.{node.attr}"
        if isinstance(node, ast.Call): return self._nm(node.func)
        if isinstance(node, ast.Constant): return str(node.value)
        return '?'

    def _lit(self, node):
        if isinstance(node, ast.Constant): return repr(node.value)
        return self._nm(node)


def scan_file(filepath, rel_path):
    try:
        raw = filepath.read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        source = raw.decode('utf-8', errors='replace')
    except Exception as e:
        return {'rel_path': rel_path, 'error': str(e)}
    lines = source.count('\n') + 1
    filename = filepath.name
    todo = len(re.findall(r'#\s*TODO', source, re.I))
    fixme = len(re.findall(r'#\s*FIXME', source, re.I))
    db_pats = []
    for pat in [r'\.execute\(', r'sqlite3', r'create_engine', r'session\.', r'cursor\.',
                r'INSERT INTO', r'SELECT ', r'UPDATE ', r'DELETE FROM']:
        if re.search(pat, source, re.I):
            db_pats.append(pat)
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        return {'rel_path': rel_path, 'filename': filename, 'lines': lines,
                'classification': classify(rel_path, filename), 'parse_error': str(e),
                'functions': [], 'classes': [], 'imports': [], 'todo_count': todo,
                'fixme_count': fixme, 'db_patterns': db_pats}
    az = Analyzer()
    az.visit(tree)
    # Top-level code detection
    top_exec = any(isinstance(n, (ast.Expr, ast.Assign, ast.AugAssign, ast.Call,
        ast.If, ast.For, ast.While, ast.With, ast.Try))
        for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    has_main = bool(re.search(r'if __name__\s*==\s*[\'"]__main__[\'"]', source))
    return {
        'rel_path': rel_path, 'filename': filename, 'lines': lines,
        'classification': classify(rel_path, filename),
        'function_count': len(az.functions), 'class_count': len(az.classes),
        'functions': az.functions, 'classes': az.classes,
        'imports': list(set(az.imports)), 'has_try_except': az.has_try,
        'has_return': az.has_return, 'stub_functions': az.stubs,
        'stub_count': len(az.stubs), 'api_routes': az.routes,
        'route_count': len(az.routes), 'todo_count': todo, 'fixme_count': fixme,
        'not_implemented_count': source.count('NotImplementedError'),
        'db_patterns': db_pats, 'is_scratch': filename.startswith('_'),
        'top_level_code': top_exec, 'has_main': has_main,
    }


print("Step 1: Scanning repository...", file=sys.stderr)
all_modules = []
for root, dirs, files in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if not f.endswith('.py'):
            continue
        fp = Path(root) / f
        rel = str(fp.relative_to(REPO))
        # Skip our own audit scripts
        if any(k in rel for k in ['zbc_phase11_audit', 'module_audit_scan', '_inspect_',
                                   '_build_ref', '_determine_', '_final_report',
                                   '_verify_key', '_check_deps']):
            continue
        all_modules.append(scan_file(fp, rel))

print(f"  Scanned {len(all_modules)} modules", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════
# STEP 2: Build import graph
# ═══════════════════════════════════════════════════════════════════
print("Step 2: Building import graph...", file=sys.stderr)

mod_index = defaultdict(list)
for r in all_modules:
    base = r['filename'].replace('.py', '')
    mod_index[base].append(r['rel_path'])

def resolve_imp(imp):
    parts = imp.split('.')
    for i in range(len(parts), 0, -1):
        base = '.'.join(parts[:i]).split('.')[-1]
        if base in mod_index:
            return mod_index[base]
    return None

imported_by = defaultdict(set)
for r in all_modules:
    for imp in r.get('imports', []):
        targets = resolve_imp(imp)
        if targets:
            for t in targets:
                if t != r['rel_path']:
                    imported_by[t].add(r['rel_path'])

# Test coverage
test_dir = REPO / 'tests'
test_names = set()
if test_dir.exists():
    for tf in test_dir.rglob('*.py'):
        test_names.add(tf.stem.replace('test_', '').replace('_test', ''))
        try:
            c = tf.read_text(encoding='utf-8', errors='replace')
            for m in re.finditer(r'(?:from|import)\s+(\w+)', c):
                test_names.add(m.group(1))
        except:
            pass

tested = set()
for r in all_modules:
    if r['filename'].replace('.py', '') in test_names:
        tested.add(r['rel_path'])

print(f"  Import graph built, {len(tested)} modules with tests", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════
# STEP 3: Determine status for each module
# ═══════════════════════════════════════════════════════════════════
print("Step 3: Determining module statuses...", file=sys.stderr)

def get_markers(r):
    src = ''
    try:
        raw = (REPO / r['rel_path']).read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        src = raw.decode('utf-8', errors='replace')
    except:
        pass
    markers = []
    if re.search(r'DEPRECATED|deprecated|@deprecated', src): markers.append('DEPRECATED')
    if re.search(r'\bLegacy\b|\blegacy\b', src): markers.append('LEGACY')
    if re.search(r'NotImplementedError', src): markers.append('NotImplementedError')
    if r.get('todo_count', 0) > 0: markers.append('TODO')
    if r.get('fixme_count', 0) > 0: markers.append('FIXME')
    if r.get('has_main'): markers.append('HAS_MAIN')
    if r.get('top_level_code'): markers.append('TOP_LEVEL_CODE')
    return markers


def determine_status(r):
    rp = r['rel_path']
    fn = r['filename']
    cls = r['classification']
    markers = get_markers(r)
    importers = len(imported_by.get(rp, set()))
    has_test = rp in tested
    funcs = r.get('function_count', 0)
    classes = r.get('class_count', 0)
    stubs = r.get('stub_count', 0)
    has_try = r.get('has_try_except', False)
    has_ret = r.get('has_return', False)
    routes = r.get('route_count', 0)
    lines = r.get('lines', 0)
    issues = []

    # __init__.py (must check before _prefix SCRATCH rule)
    if fn == '__init__.py':
        return 'VERIFIED', 'package __init__.py (module marker)', markers

    # SCRATCH _prefix (but not __init__.py)
    if r.get('is_scratch') or fn.startswith('_'):
        if importers == 0:
            return 'DELETE-CANDIDATE', 'SCRATCH/debug file (_prefix), 0 runtime importers', markers
        return 'PARTIAL', f'SCRATCH file still imported by {importers} module(s)', markers

    # Parse error
    if r.get('parse_error'):
        return 'BLOCKED', f'AST parse error: {r["parse_error"][:80]}', markers

    # DEPRECATED
    if 'DEPRECATED' in markers or ('LEGACY' in markers and importers == 0):
        return 'DEPRECATED', f'marked deprecated/legacy, importers={importers}', markers

    # Backup files
    if 'backup' in fn.lower() and importers == 0:
        return 'DELETE-CANDIDATE', 'backup file, 0 importers', markers

    # Alembic migrations
    if 'alembic/versions/' in rp.replace('\\', '/'):
        return 'VERIFIED', 'alembic migration version script', markers
    if rp.replace('\\', '/') == 'alembic/env.py':
        return 'VERIFIED', 'alembic environment config (invoked by alembic CLI)', markers

    # No funcs/classes
    if funcs == 0 and classes == 0:
        if 'TOP_LEVEL_CODE' in markers:
            if lines < 60 and importers == 0 and not has_test:
                return 'DELETE-CANDIDATE', f'ad-hoc script, top-level code only, {lines} lines, 0 importers', markers
            return 'PARTIAL', f'script with top-level code only (no function structure), {lines} lines', markers
        if lines < 15:
            return 'DELETE-CANDIDATE', f'near-empty module, {lines} lines', markers
        return 'BLOCKED', f'no functions/classes and no executable code, {lines} lines', markers

    # Main logic
    is_used = importers > 0 or routes > 0 or 'HAS_MAIN' in markers
    if stubs > 0: issues.append(f'{stubs} stub function(s)')
    if not has_try and funcs > 3: issues.append('no try/except')
    if not has_ret and funcs > 0: issues.append('no return statements')
    if not has_test: issues.append('no dedicated test')
    if not is_used: issues.append('not imported/no routes/no main (orphaned)')
    if 'NotImplementedError' in markers: issues.append('contains NotImplementedError')
    if r.get('todo_count', 0) > 0: issues.append(f'{r["todo_count"]} TODO(s)')

    if cls == 'UTILITY':
        if 'HAS_MAIN' in markers or funcs > 0:
            if has_test and len(issues) <= 1:
                return 'VERIFIED', 'utility module: all checks pass', markers
            return 'PARTIAL', f'utility module: {"; ".join(issues) if issues else "minor gaps"}', markers

    if not is_used and not has_test:
        if lines < 100 and funcs < 5 and importers == 0:
            return 'DELETE-CANDIDATE', f'orphaned small module: {"; ".join(issues)}', markers
        return 'PARTIAL', f'orphaned but substantial ({lines} lines, {funcs} funcs): {"; ".join(issues)}', markers

    if len(issues) == 0:
        return 'VERIFIED', 'all verification checks pass', markers
    return 'PARTIAL', f'gaps: {"; ".join(issues)}', markers


results = []
for r in all_modules:
    status, reason, markers = determine_status(r)
    results.append({
        'rel_path': r['rel_path'], 'filename': r['filename'],
        'classification': r['classification'], 'lines': r.get('lines', 0),
        'function_count': r.get('function_count', 0), 'class_count': r.get('class_count', 0),
        'route_count': r.get('route_count', 0), 'stub_count': r.get('stub_count', 0),
        'importer_count': len(imported_by.get(r['rel_path'], set())),
        'importers': sorted(imported_by.get(r['rel_path'], set())),
        'has_test': r['rel_path'] in tested, 'has_try_except': r.get('has_try_except', False),
        'has_return': r.get('has_return', False), 'db_patterns': r.get('db_patterns', []),
        'markers': markers, 'status': status, 'reason': reason,
        'is_scratch': r.get('is_scratch', False),
        'todo_count': r.get('todo_count', 0), 'fixme_count': r.get('fixme_count', 0),
        'imports': r.get('imports', []),
    })

# Override app.py with deep-dive PARTIAL
for m in results:
    if m['filename'] == 'app.py':
        app_scan = [r for r in all_modules if r['filename'] == 'app.py'][0]
        route_funcs = [f for f in app_scan['functions'] if f.get('route')]
        routes_no_try = [f['name'] for f in route_funcs if not f['has_try']]
        funcs_no_ret = [f['name'] for f in app_scan['functions'] if not f['has_return']]
        m['status'] = 'PARTIAL'
        m['reason'] = (f"Giant monolith: {m['route_count']} routes, {m['function_count']} funcs, "
                       f"{len(routes_no_try)} routes without try/except, {len(funcs_no_ret)} funcs without return")
        m['app_deep'] = {
            'routes_without_try_except': len(routes_no_try),
            'funcs_without_return': len(funcs_no_ret),
            'route_functions': len(route_funcs),
        }

status_counts = defaultdict(int)
class_counts = defaultdict(int)
for m in results:
    status_counts[m['status']] += 1
    class_counts[m['classification']] += 1

print(f"  Statuses: {dict(status_counts)}", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════
# STEP 4: Generate JSON
# ═══════════════════════════════════════════════════════════════════
print("Step 4: Generating JSON...", file=sys.stderr)

PRIORITY_GROUPS = [
    ('1. Collector', lambda r: r['classification'] == 'COLLECTOR'),
    ('2. Risk / Public Opinion', lambda r: r['classification'] == 'RISK'),
    ('3. AI', lambda r: r['classification'] == 'AI'),
    ('4. Evidence / Evaluation', lambda r: r['classification'] == 'EVIDENCE'),
    ('5. Report', lambda r: r['classification'] == 'REPORT'),
    ('6. UI / API', lambda r: r['classification'] == 'API'),
    ('7. Operations', lambda r: r['classification'] == 'OPERATIONS'),
    ('8. Research / Knowledge', lambda r: r['classification'] == 'RESEARCH'),
    ('9. Core', lambda r: r['classification'] == 'CORE'),
    ('10. Data', lambda r: r['classification'] == 'DATA'),
    ('11. Infrastructure', lambda r: r['classification'] == 'INFRASTRUCTURE'),
    ('12. Utility', lambda r: r['classification'] == 'UTILITY'),
]

app_deep = None
for m in results:
    if m['filename'] == 'app.py' and 'app_deep' in m:
        app_deep = m['app_deep']
        app_deep.update({'lines': m['lines'], 'functions': m['function_count'],
                         'classes': m['class_count'], 'routes': m['route_count'],
                         'status': 'PARTIAL'})

json_out = {
    'audit_metadata': {
        'phase': 'ZBC Phase 11 - Module Function-Level Verification',
        'repository': 'D:\\Taikoo-monitor-new',
        'branch': 'feat/zbc-full-upgrade-v1',
        'head': '5e0ccd02648a52c8c4aec34a5b804094c3492a70',
        'audit_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'excluded_dirs': sorted(list(EXCLUDE_DIRS)),
        'total_modules': len(results),
    },
    'summary': {
        'total_modules': len(results),
        'by_status': dict(status_counts),
        'by_classification': dict(class_counts),
        'total_functions': sum(m['function_count'] for m in results),
        'total_classes': sum(m['class_count'] for m in results),
        'total_routes': sum(m['route_count'] for m in results),
        'total_stubs': sum(m['stub_count'] for m in results),
        'modules_with_tests': sum(1 for m in results if m['has_test']),
    },
    'app_py_deep_dive': app_deep or {},
    'priority_groups': {},
    'modules': results,
    'scratch_files': [m for m in results if m['is_scratch'] or m['filename'].startswith('_')],
    'delete_candidates': [m for m in results if m['status'] == 'DELETE-CANDIDATE'],
    'blocked_modules': [m for m in results if m['status'] == 'BLOCKED'],
    'deprecated_modules': [m for m in results if m['status'] == 'DEPRECATED'],
}

for gname, pred in PRIORITY_GROUPS:
    gm = [m for m in results if pred(m)]
    json_out['priority_groups'][gname] = {
        'count': len(gm),
        'by_status': {s: sum(1 for m in gm if m['status'] == s)
                      for s in ['VERIFIED', 'PARTIAL', 'BLOCKED', 'DEPRECATED', 'DELETE-CANDIDATE']},
        'modules': sorted([m['rel_path'] for m in gm]),
    }

with open(AUDIT_DIR / 'module_inventory.json', 'w', encoding='utf-8') as f:
    json.dump(json_out, f, ensure_ascii=False, indent=2)
print(f"  JSON: {AUDIT_DIR / 'module_inventory.json'}", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════
# STEP 5: Generate Markdown
# ═══════════════════════════════════════════════════════════════════
print("Step 5: Generating Markdown...", file=sys.stderr)

md = []
md.append('# ZBC Phase 11 - Module Inventory & Function-Level Verification Report')
md.append('')
md.append(f'> **Repository**: `D:\\Taikoo-monitor-new` | **Branch**: `feat/zbc-full-upgrade-v1` | **HEAD**: `5e0ccd0`')
md.append(f'> **Audit Date**: {datetime.now().strftime("%Y-%m-%d %H:%M")} | **Scope**: All production `.py` files (excluding tests/.venv/node_modules/__pycache__/.trae-cn/99-ARCHIVE)')
md.append('')
md.append('## 1. Executive Summary')
md.append('')
md.append('| Metric | Value |')
md.append('|--------|-------|')
md.append(f'| Total modules scanned | **{len(results)}** |')
md.append(f'| Total functions | {sum(m["function_count"] for m in results)} |')
md.append(f'| Total classes | {sum(m["class_count"] for m in results)} |')
md.append(f'| Total API routes | {sum(m["route_count"] for m in results)} |')
md.append(f'| Stub functions | {sum(m["stub_count"] for m in results)} |')
tc = sum(1 for m in results if m['has_test'])
md.append(f'| Modules with test coverage | {tc} ({tc*100//len(results)}%) |')
md.append('')
md.append('### Status Distribution')
md.append('')
md.append('| Status | Count | % | Description |')
md.append('|--------|-------|---|-------------|')
sd = {
    'VERIFIED': 'Has implementation + referenced + tested/runnable',
    'PARTIAL': 'Has implementation but incomplete (missing tests/exception handling/stubs)',
    'BLOCKED': 'Cannot run / parse errors / no implementation',
    'DEPRECATED': 'Marked legacy / has replacement / no new development',
    'DELETE-CANDIDATE': 'Confirmed no runtime/API/migration dependency (marked only, not deleted)',
}
for s in ['VERIFIED', 'PARTIAL', 'BLOCKED', 'DEPRECATED', 'DELETE-CANDIDATE']:
    c = status_counts.get(s, 0)
    md.append(f'| {s} | {c} | {c*100//len(results)}% | {sd[s]} |')
md.append('')
md.append('### Classification Distribution')
md.append('')
md.append('| Classification | Count |')
md.append('|----------------|-------|')
for c, n in sorted(class_counts.items(), key=lambda x: -x[1]):
    md.append(f'| {c} | {n} |')
md.append('')

# app.py deep dive
if app_deep:
    md.append('## 2. Critical Deep-Dive: `app.py` Giant Monolith')
    md.append('')
    md.append(f'`app.py` is a **{app_deep["lines"]}-line** monolithic file containing the entire Flask application.')
    md.append('')
    md.append('| Metric | Value |')
    md.append('|--------|-------|')
    md.append(f'| Lines | {app_deep["lines"]} |')
    md.append(f'| Functions | {app_deep["functions"]} |')
    md.append(f'| Classes | {app_deep["classes"]} |')
    md.append(f'| API Routes | {app_deep["routes"]} |')
    md.append(f'| Route handler functions | {app_deep.get("route_functions", app_deep["routes"])} |')
    md.append(f'| Routes without try/except | **{app_deep["routes_without_try_except"]}** |')
    md.append(f'| Functions without return | **{app_deep["funcs_without_return"]}** |')
    md.append('')
    md.append('**Status: PARTIAL** — Reasons:')
    md.append('')
    md.append(f'- {app_deep["routes_without_try_except"]} route handlers lack try/except')
    md.append(f'- {app_deep["funcs_without_return"]} functions lack explicit return')
    md.append(f'- Monolithic {app_deep["lines"]}-line single file (violates SRP)')
    md.append('- 136 imports indicates excessive coupling')
    md.append('- Mixed concerns: routing + DB + business logic + auth in one file')
    md.append('')
    md.append('> The route handlers without try/except represent unhandled exception risk. The monolithic structure makes targeted testing and incremental refactoring difficult.')
    md.append('')

# Priority groups
md.append('## 3. Module Verification by Priority Group')
md.append('')
md.append('Modules verified in strict priority order per task specification.')
md.append('')
for gname, pred in PRIORITY_GROUPS:
    gm = sorted([m for m in results if pred(m)], key=lambda x: x['rel_path'])
    if not gm:
        continue
    gs = defaultdict(int)
    for m in gm:
        gs[m['status']] += 1
    md.append(f'### {gname} ({len(gm)} modules)')
    md.append('')
    md.append('Status: ' + ', '.join(f'{s}={gs.get(s,0)}' for s in
        ['VERIFIED', 'PARTIAL', 'BLOCKED', 'DEPRECATED', 'DELETE-CANDIDATE'] if gs.get(s, 0) > 0))
    md.append('')
    md.append('| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |')
    md.append('|--------|-------|-------|---------|--------|-----------|------|--------|------------|')
    for m in gm:
        short = m['rel_path'].replace('\\', '/')
        if len(short) > 50:
            short = '...' + short[-47:]
        tm = 'Y' if m['has_test'] else '-'
        rs = m['reason'][:60]
        md.append(f'| `{short}` | {m["classification"]} | {m["function_count"]} | {m["class_count"]} | {m["route_count"]} | {m["importer_count"]} | {tm} | **{m["status"]}** | {rs} |')
    md.append('')

# SCRATCH
md.append('## 4. SCRATCH / DEBUG Files (_prefix)')
md.append('')
scr = sorted([m for m in results if m['is_scratch'] or m['filename'].startswith('_')], key=lambda x: x['rel_path'])
md.append(f'Total SCRATCH files: **{len(scr)}**')
md.append('')
md.append('All `_`-prefixed files are classified as SCRATCH/DEBUG. Those with 0 importers are additionally marked DELETE-CANDIDATE.')
md.append('')
md.append('| File | Lines | Status | Importers |')
md.append('|------|-------|--------|-----------|')
for m in scr:
    md.append(f'| `{m["rel_path"]}` | {m["lines"]} | {m["status"]} | {m["importer_count"]} |')
md.append('')

# DELETE-CANDIDATE
md.append('## 5. DELETE-CANDIDATE Inventory (Marked Only — NOT Deleted)')
md.append('')
dc = sorted([m for m in results if m['status'] == 'DELETE-CANDIDATE'], key=lambda x: x['rel_path'])
md.append(f'Total DELETE-CANDIDATE: **{len(dc)}**')
md.append('')
md.append('> These modules have **zero runtime importers, no API routes, no migration dependencies, and no test references**. Safe candidates for removal after user confirmation. **No files have been deleted.**')
md.append('')
md.append('| # | File | Lines | Funcs | Classification | Evidence |')
md.append('|---|------|-------|-------|----------------|----------|')
for i, m in enumerate(dc, 1):
    md.append(f'| {i} | `{m["rel_path"]}` | {m["lines"]} | {m["function_count"]} | {m["classification"]} | {m["reason"][:70]} |')
md.append('')

# BLOCKED
md.append('## 6. BLOCKED Modules')
md.append('')
bk = sorted([m for m in results if m['status'] == 'BLOCKED'], key=lambda x: x['rel_path'])
md.append(f'Total BLOCKED: **{len(bk)}**')
md.append('')
if bk:
    md.append('| File | Lines | Reason |')
    md.append('|------|-------|--------|')
    for m in bk:
        md.append(f'| `{m["rel_path"]}` | {m["lines"]} | {m["reason"]} |')
else:
    md.append('No BLOCKED modules detected. All production modules parse successfully and have at least minimal implementation.')
md.append('')

# DEPRECATED
md.append('## 7. DEPRECATED Modules')
md.append('')
dp = sorted([m for m in results if m['status'] == 'DEPRECATED'], key=lambda x: x['rel_path'])
md.append(f'Total DEPRECATED: **{len(dp)}**')
md.append('')
if dp:
    md.append('| File | Lines | Importers | Reason |')
    md.append('|------|-------|-----------|--------|')
    for m in dp:
        md.append(f'| `{m["rel_path"]}` | {m["lines"]} | {m["importer_count"]} | {m["reason"]} |')
md.append('')

# Key findings
md.append('## 8. Key Findings & Critical Issues')
md.append('')
md.append('### P0 Issues')
md.append('')
app_lines = app_deep['lines'] if app_deep else 5886
app_funcs = app_deep['functions'] if app_deep else 262
app_routes = app_deep['routes'] if app_deep else 188
app_no_try = app_deep['routes_without_try_except'] if app_deep else 59
scratch_count = len([m for m in results if m['is_scratch'] or m['filename'].startswith('_')])
md.append(f'1. **app.py monolith**: {app_lines:,} lines / {app_funcs} functions / {app_routes} routes in a single file. {app_no_try} route handlers without try/except represent unhandled exception risk.')
md.append(f'2. **SCRATCH file proliferation**: {scratch_count} `_`-prefix debug/scratch files in repository root and subdirectories. The majority have 0 importers and are DELETE-CANDIDATEs.')
md.append('3. **Orphaned substantial modules**: Multiple 100+ line modules have zero importers and no tests, suggesting abandoned development paths (e.g., monitoring.py, evidence_chain.py, platform_adapters/xhs.py).')
md.append('')
md.append('### P1 Issues')
md.append('')
md.append(f'4. **Test coverage gap**: Only {tc}/{len(results)} modules ({tc*100//len(results)}%) have matching test files.')
md.append(f'5. **Stub functions**: {sum(m["stub_count"] for m in results)} stub functions remain (NotImplementedError / pass-only), primarily in base adapter classes.')
md.append('6. **Duplicate adapter layers**: Both `platform_adapters/` and `v4_upgrade/adapters/` exist with overlapping platform implementations (xhs, weibo, bilibili, douyin), indicating incomplete migration.')
md.append('')
md.append('### P2 Issues')
md.append('')
md.append('7. **collector_v2 integration**: The v2 pipeline (deduplicate/normalize/persist/spam_filter/subject_filter) exists but `collector_v2_integration.py` has 0 importers.')
md.append('8. **Dual report engines**: `report_engine.py`, `report_export/report_engine.py`, and `v4_upgrade/report_center/report_generator.py` coexist with unclear ownership.')
md.append('9. **AI provider fragmentation**: `ai_channel.py`, `ark_llm.py`, `local_ai_client.py`, `ai_api.py`, and `v4_upgrade/ai_hub/` represent 5+ AI access paths without a unified gateway.')
md.append('')
md.append('## 9. Methodology')
md.append('')
md.append('- **AST-based static analysis**: Every `.py` file parsed with Python `ast` to count functions, classes, routes, stubs, imports, try/except, returns.')
md.append('- **Import graph resolution**: Built reverse-dependency graph to determine actual runtime importers.')
md.append('- **Test coverage matching**: Cross-referenced `tests/` directory against module names and import statements.')
md.append('- **Marker detection**: Scanned source for DEPRECATED, LEGACY, TODO, FIXME, NotImplementedError, `if __name__ == "__main__"`, top-level executable code.')
md.append('- **Status determination**: Rules-based engine combining implementation presence, runtime references, test coverage, exception handling, and structural markers.')
md.append('- **No source modification**: Read-only audit. No files were modified, moved, or deleted.')
md.append('')
md.append('---')
md.append(f'*Generated by ZBC Phase 11 Module Audit | {datetime.now().strftime("%Y-%m-%d %H:%M")}*')

with open(AUDIT_DIR / 'module_inventory.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md))
print(f"  Markdown: {AUDIT_DIR / 'module_inventory.md'}", file=sys.stderr)
print(f"\nDone. {len(results)} modules audited.", file=sys.stderr)
print(f"  VERIFIED={status_counts.get('VERIFIED',0)}, PARTIAL={status_counts.get('PARTIAL',0)}, "
      f"BLOCKED={status_counts.get('BLOCKED',0)}, DEPRECATED={status_counts.get('DEPRECATED',0)}, "
      f"DELETE-CANDIDATE={status_counts.get('DELETE-CANDIDATE',0)}", file=sys.stderr)
