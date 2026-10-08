"""Hermetic contract tests for case AI evaluation through the owned Gateway.

All Case reads and Gateway results are fixture-only monkeypatches. These tests
do not prove live Permission, Evidence, model, database, or runtime behavior.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

import case_ai_evaluate
import cth_cases
from lumenis.system.ai_gateway import core, owned_service


SCORE_FIELDS = ("impact", "innovation", "replicability", "risk", "overall")
DIMENSION_FIELDS = ("impact", "innovation", "replicability", "risk")

EXPECTED_CASE_EVALUATION_SCHEMA = {
    "type": "object",
    "required": ["impact", "innovation", "replicability", "risk", "advice"],
    "properties": {
        "impact": {"type": "number", "minimum": 0, "maximum": 10},
        "innovation": {"type": "number", "minimum": 0, "maximum": 10},
        "replicability": {"type": "number", "minimum": 0, "maximum": 10},
        "risk": {"type": "number", "minimum": 0, "maximum": 10},
        "advice": {"type": "string", "minLength": 1, "maxLength": 800},
    },
    "additionalProperties": False,
}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _case_evaluation_schema() -> dict:
    factory = getattr(case_ai_evaluate, "case_evaluation_schema", None)
    if callable(factory):
        return factory()
    # Lets the contract tests reach the missing evaluator behavior on the
    # pre-implementation source. The dedicated schema test still requires the
    # production factory to exist and return these semantics.
    return copy.deepcopy(EXPECTED_CASE_EVALUATION_SCHEMA)


def _signed_case() -> dict:
    created_at = "2026-10-08T08:30:00+00:00"
    return {
        "case_id": "CASE-HERMETIC-001",
        "title": "危机应对案例",
        "question": "如何基于已授权材料评估该案例？" + "问题补充。" * 230,
        "state": "OPEN",
        "scope": {
            "product_id": "CTH",
            "domain_id": "cth",
            "global": False,
            "subject_id": "SUBJECT-HERMETIC-001",
            "brand_focus_id": None,
        },
        "created_at": created_at,
        "source_refs": [
            {"source_id": "SOURCE-HERMETIC-1", "scope_evidence_ref": "evidence:scope:one"},
            {"source_id": "SOURCE-HERMETIC-2", "scope_evidence_ref": "evidence:scope:two"},
        ],
        "source_job_id": "SOURCE-JOB-HERMETIC-001",
        "source_report_hash": _sha("hermetic-source-report"),
        "creation_evidence_ref": "app_evidence_records:9001",
        "analysis_state": "NOT_REQUESTED",
        "business_outcome": "NOT_OBSERVED",
        "timeline": [{"stage": "CASE", "state": "recorded", "occurred_at": created_at}],
    }


def _materials(case: dict) -> list[dict]:
    result = []
    for index, source_ref in enumerate(case["source_refs"], start=1):
        text = f"Hermetic source material {index}. " + ("证据正文。" * 1_000)
        result.append({
            "source_id": source_ref["source_id"],
            "text": text,
            "content_evidence_ref": f"evidence:content:{index}",
            "body_sha256": _sha(text),
            "provenance": {
                "fixture": "HERMETIC_ONLY",
                "publication_time": "UNKNOWN",
                "use_rights": "test-only",
            },
        })
    return result


def _request(case: dict, materials: list[dict], **changes) -> owned_service.OwnedServiceRequest:
    payload = _canonical_json({"case": case, "materials": materials})
    evidence_refs = [case["creation_evidence_ref"]]
    evidence_refs.extend(item["scope_evidence_ref"] for item in case["source_refs"])
    evidence_refs.extend(item["content_evidence_ref"] for item in materials)
    values = {
        "operation": "case_evaluate",
        "request_id": "request-HERMETIC-001",
        "job_id": "job-HERMETIC-001",
        "actor_ref": "actor-HERMETIC-001",
        "domain_id": "cth",
        "scope": case["scope"]["subject_id"],
        "source_use_policy_version": "cth-case-source-use-v1",
        "source_use_policy_sha256": _sha("hermetic-source-use-policy"),
        "source_binding_sha256": _sha("hermetic-source-binding"),
        "source_evidence_refs": tuple(evidence_refs),
        "input_revision_sha256": _sha(payload),
        "system_prompt": "Evaluate only the supplied authorized Case and materials.",
        "user_payload": payload,
        "response_schema_json": _canonical_json(_case_evaluation_schema()),
        "max_output_tokens": 512,
    }
    values.update(changes)
    return owned_service.OwnedServiceRequest(**values)


def _owned_success(request: owned_service.OwnedServiceRequest, analysis: dict) -> dict:
    request_digest = owned_service.owned_service_request_digest(request)
    return {
        "ok": True,
        "status": "COMPLETED",
        "code": "OWNED_INFERENCE_COMPLETED",
        "provider": "owned",
        "request_id": request.request_id,
        "request_digest": request_digest,
        "run_id": "run-HERMETIC-001",
        "model_id": "model-HERMETIC-001",
        "model_revision": "revision-HERMETIC-001",
        "recipe": "recipe-HERMETIC-001",
        "candidate_identity_sha256": _sha("candidate-identity"),
        "adapter_sha256": _sha("adapter"),
        "adapter_config_sha256": _sha("adapter-config"),
        "runtime_sha256": _sha("runtime"),
        "executor_sha256": _sha("executor"),
        "manifest_sha256": _sha("manifest"),
        "train_sha256": _sha("train"),
        "heldout_sha256": _sha("heldout"),
        "context_window_tokens": 4096,
        "output_token_limit": 1024,
        "training_run_sha256": _sha("training-run"),
        "checkpoint_recovery_sha256": _sha("checkpoint-recovery"),
        "evaluation_sha256": _sha("evaluation"),
        "quality_review_sha256": _sha("quality-review"),
        "evaluation_ref": "evaluation:HERMETIC-001",
        "quality_review_ref": "quality:HERMETIC-001",
        "source_use_policy_version": request.source_use_policy_version,
        "source_use_policy_sha256": request.source_use_policy_sha256,
        "source_binding_sha256": request.source_binding_sha256,
        "input_revision_sha256": request.input_revision_sha256,
        "source_evidence_refs": list(request.source_evidence_refs),
        "source_audit_ids": {
            "scope_before": "scope-audit-before-HERMETIC",
            "source_before": "source-audit-before-HERMETIC",
            "scope_after": "scope-audit-after-HERMETIC",
            "source_after": "source-audit-after-HERMETIC",
        },
        "admission_request_sha256": _sha("admission-request"),
        "admission_audit_hashes": {
            "permission": _sha("permission-audit"),
            "admission": _sha("admission-audit"),
        },
        "text": None,
        "analysis": copy.deepcopy(analysis),
        "response_schema_state": "SUBSET_VALIDATED",
        "prompt_tokens": 120,
        "completion_tokens": 32,
        "total_tokens": 152,
        "real_input_bound": True,
        "evaluation_state": "NOT_RUN",
        "quality_state": "NOT_EVALUATED",
        "promotion_status": "NOT_PROMOTED",
        "product_acceptance": False,
    }


def _valid_analysis(**changes) -> dict:
    analysis = {
        "impact": 0,
        "innovation": 10,
        "replicability": 5.5,
        "risk": 10,
        "advice": "结论仅基于已绑定材料。",
    }
    analysis.update(changes)
    return analysis


def _forbid_legacy_provider(monkeypatch) -> list[tuple]:
    calls = []

    def forbidden(name):
        def fail(*args, **kwargs):
            calls.append((name, args, kwargs))
            raise AssertionError(f"legacy provider helper called: {name}")
        return fail

    monkeypatch.setattr(case_ai_evaluate, "_get_zhipu_key", forbidden("_get_zhipu_key"))
    monkeypatch.setattr(case_ai_evaluate, "_chat", forbidden("_chat"))
    return calls


def _install_harness(
    monkeypatch,
    case: dict,
    result: dict,
    *,
    second_case: dict | None = None,
    second_error: Exception | None = None,
):
    reads = []
    calls = []
    events = []

    def get_case(case_id, *, actor_ref, expected_scope):
        events.append("case-read")
        reads.append((case_id, actor_ref, copy.deepcopy(expected_scope)))
        assert case_id == case["case_id"]
        assert actor_ref == "actor-HERMETIC-001"
        assert expected_scope == case["scope"]
        if len(reads) > 1 and second_error is not None:
            raise second_error
        selected = second_case if len(reads) > 1 and second_case is not None else case
        return copy.deepcopy(selected)

    def run_owned_request(request, *, is_cancelled=None):
        events.append("gateway")
        calls.append((request, is_cancelled))
        return copy.deepcopy(result)

    monkeypatch.setattr(cth_cases, "get_cth_case", get_case)
    monkeypatch.setattr(core, "run_owned_request", run_owned_request)
    return {"reads": reads, "calls": calls, "events": events}


def _assert_no_scores(result: dict) -> None:
    ai = result["ai"]
    assert ai["enabled"] is False
    assert ai["score"] == {field: None for field in SCORE_FIELDS}
    assert ai["advice"] == ""


def _assert_advisory_templates(result: dict) -> None:
    assert result["templates_state"] == "LOCAL_ADVISORY"
    assert result["templates_are_evidence"] is False
    assert isinstance(result["templates"], list)
    assert result["templates"]


def _flatten_ai_metadata(ai: dict) -> dict:
    metadata = dict(ai)
    provenance = ai.get("provenance")
    if isinstance(provenance, dict):
        metadata.update(provenance)
    return metadata


def test_schema_requires_all_finite_bounded_scores_and_nonempty_advice():
    schema = case_ai_evaluate.case_evaluation_schema()
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {*DIMENSION_FIELDS, "advice"}
    for field in DIMENSION_FIELDS:
        assert schema["properties"][field]["type"] == "number"
        assert schema["properties"][field]["minimum"] == 0
        assert schema["properties"][field]["maximum"] == 10
    assert schema["properties"]["advice"]["type"] == "string"
    assert schema["properties"]["advice"]["minLength"] >= 1
    assert schema["properties"]["advice"]["maxLength"] == 800


def test_missing_request_is_unavailable_and_templates_remain_advisory(monkeypatch):
    case = _signed_case()
    provider_calls = _forbid_legacy_provider(monkeypatch)

    def forbidden_db_read(*args, **kwargs):
        raise AssertionError("Case database read must not happen without a typed request")

    def forbidden_gateway(*args, **kwargs):
        raise AssertionError("Gateway must not run without a typed request")

    monkeypatch.setattr(cth_cases, "get_cth_case", forbidden_db_read)
    monkeypatch.setattr(core, "run_owned_request", forbidden_gateway)

    result = case_ai_evaluate.evaluate_case(case)

    _assert_no_scores(result)
    assert result["ai"]["status"] == "UNAVAILABLE"
    assert result["ai"]["code"] == "CASE_OWNED_REQUEST_REQUIRED"
    _assert_advisory_templates(result)
    assert provider_calls == []


def test_valid_owned_result_preserves_case_payload_lineage_and_formula(monkeypatch):
    case = _signed_case()
    materials = _materials(case)
    request = _request(case, materials)
    gateway_result = _owned_success(request, _valid_analysis())
    harness = _install_harness(monkeypatch, case, gateway_result)
    provider_calls = _forbid_legacy_provider(monkeypatch)
    cancel_check = lambda: False

    validation_calls = []
    original_validator = owned_service.validate_owned_service_request

    def track_validation(value):
        validation_calls.append(value)
        return original_validator(value)

    monkeypatch.setattr(owned_service, "validate_owned_service_request", track_validation)
    if hasattr(case_ai_evaluate, "validate_owned_service_request"):
        monkeypatch.setattr(case_ai_evaluate, "validate_owned_service_request", track_validation)

    result = case_ai_evaluate.evaluate_case(case, request=request, is_cancelled=cancel_check)

    assert harness["events"] == ["case-read", "gateway", "case-read"]
    assert harness["reads"] == [
        (case["case_id"], request.actor_ref, case["scope"]),
        (case["case_id"], request.actor_ref, case["scope"]),
    ]
    assert harness["calls"] == [(request, cancel_check)]
    assert request in validation_calls
    assert request.operation == "case_evaluate"
    assert request.domain_id == "cth"
    assert request.scope == case["scope"]["subject_id"]
    assert request.response_schema_json == _canonical_json(case_ai_evaluate.case_evaluation_schema())

    payload = json.loads(request.user_payload)
    assert list(payload) == ["case", "materials"]
    assert payload == {"case": case, "materials": materials}
    assert request.user_payload == _canonical_json({"case": case, "materials": materials})
    assert request.input_revision_sha256 == _sha(request.user_payload)
    assert [row["source_id"] for row in payload["materials"]] == [
        row["source_id"] for row in case["source_refs"]
    ]
    assert len(request.user_payload) > 10_000
    assert len(case["question"]) > 1_000
    assert len(payload["materials"][0]["text"]) > 5_000

    ai = result["ai"]
    assert ai["enabled"] is True
    assert ai["claim_type"] == "INFERRED"
    assert ai["score"] == {
        "impact": 0,
        "innovation": 10,
        "replicability": 5.5,
        "risk": 10,
        "overall": 3.9,
    }
    assert ai["advice"] == "结论仅基于已绑定材料。"
    assert ai["evaluation_state"] == "NOT_RUN"
    assert ai["quality_state"] == "NOT_EVALUATED"
    assert ai["product_acceptance"] is False

    metadata = _flatten_ai_metadata(ai)
    for key in (
        "request_id", "request_digest", "run_id", "model_id", "model_revision", "recipe",
        "candidate_identity_sha256", "adapter_sha256", "adapter_config_sha256",
        "runtime_sha256", "executor_sha256", "manifest_sha256", "train_sha256",
        "heldout_sha256", "training_run_sha256", "checkpoint_recovery_sha256",
        "evaluation_sha256", "quality_review_sha256", "evaluation_ref", "quality_review_ref",
        "source_use_policy_version", "source_use_policy_sha256", "source_binding_sha256",
        "input_revision_sha256", "source_evidence_refs", "source_audit_ids",
        "admission_request_sha256", "admission_audit_hashes", "prompt_tokens",
        "completion_tokens", "total_tokens", "promotion_status",
    ):
        assert key in metadata
    assert metadata["request_digest"] == gateway_result["request_digest"]
    assert metadata["source_use_policy_sha256"] == request.source_use_policy_sha256
    assert metadata["source_binding_sha256"] == request.source_binding_sha256
    assert metadata["input_revision_sha256"] == request.input_revision_sha256
    assert metadata["source_evidence_refs"] == list(request.source_evidence_refs)
    assert gateway_result["real_input_bound"] is True
    assert metadata["prompt_tokens"] + metadata["completion_tokens"] == metadata["total_tokens"]
    _assert_advisory_templates(result)
    assert provider_calls == []


@pytest.mark.parametrize(
    "bad_value",
    [True, "5", -0.01, 10.01, float("nan"), float("inf"), -float("inf")],
    ids=["bool", "numeric-string", "below-range", "above-range", "nan", "positive-inf", "negative-inf"],
)
def test_bad_dimension_values_never_receive_scores_or_overall(monkeypatch, bad_value):
    case = _signed_case()
    request = _request(case, _materials(case))
    result = _owned_success(request, _valid_analysis(impact=bad_value))
    _install_harness(monkeypatch, case, result)
    _forbid_legacy_provider(monkeypatch)

    outcome = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(outcome)


@pytest.mark.parametrize("missing_field", DIMENSION_FIELDS)
def test_missing_dimension_never_defaults_to_five_or_computes_overall(monkeypatch, missing_field):
    case = _signed_case()
    request = _request(case, _materials(case))
    analysis = _valid_analysis()
    analysis.pop(missing_field)
    _install_harness(monkeypatch, case, _owned_success(request, analysis))
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(result)


@pytest.mark.parametrize("advice", ["", "x" * 801, 7], ids=["empty", "too-long", "wrong-type"])
def test_invalid_advice_fails_the_owned_evaluation(monkeypatch, advice):
    case = _signed_case()
    request = _request(case, _materials(case))
    _install_harness(monkeypatch, case, _owned_success(request, _valid_analysis(advice=advice)))
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(result)


@pytest.mark.parametrize(
    "mutation",
    ["wrong-operation", "wrong-domain", "wrong-scope", "wrong-schema", "payload-extra-key", "bad-revision", "bad-evidence-refs", "untyped"],
)
def test_request_mismatch_fails_before_gateway(monkeypatch, mutation):
    case = _signed_case()
    materials = _materials(case)
    request = _request(case, materials)
    if mutation == "wrong-operation":
        request = replace(request, operation="summary")
    elif mutation == "wrong-domain":
        request = replace(request, domain_id="bmp")
    elif mutation == "wrong-scope":
        request = replace(request, scope="SUBJECT-OTHER")
    elif mutation == "wrong-schema":
        request = replace(
            request,
            response_schema_json=_canonical_json({
                "type": "object", "required": [], "properties": {}, "additionalProperties": False,
            }),
        )
    elif mutation == "payload-extra-key":
        payload = {"case": case, "materials": materials, "extra": "not allowed"}
        encoded = _canonical_json(payload)
        request = replace(request, user_payload=encoded, input_revision_sha256=_sha(encoded))
    elif mutation == "bad-revision":
        request = replace(request, input_revision_sha256=_sha("different revision"))
    elif mutation == "bad-evidence-refs":
        request = replace(request, source_evidence_refs=("evidence:unrelated",))
    elif mutation == "untyped":
        request = asdict(request)

    gateway_calls = []

    def forbidden_gateway(*args, **kwargs):
        gateway_calls.append((args, kwargs))
        raise AssertionError("invalid request must not reach the Gateway")

    monkeypatch.setattr(core, "run_owned_request", forbidden_gateway)
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(result)
    assert gateway_calls == []


@pytest.mark.parametrize("mutation", ["missing-source", "extra-source", "duplicate-source", "body-hash-format"])
def test_materials_must_bind_exact_sources_and_body_hashes(monkeypatch, mutation):
    case = _signed_case()
    materials = _materials(case)
    if mutation == "missing-source":
        materials = materials[:1]
    elif mutation == "extra-source":
        materials.append({
            "source_id": "SOURCE-HERMETIC-EXTRA",
            "text": "extra source text",
            "content_evidence_ref": "evidence:content:extra",
            "body_sha256": _sha("extra source text"),
        })
    elif mutation == "duplicate-source":
        materials.append({
            **copy.deepcopy(materials[0]),
            "content_evidence_ref": "evidence:content:duplicate",
        })
    elif mutation == "body-hash-format":
        materials[0]["body_sha256"] = "not-a-sha256-digest"

    request = _request(case, materials)
    gateway_calls = []

    def forbidden_gateway(*args, **kwargs):
        gateway_calls.append((args, kwargs))
        raise AssertionError("unbound or duplicate material must not reach the Gateway")

    monkeypatch.setattr(core, "run_owned_request", forbidden_gateway)
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(result)
    assert gateway_calls == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_digest", _sha("replayed request")),
        ("source_use_policy_sha256", _sha("different policy")),
        ("source_binding_sha256", _sha("different binding")),
        ("input_revision_sha256", _sha("different revision")),
        ("source_evidence_refs", ["evidence:unrelated"]),
        ("request_id", "request-OTHER"),
    ],
)
def test_replayed_or_mismatched_gateway_result_is_discarded(monkeypatch, field, value):
    case = _signed_case()
    request = _request(case, _materials(case))
    result = _owned_success(request, _valid_analysis())
    result[field] = value
    _install_harness(monkeypatch, case, result)
    _forbid_legacy_provider(monkeypatch)

    outcome = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(outcome)


@pytest.mark.parametrize(
    "field",
    ["run_id", "model_id", "model_revision", "recipe", "source_audit_ids", "admission_audit_hashes", "total_tokens"],
)
def test_incomplete_gateway_provenance_or_token_metadata_fails_closed(monkeypatch, field):
    case = _signed_case()
    request = _request(case, _materials(case))
    result = _owned_success(request, _valid_analysis())
    result.pop(field)
    _install_harness(monkeypatch, case, result)
    _forbid_legacy_provider(monkeypatch)

    outcome = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(outcome)


@pytest.mark.parametrize("failure_status", ["UNAVAILABLE", "ERROR", "BLOCKED"])
def test_gateway_failure_is_unavailable_without_scores_or_raw_details(monkeypatch, failure_status):
    case = _signed_case()
    request = _request(case, _materials(case))
    gateway_failure = {
        "ok": False,
        "status": failure_status,
        "code": "OWNED_RUNTIME_NOT_BOUND",
        "provider": "owned",
        "request_id": request.request_id,
        "request_digest": owned_service.owned_service_request_digest(request),
        "text": None,
        "analysis": None,
        "real_input_bound": False,
        "evaluation_state": "NOT_RUN",
        "quality_state": "NOT_EVALUATED",
        "promotion_status": "NOT_PROMOTED",
        "debug_detail": "SENTINEL_PRIVATE_DETAIL_MUST_NOT_ESCAPE",
    }
    _install_harness(monkeypatch, case, gateway_failure)
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    _assert_no_scores(result)
    assert "SENTINEL_PRIVATE_DETAIL_MUST_NOT_ESCAPE" not in repr(result)
    assert "OWNED_RUNTIME_NOT_BOUND" in repr(result)


@pytest.mark.parametrize("second_case", ["changed-question", "changed-source", "changed-report"])
def test_case_change_after_gateway_read_discards_result(monkeypatch, second_case):
    case = _signed_case()
    request = _request(case, _materials(case))
    changed = copy.deepcopy(case)
    if second_case == "changed-question":
        changed["question"] += " changed"
    elif second_case == "changed-source":
        changed["source_refs"][0]["source_id"] = "SOURCE-OTHER"
    else:
        changed["source_report_hash"] = _sha("newer source report")
    result = _owned_success(request, _valid_analysis())
    harness = _install_harness(monkeypatch, case, result, second_case=changed)
    _forbid_legacy_provider(monkeypatch)

    outcome = case_ai_evaluate.evaluate_case(case, request=request)

    assert len(harness["reads"]) == 2
    assert len(harness["calls"]) == 1
    _assert_no_scores(outcome)


def test_reader_revocation_after_generation_discards_result_and_sanitizes_error(monkeypatch):
    case = _signed_case()
    request = _request(case, _materials(case))
    harness = _install_harness(
        monkeypatch,
        case,
        _owned_success(request, _valid_analysis()),
        second_error=PermissionError("SENTINEL_PRIVATE_READER_DETAIL"),
    )
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    assert len(harness["reads"]) == 2
    assert len(harness["calls"]) == 1
    _assert_no_scores(result)
    assert "SENTINEL_PRIVATE_READER_DETAIL" not in repr(result)


@pytest.mark.parametrize("mutation", ["changed-before-gateway", "legacy-shape-before-gateway"])
def test_case_must_match_current_signed_snapshot_before_gateway(monkeypatch, mutation):
    case = _signed_case()
    request = _request(case, _materials(case))
    changed = copy.deepcopy(case)
    if mutation == "changed-before-gateway":
        changed["question"] += " changed before evaluation"
    else:
        changed = {"case_id": case["case_id"], "case_title": "legacy case library object"}

    reads = []
    gateway_calls = []

    def get_case(case_id, *, actor_ref, expected_scope):
        reads.append((case_id, actor_ref, copy.deepcopy(expected_scope)))
        return copy.deepcopy(changed)

    def run_owned_request(*args, **kwargs):
        gateway_calls.append((args, kwargs))
        raise AssertionError("mismatched Case must not reach Gateway")

    monkeypatch.setattr(cth_cases, "get_cth_case", get_case)
    monkeypatch.setattr(core, "run_owned_request", run_owned_request)
    _forbid_legacy_provider(monkeypatch)

    result = case_ai_evaluate.evaluate_case(case, request=request)

    assert reads
    assert gateway_calls == []
    _assert_no_scores(result)


def test_legacy_provider_shims_are_inert_without_env_or_network(monkeypatch):
    class ForbiddenEnvironment:
        def get(self, *args, **kwargs):
            raise AssertionError("legacy key helper read environment")

    network_calls = []

    def forbidden_urlopen(*args, **kwargs):
        network_calls.append((args, kwargs))
        raise AssertionError("provider network call blocked by test")

    monkeypatch.setattr(
        case_ai_evaluate,
        "os",
        SimpleNamespace(environ=ForbiddenEnvironment(), getenv=ForbiddenEnvironment().get),
        raising=False,
    )
    monkeypatch.setattr(
        case_ai_evaluate,
        "urllib",
        SimpleNamespace(request=SimpleNamespace(urlopen=forbidden_urlopen)),
        raising=False,
    )
    monkeypatch.setattr(
        case_ai_evaluate,
        "time",
        SimpleNamespace(sleep=lambda _seconds: None),
        raising=False,
    )

    assert case_ai_evaluate._get_zhipu_key() == ""
    assert case_ai_evaluate._chat("hermetic compatibility probe") == ""
    assert hasattr(case_ai_evaluate, "_ZHIPU_URL")
    assert network_calls == []
