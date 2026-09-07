# -*- coding: utf-8 -*-
"""agent_memory / agent_capability 测试共享 fixture。

使用临时 SQLite DB 文件，真实操作（不 mock）。
创建测试所需的表结构（与生产 monitor.db 对齐的子集）。
"""
import os
import sys
import json
import sqlite3
import tempfile
import pytest

# 确保项目根目录在 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 测试所需的表结构 DDL（与生产表对齐的子集）
TEST_TABLES_DDL = """
CREATE TABLE IF NOT EXISTS ai_task (
    task_id TEXT PRIMARY KEY,
    user_input TEXT,
    intent TEXT,
    confidence REAL,
    entities_json TEXT,
    parameters_json TEXT,
    context_json TEXT,
    agent_id TEXT,
    skill_id TEXT,
    status TEXT,
    risk_level TEXT,
    risk_reason TEXT,
    permission_required TEXT,
    permission_result TEXT,
    approval_token TEXT,
    approved_by TEXT,
    approved_at TEXT,
    result_json TEXT,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TEXT,
    updated_at TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_by TEXT,
    permanent_deny INTEGER DEFAULT 0,
    admin_required INTEGER DEFAULT 0,
    human_approval_required INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ai_task_step (
    step_id TEXT PRIMARY KEY,
    task_id TEXT,
    phase TEXT,
    status TEXT,
    detail TEXT,
    agent_id TEXT,
    skill_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS ai_task_evidence (
    evidence_id TEXT PRIMARY KEY,
    task_id TEXT,
    step_id TEXT,
    evidence_type TEXT,
    content TEXT,
    source TEXT,
    authenticity_score REAL,
    created_at TEXT,
    previous_hash TEXT,
    current_hash TEXT
);

CREATE TABLE IF NOT EXISTS ai_task_trace (
    trace_id TEXT,
    task_id TEXT,
    span TEXT,
    parent_span TEXT,
    detail TEXT,
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS skills_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT UNIQUE,
    name TEXT,
    description TEXT,
    product TEXT,
    domain TEXT,
    status TEXT,
    config_json TEXT,
    version TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS skill_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,
    skill_id TEXT NOT NULL,
    user_id INTEGER,
    domain TEXT DEFAULT 'SYSTEM',
    product TEXT DEFAULT 'SYSTEM',
    task TEXT,
    action_type TEXT DEFAULT 'ANALYZE',
    input_json TEXT,
    output_json TEXT,
    status TEXT DEFAULT 'pending',
    error TEXT,
    evidence_json TEXT,
    evaluation_json TEXT,
    permission_json TEXT,
    firewall_json TEXT,
    effect_fence_json TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS feedback_keywords (
    keyword TEXT PRIMARY KEY,
    source TEXT,
    score REAL,
    enabled INTEGER DEFAULT 1,
    first_seen TEXT,
    last_seen TEXT,
    used_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS note_review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT,
    old_relevance TEXT,
    new_relevance TEXT,
    old_sentiment TEXT,
    new_sentiment TEXT,
    old_risk TEXT,
    new_risk TEXT,
    reason TEXT,
    provider TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS intelligence_assets (
    asset_id TEXT PRIMARY KEY,
    title TEXT,
    sub_library TEXT,
    source_origin TEXT,
    source_path TEXT,
    library_path TEXT,
    product TEXT,
    domain TEXT,
    evidence_level TEXT,
    knowledge_status TEXT,
    tags TEXT,
    summary TEXT,
    landing_status TEXT,
    admission_status TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS rule_version_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT,
    rule_type TEXT,
    description TEXT,
    subject_words_count INTEGER,
    exclude_words_count INTEGER,
    subject_words_hash TEXT,
    exclude_words_hash TEXT,
    applied_at TEXT,
    applied_by TEXT,
    is_active INTEGER DEFAULT 0,
    changelog TEXT
);

CREATE TABLE IF NOT EXISTS ai_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT,
    model TEXT,
    prompt_version TEXT,
    input_hash TEXT,
    output TEXT,
    confidence REAL,
    rule_result TEXT,
    final_result TEXT,
    human_correction TEXT,
    latency_ms INTEGER,
    token_usage INTEGER,
    failure_reason TEXT,
    success INTEGER DEFAULT 0,
    created_at TEXT,
    input_text TEXT,
    final_decision TEXT,
    task_id TEXT,
    trace_id TEXT,
    timestamp TEXT,
    domain_id TEXT,
    product_id TEXT,
    output_hash TEXT,
    target_type TEXT,
    target_id TEXT,
    model_version TEXT,
    system_result TEXT,
    accepted TEXT
);

CREATE TABLE IF NOT EXISTS agent_learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT UNIQUE NOT NULL,
    learning_type TEXT NOT NULL DEFAULT 'feedback',
    source TEXT NOT NULL DEFAULT 'agent_runtime',
    content_json TEXT,
    confidence REAL DEFAULT 0.5,
    lifecycle_stage TEXT DEFAULT 'raw',
    related_task_id TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    promoted_at TEXT,
    promoted_by TEXT,
    metadata_json TEXT
);
"""


@pytest.fixture
def temp_db():
    """创建临时测试数据库，包含所有测试所需表。"""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="zbc_agent_test_")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(TEST_TABLES_DDL)
    conn.commit()
    conn.close()
    yield path
    # 清理
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def seeded_db(temp_db):
    """预置测试数据的临时数据库。"""
    conn = sqlite3.connect(temp_db)
    # 预置 ai_task
    conn.execute(
        """INSERT INTO ai_task (task_id, user_input, intent, status, result_json, created_at)
           VALUES (?,?,?,?,?,?)""",
        ("task_001", "分析今日舆情", "analysis", "completed",
         json.dumps({"summary": "test result"}), "2026-09-07T10:00:00"),
    )
    conn.execute(
        """INSERT INTO ai_task (task_id, user_input, intent, status, created_at)
           VALUES (?,?,?,?,?)""",
        ("task_002", "查询风险事件", "risk_query", "failed",
         "2026-09-07T11:00:00"),
    )
    # 预置 ai_task_step
    conn.execute(
        """INSERT INTO ai_task_step (step_id, task_id, phase, status, detail, started_at)
           VALUES (?,?,?,?,?,?)""",
        ("step_001", "task_001", "parse", "completed", "parsed input", "2026-09-07T10:00:01"),
    )
    # 预置 ai_task_evidence
    conn.execute(
        """INSERT INTO ai_task_evidence
           (evidence_id, task_id, step_id, evidence_type, content, source, authenticity_score, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("ev_001", "task_001", "step_001", "result",
         json.dumps({"key": "value", "trend": "up"}), "ai_engine", 0.9,
         "2026-09-07T10:00:02"),
    )
    conn.execute(
        """INSERT INTO ai_task_evidence
           (evidence_id, task_id, step_id, evidence_type, content, source, authenticity_score, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("ev_002", "task_002", "step_002", "error",
         json.dumps({"error": "timeout"}), "ai_engine", 0.2,
         "2026-09-07T11:00:02"),
    )
    # 预置 skills_registry
    conn.execute(
        """INSERT INTO skills_registry (skill_id, name, description, status, version, config_json)
           VALUES (?,?,?,?,?,?)""",
        ("test_skill_a", "测试技能A", "用于测试的技能A", "enabled", "1.0.0",
         json.dumps({"category": "test", "tags": ["test", "a"]})),
    )
    conn.execute(
        """INSERT INTO skills_registry (skill_id, name, description, status, version, config_json)
           VALUES (?,?,?,?,?,?)""",
        ("collector_xhs", "小红书采集", "小红书数据采集", "disabled", "1.0",
         json.dumps({"category": "collection"})),
    )
    # 预置 skill_executions
    conn.execute(
        """INSERT INTO skill_executions
           (execution_id, skill_id, status, action_type, duration_ms, created_at)
           VALUES (?,?,?,?,?,?)""",
        ("exec_001", "test_skill_a", "completed", "ANALYZE", 150, "2026-09-07T10:00:00"),
    )
    conn.execute(
        """INSERT INTO skill_executions
           (execution_id, skill_id, status, action_type, duration_ms, created_at)
           VALUES (?,?,?,?,?,?)""",
        ("exec_002", "test_skill_a", "failed", "ANALYZE", 200, "2026-09-07T10:01:00"),
    )
    # 预置 feedback_keywords
    conn.execute(
        """INSERT INTO feedback_keywords (keyword, source, score, enabled, used_count)
           VALUES (?,?,?,?,?)""",
        ("排队", "user", 0.9, 1, 5),
    )
    conn.execute(
        """INSERT INTO feedback_keywords (keyword, source, score, enabled, used_count)
           VALUES (?,?,?,?,?)""",
        ("服务态度", "user", 0.7, 1, 3),
    )
    # 预置 note_review_history
    conn.execute(
        """INSERT INTO note_review_history
           (note_id, old_relevance, new_relevance, old_sentiment, new_sentiment,
            old_risk, new_risk, reason, provider, reviewed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        ("note_001", "relevant", "relevant", "negative", "neutral",
         "high", "low", "误判风险等级", "ai_engine", "2026-09-07T09:00:00"),
    )
    # 预置 intelligence_assets
    conn.execute(
        """INSERT INTO intelligence_assets
           (asset_id, title, sub_library, tags, summary, evidence_level, knowledge_status, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("asset_001", "太古汇品牌营销策略", "brand_knowledge",
         "品牌,营销,策略", "广州太古汇的品牌营销策略分析", "high", "verified",
         "2026-09-01T00:00:00"),
    )
    conn.execute(
        """INSERT INTO intelligence_assets
           (asset_id, title, sub_library, tags, summary, evidence_level, knowledge_status, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("asset_002", "舆情危机处理案例", "case_library",
         "危机,公关,案例", "典型舆情危机处理案例汇总", "medium", "pending",
         "2026-09-02T00:00:00"),
    )
    # 预置 rule_version_registry
    conn.execute(
        """INSERT INTO rule_version_registry
           (version, rule_type, subject_words_count, exclude_words_count, is_active, applied_at)
           VALUES (?,?,?,?,?,?)""",
        ("v1.0", "subject_words", 50, 20, 1, "2026-09-01T00:00:00"),
    )
    # 预置 ai_call_logs
    conn.execute(
        """INSERT INTO ai_call_logs
           (provider, model, success, latency_ms, human_correction, created_at, task_id)
           VALUES (?,?,?,?,?,?,?)""",
        ("zhipu", "glm-4.5-air", 1, 1200, None, "2026-09-07T10:00:00", "task_001"),
    )
    conn.execute(
        """INSERT INTO ai_call_logs
           (provider, model, success, latency_ms, human_correction, failure_reason, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        ("zhipu", "glm-4.5-air", 0, 5000, None, "timeout", "2026-09-07T11:00:00"),
    )
    conn.commit()
    conn.close()
    return temp_db
