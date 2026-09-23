import sqlite3

import pytest

from lumenis.shared.database.repository import DatabaseRepository


def test_executescript_rolls_back_schema_and_rows_on_failure(tmp_path):
    repository = DatabaseRepository(str(tmp_path / "rollback.sqlite3"))

    with pytest.raises(sqlite3.OperationalError):
        repository.executescript(
            """
            CREATE TABLE atomicity_probe (value TEXT NOT NULL);
            INSERT INTO atomicity_probe (value) VALUES ('committed too early');
            INSERT INTO missing_atomicity_probe (value) VALUES ('failure');
            """
        )

    assert not repository.table_exists("atomicity_probe")


def test_executescript_commits_all_statements_on_success(tmp_path):
    repository = DatabaseRepository(str(tmp_path / "success.sqlite3"))

    repository.executescript(
        """
        CREATE TABLE atomicity_probe (value TEXT NOT NULL);
        INSERT INTO atomicity_probe (value) VALUES ('first');
        INSERT INTO atomicity_probe (value) VALUES ('second')
        """
    )

    rows = repository.query_all("SELECT value FROM atomicity_probe ORDER BY rowid")
    assert [row[0] for row in rows] == ["first", "second"]
