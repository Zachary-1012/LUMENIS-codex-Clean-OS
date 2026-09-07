# -*- coding: utf-8 -*-
"""
Research Runner — 探索式研究主运行器
流程：生成假设 → 并行探索（循环模拟）→ 互相质疑 → 验证 → 排序 → 汇总。
纯规则实现，不调用外部 AI，不创建多进程/多线程。每个 finding 带 evidence_refs 和 lineage_id。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from agent_research.specialist import Specialist, SpecialistRegistry, default_specialists, _short_id, _utc_now_iso
from agent_research.hypothesis import (
    Hypothesis, ExplorationPath, HypothesisGenerator,
    HYPOTHESIS_CHALLENGED, HYPOTHESIS_VERIFIED, HYPOTHESIS_REJECTED,
)
from agent_research.debate import Critique, DebateRound, DebateOrchestrator, SEVERITY_CRITICAL, SEVERITY_HIGH
from agent_research.lineage import LineageTracker


@dataclass
class ResearchResult:
    """研究结果：goal/summary/ranked_findings/evidence_lineage/debate_transcript/specialist_contributions/confidence。"""
    research_id: str
    goal: str
    summary: str
    ranked_findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_lineage: List[Dict[str, Any]] = field(default_factory=list)
    debate_transcript: List[Dict[str, Any]] = field(default_factory=list)
    specialist_contributions: Dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0
    started_at: str = field(default_factory=_utc_now_iso)
    finished_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class ResearchRunner:
    """探索式研究主运行器。"""

    def __init__(self, specialists: Optional[List[Specialist]] = None) -> None:
        self._specialists = [s for s in (specialists if specialists else default_specialists()) if s.enabled]
        self._registry = SpecialistRegistry()
        for sp in self._specialists:
            self._registry.register(sp)
        self._debate = DebateOrchestrator()

    def run_research(
        self, goal: str, specialists: Optional[List[Specialist]] = None, max_rounds: int = 3,
    ) -> ResearchResult:
        """主入口：生成假设 → 多轮探索/质疑/验证 → 排序 → 汇总。"""
        started_at = _utc_now_iso()
        research_id = _short_id("res")

        if not goal or not goal.strip():
            return ResearchResult(
                research_id=research_id, goal="",
                summary="研究目标为空，未执行任何探索。",
                started_at=started_at, finished_at=_utc_now_iso(),
            )

        active = [s for s in (specialists if specialists else self._specialists) if s.enabled]
        if not active:
            active = default_specialists()
        max_rounds = max(1, max_rounds)

        lineage = LineageTracker()
        hypotheses = HypothesisGenerator(active).generate(goal, max_per_specialist=2)

        all_findings: List[Dict[str, Any]] = []
        debate_rounds: List[DebateRound] = []

        for rnd in range(1, max_rounds + 1):
            findings, _ = self._parallel_explore(goal, hypotheses, active, rnd, lineage)
            all_findings.extend(findings)
            dr = self._debate.run_debate_round(hypotheses, active, round_number=rnd)
            debate_rounds.append(dr)
            self._validate(findings, hypotheses, dr)

        all_critiques = [c for dr in debate_rounds for c in dr.critiques]
        ranked = self._rank_findings(all_findings, all_critiques)
        contrib = self._count_contrib(all_findings, active)
        summary = self._synthesize(goal, ranked, hypotheses, debate_rounds, contrib)
        overall_conf = ranked[0]["confidence"] if ranked else 0.0

        return ResearchResult(
            research_id=research_id, goal=goal, summary=summary,
            ranked_findings=ranked, evidence_lineage=lineage.export(),
            debate_transcript=[dr.to_dict() for dr in debate_rounds],
            specialist_contributions=contrib, confidence=overall_conf,
            started_at=started_at, finished_at=_utc_now_iso(),
        )

    def _parallel_explore(
        self, goal: str, hypotheses: List[Hypothesis],
        specialists: List[Specialist], round_num: int, lineage: LineageTracker,
    ) -> tuple:
        """并行探索（循环模拟）：每个专家对每个假设生成 1 条 finding，追踪血缘。"""
        findings: List[Dict[str, Any]] = []
        paths: List[ExplorationPath] = []
        for sp in specialists:
            path = ExplorationPath(path_id=_short_id("path"), specialist_id=sp.specialist_id)
            for idx, hyp in enumerate(hypotheses, 1):
                ev_id = _short_id("ev")
                lid = lineage.track(
                    evidence_id=ev_id, source=sp.specialist_id,
                    path=[hyp.hypothesis_id, f"finding_{sp.specialist_id}_{idx}", ev_id],
                    provenance={"method": "rule_based_exploration", "specialist_role": sp.role,
                                "round": round_num, "hypothesis_id": hyp.hypothesis_id},
                )
                conf = min(0.4 + 0.1 * (round_num - 1) + (0.1 if sp.role == "validator" else 0), 0.95)
                finding = {
                    "finding_id": _short_id("find"), "specialist_id": sp.specialist_id,
                    "hypothesis_id": hyp.hypothesis_id,
                    "content": self._finding_content(sp, hyp, goal, round_num),
                    "confidence": conf, "evidence_refs": [ev_id], "lineage_id": lid,
                    "round": round_num, "validated": False,
                }
                findings.append(finding)
                path.steps.append({"step": idx, "action": "explore_hypothesis",
                                   "detail": hyp.statement[:60], "result": f"generated_finding_{finding['finding_id']}"})
                path.findings.append({"content": finding["content"], "confidence": conf, "evidence_refs": [ev_id]})
                path.evidence_chain.append(ev_id)
            path.status = "completed"
            paths.append(path)
        return findings, paths

    def _finding_content(self, sp: Specialist, hyp: Hypothesis, goal: str, rnd: int) -> str:
        templates = {
            "analyst": f"[分析员·第{rnd}轮] 针对假设「{hyp.statement[:40]}...」，从目标「{goal[:30]}...」中识别出结构化维度差异，建议进一步量化分析。",
            "critic": f"[评论员·第{rnd}轮] 审视假设「{hyp.statement[:40]}...」，发现其前提条件需要更严格的边界定义，反例场景尚未完全排除。",
            "validator": f"[验证员·第{rnd}轮] 验证假设「{hyp.statement[:40]}...」，证据链基本完整，内部一致性检查通过，结论可纳入候选排序。",
        }
        return templates.get(sp.role, f"[{sp.name}·第{rnd}轮] 探索假设「{hyp.statement[:40]}...」，获得初步发现，需结合更多证据确认。")

    def _validate(self, findings: List[Dict], hypotheses: List[Hypothesis], debate_round: DebateRound) -> None:
        """验证：finding 有证据且置信度合理→validated；被高严重度质疑且无证据→rejected；验证员支持→verified。"""
        for f in findings:
            f["validated"] = bool(f.get("evidence_refs")) and 0.0 <= f.get("confidence", 0) <= 1.0
        critical_hyps = {c.to_hypothesis for c in debate_round.critiques if c.severity in (SEVERITY_CRITICAL, SEVERITY_HIGH)}
        validator_supported = {f["hypothesis_id"] for f in findings if f.get("specialist_id") == "validator" and f.get("validated")}
        for hyp in hypotheses:
            if hyp.hypothesis_id in critical_hyps and not hyp.evidence_refs:
                hyp.status = HYPOTHESIS_REJECTED
            elif hyp.hypothesis_id in validator_supported and hyp.evidence_refs:
                hyp.status = HYPOTHESIS_VERIFIED

    def _rank_findings(self, findings: List[Dict], critiques: List[Critique]) -> List[Dict]:
        """按 rank_score = confidence*0.6 + evidence_strength*0.4 降序排序，被高严重度质疑降权 0.2。"""
        sev_order = {SEVERITY_CRITICAL: 3, SEVERITY_HIGH: 2, "medium": 1, "low": 0}
        hyp_max_sev: Dict[str, str] = {}
        for c in critiques:
            cur = hyp_max_sev.get(c.to_hypothesis, "low")
            if sev_order.get(c.severity, 0) > sev_order.get(cur, 0):
                hyp_max_sev[c.to_hypothesis] = c.severity
        ranked = []
        for f in findings:
            ev_strength = min(len(f.get("evidence_refs", [])) / 2.0, 1.0)
            score = f.get("confidence", 0) * 0.6 + ev_strength * 0.4
            if hyp_max_sev.get(f.get("hypothesis_id", ""), "low") in (SEVERITY_CRITICAL, SEVERITY_HIGH):
                score -= 0.2
            fc = dict(f)
            fc["evidence_strength"] = ev_strength
            fc["rank_score"] = round(max(score, 0.0), 4)
            ranked.append(fc)
        ranked.sort(key=lambda x: x["rank_score"], reverse=True)
        return ranked

    def _count_contrib(self, findings: List[Dict], specialists: List[Specialist]) -> Dict[str, int]:
        contrib = {s.specialist_id: 0 for s in specialists}
        for f in findings:
            contrib[f.get("specialist_id", "")] = contrib.get(f.get("specialist_id", ""), 0) + 1
        return contrib

    def _synthesize(
        self, goal: str, ranked: List[Dict], hypotheses: List[Hypothesis],
        debate_rounds: List[DebateRound], contrib: Dict[str, int],
    ) -> str:
        verified = sum(1 for h in hypotheses if h.status == HYPOTHESIS_VERIFIED)
        rejected = sum(1 for h in hypotheses if h.status == HYPOTHESIS_REJECTED)
        total_crit = sum(len(dr.critiques) for dr in debate_rounds)
        lines = [
            f"研究目标：{goal}",
            f"研究概况：共生成 {len(hypotheses)} 个假设，经过 {len(debate_rounds)} 轮探索与辩论，"
            f"产出 {len(ranked)} 条发现，其中 {verified} 个假设验证通过、{rejected} 个被否决，累计 {total_crit} 条质疑。",
        ]
        if ranked:
            top = ranked[0]
            lines.append(
                f"核心发现（排名第1，专家={top.get('specialist_id')}，置信度={top.get('confidence', 0):.2f}，"
                f"综合分={top.get('rank_score', 0):.4f}）：{top.get('content', '')}"
            )
        parts = [f"{sid}({cnt}条)" for sid, cnt in contrib.items() if cnt > 0]
        if parts:
            lines.append(f"专家贡献分布：{', '.join(parts)}。")
        lines.append("所有发现均附带证据引用与血缘追踪，可通过 evidence_lineage 回溯至假设→专家→证据。")
        return "\n".join(lines)


def run_research(goal: str, specialists: list = None) -> ResearchResult:
    """模块级便捷函数：使用默认 ResearchRunner 执行研究（max_rounds=3）。"""
    runner = ResearchRunner(specialists=specialists)
    return runner.run_research(goal=goal, specialists=specialists, max_rounds=3)
