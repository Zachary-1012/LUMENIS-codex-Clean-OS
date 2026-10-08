"""Hermetic BusinessBrief-to-owned-Gateway contract regressions.

The Gateway result is synthetic in the success cases. These tests prove the
typed request, source-use boundary, persistence and reopen contract only; they
do not prove an installed runtime, real model quality, or user acceptance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from tests.test_saved_document_workflow import _source, workspace
from lumenis.shared.evidence import store as evidence_store
from lumenis.shared.reporting import business_brief as brief
from lumenis.shared.reporting import media_brief
from lumenis.system.ai_gateway import core as gateway, owned_service
from lumenis.system.security import permission


JOB_ID = "business-brief-owned-0001"
QUESTION = "What can this source support, and what useful next steps remain unknown?"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _wire_repositories(workspace, monkeypatch):
    # The imported fixture already points these owners at its disposable DB.
    # BusinessBrief and its row reader are wired to that same repository here.
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    monkeypatch.setattr(media_brief, "get_repository", lambda: workspace["repo"])


def _seed_source(workspace, *, filename="owned-business-source.txt"):
    _, _, imported = _source(workspace, filename=filename)
    row = workspace["repo"].query_one(
        "SELECT id, asset_id, content_hash, collection_metadata "
        "FROM app_evidence_records WHERE id=?",
        (imported["evidence_id"],),
    )
    assert row is not None
    evidence_id, asset_id, content_hash, metadata_json = row
    metadata = json.loads(metadata_json)
    parsed_text = metadata["parsed_text"]
    canonical = workspace["repo"].query_one(
        "SELECT title, publish_datetime, source_platform FROM canonical_data WHERE source_id=?",
        (asset_id,),
    )
    assert canonical is not None
    title, publish_datetime, source_platform = canonical
    assert imported["source_id"] == asset_id
    assert hashlib.sha256(parsed_text.encode("utf-8")).hexdigest() == content_hash
    return {
        "source_id": asset_id,
        "evidence_ref": str(evidence_id),
        "text": parsed_text,
        "body_sha256": content_hash,
        "title": title,
        "publish_datetime": publish_datetime,
        "source_platform": source_platform,
    }, imported


def _analyze(workspace, source, *, before_evidence=None, max_output_tokens=4096):
    actor_ref = media_brief._actor_ref(workspace["actor"])
    return brief.analyze_business_brief(
        question=QUESTION,
        sources=[source],
        sample={"test_only": True, "coverage": "PARTIAL"},
        scope=workspace["scope"],
        job_id=JOB_ID,
        actor_ref=actor_ref,
        actor=workspace["actor"],
        before_evidence=before_evidence,
        max_output_tokens=max_output_tokens,
    )


def _analysis(source_id):
    pilot = {
        "audience": "Invite a small group who agrees to review the two concepts.",
        "procedure": "Show both drafts in alternating order and record each response.",
        "measure": "Record the participant's interpretation, preference and reason.",
        "continue_if": "Continue exploring only if participants understand the intended message.",
        "stop_if": "Revise after confusion and draw no conclusion from insufficient feedback.",
    }
    return {
        "source_observations": [{"source_id": source_id, "excerpt_index": 0}],
        "interpretations": [
            {"text": "This material supports a claim about its own wording only.",
             "source_ids": [source_id]},
            {"text": "Audience response remains unverified without direct feedback.",
             "source_ids": [source_id]},
        ],
        "proposed_actions": [
            {"action": "Compare two concise versions of the message.",
             "reason": "The source provides wording to examine, not evidence of impact.",
             "check": "Ask reviewers what each version communicates before choosing.",
             "source_ids": [source_id], "pilot": dict(pilot)},
            {"action": "Check whether the source wording needs additional context.",
             "reason": "The present material does not establish the audience's interpretation.",
             "check": "Record misunderstandings and revise the wording for another review.",
             "source_ids": [source_id], "pilot": dict(pilot)},
        ],
        "unknowns": [
            "No customer response or business outcome is established by this source.",
            "Review resources and source-use rights still require confirmation.",
        ],
    }


def _owned_result(request, *, actor, analysis=None):
    payload = json.loads(request.user_payload)
    source_id = payload["material"]["sources"][0]["source_id"]
    before = brief.validate_business_source_use(request, actor=actor)
    after = brief.validate_business_source_use(request, actor=actor)
    request_digest = owned_service.owned_service_request_digest(request)
    result = {
        "ok": True,
        "status": "COMPLETED",
        "code": "OWNED_INFERENCE_COMPLETED",
        "provider": "owned",
        "request_id": request.request_id,
        "request_digest": request_digest,
        "run_id": "fixture-owned-run-0001",
        "model_id": "fixture-owned-model",
        "model_revision": "fixture-owned-revision-1",
        "recipe": "fixture-owned-recipe-1",
        "candidate_identity_sha256": _sha("candidate-identity"),
        "adapter_sha256": _sha("adapter"),
        "adapter_config_sha256": _sha("adapter-config"),
        "runtime_sha256": _sha("runtime"),
        "executor_sha256": _sha("executor"),
        "manifest_sha256": _sha("manifest"),
        "train_sha256": _sha("train"),
        "heldout_sha256": _sha("heldout"),
        "training_run_sha256": _sha("training-run"),
        "checkpoint_recovery_sha256": _sha("checkpoint-recovery"),
        "evaluation_sha256": _sha("evaluation"),
        "quality_review_sha256": _sha("quality-review"),
        "evaluation_ref": "fixture-evaluation-ref",
        "quality_review_ref": "fixture-quality-review-ref",
        "source_use_policy_version": request.source_use_policy_version,
        "source_use_policy_sha256": request.source_use_policy_sha256,
        "source_binding_sha256": request.source_binding_sha256,
        "input_revision_sha256": request.input_revision_sha256,
        "source_evidence_refs": list(request.source_evidence_refs),
        "source_audit_ids": {
            "scope_before": before.scope_audit_id,
            "source_before": before.source_audit_id,
            "scope_after": after.scope_audit_id,
            "source_after": after.source_audit_id,
        },
        "admission_request_sha256": _sha("admission-request"),
        "admission_audit_hashes": {"admission": _sha("admission-audit")},
        "analysis": analysis or _analysis(source_id),
        "response_schema_state": "SUBSET_VALIDATED",
        "context_window_tokens": 16384,
        "output_token_limit": 4096,
        "prompt_tokens": 100,
        "completion_tokens": 500,
        "total_tokens": 600,
        "real_input_bound": True,
        "evaluation_state": "NOT_RUN",
        "quality_state": "NOT_EVALUATED",
        "promotion_status": "NOT_PROMOTED",
        "product_acceptance": False,
    }
    return result


def _forbid_gateway(monkeypatch):
    calls = []

    def forbidden(request, **kwargs):
        calls.append(request)
        pytest.fail("invalid source or permission reached the owned Gateway")

    monkeypatch.setattr(brief.gateway, "run_owned_request", forbidden)
    return calls


def _assert_no_business_evidence(workspace):
    count = workspace["repo"].query_one(
        "SELECT COUNT(*) FROM app_evidence_records "
        "WHERE feature_id IN ('REPORT_BUSINESS_ANALYSIS','REPORT_BUSINESS_ANALYSIS_REJECTED')"
    )[0]
    assert count == 0


def _signed_source_variant(workspace, source, *, suffix, rights=None, artifact_ref=None):
    """Create a writer-signed isolated boundary fixture, not a production source."""
    original_id = int(source["evidence_ref"])
    row = workspace["repo"].query_one(
        "SELECT version, captured_at, publish_datetime, collection_metadata "
        "FROM app_evidence_records WHERE id=?",
        (original_id,),
    )
    assert row is not None
    version, captured_at, publish_datetime, metadata_json = row
    metadata = json.loads(metadata_json)
    source_id = source["source_id"] + suffix
    if rights is not None:
        metadata["provenance"]["rights"] = rights
    if artifact_ref is not None:
        metadata["source_artifact_ref"] = artifact_ref
    parsed_text = metadata["parsed_text"]
    scope = workspace["scope"]
    with workspace["repo"].transaction() as connection:
        evidence_id = evidence_store.record_evidence(
            connection=connection,
            source="document_import",
            product="CTH",
            feature_id="DOCUMENT_IMPORT_TEST_VARIANT",
            asset_id=source_id,
            version=version,
            env="staging",
            test_name=source_id,
            capture_mode="file_import",
            captured_at=captured_at,
            inputs={"source_ids": [source_id], "fixture_variant": suffix},
            outputs={"parsed_text_sha256": _sha(parsed_text)},
            result="PASS",
            status="verified",
            raw_content=parsed_text,
            collection_metadata=metadata,
            provider="importer",
            publish_datetime=publish_datetime or "",
            domain_id=scope["domain_id"],
            subject_id=scope["subject_id"],
            brand_focus_id=scope["brand_focus_id"],
            global_scope=scope["global_scope"],
        )
    return {**source, "source_id": source_id, "evidence_ref": str(evidence_id)}


def test_typed_owned_business_brief_saves_and_reopens_complete_lineage(workspace, monkeypatch):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    actor_ref = media_brief._actor_ref(workspace["actor"])
    calls = []

    def run(request):
        assert type(request) is owned_service.OwnedServiceRequest
        calls.append(request)
        assert request.operation == "business_brief"
        assert request.request_id.startswith("business-brief:")
        assert request.job_id == JOB_ID
        assert request.actor_ref == actor_ref
        assert request.domain_id == "cth"
        assert request.scope == "GLOBAL / ALL"
        assert request.max_output_tokens == 4096
        payload = json.loads(request.user_payload)
        assert payload["material"]["sources"][0] == source
        assert request.input_revision_sha256 == brief._digest(payload["material"])
        assert request.source_evidence_refs == (f"app_evidence_records:{source['evidence_ref']}",)
        schema = json.loads(request.response_schema_json)
        assert schema["properties"]["proposed_actions"]["maxItems"] > 1
        return _owned_result(request, actor=workspace["actor"])

    monkeypatch.setattr(brief.gateway, "run_owned_request", run)
    result = _analyze(workspace, source)

    assert result["state"] == "draft"
    assert result["provider"] == "owned"
    assert result["real_input_bound"] is True
    assert len(result["analysis"]["proposed_actions"]) == 2
    assert all(set(item["pilot"]) == set(brief._PILOT_FIELDS)
               for item in result["analysis"]["proposed_actions"])
    assert len(calls) == 1
    provenance = result["owned_provenance"]
    assert provenance["run_id"] == "fixture-owned-run-0001"
    assert provenance["model_id"] == result["model"] == "fixture-owned-model"
    assert provenance["model_revision"] == "fixture-owned-revision-1"
    assert provenance["recipe"] == "fixture-owned-recipe-1"
    assert (provenance["prompt_tokens"], provenance["completion_tokens"],
            provenance["total_tokens"]) == (100, 500, 600)
    assert provenance["source_evidence_refs"] == [f"app_evidence_records:{source['evidence_ref']}"]
    assert provenance["evaluation_state"] == "NOT_RUN"
    assert provenance["quality_state"] == "NOT_EVALUATED"
    reopened = brief.read_business_brief(
        result["evidence_ref"], job_id=JOB_ID, actor_ref=actor_ref,
        scope=workspace["scope"], actor=workspace["actor"],
    )
    assert reopened["provider"] == "owned"
    assert reopened["analysis"] == result["analysis"]
    assert reopened["owned_provenance"] == provenance


def test_original_document_projects_into_saved_source_brief_job(workspace, monkeypatch):
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation import recorder
    from lumenis.shared.reporting import source_brief_job as jobs
    import subject_registry

    _wire_repositories(workspace, monkeypatch)
    monkeypatch.setattr(jobs, 'get_repository', lambda: workspace['repo'])
    with workspace['repo'].transaction() as con:
        apply_business_schema(con)
    recorder.init_db()
    entry, _ = subject_registry.add_subject({
        'domain_id': 'CTH', 'subject_type': 'company',
        'name_en': 'Synthetic source brief subject', 'name_zh': '隔离测试主体',
    })
    workspace = {**workspace, 'scope': {**workspace['scope'],
                 'subject_id': entry['subject_id'], 'global_scope': False}}
    source, _ = _seed_source(workspace)
    calls = []

    def run(request):
        calls.append(request)
        material = json.loads(request.user_payload)['material']
        projected = material['sources'][0]
        assert projected['source_id'] == source['source_id']
        assert projected['content_evidence_ref'] == 'app_evidence_records:' + source['evidence_ref']
        return _owned_result(request, actor=workspace['actor'])

    monkeypatch.setattr(brief.gateway, 'run_owned_request', run)
    actor_ref = media_brief._actor_ref(workspace['actor'])
    with workspace['repo'].connection(read_only=True, wal=False) as con:
        result = jobs.create_source_brief_job(
            con, product_id='CTH', global_scope=False, entity_label=entry['name_en'],
            subject_id=entry['subject_id'],
            actor_id=actor_ref, image_actor=workspace['actor'], permission_audit_ref='test-source-read',
            trace_id='test-source-brief-typed', job_id='job-source-brief-typed-0001',
            business_question=QUESTION, source_ids=[source['source_id']],
        )
    assert len(calls) == 1
    assert result['business_analysis']['state'] == 'draft'
    assert result['business_analysis']['provider'] == 'owned'
    reopened = jobs.get_source_brief_job(
        result['job_id'], actor_id=actor_ref, expected_scope=result['source_brief']['scope'],
        actor=workspace['actor'],
    )
    assert reopened == result
    assert reopened['artifact_outcome']['state'] == 'persisted_and_reopened_verified'
    assert reopened['business_analysis']['owned_provenance']['run_id'] == 'fixture-owned-run-0001'
    assert reopened['business_analysis']['outcome_state'] == 'NOT_OBSERVED'


def test_actual_unbound_gateway_returns_unavailable_without_derivative(workspace, monkeypatch):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    assert gateway.owned_inference_status("cth")["service_binding"] == "NOT_BOUND"

    result = _analyze(workspace, source)

    assert result["state"] == "unavailable"
    assert result["provider"] == "owned"
    assert result["real_input_bound"] is False
    assert result["provider_status"]["generation_probe_performed"] is False
    assert result["provider_status"]["fallback_allowed"] is False
    _assert_no_business_evidence(workspace)


@pytest.mark.parametrize('mutation', ['question', 'source_text', 'extra_payload', 'system_prompt', 'schema', 'budget'])
def test_source_validator_rejects_model_input_outside_verified_material(workspace, monkeypatch, mutation):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    calls = []

    def unavailable(request):
        calls.append(request)
        return {'ok': False, 'status': 'UNAVAILABLE', 'code': 'OWNED_RUNTIME_NOT_BOUND'}

    monkeypatch.setattr(brief.gateway, 'run_owned_request', unavailable)
    assert _analyze(workspace, source)['state'] == 'unavailable'
    assert len(calls) == 1
    request = calls[0]
    payload = json.loads(request.user_payload)
    if mutation == 'question':
        payload['question'] = 'A different task outside the signed material.'
        forged = replace(request, user_payload=brief._json(payload))
    elif mutation == 'source_text':
        payload['sources'][0]['excerpts'] = ['Undeclared model input.']
        forged = replace(request, user_payload=brief._json(payload))
    elif mutation == 'extra_payload':
        payload['undeclared_material'] = 'Extra source content.'
        forged = replace(request, user_payload=brief._json(payload))
    elif mutation == 'system_prompt':
        forged = replace(request, system_prompt=request.system_prompt + ' Additional instructions.')
    elif mutation == 'schema':
        forged = replace(request, response_schema_json='{}')
    else:
        forged = replace(request, max_output_tokens=request.max_output_tokens + 1)
    with pytest.raises((ValueError, PermissionError), match='BUSINESS_BRIEF_(MODEL_INPUT_BINDING|MATERIAL)_INVALID'):
        brief.validate_business_source_use(forged, actor=workspace['actor'])
    _assert_no_business_evidence(workspace)


@pytest.mark.parametrize(
    "variant_kwargs",
    [
        {"suffix": "-unknown-rights", "rights": "unregistered-rights"},
        {"suffix": "-scope-only", "artifact_ref": "ART-0000000000000000"},
    ],
    ids=["unknown-rights", "scope-only-evidence"],
)
def test_unverified_rights_or_scope_only_evidence_never_reaches_gateway(
    workspace, monkeypatch, variant_kwargs,
):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    variant = _signed_source_variant(workspace, source, **variant_kwargs)
    calls = _forbid_gateway(monkeypatch)

    result = _analyze(workspace, variant)

    assert result["state"] == "unavailable"
    assert result["real_input_bound"] is False
    assert calls == []
    _assert_no_business_evidence(workspace)


def test_mutated_original_artifact_bytes_never_reach_gateway(workspace, monkeypatch):
    _wire_repositories(workspace, monkeypatch)
    source, imported = _seed_source(workspace)
    artifact = workspace["repo"].query_one(
        "SELECT relative_path FROM lumenis_shared_artifacts WHERE artifact_id=?",
        (imported["source_artifact_ref"],),
    )
    assert artifact is not None
    (workspace["root"] / "artifacts" / artifact[0]).write_bytes(b"changed original Artifact bytes")
    calls = _forbid_gateway(monkeypatch)

    result = _analyze(workspace, source)

    assert result["state"] == "unavailable"
    assert result["real_input_bound"] is False
    assert calls == []
    _assert_no_business_evidence(workspace)


def test_denied_ai_call_permission_never_reaches_gateway(workspace, monkeypatch):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    workspace["gate"].revoke_permission(permission.PermissionLevel.ANALYZE)
    calls = _forbid_gateway(monkeypatch)

    result = _analyze(workspace, source)

    assert result["state"] == "unavailable"
    assert result["real_input_bound"] is False
    assert "ANALYSIS_PERMISSION_DENIED" in result["reason"]
    assert calls == []
    _assert_no_business_evidence(workspace)


@pytest.mark.parametrize("revoke_at", ["gateway_callback", "before_evidence"])
def test_permission_revoked_during_execution_or_before_evidence_prevents_save(
    workspace, monkeypatch, revoke_at,
):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    calls = []

    def run(request):
        calls.append(request)
        result = _owned_result(request, actor=workspace["actor"])
        if revoke_at == "gateway_callback":
            workspace["gate"].revoke_permission(permission.PermissionLevel.ANALYZE)
        return result

    monkeypatch.setattr(brief.gateway, "run_owned_request", run)
    before_evidence = None
    if revoke_at == "before_evidence":
        def revoke_before_evidence():
            workspace["gate"].revoke_permission(permission.PermissionLevel.ANALYZE)
        before_evidence = revoke_before_evidence

    if revoke_at == "before_evidence":
        with pytest.raises(PermissionError, match="BUSINESS_BRIEF_ANALYSIS_PERMISSION_DENIED"):
            _analyze(workspace, source, before_evidence=before_evidence)
    else:
        result = _analyze(workspace, source)
        assert result["state"] == "unavailable"
        assert result["real_input_bound"] is False

    assert len(calls) == 1
    _assert_no_business_evidence(workspace)


@pytest.mark.parametrize("mismatch", ["source_binding", "output_budget"])
def test_owned_result_binding_mismatch_or_budget_overrun_is_not_saved(
    workspace, monkeypatch, mismatch,
):
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    calls = []

    def run(request):
        calls.append(request)
        result = _owned_result(request, actor=workspace["actor"])
        if mismatch == "source_binding":
            result["source_binding_sha256"] = _sha("different-source-binding")
        else:
            result["completion_tokens"] = request.max_output_tokens + 1
            result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"]
        return result

    monkeypatch.setattr(brief.gateway, "run_owned_request", run)
    result = _analyze(workspace, source)

    assert result["state"] == "unavailable"
    assert result["real_input_bound"] is False
    assert len(calls) == 1
    _assert_no_business_evidence(workspace)


def test_legacy_signed_version_seven_ollama_record_reopens_without_provider_call(
    workspace, monkeypatch,
):
    _wire_repositories(workspace, monkeypatch)
    actor_ref = media_brief._actor_ref(workspace["actor"])
    source_id = "legacy-signed-source"
    excerpt = "A historical signed source excerpt."
    material = {
        "question": "What does this historical source say?",
        "sources": [{"source_id": source_id, "text": excerpt}],
        "sample": {"test_only": True},
    }
    pilot = {
        "audience": "Invite willing reviewers.",
        "procedure": "Show two wording options.",
        "measure": "Record stated interpretations.",
        "continue_if": "Continue only after clear interpretation.",
        "stop_if": "Revise if reviewers misunderstand.",
    }
    analysis = {
        "source_observations": [{"source_id": source_id, "excerpt": excerpt}],
        "interpretations": [{"text": "The excerpt supports only its own statement.",
                             "source_ids": [source_id]}],
        "proposed_actions": [{"action": "Compare two wording options.",
                              "reason": "Audience response is not established.",
                              "check": "Ask reviewers what each option communicates.",
                              "source_ids": [source_id], "pilot": pilot}],
        "unknowns": ["No audience response is established."],
    }
    with workspace["repo"].transaction() as connection:
        evidence_id = evidence_store.record_evidence(
            connection=connection,
            source="shared_reporting",
            product="CTH",
            feature_id="REPORT_BUSINESS_ANALYSIS",
            test_name=JOB_ID,
            result="PASS",
            status="derived",
            inputs={"job_id": JOB_ID, "actor_ref": actor_ref,
                    "scope": workspace["scope"], "version": "report-business-brief/7",
                    "material": material},
            outputs={"analysis": analysis, "analysis_sha256": brief._digest(analysis),
                     "input_sha256": brief._digest(material), "provider": "ollama",
                     "model": "historical-fixture-model"},
            provider="ollama",
            domain_id="cth",
            global_scope=True,
        )

    reopened = brief.read_business_brief(
        f"app_evidence_records:{evidence_id}", job_id=JOB_ID,
        actor_ref=actor_ref, scope=workspace["scope"], actor=workspace["actor"],
    )

    assert reopened["provider"] == "ollama"
    assert reopened["analysis"] == analysis
    assert reopened["review_status"] == "HUMAN_PENDING"
