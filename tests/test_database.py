"""
数据库测试 - 广州太古汇舆情监测系统
"""
import os
import sys
import pytest
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDatabase:
    """数据库基础测试"""

    def test_database_exists(self):
        """测试数据库文件存在"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        assert os.path.exists(db_path), f"数据库文件不存在: {db_path}"

    def test_database_connection(self):
        """测试数据库连接"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        assert conn is not None
        conn.close()

    def test_required_tables_exist(self):
        """测试必需的数据表存在"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        required_tables = [
            'notes', 'events', 'comments', 'daily_reports',
            'web_topics', 'web_events', 'weekly_events',
            'brand_industry_monitor', 'notification_logs',
            'system_config', 'token_stat'
        ]

        for table in required_tables:
            assert table in tables, f"必需的数据表不存在: {table}"

    def test_notes_table_structure(self):
        """测试笔记表结构"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(notes)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        required_columns = ['id', 'title', 'content', 'author_nickname', 'publish_date', 'sentiment', 'risk_level']
        for col in required_columns:
            assert col in columns, f"笔记表缺少必需字段: {col}"

    def test_events_table_structure(self):
        """测试事件表结构"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        required_columns = ['id', 'title', 'summary', 'risk_level', 'first_seen', 'last_seen']
        for col in required_columns:
            assert col in columns, f"事件表缺少必需字段: {col}"

    def test_notes_has_data(self):
        """测试笔记表有数据"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, "笔记表没有数据"

    def test_database_integrity(self):
        """测试数据库完整性"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        assert result == 'ok', f"数据库完整性检查失败: {result}"
