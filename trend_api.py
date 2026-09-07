"""
ZBC 统一时间序列趋势API v1.0
全局趋势线数据源：笔记/事件/风险/KOS/互动量，全部按发布日期(publish_datetime)聚合。
函数驱动：SQL聚合 → Canonical格式 → xujing-viz FN_TREND_SERIES → 页面SVG趋势线。
"""
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

trend_bp = Blueprint('trend', __name__)

DB_PATH = 'data/monitor.db'

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _date_range(days=30):
    """生成日期范围，确保无数据的日期也显示0。"""
    end = datetime.now().date()
    start = end - timedelta(days=days-1)
    dates = []
    d = start
    while d <= end:
        dates.append(d.isoformat())
        d += timedelta(days=1)
    return dates

def _fill_zeros(data_by_date, dates, metric='count'):
    """填充无数据日期为0，按日期排序。"""
    result = []
    for d in dates:
        val = data_by_date.get(d, 0)
        result.append({'date': d, 'label': d[5:], metric: val, 'total': val if metric == 'count' else val})
    return result

@trend_bp.route('/api/trend/notes')
def trend_notes():
    """笔记发布趋势 - 按publish_datetime聚合。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    platform = request.args.get('platform', '').strip()
    domain = request.args.get('domain', '').strip()

    conn = _get_db()
    try:
        q = "SELECT DATE(publish_datetime) as d, COUNT(*) as cnt FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != ''"
        params = []
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

    dates = _date_range(days)
    series = _fill_zeros(data_by_date, dates)
    return jsonify({'ok': True, 'metric': 'notes', 'days': days, 'series': series})

@trend_bp.route('/api/trend/events')
def trend_events():
    """事件趋势 - 按事件开始/发现时间聚合。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        # 尝试不同的时间字段
        for col in ['start_time', 'discovered_at', 'created_at', 'first_seen_at']:
            try:
                rows = conn.execute(f"SELECT DATE({col}) as d, COUNT(*) as cnt FROM events WHERE {col} IS NOT NULL GROUP BY d").fetchall()
                if rows:
                    break
            except:
                continue
        else:
            rows = []
        data_by_date = {r['d']: r['cnt'] for r in rows}
    finally:
        conn.close()

    dates = _date_range(days)
    series = _fill_zeros(data_by_date, dates)
    return jsonify({'ok': True, 'metric': 'events', 'days': days, 'series': series})

@trend_bp.route('/api/trend/risk')
def trend_risk():
    """风险趋势 - 按风险记录时间聚合，分high/medium/low。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        # 尝试风险表
        for table in ['risk_records', 'risks', 'note_risk_log']:
            try:
                for col in ['created_at', 'detected_at', 'risk_time']:
                    try:
                        rows = conn.execute(f"SELECT DATE({col}) as d, risk_level, COUNT(*) as cnt FROM {table} WHERE {col} IS NOT NULL GROUP BY d, risk_level").fetchall()
                        if rows:
                            break
                    except:
                        continue
                if rows:
                    break
            except:
                continue
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

@trend_bp.route('/api/trend/engagement')
def trend_engagement():
    """互动量趋势 - 按发布日期聚合点赞+评论+收藏+分享。"""
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

@trend_bp.route('/api/trend/kos')
def trend_kos():
    """KOS达人内容趋势 - 按发布日期聚合KOS相关笔记。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        # KOS笔记：subject_type包含kos或author在kos_profiles中
        q = """SELECT DATE(n.publish_datetime) as d, COUNT(*) as cnt
               FROM notes n
               WHERE n.publish_datetime IS NOT NULL AND n.publish_datetime != ''
               AND (n.subject_type LIKE '%kos%' OR n.subject_type LIKE '%kol%' OR n.subject_type LIKE '%koc%')
               GROUP BY d ORDER BY d"""
        rows = conn.execute(q).fetchall()
        data_by_date = {r['d']: r['cnt'] for r in rows}
    finally:
        conn.close()

    dates = _date_range(days)
    series = _fill_zeros(data_by_date, dates)
    return jsonify({'ok': True, 'metric': 'kos', 'days': days, 'series': series})

@trend_bp.route('/api/trend/sentiment')
def trend_sentiment():
    """情感趋势 - 按发布日期聚合正面/中性/负面。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    conn = _get_db()
    try:
        for col in ['sentiment', 'sentiment_label', 'emotion']:
            try:
                rows = conn.execute(f"""SELECT DATE(publish_datetime) as d, {col} as s, COUNT(*) as cnt
                    FROM notes WHERE publish_datetime IS NOT NULL AND {col} IS NOT NULL AND {col} != ''
                    GROUP BY d, {col}""").fetchall()
                if rows:
                    break
            except:
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

@trend_bp.route('/api/trend/overview')
def trend_overview():
    """全局概览趋势 - 一次性返回笔记/事件/风险/互动的时间序列。"""
    days = min(90, max(7, int(request.args.get('days', 30))))
    # 复用各API逻辑但合并
    notes_data = _get_notes_series(days)
    engagement_data = _get_engagement_series(days)
    return jsonify({
        'ok': True, 'days': days,
        'notes': notes_data,
        'engagement': engagement_data
    })

def _get_notes_series(days):
    conn = _get_db()
    try:
        rows = conn.execute("SELECT DATE(publish_datetime) as d, COUNT(*) as cnt FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != '' GROUP BY d").fetchall()
        data_by_date = {r['d']: r['cnt'] for r in rows}
    finally:
        conn.close()
    return _fill_zeros(data_by_date, _date_range(days))

def _get_engagement_series(days):
    conn = _get_db()
    try:
        rows = conn.execute("""SELECT DATE(publish_datetime) as d,
            COALESCE(SUM(likes),0)+COALESCE(SUM(comments),0)+COALESCE(SUM(collects),0)+COALESCE(SUM(shares),0) as total
            FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != '' GROUP BY d""").fetchall()
        data_by_date = {r['d']: r['total'] for r in rows}
    finally:
        conn.close()
    return _fill_zeros(data_by_date, _date_range(days))
