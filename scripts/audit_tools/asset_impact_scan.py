# -*- coding: utf-8 -*-
"""
ZBC/LUMENIS 全库资产与影响图扫描器 (Asset Impact Graph Scanner)

P1 复杂度治理 — 统一资产登记，覆盖：
  产品 → 模块 → 文件 → 函数 → API → 数据表 → 工作流 → Skill → Contract → Test → UI → 部署 → 生产影响

扫描范围（脚本自动，不手动编）：
  - *.py: 函数定义/类/Blueprint路由/import关系
  - templates/*.html: 页面/路由/API调用
  - static/js/*.js: fetch/XHR调用
  - DB (sqlite_master): 表名/字段/索引
  - tests/: 测试覆盖
  - contracts/: 跨库契约
  - .github/workflows/: CI/CD

输出：
  audit/ASSET_IMPACT_GRAPH.json  (机器可读统一索引)
  audit/ASSET_IMPACT_GRAPH.md    (人类可读摘要)

用法：
  python scripts/audit_tools/asset_impact_scan.py
  python scripts/audit_tools/asset_impact_scan.py --db D:\\path\\to\\monitor.db
"""
from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================
# 配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = PROJECT_ROOT / "data" / "monitor.db"
OUTPUT_JSON = PROJECT_ROOT / "audit" / "ASSET_IMPACT_GRAPH.json"
OUTPUT_MD = PROJECT_ROOT / "audit" / "ASSET_IMPACT_GRAPH.md"

# 排除目录（不扫描）
EXCLUDE_DIRS = {
    ".venv", "node_modules", "__pycache__", ".git", ".gitignore",
    ".trae", ".trae-cn", ".opencode", ".ollama", ".skills-router",
    ".vscode", "_pitch_dump", "_ref_frames", "_shots", "_u",
    "99-ARCHIVE", "archive", "backups", "logs", "deliverables",
    "staging", "user_file",
}

# 产品/域分类规则（基于路径/文件名关键词）
DOMAIN_RULES = [
    ("ZBMP", ["zbrand", "zbmp", "multi_brand", "brand_propagation", "brand_directory",
              "brand_knowledge", "brand_report", "brand_stats", "brand_websites",
              "swire", "pr_case", "public_opinion_cases"]),
    ("CTH", ["taikoo", "cth", "太古汇", "subject_", "risk_engine", "daily_report",
             "weekly_events", "topic_campaign", "topic_monitor", "topic_snapshot",
             "web_monitor", "collection_api", "collector", "xhs_", "rednote"]),
    ("SYSTEM", ["system_", "auth_", "permission", "security", "v4_", "account",
                "runtime_", "guardian", "watchdog", "monitoring", "stability",
                "performance_isolation", "domain_isolation", "data_boundary",
                "safety_boundary", "security_boundary", "compliance", "ci_cd"]),
    ("KOS", ["kos_"]),
    ("AI", ["ai_", "llm", "ollama", "ark_", "local_ai", "provider", "lumenis",
            "intelligence", "learning_", "evaluation", "agent_", "skill_",
            "memory_", "context_"]),
    ("INTELLIGENCE_LIBRARY", ["intelligence_library"]),
    ("DCC", ["dcc", "data_quality", "data_feedback", "canonical", "evidence",
             "production_evidence", "app_evidence"]),
    ("OSAI", ["osai", "zachary", "序境"]),
    ("PODCAST", ["podcast"]),
    ("MIGRATION", ["migration", "migrate", "alembic", "lumenis", "historical"]),
    ("COOKIE", ["cookie", "auth_recovery", "login_manager", "account_keepalive",
                "browser_runtime", "internal_browser", "cdp_", "edge-cdp"]),
    ("NOTIFICATION", ["notification", "alert", "wechat_notifier", "badge"]),
    ("CI", [".github", "workflow", "ci_cd", "docker", "deployment", "deploy"]),
    ("REPORT", ["report_", "export_report", "report_export", "daily_report",
                "weekly", "monthly"]),
    ("COLLECTOR", ["collector", "crawl", "spider", "scraper", "platform_adapter",
                   "xhs_cdp", "xhs_collection", "xhs_runtime", "xhs_p0",
                   "collector_guard", "collector_v2", "collection_"]),
    ("UI", ["templates", "static", "lumenis_frontend", "ui_", "viz_",
            "frontend", "dashboard"]),
]

# 产品映射
PRODUCT_MAP = {
    "CTH": "CorTech-TaikooHui",
    "ZBMP": "Z-Brand Monitoring Platform",
    "SYSTEM": "Shared Core / System",
    "KOS": "KOS Module",
    "AI": "AI Runtime",
    "INTELLIGENCE_LIBRARY": "Intelligence Library",
    "DCC": "Data Canonical Chain",
    "OSAI": "OSAI (External)",
    "PODCAST": "Podcast Module",
    "MIGRATION": "Migration & Upgrade",
    "COOKIE": "Cookie & Auth",
    "NOTIFICATION": "Notification & Alert",
    "CI": "CI/CD & Deployment",
    "REPORT": "Report & Export",
    "COLLECTOR": "Collector & Adapters",
    "UI": "UI & Frontend",
}


def classify_domain(filepath: str) -> str:
    """根据文件路径分类到域"""
    fp = filepath.lower().replace("\\", "/")
    for domain, keywords in DOMAIN_RULES:
        for kw in keywords:
            if kw.lower() in fp:
                return domain
    return "CORE"


def classify_product(domain: str) -> str:
    return PRODUCT_MAP.get(domain, "Shared Core")


def file_hash(path: Path) -> str:
    """计算文件内容 SHA256 前16位（用于变更检测）"""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


# ============================================================
# Python AST 扫描
# ============================================================
class PyAnalyzer(ast.NodeVisitor):
    """分析单个 Python 文件的函数/类/路由/import"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.functions: List[Dict] = []
        self.classes: List[Dict] = []
        self.routes: List[Dict] = []
        self.imports: List[str] = []
        self.blueprints: List[str] = []
        self._current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        cls_info = {
            "name": node.name,
            "lineno": node.lineno,
            "methods": [],
            "bases": [ast.unparse(b) if hasattr(ast, "unparse") else "" for b in node.bases],
            "decorators": [ast.unparse(d) if hasattr(ast, "unparse") else "" for d in node.decorator_list],
        }
        self.classes.append(cls_info)
        old = self._current_class
        self._current_class = node.name
        # 提取方法
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls_info["methods"].append({
                    "name": item.name,
                    "lineno": item.lineno,
                    "args": [a.arg for a in item.args.args],
                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                })
        self._current_class = old
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._record_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._record_function(node, is_async=True)
        self.generic_visit(node)

    def _record_function(self, node, is_async: bool):
        if self._current_class:
            return  # 方法已在 class 中记录
        func_info = {
            "name": node.name,
            "lineno": node.lineno,
            "args": [a.arg for a in node.args.args],
            "is_async": is_async,
            "decorators": [ast.unparse(d) if hasattr(ast, "unparse") else "" for d in node.decorator_list],
        }
        self.functions.append(func_info)
        # 检测 Blueprint 路由装饰器
        for dec in node.decorator_list:
            try:
                dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
            except Exception:
                dec_str = ""
            route_match = re.search(r'@?(\w+_bp)\.route\(["\']([^"\']+)["\']', dec_str)
            if route_match:
                self.routes.append({
                    "blueprint": route_match.group(1),
                    "path": route_match.group(2),
                    "function": node.name,
                    "lineno": node.lineno,
                    "methods": self._extract_methods(dec),
                })
            # app.route 直接注册
            app_match = re.search(r'@?app\.route\(["\']([^"\']+)["\']', dec_str)
            if app_match:
                self.routes.append({
                    "blueprint": "app",
                    "path": app_match.group(1),
                    "function": node.name,
                    "lineno": node.lineno,
                    "methods": self._extract_methods(dec),
                })

    def _extract_methods(self, dec) -> List[str]:
        try:
            dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
            m = re.search(r'methods\s*=\s*\[([^\]]+)\]', dec_str)
            if m:
                return [x.strip().strip("'\"") for x in m.group(1).split(",")]
        except Exception:
            pass
        return ["GET"]


def scan_python_file(path: Path) -> Dict:
    """扫描单个 Python 文件"""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return {"error": "syntax_error", "functions": [], "classes": [], "routes": [], "imports": []}
    except Exception as e:
        return {"error": str(e)[:100], "functions": [], "classes": [], "routes": [], "imports": []}

    analyzer = PyAnalyzer(str(path))
    analyzer.visit(tree)

    # 检测 Blueprint 定义
    blueprint_defs = re.findall(
        r'(\w+_bp)\s*=\s*Blueprint\(["\'](\w+)["\']', source
    )
    blueprints = [{"var": b[0], "name": b[1]} for b in blueprint_defs]

    # 检测 register_blueprint
    registered = re.findall(r'register_blueprint\((\w+)', source)

    return {
        "functions": analyzer.functions,
        "classes": analyzer.classes,
        "routes": analyzer.routes,
        "imports": analyzer.imports,
        "blueprints": blueprints,
        "registered_blueprints": registered,
        "line_count": source.count("\n") + 1,
    }


# ============================================================
# HTML 模板扫描
# ============================================================
def scan_html_file(path: Path) -> Dict:
    """扫描 HTML 模板中的页面路由和 API 调用"""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"error": "read_failed"}

    # 提取 fetch/axios/XHR 调用
    api_calls = []
    fetch_patterns = [
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.(get|post|put|delete)\(["\']([^"\']+)["\']',
        r'\$\.ajax\([^)]*url\s*:\s*["\']([^"\']+)["\']',
        r'url\s*:\s*["\'](/api/[^"\']+)["\']',
    ]
    for pat in fetch_patterns:
        for m in re.finditer(pat, content):
            url = m.group(1) if m.lastindex == 1 else m.group(2)
            if url and (url.startswith("/api/") or url.startswith("api/")):
                api_calls.append(url)

    # 提取页面路由（href 中的 / 路径）
    page_routes = list(set(re.findall(r'href\s*=\s*["\'](/[^"\']+)["\']', content)))
    page_routes = [r for r in page_routes if not r.startswith(("/static", "/api", "#"))]

    return {
        "api_calls": list(set(api_calls)),
        "page_routes": page_routes[:50],  # 限制数量
        "line_count": content.count("\n") + 1,
    }


# ============================================================
# JS 扫描
# ============================================================
def scan_js_file(path: Path) -> Dict:
    """扫描 JS 文件中的 fetch/XHR 调用"""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"error": "read_failed"}

    api_calls = []
    for pat in [
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        r'XMLHttpRequest',
    ]:
        for m in re.finditer(pat, content):
            if m.lastindex and m.lastindex >= 1:
                url = m.group(1) if m.lastindex == 1 else m.group(2)
                if url and "/api/" in url:
                    api_calls.append(url)

    return {
        "api_calls": list(set(api_calls))[:100],
        "has_xhr": "XMLHttpRequest" in content,
        "line_count": content.count("\n") + 1,
    }


# ============================================================
# 数据库扫描
# ============================================================
def scan_database(db_path: Path) -> Dict:
    """扫描 SQLite 数据库表结构"""
    tables = {}
    if not db_path.exists():
        return {"error": f"DB not found: {db_path}", "tables": {}}

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        table_rows = c.fetchall()

        for row in table_rows:
            tname = row["name"]
            if tname.startswith("sqlite_"):
                continue
            # 字段
            c.execute(f"PRAGMA table_info([{tname}])")
            cols = []
            for col in c.fetchall():
                cols.append({
                    "name": col["name"],
                    "type": col["type"],
                    "notnull": bool(col["notnull"]),
                    "pk": bool(col["pk"]),
                    "default": str(col["dflt_value"]) if col["dflt_value"] is not None else None,
                })
            # 索引
            c.execute(f"PRAGMA index_list([{tname}])")
            indexes = []
            for idx in c.fetchall():
                idx_name = idx["name"]
                c.execute(f"PRAGMA index_info([{idx_name}])")
                idx_cols = [ic["name"] for ic in c.fetchall()]
                indexes.append({"name": idx_name, "columns": idx_cols, "unique": bool(idx["unique"])})
            # 行数
            try:
                c.execute(f"SELECT COUNT(*) FROM [{tname}]")
                row_count = c.fetchone()[0]
            except Exception:
                row_count = -1

            tables[tname] = {
                "columns": cols,
                "indexes": indexes,
                "row_count": row_count,
                "has_create_sql": bool(row["sql"]),
            }

        conn.close()
    except Exception as e:
        return {"error": str(e), "tables": tables}

    return {"tables": tables, "table_count": len(tables)}


# ============================================================
# 测试扫描
# ============================================================
def scan_tests(tests_dir: Path) -> Dict:
    """扫描 tests 目录"""
    test_files = []
    total_tests = 0
    if not tests_dir.exists():
        return {"test_files": [], "total_tests": 0}

    for f in tests_dir.rglob("test_*.py"):
        if any(ex in str(f) for ex in EXCLUDE_DIRS):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            test_funcs = re.findall(r'def (test_\w+)', content)
            test_classes = re.findall(r'class (Test\w+)', content)
            rel = str(f.relative_to(PROJECT_ROOT))
            test_files.append({
                "file": rel,
                "test_functions": test_funcs,
                "test_classes": test_classes,
                "count": len(test_funcs),
            })
            total_tests += len(test_funcs)
        except Exception:
            pass

    return {"test_files": test_files, "total_tests": total_tests}


# ============================================================
# Contract / Skill / CI 扫描
# ============================================================
def scan_contracts(contracts_dir: Path) -> List[Dict]:
    """扫描 contracts 目录"""
    contracts = []
    if not contracts_dir.exists():
        return contracts
    for f in contracts_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".md", ".json", ".yaml", ".yml"):
            rel = str(f.relative_to(PROJECT_ROOT))
            contracts.append({
                "file": rel,
                "type": f.suffix.lstrip("."),
                "domain": classify_domain(rel),
            })
    return contracts


def scan_skills() -> List[Dict]:
    """扫描 skill 相关文件"""
    skills = []
    skill_patterns = ["skill_registry.py", "lumenis_skill_adapter.py", "skills_registry"]
    for pat in skill_patterns:
        for f in PROJECT_ROOT.rglob(pat):
            if any(ex in str(f) for ex in EXCLUDE_DIRS):
                continue
            rel = str(f.relative_to(PROJECT_ROOT))
            skills.append({"file": rel, "type": "skill_registry"})
    # DB 中的 skills_registry 表
    return skills


def scan_ci(github_dir: Path) -> List[Dict]:
    """扫描 .github/workflows"""
    workflows = []
    wf_dir = github_dir / "workflows"
    if not wf_dir.exists():
        return workflows
    for f in wf_dir.glob("*.yml"):
        rel = str(f.relative_to(PROJECT_ROOT))
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
            workflows.append({
                "file": rel,
                "name": name_match.group(1).strip() if name_match else f.stem,
                "triggers": re.findall(r'^\s+(\w+):', content),
            })
        except Exception:
            workflows.append({"file": rel, "name": f.stem})
    return workflows


# ============================================================
# 主扫描流程
# ============================================================
def scan_all(db_path: Optional[Path] = None) -> Dict:
    """执行全库扫描，返回统一资产索引"""
    db_path = db_path or DEFAULT_DB
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    assets: Dict[str, Any] = {
        "metadata": {
            "generated_at": scan_time,
            "project_root": str(PROJECT_ROOT),
            "db_path": str(db_path),
            "scanner_version": "1.0.0",
        },
        "summary": {},
        "domains": {},
        "files": {},
        "apis": [],
        "tables": {},
        "tests": {},
        "contracts": [],
        "skills": [],
        "ci_workflows": [],
        "ui_pages": [],
        "dependencies": {"internal": [], "external": set()},
    }

    # ---- 1. 扫描 Python 文件 ----
    print("[1/6] Scanning Python files...")
    py_files_scanned = 0
    all_functions = 0
    all_classes = 0
    all_routes = 0
    domain_file_count: Dict[str, int] = {}
    domain_func_count: Dict[str, int] = {}

    for py_file in PROJECT_ROOT.rglob("*.py"):
        rel = str(py_file.relative_to(PROJECT_ROOT))
        # 排除
        if any(ex in rel for ex in EXCLUDE_DIRS):
            continue
        if rel.startswith(("data/", "logs/", "backups/", "node_modules/")):
            continue

        domain = classify_domain(rel)
        product = classify_product(domain)

        result = scan_python_file(py_file)
        if "error" in result and not result.get("functions"):
            continue

        py_files_scanned += 1
        all_functions += len(result.get("functions", []))
        all_classes += len(result.get("classes", []))
        all_routes += len(result.get("routes", []))

        domain_file_count[domain] = domain_file_count.get(domain, 0) + 1
        domain_func_count[domain] = domain_func_count.get(domain, 0) + len(result.get("functions", []))

        assets["files"][rel] = {
            "id": hashlib.md5(rel.encode()).hexdigest()[:12],
            "type": "python",
            "product": product,
            "domain": domain,
            "path": rel,
            "line_count": result.get("line_count", 0),
            "function_count": len(result.get("functions", [])),
            "class_count": len(result.get("classes", [])),
            "route_count": len(result.get("routes", [])),
            "functions": [f["name"] for f in result.get("functions", [])],
            "classes": [c["name"] for c in result.get("classes", [])],
            "imports": result.get("imports", [])[:50],
            "blueprints": result.get("blueprints", []),
            "file_hash": file_hash(py_file),
        }

        # 收集 API 路由
        for route in result.get("routes", []):
            assets["apis"].append({
                "path": route["path"],
                "methods": route.get("methods", ["GET"]),
                "function": route["function"],
                "file": rel,
                "blueprint": route["blueprint"],
                "domain": domain,
                "product": product,
            })

    print(f"  → {py_files_scanned} Python files, {all_functions} functions, {all_classes} classes, {all_routes} routes")

    # ---- 2. 扫描 HTML 模板 ----
    print("[2/6] Scanning HTML templates...")
    html_count = 0
    all_page_routes = set()
    all_template_api_calls = set()
    templates_dir = PROJECT_ROOT / "templates"
    if templates_dir.exists():
        for html_file in templates_dir.rglob("*.html"):
            rel = str(html_file.relative_to(PROJECT_ROOT))
            result = scan_html_file(html_file)
            if "error" in result:
                continue
            html_count += 1
            for pr in result.get("page_routes", []):
                all_page_routes.add(pr)
            for ac in result.get("api_calls", []):
                all_template_api_calls.add(ac)
            assets["ui_pages"].append({
                "file": rel,
                "page_routes": result.get("page_routes", [])[:20],
                "api_calls": result.get("api_calls", [])[:30],
                "domain": classify_domain(rel),
            })
    print(f"  → {html_count} HTML templates, {len(all_page_routes)} page routes, {len(all_template_api_calls)} API calls")

    # ---- 3. 扫描 JS ----
    print("[3/6] Scanning JS files...")
    js_count = 0
    all_js_api_calls = set()
    static_dir = PROJECT_ROOT / "static"
    if static_dir.exists():
        for js_file in static_dir.rglob("*.js"):
            if any(ex in str(js_file) for ex in EXCLUDE_DIRS):
                continue
            rel = str(js_file.relative_to(PROJECT_ROOT))
            result = scan_js_file(js_file)
            if "error" in result:
                continue
            js_count += 1
            for ac in result.get("api_calls", []):
                all_js_api_calls.add(ac)
    print(f"  → {js_count} JS files, {len(all_js_api_calls)} API calls")

    # ---- 4. 扫描数据库 ----
    print("[4/6] Scanning database...")
    db_result = scan_database(db_path)
    assets["tables"] = db_result.get("tables", {})
    table_count = db_result.get("table_count", 0)
    print(f"  → {table_count} tables")

    # ---- 5. 扫描测试 ----
    print("[5/6] Scanning tests...")
    tests_result = scan_tests(PROJECT_ROOT / "tests")
    assets["tests"] = tests_result
    print(f"  → {len(tests_result.get('test_files', []))} test files, {tests_result.get('total_tests', 0)} test functions")

    # ---- 6. 扫描 Contracts / Skills / CI ----
    print("[6/6] Scanning contracts, skills, CI...")
    assets["contracts"] = scan_contracts(PROJECT_ROOT / "contracts")
    assets["skills"] = scan_skills()
    assets["ci_workflows"] = scan_ci(PROJECT_ROOT / ".github")
    print(f"  → {len(assets['contracts'])} contracts, {len(assets['skills'])} skill files, {len(assets['ci_workflows'])} CI workflows")

    # ---- 汇总 ----
    total_api = len(assets["apis"])
    # 去重 API path
    unique_api_paths = list(set(a["path"] for a in assets["apis"]))

    assets["summary"] = {
        "python_files": py_files_scanned,
        "total_functions": all_functions,
        "total_classes": all_classes,
        "total_routes": all_routes,
        "unique_api_paths": len(unique_api_paths),
        "html_templates": html_count,
        "js_files": js_count,
        "db_tables": table_count,
        "test_files": len(tests_result.get("test_files", [])),
        "total_test_functions": tests_result.get("total_tests", 0),
        "contracts": len(assets["contracts"]),
        "skills": len(assets["skills"]),
        "ci_workflows": len(assets["ci_workflows"]),
        "ui_pages": len(assets["ui_pages"]),
        "domain_file_count": domain_file_count,
        "domain_function_count": domain_func_count,
    }

    # 按域组织
    for domain in set(list(domain_file_count.keys()) + ["CORE"]):
        domain_files = {k: v for k, v in assets["files"].items() if v["domain"] == domain}
        assets["domains"][domain] = {
            "product": classify_product(domain),
            "file_count": len(domain_files),
            "function_count": sum(f["function_count"] for f in domain_files.values()),
            "route_count": sum(f["route_count"] for f in domain_files.values()),
            "files": list(domain_files.keys())[:200],  # 限制
            "apis": [a for a in assets["apis"] if a["domain"] == domain],
        }

    return assets


def generate_markdown(assets: Dict) -> str:
    """生成可读的 Markdown 报告"""
    s = assets["summary"]
    lines = [
        "# ZBC/LUMENIS 全库资产与影响图 (Asset Impact Graph)",
        "",
        f"> 生成时间: {assets['metadata']['generated_at']}",
        f"> 扫描器版本: {assets['metadata']['scanner_version']}",
        f"> 项目根目录: {assets['metadata']['project_root']}",
        "",
        "## 1. 总览 (Summary)",
        "",
        "| 指标 | 数量 |",
        "|------|------|",
        f"| Python 源文件 | {s['python_files']} |",
        f"| 函数定义 | {s['total_functions']} |",
        f"| 类定义 | {s['total_classes']} |",
        f"| API 路由 (注册) | {s['total_routes']} |",
        f"| 唯一 API Path | {s['unique_api_paths']} |",
        f"| HTML 模板 | {s['html_templates']} |",
        f"| JS 文件 | {s['js_files']} |",
        f"| 数据库表 | {s['db_tables']} |",
        f"| 测试文件 | {s['test_files']} |",
        f"| 测试函数 | {s['total_test_functions']} |",
        f"| Contract 文件 | {s['contracts']} |",
        f"| Skill 注册文件 | {s['skills']} |",
        f"| CI Workflow | {s['ci_workflows']} |",
        f"| UI 页面 | {s['ui_pages']} |",
        "",
        "## 2. 按域分布 (Domain Distribution)",
        "",
        "| 域 (Domain) | 产品 | 文件数 | 函数数 | 路由数 |",
        "|-------------|------|--------|--------|--------|",
    ]

    for domain in sorted(assets["domains"].keys()):
        d = assets["domains"][domain]
        lines.append(
            f"| {domain} | {d['product']} | {d['file_count']} | "
            f"{d['function_count']} | {d['route_count']} |"
        )

    lines.extend([
        "",
        "## 3. 数据库表清单 (Database Tables)",
        "",
        "| 表名 | 字段数 | 行数 | 索引数 |",
        "|------|--------|------|--------|",
    ])
    for tname in sorted(assets["tables"].keys()):
        t = assets["tables"][tname]
        lines.append(
            f"| {tname} | {len(t.get('columns', []))} | "
            f"{t.get('row_count', 'N/A')} | {len(t.get('indexes', []))} |"
        )

    lines.extend([
        "",
        "## 4. API 路由清单 (按域)",
        "",
    ])
    for domain in sorted(assets["domains"].keys()):
        apis = assets["domains"][domain].get("apis", [])
        if not apis:
            continue
        lines.append(f"### {domain} ({len(apis)} routes)")
        lines.append("")
        lines.append("| Method | Path | Function | File |")
        lines.append("|--------|------|----------|------|")
        for api in sorted(apis, key=lambda x: x["path"]):
            methods = ",".join(api.get("methods", ["GET"]))
            lines.append(f"| {methods} | {api['path']} | {api['function']} | {api['file']} |")
        lines.append("")

    lines.extend([
        "## 5. CI/CD Workflows",
        "",
        "| Workflow | File |",
        "|----------|------|",
    ])
    for wf in assets["ci_workflows"]:
        lines.append(f"| {wf.get('name', '')} | {wf['file']} |")

    lines.extend([
        "",
        "## 6. Contracts (跨库契约)",
        "",
        "| 文件 | 类型 | 域 |",
        "|------|------|-----|",
    ])
    for c in assets["contracts"]:
        lines.append(f"| {c['file']} | {c['type']} | {c['domain']} |")

    lines.extend([
        "",
        "## 7. 测试覆盖 (Test Coverage)",
        "",
        f"总测试函数: **{s['total_test_functions']}**",
        "",
        "| 测试文件 | 测试函数数 |",
        "|----------|-----------|",
    ])
    for tf in sorted(assets["tests"].get("test_files", []), key=lambda x: -x["count"])[:50]:
        lines.append(f"| {tf['file']} | {tf['count']} |")

    lines.extend([
        "",
        "---",
        "",
        "*本文件由 scripts/audit_tools/asset_impact_scan.py 自动生成，请勿手动编辑。*",
        "*完整机器可读索引见 audit/ASSET_IMPACT_GRAPH.json*",
    ])

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ZBC Asset Impact Graph Scanner")
    parser.add_argument("--db", default=None, help="SQLite DB path")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else DEFAULT_DB
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ZBC/LUMENIS Asset Impact Graph Scanner v1.0.0")
    print("=" * 60)

    assets = scan_all(db_path)

    # 写 JSON
    json_path = output_dir / "ASSET_IMPACT_GRAPH.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(assets, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[OK] JSON → {json_path}")

    # 写 MD
    md_path = output_dir / "ASSET_IMPACT_GRAPH.md"
    md_content = generate_markdown(assets)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[OK] MD   → {md_path}")

    # 摘要
    s = assets["summary"]
    print(f"\n{'='*60}")
    print("扫描完成摘要:")
    print(f"  Python 文件: {s['python_files']}")
    print(f"  函数: {s['total_functions']}, 类: {s['total_classes']}")
    print(f"  API 路由: {s['total_routes']} (唯一 path: {s['unique_api_paths']})")
    print(f"  DB 表: {s['db_tables']}")
    print(f"  测试: {s['test_files']} 文件 / {s['total_test_functions']} 函数")
    print(f"  域数量: {len(assets['domains'])}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
