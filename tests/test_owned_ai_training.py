"""Safety-gate tests for the local-only owned-model training helper."""
import builtins
import hashlib
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from lumenis.system.ai_gateway import owned_training as training


@pytest.fixture(autouse=True)
def _phase_fixture_monkeypatch(monkeypatch):
    from tests.test_owned_training_callback_v3 import _unit_signer
    _unit_signer(monkeypatch)


def _record(case_id: str, prompt: str) -> dict:
    answer = f"Reviewed answer for {case_id}."
    return {
        "case_id": case_id,
        "source_evidence_refs": [f"EVIDENCE-{case_id}"],
        "scope": "GLOBAL / ALL",
        "domain": "CTH",
        "context": "Approved typed decision task",
        "permission_ref": f"PERMISSION-{case_id}",
        "rights_ref": f"RIGHTS-{case_id}",
        "review_status": "REVIEWER_APPROVED",
        "reviewer_approval_ref": f"REVIEW-{case_id}",
        "reviewer_approved_target": answer,
        "training_eligible": True,
        "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": answer, "channel": "final"}],
    }


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    return path


def _inputs(tmp_path: Path, monkeypatch):
    model = tmp_path / "snapshot"
    model.mkdir()
    entries = {}
    for name in training._MODEL_FILES:
        content = ("pinned-model-file:" + name).encode()
        (model / name).write_bytes(content)
        entries[name] = {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    manifest = tmp_path / "config" / "ai-owned-foundation.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "owner": "SYSTEM AI Gateway",
        "model_id": training.MODEL_ID,
        "revision": training.MODEL_REVISION,
        "license": "Apache-2.0",
        "usage_policy_url": f"https://huggingface.co/{training.MODEL_ID}/blob/{training.MODEL_REVISION}/USAGE_POLICY",
        "capability": "text",
        "format": "transformers_safetensors",
        "status": "APPROVED_FOUNDATION_NOT_TRAINED",
        "source_url": f"https://huggingface.co/{training.MODEL_ID}/tree/{training.MODEL_REVISION}",
        "fine_tune_reference": "https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers",
        "files": entries,
    }), encoding="utf-8")
    monkeypatch.setattr(training, "APPROVED_MANIFEST_PATH", manifest)
    train = _write_jsonl(tmp_path / "train.jsonl", [_record("TRAIN-1", "Question A")])
    heldout = _write_jsonl(tmp_path / "heldout.jsonl", [_record("TEST-1", "Question B")])
    return model, manifest, train, heldout, tmp_path / "candidate-output"


def _run(paths, *, execute=False, approval_verifier=None, manifest=None, recipe=training.H100_RECIPE):
    model, canonical_manifest, train, heldout, output = paths
    phase_client = None
    return training.run_owned_lora_training(
        model, train, heldout, output, manifest_path=manifest or canonical_manifest,
        execute=execute, approval_verifier=approval_verifier, recipe=recipe, phase_client=phase_client,
    )


def test_preflight_validates_pinned_local_inputs_without_optional_imports_or_writes(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    original_import = builtins.__import__

    def reject_training_import(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "transformers", "peft", "trl", "datasets"}:
            raise AssertionError("preflight imported a training dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_training_import)
    result = _run(paths)
    assert result["status"] == "VALIDATED_LOCAL_INPUTS_NOT_PRODUCTION_ACCEPTANCE"
    assert result["execution_state"] == "PREFLIGHT_ONLY"
    assert result["candidate_status"] == "NOT_EVALUATED"
    assert result["permission_evidence_state"] == "LOCAL_ATTESTATIONS_ONLY_NOT_VERIFIED"
    assert result["train_case_count"] == result["heldout_case_count"] == 1
    assert not paths[-1].exists()


@pytest.mark.parametrize(("field", "value"), [
    ("rights_ref", "UNKNOWN"),
    ("training_eligible", False),
    ("review_status", "HUMAN_PENDING"),
    ("review_status", "REJECTED_FEEDBACK"),
    ("reviewer_approved_target", "different from assistant message"),
])
def test_preflight_rejects_unapproved_or_unknown_records(tmp_path, monkeypatch, field, value):
    paths = _inputs(tmp_path, monkeypatch)
    paths[2].write_text(json.dumps({**_record("TRAIN-1", "Question A"), field: value}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid approved dataset record"):
        _run(paths)
    assert not paths[-1].exists()


def test_preflight_rejects_secret_values_and_ineligible_raw_feedback(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    record = _record("TRAIN-1", "Question A")
    record["messages"][0]["content"] = "Use this sk-proj-abcdefghijklmnopqrstuvwxyz123456 secret"
    paths[2].write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid approved dataset record"):
        _run(paths)
    record = _record("TRAIN-1", "Question A")
    record["review_status"] = "RAW"
    paths[2].write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid approved dataset record"):
        _run(paths)


@pytest.mark.parametrize("kind", ["PRIVATE", "RSA PRIVATE", "EC PRIVATE", "OPENSSH PRIVATE", "ENCRYPTED PRIVATE"])
def test_preflight_rejects_private_key_headers(tmp_path, monkeypatch, kind):
    paths = _inputs(tmp_path, monkeypatch)
    record = _record("TRAIN-1", "Question A")
    record["messages"][0]["content"] = "-" * 5 + "BEGIN " + kind + " KEY" + "-" * 5
    _write_jsonl(paths[2], [record])
    with pytest.raises(ValueError, match="Invalid approved dataset record"):
        _run(paths)
    assert not paths[-1].exists()


@pytest.mark.parametrize("duplicate", ["case_id", "prompt"])
def test_preflight_rejects_train_heldout_overlap(tmp_path, monkeypatch, duplicate):
    paths = _inputs(tmp_path, monkeypatch)
    heldout = _record("TRAIN-1" if duplicate == "case_id" else "TEST-1", "Question A" if duplicate == "prompt" else "Question B")
    _write_jsonl(paths[3], [heldout])
    with pytest.raises(ValueError, match="overlap"):
        _run(paths)
    assert not paths[-1].exists()


def test_preflight_rejects_pinned_snapshot_hash_mismatch(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    (paths[0] / "config.json").write_text("changed", encoding="utf-8")
    with pytest.raises(training.TrainingBlocked, match="LOCAL_MODEL_FILE_HASH_MISMATCH"):
        _run(paths)


def test_preflight_rejects_empty_split_and_output_inside_model_snapshot(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    paths[3].write_bytes(b"")
    with pytest.raises(ValueError, match="non-empty"):
        _run(paths)
    _write_jsonl(paths[3], [_record("TEST-1", "Question B")])
    unsafe_paths = (*paths[:4], paths[0] / "candidate-output")
    with pytest.raises(ValueError, match="overlaps protected"):
        _run(unsafe_paths)


def test_withdrawn_gpu_training_rejects_before_model_imports_or_output(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    original_import = builtins.__import__

    def reject_training_import(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "transformers", "peft", "trl", "datasets"}:
            raise AssertionError("execution imported before canonical Learning approval")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_training_import)
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, execute=True)
    assert not paths[-1].exists()


def test_withdrawn_gpu_training_does_not_consume_or_check_approval(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    seen = []

    def reject_approval(request):
        seen.append(request)
        return False

    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, execute=True, approval_verifier=reject_approval)
    assert seen == []
    assert not paths[-1].exists()


def test_same_global_label_does_not_merge_cth_and_bmp_training_scopes(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    heldout = _record("BMP-HELDOUT", "Different brand question")
    heldout["domain"] = "BMP"
    _write_jsonl(paths[3], [heldout])
    with pytest.raises(training.TrainingBlocked, match="MIXED_DOMAIN_TRAINING"):
        _run(paths)
    assert not paths[-1].exists()


def test_withdrawn_gpu_training_does_not_load_cuda_or_call_approval(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(training, "_require_cuda", lambda *_args, **_kwargs: pytest.fail("CUDA path reached"))
    monkeypatch.setattr(training, "_verify_training_boundary", lambda *_args, **_kwargs: called.append("permission"))
    paths = _inputs(tmp_path, monkeypatch)
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, execute=True, approval_verifier=lambda _request: called.append("approval"))
    assert called == []
    assert not paths[-1].exists()


def _t4_inputs(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    model, manifest, *_ = paths
    # Disposable synthetic snapshot; never a training or hardware acceptance claim.
    for item in model.iterdir():
        item.unlink()
    names = {"chat_template.json", "config.json", "generation_config.json", "model.safetensors.index.json",
             "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
             *(f"model-{i:05d}-of-00004.safetensors" for i in range(1, 5))}
    entries = {}
    for name in names:
        content = ("disposable-nf4-test:" + name).encode()
        (model / name).write_bytes(content)
        entries[name] = {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    data = json.loads(manifest.read_text())
    data["training_variants"] = {training.T4_RECIPE: {
        "model_id": training.T4_MODEL_ID, "revision": training.T4_MODEL_REVISION,
        "license": "Apache-2.0", "base_model": training.MODEL_ID,
        "base_revision_state": "UPSTREAM_UNSPECIFIED", "format": "bitsandbytes_nf4",
        "source_url": f"https://huggingface.co/{training.T4_MODEL_ID}/tree/{training.T4_MODEL_REVISION}",
        "files": entries,
    }}
    manifest.write_text(json.dumps(data))
    return paths


def test_t4_preflight_keeps_derivative_identity_and_requires_exact_approval(tmp_path, monkeypatch):
    paths = _t4_inputs(tmp_path, monkeypatch)
    result = _run(paths, recipe=training.T4_RECIPE)
    assert result["model_id"] == training.T4_MODEL_ID
    assert result["model_revision"] == training.T4_MODEL_REVISION
    assert result["base_revision_state"] == "UPSTREAM_UNSPECIFIED"
    assert result["execution_state"] == "PREFLIGHT_ONLY"
    seen = []
    def deny(request):
        seen.append(request)
        return False
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, recipe=training.T4_RECIPE, execute=True, approval_verifier=deny)
    assert seen == []
    assert not paths[-1].exists()


def test_t4_does_not_accept_raw_mxfp4_or_unpinned_derivative(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    with pytest.raises(training.TrainingBlocked, match="T4_DERIVATIVE_MANIFEST_INVALID"):
        _run(paths, recipe=training.T4_RECIPE)
    with pytest.raises(training.TrainingBlocked, match="NO_AUTOMATIC_FALLBACK"):
        _run(paths, recipe="auto")
    (tmp_path / "variant").mkdir()
    paths = _t4_inputs(tmp_path / "variant", monkeypatch)
    data = json.loads(paths[1].read_text())
    data["training_variants"][training.T4_RECIPE]["revision"] = "main"
    paths[1].write_text(json.dumps(data))
    with pytest.raises(training.TrainingBlocked, match="T4_DERIVATIVE_MANIFEST_INVALID"):
        _run(paths, recipe=training.T4_RECIPE)


def test_t4_snapshot_hash_mismatch_remains_blocking(tmp_path, monkeypatch):
    paths = _t4_inputs(tmp_path, monkeypatch)
    (paths[0] / "config.json").write_text("tampered")
    with pytest.raises(training.TrainingBlocked, match="LOCAL_MODEL_FILE_HASH_MISMATCH"):
        _run(paths, recipe=training.T4_RECIPE)


@pytest.mark.parametrize("major,minor,memory,recipe,allowed", [
    (7, 5, 15637086208, training.T4_RECIPE, True),
    (7, 5, 8 * 1024**3, training.T4_RECIPE, False),
    (8, 0, 80 * 1024**3, training.T4_RECIPE, False),
    (7, 5, 15637086208, training.H100_RECIPE, False),
])
def test_recipe_specific_cuda_gate_preserves_h100_boundary(monkeypatch, major, minor, memory, recipe, allowed):
    device = SimpleNamespace(name="synthetic-cuda", major=major, minor=minor, total_memory=memory)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
        is_available=lambda: True, device_count=lambda: 1,
        get_device_properties=lambda _: device, is_bf16_supported=lambda: False)))
    if allowed:
        assert training._require_cuda(recipe)[2] == memory
    else:
        with pytest.raises(training.TrainingBlocked):
            training._require_cuda(recipe)


def test_t4_precision_and_offline_environment_are_scoped_and_restored(monkeypatch):
    monkeypatch.setenv("UNSLOTH_FORCE_FLOAT32", "before")
    monkeypatch.delenv("UNSLOTH_DISABLE_STATISTICS", raising=False)
    with training._offline_hf(training.T4_RECIPE):
        assert training.os.environ["UNSLOTH_FORCE_FLOAT32"] == "1"
        assert training.os.environ["UNSLOTH_DISABLE_STATISTICS"] == "1"
        assert training.os.environ["HF_HUB_OFFLINE"] == "1"
    assert training.os.environ["UNSLOTH_FORCE_FLOAT32"] == "before"
    assert "UNSLOTH_DISABLE_STATISTICS" not in training.os.environ


def test_t4_training_preflight_is_read_only_and_execution_is_withdrawn(tmp_path, monkeypatch):
    paths = _t4_inputs(tmp_path, monkeypatch)
    preflight = _run(paths, recipe=training.T4_RECIPE)
    assert preflight["execution_state"] == "PREFLIGHT_ONLY"
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, execute=True, approval_verifier=lambda _request: pytest.fail("approval called"),
            recipe=training.T4_RECIPE)
    assert not paths[-1].exists()
