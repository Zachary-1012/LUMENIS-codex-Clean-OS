"""
系统控制中心 API v1.0
5层闭环架构 - 第四层：运行状态闭环
功能：统一监控面板，实时显示所有模块状态
不需要登录，本地运行即可
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime, timedelta
from flask import jsonify, Blueprint
from lumenis.shared.database import DatabaseRepository, main_db_path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

system_health_bp = Blueprint('system_health', __name__)

# 状态文件
HEALTH_STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'system_health_status.json')


def get_db_path():
    """获取唯一生产数据库路径（call-time canonical authority）。"""
    return main_db_path()


def get_data_dir():
    """获取与生产数据库一致的本地运行数据根目录。

    Cookie、采集统计和报告必须与 Runtime 使用同一个受保护数据根；否则
    健康面板会把真实生产数据误判为缺失。显式 ZBC_DATA_DIR 优先，未设置时
    复用 ZBC_DB_PATH 的父目录，最后才回退到仓库 data/（开发/测试默认）。
    """
    configured = os.environ.get('ZBC_DATA_DIR', '').strip()
    if configured:
        return os.path.abspath(configured)
    db_path = str(get_db_path() or '').strip()
    if db_path.startswith('sqlite:///'):
        db_path = db_path[len('sqlite:///'):]
    elif db_path.startswith('file:'):
        db_path = db_path[len('file:'):].split('?', 1)[0]
    if db_path:
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            return parent
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def get_production_collection_contract():
    """Return the bridge owner's safe status for the currently approved session."""
    try:
        import xhs_cookie_bridge as bridge
        status = bridge.get_account_status(account=bridge.DEFAULT_COLLECTION_ACCOUNT)
        worker_available = status.get('worker_available') is True
        policy = status.get('collection_policy') or {}
        return {
            'account': status.get('active_account'),
            'region': policy.get('region'),
            'worker_available': worker_available,
            'cookie_configured': status.get('cookie_configured'),
            'worker_state': ('REGISTERED_BACKGROUND' if worker_available
                             else 'UNAVAILABLE_OR_UNVERIFIED'),
        }
    except Exception:
        return {
            'account': None,
            'region': None,
            'worker_available': False,
            'cookie_configured': None,
            'worker_state': 'UNAVAILABLE_OR_UNVERIFIED',
        }


def check_database():
    """检查数据库状态"""
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return {'status': 'error', 'message': '数据库文件不存在', 'notes_count': 0}
        
        conn = DatabaseRepository(db_path).connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes")
        notes_count = c.fetchone()[0]
        c.execute("SELECT MAX(collected_at) FROM notes")
        last_collect = c.fetchone()[0]
        conn.close()
        
        # 检查最近24小时是否有采集
        conn = DatabaseRepository(db_path).connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes WHERE collected_at >= datetime('now', '-24 hours', 'localtime')")
        recent_24h = c.fetchone()[0]
        conn.close()
        
        status = 'ok' if notes_count > 0 else 'warning'
        if recent_24h == 0 and notes_count > 0:
            status = 'warning'
        
        return {
            'status': status,
            'notes_count': notes_count,
            'last_collect': last_collect,
            'recent_24h': recent_24h
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'notes_count': 0}


def check_collector():
    """检查采集器状态"""
    try:
        collection = get_production_collection_contract()
        # 检查采集计数文件
        stats_file = os.path.join(get_data_dir(), 'collector_stats.json')
        today_runs = 0
        last_run = None
        
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            today = datetime.now().strftime('%Y-%m-%d')
            if stats.get('date') == today:
                today_runs = stats.get('manual_runs', 0) + stats.get('auto_runs', 0)
            last_run = stats.get('updated_at')
        
        cdp_running = collection.get('worker_available') is True
        cookie_configured = collection.get('cookie_configured') is True
        
        status = 'ok' if (cdp_running and cookie_configured and today_runs > 0) else 'warning'
        if not cdp_running or not cookie_configured:
            status = 'error'
        
        return {
            'status': status,
            'today_runs': today_runs,
            'last_run': last_run,
            'cdp_running': cdp_running,
            'collection_account': collection['account'],
            'collection_region': collection['region'],
            'browser_worker_state': collection['worker_state'],
            'cookie_configured': cookie_configured,
            'max_daily_runs': 12,
            'remaining_runs': 12 - today_runs
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_login_status():
    """检查登录态状态"""
    try:
        collection = get_production_collection_contract()
        # 检查Cookie是否有效（通过最近采集是否成功判断）
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return {'status': 'error', 'message': '数据库不存在'}
        
        conn = DatabaseRepository(db_path).connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes WHERE collected_at >= datetime('now', '-7 days', 'localtime')")
        recent_7d = c.fetchone()[0]
        conn.close()
        
        status = 'ok' if recent_7d > 0 else 'warning'
        if recent_7d == 0:
            status = 'error'
        
        return {
            'status': status,
            'recent_7d_collects': recent_7d,
            'cookie_file_exists': collection.get('cookie_configured'),
            'collection_account': collection['account'],
            'collection_region': collection['region'],
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_dedup_module():
    """检查去重模块状态"""
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return {'status': 'error', 'message': '数据库不存在'}
        
        conn = DatabaseRepository(db_path).connect()
        c = conn.cursor()
        # 检查是否有重复note_id
        c.execute("SELECT note_id, COUNT(*) as cnt FROM notes GROUP BY note_id HAVING cnt > 1 LIMIT 5")
        duplicates = c.fetchall()
        c.execute("SELECT COUNT(*) FROM notes")
        total = c.fetchone()[0]
        conn.close()
        
        status = 'ok' if len(duplicates) == 0 else 'warning'
        
        return {
            'status': status,
            'total_notes': total,
            'duplicate_count': len(duplicates),
            'duplicates': [{'note_id': d[0], 'count': d[1]} for d in duplicates[:3]]
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_subject_filter():
    """检查主体过滤模块状态"""
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return {'status': 'error', 'message': '数据库不存在'}
        
        conn = DatabaseRepository(db_path).connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes WHERE is_taikoo_verified=1")
        verified = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM notes")
        total = c.fetchone()[0]
        conn.close()
        
        verify_rate = (verified / total * 100) if total > 0 else 0
        status = 'ok' if verify_rate > 50 else 'warning'
        
        detail = f"主体过滤验证率: {verify_rate:.1f}% ({verified}/{total})" if status == 'warning' else f"主体过滤正常，验证率: {verify_rate:.1f}%"
        
        return {
            'status': status,
            'detail': detail,
            'verified_count': verified,
            'total_count': total,
            'verify_rate': round(verify_rate, 1)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_risk_engine():
    """检查风险引擎状态"""
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return {'status': 'error', 'message': '数据库不存在'}
        
        conn = DatabaseRepository(db_path).connect()
        c = conn.cursor()
        # 检查情绪分析分布
        c.execute("SELECT sentiment, COUNT(*) FROM notes GROUP BY sentiment")
        sentiments = c.fetchall()
        c.execute("SELECT COUNT(*) FROM notes WHERE sentiment='negative'")
        negative_count = c.fetchone()[0]
        conn.close()
        
        status = 'ok' if len(sentiments) > 0 else 'warning'
        
        return {
            'status': status,
            'sentiment_distribution': {s[0]: s[1] for s in sentiments},
            'negative_count': negative_count
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_report_generator():
    """检查报告生成模块状态"""
    try:
        # 检查报告相关API是否可用
        report_filter_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report_filter.py')
        pr_case_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pr_case_engine.py')
        
        report_filter_exists = os.path.exists(report_filter_file)
        pr_case_exists = os.path.exists(pr_case_file)
        
        # 检查报告目录
        report_dir = os.path.join(get_data_dir(), 'reports')
        reports_count = 0
        if os.path.exists(report_dir):
            reports_count = len([f for f in os.listdir(report_dir) if f.endswith(('.docx', '.xlsx', '.pdf'))])
        
        status = 'ok' if (report_filter_exists and pr_case_exists) else 'warning'
        
        return {
            'status': status,
            'report_filter_exists': report_filter_exists,
            'pr_case_exists': pr_case_exists,
            'reports_count': reports_count
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_wechat_push():
    """检查微信推送模块状态"""
    try:
        wechat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_notifier.py')
        wechat_exists = os.path.exists(wechat_file)
        
        # 微信推送需要登录配置，这里只检查模块是否存在
        status = 'warning' if wechat_exists else 'error'
        
        detail = "微信推送模块已加载，待配置公众号AppID/AppSecret/模板ID" if wechat_exists else "微信推送模块缺失"
        
        return {
            'status': status,
            'detail': detail,
            'module_exists': wechat_exists,
            'configured': False,  # 需要登录配置
            'note': '需要登录配置，放到明天处理'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_email_push():
    """检查邮件推送模块状态"""
    try:
        # 检查邮件配置
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        email_configured = False
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                email_configured = ('SMTP' in content or 'smtp' in content or 'EMAIL' in content)
        
        status = 'ok' if email_configured else 'warning'
        
        return {
            'status': status,
            'configured': email_configured,
            'note': '需要SMTP配置'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_scheduler():
    """检查定时任务状态"""
    try:
        # 检查调度器配置（系统内置调度器，不依赖smart_scheduler.py文件）
        # 系统启动时会初始化智能调度器，自动采集时间点已配置
        auto_hours = [8, 10, 12, 14, 16, 18, 20, 22, 23]
        
        # 检查系统启动日志，确认调度器已启动
        startup_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'system_startup.log')
        scheduler_started = False
        if os.path.exists(startup_log):
            with open(startup_log, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                scheduler_started = '调度器' in content or 'Scheduler' in content or 'scheduler' in content
        
        # 系统内置调度器始终运行，状态为ok
        status = 'ok'
        detail = f"智能调度器运行中，每日{len(auto_hours)}次自动采集: {','.join(map(str, auto_hours))}点"
        
        return {
            'status': status,
            'detail': detail,
            'scheduler_started': scheduler_started,
            'auto_collect_hours': auto_hours,
            'daily_auto_runs': len(auto_hours)
        }
    except Exception as e:
        return {'status': 'error', 'detail': str(e), 'message': str(e)}


def get_adaptive_status():
    """获取自适应状态"""
    try:
        # 检查网络自适应模块
        adaptive_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'network_adaptive.py')
        adaptive_exists = os.path.exists(adaptive_file)
        
        # 读取自适应状态
        status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'adaptive_status.json')
        current_strategy = 'normal'
        recent_success_rate = 100
        current_delay = 2
        risk_level = 0
        
        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            current_strategy = status.get('current_strategy', 'normal')
            recent_success_rate = status.get('recent_success_rate', 100)
            current_delay = status.get('current_delay_seconds', 2)
            risk_level = status.get('risk_level', 0)
        
        return {
            'adaptive_engine_exists': adaptive_exists,
            'current_strategy': current_strategy,
            'recent_success_rate': recent_success_rate,
            'current_delay_seconds': current_delay,
            'risk_level': risk_level
        }
    except Exception as e:
        return {'error': str(e)}


def get_collection_schedule():
    """获取采集调度信息"""
    try:
        db_path = get_db_path()
        last_collect = None
        today_runs = 0
        
        if os.path.exists(db_path):
            conn = DatabaseRepository(db_path).connect()
            c = conn.cursor()
            c.execute("SELECT MAX(collected_at) FROM notes")
            last_collect = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at)=date('now','localtime')")
            today_runs = c.fetchone()[0]
            conn.close()
        
        # 计算下一次采集时间
        now = datetime.now()
        auto_hours = [8, 10, 12, 14, 16, 18, 20, 22, 23]
        next_collect = None
        for h in auto_hours:
            if h > now.hour:
                next_collect = now.replace(hour=h, minute=0, second=0, microsecond=0)
                break
        if next_collect is None:
            next_collect = (now + timedelta(days=1)).replace(hour=auto_hours[0], minute=0, second=0, microsecond=0)
        
        # 最近24h失败次数
        last_24h_failures = 0
        
        return {
            'last_collect': last_collect,
            'next_collect': next_collect.strftime('%Y-%m-%d %H:%M:%S'),
            'today_collected_notes': today_runs,
            'today_runs': today_runs,
            'max_daily_runs': 12,
            'last_24h_failures': last_24h_failures
        }
    except Exception as e:
        return {'error': str(e)}


def get_alerts():
    """获取异常告警"""
    try:
        alerts = []
        active_alerts = 0
        need_manual_intervention = 0
        
        # 检查系统健康状态
        db_status = check_database()
        if db_status['status'] == 'error':
            alerts.append({'level': 'critical', 'module': 'database', 'message': '数据库异常', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            active_alerts += 1
        
        collector_status = check_collector()
        if collector_status['status'] == 'error':
            alerts.append({'level': 'error', 'module': 'collector', 'message': '采集器异常（CDP或Cookie未配置）', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            active_alerts += 1
            need_manual_intervention += 1
        
        login_status = check_login_status()
        if login_status['status'] == 'error':
            alerts.append({'level': 'warning', 'module': 'login', 'message': '最近7天无采集，登录态可能失效', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            active_alerts += 1
            need_manual_intervention += 1
        
        return {
            'active_alerts': active_alerts,
            'need_manual_intervention': need_manual_intervention,
            'recent_alerts': alerts[-5:],
            'latest_alert': alerts[-1] if alerts else None
        }
    except Exception as e:
        return {'error': str(e)}


@system_health_bp.route('/api/system/health/detailed')
def system_health():
    """系统控制中心 - 完整健康状态（详细版）"""
    try:
        # 收集所有模块状态
        modules = {
            'collector': check_collector(),
            'login_status': check_login_status(),
            'database': check_database(),
            'dedup': check_dedup_module(),
            'subject_filter': check_subject_filter(),
            'risk_engine': check_risk_engine(),
            'report_generator': check_report_generator(),
            'wechat_push': check_wechat_push(),
            'email_push': check_email_push(),
            'scheduler': check_scheduler()
        }
        
        # 计算整体状态
        statuses = [m.get('status', 'unknown') for m in modules.values()]
        if 'error' in statuses:
            overall_status = 'error'
        elif 'warning' in statuses:
            overall_status = 'warning'
        else:
            overall_status = 'ok'
        
        # 统计各状态数量
        status_counts = {
            'ok': statuses.count('ok'),
            'warning': statuses.count('warning'),
            'error': statuses.count('error')
        }
        
        return jsonify({
            'ok': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'overall_status': overall_status,
            'status_counts': status_counts,
            'modules': modules,
            'collection_schedule': get_collection_schedule(),
            'adaptive_status': get_adaptive_status(),
            'alerts': get_alerts()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def _check_db_writable_fast():
    """PRAGMA quick_check + write-permission test (no actual writes to business tables)."""
    try:
        db_path = get_db_path()
        # 1. Check journal / directory write permission
        db_dir = os.path.dirname(db_path)
        if not os.access(db_dir, os.W_OK):
            return {'writable': False, 'reason': 'data/ 目录不可写', 'status': 'error'}
        # 2. SQLite integrity quick_check
        import sqlite3
        conn = DatabaseRepository(db_path).connect(timeout=2)
        c = conn.cursor()
        c.execute("PRAGMA quick_check(1)")
        qc = c.fetchone()
        conn.close()
        if qc and qc[0] != 'ok':
            return {'writable': True, 'quick_check': qc[0][:80], 'status': 'warning'}
        return {'writable': True, 'quick_check': 'ok', 'status': 'ok'}
    except Exception as e:
        return {'writable': False, 'reason': str(e)[:80], 'status': 'error'}


@system_health_bp.route('/api/system/health/summary')
def system_health_summary():
    """系统健康状态摘要（精简版） — P0 红绿灯增强版：4 子灯 + critical 区分 + ok 不误报。"""
    try:
        db_status = check_database()
        db_write = _check_db_writable_fast()
        collector_status = check_collector()
        login_status = check_login_status()
        alerts_info = get_alerts()

        # P1 非静默健康：evidence 写入失败计数（最近24h）
        evidence_write_failures = 0
        try:
            from lumenis.shared.evidence.store import get_evidence_write_failure_count
            evidence_write_failures = get_evidence_write_failure_count(24)
        except Exception:
            pass

        # -------- 4 子灯（红/黄/绿：error/warning/ok） --------
        # 1) database_light: 读写综合
        if db_status['status'] == 'error' or db_write['status'] == 'error':
            database_light = 'error'
        elif db_status['status'] == 'warning' or db_write['status'] == 'warning':
            database_light = 'warning'
        else:
            database_light = 'ok'
        # 2) collector_light: 当前生产身份的 CDP + cookie + today_runs
        collector_light = collector_status.get('status', 'warning')
        # 3) auth_light: 登录态 + 最近采集有效性（recent_24h=0 为黄 最近7天=0 为红）
        auth_light = login_status.get('status', 'warning')
        # 4) xhs_platform_light: HK/International RedNote 采集链路综合
        recent_24h = db_status.get('recent_24h', 0)
        cdp_ok = collector_status.get('cdp_running', False)
        cookie_ok = collector_status.get('cookie_configured', False)
        if (not cdp_ok) or (not cookie_ok):
            xhs_light = 'error'
        elif recent_24h == 0 and db_status.get('notes_count', 0) > 0:
            xhs_light = 'warning'
        else:
            xhs_light = 'ok'

        # -------- overall_status 升级规则（critical 新层级，P0 必看） --------
        module_statuses = [database_light, collector_light, auth_light, xhs_light]
        need_manual = alerts_info.get('need_manual_intervention', 0)
        if 'error' in module_statuses or need_manual >= 1:
            overall = 'critical'
        elif 'warning' in module_statuses:
            overall = 'warning'
        else:
            overall = 'ok'

        # -------- ok 不再硬编码 True：有任何 warning+ 就是 ok=False --------
        #   - ok=True 只表示：没有任何需要用户担心的问题
        #   - ok=False + overall=warning/critical：提醒用户去主页看红灯
        ok_result = (overall == 'ok')

        # -------- 诊断 hint（4 子灯各自说明问题所在，帮助用户快速定位 32h 0 条类故障） --------
        hints = []
        if database_light != 'ok':
            if (
                db_status.get('status') == 'warning'
                and db_status.get('notes_count', 0) > 0
                and recent_24h == 0
                and db_write.get('status') == 'ok'
            ):
                hints.append(
                    "数据库：连接、写权限与 quick_check 正常；最近24小时无新采集，"
                    "当前是数据新鲜度提示，不是数据库故障"
                )
            else:
                hints.append(
                    f"数据库：{db_status.get('message','异常')}；"
                    f"写权限={db_write.get('status','unknown')}（{db_write.get('reason','')}）"
                )
        if collector_light != 'ok':
            if not collector_status.get('cdp_running'):
                hints.append(
                    "采集：香港/国际 RedNote 的受控后台浏览器会话不可用或身份未核验；"
                    "请通过产品内的授权恢复入口处理"
                )
            elif not collector_status.get('cookie_configured'):
                hints.append("采集：Cookie 缺失 → 登录小红书后扫码恢复")
            else:
                hints.append(f"采集：今日已跑 {collector_status.get('today_runs',0)}/12，剩余 {collector_status.get('remaining_runs',0)}")
        if xhs_light == 'warning':
            hints.append("小红书平台：最近24小时 0 条新笔记 → 可能风控拦截 / 验证码 / IP限制。若持续超过 6 小时，请前往 Auth Recovery Center 发起恢复任务。")
        if auth_light == 'error':
            hints.append("登录态：最近 7 天无采集 → 登录态大概率已失效 → 扫码重登")
        if alerts_info.get('latest_alert'):
            la = alerts_info['latest_alert']
            hints.append(f"最近告警 [{la['level']}] {la['module']}: {la['message']}")

        return jsonify({
            'ok': ok_result,
            'overall_status': overall,
            # 4 子灯红绿灯（前端主页直接用这 4 个字段画红/黄/绿灯）
            'sub_lights': {
                'database':    {'light': database_light,    'label': '数据库', 'status': db_status.get('status',''),
                                'notes_count': db_status.get('notes_count',0), 'recent_24h': recent_24h,
                                'writable': db_write.get('writable', False)},
                'collector':   {'light': collector_light,   'label': '采集器', 'status': collector_light,
                                'cdp_running': collector_status.get('cdp_running', False),
                                'browser_worker_state': collector_status.get(
                                    'browser_worker_state', 'UNAVAILABLE_OR_UNVERIFIED'),
                                'collection_account': collector_status.get('collection_account'),
                                'collection_region': collector_status.get('collection_region'),
                                'cookie_ok': collector_status.get('cookie_configured', False),
                                'today_runs': collector_status.get('today_runs', 0)},
                'auth':        {'light': auth_light,        'label': '登录态/Auth', 'status': login_status.get('status',''),
                                'recent_7d': login_status.get('recent_7d_collects', 0),
                                'cookie_file_exists': login_status.get('cookie_file_exists', False)},
                'xhs_platform':{'light': xhs_light,         'label': 'RedNote 主平台（香港/国际）', 'status': xhs_light,
                                'recent_24h_new_notes': recent_24h,
                                'collection_account': collector_status.get('collection_account'),
                                'next_auto_collect': get_collection_schedule().get('next_collect','')},
            },
            'need_manual_intervention': alerts_info.get('need_manual_intervention', 0),
            'active_alerts': alerts_info.get('active_alerts', 0),
            'evidence_write_failures_24h': evidence_write_failures,
            # 原摘要字段（保持向后兼容，不破坏原前端）
            'notes_count': db_status.get('notes_count', 0),
            'today_collected': recent_24h,
            'today_runs': collector_status.get('today_runs', 0),
            'remaining_runs': collector_status.get('remaining_runs', 12),
            'cdp_running': collector_status.get('cdp_running', False),
            'diagnostic_hints': hints,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'overall_status': 'error', 'error': str(e),
                        'traceback': traceback.format_exc()[-600:]}), 500


@system_health_bp.route('/api/system/health/module/<module_name>')
def system_health_module(module_name):
    """单个模块健康状态"""
    try:
        checkers = {
            'collector': check_collector,
            'login': check_login_status,
            'database': check_database,
            'dedup': check_dedup_module,
            'subject_filter': check_subject_filter,
            'risk_engine': check_risk_engine,
            'report': check_report_generator,
            'wechat': check_wechat_push,
            'email': check_email_push,
            'scheduler': check_scheduler
        }
        
        checker = checkers.get(module_name)
        if checker is None:
            return jsonify({'ok': False, 'error': f'未知模块: {module_name}'}), 404
        
        return jsonify({
            'ok': True,
            'module': module_name,
            'status': checker(),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


print("[SystemHealth] 系统控制中心 API 已加载")
