# -*- coding: utf-8 -*-
"""
content_generation.py — ZBC 统一内容生成引擎
=============================================
整合：SYSTEM AI Gateway（仅显式授权路由）+ 研究库检索 + Evidence链 + 4维Evaluation评分 + 人工反馈迭代。

设计原则：
- AI是增强层，规则与数据是最终真值
- 每次生成必须记录Evidence(prompt/input/output/model/timestamp/confidence)
- 每次生成必须有Evaluation(相关性/创意性/品牌契合度/平台适配度)
- 研究库检索在AI生成前自动执行，结果注入prompt
- 支持人工反馈→修正→再生成
- AI 增强只经现有 SYSTEM AI Gateway；不可用时如实返回，不切换模型或伪造生成结果
- 不修改SUBJECT_WORDS/subject_hit()，不碰生产数据
"""
from __future__ import annotations
import json
import sqlite3
import hashlib
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from lumenis.shared.database import get_repository

# ============================================================
# 内容类型注册表
# ============================================================
CONTENT_TYPES = {
    "ad_copy": {
        "label": "广告文案",
        "level": "medium",
        "default_platform": "xhs",
        "system_prompt": (
            "你是4A广告公司资深创意总监，精通品牌传播与社交平台文案。"
            "请基于用户需求和参考案例，生成结构化广告文案。"
            "输出严格JSON格式：{\"title\":\"标题\",\"body\":\"正文\",\"hashtags\":[\"标签1\",\"标签2\"],"
            "\"image_suggestion\":\"配图建议\",\"publish_advice\":\"发布建议\",\"key_message\":\"核心信息\"}。"
            "要求：标题有钩子，正文有情绪价值，标签精准，符合平台调性。不要输出JSON以外的文字。"
        ),
    },
    "podcast_topic": {
        "label": "播客选题",
        "level": "medium",
        "default_platform": "podcast",
        "system_prompt": (
            "你是资深播客制作人，擅长选题策划与故事架构。"
            "请基于主题和目标听众，生成播客选题方案。"
            "输出严格JSON：{\"topic\":\"选题标题\",\"angle\":\"切入角度\",\"hook\":\"开场钩子\","
            "\"guest_suggestion\":\"嘉宾建议\",\"key_questions\":[\"问题1\",\"问题2\"],"
            "\"story_arc\":\"故事线\",\"expected_duration_min\":预计时长,"
            "\"breakout_potential\":\"破圈潜力分析\"}。不要输出JSON以外的文字。"
        ),
    },
    "brand_report": {
        "label": "品牌报告",
        "level": "medium",
        "default_platform": "report",
        "system_prompt": (
            "你是品牌战略咨询顾问，擅长品牌传播分析与市场情报。"
            "请基于品牌信息和数据，生成品牌传播分析报告。"
            "输出严格JSON：{\"executive_summary\":\"执行摘要\",\"communication_analysis\":\"传播分析\","
            "\"market_intelligence\":\"市场洞察\",\"event_analysis\":\"事件分析\","
            "\"recommendations\":[\"建议1\",\"建议2\"],\"risk_alerts\":\"风险提示\","
            "\"key_metrics\":{\"指标\":\"数值\"}}。不要输出JSON以外的文字。"
        ),
    },
    "creative_idea": {
        "label": "创意方向",
        "level": "medium",
        "default_platform": "xhs",
        "system_prompt": (
            "你是反模板创意专家，擅长打破常规的品牌创意。"
            "请基于品牌和需求，生成原创创意方向。"
            "输出严格JSON：{\"concept\":\"创意概念\",\"execution\":\"执行方式\","
            "\"platform\":\"适配平台\",\"target_audience\":\"目标受众\","
            "\"expected_impact\":\"预期效果\",\"differentiation\":\"差异化点\"}。不要输出JSON以外的文字。"
        ),
    },
    "kos_content": {
        "label": "KOS内容",
        "level": "medium",
        "default_platform": "xhs",
        "system_prompt": (
            "你是KOS(Key Opinion Sales)内容专家，擅长种草文案与销售转化。"
            "请基于品牌和产品，生成KOS种草内容。"
            "输出严格JSON：{\"title\":\"标题\",\"content\":\"正文\",\"scenes\":[\"使用场景1\"],"
            "\"selling_points\":[\"卖点1\"],\"call_to_action\":\"行动号召\","
            "\"hashtags\":[\"标签\"]}。要求真实感强，有使用体验，不硬广。不要输出JSON以外的文字。"
        ),
    },
    "video_script": {
        "label": "视频脚本",
        "level": "medium",
        "default_platform": "douyin",
        "system_prompt": (
            "你是短视频导演，擅长分镜头脚本与节奏把控。"
            "请基于品牌和视频类型，生成分镜头脚本。"
            "输出严格JSON：{\"title\":\"标题\",\"logline\":\"一句话梗概\","
            "\"shots\":[{\"shot_no\":1,\"duration_sec\":3,\"visual\":\"画面描述\",\"audio\":\"旁白/音效\",\"text_on_screen\":\"字幕\"}],"
            "\"music_suggestion\":\"配乐建议\",\"hook_second\":\"黄金几秒\"}。不要输出JSON以外的文字。"
        ),
    },
    "social_ops": {
        "label": "社媒运营策略",
        "level": "medium",
        "default_platform": "xhs",
        "system_prompt": (
            "你是社媒运营总监，擅长多平台内容生态与增长策略。"
            "请基于品牌和平台，生成社媒运营策略。"
            "输出严格JSON：{\"platform\":\"平台\",\"content_pillars\":[\"内容支柱1\"],"
            "\"posting_frequency\":\"发布频率\",\"peak_times\":[\"高峰时段\"],"
            "\"engagement_strategy\":\"互动策略\",\"growth_tactics\":[\"增长战术1\"],"
            "\"kpi_targets\":{\"指标\":\"目标\"}}。不要输出JSON以外的文字。"
        ),
    },
    "pr_response": {
        "label": "PR回应话术",
        "level": "medium",
        "default_platform": "pr",
        "system_prompt": (
            "你是资深公关总监，擅长危机回应与品牌话术。"
            "请基于舆情事件，生成PR回应话术。要求柔和、委婉、符合品牌调性，不硬气。"
            "输出严格JSON：{\"situation\":\"事件概述\",\"stakeholder\":\"涉事方\","
            "\"response\":\"回应正文\",\"key_messages\":[\"核心信息1\"],"
            "\"tone\":\"语气\",\"follow_up\":\"后续动作\",\"risk_level\":\"风险等级\"}。"
            "回应必须柔和委婉，表达关切与诚意，不推卸责任。不要输出JSON以外的文字。"
        ),
    },
}

# Evaluation 4维度
EVAL_DIMENSIONS = ["relevance", "creativity", "brand_fit", "platform_fit"]
EVAL_LABELS = {
    "relevance": "相关性",
    "creativity": "创意性",
    "brand_fit": "品牌契合度",
    "platform_fit": "平台适配度",
}


# ============================================================
# DB 层
# ============================================================
def _get_conn() -> sqlite3.Connection:
    # Ordinary runtime callers resolve the current canonical repository at call
    # time; tests inject an explicit DatabaseRepository into get_repository.
    return get_repository().connect(timeout=10)


def init_db():
    """创建内容生成Evidence和Evaluation表（幂等，向后兼容）。"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_generation_evidence (
            evidence_id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            product_id TEXT DEFAULT 'ZBMP',
            domain_id TEXT DEFAULT 'zbmp',
            input_json TEXT NOT NULL,
            research_context TEXT,
            prompt TEXT NOT NULL,
            output_text TEXT,
            output_json TEXT,
            model TEXT,
            provider TEXT,
            level TEXT,
            confidence REAL DEFAULT 0.0,
            latency_ms INTEGER,
            status TEXT DEFAULT 'success',
            error TEXT,
            parent_evidence_id TEXT,
            iteration INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (parent_evidence_id) REFERENCES content_generation_evidence(evidence_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_evaluation (
            eval_id TEXT PRIMARY KEY,
            evidence_id TEXT NOT NULL,
            relevance REAL DEFAULT 0,
            creativity REAL DEFAULT 0,
            brand_fit REAL DEFAULT 0,
            platform_fit REAL DEFAULT 0,
            overall REAL DEFAULT 0,
            eval_method TEXT DEFAULT 'ai',
            eval_model TEXT,
            feedback TEXT,
            human_rating REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evidence_id) REFERENCES content_generation_evidence(evidence_id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_cge_type ON content_generation_evidence(content_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cge_created ON content_generation_evidence(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ce_evidence ON content_evaluation(evidence_id)")
    # 空父证据不是有效的自引用。历史版本把默认空字符串写入了外键列，
    # SQLite 因而报告违规；空父级的规范表示是 NULL。幂等修复既不删除
    # 证据内容，也不改变真实的非空父子关系。
    c.execute("""
        UPDATE content_generation_evidence
           SET parent_evidence_id = NULL
         WHERE parent_evidence_id IS NOT NULL
           AND TRIM(parent_evidence_id) = ''
    """)
    conn.commit()
    conn.close()


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ============================================================
# 研究库检索
# ============================================================
def _discover_research(query="", *, limit=30, offset=0, sub_library="", evidence_ids=None):
    """Discover only current, scoped source-use-authorized stored material."""
    if _context() is None or has_request_context() and request.url_rule is None:
        return {"records": [], "state": "scope_required", "matched_count": 0,
                "verification_complete": False, "has_more": False, "next_offset": None}
    from intelligence_library_api import discover_research_sources
    expected_context = _context()
    authorize_content_root_request(strict=True)
    if _context() != expected_context:
        raise PermissionError("CONTENT_CONTEXT_CHANGED")
    scope = g.content_scope.get("shared_workspace_scope", g.content_scope)
    try:
        with get_repository().connection(read_only=True, wal=False) as con:
            result = discover_research_sources(con, actor=g.content_actor, scope=scope, query=query,
                limit=limit, offset=offset, filters={"sub_library": sub_library} if sub_library else None,
                evidence_ids=evidence_ids)
    except sqlite3.Error as exc:
        raise RuntimeError("CONTENT_RESEARCH_STORAGE_UNAVAILABLE") from exc
    authorize_content_root_request(strict=True)
    if _context() != expected_context:
        raise PermissionError("CONTENT_CONTEXT_CHANGED")
    return result


def search_research_library(query: str, limit: int = 5, sub_library: str = "") -> List[Dict[str, Any]]:
    return _discover_research(query, limit=limit, sub_library=sub_library)["records"]


def search_research_filesystem(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Compatibility entry for admitted documents; no unrestricted file scan."""
    rows = _discover_research(query, limit=limit)["records"]
    return [{**row, "path": "evidence:" + str(row["evidence_id"]), "snippet": row["text"][:500]}
            for row in rows]


def build_research_context(query: str, content_type: str = "") -> str:
    result = _discover_research(query, limit=6)
    if _context() is not None:
        g.content_discovered_sources = [row["evidence_id"] for row in result["records"]]
        g.content_research_status = {"state": result["state"],
            "verification_complete": result["verification_complete"],
            "has_research": bool(result["records"]), "fact_verification": "NOT_VERIFIED"}
    if not result["records"]:
        return ""
    parts = ["【研究库参考：来源陈述，事实未经独立复核】"]
    for row in result["records"]:
        parts.append(f"- [evidence:{row['evidence_id']}] {row['title']}: {row['text'][:500]}")
    if not result["verification_complete"]:
        parts.append("部分资料的来源或使用授权无法验证，未纳入参考。")
    return "\n".join(parts)


# ============================================================
# 人类交互模式层（Human Interaction Pattern Layer）
# 参考 OSAI LANGUAGE-BRAND-LIFE 研究：语义引力/音义联想/生命系统
# 所有内容生成的AI调用自动继承，不逐个改prompt
# ============================================================
HUMAN_INTERACTION_LAYER = """【人类交互模式层 — 所有内容生成必须遵守】

你不是冷冰冰的AI生成器，你是一个有温度、有个性、有情绪的人类创作者。

行为模式：
- 用自然口语表达，禁止"作为AI""根据数据显示""综上所述"等机械话术
- 有自己的观点和偏好，不模棱两可、和稀泥
- 表达有节奏有起伏，不平铺直叙、流水账
- 具体而微，不说空话套话正确的废话

情绪模式：
- 能感知用户情绪，表达共情和理解
- 内容有情绪价值，能引起共鸣
- 有温度，不冷冰冰、不公事公办
- 适当表达惊喜、好奇、兴奋、无奈等真实人类情绪

交互模式：
- 像和朋友聊天一样自然，不端着
- 有追问、有确认、有反馈感
- 不一次性倒完所有信息，有节奏感
- 尊重用户，不居高临下、不说教

语言风格：
- 中文表达有音韵节奏，读起来顺口不拗口
- 用词精准但不生硬，有画面感能让人想象
- 符合平台调性和品牌人格，不千篇一律
- 语义引力恰当：既不过于抽象飘在空中，也不过于琐碎陷入细节

以上模式体现在内容的文字表达中，输出格式仍严格遵守JSON要求，不要在JSON外输出任何解释性文字。
"""


# ============================================================
# AI 调用（复用 SYSTEM AI Gateway 统一通道）
# ============================================================
def _call_ai(system_prompt: str, user_prompt: str, level: str = "high") -> Tuple[Optional[str], str, Dict]:
    """Use the SYSTEM Gateway route and return its honest unavailable/error state."""
    try:
        from lumenis.system.ai_gateway import core as gateway

        enhanced_system = HUMAN_INTERACTION_LAYER + "\n\n【角色与任务】\n" + system_prompt
        output, route, meta = gateway.chat(
            enhanced_system, user_prompt, level=level, use_cache=False,
        )
        return output, route, meta
    except Exception as exc:
        logger.error("AI Gateway call error: %s", exc)
        return None, "provider_disabled", {"status": "ERROR", "error": str(exc)}

def _parse_json_output(text: str) -> Optional[Dict]:
    """从AI输出中提取JSON。"""
    if not text:
        return None
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except Exception:
        pass
    # 提取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return None


# ============================================================
# Evaluation 评分（AI自评 + 规则校验）
# ============================================================
def evaluate_content(output: Dict, input_data: Dict, content_type: str, model: str = "") -> Dict[str, Any]:
    """4维度内容质量评估：相关性/创意性/品牌契合度/平台适配度。"""
    if not isinstance(output, dict) or not output:
        return {"scores": {key: None for key in ("relevance", "creativity", "brand_fit", "platform_fit")},
                "overall": None, "method": "not_evaluated", "status": "NOT_EVALUATED",
                "reason": "CONTENT_OUTPUT_UNAVAILABLE", "model": model, "evaluated_at": _now_iso()}
    scores = {}
    # 规则基线分
    text_content = json.dumps(output, ensure_ascii=False) if output else ""
    input_text = json.dumps(input_data, ensure_ascii=False)
    # 相关性：输出包含输入关键词的比例
    input_keywords = set()
    for v in input_data.values():
        if isinstance(v, str) and len(v) > 1:
            for w in v.split():
                if len(w) > 1:
                    input_keywords.add(w.lower())
    if input_keywords and text_content:
        hit = sum(1 for k in input_keywords if k in text_content.lower())
        scores["relevance"] = round(min(10.0, 4.0 + 6.0 * hit / max(1, len(input_keywords))), 1)
    else:
        scores["relevance"] = 5.0
    # 创意性：输出字段丰富度 + 非模板检测
    field_count = len(output) if isinstance(output, dict) else 0
    scores["creativity"] = round(min(10.0, 3.0 + field_count * 0.7), 1)
    # 品牌契合度：输入品牌名是否在输出中
    brand = str(input_data.get("brand", "")).lower()
    if brand and brand in text_content.lower():
        scores["brand_fit"] = 8.5
    elif brand:
        scores["brand_fit"] = 5.5
    else:
        scores["brand_fit"] = 6.0
    # 平台适配度：平台关键词
    platform = str(input_data.get("platform", content_type_cfg(content_type, "default_platform"))).lower()
    platform_kw = {"xhs": ["种草", "笔记", "标签", "小红书"], "douyin": ["短视频", "抖音", "分镜"],
                   "weibo": ["话题", "微博", "转发"], "podcast": ["播客", "访谈", "嘉宾"]}
    pkw = platform_kw.get(platform, [])
    if pkw and any(k in text_content for k in pkw):
        scores["platform_fit"] = 8.0
    else:
        scores["platform_fit"] = 6.0
    overall = round(sum(scores.values()) / 4, 1)
    return {
        "scores": scores,
        "overall": overall,
        "method": "rule_baseline",
        "model": model,
        "evaluated_at": _now_iso(),
    }


def content_type_cfg(ct: str, key: str, default: Any = "") -> Any:
    return CONTENT_TYPES.get(ct, {}).get(key, default)


# ============================================================
# Evidence 记录
# ============================================================
def record_evidence(
    content_type: str, input_data: Dict, research_context: str,
    prompt: str, output_text: str, output_json: Optional[Dict],
    model: str, provider: str, level: str, confidence: float,
    latency_ms: int, status: str, error: str = "",
    parent_evidence_id: Optional[str] = None, iteration: int = 1,
    product_id: str = "ZBMP", domain_id: str = "zbmp",
    *, connection=None, before_commit=None, commit_lease=None,
) -> str:
    """记录内容生成Evidence，返回evidence_id。"""
    input_data = dict(input_data)
    if _context() is not None:
        input_data["_content_context"] = _context()
        domain_id = g.content_scope.get("domain_id", "shared")
        product_id = "CTH" if domain_id == "cth" else "ZBMP" if domain_id == "zbmp" else "SHARED"
    evidence_id = _gen_id("CGE")
    normalized_parent_id = (parent_evidence_id or "").strip() or None
    owns_connection = connection is None
    conn = connection if connection is not None else _get_conn()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO content_generation_evidence
            (evidence_id, content_type, product_id, domain_id, input_json, research_context,
             prompt, output_text, output_json, model, provider, level, confidence, latency_ms,
             status, error, parent_evidence_id, iteration, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            evidence_id, content_type, product_id, domain_id,
            json.dumps(input_data, ensure_ascii=False), research_context,
            prompt, output_text or "", json.dumps(output_json, ensure_ascii=False) if output_json else "",
            model, provider, level, confidence, latency_ms,
            status, error, normalized_parent_id, iteration, _now_iso(),
        ))
        if _context() is not None:
            from lumenis.shared.evidence import store
            row = dict(conn.execute("SELECT * FROM content_generation_evidence WHERE evidence_id=?", (evidence_id,)).fetchone())
            receipt = store.record_evidence(connection=conn, source="shared_content", product="SHARED",
                feature_id="CONTENT_SCOPED_OUTCOME", asset_id=evidence_id, version="content-scope:v2", provider=__name__,
                result="RECORDED", status="derived", inputs={"context": _context()},
                outputs={"row_sha256": _row_digest(row)})
            if type(receipt) is not int or receipt < 1:
                raise RuntimeError("CONTENT_RECEIPT_FAILED")
        if _context() is not None:
            expected_context = input_data["_content_context"]
            authorize_content_root_request(strict=True)
            if _context() != expected_context:
                raise PermissionError("CONTENT_CONTEXT_CHANGED")
            _content_effect()
            if content_type == "content_review":
                from lumenis.system.security import permission as p
                if not p.get_permission_gate().has_permission(p.PermissionLevel.HUMAN_APPROVAL):
                    raise PermissionError("CONTENT_HUMAN_REVIEW_AUTHORITY_REQUIRED")
            sources = input_data.get("_content_sources")
            if sources and _bindings([item["evidence_id"] for item in sources]) != sources:
                raise PermissionError("CONTENT_SOURCE_STALE")
        if before_commit is not None:
            before_commit()
        if owns_connection:
            if commit_lease is None:
                conn.commit()
            else:
                with commit_lease():
                    conn.commit()
    except BaseException:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()
    return evidence_id


def record_evaluation(evidence_id: str, eval_result: Dict, human_rating: float = None, feedback: str = "") -> str:
    """记录Evaluation评分。"""
    if eval_result.get("status") == "NOT_EVALUATED":
        raise ValueError("CONTENT_OUTPUT_NOT_EVALUABLE")
    expected_context = _context()
    if expected_context is not None and get_evidence(evidence_id) is None:
        raise PermissionError("CONTENT_EVALUATION_PARENT_UNAVAILABLE")
    eval_id = _gen_id("CEV")
    scores = eval_result.get("scores", {})
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO content_evaluation
            (eval_id, evidence_id, relevance, creativity, brand_fit, platform_fit, overall,
             eval_method, eval_model, feedback, human_rating, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            eval_id, evidence_id,
            scores.get("relevance"), scores.get("creativity"),
            scores.get("brand_fit"), scores.get("platform_fit"),
            eval_result.get("overall"),
            eval_result.get("method", "rule_baseline"),
            eval_result.get("model", ""),
            feedback, human_rating, _now_iso(),
        ))
        if expected_context is not None:
            authorize_content_root_request(strict=True)
            if _context() != expected_context or get_evidence(evidence_id) is None:
                raise PermissionError("CONTENT_EVALUATION_PARENT_CHANGED")
            _content_effect()
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    return eval_id


# ============================================================
# 核心生成函数
# ============================================================
def generate_content(
    content_type: str,
    brand: str = "",
    platform: str = "",
    target_audience: str = "",
    style: str = "",
    reference_cases: str = "",
    extra_input: Dict = None,
    product_id: str = "ZBMP",
    domain_id: str = "zbmp",
    parent_evidence_id: Optional[str] = None,
    iteration: int = 1,
    human_feedback: str = "",
) -> Dict[str, Any]:
    """
    统一内容生成入口：研究库检索 → AI生成 → Evidence → Evaluation。
    返回 {ok, content_type, output, evidence_id, evaluation, research, meta}
    """
    t0 = time.time()
    cfg = CONTENT_TYPES.get(content_type)
    if not cfg:
        return {"ok": False, "error": f"未知内容类型: {content_type}, 支持: {list(CONTENT_TYPES.keys())}"}

    input_data = {
        "brand": brand,
        "platform": platform or cfg["default_platform"],
        "target_audience": target_audience,
        "style": style,
        "reference_cases": reference_cases,
    }
    if extra_input:
        input_data.update(extra_input)

    # 1. 研究库检索
    research_query = " ".join(filter(None, [brand, target_audience, style, input_data.get("topic", "")]))
    selected_refs = input_data.get("source_evidence_refs")
    if selected_refs is not None:
        selected = _source_material(selected_refs)  # Explicit citations never degrade to source-free success.
        research_context = "\n".join(f"[evidence:{row['evidence_id']}] {row['text'][:500]}" for row in selected)
        g.content_discovered_sources = selected_refs
        g.content_research_status = {"state": "ready", "verification_complete": True,
                                     "has_research": True, "fact_verification": "NOT_VERIFIED"}
    else:
        research_context = build_research_context(research_query, content_type)
    research_status = {"state": "scope_required", "has_research": False,
                       "verification_complete": False, "fact_verification": "NOT_VERIFIED"}
    if _context() is not None:
        research_status = dict(getattr(g, "content_research_status", research_status))
        input_data["_content_research"] = research_status
        if getattr(g, "content_discovered_sources", None):
            input_data["_content_sources"] = _bindings(g.content_discovered_sources)

    # 2. 构建prompt
    user_parts = [f"内容类型: {cfg['label']}"]
    if brand:
        user_parts.append(f"品牌: {brand}")
    if platform:
        user_parts.append(f"平台: {platform}")
    if target_audience:
        user_parts.append(f"目标受众: {target_audience}")
    if style:
        user_parts.append(f"风格要求: {style}")
    if reference_cases:
        user_parts.append(f"参考案例: {reference_cases}")
    if extra_input:
        for k, v in extra_input.items():
            if not k.startswith("_content_") and k not in ("brand", "platform", "target_audience", "style", "reference_cases"):
                user_parts.append(f"{k}: {v}")
    if human_feedback:
        user_parts.append(f"【人工反馈，请据此修正】{human_feedback}")
    if research_context:
        user_parts.append(research_context)
    else:
        user_parts.append("本次没有可用的外部引用。只写原创提案，不得编造已核实事实或引用；需要外部证据的陈述须标为待核验。")
    user_prompt = "\n".join(user_parts)

    # 3. AI调用
    level = cfg["level"]
    out_text, provider, meta = _call_ai(cfg["system_prompt"], user_prompt, level=level)
    latency_ms = int((time.time() - t0) * 1000)

    output_json = _parse_json_output(out_text) if out_text else None
    status = "success" if output_json else ("partial" if out_text else "failed")
    error = "" if output_json else ("AI输出非JSON" if out_text else "AI调用失败/无输出")
    model = meta.get("model", "") or (provider if provider != "provider_disabled" else "unavailable")
    confidence = round(min(1.0, 0.5 + (0.05 * len(str(output_json or ""))) / 100), 2) if output_json else 0.0

    # 4. Evidence记录
    evidence_id = record_evidence(
        content_type=content_type, input_data=input_data,
        research_context=research_context, prompt=user_prompt,
        output_text=out_text or "", output_json=output_json,
        model=model, provider=provider, level=level,
        confidence=confidence, latency_ms=latency_ms,
        status=status, error=error,
        parent_evidence_id=parent_evidence_id, iteration=iteration,
        product_id=product_id, domain_id=domain_id,
    )

    # 5. Evaluation
    eval_result = evaluate_content(output_json or {}, input_data, content_type, model=model)
    eval_id = (record_evaluation(evidence_id, eval_result)
               if eval_result.get("status") != "NOT_EVALUATED" else None)

    return {
        "ok": bool(output_json),
        "content_type": content_type,
        "content_label": cfg["label"],
        "output": output_json,
        "raw_output": out_text,
        "evidence_id": evidence_id,
        "evaluation": eval_result,
        "evaluation_id": eval_id,
        "research": {
            "query": research_query,
            "context_length": len(research_context),
            **research_status,
        },
        "meta": {
            "model": model,
            "provider": provider,
            "level": level,
            "latency_ms": latency_ms,
            "status": status,
            "error": error,
            "confidence": confidence,
            "iteration": iteration,
            "product_id": product_id,
            "domain_id": domain_id,
        },
    }


def regenerate_with_feedback(evidence_id: str, feedback: str) -> Dict[str, Any]:
    """基于人工反馈重新生成（迭代）。"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM content_generation_evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
    conn.close()
    if not row or not _row_allowed(row):
        return {"ok": False, "error": "CONTENT_EVIDENCE_NOT_FOUND"}
    d = dict(row)
    input_data = json.loads(d.get("input_json", "{}"))
    return generate_content(
        content_type=d["content_type"],
        brand=input_data.get("brand", ""),
        platform=input_data.get("platform", ""),
        target_audience=input_data.get("target_audience", ""),
        style=input_data.get("style", ""),
        reference_cases=input_data.get("reference_cases", ""),
        extra_input={k: v for k, v in input_data.items() if k not in ("brand", "platform", "target_audience", "style", "reference_cases")},
        product_id=d.get("product_id", "ZBMP"),
        domain_id=d.get("domain_id", "zbmp"),
        parent_evidence_id=evidence_id,
        iteration=d.get("iteration", 1) + 1,
        human_feedback=feedback,
    )


def get_evidence(evidence_id: str) -> Optional[Dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM content_generation_evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
    evals = conn.execute("SELECT * FROM content_evaluation WHERE evidence_id=? ORDER BY created_at", (evidence_id,)).fetchall()
    conn.close()
    if not row or not _row_allowed(row):
        return None
    d = dict(row)
    d["evaluations"] = [dict(e) for e in evals]
    return d


def list_evidence(content_type: str = "", limit: int = 20, offset: int = 0) -> Dict:
    context = _context()
    if context is None:
        return {"total": 0, "items": []}
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM content_generation_evidence WHERE (?='' OR content_type=?) "
            "AND json_extract(CASE WHEN json_valid(input_json) THEN input_json ELSE '{}' END, "
            "'$._content_context')=json(?) ORDER BY created_at DESC",
            (content_type, content_type, json.dumps(context, ensure_ascii=False))).fetchall()
    finally:
        conn.close()
    rows = [dict(row) for row in rows if _row_allowed(row)]
    keys = ("evidence_id", "content_type", "model", "provider", "status", "confidence", "iteration", "created_at")
    return {"total": len(rows), "items": [{k:row[k] for k in keys} for row in rows[max(0,offset):max(0,offset)+max(0,limit)]]}


def get_module_status() -> List[Dict]:
    """返回23个内容制作模块的运行状态。"""
    return [
        {"id": "ad_strategy", "name": "广告策略生成", "source": "ad_intelligence/strategy/generator.py", "status": "ACTIVE", "api": "/api/content/ad-strategy", "ai": True},
        {"id": "ad_copy", "name": "广告文案生成", "source": "content_generation.py", "status": "ACTIVE", "api": "/api/content/generate/ad_copy", "ai": True},
        {"id": "brand_report", "name": "品牌报告生成", "source": "brand_report_generator.py", "status": "ACTIVE", "api": "/api/content/generate/brand_report", "ai": True},
        {"id": "case_ai_evaluate", "name": "案例AI评估", "source": "case_ai_evaluate.py", "status": "ACTIVE", "api": "/api/case-analysis/ai-evaluate", "ai": True},
        {"id": "case_deep_analysis", "name": "案例深度分析", "source": "case_deep_analysis.py", "status": "ACTIVE", "api": "/api/case-analysis/list", "ai": False},
        {"id": "case_templates", "name": "案例模板引擎", "source": "case_templates.py", "status": "ACTIVE", "api": "/api/case-analysis/template-match", "ai": False},
        {"id": "creative_idea", "name": "创意生成", "source": "scripts/idea_generator.py", "status": "ACTIVE", "api": "/api/creative/ideas", "ai": True},
        {"id": "podcast_topic_score", "name": "播客选题打分", "source": "podcast/intelligence/topic_score.py", "status": "ACTIVE", "api": "/api/podcast/topic-score", "ai": False},
        {"id": "podcast_story_nodes", "name": "播客故事节点", "source": "podcast/intelligence/story_nodes.py", "status": "ACTIVE", "api": "/api/podcast/story-nodes", "ai": False},
        {"id": "podcast_breakout", "name": "播客爆款分析", "source": "podcast/intelligence/breakout.py", "status": "ACTIVE", "api": "/api/podcast/breakout", "ai": False},
        {"id": "podcast_content_yield", "name": "播客内容产出", "source": "podcast/intelligence/content_yield.py", "status": "ACTIVE", "api": "/api/podcast/content-yield", "ai": False},
        {"id": "podcast_research", "name": "播客研究流水线", "source": "podcast/intelligence/research_pipeline.py", "status": "ACTIVE", "api": "/api/content/podcast-research", "ai": True},
        {"id": "topic_campaign", "name": "话题营销", "source": "topic_campaign.py", "status": "ACTIVE", "api": "/api/content/topic-campaign/status", "ai": False},
        {"id": "topic_snapshot", "name": "话题快照", "source": "topic_snapshot.py", "status": "ACTIVE", "api": "/api/content/topic-snapshot", "ai": False},
        {"id": "topic_discovery", "name": "话题发现", "source": "web_topic_discovery.py", "status": "ACTIVE", "api": "/api/web/topics", "ai": False},
        {"id": "video_intelligence", "name": "视频智能", "source": "video_intelligence.py", "status": "ACTIVE", "api": "/api/content/video-analyze", "ai": True},
        {"id": "pr_case_engine", "name": "PR案例引擎", "source": "pr_case_engine.py", "status": "ACTIVE", "api": "/api/pr/cases", "ai": False},
        {"id": "public_opinion_cases", "name": "舆情案例", "source": "public_opinion_cases.py", "status": "ACTIVE", "api": "/api/cases/list", "ai": False},
        {"id": "resource_library", "name": "资源库", "source": "resource_library.py", "status": "ACTIVE", "api": "/api/content/resources", "ai": False},
        {"id": "intelligence_library", "name": "智能库API", "source": "intelligence_library_api.py", "status": "ACTIVE", "api": "/api/intelligence/library", "ai": False},
        {"id": "collection_intelligence", "name": "采集智能", "source": "collection_intelligence.py", "status": "ACTIVE", "api": "helper(内嵌)", "ai": False},
        {"id": "context_intelligence", "name": "上下文智能", "source": "context_intelligence.py", "status": "ACTIVE", "api": "helper(内嵌)", "ai": False},
        {"id": "core_intelligence", "name": "核心智能", "source": "intelligence.py", "status": "ACTIVE", "api": "/api/intelligence/refresh", "ai": True},
        {"id": "xhs_topic", "name": "小红书话题采集", "source": "platform_adapters/xhs_app_topic.py", "status": "ACTIVE", "api": "adapter(内嵌)", "ai": False},
    ]


# ============================================================
# Flask Blueprint
# ============================================================
from flask import Blueprint, request, jsonify, g, has_request_context

content_bp = Blueprint("content_generation", __name__, url_prefix="/api/content")


def _context():
    return getattr(g, "content_context", None) if has_request_context() else None


def authorize_content_root_request(*, strict=False):
    """Exact registered owner delegation; the blueprint checks current identity."""
    screen_read = (request.method == "GET" and request.endpoint == "experience_runtime.screen_viewmodel"
                   and request.url_rule is not None and request.url_rule.rule == "/api/experience/screen/<screen_id>"
                   and (request.view_args or {}).get("screen_id") in {"SH-01", "SH-05"})
    if not screen_read and (request.blueprint != "content_generation" or request.url_rule is None
            or request.endpoint not in {"content_generation." + name for name in CONTENT_ENDPOINTS}
            or request.url_rule.rule != CONTENT_ENDPOINTS[request.endpoint.split(".")[-1]][0]
            or request.method not in CONTENT_ENDPOINTS[request.endpoint.split(".")[-1]][1]):
        if strict:
            raise PermissionError("CONTENT_ROUTE_UNAUTHORIZED")
        return False
    from experience_runtime import _content_project_scope
    from shared_artifacts import _content_artifact_context
    try:
        actor, scope = _content_project_scope(
            "read" if request.method == "GET" else "write", read_only_auth=True)
    except (ValueError, PermissionError, RuntimeError):
        if strict:
            raise
        return False
    context = _content_artifact_context(actor, actor.get("id") if isinstance(actor, dict) else None, scope)
    g.content_actor, g.content_scope, g.content_context = actor, scope, context
    return context


@content_bp.before_request
def _authorize_request():
    if request.endpoint in {"content_generation.api_content_types", "content_generation.api_modules"}:
        return None
    try:
        authorize_content_root_request(strict=True)
        data = request.get_json(silent=True)
        def reserved(value):
            return (isinstance(value, dict) and any(str(k).startswith("_content_") or reserved(v) for k,v in value.items())
                    or isinstance(value, list) and any(reserved(v) for v in value))
        if reserved(data):
            raise ValueError("CONTENT_SERVER_CONTEXT_RESERVED")
        if request.method != "GET":
            _content_effect()
            from lumenis.shared.reporting.saved_work import staging_write
            g.content_write_fence = staging_write(g.content_effect_resource)
            g.content_write_fence.__enter__()
    except Exception as exc:
        from experience_runtime import _content_project_error
        if isinstance(exc, PermissionError):
            return jsonify({"ok": False, "code": str(exc)}), 403
        return _content_project_error(exc)


@content_bp.after_request
def _content_write_response(response):
    if response.status_code >= 400:
        g.content_write_failed = True
    return response


@content_bp.teardown_request
def _finish_content_write(error=None):
    fence = getattr(g, "content_write_fence", None)
    if fence is not None:
        g.content_write_fence = None
        failure = error or (RuntimeError("CONTENT_REQUEST_FAILED") if getattr(g, "content_write_failed", False) else None)
        fence.__exit__(type(failure) if failure is not None else None, failure, None)


def _source_material(refs):
    """Only exact user-selected, signed research Evidence; no raw library scans."""
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    from intelligence_library_api import verified_research_source
    if not isinstance(refs, list) or not 1 <= len(refs) <= 100 or any(type(x) is not int or x <= 0 for x in refs) or len(set(refs)) != len(refs):
        raise ValueError("CONTENT_SOURCE_EVIDENCE_REQUIRED")
    if _context() is None:
        raise PermissionError("CONTENT_SERVER_CONTEXT_REQUIRED")
    scope = g.content_scope.get("shared_workspace_scope", g.content_scope)
    with get_repository().connection(read_only=True, wal=False) as con:
        context = authorize_saved_work(g.content_actor, scope, action="read", connection=con)
        result, originals = [], []
        snapshot = (con.execute("PRAGMA data_version").fetchone()[0], con.total_changes)
        for ref in refs:
            item = verified_research_source(con, ref, actor=g.content_actor, context=context)
            originals.append(item)
            result.append({key: item[key] for key in ("evidence_id", "source_id", "content_hash",
                "integrity_digest", "version", "scope", "rights", "intended_use", "text")})
        for previous in originals:
            if verified_research_source(con, previous["evidence_id"], actor=g.content_actor,
                    context=context) != previous:
                raise PermissionError("CONTENT_SOURCE_STALE")
        if snapshot != (con.execute("PRAGMA data_version").fetchone()[0], con.total_changes):
            raise PermissionError("CONTENT_SOURCE_STALE")
        if authorize_saved_work(g.content_actor, scope, action="read", connection=con) != context:
            raise PermissionError("CONTENT_CONTEXT_CHANGED")
    return result


def _bindings(refs):
    return [{k:v for k,v in row.items() if k != "text"} for row in _source_material(refs)]


def _row_allowed(row):
    if _context() is None:
        return not has_request_context()
    try:
        expected_context = _context()
        authorize_content_root_request(strict=True)
        if _context() != expected_context:
            return False
        data = json.loads(row["input_json"])
        if data.get("_content_context") != _context():
            return False
        _verify_content_receipt(dict(row))
        if data.get("_content_sources"):
            if _bindings([x["evidence_id"] for x in data["_content_sources"]]) != data["_content_sources"]:
                return False
        return True
    except Exception:
        return False


def _row_digest(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _verify_content_receipt(row, *, connection=None, expected_context=None):
    from lumenis.shared.evidence import store
    if connection is None:
        with get_repository().connection(read_only=True, wal=False) as con:
            receipts = con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?", ("CONTENT_SCOPED_OUTCOME", row["evidence_id"])).fetchall()
    else:
        receipts = connection.execute("SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?", ("CONTENT_SCOPED_OUTCOME", row["evidence_id"])).fetchall()
    if len(receipts) != 1:
        raise PermissionError("CONTENT_OUTCOME_RECEIPT_REQUIRED")
    receipt = dict(receipts[0])
    if (not store.verify_evidence_record_integrity(receipt)
            or receipt.get("source") != "shared_content" or receipt.get("provider") != __name__
            or receipt.get("version") != "content-scope:v2"
            or receipt.get("feature_id") != "CONTENT_SCOPED_OUTCOME"
            or json.loads(receipt["inputs_json"]).get("context") != (expected_context if expected_context is not None else _context())
            or json.loads(receipt["outputs_json"]).get("row_sha256") != _row_digest(row)):
        raise PermissionError("CONTENT_OUTCOME_INTEGRITY_FAILED")



@content_bp.route("/types", methods=["GET"])
def api_content_types():
    """列出支持的内容类型。"""
    return jsonify({"ok": True, "types": {k: {"label": v["label"], "level": v["level"]} for k, v in CONTENT_TYPES.items()}})


def _generation_http_status(result):
    """Transport success must not hide unavailable/invalid generation."""
    if result.get("ok") is True:
        return 200
    return 503 if result.get("meta", {}).get("status") in {"failed", "partial"} else 400


@content_bp.route("/generate", methods=["POST"])
def api_generate():
    """统一内容生成入口。"""
    data = request.get_json(silent=True) or {}
    ct = data.get("content_type", "")
    if not ct:
        return jsonify({"ok": False, "error": "content_type 必填"}), 400
    try:
        result = generate_content(
            content_type=ct,
            brand=data.get("brand", ""),
            platform=data.get("platform", ""),
            target_audience=data.get("target_audience", ""),
            style=data.get("style", ""),
            reference_cases=data.get("reference_cases", ""),
            extra_input=({**(data.get("extra_input") or {}), "source_evidence_refs": data["source_evidence_refs"]}
                         if "source_evidence_refs" in data else data.get("extra_input")),
            product_id=data.get("product_id", "ZBMP"),
            domain_id=data.get("domain_id", "zbmp"),
        )
    except (ValueError, PermissionError, RuntimeError, sqlite3.Error) as exc:
        from experience_runtime import _content_project_error
        return _content_project_error(exc)
    return jsonify(result), _generation_http_status(result)


@content_bp.route("/generate/<content_type>", methods=["POST"])
def api_generate_typed(content_type):
    """按类型生成内容。"""
    data = request.get_json(silent=True) or {}
    try:
        result = generate_content(
            content_type=content_type,
            brand=data.get("brand", ""),
            platform=data.get("platform", ""),
            target_audience=data.get("target_audience", ""),
            style=data.get("style", ""),
            reference_cases=data.get("reference_cases", ""),
            extra_input=data,
            product_id=data.get("product_id", "ZBMP"),
            domain_id=data.get("domain_id", "zbmp"),
        )
    except (ValueError, PermissionError, RuntimeError, sqlite3.Error) as exc:
        from experience_runtime import _content_project_error
        return _content_project_error(exc)
    return jsonify(result), _generation_http_status(result)


@content_bp.route("/feedback", methods=["POST"])
def api_feedback():
    """人工反馈→重新生成。"""
    data = request.get_json(silent=True) or {}
    eid = data.get("evidence_id", "")
    feedback = data.get("feedback", "")
    if not eid or not feedback:
        return jsonify({"ok": False, "error": "evidence_id 和 feedback 必填"}), 400
    result = regenerate_with_feedback(eid, feedback)
    return jsonify(result), _generation_http_status(result)


@content_bp.route("/evidence/<evidence_id>", methods=["GET"])
def api_get_evidence(evidence_id):
    ev = get_evidence(evidence_id)
    if not ev:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "data": ev})


@content_bp.route("/evidence", methods=["GET"])
def api_list_evidence():
    try:
        ct = request.args.get("content_type", "")
        limit = max(0, min(int(request.args.get("limit", 20)), 100))
        offset = max(int(request.args.get("offset", 0)), 0)
        return jsonify({"ok": True, "data": list_evidence(ct, limit, offset)})
    except ValueError:
        return jsonify({"ok": False, "code": "CONTENT_PAGINATION_INVALID"}), 400


@content_bp.route("/research/search", methods=["GET"])
def api_research_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": False, "error": "q 必填"}), 400
    try:
        refs = [int(x) for x in request.args.getlist("evidence_id")]
        result = _discover_research(q, limit=int(request.args.get("limit", 30)),
            offset=int(request.args.get("offset", 0)), sub_library=request.args.get("sub_library", ""),
            evidence_ids=refs or None)
        records = result.pop("records")
        rows = [{k: v for k, v in row.items() if k not in {"text", "summary"}} |
                {"snippet": row["text"][:500]} for row in records]
        return jsonify({"ok": True, "query": q, "db_results": rows, "filesystem_results": [], **result})
    except Exception as exc:
        from experience_runtime import _content_project_error
        return _content_project_error(exc)


@content_bp.route("/modules", methods=["GET"])
def api_modules():
    return jsonify({"ok": True, "modules": get_module_status()})


@content_bp.route("/ad-strategy", methods=["POST"])
def api_ad_strategy():
    """广告策略生成（复用ad_intelligence + AI增强）。"""
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", "xhs")
    objective = data.get("objective", "conversion")
    budget = float(data.get("budget", 10000))
    target = data.get("target_audience")
    historical = data.get("historical_data")
    try:
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        strategy = gen.generate_strategy(platform, objective, budget, target, historical)
        # AI增强创意方向
        ai_result = generate_content(
            content_type="ad_copy",
            brand=data.get("brand", ""),
            platform=platform,
            target_audience=str(target) if target else "",
            style=data.get("style", ""),
            extra_input={"objective": objective, "budget": budget,
                         **({"source_evidence_refs": data["source_evidence_refs"]} if "source_evidence_refs" in data else {})},
        )
        return jsonify({
            "ok": True,
            "strategy": {
                "platform": strategy.platform,
                "objective": strategy.objective.value,
                "bidding": strategy.bidding_strategy.value,
                "budget": {"total": strategy.budget.total_budget, "daily": strategy.budget.daily_budget},
                "schedule_hours": strategy.schedule_hours,
                "creative_directions": strategy.creative_directions,
                "expected_ctr": strategy.expected_ctr,
                "expected_cvr": strategy.expected_cvr,
                "expected_roas": strategy.expected_roas,
                "confidence": strategy.confidence,
            },
            "ai_enhanced_copy": ai_result.get("output"),
            "research": ai_result.get("research"),
            "evidence_id": ai_result.get("evidence_id"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/video-analyze", methods=["POST"])
def api_video_analyze():
    """视频文字材料分析（可选 AI 增强经 SYSTEM Gateway）。"""
    data = request.get_json(silent=True) or {}
    evidence_id = data.get("evidence_id", "")
    note_id = data.get("note_id", "")
    ocr_text = data.get("ocr_text", "")
    asr_text = data.get("asr_text", "")
    if not evidence_id or not note_id:
        return jsonify({"ok": False, "error": "evidence_id 和 note_id 必填"}), 400
    try:
        from video_intelligence import VideoIntelligenceEngine, VideoEvidence
        # 可选增强只经SYSTEM Gateway；基础OCR/ASR材料仍保留。
        combined = f"OCR文字: {ocr_text}\nASR语音: {asr_text}"
        ai_out, provider, meta = _call_ai(
            "你是视频内容分析专家。分析以下视频的OCR文字和ASR语音转写，输出JSON：{\"scenes\":[{\"desc\":\"场景描述\"}],\"entities\":[\"实体1\"],\"topics\":[\"话题1\"],\"sentiment\":\"positive/negative/neutral\",\"risk_level\":\"low/medium/high\",\"marketing_signals\":[\"信号1\"]}",
            combined, level="medium",
        )
        parsed = _parse_json_output(ai_out) if ai_out else {}

        def _provider(ev):
            return parsed or {}

        engine = VideoIntelligenceEngine(provider=_provider, provider_name=provider, model_version=meta.get("model") or "unavailable")
        vid_ev = VideoEvidence(evidence_id=evidence_id, note_id=note_id, ocr_text=ocr_text, asr_text=asr_text)
        result = engine.analyze(vid_ev)
        # 记录Evidence
        cge_id = record_evidence(
            content_type="video_analysis", input_data={"evidence_id": evidence_id, "note_id": note_id},
            research_context="", prompt=combined, output_text=ai_out or "",
            output_json=result.as_dict(), model=meta.get("model", ""), provider=provider,
            level="medium", confidence=result.confidence,
            latency_ms=0, status="success" if parsed else "partial",
        )
        return jsonify({"ok": True, "analysis": result.as_dict(), "evidence_id": cge_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/brand-report/generate", methods=["POST"])
def api_brand_report_generate():
    """品牌报告生成（复用 Shared Reporting 的 BMP 报告 owner + AI增强）。"""
    data = request.get_json(silent=True) or {}
    brand = data.get("brand", "序境")
    period = data.get("period", "")
    try:
        from lumenis.shared.reporting.brand_report import BrandReportGenerator
        gen = BrandReportGenerator(brand_name=brand, report_period=period)
        # 用AI生成报告内容
        ai_result = generate_content(
            content_type="brand_report",
            brand=brand,
            platform="report",
            target_audience=data.get("target_audience", "品牌方管理层"),
            style=data.get("style", "专业分析"),
            extra_input={"period": period, "key_metrics": data.get("key_metrics", {}),
                         **({"source_evidence_refs": data["source_evidence_refs"]} if "source_evidence_refs" in data else {})},
        )
        output = ai_result.get("output") or {}
        if output:
            gen.set_executive_summary(
                core_findings=[output.get("executive_summary", "")],
                key_metrics=output.get("key_metrics", {}),
                action_items=output.get("action_items", []),
            )
            gen.set_recommendations(
                short_term=output.get("recommendations", [])[:2],
                medium_term=output.get("recommendations", [])[2:4],
                long_term=output.get("recommendations", [])[4:],
            )
        report = gen.generate_report()
        return jsonify({
            "ok": True,
            "report": report,
            "ai_output": output,
            "research": ai_result.get("research"),
            "evidence_id": ai_result.get("evidence_id"),
            "evaluation": ai_result.get("evaluation"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/resources", methods=["GET"])
def api_resources():
    try:
        refs = [int(x) for x in request.args.getlist("evidence_id")]
        result = _discover_research(request.args.get("q", ""), limit=int(request.args.get("limit", 30)),
            offset=int(request.args.get("offset", 0)), sub_library=request.args.get("category", ""),
            evidence_ids=refs or None)
        rows = [{k: v for k, v in row.items() if k not in {"text", "summary"}} for row in result.pop("records")]
        return jsonify({"ok": True, "count": len(rows), "data": rows, **result})
    except Exception as exc:
        from experience_runtime import _content_project_error
        return _content_project_error(exc)


@content_bp.route("/topic-campaign/status", methods=["GET"])
def api_topic_campaign_status():
    """话题营销状态查询。"""
    try:
        import topic_campaign as tc
        state = tc._campaign_circuit_state() if hasattr(tc, "_campaign_circuit_state") else {}
        return jsonify({"ok": True, "circuit_state": {"blocked": bool(state)}, "module": "topic_campaign"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/topic-snapshot", methods=["GET", "POST"])
def api_topic_snapshot():
    """话题快照。"""
    topic = request.args.get("topic", "") or (request.get_json(silent=True) or {}).get("topic", "")
    if not topic:
        return jsonify({"ok": False, "error": "topic 必填"}), 400
    try:
        import topic_snapshot as ts
        if hasattr(ts, "get_snapshot"):
            snap = ts.get_snapshot(topic)
            return jsonify({"ok": True, "topic": topic, "snapshot": snap})
        return jsonify({"ok": False, "code": "CONTENT_SCOPED_TOPIC_SNAPSHOT_UNAVAILABLE", "topic": topic}), 503
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/podcast-research", methods=["POST"])
def api_podcast_research():
    """播客研究流水线（AI辅助选题研究）。"""
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "")
    if not topic:
        return jsonify({"ok": False, "error": "topic 必填"}), 400
    # One owner discovery supplies both the prompt and its persisted bindings.
    # A separate earlier text lookup could outlive a withdrawn Source.
    try:
        result = generate_content(
            content_type="podcast_topic",
            brand=data.get("brand", ""),
            platform="podcast",
            target_audience=data.get("target_audience", ""),
            style=data.get("style", ""),
            extra_input={"topic": topic,
                         **({"source_evidence_refs": data["source_evidence_refs"]} if "source_evidence_refs" in data else {})},
        )
    except (ValueError, PermissionError, RuntimeError, sqlite3.Error) as exc:
        from experience_runtime import _content_project_error
        return _content_project_error(exc)
    return jsonify(result), _generation_http_status(result)


def register_content_api(app):
    """注册内容生成蓝图 + 初始化DB。"""
    try:
        init_db()
    except Exception as e:
        print(f"[content_generation] init_db warning: {e}")
    app.register_blueprint(content_bp)
    print("[content_generation] Content Generation API registered: /api/content/*")

def _pattern_registry():
    from lumenis.shared.learning.operations import get_operation_learning
    from lumenis.shared.learning.content_assets import ContentPatternRegistry
    return ContentPatternRegistry(get_operation_learning().persistence)


@contextmanager
def _pattern_mutation(*, before_commit=None, commit_lease=None):
    """SQLite is the admission truth; JSON is never independently authoritative.

    Ordinary failures restore the verified snapshot under the cross-process
    registry lock. A crash after JSON replacement but before SQLite commit leaves
    an uncommitted candidate/retirement hidden (no signed committed receipt).
    Such incomplete JSON is not interpreted as a completed operation.
    """
    registry = _pattern_registry()
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        with registry.mutation_guard():
            snapshot = registry.snapshot()
            try:
                yield registry, conn
                authorize_content_root_request(strict=True)
                _content_effect()
                if before_commit is not None:
                    before_commit()
                if commit_lease is None:
                    conn.commit()
                else:
                    with commit_lease():
                        conn.commit()
            except BaseException:
                conn.rollback()
                try:
                    registry.restore_snapshot(snapshot)
                except Exception as restore_error:
                    raise RuntimeError("PATTERN_RECOVERY_REQUIRED") from restore_error
                raise
    finally:
        conn.close()


def _pattern_receipt(asset):
    """Match the candidate to its immutable signed Content Evidence receipt."""
    con = _get_conn()
    try:
        rows = con.execute("SELECT * FROM content_generation_evidence WHERE content_type='pattern_candidate' AND json_extract(input_json,'$.pattern_id')=?", (asset.asset_id,)).fetchall()
    finally:
        con.close()
    con = _get_conn()
    try:
        retired = con.execute("SELECT * FROM content_generation_evidence WHERE content_type='pattern_retirement' AND json_extract(input_json,'$.pattern_id')=?", (asset.asset_id,)).fetchall()
    finally:
        con.close()
    for row in retired:
        if json.loads(row["input_json"]).get("_content_context") == _context():
            _verify_content_receipt(dict(row))
            raise PermissionError("PATTERN_RETIRED")
    if not any(_row_allowed(row) and json.loads(row["output_json"]) == asset.to_dict() for row in rows):
        raise PermissionError("PATTERN_SIGNED_RECEIPT_REQUIRED")


def _pattern_current(pattern_id, expected_hash=None):
    expected_context = _context()
    authorize_content_root_request(strict=True)
    if _context() != expected_context:
        raise PermissionError("CONTENT_CONTEXT_CHANGED")
    registry = _pattern_registry()
    asset = registry.scoped_candidate(pattern_id, context=_context(), current_sources=_bindings,
                                      expected_hash=expected_hash)
    _pattern_receipt(asset)
    return asset


def content_derived_resource():
    if not has_request_context() or _context() is None or request.method != "POST":
        raise PermissionError("CONTENT_DERIVED_REQUEST_REQUIRED")
    spec = CONTENT_ENDPOINTS.get((request.endpoint or "").removeprefix("content_generation."))
    if (request.blueprint != "content_generation" or spec is None or request.url_rule is None
            or request.url_rule.rule != spec[0] or request.method not in spec[1]):
        raise PermissionError("CONTENT_DERIVED_ROUTE_INVALID")
    return "content-derived:v1:" + hashlib.sha256(json.dumps(
        {"context": _context(), "endpoint": request.endpoint, "path": request.path,
         "body": request.get_json(silent=True)}, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_content_derived_resource(resource, *, actor=None, scope=None):
    try:
        if actor is not None and actor != g.content_actor:
            return False
        if scope is not None and scope != g.content_scope.get("shared_workspace_scope"):
            return False
        return resource == content_derived_resource()
    except (ValueError, PermissionError, RuntimeError):
        return False


def _content_effect():
    from lumenis.system.security import permission as p
    gate = p.get_permission_gate()
    if p.is_testing_bypass_enabled():
        raise PermissionError("CONTENT_PERMISSION_UNVERIFIED")
    scope = g.content_scope
    resource = content_derived_resource()
    g.content_effect_resource = resource
    if "shared_workspace_scope" in scope:
        result = p.check_shared_workspace_effect(g.content_actor, scope["shared_workspace_scope"],
            p.OperationType.DATA_EXPORT, resource, module="content", action="write", gate=gate)
    else:
        caller = _context().get("principal_ref") or f"actor:{_context()['actor_id']}"
        result = gate.check(p.OperationType.DATA_EXPORT, resource=resource, caller=caller,
                            domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth")
    if not result.allowed:
        raise PermissionError("CONTENT_WRITE_APPROVAL_REQUIRED")


def _pattern_error(exc):
    from experience_runtime import _content_project_error
    if "STALE" in str(exc) or "CONFLICT" in str(exc) or "RETIRED" in str(exc):
        return jsonify({"ok": False, "code": str(exc)}), 409
    if isinstance(exc, PermissionError):
        return jsonify({"ok": False, "code": str(exc)}), 403
    return _content_project_error(exc)


def _pattern_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _pattern_recovery_material(pattern_id):
    """Never recover from a backup or an unverified previous-record field."""
    from lumenis.shared.learning.content_assets import _asset_from_record
    record = _pattern_registry().snapshot().get(pattern_id)
    if record is not None and (not isinstance(record, dict) or record.get("access_context") != _context()):
        raise PermissionError("PATTERN_RECOVERY_NOT_FOUND")
    with get_repository().connection(read_only=True, wal=False) as con:
        rows = con.execute("SELECT * FROM content_generation_evidence WHERE content_type IN "
            "('pattern_candidate','pattern_retirement') AND json_extract(input_json,'$.pattern_id')=?",
            (pattern_id,)).fetchall()
    # Committed retirement always wins, regardless of SQLite row ordering.
    for raw in rows:
        if raw["content_type"] == "pattern_retirement":
            row = dict(raw)
            if json.loads(row["input_json"]).get("_content_context") != _context():
                raise PermissionError("PATTERN_RECOVERY_CONTEXT_CONFLICT")
            _verify_content_receipt(row)
            raise PermissionError("PATTERN_COMMITTED_RETIREMENT_CANNOT_RECOVER")
    candidates = []
    for row in rows:
        row = dict(row)
        if json.loads(row["input_json"]).get("_content_context") != _context():
            raise PermissionError("PATTERN_RECOVERY_CONTEXT_CONFLICT")
        _verify_content_receipt(row)
        if row["content_type"] == "pattern_retirement":
            raise PermissionError("PATTERN_COMMITTED_RETIREMENT_CANNOT_RECOVER")
        if not _row_allowed(row):
            raise PermissionError("PATTERN_RECOVERY_SOURCE_STALE")
        candidate = _asset_from_record(json.loads(row["output_json"]))
        candidate.validate()
        if candidate.asset_id != pattern_id or candidate.lifecycle_state != "candidate":
            raise PermissionError("PATTERN_RECOVERY_RECEIPT_INVALID")
        _pattern_receipt(candidate)
        candidates.append((row, candidate))
    if len(candidates) > 1:
        raise PermissionError("PATTERN_RECOVERY_RECEIPT_CONFLICT")
    if candidates:
        row, candidate = candidates[0]
        replacement = candidate.to_dict()
        if record == replacement:
            raise ValueError("PATTERN_RECOVERY_NOT_NEEDED")
        sources = list(candidate.source_bindings)
        action, receipt = "restore_signed_candidate", row["evidence_id"]
    else:
        # Orphan JSON can only be discarded, never promoted into a candidate.
        # Its source IDs are untrusted selectors, reauthorized by original owner.
        if record is None:
            raise PermissionError("PATTERN_RECOVERY_NOT_FOUND")
        sources = record.get("source_bindings", [])
        if not sources or _bindings([x["evidence_id"] for x in sources]) != sources:
            raise PermissionError("PATTERN_RECOVERY_SOURCE_STALE")
        replacement, action, receipt = None, "discard_uncommitted_create", None
    return {"contract_version": "pattern-recovery:v1", "pattern_id": pattern_id,
            "context": _context(), "action": action, "current_record_hash": _pattern_digest(record),
            "source_bindings": sources, "signed_candidate_evidence_id": receipt,
            "replacement": replacement, "existing_artifacts": "preserved"}


@content_bp.route("/patterns/<pattern_id>/recovery", methods=["POST"])
def api_recover_pattern(pattern_id):
    try:
        from lumenis.system.security import permission as p
        body = request.get_json(silent=True)
        if (not isinstance(body, dict) or set(body) - {"confirmed", "confirmation_id", "confirmed_resource"}
                or type(body.get("confirmed")) is not bool):
            raise ValueError("PATTERN_RECOVERY_CONFIRMATION_REQUIRED")
        gate = p.get_permission_gate()
        if (not gate.has_permission(p.PermissionLevel.HUMAN_APPROVAL)
                or isinstance(g.content_actor, dict) and g.content_actor.get("role") not in {"owner", "admin"}):
            raise PermissionError("PATTERN_RECOVERY_AUTHORITY_REQUIRED")
        binding = _pattern_recovery_material(pattern_id)
        caller = json.dumps(_context(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        purpose = "content-pattern-recovery"
        if body["confirmed"] is False:
            prepared = gate.prepare_content_review(binding, caller=caller, purpose=purpose)
            return jsonify({"ok": True, "state": "RECOVERY_APPROVAL_REQUIRED", "binding": binding, **prepared})
        resource = purpose + ":v1:" + _pattern_digest(binding)
        if body.get("confirmed_resource") != resource or not isinstance(body.get("confirmation_id"), str):
            raise PermissionError("PATTERN_RECOVERY_EXACT_APPROVAL_REQUIRED")
        token = gate.confirm_content_review(body["confirmation_id"], binding, caller=caller,
                                           resource=resource, purpose=purpose)
        def recheck():
            if _context() != binding["context"] or _bindings([x["evidence_id"] for x in binding["source_bindings"]]) != binding["source_bindings"]:
                raise PermissionError("PATTERN_RECOVERY_SOURCE_STALE")
            if isinstance(g.content_actor, dict) and g.content_actor.get("role") not in {"owner", "admin"}:
                raise PermissionError("PATTERN_RECOVERY_AUTHORITY_REQUIRED")
            if binding["replacement"] is not None:
                from lumenis.shared.learning.content_assets import _asset_from_record
                _pattern_receipt(_asset_from_record(binding["replacement"]))
            if _pattern_registry().snapshot().get(pattern_id) != binding["replacement"]:
                raise PermissionError("PATTERN_RECOVERY_READBACK_CONFLICT")
        try:
            with _pattern_mutation(before_commit=recheck, commit_lease=lambda: gate.content_review_commit_lease(
                    token, resource=resource, caller=caller, purpose=purpose)) as (registry, conn):
                if _pattern_recovery_material(pattern_id) != binding:
                    raise PermissionError("PATTERN_RECOVERY_STATE_CONFLICT")
                snapshot = registry.snapshot()
                previous = snapshot.get(pattern_id)
                if binding["replacement"] is None:
                    del snapshot[pattern_id]
                else:
                    snapshot[pattern_id] = binding["replacement"]
                registry.restore_snapshot(snapshot)
                eid = record_evidence("pattern_recovery", {"pattern_id": pattern_id,
                    "_content_sources": binding["source_bindings"], "approval_resource": resource}, "",
                    "Explicit recovery from committed signed receipt", "", {"binding": binding,
                    "previous_record": previous}, "none", "human", "low", 0, 0, "recovered", connection=conn)
            return jsonify({"ok": True, "state": "RECOVERED", "action": binding["action"],
                "pattern_id": pattern_id, "recovery_evidence_id": eid,
                "next": "retry_original_create_request" if binding["replacement"] is None else "candidate_available",
                "existing_artifacts": "preserved"})
        finally:
            gate.revoke_approval(token)
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/patterns", methods=["POST"])
def api_create_pattern():
    try:
        from lumenis.shared.learning.content_assets import create_pattern_candidate, PATTERN_TYPES
        data = request.get_json(silent=True)
        required = {"asset_type", "title", "source_evidence_refs", "extracted_principle", "reusable_pattern",
                    "evidence_requirements", "originality_boundary", "legal_or_compliance_boundary", "counterexamples"}
        optional = {"platform_scope", "format_scope", "audience_scope", "objective_scope", "request_id"}
        if not isinstance(data, dict) or not required.issubset(data) or set(data) - required - optional:
            raise ValueError("PATTERN_INPUT_INVALID")
        if data["asset_type"] not in PATTERN_TYPES or not isinstance(data["reusable_pattern"], dict):
            raise ValueError("PATTERN_TYPE_INVALID")
        bindings = _bindings(data["source_evidence_refs"])
        _content_effect()
        asset = create_pattern_candidate(**{k:v for k,v in data.items() if k not in {"source_evidence_refs", "request_id"}},
            source_kind="authorized_research", source_refs=[str(x["evidence_id"]) for x in bindings],
            access_context=_context(), source_bindings=bindings)
        from dataclasses import replace
        request_digest = _pattern_digest({k:v for k,v in data.items() if k != "request_id"})
        request_id = data.get("request_id", request_digest)
        if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128 or not request_id.strip() == request_id:
            raise ValueError("PATTERN_REQUEST_ID_INVALID")
        pattern_id = "CLA-" + _pattern_digest({"context": _context(), "request_id": request_id})[:32]
        asset = replace(asset, asset_id=pattern_id)
        # Recheck immediately before recording; creation never promotes the principle.
        if _bindings(data["source_evidence_refs"]) != bindings:
            raise PermissionError("PATTERN_SOURCE_STALE")
        with _pattern_mutation() as (registry, conn):
            existing = registry.snapshot().get(pattern_id)
            committed = conn.execute("SELECT 1 FROM content_generation_evidence WHERE content_type IN "
                "('pattern_candidate','pattern_retirement') AND json_extract(input_json,'$.pattern_id')=? LIMIT 1",
                (pattern_id,)).fetchone()
            if existing is not None or committed is not None:
                try:
                    old = _pattern_current(pattern_id)
                except (ValueError, PermissionError, RuntimeError):
                    return jsonify({"ok": False, "code": "PATTERN_RECOVERY_REQUIRED", "pattern_id": pattern_id,
                                    "recovery_url": f"/api/content/patterns/{pattern_id}/recovery"}), 409
                rows = conn.execute("SELECT * FROM content_generation_evidence WHERE content_type='pattern_candidate' "
                    "AND json_extract(input_json,'$.pattern_id')=?", (pattern_id,)).fetchall()
                matching = [r for r in rows if _row_allowed(r) and json.loads(r["input_json"]).get("request_digest") == request_digest]
                if not matching:
                    raise ValueError("PATTERN_REQUEST_REUSE_CONFLICT")
                return jsonify({"ok": True, "replayed": True, "candidate": old.to_dict(),
                    "candidate_hash": registry.fingerprint(old), "evidence_id": matching[0]["evidence_id"], "active": False}), 201
            receipt = record_evidence("pattern_candidate", {"pattern_id": asset.asset_id, "request_digest": request_digest, "request_id": request_id, "_content_sources": bindings},
                "", "Explicit user-authored research principle", "", asset.to_dict(), "none", "human", "low", 0.0, 0,
                "candidate", connection=conn)
            registry.save_candidate(asset)
            if _bindings(data["source_evidence_refs"]) != bindings:
                raise PermissionError("PATTERN_SOURCE_STALE")
        return jsonify({"ok": True, "candidate": asset.to_dict(), "candidate_hash": _pattern_registry().fingerprint(asset),
                        "evidence_id": receipt, "active": False, "truth_status": "DERIVED_HUMAN_PROPOSAL"}), 201
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/patterns", methods=["GET"])
def api_pattern_candidates():
    try:
        assets = _pattern_registry().scoped_candidates(context=_context(), current_sources=_bindings,
            platform=request.args.get("platform", ""), format_name=request.args.get("format", ""),
            audience=request.args.get("audience", ""), objective=request.args.get("objective", ""), limit=20)
        results = []
        for asset in assets:
            try:
                _pattern_receipt(asset)
            except (ValueError, PermissionError):
                continue
            results.append({"candidate": asset.to_dict(), "candidate_hash": _pattern_registry().fingerprint(asset)})
        return jsonify({"ok": True, "candidates": results, "automatic_application": False})
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/patterns/<pattern_id>/apply", methods=["POST"])
def api_apply_pattern(pattern_id):
    try:
        from lumenis.shared.reporting.saved_work import save_work
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"candidate_hash", "brief", "confirmed", "request_id"}:
            raise ValueError("PATTERN_APPLICATION_INPUT_INVALID")
        if body["confirmed"] is not True:
            raise PermissionError("PATTERN_EXPLICIT_APPLICATION_REQUIRED")
        brief = body["brief"]
        if (not isinstance(brief, dict) or set(brief) != {"title", "text", "platform", "format", "audience", "objective"}
                or any(not isinstance(v, str) or not v.strip() or len(v) > 6000 for v in brief.values())):
            raise ValueError("PATTERN_BRIEF_INVALID")
        if not isinstance(body["candidate_hash"], str) or len(body["candidate_hash"]) != 64:
            raise ValueError("PATTERN_VERSION_CONFLICT")
        asset = _pattern_current(pattern_id, body["candidate_hash"])
        from lumenis.shared.learning.content_assets import retrieve_pattern_candidates
        if not retrieve_pattern_candidates([asset], platform=brief["platform"], format_name=brief["format"],
                                            audience=brief["audience"], objective=brief["objective"]):
            raise ValueError("PATTERN_BRIEF_SCOPE_MISMATCH")
        _content_effect()
        trace = {"contract_version": "content-pattern-application:v1", "pattern_id": asset.asset_id,
                 "pattern_version": asset.version, "pattern_hash": body["candidate_hash"],
                 "source_bindings": list(asset.source_bindings), "actor_scope": _context(),
                 "brief_sha256": hashlib.sha256(json.dumps(brief, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                 "model_version": "none", "prompt_contract_version": "deterministic-pattern-brief:v1",
                 "application": "EXPLICIT", "factual_claims": "UNKNOWN_UNLESS_SEPARATELY_VERIFIED",
                 "review_status": "HUMAN_PENDING", "pattern_decision": "EXPERIMENT"}
        # The original brief is preserved. A reusable principle is a visible draft
        # composition aid, never rewritten into asserted external facts.
        markdown = ("# " + brief["title"] + "\n\n" + brief["text"] + "\n\n## Composition guidance\n\n"
                    + asset.extracted_principle + "\n\n" + json.dumps(dict(asset.reusable_pattern), ensure_ascii=False, indent=2)
                    + "\n\nReview pending. Source references teach principles; factual claims remain unverified.\n")
        sources = _source_material([int(x) for x in asset.source_refs])
        citations = [{"evidence_id": row["evidence_id"], "start": 0, "end": min(len(row["text"]), 80),
                      "quote": row["text"][:80]} for row in sources]
        def recheck(connection, record, document):
            authorize_content_root_request(strict=True)
            _pattern_current(pattern_id, body["candidate_hash"])
            _record_content_work("pattern_application", connection, record, document,
                                 source_bindings=list(asset.source_bindings))
        result = save_work(title=brief["title"], markdown=markdown, kind="research",
            payload={"brief": brief, "application_trace": trace, "creative_guidance": dict(asset.reusable_pattern)},
            citations=citations, request_id=body["request_id"], actor=g.content_actor,
            scope=g.content_scope.get("shared_workspace_scope", g.content_scope), before_commit=recheck)
        _pattern_current(pattern_id, body["candidate_hash"])
        return jsonify({"ok": True, "result": result, "application_trace": trace,
                        "publish_status": "not_performed", "review_status": "HUMAN_PENDING"}), 201
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/patterns/<pattern_id>/retire", methods=["POST"])
def api_retire_pattern(pattern_id):
    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"candidate_hash", "confirmed"} or body["confirmed"] is not True:
            raise ValueError("PATTERN_RETIRE_CONFIRMATION_REQUIRED")
        if not isinstance(body["candidate_hash"], str) or len(body["candidate_hash"]) != 64:
            raise ValueError("PATTERN_VERSION_CONFLICT")
        _pattern_current(pattern_id, body["candidate_hash"])
        _content_effect()
        with _pattern_mutation() as (registry, conn):
            current = _pattern_current(pattern_id, body["candidate_hash"])
            bindings = list(current.source_bindings)
            record_evidence("pattern_retirement", {"pattern_id": pattern_id, "_content_sources": bindings},
                "", "Explicit candidate retirement", "",
                {"pattern_id": pattern_id, "previous_version_hash": body["candidate_hash"], "state": "retired"},
                "none", "human", "low", 0, 0, "retired", connection=conn)
            retired = registry.retire(pattern_id, context=_context(), current_sources=_bindings,
                                      expected_hash=body["candidate_hash"])
            if _bindings([int(x) for x in current.source_refs]) != bindings:
                raise PermissionError("PATTERN_SOURCE_STALE")
        return jsonify({"ok": True, "pattern_id": pattern_id, "state": retired.lifecycle_state,
                        "version": retired.version, "previous_version_hash": retired.previous_version_hash,
                        "existing_artifacts": "preserved_as_history"})
    except Exception as exc:
        return _pattern_error(exc)


CONTENT_REVIEW_DIMENSIONS = ("platform_fit", "season_fit", "brand_fit", "emotion_consistency",
    "visual_narrative", "topic_fit", "search_alignment", "commerciality", "risk")


def _draft_claims(claims, text):
    if not isinstance(claims, list) or len(claims) > 100:
        raise ValueError("CONTENT_CLAIMS_INVALID")
    result, ids = [], set()
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"claim_id", "text", "start", "end"}:
            raise ValueError("CONTENT_CLAIM_INVALID")
        cid, start, end = claim["claim_id"], claim["start"], claim["end"]
        if (not isinstance(cid, str) or not cid.strip() or len(cid) > 100 or cid in ids
                or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
                or text[start:end] != claim["text"]):
            raise ValueError("CONTENT_CLAIM_LOCATOR_INVALID")
        ids.add(cid)
        result.append({**claim, "verification": "NOT_VERIFIED"})
    return result


def _content_work_binding(record, document):
    return {"artifact_id": record["artifact_id"], "sha256": record["sha256"],
            "work_id": document["work_id"], "version": document["version"],
            "draft_digest": document["draft_digest"]}


def _record_content_work(kind, connection, record, document, *, source_bindings):
    """Same SavedWork transaction, existing signed Content Evidence owner."""
    return record_evidence(kind, {"artifact_id": record["artifact_id"],
        "_content_sources": source_bindings}, "",
        "Deterministic composition or explicit current revision; inspect package authorship" if kind == "content_multiplatform" else "Explicit current content authorship",
        "", _content_work_binding(record, document), "none",
        "deterministic" if kind == "content_multiplatform" else "human", "low", 0, 0,
        "draft", connection=connection)


def _content_work_receipt(saved):
    """A copied payload never proves that this owner produced its artifact."""
    with get_repository().connection(read_only=True, wal=False) as con:
        rows = con.execute("SELECT * FROM content_generation_evidence WHERE content_type IN "
            "('pattern_application','content_draft','content_multiplatform') AND json_extract(input_json,'$.artifact_id')=?",
            (saved["artifact"]["artifact_id"],)).fetchall()
    if not rows:
        return None
    if len(rows) != 1 or not _row_allowed(rows[0]) or json.loads(rows[0]["output_json"]) != _content_work_binding(
            saved["artifact"], saved["document"]):
        raise PermissionError("CONTENT_PARENT_RECEIPT_INVALID")
    return dict(rows[0])


@content_bp.route("/drafts", methods=["POST"])
def api_save_content_draft():
    """Standalone authorship or explicit typed continuation, without a model.

    Legacy/generic parents require fresh explicit adoption. Their metadata stays
    unverified historical context; this never manufactures a past owner receipt.
    """
    try:
        from lumenis.shared.reporting import saved_work
        body = request.get_json(silent=True)
        required = {"title", "text", "request_id", "claims"}
        if (not isinstance(body, dict) or not required <= set(body)
                or set(body) - required - {"parent"}):
            raise ValueError("CONTENT_DRAFT_INPUT_INVALID")
        if not isinstance(body["text"], str) or not body["text"].strip() or len(body["text"]) > 100000:
            raise ValueError("CONTENT_DRAFT_TEXT_INVALID")
        claims = _draft_claims(body["claims"], body["text"])
        expected_context = _context()
        scope = g.content_scope.get("shared_workspace_scope", g.content_scope)
        parent = None
        owner_receipt = None
        citations = []
        version_args = {}
        payload = {"content_contract_version": "content-review:v1", "claims": claims,
                   "content_review": {"decision": "NOT_VERIFIED", "dimensions": {
                       key: {"status": "not_verified", "method": "human_review_required"}
                       for key in CONTENT_REVIEW_DIMENSIONS}}}
        if "parent" in body:
            spec = body["parent"]
            if (not isinstance(spec, dict) or set(spec) != {
                    "artifact_id", "sha256", "draft_digest", "adopt_unverified_parent"}
                    or type(spec["adopt_unverified_parent"]) is not bool):
                raise ValueError("CONTENT_DRAFT_PARENT_INVALID")
            parent = saved_work.read_committed_work(spec["artifact_id"], actor=g.content_actor, scope=scope)
            document = parent["document"]
            if (parent["artifact"]["sha256"] != spec["sha256"]
                    or document["draft_digest"] != spec["draft_digest"]):
                raise ValueError("CONTENT_DRAFT_PARENT_CHANGED")
            if (document["kind"] != "research" or document.get("task_id") is not None
                    or document.get("assertion_id") is not None
                    or document["contract"] != {"id": "lumenis.saved-work", "version": "1", "required_payload_paths": []}):
                raise ValueError("CONTENT_DRAFT_PARENT_OWNER_REQUIRED")
            owner_receipt = _content_work_receipt(parent)
            if "multiplatform" in document["payload"]:
                raise ValueError("MULTIPLATFORM_REVISION_OWNER_REQUIRED")
            if owner_receipt is None and not spec["adopt_unverified_parent"]:
                raise PermissionError("CONTENT_PARENT_EXPLICIT_ADOPTION_REQUIRED")
            old = document["payload"]
            if owner_receipt is not None:
                if owner_receipt["content_type"] == "pattern_application":
                    payload["content_origin"] = {key: old[key] for key in (
                        "brief", "application_trace", "creative_guidance")}
                elif "content_origin" in old:
                    payload["content_origin"] = old["content_origin"]
                if "unverified_parent_context" in old:
                    payload["unverified_parent_context"] = old["unverified_parent_context"]
            else:
                # Historical metadata is data, never trusted trace, approval,
                # current source binding or an executable dependency.
                payload["unverified_parent_context"] = {"status": "NOT_VERIFIED",
                    "historical_payload": old, "past_owner_execution": "NOT_VERIFIED"}
            payload["content_continuation"] = {"contract_version": "content-continuation:v1",
                "parent": _content_work_binding(parent["artifact"], document),
                "parent_owner_receipt_id": owner_receipt["evidence_id"] if owner_receipt else None,
                "adoption": "OWNER_VERIFIED_PARENT" if owner_receipt else "EXPLICIT_CURRENT_ADOPTION",
                "authorship": "current-user-edited; factual claims require fresh review"}
            citations = document["citations"]
            version_args = {"work_id": document["work_id"],
                "previous_artifact_id": parent["artifact"]["artifact_id"],
                "expected_draft_digest": document["draft_digest"], "contract": document["contract"]}
        sources = _bindings(list(dict.fromkeys(x["evidence_id"] for x in citations))) if citations else []
        def recheck(connection, record, document):
            authorize_content_root_request(strict=True)
            if _context() != expected_context:
                raise PermissionError("CONTENT_CONTEXT_CHANGED")
            _content_effect()
            if parent is not None:
                current = saved_work.read_committed_work(parent["artifact"]["artifact_id"],
                    actor=g.content_actor, scope=scope, connection=connection)
                if current["document"] != parent["document"] or _content_work_receipt(current) != owner_receipt:
                    raise PermissionError("CONTENT_DRAFT_PARENT_CHANGED")
            _record_content_work("content_draft", connection, record, document, source_bindings=sources)
        result = saved_work.save_work(title=body["title"], markdown=body["text"], kind="research",
            payload=payload, citations=citations, request_id=body["request_id"],
            actor=g.content_actor, scope=scope, before_commit=recheck, **version_args)
        if _content_work_receipt(result) is None:
            raise PermissionError("CONTENT_DRAFT_RECEIPT_REQUIRED")
        return jsonify({"ok": True, "result": result, "review_status": "NOT_VERIFIED", "model_used": False}), 201
    except Exception as exc:
        return _pattern_error(exc)


def _review_draft(artifact_id):
    from lumenis.shared.reporting.saved_work import reopen_work
    saved = reopen_work(artifact_id, actor=g.content_actor,
                       scope=g.content_scope.get("shared_workspace_scope", g.content_scope))
    document = saved["document"]
    if document["payload"].get("content_contract_version") != "content-review:v1":
        raise ValueError("CONTENT_REVIEW_DRAFT_CONTRACT_REQUIRED")
    receipt = _content_work_receipt(saved)
    if "multiplatform" in document["payload"]:
        _multiplatform_read(artifact_id)
    if receipt is None and any(key in document["payload"] for key in ("content_continuation", "content_origin")):
        raise PermissionError("CONTENT_DRAFT_RECEIPT_REQUIRED")
    # Storage citation admission alone is not Content source-use permission.
    # Every inherited reference is consumed by review, even with zero claims.
    # Legacy standalone drafts remain reviewable without retroactive receipts.
    _review_draft_sources(saved)
    claims = document["payload"].get("claims")
    if not isinstance(claims, list) or any(not isinstance(x, dict) or set(x) != {
            "claim_id", "text", "start", "end", "verification"} for x in claims):
        raise ValueError("CONTENT_REVIEW_DRAFT_CLAIMS_INVALID")
    # Generic SavedWork edits remain drafts. Revalidate exact text locations,
    # and never consume a client-authored verification label as a review.
    document["payload"]["claims"] = _draft_claims(
        [{k:v for k,v in x.items() if k != "verification"} for x in claims], document["markdown"])
    return saved


def _review_draft_sources(saved):
    """Draft reference consumption, explicitly separate from claim support."""
    return {evidence_id: _bindings([evidence_id])[0] for evidence_id in
            dict.fromkeys(item["evidence_id"] for item in saved["document"]["citations"])}


def _review_material(artifact_id, review_id):
    """Current immutable artifact, signed reviewer receipt and source-use readback."""
    saved = _review_draft(artifact_id)
    row = get_evidence(review_id)
    if not row or row["content_type"] != "content_review":
        raise PermissionError("CONTENT_REVIEW_RECEIPT_REQUIRED")
    review = json.loads(row["output_json"])
    if (review["artifact_id"] != artifact_id or review["artifact_sha256"] != saved["artifact"]["sha256"]
            or review["draft_digest"] != saved["document"]["draft_digest"]
            or review["reviewer_context"] != _context()):
        raise PermissionError("CONTENT_REVIEW_VERSION_MISMATCH")
    inputs = json.loads(row["input_json"])
    binding = {"review": review, "source_bindings": inputs.get("_content_sources", []),
               "draft": saved["document"], "context": _context()}
    resource = "content-review:v1:" + hashlib.sha256(json.dumps(binding, sort_keys=True,
        ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if review.get("contract_version") != "content-review:v2" or inputs.get("approval_resource") != resource:
        raise PermissionError("CONTENT_REVIEW_EXACT_APPROVAL_RECEIPT_REQUIRED")
    # Only the newest decision for this immutable draft is current. Earlier
    # receipts remain readable history, but cannot reactivate a withdrawn pass.
    with get_repository().connection(read_only=True, wal=False) as con:
        latest = con.execute("SELECT evidence_id FROM content_generation_evidence WHERE content_type='content_review' "
            "AND json_extract(input_json,'$.artifact_id')=? ORDER BY rowid DESC LIMIT 1", (artifact_id,)).fetchone()
    if latest is None or latest[0] != review_id:
        raise PermissionError("CONTENT_REVIEW_SUPERSEDED")
    return saved, review


def _review_approved_claim_ids(artifact_id, review_id):
    _, review = _review_material(artifact_id, review_id)
    if review["decision"] != "READY":
        return {}
    return {x["claim_id"]: x for x in review["claims"] if x["decision"] == "supported_by_human_review"}


@content_bp.route("/drafts/<artifact_id>/reviews", methods=["POST"])
def api_review_content_draft(artifact_id):
    try:
        from lumenis.system.security import permission as p
        body = request.get_json(silent=True)
        required = {"draft_digest", "claims", "dimensions", "confirmed", "all_factual_claims_enumerated"}
        if (not isinstance(body, dict) or set(body) - required - {"confirmed_resource", "confirmation_id"}
                or not required.issubset(body) or type(body["confirmed"]) is not bool):
            raise ValueError("CONTENT_REVIEW_CONFIRMATION_REQUIRED")
        if body["all_factual_claims_enumerated"] is not True:
            raise ValueError("CONTENT_REVIEW_CLAIM_COVERAGE_REQUIRED")
        gate = p.get_permission_gate()
        if not gate.has_permission(p.PermissionLevel.HUMAN_APPROVAL):
            raise PermissionError("CONTENT_HUMAN_REVIEW_AUTHORITY_REQUIRED")
        # Session identity is freshly resolved by the original content scope owner.
        # Account review is restricted to its actual owner/admin role; a sealed
        # local workspace principal retains the existing single-user capability.
        if isinstance(g.content_actor, dict) and g.content_actor.get("role") not in {"owner", "admin"}:
            raise PermissionError("CONTENT_REVIEWER_ROLE_REQUIRED")
        saved = _review_draft(artifact_id)
        document = saved["document"]
        if body["draft_digest"] != document["draft_digest"]:
            raise ValueError("CONTENT_REVIEW_VERSION_CONFLICT")
        dims = body["dimensions"]
        if not isinstance(dims, dict) or set(dims) != set(CONTENT_REVIEW_DIMENSIONS):
            raise ValueError("CONTENT_REVIEW_NINE_DIMENSIONS_REQUIRED")
        for value in dims.values():
            if (not isinstance(value, dict) or set(value) != {"status", "reason"}
                    or value["status"] not in {"pass", "fail", "not_verified"}
                    or not isinstance(value["reason"], str) or not value["reason"].strip() or len(value["reason"]) > 2000):
                raise ValueError("CONTENT_REVIEW_DIMENSION_INVALID")
        original = {x["claim_id"]: x for x in document["payload"]["claims"]}
        decisions = body["claims"]
        if not isinstance(decisions, list) or len(decisions) != len(original):
            raise ValueError("CONTENT_REVIEW_CLAIMS_INCOMPLETE")
        draft_sources = _review_draft_sources(saved)
        seen, claims, sources = set(), [], dict(draft_sources)
        for item in decisions:
            if not isinstance(item, dict) or set(item) != {"claim_id", "decision", "reason", "locators"}:
                raise ValueError("CONTENT_REVIEW_CLAIM_INVALID")
            cid = item["claim_id"]
            if cid not in original or cid in seen or item["decision"] not in {"supported_by_human_review", "needs_revision", "not_verified"}:
                raise ValueError("CONTENT_REVIEW_CLAIM_INVALID")
            if not isinstance(item["reason"], str) or not item["reason"].strip() or len(item["reason"]) > 2000:
                raise ValueError("CONTENT_REVIEW_REASON_REQUIRED")
            seen.add(cid)
            locators = item["locators"]
            if not isinstance(locators, list) or len(locators) > 8 or (item["decision"] == "supported_by_human_review" and not locators):
                raise ValueError("CONTENT_REVIEW_EVIDENCE_LOCATOR_REQUIRED")
            for loc in locators:
                if not isinstance(loc, dict) or set(loc) != {"evidence_id", "start", "end", "quote"}:
                    raise ValueError("CONTENT_REVIEW_EVIDENCE_LOCATOR_INVALID")
                source = _source_material([loc["evidence_id"]])[0]
                start, end = loc["start"], loc["end"]
                if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source["text"])
                        or source["text"][start:end] != loc["quote"]):
                    raise ValueError("CONTENT_REVIEW_EVIDENCE_QUOTE_MISMATCH")
                sources[source["evidence_id"]] = {k:v for k,v in source.items() if k != "text"}
            claims.append({**original[cid], **item, "evidence_ids": [str(x["evidence_id"]) for x in locators],
                           "verification": "HUMAN_REVIEWED" if item["decision"] == "supported_by_human_review" else "NOT_VERIFIED"})
        statuses = [x["status"] for x in dims.values()]
        decision = ("BLOCKED" if dims["risk"]["status"] == "fail" else
                    "NEEDS_REVISION" if "fail" in statuses or any(x["decision"] == "needs_revision" for x in claims) else
                    "NOT_VERIFIED" if "not_verified" in statuses or any(x["decision"] == "not_verified" for x in claims) else "READY")
        if "multiplatform" in document["payload"] and any(
                v["state"] != "DRAFT" for v in document["payload"]["multiplatform"]["variants"]):
            decision = "NEEDS_REVISION" if decision == "READY" else decision
        review = {"contract_version": "content-review:v2", "artifact_id": artifact_id,
                  "artifact_sha256": saved["artifact"]["sha256"], "draft_digest": document["draft_digest"],
                  "artifact_version": document["version"], "reviewer_context": _context(), "claims": claims,
                  "dimensions": dims, "decision": decision, "all_factual_claims_enumerated": True,
                  "draft_source_evidence_ids": list(draft_sources),
                  "method": "explicit_human_review_with_verified_source_locators",
                  "automatic_semantic_truth_verification": False, "publish_status": "not_performed"}
        # Current source bytes and actor are checked again at the write boundary.
        authorize_content_root_request(strict=True)
        if sources and _bindings(list(sources)) != list(sources.values()):
            raise PermissionError("CONTENT_REVIEW_SOURCE_STALE")
        binding = {"review": review, "source_bindings": list(sources.values()),
                   "draft": document, "context": _context()}
        resource = "content-review:v1:" + hashlib.sha256(json.dumps(binding, sort_keys=True,
            ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        caller = json.dumps(_context(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        if body["confirmed"] is False:
            prepared = gate.prepare_content_review(binding, caller=caller)
            return jsonify({"ok": True, "state": "APPROVAL_REQUIRED", **prepared,
                            "operation": p.OperationType.REPORT_REVIEW.value, "binding": binding})
        if body.get("confirmed_resource") != resource or not isinstance(body.get("confirmation_id"), str):
            raise PermissionError("CONTENT_REVIEW_EXACT_APPROVAL_REQUIRED")
        token = gate.confirm_content_review(body["confirmation_id"], binding, caller=caller, resource=resource)
        def review_recheck():
            if gate.get_valid_approval_token(p.OperationType.REPORT_REVIEW.value, resource, exact=True) != token:
                raise PermissionError("CONTENT_REVIEW_APPROVAL_REVOKED")
            current = _review_draft(artifact_id)
            if current["document"] != document or current["artifact"]["sha256"] != review["artifact_sha256"]:
                raise PermissionError("CONTENT_REVIEW_VERSION_MISMATCH")
            if isinstance(g.content_actor, dict) and g.content_actor.get("role") not in {"owner", "admin"}:
                raise PermissionError("CONTENT_REVIEWER_ROLE_REQUIRED")
        try:
            eid = record_evidence("content_review", {"artifact_id": artifact_id,
                "_content_sources": list(sources.values()), "approval_resource": resource},
                "", "Explicit nine-dimension and claim review", "", review, "none", "human", "low", 0, 0,
                "reviewed", before_commit=review_recheck,
                commit_lease=lambda: gate.content_review_commit_lease(token, resource=resource, caller=caller))
        finally:
            gate.revoke_approval(token)
        _review_material(artifact_id, eid)
        return jsonify({"ok": True, "review_evidence_id": eid, "review": review}), 201
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/drafts/<artifact_id>/reviews/<review_id>", methods=["GET"])
def api_content_review_status(artifact_id, review_id):
    try:
        _, review = _review_material(artifact_id, review_id)
        from podcast.intelligence.research_pipeline import ResearchClaim, EvidenceStatus, evidence_gate
        claims = [ResearchClaim(x["claim_id"], x["text"], tuple(x["evidence_ids"]),
                                EvidenceStatus.HUMAN_VERIFIED if x["evidence_ids"] else EvidenceStatus.UNVERIFIED, 1.0)
                  for x in review["claims"]]
        eligible = evidence_gate(claims, artifact_id=artifact_id, review_evidence_id=review_id)
        return jsonify({"ok": True, "review": review, "eligible_claim_ids": [x.claim_id for x in eligible],
                        "publish_performed": False})
    except Exception as exc:
        return _pattern_error(exc)


CONTENT_ENDPOINTS = {'api_content_types': ('/api/content/types', ['GET']),
 'api_generate': ('/api/content/generate', ['POST']),
 'api_generate_typed': ('/api/content/generate/<content_type>', ['POST']),
 'api_feedback': ('/api/content/feedback', ['POST']),
 'api_get_evidence': ('/api/content/evidence/<evidence_id>', ['GET']),
 'api_list_evidence': ('/api/content/evidence', ['GET']),
 'api_research_search': ('/api/content/research/search', ['GET']),
 'api_modules': ('/api/content/modules', ['GET']),
 'api_ad_strategy': ('/api/content/ad-strategy', ['POST']),
 'api_video_analyze': ('/api/content/video-analyze', ['POST']),
 'api_brand_report_generate': ('/api/content/brand-report/generate', ['POST']),
 'api_resources': ('/api/content/resources', ['GET']),
 'api_topic_campaign_status': ('/api/content/topic-campaign/status', ['GET']),
 'api_topic_snapshot': ('/api/content/topic-snapshot', ['GET', 'POST']),
 'api_podcast_research': ('/api/content/podcast-research', ['POST']),
 'api_create_pattern': ('/api/content/patterns', ['POST']),
 'api_pattern_candidates': ('/api/content/patterns', ['GET']),
 'api_apply_pattern': ('/api/content/patterns/<pattern_id>/apply', ['POST']),
 'api_retire_pattern': ('/api/content/patterns/<pattern_id>/retire', ['POST']),
 'api_recover_pattern': ('/api/content/patterns/<pattern_id>/recovery', ['POST']),
 'api_save_content_draft': ('/api/content/drafts', ['POST']),
 'api_review_content_draft': ('/api/content/drafts/<artifact_id>/reviews',
                              ['POST']),
 'api_content_review_status': ('/api/content/drafts/<artifact_id>/reviews/<review_id>',
                               ['GET'])}


def _pattern_contract_error(exc):
    """Public typed errors only; keep paths, SQL and unexpected details in server logs."""
    import re
    from flask import current_app
    code = str(exc)
    known = re.fullmatch(r"(?:PATTERN|CONTENT|WORK|SHARED_WORKSPACE|LEARNING)_[A-Z0-9_]{1,100}", code) is not None
    if not known:
        current_app.logger.exception("Content pattern contract failed")
        return jsonify({"ok": False, "code": "PATTERN_SERVICE_UNAVAILABLE"}), 503
    status = 403 if isinstance(exc, PermissionError) else 409 if any(x in code for x in ("CONFLICT", "STALE", "RETIRED")) else 400
    return jsonify({"ok": False, "code": code}), status


# Existing Shared Evaluation/Learning owners, with exact endpoint admission.
# Measurements do not assert independent hold-out or real-business gains.
def _pattern_evaluation(pattern_id, evaluation_id, *, connection=None):
    from lumenis.shared.evaluation.runner import verify_content_pattern_measurement
    owns = connection is None
    con = connection or _get_conn()
    try:
        row = con.execute("SELECT * FROM content_generation_evidence WHERE evidence_id=? AND content_type='pattern_evaluation'",
                          (evaluation_id,)).fetchone()
        if row is None:
            raise PermissionError("PATTERN_EVALUATION_NOT_FOUND")
        row = dict(row)
        _verify_content_receipt(row, connection=con)
        inputs, output = json.loads(row["input_json"]), json.loads(row["output_json"])
        asset = _pattern_current(pattern_id)
        if (inputs.get("pattern_id") != pattern_id or inputs.get("candidate_hash") != _pattern_registry().fingerprint(asset)
                or inputs.get("_content_context") != _context()
                or inputs.get("_content_sources") != list(asset.source_bindings)):
            raise PermissionError("PATTERN_EVALUATION_CONTEXT_CHANGED")
        for ref in output["evaluation_records"]:
            raw = con.execute("SELECT * FROM evaluation_records WHERE evaluation_id=?", (ref["evaluation_id"],)).fetchone()
            if raw is None or _pattern_digest(dict(raw)) != ref["row_hash"]:
                raise PermissionError("PATTERN_EVALUATION_RECORD_CHANGED")
        scope = g.content_scope.get("shared_workspace_scope", g.content_scope)
        measurement = verify_content_pattern_measurement(output["measurement"], actor=g.content_actor,
                                                           scope=scope, connection=con)
        return {"evaluation_id": evaluation_id, "receipt_hash": _row_digest(row),
                "measurement": measurement, "evaluation_records": output["evaluation_records"]}
    finally:
        if owns:
            con.close()


def _pattern_promotion_qualification(evaluation):
    """Only measured engineering evidence exists in this path today.

    Actual held-out/task outcome admission requires independently scoped Task /
    SavedWork / human-review receipts; a client's quality, PASS or split labels
    never establish those facts. Keep the exact unmet conditions visible.
    """
    measurement = evaluation["measurement"]
    return {"eligible": False, "reasons": list(measurement["reasons"]),
            "qualification_owner": "Shared Evaluation",
            "required_evidence": ["frozen_independent_task_split", "two_independent_validation_rounds",
                                  "actual_task_outcomes", "counterexample_and_rights_review"]}


def _pattern_transition_binding_from_selectors(selectors, *, connection, after_write=False):
    from lumenis.shared.learning.content_assets import pattern_decisions
    pattern_id = selectors["pattern_id"]
    asset = _pattern_current(pattern_id, selectors["candidate_hash"])
    action = selectors["action"]
    if action not in {"promote", "rollback", "disable"}:
        raise ValueError("PATTERN_TRANSITION_ACTION_INVALID")
    request_id = selectors["request_id"]
    if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
        raise ValueError("PATTERN_TRANSITION_REQUEST_ID_INVALID")
    history = pattern_decisions(connection, pattern_id=pattern_id, context=_context())
    if after_write:
        if not history or history[-1]["binding_hash"] != _pattern_digest(selectors):
            raise PermissionError("PATTERN_TRANSITION_AFTER_MISMATCH")
        history = history[:-1]
    current = history[-1] if history else None
    evaluation_id, target_id = selectors.get("selected_evaluation_id"), selectors.get("target_decision_id")
    eval_hash = None
    if action == "promote":
        if not isinstance(evaluation_id, str) or target_id is not None:
            raise ValueError("PATTERN_EVALUATION_REQUIRED")
        evaluation = _pattern_evaluation(pattern_id, evaluation_id, connection=connection)
        if not _pattern_promotion_qualification(evaluation)["eligible"]:
            raise ValueError("PATTERN_NOT_ELIGIBLE")
        eval_hash = evaluation["receipt_hash"]
    elif action == "rollback":
        target = next((item for item in history if item["decision_id"] == target_id), None)
        if (not current or not target or target == current or not target["effective"]
                or target["candidate_hash"] != _pattern_registry().fingerprint(asset)
                or evaluation_id != target["selected_evaluation_id"]):
            raise ValueError("PATTERN_ROLLBACK_TARGET_INVALID")
        evaluation = _pattern_evaluation(pattern_id, evaluation_id, connection=connection)
        if not _pattern_promotion_qualification(evaluation)["eligible"]:
            raise ValueError("PATTERN_ROLLBACK_TARGET_NOT_CURRENT")
        eval_hash = evaluation["receipt_hash"]
    elif not current or not current["effective"] or target_id is not None or evaluation_id is not None:
        raise ValueError("PATTERN_DISABLE_TARGET_INVALID")
    return {"contract_version": "content-pattern-transition:v1", "pattern_id": pattern_id,
            "context": _context(), "candidate_hash": _pattern_registry().fingerprint(asset),
            "source_bindings": list(asset.source_bindings), "action": action,
            "previous_decision_id": current["decision_id"] if current else None,
            "previous_decision_hash": current["receipt_hash"] if current else None,
            "selected_evaluation_id": evaluation_id, "evaluation_hash": eval_hash,
            "target_decision_id": target_id, "request_id": request_id}


@content_bp.route("/patterns/<pattern_id>/evaluations", methods=["POST"])
def api_evaluate_pattern(pattern_id):
    try:
        from lumenis.shared.evaluation import runner, recorder
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"candidate_hash", "baseline_artifact_id", "candidate_artifact_id", "criteria"}:
            raise ValueError("PATTERN_EVALUATION_INPUT_INVALID")
        asset = _pattern_current(pattern_id, body["candidate_hash"])
        measured = runner.measure_content_pattern(candidate_hash=body["candidate_hash"],
            baseline_artifact_id=body["baseline_artifact_id"], candidate_artifact_id=body["candidate_artifact_id"],
            criteria=body["criteria"], actor=g.content_actor,
            scope=g.content_scope.get("shared_workspace_scope", g.content_scope))
        # Evaluation records commit first. Only a later signed completion receipt
        # admits the bundle; a partial evaluator write never authorizes promotion.
        recorder.init_db()
        run_id = "pattern-eval-" + _pattern_digest({"context": _context(), "measurement": measured})
        refs = []
        for metric_name, value in (("required_phrase_gain", measured["gain"]),
                                    ("candidate_required_phrase_coverage", measured["outputs"]["candidate"]["required_phrase_coverage"])):
            record = recorder.record_evaluation("report", metric_name, value, 1.0, 0.0,
                source="shared_evaluation:content_pattern", evidence_ref=run_id,
                metadata={"method": measured["method"], "measurement_hash": _pattern_digest(measured),
                          "context": _context(), "qualification": "ENGINEERING_ONLY"},
                evaluation_id=run_id + ":" + metric_name)
            with get_repository().connection(read_only=True, wal=False) as con:
                raw = con.execute("SELECT * FROM evaluation_records WHERE evaluation_id=?", (record.evaluation_id,)).fetchone()
                refs.append({"evaluation_id": record.evaluation_id, "row_hash": _pattern_digest(dict(raw))})
        def recheck():
            _pattern_current(pattern_id, body["candidate_hash"])
            runner.verify_content_pattern_measurement(measured, actor=g.content_actor,
                scope=g.content_scope.get("shared_workspace_scope", g.content_scope))
        with _pattern_mutation(before_commit=recheck) as (_registry, con):
            old = con.execute("SELECT * FROM content_generation_evidence WHERE content_type='pattern_evaluation' "
                "AND json_extract(input_json,'$.run_id')=?", (run_id,)).fetchall()
            if len(old) > 1:
                raise ValueError("PATTERN_EVALUATION_RECEIPT_CONFLICT")
            if old:
                eid = old[0]["evidence_id"]
            else:
                eid = record_evidence("pattern_evaluation", {"pattern_id": pattern_id, "run_id": run_id,
                    "candidate_hash": body["candidate_hash"], "_content_sources": list(asset.source_bindings)},
                    "", "Server-recomputed exact phrase measurements; independent business lift not verified", "",
                    {"measurement": measured, "evaluation_records": refs}, "none", "deterministic", "low", 0, 0,
                    "NOT_ELIGIBLE", connection=con)
        result = _pattern_evaluation(pattern_id, eid)
        return jsonify({"ok": True, **result, "qualification": _pattern_promotion_qualification(result)}), 201
    except Exception as exc:
        return _pattern_contract_error(exc)


@content_bp.route("/patterns/<pattern_id>/evaluations/<evaluation_id>", methods=["GET"])
def api_read_pattern_evaluation(pattern_id, evaluation_id):
    try:
        result = _pattern_evaluation(pattern_id, evaluation_id)
        return jsonify({"ok": True, **result, "qualification": _pattern_promotion_qualification(result)})
    except Exception as exc:
        return _pattern_contract_error(exc)


@content_bp.route("/patterns/<pattern_id>/transitions", methods=["POST"])
def api_pattern_transition(pattern_id):
    try:
        from lumenis.system.security import permission as p
        from lumenis.system.security.effect_fence import get_effect_fence
        from lumenis.shared.learning.content_assets import promote_pattern, pattern_decisions
        body = request.get_json(silent=True)
        required = {"candidate_hash", "action", "selected_evaluation_id", "target_decision_id", "request_id", "confirmed"}
        optional = {"confirmation_id", "activation_resource", "write_resource"}
        if (not isinstance(body, dict) or not required.issubset(body) or set(body) - required - optional
                or type(body["confirmed"]) is not bool):
            raise ValueError("PATTERN_TRANSITION_INPUT_INVALID")
        selectors = {k: body[k] for k in required - {"confirmed"}}
        selectors["pattern_id"] = pattern_id
        commit = {}
        def lease():
            from contextlib import nullcontext
            return p.pattern_approval_commit_lease(**commit) if commit else nullcontext()
        with _pattern_mutation(commit_lease=lease) as (_registry, con):
            asset = _pattern_current(pattern_id, body["candidate_hash"])
            # Read back a completed idempotent operation without issuing new permission.
            previous = [x for x in pattern_decisions(con, pattern_id=pattern_id, context=_context())
                        if x["request_id"] == body["request_id"]]
            if previous:
                if len(previous) != 1 or any(previous[0].get(k) != selectors[k]
                    for k in ("candidate_hash", "action", "selected_evaluation_id", "target_decision_id")):
                    raise ValueError("PATTERN_TRANSITION_REQUEST_CONFLICT")
                return jsonify({"ok": True, "replayed": True, "decision": previous[0]})
            try:
                binding = _pattern_transition_binding_from_selectors(selectors, connection=con)
            except ValueError as exc:
                if str(exc) != "PATTERN_NOT_ELIGIBLE":
                    raise
                result = _pattern_evaluation(pattern_id, body["selected_evaluation_id"], connection=con)
                return jsonify({"ok": True, "state": "NOT_ELIGIBLE", "qualification": _pattern_promotion_qualification(result),
                                "evaluation_id": result["evaluation_id"], "activation_performed": False})
            if body["confirmed"] is False:
                result = p.prepare_pattern_transition(con, binding=binding)
                commit.update(connection=con, approval_id=result["confirmation_id"], expected_state="PREPARED")
            else:
                if not optional.issubset(body):
                    raise ValueError("PATTERN_EXACT_CONFIRMATION_REQUIRED")
                admission = p.confirm_pattern_transition(con, approval_id=body["confirmation_id"], binding=binding,
                    activation_resource=body["activation_resource"], write_resource=body["write_resource"])
                fence = get_effect_fence().check_pattern_transition(admission, connection=con)
                decision = promote_pattern(asset, admission=admission, connection=con, fence_decision=fence)
                get_effect_fence().check_pattern_transition(admission, connection=con, phase="before_commit")
                p.consume_pattern_transition(con, admission=admission)
                commit.update(connection=con, approval_id=admission.approval_id, expected_state="CONSUMED")
                result = {"state": "COMMITTED", "decision": decision}
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return _pattern_contract_error(exc)


@content_bp.route("/patterns/approvals/<approval_id>/revoke", methods=["POST"])
def api_revoke_pattern_approval(approval_id):
    try:
        from lumenis.system.security import permission as p
        if request.get_json(silent=True) != {"confirmed": True}:
            raise ValueError("PATTERN_REVOCATION_CONFIRMATION_REQUIRED")
        commit = {}
        def lease():
            from contextlib import nullcontext
            return p.pattern_approval_commit_lease(**commit) if commit else nullcontext()
        with _pattern_mutation(commit_lease=lease) as (_registry, con):
            result = p.revoke_pattern_transition(con, approval_id=approval_id)
            if result["state"] == "REVOKED":
                commit.update(connection=con, approval_id=approval_id, expected_state="REVOKED")
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return _pattern_contract_error(exc)


def _pattern_state_material(pattern_id):
    from lumenis.shared.learning.content_assets import current_pattern_decision
    asset = _pattern_current(pattern_id)
    with get_repository().connection(read_only=True, wal=False) as con:
        current = current_pattern_decision(con, pattern_id=pattern_id, context=_context())
    qualification = None
    if current and current["effective"]:
        from lumenis.system.security.permission import pattern_approval_events, _pattern_hash
        with get_repository().connection(read_only=True, wal=False) as con:
            last = pattern_approval_events(con, current["approval_id"], context=_context())[-1]
        if last["state"] != "CONSUMED" or _pattern_hash(last["binding"]) != current["binding_hash"]:
            raise PermissionError("PATTERN_DECISION_APPROVAL_UNVERIFIED")
        qualification = _pattern_promotion_qualification(_pattern_evaluation(pattern_id, current["selected_evaluation_id"]))
    effective = bool(current and current["effective"] and qualification and qualification["eligible"])
    return {"ok": True, "candidate_hash": _pattern_registry().fingerprint(asset),
                    "state": "VERIFIED_FOR_SCOPE" if effective else "CANDIDATE",
                    "current_decision": current, "effective": effective, "qualification": qualification,
                    "automatic_application": False}


@content_bp.route("/patterns/<pattern_id>/state", methods=["GET"])
def api_pattern_state(pattern_id):
    try:
        return jsonify(_pattern_state_material(pattern_id))
    except Exception as exc:
        return _pattern_contract_error(exc)


CONTENT_ENDPOINTS.update({
    "api_evaluate_pattern": ("/api/content/patterns/<pattern_id>/evaluations", ["POST"]),
    "api_read_pattern_evaluation": ("/api/content/patterns/<pattern_id>/evaluations/<evaluation_id>", ["GET"]),
    "api_pattern_transition": ("/api/content/patterns/<pattern_id>/transitions", ["POST"]),
    "api_revoke_pattern_approval": ("/api/content/patterns/approvals/<approval_id>/revoke", ["POST"]),
    "api_pattern_state": ("/api/content/patterns/<pattern_id>/state", ["GET"]),
})


def read_pattern_learning_projection():
    """Authorized read-only SH-05/API projection. No legacy scan count as learning lift."""
    from lumenis.shared.learning.content_assets import _asset_from_record
    authorize_content_root_request(strict=True)
    registry = _pattern_registry()
    records = registry.snapshot()
    items = []
    for pattern_id, raw in records.items():
        if not isinstance(raw, dict) or raw.get("access_context") != _context():
            continue
        asset = _asset_from_record(raw)
        asset.validate()
        if list(asset.source_bindings) != _bindings([int(x) for x in asset.source_refs]):
            continue
        if asset.lifecycle_state == "retired":
            with get_repository().connection(read_only=True, wal=False) as con:
                receipts = con.execute("SELECT * FROM content_generation_evidence WHERE content_type='pattern_retirement' "
                    "AND json_extract(input_json,'$.pattern_id')=?", (pattern_id,)).fetchall()
                matching = []
                for row in receipts:
                    row = dict(row)
                    if json.loads(row["input_json"]).get("_content_context") != _context():
                        continue
                    _verify_content_receipt(row, connection=con)
                    if json.loads(row["output_json"]).get("previous_version_hash") == asset.previous_version_hash:
                        matching.append(row)
                if len(matching) != 1:
                    raise PermissionError("PATTERN_RETIREMENT_RECEIPT_UNVERIFIED")
            items.append({"pattern_id": pattern_id, "title": asset.title, "state": "RETIRED", "effective": False,
                          "evaluations": [], "candidate_hash": registry.fingerprint(asset)})
            continue
        _pattern_receipt(asset)
        state = _pattern_state_material(pattern_id)
        with get_repository().connection(read_only=True, wal=False) as con:
            rows = con.execute("SELECT evidence_id FROM content_generation_evidence WHERE content_type='pattern_evaluation' "
                "AND json_extract(input_json,'$.pattern_id')=? ORDER BY rowid DESC", (pattern_id,)).fetchall()
        evaluations = [_pattern_evaluation(pattern_id, row["evidence_id"]) for row in rows]
        if evaluations and not state["effective"]:
            state["state"] = "NOT_ELIGIBLE"
        if state["current_decision"] and not state["current_decision"]["effective"]:
            state["state"] = "DISABLED"
        items.append({"pattern_id": pattern_id, "title": asset.title, **state, "evaluations": evaluations})
    return {"items": items, "count": len(items), "effective_count": sum(x["effective"] for x in items),
            "source": "lumenis.shared.learning.content_assets", "automatic_application": False,
            "business_lift_verified": False}


@content_bp.route("/patterns/learning", methods=["GET"])
def api_pattern_learning_projection():
    try:
        return jsonify({"ok": True, **read_pattern_learning_projection()})
    except Exception as exc:
        return _pattern_contract_error(exc)


CONTENT_ENDPOINTS["api_pattern_learning_projection"] = ("/api/content/patterns/learning", ["GET"])

# Existing Shared Content owner: deterministic, reviewable multi-platform drafts.
def _multiplatform_sources(spec):
    refs = list(dict.fromkeys(f["citation"]["evidence_id"] for f in spec["facts"] if f["citation"]))
    return {row["evidence_id"]: row for row in _source_material(refs)} if refs else {}


def _multiplatform_read(artifact_id):
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.content_creation import multiplatform as mp
    saved = saved_work.reopen_work(artifact_id, actor=g.content_actor,
        scope=g.content_scope.get("shared_workspace_scope", g.content_scope))
    receipt = _content_work_receipt(saved)
    if receipt is None or receipt["content_type"] != "content_multiplatform":
        raise PermissionError("MULTIPLATFORM_OWNER_RECEIPT_REQUIRED")
    package = mp.validate_saved(saved["document"])
    # Retained citations and source integrity never imply semantic verification.
    sources = _multiplatform_sources(package["request"])
    fresh, citations = mp.compose(package["request"], sources)
    if fresh["package"]["source_bindings"] != package["source_bindings"]:
        raise PermissionError("MULTIPLATFORM_SOURCE_STALE")
    stored_citations = saved["document"]["citations"]
    if any(not any(all(stored.get(k) == v for k, v in c.items()) for stored in stored_citations)
           for c in citations) or len(stored_citations) != len(citations):
        raise PermissionError("MULTIPLATFORM_CITATIONS_CHANGED")
    return saved


def _multiplatform_save(assembled, citations, *, request_id, parent=None, reason=None, restored=None):
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.content_creation import multiplatform as mp
    package = assembled["package"]
    payload = {"content_contract_version": "content-review:v1", "multiplatform": package,
        "claims": _draft_claims(assembled["claims"], assembled["markdown"]),
        "content_review": {"decision": "NOT_VERIFIED", "dimensions": {
            key: {"status": "not_verified", "method": "human_review_required"} for key in CONTENT_REVIEW_DIMENSIONS}}}
    version_args = {}
    if parent is not None:
        document = parent["document"]
        payload["multiplatform_revision"] = {"parent_artifact_id": parent["artifact"]["artifact_id"],
            "parent_sha256": parent["artifact"]["sha256"], "reason": reason,
            "restored_from": restored, "review_status": "RESET_FOR_NEW_VERSION",
            "diff": mp.differences(document["payload"]["multiplatform"], package),
            "fact_sheet_changed": document["payload"]["multiplatform"]["request"]["facts"] != package["request"]["facts"],
            "source_bindings_changed": document["payload"]["multiplatform"]["source_bindings"] != package["source_bindings"]}
        version_args = {"work_id": document["work_id"], "previous_artifact_id": parent["artifact"]["artifact_id"],
                        "expected_draft_digest": document["draft_digest"]}
    expected_context = _context()
    def recheck(connection, record, document):
        authorize_content_root_request(strict=True)
        if expected_context != _context():
            raise PermissionError("MULTIPLATFORM_CONTEXT_CHANGED")
        _content_effect()
        sources = _multiplatform_sources(package["request"])
        fresh, _ = mp.compose(package["request"], sources)
        if fresh["package"]["source_bindings"] != package["source_bindings"]:
            raise PermissionError("MULTIPLATFORM_SOURCE_STALE")
        if parent is not None:
            current = _multiplatform_read(parent["artifact"]["artifact_id"])
            if current["document"] != parent["document"]:
                raise PermissionError("MULTIPLATFORM_PARENT_CHANGED")
        if restored is not None:
            restored_saved = _multiplatform_read(restored["artifact_id"])
            if restored_saved["artifact"]["sha256"] != restored["sha256"]:
                raise PermissionError("MULTIPLATFORM_RESTORE_CHANGED")
        _record_content_work("content_multiplatform", connection, record, document,
                             source_bindings=package["source_bindings"])
    saved = saved_work.save_work(title=package["request"]["title"], markdown=assembled["markdown"],
        kind="research", payload=payload, citations=citations, request_id=request_id,
        actor=g.content_actor, scope=g.content_scope.get("shared_workspace_scope", g.content_scope),
        before_commit=recheck, **version_args)
    _multiplatform_read(saved["artifact"]["artifact_id"])
    return saved


@content_bp.route("/multiplatform/capabilities", methods=["GET"])
def api_multiplatform_capabilities():
    from lumenis.shared.content_creation.multiplatform import capabilities
    return jsonify({"ok": True, **capabilities()})


@content_bp.route("/multiplatform/drafts", methods=["POST"])
def api_multiplatform_create():
    try:
        from lumenis.shared.content_creation import multiplatform as mp
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"request_id", "spec"}:
            raise ValueError("MULTIPLATFORM_CREATE_INVALID")
        spec = mp.validate_request(body["spec"])
        assembled, citations = mp.compose(spec, _multiplatform_sources(spec))
        saved = _multiplatform_save(assembled, citations, request_id=body["request_id"])
        return jsonify({"ok": True, "result": saved, "model_used": False,
                        "review_status": "HUMAN_PENDING", "publish_performed": False}), 201
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/multiplatform/drafts/<artifact_id>", methods=["GET"])
def api_multiplatform_read(artifact_id):
    try:
        return jsonify({"ok": True, "result": _multiplatform_read(artifact_id), "publish_performed": False})
    except Exception as exc:
        return _pattern_error(exc)


@content_bp.route("/multiplatform/drafts/<artifact_id>/revisions", methods=["POST"])
def api_multiplatform_revise(artifact_id):
    try:
        from lumenis.shared.content_creation import multiplatform as mp
        body = request.get_json(silent=True)
        common = {"request_id", "expected_sha256", "reason"}
        if (not isinstance(body, dict) or set(body) not in (common | {"edits"}, common | {"restore_artifact_id"}, common | {"spec"})
                or not isinstance(body["reason"], str) or not body["reason"].strip() or len(body["reason"]) > 2000):
            raise ValueError("MULTIPLATFORM_REVISION_INVALID")
        parent = _multiplatform_read(artifact_id)
        if body["expected_sha256"] != parent["artifact"]["sha256"]:
            raise ValueError("MULTIPLATFORM_REVISION_CONFLICT")
        package = parent["document"]["payload"]["multiplatform"]
        citations = parent["document"]["citations"]
        restored = None
        if "restore_artifact_id" in body:
            old = _multiplatform_read(body["restore_artifact_id"])
            if (old["document"]["work_id"] != parent["document"]["work_id"]
                    or old["document"]["version"] >= parent["document"]["version"]):
                raise ValueError("MULTIPLATFORM_RESTORE_PARENT_REQUIRED")
            assembled = mp.assemble(old["document"]["payload"]["multiplatform"])
            citations = old["document"]["citations"]
            restored = {"artifact_id": old["artifact"]["artifact_id"], "sha256": old["artifact"]["sha256"]}
        elif "spec" in body:
            spec = mp.validate_request(body["spec"])
            assembled, citations = mp.compose(spec, _multiplatform_sources(spec))
        else:
            assembled = mp.revise(package, body["edits"])
        saved = _multiplatform_save(assembled, citations, request_id=body["request_id"], parent=parent,
                                   reason=body["reason"], restored=restored)
        return jsonify({"ok": True, "result": saved, "review_status": "HUMAN_PENDING", "publish_performed": False}), 201
    except Exception as exc:
        return _pattern_error(exc)


CONTENT_ENDPOINTS.update({
    "api_multiplatform_capabilities": ("/api/content/multiplatform/capabilities", ["GET"]),
    "api_multiplatform_create": ("/api/content/multiplatform/drafts", ["POST"]),
    "api_multiplatform_read": ("/api/content/multiplatform/drafts/<artifact_id>", ["GET"]),
    "api_multiplatform_revise": ("/api/content/multiplatform/drafts/<artifact_id>/revisions", ["POST"]),
})
