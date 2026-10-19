# -*- coding: utf-8 -*-
"""Compatibility runner for source-bound, deterministic research drafts.

The old specialist × hypothesis × round template loop is intentionally removed:
its random evidence IDs and non-empty-reference validation were not evidence.
The caller retains ownership of fresh source authorization and persistence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from agent_research.specialist import Specialist, default_specialists
from agent_research.source_bound import analyze_source_records


@dataclass
class ResearchResult:
    research_id: str
    goal: str
    summary: str
    ranked_findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_lineage: List[Dict[str, Any]] = field(default_factory=list)
    debate_transcript: List[Dict[str, Any]] = field(default_factory=list)
    specialist_contributions: Dict[str, int] = field(default_factory=dict)
    confidence: Optional[float] = None
    started_at: str = ''
    finished_at: str = ''
    status: str = 'needs_sources'
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    comparisons: List[Dict[str, Any]] = field(default_factory=list)
    effective_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    effective_findings: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class ResearchRunner:
    def __init__(self, specialists: Optional[List[Specialist]] = None) -> None:
        self._specialists = [s for s in (specialists if specialists is not None else default_specialists()) if s.enabled]

    def run_research(self, goal: str, specialists: Optional[List[Specialist]] = None,
                     max_rounds: int = 3, *, records: Optional[List[dict]] = None,
                     actor_id: str = '', scope: Optional[dict] = None,
                     dimension: str = 'growth_opportunity', regions: Optional[List[str]] = None,
                     languages: Optional[List[str]] = None,
                     hypothesis_reviews: Optional[List[dict]] = None) -> ResearchResult:
        """Legacy positional API remains accepted; rounds cannot create evidence.

        Specialist/round arguments are planning hints retained for compatibility,
        not executed agents or independent verification. No sources => no findings.
        """
        if type(max_rounds) is not int:
            raise ValueError('INVALID_RESEARCH_ROUNDS')
        max_rounds = max(1, max_rounds)  # Preserve legacy nonpositive-round compatibility.
        result = analyze_source_records(goal, records if records is not None else [],
                                        actor_id=actor_id, scope=scope, dimension=dimension,
                                        regions=regions, languages=languages, hypothesis_reviews=hypothesis_reviews)
        return ResearchResult(
            research_id=result['research_id'], goal=result['goal'], summary=result['summary'],
            ranked_findings=result['ranked_findings'], evidence_lineage=result['evidence_lineage'],
            specialist_contributions={'source_reader': len(result['ranked_findings'])},
            debate_transcript=result['debate_transcript'],
            effective_hypotheses=result['effective_hypotheses'],
            effective_findings=result['effective_findings'],
            status=result['status'], hypotheses=result['hypotheses'], comparisons=result['comparisons'],
            metrics=result['metrics'], limitations=result['limitations'],
        )


def run_research(goal: str, specialists: list = None, *, records: Optional[List[dict]] = None,
                 actor_id: str = '', scope: Optional[dict] = None,
                 dimension: str = 'growth_opportunity', regions: Optional[List[str]] = None,
                 languages: Optional[List[str]] = None,
                     hypothesis_reviews: Optional[List[dict]] = None) -> ResearchResult:
    return ResearchRunner(specialists).run_research(
        goal, specialists, records=records, actor_id=actor_id, scope=scope,
        dimension=dimension, regions=regions, languages=languages, hypothesis_reviews=hypothesis_reviews)
