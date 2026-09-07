# -*- coding: utf-8 -*-
"""迁移脚本：创建 agent_learning_records 表（Learning Memory 持久化层）。

⚠️ 本脚本仅定义迁移，不自动执行。
执行方式：python migrations/011_create_agent_learning_records.py
执行前请确认：
  1. 已备份 data/monitor.db
  2. 已确认不影响现有表结构
  3. 仅在测试环境验证后再应用到生产

表设计：
  - record_id: 学习记录唯一ID
  - learning_type: feedback/correction/outcome/pattern/rule_suggestion
  - source: user/human/agent/system
  - content_json: 学习内容（JSON）
  - confidence: 置信度 0-1
  - lifecycle_stage: raw/reviewed/validated/promoted/archived
  - related_task_id: 关联任务ID
  - created_at: 创建时间
  - promoted_at: 提升为规则的时间
  - promoted_by: 提升操作人

与 OSAI learning_record_contract.py 的 LearningRecord 结构对齐。
"""
from __future__ import annotations

import os
import sys
import sqlite3
from datetime import datetime, timezone

# 迁移元数据
MIGRATION_ID = "011"
MIGRATION_NAME = "create_agent_learning_records"
MIGRATION_VERSION = "1.0.0"
MIGRATION_DATE = "2026-09-07"
MIGRATION_AUTHOR = "agent_runtime"

CREATE_TABLE_SQL = """
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

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_agent_learning_type
    ON agent_learning_records(learning_type);
CREATE INDEX IF NOT EXISTS idx_agent_learning_stage
    ON agent_learning_records(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_agent_learning_task
    ON agent_learning_records(related_task_id);
CREATE INDEX IF NOT EXISTS idx_agent_learning_created
    ON agent_learning_records(created_at);
"""

# 迁移说明（写入 migration_log）
MIGRATION_DESCRIPTION = """
Agent Runtime Learning Memory 持久化表。
存储用户反馈、AI输出修正、规则建议等学习记录。
学习结果不直接成为 Production Truth，需经过 lifecycle_stage 推进（raw→reviewed→validated→promoted）。
复用 feedback_keywords 表作为反馈关键词源，本表存储结构化学习记录。
"""


def upgrade(db_path: str) -> bool:
    """执行迁移：创建表和索引。"""
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.executescript(CREATE_INDEX_SQL)

        # 记录迁移日志（如果有 migration_log 表）
        try:
            conn.execute(
                """INSERT OR IGNORE INTO migration_log
                   (migration_id, name, version, applied_at, applied_by, description)
                   VALUES (?,?,?,?,?,?)""",
                (
                    f"{MIGRATION_ID}_{MIGRATION_NAME}",
                    MIGRATION_NAME,
                    MIGRATION_VERSION,
                    datetime.now(timezone.utc).isoformat(),
                    MIGRATION_AUTHOR,
                    MIGRATION_DESCRIPTION.strip(),
                ),
            )
        except Exception:
            pass  # migration_log 表可能不存在

        conn.commit()
        print(f"[OK] Migration {MIGRATION_ID}_{MIGRATION_NAME} applied successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def downgrade(db_path: str) -> bool:
    """回滚迁移：删除表（危险操作，仅用于测试环境）。"""
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS agent_learning_records")
        conn.commit()
        print(f"[OK] Migration {MIGRATION_ID}_{MIGRATION_NAME} rolled back")
        return True
    except Exception as e:
        print(f"[ERROR] Rollback failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify(db_path: str) -> bool:
    """验证迁移是否已应用。"""
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_learning_records'"
        ).fetchone()
        exists = row is not None
        if exists:
            cols = conn.execute("PRAGMA table_info(agent_learning_records)").fetchall()
            print(f"[OK] Table exists with {len(cols)} columns")
        else:
            print("[INFO] Table does not exist")
        return exists
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration: create agent_learning_records table")
    parser.add_argument("action", choices=["upgrade", "downgrade", "verify"],
                        help="Migration action")
    parser.add_argument("--db", default="data/monitor.db",
                        help="Path to SQLite database")
    args = parser.parse_args()

    db_path = args.db
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), db_path)

    if args.action == "upgrade":
        success = upgrade(db_path)
        sys.exit(0 if success else 1)
    elif args.action == "downgrade":
        success = downgrade(db_path)
        sys.exit(0 if success else 1)
    else:
        verify(db_path)
