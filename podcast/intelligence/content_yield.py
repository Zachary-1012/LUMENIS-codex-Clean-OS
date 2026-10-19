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
    story_count: int | None = None
    insight_count: int | None = None
    emotion_peak_count: int | None = None
    quote_count: int | None = None
    evidence_count: int | None = None


    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value=getattr(self,name)
            if value is not None and (type(value) is not int or not 0<=value<=1000000):
                raise ValueError("PODCAST_YIELD_SIGNAL_INVALID:"+name)


@dataclass(frozen=True)
class YieldPlan:
    assets: tuple[AssetKind, ...]
    rationale: tuple[str, ...]
    state: str = "planned"
    missing_signals: tuple[str, ...] = ()


def plan_yield(signal: YieldSignal) -> YieldPlan:
    missing=tuple(name for name in signal.__dataclass_fields__ if getattr(signal,name) is None)
    if missing:
        return YieldPlan(assets=(),rationale=("Missing counts are unknown, not zero; provide observations before planning.",),state="input_required",missing_signals=missing)
    assets: list[AssetKind] = ["full_episode"]
    rationale: list[str] = ["Plan to retain the full episode; this does not create an asset or promote Canonical facts."]

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
