# -*- coding: utf-8 -*-
"""ZBC AI Task Parser — 自然语言任务解析器（Production-Ready）

调用链位置：User → AI Task → Task Parser → Intent → Agent → ...

设计原则：
  1. 规则优先（deterministic），AI 仅作为可选增强，断网/无 key 时仍可解析。
  2. 解析失败显式标记 intent=unknown，不得静默猜测为高风险操作。
  3. 输出结构化 ParsedTask：intent / entities / parameters / context / risk_hint。
  4. 不修改 SUBJECT_WORDS 等生产口径，仅读取。
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. Intent 枚举（与任务书一致）
# ═══════════════════════════════════════════════════════════════

class Intent(str, Enum):
    QUERY_DATA = "query_data"                # 查询数据
    SUMMARIZE = "summarize"                  # 总结
    CLASSIFY = "classify"                    # 分类
    COMPARE = "compare"                      # 对比
    REASON = "reason"                        # 推理
    ANOMALY_DETECTION = "anomaly_detection" # 异常发现
    RISK_EXPLAIN = "risk_explain"            # 风险解释
    OPEN_BROWSER = "open_browser"            # 打开 Browser
    WEB_SEARCH = "web_search"                # 搜索网页
    PAGE_OPERATION = "page_operation"        # 页面操作
    GENERATE_REPORT = "generate_report"      # 生成报告
    CHAT = "chat"                            # 闲聊/问候/对话（L0自动通过）
    UNKNOWN = "unknown"                       # 未知（显式标记，fail-closed）


# ═══════════════════════════════════════════════════════════════
# 2. 风险等级 L0-L4（与任务书 Permission Matrix 对齐）
# ═══════════════════════════════════════════════════════════════

class TaskRiskLevel(str, Enum):
    L0 = "L0"  # Read (Auto)
    L1 = "L1"  # Low-risk (Auto+Trace)
    L2 = "L2"  # External side effect (Permission+Verify)
    L3 = "L3"  # Sensitive (Human Approval)
    L4 = "L4"  # Financial/irreversible (Human Approval+Explicit Confirm)


# ═══════════════════════════════════════════════════════════════
# 3. 硬编码高风险关键词（永久 DENY 或需 Admin）
# ═══════════════════════════════════════════════════════════════

# 永久 DENY：支付
_PERMANENT_DENY_PATTERNS = [
    r"(支付|付款|转账|充值|提现|pay\s*now|payment|transaction.*money)",
]

# 需 Admin：删除数据 / 修改核心配置 / 修改 Production Truth / 修改代码 / Deploy
_ADMIN_REQUIRED_PATTERNS = [
    r"(删除数据|清空.*表|drop\s*table|truncate|delete\s+from|删库|删表|清空数据库)",
    r"(修改.*配置|改配置|config.*modify|修改核心配置|改核心配置)",
    r"(修改.*生产|production.*truth|改生产数据|修改生产数据)",
    r"(修改代码|改代码|commit|push|deploy|部署|上线|改源码)",
]

# 需人工审批（L3）：上传文件 / 登录 / 发布内容 / 发送消息
_HUMAN_APPROVAL_PATTERNS = [
    r"(上传文件|上传|upload)",
    r"(登录|login|sign\s*in|扫码登录)",
    r"(发布内容|发布|发笔记|发微博|publish|post)",
    r"(发送消息|发消息|私信|send\s*message|dm)",
]


# ═══════════════════════════════════════════════════════════════
# 4. Intent 规则匹配表（关键词 → Intent）
#    按优先级排序，先匹配高特异性规则
# ═══════════════════════════════════════════════════════════════

_INTENT_RULES: List[Tuple[Intent, List[str]]] = [
    (Intent.CHAT, [
        "你好", "您好", "嗨", "hi", "hello", "在吗", "在不在", "哈喽", "喂",
        "早上好", "下午好", "晚上好", "你好啊", "你好呀", "在么", "在嘛",
        "hey", "yo", "sup", "你好吗", "最近怎么样", "忙吗",
    ]),
    (Intent.GENERATE_REPORT, [
        "生成报告", "生成日报", "生成周报", "生成月报", "出报告", "写报告",
        "report", "daily report", "weekly report",
    ]),
    (Intent.OPEN_BROWSER, [
        "打开浏览器", "打开browser", "打开页面", "open browser", "launch browser",
    ]),
    (Intent.WEB_SEARCH, [
        "搜索网页", "百度", "谷歌", "google", "bing", "搜索一下", "搜一下",
        "web search", "search the web",
    ]),
    (Intent.PAGE_OPERATION, [
        "点击", "滚动", "截图", "填写表单", "页面操作", "page operation",
        "click", "scroll", "screenshot",
    ]),
    (Intent.ANOMALY_DETECTION, [
        "异常", "异常发现", "找异常", "数据异常", "anomaly", "outlier",
        "突增", "突降", "波动",
    ]),
    (Intent.RISK_EXPLAIN, [
        "风险解释", "解释风险", "风险原因", "为什么风险", "risk explain",
        "负面原因", "舆情风险",
    ]),
    (Intent.COMPARE, [
        "对比", "比较", "compare", "vs", " versus ", "差异",
    ]),
    (Intent.CLASSIFY, [
        "分类", "归类", "classify", "categorize", "标签",
    ]),
    (Intent.SUMMARIZE, [
        "总结", "摘要", "概括", "summarize", "summary", "归纳",
    ]),
    (Intent.REASON, [
        "推理", "分析原因", "为什么", "reason", "根因", "root cause",
        "推导",
    ]),
    (Intent.QUERY_DATA, [
        "查询", "查一下", "看看", "有多少", "统计", "数据", "query",
        "多少条", "列表", "详情",
    ]),
]


# ═══════════════════════════════════════════════════════════════
# 5. 实体提取（简单规则，可扩展）
# ═══════════════════════════════════════════════════════════════

_ENTITY_PATTERNS = {
    "date": re.compile(
        r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?|"
        r"\d{1,2}月\d{1,2}日|今天|昨天|前天|本周|上周|本月|上月)"
    ),
    "platform": re.compile(
        r"(小红书|微博|B站|哔哩哔哩|抖音|微信|xhs|weibo|bilibili|douyin)",
        re.IGNORECASE,
    ),
    "brand": re.compile(
        r"(太古汇|taikoo|广州太古汇|上海太古汇|北京太古汇|成都太古汇|香港太古汇)",
        re.IGNORECASE,
    ),
    "metric": re.compile(
        r"(曝光|互动|点赞|收藏|评论|转发|阅读|粉丝|声量|舆情量|负面量|风险)"
    ),
}


def _extract_entities(text: str) -> Dict[str, List[str]]:
    entities: Dict[str, List[str]] = {}
    patterns = dict(_ENTITY_PATTERNS)
    try:
        from subject_registry import registered_subject_names
        names = sorted(registered_subject_names(), key=len, reverse=True)
        if names:
            patterns["brand"] = re.compile("(" + "|".join(re.escape(n) for n in names) + ")", re.IGNORECASE)
    except Exception:
        pass
    for etype, pattern in patterns.items():
        matches = pattern.findall(text)
        if matches:
            # 去重保序
            seen = set()
            unique = []
            for m in matches:
                key = str(m).lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(str(m))
            entities[etype] = unique
    return entities


# ═══════════════════════════════════════════════════════════════
# 6. ParsedTask 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class ParsedTask:
    task_id: str
    raw_input: str
    intent: Intent
    confidence: float                       # 0.0 - 1.0
    entities: Dict[str, List[str]] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    risk_level: TaskRiskLevel = TaskRiskLevel.L0
    risk_reason: str = ""
    permanent_deny: bool = False
    admin_required: bool = False
    human_approval_required: bool = False
    parsed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    parser_version: str = "task-parser-v1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["intent"] = self.intent.value
        d["risk_level"] = self.risk_level.value
        return d


# ═══════════════════════════════════════════════════════════════
# 7. TaskParser 核心类
# ═══════════════════════════════════════════════════════════════

class TaskParser:
    """自然语言任务解析器。

    用法：
        parser = TaskParser()
        parsed = parser.parse("帮我查一下今天太古汇的舆情量", context={"current_page": "/dashboard"})
    """

    def __init__(self, enable_ai_enhancement: bool = True):
        self.enable_ai_enhancement = enable_ai_enhancement
        self._compiled_permanent_deny = [
            re.compile(p, re.IGNORECASE) for p in _PERMANENT_DENY_PATTERNS
        ]
        self._compiled_admin = [
            re.compile(p, re.IGNORECASE) for p in _ADMIN_REQUIRED_PATTERNS
        ]
        self._compiled_human = [
            re.compile(p, re.IGNORECASE) for p in _HUMAN_APPROVAL_PATTERNS
        ]

    # ──────────────────────────────────────────────────────────
    # 主入口
    # ──────────────────────────────────────────────────────────

    def parse(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> ParsedTask:
        """解析用户自然语言输入为结构化任务。

        Args:
            user_input: 原始用户输入
            context: 上下文（当前页面 / ZBC 数据 / 用户权限等）
            task_id: 预分配 task_id（None 则自动生成）

        Returns:
            ParsedTask
        """
        if not user_input or not user_input.strip():
            return ParsedTask(
                task_id=task_id or self._gen_id(),
                raw_input=user_input or "",
                intent=Intent.UNKNOWN,
                confidence=0.0,
                risk_level=TaskRiskLevel.L0,
                risk_reason="empty input",
            )

        text = user_input.strip()
        tid = task_id or self._gen_id()

        # 1. 永久 DENY 检测（最高优先级）
        permanent_deny = any(p.search(text) for p in self._compiled_permanent_deny)

        # 2. Admin 需求检测
        admin_required = any(p.search(text) for p in self._compiled_admin)

        # 3. 人工审批检测
        human_approval = any(p.search(text) for p in self._compiled_human)

        # 4. Intent 规则匹配
        intent, confidence = self._match_intent(text)

        # 5. 实体提取
        entities = _extract_entities(text)

        # 6. 风险等级判定
        risk_level, risk_reason = self._determine_risk(
            intent, permanent_deny, admin_required, human_approval, text
        )

        # 7. 参数提取（从实体 + 上下文）
        parameters = self._extract_parameters(text, entities, context or {})

        return ParsedTask(
            task_id=tid,
            raw_input=text,
            intent=intent,
            confidence=confidence,
            entities=entities,
            parameters=parameters,
            context=context or {},
            risk_level=risk_level,
            risk_reason=risk_reason,
            permanent_deny=permanent_deny,
            admin_required=admin_required,
            human_approval_required=human_approval,
        )

    # ──────────────────────────────────────────────────────────
    # Intent 匹配
    # ──────────────────────────────────────────────────────────

    def _match_intent(self, text: str) -> Tuple[Intent, float]:
        """基于关键词规则匹配 Intent。返回 (intent, confidence)。"""
        text_lower = text.lower()
        best_intent = Intent.UNKNOWN
        best_score = 0.0

        for intent, keywords in _INTENT_RULES:
            score = 0.0
            for kw in keywords:
                if kw.lower() in text_lower:
                    # 长关键词权重更高
                    score += min(0.4, 0.15 + len(kw) * 0.01)
            if score > best_score:
                best_score = score
                best_intent = intent

        if best_intent == Intent.UNKNOWN:
            return Intent.UNKNOWN, 0.0

        # confidence 封顶 0.95（规则解析不可能 100% 确定）
        confidence = min(0.95, best_score)
        return best_intent, confidence

    # ──────────────────────────────────────────────────────────
    # 风险等级判定
    # ──────────────────────────────────────────────────────────

    def _determine_risk(
        self,
        intent: Intent,
        permanent_deny: bool,
        admin_required: bool,
        human_approval: bool,
        text: str,
    ) -> Tuple[TaskRiskLevel, str]:
        """判定任务风险等级。"""
        if permanent_deny:
            return TaskRiskLevel.L4, "permanent deny: 支付类操作永久禁止"

        if admin_required:
            return TaskRiskLevel.L4, "admin required: 删除数据/修改配置/生产数据/代码/部署需 Admin"

        if human_approval:
            return TaskRiskLevel.L3, "human approval required: 上传/登录/发布/发送消息需人工审批"

        # 按 Intent 判定基础风险
        intent_risk_map = {
            Intent.CHAT: (TaskRiskLevel.L0, "casual chat, auto-pass"),
    Intent.QUERY_DATA: (TaskRiskLevel.L0, "read-only data query"),
            Intent.SUMMARIZE: (TaskRiskLevel.L0, "read-only summarization"),
            Intent.CLASSIFY: (TaskRiskLevel.L0, "read-only classification"),
            Intent.COMPARE: (TaskRiskLevel.L0, "read-only comparison"),
            Intent.REASON: (TaskRiskLevel.L1, "analysis with trace"),
            Intent.ANOMALY_DETECTION: (TaskRiskLevel.L1, "anomaly detection with trace"),
            Intent.RISK_EXPLAIN: (TaskRiskLevel.L1, "risk explanation with trace"),
            Intent.GENERATE_REPORT: (TaskRiskLevel.L1, "report generation with trace"),
            Intent.OPEN_BROWSER: (TaskRiskLevel.L2, "browser operation: permission+verify"),
            Intent.WEB_SEARCH: (TaskRiskLevel.L2, "external network: permission+verify"),
            Intent.PAGE_OPERATION: (TaskRiskLevel.L2, "page operation: permission+verify"),
            Intent.UNKNOWN: (TaskRiskLevel.L3, "unknown intent: fail-closed, human review"),
        }
        return intent_risk_map.get(intent, (TaskRiskLevel.L3, "unmapped intent: fail-closed"))

    # ──────────────────────────────────────────────────────────
    # 参数提取
    # ──────────────────────────────────────────────────────────

    def _extract_parameters(
        self,
        text: str,
        entities: Dict[str, List[str]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从实体和上下文中提取结构化参数。"""
        params: Dict[str, Any] = {}
        if entities.get("date"):
            params["date_range"] = entities["date"]
        if entities.get("platform"):
            params["platforms"] = entities["platform"]
        if entities.get("brand"):
            params["brands"] = entities["brand"]
        if entities.get("metric"):
            params["metrics"] = entities["metric"]
        # 上下文透传
        if context.get("current_page"):
            params["current_page"] = context["current_page"]
        if context.get("user_role"):
            params["user_role"] = context["user_role"]
        return params

    # ──────────────────────────────────────────────────────────
    # 工具
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _gen_id() -> str:
        return "task_" + uuid.uuid4().hex[:16]

    def list_intents(self) -> List[Dict[str, str]]:
        """列出所有支持的 Intent（用于 /api/ai/capabilities）。"""
        return [
            {"intent": i.value, "description": i.name.replace("_", " ").title()}
            for i in Intent
        ]


# ═══════════════════════════════════════════════════════════════
# 8. 全局单例
# ═══════════════════════════════════════════════════════════════

_default_parser: Optional[TaskParser] = None


def get_task_parser() -> TaskParser:
    global _default_parser
    if _default_parser is None:
        _default_parser = TaskParser()
    return _default_parser


def reset_task_parser() -> None:
    global _default_parser
    _default_parser = None


__all__ = [
    "Intent",
    "TaskRiskLevel",
    "ParsedTask",
    "TaskParser",
    "get_task_parser",
    "reset_task_parser",
]
