"""广州太古汇舆情监测系统 - SQLite 数据层（v4 修复版）"""
import sqlite3
import json
import os
import re
from datetime import datetime
from contextlib import contextmanager
from subject_rules import SUBJECT_FIELDS, subject_hit, subject_sql_and_values

import time
import logging

logger = logging.getLogger(__name__)

# 数据库锁超时重试配置
_DB_MAX_RETRIES = 3
_DB_RETRY_BASE_DELAY = 0.5  # 秒，指数退避基数

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 数据库路径：允许通过环境变量 ZBC_DB_PATH 指定独立库（Staging/测试隔离）。
# 未设置该变量时默认生产库 data/monitor.db，行为与历史完全一致（向后兼容）。
DB_PATH = os.path.abspath(os.environ.get('ZBC_DB_PATH') or os.path.join(_BASE_DIR, 'data', 'monitor.db'))

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


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
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


def _db_connect_with_retry():
    """带重试的数据库连接，处理 database is locked 错误。"""
    last_exc = None
    for attempt in range(_DB_MAX_RETRIES):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA busy_timeout=30000')
            conn.execute('PRAGMA journal_mode=WAL')
            return conn
        except sqlite3.OperationalError as e:
            last_exc = e
            if 'locked' in str(e).lower() or 'busy' in str(e).lower():
                delay = _DB_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning('DB connect locked (attempt %d/%d), retrying in %.1fs: %s',
                               attempt + 1, _DB_MAX_RETRIES, delay, e)
                time.sleep(delay)
            else:
                raise
    raise last_exc


@contextmanager
def get_db():
    conn = _db_connect_with_retry()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error('DB operation rolled back: %s', e, exc_info=True)
        raise
    finally:
        conn.close()


def note_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    try:
        d['topics'] = json.loads(d.get('topics') or '[]')
        if not isinstance(d['topics'], list): d['topics'] = []
    except Exception:
        d['topics'] = [x.strip() for x in str(d.get('topics') or '').split(',') if x.strip()]
    try:
        d['translations'] = json.loads(d.get('translations') or '{}')
        if not isinstance(d['translations'], dict): d['translations'] = {}
    except Exception:
        d['translations'] = {}
    return d


def insert_note(note_data):
    """插入/更新笔记；返回 (row_id, inserted_bool)。"""
    nid = str(note_data.get('note_id') or '').strip()
    if not nid:
        raise ValueError('note_id 不能为空')
    with get_db() as conn:
        existing = conn.execute('SELECT * FROM notes WHERE note_id=?', (nid,)).fetchone()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        vals = {
            'title': note_data.get('title','') or '', 'source_platform': note_data.get('source_platform','xhs') or 'xhs', 'content': note_data.get('content','') or '',
            'url': note_data.get('url','') or '', 'cover': note_data.get('cover','') or '',
            'author_id': note_data.get('author_id','') or '', 'author_nickname': note_data.get('author_nickname','') or '',
            'author_avatar': note_data.get('author_avatar','') or '',
            'likes': int(note_data.get('likes',0) or 0), 'comments': int(note_data.get('comments',0) or 0),
            'collects': int(note_data.get('collects',0) or 0), 'shares': int(note_data.get('shares',0) or 0),
            'note_type': note_data.get('type','normal') or 'normal', 'xsec_token': note_data.get('xsec_token','') or '',
            'publish_date': (note_data.get('publish_datetime','') or note_data.get('publish_date','') or '').strip(),
            'is_taikoo_verified': int(note_data.get('is_taikoo_verified',0) or 0),
            'verify_reason': note_data.get('verify_reason','') or '',
            'body': note_data.get('body', note_data.get('content','')) or '',
            'source_keyword': note_data.get('source_keyword','') or '',
            'matched_keywords': note_data.get('matched_keywords','') or '',
        }
        # 数据质量软门（写入门接线，enrich 标记不丢弃=数据零丢失）：
        # 调用方未显式传 data_quality_status 时，自动用 DataQualityGate(note 契约) 校验并标记。
        # INSERT/UPDATE 分支已消费 note_data 的这两个字段，此处统一填充，零侵入各采集入口。
        if not (note_data.get('data_quality_status') or ''):
            try:
                from data_quality_gate import DataQualityGate
                _q = DataQualityGate().enrich_quality_record('note', {
                    'title': vals['title'], 'url': vals['url'],
                    'publish_date': vals['publish_date'],
                    'risk_level': note_data.get('risk_level', '') or 'unconfirmed',
                })
                note_data['data_quality_status'] = _q['data_quality_status']
                note_data['data_quality_score'] = _q['data_quality_score']
            except Exception:
                pass  # 软门失败绝不影响写入（数据零丢失红线）
        # 标题兜底：标题缺失时用正文首句(去空白/截24)补，再退作者昵称；保证列表不出现空标题(新增/更新均覆盖)
        if not (vals['title'] or '').strip():
            _t = ''
            _ct = (vals['content'] or '').strip()
            if _ct:
                _first = re.split(r'[\n\r\t。！？!?]', _ct)[0]
                _t = re.sub(r'\s+', '', _first).strip(':：').strip()[:24]
            if not _t and vals['author_nickname']:
                _t = vals['author_nickname'] + '的笔记'
            vals['title'] = _t
        # 双时间铁律：publish_* 来自平台发布时间，captured_at 是本机采集时刻，二者来源不同、绝不互相顶替。
        # 真人通道通常只给到日期(publish_date)，用它回填缺失的 publish_datetime，保证发布时间不留空。
        # GAP-06 双维度标注（纯增强：失败兜底空串，不参与主体口径/风险/统计，不阻断采集）
        try:
            from subject_classifier import enrich_note_types as _enrich_types
            _stype, _ctype = _enrich_types(
                vals.get('author_nickname', ''), note_data.get('author_desc', ''),
                note_data.get('followers', 0) or 0, int(vals.get('is_official', 0) or 0),
                note_data.get('verified_type', ''), (vals.get('title', '') + ' ' + vals.get('body', '')))
        except Exception:
            _stype = _ctype = ''
        pub_dt = (note_data.get('publish_datetime', '') or note_data.get('publish_date', '') or '').strip()
        coll_at = (note_data.get('collected_at', '') or note_data.get('captured_at', '') or '').strip()
        if existing:
            conn.execute("""UPDATE notes SET source_platform=?, title=?, content=CASE WHEN ?<>'' THEN ? ELSE content END,
                url=CASE WHEN ?<>'' THEN ? ELSE url END, cover=CASE WHEN ?<>'' THEN ? ELSE cover END,
                author_id=CASE WHEN ?<>'' THEN ? ELSE author_id END,
                author_nickname=CASE WHEN ?<>'' THEN ? ELSE author_nickname END,
                author_avatar=CASE WHEN ?<>'' THEN ? ELSE author_avatar END,
                likes=?, comments=?, collects=?, shares=?, note_type=?,
                xsec_token=CASE WHEN ?<>'' THEN ? ELSE xsec_token END,
                publish_date=CASE WHEN ?<>'' THEN ? ELSE publish_date END,
                is_taikoo_verified=CASE WHEN ?=1 THEN 1 ELSE is_taikoo_verified END,
                verify_reason=CASE WHEN ?<>'' THEN ? ELSE verify_reason END,
                publish_datetime=CASE WHEN ?<>'' THEN ? ELSE publish_datetime END,
                collected_at=CASE WHEN ?<>'' THEN ? ELSE collected_at END,
                captured_at=CASE WHEN ?<>'' THEN ? ELSE captured_at END,
                detail_fetched_at=CASE WHEN ?<>'' THEN ? ELSE detail_fetched_at END,
                comments_fetched_at=CASE WHEN ?<>'' THEN ? ELSE comments_fetched_at END,
                comments_collected=CASE WHEN ? >= 0 THEN ? ELSE comments_collected END,
                data_quality_status=CASE WHEN ?<>'' THEN ? ELSE data_quality_status END,
                data_quality_score=CASE WHEN ? > 0 THEN ? ELSE data_quality_score END,
                collector_version=CASE WHEN ?<>'' THEN ? ELSE collector_version END,
                status='active', last_seen_at=?
                WHERE note_id=?""", (
                vals['source_platform'], vals['title'], vals['content'], vals['content'], vals['url'], vals['url'], vals['cover'], vals['cover'],
                vals['author_id'], vals['author_id'], vals['author_nickname'], vals['author_nickname'],
                vals['author_avatar'], vals['author_avatar'], vals['likes'], vals['comments'], vals['collects'], vals['shares'],
                vals['note_type'], vals['xsec_token'], vals['xsec_token'], vals['publish_date'], vals['publish_date'], vals['is_taikoo_verified'], vals['verify_reason'], vals['verify_reason'],
                pub_dt, pub_dt,
                coll_at, coll_at,
                coll_at, coll_at,
                note_data.get('detail_fetched_at','') or '', note_data.get('detail_fetched_at','') or '',
                note_data.get('comments_fetched_at','') or '', note_data.get('comments_fetched_at','') or '',
                int(note_data.get('comments_collected',0) or 0), int(note_data.get('comments_collected',0) or 0),
                note_data.get('data_quality_status','') or '', note_data.get('data_quality_status','') or '',
                float(note_data.get('data_quality_score',0) or 0), float(note_data.get('data_quality_score',0) or 0),
                note_data.get('collector_version','') or '', note_data.get('collector_version','') or '', now, nid))
            conn.execute("UPDATE notes SET body=CASE WHEN ?<>'' THEN ? ELSE body END, source_keyword=CASE WHEN ?<>'' THEN ? ELSE source_keyword END, matched_keywords=CASE WHEN ?<>'' THEN ? ELSE matched_keywords END WHERE note_id=?", (vals['body'], vals['body'], vals['source_keyword'], vals['source_keyword'], vals['matched_keywords'], vals['matched_keywords'], nid))
            if _stype:
                conn.execute("UPDATE notes SET subject_type=CASE WHEN ?<>'' THEN ? ELSE subject_type END, "
                             "content_type=CASE WHEN ?<>'' THEN ? ELSE content_type END WHERE note_id=?",
                             (_stype, _stype, _ctype, _ctype, nid))
            # 指标快照（基线§11 Snapshot Date）：互动量被覆盖前留痕；纯旁路，任何异常都不得阻断采集主流程
            try:
                record_note_metric_snapshot(
                    conn, nid,
                    {'likes': vals['likes'], 'comments': vals['comments'],
                     'collects': vals['collects'], 'shares': vals['shares']},
                    source='live', collector_version=note_data.get('collector_version', '') or '')
            except Exception:
                pass
            return existing['id'], False
        cur = conn.execute("""INSERT INTO notes
            (note_id,source_platform,title,content,url,cover,author_id,author_nickname,author_avatar,likes,comments,collects,shares,
             note_type,xsec_token,publish_date,publish_datetime,collected_at,captured_at,detail_fetched_at,comments_fetched_at,comments_collected,
             data_quality_status,data_quality_score,collector_version,status,last_seen_at,is_official,is_taikoo_verified,verify_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'active',?,?,?,?)""", (
            nid, vals['source_platform'], vals['title'], vals['content'], vals['url'], vals['cover'], vals['author_id'], vals['author_nickname'],
            vals['author_avatar'], vals['likes'], vals['comments'], vals['collects'], vals['shares'], vals['note_type'],
            vals['xsec_token'], vals['publish_date'], pub_dt, coll_at or now, coll_at or now,
            note_data.get('detail_fetched_at','') or '', note_data.get('comments_fetched_at','') or '', int(note_data.get('comments_collected',0) or 0),
            note_data.get('data_quality_status','unknown') or 'unknown', float(note_data.get('data_quality_score',0) or 0),
            note_data.get('collector_version','') or '', now, 1 if vals['author_nickname']=='广州太古汇' else 0, vals['is_taikoo_verified'], vals['verify_reason']))
        conn.execute('UPDATE notes SET body=?, source_keyword=?, matched_keywords=? WHERE note_id=?', (vals['body'], vals['source_keyword'], vals['matched_keywords'], nid))
        if _stype:
            conn.execute("UPDATE notes SET subject_type=CASE WHEN ?<>'' THEN ? ELSE subject_type END, "
                         "content_type=CASE WHEN ?<>'' THEN ? ELSE content_type END WHERE note_id=?",
                         (_stype, _stype, _ctype, _ctype, nid))
        return cur.lastrowid, True


def _metric_snapshot_enabled():
    """指标快照开关（默认开；ZBC_METRIC_SNAPSHOT=0/false/off/no 关闭）。资源受限时可关，不影响主流程。"""
    return os.environ.get('ZBC_METRIC_SNAPSHOT', '1').strip().lower() not in ('0', 'false', 'off', 'no')


_NOTE_METRIC_KEYS = ('likes', 'comments', 'collects', 'shares')
_TOPIC_METRIC_KEYS = ('browse_count', 'discussion_count', 'note_count')


def record_note_metric_snapshot(conn, note_id, metrics, source='live', collector_version='', force=False):
    """在已有事务连接内为笔记写一条互动量快照；仅当指标相对上一条快照发生变化时写入（不该算的一次不浪费）。

    返回 True=已写 / False=跳过。调用方需自行 try/except 旁路，保证快照失败不阻断采集。
    """
    if not _metric_snapshot_enabled() or not note_id:
        return False
    cur_vals = tuple(int(metrics.get(k, 0) or 0) for k in _NOTE_METRIC_KEYS)
    if not force:
        row = conn.execute(
            "SELECT likes,comments,collects,shares FROM metric_snapshots "
            "WHERE entity_type='note' AND entity_key=? ORDER BY id DESC LIMIT 1", (note_id,)).fetchone()
        if row is not None and tuple(int(row[k] or 0) for k in _NOTE_METRIC_KEYS) == cur_vals:
            return False  # 指标无变化，不重复刷表
    conn.execute(
        "INSERT INTO metric_snapshots(entity_type,entity_key,likes,comments,collects,shares,"
        "browse_count,discussion_count,note_count,source,collector_version) "
        "VALUES('note',?,?,?,?,?,NULL,NULL,NULL,?,?)",
        (note_id, *cur_vals, source, collector_version or ''))
    return True


def record_topic_snapshot(topic_key, browse_count=None, discussion_count=None, note_count=None,
                          source='live', extra=None):
    """为话题写一条指标快照（浏览量/讨论量/笔记数随时间变化，基线§9 Topic Snapshot）。

    独立连接、变化才写、旁路不抛错。返回 True=已写 / False=跳过或关闭。
    """
    try:
        if not _metric_snapshot_enabled() or not topic_key:
            return False
        cur = (None if browse_count is None else int(browse_count),
               None if discussion_count is None else int(discussion_count),
               None if note_count is None else int(note_count))
        with get_db() as conn:
            row = conn.execute(
                "SELECT browse_count,discussion_count,note_count FROM metric_snapshots "
                "WHERE entity_type='topic' AND entity_key=? ORDER BY id DESC LIMIT 1", (topic_key,)).fetchone()
            if row is not None:
                prev = tuple(None if row[k] is None else int(row[k]) for k in _TOPIC_METRIC_KEYS)
                if prev == cur:
                    return False
            conn.execute(
                "INSERT INTO metric_snapshots(entity_type,entity_key,likes,comments,collects,shares,"
                "browse_count,discussion_count,note_count,raw_json,source) "
                "VALUES('topic',?,NULL,NULL,NULL,NULL,?,?,?,?,?)",
                (topic_key, cur[0], cur[1], cur[2],
                 json.dumps(extra or {}, ensure_ascii=False), source))
        return True
    except Exception:
        return False


def get_metric_trend(entity_type, entity_key, limit=200):
    """读取某实体的指标时间序列（snapshot_at 升序），供报告/前端动态可视化绑定真实数据。"""
    out = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM metric_snapshots WHERE entity_type=? AND entity_key=? "
            "ORDER BY id ASC LIMIT ?", (entity_type, entity_key, int(limit))).fetchall()
        for r in rows:
            d = dict(r)
            out.append(d)
    return out


def mark_disappeared_notes(seen_note_ids=None):
    """只对本次快照明确未出现的笔记标记消失；不再误伤其他关键词/历史数据。"""
    with get_db() as conn:
        if seen_note_ids is None:
            return 0
        ids = [str(x) for x in seen_note_ids if x]
        if not ids:
            return 0
        placeholders = ','.join('?' * len(ids))
        cur = conn.execute(f"UPDATE notes SET status='disappeared' WHERE status='active' AND note_id NOT IN ({placeholders})", ids)
        return cur.rowcount


def update_note_analysis(note_id, analysis):
    with get_db() as conn:
        conn.execute("""UPDATE notes SET sentiment=?, sentiment_score=?, risk_level=?, risk_score=?,
            summary=?, topics=?, ai_provider=?, ai_analyzed_at=?, category=?, is_official=?
            WHERE note_id=?""", (
            analysis.get('sentiment','neutral'), analysis.get('sentiment_score',0), analysis.get('risk_level','low'),
            analysis.get('risk_score',0), analysis.get('summary',''), json.dumps(analysis.get('topics',[]),ensure_ascii=False),
            analysis.get('ai_provider','rule'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            analysis.get('category','other'), int(analysis.get('is_official',0) or 0), note_id))


def _subject_clause(alias=''):
    clause, values = subject_sql_and_values(alias)
    return clause, values


def _verified_base(alias=''):
    prefix = f'{alias}.' if alias else ''
    clause, values = _subject_clause(alias)
    return f"{prefix}is_taikoo_verified=1 AND COALESCE({prefix}relevance_status,'relevant')!='irrelevant' AND {clause}", values


def _apply_filters(query, params, filters):
    filters = filters or {}
    if filters.get('sentiment'): query += ' AND sentiment=?'; params.append(filters['sentiment'])
    if filters.get('risk_level'): query += ' AND risk_level=?'; params.append(filters['risk_level'])
    if filters.get('category'): query += ' AND (category=? OR topics LIKE ?)'; params.extend([filters['category'], f"%{filters['category']}%"])
    if filters.get('keyword'):
        _kw=f"%{filters['keyword']}%"
        query += ' AND (title LIKE ? OR content LIKE ? OR summary LIKE ? OR topics LIKE ? OR event_hint LIKE ? OR author_nickname LIKE ? OR category LIKE ?)'
        params.extend([_kw]*7)
    if filters.get('is_official') is not None: query += ' AND is_official=?'; params.append(1 if filters['is_official'] else 0)
    if filters.get('date_start'): query += ' AND publish_date>=?'; params.append(filters['date_start'])
    if filters.get('date_end'): query += ' AND publish_date<=?'; params.append(filters['date_end'])
    if filters.get('verified') is not None: query += ' AND is_taikoo_verified=?'; params.append(1 if filters['verified'] else 0)
    # GAP-06 双维度筛选：固定枚举白名单，拒绝任意列名/非法值，不接受旧 user_type=UGC 写法
    _ST = {'official','kos','kol','koc','normal_user','media','institution'}
    _CT = {'ugc','commercial','official','review','experience','complaint','event'}
    if filters.get('subject_type') in _ST: query += ' AND subject_type=?'; params.append(filters['subject_type'])
    if filters.get('content_type') in _CT: query += ' AND content_type=?'; params.append(filters['content_type'])
    return query, params


def get_notes(filters=None, limit=100, offset=0):
    limit=max(1,min(int(limit),1000)); offset=max(0,int(offset))
    base, subject_params = _verified_base()
    query, params = _apply_filters(f"SELECT * FROM notes WHERE {base}", list(subject_params), filters)
    query += ' ORDER BY COALESCE(publish_date, collected_at) DESC, collected_at DESC LIMIT ? OFFSET ?'
    params.extend([limit,offset])
    with get_db() as conn: return [note_to_dict(r) for r in conn.execute(query,params).fetchall()]


def get_note_count(filters=None):
    base, subject_params = _verified_base()
    query, params = _apply_filters(f"SELECT COUNT(*) AS cnt FROM notes WHERE {base}", list(subject_params), filters)
    with get_db() as conn: return conn.execute(query,params).fetchone()['cnt']


def get_stats():
    base, subject_params = _verified_base()
    with get_db() as conn:
        def q(sql, extra=()): return conn.execute(sql, tuple(subject_params)+tuple(extra)).fetchone()['c']
        total=q(f'SELECT COUNT(*) c FROM notes WHERE {base}')
        pos=q(f"SELECT COUNT(*) c FROM notes WHERE {base} AND sentiment='positive'")
        neu=q(f"SELECT COUNT(*) c FROM notes WHERE {base} AND sentiment='neutral'")
        neg=q(f"SELECT COUNT(*) c FROM notes WHERE {base} AND sentiment='negative'")
        high=q(f"SELECT COUNT(*) c FROM notes WHERE {base} AND risk_level='high'")
        med=q(f"SELECT COUNT(*) c FROM notes WHERE {base} AND risk_level='medium'")
        low=q(f"SELECT COUNT(*) c FROM notes WHERE {base} AND risk_level='low'")
        total_likes=conn.execute(f'SELECT COALESCE(SUM(likes),0) s FROM notes WHERE {base}',tuple(subject_params)).fetchone()['s']
        total_comments=conn.execute(f'SELECT COALESCE(SUM(comments),0) s FROM notes WHERE {base}',tuple(subject_params)).fetchone()['s']
        total_eng=conn.execute(f'SELECT COALESCE(SUM(likes+comments+collects+shares),0) s FROM notes WHERE {base}',tuple(subject_params)).fetchone()['s']
        official=q(f'SELECT COUNT(*) c FROM notes WHERE {base} AND is_official=1')
        return {'total':total,'positive':pos,'neutral':neu,'negative':neg,'high_risk':high,'medium_risk':med,'low_risk':low,'total_likes':total_likes,'total_comments':total_comments,'total_engagements':total_eng,'official_count':official,'verified_count':total}

def get_hot_topics(limit=12):
    """返回首页热门话题；严格继承广州太古汇主体口径。"""
    buckets={}; base,sp=_verified_base()
    with get_db() as conn:
        rows=conn.execute(f"SELECT topics,sentiment FROM notes WHERE {base} AND topics IS NOT NULL AND topics!=''",tuple(sp)).fetchall()
    for r in rows:
        try: vals=json.loads(r['topics'] or '[]')
        except Exception: vals=[x.strip() for x in str(r['topics'] or '').split(',') if x.strip()]
        if not isinstance(vals,list): vals=[]
        sentiment=r['sentiment'] or 'neutral'
        for t in vals:
            t=str(t).strip()
            if not t: continue
            b=buckets.setdefault(t, {'topic':t,'count':0,'positive':0,'neutral':0,'negative':0})
            b['count']+=1
            b[sentiment if sentiment in ('positive','neutral','negative') else 'neutral']+=1
    items=[]
    for b in buckets.values():
        counts={'positive':b['positive'],'neutral':b['neutral'],'negative':b['negative']}
        dominant=max(counts,key=counts.get)
        # 以“热度 + 正负方向”决定轻微排序，不把负面绝对置顶。
        b['sentiment']=dominant
        b['sentiment_count']=counts[dominant]
        items.append(b)
    return sorted(items,key=lambda x:(x['count'],x['sentiment_count']),reverse=True)[:max(1,int(limit))]


def get_top_topics(limit=15):
    counts={}; base,sp=_verified_base()
    with get_db() as conn: rows=conn.execute(f"SELECT topics FROM notes WHERE {base} AND topics IS NOT NULL AND topics!=''",tuple(sp)).fetchall()
    for r in rows:
        try: vals=json.loads(r['topics'] or '[]')
        except Exception: vals=[x.strip() for x in str(r['topics'] or '').split(',')]
        if isinstance(vals,list):
            for t in vals:
                if t: counts[t]=counts.get(t,0)+1
    return sorted(counts.items(),key=lambda x:x[1],reverse=True)[:limit]


def get_hot_notes(limit=10):
    base,sp=_verified_base()
    with get_db() as conn: return [note_to_dict(r) for r in conn.execute(f"SELECT * FROM notes WHERE {base} ORDER BY (likes+comments+collects+shares) DESC LIMIT ?", tuple(sp)+(limit,)).fetchall()]


def get_high_risk_notes(limit=20):
    base,sp=_verified_base()
    # v5.8.2：排除已人工驳回(negative_confirmed=2)；近30天风险优先，其次风险分/时间，避免永远显示历史旧数据
    sql=(f"SELECT * FROM notes WHERE {base} AND risk_level IN ('critical','high','medium') "
         f"AND COALESCE(negative_confirmed,0)<>2 "
         f"ORDER BY (CASE WHEN date(COALESCE(NULLIF(collected_at,''),NULLIF(publish_date,'')))>=date('now','localtime','-30 day') THEN 0 ELSE 1 END), "
         f"risk_score DESC, collected_at DESC, (likes+comments) DESC LIMIT ?")
    with get_db() as conn: return [note_to_dict(r) for r in conn.execute(sql,tuple(sp)+(limit,)).fetchall()]


def get_category_distribution():
    base,sp=_verified_base()
    with get_db() as conn: return [{'category':r['category'],'count':r['cnt']} for r in conn.execute(f"SELECT category,COUNT(*) cnt FROM notes WHERE {base} GROUP BY category ORDER BY cnt DESC",tuple(sp)).fetchall()]


def save_daily_report(report):
    with get_db() as conn:
        rtype=report.get('report_type','daily'); date=report['report_date']
        values=(rtype,date,report.get('period_start',''),report.get('period_end',''),report.get('total_notes',0),report.get('positive_count',0),report.get('neutral_count',0),report.get('negative_count',0),report.get('high_risk_count',0),report.get('medium_risk_count',0),report.get('low_risk_count',0),report.get('total_likes',0),report.get('total_comments',0),report.get('total_engagements',0),json.dumps(report.get('top_topics',[]),ensure_ascii=False),json.dumps(report.get('hot_notes',[]),ensure_ascii=False),json.dumps(report.get('risk_alerts',[]),ensure_ascii=False),json.dumps(report.get('key_events',[]),ensure_ascii=False),report.get('event_summary',''),report.get('sentiment_analysis',''),report.get('summary',''),report.get('report_id',''),report.get('artifact_hash',''),report.get('generator_version',''),report.get('data_version',''),report.get('source_snapshot',''))
        existing=conn.execute('SELECT id FROM daily_reports WHERE report_type=? AND report_date=?',(rtype,date)).fetchone()
        if existing:
            conn.execute("""UPDATE daily_reports SET period_start=?,period_end=?,total_notes=?,positive_count=?,neutral_count=?,negative_count=?,high_risk_count=?,medium_risk_count=?,low_risk_count=?,total_likes=?,total_comments=?,total_engagements=?,top_topics=?,hot_notes=?,risk_alerts=?,key_events=?,event_summary=?,sentiment_analysis=?,summary=?,report_id=?,artifact_hash=?,generator_version=?,data_version=?,source_snapshot=?,generated_at=datetime('now','localtime') WHERE id=?""", values[2:]+(existing['id'],))
            return existing['id']
        cur=conn.execute("""INSERT INTO daily_reports(report_type,report_date,period_start,period_end,total_notes,positive_count,neutral_count,negative_count,high_risk_count,medium_risk_count,low_risk_count,total_likes,total_comments,total_engagements,top_topics,hot_notes,risk_alerts,key_events,event_summary,sentiment_analysis,summary,report_id,artifact_hash,generator_version,data_version,source_snapshot) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",values)
        return cur.lastrowid


def _decode_report(row):
    if not row: return None
    d=dict(row)
    for k in ('top_topics','hot_notes','risk_alerts','key_events'):
        try: d[k]=json.loads(d.get(k) or '[]')
        except Exception: d[k]=[]
    return d


def get_latest_report(report_type='daily'):
    with get_db() as conn: return _decode_report(conn.execute('SELECT * FROM daily_reports WHERE report_type=? ORDER BY report_date DESC LIMIT 1',(report_type,)).fetchone())


def get_negative_comments(limit=50):
    with get_db() as conn:
        try:
            clause,sp=subject_sql_and_values('n')
            rows=conn.execute(f'''SELECT c.*,n.title note_title,n.url note_url FROM comments c LEFT JOIN notes n ON n.note_id=c.note_id WHERE c.is_negative=1 AND n.is_taikoo_verified=1 AND {clause} ORDER BY c.likes DESC LIMIT ?''',tuple(sp)+(limit,)).fetchall()
        except sqlite3.OperationalError:
            rows=[]
        return [dict(r) for r in rows]


def search_notes_by_keyword(keyword,limit=10):
    base,sp=_verified_base(); params=tuple(sp)+(f'%{keyword}%',f'%{keyword}%',limit)
    with get_db() as conn: return [note_to_dict(r) for r in conn.execute(f'SELECT * FROM notes WHERE {base} AND (title LIKE ? OR content LIKE ?) ORDER BY (likes+comments+collects+shares) DESC LIMIT ?',params).fetchall()]


def get_notes_by_date_range(start_date,end_date):
    base, sp = _verified_base(); params=tuple(sp)+(start_date,end_date)
    with get_db() as conn: return [note_to_dict(r) for r in conn.execute(f"SELECT * FROM notes WHERE {base} AND publish_date BETWEEN ? AND ? ORDER BY (likes+comments+collects+shares) DESC",params).fetchall()]


def get_stats_by_date_range(start_date,end_date):
    base, sp = _verified_base(); p=tuple(sp)+(start_date,end_date)
    where=f"{base} AND publish_date BETWEEN ? AND ?"
    with get_db() as conn:
        q=lambda extra='': conn.execute(f'SELECT COUNT(*) c FROM notes WHERE {where}{extra}',p).fetchone()['c']
        total=q(); pos=q(" AND sentiment='positive'"); neu=q(" AND sentiment='neutral'"); neg=q(" AND sentiment='negative'"); high=q(" AND risk_level='high'"); med=q(" AND risk_level='medium'"); low=q(" AND risk_level='low'")
        eng=conn.execute(f'SELECT COALESCE(SUM(likes+comments+collects+shares),0) s FROM notes WHERE {where}',p).fetchone()['s']
        likes=conn.execute(f'SELECT COALESCE(SUM(likes),0) s FROM notes WHERE {where}',p).fetchone()['s']; comments=conn.execute(f'SELECT COALESCE(SUM(comments),0) s FROM notes WHERE {where}',p).fetchone()['s']
        return {'total':total,'positive':pos,'neutral':neu,'negative':neg,'high_risk':high,'medium_risk':med,'low_risk':low,'total_likes':likes,'total_comments':comments,'total_engagements':eng}


def get_historical_notes(period_start,period_end,limit=100):
    base,sp=_verified_base(); params=tuple(sp)+(period_start,period_end,limit)
    with get_db() as conn: return [note_to_dict(r) for r in conn.execute(f'SELECT * FROM notes WHERE {base} AND (publish_date < ? OR publish_date > ?) ORDER BY publish_date DESC LIMIT ?',params).fetchall()]


def get_historical_stats(period_start,period_end):
    base,sp=_verified_base(); p=tuple(sp)+(period_start,period_end)
    with get_db() as conn:
        total=conn.execute(f'SELECT COUNT(*) c FROM notes WHERE {base} AND (publish_date < ? OR publish_date > ?)',p).fetchone()['c']
        neg=conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base} AND (publish_date < ? OR publish_date > ?) AND sentiment='negative'",p).fetchone()['c']
        return {'total':total,'negative':neg}


def backup_database(destination):
    """使用 SQLite Online Backup API 生成一致性备份。

    不直接 copy monitor.db，避免 WAL 模式运行中复制数据库时得到不完整快照。
    """
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    src = sqlite3.connect(DB_PATH, timeout=30)
    try:
        dst = sqlite3.connect(destination)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return destination


def log_collection(keyword,count,status='success',error=''):
    with get_db() as conn:
        conn.execute("INSERT INTO collection_logs(keyword,notes_count,status,error_msg,finished_at) VALUES (?,?,?,?,datetime('now','localtime'))",(keyword,count,status,error))


def insert_web_mention(item):
    sid=str(item.get('source_id') or item.get('canonical_url') or item.get('url') or item.get('title') or '').strip()
    if not sid:return False
    with get_db() as conn:
        existing=conn.execute('SELECT id FROM web_mentions WHERE source_id=?',(sid,)).fetchone()
        vals=(sid,item.get('source_platform','web'),item.get('source_type','web'),item.get('title',''),item.get('content',''),item.get('url',''),item.get('domain',''),item.get('published_at',''),item.get('source_adapter',''),item.get('query',''),item.get('canonical_url',''))
        if existing:
            conn.execute("UPDATE web_mentions SET source_platform=?,title=?,content=?,url=?,domain=?,published_at=?,source_adapter=?,query=?,canonical_url=?,fetched_at=datetime('now','localtime') WHERE source_id=?",(vals[1],vals[3],vals[4],vals[5],vals[6],vals[7],vals[8],vals[9],vals[10],sid)); return False
        conn.execute('INSERT INTO web_mentions(source_id,source_platform,source_type,title,content,url,domain,published_at,source_adapter,query,canonical_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)',vals)
        return True

def update_web_analysis(source_id, analysis):
    with get_db() as conn:
        conn.execute('UPDATE web_mentions SET relevance=?,verification=?,confidence=?,sentiment=?,risk_level=?,risk_score=?,summary=?,event_hint=?,topics=?,ai_provider=? WHERE source_id=?',(
            analysis.get('relevance','relevant'),analysis.get('verification','review'),analysis.get('confidence',0.5),analysis.get('sentiment','neutral'),analysis.get('risk_level','low'),analysis.get('risk_score',0),analysis.get('summary',''),analysis.get('event_hint',''),json.dumps(analysis.get('topics',[]),ensure_ascii=False),analysis.get('provider','rule'),source_id))

def log_web_source(source_key,source_name,adapter,success=True,error='',item_count=0):
    with get_db() as conn:
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO web_sources(source_key,source_name,adapter,enabled,last_run_at,last_success_at,last_error,item_count) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(source_key) DO UPDATE SET last_run_at=excluded.last_run_at,last_success_at=excluded.last_success_at,last_error=excluded.last_error,item_count=excluded.item_count',
            (source_key,source_name,adapter,1,now,now if success else '',error,item_count))

def log_web_run(adapter,query,started,finished,fetched,accepted,rejected,error=''):
    with get_db() as conn:
        conn.execute('INSERT INTO web_runs(adapter,query,started_at,finished_at,fetched,accepted,rejected,error) VALUES (?,?,?,?,?,?,?,?)',(adapter,query,started,finished,fetched,accepted,rejected,error))

def get_web_mentions(limit=100, relevant_only=True):
    q='SELECT * FROM web_mentions'
    if relevant_only: q += " WHERE relevance='relevant'"
    q += ' ORDER BY COALESCE(published_at,fetched_at) DESC LIMIT ?'
    with get_db() as conn:
        rows=conn.execute(q,(limit,)).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            try: d['topics']=json.loads(d.get('topics') or '[]')
            except Exception: d['topics']=[]
            out.append(d)
        return out


def upsert_feedback_keyword(keyword, score, source='web'):
    with get_db() as conn:
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO feedback_keywords(keyword,source,score,first_seen,last_seen) VALUES (?,?,?,?,?) ON CONFLICT(keyword) DO UPDATE SET score=MAX(feedback_keywords.score,excluded.score),last_seen=excluded.last_seen,source=excluded.source',(keyword,source,score,now,now))


def get_feedback_keywords(limit=10):
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM feedback_keywords WHERE enabled=1 ORDER BY score DESC,last_seen DESC LIMIT ?',(limit,)).fetchall()]


def upsert_event(event):
    with get_db() as conn:
        existing=conn.execute('SELECT id FROM events WHERE event_key=?',(event['event_key'],)).fetchone()
        vals=(event['event_key'],event.get('title',''),event.get('summary',''),event.get('fact_status','unconfirmed'),event.get('impact','neutral'),event.get('risk_reason',''),event.get('recommended_action',''),event.get('first_seen',''),event.get('last_seen',''),event.get('mention_count',0),event.get('source_count',0),event.get('risk_level','low'),event.get('risk_score',0),event.get('status','active'),json.dumps(event.get('keywords',[]),ensure_ascii=False),json.dumps(event.get('translations',{}),ensure_ascii=False),event.get('ai_provider','rule'))
        if existing:
            conn.execute('UPDATE events SET title=?,summary=?,fact_status=?,impact=?,risk_reason=?,recommended_action=?,first_seen=?,last_seen=?,mention_count=?,source_count=?,risk_level=?,risk_score=?,status=?,keywords=?,translations=?,ai_provider=? WHERE event_key=?',vals[1:]+(vals[0],))
            return existing['id']
        cur=conn.execute('INSERT INTO events(event_key,title,summary,fact_status,impact,risk_reason,recommended_action,first_seen,last_seen,mention_count,source_count,risk_level,risk_score,status,keywords,translations,ai_provider) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals)
        conn.execute('UPDATE events SET event_date=? WHERE id=?',(event.get('event_date') or event.get('first_seen',''), cur.lastrowid))
        return cur.lastrowid


def get_events(limit=50):
    from subject_rules import subject_hit
    with get_db() as conn:
        # 多取一批，再按统一主体口径过滤历史事件，避免旧库污染前端。
        rows=conn.execute("SELECT * FROM events ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END, CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, CASE WHEN COALESCE(source_count,0)>=2 THEN 0 ELSE 1 END, COALESCE(event_date,first_seen,last_seen,'') DESC, risk_score DESC, mention_count DESC LIMIT ?",(max(limit*4,limit),)).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            for k in ('keywords','translations'):
                try: d[k]=json.loads(d.get(k) or ('[]' if k=='keywords' else '{}'))
                except Exception: d[k]=[] if k=='keywords' else {}
            if subject_hit(d.get('title',''), d.get('summary',''), d.get('summary',''), '', d.get('keywords',[])):
                out.append(d)
            if len(out)>=limit: break
        return out


# ===================== 事件质量分级（事件中心治理，不删除原始数据）=====================
# 占位/待核提示类标题：并非真实事件，而是“暂无/待补原文/非商场”等系统备注，默认不在事件中心展示
_EVENT_NOISE_PATTERNS = (
    '无事件', '无明确事件', '其他', '无实质事件', '信息不足', '讨论提问帖', '招聘岗位信息',
)
def _event_title_is_noise(title):
    """判断事件标题是否为占位/待核/非商场本体的备注类噪音（不是真实舆情事件）"""
    t = (title or '').strip()
    if not t:
        return True
    if t in _EVENT_NOISE_PATTERNS:
        return True
    # “需补充/调取/获取原文…”“无明确风险事件…”“…非商场…”等备注句
    if t.startswith(('需补', '需获取', '需调取', '核查', '待补')):
        return True
    if t.startswith('无明确风险事件') or '非商场' in t:
        return True
    return False

def classify_event_quality(e):
    """事件质量三级：featured 重点事件 / generic 单篇泛化“相关讨论” / noise 占位备注"""
    title = (e.get('title') or '').strip()
    if _event_title_is_noise(title):
        return 'noise'
    try:
        mc = int(e.get('mention_count') or 1)
    except (TypeError, ValueError):
        mc = 1
    rl = e.get('risk_level')
    # 以“相关讨论”结尾、单篇提及且非中高风险的，归为泛化讨论（折叠展示，不与真事件抢注意力）
    if title.endswith('相关讨论') and mc <= 1 and rl not in ('high', 'medium'):
        return 'generic'
    return 'featured'

def get_events_curated(limit=50):
    """事件中心专用：在主体过滤基础上做质量分级。
    返回 {'featured':[...], 'generic_count':N, 'noise_count':N, 'total':N}。
    重点事件优先；泛化“相关讨论”只回传数量（前端折叠后按需展开），噪音备注默认隐藏。"""
    from subject_rules import subject_hit
    featured, generic_cnt, noise_cnt = [], 0, 0
    with get_db() as conn:
        # 多取再过滤/分级，排序口径与 get_events 一致（活跃→风险→多来源→时间）
        rows = conn.execute(
            "SELECT * FROM events ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END, "
            "CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
            "CASE WHEN COALESCE(source_count,0)>=2 THEN 0 ELSE 1 END, "
            "COALESCE(event_date,first_seen,last_seen,'') DESC, risk_score DESC, mention_count DESC LIMIT ?",
            (max(limit * 8, 200),)).fetchall()
        for r in rows:
            d = dict(r)
            for k in ('keywords', 'translations'):
                try:
                    d[k] = json.loads(d.get(k) or ('[]' if k == 'keywords' else '{}'))
                except Exception:
                    d[k] = [] if k == 'keywords' else {}
            if not subject_hit(d.get('title', ''), d.get('summary', ''), d.get('summary', ''), '', d.get('keywords', [])):
                continue
            q = classify_event_quality(d)
            if q == 'noise':
                noise_cnt += 1
            elif q == 'generic':
                generic_cnt += 1
                if len(featured) < limit:  # 泛化事件不进主列表，仅计数
                    pass
            else:
                d['quality'] = 'featured'
                featured.append(d)
            if len(featured) >= limit:
                break
    return {'featured': featured, 'generic_count': generic_cnt,
            'noise_count': noise_cnt, 'total': len(featured) + generic_cnt + noise_cnt}



def update_note_intelligence(note_id, data):
    with get_db() as conn:
        conn.execute('UPDATE notes SET relevance_status=?,verification_status=?,verification_confidence=?,fact_basis=?,ai_reason=?,event_hint=?,translations=? WHERE note_id=?',(
            data.get('relevance','relevant'),data.get('verification','review'),data.get('confidence',0.5),data.get('fact_basis','text'),data.get('risk_reason',''),data.get('event_hint',''),json.dumps(data.get('translations',{}),ensure_ascii=False),note_id))


def link_event_mentions(event_id, mentions):
    with get_db() as conn:
        for m in mentions:
            sid=m.get('source_id') or m.get('note_id') or m.get('url') or ''
            if not sid: continue
            st=m.get('source_platform','xhs')
            conn.execute('INSERT OR REPLACE INTO event_mentions(event_id,source_type,source_id,match_score) VALUES (?,?,?,?)',(event_id,st,sid,float(m.get('_match_score',1.0) or 1.0)))

# ===================== v5.3.2 AI过滤层 & 日报增强 数据操作 =====================

def update_note_ai_filter(note_id, filter_result, reason='', noise_type='', confidence=0.0, provider='rule', quality_score=0.5, is_duplicate=0, duplicate_of='', ai_insight=''):
    """更新笔记的AI过滤层状态。"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        conn.execute("""UPDATE notes SET ai_filter_status=?, ai_filter_reason=?, ai_filtered_at=?,
            content_quality_score=?, is_duplicate=?, duplicate_of=?, noise_type=?, ai_insight=?
            WHERE note_id=?""", (filter_result, reason, now, quality_score, is_duplicate, duplicate_of, noise_type, ai_insight, note_id))
        conn.execute("""INSERT INTO ai_filter_log(note_id, filter_stage, filter_result, filter_reason, noise_type, confidence, provider, filtered_at)
            VALUES (?,?,?,?,?,?,?,?)""", (note_id, 'secondary', filter_result, reason, noise_type, confidence, provider, now))

def get_pending_filter_notes(limit=500):
    """获取待AI二次过滤的笔记。"""
    with get_db() as conn:
        base,sp=_verified_base()
        rows = conn.execute(f"SELECT * FROM notes WHERE {base} AND (ai_filter_status='' OR ai_filter_status='pending' OR ai_filter_status IS NULL) ORDER BY id DESC LIMIT ?", tuple(sp)+(limit,)).fetchall()
        return [note_to_dict(r) for r in rows]

def get_filtered_notes(filter_result='accepted', limit=100, offset=0):
    """按AI过滤结果获取笔记。"""
    with get_db() as conn:
        base,sp=_verified_base()
        rows = conn.execute(f"SELECT * FROM notes WHERE {base} AND ai_filter_status=? ORDER BY COALESCE(publish_date, collected_at) DESC LIMIT ? OFFSET ?", tuple(sp)+(filter_result, limit, offset)).fetchall()
        return [note_to_dict(r) for r in rows]

def get_filter_stats():
    """获取AI过滤统计。"""
    with get_db() as conn:
        base,sp = _verified_base()
        total = conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base}",tuple(sp)).fetchone()['c']
        accepted = conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base} AND ai_filter_status='accepted'",tuple(sp)).fetchone()['c']
        rejected = conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base} AND ai_filter_status='rejected'",tuple(sp)).fetchone()['c']
        pending = conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base} AND (ai_filter_status='' OR ai_filter_status='pending' OR ai_filter_status IS NULL)",tuple(sp)).fetchone()['c']
        duplicates = conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base} AND is_duplicate=1",tuple(sp)).fetchone()['c']
        noise = conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base} AND noise_type!=''",tuple(sp)).fetchone()['c']
        return {'total': total, 'accepted': accepted, 'rejected': rejected, 'pending': pending, 'duplicates': duplicates, 'noise': noise}

def find_duplicate_notes(note, similarity_threshold=0.7):
    """基于标题和内容相似度查找潜在重复笔记（规则版，不依赖AI）。"""
    title = (note.get('title', '') or '').strip()
    content = (note.get('content', '') or '').strip()
    if not title and not content:
        return []
    # 简单关键词重叠匹配
    def keywords(text):
        import re
        words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text)
        return set(words[:50])
    kw1 = keywords(title + ' ' + content)
    if not kw1:
        return []
    with get_db() as conn:
        rows = conn.execute("""SELECT note_id, title, content FROM notes
            WHERE is_taikoo_verified=1 AND note_id != ?
            AND COALESCE(relevance_status,'relevant')!='irrelevant'
            ORDER BY id DESC LIMIT 200""", (note.get('note_id', ''),)).fetchall()
    duplicates = []
    for r in rows:
        kw2 = keywords((r['title'] or '') + ' ' + (r['content'] or ''))
        if not kw2:
            continue
        overlap = len(kw1 & kw2)
        union = len(kw1 | kw2)
        sim = overlap / union if union > 0 else 0
        if sim >= similarity_threshold:
            duplicates.append({'note_id': r['note_id'], 'title': r['title'], 'similarity': round(sim, 3)})
    return duplicates[:10]

def save_daily_digest(digest):
    """保存每日摘要（增强版日报）。"""
    with get_db() as conn:
        vals = (
            digest.get('digest_date', ''),
            digest.get('total_found', 0), digest.get('effective_count', 0),
            digest.get('positive_count', 0), digest.get('neutral_count', 0), digest.get('risk_count', 0),
            digest.get('risk_index', 0), digest.get('brand_health_score', 0),
            digest.get('ai_summary', ''), digest.get('executive_summary', ''),
            json.dumps(digest.get('key_insights', []), ensure_ascii=False),
            json.dumps(digest.get('action_items', []), ensure_ascii=False),
            json.dumps(digest.get('top_events', []), ensure_ascii=False),
        )
        existing = conn.execute('SELECT id FROM daily_digest WHERE digest_date=?', (vals[0],)).fetchone()
        if existing:
            conn.execute("""UPDATE daily_digest SET total_found=?, effective_count=?, positive_count=?, neutral_count=?, risk_count=?,
                risk_index=?, brand_health_score=?, ai_summary=?, executive_summary=?, key_insights=?, action_items=?, top_events=?,
                generated_at=datetime('now','localtime') WHERE digest_date=?""", vals[1:] + (vals[0],))
            return existing['id']
        cur = conn.execute("""INSERT INTO daily_digest(digest_date, total_found, effective_count, positive_count, neutral_count, risk_count,
            risk_index, brand_health_score, ai_summary, executive_summary, key_insights, action_items, top_events)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
        return cur.lastrowid

def get_latest_digest(date_str=None):
    """获取最新每日摘要。"""
    with get_db() as conn:
        if date_str:
            row = conn.execute('SELECT * FROM daily_digest WHERE digest_date=?', (date_str,)).fetchone()
        else:
            row = conn.execute('SELECT * FROM daily_digest ORDER BY digest_date DESC LIMIT 1').fetchone()
        if not row:
            return None
        d = dict(row)
        for k in ('key_insights', 'action_items', 'top_events'):
            try: d[k] = json.loads(d.get(k) or '[]')
            except Exception: d[k] = []
        return d

def save_event_insight(event_id, insight):
    """保存事件AI洞察。"""
    with get_db() as conn:
        conn.execute("""INSERT INTO event_insights(event_id, ai_summary, risk_assessment, recommended_action, sentiment_trend,
            propagation_analysis, key_voices, provider) VALUES (?,?,?,?,?,?,?,?)""", (
            event_id, insight.get('ai_summary', ''), insight.get('risk_assessment', ''),
            insight.get('recommended_action', ''), insight.get('sentiment_trend', ''),
            insight.get('propagation_analysis', ''),
            json.dumps(insight.get('key_voices', []), ensure_ascii=False),
            insight.get('provider', 'rule')))

def get_event_insight(event_id):
    """获取事件最新AI洞察。"""
    with get_db() as conn:
        row = conn.execute('SELECT * FROM event_insights WHERE event_id=? ORDER BY id DESC LIMIT 1', (event_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try: d['key_voices'] = json.loads(d.get('key_voices') or '[]')
        except Exception: d['key_voices'] = []
        return d

def get_effective_notes_count(date_str=None):
    """获取有效舆情数量（通过AI过滤层accepted的）。"""
    with get_db() as conn:
        base,sp = _verified_base()
        base += " AND ai_filter_status='accepted'"
        if date_str:
            base += " AND publish_date=?"
            return conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base}", tuple(sp)+(date_str,)).fetchone()['c']
        return conn.execute(f"SELECT COUNT(*) c FROM notes WHERE {base}", tuple(sp)).fetchone()['c']

# ===== v5.3.2 live collector additive helpers =====
def save_collector_quality(note_id, quality):
    """保存采集质量审计信息；不修改主体判定。"""
    with get_db() as conn:
        conn.execute("""INSERT INTO collector_quality_log
            (note_id,status,score,detail_status,comments_collected,collector_version,checked_at,reason)
            VALUES (?,?,?,?,?,?,?,?)""", (
            str(note_id), quality.get('status','unknown'), float(quality.get('score',0) or 0),
            quality.get('detail_status',''), int(quality.get('comments_collected',0) or 0),
            quality.get('collector_version','xhs-live-v1'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            quality.get('reason','') or ''))


def upsert_note_comments(note_id, comments):
    """增量保存评论快照；comment_id 唯一，保留最新抓取信息。"""
    with get_db() as conn:
        for c in comments or []:
            cid = str(c.get('comment_id') or '').strip()
            if not cid:
                continue
            conn.execute("""INSERT INTO note_comments
                (comment_id,note_id,content,author_id,author_nickname,likes,publish_time,parent_id,raw_json,fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(comment_id) DO UPDATE SET
                  content=excluded.content, likes=excluded.likes, publish_time=excluded.publish_time,
                  raw_json=excluded.raw_json, fetched_at=excluded.fetched_at""", (
                cid, str(note_id), c.get('content','') or '', c.get('author_id','') or '',
                c.get('author_nickname','') or '', int(c.get('likes',0) or 0), c.get('publish_time','') or '',
                c.get('parent_id','') or '', json.dumps(c.get('raw_data',{}), ensure_ascii=False),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
