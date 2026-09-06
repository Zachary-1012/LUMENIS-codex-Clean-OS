# -*- coding: utf-8 -*-
"""ZBC 验收证据链构建器（Acceptance Evidence Chain）。

桥接 acceptance_gate.py（纯逻辑判定器）与 evidence_chain.py（证据存储/生命周期）。

核心链路（对应用户第五节）：
    Task → Commit → Source → Call Graph → Test → Runtime
         → Evidence → Verification → Final Status

AI / Browser 特殊链路（对应用户第七节，硬要求）：
    AI Task → Agent → Skill → Permission → Browser/Tool → Action
            → Result → Evidence → Verification → Trace

设计原则：
1. 不修改 acceptance_gate.py / evidence_chain.py 任何一行，只做桥接增量；
2. 纯逻辑构建 + 可选持久化（evidence_chain 写入独立表 zbc_evidence，不碰生产表）；
3. 每个状态可追溯「为什么」——禁止只给百分比；
4. PARTIAL 原因与 acceptance_gate.PartialReason 完全对齐；
5. 向后兼容：缺证据显式标缺失，不静默成 0 条 / 不静默成 VERIFIED。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# 延迟导入：避免无 DB 环境下 import 失败；纯逻辑部分不依赖 evidence_chain
try:
    from evidence_chain import EvidenceChain, compute_content_hash, generate_evidence_id
    _HAS_EVIDENCE_CHAIN = True
except ImportError:
    _HAS_EVIDENCE_CHAIN = False

try:
    import acceptance_gate as ag
    _HAS_ACCEPTANCE_GATE = True
except ImportError:
    _HAS_ACCEPTANCE_GATE = False


# ============================================================
# 证据链节点类型（9 节点 + AI/Browser 扩展节点）
# ============================================================
class ChainNode(str):
    """证据链节点标识（字符串子类，可直接当字符串用）。"""
    pass


# 通用功能验收链路 9 节点
NODE_TASK = ChainNode("task")
NODE_COMMIT = ChainNode("commit")
NODE_SOURCE = ChainNode("source")
NODE_CALL_GRAPH = ChainNode("call_graph")
NODE_TEST = ChainNode("test")
NODE_RUNTIME = ChainNode("runtime")
NODE_EVIDENCE = ChainNode("evidence")
NODE_VERIFICATION = ChainNode("verification")
NODE_FINAL_STATUS = ChainNode("final_status")

GENERIC_CHAIN_ORDER = [
    NODE_TASK, NODE_COMMIT, NODE_SOURCE, NODE_CALL_GRAPH, NODE_TEST,
    NODE_RUNTIME, NODE_EVIDENCE, NODE_VERIFICATION, NODE_FINAL_STATUS,
]

# AI / Browser 特殊验收链路（11 节点，对应用户第七节硬要求）
AI_NODE_TASK = ChainNode("task")  # 与通用链路共用 task 节点名
AI_NODE_AGENT = ChainNode("agent")
AI_NODE_SKILL = ChainNode("skill")
AI_NODE_PERMISSION = ChainNode("permission")
AI_NODE_BROWSER_TOOL = ChainNode("browser_tool")
AI_NODE_ACTION = ChainNode("action")
AI_NODE_RESULT = ChainNode("result")
AI_NODE_EVIDENCE = ChainNode("evidence")
AI_NODE_VERIFICATION = ChainNode("verification")
AI_NODE_TRACE = ChainNode("trace")
AI_NODE_FINAL_STATUS = ChainNode("final_status")

AI_CHAIN_ORDER = [
    AI_NODE_TASK, AI_NODE_AGENT, AI_NODE_SKILL, AI_NODE_PERMISSION,
    AI_NODE_BROWSER_TOOL, AI_NODE_ACTION, AI_NODE_RESULT,
    AI_NODE_EVIDENCE, AI_NODE_VERIFICATION, AI_NODE_TRACE, AI_NODE_FINAL_STATUS,
]


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ChainNodeEvidence:
    """单个链路节点的证据记录。"""
    node: str                          # 节点标识
    status: str                        # "passed" / "failed" / "missing" / "not_applicable"
    evidence_ref: str = ""             # 证据指针（文件路径 / commit sha / test id / evidence_id / URL）
    detail: str = ""                   # 人类可读详情
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AcceptanceEvidenceChain:
    """完整验收证据链：可追溯「为什么得到这个状态」。"""
    task_id: str
    is_ai_or_browser: bool = False
    nodes: List[ChainNodeEvidence] = field(default_factory=list)
    commit_sha: str = ""
    # 最终判定结果（由 build_and_judge 填充）
    ci_status: str = "UNKNOWN"
    functional_status: str = "PLANNED"
    evidence_coverage: float = 0.0
    partial_reasons: List[str] = field(default_factory=list)
    missing_dimensions: List[str] = field(default_factory=list)
    satisfied_dimensions: List[str] = field(default_factory=list)
    note: str = ""

    def chain_order(self) -> List[str]:
        return AI_CHAIN_ORDER if self.is_ai_or_browser else GENERIC_CHAIN_ORDER

    def add_node(self, node: str, status: str, evidence_ref: str = "",
                 detail: str = "", **metadata) -> "AcceptanceEvidenceChain":
        """追加一个节点证据。链式调用。"""
        self.nodes.append(ChainNodeEvidence(
            node=node, status=status, evidence_ref=evidence_ref,
            detail=detail, metadata=metadata,
        ))
        return self

    def get_node(self, node: str) -> Optional[ChainNodeEvidence]:
        for n in self.nodes:
            if n.node == node:
                return n
        return None

    def passed_nodes(self) -> List[str]:
        return [n.node for n in self.nodes if n.status == "passed"]

    def failed_nodes(self) -> List[str]:
        return [n.node for n in self.nodes if n.status == "failed"]

    def missing_nodes(self) -> List[str]:
        """链路中应有但缺失（未记录或 status=missing）的节点。"""
        present = {n.node for n in self.nodes if n.status in ("passed", "failed")}
        return [n for n in self.chain_order() if n not in present]

    def coverage(self) -> float:
        """链路节点覆盖率（passed / 总应有节点）。"""
        order = self.chain_order()
        if not order:
            return 0.0
        passed = self.passed_nodes()
        return round(100.0 * len([n for n in passed if n in order]) / len(order), 1)

    def to_acceptance_input(self) -> Optional[Dict[str, Any]]:
        """将证据链转换为 acceptance_gate.AcceptanceInput 可接受的 dict。

        映射规则（链路节点 → 8 维验收维度）：
          source       ← NODE_SOURCE passed
          call_graph   ← NODE_CALL_GRAPH passed（AI 还需 AI_NODE_AGENT/SKILL/PERMISSION/BROWSER_TOOL/ACTION 全 passed）
          runtime      ← NODE_RUNTIME passed（AI 还需 AI_NODE_RESULT passed）
          test         ← NODE_TEST passed
          evidence     ← NODE_EVIDENCE / AI_NODE_EVIDENCE passed
          verification ← NODE_VERIFICATION / AI_NODE_VERIFICATION passed
          security     ← 权限节点 passed（AI: AI_NODE_PERMISSION；通用: metadata 中 security_verified）
          regression   ← metadata 中 regression_passed（链路本身不含回归，由调用方注入）
        """
        if not _HAS_ACCEPTANCE_GATE:
            return None

        def _node_passed(node_name: str) -> bool:
            n = self.get_node(node_name)
            return n is not None and n.status == "passed"

        source = _node_passed(NODE_SOURCE)

        # 调用链：通用看 call_graph 节点；AI 要求 agent+skill+permission+browser_tool+action 全过
        if self.is_ai_or_browser:
            call_graph = all(_node_passed(n) for n in (
                AI_NODE_AGENT, AI_NODE_SKILL, AI_NODE_PERMISSION,
                AI_NODE_BROWSER_TOOL, AI_NODE_ACTION,
            ))
        else:
            call_graph = _node_passed(NODE_CALL_GRAPH)

        # 运行时：通用看 runtime；AI 还要求 result
        if self.is_ai_or_browser:
            runtime = _node_passed(AI_NODE_RESULT) and _node_passed(NODE_RUNTIME)
        else:
            runtime = _node_passed(NODE_RUNTIME)

        test = _node_passed(NODE_TEST)

        evidence_node = AI_NODE_EVIDENCE if self.is_ai_or_browser else NODE_EVIDENCE
        evidence = _node_passed(evidence_node)

        verify_node = AI_NODE_VERIFICATION if self.is_ai_or_browser else NODE_VERIFICATION
        verification = _node_passed(verify_node)

        # 安全/权限：AI 看 permission 节点；通用从 metadata 聚合
        if self.is_ai_or_browser:
            security = _node_passed(AI_NODE_PERMISSION)
        else:
            security = any(
                n.metadata.get("security_verified") is True
                for n in self.nodes
            )

        # 回归：从所有节点 metadata 聚合（链路本身不含独立回归节点）
        regression = any(
            n.metadata.get("regression_passed") is True
            for n in self.nodes
        )

        # CI：从 commit 节点取
        commit_node = self.get_node(NODE_COMMIT)
        ci_passed: Optional[bool] = None
        if commit_node is not None:
            if commit_node.status == "passed":
                ci_passed = True
            elif commit_node.status == "failed":
                ci_passed = False

        # AI 链路闭环判定
        ai_chain_closed = None
        if self.is_ai_or_browser:
            ai_chain_closed = all(_node_passed(n) for n in AI_CHAIN_ORDER if n != AI_NODE_FINAL_STATUS)

        return {
            "task_id": self.task_id,
            "ci_passed": ci_passed,
            "commit_sha": self.commit_sha,
            "source_exists": source,
            "call_graph_closed": call_graph,
            "runtime_evidence": runtime,
            "test_passed": test,
            "evidence_recorded": evidence,
            "verification_passed": verification,
            "security_verified": security,
            "regression_passed": regression,
            "ai_chain_closed": ai_chain_closed,
            "is_ai_or_browser": self.is_ai_or_browser,
            "note": self.note,
        }

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["chain_order"] = self.chain_order()
        d["passed_nodes"] = self.passed_nodes()
        d["missing_nodes"] = self.missing_nodes()
        d["node_coverage"] = self.coverage()
        return d

    def explain(self) -> str:
        """生成人类可读的「为什么是这个状态」解释。禁止只给百分比。"""
        lines = [
            f"任务: {self.task_id}",
            f"类型: {'AI/Browser 特殊验收' if self.is_ai_or_browser else '通用功能验收'}",
            f"CI Status: {self.ci_status}",
            f"Functional Status: {self.functional_status}",
            f"Evidence Coverage: {self.evidence_coverage}%",
            "",
            "链路节点状态:",
        ]
        for node_name in self.chain_order():
            n = self.get_node(node_name)
            if n is None:
                lines.append(f"  [{node_name}] ⚠ MISSING（未提供证据）")
            elif n.status == "passed":
                ref = f" ← {n.evidence_ref}" if n.evidence_ref else ""
                lines.append(f"  [{node_name}] ✓ PASS{ref}")
            elif n.status == "failed":
                ref = f" ← {n.evidence_ref}" if n.evidence_ref else ""
                lines.append(f"  [{node_name}] ✗ FAIL{ref} {n.detail}")
            else:
                lines.append(f"  [{node_name}] ⚠ MISSING（{n.detail or '未提供证据'}）")

        if self.partial_reasons:
            lines.append("")
            lines.append("未验收原因 (PARTIAL reasons):")
            for r in self.partial_reasons:
                lines.append(f"  - {r}")

        if self.missing_dimensions:
            lines.append("")
            lines.append(f"缺失验收维度: {', '.join(self.missing_dimensions)}")
        if self.satisfied_dimensions:
            lines.append(f"已满足验收维度: {', '.join(self.satisfied_dimensions)}")

        return "\n".join(lines)


# ============================================================
# 核心构建器
# ============================================================
def build_chain(
    task_id: str,
    *,
    is_ai_or_browser: bool = False,
    commit_sha: str = "",
    ci_passed: Optional[bool] = None,
    source_exists: Optional[bool] = None,
    source_ref: str = "",
    call_graph_closed: Optional[bool] = None,
    call_graph_ref: str = "",
    test_passed: Optional[bool] = None,
    test_ref: str = "",
    runtime_evidence: Optional[bool] = None,
    runtime_ref: str = "",
    evidence_recorded: Optional[bool] = None,
    evidence_ref: str = "",
    verification_passed: Optional[bool] = None,
    verification_ref: str = "",
    security_verified: Optional[bool] = None,
    regression_passed: Optional[bool] = None,
    # AI/Browser 扩展节点
    ai_agent_ok: Optional[bool] = None,
    ai_skill_ok: Optional[bool] = None,
    ai_permission_ok: Optional[bool] = None,
    ai_browser_tool_ok: Optional[bool] = None,
    ai_action_ok: Optional[bool] = None,
    ai_result_ok: Optional[bool] = None,
    ai_trace_ok: Optional[bool] = None,
    note: str = "",
) -> AcceptanceEvidenceChain:
    """从各维度证据构建完整证据链。

    每个 Optional[bool]：True=passed, False=failed, None=missing（未提供证据）。
    缺失节点显式标记，不静默跳过。
    """
    chain = AcceptanceEvidenceChain(
        task_id=task_id, is_ai_or_browser=is_ai_or_browser,
        commit_sha=commit_sha, note=note,
    )

    def _st(val: Optional[bool]) -> str:
        if val is True:
            return "passed"
        if val is False:
            return "failed"
        return "missing"

    # ---- 通用节点（所有链路都有）----
    chain.add_node(NODE_TASK, "passed", evidence_ref=task_id,
                   detail=f"任务 {task_id} 已登记")

    chain.add_node(NODE_COMMIT, _st(ci_passed),
                   evidence_ref=commit_sha,
                   detail="CI/代码检查通过" if ci_passed else
                          ("CI/代码检查失败" if ci_passed is False else "未提供 CI 结果"))

    chain.add_node(NODE_SOURCE, _st(source_exists),
                   evidence_ref=source_ref,
                   detail="源码存在" if source_exists else
                          ("源码不存在" if source_exists is False else "未验证源码存在性"))

    if not is_ai_or_browser:
        chain.add_node(NODE_CALL_GRAPH, _st(call_graph_closed),
                       evidence_ref=call_graph_ref,
                       detail="调用链闭环可定位" if call_graph_closed else
                              ("调用链未闭环" if call_graph_closed is False else "未验证调用链"))

    chain.add_node(NODE_TEST, _st(test_passed),
                   evidence_ref=test_ref,
                   detail="自动化测试通过" if test_passed else
                          ("自动化测试失败" if test_passed is False else "未提供测试结果"))

    chain.add_node(NODE_RUNTIME, _st(runtime_evidence),
                   evidence_ref=runtime_ref,
                   detail="真实运行证据存在" if runtime_evidence else
                          ("无真实运行证据" if runtime_evidence is False else "未验证真实运行"))

    ev_node = AI_NODE_EVIDENCE if is_ai_or_browser else NODE_EVIDENCE
    chain.add_node(ev_node, _st(evidence_recorded),
                   evidence_ref=evidence_ref,
                   detail="Evidence 链可追溯" if evidence_recorded else
                          ("Evidence 缺失" if evidence_recorded is False else "未记录 Evidence"))

    ver_node = AI_NODE_VERIFICATION if is_ai_or_browser else NODE_VERIFICATION
    chain.add_node(ver_node, _st(verification_passed),
                   evidence_ref=verification_ref,
                   detail="预期 vs 实际核验通过" if verification_passed else
                          ("核验未通过" if verification_passed is False else "未执行预期核验"))

    # 安全/回归：作为 metadata 注入到 verification 节点（链路中无独立节点）
    ver_node_obj = chain.get_node(ver_node)
    if ver_node_obj is not None:
        if security_verified is not None:
            ver_node_obj.metadata["security_verified"] = security_verified
        if regression_passed is not None:
            ver_node_obj.metadata["regression_passed"] = regression_passed

    # ---- AI/Browser 扩展节点 ----
    if is_ai_or_browser:
        chain.add_node(AI_NODE_AGENT, _st(ai_agent_ok),
                       detail="Agent 调度成功" if ai_agent_ok else
                              ("Agent 调度失败" if ai_agent_ok is False else "未验证 Agent"))
        chain.add_node(AI_NODE_SKILL, _st(ai_skill_ok),
                       detail="Skill 加载/执行成功" if ai_skill_ok else
                              ("Skill 执行失败" if ai_skill_ok is False else "未验证 Skill"))
        chain.add_node(AI_NODE_PERMISSION, _st(ai_permission_ok),
                       detail="权限校验通过" if ai_permission_ok else
                              ("权限校验失败" if ai_permission_ok is False else "未验证权限"))
        chain.add_node(AI_NODE_BROWSER_TOOL, _st(ai_browser_tool_ok),
                       detail="Browser/Tool 调用成功" if ai_browser_tool_ok else
                              ("Browser/Tool 调用失败" if ai_browser_tool_ok is False else "未验证 Browser/Tool"))
        chain.add_node(AI_NODE_ACTION, _st(ai_action_ok),
                       detail="Action 执行成功" if ai_action_ok else
                              ("Action 执行失败" if ai_action_ok is False else "未验证 Action"))
        chain.add_node(AI_NODE_RESULT, _st(ai_result_ok),
                       detail="Result 产出符合预期" if ai_result_ok else
                              ("Result 不符合预期" if ai_result_ok is False else "未验证 Result"))
        chain.add_node(AI_NODE_TRACE, _st(ai_trace_ok),
                       detail="全链路 Trace 可追溯" if ai_trace_ok else
                              ("Trace 缺失" if ai_trace_ok is False else "未记录 Trace"))

    # 最终状态节点（占位，由 build_and_judge 填充实际判定）
    chain.add_node(NODE_FINAL_STATUS, "missing",
                   detail="待判定（调用 build_and_judge 后填充）")

    return chain


def build_and_judge(
    task_id: str,
    *,
    persist_evidence: bool = False,
    db_path: Optional[str] = None,
    **kwargs,
) -> AcceptanceEvidenceChain:
    """构建证据链 + 调用 acceptance_gate.judge 判定 + 可选持久化 Evidence。

    一步完成：build_chain → to_acceptance_input → judge → 回填最终状态。
    若 persist_evidence=True 且 evidence_chain 可用，则将整条链的摘要作为一条
    Evidence 写入 zbc_evidence 表（独立表，不碰生产表）。
    """
    chain = build_chain(task_id, **kwargs)

    if _HAS_ACCEPTANCE_GATE:
        inp_dict = chain.to_acceptance_input()
        if inp_dict is not None:
            verdict = ag.judge(ag.AcceptanceInput(**inp_dict))
            chain.ci_status = verdict.ci_status
            chain.functional_status = verdict.functional_status
            chain.evidence_coverage = verdict.evidence_coverage
            chain.partial_reasons = verdict.partial_reasons
            chain.missing_dimensions = verdict.missing_dimensions
            chain.satisfied_dimensions = verdict.satisfied_dimensions

            # 回填 final_status 节点
            final_node = chain.get_node(NODE_FINAL_STATUS)
            if final_node is not None:
                final_node.status = "passed" if verdict.functional_status in (
                    "VERIFIED", "RELEASED", "OPERATING") else "failed"
                final_node.detail = (
                    f"最终判定: CI={verdict.ci_status}, "
                    f"Function={verdict.functional_status}, "
                    f"Coverage={verdict.evidence_coverage}%"
                )
                final_node.evidence_ref = verdict.commit_sha or ""

    # 可选持久化
    if persist_evidence and _HAS_EVIDENCE_CHAIN:
        try:
            ec = EvidenceChain(db_path=db_path) if db_path else EvidenceChain()
            chain_summary = json.dumps(chain.to_dict(), ensure_ascii=False)
            ev, is_new = ec.evidence_store.add_evidence(
                source_type="acceptance_chain",
                source_url=f"acceptance://{task_id}",
                raw_content=chain_summary,
                source_id=task_id,
                task_id=task_id,
                subject_scope="SYSTEM",
                provider="acceptance_evidence_chain",
                collection_metadata={
                    "is_ai_or_browser": chain.is_ai_or_browser,
                    "functional_status": chain.functional_status,
                    "ci_status": chain.ci_status,
                    "evidence_coverage": chain.evidence_coverage,
                    "partial_reasons": chain.partial_reasons,
                },
            )
            # 回填 evidence 节点的 ref
            ev_node_name = AI_NODE_EVIDENCE if chain.is_ai_or_browser else NODE_EVIDENCE
            ev_node = chain.get_node(ev_node_name)
            if ev_node is not None and not ev_node.evidence_ref:
                ev_node.evidence_ref = ev.evidence_id
        except Exception as e:
            # 持久化失败不影响判定结果，只记录 note
            chain.note = (chain.note + f" | Evidence持久化失败: {e}").strip(" |")

    return chain


def batch_build_and_judge(
    tasks: List[Dict[str, Any]],
    *,
    persist_evidence: bool = False,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """批量构建+判定。返回汇总 + 每条链的完整可追溯结果。"""
    chains = []
    for t in tasks:
        tid = t.pop("task_id", "UNKNOWN")
        chains.append(build_and_judge(tid, persist_evidence=persist_evidence,
                                       db_path=db_path, **t))

    by_status: Dict[str, int] = {}
    partial_detail = []
    accepted = {"VERIFIED", "RELEASED", "OPERATING"}
    for c in chains:
        by_status[c.functional_status] = by_status.get(c.functional_status, 0) + 1
        if c.functional_status not in accepted:
            partial_detail.append({
                "task_id": c.task_id,
                "functional_status": c.functional_status,
                "ci_status": c.ci_status,
                "evidence_coverage": c.evidence_coverage,
                "partial_reasons": c.partial_reasons,
                "missing_nodes": c.missing_nodes(),
            })

    coverages = [c.evidence_coverage for c in chains]
    return {
        "ok": True,
        "total": len(chains),
        "by_functional_status": by_status,
        "average_evidence_coverage": round(sum(coverages) / len(coverages), 1) if coverages else 0.0,
        "chains": [c.to_dict() for c in chains],
        "partial_detail": partial_detail,
    }


# ============================================================
# 验收最高原则（写入代码注释，对应用户第九节）
# ============================================================
# CI PASS ≠ VERIFIED
# 代码存在 ≠ VERIFIED
# AI说完成 ≠ VERIFIED
# 只有：真实源码 + 真实调用链 + 真实测试 + 真实运行 + 真实Evidence + 真实验证 = VERIFIED
ACCEPTANCE_PRINCIPLE = (
    "CI PASS ≠ VERIFIED | 代码存在 ≠ VERIFIED | AI说完成 ≠ VERIFIED | "
    "只有：真实源码 + 真实调用链 + 真实测试 + 真实运行 + 真实Evidence + 真实验证 = VERIFIED"
)


__all__ = [
    "AcceptanceEvidenceChain",
    "ChainNodeEvidence",
    "build_chain",
    "build_and_judge",
    "batch_build_and_judge",
    "GENERIC_CHAIN_ORDER",
    "AI_CHAIN_ORDER",
    "ACCEPTANCE_PRINCIPLE",
]
