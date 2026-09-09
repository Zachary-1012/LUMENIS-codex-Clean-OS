from __future__ import annotations

import os
import uuid
from typing import Any

from .contracts import AnalysisRequest, RouteDecision, RuntimeMode


class IntelligenceRouter:
    def __init__(self, runtime_config: dict[str, Any]):
        self.config = runtime_config

    @staticmethod
    def configured_mode(default: str = "LOCAL_ONLY") -> RuntimeMode:
        value = os.getenv("LUMENIS_AI_RUNTIME_MODE", default).strip().upper()
        try:
            return RuntimeMode(value)
        except ValueError as exc:
            raise ValueError(f"invalid LUMENIS_AI_RUNTIME_MODE: {value}") from exc

    def route(self, request: AnalysisRequest, local_health: dict[str, Any], cloud_health: dict[str, Any] | None = None) -> RouteDecision:
        mode = request.runtime_mode
        trace_id = uuid.uuid4().hex
        budget = {**self.config.get("resource_guard", {}), **request.resource_budget}
        if request.evidence_available and request.task_type == "evidence_lookup":
            return RouteDecision("DETERMINISTIC_RULE", "existing_evidence", "existing evidence satisfies task", [], budget, trace_id)
        local_up = local_health.get("status") == "UP" and local_health.get("installed", False)
        if local_up:
            fallback = ["DETERMINISTIC_RULE"] if mode == RuntimeMode.LOCAL_ONLY else ["ZHIPU", "DETERMINISTIC_RULE"]
            return RouteDecision("OLLAMA_LOCAL", self.config["default_model"], f"{mode.value}: local-first policy", fallback, budget, trace_id)
        if mode == RuntimeMode.LOCAL_ONLY:
            return RouteDecision("DETERMINISTIC_RULE", "no_ai_rule", "LOCAL_ONLY forbids cloud and local is unavailable", [], budget, trace_id)
        error_type = str(local_health.get("error_type") or "DOWN")
        allowed = set(self.config.get("cloud_escalation_errors", []))
        cloud_up = bool((cloud_health or {}).get("status") == "UP")
        cloud_disabled = os.getenv("CLOUD_AI_DISABLED", "").lower() in {"1", "true", "yes", "on"} or os.getenv("ZHIPU_DISABLED", "").lower() in {"1", "true", "yes", "on"}
        if error_type in allowed and cloud_up and not cloud_disabled:
            return RouteDecision("ZHIPU", "policy-selected", f"local {error_type}; policy permits cloud escalation", ["DETERMINISTIC_RULE"], budget, trace_id)
        return RouteDecision("DETERMINISTIC_RULE", "no_ai_rule", "no permitted healthy model provider", [], budget, trace_id)
