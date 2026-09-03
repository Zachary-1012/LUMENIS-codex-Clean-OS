"""Plan reusable content assets from one interview without generating copy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AssetKind = Literal[
    "full_episode", "chapter", "clip", "quote", "short_video",
    "article", "social_post", "newsletter", "research_node"
]


@dataclass(frozen=True)
class YieldSignal:
    story_count: int = 0
    insight_count: int = 0
    emotion_peak_count: int = 0
    quote_count: int = 0
    evidence_count: int = 0


@dataclass(frozen=True)
class YieldPlan:
    assets: tuple[AssetKind, ...]
    rationale: tuple[str, ...]


def plan_yield(signal: YieldSignal) -> YieldPlan:
    assets: list[AssetKind] = ["full_episode"]
    rationale: list[str] = ["Every interview retains a canonical full-episode asset."]

    if signal.story_count:
        assets.append("chapter")
        rationale.append("Story nodes can become navigable chapters.")
    if signal.insight_count or signal.emotion_peak_count:
        assets.append("clip")
        assets.append("short_video")
        rationale.append("High-value narrative or emotional nodes are eligible for short-form derivatives.")
    if signal.quote_count:
        assets.append("quote")
        assets.append("social_post")
        rationale.append("Quote candidates can become standalone distribution assets after review.")
    if signal.evidence_count:
        assets.append("research_node")
        rationale.append("Evidence-bearing segments can enrich the research graph.")
    if signal.story_count + signal.insight_count >= 3:
        assets.extend(["article", "newsletter"])
        rationale.append("Sufficient narrative density may justify long-form derivatives.")

    return YieldPlan(assets=tuple(dict.fromkeys(assets)), rationale=tuple(rationale))
