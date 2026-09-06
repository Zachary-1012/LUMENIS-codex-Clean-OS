# -*- coding: utf-8 -*-
"""审计用：真实生成所有报告类型并落盘验证。"""
import json
import os
import sys
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from report_engine import generate_report, period_for

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_export", "audit")
os.makedirs(OUT_DIR, exist_ok=True)

results = {}

for rtype in ("daily", "weekly", "monthly", "yearly", "special"):
    print(f"\n{'='*60}")
    print(f"Generating {rtype} report...")
    started = datetime.now().isoformat()
    try:
        start, end = period_for(rtype)
        report, digest = generate_report(rtype, start, end)
        finished = datetime.now().isoformat()

        # 写 JSON
        fname = f"report_{rtype}_{start}_{end}.json"
        fpath = os.path.join(OUT_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        fsize = os.path.getsize(fpath)

        # 写 digest（如果有）
        digest_path = None
        if digest:
            dname = f"digest_{rtype}_{start}_{end}.json"
            digest_path = os.path.join(OUT_DIR, dname)
            with open(digest_path, "w", encoding="utf-8") as f:
                json.dump(digest, f, ensure_ascii=False, indent=2, default=str)

        results[rtype] = {
            "status": "SUCCESS",
            "started_at": started,
            "finished_at": finished,
            "file": fpath,
            "file_size": fsize,
            "digest_file": digest_path,
            "db_row_id": report.get("_db_row_id"),
            "artifact_verified": report.get("_artifact_verified"),
            "total_notes": report.get("total_notes"),
            "period": f"{start} -> {end}",
            "keys_count": len(report.keys()),
        }
        print(f"  OK: file={fpath}, size={fsize}B, db_row={report.get('_db_row_id')}, notes={report.get('total_notes')}")
    except Exception as e:
        finished = datetime.now().isoformat()
        results[rtype] = {
            "status": "FAIL",
            "started_at": started,
            "finished_at": finished,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        }
        print(f"  FAIL: {type(e).__name__}: {e}")

# 品牌报告
print(f"\n{'='*60}")
print("Generating brand report...")
started = datetime.now().isoformat()
try:
    from brand_report_generator import BrandReportGenerator
    gen = BrandReportGenerator(brand_name="广州太古汇", report_period="2026年9月", language="zh")
    # 设置母模型数据（用真实DB数据填充）
    import database as db
    notes = db.get_notes_by_date_range("2026-08-07", "2026-09-06")
    stats = db.get_stats_by_date_range("2026-08-07", "2026-09-06") or {}
    gen.set_decision_model(
        problem_center={"question": "广州太古汇近期品牌传播态势如何？", "context": f"近30天监测{stats.get('total',0)}条舆情"},
        events=[{"name": "日常舆情监测", "impact": "持续跟踪"}],
        impacts=[{"area": "品牌声誉", "level": "medium"}],
        risks=[{"risk": "负面舆情扩散", "probability": "low"}],
        evidence=[{"source": "小红书", "count": stats.get("total", 0)}],
        decisions={"short_term": ["持续监测"], "medium_term": ["优化内容策略"], "long_term": ["品牌建设"]},
    )
    gen.set_executive_summary(
        core_findings=[f"近30天共监测{stats.get('total',0)}条舆情", f"负面{stats.get('negative',0)}条"],
        key_metrics={"total": stats.get("total",0), "negative": stats.get("negative",0), "positive": stats.get("positive",0)},
        action_items=["持续日常监测", "关注高互动内容"],
    )
    gen.set_communication_analysis(
        subject_distribution={"品牌相关": stats.get("total",0)},
        channel_analysis={"小红书": stats.get("total",0)},
        effect_evaluation={"total_engagement": stats.get("total_engagements",0)},
        content_type_distribution={"图文": len([n for n in notes if n.get('type')=='note']), "视频": len([n for n in notes if n.get('type')=='video'])},
    )
    gen.set_market_intelligence(
        competitor_updates=[],
        industry_trends=["奢侈品消费回暖", "体验式零售受关注"],
        opportunities=["节日营销节点"],
        threats=["竞品促销活动"],
    )
    gen.set_public_opinion_analysis(
        sentiment_distribution={"positive": stats.get("positive",0), "neutral": stats.get("neutral",0), "negative": stats.get("negative",0)},
        hot_topics=[{"topic": "太古汇探店", "count": 3}],
        key_influencers=[],
        risk_warnings=["无重大风险"] if stats.get("negative",0) < 5 else ["需关注负面舆情"],
    )
    brand_result = gen.generate_report()
    finished = datetime.now().isoformat()
    bname = "brand_report_guangzhou_taikoo_hui.json"
    bpath = os.path.join(OUT_DIR, bname)
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump(brand_result, f, ensure_ascii=False, indent=2, default=str)
    bsize = os.path.getsize(bpath)
    # 同时导出 Markdown
    mdpath = os.path.join(OUT_DIR, "brand_report_guangzhou_taikoo_hui.md")
    gen.export_markdown(mdpath)
    mdsize = os.path.getsize(mdpath) if os.path.exists(mdpath) else 0
    results["brand"] = {
        "status": "SUCCESS",
        "started_at": started,
        "finished_at": finished,
        "file": bpath,
        "file_size": bsize,
        "markdown_file": mdpath,
        "markdown_size": mdsize,
        "keys_count": len(brand_result.keys()),
        "report_id": brand_result.get("report_id"),
    }
    print(f"  OK: json={bpath}({bsize}B), md={mdpath}({mdsize}B)")
except Exception as e:
    finished = datetime.now().isoformat()
    results["brand"] = {
        "status": "FAIL",
        "started_at": started,
        "finished_at": finished,
        "error": f"{type(e).__name__}: {e}",
        "traceback": traceback.format_exc()[-2000:],
    }
    print(f"  FAIL: {type(e).__name__}: {e}")

# 写汇总
summary_path = os.path.join(OUT_DIR, "_generation_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"\n{'='*60}")
print("SUMMARY:")
for k, v in results.items():
    print(f"  {k}: {v['status']} ({v.get('file_size', 'N/A')}B)")
print(f"\nSummary written to: {summary_path}")
