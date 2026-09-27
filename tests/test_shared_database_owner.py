"""Only-One guard for Shared Database path ownership."""
import ast
from pathlib import Path

from scripts.audit_tools.verify_database_authority import (
    DIRECT_CONNECT_OWNERS,
    audit_repository,
    find_direct_sqlite_calls,
)

REPO = Path(__file__).resolve().parents[1]

BUSINESS_SCHEMA_SYMBOLS = {
    "SCHEMA",
    "NOTE_MIGRATIONS",
    "WEB_MIGRATIONS",
    "REPORT_MIGRATIONS",
    "EVENT_MIGRATIONS",
}


def test_business_schema_has_one_canonical_owner_and_compatible_exports():
    import database
    import lumenis.shared.database as shared_database
    from lumenis.shared.database import business_schema

    root_tree = ast.parse((REPO / "database.py").read_text(encoding="utf-8"))
    root_assignments = {
        target.id
        for node in root_tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else (node.target,)
        )
        if isinstance(target, ast.Name)
    }

    assert BUSINESS_SCHEMA_SYMBOLS.isdisjoint(root_assignments)
    for symbol in BUSINESS_SCHEMA_SYMBOLS:
        canonical = getattr(business_schema, symbol)
        assert getattr(database, symbol) is canonical
        assert getattr(shared_database, symbol) is canonical
        assert symbol in shared_database.__all__
    assert shared_database.apply_business_schema is business_schema.apply_business_schema
    assert "apply_business_schema" in shared_database.__all__


def test_root_init_db_is_a_thin_canonical_schema_delegate():
    root_tree = ast.parse((REPO / "database.py").read_text(encoding="utf-8"))
    init_db = next(
        node
        for node in root_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "init_db"
    )
    calls = [
        node.func.id
        for node in ast.walk(init_db)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert calls.count("apply_business_schema") == 1
    assert "executescript" not in ast.unparse(init_db)

def test_shared_database_is_canonical_path_owner():
    source = (REPO / "lumenis/shared/database/paths.py").read_text(encoding="utf-8")
    assert "ZBC_DB_PATH" in source
    assert "ZBC_EVIDENCE_DB_PATH" not in source
    assert "ZBC_RUNTIME_GUARDIAN_DB" not in source
    assert "ZBC_TOKEN_DB_PATH" not in source

def test_root_db_paths_has_no_independent_resolution_logic():
    source = (REPO / "db_paths.py").read_text(encoding="utf-8")
    assert "lumenis.shared.database.paths" in source
    assert "_BASE_DIR" not in source
    assert "_first_env" not in source
    assert "os.environ" not in source

def test_shared_evidence_consumes_shared_database():
    for rel in [
        "lumenis/shared/evidence/chain.py",
        "lumenis/shared/evidence/store.py",
    ]:
        source = (REPO / rel).read_text(encoding="utf-8")
        assert "from db_paths import" not in source
        assert "lumenis.shared.database" in source

def test_known_runtime_callers_use_shared_database_owner():
    for rel in [
        "database.py",
        "database_migrations.py",
        "runtime_guardian.py",
        "ai_task_engine.py",
        "ark_llm.py",
        "intelligence_library_api.py",
        "badge_api.py",
        "data_center_api.py",
        "lumenis/shared/evidence/manual.py",
        "lumenis/shared/evaluation/recorder.py",
        "lumenis/shared/learning/feedback.py",
    ]:
        source = (REPO / rel).read_text(encoding="utf-8")
        assert "from db_paths import" not in source, rel

def test_migration_owner_is_shared_database():
    canonical = (REPO / "lumenis/shared/database/migrations.py").read_text(encoding="utf-8")
    root = (REPO / "database_migrations.py").read_text(encoding="utf-8")
    app = (REPO / "app.py").read_text(encoding="utf-8")
    assert "CURRENT_VERSION = 18" in canonical
    assert "def migration_16_to_17" in canonical
    assert "16: migration_16_to_17" in canonical
    assert "migration_12_to_13" in canonical
    assert "migration_13_to_14" in canonical
    assert "migration_14_to_15" in canonical
    assert "platform_schema" in canonical
    assert not (REPO / "migrations/migrate_platform_data_dict_v1.py").exists()
    assert not (REPO / "migrations/init_platform_registry.py").exists()
    assert "MIGRATIONS" in canonical
    assert "from lumenis.shared.database.migrations import *" in root
    assert "CURRENT_VERSION =" not in root
    assert "import database_migrations as _dm" not in app
    assert "from lumenis.shared.database import migrations as _dm" in app

def test_repository_registry_has_one_canonical_owner():
    canonical = (REPO / "lumenis/shared/database/registry.py").read_text(encoding="utf-8")
    root = (REPO / "repository_registry.py").read_text(encoding="utf-8")
    core = (REPO / "core/repository_registry.py").read_text(encoding="utf-8")
    assert "class RepositoryRegistry" in canonical
    assert "class RepositoryRegistry" not in root
    assert "class RepositoryRegistry" not in core
    assert "lumenis.shared.database.registry" in root
    assert "lumenis.shared.database.registry" in core

def test_database_repository_layer_is_canonical():
    source = (REPO / "lumenis/shared/database/repository.py").read_text(encoding="utf-8")
    assert "class DatabaseRepository" in source
    assert "connect_sqlite" in source
    assert "sqlite3.connect(" not in source

def test_first_standard_runtime_callers_use_repository_layer():
    for rel in [
        "badge_api.py",
        "data_center_api.py",
        "intelligence_library_api.py",
        "ai_call_logger.py",
        "content_generation.py",
    ]:
        source = (REPO / rel).read_text(encoding="utf-8")
        assert "get_repository" in source, rel
        assert "sqlite3.connect(" not in source, rel

def test_second_standard_runtime_callers_use_repository_layer():
    for rel in [
        "auth_recovery_center.py",
        "brand_knowledge_base.py",
        "case_deep_analysis.py",
        "collection_quality_gate.py",
    ]:
        source = (REPO / rel).read_text(encoding="utf-8")
        assert "DatabaseRepository" in source or "get_repository" in source, rel
        assert "sqlite3.connect(" not in source, rel

def test_priority_database_writers_use_repository_layer():
    for rel in [
        "ai_browser_runtime.py",
        "auth_recovery_center.py",
        "content_generation.py",
        "kos_engine.py",
        "kos_execution.py",
        "kos_ops.py",
        "kos_paid.py",
        "canonical_data.py",
        "human_correction.py",
    ]:
        source = (REPO / rel).read_text(encoding="utf-8")
        assert "lumenis.shared.database" in source, rel
        assert "os.environ.get(\"ZBC_DB_PATH\"" not in source, rel

def test_app_has_no_direct_sqlite_connections():
    source = (REPO / "app.py").read_text(encoding="utf-8")
    assert "sqlite3.connect(" not in source
    assert "_sq3.connect(" not in source
    assert "get_repository" in source

def test_production_modules_do_not_bypass_database_repository():
    """Ordinary production modules must not open SQLite directly.

    Canonical connection/migration infrastructure is the only allowed owner of
    raw sqlite3.connect. Tests, scripts and historical audit assets are outside
    this production-runtime guard.
    """
    allowed = {
        "lumenis/shared/database/connection.py",
        "lumenis/shared/database/migrations.py",
    }
    excluded_roots = {
        "tests", "scripts", "audit", "docs", "99-ARCHIVE",
        "OSAI测试证据", "intelligence_library", "build", "vendor",
    }
    violations = []
    for path in REPO.rglob("*.py"):
        rel = path.relative_to(REPO).as_posix()
        if rel in allowed:
            continue
        if rel.split("/", 1)[0] in excluded_roots:
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        if "sqlite3.connect(" in source:
            violations.append(rel)
    assert not violations, "Direct SQLite bypasses: " + ", ".join(sorted(violations))


def test_ast_guard_detects_supported_sqlite_alias_forms():
    samples = (
        "import sqlite3 as db\ndb.connect(':memory:')\n",
        "from sqlite3 import connect as open_db\nopen_db(':memory:')\n",
        "import sqlite3\nopen_db = sqlite3.connect\nopen_db(':memory:')\n",
    )
    for source in samples:
        assert find_direct_sqlite_calls(source), source


def test_ast_guard_accepts_only_canonical_direct_connection_owners():
    _, direct_findings, _ = audit_repository()
    assert not direct_findings, "Direct SQLite bypasses: " + ", ".join(
        finding.render() for finding in direct_findings
    )
    assert DIRECT_CONNECT_OWNERS == {
        "lumenis/shared/database/connection.py",
        "lumenis/shared/database/migrations.py",
    }
