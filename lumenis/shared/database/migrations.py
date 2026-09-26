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
import tempfile
from datetime import datetime
from typing import Optional, List, Dict, Any

# Database path selection is owned by LUMENIS Shared Database.
from .paths import main_db_path
from .business_schema import apply_business_schema
DB_PATH = main_db_path()
BACKUP_DIR = os.path.join(os.path.dirname(DB_PATH), 'backups')

# 当前最新版本
CURRENT_VERSION = 17

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
    13: "SYSTEM Collector 数据中心平台 schema 与静态目录接入 Shared Database；既存 registry 运行状态保持不变",
    14: "Add nullable Subject/BrandFocus scope keys and Evidence references; historical rows remain UNASSIGNED",
    15: "Canonical Subject Registry BrandFocus identity; BMP rows receive deterministic IDs",
    16: "Content Evidence source references, parent cleanup, and query indexes",
    17: "Add nullable full-record integrity metadata to canonical Evidence records",
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


def set_version(
    conn: sqlite3.Connection,
    version: int,
    description: str = "",
    *,
    commit: bool = True,
):
    """设置数据库版本"""
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
        (version, description, datetime.now().isoformat())
    )
    if commit:
        conn.commit()


def backup_database(backup_name: Optional[str] = None) -> str:
    """Create a validated, WAL-consistent backup of the call-time canonical DB."""
    db_path = get_db_path()
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")

    if not backup_name:
        version_conn = get_connection()
        try:
            current_version = get_current_version(version_conn)
        finally:
            version_conn.close()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"monitor_db_v{current_version}_{timestamp}.db"
    else:
        backup_name = os.fspath(backup_name)
        if (
            backup_name in {".", ".."}
            or os.path.basename(backup_name) != backup_name
        ):
            raise ValueError("backup_name must be a filename within the canonical backup folder")

    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, backup_name)
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    temp_path = None
    source = None
    destination = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(backup_path)}.",
            suffix=".tmp",
            dir=backup_dir,
        )
        os.close(fd)
        source = sqlite3.connect(db_path)
        destination = sqlite3.connect(temp_path)
        source.backup(destination)
        result = destination.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise sqlite3.DatabaseError(f"备份完整性校验失败: {result!r}")
        destination.close()
        destination = None
        source.close()
        source = None
        os.replace(temp_path, backup_path)
        temp_path = None
    except Exception:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        raise
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    print(f"✅ 数据库已备份到: {backup_path}")
    print(f"   备份大小: {os.path.getsize(backup_path) / 1024 / 1024:.2f} MB")
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


def migration_12_to_13(conn):
    """接入数据中心平台 schema，使用 additive DDL 并保留 registry 运行状态。"""
    from .platform_schema import apply_platform_schema

    apply_platform_schema(conn)


def migration_13_to_14(conn: sqlite3.Connection):
    """Add nullable scope keys and Evidence references without backfilling identity."""
    from .business_schema import ensure_business_scope_storage
    from canonical_data import ensure_canonical_scope_columns

    # SQLite otherwise autocommits each DDL statement on a connection with no
    # active transaction. Keep this version's schema and history row atomic.
    if not conn.in_transaction:
        conn.execute("BEGIN")
    ensure_business_scope_storage(conn)
    ensure_canonical_scope_columns(conn)


def migration_14_to_15(conn: sqlite3.Connection):
    """Add deterministic BrandFocus identity to the canonical Subject Registry."""
    # sqlite3 does not implicitly wrap DDL in the caller's DML transaction.
    # Keep the column, backfill, unique index and schema-version row atomic.
    if not conn.in_transaction:
        conn.execute("BEGIN")
    from subject_registry import ensure_schema

    ensure_schema(conn)


def migration_15_to_16(conn: sqlite3.Connection):
    """Additive Content Evidence lineage and query indexes in Shared DB.

    The content feature owns its tables; this versioned migration only adapts
    tables that already exist. Legacy source references stay NULL, while blank
    ancestry is normalized to the canonical NULL representation.
    """
    if not conn.in_transaction:
        conn.execute("BEGIN")

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    if "content_generation_evidence" in tables:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(content_generation_evidence)"
            ).fetchall()
        }
        if "source_evidence_ref" not in columns:
            conn.execute(
                "ALTER TABLE content_generation_evidence "
                "ADD COLUMN source_evidence_ref TEXT"
            )
            columns.add("source_evidence_ref")

        if "parent_evidence_id" in columns:
            conn.execute(
                "UPDATE content_generation_evidence "
                "SET parent_evidence_id=NULL "
                "WHERE parent_evidence_id IS NOT NULL "
                "AND TRIM(parent_evidence_id)=''"
            )

        for index_name, column in (
            ("idx_cge_type", "content_type"),
            ("idx_cge_created", "created_at"),
            ("idx_cge_source_evidence_ref", "source_evidence_ref"),
        ):
            if column in columns:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON content_generation_evidence({column})"
                )

    if "content_evaluation" in tables:
        evaluation_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(content_evaluation)"
            ).fetchall()
        }
        if "evidence_id" in evaluation_columns:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ce_evidence "
                "ON content_evaluation(evidence_id)"
            )


def migration_16_to_17(conn: sqlite3.Connection):
    """Add nullable full-record integrity storage through the Evidence owner."""
    if not conn.in_transaction:
        conn.execute("BEGIN")

    from lumenis.shared.evidence.store import ensure_evidence_schema

    ensure_evidence_schema(conn)


def _ensure_migration_prerequisites(
    conn, current_version: int, target_version: int
) -> int:
    """Create owner-managed base schemas required by the historical migrations.

    The versioned upgrade predates the current business, Canonical Data, and
    Evidence owners. A genuinely empty v0 database needs those owner schemas
    before the historical migrations can add their versioned fields. Existing
    databases keep their historical DDL/data semantics: this function never
    reapplies the current business schema over a versioned or partial database.
    """
    if current_version == 0 and target_version >= 1:
        base_tables = {"notes", "daily_reports", "collection_logs"}
        existing_base_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if row[0] in base_tables
        }
        if not existing_base_tables:
            # get_current_version() has already committed the empty schema_version
            # table. Keep the new base schema and v1 marker in one transaction
            # with the owner prerequisites below.
            conn.execute("BEGIN")
            apply_business_schema(conn)
        elif existing_base_tables != base_tables:
            missing = sorted(base_tables - existing_base_tables)
            raise RuntimeError(
                "v0 database has a partial historical base schema; "
                f"refusing current-schema repair (missing: {missing})"
            )
        else:
            reference = sqlite3.connect(":memory:")
            try:
                apply_business_schema(reference)
                for table in sorted(base_tables):
                    expected = {
                        row[1]: (row[2], row[3], row[4], row[5])
                        for row in reference.execute(
                            f"PRAGMA table_info({table})"
                        ).fetchall()
                    }
                    actual = {
                        row[1]: (row[2], row[3], row[4], row[5])
                        for row in conn.execute(
                            f"PRAGMA table_info({table})"
                        ).fetchall()
                    }
                    missing_or_changed = sorted(
                        column
                        for column, contract in expected.items()
                        if actual.get(column) != contract
                    )
                    if missing_or_changed:
                        raise RuntimeError(
                            "v0 database does not match the canonical business "
                            f"schema for {table}: {missing_or_changed}"
                        )
            finally:
                reference.close()

            # Existing v0 base rows are valid, but the v1 marker must remain
            # part of the same transaction as all owner prerequisites and the
            # first versioned migration. A later failure must leave v0 intact.
            if not conn.in_transaction:
                conn.execute("BEGIN")

        set_version(
            conn,
            1,
            MIGRATION_HISTORY[1],
            commit=False,
        )
        current_version = 1

    needs_canonical_schema = (
        target_version >= 10
        and conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='canonical_data'"
        ).fetchone() is None
    )
    needs_evidence_schema = (
        target_version >= 11
        and conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zbc_canonical_data'"
        ).fetchone() is None
    )

    # The owner initializers preserve caller transactions when given this
    # connection. Start one here so their DDL remains rollback-safe after the
    # version-table bootstrap has committed.
    if (needs_canonical_schema or needs_evidence_schema) and not conn.in_transaction:
        conn.execute("BEGIN")

    if needs_canonical_schema:
        from canonical_data import ensure_canonical_table

        ensure_canonical_table(connection=conn)

    if needs_evidence_schema:
        from lumenis.shared.evidence.chain import init_db as init_evidence_chain_db

        init_evidence_chain_db(connection=conn)

    return current_version


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
    12: migration_12_to_13,
    13: migration_13_to_14,
    14: migration_14_to_15,
    15: migration_15_to_16,
    16: migration_16_to_17,
}


def migrate(target_version: Optional[int] = None) -> bool:
    """执行数据库迁移"""
    if target_version is None:
        target_version = CURRENT_VERSION
    
    conn = get_connection()
    current_version = get_current_version(conn)
    
    print(f"📊 当前数据库版本: v{current_version}")
    print(f"🎯 目标版本: v{target_version}")
    
    if target_version < current_version:
        print(f"❌ 拒绝 schema 降级: 当前 v{current_version}，目标 v{target_version}")
        conn.close()
        return False

    if current_version == target_version:
        print("✅ 数据库已是目标版本，无需迁移")
        conn.close()
        return True

    # 迁移前自动备份。A missing or failed snapshot must stop all schema writes.
    print("\n📦 迁移前自动备份数据库...")
    try:
        backup_path = backup_database(
            f"before_migration_v{current_version}_to_v{target_version}.db"
        )
        if not backup_path or not os.path.isfile(backup_path):
            raise OSError("备份函数未生成可用文件")
    except Exception as e:
        print(f"❌ 迁移前备份失败，已拒绝迁移: {e}")
        conn.close()
        return False

    try:
        current_version = _ensure_migration_prerequisites(
            conn, current_version, target_version
        )
        if current_version == target_version and conn.in_transaction:
            # A fresh v0 database has no versioned step to commit its bootstrap.
            conn.commit()
    except Exception as e:
        print(f"❌ 迁移前共享 schema 初始化失败: {e}")
        conn.rollback()
        conn.close()
        return False

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
                print("   ⚠️  未提交的迁移更改已回滚")
                conn.rollback()
                conn.close()
                return False
        else:
            print(f"⚠️  跳过未知迁移 v{version} → v{version + 1}")
    
    print(f"\n🎉 数据库迁移完成！当前版本: v{get_current_version(conn)}")
    conn.close()
    return True


def rollback() -> bool:
    """Refuse downgrade until reversible schema migrations are implemented."""
    print("❌ 当前 schema 迁移没有可执行的反向步骤，拒绝回滚")
    return False


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
