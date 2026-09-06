# -*- coding: utf-8 -*-
"""G2 单测：ai_call_logger.py 审计字段补全

验证：
1. ALTER TABLE 幂等（重复执行不报错）
2. 新字段（target_type/target_id/model_version/system_result/accepted）可写入
3. 旧调用（不传新参数）兼容，新字段为空
"""
import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

import ai_call_logger as acl


@pytest.fixture
def temp_db():
    """使用临时数据库，不污染生产库。"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    old_path = acl.DB_PATH
    acl.DB_PATH = path
    # 重置连接缓存
    acl.init_db()
    yield path
    acl.DB_PATH = old_path
    os.unlink(path)


class TestG2SchemaMigration:
    """G2: ALTER TABLE 幂等与新字段存在"""

    def test_new_columns_exist(self, temp_db):
        """G2 新字段应存在于表结构中。"""
        conn = sqlite3.connect(temp_db)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ai_call_logs)").fetchall()]
        conn.close()
        for col in ("target_type", "target_id", "model_version", "system_result", "accepted"):
            assert col in cols, f"缺失字段: {col}"

    def test_migration_idempotent(self, temp_db):
        """重复执行迁移（init_db）不报错，幂等。"""
        assert acl.init_db() is True
        assert acl.init_db() is True  # 第二次不报错
        # 验证字段仍然存在
        conn = sqlite3.connect(temp_db)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ai_call_logs)").fetchall()]
        conn.close()
        assert "target_type" in cols

    def test_existing_data_preserved(self, temp_db):
        """迁移不破坏历史数据。"""
        # 先插入一条旧格式数据
        rid = acl.log_call(provider='old', model='m1', output='old data', success=True)
        assert rid is not None
        # 再次迁移
        acl.init_db()
        # 验证数据仍在
        conn = sqlite3.connect(temp_db)
        row = conn.execute("SELECT provider, output FROM ai_call_logs WHERE id=?", (rid,)).fetchone()
        conn.close()
        assert row[0] == 'old'
        assert row[1] == 'old data'


class TestG2NewFields:
    """G2: 新字段可写入与查询"""

    def test_new_fields_written(self, temp_db):
        """传入新参数时，应正确写入数据库。"""
        rid = acl.log_call(
            provider='test', model='glm-4.5', output='result',
            target_type='note', target_id='note_001',
            model_version='glm-4.5-air', system_result='{"risk":"low"}',
            accepted='yes', success=True,
        )
        assert rid is not None
        rows = acl.query_calls(provider='test', limit=1)
        assert len(rows) == 1
        r = rows[0]
        assert r['target_type'] == 'note'
        assert r['target_id'] == 'note_001'
        assert r['model_version'] == 'glm-4.5-air'
        assert r['system_result'] == '{"risk":"low"}'
        assert r['accepted'] == 'yes'

    def test_old_call_compatible(self, temp_db):
        """旧调用（不传新参数）兼容，新字段应为空串。"""
        rid = acl.log_call(provider='legacy', model='m1', output='legacy', success=True)
        assert rid is not None
        rows = acl.query_calls(provider='legacy', limit=1)
        assert len(rows) == 1
        r = rows[0]
        assert r['target_type'] == ''
        assert r['target_id'] == ''
        assert r['model_version'] == ''
        assert r['system_result'] == ''
        assert r['accepted'] == ''

    def test_none_params_become_empty(self, temp_db):
        """新参数传 None 时应转为空串（不破坏旧调用）。"""
        rid = acl.log_call(
            provider='none_test', model='m1', output='x',
            target_type=None, target_id=None, model_version=None,
            system_result=None, accepted=None, success=True,
        )
        assert rid is not None
        rows = acl.query_calls(provider='none_test', limit=1)
        r = rows[0]
        assert r['target_type'] == ''
        assert r['accepted'] == ''

    def test_query_by_target_type(self, temp_db):
        """支持按 target_type 查询。"""
        acl.log_call(provider='t1', target_type='note', target_id='n1', success=True)
        acl.log_call(provider='t2', target_type='event', target_id='e1', success=True)
        rows = acl.query_calls(target_type='note', limit=10)
        assert len(rows) >= 1
        assert all(r['target_type'] == 'note' for r in rows)


class TestG2BypassSafety:
    """G2: 旁路写入不阻断主链路"""

    def test_log_call_never_raises(self, temp_db):
        """log_call 任何异常都应被捕获，不抛出。"""
        # 即使传入异常参数也不应抛出
        try:
            rid = acl.log_call(provider='x', model='y', output=object(), success=True)
            assert rid is not None or rid is None  # 两种都可以
        except Exception as e:
            pytest.fail(f"log_call 不应抛出异常: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
