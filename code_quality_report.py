# -*- coding: utf-8 -*-
"""
ZBC Phase 16 - Code Quality Report Tool
代码质量扫描工具：dead code / duplicate code / unused import / hidden side effect / circular dependency / secret leak

用法：
    python code_quality_report.py            # 全量扫描，输出摘要
    python code_quality_report.py --json     # 输出 JSON 结构化报告
    python code_quality_report.py --full     # 输出完整明细

设计原则：
- 只读扫描，不修改任何源码
- 排除 tests/、.trae-cn/、archive/、99-ARCHIVE/、docs/、node_modules/、.venv/
- 对 _ 前缀 scratch 文件单独标记，不混入生产代码统计
- 可重复运行
"""
import ast
import os
import re
import sys
import json
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

REPO_ROOT = Path(__file__).resolve().parent

EXCLUDE_DIRS = {
    'tests', '.trae-cn', '.trae', 'archive', '99-ARCHIVE', 'docs',
    'node_modules', '.venv', '.git', '__pycache__', '.pytest_cache',
    '.github', '.vscode', '.skills-router', 'staging', 'backups',
    'data', 'logs', 'deliverables', '2026-08-30', '2026-09-01',
    '序境', '_pitch_dump', '_ref_frames', '_shots', '_u', '_video_frames',
    '00-GOVERNANCE', '02-ARCHITECTURE', '08-AUDIT',
}

PROD_SUBDIRS = {
    'platform_adapters', 'collector_v2', 'browser_runtime', 'collector_guard',
    'config', 'contracts', 'dependencies', 'deployment', 'docker',
    'edge-cdp-general', 'edge-cdp-newaccount', 'edge-cdp-profile',
    'edge-cdp-retinaut', 'evaluation', 'migrations', 'proxy_pool',
    'report_export', 'scripts', 'static', 'templates', 'v4_upgrade',
    'account_keepalive', 'ad_intelligence', 'podcast', 'ref_gpt_v2',
    'alembic',
}


def is_production_file(filepath):
    if filepath.suffix != '.py':
        return False
    rel = filepath.relative_to(REPO_ROOT)
    parts = rel.parts
    for part in parts:
        if part in EXCLUDE_DIRS:
            return False
    if len(parts) > 1 and parts[0] not in PROD_SUBDIRS:
        return False
    return True


def is_scratch_file(filepath):
    name = filepath.name
    patterns = [
        r'^_', r'_debug_', r'_tmp_', r'_shardC_', r'_t7_',
        r'_verify_', r'_parse_', r'_douyin_', r'_open_login',
        r'_db_audit', r'_db_inspect', r'_split_report', r'_audit_',
    ]
    return any(re.search(p, name) for p in patterns)


def collect_python_files():
    prod_files = []
    scratch_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in files:
            if not f.endswith('.py'):
                continue
            fp = Path(root) / f
            if is_scratch_file(fp):
                scratch_files.append(fp)
            elif is_production_file(fp):
                prod_files.append(fp)
    return sorted(prod_files), sorted(scratch_files)


def safe_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return ast.parse(f.read(), filename=str(filepath))
    except Exception:
        return None


def get_module_name(filepath):
    rel = filepath.relative_to(REPO_ROOT)
    parts = list(rel.parts)
    if parts[-1] == '__init__.py':
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return '.'.join(parts)


def scan_unused_imports(files):
    results = []
    for fp in files:
        tree = safe_parse(fp)
        if tree is None:
            continue
        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    imported[name] = (node.lineno, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module == '__future__':
                    continue
                for alias in node.names:
                    if alias.name == '*':
                        continue
                    name = alias.asname or alias.name
                    imported[name] = (node.lineno, '%s.%s' % (node.module, alias.name))
        if not imported:
            continue
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                base = node
                while isinstance(base, ast.Attribute):
                    base = base.value
                if isinstance(base, ast.Name):
                    used_names.add(base.id)
        source_text = ''
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                source_text = f.read()
        except Exception:
            pass
        unused = []
        for name, (lineno, origin) in imported.items():
            if name in used_names:
                continue
            if ("'%s'" % name) in source_text or ('"%s"' % name) in source_text:
                continue
            unused.append({'name': name, 'line': lineno, 'origin': origin})
        if unused:
            results.append({'file': str(fp.relative_to(REPO_ROOT)), 'unused_count': len(unused), 'items': unused})
    return results


def scan_dead_code(files):
    module_exports = defaultdict(dict)
    file_modules = {}
    for fp in files:
        tree = safe_parse(fp)
        if tree is None:
            continue
        mod_name = get_module_name(fp)
        file_modules[fp] = mod_name
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    module_exports[mod_name][node.name] = node.lineno
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    module_exports[mod_name][node.name] = node.lineno
    imported_names = set()
    imported_modules = set()
    for fp in files:
        tree = safe_parse(fp)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)
                    for alias in node.names:
                        if alias.name != '*':
                            imported_names.add((node.module, alias.name))
    dead = []
    for mod_name, exports in module_exports.items():
        for name, lineno in exports.items():
            if (mod_name, name) in imported_names:
                continue
            if mod_name in imported_modules:
                found = False
                for fp in files:
                    try:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            if ('%s.%s' % (mod_name, name)) in f.read():
                                found = True
                                break
                    except Exception:
                        pass
                if found:
                    continue
            found_in_str = False
            for fp in files:
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    if ("'%s'" % name) in text or ('"%s"' % name) in text:
                        found_in_str = True
                        break
                except Exception:
                    pass
            if found_in_str:
                continue
            fp = None
            for f, m in file_modules.items():
                if m == mod_name:
                    fp = f
                    break
            if fp:
                dead.append({'file': str(fp.relative_to(REPO_ROOT)), 'module': mod_name, 'name': name, 'line': lineno})
    return dead


def scan_duplicate_code(files, min_lines=8):
    func_hashes = defaultdict(list)
    for fp in files:
        tree = safe_parse(fp)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body_lines = []
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        continue
                    try:
                        line = ast.dump(stmt, annotate_fields=False)
                        line = re.sub(r"value='[^']*'", "value=''", line)
                        line = re.sub(r'value="[^"]*"', 'value=""', line)
                        body_lines.append(line)
                    except Exception:
                        pass
                if len(body_lines) < min_lines:
                    continue
                h = hashlib.md5('\n'.join(body_lines).encode()).hexdigest()
                func_hashes[h].append({'file': str(fp.relative_to(REPO_ROOT)), 'function': node.name, 'line': node.lineno, 'body_lines': len(body_lines)})
    duplicates = []
    for h, occ in func_hashes.items():
        if len(occ) > 1:
            duplicates.append({'hash': h[:8], 'count': len(occ), 'occurrences': occ})
    return sorted(duplicates, key=lambda x: -x['count'])


def scan_hidden_side_effects(files):
    DANGEROUS = {
        'requests.get', 'requests.post', 'urllib.request.urlopen', 'urlopen',
        'sqlite3.connect', 'subprocess.run', 'subprocess.Popen', 'os.system',
        'exec', 'eval', 'print', 'logging.info', 'logging.debug', 'logging.warning',
        'logging.error', 'logger.info', 'logger.debug', 'logger.warning', 'logger.error',
        'load_dotenv',
    }
    results = []
    for fp in files:
        tree = safe_parse(fp)
        if tree is None:
            continue
        issues = []
        for node in tree.body:
            if isinstance(node, ast.If):
                try:
                    test = node.test
                    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == '__name__':
                        continue
                except Exception:
                    pass
                issues.append({'line': node.lineno, 'type': 'module_level_if', 'description': 'module-level if'})
                continue
            if isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    call_name = _get_call_name(node.value)
                    if call_name in DANGEROUS:
                        issues.append({'line': node.lineno, 'type': 'dangerous_module_call', 'call': call_name})
                    elif call_name:
                        issues.append({'line': node.lineno, 'type': 'module_call', 'call': call_name})
                continue
            if isinstance(node, (ast.For, ast.While, ast.Try, ast.With)):
                issues.append({'line': node.lineno, 'type': 'module_level_%s' % type(node).__name__.lower()})
                continue
        if issues:
            results.append({'file': str(fp.relative_to(REPO_ROOT)), 'issue_count': len(issues), 'items': issues})
    return results


def _get_call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        cur = node.func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return '.'.join(reversed(parts))
    return ''


def scan_circular_dependencies(files):
    graph = defaultdict(set)
    for fp in files:
        mod_name = get_module_name(fp)
        tree = safe_parse(fp)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    graph[mod_name].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    graph[mod_name].add(node.module)
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    def dfs(n):
        visited.add(n)
        rec_stack.add(n)
        path.append(n)
        for nb in graph.get(n, set()):
            if nb not in visited:
                dfs(nb)
            elif nb in rec_stack:
                cs = path.index(nb)
                cycle = path[cs:] + [nb]
                ck = tuple(sorted(set(cycle)))
                if not any(tuple(sorted(set(c))) == ck for c in cycles):
                    cycles.append(cycle)
        path.pop()
        rec_stack.discard(n)
    for m in graph:
        if m not in visited:
            dfs(m)
    return cycles


SECRET_PATTERNS = [
    (r'sk-[A-Za-z0-9]{20,}', 'OpenAI-style API Key'),
    (r'ark-[0-9a-f]{8,}-[0-9a-f]{4,}', 'Volcano ARK Key'),
    (r'[0-9a-f]{32}\.[0-9a-zA-Z]{20,}', 'Zhipu GLM Key'),
    (r'(?:api_key|apikey|secret|token|password)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']', 'Hardcoded credential'),
    (r'auth_token[0-9a-f]{30,}', 'Twitter auth_token'),
    (r'ct0[0-9a-f]{30,}', 'Twitter ct0 token'),
    (r'PC_TOKEN["\']?\s*[:=]\s*["\'][A-Za-z0-9]{8,}', 'Weibo PC_TOKEN'),
    (r'SESSDATA["\']?\s*[:=]\s*["\'][A-Za-z0-9%]{20,}', 'Bilibili SESSDATA'),
    (r'access-token-creator\.xiaohongshu\.com=[A-Za-z0-9]+', 'XHS access token'),
    (r'-----BEGIN.*PRIVATE KEY-----', 'Private Key'),
]


def scan_secrets(files, scratch_files):
    results = []
    for fp in files + scratch_files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue
        for pattern, desc in SECRET_PATTERNS:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                line_no = content[:m.start()].count('\n') + 1
                line = content.split('\n')[line_no - 1] if line_no > 0 else ''
                if any(x in line.lower() for x in ['your_', 'please_fill', 'example', 'placeholder', 'test-key', 'xxx', 'redacted']):
                    continue
                if 'SECRET_PATTERNS' in content and 'pattern' in line:
                    continue
                results.append({'file': str(fp.relative_to(REPO_ROOT)), 'line': line_no, 'type': desc, 'match': m.group()[:60], 'is_scratch': is_scratch_file(fp)})
    return results


def scan_hardcoded_paths(files):
    results = []
    pats = [r'C:\\Users\\\w+', r'/home/\w+', r'/Users/\w+']
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    for p in pats:
                        if re.search(p, line):
                            results.append({'file': str(fp.relative_to(REPO_ROOT)), 'line': i, 'match': line.strip()[:100]})
                            break
        except Exception:
            pass
    return results


def scan_hardcoded_ports(files):
    KNOWN = {'8200', '8201', '9222', '9223', '11434', '1234', '8080', '10808', '10809', '465', '587', '25', '80', '443'}
    results = []
    pat = re.compile(r'[:/](\d{4,5})\b')
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if line.strip().startswith('#'):
                        continue
                    for m in pat.finditer(line):
                        if m.group(1) not in KNOWN:
                            results.append({'file': str(fp.relative_to(REPO_ROOT)), 'line': i, 'port': m.group(1), 'context': line.strip()[:80]})
        except Exception:
            pass
    return results


def scan_scratch_files(scratch_files):
    return [{'file': str(fp.relative_to(REPO_ROOT)), 'size_bytes': fp.stat().st_size if fp.exists() else 0, 'classification': 'DELETE-CANDIDATE'} for fp in scratch_files]


def check_config_completeness():
    env_keys = set()
    env_example_keys = set()
    for fname, target in [('.env', env_keys), ('.env.example', env_example_keys)]:
        p = REPO_ROOT / fname
        if p.exists():
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        target.add(line.split('=', 1)[0].strip())
    config_known = set()
    cp = REPO_ROOT / 'config.py'
    if cp.exists():
        tree = safe_parse(cp)
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == 'get_known_keys':
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.isupper() and '_' in sub.value:
                            config_known.add(sub.value)
    return {
        'env_keys': sorted(env_keys), 'env_example_keys': sorted(env_example_keys),
        'config_known_keys': sorted(config_known),
        'in_env_not_example': sorted(env_keys - env_example_keys),
        'in_example_not_env': sorted(env_example_keys - env_keys),
        'in_env_not_config_known': sorted(env_keys - config_known),
        'in_config_known_not_env': sorted(config_known - env_keys),
    }


def run_full_scan():
    print('[1/9] Collecting files...', file=sys.stderr)
    prod, scratch = collect_python_files()
    print('  prod=%d scratch=%d' % (len(prod), len(scratch)), file=sys.stderr)
    print('[2/9] Unused imports...', file=sys.stderr)
    ui = scan_unused_imports(prod)
    print('[3/9] Dead code...', file=sys.stderr)
    dc = scan_dead_code(prod)
    print('[4/9] Duplicate code...', file=sys.stderr)
    dup = scan_duplicate_code(prod)
    print('[5/9] Hidden side effects...', file=sys.stderr)
    se = scan_hidden_side_effects(prod)
    print('[6/9] Circular deps...', file=sys.stderr)
    cd = scan_circular_dependencies(prod)
    print('[7/9] Secrets...', file=sys.stderr)
    sec = scan_secrets(prod, scratch)
    print('[8/9] Hardcoded paths/ports...', file=sys.stderr)
    hp = scan_hardcoded_paths(prod)
    hport = scan_hardcoded_ports(prod)
    print('[9/9] Config completeness...', file=sys.stderr)
    cc = check_config_completeness()
    sl = scan_scratch_files(scratch)
    return {
        'summary': {
            'prod_file_count': len(prod), 'scratch_file_count': len(scratch),
            'unused_import_files': len(ui), 'unused_import_total': sum(u['unused_count'] for u in ui),
            'dead_code_count': len(dc), 'duplicate_groups': len(dup),
            'duplicate_total_functions': sum(d['count'] for d in dup),
            'side_effect_files': len(se), 'side_effect_total': sum(s['issue_count'] for s in se),
            'circular_dependency_count': len(cd), 'secret_findings': len(sec),
            'secret_prod': sum(1 for s in sec if not s['is_scratch']),
            'secret_scratch': sum(1 for s in sec if s['is_scratch']),
            'hardcoded_paths': len(hp), 'hardcoded_ports': len(hport), 'scratch_files': len(sl),
        },
        'unused_imports': ui, 'dead_code': dc, 'duplicate_code': dup,
        'hidden_side_effects': se, 'circular_dependencies': cd,
        'secrets': sec, 'hardcoded_paths': hp, 'hardcoded_ports': hport,
        'scratch_files': sl, 'config_check': cc,
    }


def print_summary(r):
    s = r['summary']
    print('\n' + '=' * 60)
    print('ZBC Phase 16 - Code Quality Report')
    print('=' * 60)
    print('Production files:     %d' % s['prod_file_count'])
    print('Scratch files:        %d' % s['scratch_file_count'])
    print('-' * 60)
    print('Unused imports:       %d (%d files)' % (s['unused_import_total'], s['unused_import_files']))
    print('Dead code:            %d funcs/classes' % s['dead_code_count'])
    print('Duplicate code:       %d groups (%d funcs)' % (s['duplicate_groups'], s['duplicate_total_functions']))
    print('Hidden side effects:  %d (%d files)' % (s['side_effect_total'], s['side_effect_files']))
    print('Circular deps:        %d' % s['circular_dependency_count'])
    print('Secret findings:      %d (prod=%d scratch=%d)' % (s['secret_findings'], s['secret_prod'], s['secret_scratch']))
    print('Hardcoded paths:      %d' % s['hardcoded_paths'])
    print('Hardcoded ports:      %d' % s['hardcoded_ports'])
    print('=' * 60)


if __name__ == '__main__':
    report = run_full_scan()
    if '--json' in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    elif '--full' in sys.argv:
        print_summary(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print_summary(report)
        out = REPO_ROOT / 'audit' / 'code_quality_scan.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print('\nFull report saved: %s' % out)
