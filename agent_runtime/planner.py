# -*- coding: utf-8 -*-
"""
Planner — 基于 OSAI Contract 的规划器
======================================
将 goal（自然语言目标）分解为步骤列表。
经唯一 Gateway 调用获准的类型化请求；未配置时明确不可用。

每步包含：action、tool、params、expected_output、risk_level。

复用：
  - 唯一 SYSTEM AI Gateway（不重写 AI 调用）
  - ai_task_engine 持久化规划结果到 ai_task 表（复用）

设计原则：
  - AI 输出必须经过 JSON 解析和结构验证，不直接信任
  - 规划失败返回空计划与明确原因，不伪造执行动作
  - 规划结果可持久化、可人工修正
  - 不引入 OSAI 运行时依赖，通过 Contract 接口对齐

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - Plan 结构：steps[].{action, tool, params, expected_output, risk_level}
  - 规划模式仅代表预算；模型选择归唯一 Gateway
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PlanMode(str, Enum):
    """规划模式。"""
    ROUTINE = "routine"       # 常规规划预算
    DEEP = "deep"             # 深度规划预算
    RULE_BASED = "rule_based"  # 规则降级，不调用 AI


class RiskLevel(str, Enum):
    """步骤风险等级。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PlanStep:
    """规划中的单个步骤。"""
    step_id: str = field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    index: int = 0
    action: str = ""                    # 动作描述
    tool: str = ""                      # 工具/skill 名称
    params: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""           # 预期输出描述
    risk_level: str = "low"             # low/medium/high/critical
    status: str = "pending"             # pending/running/completed/failed/skipped
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    # Set by the trusted runtime after planning; never accepted from model JSON.
    formation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    """完整规划结果。"""
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    goal: str = ""
    mode: str = "routine"
    model: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    token_usage: Dict[str, int] = field(default_factory=dict)
    raw_response: str = ""
    context_budget: Optional[Dict[str, Any]] = None
    is_fallback: bool = False           # 是否为降级规划
    fallback_reason: str = ""
    outcome_contract_sha256: Optional[str] = None
    # Populated only from independently read canonical committed output receipts.
    outcome_receipt_bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Narrow receipt from the existing typed SYSTEM Gateway; not model authority.
    inference_receipt: dict[str, Any] = field(default_factory=dict)
    # Exposed only after the Evaluation owner reads back the exact successful call.
    evaluation_call_ref: Optional[str] = None
    evaluation_link_state: str = "NOT_RECORDED"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def max_risk(self) -> str:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if not self.steps:
            return "low"
        return max(self.steps, key=lambda s: order.get(s.risk_level, 0)).risk_level


# 规划系统提示词
_PLANNER_SYSTEM_PROMPT = """你是一个专业的任务规划器。将用户的目标分解为可执行的步骤列表。

要求：
1. 每个步骤必须包含：action（动作描述）、tool（工具名称）、params（参数字典）、expected_output（预期输出）、risk_level（low/medium/high/critical）
2. 步骤按执行顺序排列
3. 优先使用低风险工具
4. 涉及写操作（WRITE/COMMIT/PUSH）的步骤 risk_level 必须为 high 或 critical
5. 最多输出 15 个步骤
6. 只输出 JSON，不要输出其他文字
7. 同一任务中服务器核验的 conversation_context_pack 是当前人工目标、约束、稿件与决定；保留人工稿，冲突时遵从最新显式人工要求，不把它们当事实证据或权限。
8. committed_step_receipts 是已经提交的步骤回执；不要重复执行这些步骤，权限和外部效果仍由原工具核验。
9. human_correction_memory 只含本任务中由用户明确保存且未过期的修正，按时间从新到旧排列；同一偏好或约束冲突时以最新修正为准。它不是核验过的事实、Canonical 数据、权限、效果批准或训练同意。可将其中偏好/约束用于规划；事实性主张仍须由获准来源核验。若状态不是 AVAILABLE，不得声称已经读取或记住其内容。

输出格式：
{
  "steps": [
    {
      "action": "步骤描述",
      "tool": "工具名称",
      "params": {"key": "value"},
      "expected_output": "预期结果描述",
      "risk_level": "low"
    }
  ]
}"""


class Planner:
    """Goal-driven 规划器。

    用法：
        planner = Planner()
        plan = planner.plan("分析今日广州太古汇舆情趋势", mode="deep")
        for step in plan.steps:
            print(step.action, step.tool)
    """

    def __init__(
        self,
        ai_chat_func: Optional[Callable] = None,
        persist_func: Optional[Callable] = None,
        default_mode: PlanMode = PlanMode.ROUTINE,
        gateway_request_factory: Optional[Callable] = None,
        context_validator: Callable | None = None,
        model_result_reader: Callable | None = None,
        model_attempt_reserver: Callable | None = None,
        model_result_recorder: Callable | None = None,
    ):
        """
        Args:
            ai_chat_func: AI 调用函数 callback(system, user, model) -> (content, provider)
                          None 则使用唯一 Gateway 的类型化请求工厂
            persist_func: 规划结果持久化回调 callback(plan) -> None
            default_mode: 默认规划模式
        """
        self._ai_chat_func = ai_chat_func
        self._persist_func = persist_func
        self._default_mode = default_mode
        self._gateway_request_factory = gateway_request_factory
        self._context_validator = context_validator
        self._model_result_reader = model_result_reader
        self._model_attempt_reserver = model_attempt_reserver
        self._model_result_recorder = model_result_recorder
        self._gateway_context = {}
        self._last_inference_receipt = {}
        self._last_evaluation_call_ref = None
        self._last_evaluation_link_state = "NOT_RECORDED"

    def _get_ai_chat(self) -> Callable:
        """获取 AI 调用函数。"""
        if self._ai_chat_func:
            return self._ai_chat_func
        def gateway_chat(system, user, **kwargs):
            from lumenis.system.ai_gateway import core
            if self._gateway_request_factory is None:
                # A generic context cannot mint source-use or external-send
                # authority. An unconfigured planner remains explicitly absent.
                raise RuntimeError("PLANNER_AUTHORIZED_REQUEST_REQUIRED")
            if self._context_validator is not None:
                self._context_validator()
            request = self._gateway_request_factory(system, user, dict(self._gateway_context))
            from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
            if type(request) is not OwnedServiceRequest or request.operation != "agent_plan":
                raise RuntimeError("PLANNER_TYPED_REQUEST_REQUIRED")
            request = replace(request, response_schema_json=json.dumps(
                self._response_schema(self._gateway_max_steps),
                ensure_ascii=False, sort_keys=True, allow_nan=False))
            recovered = self._model_result_reader(request) if self._model_result_reader is not None else None
            if recovered is not None:
                result = recovered['result']
                self._last_context_budget = recovered['context_budget']
                self._last_evaluation_call_ref = recovered.get('evaluation_call_ref')
                self._last_evaluation_link_state = recovered.get(
                    'evaluation_link_state', 'NOT_RECORDED')
                if self._context_validator is not None:
                    self._context_validator()
                self._last_inference_receipt = self._validated_inference_receipt(
                    result, request, allow_legacy_receipt=True,
                )
                if self._last_inference_receipt is None:
                    raise RuntimeError("PLANNER_RECOVERED_RECEIPT_INVALID")
                content = result['analysis']
                return (json.dumps(content, ensure_ascii=False, allow_nan=False)
                        if isinstance(content, dict) else content), 'owned'
            from lumenis.system.ai_gateway.owned_service import (
                measure_owned_request,
                owned_service_status,
            )
            measured = measure_owned_request(request)
            omitted = []
            reduced = dict(self._gateway_context)
            # Preserve goal, identity/scope and tool contracts in full. Remove
            # only complete low-priority derived sections, with explicit receipt.
            for key in ("derived_memory", "reviewed_learning_context"):
                if measured.get("ok") is not True or measured.get("fits") is True:
                    break
                if key not in reduced:
                    continue
                value = reduced.pop(key)
                import hashlib
                omitted.append({"section": key, "sha256": hashlib.sha256(json.dumps(
                    value, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                    "reason": "selected_model_context_budget"})
                reduced["context_omissions"] = list(omitted)
                user = self._build_user_prompt(self._gateway_goal, reduced, self._gateway_max_steps)
                request = self._gateway_request_factory(system, user, dict(self._gateway_context))
                if type(request) is not OwnedServiceRequest or request.operation != "agent_plan":
                    raise RuntimeError("PLANNER_TYPED_REQUEST_REQUIRED")
                request = replace(request, response_schema_json=json.dumps(
                    self._response_schema(self._gateway_max_steps),
                    ensure_ascii=False, sort_keys=True, allow_nan=False))
                measured = measure_owned_request(request)
            if measured.get("ok") is not True:
                raise RuntimeError(measured.get("code", "PLANNER_TOKEN_COUNT_UNAVAILABLE"))
            self._last_context_budget = {**measured, "omitted_sections": omitted}
            pack = self._gateway_context.get('conversation_context_pack')
            if type(pack) is dict:
                self._last_context_budget['required_context_sha256'] = pack['sha256']
            memory = self._gateway_context.get('human_correction_memory')
            if (type(memory) is dict and type(memory.get('snapshot_sha256')) is str
                    and re.fullmatch(r'[0-9a-f]{64}', memory['snapshot_sha256'])):
                self._last_context_budget['human_correction_memory_sha256'] = memory['snapshot_sha256']
            if measured.get("fits") is not True:
                raise RuntimeError("PLANNER_REQUIRED_CONTEXT_EXCEEDS_MODEL_BUDGET")
            status = owned_service_status(request.domain_id)
            if status.get("binding_sha256") != measured.get("binding_sha256"):
                raise RuntimeError("PLANNER_MEASURED_BINDING_CHANGED")
            # Gateway and runtime revalidate binding, source and exact tokenizer
            # budget again before generation; this receipt is never an authority.
            control = {}
            if self._context_validator is not None:
                self._context_validator()
                def context_cancelled():
                    try:
                        self._context_validator()
                        return False
                    except (PermissionError, RuntimeError, ValueError):
                        return True
                control['is_cancelled'] = context_cancelled
            reservation = self._model_attempt_reserver(request) if self._model_attempt_reserver is not None else None
            gateway_started = time.perf_counter()
            result = core.run_owned_request(request, expected_binding_sha256=measured["binding_sha256"], **control)
            gateway_latency_ms = max(0, int((time.perf_counter() - gateway_started) * 1000))
            # Agent planning is a real typed Gateway consumer too. Reuse the
            # Shared Evaluation owner, which records hashes and request/model
            # bindings only; evaluation storage failure must not discard an
            # otherwise valid task result.
            evaluation_call_ref = None
            evaluation_link_state = 'NOT_RECORDED'
            try:
                from lumenis.shared.evaluation.ai import record_owned_gateway_execution
                evaluation_call_ref = record_owned_gateway_execution(
                    request, result, latency_ms=gateway_latency_ms)
            except Exception:
                evaluation_link_state = 'UNAVAILABLE'
            verified_receipt = self._validated_inference_receipt(result, request)
            if type(evaluation_call_ref) is str and verified_receipt is not None:
                try:
                    from lumenis.shared.evaluation.ai import (
                        owned_gateway_output_sha256,
                        verify_owned_gateway_execution_ref,
                    )
                    expected_provenance = {
                        'attempt_id': verified_receipt['attempt_id'],
                        'run_id': verified_receipt['run_id'],
                        'model_id': verified_receipt['model_id'],
                        'model_revision': verified_receipt['model_revision'],
                        'runtime_sha256': verified_receipt['runtime_sha256'],
                        'executor_sha256': verified_receipt['executor_sha256'],
                        'evaluation_output_sha256': owned_gateway_output_sha256(result),
                    }
                    evaluation_link_state = verify_owned_gateway_execution_ref(
                        evaluation_call_ref, request, expected_provenance=expected_provenance)
                except Exception:
                    evaluation_link_state = 'UNAVAILABLE'
            elif evaluation_link_state != 'UNAVAILABLE':
                evaluation_link_state = 'NOT_LINKED' if evaluation_call_ref else 'NOT_RECORDED'
            self._last_evaluation_call_ref = (
                evaluation_call_ref if evaluation_link_state == 'VERIFIED' else None)
            self._last_evaluation_link_state = evaluation_link_state
            if self._context_validator is not None:
                self._context_validator()
            if self._model_result_recorder is not None:
                self._model_result_recorder(
                    request, reservation, result, self._last_context_budget,
                    evaluation_call_ref=self._last_evaluation_call_ref,
                    evaluation_link_state=self._last_evaluation_link_state,
                )
            if type(result) is not dict or result.get("ok") is not True or result.get("status") != "COMPLETED":
                code = result.get("code") if type(result) is dict else None
                if type(code) is not str or not re.fullmatch(r"[A-Z0-9_]{1,96}", code):
                    code = "PLANNER_GATEWAY_UNAVAILABLE"
                raise RuntimeError(code)
            receipt = self._validated_inference_receipt(result, request)
            if receipt is None:
                raise RuntimeError("PLANNER_GATEWAY_RECEIPT_INVALID")
            content = result.get("analysis")
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False, allow_nan=False)
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("PLANNER_GATEWAY_RESULT_INVALID")
            self._last_inference_receipt = receipt
            return content, "owned"
        return gateway_chat

    @staticmethod
    def _validated_inference_receipt(
        result: Any, request: Any, *, allow_legacy_receipt: bool = False,
    ) -> dict[str, Any] | None:
        """Keep only the existing Gateway's verifiable, non-secret run receipt."""
        if type(result) is not dict:
            return None
        from lumenis.system.ai_gateway.owned_service import (
            OwnedServiceRequest, owned_service_request_digest,
        )
        if type(request) is not OwnedServiceRequest:
            return None
        fields = (
            "provider", "status", "code", "operation", "attempt_id", "domain_id", "scope",
            "request_id", "request_digest", "run_id", "model_id", "model_revision", "recipe",
            "runtime_sha256", "executor_sha256", "source_use_policy_version", "source_use_policy_sha256",
            "source_binding_sha256", "input_revision_sha256", "source_evidence_refs",
            "prompt_tokens", "completion_tokens", "total_tokens",
        )
        legacy_only = {"code", "attempt_id", "domain_id", "scope", "runtime_sha256",
                       "executor_sha256", "source_use_policy_version"}
        legacy = allow_legacy_receipt and not any(key in result for key in legacy_only)
        if legacy:
            fields = tuple(key for key in fields if key not in legacy_only)
        receipt = {key: result.get(key) for key in fields}
        hashes = ["request_digest", "source_use_policy_sha256", "source_binding_sha256",
                  "input_revision_sha256"]
        if not legacy:
            hashes.extend(("runtime_sha256", "executor_sha256"))
        if (receipt["provider"] != "owned" or receipt["status"] != "COMPLETED"
                or not legacy and receipt["code"] != "OWNED_INFERENCE_COMPLETED"
                or receipt["operation"] != request.operation or request.operation != "agent_plan"
                or not legacy and (type(receipt["attempt_id"]) is not str
                    or not re.fullmatch(r"attempt_[0-9a-f]{32}", receipt["attempt_id"]))
                or not legacy and (receipt["domain_id"] != request.domain_id
                    or receipt["scope"] != request.scope)
                or receipt["request_id"] != request.request_id
                or receipt["request_digest"] != owned_service_request_digest(request)
                or not legacy and receipt["source_use_policy_version"] != request.source_use_policy_version
                or receipt["source_use_policy_sha256"] != request.source_use_policy_sha256
                or receipt["source_binding_sha256"] != request.source_binding_sha256
                or receipt["input_revision_sha256"] != request.input_revision_sha256
                or receipt["source_evidence_refs"] != list(request.source_evidence_refs)
                or result.get("ok") is not True or result.get("real_input_bound") is not True
                or any(type(receipt[key]) is not str or not receipt[key].strip()
                       or len(receipt[key]) > 512 for key in (
                           "request_id", "run_id", "model_id", "model_revision", "recipe"))
                or any(type(receipt[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", receipt[key])
                       for key in hashes)
                or type(receipt["source_evidence_refs"]) is not list
                or not receipt["source_evidence_refs"]
                or len(receipt["source_evidence_refs"]) > 128
                or any(type(item) is not str or not item.strip() or len(item) > 512
                       for item in receipt["source_evidence_refs"])
                or any(type(receipt[key]) is not int or receipt[key] < 0
                       for key in ("prompt_tokens", "completion_tokens", "total_tokens"))
                or receipt["completion_tokens"] < 1
                or receipt["total_tokens"] != receipt["prompt_tokens"] + receipt["completion_tokens"]):
            return None
        return receipt

    def _select_model(self, mode: PlanMode) -> str:
        # The unique Gateway owns actual user/provider/model selection. These
        # planning budgets do not choose or silently fall back to any provider.
        return "gateway-selected" if mode is not PlanMode.RULE_BASED else "none"

    def plan(
        self,
        goal: str,
        mode: Optional[PlanMode] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 15,
    ) -> Plan:
        """将目标分解为步骤列表。

        Args:
            goal: 自然语言目标
            mode: 规划模式（routine/deep），None 则使用默认
            context: 附加上下文
            max_steps: 最大步骤数

        Returns:
            Plan 规划结果
        """
        mode = mode or self._default_mode
        model = self._select_model(mode)
        plan = Plan(goal=goal, mode=mode.value, model=model)
        self._last_inference_receipt = {}
        self._last_evaluation_call_ref = None
        self._last_evaluation_link_state = "NOT_RECORDED"

        if mode == PlanMode.RULE_BASED:
            try:
                if self._context_validator is not None:
                    self._context_validator()
            except (PermissionError, RuntimeError, ValueError) as exc:
                return self._fallback_plan(goal, plan, str(exc))
            return self._persist_plan(self._rule_based_plan(goal, plan))

        if type(max_steps) is not int or not 1 <= max_steps <= 15:
            return self._fallback_plan(goal, plan, "PLANNER_MAX_STEPS_INVALID")

        try:
            if self._context_validator is not None:
                self._context_validator()
            self._gateway_context = dict(context or {})
            self._gateway_goal, self._gateway_max_steps = goal, max_steps
            self._last_context_budget = None
            user_prompt = self._build_user_prompt(goal, context, max_steps)
            chat_func = self._get_ai_chat()

            content, provider = chat_func(
                _PLANNER_SYSTEM_PROMPT,
                user_prompt,
                model=model,
                temperature=0.1,
                max_tokens=2000,
            )
            if self._context_validator is not None:
                self._context_validator()

            plan.context_budget = self._last_context_budget
            plan.raw_response = content or ""
            plan.inference_receipt = dict(self._last_inference_receipt)
            plan.evaluation_call_ref = self._last_evaluation_call_ref
            plan.evaluation_link_state = self._last_evaluation_link_state
            plan.token_usage = {key: plan.inference_receipt[key] for key in (
                "prompt_tokens", "completion_tokens", "total_tokens")
                if key in plan.inference_receipt}
            if plan.inference_receipt:
                plan.model = plan.inference_receipt["model_id"]

            if not content:
                return self._fallback_plan(goal, plan, "AI returned empty response")

            steps = self._parse_plan_response(content, max_steps)
            if not steps:
                return self._fallback_plan(goal, plan, "Failed to parse AI response as JSON")

            plan.steps = steps
            plan.is_fallback = False

        except Exception as e:
            code = getattr(e, "code", None) or str(e)
            reason = code if type(code) is str and re.fullmatch(r"[A-Z0-9_]{1,96}", code) else (
                f"AI planning failed: {type(e).__name__}")
            plan.inference_receipt = dict(self._last_inference_receipt)
            plan.evaluation_call_ref = self._last_evaluation_call_ref
            plan.evaluation_link_state = self._last_evaluation_link_state
            if plan.inference_receipt:
                plan.token_usage = {key: plan.inference_receipt[key] for key in (
                    "prompt_tokens", "completion_tokens", "total_tokens")}
                plan.model = plan.inference_receipt["model_id"]
            return self._fallback_plan(goal, plan, reason)

        return self._persist_plan(plan)

    def _persist_plan(self, plan: Plan) -> Plan:
        if self._persist_func is not None:
            try:
                self._persist_func(plan)
            except Exception:
                plan.steps = []
                plan.is_fallback = True
                plan.fallback_reason = "PLANNING_PERSISTENCE_FAILED"
        return plan

    @staticmethod
    def _response_schema(max_steps: int) -> dict[str, Any]:
        return {
            "type": "object", "required": ["steps"], "additionalProperties": False,
            "properties": {"steps": {
                "type": "array", "minItems": 1, "maxItems": max_steps,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["action", "tool", "params", "expected_output", "risk_level"],
                    "properties": {
                        "action": {"type": "string", "minLength": 1},
                        "tool": {"type": "string", "minLength": 1},
                        "params": {"type": "object"},
                        "expected_output": {"type": "string", "minLength": 1},
                        "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    },
                },
            }},
        }

    def _build_user_prompt(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        max_steps: int,
    ) -> str:
        """构建用户提示词。"""
        parts = [f"目标：{goal}", f"最大步骤数：{max_steps}"]
        if context:
            raw = json.dumps(context, ensure_ascii=False, allow_nan=False)
            # Explicit bounded payload, never an invalid half-JSON or silent loss.
            if len(raw.encode("utf-8")) > 8 * 1024 * 1024:
                raise ValueError("PLANNER_CONTEXT_TOO_LARGE")
            parts.append(f"上下文：{raw}")
        parts.append("请输出规划 JSON。")
        return "\n".join(parts)

    def _parse_plan_response(self, content: str, max_steps: int) -> List[PlanStep]:
        """解析 AI 返回的规划 JSON。"""
        # 提取 JSON（AI 可能在 JSON 前后加文字）
        json_str = self._extract_json(content)
        if not json_str:
            return []

        from lumenis.system.ai_gateway.owned_service import (
            OwnedServiceBlocked,
            _strict_json,
        )
        try:
            data = _strict_json(json_str)
            json.dumps(data, ensure_ascii=False, allow_nan=False)
        except (OwnedServiceBlocked, ValueError, TypeError):
            return []
        if type(data) is not dict or set(data) != {"steps"}:
            return []
        raw_steps = data["steps"]
        if type(raw_steps) is not list or not 1 <= len(raw_steps) <= max_steps:
            return []
        steps = []
        for i, raw in enumerate(raw_steps):
            if (type(raw) is not dict
                    or set(raw) != {"action", "tool", "params", "expected_output", "risk_level"}
                    or any(type(raw[key]) is not str or not raw[key].strip()
                           for key in ("action", "tool", "expected_output"))
                    or type(raw["params"]) is not dict
                    or type(raw["risk_level"]) is not str
                    or raw["risk_level"] not in {"low", "medium", "high", "critical"}):
                return []
            step = PlanStep(
                index=i,
                action=raw["action"],
                tool=raw["tool"],
                params=raw["params"],
                expected_output=raw["expected_output"],
                risk_level=raw["risk_level"],
            )
            steps.append(step)
        return steps

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """从文本中提取 JSON 字符串。"""
        if type(text) is not str:
            return None
        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # One balanced top-level object only: never recover a nested fragment
        # from malformed output or guess between multiple model responses.
        candidates = []
        start, depth, quoted, escaped = None, 0, False, False
        for index, character in enumerate(text):
            if depth and quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
                continue
            if depth and character == '"':
                quoted = True
            elif character == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif character == "}" and depth:
                depth -= 1
                if depth == 0:
                    candidate = text[start:index + 1]
                    try:
                        json.loads(candidate)
                        candidates.append(candidate)
                    except json.JSONDecodeError:
                        pass
        return candidates[0] if len(candidates) == 1 and depth == 0 else None

    def _fallback_plan(self, goal: str, plan: Plan, reason: str) -> Plan:
        """规划不可用；保留完整目标，不合成可执行动作。"""
        plan.is_fallback = True
        plan.fallback_reason = reason
        plan.context_budget = getattr(self, "_last_context_budget", None)
        plan.steps = []
        return self._persist_plan(plan)

    def _rule_based_plan(self, goal: str, plan: Plan) -> Plan:
        """规则规划（不调用 AI）。"""
        plan.is_fallback = True
        plan.fallback_reason = "rule_based mode"
        plan.steps = [
            PlanStep(
                index=0,
                action=f"规则执行：{goal}",
                tool="rule_engine",
                params={"goal": goal},
                expected_output="规则引擎执行结果",
                risk_level="low",
            )
        ]
        return plan

    @staticmethod
    def _extract_token_usage() -> Dict[str, int]:
        # No usage claim without the exact Gateway receipt. Never read a stale
        # thread-local receipt from a retired provider module.
        return {}

    def validate_plan(self, plan: Plan) -> List[str]:
        """验证规划结果的完整性和安全性。

        Returns:
            问题列表（空列表表示验证通过）
        """
        issues = []
        if not plan.goal:
            issues.append("plan.goal is empty")
        if not plan.steps:
            issues.append("plan has no steps")
        for i, step in enumerate(plan.steps):
            if not step.action:
                issues.append(f"step[{i}].action is empty")
            if step.risk_level in ("high", "critical") and not step.tool:
                issues.append(f"step[{i}] high risk but no tool specified")
        return issues
