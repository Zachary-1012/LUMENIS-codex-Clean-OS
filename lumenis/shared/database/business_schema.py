"""Canonical CTH/BMP/Shared business schema and idempotent application logic."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT UNIQUE NOT NULL,
    title TEXT DEFAULT '', content TEXT DEFAULT '', url TEXT DEFAULT '', cover TEXT DEFAULT '',
    author_id TEXT DEFAULT '', author_nickname TEXT DEFAULT '', author_avatar TEXT DEFAULT '',
    likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, collects INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
    note_type TEXT DEFAULT 'normal', xsec_token TEXT DEFAULT '',
    collected_at TEXT DEFAULT (datetime('now','localtime')), publish_date TEXT DEFAULT '',
    sentiment TEXT DEFAULT 'neutral', sentiment_score REAL DEFAULT 0.0,
    risk_level TEXT DEFAULT 'low', risk_score INTEGER DEFAULT 0, summary TEXT DEFAULT '',
    topics TEXT DEFAULT '[]', ai_provider TEXT DEFAULT 'rule', ai_analyzed_at TEXT DEFAULT '',
    is_official INTEGER DEFAULT 0, category TEXT DEFAULT 'other',
    status TEXT DEFAULT 'active', last_seen_at TEXT DEFAULT '',
    is_taikoo_verified INTEGER DEFAULT 0, verify_reason TEXT DEFAULT '',
    negative_confirmed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, report_type TEXT DEFAULT 'daily', report_date TEXT NOT NULL,
    period_start TEXT DEFAULT '', period_end TEXT DEFAULT '', total_notes INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0, neutral_count INTEGER DEFAULT 0, negative_count INTEGER DEFAULT 0,
    high_risk_count INTEGER DEFAULT 0, medium_risk_count INTEGER DEFAULT 0, low_risk_count INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0, total_comments INTEGER DEFAULT 0, total_engagements INTEGER DEFAULT 0,
    top_topics TEXT DEFAULT '[]', hot_notes TEXT DEFAULT '[]', risk_alerts TEXT DEFAULT '[]',
    key_events TEXT DEFAULT '[]', event_summary TEXT DEFAULT '', sentiment_analysis TEXT DEFAULT '',
    summary TEXT DEFAULT '', generated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS collection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT NOT NULL, notes_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success', error_msg TEXT DEFAULT '',
    started_at TEXT DEFAULT (datetime('now','localtime')), finished_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS web_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL, source_platform TEXT DEFAULT 'web', source_type TEXT DEFAULT 'web',
    title TEXT DEFAULT '', content TEXT DEFAULT '', url TEXT DEFAULT '', domain TEXT DEFAULT '',
    published_at TEXT DEFAULT '', fetched_at TEXT DEFAULT (datetime('now','localtime')),
    relevance TEXT DEFAULT 'pending', verification TEXT DEFAULT 'review', confidence REAL DEFAULT 0,
    sentiment TEXT DEFAULT 'neutral', risk_level TEXT DEFAULT 'low', risk_score INTEGER DEFAULT 0,
    summary TEXT DEFAULT '', event_hint TEXT DEFAULT '', topics TEXT DEFAULT '[]',
    ai_provider TEXT DEFAULT 'rule', related_event_id INTEGER DEFAULT NULL,
    source_adapter TEXT DEFAULT '', query TEXT DEFAULT '', canonical_url TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE NOT NULL, title TEXT DEFAULT '', summary TEXT DEFAULT '',
    fact_status TEXT DEFAULT 'unconfirmed', impact TEXT DEFAULT 'neutral', risk_reason TEXT DEFAULT '', recommended_action TEXT DEFAULT '',
    first_seen TEXT DEFAULT '', last_seen TEXT DEFAULT '', mention_count INTEGER DEFAULT 0, source_count INTEGER DEFAULT 0,
    risk_level TEXT DEFAULT 'low', risk_score INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
    keywords TEXT DEFAULT '[]', translations TEXT DEFAULT '{}', ai_provider TEXT DEFAULT 'rule', event_date TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS feedback_keywords (
    keyword TEXT PRIMARY KEY, source TEXT DEFAULT 'web', score REAL DEFAULT 0, enabled INTEGER DEFAULT 1,
    first_seen TEXT DEFAULT '', last_seen TEXT DEFAULT '', used_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_web_relevance ON web_mentions(relevance);
CREATE INDEX IF NOT EXISTS idx_web_published ON web_mentions(published_at);
CREATE INDEX IF NOT EXISTS idx_events_risk ON events(risk_level);
CREATE INDEX IF NOT EXISTS idx_notes_sentiment ON notes(sentiment);
CREATE INDEX IF NOT EXISTS idx_notes_risk ON notes(risk_level);
CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
CREATE INDEX IF NOT EXISTS idx_notes_collected ON notes(collected_at);
CREATE INDEX IF NOT EXISTS idx_notes_publish_date ON notes(publish_date);
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author_id);
CREATE INDEX IF NOT EXISTS idx_notes_status ON notes(status);
CREATE INDEX IF NOT EXISTS idx_notes_verified ON notes(is_taikoo_verified);
CREATE TABLE IF NOT EXISTS web_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT, source_key TEXT UNIQUE NOT NULL, source_name TEXT DEFAULT '', adapter TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1, last_run_at TEXT DEFAULT '', last_success_at TEXT DEFAULT '', last_error TEXT DEFAULT '', item_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS web_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, adapter TEXT DEFAULT '', query TEXT DEFAULT '', started_at TEXT DEFAULT '', finished_at TEXT DEFAULT '',
    fetched INTEGER DEFAULT 0, accepted INTEGER DEFAULT 0, rejected INTEGER DEFAULT 0, error TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS event_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, source_type TEXT DEFAULT '', source_id TEXT DEFAULT '', match_score REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')), UNIQUE(event_id,source_type,source_id)
);
CREATE TABLE IF NOT EXISTS note_review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, note_id TEXT NOT NULL, old_relevance TEXT DEFAULT '', new_relevance TEXT DEFAULT '', old_sentiment TEXT DEFAULT '', new_sentiment TEXT DEFAULT '',
    old_risk TEXT DEFAULT '', new_risk TEXT DEFAULT '', reason TEXT DEFAULT '', provider TEXT DEFAULT 'rule', reviewed_at TEXT DEFAULT (datetime('now','localtime'))
);
-- ===== v5.3.2 新增表 =====
CREATE TABLE IF NOT EXISTS ai_filter_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT NOT NULL,
    filter_stage TEXT DEFAULT 'secondary',
    filter_result TEXT DEFAULT 'pending',
    filter_reason TEXT DEFAULT '',
    noise_type TEXT DEFAULT '',
    confidence REAL DEFAULT 0,
    provider TEXT DEFAULT 'rule',
    filtered_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS daily_digest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_date TEXT UNIQUE NOT NULL,
    total_found INTEGER DEFAULT 0,
    effective_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    risk_count INTEGER DEFAULT 0,
    risk_index REAL DEFAULT 0,
    brand_health_score REAL DEFAULT 0,
    ai_summary TEXT DEFAULT '',
    executive_summary TEXT DEFAULT '',
    key_insights TEXT DEFAULT '[]',
    action_items TEXT DEFAULT '[]',
    top_events TEXT DEFAULT '[]',
    generated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS event_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    ai_summary TEXT DEFAULT '',
    risk_assessment TEXT DEFAULT '',
    recommended_action TEXT DEFAULT '',
    sentiment_trend TEXT DEFAULT '',
    propagation_analysis TEXT DEFAULT '',
    key_voices TEXT DEFAULT '[]',
    provider TEXT DEFAULT 'rule',
    generated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ai_filter_note ON ai_filter_log(note_id);
CREATE INDEX IF NOT EXISTS idx_ai_filter_result ON ai_filter_log(filter_result);
CREATE INDEX IF NOT EXISTS idx_daily_digest_date ON daily_digest(digest_date);
CREATE INDEX IF NOT EXISTS idx_event_insights_event ON event_insights(event_id);
CREATE TABLE IF NOT EXISTS collector_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, note_id TEXT NOT NULL, status TEXT DEFAULT 'unknown', score REAL DEFAULT 0,
    detail_status TEXT DEFAULT '', comments_collected INTEGER DEFAULT 0, collector_version TEXT DEFAULT '',
    checked_at TEXT DEFAULT (datetime('now','localtime')), reason TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS note_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, comment_id TEXT UNIQUE NOT NULL, note_id TEXT NOT NULL,
    content TEXT DEFAULT '', author_id TEXT DEFAULT '', author_nickname TEXT DEFAULT '', likes INTEGER DEFAULT 0,
    publish_time TEXT DEFAULT '', parent_id TEXT DEFAULT '', raw_json TEXT DEFAULT '{}',
    fetched_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_collector_quality_note ON collector_quality_log(note_id);
CREATE INDEX IF NOT EXISTS idx_note_comments_note ON note_comments(note_id);

-- ===== 指标快照时序（UNIFIED-BASELINE §9/§11）：note 互动量 + topic 指标统一 Canonical 快照表 =====
-- notes 单行只保留最新值；每次采集指标"发生变化"时在此留痕，保证 likes/comments/... 随时间可追溯、可恢复。
-- entity_type='note' 用互动量四列；entity_type='topic' 用 browse/discussion/note_count 三列。snapshot_at 为独立 Snapshot Date。
CREATE TABLE IF NOT EXISTS metric_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    likes INTEGER, comments INTEGER, collects INTEGER, shares INTEGER,
    browse_count INTEGER, discussion_count INTEGER, note_count INTEGER,
    raw_json TEXT DEFAULT '{}',
    source TEXT DEFAULT '',
    collector_version TEXT DEFAULT '',
    snapshot_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_metric_snap_entity ON metric_snapshots(entity_type, entity_key, snapshot_at);
"""

NOTE_MIGRATIONS = {
    'status': "ALTER TABLE notes ADD COLUMN status TEXT DEFAULT 'active'",
    'last_seen_at': "ALTER TABLE notes ADD COLUMN last_seen_at TEXT DEFAULT ''",
    'is_taikoo_verified': "ALTER TABLE notes ADD COLUMN is_taikoo_verified INTEGER DEFAULT 0",
    'verify_reason': "ALTER TABLE notes ADD COLUMN verify_reason TEXT DEFAULT ''",
}

NOTE_MIGRATIONS.update({
    'source_platform': "ALTER TABLE notes ADD COLUMN source_platform TEXT DEFAULT 'xhs'",
    'relevance_status': "ALTER TABLE notes ADD COLUMN relevance_status TEXT DEFAULT 'relevant'",
    'verification_status': "ALTER TABLE notes ADD COLUMN verification_status TEXT DEFAULT 'review'",
    'verification_confidence': "ALTER TABLE notes ADD COLUMN verification_confidence REAL DEFAULT 0",
    'fact_basis': "ALTER TABLE notes ADD COLUMN fact_basis TEXT DEFAULT 'text'",
    'ai_reason': "ALTER TABLE notes ADD COLUMN ai_reason TEXT DEFAULT ''",
    'event_hint': "ALTER TABLE notes ADD COLUMN event_hint TEXT DEFAULT ''",
    'translations': "ALTER TABLE notes ADD COLUMN translations TEXT DEFAULT '{}'",
    'relevance_score': "ALTER TABLE notes ADD COLUMN relevance_score REAL DEFAULT 1.0",
    'content_quality': "ALTER TABLE notes ADD COLUMN content_quality REAL DEFAULT 0.5",
    'duplicate_of': "ALTER TABLE notes ADD COLUMN duplicate_of TEXT DEFAULT ''",
    'ai_model': "ALTER TABLE notes ADD COLUMN ai_model TEXT DEFAULT ''",
    'last_reviewed_at': "ALTER TABLE notes ADD COLUMN last_reviewed_at TEXT DEFAULT ''",
    # ===== v5.3.2 AI过滤层新增字段 =====
    'ai_filter_status': "ALTER TABLE notes ADD COLUMN ai_filter_status TEXT DEFAULT 'pending'",
    'ai_filter_reason': "ALTER TABLE notes ADD COLUMN ai_filter_reason TEXT DEFAULT ''",
    'ai_filtered_at': "ALTER TABLE notes ADD COLUMN ai_filtered_at TEXT DEFAULT ''",
    'content_quality_score': "ALTER TABLE notes ADD COLUMN content_quality_score REAL DEFAULT 0.5",
    'is_duplicate': "ALTER TABLE notes ADD COLUMN is_duplicate INTEGER DEFAULT 0",
    'noise_type': "ALTER TABLE notes ADD COLUMN noise_type TEXT DEFAULT ''",
    'ai_insight': "ALTER TABLE notes ADD COLUMN ai_insight TEXT DEFAULT ''",
    # ===== live collector data-quality fields (additive, backward-compatible) =====
    'publish_datetime': "ALTER TABLE notes ADD COLUMN publish_datetime TEXT DEFAULT ''",
    'captured_at': "ALTER TABLE notes ADD COLUMN captured_at TEXT DEFAULT ''",
    'detail_fetched_at': "ALTER TABLE notes ADD COLUMN detail_fetched_at TEXT DEFAULT ''",
    'comments_fetched_at': "ALTER TABLE notes ADD COLUMN comments_fetched_at TEXT DEFAULT ''",
    'comments_collected': "ALTER TABLE notes ADD COLUMN comments_collected INTEGER DEFAULT 0",
    'data_quality_status': "ALTER TABLE notes ADD COLUMN data_quality_status TEXT DEFAULT 'unknown'",
    'data_quality_score': "ALTER TABLE notes ADD COLUMN data_quality_score REAL DEFAULT 0",
    'collector_version': "ALTER TABLE notes ADD COLUMN collector_version TEXT DEFAULT ''",
    'body': "ALTER TABLE notes ADD COLUMN body TEXT DEFAULT ''",
    'source_keyword': "ALTER TABLE notes ADD COLUMN source_keyword TEXT DEFAULT ''",
    'matched_keywords': "ALTER TABLE notes ADD COLUMN matched_keywords TEXT DEFAULT ''",
    # GAP-06 传播主体/内容双维度（纯增量、向后兼容、默认空串，不影响既有主体/风险/统计口径）
    'subject_type': "ALTER TABLE notes ADD COLUMN subject_type TEXT DEFAULT ''",
    'content_type': "ALTER TABLE notes ADD COLUMN content_type TEXT DEFAULT ''",
})

WEB_MIGRATIONS = {
    'source_adapter': "ALTER TABLE web_mentions ADD COLUMN source_adapter TEXT DEFAULT ''",
    'query': "ALTER TABLE web_mentions ADD COLUMN query TEXT DEFAULT ''",
    'canonical_url': "ALTER TABLE web_mentions ADD COLUMN canonical_url TEXT DEFAULT ''",
}

REPORT_MIGRATIONS = {
    'report_type': "ALTER TABLE daily_reports ADD COLUMN report_type TEXT DEFAULT 'daily'",
    'period_start': "ALTER TABLE daily_reports ADD COLUMN period_start TEXT DEFAULT ''",
    'period_end': "ALTER TABLE daily_reports ADD COLUMN period_end TEXT DEFAULT ''",
    'key_events': "ALTER TABLE daily_reports ADD COLUMN key_events TEXT DEFAULT '[]'",
    'event_summary': "ALTER TABLE daily_reports ADD COLUMN event_summary TEXT DEFAULT ''",
    'sentiment_analysis': "ALTER TABLE daily_reports ADD COLUMN sentiment_analysis TEXT DEFAULT ''",
    # ===== v5.3.2 日报增强字段 =====
    'executive_summary': "ALTER TABLE daily_reports ADD COLUMN executive_summary TEXT DEFAULT ''",
    'ai_summary': "ALTER TABLE daily_reports ADD COLUMN ai_summary TEXT DEFAULT ''",
    'key_insights': "ALTER TABLE daily_reports ADD COLUMN key_insights TEXT DEFAULT '[]'",
    'action_items': "ALTER TABLE daily_reports ADD COLUMN action_items TEXT DEFAULT '[]'",
    'risk_index': "ALTER TABLE daily_reports ADD COLUMN risk_index REAL DEFAULT 0",
    'brand_health_score': "ALTER TABLE daily_reports ADD COLUMN brand_health_score REAL DEFAULT 0",
    # ===== ZBC Phase 9 报告 artifact 真实性字段（纯增量、向后兼容、默认空，不影响既有数据）=====
    'report_id': "ALTER TABLE daily_reports ADD COLUMN report_id TEXT DEFAULT ''",
    'artifact_hash': "ALTER TABLE daily_reports ADD COLUMN artifact_hash TEXT DEFAULT ''",
    'generator_version': "ALTER TABLE daily_reports ADD COLUMN generator_version TEXT DEFAULT ''",
    'data_version': "ALTER TABLE daily_reports ADD COLUMN data_version TEXT DEFAULT ''",
    'source_snapshot': "ALTER TABLE daily_reports ADD COLUMN source_snapshot TEXT DEFAULT ''",
}

# ===== v5.8.2 事件负面二次确认（与笔记 negative_confirmed 同口径：0待确认/1确认/2驳回）=====
EVENT_MIGRATIONS = {
    'negative_confirmed': "ALTER TABLE events ADD COLUMN negative_confirmed INTEGER DEFAULT 0",
    'negative_confirmed_at': "ALTER TABLE events ADD COLUMN negative_confirmed_at TEXT DEFAULT ''",
    'negative_confirmed_by': "ALTER TABLE events ADD COLUMN negative_confirmed_by TEXT DEFAULT ''",
    'event_date': "ALTER TABLE events ADD COLUMN event_date TEXT DEFAULT ''",
}



def apply_business_schema(conn):
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute('PRAGMA table_info(notes)').fetchall()}
    for col, ddl in NOTE_MIGRATIONS.items():
        if col not in cols:
            conn.execute(ddl)
    web_cols = {r[1] for r in conn.execute('PRAGMA table_info(web_mentions)').fetchall()}
    for col, ddl in WEB_MIGRATIONS.items():
        if col not in web_cols:
            conn.execute(ddl)
    report_cols = {r[1] for r in conn.execute('PRAGMA table_info(daily_reports)').fetchall()}
    for col, ddl in REPORT_MIGRATIONS.items():
        if col not in report_cols:
            conn.execute(ddl)
    # v5.8.2 事件负面确认字段（幂等）
    evt_cols = {r[1] for r in conn.execute('PRAGMA table_info(events)').fetchall()}
    for col, ddl in EVENT_MIGRATIONS.items():
        if col not in evt_cols:
            conn.execute(ddl)
    conn.execute("UPDATE notes SET status='active' WHERE status IS NULL OR status=''")
    conn.execute("UPDATE notes SET last_seen_at=COALESCE(NULLIF(last_seen_at,''), collected_at, datetime('now','localtime'))")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_type_date ON daily_reports(report_type, report_date)")
    conn.execute("UPDATE notes SET source_platform='xhs' WHERE source_platform IS NULL OR source_platform=''")
    conn.execute("UPDATE notes SET relevance_status='relevant' WHERE relevance_status IS NULL OR relevance_status=''")
    conn.execute("UPDATE notes SET body=content WHERE (body IS NULL OR body='') AND content<>''")
    # v5.8.5 事件发生日期兜底：缺省以首次发现日为发生下限（可被关联笔记最早发布日校正）
    conn.execute("UPDATE events SET event_date=first_seen WHERE event_date IS NULL OR event_date=''")
    # 以关联笔记的最早「规范发布日期」校正发生日期；聚合 min 无规范日期时置空（前端显示待核，不展示“编辑于/小时前”等脏相对时间）
    conn.execute('''UPDATE events SET event_date=(
            SELECT min(substr(COALESCE(n.publish_date,n.publish_datetime,''),1,10))
            FROM event_mentions em JOIN notes n ON n.note_id=em.source_id
            WHERE em.event_id=events.id AND substr(COALESCE(n.publish_date,n.publish_datetime,''),1,10) GLOB '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        ) WHERE EXISTS (
            SELECT 1 FROM event_mentions em JOIN notes n ON n.note_id=em.source_id
            WHERE em.event_id=events.id)''')
