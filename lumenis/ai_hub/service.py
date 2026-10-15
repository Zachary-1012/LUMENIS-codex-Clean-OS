# -*- coding: utf-8 -*-
"""AI Hub compatibility service routed through the single SYSTEM AI Gateway.

It retrieves product context and asks the owned runtime for analysis. It does
not discover provider APIs or turn rule output into completed AI work.
"""
from __future__ import annotations
import os, sys, json, time, threading, logging
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lumenis.system.ai_gateway import core as intelligence  # canonical SYSTEM AI Gateway
import function_registry as freg
from ..config import DB_PATH

logger = logging.getLogger(__name__)
_db = None
_learn_lock = threading.Lock()
LEARN_LOG = os.path.join(os.path.dirname(DB_PATH), "ai_learning_log.jsonl")

SYSTEM_ROLE = (
    "你是序境 LUMENIS 的业务助手，服务于 CTH 与 BMP 工作流。回答要求：\n"
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
    """Report the selected Gateway route without discovery or inference calls."""
    from lumenis.system.ai_gateway import user_api_adapter
    if user_api_adapter.is_selected():
        return {**user_api_adapter.status(), "enabled": user_api_adapter.is_configured(),
                "rule_fallback": False, "ok": True}
    try:
        runtime = intelligence.owned_inference_status()
    except Exception:
        runtime = None
    if not isinstance(runtime, dict):
        runtime = {
            "provider": "owned", "available": False,
            "service_binding": "NOT_BOUND", "state": "UNAVAILABLE",
            "reason": "OWNED_RUNTIME_STATUS_UNAVAILABLE",
        }
    return {
        **runtime,
        "provider": "owned",
        "enabled": runtime.get("available") is True and runtime.get("service_binding") == "BOUND",
        "rule_fallback": False,
        "fallback_allowed": False,
        "ok": True,
    }


def retrieve(question: str, limit: int = 8, *, source_scope=None) -> dict:
    """Search public reference material and only scope-authorized business sources."""
    try:
        return freg.search_targets(question or "", _get_db(), limit, scope=source_scope)
    except Exception as e:
        logger.warning("retrieve with db failed: %s", e)
        try:
            return freg.search_targets(question or "", None, limit, scope=source_scope)
        except Exception as e2:
            logger.warning("retrieve fallback failed: %s", e2)
            return {"functions": [], "brands": [], "websites": [], "cases": [],
                    "notes": [], "events": [], "meta": {}}


def _context_text(question: str, *, source_scope=None) -> str:
    try:
        return freg.build_context(question, _get_db(), scope=source_scope)
    except Exception:
        try:
            return freg.build_context(question, None, scope=source_scope)
        except Exception:
            return "未检索到与问题直接对应的结构化记录。"


def _owned_result_text(result):
    analysis = result.get("analysis") if isinstance(result, dict) else None
    if isinstance(analysis, str) and analysis.strip():
        return analysis.strip()
    if isinstance(analysis, dict):
        for key in ("reply", "summary", "text", "content"):
            value = analysis.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _run_owned(text, analysis_type):
    try:
        result = intelligence.run_owned_analysis(text=text, analysis_type=analysis_type)
    except Exception:
        return {
            "ok": False, "status": "ERROR", "code": "OWNED_ANALYSIS_EXECUTION_FAILED",
            "provider": "owned", "analysis": None,
        }
    if not isinstance(result, dict):
        return {
            "ok": False, "status": "ERROR", "code": "OWNED_ANALYSIS_RESULT_INVALID",
            "provider": "owned", "analysis": None,
        }
    return result


def _completed(result):
    return (
        isinstance(result, dict) and result.get("ok") is True
        and result.get("status") == "COMPLETED" and result.get("provider") == "owned"
        and _owned_result_text(result) is not None
    )


def chat(question: str, history=None, scope: str = "all", *, source_scope=None) -> dict:
    """Chat through the explicitly selected Gateway, without business data export."""
    t0 = time.time()
    question = (question or "").strip()
    if not question:
        return {"ok": False, "status": "INVALID_INPUT", "code": "MESSAGE_REQUIRED"}
    # This compatibility chat operation has no typed SourceUse request. Do
    # not call retrieve/build_context here: those helpers may load business
    # directories and case material. Route hints come only from static
    # FUNCTION_MAP metadata; a caller scope is not a source-use grant.
    functions = freg.search_function_metadata(question, 5)
    hits = {"functions": functions, "brands": [], "websites": [], "cases": [],
            "notes": [], "events": []}
    context = ("可用功能入口（仅路由信息，不代表当前业务数据）："
               + "、".join(function.get("label", "") for function in functions)
               if functions else "未匹配到功能入口；本次对话未读取业务记录或案例资料。")
    hint = MODULE_HINTS.get(scope, "")
    sys_prompt = SYSTEM_ROLE
    if hint:
        sys_prompt += "\n当前聚焦模块：" + hint
    sys_prompt += "\n\n== 功能路由提示（不是业务数据） ==\n" + context
    sys_prompt += (
        "\n\n【数据边界】本次聊天没有绑定按会话逐来源核验的SourceUse操作。"
        "功能目录和用户问题不能当作当前业务数据；不要声称读取、核验或引用了品牌、案例、笔记或事件记录，"
        "也不要编造任何当前业务数字。普通对话仍可继续。")

    targets = [{"id": f.get("id"), "label": f.get("label"), "page": f.get("page")}
               for f in hits.get("functions", [])[:5]]
    st = status()
    conversation = question
    if isinstance(history, list):
        turns = []
        for item in history[-6:]:
            if not isinstance(item, dict) or item.get("role") not in {"user", "human", "assistant"}:
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                role = "用户" if item["role"] in {"user", "human"} else "LUMENIS"
                turns.append(f"{role}：{content[:800]}")
        if turns:
            conversation = "最近对话（用户提供，非核验事实）：\n" + "\n".join(turns) + "\n当前问题：" + question
    prompt = sys_prompt + "\n\n用户问题：" + question
    from lumenis.system.ai_gateway import user_api_adapter
    usage = None
    if user_api_adapter.is_selected():
        # Only user-entered conversation and static routing metadata go out.
        # Configuring an API does not grant export of stored business sources.
        content, transport, _meta = intelligence.chat(
            sys_prompt, conversation, external_user_input=True,
        )
        provider_usage = _meta.get("usage") if isinstance(_meta, dict) else None
        if isinstance(provider_usage, dict):
            usage = {
                key: value for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                if type(value := provider_usage.get(key)) is int and value >= 0
            } or None
        completed = transport == "user_api" and isinstance(content, str) and bool(content.strip())
        provider = "user_api"
        result = {"ok": completed, "provider": provider, "analysis": content if completed else None,
                  "status": "COMPLETED" if completed else "UNAVAILABLE",
                  "code": None if completed else transport.upper()}
    else:
        result = _run_owned(prompt, "conversation")
        completed = _completed(result)
        provider = "owned"
    record_learning("chat", {
        # An inference request grants neither corpus admission nor retention
        # of raw conversation. Keep operational counts, never input/output.
        "provider": provider, "scope": scope if scope in MODULE_HINTS else "all",
        "status": result.get("status"), "code": result.get("code"),
        "usage": usage,
    })
    return {
        "ok": completed,
        "status": "COMPLETED" if completed else (
            result.get("status") if result.get("status") != "COMPLETED" else "ERROR"
        ) or "ERROR",
        "code": None if completed else (result.get("code") or "OWNED_ANALYSIS_NOT_COMPLETED"),
        "reply": _owned_result_text(result) if completed else None,
        "provider": provider, "model": st.get("model_id"), "runtime": st.get("state"),
        "usage": usage,
        "used_rule_fallback": False, "fallback_allowed": False, "targets": targets,
        "context": context,
        "source_context": {
            "scope_state": "SOURCE_USE_NOT_BOUND_FOR_CONVERSATION",
            "business_retrieval_state": "UNAVAILABLE_TYPED_SOURCE_USE_OPERATION_REQUIRED",
            "notes_state": "NOT_READ",
            "events_state": "NOT_READ",
        },
        "matched": {"brands": len(hits.get("brands", [])), "cases": len(hits.get("cases", [])),
                    "notes": 0, "events": 0},
        "elapsed_seconds": round(time.time() - t0, 2),
    }


def analyze_module(module: str, text: str, meta=None) -> dict:
    """Analyze supplied module text through the owned Gateway, without rule substitution."""
    t0 = time.time()
    module = (module or "").strip() or "notes"
    text = (text or "").strip()
    if not text:
        return {"ok": False, "status": "INVALID_INPUT", "code": "ANALYSIS_TEXT_REQUIRED"}
    meta = meta or {}
    sys_prompt = (
        SYSTEM_ROLE
        + f"\n当前分析模块：{module}。{MODULE_HINTS.get(module,'')}"
        + "\n只输出严格 JSON：{\"summary\":\"不超过60字摘要\",\"sentiment\":\"positive/neutral/negative\","
        "\"risk_level\":\"high/medium/low\",\"risk_points\":[\"风险点\"],\"suggestion\":\"不超过80字下一步建议\"}。"
        "单一来源指控保持待证实，不要夸大。"
    )
    user = f"模块附加信息：{json.dumps(meta, ensure_ascii=False)[:800]}\n待分析内容：\n{text[:6000]}"
    result = _run_owned(sys_prompt + "\n\n" + user, "module_analysis")
    analysis = result.get("analysis") if isinstance(result, dict) else None
    completed = _completed(result) and isinstance(analysis, dict)
    if completed:
        required = ("summary", "sentiment", "risk_level", "risk_points", "suggestion")
        completed = (
            all(key in analysis for key in required)
            and isinstance(analysis.get("summary"), str)
            and analysis.get("sentiment") in {"positive", "neutral", "negative"}
            and analysis.get("risk_level") in {"high", "medium", "low"}
            and isinstance(analysis.get("risk_points"), list)
            and all(isinstance(item, str) for item in analysis.get("risk_points", []))
            and isinstance(analysis.get("suggestion"), str)
        )
    record_learning("analyze", {
        "module": module, "provider": "owned", "status": result.get("status"),
        "code": result.get("code"), "len": len(text),
    })
    if not completed:
        return {
            "ok": False,
            "status": (result.get("status") if result.get("status") != "COMPLETED" else "ERROR") or "ERROR",
            "code": result.get("code") or "OWNED_MODULE_ANALYSIS_NOT_COMPLETED",
            "provider": "owned", "module": module, "analysis": None,
            "elapsed_seconds": round(time.time() - t0, 2),
        }
    return {
        **analysis, "ok": True, "status": "COMPLETED", "provider": "owned",
        "module": module, "elapsed_seconds": round(time.time() - t0, 2),
    }


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
