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
    from lumenis.shared.evidence.chain import EvidenceChain, compute_content_hash, generate_evidence_id
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