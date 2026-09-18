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
DEFAULT_DB = PROJECT_ROOT / "data" / "monitor.db"
OUTPUT_MD = PROJECT_ROOT / "audit" / "BOUNDARY_CHECK_REPORT.md"
OUTPUT_JSON = PROJECT_ROOT / "audit" / "BOUNDARY_CHECK_REPORT.json"

# 排除目录（非生产代码）
EXCLUDE_DIRS = {
    ".venv", "node_modules", "__pycache__", ".git",
    ".trae", ".trae-cn", ".opencode", ".ollama", ".skills-router",
    ".vscode", "_pitch_dump", "_ref_frames", "_shots", "_u",
    "99-ARCHIVE", "archive", "backups", "logs", "deliverables",
    "staging", "user_file", "_path_backup", "_scan_output",
    "audit", "docs", "00-GOVERNANCE", "02-ARCHITECTURE", "08-AUDIT",
    "intelligence_library",  # 研究库单独检查
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
    parts = rel_path.replace("\\", "/").split("/")
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
    for py_file in PROJECT_ROOT.rglob("*.py"):
        rel = str(py_file.relative_to(PROJECT_ROOT))
        if not is_production_file(rel):
            continue
        if rel.startswith(("data/", "logs/", "backups/", "node_modules/")):
            continue
        files.append(py_file)
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
            source = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 用 AST 精确检测 import（排除字符串中的 subprocess 调用）
        try:
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError:
            continue

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
        except Exception:
            continue
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
        except Exception:
            continue
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
    # 查找所有 subprocess 调用 OSAI 的地方，确认是否有 contract 伴随
    subprocess_osai = []
    for fpath in files:
        rel = str(fpath.relative_to(PROJECT_ROOT))
        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "osai" in source.lower() and ("subprocess" in source or "Popen" in source or "run(" in source):
            for i, line in enumerate(source.split("\n"), 1):
                if "osai" in line.lower() and ("subprocess" in line or "Popen" in line or ".run(" in line):
                    subprocess_osai.append((rel, i, line.strip()[:100]))

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

    # 检查是否有 artifact 交换机制
    artifact_files = list(PROJECT_ROOT.rglob("*artifact*"))
    artifact_files = [f for f in artifact_files if f.is_file() and is_production_file(str(f.relative_to(PROJECT_ROOT)))]
    if not artifact_files:
        violations.append(Violation(
            "B5-CONTRACT", "N/A", 0,
            "未找到 artifact 交换机制文件",
            SEVERITY_LOW,
            "跨库数据交换建议通过 artifact 文件（JSON/CSV）"
        ))

    # 记录 subprocess 调用为 INFO（合规模式）
    for rel, lineno, line in subprocess_osai[:10]:
        violations.append(Violation(
            "B5-CONTRACT", rel, lineno,
            f"subprocess 调用 OSAI（合规模式）: {line}",
            SEVERITY_INFO,
            "通过 subprocess 调用 OSAI 是允许的边界模式，需确保有 contract 定义"
        ))

    return violations


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

    permission_gate_file = PROJECT_ROOT / "permission_gate.py"
    has_permission_gate = permission_gate_file.exists()

    if not has_permission_gate:
        violations.append(Violation(
            "B6-PERMISSION", "permission_gate.py", 0,
            "permission_gate.py 不存在",
            SEVERITY_HIGH,
            "Agent/Skill 执行应经过 Permission Gate"
        ))
        return violations

    # 检查 agent/skill 文件是否 import permission_gate
    for fpath in agent_skill_files:
        rel = str(fpath.relative_to(PROJECT_ROOT))
        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        has_gate_import = ("permission_gate" in source or
                          "PermissionGate" in source or
                          "check_permission" in source)
        has_execution = ("def execute" in source or
                        "def run" in source or
                        "def invoke" in source or
                        "def call_skill" in source)
        if has_execution and not has_gate_import:
            violations.append(Violation(
                "B6-PERMISSION", rel, 0,
                f"Agent/Skill 执行入口未引用 Permission Gate",
                SEVERITY_MEDIUM,
                "Agent/Skill 执行前应检查权限（permission_gate）"
            ))

    return violations


# ============================================================
# 检查 7: PENDING/CONCEPT 资产被生产代码引用
# ============================================================
def check_pending_assets_production_ref(files: List[Path]) -> List[Violation]:
    """检查 intelligence_library 中 PENDING/CONCEPT 状态资产是否被生产代码直接引用"""
    violations = []

    # 从 DB 读取 PENDING/CONCEPT 资产
    pending_assets = set()
    if DEFAULT_DB.exists():
        try:
            conn = sqlite3.connect(str(DEFAULT_DB))
            c = conn.cursor()
            c.execute("""
                SELECT asset_id, title, knowledge_status, admission_status
                FROM intelligence_assets
                WHERE knowledge_status IN ('PENDING', 'CONCEPT')
                   OR admission_status IN ('PENDING', 'CANDIDATE')
            """)
            for row in c.fetchall():
                pending_assets.add(row[0])
                pending_assets.add(row[1])  # title 也可能被引用
            conn.close()
        except Exception:
            pass

    # 检查生产代码中是否硬编码引用这些资产 ID/标题
    for fpath in files:
        rel = str(fpath.relative_to(PROJECT_ROOT))
        if "intelligence_library" in rel:
            continue  # 研究库自身不算
        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for asset_id in list(pending_assets)[:200]:  # 限制检查数量
            if asset_id and len(asset_id) > 4 and asset_id in source:
                # 找到行号
                for i, line in enumerate(source.split("\n"), 1):
                    if asset_id in line:
                        violations.append(Violation(
                            "B7-PENDING-REF", rel, i,
                            f"生产代码引用未验证资产: {asset_id[:50]}",
                            SEVERITY_MEDIUM,
                            "PENDING/CONCEPT 状态资产不得被生产代码直接引用"
                        ))
                        break

    # 检查生产代码是否直接查询 intelligence_assets 且不过滤状态
    for fpath in files:
        rel = str(fpath.relative_to(PROJECT_ROOT))
        if "intelligence_library" in rel or "intelligence_library_api" in rel:
            continue
        if "test" in rel.lower() or rel.startswith("_") or "/_tmp" in rel:
            continue  # 测试/扫描脚本不算生产引用
        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "intelligence_assets" in source:
            for i, line in enumerate(source.split("\n"), 1):
                if "intelligence_assets" in line and "SELECT" in line.upper():
                    if "knowledge_status" not in source and "admission_status" not in source:
                        violations.append(Violation(
                            "B7-PENDING-REF", rel, i,
                            f"查询 intelligence_assets 未过滤 knowledge_status/admission_status",
                            SEVERITY_HIGH,
                            "生产代码查询 intelligence_assets 必须过滤 PENDING/CONCEPT 状态"
                        ))
                    break

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
            source = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(source.split("\n"), 1):
            for pat, desc in secret_patterns:
                if pat.search(line):
                    violations.append(Violation(
                        "B8-CREDENTIAL", rel, i,
                        f"{desc}: {line.strip()[:60]}",
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
    if DEFAULT_DB.exists():
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
    print("ZBC/LUMENIS 双库边界检查器 v1.0.0")
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
            "scanner_version": "1.0.0",
            "project_root": str(PROJECT_ROOT),
            "osai_path": str(osai_path) if osai_path else "not specified",
            "production_files_scanned": len(files),
            "production_tables": len(production_tables),
        },
        "summary": {
            "total_violations": len(all_violations),
            "by_severity": severity_counts,
            "by_check": {k: v["violations"] for k, v in check_results.items()},
        },
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
        f"**总违规数: {s['total_violations']}**",
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
    print(f"边界检查完成: {s['total_violations']} violations")
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
