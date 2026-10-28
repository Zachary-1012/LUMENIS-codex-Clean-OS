"""Hermetic SYSTEM AI Gateway service routing and contract checks.

The fake verifier/runtime below exercise only in-process routing semantics.
They are not Permission, GPU, model-quality, deployment, or user-acceptance proof.
"""
from dataclasses import asdict, replace
import hashlib
import json

import pytest

from agent_capability.formation import implementation_identity
from lumenis.system.ai_gateway import core, owned_service


@pytest.fixture(autouse=True)
def _empty_service_slots():
    owned_service._SLOTS.clear()
    yield
    owned_service._SLOTS.clear()


def _sha(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _request(**changes):
    values = {
        "operation": "inference_generate",
        "request_id": "request-1",
        "job_id": "job-1",
        "actor_ref": "actor-1",
        "domain_id": "cth",
        "scope": "GLOBAL / ALL",
        "source_use_policy_version": "source-use-v1",
        "source_use_policy_sha256": _sha("source-use-policy"),
        "source_binding_sha256": _sha("source-binding"),
        "source_evidence_refs": ("evidence:1",),
        "input_revision_sha256": _sha("input-revision"),
        "system_prompt": "Answer only from the supplied evidence.",
        "user_payload": "Summarize the supplied evidence.",
        "response_schema_json": '',
        "max_output_tokens": 32,
    }
    values.update(changes)
    return owned_service.OwnedServiceRequest(**values)


def _source_validator(request):
    return owned_service.SourceUseDecision(
        allowed=True, code="SOURCE_USE_ALLOWED", actor_ref=request.actor_ref,
        domain_id=request.domain_id, scope=request.scope,
        source_use_policy_version=request.source_use_policy_version,
        source_use_policy_sha256=request.source_use_policy_sha256,
        source_binding_sha256=request.source_binding_sha256,
        source_evidence_refs=request.source_evidence_refs,
        scope_audit_id="scope-audit-1", source_audit_id="source-audit-1",
    )


class _FakeVerifier:
    def __init__(self, request, *, caller="actor-1"):
        self.request = request
        self.request_sha256 = _sha(json.dumps(asdict(request), sort_keys=True))
        self.resource = "test-admission-resource"
        self.public_identity = {"caller": caller, "request_sha256": self.request_sha256}

    def recheck(self):
        return type("Decision", (), {
            "allowed": True, "code": "EXACT_RUNTIME_APPROVAL_VERIFIED",
            "resource": self.resource, "request_sha256": self.request_sha256,
            "audit_hashes": {"permission": _sha("permission-audit")},
        })()


class _FakeRuntime:
    def __init__(self, identity, source_validator, dependency_paths=()):
        self._identity = identity
        self._source_validator = source_validator
        self._source_dependency_paths = tuple(dependency_paths)
        self.generated = 0
        self.output_override = None
        self.on_generate = None

    def identity(self):
        return dict(self._identity)

    def measure_request(self, request):
        return {'prompt_tokens': 17, 'output_tokens_reserved': request.max_output_tokens,
            'context_window_tokens': self._identity['context_window_tokens'],
            'output_token_limit': self._identity['output_token_limit'], 'fits': True,
            'request_sha256': owned_service.owned_service_request_digest(request),
            'runtime_sha256': self._identity['runtime_sha256'],
            'tokenizer_identity': self._identity['runtime_sha256'],
            'formatter_sha256': self._identity['executor_sha256'],
            'count_method': 'loaded_runtime_tokenizer', 'generation_performed': False}

    def generate(self, request, *, is_cancelled=None):
        self.generated += 1
        if self.on_generate is not None:
            self.on_generate()
        if is_cancelled is not None and is_cancelled():
            from lumenis.system.ai_gateway.owned_inference import OwnedInferenceBlocked

            raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCELLED")
        if self.output_override is not None:
            return self.output_override
        digest = owned_service.owned_service_request_digest(request)
        final = "<|start|>assistant<|channel|>final<|message|>A grounded answer.<|return|>"
        return {
            "generated_text": final, "text": final, "finish_reason": "stop",
            "termination_token": "<|return|>", "final_channel_prefill": True,
            "request_sha256": digest, "request_digest": digest,
            "run_id": "run-1", **self._identity,
            "prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16,
        }


def _admission_request(*, action="admit", prior=None, domain="cth", source_hash=None):
    return owned_service.OwnedModelAdmissionRequest(
        action=action, model_id="lumenis/owned-base", model_revision="rev-1",
        recipe="t4-recipe-v1", domain_id=domain, scopes=("GLOBAL / ALL",),
        manifest_sha256=_sha("manifest"), train_sha256=_sha("train"),
        heldout_sha256=_sha("heldout"), candidate_identity_sha256=_sha("candidate"),
        adapter_sha256=_sha("adapter"), adapter_config_sha256=_sha("adapter-config"),
        training_run_sha256=_sha("training-run"), checkpoint_recovery_sha256=_sha("recovery"),
        evaluation_sha256=_sha("evaluation"), quality_review_sha256=_sha("quality-review"),
        source_use_sha256=_sha("source-use-policy"), source_use_version="source-use-v1",
        evaluation_ref="evaluation:1", quality_review_ref="quality:1",
        runtime_sha256=_sha("runtime"), executor_sha256=_sha("executor"),
        review_validator_sha256=_sha("reviewer"),
        source_validator_sha256=source_hash or implementation_identity(_source_validator),
        allowed_operations=("inference_generate",), context_window_tokens=512,
        output_token_limit=64, prior_binding_sha256=prior,
    )


def _identity(request):
    return {
        "runtime_sha256": request.runtime_sha256,
        "executor_sha256": request.executor_sha256,
        "candidate_identity_sha256": request.candidate_identity_sha256,
        "model_id": request.model_id, "model_revision": request.model_revision,
        "recipe": request.recipe, "manifest_sha256": request.manifest_sha256,
        "train_sha256": request.train_sha256, "heldout_sha256": request.heldout_sha256,
        "adapter_sha256": request.adapter_sha256,
        "adapter_config_sha256": request.adapter_config_sha256,
        "context_window_tokens": request.context_window_tokens,
        "output_token_limit": request.output_token_limit,
    }


def _runtime_output(request, runtime, generated_text, *, text=None, request_digest=None):
    digest = owned_service.owned_service_request_digest(request)
    return {
        "generated_text": generated_text,
        "text": generated_text if text is None else text,
        "finish_reason": "stop", "termination_token": "<|return|>",
        "final_channel_prefill": True,
        "request_sha256": request_digest or digest,
        "request_digest": request_digest or digest,
        "run_id": "run-override", **runtime._identity,
        "prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16,
    }


def _binding(monkeypatch, request=None, *, caller="actor-1", source_validator=_source_validator):
    request = request or _admission_request(source_hash=implementation_identity(source_validator))
    verifier = _FakeVerifier(request, caller=caller)
    runtime = _FakeRuntime(_identity(request), source_validator)
    monkeypatch.setattr(owned_service, "_security_contract", lambda: (
        None, owned_service.OwnedModelAdmissionRequest, _FakeVerifier,
    ))
    monkeypatch.setattr(owned_service, "_runtime_type", lambda: _FakeRuntime)
    monkeypatch.setattr(owned_service, "_runtime_type_for_admission", lambda _request: _FakeRuntime)
    return owned_service.OwnedServiceBinding(
        admission_verifier=verifier, runtime=runtime,
        source_validator=source_validator, source_dependency_paths=(),
    ), runtime


def test_v1_trained_runtime_admission_is_retired_but_keeps_typed_history(monkeypatch):
    request = _admission_request()
    monkeypatch.setattr(owned_service, "_security_contract", lambda: (
        None, owned_service.OwnedModelAdmissionRequest, _FakeVerifier,
    ))

    with pytest.raises(owned_service.OwnedServiceBlocked, match="TRAINED_CUDA_RUNTIME_WITHDRAWN_BY_PO"):
        owned_service._runtime_type_for_admission(request)

    # The legacy request remains structurally readable for audit/revocation.
    owned_service._validate_admission_request(request)


def test_request_digest_is_exact_dataclass_payload_and_prompt_sensitive():
    request = _request()
    expected = hashlib.sha256(json.dumps(
        asdict(request), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    assert owned_service.owned_service_request_digest(request) == expected
    assert owned_service.owned_service_request_digest(
        replace(request, system_prompt="Different instructions.")
    ) != expected


def test_typed_request_routes_only_after_explicit_hermetic_binding(monkeypatch):
    request = _request(response_schema_json=json.dumps({
        "type": "object", "properties": {"answer": {"type": "string"}},
        "required": ["answer"], "additionalProperties": False,
    }, separators=(",", ":")))
    admission = _admission_request(source_hash=implementation_identity(_source_validator))
    # Keep the exact policy and scope identities aligned with the typed service request.
    request = replace(request, source_use_policy_sha256=admission.source_use_sha256)
    binding, runtime = _binding(monkeypatch, admission)
    owned_service.bind_owned_service(binding)

    generated = "<|start|>assistant<|channel|>final<|message|>{\"answer\":\"grounded\"}<|return|>"
    runtime.output_override = _runtime_output(request, runtime, generated)

    result = owned_service.run_owned_request(request)
    assert result["ok"] is True
    assert len(result.get('attempt_id', '')) == len('attempt_') + 32
    assert result['attempt_id'].startswith('attempt_')
    assert result["provider"] == "owned"
    assert result["analysis"] == {"answer": "grounded"}
    assert result["real_input_bound"] is True
    assert result["evaluation_state"] == "NOT_RUN"
    assert result["promotion_status"] == "NOT_PROMOTED"
    assert result["source_evidence_refs"] == ["evidence:1"]


def test_independent_shared_request_needs_its_own_scoped_binding(monkeypatch):
    request = _request(domain_id='shared', scope='shared_workspace:v1', operation='professional_creation')
    unavailable = owned_service.run_owned_request(request)
    assert unavailable['code'] == 'OWNED_SERVICE_EXECUTOR_NOT_BOUND'
    assert 'attempt_id' not in unavailable
    business, business_runtime = _binding(monkeypatch)
    owned_service.bind_owned_service(business)
    assert owned_service.run_owned_request(request)['code'] == 'OWNED_SERVICE_EXECUTOR_NOT_BOUND'
    assert business_runtime.generated == 0
    admitted = replace(_admission_request(domain='shared'), scopes=('shared_workspace:v1',),
                       allowed_operations=('professional_creation',))
    shared, runtime = _binding(monkeypatch, admitted)
    owned_service.bind_owned_service(shared)
    result = owned_service.run_owned_request(request)
    assert result['ok'] is True and runtime.generated == 1
    assert result['operation'] == 'professional_creation'
    assert business_runtime.generated == 0
    assert owned_service.run_owned_request(replace(request, scope='GLOBAL / ALL'))['code'] == 'OWNED_SERVICE_SCOPE_INVALID'
    assert owned_service.run_owned_request(replace(request, actor_ref='other-actor'))['code'] == 'OWNED_SERVICE_ACTOR_MISMATCH'


def test_actor_and_cancel_mismatch_fail_without_generation(monkeypatch):
    request = _request()
    binding, runtime = _binding(monkeypatch, caller="different-actor")
    owned_service.bind_owned_service(binding)

    actor_result = owned_service.run_owned_request(request)
    assert actor_result["ok"] is False
    assert actor_result["code"] == "OWNED_SERVICE_ACTOR_MISMATCH"
    assert 'attempt_id' not in actor_result
    assert runtime.generated == 0

    cancelled = owned_service.run_owned_request(request, is_cancelled=lambda: True)
    assert cancelled["status"] == "CANCELLED"
    assert 'attempt_id' not in cancelled
    assert runtime.generated == 0


@pytest.mark.parametrize("method_name", ["identity", "generate"])
def test_runtime_instance_method_shadow_is_rejected_before_binding(monkeypatch, method_name):
    binding, runtime = _binding(monkeypatch)
    shadow_calls = []
    setattr(runtime, method_name, lambda *args, **kwargs: shadow_calls.append(method_name))

    with pytest.raises(owned_service.OwnedServiceBlocked, match="OWNED_RUNTIME_METHOD_SHADOWED"):
        owned_service.bind_owned_service(binding)

    assert shadow_calls == []
    assert runtime.generated == 0


def test_runtime_generate_shadow_after_binding_cannot_replace_executor(monkeypatch):
    binding, runtime = _binding(monkeypatch)
    owned_service.bind_owned_service(binding)
    shadow_calls = []
    runtime.generate = lambda *args, **kwargs: shadow_calls.append("shadow")

    result = owned_service.run_owned_request(_request())

    assert result["ok"] is False
    assert result["code"] == "OWNED_RUNTIME_METHOD_SHADOWED"
    assert shadow_calls == []
    assert runtime.generated == 0


def test_request_input_drift_invalidates_the_bound_runtime_result(monkeypatch):
    request = _request()
    binding, runtime = _binding(monkeypatch)
    owned_service.bind_owned_service(binding)
    generated = "<|start|>assistant<|channel|>final<|message|>Pinned answer.<|return|>"
    runtime.output_override = _runtime_output(request, runtime, generated)

    changed = replace(request, user_payload="A changed input with the old runtime result.")
    result = owned_service.run_owned_request(changed)

    assert result["ok"] is False
    assert result["code"] == "OWNED_RUNTIME_RESULT_INVALID"
    assert result["request_digest"] == owned_service.owned_service_request_digest(changed)
    assert result['attempt_id'].startswith('attempt_')


def test_runtime_text_alias_drift_is_rejected(monkeypatch):
    request = _request()
    binding, runtime = _binding(monkeypatch)
    owned_service.bind_owned_service(binding)
    generated = "<|start|>assistant<|channel|>final<|message|>Grounded answer.<|return|>"
    runtime.output_override = _runtime_output(
        request, runtime, generated, text="Different unpinned text.<|return|>",
    )

    result = owned_service.run_owned_request(request)

    assert result["ok"] is False
    assert result["code"] == "OWNED_RUNTIME_RESULT_INVALID"


def test_runtime_structured_output_must_match_requested_schema(monkeypatch):
    request = _request(response_schema_json=json.dumps({
        "type": "object", "properties": {"answer": {"type": "string"}},
        "required": ["answer"], "additionalProperties": False,
    }, separators=(",", ":")))
    binding, runtime = _binding(monkeypatch, _admission_request())
    owned_service.bind_owned_service(binding)
    generated = "<|start|>assistant<|channel|>final<|message|>{\"other\":\"value\"}<|return|>"
    runtime.output_override = _runtime_output(request, runtime, generated)

    result = owned_service.run_owned_request(request)

    assert result["ok"] is False
    assert result["code"] == "OWNED_SERVICE_RESPONSE_SCHEMA_MISMATCH"
    assert result["analysis"] is None


def test_in_generation_cancellation_maps_runtime_cancel_to_cancelled(monkeypatch):
    request = _request()
    binding, runtime = _binding(monkeypatch)
    owned_service.bind_owned_service(binding)
    cancel = {"value": False}
    runtime.on_generate = lambda: cancel.update(value=True)

    result = owned_service.run_owned_request(
        request, is_cancelled=lambda: cancel["value"],
    )

    assert result["ok"] is False
    assert result["status"] == "CANCELLED"
    assert result["code"] == "OWNED_INFERENCE_CANCELLED"
    assert result['attempt_id'].startswith('attempt_')
    assert runtime.generated == 1


def test_in_flight_binding_replacement_cancels_the_old_run(monkeypatch):
    initial_request = _admission_request()
    initial, runtime = _binding(monkeypatch, initial_request)
    first = owned_service.bind_owned_service(initial)
    replacement_request = replace(
        initial_request, action="rollback", prior_binding_sha256=first["binding_sha256"],
    )
    replacement, _replacement_runtime = _binding(monkeypatch, replacement_request)
    runtime.on_generate = lambda: owned_service.bind_owned_service(replacement)

    result = owned_service.run_owned_request(_request())

    assert result["ok"] is False
    assert result["status"] == "CANCELLED"
    assert result["code"] == "OWNED_INFERENCE_CANCELLED"
    assert owned_service.owned_service_status("cth")["service_binding"] == "BOUND"


def test_source_validator_must_match_the_approved_source_pin(monkeypatch):
    def changed_source_validator(request):
        return _source_validator(request)

    admission = _admission_request(source_hash=implementation_identity(_source_validator))
    binding, runtime = _binding(
        monkeypatch, admission, source_validator=changed_source_validator,
    )

    with pytest.raises(owned_service.OwnedServiceBlocked, match="OWNED_SOURCE_VALIDATOR_HASH_MISMATCH"):
        owned_service.bind_owned_service(binding)

    assert runtime.generated == 0


def test_rollback_clear_and_revoke_require_the_exact_prior_binding(monkeypatch):
    admission = _admission_request()
    initial, _ = _binding(monkeypatch, admission)
    first = owned_service.bind_owned_service(initial)
    first_hash = first["binding_sha256"]

    with pytest.raises(owned_service.OwnedServiceBlocked, match="OWNED_SERVICE_BINDING_MISMATCH"):
        owned_service.clear_owned_service("cth", _sha("wrong-binding"))

    rollback_request = replace(
        admission, action="rollback", prior_binding_sha256=first_hash,
    )
    rollback, _ = _binding(monkeypatch, rollback_request)
    second = owned_service.bind_owned_service(rollback)
    assert second["status"] == "BOUND"
    assert second["binding_sha256"] != first_hash

    revoke_request = replace(
        admission, action="revoke", prior_binding_sha256=second["binding_sha256"],
    )
    revoke_verifier = _FakeVerifier(revoke_request)
    revoked = owned_service.revoke_owned_service(revoke_verifier)
    assert revoked["status"] == "REVOKED"
    assert owned_service.owned_service_status("cth")["service_binding"] == "NOT_BOUND"


def test_legacy_text_path_remains_unavailable_and_typed_path_is_forwarded(monkeypatch):
    legacy = core.run_owned_analysis(text="unscoped input", analysis_type="summary")
    assert legacy["ok"] is False
    assert legacy["status"] == "UNAVAILABLE"
    assert legacy["code"] == "OWNED_RUNTIME_NOT_BOUND"

    request = _request()
    expected = {"ok": False, "status": "BLOCKED", "code": "TEST_ROUTED"}
    calls = []
    monkeypatch.setattr(core, "run_owned_request", lambda actual, **kw: (calls.append((actual, kw)) or expected))
    result = core.run_owned_analysis(
        request=request, is_cancelled=lambda: False, note_id="note-1",
    )
    assert len(calls) == 1
    assert calls[0][0] is request
    assert calls[0][1]["is_cancelled"]() is False
    assert result["code"] == "TEST_ROUTED"
    assert result["note_id"] == "note-1"


def test_domain_slot_status_requires_explicit_canonical_scope():
    assert core.owned_inference_status()["available"] is False
    assert core.owned_inference_status("bmp")["reason"] == "OWNED_SERVICE_EXECUTOR_NOT_BOUND"
    assert core.owned_inference_status("zbmp")["reason"] == "OWNED_SERVICE_DOMAIN_INVALID"


def test_gateway_observation_reports_each_real_domain_slot_reason():
    status = core.owned_service_observation()

    assert status["available"] is False
    assert status["service_binding"] == "NOT_BOUND"
    assert set(status["domains"]) == {"cth", "bmp", "shared"}
    assert all(item["reason"] == "OWNED_SERVICE_EXECUTOR_NOT_BOUND"
               and item["available"] is False for item in status["domains"].values())


def test_status_reports_only_verified_bound_token_budget(monkeypatch):
    unavailable = owned_service.owned_service_status('cth')
    assert 'context_window_tokens' not in unavailable
    admission = _admission_request()
    binding, runtime = _binding(monkeypatch, admission)
    bound = owned_service.bind_owned_service(binding)
    status = owned_service.owned_service_status('cth')
    assert status['available'] is True
    assert status['context_window_tokens'] == admission.context_window_tokens
    assert status['output_token_limit'] == admission.output_token_limit
    assert status['binding_sha256'] == bound['binding_sha256']
    monkeypatch.setattr(owned_service, '_validate_binding', lambda *a, **kw: (_ for _ in ()).throw(
        owned_service.OwnedServiceBlocked('REVOKED')))
    revoked = owned_service.owned_service_status('cth')
    assert revoked['available'] is False
    assert 'context_window_tokens' not in revoked and 'output_token_limit' not in revoked


def test_restart_recovery_rebinds_only_fresh_exact_slots_and_never_replays(monkeypatch):
    binding, _runtime = _binding(monkeypatch)
    result = owned_service.restore_owned_service_bindings(
        lambda domain: binding if domain == "cth" else None,
    )

    assert result["automatic_replay"] is False
    assert result["generation_probe_performed"] is False
    assert result["domains"]["cth"]["state"] == "RESTORED"
    assert result["domains"]["bmp"]["state"] == "NOT_CONFIGURED"
    assert result["domains"]["shared"]["state"] == "NOT_CONFIGURED"
    assert owned_service.owned_service_status("cth")["available"] is True


def test_pretrained_restart_restore_cannot_be_called_without_an_owner_resolver():
    with pytest.raises(TypeError):
        core.restore_owned_pretrained_service_bindings()


def test_measurement_validates_bound_source_and_budget_without_generation(monkeypatch):
    binding, runtime = _binding(monkeypatch)
    owned_service.bind_owned_service(binding)
    result = owned_service.measure_owned_request(_request())
    assert result['ok'] is True and result['prompt_tokens'] == 17
    assert runtime.generated == 0
    assert owned_service.measure_owned_request(_request(actor_ref='other'))['ok'] is False
    assert runtime.generated == 0


def test_expected_measured_binding_must_match_before_generation(monkeypatch):
    binding, runtime = _binding(monkeypatch)
    bound = owned_service.bind_owned_service(binding)
    result = core.run_owned_request(_request(), expected_binding_sha256=bound['binding_sha256'])
    assert result['ok'] is True
    before = runtime.generated
    changed = core.run_owned_request(_request(), expected_binding_sha256='f' * 64)
    assert changed['code'] == 'OWNED_SERVICE_BINDING_CHANGED' and runtime.generated == before
    invalid = core.run_owned_request(_request(), expected_binding_sha256='invalid')
    assert invalid['status'] == 'INVALID_INPUT' and runtime.generated == before
    replacement_request = replace(binding.admission_verifier.request, action='rollback',
                                  prior_binding_sha256=bound['binding_sha256'])
    replacement, new_runtime = _binding(monkeypatch, replacement_request)
    newer = owned_service.bind_owned_service(replacement)
    replaced = core.run_owned_request(_request(), expected_binding_sha256=bound['binding_sha256'])
    assert replaced['code'] == 'OWNED_SERVICE_BINDING_CHANGED' and new_runtime.generated == 0
    assert core.run_owned_request(_request(), expected_binding_sha256=newer['binding_sha256'])['ok'] is True
