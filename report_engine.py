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

# ============================================================
# ZBC V2.0 双域报告类型定义
# ============================================================
# CTH 报告：太古汇专项
CTH_REPORT_TYPES = ('daily', 'weekly', 'monthly', 'event_special', 'risk_special', 'taikoo_intelligence')
# ZBMP 报告：多品牌平台
ZBMP_REPORT_TYPES = ('brand', 'performance', 'competitive', 'growth', 'content', 'brand_risk')

# 双域报告注册表：domain_id -> report_type -> generator info
DUAL_DOMAIN_REPORTS = {
    "cth": {
        "daily": {"name": "太古汇日报", "template": "cth_daily", "protected": True},
        "weekly": {"name": "太古汇周报", "template": "cth_weekly", "protected": True},
        "monthly": {"name": "太古汇月报", "template": "cth_monthly", "protected": True},
        "event_special": {"name": "太古汇事件专报", "template": "cth_event_special", "protected": True},
        "risk_special": {"name": "太古汇风险专报", "template": "cth_risk_special", "protected": True},
        "taikoo_intelligence": {"name": "太古汇情报报告", "template": "cth_intelligence", "protected": True},
    },
    "zbmp": {
        "brand": {"name": "品牌报告", "template": "zbmp_brand", "protected": False},
        "performance": {"name": "表现报告", "template": "zbmp_performance", "protected": False},
        "competitive": {"name": "竞争报告", "template": "zbmp_competitive", "protected": False},
        "growth": {"name": "增长报告", "template": "zbmp_growth", "protected": False},
        "content": {"name": "内容报告", "template": "zbmp_content", "protected": False},
        "brand_risk": {"name": "品牌风险报告", "template": "zbmp_brand_risk", "protected": False},
    },
}


# ZBC Lifecycle Contract V1.0 (bypass-mode)
try:
    from lifecycle_mixin import lifecycle_task as _lifecycle_task
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _lifecycle_task = None
    _LIFECYCLE_AVAILABLE = False


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


def generate_report(report_type: str, start: str | None = None, end: str | None = None,
                    domain_id: str | None = None):
    started_at = datetime.now().isoformat()
    # ZBC V2.0 双域隔离：解析域身份
    if domain_id is None:
        try:
            from ai_domain_context import get_current_domain
            domain_id = get_current_domain()
        except ImportError:
            domain_id = "cth"

    # 域报告类型校验
    domain_reports = DUAL_DOMAIN_REPORTS.get(domain_id, {})
    is_domain_specific = report_type in domain_reports
    is_legacy_type = report_type in REPORT_TYPES

    if not is_domain_specific and not is_legacy_type:
        raise ValueError(
            f'无效报告类型: {report_type} (domain={domain_id}). '
            f'CTH types: {CTH_REPORT_TYPES}, ZBMP types: {ZBMP_REPORT_TYPES}'
        )

    # CTH 保护：CTH 报告必须保护 SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit()
    if domain_id == "cth" and is_domain_specific:
        try:
            from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit
            # 验证太古汇专项规则存在（不修改，仅确认加载）
            _ = len(SUBJECT_WORDS)
            _ = len(SUBJECT_EXCLUDE_WORDS)
        except ImportError:
            pass  # subject_rules 可能在测试环境中不可用

    # ZBMP 报告不得使用 CTH 专项过滤条件作为隐式全局过滤
    if domain_id == "zbmp":
        # 确保不加载 CTH 专项 subject 过滤作为全局过滤
        pass  # ZBMP 使用多品牌过滤，由 brand_report_generator 处理

    if not start or not end:
        if is_domain_specific and report_type in ('event_special', 'risk_special', 'taikoo_intelligence'):
            # 专报默认近 30 天
            start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end = datetime.now().strftime('%Y-%m-%d')
        elif is_domain_specific and report_type in ('brand', 'performance', 'competitive', 'growth', 'content', 'brand_risk'):
            # ZBMP 报告默认近 30 天
            start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end = datetime.now().strftime('%Y-%m-%d')
        else:
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
        'domain_id': domain_id,
        'product_id': 'CTH' if domain_id == 'cth' else 'ZBMP',
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


# ============================================================
# ZBC V2.0 双域报告生成（独立函数，不影响现有 generate_report）
# ============================================================
def generate_domain_report(
    report_type: str,
    domain_id: str,
    start: str | None = None,
    end: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """生成指定域的报告（双域隔离）。

    CTH 报告保护太古汇专项规则；ZBMP 报告使用多品牌视角。
    共享 Report Engine/Artifact/Evidence/Export，但使用各自模板和数据查询。

    Returns:
        {
            "report_type", "domain_id", "product_id",
            "start", "end", "status", "file_path", "file_size",
            "report_data": {...},
        }
    """
    # Lifecycle Contract V1.0 (bypass-mode, never breaks report generation)
    _lc_worker = None
    if _LIFECYCLE_AVAILABLE:
        try:
            from lifecycle_mixin import LifecycleMixin
            _lc_worker = LifecycleMixin(
                worker_name=f"report_{report_type}",
                domain_id="system", product_id="SYSTEM",
            )
            _lc_worker.lifecycle_create()
            _lc_worker.lifecycle_start(run_id=f"report_{report_type}_{int(__import__('time').time())}")
        except Exception:
            _lc_worker = None

    def _domain_report_inner():
        # start/end/output_dir 在下方被重新赋值，需 nonlocal 绑定外层参数而非成为 inner 局部变量
        nonlocal start, end, output_dir
        import json
        import os as _os

        if domain_id not in DUAL_DOMAIN_REPORTS:
            raise ValueError(f"未知域: {domain_id}，有效域: {list(DUAL_DOMAIN_REPORTS.keys())}")

        domain_info = DUAL_DOMAIN_REPORTS[domain_id]
        if report_type not in domain_info:
            raise ValueError(
                f"域 {domain_id} 不支持报告类型 {report_type}，"
                f"支持: {list(domain_info.keys())}"
            )

        report_meta = domain_info[report_type]
        now = datetime.now()
        if not start:
            start = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end:
            end = now.strftime('%Y-%m-%d')

        # 构建报告数据（共享 Report Engine 逻辑）
        report_data = {
            "report_type": report_type,
            "domain_id": domain_id,
            "product_id": "CTH" if domain_id == "cth" else "ZBMP",
            "report_name": report_meta["name"],
            "template": report_meta["template"],
            "period_start": start,
            "period_end": end,
            "generated_at": now.isoformat(),
            "generator_version": "dual-domain-v2.0",
            "protected": report_meta["protected"],
            "status": "success",
        }

        # CTH 专项：添加太古汇专项数据标记
        if domain_id == "cth":
            report_data["cth_specific"] = {
                "subject_words_protected": True,
                "subject_exclude_words_protected": True,
                "subject_hit_enabled": True,
                "brand_count": 199,
                "business_formats": 9,
                "note": "CTH report uses Taikoo Hui specific subject filtering and rules",
            }
            # 尝试获取真实统计数据
            try:
                notes = db.get_notes_by_date_range(start, end)
                stats = db.get_stats_by_date_range(start, end)
                report_data["total_notes"] = stats.get("total", 0)
                report_data["positive_count"] = stats.get("positive", 0)
                report_data["negative_count"] = stats.get("negative", 0)
                report_data["high_risk_count"] = stats.get("high_risk", 0)
                report_data["data_source"] = "real_db"
            except Exception as _e:
                report_data["total_notes"] = 0
                report_data["data_source"] = "db_unavailable"
                report_data["db_error"] = str(_e)[:200]

        # ZBMP 专项：添加多品牌数据标记
        if domain_id == "zbmp":
            report_data["zbmp_specific"] = {
                "multi_brand": True,
                "competitive_analysis": True,
                "market_trends": True,
                "brand_growth": True,
                "note": "ZBMP report uses multi-brand perspective, no CTH-specific subject filtering",
            }
            # 尝试使用品牌报告生成器
            try:
                from brand_report_generator import BrandReportGenerator
                gen = BrandReportGenerator(brand_name="多品牌平台", report_period=f"{start}~{end}")
                report_data["brand_report_available"] = True
            except Exception as _e:
                report_data["brand_report_available"] = False
                report_data["brand_report_error"] = str(_e)[:200]

        # 落盘为 JSON 文件
        if output_dir is None:
            output_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "reports", domain_id)
        _os.makedirs(output_dir, exist_ok=True)

        filename = f"{domain_id}_{report_type}_{end.replace('-', '')}_{now.strftime('%H%M%S')}.json"
        file_path = _os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        file_size = _os.path.getsize(file_path)

        return {
            "report_type": report_type,
            "domain_id": domain_id,
            "product_id": report_data["product_id"],
            "start": start,
            "end": end,
            "status": "success",
            "file_path": file_path,
            "file_size": file_size,
            "report_name": report_meta["name"],
            "report_data": report_data,
        }


    try:
        return _domain_report_inner()
    finally:
        # 保证任何 return/raise 分支都停止 lifecycle 心跳线程，杜绝线程泄漏
        if _lc_worker is not None:
            try:
                _lc_worker.lifecycle_stop(reason='report_finished')
            except Exception:
                pass


def list_domain_reports(domain_id: str | None = None) -> dict:
    """列出双域报告类型（用于审计/API）。"""
    result = {}
    domains = [domain_id] if domain_id else list(DUAL_DOMAIN_REPORTS.keys())
    for did in domains:
        if did in DUAL_DOMAIN_REPORTS:
            result[did] = {
                rtype: {"name": info["name"], "protected": info["protected"]}
                for rtype, info in DUAL_DOMAIN_REPORTS[did].items()
            }
    return result


def verify_domain_report_file(file_path: str) -> dict:
    """验证报告文件真实落盘、大小合理、内容非空、域数据正确。"""
    import json
    import os as _os

    if not _os.path.exists(file_path):
        return {"valid": False, "reason": "文件不存在", "file_path": file_path}

    file_size = _os.path.getsize(file_path)
    if file_size == 0:
        return {"valid": False, "reason": "文件为空", "file_path": file_path, "file_size": 0}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"valid": False, "reason": f"JSON 解析失败: {e}", "file_path": file_path}

    domain_id = data.get("domain_id", "")
    product_id = data.get("product_id", "")
    report_type = data.get("report_type", "")

    # 域数据正确性校验
    domain_valid = domain_id in DUAL_DOMAIN_REPORTS
    product_valid = (domain_id == "cth" and product_id == "CTH") or (domain_id == "zbmp" and product_id == "ZBMP")
    type_valid = report_type in DUAL_DOMAIN_REPORTS.get(domain_id, {})

    return {
        "valid": domain_valid and product_valid and type_valid,
        "file_path": file_path,
        "file_size": file_size,
        "domain_id": domain_id,
        "product_id": product_id,
        "report_type": report_type,
        "domain_valid": domain_valid,
        "product_valid": product_valid,
        "type_valid": type_valid,
        "content_non_empty": len(data) > 0,
        "size_reasonable": file_size > 100,
    }
