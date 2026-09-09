import json
import sqlite3
from pathlib import Path

import pytest

from scripts import p0_asset_freeze


def test_sqlite_summary_and_backup_do_not_change_source(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO evidence(value) VALUES ('fact')")
    connection.commit()
    connection.close()
    before = p0_asset_freeze.sha256_file(source)

    summary = p0_asset_freeze.sqlite_summary(source)
    backup = p0_asset_freeze.backup_sqlite(source, tmp_path / "outside" / "backup.db")

    assert p0_asset_freeze.sha256_file(source) == before
    assert summary["integrity"] == ["ok"]
    assert summary["table_counts"]["evidence"] == 1
    assert backup["integrity"] == "ok"


def test_env_inventory_records_names_not_values(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("API_KEY=very-secret-value\nPORT=8201\n", encoding="utf-8")
    result = p0_asset_freeze.env_key_names(tmp_path)
    serialized = json.dumps(result)
    assert result[".env"] == ["API_KEY", "PORT"]
    assert "very-secret-value" not in serialized


def test_output_must_be_outside_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"assets": [], "database_candidates": []}', encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["p0_asset_freeze.py", "--config", str(config), "--output", str(Path(__file__).parents[1] / "bad")],
    )
    with pytest.raises(SystemExit):
        p0_asset_freeze.main()
