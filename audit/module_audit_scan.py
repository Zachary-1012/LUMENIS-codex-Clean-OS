# -*- coding: utf-8 -*-
"""
ZBC Phase 11 - Module Function-Level Audit Scanner
Pure read-only AST analysis. No source modification.
"""
import ast
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(r"D:\Taikoo-monitor-new")
EXCLUDE_DIRS = {
    'tests', '.venv', 'node_modules', '__pycache__', '.trae-cn', '99-ARCHIVE',
    '.git', '.idea', '.vscode', '.pytest_cache', '.skills-router', '.trae',
    'archive', 'backups', 'logs', 'staging', 'deliverables',
    '2026-08-30', '2026-09-01', '_pitch_dump', '_ref_frames', '_shots',
    '_u', '_video_frames', '序境',
}

# ── Classification rules ──────────────────────────────────────────
def classify(rel_path: str, filename: str) -> str:
    p = rel_path.lower().replace('\\', '/')
    name = filename.lower()

    # SCRATCH / DEBUG: underscore prefix
    if filename.startswith('_'):
        return 'SCRATCH'

    # Collector
    if any(k in p for k in ['collector_v2/', 'collector_guard/', 'platform_adapters/']):
        return 'COLLECTOR'
    if re.match(r'^(collector|xhs_|xhs\.)', name) or name in ('collector.py',):
        return 'COLLECTOR'
    if name.startswith('collector') or name.startswith('xhs_'):
        return 'COLLECTOR'

    # Risk / Public Opinion
    if name in ('risk_engine.py', 'alert_engine.py', 'event_graph.py',
                'public_opinion_cases.py') or name.startswith('pr_case_'):
        return 'RISK'

    # AI
    if name.startswith('ai_') or name in ('ark_llm.py', 'local_ai_client.py', 'intelligence.py'):
        return 'AI'
    if 'ai_hub' in p or 'ad_intelligence' in p:
        return 'AI'

    # Evidence / Evaluation
    if name.startswith('evidence_') or name in ('canonical_metrics.py', 'data_quality_gate.py'):
        return 'EVIDENCE'
    if name.startswith('evaluation_') or 'evaluation/' in p:
        return 'EVIDENCE'

    # Report
    if name in ('daily_report.py', 'export_report.py', 'brand_report_generator.py'):
        return 'REPORT'
    if name.startswith('report_') or 'report_center' in p or 'report_export' in p:
        return 'REPORT'

    # UI / API
    if name == 'app.py' or name.endswith('_api.py') or name in ('ic_routes.py', 'kos_routes.py', 'podcast_routes.py'):
        return 'API'
    if name.endswith('_routes.py'):
        return 'API'

    # Operations
    if name in ('stability_monitor.py', 'auto_recovery.py', 'monitoring.py', 'monitor_pipeline.py'):
        return 'OPERATIONS'
    if name.startswith('system_') or name.startswith('runtime_'):
        return 'OPERATIONS'

    # Research / Knowledge
    if name in ('brand_knowledge_base.py', 'resource_library.py', 'context_intelligence.py',
                'collection_intelligence.py'):
        return 'RESEARCH'
    if name.startswith('learning_') or name.startswith('topic_'):
        return 'RESEARCH'

    # Data / DB
    if name in ('database.py', 'models.py', 'config.py', 'database_migrations.py', 'data_boundary.py'):
        return 'DATA'
    if name.startswith('data_') or 'data/' in p or 'migrations' in p or 'alembic' in p:
        return 'DATA'

    # Infrastructure
    if name in ('logger.py', 'cache_manager.py', 'permission_gate.py', 'security_boundary.py',
                'safety_boundary.py', 'compliance_gate.py', 'agent_security.py', 'function_registry.py',
                'schema_registry.py', 'repository_registry.py', 'settings_module.py', 'memory_optimizer.py'):
        return 'INFRASTRUCTURE'

    # Utility / scripts
    if 'scripts/' in p or 'tools/' in p:
        return 'UTILITY'

    # v4_upgrade
    if 'v4_upgrade/' in p:
        return 'INFRASTRUCTURE'

    # browser_runtime
    if 'browser_runtime/' in p or name.startswith('browser_'):
        return 'INFRASTRUCTURE'

    # proxy_pool
    if 'proxy_pool/' in p:
        return 'INFRASTRUCTURE'

    # podcast
    if 'podcast/' in p:
        return 'RESEARCH'

    # ad_intelligence
    if 'ad_intelligence/' in p:
        return 'AI'

    # account_keepalive
    if 'account_keepalive/' in p:
        return 'OPERATIONS'

    # contracts
    if 'contracts/' in p:
        return 'INFRASTRUCTURE'

    # deployment
    if 'deployment/' in p:
        return 'OPERATIONS'

    # docs reference scripts
    if 'docs/' in p:
        return 'UTILITY'

    # audit scripts
    if 'audit/' in p and name != 'module_audit_scan.py':
        return 'UTILITY'

    return 'CORE'


# ── AST Visitor ────────────────────────────────────────────────────
class ModuleAnalyzer(ast.NodeVisitor):
    def __init__(self, source: str, rel_path: str):
        self.source = source
        self.rel_path = rel_path
        self.functions = []       # list of dict
        self.classes = []
        self.imports = []
        self.has_try_except = False
        self.has_return = False
        self.db_ops = []
        self.api_routes = []
        self.stub_funcs = []
        self.todo_count = 0
        self.fixme_count = 0
        self.not_implemented_count = 0
        self.pass_only_funcs = []
        self._current_class = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_Try(self, node):
        self.has_try_except = True
        self.generic_visit(node)

    def visit_Return(self, node):
        self.has_return = True
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        prev = self._current_class
        self._current_class = node.name
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.classes.append({
            'name': node.name,
            'lineno': node.lineno,
            'method_count': len(methods),
            'bases': [self._name(b) for b in node.bases],
            'has_methods': len(methods) > 0,
            'is_stub': all(self._is_stub_body(m.body) for m in methods) if methods else self._is_stub_body(node.body),
        })
        self.generic_visit(node)
        self._current_class = prev

    def visit_FunctionDef(self, node):
        self._record_func(node, async_fn=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._record_func(node, async_fn=True)
        self.generic_visit(node)

    def _record_func(self, node, async_fn):
        params = [a.arg for a in node.args.args]
        is_stub = self._is_stub_body(node.body)
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
        has_try = any(isinstance(n, ast.Try) for n in ast.walk(node))
        decorators = [self._name(d) for d in node.decorator_list]

        # Detect route decorators
        route = None
        for d in node.decorator_list:
            dn = self._name(d)
            if 'route' in dn.lower() or 'get' == dn.lower() or 'post' == dn.lower() or 'put' == dn.lower() or 'delete' == dn.lower():
                if isinstance(d, ast.Call):
                    args = [self._literal(a) for a in d.args]
                    route = f"{dn}({', '.join(args)})"
                else:
                    route = dn

        func_info = {
            'name': node.name,
            'lineno': node.lineno,
            'class': self._current_class,
            'params': params,
            'is_async': async_fn,
            'is_stub': is_stub,
            'has_return': has_return,
            'has_try': has_try,
            'decorators': decorators,
            'route': route,
            'body_lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0,
        }
        self.functions.append(func_info)

        if is_stub:
            self.stub_funcs.append(f"{self._current_class + '.' if self._current_class else ''}{node.name}")
        if route:
            self.api_routes.append(route)

    def _is_stub_body(self, body):
        """Check if function body is effectively a stub: only pass, docstring, raise NotImplementedError, or TODO."""
        if not body:
            return True
        real_stmts = []
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue  # docstring
            if isinstance(stmt, ast.Pass):
                continue
            if isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    exc_name = self._name(stmt.exc.func)
                    if 'NotImplemented' in exc_name:
                        return True
                real_stmts.append(stmt)
                continue
            real_stmts.append(stmt)
        return len(real_stmts) == 0

    def _name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._name(node.func)
        if isinstance(node, ast.Constant):
            return str(node.value)
        return ast.dump(node)[:50]

    def _literal(self, node):
        if isinstance(node, ast.Constant):
            return repr(node.value)
        return self._name(node)


def analyze_file(filepath: Path, rel_path: str) -> dict:
    try:
        raw = filepath.read_bytes()
        # Strip BOM if present
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        source = raw.decode('utf-8', errors='replace')
    except Exception as e:
        return {'error': str(e), 'rel_path': rel_path}

    lines = source.count('\n') + 1
    filename = filepath.name

    # Count TODO/FIXME in comments
    todo_count = len(re.findall(r'#\s*TODO', source, re.IGNORECASE))
    fixme_count = len(re.findall(r'#\s*FIXME', source, re.IGNORECASE))
    not_impl_count = source.count('NotImplementedError')

    # DB operation hints
    db_patterns = []
    for pat in [r'\.execute\(', r'sqlite3', r'SQLAlchemy', r'create_engine', r'session\.', r'cursor\.', r'INSERT INTO', r'SELECT ', r'UPDATE ', r'DELETE FROM']:
        if re.search(pat, source, re.IGNORECASE):
            db_patterns.append(pat)

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        return {
            'rel_path': rel_path, 'filename': filename, 'lines': lines,
            'classification': classify(rel_path, filename),
            'parse_error': str(e),
            'functions': [], 'classes': [], 'imports': [],
            'todo_count': todo_count, 'fixme_count': fixme_count,
            'not_implemented_count': not_impl_count,
            'db_patterns': db_patterns,
        }

    analyzer = ModuleAnalyzer(source, rel_path)
    analyzer.visit(tree)
    analyzer.todo_count = todo_count
    analyzer.fixme_count = fixme_count
    analyzer.not_implemented_count = not_impl_count

    return {
        'rel_path': rel_path,
        'filename': filename,
        'lines': lines,
        'classification': classify(rel_path, filename),
        'function_count': len(analyzer.functions),
        'class_count': len(analyzer.classes),
        'functions': analyzer.functions,
        'classes': analyzer.classes,
        'imports': list(set(analyzer.imports)),
        'has_try_except': analyzer.has_try_except,
        'has_return': analyzer.has_return,
        'stub_functions': analyzer.stub_funcs,
        'stub_count': len(analyzer.stub_funcs),
        'api_routes': analyzer.api_routes,
        'route_count': len(analyzer.api_routes),
        'todo_count': todo_count,
        'fixme_count': fixme_count,
        'not_implemented_count': not_impl_count,
        'db_patterns': db_patterns,
        'is_scratch': filename.startswith('_'),
    }


def scan_repo():
    results = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Prune excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if not f.endswith('.py'):
                continue
            filepath = Path(root) / f
            rel = str(filepath.relative_to(REPO_ROOT))
            results.append(analyze_file(filepath, rel))
    return results


if __name__ == '__main__':
    print("Scanning repository...", file=sys.stderr)
    results = scan_repo()
    print(f"Scanned {len(results)} files", file=sys.stderr)

    # Write raw JSON
    out = REPO_ROOT / 'audit' / '_module_scan_raw.json'
    out.parent.mkdir(exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(f"Raw scan written to {out}", file=sys.stderr)

    # Summary
    by_class = defaultdict(int)
    for r in results:
        by_class[r.get('classification', 'UNKNOWN')] += 1
    print("\n=== Classification Summary ===", file=sys.stderr)
    for k, v in sorted(by_class.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}", file=sys.stderr)

    total_funcs = sum(r.get('function_count', 0) for r in results)
    total_stubs = sum(r.get('stub_count', 0) for r in results)
    total_routes = sum(r.get('route_count', 0) for r in results)
    print(f"\nTotal functions: {total_funcs}", file=sys.stderr)
    print(f"Total stub functions: {total_stubs}", file=sys.stderr)
    print(f"Total API routes: {total_routes}", file=sys.stderr)
    print(f"Files with parse errors: {sum(1 for r in results if r.get('parse_error'))}", file=sys.stderr)
