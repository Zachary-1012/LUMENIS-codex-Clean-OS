"""
LUMENIS Shared Database - canonical migration engine
统一 schema 演进，避免升级时数据丢失

使用方法：
    python database_migrations.py status          # 查看当前数据库版本
    python database_migrations.py migrate         # 升级到最新版本
    python database_migrations.py rollback        # 回滚到上一个版本
    python database_migrations.py backup          # 备份数据库
    python database_migrations.py info            # 查看数据库信息
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any

# Database path selection is owned by LUMENIS Shared Database.
from lumenis.shared.database import main_db_path
DB_PATH = main_db_path()
BACKUP_DIR = os.path.join(os.path.dirname(DB_PATH), 'backups')

# 当前最新版本
CURRENT_VERSION = 12

# 迁移历史记录
MIGRATION_HISTORY = {
    1: "初始版本 - 基础表结构(notes, daily_reports, collection_logs)",
    2: "添加 web_mentions, events, feedback_keywords 表",
    3: "添加 web_sources, web_runs, event_mentions 表",
    4: "添加 note_review_history, ai_filter_log 表",
    5: "添加 daily_digest, event_insights 表",
    6: "添加 collector_quality_log, note_comments 表",
    7: "添加负面舆情二次确认字段(negative_confirmed, negative_confirmed_at, negative_confirmed_by)",
    8: "添加数据质量字段(publish_datetime, captured_at, detail_fetched_at, comments_fetched_at, data_quality_status, data_quality_score, collector_version)",
    9: "添加 HUMAN_CONTROL_GATE 执行审计表 kos_executions(AI_GENERATED->PENDING_HUMAN_REVIEW->HUMAN_APPROVED->EXECUTING->SUCCESS/FAILED)",
    10: "ZBC Phase15 历史数据治理: notes/canonical_data 添加 rule_version(可空), notes 添加 content_hash/provenance/product_id(可空), 新建 rule_version_registry 与 historical_import_log 表",
    11: "Evidence Chain/Canonical Data bypass: collection_quality_log table, zbc_canonical_data domain_id/product_id, notes domain_id, daily_reports evidence_ids",
    12: "P0-2 性能修复: notes.publish_datetime 添加索引 idx_notes_publish_datetime（趋势API日期范围查询加速）",
}


def get_db_path() -> str:
    """获取数据库路径（call-time canonical authority）。"""
    return main_db_path()


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(main_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_version_table(conn: sqlite3.Connection):
    """初始化版本管理表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_by TEXT DEFAULT 'system'
        )
    """)
    conn.commit()


def get_current_version(conn: sqlite3.Connection) -> int:
    """获取当前数据库版本（int）。

    兼容处理：部分外部模块（如 t4-canonical）会向 schema_version 写入
    字符串版本号（如 '1.0.0'），导致 SQLite MAX() 在混合类型列上返回
    TEXT 而非 INTEGER。此处只取可解析为 int 的版本号求最大值。
    """
    init_version_table(conn)
    cursor = conn.execute("SELECT version FROM schema_version")
    versions = []
    for row in cursor.fetchall():
        v = row[0]
        if isinstance(v, int):
            versions.append(v)
        elif isinstance(v, str):
            try:
                versions.append(int(v.strip()))
            except (ValueError, TypeError):
                pass  # 跳过非数字版本号如 '1.0.0'
    return max(versions) if versions else 0


def set_version(conn: sqlite3.Connection, version: int, description: str = ""):
    """设置数据库版本"""
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
        (version, description, datetime.now().isoformat())
    )
    conn.commit()


def backup_database(backup_name: Optional[str] = None) -> str:
    """备份数据库"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    if not backup_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"monitor_db_v{get_current_version(get_connection())}_{timestamp}.db"
    
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        print(f"   备份大小: {os.path.getsize(backup_path) / 1024 / 1024:.2f} MB")
    else:
        print(f"⚠️  数据库不存在: {DB_PATH}")
    
    return backup_path


def migration_1_to_2(conn: sqlite3.Connection):
    """迁移1→2：添加 web_mentions, events, feedback_keywords 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS web_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            author TEXT,
            published_at TIMESTAMP,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relevance REAL DEFAULT 0,
            sentiment TEXT,
            risk_level TEXT DEFAULT 'low',
            is_taikoo_related INTEGER DEFAULT 0
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE,
            title TEXT,
            description TEXT,
            risk_level TEXT DEFAULT 'low',
            status TEXT DEFAULT 'active',
            first_seen TIMESTAMP,
            last_updated TIMESTAMP,
            note_count INTEGER DEFAULT 0,
            total_engagement INTEGER DEFAULT 0,
            category TEXT,
            tags TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            category TEXT,
            sentiment TEXT,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_relevance ON web_mentions(relevance)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_published ON web_mentions(published_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_risk ON events(risk_level)")


def migration_2_to_3(conn: sqlite3.Connection):
    """迁移2→3：添加 web_sources, web_runs, event_mentions 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS web_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            url TEXT,
            type TEXT,
            enabled INTEGER DEFAULT 1,
            last_run TIMESTAMP,
            config TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS web_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            status TEXT,
            items_found INTEGER DEFAULT 0,
            items_new INTEGER DEFAULT 0,
            error TEXT,
            FOREIGN KEY (source_id) REFERENCES web_sources(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            note_id TEXT,
            mention_type TEXT,
            relevance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, note_id)
        )
    """)


def migration_3_to_4(conn: sqlite3.Connection):
    """迁移3→4：添加 note_review_history, ai_filter_log 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS note_review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT,
            review_type TEXT,
            reviewer TEXT,
            review_result TEXT,
            review_notes TEXT,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_filter_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT,
            filter_type TEXT,
            filter_result TEXT,
            confidence REAL,
            ai_provider TEXT,
            ai_model TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_response TEXT
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_filter_note ON ai_filter_log(note_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_filter_result ON ai_filter_log(filter_result)")


def migration_4_to_5(conn: sqlite3.Connection):
    """迁移4→5：添加 daily_digest, event_insights 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_digest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            digest_date DATE UNIQUE,
            total_notes INTEGER DEFAULT 0,
            negative_notes INTEGER DEFAULT 0,
            positive_notes INTEGER DEFAULT 0,
            neutral_notes INTEGER DEFAULT 0,
            high_risk_notes INTEGER DEFAULT 0,
            total_engagement INTEGER DEFAULT 0,
            top_topics TEXT,
            top_events TEXT,
            summary TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            insight_type TEXT,
            insight_text TEXT,
            ai_provider TEXT,
            confidence REAL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_digest_date ON daily_digest(digest_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_insights_event ON event_insights(event_id)")


def migration_5_to_6(conn: sqlite3.Connection):
    """迁移5→6：添加 collector_quality_log, note_comments 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collector_quality_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT,
            collector_version TEXT,
            detail_fetched INTEGER DEFAULT 0,
            comments_fetched INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            data_quality_status TEXT DEFAULT 'unknown',
            data_quality_score REAL DEFAULT 0,
            error_message TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS note_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT,
            comment_id TEXT UNIQUE,
            author_id TEXT,
            author_name TEXT,
            content TEXT,
            likes INTEGER DEFAULT 0,
            published_at TIMESTAMP,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sentiment TEXT,
            parent_comment_id TEXT
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_collector_quality_note ON collector_quality_log(note_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_comments_note ON note_comments(note_id)")


def migration_6_to_7(conn: sqlite3.Connection):
    """迁移6→7：添加负面舆情二次确认字段"""
    # 检查字段是否已存在
    cursor = conn.execute("PRAGMA table_info(notes)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'negative_confirmed' not in columns:
        conn.execute("ALTER TABLE notes ADD COLUMN negative_confirmed INTEGER DEFAULT 0")
    if 'negative_confirmed_at' not in columns:
        conn.execute("ALTER TABLE notes ADD COLUMN negative_confirmed_at TIMESTAMP")
    if 'negative_confirmed_by' not in columns:
        conn.execute("ALTER TABLE notes ADD COLUMN negative_confirmed_by TEXT")


def migration_7_to_8(conn: sqlite3.Connection):
    """迁移7→8：添加数据质量字段"""
    cursor = conn.execute("PRAGMA table_info(notes)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    new_columns = [
        ('publish_datetime', 'TIMESTAMP'),
        ('captured_at', 'TIMESTAMP'),
        ('detail_fetched_at', 'TIMESTAMP'),
        ('comments_fetched_at', 'TIMESTAMP'),
        ('comments_collected', 'INTEGER DEFAULT 0'),
        ('data_quality_status', "TEXT DEFAULT 'unknown'"),
        ('data_quality_score', 'REAL DEFAULT 0'),
        ('collector_version', 'TEXT'),
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            conn.execute(f"ALTER TABLE notes ADD COLUMN {col_name} {col_type}")


def migration_8_to_9(conn):
    """迁移8→9：新建 HUMAN_CONTROL_GATE 执行审计表（AI_GENERATED->PENDING_HUMAN_REVIEW->HUMAN_APPROVED->EXECUTING->SUCCESS/FAILED）。
    敏感动作（外联/邮件/留资/合作/投流/预算/发布等）执行必须经人工确认并留审计。
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kos_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE,
            action_type TEXT NOT NULL,
            target_author_id TEXT DEFAULT '',
            target_brand TEXT DEFAULT '',
            payload TEXT DEFAULT '{}',
            status TEXT DEFAULT 'AI_GENERATED',
            actor TEXT DEFAULT '',
            created_at TEXT,
            approved_at TEXT,
            executed_at TEXT,
            result TEXT DEFAULT '',
            evidence_ref TEXT DEFAULT '',
            failure_reason TEXT DEFAULT '',
            version TEXT DEFAULT 'v1'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kos_exec_status ON kos_executions(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kos_exec_author ON kos_executions(target_author_id)")


def migration_9_to_10(conn):
    """迁移9→10：ZBC Phase15 历史数据治理。
    - notes/canonical_data 添加 rule_version（可空，不修改现有数据）
    - notes 添加 content_hash/provenance/product_id（可空，历史数据治理字段）
    - 新建 rule_version_registry 表（规则版本注册）
    - 新建 historical_import_log 表（历史导入审计日志）
    所有 ADD COLUMN 均无 DEFAULT，现有行保持 NULL，不被新规则静默改写。
    """
    # --- notes 表：添加历史数据治理字段（可空，不修改现有数据）---
    cursor = conn.execute("PRAGMA table_info(notes)")
    note_cols = {row['name'] for row in cursor.fetchall()}

    note_new_columns = [
        ('rule_version', 'TEXT'),          # 规则版本追踪，历史数据保持原始版本
        ('content_hash', 'TEXT'),          # SHA256 内容哈希，用于去重
        ('provenance', 'TEXT'),            # 来源溯源 source_table:source_id
        ('product_id', 'TEXT'),            # 产品标识 CTH/ZBC，namespace 隔离
    ]
    for col_name, col_type in note_new_columns:
        if col_name not in note_cols:
            conn.execute(f"ALTER TABLE notes ADD COLUMN {col_name} {col_type}")

    # --- canonical_data 表：添加 rule_version（可空）---
    cursor = conn.execute("PRAGMA table_info(canonical_data)")
    cd_cols = {row['name'] for row in cursor.fetchall()}
    if 'rule_version' not in cd_cols:
        conn.execute("ALTER TABLE canonical_data ADD COLUMN rule_version TEXT")

    # --- rule_version_registry：规则版本注册表 ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rule_version_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            rule_type TEXT NOT NULL DEFAULT 'subject',
            description TEXT DEFAULT '',
            subject_words_count INTEGER DEFAULT 0,
            exclude_words_count INTEGER DEFAULT 0,
            subject_words_hash TEXT DEFAULT '',
            exclude_words_hash TEXT DEFAULT '',
            applied_at TEXT DEFAULT '',
            applied_by TEXT DEFAULT 'system',
            is_active INTEGER DEFAULT 0,
            changelog TEXT DEFAULT '{}'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rvr_version ON rule_version_registry(version)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rvr_active ON rule_version_registry(is_active)")

    # --- historical_import_log：历史数据导入审计日志 ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historical_import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_table TEXT NOT NULL,
            target_id TEXT DEFAULT '',
            content_hash TEXT DEFAULT '',
            rule_version TEXT DEFAULT '',
            product_id TEXT DEFAULT 'CTH',
            subject_hit INTEGER DEFAULT 0,
            subject_reason TEXT DEFAULT '',
            publish_datetime TEXT DEFAULT '',
            captured_at TEXT DEFAULT '',
            source_platform TEXT DEFAULT '',
            import_status TEXT DEFAULT 'imported',
            dedup_hit INTEGER DEFAULT 0,
            dedup_of TEXT DEFAULT '',
            imported_at TEXT DEFAULT '',
            imported_by TEXT DEFAULT 'historical_importer',
            notes TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hil_batch ON historical_import_log(import_batch_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hil_hash ON historical_import_log(content_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hil_product ON historical_import_log(product_id)")


def migration_10_to_11(conn):
    """Migration 10->11: Evidence Chain / Canonical Data bypass + Collector Health + dual-domain.

    P1-2: Create collection_quality_log table (5-step quality gate log).
    P1-3: zbc_canonical_data add domain_id/product_id; notes add domain_id (already has product_id).
    P1-4: daily_reports add evidence_ids TEXT (JSON array, nullable, no logic change).
    All ADD COLUMN have DEFAULT, backward compatible.
    """
    # P1-2: collection_quality_log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collection_quality_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT DEFAULT '',
            step TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT DEFAULT '',
            source_platform TEXT DEFAULT '',
            content_hash TEXT DEFAULT '',
            canonical_id TEXT DEFAULT '',
            raw_ref TEXT DEFAULT '',
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_log_step ON collection_quality_log(step, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_log_hash ON collection_quality_log(content_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_log_run ON collection_quality_log(run_id)")

    # P1-3: zbc_canonical_data dual-domain columns
    zbc_cd_cols = {row[1] for row in conn.execute("PRAGMA table_info(zbc_canonical_data)").fetchall()}
    if 'domain_id' not in zbc_cd_cols:
        conn.execute("ALTER TABLE zbc_canonical_data ADD COLUMN domain_id TEXT NOT NULL DEFAULT 'cth'")
    if 'product_id' not in zbc_cd_cols:
        conn.execute("ALTER TABLE zbc_canonical_data ADD COLUMN product_id TEXT NOT NULL DEFAULT 'CTH'")

    # P1-3: notes add domain_id (already has product_id from migration 9->10)
    note_cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if 'domain_id' not in note_cols:
        conn.execute("ALTER TABLE notes ADD COLUMN domain_id TEXT DEFAULT 'cth'")
        conn.execute("UPDATE notes SET domain_id='cth' WHERE product_id='CTH' AND (domain_id IS NULL OR domain_id='')")
        conn.execute("UPDATE notes SET domain_id='zbmp' WHERE product_id='ZBMP' AND (domain_id IS NULL OR domain_id='')")

    # P1-4: daily_reports evidence_ids (reserved, no logic change)
    dr_cols = {row[1] for row in conn.execute("PRAGMA table_info(daily_reports)").fetchall()}
    if 'evidence_ids' not in dr_cols:
        conn.execute("ALTER TABLE daily_reports ADD COLUMN evidence_ids TEXT DEFAULT '[]'")

    # Pre-existing schema drift fix: canonical_data table missing columns defined in CanonicalRecord DDL
    cd_actual = {row[1] for row in conn.execute("PRAGMA table_info(canonical_data)").fetchall()}
    cd_missing = [
        ('localization_score', 'REAL'),
        ('comments_status', "TEXT DEFAULT 'pending'"),
        ('detail_status', "TEXT DEFAULT 'pending'"),
        ('comments_error', "TEXT DEFAULT ''"),
        ('detail_error', "TEXT DEFAULT ''"),
        ('ai_analysis', "TEXT DEFAULT ''"),
    ]
    for _col, _def in cd_missing:
        if _col not in cd_actual:
            conn.execute(f"ALTER TABLE canonical_data ADD COLUMN {_col} {_def}")


def migration_11_to_12(conn):
    """迁移11→12：P0-2 性能修复。
    为 notes.publish_datetime 创建索引，加速趋势API的日期范围 GROUP BY 查询。
    使用 IF NOT EXISTS，幂等安全，不修改现有表结构/数据。
    """
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_publish_datetime ON notes(publish_datetime)")
    conn.commit()


def _migrate_add_publish_datetime_index():
    """独立入口：启动时直接确保 publish_datetime 索引存在（幂等，不触发完整版本迁移/备份）。
    P0-2：趋势API日期范围查询依赖此索引。
    """
    conn = get_connection()
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_publish_datetime ON notes(publish_datetime)")
        conn.commit()
    finally:
        conn.close()


# 迁移函数映射
MIGRATIONS = {
    1: migration_1_to_2,
    2: migration_2_to_3,
    3: migration_3_to_4,
    4: migration_4_to_5,
    5: migration_5_to_6,
    6: migration_6_to_7,
    7: migration_7_to_8,
    8: migration_8_to_9,
    9: migration_9_to_10,
    10: migration_10_to_11,
    11: migration_11_to_12,
}


def migrate(target_version: Optional[int] = None) -> bool:
    """执行数据库迁移"""
    if target_version is None:
        target_version = CURRENT_VERSION
    
    conn = get_connection()
    current_version = get_current_version(conn)
    
    print(f"📊 当前数据库版本: v{current_version}")
    print(f"🎯 目标版本: v{target_version}")
    
    if current_version >= target_version:
        print("✅ 数据库已是最新版本，无需迁移")
        conn.close()
        return True
    
    # 迁移前自动备份
    print("\n📦 迁移前自动备份数据库...")
    backup_database(f"before_migration_v{current_version}_to_v{target_version}.db")
    
    # 执行迁移
    for version in range(current_version, target_version):
        if version in MIGRATIONS:
            print(f"\n🔄 执行迁移 v{version} → v{version + 1}...")
            print(f"   {MIGRATION_HISTORY.get(version + 1, '未知迁移')}")
            
            try:
                MIGRATIONS[version](conn)
                set_version(conn, version + 1, MIGRATION_HISTORY.get(version + 1, ''))
                print(f"   ✅ 迁移成功")
            except Exception as e:
                print(f"   ❌ 迁移失败: {e}")
                print(f"   ⚠️  数据库已回滚到 v{current_version}")
                conn.rollback()
                conn.close()
                return False
        else:
            print(f"⚠️  跳过未知迁移 v{version} → v{version + 1}")
    
    print(f"\n🎉 数据库迁移完成！当前版本: v{get_current_version(conn)}")
    conn.close()
    return True


def rollback() -> bool:
    """回滚到上一个版本（简化版，仅记录，不实际删除表）"""
    conn = get_connection()
    current_version = get_current_version(conn)
    
    if current_version <= 0:
        print("⚠️  数据库已是初始版本，无法回滚")
        conn.close()
        return False
    
    print(f"📊 当前版本: v{current_version}")
    print(f"⏪ 回滚到: v{current_version - 1}")
    
    # 回滚前备份
    backup_database(f"before_rollback_v{current_version}.db")
    
    # 记录回滚（简化版，不实际删除表）
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
        (current_version - 1, f"回滚从 v{current_version}", datetime.now().isoformat())
    )
    conn.commit()
    
    print(f"✅ 已记录回滚到 v{current_version - 1}")
    print("⚠️  注意：表结构未实际删除，仅版本号回退")
    conn.close()
    return True


def show_status():
    """显示数据库状态"""
    conn = get_connection()
    current_version = get_current_version(conn)
    
    print("=" * 60)
    print("📊 数据库状态")
    print("=" * 60)
    print(f"数据库路径: {DB_PATH}")
    print(f"数据库大小: {os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB" if os.path.exists(DB_PATH) else "数据库不存在")
    print(f"当前版本: v{current_version}")
    print(f"最新版本: v{CURRENT_VERSION}")
    print(f"更新状态: {'✅ 已是最新' if current_version >= CURRENT_VERSION else '⚠️  需要更新'}")
    print()
    
    # 表统计
    print("📋 表统计:")
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row['name'] for row in cursor.fetchall()]
    
    for table in tables:
        try:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"  {table}: {count} 条记录")
        except:
            print(f"  {table}: (无法统计)")
    
    print()
    print("📜 迁移历史:")
    cursor = conn.execute("SELECT * FROM schema_version ORDER BY version DESC LIMIT 10")
    for row in cursor.fetchall():
        print(f"  v{row['version']} - {row['description'][:50] if row['description'] else ''} ({row['applied_at']})")
    
    conn.close()


def show_info():
    """显示数据库详细信息"""
    conn = get_connection()
    
    print("=" * 60)
    print("📋 数据库详细信息")
    print("=" * 60)
    
    # 表结构
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row['name'] for row in cursor.fetchall()]
    
    for table in tables:
        print(f"\n📊 {table}:")
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col['name']} ({col['type']}) {'PK' if col['pk'] else ''}")
        
        # 索引
        cursor = conn.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        if indexes:
            print(f"  索引:")
            for idx in indexes:
                print(f"    {idx['name']} {'UNIQUE' if idx['unique'] else ''}")
    
    conn.close()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python database_migrations.py status    # 查看数据库状态")
        print("  python database_migrations.py migrate   # 升级到最新版本")
        print("  python database_migrations.py rollback  # 回滚到上一个版本")
        print("  python database_migrations.py backup    # 备份数据库")
        print("  python database_migrations.py info      # 查看数据库详细信息")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        show_status()
    elif command == 'migrate':
        migrate()
    elif command == 'rollback':
        rollback()
    elif command == 'backup':
        backup_database()
    elif command == 'info':
        show_info()
    else:
        print(f"未知命令: {command}")


if __name__ == '__main__':
    main()
