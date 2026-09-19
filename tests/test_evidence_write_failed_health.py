# -*- coding: utf-8 -*-
"""
P1 复杂度治理 — Evidence 非静默健康机制测试

测试链路：
  evidence 写失败 → audit_logs 有记录 → 健康摘要计数+1 → replay 成功 → 计数清零

使用临时 DB，不触碰生产数据。
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestEvidenceWriteFailedHealth(unittest.TestCase):
    """Evidence 写入失败非静默健康机制测试"""

    def setUp(self):
        """创建临时 DB，复制必要表结构"""
        self.tmpdir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.tmpdir, "test_monitor.db")

        # 创建测试用表
        conn = sqlite3.connect(self.test_db)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS app_evidence_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, project TEXT, product TEXT, feature_id TEXT,
                asset_id TEXT, commit_sha TEXT, version TEXT, env TEXT,
                level TEXT, test_name TEXT, result TEXT, started_at TEXT,
                finished_at TEXT, inputs_json TEXT, outputs_json TEXT,
                expected TEXT, actual TEXT, log_path TEXT, screenshot_path TEXT,
                trace_path TEXT, api_request TEXT, api_response TEXT,
                db_before TEXT, db_after TEXT, root_cause TEXT, resolution TEXT,
                account TEXT, duration_ms INTEGER, notes TEXT,
                metric_name TEXT, metric_value TEXT, topic TEXT, status TEXT,
                content_hash TEXT, subject_scope TEXT, collection_metadata TEXT,
                provider TEXT, authenticity_score REAL, publish_datetime TEXT,
                created_at TEXT, updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS v4_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, username TEXT, action TEXT, resource TEXT,
                resource_id TEXT, detail TEXT, ip TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS runtime_guardian_dlq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dlq_id TEXT, worker_id TEXT, run_id TEXT, task_type TEXT,
                payload TEXT, error TEXT, error_type TEXT,
                attempts INTEGER, max_attempts INTEGER, status TEXT,
                created_at TEXT, updated_at TEXT, last_attempt_at TEXT,
                resolved_at TEXT, domain_id TEXT, product_id TEXT
            );
        """)
        conn.commit()
        conn.close()

        # 保存原 DB_PATH，测试后恢复
        self.original_db_path = os.environ.get("ZBC_DB_PATH")
        os.environ["ZBC_DB_PATH"] = self.test_db

        # 重新导入 evidence_store 以使用新 DB_PATH
        import importlib
        from lumenis.shared.evidence import store as evidence_store
        importlib.reload(evidence_store)
        self.evidence_store = evidence_store

    def tearDown(self):
        """恢复环境"""
        if self.original_db_path:
            os.environ["ZBC_DB_PATH"] = self.original_db_path
        else:
            os.environ.pop("ZBC_DB_PATH", None)
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _count_audit_logs(self, action="evidence_write_failed"):
        conn = sqlite3.connect(self.test_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM v4_audit_logs WHERE action=?", (action,)
        ).fetchone()[0]
        conn.close()
        return count

    def _count_dlq(self, status=None):
        conn = sqlite3.connect(self.test_db)
        if status:
            count = conn.execute(
                "SELECT COUNT(*) FROM runtime_guardian_dlq WHERE task_type='evidence_write' AND status=?",
                (status,)
            ).fetchone()[0]
        else:
            count = conn.execute(
                "SELECT COUNT(*) FROM runtime_guardian_dlq WHERE task_type='evidence_write'"
            ).fetchone()[0]
        conn.close()
        return count

    def test_normal_write_succeeds(self):
        """正常 evidence 写入应成功，返回正整数 id"""
        ev_id = self.evidence_store.record_evidence(
            source="test", feature_id="TEST_NORMAL", result="PASS",
            level="L4", test_name="test_normal"
        )
        self.assertIsInstance(ev_id, int)
        self.assertGreater(ev_id, 0)
        # 不应有失败记录
        self.assertEqual(self._count_audit_logs(), 0)
        self.assertEqual(self._count_dlq(), 0)

    def test_write_failure_records_audit_and_dlq(self):
        """evidence 写入失败时：必须写 audit_logs + DLQ，返回 -1，不抛异常"""
        # 模拟 DB 写入失败：patch _get_conn 返回一个 execute 会抛异常的连接
        real_conn = sqlite3.connect(self.test_db)

        class FailingConn:
            def __init__(self, real):
                self._real = real
            def execute(self, sql, *params):
                if "INSERT INTO app_evidence_records" in sql:
                    raise sqlite3.OperationalError("模拟: database is locked")
                return self._real.execute(sql, *params)
            def commit(self):
                return self._real.commit()
            def rollback(self):
                return self._real.rollback()
            def close(self):
                return self._real.close()

        with patch.object(self.evidence_store, "_get_conn", return_value=FailingConn(real_conn)):
            ev_id = self.evidence_store.record_evidence(
                source="test", feature_id="TEST_FAIL", result="FAIL",
                level="L4", test_name="test_failure", asset_id="asset-001"
            )

        # 失败应返回 -1
        self.assertEqual(ev_id, -1)

        # audit_logs 应有记录
        audit_count = self._count_audit_logs()
        self.assertGreater(audit_count, 0, "evidence_write_failed 必须写入 audit_logs")

        # 验证 audit 记录内容
        conn = sqlite3.connect(self.test_db)
        row = conn.execute(
            "SELECT action, resource, resource_id, detail FROM v4_audit_logs WHERE action='evidence_write_failed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "evidence_write_failed")
        self.assertEqual(row[1], "app_evidence_records")
        detail = json.loads(row[3])
        self.assertIn("error_type", detail)
        self.assertIn("error_message", detail)
        self.assertEqual(detail.get("asset_id"), "asset-001")

        # DLQ 应有 PENDING 记录
        dlq_count = self._count_dlq(status="PENDING")
        self.assertGreater(dlq_count, 0, "失败 evidence 必须进入 DLQ 待重放")

    def test_health_summary_failure_count(self):
        """健康摘要：get_evidence_write_failure_count 应正确返回最近24h失败数"""
        # 初始为 0
        count = self.evidence_store.get_evidence_write_failure_count(24)
        self.assertEqual(count, 0)

        # 手动插入一条失败记录
        conn = sqlite3.connect(self.test_db)
        conn.execute(
            "INSERT INTO v4_audit_logs (user_id, username, action, resource, detail, created_at) "
            "VALUES (0, 'system', 'evidence_write_failed', 'app_evidence_records', '{}', datetime('now', 'localtime'))"
        )
        conn.commit()
        conn.close()

        # 计数应为 1
        count = self.evidence_store.get_evidence_write_failure_count(24)
        self.assertEqual(count, 1)

    def test_replay_failed_evidence_success(self):
        """重放失败 evidence：成功后 DLQ 标记 RESOLVED，可重新写入"""
        # 先插入一条 DLQ 记录（模拟之前失败的 evidence）
        payload = json.dumps({
            "source": "test", "project": "ZBC", "product": "CTH",
            "feature_id": "TEST_REPLAY", "level": "L4", "result": "PASS",
            "test_name": "replay_test", "started_at": "2026-01-01 00:00:00",
            "finished_at": "2026-01-01 00:00:01",
            "created_at": "2026-01-01 00:00:01", "updated_at": "2026-01-01 00:00:01",
        })
        conn = sqlite3.connect(self.test_db)
        conn.execute(
            "INSERT INTO runtime_guardian_dlq "
            "(dlq_id, worker_id, run_id, task_type, payload, error, error_type, "
            " attempts, max_attempts, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("evfail-test001", "evidence_store", "record_evidence", "evidence_write",
             payload, "database is locked", "OperationalError",
             1, 3, "PENDING", "2026-01-01 00:00:00", "2026-01-01 00:00:00")
        )
        conn.commit()
        conn.close()

        # 执行重放
        result = self.evidence_store.replay_failed_evidence(limit=10)

        # 验证重放结果
        self.assertEqual(result["replayed"], 1)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["failed"], 0)

        # DLQ 应标记为 RESOLVED
        resolved_count = self._count_dlq(status="RESOLVED")
        self.assertEqual(resolved_count, 1)

        # evidence 表应有新记录
        conn = sqlite3.connect(self.test_db)
        ev_count = conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='TEST_REPLAY'"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(ev_count, 1)

    def test_replay_clears_failure_backlog(self):
        """重放成功后，剩余失败数应为 0"""
        # 插入 2 条 DLQ 记录
        for i in range(2):
            payload = json.dumps({
                "source": "test", "project": "ZBC", "product": "CTH",
                "feature_id": f"TEST_CLEAR_{i}", "level": "L4", "result": "PASS",
                "test_name": f"clear_test_{i}",
                "started_at": "2026-01-01 00:00:00", "finished_at": "2026-01-01 00:00:01",
                "created_at": "2026-01-01 00:00:01", "updated_at": "2026-01-01 00:00:01",
            })
            conn = sqlite3.connect(self.test_db)
            conn.execute(
                "INSERT INTO runtime_guardian_dlq "
                "(dlq_id, task_type, payload, error, attempts, max_attempts, status, created_at, updated_at) "
                "VALUES (?, 'evidence_write', ?, 'locked', 1, 3, 'PENDING', ?, ?)",
                (f"evfail-clear-{i}", payload, "2026-01-01 00:00:00", "2026-01-01 00:00:00")
            )
            conn.commit()
            conn.close()

        # 重放前剩余 2
        result_before = self.evidence_store.replay_failed_evidence(limit=0)
        # 重放全部
        result = self.evidence_store.replay_failed_evidence(limit=10)
        self.assertEqual(result["succeeded"], 2)
        self.assertEqual(result["remaining"], 0)

    def test_failure_does_not_raise_exception(self):
        """核心原则：evidence 写入失败不中断业务，不抛异常到调用方"""
        # 模拟 _get_conn 完全失败
        def always_fail_conn():
            raise sqlite3.OperationalError("模拟: 完全无法连接 DB")

        with patch.object(self.evidence_store, "_get_conn", side_effect=always_fail_conn):
            # 不应抛异常
            try:
                ev_id = self.evidence_store.record_evidence(
                    source="test", feature_id="TEST_NO_EXCEPTION", result="PASS"
                )
                self.assertEqual(ev_id, -1)
            except Exception as e:
                self.fail(f"record_evidence 不应抛异常: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)