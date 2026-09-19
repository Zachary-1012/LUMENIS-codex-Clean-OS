"""
ZBC 统一时间序列趋势API v1.1
全局趋势线数据源：笔记/事件/风险/KOS/互动量，全部按发布日期(publish_datetime)聚合。
函数驱动：SQL聚合 → Canonical格式 → xujing-viz FN_TREND_SERIES → 页面SVG趋势线。

v1.1 变更（P0 修复）：
- P0-1：所有 notes 表查询追加主体过滤（委托 subject_rules.subject_sql_and_values）
- P0-2：所有查询追加日期范围约束（SQL 层限定天数，而非 Python 端裁剪）
- P1-6：trend_notes 与 _get_notes_series 去重，trend_notes 委托 _get_notes_series
- P1-8：动态列名/表名使用白名单校验，裸 except 改为 except Exception + log warning
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from lumenis.shared.database import get_repository, main_db_path

from subject_rules import subject_sql_and_values, get_brand_config, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS

logger = logging.getLogger(__name__)

trend_bp = Blueprint('trend', __name__)

DB_PATH = main_db_path()

# ============================================================
# 白名单：动态列名 / 表名（P1-8：防 SQL 注入）
# ============================================================
_EVENT_TIME_COLUMNS = frozenset({'start_time', 'discovered_at', 'created_at', 'first_seen_at',
                                   'event_date', 'first_seen', 'last_seen', 'negative_confirmed_at'})
_RISK_TABLES = frozenset({'risk_records', 'risks', 'note_risk_log', 'events'})
_RISK_TIME_COLUMNS = frozenset({'created_at', 'detected_at', 'risk_time', 'event_date', 'first_seen'})
# 每张风险表优先尝试的时间列（Phase3：events 表实际存储 risk_level，优先 event_date）
_RISK_TABLE_COLUMNS = {
    'events': ['event_date', 'first_seen'],
    'risk_records': ['created_at', 'detected_at', 'risk_time'],
    'risks': ['created_at', 'detected_at', 'risk_time'],
    'note_risk_log': ['created_at', 'detected_at', 'risk_time'],
}
_SENTIMENT_COLUMNS = frozenset({'sentiment', 'sentiment_label', 'emotion'})

# 主体过滤所需字段（用于非 notes 表的安全降级）
_SUBJECT_FIELDS = ('title', 'body', 'content', 'source_keyword', 'matched_keywords')


def _get_db():
    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    return conn


def _date_range(days=30):
    """生成日期范围，确保无数据的日期也显示0。"""
    end = datetime.now().date()
    start = end - timedelta(days=days - 1)
    dates = []
    d = start
    while d <= end:
        dates.append(d.isoformat())
        d += timedelta(days=1)
    return dates


def _days_offset(days):
    """SQLite date() 偏移参数：覆盖 days 天（含今天），即回溯 days-1 天。"""
    return f'-{days - 1} days'


def _fill_zeros(data_by_date, dates, metric='count'):
    """填充无数据日期为0，按日期排序。"""
    result = []
    for d in dates:
        val = data_by_date.get(d, 0)
        result.append({'date': d, 'label': d[5:], metric: val, 'total': val if metric == 'count' else val})
    return result


def _subject_clause(alias=''):
    """统一主体过滤：委托 subject_rules.subject_sql_and_values（P0-1）。
    适用于 notes 表（含全部主体字段）。"""
    return subject_sql_and_values(alias)


def _safe_subject_clause(conn, table, alias=''):
    """对非 notes 表安全应用主体过滤（P0-1 降级）。

    events / risk 表可能不具备全部 5 个主体字段。
    仅当表至少拥有 title 列时，基于实际存在的列生成简化主体过滤；
    否则返回空（数据在创建时已通过 notes 主体边界化）。
    """
    try:
        existing = {r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    except Exception as e:
        logger.warning('[trend] _safe_subject_clause PRAGMA failed for %s: %s', table, e)
        return '', []
    usable = [f for f in _SUBJECT_FIELDS if f in existing]
    if 'title' not in usable:
        return '', []
    cfg = get_brand_config()
    sw = cfg.get('subject_words', SUBJECT_WORDS)
    ew = cfg.get('exclude_words', SUBJECT_EXCLUDE_WORDS)
    prefix = f'{alias}.' if alias else ''
    positives = []
    values = []
    for field in usable:
        for word in sw:
            positives.append(f"LOWER(COALESCE({prefix}{field}, '')) LIKE ?")
            values.append(f'%{word.lower()}%')
    excludes = []
    for field in usable:
        for word in ew:
            excludes.append(f"LOWER(COALESCE({prefix}{field}, '')) LIKE ?")
            values.append(f'%{word.lower()}%')
    clause = f"({' OR '.join(positives)}) AND NOT ({' OR '.join(excludes)})"
    return clause, values


# ============================================================
# 笔记趋势
# ============================================================
@trend_bp.route('/api/trend/notes')
def trend_notes():
    """笔记发布趋势 - 按publish_datetime聚合。
    P1-6：委托 _get_notes_series，消除重复 SQL。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    platform = request.args.get('platform', '').strip()
    domain = request.args.get('domain', '').strip()
    series = _get_notes_series(days, platform=platform, domain=domain)
    return jsonify({'ok': True, 'metric': 'notes', 'days': days, 'series': series})


def _get_notes_series(days, platform='', domain=''):
    """笔记时间序列（P0-1 主体过滤 + P0-2 日期范围）。
    供 trend_notes 与 trend_overview 复用（P1-6 去重）。"""
    conn = _get_db()
    try:
        q = "SELECT DATE(publish_datetime) as d, COUNT(*) as cnt FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != ''"
        params = []
        # P0-2：SQL 层日期范围约束
        q += " AND date(publish_datetime) >= date('now', ?)"
        params.append(_days_offset(days))
        # P0-1：主体过滤
        subj_sql, subj_vals = _subject_clause()
        q += f" AND {subj_sql}"
        params.extend(subj_vals)
        if platform:
            q += " AND source_platform = ?"
            params.append(platform)
        if domain:
            q += " AND subject_type = ?"
            params.append(domain)
        q += " GROUP BY d ORDER BY d"
        rows = conn.execute(q, params).fetchall()
        data_by_date = {r['d']: r['cnt'] for r in rows}
    finally:
        conn.close()
    return _fill_zeros(data_by_date, _date_range(days))


# ============================================================
# 事件趋势
# ============================================================
@trend_bp.route('/api/trend/events')
def trend_events():
    """事件趋势 - 按事件开始/发现时间聚合。
    P0-2：日期范围约束；P1-8：列名白名单 + 异常日志。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        rows = []
        # P0-1：events 表安全主体过滤（降级）
        subj_sql, subj_vals = _safe_subject_clause(conn, 'events')
        # Phase3：优先 events 表实际存在的时间列，旧列名向后兼容
        for col in ['event_date', 'first_seen', 'last_seen', 'negative_confirmed_at',
                    'start_time', 'discovered_at', 'created_at', 'first_seen_at']:
            if col not in _EVENT_TIME_COLUMNS:
                continue
            try:
                q = f"SELECT DATE({col}) as d, COUNT(*) as cnt FROM events WHERE {col} IS NOT NULL"
                params = []
                # P0-2：日期范围
                q += f" AND date({col}) >= date('now', ?)"
                params.append(_days_offset(days))
                if subj_sql:
                    q += f" AND {subj_sql}"
                    params.extend(subj_vals)
                q += " GROUP BY d ORDER BY d"
                rows = conn.execute(q, params).fetchall()
                if rows:
                    break
            except Exception as e:
                logger.warning('[trend/events] column %s query failed: %s', col, e)
                continue
        data_by_date = {r['d']: r['cnt'] for r in rows}
    finally:
        conn.close()

    dates = _date_range(days)
    series = _fill_zeros(data_by_date, dates)
    return jsonify({'ok': True, 'metric': 'events', 'days': days, 'series': series})


# ============================================================
# 风险趋势
# ============================================================
@trend_bp.route('/api/trend/risk')
def trend_risk():
    """风险趋势 - 按风险记录时间聚合，分high/medium/low。
    P0-2：日期范围约束；P1-8：表名/列名白名单 + 异常日志。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        rows = []
        # Phase3：events 表实际存储 risk_level（461行），优先查；旧空表向后兼容
        for table in ['events', 'risk_records', 'risks', 'note_risk_log']:
            if table not in _RISK_TABLES:
                continue
            # P0-1：risk 表安全主体过滤（降级）
            subj_sql, subj_vals = _safe_subject_clause(conn, table)
            found = False
            for col in _RISK_TABLE_COLUMNS.get(table, []):
                if col not in _RISK_TIME_COLUMNS:
                    continue
                try:
                    q = f"SELECT DATE({col}) as d, risk_level, COUNT(*) as cnt FROM {table} WHERE {col} IS NOT NULL"
                    params = []
                    # P0-2：日期范围
                    q += f" AND date({col}) >= date('now', ?)"
                    params.append(_days_offset(days))
                    if subj_sql:
                        q += f" AND {subj_sql}"
                        params.extend(subj_vals)
                    q += " GROUP BY d, risk_level ORDER BY d"
                    rows = conn.execute(q, params).fetchall()
                    if rows:
                        found = True
                        break
                except Exception as e:
                    logger.warning('[trend/risk] table=%s col=%s query failed: %s', table, col, e)
                    continue
            if found:
                break
        else:
            rows = []

        # 按日期和风险等级组织
        by_date = {}
        for r in rows:
            d = r['d']
            level = r['risk_level'] if 'risk_level' in r.keys() else 'medium'
            if d not in by_date:
                by_date[d] = {'high': 0, 'medium': 0, 'low': 0, 'critical': 0}
            by_date[d][level] = by_date[d].get(level, 0) + r['cnt']
    finally:
        conn.close()

    dates = _date_range(days)
    series = []
    for d in dates:
        levels = by_date.get(d, {'high': 0, 'medium': 0, 'low': 0, 'critical': 0})
        total = sum(levels.values())
        series.append({
            'date': d, 'label': d[5:],
            'high': levels.get('high', 0),
            'medium': levels.get('medium', 0),
            'low': levels.get('low', 0),
            'critical': levels.get('critical', 0),
            'total': total
        })
    return jsonify({'ok': True, 'metric': 'risk', 'days': days, 'series': series})


# ============================================================
# 互动量趋势
# ============================================================
@trend_bp.route('/api/trend/engagement')
def trend_engagement():
    """互动量趋势 - 按发布日期聚合点赞+评论+收藏+分享。
    P0-1 主体过滤 + P0-2 日期范围。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    platform = request.args.get('platform', '').strip()
    conn = _get_db()
    try:
        q = """SELECT DATE(publish_datetime) as d,
               COALESCE(SUM(likes),0) as likes,
               COALESCE(SUM(comments),0) as comments,
               COALESCE(SUM(collects),0) as collects,
               COALESCE(SUM(shares),0) as shares
               FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != ''"""
        params = []
        # P0-2：日期范围
        q += " AND date(publish_datetime) >= date('now', ?)"
        params.append(_days_offset(days))
        # P0-1：主体过滤
        subj_sql, subj_vals = _subject_clause()
        q += f" AND {subj_sql}"
        params.extend(subj_vals)
        if platform:
            q += " AND source_platform = ?"
            params.append(platform)
        q += " GROUP BY d ORDER BY d"
        rows = conn.execute(q, params).fetchall()
        data_by_date = {r['d']: {
            'likes': r['likes'], 'comments': r['comments'],
            'collects': r['collects'], 'shares': r['shares'],
            'total': r['likes'] + r['comments'] + r['collects'] + r['shares']
        } for r in rows}
    finally:
        conn.close()

    dates = _date_range(days)
    series = []
    for d in dates:
        e = data_by_date.get(d, {'likes': 0, 'comments': 0, 'collects': 0, 'shares': 0, 'total': 0})
        series.append({'date': d, 'label': d[5:], **e})
    return jsonify({'ok': True, 'metric': 'engagement', 'days': days, 'series': series})


# ============================================================
# KOS 达人内容趋势
# ============================================================
@trend_bp.route('/api/trend/kos')
def trend_kos():
    """KOS达人内容趋势 - 按发布日期聚合KOS相关笔记。
    P0-1 主体过滤 + P0-2 日期范围。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        # KOS笔记：author在kos_profiles(is_kos=1) 或 subject_type标记为kos/kol/koc
        q = """SELECT DATE(n.publish_datetime) as d, COUNT(*) as cnt
               FROM notes n
               LEFT JOIN kos_profiles k ON n.author_id = k.author_id
               WHERE n.publish_datetime IS NOT NULL AND n.publish_datetime != ''"""
        params = []
        # P0-2：日期范围
        q += " AND date(n.publish_datetime) >= date('now', ?)"
        params.append(_days_offset(days))
        # P0-1：主体过滤（使用别名 n）
        subj_sql, subj_vals = _subject_clause(alias='n')
        q += f" AND {subj_sql}"
        params.extend(subj_vals)
        # Phase3：JOIN kos_profiles 后按 is_kos=1 过滤，兼容 subject_type 标记
        q += """ AND (k.is_kos = 1 OR n.subject_type LIKE '%kos%' OR n.subject_type LIKE '%kol%' OR n.subject_type LIKE '%koc%')
               GROUP BY d ORDER BY d"""
        rows = conn.execute(q, params).fetchall()
        data_by_date = {r['d']: r['cnt'] for r in rows}
    finally:
        conn.close()

    dates = _date_range(days)
    series = _fill_zeros(data_by_date, dates)
    return jsonify({'ok': True, 'metric': 'kos', 'days': days, 'series': series})


# ============================================================
# 情感趋势
# ============================================================
@trend_bp.route('/api/trend/sentiment')
def trend_sentiment():
    """情感趋势 - 按发布日期聚合正面/中性/负面。
    P0-1 主体过滤 + P0-2 日期范围 + P1-8 列名白名单。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        rows = []
        for col in ['sentiment', 'sentiment_label', 'emotion']:
            if col not in _SENTIMENT_COLUMNS:
                continue
            try:
                q = f"""SELECT DATE(publish_datetime) as d, {col} as s, COUNT(*) as cnt
                    FROM notes WHERE publish_datetime IS NOT NULL AND {col} IS NOT NULL AND {col} != ''"""
                params = []
                # P0-2：日期范围
                q += " AND date(publish_datetime) >= date('now', ?)"
                params.append(_days_offset(days))
                # P0-1：主体过滤
                subj_sql, subj_vals = _subject_clause()
                q += f" AND {subj_sql}"
                params.extend(subj_vals)
                q += f" GROUP BY d, {col} ORDER BY d"
                rows = conn.execute(q, params).fetchall()
                if rows:
                    break
            except Exception as e:
                logger.warning('[trend/sentiment] column %s query failed: %s', col, e)
                continue
        else:
            rows = []

        by_date = {}
        for r in rows:
            d = r['d']
            s = (r['s'] or '').lower()
            if d not in by_date:
                by_date[d] = {'positive': 0, 'neutral': 0, 'negative': 0}
            if 'pos' in s or s in ('正面', 'positive'):
                by_date[d]['positive'] += r['cnt']
            elif 'neg' in s or s in ('负面', 'negative'):
                by_date[d]['negative'] += r['cnt']
            else:
                by_date[d]['neutral'] += r['cnt']
    finally:
        conn.close()

    dates = _date_range(days)
    series = []
    for d in dates:
        s = by_date.get(d, {'positive': 0, 'neutral': 0, 'negative': 0})
        total = sum(s.values())
        series.append({'date': d, 'label': d[5:], **s, 'total': total})
    return jsonify({'ok': True, 'metric': 'sentiment', 'days': days, 'series': series})


# ============================================================
# 全局概览趋势
# ============================================================
@trend_bp.route('/api/trend/overview')
def trend_overview():
    """全局概览趋势 - 一次性返回笔记/事件/风险/互动的时间序列。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    # 复用各 API 逻辑但合并
    notes_data = _get_notes_series(days)
    engagement_data = _get_engagement_series(days)
    return jsonify({
        'ok': True, 'days': days,
        'notes': notes_data,
        'engagement': engagement_data
    })


def _get_engagement_series(days):
    """互动量时间序列（P0-1 主体过滤 + P0-2 日期范围）。
    供 trend_overview 复用。"""
    conn = _get_db()
    try:
        q = """SELECT DATE(publish_datetime) as d,
            COALESCE(SUM(likes),0)+COALESCE(SUM(comments),0)+COALESCE(SUM(collects),0)+COALESCE(SUM(shares),0) as total
            FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != ''"""
        params = []
        # P0-2：日期范围
        q += " AND date(publish_datetime) >= date('now', ?)"
        params.append(_days_offset(days))
        # P0-1：主体过滤
        subj_sql, subj_vals = _subject_clause()
        q += f" AND {subj_sql}"
        params.extend(subj_vals)
        q += " GROUP BY d ORDER BY d"
        rows = conn.execute(q, params).fetchall()
        data_by_date = {r['d']: r['total'] for r in rows}
    finally:
        conn.close()
    return _fill_zeros(data_by_date, _date_range(days))
