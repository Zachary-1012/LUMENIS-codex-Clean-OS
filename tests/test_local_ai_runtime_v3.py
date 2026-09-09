from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_ai_runtime.contracts import AnalysisRequest, RuntimeMode
from local_ai_runtime.evidence import EvidenceWriter
from local_ai_runtime.ollama import OllamaRuntimeError
from local_ai_runtime.benchmark import run_acceptance
from local_ai_runtime.research import ResearchBudget, ResearchOptimizer
from local_ai_runtime.registry import AIRuntimeRegistry, RegistryError
from local_ai_runtime.resource_guard import ResourceGuard, ResourceLimitError
from local_ai_runtime.router import IntelligenceRouter
from local_ai_runtime.security import sanitize_trace, validate_local_endpoint, validate_model_name
from local_ai_runtime.service import LocalFirstAIService, validate_analysis


class FakeOllama:
    def __init__(self, status: str = "UP", error: str | None = None):
        self.status = status
        self.error = error
        self.calls = 0

    def health(self, real_call: bool = False):
        return {"status": self.status, "installed": self.status == "UP", "error_type": "DOWN" if self.status != "UP" else ""}

    def chat(self, system, user, schema, max_tokens=512):
        self.calls += 1
        if self.error:
            raise OllamaRuntimeError(self.error, self.error)
        return {
            "content": {"summary": user[:40], "sentiment": "neutral", "topics": ["太古汇"], "confidence": 0.8, "fact_basis": "provided_text"},
            "latency_ms": 1,
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "done_reason": "stop",
        }


def test_registry_contains_governed_local_model() -> None:
    registry = AIRuntimeRegistry()
    model = registry.model("qwen2.5-coder:1.5b-instruct")
    assert model["provider"] == "OLLAMA_LOCAL"
    assert model["license_verified"] is True
    assert model["weight_license_verified"] is True
    assert registry.provider("OPENCODE_EXECUTION")["production_business_allowed"] is False
    assert registry.provider("CODEX_SOL")["engineering_only"] is True
    assert registry.provider("INTERACTION_MODEL_FUTURE")["status"] == "RESEARCH_ONLY"
    assert registry.runtime["default_model"] == model["id"]


def test_registry_rejects_unknown_license(tmp_path: Path) -> None:
    source = Path("config/ai_runtime")
    for name in ("providers.json", "models.json", "runtime.json"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    models = json.loads((tmp_path / "models.json").read_text(encoding="utf-8"))
    models["models"][0]["license_verified"] = False
    (tmp_path / "models.json").write_text(json.dumps(models), encoding="utf-8")
    with pytest.raises(RegistryError, match="unknown license"):
        AIRuntimeRegistry(tmp_path)


def test_registry_rejects_tampered_checksum_manifest(tmp_path: Path) -> None:
    source = Path("config/ai_runtime")
    for name in ("providers.json", "models.json", "runtime.json"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    models = json.loads((tmp_path / "models.json").read_text(encoding="utf-8"))
    models["models"][0]["checksum"] = "sha256:tampered"
    (tmp_path / "models.json").write_text(json.dumps(models), encoding="utf-8")
    with pytest.raises(RegistryError, match="invalid checksum"):
        AIRuntimeRegistry(tmp_path)


@pytest.mark.parametrize("mode", list(RuntimeMode))
def test_modes_are_configured_and_auditable(mode: RuntimeMode) -> None:
    registry = AIRuntimeRegistry()
    router = IntelligenceRouter(registry.runtime)
    decision = router.route(AnalysisRequest("事实", runtime_mode=mode), {"status": "UP", "installed": True})
    assert decision.selected_provider == "OLLAMA_LOCAL"
    assert mode.value in decision.reason
    assert decision.trace_id


def test_local_only_never_escalates_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", "must-not-be-used")
    registry = AIRuntimeRegistry()
    decision = IntelligenceRouter(registry.runtime).route(
        AnalysisRequest("事实", runtime_mode=RuntimeMode.LOCAL_ONLY),
        {"status": "DOWN", "installed": False, "error_type": "DOWN"},
        {"status": "UP"},
    )
    assert decision.selected_provider == "DETERMINISTIC_RULE"
    assert "ZHIPU" not in decision.fallback_chain


def test_cloud_fallback_requires_policy_error_and_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUD_AI_DISABLED", raising=False)
    monkeypatch.delenv("ZHIPU_DISABLED", raising=False)
    registry = AIRuntimeRegistry()
    router = IntelligenceRouter(registry.runtime)
    decision = router.route(
        AnalysisRequest("事实", runtime_mode=RuntimeMode.CLOUD_FALLBACK),
        {"status": "DOWN", "installed": False, "error_type": "TIMEOUT"},
        {"status": "UP"},
    )
    assert decision.selected_provider == "ZHIPU"


def test_cloud_disable_flag_blocks_escalation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_AI_DISABLED", "1")
    registry = AIRuntimeRegistry()
    decision = IntelligenceRouter(registry.runtime).route(
        AnalysisRequest("事实", runtime_mode=RuntimeMode.HYBRID),
        {"status": "DOWN", "installed": False, "error_type": "DOWN"},
        {"status": "UP"},
    )
    assert decision.selected_provider == "DETERMINISTIC_RULE"


def test_cloud_key_without_verified_adapter_does_not_escalate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", "test-placeholder")
    monkeypatch.delenv("ZHIPU_DISABLED", raising=False)
    monkeypatch.delenv("CLOUD_AI_DISABLED", raising=False)
    monkeypatch.setattr("local_ai_runtime.resource_guard._memory_snapshot", lambda: {"total_ram_mb": 16000, "available_ram_mb": 8000})
    service = LocalFirstAIService(evidence_dir=tmp_path, adapter=FakeOllama(status="DOWN"))
    result = service.analyze("事实", mode="CLOUD_FALLBACK")
    assert result["provider"] == "DETERMINISTIC_RULE"
    assert result["error_type"] == "DOWN"


def test_cloud_shadow_requires_explicit_governance_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", "test-placeholder")
    monkeypatch.delenv("LUMENIS_ZHIPU_SHADOW_ALLOWED", raising=False)
    monkeypatch.delenv("ZHIPU_DISABLED", raising=False)
    monkeypatch.delenv("CLOUD_AI_DISABLED", raising=False)
    monkeypatch.setattr("local_ai_runtime.resource_guard._memory_snapshot", lambda: {"total_ram_mb": 16000, "available_ram_mb": 8000})
    calls = []
    service = LocalFirstAIService(evidence_dir=tmp_path, adapter=FakeOllama(status="DOWN"), cloud_call=lambda **kw: calls.append(kw))
    result = service.analyze("事实", mode="CLOUD_FALLBACK")
    assert result["provider"] == "DETERMINISTIC_RULE"
    assert calls == []


def test_service_returns_structured_local_result_and_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("local_ai_runtime.resource_guard._memory_snapshot", lambda: {"total_ram_mb": 16000, "available_ram_mb": 8000})
    adapter = FakeOllama()
    service = LocalFirstAIService(evidence_dir=tmp_path, adapter=adapter)
    result = service.analyze("广州太古汇发布活动信息。", mode="LOCAL_ONLY", evidence_ids=["note-1"])
    assert result["provider"] == "OLLAMA_LOCAL"
    assert result["advisory"] is True
    assert result["evidence_id"]
    assert adapter.calls == 1
    assert service.evidence.verify() is True
    stored = (tmp_path / "ai-runtime-evidence.jsonl").read_text(encoding="utf-8")
    assert "note-1" in stored


def test_service_local_failure_is_explicit_and_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("local_ai_runtime.resource_guard._memory_snapshot", lambda: {"total_ram_mb": 16000, "available_ram_mb": 8000})
    adapter = FakeOllama(error="TIMEOUT")
    service = LocalFirstAIService(evidence_dir=tmp_path, adapter=adapter)
    result = service.analyze("用户投诉停车等待时间过长。", mode="LOCAL_ONLY")
    assert result["provider"] == "DETERMINISTIC_RULE"
    assert result["fallback"] is True
    assert result["error_type"] == "TIMEOUT"
    assert adapter.calls == 2


def test_invalid_structured_output_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_analysis({"summary": "missing"})


def test_resource_guard_rejects_low_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("local_ai_runtime.resource_guard._memory_snapshot", lambda: {"total_ram_mb": 16000, "available_ram_mb": 100})
    guard = ResourceGuard({"max_concurrency": 1, "max_queue": 1, "min_free_ram_mb": 1024, "cooldown_seconds": 0.01})
    with pytest.raises(ResourceLimitError, match="min_free_ram"):
        with guard.reserve():
            pass


def test_research_optimizer_never_mutates_production() -> None:
    optimizer = ResearchOptimizer(ResearchBudget(max_iterations=1, max_runtime_seconds=1, max_model_calls=0, max_resource_mb=32))
    result = optimizer.run("compact", lambda: '{"a": 1}', lambda: '{"a":1}', lambda a, b: json.loads(a) == json.loads(b))
    assert result["quality_equivalence"] is True
    assert result["production_mutation"] is False
    assert result["result"] in {"KEEP", "REJECT"}


def test_benchmark_contract_with_fake_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("local_ai_runtime.resource_guard._memory_snapshot", lambda: {"total_ram_mb": 16000, "available_ram_mb": 8000})
    service = LocalFirstAIService(evidence_dir=tmp_path, adapter=FakeOllama())
    report = run_acceptance(service)
    assert len(report["cases"]) == 6
    assert "quality_score" in report and "error_rate" in report


def test_security_blocks_remote_endpoint_and_unsafe_model() -> None:
    with pytest.raises(ValueError):
        validate_local_endpoint("https://example.com:11434")
    with pytest.raises(ValueError):
        validate_model_name("../../model")
    with pytest.raises(ValueError):
        validate_model_name("model;whoami")


def test_trace_sanitizes_secret() -> None:
    result = sanitize_trace({"authorization": "Bearer-secret-value", "completion_tokens": 12})
    assert "secret-value" not in json.dumps(result)
    assert result["completion_tokens"] == 12


def test_evidence_detects_tampering(tmp_path: Path) -> None:
    writer = EvidenceWriter(tmp_path)
    writer.append("TEST", {"value": 1}, "trace")
    assert writer.verify() is True
    writer.path.write_text(writer.path.read_text(encoding="utf-8").replace('"value": 1', '"value": 2'), encoding="utf-8")
    assert writer.verify() is False
