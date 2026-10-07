# -*- coding: utf-8 -*-
"""数据查询 API 蓝图（app.py 巨石拆分 · 第 1 批，P1-10）。

只搬迁“纯只读、仅依赖 database 模块 + Flask”的查询接口，函数体零逻辑改动。
显式保留原 endpoint 名（endpoint='api_xxx'），确保 url_for / OpenAPI operationId 零变更。
后续批次（采集控制/报告/AI/运维）按 docs/APP-REFACTOR-PLAN.md 继续。
"""
from __future__ import annotations

import database as db
import json
from flask import Blueprint, jsonify, request
from lumenis.system.collector.guard.resource_guard import ResourceGuard

_resource_guard = ResourceGuard()  # P0-G 统一资源守卫（只读决策，无共享状态）


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

    # P0 断链兼容路由：保留两个旧 URL，但风险读取必须有显式业务域，
    # 并复用当前 Permission + Canonical owner；不能把跨域 GLOBAL 映射成旧 notes 查询。
    @bp.route('/api/risks/active', endpoint='api_risks_active')
    @bp.route('/api/risk/active', endpoint='api_risk_active')
    def api_risks_active():
        """读取所选业务域中已授权 Canonical 投影的活跃风险记录。"""
        limit = max(1, min(200, request.args.get('limit', 50, type=int)))
        try:
            # This legacy URL is neutral across CTH/BMP. Requiring an explicit
            # domain keeps GLOBAL / ALL from silently selecting a CTH policy or
            # reading the unscoped legacy notes table.
            import lumenis_app_api
            domain = lumenis_app_api._get_domain_context()
            if domain is None:
                return jsonify({
                    'ok': False,
                    'code': 'DOMAIN_SELECTION_REQUIRED',
                    'error': 'Select CTH or BMP before reading active risks.',
                    'risks': None,
                    'total': None,
                    'selection_required': True,
                }), 400

            # Resolve the existing domain risk policy as an explicit support
            # check; records themselves remain sourced from scoped Canonical.
            from risk_engine import get_risk_policy
            policy = get_risk_policy(domain)
            scope, canonical = lumenis_app_api._domain_api_canonical(domain, 'reports')
            records = canonical.get('records', [])
            active_levels = {'critical', 'high', 'medium', '严重', '高', '中'}
            risk_candidates = [
                row for row in records
                if isinstance(row.get('risk_level'), str)
                and row['risk_level'].strip().lower() in active_levels
            ]

            # Preserve the established human-dismissal behavior, but only for
            # note IDs already selected by the signed Canonical scope read.
            # Non-note rows or an inconsistent source reference cannot safely
            # inherit a note review state, so fail closed rather than surface a
            # possibly dismissed record as active.
            review_ids = []
            for row in risk_candidates:
                source_id = row.get('source_id')
                raw_ref = row.get('raw_ref')
                try:
                    source_ref = json.loads(raw_ref) if isinstance(raw_ref, str) else None
                except (TypeError, ValueError):
                    source_ref = None
                if (
                    row.get('source_type') != 'note'
                    or row.get('source_table') != 'notes'
                    or not isinstance(source_id, str) or not source_id.strip()
                    or row.get('external_id') != source_id
                    or not isinstance(source_ref, dict)
                    or source_ref.get('table') != 'notes'
                    or source_ref.get('note_id') != source_id
                ):
                    return jsonify({
                        'ok': False,
                        'code': 'RISK_DISMISSAL_SOURCE_MAPPING_UNAVAILABLE',
                        'error': 'Canonical risk source cannot be matched safely to its review state.',
                        'risks': None,
                        'total': None,
                        'data_state': 'UNAVAILABLE',
                    }), 503
                review_ids.append(source_id)

            if risk_candidates:
                try:
                    review_states = db.get_high_risk_note_dismissal_states(review_ids)
                except Exception:
                    return jsonify({
                        'ok': False,
                        'code': 'RISK_DISMISSAL_STATE_UNAVAILABLE',
                        'error': 'The existing note review state could not be read.',
                        'risks': None,
                        'total': None,
                        'data_state': 'UNAVAILABLE',
                    }), 503
                if set(review_states) != set(review_ids) or any(
                    isinstance(state, bool) or state not in (0, 1, 2)
                    for state in review_states.values()
                ):
                    return jsonify({
                        'ok': False,
                        'code': 'RISK_DISMISSAL_STATE_UNAVAILABLE',
                        'error': 'A Canonical risk source has no reliable note review state.',
                        'risks': None,
                        'total': None,
                        'data_state': 'UNAVAILABLE',
                    }), 503
                risk_candidates = [
                    row for row in risk_candidates
                    if review_states[row['source_id']] != 2
                ]

            risks = risk_candidates[:limit]

            by_level = {}
            for row in risks:
                level = row['risk_level'].strip().lower()
                by_level[level] = by_level.get(level, 0) + 1

            return jsonify({
                'ok': True,
                'domain': domain,
                'domain_id': scope.get('domain_id'),
                'product_id': scope.get('product_id'),
                'scope': scope,
                'risks': risks,
                'total': len(risks),
                'by_level': by_level,
                'limit': limit,
                'risk_policy_version': policy.policy_version,
                'canonical_returned': canonical.get('returned_count', len(records)),
                'canonical_candidate_count': canonical.get('candidate_count'),
                'truncated': canonical.get('truncated'),
                'data_state': 'READY' if records else 'NOT_COLLECTED',
                'source': 'permission-checked canonical_data.list_scoped_canonical',
                'dismissal_state': 'APPLIED_FOR_CANONICAL_NOTE_SOURCE_IDS',
            })
        except ValueError as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 400
        except Exception as exc:
            if hasattr(exc, 'code') and hasattr(exc, 'status'):
                return jsonify({'ok': False, 'code': exc.code}), exc.status
            return jsonify({
                'ok': False,
                'code': 'RISK_CANONICAL_UNAVAILABLE',
                'error': 'Authorized Canonical risk data is unavailable.',
            }), 503

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

    @bp.route('/api/resource-guard', endpoint='api_resource_guard')
    def api_resource_guard():
        """P0-G 最大效率统一资源守卫：消费 lifecycle_action + 资源指标，输出四态调度建议（只读）。"""
        action = request.args.get('action', 'schedule_normal')
        if action not in ('schedule_normal', 'backoff_interval', 'pause_until_cooldown',
                          'freeze_and_recover', 'probe_only', 'ramp_up'):
            return jsonify({'ok': False, 'error': 'invalid action'}), 400
        cpu = request.args.get('cpu', type=float)
        ram = request.args.get('ram', type=float)
        lag = request.args.get('queue_lag', 0, type=int)
        snap = _resource_guard.snapshot(action, cpu_pct=cpu, ram_pct=ram, queue_lag=lag)
        return jsonify({'ok': True, **snap})

    app.register_blueprint(bp)
    return bp
