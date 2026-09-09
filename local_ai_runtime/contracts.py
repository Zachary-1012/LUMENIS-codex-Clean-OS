from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RuntimeMode(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    HYBRID = "HYBRID"
    CLOUD_FALLBACK = "CLOUD_FALLBACK"


class HealthStatus(str, Enum):
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AnalysisRequest:
    text: str
    task_type: str = "business_analysis"
    risk: str = "normal"
    complexity: str = "normal"
    privacy: str = "local"
    latency_requirement: str = "interactive"
    required_capability: str = "general_analysis"
    evidence_available: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL_ONLY
    resource_budget: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteDecision:
    selected_provider: str
    selected_model: str
    reason: str
    fallback_chain: list[str]
    budget: dict[str, Any]
    trace_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    ok: bool
    advisory: bool
    task_type: str
    summary: str
    sentiment: str
    topics: list[str]
    confidence: float
    fact_basis: str
    provider: str
    model: str
    prompt_version: str
    trace_id: str
    evidence_id: str
    timestamp: str
    fallback: bool = False
    error_type: str = ""
    latency_ms: int = 0
    resource_usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
