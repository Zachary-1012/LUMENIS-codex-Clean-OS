"""Hermetic acceptance tests for the root database compatibility surface."""
import os
import sqlite3
from pathlib import Path

import pytest


FIXTURE_NOTE_ID = "round03-db-fixture"


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    """Build current module schemas and one fixture in an isolated database."""
    db_path = tmp_path / "lumenis-basic.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    import database
    import ark_llm
    import auth_recovery_center
    import kos_engine
    import kos_ops
    import kos_paid
    import podcast_store
    from lumenis.shared.database import DEFAULT_DB_PATH, DatabaseRepository

    assert db_path.resolve() != Path(DEFAULT_DB_PATH).resolve()
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    repository = DatabaseRepository(str(db_path))
    monkeypatch.setattr(database, "get_repository", lambda: repository)
    database.init_db()

    # These schemas are still initialized by their transitional module owners.
    # Bind each current initializer to the same disposable repository so this
    # test proves coverage without treating a fixture as Production Truth.
    for module in (ark_llm, auth_recovery_center, kos_engine, kos_ops, kos_paid, podcast_store):
        monkeypatch.setattr(module, "get_repository", lambda: repository)

    monkeypatch.setattr(kos_engine, "_KOS_SCHEMA_ENSURED", False)
    connection = kos_engine._get_conn()
    connection.close()

    connection = kos_paid._conn()
    connection.close()

    connection = kos_ops._conn()
    connection.close()

    podcast_store.init_db()
    assert ark_llm.load_daily_token() == 0
    auth_recovery_center.AuthRecoveryCenter()._ensure_table()

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO notes (note_id, title, content, author_nickname) "
            "VALUES (?, ?, ?, ?)",
            (FIXTURE_NOTE_ID, "Isolated fixture", "test-only", "pytest"),
        )
        connection.commit()
    return db_path


class TestDatabase:
    """数据库基础测试"""

    def test_database_exists(self, isolated_database):
        """测试数据库文件存在"""
        assert os.path.exists(isolated_database), f"数据库文件不存在: {isolated_database}"

    def test_database_connection(self, isolated_database):
        """测试数据库连接"""
        conn = sqlite3.connect(isolated_database)
        assert conn is not None
        conn.close()

    def test_required_tables_exist(self, isolated_database):
        """测试 root schema 与 transitional module schemas 均真实初始化。"""
        conn = sqlite3.connect(isolated_database)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        required_tables = [
            'notes', 'note_comments', 'events', 'daily_reports',
            'kos_profiles', 'kos_paid_plans', 'kos_operations',
            'podcast_entities', 'token_stat', 'auth_recovery_tasks',
        ]

        for table in required_tables:
            assert table in tables, f"必需的数据表不存在: {table}"

    def test_notes_table_structure(self, isolated_database):
        """测试笔记表结构"""
        conn = sqlite3.connect(isolated_database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(notes)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        required_columns = ['id', 'title', 'content', 'author_nickname', 'publish_date', 'sentiment', 'risk_level']
        for col in required_columns:
            assert col in columns, f"笔记表缺少必需字段: {col}"

    def test_events_table_structure(self, isolated_database):
        """测试事件表结构"""
        conn = sqlite3.connect(isolated_database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        required_columns = ['id', 'title', 'summary', 'risk_level', 'first_seen', 'last_seen']
        for col in required_columns:
            assert col in columns, f"事件表缺少必需字段: {col}"

    def test_explicit_fixture_record_is_queryable(self, isolated_database):
        """测试记录是显式 fixture，不代表任何生产数据。"""
        conn = sqlite3.connect(isolated_database)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT note_id, title, content, author_nickname FROM notes WHERE note_id=?",
            (FIXTURE_NOTE_ID,),
        )
        row = cursor.fetchone()
        conn.close()
        assert row == (FIXTURE_NOTE_ID, "Isolated fixture", "test-only", "pytest")

    def test_database_integrity(self, isolated_database):
        """测试数据库完整性"""
        conn = sqlite3.connect(isolated_database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        assert result == 'ok', f"数据库完整性检查失败: {result}"
