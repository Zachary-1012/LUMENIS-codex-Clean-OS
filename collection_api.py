# -*- coding: utf-8 -*-
"""采集控制 API 蓝图（app.py 巨石拆分 · 批2a，P1-10）。

本批抽取依赖“可 import 模块”（collector_automation / xhs_cookie_bridge / database）的
采集器状态与启停接口，显式保留原 endpoint 名。状态查询委托给统一 status API owner。
涉及 app.py 运行时锁/线程的更复杂接口留待后续批次。
"""
from __future__ import annotations

from datetime import datetime

import collector_automation
import database as db
import xhs_cookie_bridge
from flask import Blueprint, jsonify, request
from lumenis.system.collector.adapters.rednote_policy import automatic_collection_opt_in_enabled
from collector_status_api import get_collector_status_payload


def register_collection_api(app):
    """在 Flask app 上注册采集控制蓝图（批2a）。"""
    bp = Blueprint("collection", __name__)

    @bp.route('/api/collector/status', endpoint='api_collector_status')
    def api_collector_status():
        """Compatibility route backed by the single Collector status payload."""
        try:
            return jsonify(get_collector_status_payload())
        except Exception as e:
            return jsonify({'ok': False, 'success': False, 'data': None, 'error': str(e)}), 500

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
            auto_enabled = automatic_collection_opt_in_enabled()
            hours = acc.get('auto_collect_hours') or [8, 10, 12, 14, 16, 18, 20, 22, 23]
            nxt = next((h for h in hours if h > now.hour), None) if auto_enabled else None
            next_collect = (
                (f'今日 {nxt:02d}:05' if nxt is not None else '明日 08:05')
                if auto_enabled else '未开启自动采集'
            )
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
                            'auto_enabled': auto_enabled,
                            'cooldown_remaining_minutes': cooldown,
                            'circuit': {'open': circ.get('open', False), 'state': circ.get('state', ''),
                                        'resume_at': circ.get('resume_at', '')},
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
            mode = data.get('mode', 'manual')
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


    @bp.route('/api/xhs/collect-health', endpoint='api_xhs_collect_health')
    def api_xhs_collect_health():
        """采集六态状态中心：熔断状态 + 今日各状态计数 + 最近批次日志（BLOCKED 绝不伪装成 0 条）"""
        try:
            circ = xhs_cookie_bridge.get_circuit_state()
            with db.get_db() as conn:
                today = conn.execute("SELECT status,COUNT(*),SUM(notes_count) FROM collection_logs WHERE date(finished_at)=date('now','localtime') GROUP BY status").fetchall()
                recent = conn.execute("SELECT keyword,notes_count,status,COALESCE(error_msg,''),finished_at FROM collection_logs ORDER BY id DESC LIMIT 10").fetchall()
            state_counts = {r[0]: {'runs': r[1], 'notes': r[2] or 0} for r in today}
            recent_list = [{'keyword': r[0], 'notes': r[1], 'state': r[2], 'msg': r[3], 'at': r[4]} for r in recent]
            # 总状态判定
            bad = sum(v['runs'] for k, v in state_counts.items() if k in ('BLOCKED', 'AUTH_FAILED', 'CAPTCHA', 'NETWORK_ERROR'))
            ok = sum(v['runs'] for k, v in state_counts.items() if k in ('SUCCESS', 'EMPTY'))
            overall = 'BLOCKED' if circ.get('open') else ('OK' if ok else ('FAILED' if bad else 'IDLE'))
            return jsonify({'ok': True, 'overall': overall, 'circuit': circ,
                            'state_counts': state_counts, 'recent': recent_list,
                            'state_label': xhs_cookie_bridge.STATE_LABEL, 'test_mode': xhs_cookie_bridge.is_test_mode()})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500



    @bp.route('/api/xhs/cookie/status')
    def api_xhs_cookie_status():
        status = xhs_cookie_bridge.get_account_status()
        return jsonify({'ok':True, **status})

    @bp.route('/api/xhs/cookie/sync',methods=['POST'])
    def api_xhs_cookie_sync():
        data=request.get_json(silent=True) or {}
        keywords=data.get('keywords') or xhs_cookie_bridge.DEFAULT_KEYWORDS
        if isinstance(keywords,str): keywords=[x.strip() for x in keywords.split(',') if x.strip()]
        try: max_scroll=max(1,min(20,int(data.get('max_scroll',6))))
        except (TypeError,ValueError): return jsonify({'ok':False,'error':'max_scroll 必须为整数'}),400
        run_type = data.get('run_type', 'manual')  # manual: 一键实时更新, auto: 定时自动采集
        if run_type not in ['manual', 'auto']:
            return jsonify({'ok':False,'error':'run_type 必须为 manual 或 auto'}),400
        try: task_id=xhs_cookie_bridge.create_task(keywords,max_scroll,run_type)
        except RuntimeError as e: return jsonify({'ok':False,'error':str(e)}),409
        type_label = '手动触发（一键实时更新）' if run_type == 'manual' else '定时自动采集'
        return jsonify({'ok':True,'task_id':task_id,'run_type':run_type,'message':f'已创建{type_label}任务'})

    @bp.route('/api/xhs/collect-pause',methods=['POST'])
    def api_xhs_collect_pause():
        """用户主动暂停小红书采集（手动/自动一律不发起请求，直到 resume）；区别于风控熔断。"""
        data=request.get_json(silent=True) or {}
        reason=(data.get('reason') or '用户手动暂停')[:120]
        ok=xhs_cookie_bridge.set_user_paused(reason)
        return jsonify({'ok':ok,'paused':True,'reason':reason,'message':'小红书采集已暂停，自动/手动均不会发起请求，恢复后继续'})

    @bp.route('/api/xhs/collect-resume',methods=['POST'])
    def api_xhs_collect_resume():
        """恢复小红书采集（仅解除用户暂停开关；风控熔断按其自身健康检查恢复）。"""
        ok=xhs_cookie_bridge.resume_user_paused()
        return jsonify({'ok':ok,'paused':False,'message':'已解除手动暂停；如仍处风控熔断，需先完成验证与健康检查'})

    @bp.route('/api/xhs/collect-pause-state',methods=['GET'])
    def api_xhs_collect_pause_state():
        _p=xhs_cookie_bridge.is_user_paused()
        _c=xhs_cookie_bridge.get_circuit_state()
        return jsonify({'ok':True,'user_paused':bool(_p),'pause_info':_p,'circuit':_c})

    @bp.route('/api/xhs/cookie/sync/<task_id>')
    def api_xhs_cookie_sync_status(task_id):
        task=xhs_cookie_bridge.get_task(task_id)
        return (jsonify({'ok':True,'task':task}),200) if task else (jsonify({'ok':False,'error':'任务不存在'}),404)

    app.register_blueprint(bp)
    return bp
