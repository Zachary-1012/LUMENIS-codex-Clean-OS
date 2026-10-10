# -*- coding: utf-8 -*-
"""Capability Router — 统一工具路由层。

将 ZBC 的 API 路由/Skill/Function 注册为 Agent 可调用的 Tool。
执行链路复用 skill_execution_chain：permission → firewall → effect_fence → execute → evidence。

首批注册 12 个核心 Tool（覆盖舆情/风险/事件/采集/报告/情报/品牌/AI/系统全域）：
  1. note_search          — 笔记搜索
  2. event_query          — 事件查询
  3. trend_query          — 趋势查询
  4. risk_alert_query     — 风险预警查询
  5. collection_trigger   — 采集触发
  6. report_generate      — 报告生成
  7. intelligence_search  — 情报检索
  8. brand_query          — 品牌业态查询
  9. ai_analyze           — AI分析调用
  10. skill_execute       — Skill执行
  11. task_status         — 任务状态查询
  12. system_health       — 系统健康检查
"""
from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict, fields
from functools import wraps
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .formation import (FormationError, FormedCall, canonical_bytes, digest,
                        implementation_identity, runtime_identity, request_identity,
                        context_identity)

logger = logging.getLogger(__name__)


def _normalize_handler_result(data):
    """Respect both existing result vocabularies without using dict truthiness."""
    if isinstance(data, dict):
        flags = [data[key] for key in ("success", "ok") if key in data]
        if any(type(flag) is not bool for flag in flags):
            return {"success": False, "error": "TOOL_HANDLER_STATUS_INVALID", "result": data}
        if any(flag is False for flag in flags) or data.get("error"):
            return {**data, "success": False, "error": data.get("error") or "TOOL_HANDLER_FAILED"}
        if "success" in data:
            return data
    return {"success": True, "result": data, "source": "tool_handler"}


def _serialized_dispatch(method):
    @wraps(method)
    def dispatch(self, *args, **kwargs):
        with self._dispatch_lock:
            return method(self, *args, **kwargs)
    return dispatch


class ToolRiskLevel(str, Enum):
    LOW = "LOW"           # 只读查询
    MEDIUM = "MEDIUM"     # 分析/计算
    HIGH = "HIGH"         # 触发采集/生成报告
    CRITICAL = "CRITICAL"  # 写操作/配置变更


class ToolPermissionLevel(str, Enum):
    READ = "read"
    ANALYZE = "analyze"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class ToolParam:
    """Tool 参数定义。"""
    name: str
    type: str = "string"           # string/integer/boolean/object/array
    required: bool = False
    description: str = ""
    default: Any = None
    enum: List[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """Tool 定义（注册元数据）。"""
    tool_id: str
    name: str
    description: str
    category: str = "general"
    keywords: List[str] = field(default_factory=list)
    params: List[ToolParam] = field(default_factory=list)
    permission_level: ToolPermissionLevel = ToolPermissionLevel.READ
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    requires_approval: bool = False
    handler: Optional[Callable] = None       # 执行函数（可选，无则通过 API 路由）
    api_route: str = ""                      # 对应的 HTTP 路由
    enabled: bool = True
    version: str = "1.0.0"
    # Trusted owner metadata, never populated from a model's tool arguments.
    origin: str = ""
    resource_uri: str = ""
    identity_provider: Optional[Callable] = None
    dependency_paths: Tuple[str, ...] = ()
    resource_manifest: List[Dict[str, Any]] = field(default_factory=list)
    resource_reader: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {f.name: deepcopy(getattr(self, f.name)) for f in fields(self)
             if f.name not in {"handler", "identity_provider", "resource_reader", "dependency_paths"}}
        d["permission_level"] = self.permission_level.value
        d["risk_level"] = self.risk_level.value
        d["params"] = [asdict(p) for p in self.params]
        d.pop("handler", None)
        for key in ("identity_provider", "resource_reader", "dependency_paths"):
            d.pop(key, None)
        return d

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """校验输入参数。"""
        for p in self.params:
            if p.required and p.name not in params:
                return False, f"missing required param: {p.name}"
            if p.name in params and p.enum:
                if params[p.name] not in p.enum:
                    return False, f"param {p.name} must be one of {p.enum}"
        return True, ""


@dataclass
class ToolExecutionResult:
    """Tool 执行结果。"""
    tool_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    permission_result: Optional[Dict[str, Any]] = None
    firewall_result: Optional[Dict[str, Any]] = None
    effect_fence_result: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    duration_ms: int = 0
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    formation: Optional[Dict[str, Any]] = None
    reconciliation_required: bool = False


@dataclass(frozen=True)
class ToolActorContext:
    """Actor claims supplied by a server-side caller.

    This is deliberately separate from tool params, which are untrusted task
    input and must never select an identity or product permission scope. Its
    field shape alone is not proof of authentication or product authorization;
    CapabilityRouter requires an injected server-owned actor_authorizer before
    execution. That authorizer must bind the actor to the authenticated caller
    and current account authorization matrix.
    """
    user_id: int
    user_role: str
    product_id: str
    domain_id: str
    permission_role: str

    def valid(self) -> bool:
        product = str(self.product_id or "").upper()
        domain = str(self.domain_id or "").lower()
        permission_role = str(self.permission_role or "").lower()
        expected_domain = {"CTH": "cth", "BMP": "zbmp", "ZBMP": "zbmp", "SYSTEM": "system"}.get(product)
        expected_roles = {
            "CTH": {"cth_admin", "cth_analyst", "cth_operator"},
            "BMP": {"zbmp_admin", "zbmp_analyst", "zbmp_operator"},
            "ZBMP": {"zbmp_admin", "zbmp_analyst", "zbmp_operator"},
            "SYSTEM": {"system_admin", "system_operator", "system_writer"},
        }.get(product, set())
        return (
            isinstance(self.user_id, int) and self.user_id > 0
            and str(self.user_role or "").lower() in {"owner", "admin", "user"}
            and expected_domain == domain
            and permission_role in expected_roles
        )


# ═══════════════════════════════════════════════════════════════
# 首批核心 Tool 定义
# ═══════════════════════════════════════════════════════════════

CORE_TOOLS: List[ToolDefinition] = [
    ToolDefinition(
        tool_id="note_search",
        name="笔记搜索",
        description="搜索小红书/微博/B站笔记内容，支持关键词、时间范围、情感过滤",
        category="monitor",
        keywords=["笔记", "搜索", "帖子", "内容", "note", "search", "小红书"],
        params=[
            ToolParam("query", "string", True, "搜索关键词"),
            ToolParam("platform", "string", False, "平台: xiaohongshu/weibo/bilibili/all", "all",
                      ["xiaohongshu", "weibo", "bilibili", "all"]),
            ToolParam("limit", "integer", False, "返回数量", 20),
            ToolParam("sentiment", "string", False, "情感过滤: positive/negative/neutral/all", "all",
                      ["positive", "negative", "neutral", "all"]),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/notes/search",
    ),
    ToolDefinition(
        tool_id="event_query",
        name="事件查询",
        description="查询舆情事件列表和详情，支持事件类型、严重程度过滤",
        category="events",
        keywords=["事件", "event", "传播", "聚类", "热点", "事件中心"],
        params=[
            ToolParam("event_type", "string", False, "事件类型: marketing/spread/opinion/all", "all",
                      ["marketing", "spread", "opinion", "all"]),
            ToolParam("severity", "string", False, "严重程度: low/medium/high/all", "all",
                      ["low", "medium", "high", "all"]),
            ToolParam("limit", "integer", False, "返回数量", 20),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/events",
    ),
    ToolDefinition(
        tool_id="trend_query",
        name="趋势查询",
        description="查询舆情趋势数据，包括声量趋势、情感趋势、风险趋势",
        category="analysis",
        keywords=["趋势", "trend", "声量", "走势", "环比", "统计"],
        params=[
            ToolParam("metric", "string", False, "指标: volume/sentiment/risk/all", "all",
                      ["volume", "sentiment", "risk", "all"]),
            ToolParam("days", "integer", False, "时间范围(天)", 7),
            ToolParam("granularity", "string", False, "粒度: day/hour", "day", ["day", "hour"]),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/analysis/trend",
    ),
    ToolDefinition(
        tool_id="risk_alert_query",
        name="风险预警查询",
        description="查询风险预警列表，支持风险等级、状态过滤",
        category="risk",
        keywords=["风险", "预警", "alert", "危机", "高风险", "负面"],
        params=[
            ToolParam("level", "string", False, "风险等级: low/medium/high/critical/all", "all",
                      ["low", "medium", "high", "critical", "all"]),
            ToolParam("status", "string", False, "状态: active/resolved/all", "all",
                      ["active", "resolved", "all"]),
            ToolParam("limit", "integer", False, "返回数量", 20),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/alerts",
    ),
    ToolDefinition(
        tool_id="collection_trigger",
        name="采集触发",
        description="触发指定平台的采集任务（需人工审批）",
        category="collection",
        keywords=["采集", "collect", "触发", "更新", "crawl", "小红书采集"],
        params=[
            ToolParam("platform", "string", True, "平台: xiaohongshu/weibo/bilibili", "",
                      ["xiaohongshu", "weibo", "bilibili"]),
            ToolParam("keyword", "string", False, "采集关键词"),
            ToolParam("max_pages", "integer", False, "最大采集页数", 5),
        ],
        permission_level=ToolPermissionLevel.WRITE,
        risk_level=ToolRiskLevel.HIGH,
        requires_approval=True,
        api_route="/api/collect/trigger",
    ),
    ToolDefinition(
        tool_id="report_generate",
        name="报告生成",
        description="生成舆情日报/周报/月报/专题报告",
        category="reports",
        keywords=["报告", "report", "日报", "周报", "月报", "生成", "导出"],
        params=[
            ToolParam("report_type", "string", True, "报告类型: daily/weekly/monthly/special", "",
                      ["daily", "weekly", "monthly", "special"]),
            ToolParam("start_date", "string", False, "开始日期 YYYY-MM-DD"),
            ToolParam("end_date", "string", False, "结束日期 YYYY-MM-DD"),
        ],
        permission_level=ToolPermissionLevel.ANALYZE,
        risk_level=ToolRiskLevel.MEDIUM,
        requires_approval=False,
        api_route="/api/reports/generate",
    ),
    ToolDefinition(
        tool_id="intelligence_search",
        name="情报检索",
        description="检索情报资产库（品牌知识、案例、研究报告）",
        category="intelligence",
        keywords=["情报", "知识", "案例", "intelligence", "检索", "资料库"],
        params=[
            ToolParam("query", "string", True, "检索关键词"),
            ToolParam("sub_library", "string", False, "子库过滤"),
            ToolParam("limit", "integer", False, "返回数量", 20),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/intelligence/library",
    ),
    ToolDefinition(
        tool_id="brand_query",
        name="品牌业态查询",
        description="查询场内品牌信息、业态分布、品牌官网",
        category="brands",
        keywords=["品牌", "业态", "brand", "商户", "店铺", "楼层", "场内品牌"],
        params=[
            ToolParam("keyword", "string", False, "品牌关键词"),
            ToolParam("category", "string", False, "业态分类"),
            ToolParam("floor", "string", False, "楼层"),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/brands",
    ),
    ToolDefinition(
        tool_id="ai_analyze",
        name="AI分析",
        description="调用 AI 网关进行文本分析、摘要、情感判断",
        category="ai",
        keywords=["AI", "分析", "analyze", "摘要", "情感", "总结", "glm"],
        params=[
            ToolParam("text", "string", True, "待分析文本"),
            ToolParam("task_type", "string", False, "任务类型: summary/sentiment/risk/analysis", "analysis",
                      ["summary", "sentiment", "risk", "analysis"]),
            ToolParam("model", "string", False, "模型: glm-4.5-air/glm-5.3", "glm-4.5-air",
                      ["glm-4.5-air", "glm-5.3"]),
        ],
        permission_level=ToolPermissionLevel.ANALYZE,
        risk_level=ToolRiskLevel.MEDIUM,
        api_route="/api/ai/analyze",
    ),
    ToolDefinition(
        tool_id="skill_execute",
        name="Skill执行",
        description="执行已注册的 Skill（通过 skill_execution_chain）",
        category="skill",
        keywords=["skill", "技能", "执行", "skill_execution"],
        params=[
            ToolParam("skill_id", "string", True, "Skill ID"),
            ToolParam("inputs", "object", False, "Skill 输入参数"),
            ToolParam("action_type", "string", False, "动作类型: READ/ANALYZE/WRITE", "ANALYZE",
                      ["READ", "ANALYZE", "WRITE"]),
        ],
        permission_level=ToolPermissionLevel.ANALYZE,
        risk_level=ToolRiskLevel.MEDIUM,
        api_route="/api/skills/execute",
    ),
    ToolDefinition(
        tool_id="task_status",
        name="任务状态查询",
        description="查询 AI 任务执行状态和结果",
        category="system",
        keywords=["任务", "task", "状态", "status", "进度"],
        params=[
            ToolParam("task_id", "string", True, "任务 ID"),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/ai/tasks",
    ),
    ToolDefinition(
        tool_id="system_health",
        name="系统健康检查",
        description="检查系统运行状态、采集状态、AI网关健康度",
        category="system",
        keywords=["健康", "health", "状态", "系统", "监控", "运行"],
        params=[
            ToolParam("check_type", "string", False, "检查类型: all/collection/ai/system", "all",
                      ["all", "collection", "ai", "system"]),
        ],
        permission_level=ToolPermissionLevel.READ,
        risk_level=ToolRiskLevel.LOW,
        api_route="/api/health",
    ),
]


class CapabilityRouter:
    """统一 Tool 路由层。

    职责：
      1. Tool 注册（内存注册表，启动时加载核心 Tool + 从 skills_registry 加载）
      2. Tool 选择（基于 goal + context + 关键词匹配 + Skill Memory 成功率）
      3. Tool 执行（复用 skill_execution_chain：permission → firewall → effect_fence → execute → evidence）
    """

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False,
                 skill_memory=None,
                 actor_authorizer: Optional[Callable[[ToolActorContext, ToolDefinition], bool]] = None):
        self.db_path = db_path
        self.enabled = enabled
        self._tools: Dict[str, ToolDefinition] = {}
        self._dispatch_lock = threading.RLock()
        self.skill_memory = skill_memory
        # No production call site currently supplies trusted actor binding.
        # Keep execution disabled by default until an authenticated server
        # integration provides and tests this authorization boundary.
        self._actor_authorizer = actor_authorizer
        self._execution_history: List[ToolExecutionResult] = []
        self._register_core_tools()

    # ── Tool 注册 ────────────────────────────────────────────────

    def _register_core_tools(self) -> None:
        """注册首批核心 Tool。"""
        for tool in CORE_TOOLS:
            self._tools[tool.tool_id] = deepcopy(tool)

    def register_tool(self, tool: ToolDefinition) -> bool:
        """注册一个新 Tool。"""
        if not self.enabled:
            return False
        with self._dispatch_lock:
            old = self._tools.get(tool.tool_id)
            if old and (old.origin, old.resource_uri) != (tool.origin, tool.resource_uri):
                return False  # An ID cannot shadow another origin/URI.
            self._tools[tool.tool_id] = tool
            return True

    def unregister_tool(self, tool_id: str) -> bool:
        with self._dispatch_lock:
            return self._tools.pop(tool_id, None) is not None

    @staticmethod
    def _resource_identity(tool):
        rows = tool.resource_manifest
        if not isinstance(rows, list):
            raise FormationError("TOOL_CONTENT_MANIFEST_INVALID")
        uris = set()
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"uri", "sha256", "size"}
                    or not isinstance(row["uri"], str) or not row["uri"]
                    or row["uri"] in uris or type(row["size"]) is not int or row["size"] < 0
                    or not isinstance(row["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
                raise FormationError("TOOL_CONTENT_MANIFEST_INVALID")
            uris.add(row["uri"])
        return sorted(deepcopy(rows), key=lambda row: row["uri"])

    def form_step(self, step, context, *, expected=None):
        """Resolve once; hold that implementation through Loop admission/call."""
        with self._dispatch_lock:
            tool = self._tools.get(step.tool)
            if not self.enabled or not tool or not tool.enabled:
                raise FormationError("TOOL_RUNTIME_UNAVAILABLE")
            if not tool.origin or not tool.resource_uri or not callable(tool.handler):
                raise FormationError("TOOL_IMPLEMENTATION_NOT_BOUND")
            valid, reason = tool.validate_params(step.params)
            if not valid:
                raise FormationError("TOOL_FORMATION_PARAMETERS_INVALID")
            handler = tool.handler
            provider = tool.identity_provider

            def identity():
                if (self._tools.get(step.tool) is not tool or tool.handler is not handler
                        or not self.enabled or not tool.enabled):
                    raise FormationError("TOOL_IMPLEMENTATION_CHANGED")
                if tool.identity_provider is not provider:
                    raise FormationError("TOOL_RUNTIME_IDENTITY_CHANGED")
                resources = self._resource_identity(tool)
                content_digest = digest(resources)
                # The existing registry/package owner supplies this current
                # content-admission state. It is not a local permission grant.
                if resources:
                    state = tool.identity_provider() if callable(tool.identity_provider) else None
                    if not isinstance(state, dict) or state.get("content_manifest_digest") != content_digest:
                        raise FormationError("TOOL_CONTENT_REAPPROVAL_REQUIRED")
                effect = {ToolPermissionLevel.READ: "READ", ToolPermissionLevel.ANALYZE: "ANALYZE",
                          ToolPermissionLevel.WRITE: "WRITE", ToolPermissionLevel.ADMIN: "WRITE"}[tool.permission_level]
                return {"schema": "lumenis-formed-call:v1", "origin": tool.origin,
                        "resource_uri": tool.resource_uri, "effect": effect,
                        "descriptor_sha256": digest(tool.to_dict()),
                        "implementation_sha256": implementation_identity(handler, tool.dependency_paths),
                        "runtime_sha256": runtime_identity(tool.identity_provider),
                        "content_sha256": content_digest, "request_sha256": request_identity(step),
                        "context_sha256": context_identity(context)}

            def invoke(captured_step, _context):
                data = handler(**captured_step.params)
                # A real handler error remains an error, including uncertain
                # effects; dictionary truthiness is not completion evidence.
                return _normalize_handler_result(data)

            return FormedCall(step=step, context=context, identity=identity, invoke=invoke,
                              lock=self._dispatch_lock, expected=expected)

    def read_supporting_resource(self, step, context, binding, uri, *, actor_context=None):
        """Lazy integrity-checked bytes; reading a nested skill never activates it."""
        selected = self.form_step(step, context, expected=binding)
        with selected.guard(step, context):
            tool = self._tools[step.tool]
            row = next((r for r in self._resource_identity(tool) if r["uri"] == uri), None)
            reader = tool.resource_reader
            if not row or not callable(reader):
                raise FormationError("TOOL_CONTENT_UNAVAILABLE")
            if (not isinstance(actor_context, ToolActorContext) or not actor_context.valid()
                    or self._actor_authorizer is None
                    or self._actor_authorizer(actor_context, tool) is not True):
                raise FormationError("TOOL_CONTENT_ACTOR_NOT_AUTHORIZED")
            from lumenis.shared.agents.skills.execution import (
                SkillExecutionContext, ActionType, check_permission, action_firewall, effect_fence)
            read_context = SkillExecutionContext(
                skill_id=tool.tool_id, user_id=actor_context.user_id,
                permission_role=actor_context.permission_role, domain=actor_context.domain_id,
                product=actor_context.product_id, task="read supporting skill resource",
                input_payload={"resource_uri": uri}, action_type=ActionType.READ)
            for check in (lambda ctx: check_permission(ctx, user_role=actor_context.user_role),
                          action_firewall, effect_fence):
                if check(read_context).get("allowed") is not True:
                    raise FormationError("TOOL_CONTENT_PERMISSION_DENIED")
            selected.assert_current(step, context)
            data = reader(uri)
            selected.assert_current(step, context)
            import hashlib
            if (not isinstance(data, bytes) or len(data) != row["size"]
                    or hashlib.sha256(data).hexdigest() != row["sha256"]):
                raise FormationError("TOOL_CONTENT_INTEGRITY_FAILED")
            return data

    def list_tools(self, category: Optional[str] = None,
                   risk_level: Optional[ToolRiskLevel] = None) -> List[ToolDefinition]:
        """列出已注册 Tool。"""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if risk_level:
            tools = [t for t in tools if t.risk_level == risk_level]
        return sorted(tools, key=lambda t: t.tool_id)

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    # ── Tool 选择 ────────────────────────────────────────────────

    def select_tool(self, goal: str,
                    context: Optional[Dict[str, Any]] = None) -> Optional[ToolDefinition]:
        """基于目标 + 上下文选择最合适的 Tool。

        选择策略：
          1. 关键词匹配（goal 与 tool.keywords/description 匹配度）
          2. 风险等级最低优先
          3. Skill Memory 成功率参考（如果有对应 Skill）
          4. 上下文偏好（如 current_page 信号）
        """
        if not self.enabled or not goal:
            return None
        goal_lower = goal.lower()
        tokens = [t for t in re.split(r"[\s,，。！？、/|:：;；]+", goal_lower) if len(t) >= 2]

        scored: List[Tuple[float, ToolDefinition]] = []
        for tool in self._tools.values():
            if not tool.enabled:
                continue
            # 关键词匹配得分
            score = 0.0
            for kw in tool.keywords:
                if kw.lower() in goal_lower:
                    score += 3.0
            # 描述匹配
            desc = tool.description.lower()
            score += sum(0.5 for t in tokens if t in desc)
            # 名称匹配
            if tool.name.lower() in goal_lower:
                score += 5.0

            if score > 0:
                # 风险等级惩罚（低风险优先）
                risk_penalty = {
                    ToolRiskLevel.LOW: 0,
                    ToolRiskLevel.MEDIUM: 0.5,
                    ToolRiskLevel.HIGH: 1.5,
                    ToolRiskLevel.CRITICAL: 3.0,
                }.get(tool.risk_level, 1.0)
                score -= risk_penalty

                # Skill Memory 成功率加成
                if self.skill_memory:
                    stats = self.skill_memory.get_skill_stats(tool.tool_id)
                    if stats["total"] > 0:
                        score += stats["success_rate"] * 2.0

                scored.append((score, tool))

        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def select_tools(self, goal: str, limit: int = 3,
                     context: Optional[Dict[str, Any]] = None) -> List[ToolDefinition]:
        """选择 Top-N 候选 Tool。"""
        if not self.enabled or not goal:
            return []
        goal_lower = goal.lower()
        tokens = [t for t in re.split(r"[\s,，。！？、/|:：;；]+", goal_lower) if len(t) >= 2]

        scored: List[Tuple[float, ToolDefinition]] = []
        for tool in self._tools.values():
            if not tool.enabled:
                continue
            score = 0.0
            for kw in tool.keywords:
                if kw.lower() in goal_lower:
                    score += 3.0
            desc = tool.description.lower()
            score += sum(0.5 for t in tokens if t in desc)
            if tool.name.lower() in goal_lower:
                score += 5.0
            if score > 0:
                scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]

    # ── Tool 执行（复用 skill_execution_chain） ──────────────────

    @_serialized_dispatch
    def execute_tool(self, tool_id: str, params: Dict[str, Any],
                     user_role: Optional[str] = None,
                     agent_id: str = "agent_runtime",
                     task_id: Optional[str] = None,
                     actor_context: Optional[ToolActorContext] = None,
                     formation: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        """执行 Tool，经过完整安全链路。

        链路：参数校验 → permission_gate → action_firewall → effect_fence → 执行 → evidence
        复用 skill_execution_chain 的执行上下文和安全检查。
        """
        import time
        start = time.time()
        result = ToolExecutionResult(tool_id=tool_id, success=False)

        if not self.enabled:
            result.error = "capability router disabled"
            return result

        tool = self._tools.get(tool_id)
        if not tool:
            result.error = f"tool not found: {tool_id}"
            return result

        # 1. 参数校验
        valid, msg = tool.validate_params(params)
        if not valid:
            result.error = f"param validation failed: {msg}"
            return result

        if not isinstance(actor_context, ToolActorContext) or not actor_context.valid():
            result.error = "trusted actor context required"
            return result
        if user_role and user_role != actor_context.user_role:
            result.error = "caller role conflicts with trusted actor context"
            return result
        if self._actor_authorizer is None:
            result.error = "trusted actor authorization validator not configured"
            return result
        from agent_runtime.planner import PlanStep
        call_step = PlanStep(step_id=f"{task_id or 'direct'}:{tool_id}", tool=tool_id,
                             action="execute registered tool", params=deepcopy(params))
        call_context = {"actor_id": actor_context.user_id, "domain_id": actor_context.domain_id,
                        "role": actor_context.user_role, "product": actor_context.product_id,
                        "permission_role": actor_context.permission_role}
        try:
            selected = self.form_step(call_step, call_context, expected=formation)
            result.formation = selected.binding
        except FormationError as exc:
            result.error = str(exc)
            result.reconciliation_required = True
            return result
        try:
            authorized = self._actor_authorizer(actor_context, tool)
        except Exception as exc:
            result.error = f"trusted actor authorization failed: {exc}"
            result.duration_ms = int((time.time() - start) * 1000)
            return result
        if authorized is not True:
            result.error = "actor is not authorized for this product tool"
            return result
        user_role = actor_context.user_role
        # Admission receives exactly the captured arguments, rather than a
        # mutable caller dictionary that can diverge from the eventual handler.
        params = deepcopy(call_step.params)

        # 2. 构建执行上下文（复用 canonical Shared Skills execution owner）
        try:
            from lumenis.shared.agents.skills.execution import (
                SkillExecutionContext, ActionType, check_permission,
                action_firewall, effect_fence, execute_skill, build_evidence,
                evaluate_execution, write_trace,
            )
        except Exception as exc:
            result.error = f"canonical skill execution owner unavailable: {exc}"
            result.duration_ms = int((time.time() - start) * 1000)
            return result

        action_type = ActionType.WRITE if tool.permission_level in {ToolPermissionLevel.WRITE, ToolPermissionLevel.ADMIN} else (
            ActionType.ANALYZE if tool.permission_level == ToolPermissionLevel.ANALYZE
            else ActionType.READ
        )

        ctx = SkillExecutionContext(
            skill_id=tool_id,
            user_id=actor_context.user_id,
            permission_role=actor_context.permission_role,
            domain=actor_context.domain_id,
            product=actor_context.product_id,
            task=goal_from_params(tool_id, params),
            input_payload=params,
            action_type=action_type,
        )

        # 3. Permission Gate
        try:
            perm_result = check_permission(ctx, user_role=user_role)
            result.permission_result = perm_result
            if not perm_result.get("allowed", False):
                result.error = f"permission denied: {perm_result.get('reason', 'unknown')}"
                result.duration_ms = int((time.time() - start) * 1000)
                return result
        except Exception as e:
            result.error = f"permission check error: {e}"
            result.duration_ms = int((time.time() - start) * 1000)
            return result

        # 4. Action Firewall
        try:
            fw_result = action_firewall(ctx)
            result.firewall_result = fw_result
            if not fw_result.get("allowed", False):
                result.error = f"firewall denied: {fw_result.get('reason', 'unknown')}"
                result.duration_ms = int((time.time() - start) * 1000)
                return result
        except Exception as e:
            result.error = f"firewall error: {e}"
            result.duration_ms = int((time.time() - start) * 1000)
            return result

        # 5. Effect Fence
        try:
            fence_result = effect_fence(ctx)
            result.effect_fence_result = fence_result
            if not fence_result.get("allowed", False):
                result.error = f"effect fence denied: {fence_result.get('reason', 'unknown')}"
                result.duration_ms = int((time.time() - start) * 1000)
                return result
        except Exception as e:
            result.error = f"effect fence error: {e}"
            result.duration_ms = int((time.time() - start) * 1000)
            return result

        # 6. 执行
        try:
            # The selected handler and immutable arguments survive every
            # admission check. Do not re-resolve an ID after Permission.
            if digest(ctx.input_payload) != digest(call_step.params):
                raise FormationError("TOOL_ADMISSION_INPUT_CHANGED")
            if (ctx.user_id, ctx.domain, ctx.product, ctx.permission_role, ctx.action_type) != (
                    actor_context.user_id, actor_context.domain_id, actor_context.product_id,
                    actor_context.permission_role, action_type):
                raise FormationError("TOOL_ADMISSION_CONTEXT_CHANGED")
            exec_result = selected.invoke(call_step, call_context)
            ctx.execute_result = exec_result
            result.success = exec_result.get("success") is True
            result.data = exec_result.get("result") if result.success else None
            if not result.success:
                result.error = exec_result.get("error", "execution failed")
        except FormationError as e:
            result.error = str(e)
            result.reconciliation_required = True
        except Exception as e:
            result.error = f"execution error: {e}"

        # 7. Evidence: execution may already have happened; do not replay it.
        try:
            ctx.evidence = build_evidence(ctx)
            ctx.evaluation = evaluate_execution(ctx)
            result.evidence = ctx.evidence
        except Exception:
            result.success = False
            result.reconciliation_required = True
            result.error = "TOOL_EVIDENCE_UNAVAILABLE"

        # 8. The existing trace owner returns False on persistence failure.
        try:
            ctx.status = (ctx.status.__class__.COMPLETED if result.success
                          else ctx.status.__class__.FAILED)
            ctx.error = result.error
            duration = int((time.time() - start) * 1000)
            if write_trace(ctx, duration_ms=duration) is not True:
                raise RuntimeError("TOOL_TRACE_NOT_COMMITTED")
        except Exception:
            result.success = False
            result.reconciliation_required = True
            result.error = result.error or "TOOL_TRACE_NOT_COMMITTED"

        result.duration_ms = int((time.time() - start) * 1000)
        self._execution_history.append(result)

        # 更新 Skill Memory 反馈
        if self.skill_memory and not result.reconciliation_required:
            self.skill_memory.record_feedback(tool_id, result.success, result.duration_ms)

        return result

    def _execute_direct(self, tool: ToolDefinition, params: Dict[str, Any],
                        result: ToolExecutionResult, start: float) -> ToolExecutionResult:
        """无 skill_execution_chain 时的直接执行 fallback。"""
        try:
            if tool.handler:
                returned = _normalize_handler_result(tool.handler(**params))
                result.success = returned.get("success") is True
                result.data = returned.get("result") if result.success else None
                result.error = None if result.success else returned.get("error", "TOOL_HANDLER_FAILED")
            else:
                result.error = f"no handler for tool {tool.tool_id} (skill_execution_chain unavailable)"
        except Exception as e:
            result.error = f"execution error: {e}"
        result.duration_ms = int((__import__("time").time() - start) * 1000)
        return result

    # ── 统计 ─────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "registered_tools": len(self._tools),
            "tools_by_category": self._count_by_category(),
            "tools_by_risk": self._count_by_risk(),
            "execution_history_size": len(self._execution_history),
        }

    def _count_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for t in self._tools.values():
            counts[t.category] = counts.get(t.category, 0) + 1
        return counts

    def _count_by_risk(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for t in self._tools.values():
            counts[t.risk_level.value] = counts.get(t.risk_level.value, 0) + 1
        return counts


def goal_from_params(tool_id: str, params: Dict[str, Any]) -> str:
    """从参数生成 task 描述。"""
    return f"tool:{tool_id} params={json.dumps(params, ensure_ascii=False)[:200]}"
