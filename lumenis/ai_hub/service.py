# -*- coding: utf-8 -*-
"""AI Hub 服务层：统一对话 / 任意模块分析 / 学习记录。

三级能力来源（与主系统口径一致，外部 AI 永远不是必需项）：
  1) 本机模型（Ollama / LM Studio / llama.cpp，自动发现）
  2) 已配置 Key 的云端模型（智谱 / 千问 / DeepSeek / 豆包Ark / OpenAI）
  3) 内置可审计规则引擎（永远在线，保证核心脱离 AI 也能跑）
对话前先用 function_registry 取系统内真实数据作为上下文，AI 只可据此回答，不补造事实。
"""
from __future__ import annotations
import os, sys, json, time, threading, logging
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import intelligence          # 主系统本地智能层（三级回退）
import function_registry as freg
from ..config import DB_PATH

logger = logging.getLogger(__name__)
_db = None
_learn_lock = threading.Lock()
LEARN_LOG = os.path.join(os.path.dirname(DB_PATH), "ai_learning_log.jsonl")

SYSTEM_ROLE = (
    "你是 Zachary，CTH-POMS（CorTech Lab·广州太古汇舆情监控系统）的内置智能助手，"
    "服务于内部品牌舆情团队。回答要求：\n"
    "1. 只依据“系统内可核对数据”和用户给出的内容作答，数据不足就明确说不足，绝不编造数字、来源或事实；\n"
    "2. 单一用户/单一来源的指控一律表述为“待证实”，不得写成已确认事实；\n"
    "3. 结论优先、结构清晰，必要时分点；涉及风险给出可执行的下一步；\n"
    "4. 你可以分析系统内任意模块（采集、事件、笔记、话题、案例库、报告、账号、风控），"
    "但你只能提出建议，涉及写库/变更的动作会进入“影子队列”由人工确认，你不能直接改动客户数据；\n"
    "5. 使用与用户相同的语言，简洁专业。"
)

MODULE_HINTS = {
    "collect": "采集中心：各平台采集任务、六态健康、动态风控、登录恢复。",
    "notes": "笔记库：各平台原始笔记、情感、风险、正文与发布时间。",
    "events": "事件中心：事件聚类、传播、影响、处置建议。",
    "topics": "话题：热门话题、专题（如广州太古汇15周年）。",
    "cases": "品牌营销案例库：历史公关/营销案例与应对公式。",
    "report": "报告中心：日报/周报、导出。",
    "account": "账号与权限：三级角色、安全问答、登录态。",
    "risk": "动态风控：健康/轻度/中度/需验证/IP风险/恢复 六态。",
}


def _get_db():
    """惰性获取主系统 database 模块（失败不致命，检索退化为纯功能/案例匹配）。"""
    global _db
    if _db is None:
        import database as _dbmod
        _db = _dbmod
    return _db


def status():
    """当前 AI 运行态：provider/model/runtime + 规则保底是否在线。"""
    st = intelligence.ai_status()
    st["rule_fallback"] = True
    st["ok"] = True
    return st


def retrieve(question: str, limit: int = 8) -> dict:
    """用问题检索系统内真实数据（功能/品牌/官网/案例/笔记/事件）。"""
    try:
        return freg.search_targets(question or "", _get_db(), limit)
    except Exception as e:
        logger.warning("retrieve with db failed: %s", e)
        try:
            return freg.search_targets(question or "", None, limit)
        except Exception as e2:
            logger.warning("retrieve fallback failed: %s", e2)
            return {"functions": [], "brands": [], "websites": [], "cases": [],
                    "notes": [], "events": [], "meta": {}}


def _context_text(question: str) -> str:
    try:
        return freg.build_context(question, _get_db())
    except Exception:
        try:
            return freg.build_context(question, None)
        except Exception:
            return "未检索到与问题直接对应的结构化记录。"


def _rule_reply(question: str, hits: dict) -> str:
    """无任何模型可用时的可审计规则答复：如实汇报系统内命中，不伪装成 AI 生成。"""
    lines = ["（当前未连接本地/云端模型，以下由内置规则引擎依据系统内数据给出，不做主观推断）"]
    funcs = hits.get("functions", [])
    if funcs:
        lines.append("· 对应模块：" + "、".join(f"{f['label']}" for f in funcs[:4]))
    for key, label in (("brands", "匹配品牌"), ("cases", "相关案例"),
                       ("notes", "相关笔记"), ("events", "相关事件")):
        items = hits.get(key, [])
        if items:
            if key in ("brands",):
                names = [str(x.get("brand_cn") or x.get("brand_en", "")) for x in items[:5]]
            elif key == "cases":
                names = [f"{x.get('id','')} {x.get('title','')}" for x in items[:5]]
            elif key == "events":
                names = [str(x.get("title", "")) for x in items[:5]]
            else:
                names = [str(x.get("title") or x.get("summary") or "")[:40] for x in items[:5]]
            names = [n for n in names if n]
            if names:
                lines.append(f"· {label}（{len(items)}）：" + "；".join(names))
    if len(lines) == 1:
        lines.append("系统内暂未检索到与该问题直接对应的记录，可换个关键词，或先在采集中心采集相关数据。")
    lines.append("启动本地 Ollama/LM Studio 或在设置配置任一云端 Key 后，我可给出更深入的分析。")
    return "\n".join(lines)


def chat(question: str, history=None, scope: str = "all") -> dict:
    """统一对话：检索真实数据 → 模型生成 → 规则兜底。返回可序列化 dict。"""
    t0 = time.time()
    question = (question or "").strip()
    if not question:
        return {"ok": False, "error": "问题不能为空"}
    hits = retrieve(question)
    context = _context_text(question)
    hint = MODULE_HINTS.get(scope, "")
    has_real_data = any(hits.get(k) for k in ("notes", "events", "cases", "brands", "websites"))
    sys_prompt = SYSTEM_ROLE
    if hint:
        sys_prompt += "\n当前聚焦模块：" + hint
    sys_prompt += "\n\n== 系统内可核对的真实数据（仅可据此回答） ==\n" + context
    if not has_real_data:
        sys_prompt += (
            "\n\n【硬性约束】本次检索未命中任何笔记/事件/案例/品牌等真实业务数据。"
            "禁止给出任何具体数字、百分比、环比、排名或‘下降/增长多少’之类无来源结论；"
            "请如实说明系统内当前没有对应数据，并指出应到哪个模块采集或查看，不要替系统编造现状。")
    else:
        sys_prompt += "\n\n【约束】只引用上面给出的真实数据，未提供的数字一律不要编造。"

    raw, provider = intelligence._chat(sys_prompt, question, 0.2, 1000)
    used_rule = False
    if not raw:
        raw = _rule_reply(question, hits)
        provider = "rule"
        used_rule = True

    targets = [{"id": f.get("id"), "label": f.get("label"), "page": f.get("page")}
               for f in hits.get("functions", [])[:5]]
    st = status()
    record_learning("chat", {"q": question[:120], "provider": provider, "scope": scope})
    return {
        "ok": True, "reply": (raw or "").strip(), "provider": provider,
        "model": st.get("model", ""), "runtime": st.get("runtime", "rule"),
        "used_rule_fallback": used_rule, "targets": targets,
        "matched": {"brands": len(hits.get("brands", [])), "cases": len(hits.get("cases", [])),
                    "notes": len(hits.get("notes", [])), "events": len(hits.get("events", []))},
        "elapsed_seconds": round(time.time() - t0, 2),
    }


def analyze_module(module: str, text: str, meta=None) -> dict:
    """对系统内任意模块的一段内容做结构化分析（摘要/情感/风险/建议）。模型不可用则规则保底。"""
    t0 = time.time()
    module = (module or "").strip() or "notes"
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "待分析内容为空"}
    meta = meta or {}
    sys_prompt = (
        SYSTEM_ROLE
        + f"\n当前分析模块：{module}。{MODULE_HINTS.get(module,'')}"
        + "\n只输出严格 JSON：{\"summary\":\"不超过60字摘要\",\"sentiment\":\"positive/neutral/negative\","
        "\"risk_level\":\"high/medium/low\",\"risk_points\":[\"风险点\"],\"suggestion\":\"不超过80字下一步建议\"}。"
        "单一来源指控保持待证实，不要夸大。"
    )
    user = f"模块附加信息：{json.dumps(meta, ensure_ascii=False)[:800]}\n待分析内容：\n{text[:6000]}"
    raw, provider = intelligence._chat(sys_prompt, user, 0.0, 800)
    data = None
    if raw:
        data = intelligence._json_from_text(raw)
    if not data:
        # 规则保底：主系统本地规则分析器
        try:
            import ai_analyzer
            base = ai_analyzer.analyze_note(
                {"title": text[:120], "content": text, "likes": 0, "comments": 0},
                provider="rule",
            )
            data = {
                "summary": (base.get("summary") or "")[:60] or "规则引擎已完成基础判定，建议接入模型获得更细分析。",
                "sentiment": base.get("sentiment", "neutral"),
                "risk_level": base.get("risk_level", "low"),
                "risk_points": base.get("sentiment_reasons", [])[:3],
                "suggestion": "按既有审核流程核查原始来源后再定级。",
            }
            provider = "rule"
        except Exception:
            data = {"summary": "模型与规则分析均不可用。", "sentiment": "neutral",
                    "risk_level": "low", "risk_points": [], "suggestion": "稍后重试或检查本地AI。"}
            provider = "rule"
    data["provider"] = provider
    data["module"] = module
    data["elapsed_seconds"] = round(time.time() - t0, 2)
    data["ok"] = True
    record_learning("analyze", {"module": module, "provider": provider,
                                "len": len(text)})
    return data


def record_learning(kind: str, payload: dict) -> None:
    """系统学习记录：每次 AI 被调用都留痕，供“系统学习模块”回看能力演进（追加写，失败静默）。"""
    try:
        os.makedirs(os.path.dirname(LEARN_LOG), exist_ok=True)
        row = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, **(payload or {})}
        with _learn_lock, open(LEARN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("record_learning failed: %s", e)


def learning_stats(limit: int = 50) -> dict:
    """学习记录统计与最近记录。"""
    rows = []
    total = 0
    by_provider, by_kind = {}, {}
    try:
        with open(LEARN_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                by_kind[r.get("kind", "?")] = by_kind.get(r.get("kind", "?"), 0) + 1
                by_provider[r.get("provider", "?")] = by_provider.get(r.get("provider", "?"), 0) + 1
                rows.append(r)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("learning_stats failed: %s", e)
    return {"total": total, "by_kind": by_kind, "by_provider": by_provider,
            "recent": rows[-limit:][::-1]}
