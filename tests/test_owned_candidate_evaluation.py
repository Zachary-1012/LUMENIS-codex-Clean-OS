"""Isolated contract tests for report-only owned-candidate held-out evaluation."""
import hashlib
import json
from pathlib import Path

import pytest

from lumenis.system.ai_gateway import owned_evaluation as evaluation
from lumenis.system.ai_gateway import owned_training as training


def _record(case_id: str, prompt: str, *, domain: str = "CTH") -> dict:
    answer = f"Reviewed answer for {case_id}."
    return {
        "case_id": case_id,
        "source_evidence_refs": [f"EVIDENCE-{case_id}"],
        "scope": "GLOBAL / ALL",
        "domain": domain,
        "context": "Approved typed decision task",
        "permission_ref": f"PERMISSION-{case_id}",
        "rights_ref": f"RIGHTS-{case_id}",
        "review_status": "REVIEWER_APPROVED",
        "reviewer_approval_ref": f"REVIEW-{case_id}",
        "reviewer_approved_target": answer,
        "training_eligible": True,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer, "channel": "final"},
        ],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "disposable-never-opened.sqlite3"))
    model = tmp_path / "snapshot"
    model.mkdir()
    entries = {}
    for name in training._MODEL_FILES:
        data = ("pinned-model-file:" + name).encode()
        (model / name).write_bytes(data)
        entries[name] = {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    manifest = tmp_path / "config" / "ai-owned-foundation.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({
        "schema_version": 1, "owner": "SYSTEM AI Gateway", "model_id": training.MODEL_ID,
        "revision": training.MODEL_REVISION, "license": "Apache-2.0",
        "usage_policy_url": f"https://huggingface.co/{training.MODEL_ID}/blob/{training.MODEL_REVISION}/USAGE_POLICY",
        "capability": "text", "format": "transformers_safetensors",
        "status": "APPROVED_FOUNDATION_NOT_TRAINED",
        "source_url": f"https://huggingface.co/{training.MODEL_ID}/tree/{training.MODEL_REVISION}",
        "fine_tune_reference": "https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers",
        "files": entries,
    }), encoding="utf-8")
    monkeypatch.setattr(training, "APPROVED_MANIFEST_PATH", manifest)
    train = _write_jsonl(tmp_path / "train.jsonl", [_record("TRAIN-1", "Question A")])
    heldout = _write_jsonl(tmp_path / "heldout.jsonl", [_record("TEST-1", "Question B")])
    output = tmp_path / "candidate-output"
    output.mkdir()
    adapter = output / "adapter_model.safetensors"
    adapter.write_bytes(b"candidate-adapter-bytes")
    config = output / "adapter_config.json"
    config.write_text(json.dumps({"peft_type": "LORA", "r": 8, "lora_alpha": 16}), encoding="utf-8")
    preflight = training.run_owned_lora_training(
        model, train, heldout, tmp_path / "unused-training-output",
        manifest_path=manifest, execute=False,
    )
    status = {
        **preflight, "execution_state": "TRAINED_NOT_EVALUATED", "candidate_status": "NOT_EVALUATED",
        "cuda_device": "synthetic-test-only", "cuda_memory_bytes": 0,
    }
    (output / "training_status.json").write_text(json.dumps(status), encoding="utf-8")
    return {
        "model": model, "manifest": manifest, "train": train, "heldout": heldout,
        "output": output, "adapter_sha": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        "config_sha": hashlib.sha256(config.read_bytes()).hexdigest(),
    }


def _evaluate(candidate, infer):
    return evaluation.evaluate_owned_candidate(
        candidate["model"], candidate["train"], candidate["heldout"], candidate["output"],
        manifest_path=candidate["manifest"], expected_adapter_sha256=candidate["adapter_sha"],
        expected_adapter_config_sha256=candidate["config_sha"], local_infer=infer,
    )


def test_completed_gpt_oss_final_is_bound_to_heldout_and_stays_human_review_required(candidate):
    seen = []

    def infer(request):
        seen.append(request)
        return {
            "generated_text": "<|start|>assistant<|channel|>analysis<|message|>private reasoning<|end|>"
                              "<|start|>assistant<|channel|>final<|message|>Demand remains UNKNOWN; "
                              "source [[EVIDENCE-TEST-1]].<|return|>",
            "finish_reason": "return",
            "termination_token": "<|return|>",
        }

    result = _evaluate(candidate, infer)
    item = result["cases"][0]
    assert result["evaluation_status"] == "STRUCTURAL_OUTPUTS_CAPTURED"
    assert result["candidate_status"] == "NOT_ACCEPTED"
    assert result["business_acceptance"] == "HUMAN_REVIEW_REQUIRED"
    assert result["promotion_status"] == "NOT_PROMOTED"
    assert result["runtime_verification"] == "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"
    assert item["completion_state"] == "COMPLETED_FINAL"
    assert item["final_text"] == "Demand remains UNKNOWN; source [[EVIDENCE-TEST-1]]."
    assert "private reasoning" not in item["final_text"]
    assert item["citation_state"] == "PRESENT"
    assert item["source_evidence_refs"] == ["EVIDENCE-TEST-1"]
    assert item["heldout_origin"]["dataset_role"] == "heldout"
    assert item["heldout_origin"]["dataset_sha256"] == hashlib.sha256(candidate["heldout"].read_bytes()).hexdigest()
    assert seen[0].candidate_identity_sha256 == result["candidate_identity_sha256"]
    assert seen[0].local_only and not seen[0].network_access and not seen[0].fallback_allowed
    assert seen[0].user_messages == ("Question B",)
    assert all(state == "PENDING" for state in item["business_review"]["criteria"].values())


@pytest.mark.parametrize(("response", "completion", "citation"), [
    ({"generated_text": "<|channel|>final<|message|>Answer cut off", "finish_reason": "length",
      "termination_token": "<|return|>"},
     "GENERATION_NOT_COMPLETE", "MISSING_OR_UNRESOLVED"),
    ({"generated_text": "<|channel|>final<|message|>A complete-looking reply.<|return|>", "finish_reason": "stop",
      "termination_token": "<|return|>"},
     "COMPLETED_FINAL", "MISSING_OR_UNRESOLVED"),
    (RuntimeError("runtime unavailable"), "INFERENCE_ERROR:RuntimeError", "MISSING_OR_UNRESOLVED"),
])
def test_truncated_error_and_missing_citation_never_become_acceptance(candidate, response, completion, citation):
    def infer(_request):
        if isinstance(response, Exception):
            raise response
        return response

    result = _evaluate(candidate, infer)
    assert result["candidate_status"] == "NOT_ACCEPTED"
    assert result["business_acceptance"] == "HUMAN_REVIEW_REQUIRED"
    assert result["cases"][0]["completion_state"] == completion
    assert result["cases"][0]["citation_state"] == ("MISSING" if citation == "MISSING_OR_UNRESOLVED" else citation)


def test_unknown_and_zero_are_preserved_as_distinct_unreviewed_outputs(candidate):
    unknown = _evaluate(candidate, lambda _request: {
        "generated_text": "Sales are UNKNOWN; [[EVIDENCE-TEST-1]].<|return|>",
        "termination_token": "<|return|>", "final_channel_prefill": True,
    })
    zero = _evaluate(candidate, lambda _request: {
        "generated_text": "Sales are 0; [[EVIDENCE-TEST-1]].<|return|>",
        "termination_token": "<|return|>", "final_channel_prefill": True,
    })
    assert "UNKNOWN" in unknown["cases"][0]["final_text"]
    assert "Sales are 0" in zero["cases"][0]["final_text"]
    assert unknown["candidate_status"] == zero["candidate_status"] == "NOT_ACCEPTED"
    assert unknown["cases"][0]["business_review"]["criteria"]["UNKNOWN_VS_ZERO"] == "PENDING"
    assert zero["cases"][0]["business_review"]["criteria"]["UNKNOWN_VS_ZERO"] == "PENDING"


@pytest.mark.parametrize(("text", "terminator"), [
    ("<|im_start|>assistant<|channel|>final<|message|>Answer [[EVIDENCE-TEST-1]].<|fim_suffix|>", "<|fim_suffix|>"),
    ("<|channel|>final<|message|>Answer [[EVIDENCE-TEST-1]].<|return|>", "<|return|>"),
])
def test_harmony_headers_and_configured_termination_are_parsed(candidate, text, terminator):
    result = _evaluate(candidate, lambda _request: {"generated_text": text, "termination_token": terminator})
    assert result["cases"][0]["completion_state"] == "COMPLETED_FINAL"
    assert result["cases"][0]["termination_token"] == terminator


def test_plain_completion_requires_explicit_final_channel_prefill(candidate):
    result = _evaluate(candidate, lambda _request: {
        "generated_text": "Answer [[EVIDENCE-TEST-1]].<|return|>", "termination_token": "<|return|>"
    })
    assert result["cases"][0]["completion_state"] == "FINAL_CHANNEL_OR_PREFILL_MISSING"
    assert result["candidate_status"] == "NOT_ACCEPTED"


def test_tool_call_and_message_end_are_not_completion(candidate):
    result = _evaluate(candidate, lambda _request: {
        "generated_text": "<|start|>assistant to=functions.lookup<|channel|>commentary<|message|>{}<|call|>",
        "termination_token": "<|end|>",
    })
    assert result["cases"][0]["completion_state"] == "TERMINATION_TOKEN_UNSPECIFIED_OR_UNSUPPORTED"


def test_final_followed_by_analysis_channel_is_rejected(candidate):
    result = _evaluate(candidate, lambda _request: {
        "generated_text": "<|start|>assistant<|channel|>final<|message|>Answer [[EVIDENCE-TEST-1]]."
                          "<|channel|>analysis<|message|>leaked continuation<|return|>",
        "termination_token": "<|return|>",
    })
    assert result["cases"][0]["completion_state"] == "FINAL_CHANNEL_EMPTY_OR_INVALID"
    assert result["cases"][0]["final_text"] == ""


def test_exact_model_identity_mismatch_blocks_before_inference(candidate):
    status_path = candidate["output"] / "training_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["model_revision"] = "another-revision"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    called = []
    with pytest.raises(evaluation.CandidateEvaluationBlocked, match="TRAINING_STATUS_IDENTITY_MISMATCH"):
        _evaluate(candidate, lambda request: called.append(request))
    assert called == []


@pytest.mark.parametrize("artifact", ["adapter_model.safetensors", "adapter_config.json"])
def test_exact_adapter_digest_mismatch_blocks_before_inference(candidate, artifact):
    (candidate["output"] / artifact).write_bytes(b"changed-after-training")
    called = []
    with pytest.raises(evaluation.CandidateEvaluationBlocked, match="ADAPTER_HASH_MISMATCH"):
        _evaluate(candidate, lambda request: called.append(request))
    assert called == []


def test_dataset_identity_change_is_rejected(candidate):
    _write_jsonl(candidate["heldout"], [_record("TEST-1", "Changed question")])
    with pytest.raises(evaluation.CandidateEvaluationBlocked, match="TRAINING_STATUS_IDENTITY_MISMATCH"):
        _evaluate(candidate, lambda _request: "unused")


@pytest.mark.parametrize("duplicate", ["case_id", "prompt"])
def test_heldout_train_overlap_is_rejected(candidate, duplicate):
    row = _record("TRAIN-1" if duplicate == "case_id" else "TEST-1",
                  "Question A" if duplicate == "prompt" else "Question B")
    _write_jsonl(candidate["heldout"], [row])
    with pytest.raises(ValueError, match="overlap"):
        _evaluate(candidate, lambda _request: "unused")


def test_output_must_match_trained_status_before_any_inference(candidate):
    status_path = candidate["output"] / "training_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["execution_state"] = "TRAINING_FAILED"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    with pytest.raises(evaluation.CandidateEvaluationBlocked, match="TRAINING_STATUS_IDENTITY_MISMATCH"):
        _evaluate(candidate, lambda _request: "unused")
