# -*- coding: utf-8 -*-
"""采集控制 API 蓝图（app.py 巨石拆分 · 批2a，P1-10）。

本批只抽依赖“可 import 模块”（collector_automation / xhs_cookie_bridge / database）的
采集器状态与启停接口，函数体零逻辑改动，显式保留原 endpoint 名。
涉及 app.py 运行时锁/线程的更复杂接口留待后续批次。
"""
from __future__ import annotations

from datetime import datetime

import collector_automation
import database as db
import xhs_cookie_bridge
from flask import Blueprint, jsonify, request


def register_collection_api(app):
    """在 Flask app 上注册采集控制蓝图（批2a）。"""
    bp = Blueprint("collection", __name__)

    @bp.route('/api/collector/status', endpoint='api_collector_status')
    def api_collector_status():
        """采集器状态查询"""
        try:
            collector = collector_automation.get_collector_automation()
            status = collector.get_status()
            return jsonify({'ok': True, **status})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @bp.route('/api/collect/schedule-status', endpoint='api_collect_schedule_status')
    def api_collect_schedule_status():
        """数据更新卡片真实状态：聚合额度/熔断/运行任务/今日入库/下次计划，区分
        running采集中 / blocked风控熔断 / cooldown冷却 / pending今日尚未采集 / ok正常 / no_cookie未配置。
        绝不在“今日0次采集”时仍返回绿色就绪。"""
        try:
            acc = xhs_cookie_bridge.get_account_status()
            circ = xhs_cookie_bridge.get_circuit_state()
            now = datetime.now()
            # 正在运行的采集任务
            running = []
            try:
                for _tid, _t in (xhs_cookie_bridge._tasks or {}).items():
                    if _t.get('status') in ('running', 'pending'):
                        running.append({'task_id': _tid, 'progress': _t.get('progress', 0),
                                        'message': _t.get('message', ''), 'run_type': _t.get('run_type', '')})
            except Exception:
                pass
            # 今日实际入库笔记数 & 最近一次入库时间
            today_inserted = 0
            last_insert = None
            try:
                with db.get_db() as conn:
                    today_inserted = conn.execute(
                        "SELECT COUNT(*) FROM notes WHERE date(COALESCE(collected_at,''))=date('now','localtime')").fetchone()[0]
                    row = conn.execute("SELECT MAX(collected_at) FROM notes").fetchone()
                    last_insert = row[0] if row else None
            except Exception:
                pass
            # 上次采集时间（优先采集器记录，回退入库时间）
            last_run_ts = getattr(xhs_cookie_bridge, '_last_run_time', None)
            last_collect = datetime.fromtimestamp(last_run_ts).strftime('%Y-%m-%d %H:%M:%S') if last_run_ts else (last_insert or '无')
            # 下次计划自动采集
            hours = acc.get('auto_collect_hours') or [8, 10, 12, 14, 16, 18, 20, 22, 23]
            nxt = next((h for h in hours if h > now.hour), None)
            next_collect = f'今日 {nxt:02d}:05' if nxt is not None else '明日 08:05'
            # 综合状态机
            cooldown = acc.get('cooldown_remaining_minutes', 0)
            if running:
                state, state_cn = 'running', '采集中'
            elif circ.get('open'):
                state, state_cn = 'blocked', '采集受限·熔断'
            elif not acc.get('cookie_configured'):
                state, state_cn = 'no_cookie', '未配置登录态'
            elif cooldown and cooldown > 0:
                state, state_cn = 'cooldown', f'冷却中·剩{cooldown}分'
            elif acc.get('today_runs', 0) == 0 and now.hour >= min(hours):
                state, state_cn = 'pending', '今日尚未采集'
            elif acc.get('today_runs', 0) == 0:
                state, state_cn = 'pending', '待采集'
            else:
                state, state_cn = 'ok', '运行正常'
            return jsonify({'ok': True, 'state': state, 'state_cn': state_cn,
                            'today_runs': acc.get('today_runs', 0),
                            'max_daily_runs': acc.get('max_daily_runs', 12),
                            'manual_left': max(0, acc.get('max_manual_runs', 3) - acc.get('today_manual_runs', 0)),
                            'manual_total': acc.get('max_manual_runs', 3),
                            'auto_left': max(0, acc.get('max_auto_runs', 9) - acc.get('today_auto_runs', 0)),
                            'auto_total': acc.get('max_auto_runs', 9),
                            'today_inserted': today_inserted,
                            'last_collect': last_collect,
                            'next_collect': next_collect,
                            'cooldown_remaining_minutes': cooldown,
                            'circuit': {'open': circ.get('open', False), 'state': circ.get('state', ''),
                                        'detail': circ.get('detail', ''), 'resume_at': circ.get('resume_at', '')},
                            'running': running,
                            'server_time': now.strftime('%Y-%m-%d %H:%M:%S')})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @bp.route('/api/collector/start', methods=['POST'], endpoint='api_collector_start')
    def api_collector_start():
        """启动采集任务"""
        try:
            data = request.get_json(silent=True) or {}
            keywords = data.get('keywords')
            mode = data.get('mode', 'standard')
            account = data.get('account', 'default')
            force = bool(data.get('force', False))

            collector = collector_automation.get_collector_automation()
            result = collector.start_collection(keywords=keywords, mode=mode, account=account, force=force)
            return jsonify(result)
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @bp.route('/api/collector/stop', methods=['POST'], endpoint='api_collector_stop')
    def api_collector_stop():
        """停止采集任务"""
        try:
            collector = collector_automation.get_collector_automation()
            result = collector.stop_collection()
            return jsonify(result)
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @bp.route('/api/collector/history', endpoint='api_collector_history')
    def api_collector_history():
        """采集历史记录"""
        try:
            limit = request.args.get('limit', 20, type=int)
            collector = collector_automation.get_collector_automation()
            history = collector.get_history(limit=limit)
            return jsonify({'ok': True, 'history': history})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    app.register_blueprint(bp)
    return bp
