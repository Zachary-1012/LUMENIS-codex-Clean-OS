"""The unattended entry must not start the app or migrate a product database."""
import sqlite3

from scripts import run_prelaunch_maintenance as entry
from lumenis.shared import database
from lumenis.system.collector.adapters.scheduling import prelaunch_baseline


def test_disabled_entry_never_opens_database(monkeypatch):
    monkeypatch.setattr(prelaunch_baseline, "load_prelaunch_baseline_config",
                        lambda: {"status": "DISABLED"})
    monkeypatch.setattr(database, "connect_sqlite",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("DB opened")))
    assert entry.run_once() == {"status": "DISABLED"}


def test_old_schema_remains_unchanged(monkeypatch, tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("CREATE TABLE schema_version(version INTEGER);"
                                 "INSERT INTO schema_version VALUES(13);")
    before = path.read_bytes()
    monkeypatch.setattr(database, "main_db_path", lambda: str(path))
    monkeypatch.setattr(prelaunch_baseline, "load_prelaunch_baseline_config",
                        lambda: {"status": "READY"})
    assert entry.run_once()["reason"] == "PRODUCT_SCHEMA_REQUIRES_V18"
    assert path.read_bytes() == before


def test_success_log_omits_source_content(monkeypatch, tmp_path):
    path = tmp_path / "current.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("CREATE TABLE schema_version(version INTEGER);"
                                 "INSERT INTO schema_version VALUES(18);")
    monkeypatch.setattr(database, "main_db_path", lambda: str(path))
    monkeypatch.setattr(prelaunch_baseline, "load_prelaunch_baseline_config",
                        lambda: {"status": "READY"})
    monkeypatch.setattr(prelaunch_baseline, "run_due_prelaunch_baseline",
                        lambda: {"status": "COMPLETED", "summary": {"succeeded": 1},
                                 "runs": [{"body": "source content"}]})
    assert entry.run_once() == {"status": "COMPLETED", "summary": {"succeeded": 1}}


def test_private_environment_is_scoped_and_preserves_service_values(monkeypatch, tmp_path):
    path = tmp_path / "private.env"
    path.write_text("AI_PROVIDER=unrelated\nLUMENIS_PUBLIC_SOURCE_DOH_FALLBACK=1\n"
                    "ZBC_DB_PATH=wrong.db\n", encoding="utf-8")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK", raising=False)
    monkeypatch.setenv("ZBC_DB_PATH", "configured.db")
    entry.load_settings(path)
    assert "AI_PROVIDER" not in entry.os.environ
    assert entry.os.environ["ZBC_DB_PATH"] == "configured.db"
    assert entry.os.environ["LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK"] == "1"
