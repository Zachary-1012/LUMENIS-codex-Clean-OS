"""
广州太古汇舆情监测系统 - 数据库迁移脚本
统一schema管理，避免升级时数据丢失

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

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'data', 'backups')

# 当前最新版本
CURRENT_VERSION = 9

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
}


def get_db_path() -> str:
    """获取数据库路径"""
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
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
    """获取当前数据库版本"""
    init_version_table(conn)
    cursor = conn.execute("SELECT MAX(version) as max_version FROM schema_version")
    row = cursor.fetchone()
    return row['max_version'] if row['max_version'] else 0


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
