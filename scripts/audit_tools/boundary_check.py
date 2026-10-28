# -*- coding: utf-8 -*-
"""
ZBC/LUMENIS 双库边界机器检查器 (Boundary Check)

P1 复杂度治理 — 持续验证 ZBC 主库与 OSAI 外部库的边界隔离。

检查项：
  1. 禁止跨库直接导入生产逻辑：ZBC 代码中 `import osai_*` / `from osai_*`
  2. 禁止共享生产 DB：OSAI 代码直接连接 ZBC data/monitor.db
  3. OSAI 不得直接写序境生产真相：OSAI 模块直接写入 ZBC DB 表
  4. 序境不依赖 OSAI 启动：app 启动时不 import 任何 OSAI 模块
  5. 共享走 Contract/Artifact：跨库交互通过 contract 文件/artifact 交换
  6. Skill/Memory/Agent 不过 Permission Gate：agent/skill 执行绕过权限检查
  7. 未验证学习资产不回写生产：intelligence_library 中 PENDING/CONCEPT 被生产代码直接引用
  8. 异常时 DENY+AUDIT+可定位原因：输出 violation 列表（文件/行号/原因/严重度）

用法：
  python scripts/audit_tools/boundary_check.py
  python scripts/audit_tools/boundary_check.py --osai-path D:\\Zachary OS AI
  python scripts/audit_tools/boundary_check.py --json  # 机器可读输出
  python scripts/audit_tools/boundary_check.py --ci    # CI 模式（exit code = violation count, capped at 1）
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================
# 配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = None  # Source audit must never probe the production database implicitly.
OUTPUT_MD = PROJECT_ROOT / "audit" / "BOUNDARY_CHECK_REPORT.md"
OUTPUT_JSON = PROJECT_ROOT / "audit" / "BOUNDARY_CHECK_REPORT.json"

# 排除目录（非生产代码）
EXCLUDE_DIRS = {
    ".venv", "node_modules", "__pycache__", ".git",
    ".trae", ".trae-cn", ".opencode", ".ollama", ".skills-router",
    ".vscode", "_pitch_dump", "_ref_frames", "_shots", "_u",
    "99-ARCHIVE", "archive", "backups", "logs", "deliverables",
    "staging", "user_file", "_path_backup", "_scan_output",
    "audit", "docs", "00-GOVERNANCE", "02-ARCHITECTURE",
    "intelligence_library",  # 研究库单独检查
    "tests", "test",
}

# 生产代码目录（白名单优先）
PRODUCTION_DIRS = [
    "",  # root .py files
    "account", "account_keepalive", "ad_intelligence", "alembic",
    "browser_runtime", "collector_guard", "collector_v2", "config",
    "contracts", "core", "data", "deployment", "docker",
    "edge-cdp-general", "edge-cdp-newaccount", "edge-cdp-profile", "edge-cdp-retinaut",
    "evaluation", "migrations", "nodejs", "platform_adapters", "podcast",
    "proxy_pool", "ref_gpt_v2", "report_export", "scripts",
    "static", "templates", "tests", "tools", "lumenis", "序境",
]

# 严重度
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"


class Violation:
    """边界违规记录"""
    def __init__(self, check_id: str, file: str, lineno: int,
                 reason: str, severity: str, detail: str = ""):
        self.check_id = check_id
        self.file = file
        self.lineno = lineno
        self.reason = reason
        self.severity = severity
        self.detail = detail

    def to_dict(self) -> Dict:
        return {
            "check_id": self.check_id,
            "file": self.file,
            "lineno": self.lineno,
            "reason": self.reason,
            "severity": self.severity,
            "detail": self.detail,
        }


def is_production_file(rel_path: str) -> bool:
    """判断是否为生产代码文件（排除备份/扫描输出/文档等）"""
    normalized = rel_path.replace("\\", "/")
    if any(normalized.startswith(f"app/{platform}/flutter/ephemeral/")
           for platform in ("linux", "windows", "macos")):
        return False  # Flutter-generated dependency links, never owned source.
    parts = normalized.split("/")
    if parts[0] == "work" or rel_path == "scripts/audit_tools/boundary_check.py":
        return False
    for part in parts:
        if part in EXCLUDE_DIRS:
            return False
        if part.startswith("_") and part not in ("_patch_app.py",):
            # _开头的目录通常是临时/备份
            if part.endswith((".py",)):
                continue
            return False
    return True


def get_production_py_files() -> List[Path]:
    """获取所有生产 Python 文件"""
    files = []
    def failed(error):
        raise OSError("Included source traversal failed") from error
    for directory, dirs, names in os.walk(PROJECT_ROOT, onerror=failed, followlinks=False):
        rel_dir = Path(directory).relative_to(PROJECT_ROOT)
        selected = sorted(d for d in dirs if is_production_file((rel_dir / d / "entry.py").as_posix()))
        if any((Path(directory) / d).is_symlink() for d in selected):
            raise OSError("Included source directory is a symlink; review required")
        dirs[:] = selected
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            path = Path(directory) / name
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            if is_production_file(rel) and not rel.startswith("data/"):
                if path.is_symlink():
                    raise OSError("Symlink source requires explicit review: " + rel)
                # Included source parse/read failures are not silently skipped.
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=rel)
                files.append(path)
    return files


# ============================================================
# 检查 1: ZBC 直接 import OSAI
# ============================================================
def check_direct_osai_import(files: List[Path]) -> List[Violation]:
    """检查 ZBC 生产代码中是否直接 import osai_* 模块"""
    violations = []
    osai_pattern = re.compile(r'^\s*(import\s+osai\w*|from\s+osai\w*)', re.MULTILINE)

    for fpath in files:
        rel = str(fpath.relative_to(PROJECT_ROOT))
        try:
            source = fpath.read_text(encoding="utf-8-sig")
        except Exception as error:
            raise OSError("Source boundary input unavailable") from error

        # 用 AST 精确检测 import（排除字符串中的 subprocess 调用）
        try:
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError as error:
            raise ValueError("Source boundary syntax unavailable") from error

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("osai"):
                        # 测试/扫描脚本中的 import 降为 MEDIUM
                        is_test = "test" in rel.lower() or rel.startswith("_") or "/_tmp" in rel
                        sev = SEVERITY_MEDIUM if is_test else SEVERITY_CRITICAL
                        violations.append(Violation(
                            "B1-DIRECT-IMPORT", rel, node.lineno,
                            f"直接 import OSAI 模块: {alias.name}",
                            sev,
                            "ZBC 生产代码禁止直接 import OSAI 运行时，应通过 subprocess/contract 交互"
                        ))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("osai"):
                    is_test = "test" in rel.lower() or rel.startswith("_") or "/_tmp" in rel
                    sev = SEVERITY_MEDIUM if is_test else SEVERITY_CRITICAL
                    violations.append(Violation(
                        "B1-DIRECT-IMPORT", rel, node.lineno,
                        f"直接 from OSAI 导入: {node.module}",
                        sev,
                        "ZBC 生产代码禁止直接 from osai_* 导入，应通过 subprocess/contract 交互"
                    ))

    return violations


# ============================================================
# 检查 2: OSAI 直接连接 ZBC DB
# ============================================================
def check_osai_db_connection(osai_path: Optional[Path]) -> List[Violation]:
    """检查 OSAI 代码是否直接连接 ZBC 的 data/monitor.db"""
    violations = []
    if not osai_path or not osai_path.exists():
        violations.append(Violation(
            "B2-OSAI-DB", "N/A", 0,
            f"OSAI 路径不存在或未指定: {osai_path}",
            SEVERITY_INFO,
            "跳过 OSAI DB 连接检查（OSAI 库不在当前环境）"
        ))
        return violations

    db_patterns = [
        re.compile(r'monitor\.db'),
        re.compile(r'Taikoo[_\-]monitor'),
        re.compile(r'ZBC_DB_PATH'),
        re.compile(r'sqlite3\.connect.*monitor'),
    ]

    for py_file in osai_path.rglob("*.py"):
        if any(ex in str(py_file) for ex in ["__pycache__", ".git", ".venv"]):
            continue
        rel = str(py_file.relative_to(osai_path))
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception as error:
            raise OSError("Source boundary input unavailable") from error
        for i, line in enumerate(source.split("\n"), 1):
            for pat in db_patterns:
                if pat.search(line):
                    violations.append(Violation(
                        "B2-OSAI-DB", f"OSAI/{rel}", i,
                        f"OSAI 代码引用 ZBC DB: {line.strip()[:80]}",
                        SEVERITY_HIGH,
                        "OSAI 不得直接连接 ZBC 生产 DB，应通过 contract/artifact 交换数据"
                    ))
                    break

    return violations


# ============================================================
# 检查 3: OSAI 直接写 ZBC 生产表
# ============================================================
def check_osai_write_production(osai_path: Optional[Path],
                                 production_tables: Set[str]) -> List[Violation]:
    """检查 OSAI 模块是否直接写入 ZBC DB 生产表"""
    violations = []
    if not osai_path or not osai_path.exists():
        return violations

    write_patterns = [
        re.compile(r'INSERT\s+INTO\s+(\w+)', re.IGNORECASE),
        re.compile(r'UPDATE\s+(\w+)\s+SET', re.IGNORECASE),
        re.compile(r'DELETE\s+FROM\s+(\w+)', re.IGNORECASE),
        re.compile(r"execute\(['\"]\s*(INSERT|UPDATE|DELETE)", re.IGNORECASE),
    ]

    for py_file in osai_path.rglob("*.py"):
        if any(ex in str(py_file) for ex in ["__pycache__", ".git", ".venv"]):
            continue
        rel = str(py_file.relative_to(osai_path))
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception as error:
            raise OSError("Source boundary input unavailable") from error
        for i, line in enumerate(source.split("\n"), 1):
            for pat in write_patterns:
                m = pat.search(line)
                if m:
                    table_name = m.group(1) if m.lastindex and m.group(1).isalpha() else ""
                    if table_name and table_name.lower() in production_tables:
                        violations.append(Violation(
                            "B3-OSAI-WRITE", f"OSAI/{rel}", i,
                            f"OSAI 直接写 ZBC 生产表: {table_name}",
                            SEVERITY_CRITICAL,
                            "OSAI 不得直接写入 ZBC 生产表，必须走 contract/artifact"
                        ))
    return violations


# ============================================================
# 检查 4: app 启动不依赖 OSAI
# ============================================================
def check_app_startup_no_osai() -> List[Violation]:
    """验证 app.py 启动时不 import 任何 OSAI 模块"""
    violations = []
    app_path = PROJECT_ROOT / "app.py"
    if not app_path.exists():
        violations.append(Violation(
            "B4-STARTUP", "app.py", 0,
            "app.py 不存在",
            SEVERITY_HIGH,
            "无法验证启动依赖"
        ))
        return violations

    try:
        source = app_path.read_text(encoding="utf-8-sig", errors="replace")
        tree = ast.parse(source, filename="app.py")
    except Exception as e:
        violations.append(Violation(
            "B4-STARTUP", "app.py", 0,
            f"app.py 解析失败: {e}",
            SEVERITY_HIGH, ""
        ))
        return violations

    # 检查顶层 import
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("osai"):
                    violations.append(Violation(
                        "B4-STARTUP", "app.py", node.lineno,
                        f"app.py 顶层直接 import OSAI: {alias.name}",
                        SEVERITY_CRITICAL,
                        "app 启动不得依赖 OSAI 模块"
                    ))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("osai"):
                violations.append(Violation(
                    "B4-STARTUP", "app.py", node.lineno,
                    f"app.py 顶层 from OSAI 导入: {node.module}",
                    SEVERITY_CRITICAL,
                    "app 启动不得依赖 OSAI 模块"
                ))

    # 检查动态 import（importlib / __import__）
    dynamic_patterns = [
        re.compile(r'importlib\.import_module\(["\']osai'),
        re.compile(r'__import__\(["\']osai'),
    ]
    for i, line in enumerate(source.split("\n"), 1):
        for pat in dynamic_patterns:
            if pat.search(line):
                violations.append(Violation(
                    "B4-STARTUP", "app.py", i,
                    f"app.py 动态导入 OSAI: {line.strip()[:80]}",
                    SEVERITY_HIGH,
                    "app 启动不得动态导入 OSAI 模块"
                ))

    return violations


# ============================================================
# 检查 5: 跨库交互走 Contract/Artifact
# ============================================================
def check_contract_artifact_usage(files: List[Path]) -> List[Violation]:
    """检查跨库交互是否通过 contract 文件/artifact 交换（正向检查+违规提示）"""
    violations = []
    # AST only: comments, prose, test fixtures and this scanner are not calls.
    subprocess_osai = []
    for fpath in files:
        rel = fpath.relative_to(PROJECT_ROOT).as_posix()
        source = fpath.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            if called.startswith("subprocess.") and "osai" in ast.unparse(node).lower():
                subprocess_osai.append((rel, node.lineno, called))

    # 检查 contracts 目录是否存在
    contracts_dir = PROJECT_ROOT / "contracts"
    has_contracts = contracts_dir.exists() and any(contracts_dir.iterdir())

    if not has_contracts:
        violations.append(Violation(
            "B5-CONTRACT", "contracts/", 0,
            "contracts 目录为空或不存在",
            SEVERITY_MEDIUM,
            "跨库交互应通过 contract 文件定义接口"
        ))

    # Artifact existence is not proof of a safe exchange. Caller contracts and
    # actual permission/effect tests remain independent mandatory evidence.

    # 记录 subprocess 调用为 INFO（合规模式）
    for rel, lineno, line in subprocess_osai[:10]:
        violations.append(Violation(
            "B5-CONTRACT", rel, lineno,
            f"实际 subprocess 调用 OSAI: {line}",
            SEVERITY_INFO,
            "只确认调用存在；Permission、合同与实际可用性须独立核验，不据此宣布合规或可用"
        ))

    return violations


# Current PR146 source/dependency review identities after caller and denial-case
# verification. These pins are not grants or semantic proof; changed canonical
# LF source bytes require renewed review, and denial regressions remain required.
_REVIEWED_BOUNDARIES = {'account/skills.py': {'classification': 'OWNER_DELEGATE: execute_skill_api checks dual domain, '
                                         'task binding, then run_execution_chain; local path '
                                         'authorized_context and readback. ai_api caller reopens an '
                                         'exact execution ID only after current actor/Permission checks.',
                       'dependencies': {'account/authorization.py': 'b7111044741a5facdf3c8633f904336bb6c8276d3f1a2139f61b52ca836f8ee9',
                                        'agent_runtime/task_binding.py': '2c365ee3e41419d9404972fd3d7b70be46bee32cf963df1cf35443ffe546536e',
                                        'ai_api.py': '62d4e3f047131fb704cf74d98c2c07483b1b6ef5b3175041b8695bc37805efc6',
                                        'lumenis/shared/agents/skills/execution.py': '161f1a12e4976c6b93753c60c16303e7d73b2a2b2207d0c6a1b641c23f3a6235',
                                        'lumenis/system/security/permission.py': '4a1d011299aaf1527b9838b3bb25a60b9a70934c9b94a578a57b2f82b39e3079'},
                       'sha256': '0a93582c0a1e1d8807768b0166f42c62c8c36b2e8c9748939b9d5a0997fe6810'},
 'agent_boundary.py': {'classification': 'LOCAL_GUARD: execute_with_approval calls firewall.check, '
                                         'denies, atomically consumes bound grant; not SYSTEM '
                                         'authority; no production caller found.',
                       'sha256': 'e618affe99f146b35b54534092af933a5a382e5558178357ca92876ed7aaea3f'},
 'agent_capability/formation.py': {'classification': 'INTEGRITY_DELEGATE: FormedTool.invoke '
                                                     'asserts current actor/context/implementation '
                                                     'before callback; CapabilityRouter and '
                                                     'AgentLoop own Permission.',
                                   'dependencies': {'agent_capability/router.py': 'f6a04edffbe8a844afd86643bbe89d2837bca652f8cf7f40a9e329fc35cf3397',
                                                    'agent_runtime/loop.py': '6d09ce5619448bcb927b00cee91339825954027eb7ec0457817af8c3d5e74959'},
                                   'sha256': 'e484b4c3cef12580ddf9f0025dc31214dd279269ade5f06b7ec519bde9da6646'},
 'agent_capability/router.py': {'classification': 'CANONICAL_CHAIN: formed invoke callback '
                                                  'executes only via FormedCall/AgentLoop; execute '
                                                  'and resource reader check actor authorization '
                                                  'and canonical Permission/Firewall/Effect Fence.',
                                'dependencies': {'agent_capability/formation.py': 'e484b4c3cef12580ddf9f0025dc31214dd279269ade5f06b7ec519bde9da6646',
                                                 'lumenis/system/security/permission.py': '4a1d011299aaf1527b9838b3bb25a60b9a70934c9b94a578a57b2f82b39e3079'},
                                'sha256': 'f6a04edffbe8a844afd86643bbe89d2837bca652f8cf7f40a9e329fc35cf3397'},
 'agent_memory/semantic.py': {'classification': 'SOURCE_OWNER_DELEGATE: catalog existence reads '
                                                'SELECT 1, never facts; catalog shortcut excluded; '
                                                'discover_research_sources/verified_research_source '
                                                'facts_only=True and independent re-read, '
                                                'authorize_saved_work, task actor/scope binding, '
                                                'and independent canonical/source rechecks.',
                              'dependencies': {'agent_runtime/task_binding.py': '2c365ee3e41419d9404972fd3d7b70be46bee32cf963df1cf35443ffe546536e',
                                               'intelligence_library_api.py': '4dd71ac4eb23f5170fc9912f94aefe7077cd324832090508b0e8fac015c89fce',
                                               'lumenis/shared/reporting/saved_work.py': '60050747ec245f5240f70c59cb32d94df5fa930e25ce301985e1bf2abbad12a5'},
                              'sha256': '7dcb01e78b898642c28d7cb0a4509adf64e4a0d0e741e4d595ad76dc17be2214'},
 'agent_research/debate.py': {'classification': 'PURE_LEGACY_HELPER: in-memory critique '
                                                'transformation, no I/O/model/action; current '
                                                'ResearchRunner no longer uses template debate as '
                                                'evidence.',
                              'sha256': 'f09fcbd75525f95706ffb5e2f1e7389e2e7e87ff987e2db6034814e8239546d6'},
 'agent_research/runner.py': {'classification': 'PURE_DELEGATE: analyze_source_records transforms '
                                                'caller-resolved records; source-bound caller owns '
                                                'authorization, not a runtime execution gate.',
                              'dependencies': {'agent_research/source_bound.py': 'c4025dd6a2968a4a71c37bb00fc7081a9fe0593ea75ed40aa59b383cd0809f0e'},
                              'sha256': '2feb3519841ae10faf6d8f5780d61093fa13f7818f21d875fa98fc93b549f8bc'},
 'agent_runtime/agent_zero_gui_executor.py': {'classification': 'DELEGATED: execute calls '
                                                                '_preflight before worker; exact '
                                                                'task-scoped permission checked by '
                                                                '_permission_matches; caller owns '
                                                                'Permission issuance.',
                                              'sha256': '40a4bb47bc94b5309724f611d9014ac40f91993fe16c22e63d7f477ce8ca54e8'},
 'agent_runtime/loop.py': {'classification': 'CANONICAL_CHAIN: run reaches _execute_step; '
                                             'gate.check allowed state is required before tool '
                                             'invocation, with task scope and current binding '
                                             'checks.',
                           'dependencies': {'agent_capability/formation.py': 'e484b4c3cef12580ddf9f0025dc31214dd279269ade5f06b7ec519bde9da6646',
                                            'lumenis/system/security/permission.py': '4a1d011299aaf1527b9838b3bb25a60b9a70934c9b94a578a57b2f82b39e3079'},
                           'sha256': '6d09ce5619448bcb927b00cee91339825954027eb7ec0457817af8c3d5e74959'},
 'agent_runtime/task_binding.py': {'classification': 'CANONICAL_DELEGATE: authorized_context calls '
                                                     'check_actor_scope_permission/check_local_workspace_scope_permission; '
                                                     'invocation and result recheck bindings; '
                                                     'saved work preserves its authorized actor/scope.',
                                   'dependencies': {'account/authorization.py': 'b7111044741a5facdf3c8633f904336bb6c8276d3f1a2139f61b52ca836f8ee9',
                                                    'lumenis/shared/reporting/saved_work.py': '60050747ec245f5240f70c59cb32d94df5fa930e25ce301985e1bf2abbad12a5',
                                                    'lumenis/system/security/permission.py': '4a1d011299aaf1527b9838b3bb25a60b9a70934c9b94a578a57b2f82b39e3079'},
                                   'sha256': '2c365ee3e41419d9404972fd3d7b70be46bee32cf963df1cf35443ffe546536e'},
 'agent_smart_tool/base.py': {'classification': 'CANONICAL_CHAIN: registry.execute delegates to '
                                                'registered SmartTool.execute; '
                                                '_check_security_gates calls canonical '
                                                'Permission/Firewall/Effect Fence and rejects '
                                                'before _run.',
                              'dependencies': {'lumenis/system/security/permission.py': '4a1d011299aaf1527b9838b3bb25a60b9a70934c9b94a578a57b2f82b39e3079'},
                              'sha256': '839e213a3492b90ee5b860be394c4c99d21ce142423c06ce2c1b510ad072758a'},
 'lumenis/shared/agents/skills/execution.py': {'classification': 'CANONICAL_CHAIN: execute_skill '
                                                                 'and bound background handler are '
                                                                 'inner operations; '
                                                                 'run_execution_chain checks '
                                                                 'Permission/Firewall/Effect Fence '
                                                                 'first and background owner '
                                                                 'revalidates producer/scope.',
                                               'dependencies': {'account/authorization.py': 'b7111044741a5facdf3c8633f904336bb6c8276d3f1a2139f61b52ca836f8ee9',
                                                                'agent_runtime/task_binding.py': '2c365ee3e41419d9404972fd3d7b70be46bee32cf963df1cf35443ffe546536e',
                                                                'lumenis/system/security/permission.py': '4a1d011299aaf1527b9838b3bb25a60b9a70934c9b94a578a57b2f82b39e3079'},
                                               'sha256': '161f1a12e4976c6b93753c60c16303e7d73b2a2b2207d0c6a1b641c23f3a6235'},
 'lumenis_shared_skills.py': {'classification': 'DELEGATED: run_shared_skill is called by '
                                                'shared.agents.skills.execution._execute_builtin_local '
                                                'after canonical Permission/Firewall/Effect Fence; '
                                                'no independent permission grant.',
                              'dependencies': {'lumenis/shared/agents/skills/execution.py': '161f1a12e4976c6b93753c60c16303e7d73b2a2b2207d0c6a1b641c23f3a6235'},
                              'sha256': '16b684ebfc7103da27882a7d254b2d965d4847a61d061a529dc3107138789a89'},
 'lumenis_skill_adapter.py': {'classification': 'DELEGATED: invoked by '
                                                'shared.agents.skills.execution.execute_skill only '
                                                'after run_execution_chain '
                                                'Permission/Firewall/Effect Fence. OSAI missing '
                                                'remains unavailable.',
                              'dependencies': {'lumenis/shared/agents/skills/execution.py': '161f1a12e4976c6b93753c60c16303e7d73b2a2b2207d0c6a1b641c23f3a6235'},
                              'sha256': '9baa31c2da14ca9fa7fc79be778e875f59007548c88baa71f599bc30e394c3fe'},
 'mcp_skill_runtime.py': {'classification': 'DELEGATED: registered MCP invoked by same execution '
                                            'owner; own installation/tool allowlist/human '
                                            'approval/read-only contract checks retained.',
                          'dependencies': {'lumenis/shared/agents/skills/execution.py': '161f1a12e4976c6b93753c60c16303e7d73b2a2b2207d0c6a1b641c23f3a6235'},
                          'sha256': '18e178a6e1b1ab9c2ea39df03a2a50be1c243a28e813c78a7e487b32bfdc4769'},
 'migrations/create_intelligence_assets_table.py': {'classification': 'SCHEMA_DIAGNOSTIC: '
                                                                      'controlled migration count '
                                                                      'after CREATE TABLE; not '
                                                                      'content admission or '
                                                                      'production fact '
                                                                      'consumption; not executed '
                                                                      'by this source checker.',
                                                    'sha256': 'c436c8fa5c9b7ce18d5b2e3c38fe45d6ede99abb89ff974f8c9add77a7111eaf'},
 'scripts/audit_tools/new_asset_acceptance_check.py': {'classification': 'LEGACY_DIAGNOSTIC: '
                                                                         'catalog counts/status '
                                                                         'distribution/pending IDs '
                                                                         'for audit only; not '
                                                                         'product fact consumer, '
                                                                         'no live caller found; '
                                                                         'its runtime DB not '
                                                                         'accessed or accepted '
                                                                         'here.',
                                                       'sha256': '262bbe44b9dde42722cc796d9ee7d97edca522146fed0db2aa32aa4dd3a12490'}}


def _source_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _review_status(rel, path):
    reviewed = _REVIEWED_BOUNDARIES.get(rel)
    if reviewed is None:
        return None
    if path.is_symlink() or _source_digest(path) != reviewed["sha256"]:
        return False
    for dependency, expected in reviewed.get("dependencies", {}).items():
        linked = PROJECT_ROOT / dependency
        if not linked.is_file() or linked.is_symlink() or _source_digest(linked) != expected:
            return False
    return True


# ============================================================
# 检查 6: Skill/Memory/Agent 绕过 Permission Gate
# ============================================================
def check_permission_gate(files: List[Path]) -> List[Violation]:
    """检查 agent/skill 执行是否绕过权限检查"""
    violations = []

    # 查找 agent/skill 执行入口
    agent_skill_files = []
    for fpath in files:
        rel = str(fpath.relative_to(PROJECT_ROOT)).lower()
        if any(kw in rel for kw in ["agent", "skill", "lumenis_skill", "skill_registry"]):
            agent_skill_files.append(fpath)

    permission_owner = "lumenis/system/security/permission.py"
    permission_gate_file = PROJECT_ROOT / permission_owner
    has_permission_gate = permission_gate_file.exists()

    if not has_permission_gate:
        violations.append(Violation(
            "B6-PERMISSION", permission_owner, 0,
            "Canonical SYSTEM Permission owner 不存在",
            SEVERITY_HIGH,
            "Agent/Skill 执行应经过 Permission Gate"
        ))
        return violations

    for fpath in agent_skill_files:
        rel = fpath.relative_to(PROJECT_ROOT).as_posix()
        reviewed = _review_status(rel, fpath)
        if reviewed is True:
            continue
        if reviewed is False:
            violations.append(Violation("B6-PERMISSION", rel, 0,
                "Reviewed boundary changed; renew caller and denial-case review", SEVERITY_HIGH))
            continue
        tree = ast.parse(fpath.read_text(encoding="utf-8-sig"))
        entries = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name.startswith(("execute", "run", "invoke", "call_skill"))]
        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.setdefault(node.name, []).append(node)
        gate_names = {"check_permission", "check_actor_scope_permission", "check_local_workspace_scope_permission",
                      "authorized_context", "run_execution_chain"}
        def reaches_gate(function, seen):
            if function.name in seen:
                return False
            seen = seen | {function.name}
            # Function-local calls plus explicitly reached local delegates.
            # A gate in an unrelated function cannot authorize this entry.
            calls = []
            def visit(node):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    return
                if isinstance(node, ast.Call):
                    calls.append(node)
                for child in ast.iter_child_nodes(node):
                    visit(child)
            for statement in function.body:
                visit(statement)
            for call in calls:
                called = ast.unparse(call.func)
                name = called.rsplit(".", 1)[-1].lstrip("_")
                if name in gate_names:
                    return True
                if called.endswith("get_permission_gate().check") or called.endswith("_get_permission_gate().check"):
                    return True
                raw_name = called.rsplit(".", 1)[-1]
                if len(functions.get(raw_name, [])) == 1 and reaches_gate(functions[raw_name][0], seen):
                    return True
            return False
        for entry in entries:
            if not reaches_gate(entry, set()):
                violations.append(Violation("B6-PERMISSION", rel, entry.lineno,
                    "Execution entry has no reachable authorization check or reviewed delegation", SEVERITY_HIGH,
                    "Static candidate, not a proven exploit; trace caller and preserve denial tests before admission"))

    return violations


# ============================================================
# 检查 7: PENDING/CONCEPT 资产被生产代码引用
# ============================================================
def check_pending_assets_production_ref(files: List[Path]) -> List[Violation]:
    """检查 intelligence_library 中 PENDING/CONCEPT 状态资产是否被生产代码直接引用"""
    violations = []
    for fpath in files:
        rel = fpath.relative_to(PROJECT_ROOT).as_posix()
        if rel == "intelligence_library_api.py" or rel.startswith("intelligence_library/"):
            continue  # Source owner has dedicated admission regressions, not consumer heuristics.
        source = fpath.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        queries = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and re.search(r"\bSELECT\b.*\bFROM\s+intelligence_assets\b", n.value, re.I | re.S)]
        if not queries:
            continue
        reviewed = _review_status(rel, fpath)
        if reviewed is True:
            continue
        # Presence queries return no source material; their later use still
        # belongs to semantic review. Direct content queries require review.
        for query in queries:
            if re.fullmatch(r"\s*SELECT\s+1\s+FROM\s+intelligence_assets\s+WHERE\s+asset_id\s*=\s*\?\s*", query.value, re.I) and reviewed is not False:
                continue
            violations.append(Violation("B7-PENDING-REF", rel, query.lineno,
                "Direct catalog material query requires SourceUse/Permission review", SEVERITY_HIGH,
                "Status words elsewhere in file do not prove source admission"))
    return violations


# ============================================================
# 检查 8: 凭证安全（不进 git/不打印）
# ============================================================
def check_credential_safety(files: List[Path]) -> List[Violation]:
    """检查凭证是否硬编码/打印（辅助检查）"""
    violations = []
    secret_patterns = [
        (re.compile(r'api[_-]?key\s*=\s*["\'][A-Za-z0-9]{20,}["\']'), "API Key 硬编码"),
        (re.compile(r'secret\s*=\s*["\'][A-Za-z0-9]{16,}["\']'), "Secret 硬编码"),
        (re.compile(r'password\s*=\s*["\'][^"\']{6,}["\']'), "Password 硬编码"),
        (re.compile(r'token\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']'), "Token 硬编码"),
        (re.compile(r'cookie\s*=\s*["\'][^"\']{50,}["\']'), "Cookie 硬编码"),
    ]

    for fpath in files:
        rel = str(fpath.relative_to(PROJECT_ROOT))
        if "test" in rel.lower() or "example" in rel.lower():
            continue
        try:
            source = fpath.read_text(encoding="utf-8-sig")
        except Exception as error:
            raise OSError("Source boundary input unavailable") from error
        for i, line in enumerate(source.split("\n"), 1):
            for pat, desc in secret_patterns:
                if pat.search(line):
                    violations.append(Violation(
                        "B8-CREDENTIAL", rel, i,
                        f"{desc}（内容不输出）",
                        SEVERITY_HIGH,
                        "凭证必须通过 .env/系统密钥注入，不得硬编码"
                    ))
                    break

    return violations


# ============================================================
# 主流程
# ============================================================
def get_production_tables() -> Set[str]:
    """获取生产表名集合（小写）"""
    tables = set()
    if DEFAULT_DB is not None and DEFAULT_DB.exists():
        try:
            conn = sqlite3.connect(str(DEFAULT_DB))
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for row in c.fetchall():
                tables.add(row[0].lower())
            conn.close()
        except Exception:
            pass
    return tables


def run_all_checks(osai_path: Optional[Path] = None) -> Dict:
    """执行所有边界检查"""
    print("=" * 60)
    print("OEVIRA source boundary diagnostics v2.0.0 (bounded static evidence)")
    print("=" * 60)

    files = get_production_py_files()
    print(f"\n生产 Python 文件: {len(files)}")

    production_tables = get_production_tables()
    print(f"生产表数量: {len(production_tables)}")

    all_violations: List[Violation] = []
    check_results: Dict[str, Any] = {}

    # B1
    print("\n[B1] 检查 ZBC 直接 import OSAI...")
    v = check_direct_osai_import(files)
    all_violations.extend(v)
    check_results["B1-direct-osai-import"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B2
    print("[B2] 检查 OSAI 直接连接 ZBC DB...")
    v = check_osai_db_connection(osai_path)
    all_violations.extend(v)
    check_results["B2-osai-db-connection"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B3
    print("[B3] 检查 OSAI 直接写 ZBC 生产表...")
    v = check_osai_write_production(osai_path, production_tables)
    all_violations.extend(v)
    check_results["B3-osai-write-production"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B4
    print("[B4] 检查 app 启动不依赖 OSAI...")
    v = check_app_startup_no_osai()
    all_violations.extend(v)
    check_results["B4-app-startup"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B5
    print("[B5] 检查跨库交互走 Contract/Artifact...")
    v = check_contract_artifact_usage(files)
    all_violations.extend(v)
    check_results["B5-contract-artifact"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B6
    print("[B6] 检查 Skill/Agent Permission Gate...")
    v = check_permission_gate(files)
    all_violations.extend(v)
    check_results["B6-permission-gate"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B7
    print("[B7] 检查 PENDING/CONCEPT 资产生产引用...")
    v = check_pending_assets_production_ref(files)
    all_violations.extend(v)
    check_results["B7-pending-assets-ref"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # B8
    print("[B8] 检查凭证安全（辅助）...")
    v = check_credential_safety(files)
    all_violations.extend(v)
    check_results["B8-credential-safety"] = {"violations": len(v), "items": [x.to_dict() for x in v]}
    print(f"  → {len(v)} violations")

    # 统计
    severity_counts = {}
    for v in all_violations:
        severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1

    result = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scanner_version": "2.0.0",
            "runtime_db_access": "NOT_ACCESSED",
            "limitations": "Static source candidates, not exhaustive authorization proof; delegated paths require same-version negative regressions.",
            "project_root": str(PROJECT_ROOT),
            "osai_path": str(osai_path) if osai_path else "not specified",
            "production_files_scanned": len(files),
            "production_tables": len(production_tables),
        },
        "summary": {
            "total_violations": len(all_violations),  # Legacy field: includes INFO, not vulnerability count.
            "blocking_findings": sum(v.severity in (SEVERITY_CRITICAL, SEVERITY_HIGH) for v in all_violations),
            "information_items": sum(v.severity == SEVERITY_INFO for v in all_violations),
            "by_severity": severity_counts,
            "by_check": {k: v["violations"] for k, v in check_results.items()},
        },
        "reviewed_boundaries": [
            {"file": rel, "classification": entry["classification"],
             "identity_matches": _review_status(rel, PROJECT_ROOT / rel)}
            for rel, entry in sorted(_REVIEWED_BOUNDARIES.items())
        ],
        "checks": check_results,
        "violations": [v.to_dict() for v in all_violations],
    }

    return result


def generate_markdown(result: Dict) -> str:
    """生成可读的边界检查报告"""
    s = result["summary"]
    lines = [
        "# ZBC/LUMENIS 双库边界检查报告 (Boundary Check Report)",
        "",
        f"> 生成时间: {result['metadata']['generated_at']}",
        f"> 检查器版本: {result['metadata']['scanner_version']}",
        f"> 扫描生产文件: {result['metadata']['production_files_scanned']}",
        f"> 生产表数量: {result['metadata']['production_tables']}",
        "",
        "## 1. 总览 (Summary)",
        "",
        f"**静态记录数: {s['total_violations']}；阻断候选: {s['blocking_findings']}（不等同已证实漏洞数）**",
        "",
        "### 按严重度",
        "",
        "| 严重度 | 数量 |",
        "|--------|------|",
    ]
    for sev in [SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO]:
        count = s["by_severity"].get(sev, 0)
        lines.append(f"| {sev} | {count} |")

    lines.extend([
        "",
        "### 按检查项",
        "",
        "| 检查项 | 违规数 |",
        "|--------|--------|",
    ])
    check_names = {
        "B1-direct-osai-import": "B1: ZBC 直接 import OSAI",
        "B2-osai-db-connection": "B2: OSAI 直接连接 ZBC DB",
        "B3-osai-write-production": "B3: OSAI 直接写 ZBC 生产表",
        "B4-app-startup": "B4: app 启动依赖 OSAI",
        "B5-contract-artifact": "B5: 跨库交互 Contract/Artifact",
        "B6-permission-gate": "B6: Skill/Agent Permission Gate",
        "B7-pending-assets-ref": "B7: PENDING 资产生产引用",
        "B8-credential-safety": "B8: 凭证安全（辅助）",
    }
    for check_id, count in s["by_check"].items():
        name = check_names.get(check_id, check_id)
        lines.append(f"| {name} | {count} |")

    # 详细违规列表（CRITICAL + HIGH）
    lines.extend([
        "",
        "## 2. 关键违规详情 (CRITICAL / HIGH)",
        "",
    ])
    critical_high = [v for v in result["violations"]
                     if v["severity"] in (SEVERITY_CRITICAL, SEVERITY_HIGH)]
    if critical_high:
        lines.append("| # | 严重度 | 检查项 | 文件 | 行号 | 原因 |")
        lines.append("|---|--------|--------|------|------|------|")
        for i, v in enumerate(critical_high[:100], 1):
            reason = v["reason"].replace("|", "\\|")[:80]
            lines.append(f"| {i} | {v['severity']} | {v['check_id']} | {v['file']} | {v['lineno']} | {reason} |")
    else:
        lines.append("*无 CRITICAL/HIGH 违规*")

    # MEDIUM/LOW 摘要
    medium_low = [v for v in result["violations"]
                  if v["severity"] in (SEVERITY_MEDIUM, SEVERITY_LOW)]
    if medium_low:
        lines.extend([
            "",
            f"## 3. 中低优先级违规 ({len(medium_low)} 项)",
            "",
            "| # | 严重度 | 检查项 | 文件 | 行号 | 原因 |",
            "|---|--------|--------|------|------|------|",
        ])
        for i, v in enumerate(medium_low[:100], 1):
            reason = v["reason"].replace("|", "\\|")[:80]
            lines.append(f"| {i} | {v['severity']} | {v['check_id']} | {v['file']} | {v['lineno']} | {reason} |")

    # INFO
    info_items = [v for v in result["violations"] if v["severity"] == SEVERITY_INFO]
    if info_items:
        lines.extend([
            "",
            f"## 4. 信息项 ({len(info_items)} 项)",
            "",
        ])
        for v in info_items[:20]:
            lines.append(f"- [{v['check_id']}] {v['file']}:{v['lineno']} — {v['reason'][:80]}")

    lines.extend([
        "",
        "---",
        "",
        "## 5. 处置原则",
        "",
        "- **CRITICAL**: 立即修复，阻断合并",
        "- **HIGH**: 本迭代修复",
        "- **MEDIUM**: 排入下迭代",
        "- **LOW/INFO**: 记录跟踪",
        "- 所有违规遵循 DENY+AUDIT+可定位原因原则",
        "",
        "*本文件由 scripts/audit_tools/boundary_check.py 自动生成，请勿手动编辑。*",
    ])

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ZBC Boundary Check")
    parser.add_argument("--osai-path", default=None, help="OSAI 库路径 (e.g. D:\\Zachary OS AI)")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--ci", action="store_true", help="CI 模式（exit code 反映违规数）")
    parser.add_argument("--output-dir", default=None, help="输出目录")
    args = parser.parse_args()

    osai_path = Path(args.osai_path) if args.osai_path else None
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_all_checks(osai_path)

    # 写 JSON
    json_path = output_dir / "BOUNDARY_CHECK_REPORT.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] JSON → {json_path}")

    # 写 MD
    md_path = output_dir / "BOUNDARY_CHECK_REPORT.md"
    md_content = generate_markdown(result)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[OK] MD   → {md_path}")

    # 摘要
    s = result["summary"]
    print(f"\n{'='*60}")
    print(f"边界检查完成: {s['total_violations']} records, {s['blocking_findings']} blocking candidates")
    for sev, count in s["by_severity"].items():
        print(f"  {sev}: {count}")
    print(f"{'='*60}")

    if args.json:
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))

    if args.ci:
        # CI 模式：有 CRITICAL/HIGH 则 exit 1
        critical_high = s["by_severity"].get(SEVERITY_CRITICAL, 0) + s["by_severity"].get(SEVERITY_HIGH, 0)
        sys.exit(1 if critical_high > 0 else 0)


if __name__ == "__main__":
    main()
