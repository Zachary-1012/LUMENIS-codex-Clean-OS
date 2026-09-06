# -*- coding: utf-8 -*-
"""
ZBC Phase 16 - Code Quality Regression Tests
代码质量回归测试：Secret泄漏 / 硬编码路径 / 配置完整性 / scratch文件不被生产代码import / 无merge conflict

运行方式：
    .venv/Scripts/python.exe -m pytest tests/test_code_quality.py -v
"""
import os
import re
import ast
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 排除目录（非生产代码）
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


def _is_production_file(fp):
    if fp.suffix != '.py':
        return False
    rel = fp.relative_to(REPO_ROOT)
    parts = rel.parts
    for part in parts:
        if part in EXCLUDE_DIRS:
            return False
    if len(parts) > 1 and parts[0] not in PROD_SUBDIRS:
        return False
    return True


def _collect_prod_files():
    files = []
    for root, dirs, fnames in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in fnames:
            if f.endswith('.py'):
                fp = Path(root) / f
                if _is_production_file(fp):
                    files.append(fp)
    return files


def _collect_all_py_files():
    files = []
    for root, dirs, fnames in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in fnames:
            if f.endswith('.py'):
                files.append(Path(root) / f)
    return files


# ============================================================
# Test 1: No Secret Leakage in Source Code
# ============================================================
SECRET_PATTERNS = [
    (re.compile(r'sk-[A-Za-z0-9]{20,}', re.IGNORECASE), 'OpenAI-style API Key'),
    (re.compile(r'ark-[0-9a-f]{8,}-[0-9a-f]{4,}', re.IGNORECASE), 'Volcano ARK Key'),
    (re.compile(r'[0-9a-f]{32}\.[0-9a-zA-Z]{20,}'), 'Zhipu GLM Key'),
    (re.compile(r'auth_token[0-9a-f]{30,}', re.IGNORECASE), 'Twitter auth_token'),
    (re.compile(r'ct0[0-9a-f]{30,}', re.IGNORECASE), 'Twitter ct0 token'),
    (re.compile(r'PC_TOKEN["\']?\s*[:=]\s*["\'][A-Za-z0-9]{8,}', re.IGNORECASE), 'Weibo PC_TOKEN'),
    (re.compile(r'SESSDATA["\']?\s*[:=]\s*["\'][A-Za-z0-9%]{20,}', re.IGNORECASE), 'Bilibili SESSDATA'),
    (re.compile(r'access-token-creator\.xiaohongshu\.com=[A-Za-z0-9]+'), 'XHS access token'),
    (re.compile(r'-----BEGIN.*PRIVATE KEY-----'), 'Private Key'),
]

# 允许的误报模式（测试数据、安全扫描器自身的正则等）
FALSE_POSITIVE_MARKERS = [
    'your_', 'please_fill', 'example', 'placeholder', 'test-key',
    'xxx', 'redacted', 'REDACTED', 'sk-1234567890', 'sk-abc',
    'SECRET_PATTERNS', 'security_scanner', 'security_boundary',
    'data_boundary', 'code_quality_report', 'agent_security',
    'BEGIN.*PRIVATE', 'pattern', 'regex', 're.compile',
    'filter_output', 'sanitize_input', 'is_instruction_attempt',
]

# 定义安全模式/扫描规则的文件（自身包含 pattern 字符串，跳过）
PATTERN_DEFINER_FILES = {
    'code_quality_report.py', 'security_scanner.py', 'security_boundary.py',
    'data_boundary.py', 'agent_security.py',
}


class TestNoSecretLeakage:
    """源码中不得包含真实 Secret/token/cookie"""

    def test_no_real_secrets_in_production(self):
        """生产代码中无真实 Secret"""
        violations = []
        for fp in _collect_prod_files():
            if fp.name in PATTERN_DEFINER_FILES:
                continue
            try:
                content = fp.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                continue
            for pattern, desc in SECRET_PATTERNS:
                for m in pattern.finditer(content):
                    line_no = content[:m.start()].count('\n') + 1
                    line = content.split('\n')[line_no - 1] if line_no > 0 else ''
                    if any(marker.lower() in line.lower() for marker in FALSE_POSITIVE_MARKERS):
                        continue
                    violations.append('%s:%d [%s] %s' % (fp.relative_to(REPO_ROOT), line_no, desc, m.group()[:50]))
        assert not violations, '生产代码中发现 Secret 泄漏:\n' + '\n'.join(violations[:20])

    def test_no_real_secrets_in_scratch(self):
        """Scratch 文件中无真实 Secret（已脱敏）"""
        violations = []
        for fp in _collect_all_py_files():
            if _is_production_file(fp):
                continue
            if fp.name in PATTERN_DEFINER_FILES:
                continue
            try:
                content = fp.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                continue
            for pattern, desc in SECRET_PATTERNS:
                for m in pattern.finditer(content):
                    line_no = content[:m.start()].count('\n') + 1
                    line = content.split('\n')[line_no - 1] if line_no > 0 else ''
                    if any(marker.lower() in line.lower() for marker in FALSE_POSITIVE_MARKERS):
                        continue
                    violations.append('%s:%d [%s]' % (fp.relative_to(REPO_ROOT), line_no, desc))
        assert not violations, 'Scratch 文件中发现未脱敏 Secret:\n' + '\n'.join(violations[:20])


# ============================================================
# Test 2: No Hardcoded Personal Paths
# ============================================================
class TestNoHardcodedPaths:
    """生产代码中不得硬编码个人用户路径"""

    def test_no_windows_user_path(self):
        """无 C:\\Users\\<username> 硬编码路径"""
        pattern = re.compile(r'C:\\Users\\\w+', re.IGNORECASE)
        violations = []
        for fp in _collect_prod_files():
            try:
                content = fp.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                continue
            for m in pattern.finditer(content):
                line_no = content[:m.start()].count('\n') + 1
                violations.append('%s:%d' % (fp.relative_to(REPO_ROOT), line_no))
        assert not violations, '生产代码中发现硬编码用户路径:\n' + '\n'.join(violations[:20])

    def test_no_unix_home_path(self):
        """无 /home/<user> 或 /Users/<user> 硬编码路径"""
        pattern = re.compile(r'/(?:home|Users)/\w+')
        violations = []
        for fp in _collect_prod_files():
            try:
                content = fp.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                continue
            for m in pattern.finditer(content):
                line_no = content[:m.start()].count('\n') + 1
                line = content.split('\n')[line_no - 1]
                # 排除 os.path.expanduser 等动态用法
                if 'expanduser' in line:
                    continue
                violations.append('%s:%d' % (fp.relative_to(REPO_ROOT), line_no))
        assert not violations, '生产代码中发现硬编码用户路径:\n' + '\n'.join(violations[:20])


# ============================================================
# Test 3: Config Completeness
# ============================================================
class TestConfigCompleteness:
    """.env.example 应覆盖 .env 中所有 key；config.py known_keys 应覆盖主要配置"""

    def _parse_env_keys(self, filename):
        keys = set()
        fp = REPO_ROOT / filename
        if not fp.exists():
            return keys
        for line in fp.read_text(encoding='utf-8-sig', errors='ignore').split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                keys.add(line.split('=', 1)[0].strip())
        return keys

    def test_env_example_covers_env(self):
        """.env 中的所有 key 都应在 .env.example 中有对应项"""
        env_keys = self._parse_env_keys('.env')
        example_keys = self._parse_env_keys('.env.example')
        missing = env_keys - example_keys
        # 允许少数例外（如本地特定的覆盖）
        assert not missing, '.env 中以下 key 未在 .env.example 中定义: %s' % sorted(missing)

    def test_config_known_keys_not_empty(self):
        """config.py get_known_keys() 应返回非空列表且覆盖核心配置"""
        config_fp = REPO_ROOT / 'config.py'
        assert config_fp.exists(), 'config.py 不存在'
        tree = ast.parse(config_fp.read_text(encoding='utf-8-sig'))
        known_keys = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'get_known_keys':
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        if sub.value.isupper() and '_' in sub.value:
                            known_keys.add(sub.value)
        assert len(known_keys) >= 30, 'config.py known_keys 数量过少: %d' % len(known_keys)
        # 核心配置必须存在
        for core_key in ['DATABASE_PATH', 'AI_PROVIDER', 'ZHIPU_API_KEY']:
            assert core_key in known_keys, 'config.py known_keys 缺少核心配置: %s' % core_key


# ============================================================
# Test 4: Scratch Files Not Imported by Production Code
# ============================================================
class TestScratchIsolation:
    """Scratch/debug 文件不得被生产代码 import"""

    SCRATCH_PATTERNS = [
        r'^_', r'_debug_', r'_tmp_', r'_shardC_', r'_t7_',
        r'_verify_', r'_parse_', r'_douyin_', r'_open_login',
        r'_db_audit', r'_db_inspect', r'_split_report', r'_audit_',
    ]

    def _is_scratch(self, name):
        return any(re.search(p, name) for p in self.SCRATCH_PATTERNS)

    def test_no_production_imports_scratch(self):
        """生产代码中不得 import scratch 文件"""
        violations = []
        scratch_names = set()
        # 收集所有 scratch 模块名
        for fp in _collect_all_py_files():
            if self._is_scratch(fp.stem):
                scratch_names.add(fp.stem)
        # 检查生产代码中的 import
        for fp in _collect_prod_files():
            try:
                tree = ast.parse(fp.read_text(encoding='utf-8-sig', errors='ignore'))
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod_name = alias.name.split('.')[-1]
                        if mod_name in scratch_names:
                            violations.append('%s imports %s' % (fp.relative_to(REPO_ROOT), alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod_name = node.module.split('.')[-1]
                        if mod_name in scratch_names:
                            violations.append('%s imports %s' % (fp.relative_to(REPO_ROOT), node.module))
        assert not violations, '生产代码 import 了 scratch 文件:\n' + '\n'.join(violations[:20])


# ============================================================
# Test 5: No Unresolved Merge Conflicts
# ============================================================
class TestNoMergeConflicts:
    """所有 Python 文件不得包含未解决的 merge conflict markers"""

    def test_no_conflict_markers(self):
        """无 <<<<<<< / ======= / >>>>>>> conflict markers"""
        violations = []
        for fp in _collect_all_py_files():
            try:
                content = fp.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                continue
            for i, line in enumerate(content.split('\n'), 1):
                if line.startswith('<<<<<<< ') or line.startswith('>>>>>>> '):
                    violations.append('%s:%d' % (fp.relative_to(REPO_ROOT), i))
        assert not violations, '发现未解决的 merge conflict:\n' + '\n'.join(violations[:20])

    def test_all_production_files_parse(self):
        """所有生产 Python 文件应能成功 AST parse"""
        failures = []
        for fp in _collect_prod_files():
            try:
                ast.parse(fp.read_text(encoding='utf-8-sig', errors='ignore'))
            except SyntaxError as e:
                failures.append('%s: %s' % (fp.relative_to(REPO_ROOT), e))
        assert not failures, '以下生产文件语法错误:\n' + '\n'.join(failures[:20])


# ============================================================
# Test 6: No API Keys in Source (broader check)
# ============================================================
class TestNoApiKeysInSource:
    """源码中不得有 api_key = '真实值' 形式的硬编码"""

    def test_no_hardcoded_api_key_assignment(self):
        """无 api_key/secret/token = '长字符串' 形式的硬编码赋值"""
        pattern = re.compile(
            r'(?:api_key|apikey|api-key|secret|token|password|passwd)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']',
            re.IGNORECASE
        )
        violations = []
        for fp in _collect_prod_files():
            try:
                content = fp.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                continue
            for m in pattern.finditer(content):
                line_no = content[:m.start()].count('\n') + 1
                line = content.split('\n')[line_no - 1]
                if any(marker.lower() in line.lower() for marker in FALSE_POSITIVE_MARKERS):
                    continue
                violations.append('%s:%d' % (fp.relative_to(REPO_ROOT), line_no))
        assert not violations, '生产代码中发现硬编码凭证赋值:\n' + '\n'.join(violations[:20])
