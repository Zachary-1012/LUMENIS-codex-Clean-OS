"""Canonical migrations retain conversations and actor-bound workspace drafts."""
import sqlite3

import pytest

from lumenis.shared.database import migrations


def seed_v20(path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with sqlite3.connect(path) as connection:
        migrations.init_version_table(connection)
        migrations.set_version(connection, 20, migrations.MIGRATION_HISTORY[20])
        connection.execute("CREATE TABLE retained_business(value TEXT)")
        connection.execute("INSERT INTO retained_business VALUES ('preserve')")


def create_conversation(connection):
    connection.execute(
        "INSERT INTO ai_conversations(conversation_id,actor_ref,workspace_binding,scope_json,"
        "title,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        ("conversation-fixture", "actor:fixture", "a" * 64, "{}", "Fixture", "now", "now"),
    )


def test_default_schema_and_reopen_preserve_conversation(tmp_path, monkeypatch):
    path = tmp_path / "conversation.db"
    seed_v20(path, monkeypatch)
    assert migrations.migrate() is True
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 22
        create_conversation(connection)
    assert migrations.migrate() is True
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT conversation_id FROM ai_conversations").fetchall() == [("conversation-fixture",)]
        assert connection.execute("SELECT value FROM retained_business").fetchone()[0] == "preserve"


def test_conversation_migration_rolls_back_on_failure(tmp_path, monkeypatch):
    path = tmp_path / "failure.db"
    seed_v20(path, monkeypatch)
    original = migrations.MIGRATIONS[20]

    def failure(connection):
        original(connection)
        raise RuntimeError("isolated conversation migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 20, failure)
    assert migrations.migrate() is False
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 20
        assert connection.execute("SELECT name FROM sqlite_master WHERE name LIKE 'ai_conversation%'").fetchall() == []
        assert connection.execute("SELECT value FROM retained_business").fetchone()[0] == "preserve"


def test_turn_constraints_and_foreign_key(tmp_path, monkeypatch):
    path = tmp_path / "constraints.db"
    seed_v20(path, monkeypatch)
    assert migrations.migrate() is True
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        create_conversation(connection)
        sql = ("INSERT INTO ai_conversation_turns(turn_id,conversation_id,idempotency_key,"
               "request_sha256,sequence,role,origin_kind,content_json,state,created_at,updated_at) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?)")
        row = ["turn-1", "conversation-fixture", "same-request", "b" * 64, 1,
               "user", "user_input", '{"text":"fixture"}', "recorded", "now", "now"]
        connection.execute(sql, row)
        for changed in ({0: "turn-2"}, {0: "turn-2", 2: "different-request"},
                        {0: "turn-3", 1: "nonexistent", 2: "new", 4: 2},
                        {0: "turn-4", 2: "new", 4: 0},
                        {0: "turn-5", 2: "new", 4: 2, 7: "invalid json"},
                        {0: "turn-6", 2: "new", 4: 2, 6: "task_projection"}):
            candidate = row.copy()
            for index, value in changed.items():
                candidate[index] = value
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(sql, candidate)


def test_incompatible_preexisting_conversation_table_is_not_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "incompatible.db"
    seed_v20(path, monkeypatch)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE ai_conversations(conversation_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO ai_conversations VALUES ('keep')")
    assert migrations.migrate() is False
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 20
        assert connection.execute("SELECT * FROM ai_conversations").fetchall() == [("keep",)]
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='ai_conversation_turns'").fetchone() is None


def test_incompatible_draft_table_retains_original_data_and_version(tmp_path, monkeypatch):
    path = tmp_path / 'draft-schema.db'
    seed_v20(path, monkeypatch)
    assert migrations.migrate(target_version=21) is True
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE ai_workspace_drafts(text TEXT)')
        connection.execute("INSERT INTO ai_workspace_drafts VALUES ('retained draft')")
    assert migrations.migrate() is False
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 21
        assert connection.execute('SELECT * FROM ai_workspace_drafts').fetchall() == [('retained draft',)]
        assert connection.execute('SELECT value FROM retained_business').fetchone()[0] == 'preserve'
