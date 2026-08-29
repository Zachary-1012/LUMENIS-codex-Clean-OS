"""
初始化数据库脚本
创建所有必需的表和索引
版本: v5.8.0
"""

import sqlite3
import os
import sys

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'monitor.db')


def init_database():
    """初始化数据库"""
    print("=== 初始化数据库 ===")
    print(f"数据库路径: {DB_PATH}")

    # 确保data目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建notes表
    print("创建notes表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT UNIQUE,
            title TEXT,
            content TEXT,
            url TEXT,
            cover TEXT,
            author_id TEXT,
            author_nickname TEXT,
            author_avatar TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            collects INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            note_type TEXT,
            xsec_token TEXT,
            collected_at TEXT,
            publish_date TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            risk_level TEXT,
            risk_score INTEGER,
            summary TEXT,
            topics TEXT,
            ai_provider TEXT,
            ai_analyzed_at TEXT,
            is_official INTEGER DEFAULT 0,
            category TEXT,
            status TEXT,
            last_seen_at TEXT,
            is_taikoo_verified INTEGER DEFAULT 0,
            verify_reason TEXT,
            source_platform TEXT,
            relevance_status TEXT,
            verification_status TEXT,
            verification_confidence REAL,
            fact_basis TEXT,
            ai_reason TEXT,
            event_hint TEXT,
            translations TEXT,
            relevance_score REAL,
            content_quality REAL,
            duplicate_of TEXT,
            ai_model TEXT,
            last_reviewed_at TEXT,
            ai_filter_status TEXT,
            ai_filter_reason TEXT,
            ai_filtered_at TEXT,
            content_quality_score REAL,
            is_duplicate INTEGER DEFAULT 0,
            noise_type TEXT,
            ai_insight TEXT,
            publish_datetime TEXT,
            captured_at TEXT,
            detail_fetched_at TEXT,
            comments_fetched_at TEXT,
            comments_collected INTEGER DEFAULT 0,
            data_quality_status TEXT,
            data_quality_score REAL,
            collector_version TEXT,
            body TEXT,
            source_keyword TEXT,
            matched_keywords TEXT,
            negative_confirmed INTEGER DEFAULT 0,
            negative_confirmed_at TEXT,
            negative_confirmed_by TEXT
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_note_id ON notes(note_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_publish_date ON notes(publish_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_sentiment ON notes(sentiment)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_risk_level ON notes(risk_level)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_collected_at ON notes(collected_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_negative_confirmed ON notes(negative_confirmed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_publish_datetime ON notes(publish_datetime)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_captured_at ON notes(captured_at)')

    # 创建其他表
    tables = {
        'events': '''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT UNIQUE,
                title TEXT,
                summary TEXT,
                fact_status TEXT,
                impact TEXT,
                risk_reason TEXT,
                recommended_action TEXT,
                first_seen TEXT,
                last_seen TEXT,
                mention_count INTEGER DEFAULT 0,
                source_count INTEGER DEFAULT 0,
                risk_level TEXT,
                risk_score INTEGER,
                status TEXT,
                keywords TEXT,
                translations TEXT,
                ai_provider TEXT
            )
        ''',
        'comments': '''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT,
                comment_id TEXT,
                content TEXT,
                author_id TEXT,
                author_nickname TEXT,
                likes INTEGER DEFAULT 0,
                create_time TEXT,
                sentiment TEXT,
                risk_level TEXT,
                risk_score INTEGER,
                is_negative INTEGER DEFAULT 0,
                collected_at TEXT,
                is_taikoo_verified INTEGER DEFAULT 0
            )
        ''',
        'daily_reports': '''
            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                report_date TEXT,
                period_start TEXT,
                period_end TEXT,
                total_notes INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                neutral_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                high_risk_count INTEGER DEFAULT 0,
                medium_risk_count INTEGER DEFAULT 0,
                low_risk_count INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                total_engagements INTEGER DEFAULT 0,
                top_topics TEXT,
                hot_notes TEXT,
                risk_alerts TEXT,
                key_events TEXT,
                event_summary TEXT,
                sentiment_analysis TEXT,
                summary TEXT,
                generated_at TEXT,
                executive_summary TEXT,
                ai_summary TEXT,
                key_insights TEXT,
                action_items TEXT,
                risk_index REAL,
                brand_health_score REAL
            )
        ''',
        'collection_counters': '''
            CREATE TABLE IF NOT EXISTS collection_counters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                daily_count INTEGER DEFAULT 0,
                manual_count INTEGER DEFAULT 0,
                auto_count INTEGER DEFAULT 0,
                last_collect_at TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''',
        'system_config': '''
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE,
                config_value TEXT,
                description TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''',
        'web_topics': '''
            CREATE TABLE IF NOT EXISTS web_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                source TEXT,
                sentiment TEXT,
                relevance_score REAL,
                mention_count INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                tags TEXT,
                summary TEXT,
                created_at TEXT,
                UNIQUE(topic, source)
            )
        ''',
        'web_events': '''
            CREATE TABLE IF NOT EXISTS web_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                source TEXT,
                url TEXT,
                published_at TEXT,
                discovered_at TEXT,
                sentiment TEXT,
                risk_level TEXT,
                relevance_score REAL,
                tags TEXT,
                status TEXT,
                created_at TEXT
            )
        ''',
        'brand_industry_monitor': '''
            CREATE TABLE IF NOT EXISTS brand_industry_monitor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT,
                industry TEXT,
                source TEXT,
                mention_count INTEGER DEFAULT 0,
                sentiment TEXT,
                last_mention_at TEXT,
                keywords TEXT,
                summary TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(brand_name, source)
            )
        ''',
        'weekly_events': '''
            CREATE TABLE IF NOT EXISTS weekly_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_key TEXT,
                event_title TEXT,
                event_type TEXT,
                urgency TEXT,
                description TEXT,
                location TEXT,
                people_involved TEXT,
                process TEXT,
                screenshot_path TEXT,
                user_demand TEXT,
                sentiment TEXT,
                risk_level TEXT,
                status TEXT,
                confirmed_negative INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        ''',
        'note_comments': '''
            CREATE TABLE IF NOT EXISTS note_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT,
                note_id TEXT,
                content TEXT,
                author_id TEXT,
                author_nickname TEXT,
                likes INTEGER DEFAULT 0,
                publish_time TEXT,
                parent_id TEXT,
                raw_json TEXT,
                fetched_at TEXT
            )
        ''',
        'collector_quality_log': '''
            CREATE TABLE IF NOT EXISTS collector_quality_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT,
                status TEXT,
                score REAL,
                detail_status TEXT,
                comments_collected INTEGER DEFAULT 0,
                collector_version TEXT,
                checked_at TEXT,
                reason TEXT
            )
        ''',
    }

    for table_name, create_sql in tables.items():
        print(f"创建{table_name}表...")
        cursor.execute(create_sql)

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_web_topics_topic ON web_topics(topic)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_web_events_published_at ON web_events(published_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_weekly_events_week_key ON weekly_events(week_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_brand_industry_monitor_brand ON brand_industry_monitor(brand_name)')

    # 插入默认配置
    default_configs = [
        ('daily_collect_limit', '12', '每日采集总次数限制'),
        ('manual_collect_limit', '3', '每日手动采集次数限制'),
        ('auto_collect_limit', '9', '每日自动采集次数限制'),
        ('collect_cooldown_minutes', '15', '采集冷却时间（分钟）'),
        ('cloudflare_protocol', 'http2', 'Cloudflare协议'),
        ('cloudflare_ha_connections', '4', 'Cloudflare高可用连接数'),
        ('cloudflare_autoupdate', 'false', 'Cloudflare自动更新'),
        ('ai_provider', 'local', 'AI提供商'),
        ('daily_report_time', '09:00', '日报推送时间'),
        ('weekly_report_time', '09:00', '周报推送时间'),
    ]

    print("插入默认配置...")
    for key, value, desc in default_configs:
        cursor.execute('''
            INSERT OR IGNORE INTO system_config (config_key, config_value, description, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        ''', (key, value, desc))

    conn.commit()
    conn.close()

    print()
    print("=== 数据库初始化完成 ===")
    print(f"数据库文件: {DB_PATH}")


if __name__ == '__main__':
    init_database()
