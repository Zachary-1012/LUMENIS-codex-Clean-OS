"""报告中心核心引擎 v5.6.3。

统一负责：日报、周报、月报、年报的生成、读取与客户预览数据。
所有统计通过 database.py 的广州太古汇主体硬过滤，不在报告层自行放宽口径。

ZBC Phase 9 加固：
- 生成后必须验证 DB artifact 真实落库（report_id 可追溯）
- 报告携带 report_id / artifact_hash / generator_version / data_version
- get_bundle 区分"缓存命中"与"即时生成"，避免静默重复生成导致数据漂移
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import database as db
import ai_analyzer
import ai_filter
import daily_report
import report_artifact as ra

logger = logging.getLogger(__name__)

REPORT_TYPES = ('daily', 'weekly', 'monthly', 'yearly', 'special')


def period_for(report_type: str, now: datetime | None = None):
    now = now or datetime.now()
    today = now.strftime('%Y-%m-%d')
    if report_type == 'daily':
        return today, today
    if report_type == 'weekly':
        return (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d'), today
    if report_type == 'monthly':
        return now.replace(day=1).strftime('%Y-%m-%d'), today
    if report_type == 'yearly':
        return now.replace(month=1, day=1).strftime('%Y-%m-%d'), today
    if report_type == 'special':
        # 专报：默认近 30 天；调用方可传 start/end 自定义（generate_report 优先用自定义）
        return (now - timedelta(days=30)).strftime('%Y-%m-%d'), today
    raise ValueError(f'无效报告类型: {report_type}')


def generate_report(report_type: str, start: str | None = None, end: str | None = None):
    started_at = datetime.now().isoformat()
    if report_type not in REPORT_TYPES:
        raise ValueError(f'无效报告类型: {report_type}')
    if not start or not end:
        start, end = period_for(report_type)

    # 先过滤，再统计；报告不读取未经主体审核的数据。
    try:
        ai_filter.run_filter_batch(limit=500)
    except Exception as _e:
        logger.warning('ai_filter.run_filter_batch failed (non-blocking): %s', _e)

    notes = db.get_notes_by_date_range(start, end)
    stats = db.get_stats_by_date_range(start, end)
    report = ai_analyzer.generate_period_report(notes, stats, report_type, start, end)
    # 强制把统计口径写回报告，避免 AI 摘要误写数字。
    report.update({
        'report_type': report_type,
        'report_date': end,
        'period_start': start,
        'period_end': end,
        'total_notes': stats.get('total', 0),
        'positive_count': stats.get('positive', 0),
        'neutral_count': stats.get('neutral', 0),
        'negative_count': stats.get('negative', 0),
        'high_risk_count': stats.get('high_risk', 0),
        'medium_risk_count': stats.get('medium_risk', 0),
        'low_risk_count': stats.get('low_risk', 0),
        'total_likes': stats.get('total_likes', 0),
        'total_comments': stats.get('total_comments', 0),
        'total_engagements': stats.get('total_engagements', 0),
    })
    # 报告体系消费营销节点（芥子→须弥）：当月节点/主题/建议调性进报告，供排期与决策
    try:
        from scripts.marketing_calendar import (suggest_hotspot, cross_industry_season,
                                                cross_global, global_nodes, region_nodes)
        _mc = suggest_hotspot(end, "商业地产")
        report['marketing_nodes'] = {
            "nodes": [n["name"] for n in _mc.get("nodes", [])],
            "themes": _mc.get("themes", []),
            "tonality_advice": _mc.get("tonality_advice", ""),
            "cross": cross_industry_season("商业地产", end[:7]).get("advice", []),
            "global": cross_global(date_str=end[:7]).get("advice", []),
            "global_nodes": [n["name"] for n in global_nodes(int(end[5:7]))],
            "region": {r: [n["name"] for n in region_nodes(r, int(end[5:7]))]
                       for r in ["东南亚", "欧洲", "中东", "拉美", "北美", "东亚", "澳新"]},
        }
    except Exception as _e:
        logger.warning('marketing_calendar import failed (non-blocking): %s', _e)
        report['marketing_nodes'] = {"nodes": [], "themes": [], "tonality_advice": "",
                                     "cross": [], "global": [], "global_nodes": [],
                                     "region": {}}
    # 报告消费 EMV（芥子→须弥）：MET-CONTENT-04 估算媒体价值，独立开关、失败不阻塞报告生成
    try:
        import emv as _emv
        report['emv'] = _emv.aggregate_emv(notes)
    except Exception as _e:
        logger.warning('emv aggregate failed (non-blocking): %s', _e)
        report['emv'] = {"status": "NOT_AVAILABLE", "emv_total_yuan": None,
                         "note_count": len(notes), "available_count": 0,
                         "is_estimate": True,
                         "disclaimer": "EMV 引擎不可用，未估算"}

    # ===== ZBC Phase 9: artifact 元数据 + 真实性校验 =====
    meta = ra.build_artifact_metadata(report_type, start, end, report_data=report)
    report.update(meta)
    # source_snapshot：记录数据来源口径（publish_date 区间 + 主体过滤已由 db 层保证）
    report['source_snapshot'] = f"notes:publish_date[{start},{end}];subject:verified;stats_count={stats.get('total', 0)}"

    # 落库并验证：save_daily_report 返回行 id，id 必须 > 0 才算真实落库
    row_id = db.save_daily_report(report)
    if not row_id or row_id <= 0:
        raise RuntimeError(f"报告落库失败: save_daily_report 返回无效 row_id={row_id}")
    report['_db_row_id'] = row_id
    report['_artifact_verified'] = True

    digest = None
    if report_type == 'daily':
        digest = daily_report.generate_daily_digest(end)
    report['started_at'] = started_at
    report['finished_at'] = datetime.now().isoformat()
    report['status'] = 'success'
    report['error'] = None
    return report, digest


def generate_all(now: datetime | None = None):
    out = {}
    for typ in REPORT_TYPES:
        report, digest = generate_report(typ, *period_for(typ, now))
        out[typ] = {'report': report, 'digest': digest}
    return out


def get_bundle(report_type: str, date_str: str | None = None):
    if report_type not in REPORT_TYPES:
        raise ValueError(f'无效报告类型: {report_type}')
    report = db.get_latest_report(report_type)
    if date_str and report and report.get('report_date') != date_str:
        report = None
    if not report:
        # 缓存未命中：即时生成（标记 regenerated=True，便于上层判断数据漂移风险）
        report, digest = generate_report(report_type, *(period_for(report_type)))
        return {'report': report, 'digest': digest, 'report_type': report_type,
                'regenerated': True, 'artifact_verified': report.get('_artifact_verified', False)}
    else:
        digest = db.get_latest_digest(report.get('report_date')) if report_type == 'daily' else None
        # 缓存命中：验证报告 dict 基本真实性
        vr = ra.verify_report_dict(report)
        return {'report': report, 'digest': digest, 'report_type': report_type,
                'regenerated': False, 'artifact_verified': vr['valid']}
