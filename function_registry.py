# -*- coding: utf-8 -*-
"""广州太古汇舆情系统：函数/数据目标映射与统一检索层。

设计目标：把“用户问题/系统功能/底层数据源/页面”建立稳定映射。
不改变原有主体过滤口径；该模块只负责查询与路由，不负责放宽采集范围。
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(__file__).resolve().parent
BRAND_FILE = BASE / "data" / "brand_directory.json"
WEBSITE_FILE = BASE / "data" / "brand_websites.json"
CASE_FILE = BASE / "data" / "case_library.json"

FUNCTION_MAP = [
    {"id":"overview.stats","page":"overview","label":"舆情总览","targets":["notes","events","alerts","daily_digest"],"keywords":["总览","概况","趋势","舆情","数据","负面占比","互动量"]},
    {"id":"monitor.collect","page":"monitor","label":"实时监测/采集","targets":["rednote_cdp","collection_logs","collector_quality_log"],"keywords":["采集","更新","rednote","小红书","cdp","登录态","验证码","采集状态"]},
    {"id":"alerts.risk","page":"alerts","label":"风险预警","targets":["notes","alerts","comments"],"keywords":["风险","预警","高风险","危机","严重","安全","歧视","违法","活动","排队","秩序"]},
    {"id":"events.center","page":"events","label":"事件中心","targets":["events","event_mentions","event_insights"],"keywords":["事件","传播路径","聚类","扩散","事件中心","活动","排队","秩序"]},
    {"id":"topics.hot","page":"topics","label":"热门话题","targets":["feedback_keywords","notes"],"keywords":["热门","话题","热词","趋势话题"]},
    {"id":"notes.search","page":"notes","label":"笔记搜索","targets":["notes","note_comments","note_review_history"],"keywords":["笔记","搜索","帖子","评论","作者","点赞","收藏"]},
    {"id":"analysis.multi","page":"analysis","label":"数据分析","targets":["notes","events","daily_reports"],"keywords":["分析","情感","业态分析","风险分布","环比"]},
    {"id":"brands.matrix","page":"brands","label":"品牌业态","targets":["brand_directory","brand_websites","notes"],"keywords":["品牌","业态","场内品牌","官网","商户","店铺","楼层"]},
    {"id":"official.info","page":"official","label":"官方动态","targets":["official_info","brand_websites"],"keywords":["官网","官方","微博","微信","品牌官网","官方动态"]},
    {"id":"cases.library","page":"cases","label":"全网案例库","targets":["case_library"],"keywords":["案例","公关","话术","回复","危机处理","标杆","反面教材"]},
    {"id":"calendar.risk","page":"calendar","label":"舆情日历","targets":["notes","events"],"keywords":["日历","当天","某天","每日","日期","发布"]},
    {"id":"reports.center","page":"reports","label":"报告中心","targets":["daily_reports","daily_digest"],"keywords":["日报","周报","月报","年报","专报","汇报","导出"]},
    {"id":"settings.system","page":"settings","label":"系统设置","targets":["config","brand_directory","email"],"keywords":["设置","邮箱","域名","频率","品牌管理","AI配置"]},
    {"id":"assistant.nomi","page":"nomi","label":"诺米AI助手","targets":["all"],"keywords":["诺米","助手","帮我分析","为什么","怎么处理","建议"]},
    {"id":"FUNC-CONTENT-02","page":"analysis","label":"情感分析（统一真相源）","targets":["canonical_data","notes"],"keywords":["情感","sentiment","正负向","情感分析","情感分布","正面","负面","中性"],"single_truth":"canonical_data.sentiment","implementation":"canonical_data.unified_sentiment_analysis"},
    {"id":"topics.heat","page":"topics","label":"话题热度（派生率）","targets":["topic_campaign_snapshots","topic_campaign_notes"],"keywords":["话题热度","热词","热度","派生率","话题趋势","topic heat"]},
    {"id":"events.propagation","page":"events","label":"事件传播链","targets":["event_graph","events","event_mentions"],"keywords":["传播链","传播路径","事件传播","扩散路径","event graph","传播分析"]},
    {"id":"campaign.effect","page":"topics","label":"Campaign效果聚合","targets":["topic_campaign_notes","topic_campaign_snapshots"],"keywords":["campaign效果","活动效果","专题效果","campaign","活动数据","专题数据"]},
    {"id":"reports.aggregation","page":"reports","label":"报告聚合（日/周/月/年）","targets":["daily_reports","weekly_reports","monthly_reports","annual_reports"],"keywords":["日报","周报","月报","年报","报告聚合","daily report","weekly report","monthly report","annual report"]},
]

def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def load_brands() -> List[dict]:
    d = _load_json(BRAND_FILE, {})
    return d.get("brands", []) if isinstance(d, dict) else []

def load_websites() -> Dict[str,dict]:
    d = _load_json(WEBSITE_FILE, {})
    return d.get("brands", {}) if isinstance(d, dict) else {}

def load_cases() -> List[dict]:
    d = _load_json(CASE_FILE, {})
    return d.get("cases", []) if isinstance(d, dict) else []

def search_targets(q: str, db=None, limit: int = 12) -> Dict[str, Any]:
    q = (q or "").strip()
    ql = q.lower()
    tokens = [t for t in re.split(r"[\s,，。！？、/|:：;；]+", ql) if len(t) >= 2]
    # 功能匹配
    scored = []
    for f in FUNCTION_MAP:
        score = sum(3 for k in f["keywords"] if k.lower() in ql)
        if f["page"] in ql or f["id"].lower() in ql:
            score += 4
        if score:
            scored.append((score, f))
    scored.sort(key=lambda x:x[0], reverse=True)
    functions = [f for _,f in scored[:5]]

    brands = []
    for b in load_brands():
        hay = " ".join(str(b.get(k,"")) for k in ("brand_en","brand_cn","category","shop","floor")).lower()
        if any(t in hay for t in tokens) or (ql and ql in hay):
            brands.append(b)
    websites = []
    wm = load_websites()
    for name, b in wm.items():
        hay = " ".join([name, str(b.get("brand_cn","")), str(b.get("category","")), str(b.get("website",""))]).lower()
        if any(t in hay for t in tokens) or (ql and ql in hay):
            websites.append({"brand_en":name, **b})
    cases = []
    for c in load_cases():
        hay = " ".join(str(c.get(k,"")) for k in ("id","category","title","event","taikoo_insight","reply_formula")).lower()
        if any(t in hay for t in tokens) or (ql and ql in hay):
            cases.append(c)
    # DB检索：严格沿用 database.get_notes 的既有过滤体系
    notes = []
    events = []
    if db:
        try:
            if q:
                notes = db.get_notes({"keyword": q}, limit, 0)
        except Exception:
            try: notes = db.get_notes({"keyword": tokens[0]} if tokens else {}, limit, 0)
            except Exception: notes = []
        try:
            events = [e for e in db.get_events(30) if ql in (str(e.get("title",""))+" "+str(e.get("summary",""))).lower()][:limit]
        except Exception:
            events = []
    return {
        "ok": True, "query": q, "functions": functions,
        "brands": brands[:limit], "websites": websites[:limit],
        "cases": cases[:limit], "notes": notes[:limit], "events": events[:limit],
        "meta": {"brand_total": len(load_brands()), "website_total": len(wm), "case_total": len(load_cases())}
    }

def build_context(q: str, db=None) -> str:
    r = search_targets(q, db, 8)
    chunks = []
    if r["functions"]:
        chunks.append("功能目标："+", ".join(f["label"] for f in r["functions"]))
    if r["brands"]:
        chunks.append("匹配品牌："+", ".join((b.get("brand_cn") or b.get("brand_en","")) for b in r["brands"][:6]))
    if r["websites"]:
        chunks.append("品牌官网："+", ".join(f'{x.get("brand_en")}: {x.get("website") or "未配置"}' for x in r["websites"][:6]))
    if r["cases"]:
        chunks.append("案例："+", ".join(f'{c.get("id")} {c.get("title")}' for c in r["cases"][:5]))
    if r["notes"]:
        chunks.append("相关笔记："+", ".join((n.get("title") or n.get("summary") or "")[:45] for n in r["notes"][:5]))
    if r["events"]:
        chunks.append("相关事件："+", ".join((e.get("title") or "")[:40] for e in r["events"][:5]))
    return "\n".join(chunks) if chunks else "未检索到与问题直接对应的结构化记录。"


# ── Phase 13: SkillRegistry integration (read-only, bypass-safe) ──
_MODULE_STATUS = "ACTIVE"
_PHASE13_COMPAT = "skill_registry.SkillRegistry via register_functions_as_skills()"


def register_functions_as_skills(registry=None):
    """Register FUNCTION_MAP entries as LOW-risk READ_ONLY skills in SkillRegistry.

    This is a read-only registration: each function mapping becomes a metadata-only
    skill entry. No execution capability is granted. Returns registration results.
    """
    try:
        from skill_registry import (
            get_skill_registry, SkillMetadata, RiskLevel,
            ExecutionPolicy, EvaluationStatus,
        )
    except ImportError:
        return {"registered": 0, "errors": ["skill_registry not importable"]}

    reg = registry or get_skill_registry()
    results = []
    for func in FUNCTION_MAP:
        fid = "zbc.func." + func["id"].replace(".", "_")
        meta = SkillMetadata(
            skill_id=fid,
            version="1.0.0",
            owner="core-team",
            permission_level="READ",
            input_schema={"type": "object", "properties": {
                "query": {"type": "string"},
            }, "required": []},
            output_schema={"type": "object", "properties": {
                "functions": {"type": "array"},
                "brands": {"type": "array"},
            }},
            risk_level=RiskLevel.LOW,
            execution_policy=ExecutionPolicy.READ_ONLY,
            evidence_contract=(
                "Function mapping lookup only; returns matched functions/brands/cases. "
                "No DB writes, no subject rule modification."
            ),
            evaluation_status=EvaluationStatus.EVALUATED,
            description=func.get("label", fid),
            tags=["function_map", "readonly", func.get("page", "")],
        )
        r = reg.register(meta)
        results.append(r)
    return {
        "registered": sum(1 for r in results if r.get("registered")),
        "total": len(results),
        "errors": [e for r in results for e in r.get("errors", [])],
    }

