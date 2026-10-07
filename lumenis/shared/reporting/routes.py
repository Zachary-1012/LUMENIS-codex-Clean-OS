# -*- coding: utf-8 -*-
"""Shared Reporting routes — 报告/摘要/品牌报告 canonical API 蓝图。
原则：Shared Reporting 为报告能力唯一 Owner；路由只依赖 Shared/canonical 能力。
注册点：app.register_blueprint(lumenis.shared.reporting.routes.report_bp)"""
from flask import Blueprint, request, jsonify, Response, send_file, send_from_directory
import os, re, json, time, traceback, io, tempfile, logging
from datetime import datetime, timedelta
from pathlib import Path

import database as db
from lumenis.shared.reporting import engine as report_engine
import canonical_metrics
from subject_rules import subject_sql_and_values
from lumenis.shared.reporting import daily
from lumenis.shared.reporting.filtering import (filter_negative_for_period_report, classify_notes_by_age,
    get_daily_report_filter_stats, filter_notes_for_daily_report, get_report_period)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = PROJECT_ROOT / 'data' / 'reports'
LOGGER = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__)


def _report_failure(exc, *, fallback_status=500):
    code = str(exc)
    if code in {
        "REPORT_DOMAIN_REQUIRED", "REPORT_REFERENCE_SUBJECT_REQUIRED",
        "REPORT_CONTEXT_MISMATCH", "LEGACY_REPORT_DOMAIN_UNSUPPORTED",
    }:
        return jsonify({'ok': False, 'code': code, 'error': code}), 409
    status = 400 if isinstance(exc, ValueError) else fallback_status
    return jsonify({'ok': False, 'error': code}), status

# ===== 报告 API（从 app.py 拆分，函数体零改动）=====

@report_bp.route('/api/v2/report-center/preview')
def shared_reporting_preview():
    import re as _re
    period = (request.args.get('period') or 'daily').strip().lower()
    brand_mode = (request.args.get('brand_mode') or 'cth').strip().lower()
    if period not in ('daily', 'weekly', 'monthly', 'yearly', 'event'):
        return jsonify({'ok': False, 'error': 'period 非法，仅 daily/weekly/monthly/yearly/event'}), 400
    if brand_mode not in ('cth', 'zbmp'):
        return jsonify({'ok': False, 'error': 'brand_mode 仅支持 cth/zbmp'}), 400
    sd = (request.args.get('start_date') or '').strip()
    ed = (request.args.get('end_date') or '').strip()
    _dr = _re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if sd and not _dr.match(sd):
        return jsonify({'ok': False, 'error': 'start_date 需 YYYY-MM-DD'}), 400
    if ed and not _dr.match(ed):
        return jsonify({'ok': False, 'error': 'end_date 需 YYYY-MM-DD'}), 400
    try:
        from lumenis.shared.reporting import ReportGenerator
        rep = ReportGenerator(brand_mode=brand_mode).generate(
            period, start_date=sd or None, end_date=ed or None)
        return jsonify({'ok': True, 'report': rep,
                        'note': 'Shared Reporting canonical preview；只读预览，不替代既有报告 Owner，不产生导出副作用'})
    except ValueError as ve:
        return jsonify({'ok': False, 'error': str(ve)}), 400
    except Exception:
        LOGGER.exception('shared reporting preview failed')
        return jsonify({'ok': False, 'error': '报告生成失败，请查看服务端日志'}), 500

# ===== Global BIL 全球品牌智能：research-stage 只读（从 seed JSON 读，不建表/不写库/不联网，不参与生产口径）=====

@report_bp.route('/api/brand-report/generate', methods=['POST'])
def brand_report_generate():
    """生成品牌分析报告"""
    try:
        from lumenis.shared.reporting.brand_report import BrandReportGenerator
        data = request.get_json() or {}
        generator = BrandReportGenerator(
            brand_name=data.get('brand_name', '序境'),
            report_period=data.get('report_period', ''),
        )
        # 设置各部分数据
        if 'executive_summary' in data:
            es = data['executive_summary']
            generator.set_executive_summary(
                core_findings=es.get('core_findings', []),
                key_metrics=es.get('key_metrics', {}),
                action_items=es.get('action_items', []),
            )
        if 'communication_analysis' in data:
            ca = data['communication_analysis']
            generator.set_communication_analysis(
                subject_distribution=ca.get('subject_distribution', {}),
                channel_analysis=ca.get('channel_analysis', {}),
                effect_evaluation=ca.get('effect_evaluation', {}),
                content_type_distribution=ca.get('content_type_distribution', {}),
            )
        if 'market_intelligence' in data:
            mi = data['market_intelligence']
            generator.set_market_intelligence(
                competitor_updates=mi.get('competitor_updates', []),
                industry_trends=mi.get('industry_trends', []),
                opportunities=mi.get('opportunities', []),
                threats=mi.get('threats', []),
            )
        if 'public_opinion_analysis' in data:
            po = data['public_opinion_analysis']
            generator.set_public_opinion_analysis(
                sentiment_distribution=po.get('sentiment_distribution', {}),
                hot_topics=po.get('hot_topics', []),
                key_influencers=po.get('key_influencers', []),
                risk_warnings=po.get('risk_warnings', []),
            )
        if 'event_graph_analysis' in data:
            eg = data['event_graph_analysis']
            generator.set_event_graph_analysis(
                marketing_events=eg.get('marketing_events', []),
                propagation_events=eg.get('propagation_events', []),
                opinion_events=eg.get('opinion_events', []),
                event_chains=eg.get('event_chains', []),
            )
        if 'recommendations' in data:
            rec = data['recommendations']
            generator.set_recommendations(
                short_term=rec.get('short_term', []),
                medium_term=rec.get('medium_term', []),
                long_term=rec.get('long_term', []),
            )
        report = generator.generate_report()
        return jsonify({'ok': True, 'report': report, 'report_id': report['report_id']})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@report_bp.route('/api/brand-report/export/<report_id>')
def brand_report_export(report_id):
    """导出品牌分析报告（JSON/Markdown）"""
    try:
        from lumenis.shared.reporting.brand_report import BrandReportGenerator
        from lumenis.shared.reporting import artifact as ra
        format_type = request.args.get('format', 'json')
        # 这里简化处理，实际应从存储中读取报告
        generator = BrandReportGenerator()
        if format_type == 'markdown':
            filepath = f'data/brand_report_{report_id}.md'
            ok = generator.export_markdown(filepath)
            if not ok:
                return jsonify({'ok': False, 'error': 'Markdown 导出失败'}), 500
        else:
            filepath = f'data/brand_report_{report_id}.json'
            ok = generator.export_json(filepath)
            if not ok:
                return jsonify({'ok': False, 'error': 'JSON 导出失败'}), 500
        # ZBC Phase 9: 导出后必须验证文件真实存在且非空
        v = ra.verify_artifact_file(filepath)
        if not v['valid']:
            return jsonify({'ok': False, 'error': f'导出文件校验失败: {v["reason"]}', 'filepath': filepath}), 500
        return jsonify({'ok': True, 'format': format_type, 'filepath': filepath,
                        'size': v['size'], 'artifact_hash': v['hash']})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

APP_VERSION='5.9.9'
APP_HOST=os.getenv('TAIKOO_HOST','0.0.0.0')
APP_PORT=int(os.getenv('TAIKOO_PORT','8200'))
AUTH_USER=os.getenv('TAIKOO_AUTH_USER','')
AUTH_PASSWORD=os.getenv('TAIKOO_AUTH_PASSWORD','')


@report_bp.route('/api/report/daily')
def api_report_daily():
    """日报弹窗：只含“昨天+当天发布”的有效舆情笔记（过期笔记不弹窗，仅入库做案例）。
    一天两窗口（凌晨/晚间），是否已看过由前端按 日期+窗口 归档。"""
    def _num(v):
        try: return int(v or 0)
        except (TypeError,ValueError): return 0
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        report_engine._resolve_legacy_report_scope()
    except (ValueError, PermissionError) as exc:
        return _report_failure(exc, fallback_status=409)
    try:
        today_d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        today_d = datetime.now().date()
    yesterday_s = (today_d - timedelta(days=1)).strftime('%Y-%m-%d')
    today_s = today_d.strftime('%Y-%m-%d')
    now_h = datetime.now().hour
    window = 'morning' if now_h < 15 else 'evening'  # 15点前=早间窗口，之后=晚间窗口
    clause, sp = subject_sql_and_values()
    sql = ("SELECT * FROM notes WHERE COALESCE(is_duplicate,0)=0 AND COALESCE(noise_type,'')='' "
           "AND substr(COALESCE(publish_date,publish_datetime,collected_at,''),1,10) IN (?,?) "
           f"AND {clause} ORDER BY substr(COALESCE(publish_date,publish_datetime,''),1,10) DESC, "
           "COALESCE(likes,0) DESC LIMIT 200")
    with db.get_db() as conn:
        rows_all = [dict(r) for r in conn.execute(sql, tuple([yesterday_s, today_s] + list(sp))).fetchall()]
    # 日报推送口径：只推送负面笔记（正面/中性仅作背景统计，不进推送列表）
    rows = [n for n in rows_all if n.get('sentiment') == 'negative']
    # 负面按 风险等级→风险分→互动量 排序，高风险优先推送
    _rl_order = {'high': 0, 'medium': 1, 'low': 2}
    rows.sort(key=lambda n: (_rl_order.get(n.get('risk_level'), 3),
                             -_num(n.get('risk_score')),
                             -(_num(n.get('likes')) + _num(n.get('comments')) + _num(n.get('collects')) + _num(n.get('shares')))))
    # [Canonical WRAP-08] rows_all 情感三桶一次计算；high 在已过滤负面子集 rows 上计(输入集不变)
    import canonical_metrics as _cmC
    _sC = _cmC.sentiment_count(rows_all)
    total = len(rows_all); neg, pos, neu = _sC['negative'], _sC['positive'], _sC['neutral']
    high = _cmC.risk_count(rows)['high']
    today_cnt = sum(1 for n in rows_all if (n.get('publish_date') or n.get('publish_datetime') or '')[:10] == today_s)
    yest_cnt = total - today_cnt
    brief = []
    for n in rows[:30]:
        eng = _num(n.get('likes')) + _num(n.get('comments')) + _num(n.get('collects')) + _num(n.get('shares'))
        brief.append({'note_id': n.get('note_id'), 'title': n.get('title'), 'author': n.get('author_nickname'),
                      'sentiment': n.get('sentiment'), 'risk_level': n.get('risk_level'),
                      'risk_score': n.get('risk_score'), 'ai_reason': n.get('ai_reason') or '',
                      'publish_date': (n.get('publish_date') or n.get('publish_datetime') or '')[:10], 'engagement': eng})
    stats = {'total': total, 'negative': neg, 'positive': pos, 'neutral': neu, 'high_risk': high,
             'pushed': len(rows), 'today_count': today_cnt, 'yesterday_count': yest_cnt}
    if neg == 0:
        conclusion = (f"昨日与今日共收录有效笔记 {total} 篇（昨日 {yest_cnt}、今日 {today_cnt}；"
                      f"正面 {pos}、中性 {neu}），未发现负面舆情笔记。")
    else:
        conclusion = (f"昨日与今日共收录 {total} 篇，发现负面笔记 {neg} 篇（高风险 {high}），"
                      f"日报仅推送以下负面内容，按风险高低排序；正面 {pos}、中性 {neu} 篇不进推送。")
    return jsonify({'ok': True, 'date': today_s, 'window': window,
                    'report': {'date_range': f'{yesterday_s} 至 {today_s}', 'stats': stats,
                               'conclusion': conclusion, 'notes': brief}})


@report_bp.route('/api/reports')
def api_reports_list():
    """报告列表"""
    try:
        limit = request.args.get('limit', 10, type=int)
        report_dir = str(REPORT_DIR)
        reports = []
        if os.path.exists(report_dir):
            for f in sorted(os.listdir(report_dir), reverse=True)[:limit]:
                fpath = os.path.join(report_dir, f)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    reports.append({'name': f, 'size': stat.st_size, 'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')})
        return jsonify({'ok': True, 'reports': reports, 'count': len(reports)})
    except Exception as e:
        # ZBC Phase 9: 异常不得伪装成 ok=True 空列表（假成功）
        return jsonify({'ok': False, 'reports': [], 'count': 0, 'error': str(e)}), 500


@report_bp.route('/api/reports/<path:report_id>/download')
def api_report_download(report_id):
    """报告下载-取下载链接（前端 downloadReport 契约：返回 download_url）"""
    safe = os.path.basename(report_id)
    report_dir = str(REPORT_DIR)
    if not os.path.isfile(os.path.join(report_dir, safe)):
        return jsonify({'ok': False, 'error': '报告不存在'}), 404
    from urllib.parse import quote
    return jsonify({'ok': True, 'download_url': f'/api/reports/{quote(safe)}/file', 'name': safe})


@report_bp.route('/api/reports/<path:report_id>/file')
def api_report_file(report_id):
    """报告文件实际下载"""
    safe = os.path.basename(report_id)
    report_dir = str(REPORT_DIR)
    if not os.path.isfile(os.path.join(report_dir, safe)):
        return jsonify({'ok': False, 'error': '报告不存在'}), 404
    return send_from_directory(report_dir, safe, as_attachment=True)

# ===== GAP-04 三套 run-code 统一安全收口（单一安全策略，2026-09-01）=====
# 生产默认禁用服务端任意代码执行/写静态文件，消除 RCE 与持久化注入面；
# 仅本地开发显式 ZBC_DEV_EXEC=1 放行，且仍拦截危险构造并打印审计行。三入口统一走此闸门，
# 路由保留（前端得到明确 403 契约而非 404），不删除历史能力。
_DEV_EXEC_ENABLED = os.environ.get('ZBC_DEV_EXEC', '0') == '1'
_DEV_EXEC_BLOCK_RE = re.compile(
    r'(__[\w_]+__|\b(?:import|exec|eval|compile|open|globals|locals|vars|getattr|setattr|delattr|breakpoint)\b'
    r'|os\.|sys\.|subprocess|socket|shutil|pathlib|\.write(?:_text|_bytes)?\s*\(|rmtree|(?:unlink|remove)\s*\('
    r'|environ|urllib|requests\.|http\.client|pickle)',
    re.I)


@report_bp.route('/api/report/<report_type>')
def api_report(report_type):
    # 避免与 /api/report/export 路由冲突
    if report_type == 'export':
        try:
            return api_report_export()
        except Exception as e:
            import traceback
            return jsonify({'ok': False, 'error': '导出函数调用失败: ' + str(e), 'traceback': traceback.format_exc()}), 500
    if report_type not in report_engine.REPORT_TYPES: return jsonify({'ok':False,'error':'无效报告类型'}),400
    try:
        bundle=report_engine.get_bundle(report_type, request.args.get('date') or None)
        rpt = bundle.get('report') or {}
        # ZBC Phase 9: ok 必须基于报告真实非空 + artifact 已验证，不能仅凭 dict 非空
        from lumenis.shared.reporting import artifact as ra
        vr = ra.verify_report_dict(rpt)
        ok = bool(rpt) and vr['valid']
        return jsonify({'ok':ok,'report':rpt,'digest':bundle.get('digest'),'report_type':report_type,
                        'regenerated':bundle.get('regenerated',False),
                        'artifact_verified':bundle.get('artifact_verified',False),
                        'report_id':rpt.get('report_id',''),'artifact_hash':rpt.get('artifact_hash','')})
    except Exception as exc:
        return _report_failure(exc)


@report_bp.route('/api/report/generate',methods=['POST'])
def api_generate_report():
    try:
        result=report_engine.generate_all()
        from lumenis.shared.reporting import artifact as report_artifact
        # ZBC Phase 9: 验证每个报告真实落库（有 _db_row_id 且 artifact_verified）
        verified = {}
        for typ, bundle in result.items():
            rpt = bundle.get('report') or {}
            verified[typ] = {
                'row_id': rpt.get('_db_row_id'),
                'report_id': rpt.get('report_id', ''),
                'artifact_hash': rpt.get('artifact_hash', ''),
                'artifact_verified': bool(rpt.get('_artifact_verified')),
                'report_valid': 'total_notes' in rpt and report_artifact.verify_report_dict(rpt)['valid'],
                'total_notes': rpt.get('total_notes'),
            }
        all_ok = set(verified) == set(report_engine.REPORT_TYPES) and all(
            v['artifact_verified'] and v['row_id'] and v['report_valid']
            for v in verified.values()
        )
        if not all_ok:
            return jsonify({'ok': False, 'error': '部分报告未真实落库', 'verified': verified}), 500
        return jsonify({'ok':True,'message':'日报/周报/月报/年报已生成','reports':result,'verified':verified})
    except Exception as exc:
        return _report_failure(exc)

# ===== 优化版报告API（v2）：按发布日期筛选，周期报告负面必须二次确认 =====


def _canonical_report_metrics(report_type, date_str):
    """UDIP V1.0: 报告统一消费 Canonical Metric（MET-RISK-01/02）。
    不重复计算业务 Truth：风险指数/品牌健康度仅由 daily.generate_today_summary 权威计算。
    报告展示层从此消费该字段；如与 stats 的原始计数并存，两者语义不同（聚合风险 vs 计数）。"""
    try:
        from lumenis.shared.reporting import daily as _dr
        from lumenis.shared.reporting.filtering import (filter_negative_for_period_report, classify_notes_by_age,
            get_daily_report_filter_stats, filter_notes_for_daily_report, get_report_period)
        from datetime import datetime as _dt
        d = date_str or _dt.now().strftime('%Y-%m-%d')
        try:
            _dt.strptime(d, '%Y-%m-%d')
        except Exception:
            d = _dt.now().strftime('%Y-%m-%d')
        summary = _dr.generate_today_summary(date_str=d)
        return {
            'metric_version': 'UDIP-V1.0',
            'date': d,
            'MET-RISK-01': {'name': 'risk_index', 'value': summary.get('risk_index'), 'unit': 'score 0-100', 'function': 'FUNC-RISK-01'},
            'MET-RISK-02': {'name': 'brand_health_score', 'value': summary.get('brand_health_score'), 'unit': 'score 0-100', 'function': 'FUNC-RISK-02'},
            'context': {
                'total_found': summary.get('total_found'),
                'effective_count': summary.get('effective_count'),
                'risk_count': summary.get('risk_count'),
                'events_count': summary.get('events_count'),
            },
        }
    except Exception as e:
        return {'metric_version': 'UDIP-V1.0', 'error': str(e)}


@report_bp.route('/api/report/v2/<report_type>')
def api_report_v2(report_type):

    """优化版报告API
    - 日报：只包含当日或前一日发布的笔记（按publish_date筛选）
    - 周报/月报/年报：负面笔记必须是二次确认的（negative_confirmed=1）
    - 过期笔记：标记为历史案例，不进入日报
    """
    if report_type not in ('daily', 'weekly', 'monthly', 'yearly'):
        return jsonify({'ok': False, 'error': '无效报告类型'}), 400
    
    try:
        from lumenis.shared.reporting.filtering import get_report_period, filter_notes_for_daily_report, filter_negative_for_period_report, classify_notes_by_age, get_daily_report_filter_stats
        
        date_str = request.args.get('date')
        start, end = get_report_period(report_type)
        
        # 获取该时间段内的所有笔记（按采集时间）
        all_notes = db.get_notes_by_date_range(start, end)
        
        if report_type == 'daily':
            # 日报：按发布日期筛选，只包含当日或前一日发布的笔记
            filtered_notes = filter_notes_for_daily_report(all_notes, include_yesterday=True)
            filter_stats = get_daily_report_filter_stats(all_notes)
            # 日报的负面笔记不要求二次确认（因为日报需要及时推送）
            _, negative_notes = filter_negative_for_period_report(filtered_notes, require_confirmed=False)
        else:
            # 周报/月报/年报：负面笔记必须是二次确认的
            filtered_notes = all_notes  # 周期报告不按发布日期筛选，按采集时间
            filter_stats = {'total_collected': len(all_notes)}
            _, negative_notes = filter_negative_for_period_report(filtered_notes, require_confirmed=True)
        
        # 按发布时间分类
        age_classification = classify_notes_by_age(all_notes)
        
        # 生成统计
        total = len(filtered_notes)
        # [Canonical WRAP-08] 情感/风险分桶统一；negative_count 仍取二次确认过滤后的 negative_notes(业务口径不重算)
        import canonical_metrics as _cmA
        _sA = _cmA.sentiment_count(filtered_notes); _rA = _cmA.risk_count(filtered_notes)
        positive, neutral = _sA['positive'], _sA['neutral']
        negative_count = len(negative_notes)
        high_risk = _rA['high']
        
        return jsonify({
            'ok': True,
            'report_type': report_type,
            'period': {'start': start, 'end': end},
            'filter_stats': filter_stats,
            'age_classification': {
                'recent': len(age_classification['recent']),
                'weekly': len(age_classification['weekly']),
                'monthly': len(age_classification['monthly']),
                'historical': len(age_classification['historical'])
            },
            'stats': {
                'total': total,
                'positive': positive,
                'neutral': neutral,
                'negative': negative_count,
                'negative_confirmed_required': report_type != 'daily',
                'high_risk': high_risk
            },
            'canonical': _canonical_report_metrics(report_type, date_str),
            'notes': filtered_notes[:100],  # 最多返回100条
            'negative_notes': negative_notes[:50],  # 二次确认的负面笔记
            'historical_notes': age_classification['historical'][:50]  # 历史案例笔记
        })
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@report_bp.route('/api/report/v2/stats')
def api_report_v2_stats():
    """报告筛选统计API"""
    try:
        from lumenis.shared.reporting.filtering import get_daily_report_filter_stats, classify_notes_by_age
        
        # 获取最近7天的笔记
        from datetime import datetime, timedelta
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        all_notes = db.get_notes_by_date_range(start, end)
        
        daily_stats = get_daily_report_filter_stats(all_notes)
        age_classification = classify_notes_by_age(all_notes)
        
        # 负面确认统计
        negative_total = sum(1 for n in all_notes if n.get('sentiment') == 'negative')
        negative_confirmed = sum(1 for n in all_notes if n.get('sentiment') == 'negative' and n.get('negative_confirmed') == 1)
        negative_pending = sum(1 for n in all_notes if n.get('sentiment') == 'negative' and (n.get('negative_confirmed') == 0 or n.get('negative_confirmed') is None))
        
        return jsonify({
            'ok': True,
            'daily_filter': daily_stats,
            'age_classification': {
                'recent_2days': len(age_classification['recent']),
                'within_7days': len(age_classification['weekly']),
                'within_30days': len(age_classification['monthly']),
                'historical_over_30days': len(age_classification['historical'])
            },
            'negative_confirmation': {
                'total': negative_total,
                'confirmed': negative_confirmed,
                'pending': negative_pending,
                'confirmation_rate': round(negative_confirmed / negative_total * 100, 1) if negative_total > 0 else 0
            },
            'logic_explanation': {
                'daily_report': '只包含当日或前一日发布的笔记，过期笔记放入历史案例库',
                'weekly_monthly_yearly': '负面笔记必须是二次确认的（negative_confirmed=1）才能进入报告',
                'historical_notes': '发布时间超过7天的笔记标记为历史案例，不进入日报，但可在笔记库查看'
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@report_bp.route('/api/report/verify')
def api_report_verify_v571():
    """周期报告核对：检查指定周期内的报告数据准确性"""
    report_type=request.args.get('type','daily').strip()
    date=request.args.get('date','').strip() or datetime.now().strftime('%Y-%m-%d')
    
    # 计算周期
    if report_type=='daily':
        start=end=date
    elif report_type=='weekly':
        d=datetime.strptime(date,'%Y-%m-%d')
        start=(d-timedelta(days=d.weekday())).strftime('%Y-%m-%d')
        end=(d+timedelta(days=6-d.weekday())).strftime('%Y-%m-%d')
    elif report_type=='monthly':
        d=datetime.strptime(date,'%Y-%m-%d')
        start=d.replace(day=1).strftime('%Y-%m-%d')
        if d.month==12:
            end=d.replace(year=d.year+1,month=1,day=1)-timedelta(days=1)
        else:
            end=d.replace(month=d.month+1,day=1)-timedelta(days=1)
        end=end.strftime('%Y-%m-%d')
    else:
        return jsonify({'ok':False,'error':'type仅支持daily/weekly/monthly'}),400
    
    with db.get_db() as conn:
        # 按发布日期统计
        published=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ?",(start,end)).fetchone()[0]
        # 按采集日期统计
        collected=conn.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at) BETWEEN ? AND ?",(start,end)).fetchone()[0]
        # 负面笔记（已二次确认）
        confirmed_negative=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ? AND sentiment='negative' AND negative_confirmed=1",(start,end)).fetchone()[0]
        # 待确认负面
        pending_negative=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ? AND sentiment='negative' AND negative_confirmed=0",(start,end)).fetchone()[0]
        # 高风险
        high_risk=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ? AND risk_level='high'",(start,end)).fetchone()[0]
        # 事件数
        try:
            events=conn.execute("SELECT COUNT(*) FROM events WHERE date(first_seen) BETWEEN ? AND ?",(start,end)).fetchone()[0]
        except Exception as _e:
            import logging as _log; _log.getLogger(__name__).warning('events count query failed: %s', _e); events=0
    
    return jsonify({
        'ok':True,
        'report_type':report_type,
        'period_start':start,
        'period_end':end,
        'published_in_period':published,
        'collected_in_period':collected,
        'confirmed_negative':confirmed_negative,
        'pending_negative':pending_negative,
        'high_risk':high_risk,
        'events':events,
        'warning': '报告应基于发布日期统计，采集日期仅作参考' if published!=collected else None
    })


@report_bp.route('/api/digest/today')
def api_digest_today():
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    digest = db.get_latest_digest(date_str)
    if not digest:
        # 尝试自动生成
        try:
            digest = daily.generate_daily_digest(date_str)
        except Exception as e:
            return jsonify({'ok':False,'error':str(e)}),500
    # ZBC Phase 9: 验证 digest 非空且有日期
    if not digest or not digest.get('digest_date'):
        return jsonify({'ok':False,'error':'日报摘要生成失败或为空'}),500
    return jsonify({'ok':True,'digest':digest})


@report_bp.route('/api/digest/generate', methods=['POST'])
def api_digest_generate():
    data = request.get_json(silent=True) or {}
    date_str = data.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        digest = daily.generate_daily_digest(date_str)
        return jsonify({'ok':True,'digest':digest,'message':'日报生成完成'})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)}),500

# ===== v5.3.2 AI过滤层 API =====

@report_bp.route('/api/v2/report/export')
@report_bp.route('/api/report/export')
def api_report_export():
    """兼容旧 HTTP 契约；实现统一委托 Shared Reporting canonical export facade。"""
    from lumenis.shared.reporting import export_api as canonical_export
    report_type = request.args.get('type', 'daily')
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    fmt = request.args.get('format', 'xlsx').lower()
    if report_type not in ('daily', 'weekly', 'monthly', 'yearly'):
        return jsonify({'ok': False, 'error': 'type 必须是 daily/weekly/monthly/yearly'}), 400
    if fmt not in ('xlsx', 'docx', 'csv'):
        return jsonify({'ok': False, 'error': 'format 仅支持 xlsx/docx/csv'}), 400
    try:
        start_dt, end_dt = canonical_export.get_date_range(report_type, date_str)
        result = canonical_export.export_artifacts(
            report_type,
            start_dt.strftime('%Y-%m-%d'),
            end_dt.strftime('%Y-%m-%d'),
            (fmt,),
        )
        file_path = result['files'][fmt]
        safe_name = f"Taikoo_{report_type}_{result['payload']['period_start']}.{fmt}"
        mimetype = {
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'csv': 'text/csv; charset=utf-8-sig',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }[fmt]
        return send_file(file_path, as_attachment=True, download_name=safe_name, mimetype=mimetype)
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


# ===== v5.4 系统配置 API =====



# ============================================================
# P1-D: ACT法则应对策略生成 + 案例匹配 + 专报触发记录
# ============================================================
# ACT = Acknowledge承认 → Communicate沟通 → Transform转化
# 不改变专报8板块现有结构，只在"应对策略"板块的AI prompt中加ACT约束

ACT_STRATEGY_PROMPT = """你是广州太古汇品牌公关总监。基于事件信息生成应对策略。

## 输出结构约束（ACT法则）
所有应对策略必须严格按照 ACT 三段式结构组织：

### A - Acknowledge（承认）
- 不回避问题，先共情致歉
- 明确承认事实，不辩解不甩锅
- 表达对受影响方的关切

### C - Communicate（沟通）
- 说明已采取的动作和核查进度
- 明确沟通渠道和时间节点
- 保持信息透明，不敷衍

### T - Transform（转化）
- 给出可检验的整改方案
- 将危机转为改进契机
- 明确责任方和完成时限

## 要求
1. 每个策略项必须标注属于 A/C/T 哪个阶段
2. 策略必须具体可执行，包含责任方和时限
3. 参考匹配案例的处置方式和恢复周期
4. 禁忌：不说"个人行为与商场无关"；不甩锅顾客；不隐瞒事实
5. 直接输出策略列表，不要JSON，不要多余解释

## 匹配案例参考
{matched_cases_text}

## 事件信息
{event_info}
"""


def generate_act_strategies(event_info: str, matched_cases: list = None) -> dict:
    """P1-D: 基于ACT法则生成应对策略。

    Args:
        event_info: 事件信息文本
        matched_cases: 匹配的同类案例列表（来自案例库）

    Returns:
        {ok, strategies, act_structure, provider}
    """
    matched_cases_text = ""
    if matched_cases:
        lines = []
        for c in matched_cases:
            lines.append(f"- {c.get('case_id', '')} {c.get('title', '')}: "
                         f"处置方式: {c.get('response_summary', '')[:80]}; "
                         f"太古汇启示: {c.get('taikoo_insight', '')[:100]}")
        matched_cases_text = "\n".join(lines)
    else:
        matched_cases_text = "（无匹配案例，基于通用公关原则生成）"

    prompt = ACT_STRATEGY_PROMPT.format(
        matched_cases_text=matched_cases_text,
        event_info=event_info
    )

    try:
        import intelligence
        raw, provider, _ = intelligence.chat(
            system="你是广州太古汇品牌公关总监，擅长危机公关应对策略制定。",
            user=prompt,
            level="high",
            temperature=0.3,
            max_tokens=1500,
            pack_id="glm_4_5_air"
        )
        if raw:
            # 解析ACT结构
            strategies = [s.strip() for s in raw.strip().split("\n") if s.strip()]
            return {
                "ok": True,
                "strategies": strategies,
                "act_structure": "Acknowledge→Communicate→Transform",
                "provider": provider,
                "raw": raw[:2000],
            }
    except Exception as e:
        # AI不可用时返回规则兜底策略
        pass

    # 规则兜底：基于场景生成ACT结构策略
    fallback = [
        "[A-承认] 对事件造成的影响深表歉意，承认我们在管理/服务中存在不足，不回避不辩解。",
        "[A-承认] 已第一时间联系受影响方，表达关切并了解具体情况，承担应尽责任。",
        "[C-沟通] 已成立专项小组核查事件全貌，将在24小时内公布初步调查结果，保持信息透明。",
        "[C-沟通] 设立专门沟通渠道（客服热线/私信），接受公众咨询和监督，及时回应关切。",
        "[T-转化] 立即启动整改：对涉事环节进行全面排查，完善管理制度，防止类似事件再次发生。",
        "[T-转化] 将于7个工作日内公布完整整改报告，接受公众监督，将此次危机转化为服务提升的契机。",
    ]
    return {
        "ok": True,
        "strategies": fallback,
        "act_structure": "Acknowledge→Communicate→Transform",
        "provider": "rule_fallback",
        "note": "AI不可用，返回规则兜底策略",
    }


@report_bp.route('/api/report/special/generate-strategies', methods=['POST'])
def api_generate_special_strategies():
    """P1-D: 专报应对策略生成（ACT法则 + 案例匹配）。
    Body: {event_name, event_info, scenario, trigger_reasons}
    返回: {ok, strategies, matched_cases, act_structure, trigger_reasons}
    """
    data = request.get_json(silent=True) or {}
    event_name = data.get('event_name', '')
    event_info = data.get('event_info', '')
    scenario = data.get('scenario', '')
    trigger_reasons = data.get('trigger_reasons', [])

    if not event_info and not event_name:
        return jsonify({'ok': False, 'error': 'event_info 或 event_name 不能为空'}), 400

    # Step 1: 匹配同类案例（2-3个）
    matched_cases = []
    try:
        from public_opinion_cases import match_cases_by_scenario
        matched_cases = match_cases_by_scenario(scenario, event_info, limit=3)
    except Exception as e:
        matched_cases = []

    # Step 2: 生成ACT策略
    full_event_info = f"事件名称: {event_name}\n场景: {scenario}\n触发原因: {', '.join(trigger_reasons) if trigger_reasons else '无'}\n详情: {event_info}"
    result = generate_act_strategies(full_event_info, matched_cases)

    return jsonify({
        'ok': result.get('ok', False),
        'strategies': result.get('strategies', []),
        'matched_cases': matched_cases,
        'act_structure': result.get('act_structure', ''),
        'provider': result.get('provider', ''),
        'trigger_reasons': trigger_reasons,
    })


@report_bp.route('/api/report/special/record-trigger', methods=['POST'])
def api_record_special_trigger():
    """P1-D: 专报生成时记录触发原因。
    Body: {event_id, event_name, trigger_reasons, matched_cases}
    """
    data = request.get_json(silent=True) or {}
    event_id = data.get('event_id', '')
    event_name = data.get('event_name', '')
    trigger_reasons = data.get('trigger_reasons', [])
    matched_cases = data.get('matched_cases', [])

    if not event_id:
        return jsonify({'ok': False, 'error': 'event_id 不能为空'}), 400

    # 记录到日志（不新增表，使用现有日志机制）
    try:
        import logger
        logger.info(f"[P1-D][SpecialReport] 专报触发记录: event_id={event_id}, "
                    f"event_name={event_name}, triggers={trigger_reasons}, "
                    f"matched_cases={[c.get('case_id') for c in matched_cases]}")
    except Exception:
        pass

    return jsonify({
        'ok': True,
        'event_id': event_id,
        'event_name': event_name,
        'trigger_reasons': trigger_reasons,
        'matched_cases': matched_cases,
        'recorded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })



@report_bp.route('/api/daily-report/5sections', methods=['GET'])
def api_daily_report_5sections():
    """P1-D: 获取5板块标准格式日报。"""
    from lumenis.shared.reporting.daily import generate_daily_digest, format_daily_report_5sections
    from datetime import datetime
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        digest = generate_daily_digest(date_str)
        formatted = format_daily_report_5sections(digest, date_str)
        return jsonify({'ok': True, 'report': formatted})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@report_bp.route('/api/report/special/export', methods=['POST'])
def api_special_report_export():
    data=request.get_json(silent=True) or {}
    report=data.get('report') or {}
    fmt=str(data.get('format','docx')).lower()
    if fmt not in ('docx','pdf','html'): return jsonify({'ok':False,'error':'format仅支持docx/pdf/html'}),400
    title=str(report.get('event_name') or report.get('title') or '广州太古汇舆情专报')
    safe=re.sub(r'[^0-9A-Za-z\u4e00-\u9fff_-]+','_',title)[:80]
    sections=[('一、事件概述',report.get('event_overview','')),('二、传播路径',report.get('spread_path','')),
              ('三、案例对标','\n'.join(f"{c.get('id')}｜{c.get('title')}：{c.get('taikoo_insight','')}" for c in report.get('matched_cases',[]))),
              ('四、toC影响',report.get('toc_detail','')),('五、toB影响',report.get('tob_detail','')),
              ('六、综合评级',report.get('comprehensive_level') or report.get('level','')),
              ('七、应对策略','\n'.join(map(str,report.get('strategies',[])))),
              ('八、风险预警','\n'.join(map(str,report.get('risk_warnings',[]))))]
    if fmt=='html':
        h='<html><head><meta charset="utf-8"><title>'+title+'</title></head><body><h1>'+title+'</h1>'
        for a,b in sections: h+=f'<h2>{a}</h2><div>{str(b).replace(chr(10),"<br>")}</div>'
        h+='</body></html>'
        path=Path(tempfile.gettempdir())/(safe+'.html'); path.write_text(h,encoding='utf-8')
        return send_file(path,as_attachment=True,download_name=path.name,mimetype='text/html')
    if fmt=='docx':
        try:
            from docx import Document
            doc=Document(); doc.add_heading(title,0)
            for a,b in sections:
                doc.add_heading(a,1)
                for line in str(b).splitlines() or ['—']: doc.add_paragraph(line)
            path=Path(tempfile.gettempdir())/(safe+'.docx'); doc.save(path)
            return send_file(path,as_attachment=True,download_name=path.name,mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        except Exception as exc: return jsonify({'ok':False,'error':'DOCX导出依赖未安装：'+str(exc)}),503
    try:
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        path=Path(tempfile.gettempdir())/(safe+'.pdf'); styles=getSampleStyleSheet()
        cn=ParagraphStyle('CN', parent=styles['Normal'], fontName='STSong-Light', fontSize=10, leading=16)
        h1=ParagraphStyle('CNH1', parent=styles['Heading1'], fontName='STSong-Light', fontSize=15, leading=20)
        story=[Paragraph(re.sub(r'([&<>])',lambda m:{'&':'&amp;','<':'&lt;','>':'&gt;'}[m.group(1)],title),ParagraphStyle('CNT',parent=styles['Title'],fontName='STSong-Light')),Spacer(1,12)]
        for a,b in sections:
            txt=str(b).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>')
            story += [Paragraph(str(a),h1),Paragraph(txt or '—',cn),Spacer(1,8)]
        SimpleDocTemplate(str(path)).build(story)
        return send_file(path,as_attachment=True,download_name=path.name,mimetype='application/pdf')
    except Exception as exc: return jsonify({'ok':False,'error':'PDF导出依赖未安装：'+str(exc)}),503
