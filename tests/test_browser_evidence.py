# -*- coding: utf-8 -*-
"""
ZBC AI Browser Runtime — Evidence Tests
测试 Evidence 记录完整 + 脱敏验证
"""
import os
import sys
import json
import tempfile
import unittest
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_browser_runtime import (
    BrowserEvidenceStore,
    BrowserEvidenceRecord,
    init_browser_evidence_db,
    BROWSER_EVIDENCE_SCHEMA,
    sanitize_sensitive,
)


class TestEvidenceStore(unittest.TestCase):
    """测试 Evidence 存储层。"""

    def setUp(self):
        """使用临时数据库，不影响生产库。"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_evidence.db")
        self.store = BrowserEvidenceStore(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_init_creates_table(self):
        """初始化应创建 browser_evidence 表。"""
        conn = sqlite3.connect(self.db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='browser_evidence'"
        ).fetchall()
        conn.close()
        self.assertEqual(len(tables), 1)

    def test_record_evidence(self):
        """测试写入 Evidence 记录。"""
        record = BrowserEvidenceRecord(
            action="click",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="test_session",
            target="submit button",
            selector="#submit",
            before_state='{"url":"http://example.com"}',
            after_state='{"url":"http://example.com/success"}',
            before_state_hash="abc123",
            after_state_hash="def456",
            verification='{"passed":true}',
            expected_state='{"text_present":"success"}',
            actual_state='{"text_present":"success"}',
            task_id="task_001",
            run_id="run_001",
            step_id="step_001",
            agent_id="agent_001",
            skill_id="skill_001",
            risk_level="medium",
        )
        row_id = self.store.record(record)
        self.assertGreater(row_id, 0)

    def test_query_evidence(self):
        """测试查询 Evidence。"""
        for i in range(5):
            record = BrowserEvidenceRecord(
                action="click" if i % 2 == 0 else "input",
                timestamp=f"2026-09-07T10:00:0{i}",
                result="PASS" if i < 3 else "FAIL",
                session_id="test_session",
                target=f"button_{i}",
            )
            self.store.record(record)

        # 查询全部
        all_records = self.store.query(session_id="test_session", limit=10)
        self.assertEqual(len(all_records), 5)

        # 按 result 筛选
        pass_records = self.store.query(session_id="test_session", result="PASS", limit=10)
        self.assertEqual(len(pass_records), 3)

        # 按 action 筛选
        click_records = self.store.query(session_id="test_session", action="click", limit=10)
        self.assertEqual(len(click_records), 3)

    def test_get_stats(self):
        """测试统计。"""
        for i in range(4):
            record = BrowserEvidenceRecord(
                action="click",
                timestamp=f"2026-09-07T10:00:0{i}",
                result="PASS" if i < 3 else "FAIL",
                session_id="stats_test",
            )
            self.store.record(record)

        stats = self.store.get_stats(session_id="stats_test")
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["by_result"]["PASS"], 3)
        self.assertEqual(stats["by_result"]["FAIL"], 1)
        self.assertIn("75.0%", stats["pass_rate"])

    def test_evidence_fields_complete(self):
        """测试 Evidence 记录包含所有必要字段。"""
        record = BrowserEvidenceRecord(
            action="navigate",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="field_test",
            target="http://example.com",
            selector="",
            before_state="before",
            after_state="after",
            before_state_hash="h1",
            after_state_hash="h2",
            evidence_path="/path/to/screenshot.png",
            dom_snapshot="<div></div>",
            console_errors="error1,error2",
            verification='{"passed":true}',
            expected_state='{"url_contains":"example"}',
            actual_state='{"url":"http://example.com"}',
            error=None,
            retry_count=0,
            recovery_strategy="",
            risk_level="low",
            task_id="t1",
            run_id="r1",
            step_id="s1",
            agent_id="a1",
            skill_id="k1",
        )
        row_id = self.store.record(record)
        records = self.store.query(session_id="field_test")
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["action"], "navigate")
        self.assertEqual(r["result"], "PASS")
        self.assertEqual(r["session_id"], "field_test")
        self.assertEqual(r["before_state_hash"], "h1")
        self.assertEqual(r["after_state_hash"], "h2")
        self.assertEqual(r["evidence_path"], "/path/to/screenshot.png")
        self.assertEqual(r["retry_count"], 0)
        self.assertEqual(r["risk_level"], "low")
        self.assertEqual(r["task_id"], "t1")
        self.assertEqual(r["agent_id"], "a1")


class TestEvidenceSanitization(unittest.TestCase):
    """测试 Evidence 中的敏感信息脱敏。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_sanitize.db")
        self.store = BrowserEvidenceStore(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_cookie_in_target_sanitized(self):
        """target 中的 Cookie 应被脱敏。"""
        record = BrowserEvidenceRecord(
            action="click",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="sanitize_test",
            target="点击按钮 cookie=session_abc123def456",
        )
        self.store.record(record)
        records = self.store.query(session_id="sanitize_test")
        self.assertNotIn("abc123def456", records[0]["target"])
        self.assertIn("[REDACTED]", records[0]["target"])

    def test_token_in_before_state_sanitized(self):
        """before_state 中的 Token 应被脱敏。"""
        record = BrowserEvidenceRecord(
            action="navigate",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="sanitize_test2",
            before_state='{"url":"http://example.com","token":"xyz789secret"}',
            after_state='{"url":"http://example.com/page"}',
        )
        self.store.record(record)
        records = self.store.query(session_id="sanitize_test2")
        self.assertNotIn("xyz789secret", records[0]["before_state"])

    def test_password_in_error_sanitized(self):
        """error 中的密码应被脱敏。"""
        record = BrowserEvidenceRecord(
            action="input",
            timestamp="2026-09-07T10:00:00",
            result="FAIL",
            session_id="sanitize_test3",
            error="Failed to input password=mySecretPass123 into field",
        )
        self.store.record(record)
        records = self.store.query(session_id="sanitize_test3")
        self.assertNotIn("mySecretPass123", records[0]["error"])

    def test_jwt_in_verification_sanitized(self):
        """verification 中的 JWT 应被脱敏。"""
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        record = BrowserEvidenceRecord(
            action="click",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="sanitize_test4",
            verification=f'{{"passed":true,"token":"{jwt}"}}',
        )
        self.store.record(record)
        records = self.store.query(session_id="sanitize_test4")
        self.assertNotIn("eyJhbGci", records[0]["verification"])
        self.assertIn("[REDACTED]", records[0]["verification"])

    def test_phone_in_dom_snapshot_sanitized(self):
        """dom_snapshot 中的手机号应被脱敏。"""
        record = BrowserEvidenceRecord(
            action="observe",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="sanitize_test5",
            dom_snapshot='<div>联系电话: 13812345678</div>',
        )
        self.store.record(record)
        records = self.store.query(session_id="sanitize_test5")
        self.assertIn("[PHONE_REDACTED]", records[0]["dom_snapshot"])

    def test_no_cookie_token_in_evidence(self):
        """综合测试：Evidence 中不应包含任何敏感凭证明文。"""
        sensitive_data = {
            "cookie": "session=abc123",
            "token": "Bearer xyz789",
            "password": "secret123",
            "jwt": "eyJhbGciOiJIUzI1NiJ9.payload.sig",
            "phone": "13912345678",
        }
        record = BrowserEvidenceRecord(
            action="click",
            timestamp="2026-09-07T10:00:00",
            result="PASS",
            session_id="comprehensive_sanitize",
            target=json.dumps(sensitive_data),
            before_state=json.dumps(sensitive_data),
            after_state=json.dumps(sensitive_data),
            dom_snapshot=json.dumps(sensitive_data),
            console_errors=json.dumps(sensitive_data),
            verification=json.dumps(sensitive_data),
            error=json.dumps(sensitive_data),
            recovery_strategy=json.dumps(sensitive_data),
        )
        self.store.record(record)
        records = self.store.query(session_id="comprehensive_sanitize")
        r = records[0]
        for field in ["target", "before_state", "after_state", "dom_snapshot",
                       "console_errors", "verification", "error", "recovery_strategy"]:
            value = str(r[field])
            self.assertNotIn("abc123", value, f"Field {field} contains cookie value")
            self.assertNotIn("xyz789", value, f"Field {field} contains token value")
            self.assertNotIn("secret123", value, f"Field {field} contains password")
            self.assertNotIn("13912345678", value, f"Field {field} contains phone")


class TestEvidenceSchema(unittest.TestCase):
    """测试 Evidence 表结构（向后兼容）。"""

    def test_schema_has_required_fields(self):
        """Schema 应包含所有要求的字段。"""
        required_fields = [
            "task_id", "run_id", "step_id", "agent_id", "skill_id",
            "session_id", "action", "target", "selector", "timestamp",
            "before_state", "after_state", "before_state_hash", "after_state_hash",
            "result", "evidence_path", "dom_snapshot", "console_errors",
            "verification", "expected_state", "actual_state", "error",
            "retry_count", "recovery_strategy", "risk_level",
        ]
        for field in required_fields:
            self.assertIn(field, BROWSER_EVIDENCE_SCHEMA, f"Missing field: {field}")

    def test_create_table_if_not_exists(self):
        """应使用 CREATE TABLE IF NOT EXISTS（向后兼容）。"""
        self.assertIn("CREATE TABLE IF NOT EXISTS", BROWSER_EVIDENCE_SCHEMA)

    def test_indexes_exist(self):
        """应创建必要的索引。"""
        self.assertIn("idx_browser_evidence_session", BROWSER_EVIDENCE_SCHEMA)
        self.assertIn("idx_browser_evidence_task", BROWSER_EVIDENCE_SCHEMA)
        self.assertIn("idx_browser_evidence_result", BROWSER_EVIDENCE_SCHEMA)


if __name__ == "__main__":
    unittest.main()
