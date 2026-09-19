"""Only-One guard for Shared Database path ownership."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

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
    assert "CURRENT_VERSION = 12" in canonical
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
