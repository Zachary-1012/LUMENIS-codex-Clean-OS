# -*- coding: utf-8 -*-
"""AI Hub compatibility service routed through the single SYSTEM AI Gateway.

It retrieves product context and asks the owned runtime for analysis. It does
not discover provider APIs or turn rule output into completed AI work.
"""
from __future__ import annotations
import os, sys, json, time, threading, logging, re
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
    "你是寰意 OEVIRA 的业务助手，服务于 CTH 与 BMP 工作流。回答要求：\n"
    "1. 根据本次实际提供的用户材料与获准来源作答；来源不足、口径不明或证据相互冲突时清楚说明，不编造数字、来源或事实；\n"
    "2. 区分可核验事实、来源主张、用户提供内容、推断与待核实事项；单一来源的指控不得写成已确认事实；\n"
    "3. 用户要求研究、分析或写作时，直接给出可修改的有来源答案、分析或原创草稿，并提供结论、限制与可执行下一步；\n"
    "4. 普通草稿保存、修订与版本由对应的现有工作流和权限合同处理；只有确属需审批的效果才进入相应审批/效果边界。不得宣称保存、变更或外部行动已完成，除非收到对应所有者的成功回执；\n"
    "5. 只在本次确实绑定并核验来源时才声称使用了系统业务数据；功能目录不是业务数据。使用与用户相同的语言，简洁专业。"
)

MODULE_HINTS = {
    "collect": "采集中心：各平台采集任务、六态健康、动态风控、登录恢复。",
    "notes": "笔记库：各平台原始笔记、情感、风险、正文与发布时间。",
    "events": "事件中心：事件聚类、传播、影响、处置建议。",
    "topics": "话题：按用户当前选定的主体、范围与时间分析话题；主体或证据未绑定时先说明，不默认任何参考主体。",
    "cases": "品牌营销案例库：历史公关/营销案例与应对公式。",
    "report": "报告中心：日报/周报、导出。",
    "account": "主体与权限：仅依据当前已核验的主体、用户访问范围与权限状态回答；无法核验的状态明确标为未知。",
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
        # Conversation consumes the independently admitted Shared service, not
        # the legacy offline-evaluation handle or a business-domain slot.
        runtime = intelligence.owned_inference_status('shared')
    except Exception:
        runtime = None
    if not isinstance(runtime, dict):
        runtime = {
            "provider": "owned", "available": False,
            "service_binding": "NOT_BOUND", "state": "UNAVAILABLE",
            "reason": "OWNED_RUNTIME_STATUS_UNAVAILABLE",
        }
    from .conversations import conversation_source_use_policy
    policy = conversation_source_use_policy()
    service_available = runtime.get('available') is True and runtime.get('service_binding') == 'BOUND'
    conversation_available = (service_available and policy['operation'] in runtime.get('allowed_operations', [])
        and runtime.get('source_use_policy_version') == policy['version']
        and runtime.get('source_use_policy_sha256') == policy['sha256'])
    if service_available and not conversation_available:
        runtime = {**runtime, 'state': 'UNAVAILABLE', 'reason': 'OWNED_CONVERSATION_POLICY_NOT_ADMITTED'}
    return {
        **runtime,
        "provider": "owned",
        "available": conversation_available, "enabled": conversation_available,
        "service_available": service_available, "conversation_available": conversation_available,
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
        for key in ("reply", "answer", "summary", "text", "content"):
            value = analysis.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(result, dict) and result.get('real_input_bound') is True:
        text = result.get('text')
        if isinstance(text, str) and text.strip():
            return text.strip()
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


def invalid_chat_input(code, *, external_approval=None):
    """Retain ordinary validation; audit rejected external conversation input."""
    result = {"ok": False, "status": "INVALID_INPUT", "code": code}
    from lumenis.system.ai_gateway import user_api_adapter
    if external_approval is not None or user_api_adapter.is_selected():
        try:
            result["audit_id"] = user_api_adapter.audit_denial("USER_API_INVALID_REQUEST")
        except Exception:
            return {"ok": False, "status": "UNAVAILABLE", "code": "USER_API_AUDIT_UNAVAILABLE"}
    return result


def chat(question: str, history=None, scope: str = "all", *, source_scope=None, external_approval=None,
         _owned_request=None, is_cancelled=None, _include_evaluation_ref=False) -> dict:
    """Chat through the explicitly selected Gateway, without business data export."""
    t0 = time.time()
    if (not isinstance(question, str) or (len(question) > 4000 and _owned_request is None)
            or not isinstance(scope, str)):
        return invalid_chat_input("MESSAGE_INVALID", external_approval=external_approval)
    if _owned_request is not None:
        from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
        from .conversations import conversation_source_use_policy
        policy = conversation_source_use_policy()
        if (type(_owned_request) is not OwnedServiceRequest
                or _owned_request.operation != policy['operation']
                or _owned_request.source_use_policy_version != policy['version']
                or _owned_request.source_use_policy_sha256 != policy['sha256']):
            return invalid_chat_input('CONVERSATION_TYPED_REQUEST_REQUIRED', external_approval=external_approval)
    typed_source_bound = False
    if _owned_request is not None:
        try:
            typed_material = json.loads(_owned_request.user_payload)['material']
            typed_source_bound = typed_material.get('source_use_mode') == 'explicit_selected_sources'
        except (KeyError, TypeError, ValueError):
            return invalid_chat_input('CONVERSATION_TYPED_REQUEST_REQUIRED', external_approval=external_approval)
    question = question.strip()
    if not question:
        return invalid_chat_input("MESSAGE_REQUIRED", external_approval=external_approval)
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
        for item in history:
            if not isinstance(item, dict) or item.get("role") not in {"user", "human", "assistant"}:
                return invalid_chat_input("CONVERSATION_HISTORY_INVALID", external_approval=external_approval)
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                role = "用户" if item["role"] in {"user", "human"} else "LUMENIS"
                turns.append(f"{role}：{content}")
            else:
                return invalid_chat_input("CONVERSATION_HISTORY_INVALID", external_approval=external_approval)
        if turns:
            conversation = "完整选定对话与人工任务状态（用户提供，非核验事实、授权或效果回执）：\n" + "\n".join(turns) + "\n当前问题：" + question
    # Both routes must receive the same bounded, caller-supplied conversation.
    # Passing only the last question makes follow-up turns lose their context.
    prompt = sys_prompt + "\n\n用户对话：" + conversation
    # The selected external transport has a hard 32k-character envelope. This
    # is a transport limit, not a token estimate. Never silently cut constraints
    # or writing to fit a model whose tokenizer has not been admitted here.
    from lumenis.system.ai_gateway import user_api_adapter
    external_selected = user_api_adapter.is_selected()
    if external_selected and typed_source_bound:
        return {'ok': False, 'status': 'BLOCKED',
            'code': 'CONVERSATION_SOURCE_EXTERNAL_TRANSMISSION_NOT_GRANTED',
            'reply': None, 'provider': 'owned', 'generation_performed': False,
            'source_context': {'scope_state': 'EXTERNAL_TRANSMISSION_NOT_GRANTED',
                'business_retrieval_state': 'NOT_SENT', 'notes_state': 'NOT_READ', 'events_state': 'NOT_READ'}}
    if (external_selected or _owned_request is None) and len(sys_prompt) + len(conversation) > 32000:
        return {"ok": False, "status": "BLOCKED", "code": "CONVERSATION_CONTEXT_EXCEEDS_TRANSPORT_LIMIT",
                "reply": None, "generation_performed": False,
                "context_accounting": {"transport_characters": len(sys_prompt) + len(conversation),
                    "transport_character_limit": 32000, "token_budget_verified": False,
                    "recovery": "EXPLICIT_CONTEXT_CORRECTION_OR_FORGET_REQUIRED"}}
    usage = None
    approval_request = None
    model_budget = None
    owned_provenance = None
    owned_evaluation_call_ref = None
    if external_selected:
        # Only user-entered conversation and static routing metadata go out.
        # Configuring an API does not grant export of stored business sources.
        content, transport, _meta = intelligence.chat(
            sys_prompt, conversation, external_user_input=True, external_approval=external_approval,
        )
        approval_request = _meta.get("approval_request") if isinstance(_meta, dict) else None
        provider_usage = _meta.get("usage") if isinstance(_meta, dict) else None
        if isinstance(provider_usage, dict):
            usage = {
                key: value for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                if type(value := provider_usage.get(key)) is int and value >= 0
            } or None
        completed = transport == "user_api" and isinstance(content, str) and bool(content.strip())
        provider = "user_api"
        result = {"ok": completed, "provider": provider, "analysis": content if completed else None,
                  "status": "COMPLETED" if completed else ("APPROVAL_REQUIRED" if approval_request else "UNAVAILABLE"),
                  "code": None if completed else transport.upper(),
                  "audit_id": _meta.get("audit_id") if isinstance(_meta, dict) else None}
    elif external_approval is not None:
        # A stale external request must not silently turn into owned inference.
        result = {"ok": False, "status": "UNAVAILABLE", "code": "USER_API_NOT_SELECTED"}
        try:
            result["audit_id"] = user_api_adapter.audit_denial("USER_API_NOT_SELECTED")
        except Exception:
            result["code"] = "USER_API_AUDIT_UNAVAILABLE"
        completed = False
        provider = "user_api"
    else:
        if _owned_request is not None:
            from lumenis.ai_hub.context_pack import run_budgeted_owned_request
            from lumenis.system.ai_gateway.owned_service import owned_service_request_digest
            result = run_budgeted_owned_request(_owned_request, is_cancelled=is_cancelled)
            if type(result) is not dict:
                result = {'ok': False, 'status': 'ERROR',
                    'code': 'OWNED_CONVERSATION_RESULT_INVALID', 'provider': 'owned'}
            elif result.get('ok') is True and (
                    result.get('status') != 'COMPLETED'
                    or type(result.get('attempt_id')) is not str
                    or not re.fullmatch(r'attempt_[0-9a-f]{32}', result.get('attempt_id', ''))
                    or type(result.get('run_id')) is not str or not result.get('run_id')
                    or result.get('real_input_bound') is not True
                    or result.get('request_digest') != owned_service_request_digest(_owned_request)
                    or result.get('operation') != _owned_request.operation
                    or result.get('domain_id') != _owned_request.domain_id
                    or result.get('scope') != _owned_request.scope
                    or result.get('input_revision_sha256') != _owned_request.input_revision_sha256
                    or result.get('source_binding_sha256') != _owned_request.source_binding_sha256):
                original = result
                result = {'ok': False, 'status': 'ERROR', 'code': 'OWNED_CONVERSATION_RESULT_INVALID',
                    'provider': 'owned', 'real_input_bound': False}
                # Keep only opaque execution/version identifiers so Evaluation
                # can record a real but rejected attempt without retaining text.
                for key in ('attempt_id', 'request_digest', 'run_id', 'model_id', 'model_revision',
                            'runtime_sha256', 'executor_sha256', 'operation', 'domain_id', 'scope',
                            'input_revision_sha256', 'source_binding_sha256', 'prompt_tokens',
                            'completion_tokens', 'total_tokens'):
                    value = original.get(key)
                    if type(value) in (str, int) and (type(value) is not str or len(value) <= 512):
                        result[key] = value
                if type(original.get('context_accounting')) is dict:
                    result['context_accounting'] = original['context_accounting']
            model_budget = result.get('context_accounting')
        else:
            result = _run_owned(prompt, "conversation")
        completed = _completed(result)
        provider = "owned"
        if _owned_request is not None:
            try:
                from lumenis.shared.evaluation.ai import record_owned_gateway_execution
                owned_evaluation_call_ref = record_owned_gateway_execution(
                    _owned_request, result, latency_ms=max(0, int((time.time() - t0) * 1000)))
            except Exception:
                # Evaluation is a non-blocking side record. Its absence stays
                # unlinked in the conversation instead of fabricating a PASS.
                owned_evaluation_call_ref = None
        if completed and _owned_request is not None:
            owned_provenance = {key: value for key, value in result.items() if key in {
                'operation', 'request_id', 'request_digest', 'run_id', 'model_id', 'model_revision',
                'recipe', 'domain_id', 'scope', 'candidate_identity_sha256', 'runtime_sha256',
                'executor_sha256', 'manifest_sha256', 'adapter_sha256', 'adapter_config_sha256',
                'input_revision_sha256', 'source_binding_sha256', 'source_evidence_refs',
                'source_use_policy_version', 'source_use_policy_sha256', 'source_audit_ids',
                'admission_request_sha256', 'evaluation_ref', 'quality_review_ref', 'evaluation_state',
                'quality_state', 'product_acceptance', 'context_window_tokens', 'output_token_limit'}}
            if _include_evaluation_ref is True and owned_evaluation_call_ref:
                owned_provenance['evaluation_call_ref'] = owned_evaluation_call_ref
            usage = {key: result[key] for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                     if type(result.get(key)) is int and result[key] >= 0} or None
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
        "provider": provider, "model": result.get('model_id') or st.get("model_id"), "runtime": st.get("state"),
        "model_budget": model_budget, "owned_provenance": owned_provenance,
        "usage": usage, "approval_request": approval_request, "audit_id": result.get("audit_id"),
        "used_rule_fallback": False, "fallback_allowed": False, "targets": targets,
        "context": context,
        "source_context": {
            "scope_state": "SOURCE_USE_VERIFIED_FOR_REQUEST" if typed_source_bound and completed else
                "SOURCE_USE_NOT_BOUND_FOR_CONVERSATION",
            "business_retrieval_state": "EXPLICITLY_SELECTED_INTERNAL_SOURCES_ONLY" if typed_source_bound and completed else
                "UNAVAILABLE_TYPED_SOURCE_USE_OPERATION_REQUIRED",
            "notes_state": "NOT_READ",
            "events_state": "NOT_READ",
        },
        "owned_analysis": result.get('analysis') if typed_source_bound and type(result.get('analysis')) is dict else None,
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
