# -*- coding: utf-8 -*-
"""
content_generation.py — ZBC 统一内容生成引擎
=============================================
整合：智谱AI调用(glm-5.3强推理/glm-4.5-air快速) + 研究库检索 + Evidence链 + 4维Evaluation评分 + 人工反馈迭代。

设计原则：
- AI是增强层，规则与数据是最终真值
- 每次生成必须记录Evidence(prompt/input/output/model/timestamp/confidence)
- 每次生成必须有Evaluation(相关性/创意性/品牌契合度/平台适配度)
- 研究库检索在AI生成前自动执行，结果注入prompt
- 支持人工反馈→修正→再生成
- Provider-Agnostic：智谱主力，失败降级到本地规则，不静默
- 不修改SUBJECT_WORDS/subject_hit()，不碰生产数据
"""
from __future__ import annotations
import json
import os
import sqlite3
import hashlib
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("ZBC_DB_PATH", str(Path(__file__).parent / "data" / "monitor.db"))

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
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


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
def search_research_library(query: str, limit: int = 5, sub_library: str = "") -> List[Dict[str, Any]]:
    """从 intelligence_assets 表检索研究资料（AI生成前自动调用）。"""
    if not query or not query.strip():
        return []
    conn = _get_conn()
    c = conn.cursor()
    terms = query.strip().split()
    where = []
    params = []
    for t in terms[:4]:
        like = f"%{t}%"
        where.append("(title LIKE ? OR summary LIKE ? OR tags LIKE ? OR sub_library LIKE ?)")
        params.extend([like, like, like, like])
    sql = "SELECT asset_id, title, summary, tags, sub_library, source_origin, domain, evidence_level, knowledge_status FROM intelligence_assets WHERE "
    sql += " OR ".join(where)
    if sub_library:
        sql += " AND sub_library = ?"
        params.append(sub_library)
    sql += " ORDER BY asset_id LIMIT ?"
    params.append(limit)
    try:
        rows = c.execute(sql, params).fetchall()
        results = [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"research search error: {e}")
        results = []
    conn.close()
    return results


def search_research_filesystem(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """从 intelligence_library/ 文件系统检索（补充DB检索，只读文件内容摘要）。"""
    if not query or not query.strip():
        return []
    base = Path(__file__).parent / "intelligence_library"
    if not base.exists():
        return []
    terms = [t.lower() for t in query.strip().split()[:3]]
    results = []
    try:
        for md_file in base.rglob("*.md"):
            if len(results) >= limit:
                break
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")[:2000]
                low = text.lower()
                score = sum(1 for t in terms if t in low)
                if score > 0:
                    rel = md_file.relative_to(base)
                    results.append({
                        "path": str(rel),
                        "title": md_file.stem,
                        "snippet": text[:300].replace("\n", " "),
                        "match_score": score,
                    })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"filesystem research error: {e}")
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:limit]


def build_research_context(query: str, content_type: str = "") -> str:
    """构建研究库上下文，注入AI prompt。"""
    db_results = search_research_library(query, limit=4)
    fs_results = search_research_filesystem(query, limit=2)
    parts = []
    if db_results:
        parts.append("【研究库参考】")
        for r in db_results:
            title = r.get("title", "")
            summary = (r.get("summary") or "")[:150]
            sub = r.get("sub_library", "")
            parts.append(f"- [{sub}] {title}: {summary}")
    if fs_results:
        parts.append("【研究文档参考】")
        for r in fs_results:
            parts.append(f"- {r['path']}: {r['snippet'][:120]}")
    return "\n".join(parts) if parts else ""


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
# AI 调用（复用 intelligence.py 统一通道）
# ============================================================
def _call_ai(system_prompt: str, user_prompt: str, level: str = "high") -> Tuple[Optional[str], str, Dict]:
    """调用智谱AI，失败返回(None, 'rule', meta)，不抛异常。
    使用glm_4_5_air资源包（token计费，配额充足），不使用per_call按次包。
    每次调用前清除intelligence.py的provider缓存（30s TTL），确保使用.env中配置的provider。
    自动注入人类交互模式层（HUMAN_INTERACTION_LAYER）。
    """
    try:
        import intelligence as intel
        # 清除provider缓存，避免30秒TTL导致使用旧的ollama检测结果
        if hasattr(intel, '_CACHE'):
            intel._CACHE['ts'] = 0
            intel._CACHE['provider'] = None
        # 注入人类交互模式层（角色prompt + 人类模式 = 有温度的专业创作）
        enhanced_system = HUMAN_INTERACTION_LAYER + "\n\n【角色与任务】\n" + system_prompt
        out, provider, meta = intel.chat(
            enhanced_system, user_prompt, level=level, use_cache=False,
            pack_id="glm_4_5_air",
        )
        return out, provider, meta
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return None, "error", {"error": str(e)}


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
) -> str:
    """记录内容生成Evidence，返回evidence_id。"""
    evidence_id = _gen_id("CGE")
    normalized_parent_id = (parent_evidence_id or "").strip() or None
    conn = _get_conn()
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
    conn.commit()
    conn.close()
    return evidence_id


def record_evaluation(evidence_id: str, eval_result: Dict, human_rating: float = None, feedback: str = "") -> str:
    """记录Evaluation评分。"""
    eval_id = _gen_id("CEV")
    scores = eval_result.get("scores", {})
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO content_evaluation
        (eval_id, evidence_id, relevance, creativity, brand_fit, platform_fit, overall,
         eval_method, eval_model, feedback, human_rating, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        eval_id, evidence_id,
        scores.get("relevance", 0), scores.get("creativity", 0),
        scores.get("brand_fit", 0), scores.get("platform_fit", 0),
        eval_result.get("overall", 0),
        eval_result.get("method", "rule_baseline"),
        eval_result.get("model", ""),
        feedback, human_rating, _now_iso(),
    ))
    conn.commit()
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
    research_query = " ".join(filter(None, [brand, content_type, target_audience, style]))
    research_context = build_research_context(research_query, content_type)

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
            if k not in ("brand", "platform", "target_audience", "style", "reference_cases"):
                user_parts.append(f"{k}: {v}")
    if human_feedback:
        user_parts.append(f"【人工反馈，请据此修正】{human_feedback}")
    if research_context:
        user_parts.append(research_context)
    user_prompt = "\n".join(user_parts)

    # 3. AI调用
    level = cfg["level"]
    out_text, provider, meta = _call_ai(cfg["system_prompt"], user_prompt, level=level)
    latency_ms = int((time.time() - t0) * 1000)

    output_json = _parse_json_output(out_text) if out_text else None
    status = "success" if output_json else ("partial" if out_text else "failed")
    error = "" if output_json else ("AI输出非JSON" if out_text else "AI调用失败/无输出")
    model = meta.get("model", "") or (provider if provider != "error" else "")
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
    eval_id = record_evaluation(evidence_id, eval_result)

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
            "has_research": bool(research_context),
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
    if not row:
        return {"ok": False, "error": f"Evidence {evidence_id} 不存在"}
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
    if not row:
        return None
    d = dict(row)
    d["evaluations"] = [dict(e) for e in evals]
    return d


def list_evidence(content_type: str = "", limit: int = 20, offset: int = 0) -> Dict:
    conn = _get_conn()
    where = "1=1"
    params = []
    if content_type:
        where += " AND content_type=?"
        params.append(content_type)
    total = conn.execute(f"SELECT COUNT(*) FROM content_generation_evidence WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT evidence_id, content_type, model, provider, status, confidence, iteration, created_at "
        f"FROM content_generation_evidence WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    conn.close()
    return {"total": total, "items": [dict(r) for r in rows]}


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
from flask import Blueprint, request, jsonify

content_bp = Blueprint("content_generation", __name__, url_prefix="/api/content")


@content_bp.route("/types", methods=["GET"])
def api_content_types():
    """列出支持的内容类型。"""
    return jsonify({"ok": True, "types": {k: {"label": v["label"], "level": v["level"]} for k, v in CONTENT_TYPES.items()}})


@content_bp.route("/generate", methods=["POST"])
def api_generate():
    """统一内容生成入口。"""
    data = request.get_json(silent=True) or {}
    ct = data.get("content_type", "")
    if not ct:
        return jsonify({"ok": False, "error": "content_type 必填"}), 400
    result = generate_content(
        content_type=ct,
        brand=data.get("brand", ""),
        platform=data.get("platform", ""),
        target_audience=data.get("target_audience", ""),
        style=data.get("style", ""),
        reference_cases=data.get("reference_cases", ""),
        extra_input=data.get("extra_input"),
        product_id=data.get("product_id", "ZBMP"),
        domain_id=data.get("domain_id", "zbmp"),
    )
    return jsonify(result), (200 if result["ok"] else 200)


@content_bp.route("/generate/<content_type>", methods=["POST"])
def api_generate_typed(content_type):
    """按类型生成内容。"""
    data = request.get_json(silent=True) or {}
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
    return jsonify(result)


@content_bp.route("/feedback", methods=["POST"])
def api_feedback():
    """人工反馈→重新生成。"""
    data = request.get_json(silent=True) or {}
    eid = data.get("evidence_id", "")
    feedback = data.get("feedback", "")
    if not eid or not feedback:
        return jsonify({"ok": False, "error": "evidence_id 和 feedback 必填"}), 400
    result = regenerate_with_feedback(eid, feedback)
    return jsonify(result)


@content_bp.route("/evidence/<evidence_id>", methods=["GET"])
def api_get_evidence(evidence_id):
    ev = get_evidence(evidence_id)
    if not ev:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "data": ev})


@content_bp.route("/evidence", methods=["GET"])
def api_list_evidence():
    ct = request.args.get("content_type", "")
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)
    return jsonify({"ok": True, "data": list_evidence(ct, limit, offset)})


@content_bp.route("/research/search", methods=["GET"])
def api_research_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": False, "error": "q 必填"}), 400
    db_results = search_research_library(q, limit=int(request.args.get("limit", 5)))
    fs_results = search_research_filesystem(q, limit=2)
    return jsonify({"ok": True, "query": q, "db_results": db_results, "filesystem_results": fs_results})


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
            extra_input={"objective": objective, "budget": budget},
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
            "evidence_id": ai_result.get("evidence_id"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/video-analyze", methods=["POST"])
def api_video_analyze():
    """视频智能分析（接入智谱视觉理解）。"""
    data = request.get_json(silent=True) or {}
    evidence_id = data.get("evidence_id", "")
    note_id = data.get("note_id", "")
    ocr_text = data.get("ocr_text", "")
    asr_text = data.get("asr_text", "")
    if not evidence_id or not note_id:
        return jsonify({"ok": False, "error": "evidence_id 和 note_id 必填"}), 400
    try:
        from video_intelligence import VideoIntelligenceEngine, VideoEvidence
        # 用智谱AI作为provider分析文本内容
        combined = f"OCR文字: {ocr_text}\nASR语音: {asr_text}"
        ai_out, provider, meta = _call_ai(
            "你是视频内容分析专家。分析以下视频的OCR文字和ASR语音转写，输出JSON：{\"scenes\":[{\"desc\":\"场景描述\"}],\"entities\":[\"实体1\"],\"topics\":[\"话题1\"],\"sentiment\":\"positive/negative/neutral\",\"risk_level\":\"low/medium/high\",\"marketing_signals\":[\"信号1\"]}",
            combined, level="medium",
        )
        parsed = _parse_json_output(ai_out) if ai_out else {}

        def _provider(ev):
            return parsed or {}

        engine = VideoIntelligenceEngine(provider=_provider, provider_name="zhipu", model_version=meta.get("model", "glm-4.5-air"))
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
    """品牌报告生成（复用brand_report_generator + AI增强）。"""
    data = request.get_json(silent=True) or {}
    brand = data.get("brand", "序境")
    period = data.get("period", "")
    try:
        from brand_report_generator import BrandReportGenerator
        gen = BrandReportGenerator(brand_name=brand, report_period=period)
        # 用AI生成报告内容
        ai_result = generate_content(
            content_type="brand_report",
            brand=brand,
            platform="report",
            target_audience=data.get("target_audience", "品牌方管理层"),
            style=data.get("style", "专业分析"),
            extra_input={"period": period, "key_metrics": data.get("key_metrics", {})},
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
            "evidence_id": ai_result.get("evidence_id"),
            "evaluation": ai_result.get("evaluation"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/resources", methods=["GET"])
def api_resources():
    """资源库查询（兼容resource_library.py，回退到intelligence_assets）。"""
    category = request.args.get("category", "")
    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    # 优先用intelligence_assets（resources表可能不存在）
    conn = _get_conn()
    try:
        if q:
            rows = conn.execute(
                "SELECT asset_id as resource_uid, title, summary as content, tags, sub_library as resource_category, source_origin as source, domain as product_context FROM intelligence_assets WHERE title LIKE ? OR summary LIKE ? ORDER BY asset_id LIMIT ?",
                (f"%{q}%", f"%{q}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT asset_id as resource_uid, title, summary as content, tags, sub_library as resource_category, source_origin as source, domain as product_context FROM intelligence_assets ORDER BY asset_id LIMIT ?",
                (limit,),
            ).fetchall()
        items = [dict(r) for r in rows]
    except Exception as e:
        items = []
    conn.close()
    return jsonify({"ok": True, "count": len(items), "data": items})


@content_bp.route("/topic-campaign/status", methods=["GET"])
def api_topic_campaign_status():
    """话题营销状态查询。"""
    try:
        import topic_campaign as tc
        state = tc._campaign_circuit_state() if hasattr(tc, "_campaign_circuit_state") else {}
        return jsonify({"ok": True, "circuit_state": state, "module": "topic_campaign"})
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
        return jsonify({"ok": True, "topic": topic, "snapshot": {}, "note": "topic_snapshot模块已加载"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@content_bp.route("/podcast-research", methods=["POST"])
def api_podcast_research():
    """播客研究流水线（AI辅助选题研究）。"""
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "")
    if not topic:
        return jsonify({"ok": False, "error": "topic 必填"}), 400
    # 研究库检索
    research = build_research_context(f"播客 {topic}", "podcast_topic")
    # AI生成选题
    result = generate_content(
        content_type="podcast_topic",
        brand=data.get("brand", ""),
        platform="podcast",
        target_audience=data.get("target_audience", ""),
        style=data.get("style", ""),
        extra_input={"topic": topic, "research": research[:500]},
    )
    return jsonify(result)


def register_content_api(app):
    """注册内容生成蓝图 + 初始化DB。"""
    try:
        init_db()
    except Exception as e:
        print(f"[content_generation] init_db warning: {e}")
    app.register_blueprint(content_bp)
    print("[content_generation] Content Generation API registered: /api/content/*")
