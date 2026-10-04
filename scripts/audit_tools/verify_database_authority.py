"""Blocking guard for the LUMENIS Shared Database authority.

The guard deliberately separates production runtime modules from tests,
operator/audit scripts, generated output, and historical documentation.  Those
excluded paths are not evidence that production callers comply; they are
verified by their own test/tooling boundaries instead.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[2]

DIRECT_CONNECT_OWNERS = {
    "lumenis/shared/database/connection.py",
    "lumenis/shared/database/migrations.py",
}

# These roots are intentionally outside the imported production-runtime scan:
# tests own disposable fixtures; scripts/audit own operator diagnostics;
# governance/docs/research/archive trees are provenance; app is Dart; output,
# tmp, caches, vendor and build trees are generated or third-party material.
EXCLUDED_ROOTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "00-GOVERNANCE",
    "02-ARCHITECTURE",
    "99-ARCHIVE",
    "CHANGELOG",
    "OSAI测试证据",
    "app",
    "audit",
    "build",
    "docs",
    "intelligence_library",
    "logs",
    "node_modules",
    "output",
    "research",
    "scripts",
    "tests",
    "tmp",
    "vendor",
    "venv",
    "work",
}

# Despite its legacy name, this environment variable selects a JSON learning
# asset, not a SQLite database.  It therefore does not create another DB path.
NON_SQLITE_ENV_ALLOWLIST = {"ZBC_LEARNING_DB_PATH"}
CANONICAL_DB_OVERRIDE = "ZBC_DB_PATH"
DB_ENV_KEY = re.compile(r"(?:DB|DATABASE|MONITOR).*(?:PATH|URL)|(?:DB|DATABASE)$")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _read_tree(path: Path) -> ast.AST:
    return ast.parse(
        path.read_text(encoding="utf-8-sig", errors="strict"),
        filename=path.as_posix(),
    )


def production_python_files(root: Path = ROOT) -> list[Path]:
    """Return Python files that can participate in the production runtime."""
    result: list[Path] = []
    for directory, dirs, files in os.walk(root, onerror=_scan_error):
        current = Path(directory)
        # Prune before descent; nested owner/work is still production source.
        dirs[:] = [name for name in dirs if name != "__pycache__"
                   and not (current == root and name in EXCLUDED_ROOTS)]
        for name in files:
            if not name.endswith(".py"):
                continue
            # Existing root test/scratch entrypoints are not runtime owners.
            if current == root and name.startswith(("test_", "_")):
                continue
            result.append(current / name)
    return sorted(result)


def _scan_error(error: OSError) -> None:
    raise error


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def find_direct_sqlite_calls(source: str, path: str = "<source>") -> list[Finding]:
    """Detect sqlite3.connect calls through module, import, or assigned aliases."""
    tree = ast.parse(source, filename=path)
    module_aliases: set[str] = set()
    connect_aliases: set[str] = set()
    star_imports: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                if imported.name == "sqlite3":
                    module_aliases.add(imported.asname or "sqlite3")
        elif isinstance(node, ast.ImportFrom) and node.module == "sqlite3":
            for imported in node.names:
                if imported.name == "connect":
                    connect_aliases.add(imported.asname or "connect")
                elif imported.name == "*":
                    star_imports.append(node.lineno)

    # Propagate simple aliases such as ``open_db = sqlite3.connect`` and
    # ``other_open = open_db`` before inspecting calls.
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            target_names = {target.id for target in targets if isinstance(target, ast.Name)}
            if not target_names:
                continue
            is_connect = (
                isinstance(value, ast.Attribute)
                and value.attr == "connect"
                and _root_name(value.value) in module_aliases
            ) or (isinstance(value, ast.Name) and value.id in connect_aliases)
            if is_connect:
                before = len(connect_aliases)
                connect_aliases.update(target_names)
                changed = changed or len(connect_aliases) != before

    findings = [
        Finding(path, line, "sqlite3 star import can hide a direct connection")
        for line in star_imports
    ]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and function.attr == "connect"
            and _root_name(function.value) in module_aliases
        ):
            findings.append(
                Finding(path, node.lineno, "direct sqlite3.connect outside repository boundary")
            )
        elif isinstance(function, ast.Name) and function.id in connect_aliases:
            findings.append(
                Finding(path, node.lineno, "direct sqlite3 connect alias outside repository boundary")
            )
    return sorted(set(findings), key=lambda finding: (finding.line, finding.message))


def _environment_keys(tree: ast.AST) -> list[tuple[str, int]]:
    os_aliases = {"os"}
    getenv_aliases: set[str] = set()
    environ_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                if imported.name == "os":
                    os_aliases.add(imported.asname or "os")
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for imported in node.names:
                if imported.name == "getenv":
                    getenv_aliases.add(imported.asname or "getenv")
                elif imported.name == "environ":
                    environ_aliases.add(imported.asname or "environ")

    keys: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args:
            function = node.func
            is_lookup = (
                isinstance(function, ast.Attribute)
                and function.attr == "getenv"
                and isinstance(function.value, ast.Name)
                and function.value.id in os_aliases
            ) or (
                isinstance(function, ast.Attribute)
                and function.attr in {"get", "setdefault", "pop"}
                and (
                    (
                        isinstance(function.value, ast.Attribute)
                        and function.value.attr == "environ"
                        and isinstance(function.value.value, ast.Name)
                        and function.value.value.id in os_aliases
                    )
                    or (
                        isinstance(function.value, ast.Name)
                        and function.value.id in environ_aliases
                    )
                )
            ) or (isinstance(function, ast.Name) and function.id in getenv_aliases)
            if is_lookup and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                keys.append((node.args[0].value, node.lineno))
        elif isinstance(node, ast.Subscript):
            value = node.value
            is_environ = (
                isinstance(value, ast.Attribute)
                and value.attr == "environ"
                and isinstance(value.value, ast.Name)
                and value.value.id in os_aliases
            ) or (isinstance(value, ast.Name) and value.id in environ_aliases)
            slice_node = node.slice
            if is_environ and isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                keys.append((slice_node.value, node.lineno))
    return keys


def _is_database_override_key(key: str) -> bool:
    upper = key.upper()
    return bool(DB_ENV_KEY.search(upper)) or upper in {
        "ZBC_EVIDENCE_DB_PATH",
        "ZBC_RUNTIME_GUARDIAN_DB",
        "ZBC_TOKEN_DB_PATH",
    }


def _check_wrapper_contracts() -> list[Finding]:
    findings: list[Finding] = []
    required_imports = {
        "db_paths.py": "lumenis.shared.database.paths",
        "database_migrations.py": "lumenis.shared.database.migrations",
        "repository_registry.py": "lumenis.shared.database.registry",
        "core/repository_registry.py": "lumenis.shared.database.registry",
    }
    for rel, owner in required_imports.items():
        path = ROOT / rel
        if not path.is_file():
            findings.append(Finding(rel, 1, "missing compatibility wrapper"))
            continue
        tree = _read_tree(path)
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        if owner not in imported:
            findings.append(Finding(rel, 1, f"wrapper does not forward to {owner}"))
        for key, line in _environment_keys(tree):
            if _is_database_override_key(key):
                findings.append(Finding(rel, line, f"wrapper independently reads {key}"))
        if "monitor.db" in path.read_text(encoding="utf-8-sig"):
            findings.append(Finding(rel, 1, "wrapper contains independent monitor.db path logic"))

    database_path = ROOT / "database.py"
    database_tree = _read_tree(database_path)
    canonical_assignment = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DB_PATH" for target in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "main_db_path"
        for node in ast.walk(database_tree)
    )
    if not canonical_assignment:
        findings.append(Finding("database.py", 1, "root database compatibility surface does not bind DB_PATH via main_db_path()"))
    return findings


def audit_repository() -> tuple[int, list[Finding], list[Finding]]:
    direct_findings: list[Finding] = []
    override_findings: list[Finding] = []
    files = production_python_files()
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            source = path.read_text(encoding="utf-8-sig", errors="strict")
            tree = ast.parse(source, filename=rel)
        except (OSError, UnicodeError, SyntaxError) as exc:
            direct_findings.append(Finding(rel, getattr(exc, "lineno", 1) or 1, f"cannot AST-audit production module: {exc}"))
            continue

        calls = find_direct_sqlite_calls(source, rel)
        if rel not in DIRECT_CONNECT_OWNERS:
            direct_findings.extend(calls)
        for key, line in _environment_keys(tree):
            if key == CANONICAL_DB_OVERRIDE or key in NON_SQLITE_ENV_ALLOWLIST:
                continue
            if _is_database_override_key(key):
                override_findings.append(
                    Finding(rel, line, f"non-canonical database override {key}; use {CANONICAL_DB_OVERRIDE}")
                )

    paths_tree = _read_tree(ROOT / "lumenis/shared/database/paths.py")
    canonical_keys = {key for key, _ in _environment_keys(paths_tree)}
    if canonical_keys != {CANONICAL_DB_OVERRIDE}:
        override_findings.append(
            Finding(
                "lumenis/shared/database/paths.py",
                1,
                f"canonical path owner environment keys are {sorted(canonical_keys)!r}, expected only {CANONICAL_DB_OVERRIDE}",
            )
        )
    override_findings.extend(_check_wrapper_contracts())
    return len(files), sorted(direct_findings, key=Finding.render), sorted(override_findings, key=Finding.render)


def main() -> int:
    scanned, direct_findings, override_findings = audit_repository()
    print(f"Production Python modules AST-audited: {scanned}")
    print("Direct SQLite owners: " + ", ".join(sorted(DIRECT_CONNECT_OWNERS)))
    print("Excluded roots: " + ", ".join(sorted(EXCLUDED_ROOTS)))
    print("Root test_*.py and root underscore scratch files: explicitly excluded")

    findings = direct_findings + override_findings
    if findings:
        print(f"FAIL: Shared Database authority violations: {len(findings)}")
        for finding in findings:
            print(f"  - {finding.render()}")
        return 1

    print("PASS: Shared Database direct-connection and path-override authority is exclusive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
