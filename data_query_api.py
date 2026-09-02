# -*- coding: utf-8 -*-
"""数据查询 API 蓝图（app.py 巨石拆分 · 第 1 批，P1-10）。

只搬迁“纯只读、仅依赖 database 模块 + Flask”的查询接口，函数体零逻辑改动。
显式保留原 endpoint 名（endpoint='api_xxx'），确保 url_for / OpenAPI operationId 零变更。
后续批次（采集控制/报告/AI/运维）按 docs/APP-REFACTOR-PLAN.md 继续。
"""
from __future__ import annotations

import database as db
from flask import Blueprint, jsonify, request


def register_data_query_api(app):
    """在 Flask app 上注册数据只读查询蓝图。"""
    bp = Blueprint("data_query", __name__)

    @bp.route('/api/stats', endpoint='api_stats')
    def api_stats():
        return jsonify({'ok': True, 'stats': db.get_stats(),
                        'top_topics': [{'topic': t, 'count': c} for t, c in db.get_top_topics(12)],
                        'categories': db.get_category_distribution()})

    @bp.route('/api/notes', endpoint='api_notes')
    def api_notes():
        try:
            page = max(1, int(request.args.get('page', 1)))
            per_page = max(1, min(100, int(request.args.get('per_page', 20))))
        except ValueError:
            return jsonify({'ok': False, 'error': 'page/per_page 必须为整数'}), 400
        filters = {}
        for key in ('sentiment', 'risk_level', 'category', 'keyword', 'date_start', 'date_end'):
            v = request.args.get(key, '')
            if v:
                filters[key] = v
        if request.args.get('is_official') in ('0', '1'):
            filters['is_official'] = request.args.get('is_official') == '1'
        if request.args.get('verified') in ('0', '1'):
            filters['verified'] = request.args.get('verified') == '1'
        # GAP-06 双维度筛选透传（非法枚举在 _apply_filters 白名单内被忽略）
        for _dim in ('subject_type', 'content_type'):
            _dv = request.args.get(_dim, '')
            if _dv:
                filters[_dim] = _dv
        offset = (page - 1) * per_page
        notes = db.get_notes(filters, per_page, offset)
        total = db.get_note_count(filters)
        return jsonify({'ok': True, 'notes': notes, 'total': total, 'page': page,
                        'per_page': per_page, 'total_pages': (total + per_page - 1) // per_page})

    @bp.route('/api/risk-alerts', endpoint='api_risk_alerts')
    def api_risk_alerts():
        return jsonify({'ok': True, 'notes': db.get_high_risk_notes(30)})

    @bp.route('/api/hot-notes', endpoint='api_hot_notes')
    def api_hot_notes():
        return jsonify({'ok': True, 'notes': db.get_hot_notes(10)})

    @bp.route('/api/comments', endpoint='api_comments')
    def api_comments():
        limit = max(1, min(200, request.args.get('limit', 50, type=int)))
        c = db.get_negative_comments(limit)
        return jsonify({'comments': c, 'total': len(c)})

    @bp.route('/api/events', endpoint='api_events')
    def api_events():
        # 默认质量分级：重点事件进主列表，单篇泛化“相关讨论”只回传折叠计数，占位备注隐藏；?include=all 可看全部
        if request.args.get('include') == 'all':
            events = db.get_events(200)
            return jsonify({'ok': True, 'events': events, 'total': len(events), 'mode': 'all'})
        cur = db.get_events_curated(50)
        return jsonify({'ok': True, 'events': cur['featured'], 'total': cur['total'],
                        'generic_count': cur['generic_count'], 'noise_count': cur['noise_count'],
                        'scope': 'cross-platform discovery + Xiaohongshu follow-up', 'mode': 'curated'})

    @bp.route('/api/web-mentions', endpoint='api_web_mentions')
    def api_web_mentions():
        limit = max(1, min(200, request.args.get('limit', 50, type=int)))
        return jsonify({'ok': True, 'mentions': db.get_web_mentions(limit, True)})

    @bp.route('/api/feedback-keywords', endpoint='api_feedback_keywords')
    def api_feedback_keywords():
        return jsonify({'ok': True, 'keywords': db.get_feedback_keywords(30)})

    @bp.route('/api/hot-topics', endpoint='api_hot_topics')
    def api_hot_topics():
        limit = max(1, min(30, request.args.get('limit', 12, type=int)))
        return jsonify({'ok': True, 'topics': db.get_hot_topics(limit)})

    @bp.route('/api/metric-trend', endpoint='api_metric_trend')
    def api_metric_trend():
        # 指标快照时间序列（BASELINE §9/§11/§12）：只读，供报告/前端动态可视化绑定真实数据
        entity_type = request.args.get('entity_type', 'note')
        entity_key = request.args.get('entity_key', '').strip()
        if entity_type not in ('note', 'topic') or not entity_key:
            return jsonify({'ok': False, 'error': 'entity_type must be note|topic and entity_key required'}), 400
        limit = max(1, min(1000, request.args.get('limit', 200, type=int)))
        rows = db.get_metric_trend(entity_type, entity_key, limit)
        return jsonify({'ok': True, 'entity_type': entity_type, 'entity_key': entity_key,
                        'points': len(rows), 'trend': rows})

    app.register_blueprint(bp)
    return bp
