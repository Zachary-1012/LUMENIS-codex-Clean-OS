# -*- coding: utf-8 -*-
"""ZBC 最终验收判定器（Acceptance Gate）· 状态分层 + Evidence 闭环。

设计原则（严格对应用户《验收机制增量升级指令》）：
1. 保留现有 ×/✓、PARTIAL/VERIFIED、P0/P1、Commit、CI/Test，不重写；
2. CI Status（代码检查结果）与 Functional Status（功能真实验收）分离，二者独立；
3. 功能状态只由「真实源码 + 调用链 + 测试 + 真实运行 + Evidence + Verification」
   共同决定，CI PASS / 代码存在 / AI 说完成 都不能单独推出 VERIFIED；
4. 本模块是纯逻辑判定器（依赖注入证据，不耦合具体 DB / 不发网络请求），便于单测；
5. 最小增量：不删除任何历史状态、不改变 P0/P1 数据。

状态机：
    PLANNED → IMPLEMENTED → TESTED → VERIFIED → RELEASED → OPERATING
    任一验收条件未闭环 = PARTIAL（携带可读原因）
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================
# 枚举
# ============================================================
class CIStatus(str, Enum):
    """CI/自动化检查状态 —— 只回答「代码检查有没有通过」。"""
    PASS = "PASS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class FunctionalStatus(str, Enum):
    """功能验收状态 —— 回答「功能到底有没有真正验收完成」。"""
    PLANNED = "PLANNED"            # 源码都不存在
    IMPLEMENTED = "IMPLEMENTED"    # 源码存在、调用链可定位，但链路未闭环
    TESTED = "TESTED"              # 自动化测试通过，但没有真实运行验证
    VERIFIED = "VERIFIED"          # 真实运行+调用链+Evidence+验收条件全部成立
    RELEASED = "RELEASED"          # 已进入正式发布
    OPERATING = "OPERATING"        # 发布后持续有运行证据
    PARTIAL = "PARTIAL"            # 任一验收条件尚未完整闭环


# 8 个验收维度（Functional Acceptance 的构成）
class Dimension(str, Enum):
    SOURCE = "source"              # 真实源码存在
    CALL_GRAPH = "call_graph"      # 调用链闭环可定位
    RUNTIME = "runtime"            # 真实运行证据
    TEST = "test"                  # 自动化测试通过
    EVIDENCE = "evidence"          # Evidence 链可追溯
    VERIFICATION = "verification"  # 预期 vs 实际核验通过
    SECURITY = "security"          # 权限/安全核验通过
    REGRESSION = "regression"      # 回归无破坏


# PARTIAL 原因（一眼可见「为什么 PARTIAL」，对齐用户第六、八节）
class PartialReason(str, Enum):
    MISSING_SOURCE = "Missing Source"
    CALL_GRAPH_INCOMPLETE = "Call Graph Incomplete"
    MISSING_RUNTIME_EVIDENCE = "Missing Runtime Evidence"
    TEST_FAILED = "Test Failed"
    MISSING_TEST = "Missing Test"
    MISSING_EVIDENCE = "Missing Evidence"
    MISSING_E2E = "Missing E2E"
    MISSING_VERIFICATION = "Missing Verification"
    PERMISSION_NOT_VERIFIED = "Permission Not Verified"
    SECURITY_NOT_VERIFIED = "Security Not Verified"
    REGRESSION_NOT_VERIFIED = "Regression Not Verified"
    AI_CHAIN_NOT_CLOSED = "AI/Browser Chain Not Closed"


# VERIFIED 必须满足的维度（缺一不可）
REQUIRED_DIMENSIONS = [d.value for d in (
    Dimension.SOURCE, Dimension.CALL_GRAPH, Dimension.RUNTIME, Dimension.TEST,
    Dimension.EVIDENCE, Dimension.VERIFICATION, Dimension.SECURITY, Dimension.REGRESSION,
)]


# ============================================================
# 数据结构
# ============================================================
@dataclass
class AcceptanceInput:
    """单个功能/任务的验收输入证据（由调用方从源码/测试/运行/Evidence 聚合后注入）。"""
    task_id: str
    # CI 维度
    ci_passed: Optional[bool] = None                 # True=PASS False=FAILED None=UNKNOWN
    commit_sha: Optional[str] = None
    # 8 个功能维度：True=成立 False=不成立 None=无证据（按不成立处理但原因不同）
    source_exists: Optional[bool] = None
    call_graph_closed: Optional[bool] = None
    runtime_evidence: Optional[bool] = None
    test_passed: Optional[bool] = None
    evidence_recorded: Optional[bool] = None
    verification_passed: Optional[bool] = None
    security_verified: Optional[bool] = None
    regression_passed: Optional[bool] = None
    # AI / Browser 特殊验收：完整链路是否真实闭环（Task→...→Trace）
    ai_chain_closed: Optional[bool] = None
    is_ai_or_browser: bool = False
    # 已发布 / 持续运行（用于 RELEASED / OPERATING 判定）
    is_released: bool = False
    has_continuous_runtime: bool = False
    # 备注/证据指针（可追溯，不允许只给百分比）
    evidence_refs: Dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def dimension_map(self) -> Dict[str, Optional[bool]]:
        return {
            Dimension.SOURCE.value: self.source_exists,
            Dimension.CALL_GRAPH.value: self.call_graph_closed,
            Dimension.RUNTIME.value: self.runtime_evidence,
            Dimension.TEST.value: self.test_passed,
            Dimension.EVIDENCE.value: self.evidence_recorded,
            Dimension.VERIFICATION.value: self.verification_passed,
            Dimension.SECURITY.value: self.security_verified,
            Dimension.REGRESSION.value: self.regression_passed,
        }


@dataclass
class AcceptanceVerdict:
    """验收判定结果：CI / Function / Evidence Coverage 三维分离。"""
    task_id: str
    ci_status: str
    functional_status: str
    evidence_coverage: float                 # 0~100，8 维中已成立的占比
    satisfied_dimensions: List[str]
    missing_dimensions: List[str]
    partial_reasons: List[str]
    commit_sha: Optional[str] = None
    evidence_refs: Dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 核心判定器
# ============================================================
def _ci_status(inp: AcceptanceInput) -> CIStatus:
    if inp.ci_passed is True:
        return CIStatus.PASS
    if inp.ci_passed is False:
        return CIStatus.FAILED
    return CIStatus.UNKNOWN


def _dimension_evidence(inp: AcceptanceInput):
    """返回 (满足维度列表, 缺失维度列表, 原因列表)。"""
    dim = inp.dimension_map()
    satisfied, missing, reasons = [], [], []

    # 维度 → 缺失原因映射
    reason_map = {
        Dimension.SOURCE.value: PartialReason.MISSING_SOURCE,
        Dimension.CALL_GRAPH.value: PartialReason.CALL_GRAPH_INCOMPLETE,
        Dimension.RUNTIME.value: PartialReason.MISSING_RUNTIME_EVIDENCE,
        Dimension.TEST.value: PartialReason.MISSING_TEST,
        Dimension.EVIDENCE.value: PartialReason.MISSING_EVIDENCE,
        Dimension.VERIFICATION.value: PartialReason.MISSING_VERIFICATION,
        Dimension.SECURITY.value: PartialReason.SECURITY_NOT_VERIFIED,
        Dimension.REGRESSION.value: PartialReason.REGRESSION_NOT_VERIFIED,
    }
    # 测试维度区分「失败」与「缺失」
    for name, ok in dim.items():
        if ok is True:
            satisfied.append(name)
        else:
            missing.append(name)
            if name == Dimension.TEST.value and inp.test_passed is False:
                reasons.append(PartialReason.TEST_FAILED.value)
            else:
                reasons.append(reason_map[name].value)

    # 安全维度细化：权限未验证
    if inp.security_verified is not True:
        if PartialReason.PERMISSION_NOT_VERIFIED.value not in reasons:
            reasons.append(PartialReason.PERMISSION_NOT_VERIFIED.value)

    # AI / Browser 特殊验收：不允许仅凭单测 VERIFIED，必须完整链路闭环
    if inp.is_ai_or_browser and inp.ai_chain_closed is not True:
        reasons.append(PartialReason.AI_CHAIN_NOT_CLOSED.value)
        # 链路未闭环视为调用链/运行证据不足
        for extra in (Dimension.CALL_GRAPH.value, Dimension.RUNTIME.value):
            if extra not in missing:
                missing.append(extra)
                if extra in satisfied:
                    satisfied.remove(extra)

    # E2E：runtime/verification 缺失时同时提示缺 E2E
    if inp.runtime_evidence is not True or inp.verification_passed is not True:
        if PartialReason.MISSING_E2E.value not in reasons:
            reasons.append(PartialReason.MISSING_E2E.value)

    return satisfied, missing, reasons


def judge(inp: AcceptanceInput) -> AcceptanceVerdict:
    """最终验收判定。纯函数，无副作用。"""
    ci = _ci_status(inp)
    satisfied, missing, reasons = _dimension_evidence(inp)
    coverage = round(100.0 * len(satisfied) / len(REQUIRED_DIMENSIONS), 1)

    # ---- 功能状态分层判定（严格按用户第二、三节）----
    # 1) 源码都不存在 → PLANNED
    if inp.source_exists is not True:
        functional = FunctionalStatus.PLANNED
    # 2) 已发布 + 持续运行证据 → OPERATING（最高态，仍要求其余维度成立）
    elif inp.is_released and inp.has_continuous_runtime and not missing:
        functional = FunctionalStatus.OPERATING
    # 3) 已发布且维度齐全 → RELEASED
    elif inp.is_released and not missing:
        functional = FunctionalStatus.RELEASED
    # 4) 8 维全部满足（AI/Browser 还要求链路闭环）→ VERIFIED
    elif not missing:
        functional = FunctionalStatus.VERIFIED
    # 5) 源码在、但调用链未闭环 → IMPLEMENTED
    elif inp.call_graph_closed is not True and inp.test_passed is not True:
        functional = FunctionalStatus.IMPLEMENTED
    # 6) 测试通过但没有真实运行验证 → TESTED
    elif inp.test_passed is True and inp.runtime_evidence is not True:
        functional = FunctionalStatus.TESTED
    # 7) 其余任一未闭环 → PARTIAL
    else:
        functional = FunctionalStatus.PARTIAL

    return AcceptanceVerdict(
        task_id=inp.task_id,
        ci_status=ci.value,
        functional_status=functional.value,
        evidence_coverage=coverage,
        satisfied_dimensions=satisfied,
        missing_dimensions=missing,
        partial_reasons=sorted(set(reasons)),
        commit_sha=inp.commit_sha,
        evidence_refs=inp.evidence_refs,
        note=inp.note,
    )


def judge_batch(items: List[AcceptanceInput]) -> Dict[str, Any]:
    """批量判定 + 汇总（解决「19 VERIFIED / 14 PARTIAL」要可见原因的问题）。"""
    verdicts = [judge(i) for i in items]
    by_status: Dict[str, int] = {}
    partial_detail = []
    # 已完成验收的终态；其余（PLANNED/IMPLEMENTED/TESTED/PARTIAL）都算「未达 VERIFIED」，
    # 都要在明细里给出原因，一眼可见为什么没验收（对应用户第六节）。
    accepted_states = {FunctionalStatus.VERIFIED.value,
                       FunctionalStatus.RELEASED.value,
                       FunctionalStatus.OPERATING.value}
    for v in verdicts:
        by_status[v.functional_status] = by_status.get(v.functional_status, 0) + 1
        if v.functional_status not in accepted_states:
            partial_detail.append({
                "task_id": v.task_id,
                "functional_status": v.functional_status,
                "ci_status": v.ci_status,
                "evidence_coverage": v.evidence_coverage,
                "reasons": v.partial_reasons,
            })
    coverages = [v.evidence_coverage for v in verdicts]
    return {
        "ok": True,
        "total": len(verdicts),
        "by_functional_status": by_status,
        "average_evidence_coverage": round(sum(coverages) / len(coverages), 1) if coverages else 0.0,
        "verdicts": [v.to_dict() for v in verdicts],
        "partial_detail": partial_detail,
    }
