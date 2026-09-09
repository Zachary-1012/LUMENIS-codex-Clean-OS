from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .contracts import AnalysisRequest, AnalysisResult, RuntimeMode
from .evidence import EvidenceWriter
from .ollama import OllamaAdapter, OllamaRuntimeError
from .registry import AIRuntimeRegistry
from .resource_guard import ResourceGuard, ResourceLimitError
from .router import IntelligenceRouter


ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative", "uncertain"]},
        "topics": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "fact_basis": {"type": "string", "enum": ["provided_text", "provided_evidence", "insufficient"]},
    },
    "required": ["summary", "sentiment", "topics", "confidence", "fact_basis"],
}
SYSTEM_PROMPT = """你是序境 LUMENIS 的本地分析增强层。只能依据输入文本和明确列出的 Evidence，不得补造事实，不得修改 Production Truth、主体归属、统计口径或风险规则。输出必须符合给定 JSON Schema。证据不足时 fact_basis=insufficient 且降低 confidence。"""


def validate_analysis(value: dict[str, Any]) -> dict[str, Any]:
    required = set(ANALYSIS_SCHEMA["required"])
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("structured_output_missing_fields")
    sentiment = str(value["sentiment"])
    fact_basis = str(value["fact_basis"])
    if sentiment not in {"positive", "neutral", "negative", "uncertain"}:
        raise ValueError("structured_output_invalid_sentiment")
    if fact_basis not in {"provided_text", "provided_evidence", "insufficient"}:
        raise ValueError("structured_output_invalid_fact_basis")
    confidence = float(value["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("structured_output_invalid_confidence")
    topics = [str(item)[:80] for item in list(value["topics"])[:5]]
    return {"summary": str(value["summary"])[:500], "sentiment": sentiment, "topics": topics, "confidence": confidence, "fact_basis": fact_basis}


def deterministic_analysis(text: str) -> dict[str, Any]:
    negative = ("投诉", "欺诈", "危险", "受伤", "失败", "差评", "过期")
    positive = ("满意", "喜欢", "推荐", "优秀", "成功", "好评")
    neg = sum(text.count(word) for word in negative)
    pos = sum(text.count(word) for word in positive)
    sentiment = "negative" if neg > pos else "positive" if pos > neg else "neutral"
    words = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    topics = list(dict.fromkeys(words))[:5]
    return {"summary": text.strip()[:120], "sentiment": sentiment, "topics": topics, "confidence": 0.35, "fact_basis": "provided_text" if text.strip() else "insufficient"}


class LocalFirstAIService:
    def __init__(self, config_dir: Path | None = None, evidence_dir: Path | None = None, adapter: OllamaAdapter | None = None, cloud_call: Callable[..., dict[str, Any]] | None = None):
        self.registry = AIRuntimeRegistry(config_dir)
        self.router = IntelligenceRouter(self.registry.runtime)
        base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", self.registry.runtime["default_model"])
        timeout = self.registry.runtime["resource_guard"]["max_runtime_seconds"]
        context_window = self.registry.runtime.get("operational_context_window", 2048)
        guard_policy = self.registry.runtime["resource_guard"]
        self.adapter = adapter or OllamaAdapter(base, model, timeout, context_window, guard_policy.get("max_retry", 1), guard_policy.get("cooldown_seconds", 15))
        self.evidence = EvidenceWriter(evidence_dir)
        self.guard = ResourceGuard(self.registry.runtime["resource_guard"])
        self.cloud_call = cloud_call
        self.model_config = self.registry.model(model)

    def health(self, real_call: bool = False) -> dict[str, Any]:
        health = self.adapter.health(real_call=real_call)
        health.update({"provider": "OLLAMA_LOCAL", "mode": self.router.configured_mode(self.registry.runtime["default_mode"]).value})
        return health

    def analyze(self, text: str, task_type: str = "business_analysis", mode: str | RuntimeMode | None = None, evidence_ids: list[str] | None = None) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text is required")
        if len(text) > 32000:
            raise ValueError("input exceeds local runtime limit")
        runtime_mode = mode if isinstance(mode, RuntimeMode) else RuntimeMode(str(mode or self.router.configured_mode(self.registry.runtime["default_mode"]).value).upper())
        health = self.adapter.health(real_call=False)
        cloud_disabled = os.getenv("CLOUD_AI_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"} or os.getenv("ZHIPU_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        cloud_entry = self.registry.provider("ZHIPU")
        shadow_allowed = os.getenv("LUMENIS_ZHIPU_SHADOW_ALLOWED", "").strip().lower() in {"1", "true", "yes", "on"}
        governed = cloud_entry.get("status") == "PRODUCTION_APPROVED" or (cloud_entry.get("status") == "SHADOW" and shadow_allowed)
        cloud_health = {"status": "UP" if governed and self.cloud_call is not None and os.getenv("ZHIPU_API_KEY") and not cloud_disabled else "NOT_CONFIGURED"}
        request = AnalysisRequest(text=text, task_type=task_type, evidence_ids=evidence_ids or [], runtime_mode=runtime_mode)
        decision = self.router.route(request, health, cloud_health)
        started = time.perf_counter()
        selected_provider = decision.selected_provider
        selected_model = decision.selected_model
        fallback = selected_provider == "DETERMINISTIC_RULE"
        error_type = str(health.get("error_type") or "") if selected_provider == "DETERMINISTIC_RULE" else ""
        usage: dict[str, Any] = {}
        try:
            required_ram = int(self.model_config.get("hardware_requirement", {}).get("required_free_ram_mb", 0))
            with self.guard.reserve(required_free_ram_mb=required_ram) as resources:
                if selected_provider == "OLLAMA_LOCAL":
                    attempts = 1 + int(self.registry.runtime["resource_guard"].get("max_retry", 1))
                    last_error: Exception | None = None
                    for _ in range(attempts):
                        try:
                            call = self.adapter.chat(SYSTEM_PROMPT, text, ANALYSIS_SCHEMA)
                            analysis = validate_analysis(call["content"])
                            usage = {k: call[k] for k in ("prompt_tokens", "completion_tokens", "done_reason")}
                            break
                        except (OllamaRuntimeError, ValueError) as exc:
                            last_error = exc
                    else:
                        raise last_error or RuntimeError("local_call_failed")
                elif selected_provider == "ZHIPU":
                    if self.cloud_call is None:
                        raise OllamaRuntimeError("NOT_CONFIGURED", "zhipu_adapter_not_configured")
                    analysis = validate_analysis(self.cloud_call(text=text, task_type=task_type))
                else:
                    analysis = deterministic_analysis(text)
                    selected_provider, selected_model, fallback = "DETERMINISTIC_RULE", "no_ai_rule", True
        except (OllamaRuntimeError, ResourceLimitError, ValueError) as exc:
            analysis = deterministic_analysis(text)
            selected_provider, selected_model, fallback = "DETERMINISTIC_RULE", "no_ai_rule", True
            error_type = getattr(exc, "error_type", type(exc).__name__)
            resources = self.guard.snapshot()
        timestamp = datetime.now(timezone.utc).isoformat()
        latency_ms = int((time.perf_counter() - started) * 1000)
        evidence_payload = {
            "advisory": True,
            "input_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "source_evidence_ids": evidence_ids or [],
            "route": decision.to_dict(),
            "actual_provider": selected_provider,
            "actual_model": selected_model,
            "analysis": analysis,
            "prompt_version": self.registry.runtime["prompt_version"],
            "latency_ms": latency_ms,
            "resource_usage": resources,
            "usage": usage,
            "error_type": error_type,
        }
        evidence_id = self.evidence.append("LOCAL_AI_ANALYSIS", evidence_payload, decision.trace_id)
        result = AnalysisResult(
            ok=True, advisory=True, task_type=task_type, provider=selected_provider,
            model=selected_model, prompt_version=self.registry.runtime["prompt_version"],
            trace_id=decision.trace_id, evidence_id=evidence_id, timestamp=timestamp,
            fallback=fallback, error_type=error_type, latency_ms=latency_ms,
            resource_usage=resources, **analysis,
        )
        return result.to_dict()
