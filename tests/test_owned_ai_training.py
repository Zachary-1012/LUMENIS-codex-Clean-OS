"""Safety-gate tests for the local-only owned-model training helper."""
import builtins
import hashlib
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from lumenis.system.ai_gateway import owned_training as training


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
    return training.run_owned_lora_training(
        model, train, heldout, output, manifest_path=manifest or canonical_manifest,
        execute=execute, approval_verifier=approval_verifier, recipe=recipe,
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


def test_execute_without_learning_approval_fails_before_imports_or_output(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    original_import = builtins.__import__

    def reject_training_import(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "transformers", "peft", "trl", "datasets"}:
            raise AssertionError("execution imported before canonical Learning approval")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_training_import)
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        _run(paths, execute=True)
    assert not paths[-1].exists()


def test_execute_approval_is_bound_to_exact_dataset_hashes_and_scope(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    seen = []

    def reject_approval(request):
        seen.append(request)
        return False

    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        _run(paths, execute=True, approval_verifier=reject_approval)
    request = seen[0]
    assert request.train_sha256 == hashlib.sha256(paths[2].read_bytes()).hexdigest()
    assert request.heldout_sha256 == hashlib.sha256(paths[3].read_bytes()).hexdigest()
    assert request.scopes == ("GLOBAL / ALL",)
    assert request.domain_id == "cth"
    assert not paths[-1].exists()


def test_same_global_label_does_not_merge_cth_and_bmp_training_scopes(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    heldout = _record("BMP-HELDOUT", "Different brand question")
    heldout["domain"] = "BMP"
    _write_jsonl(paths[3], [heldout])
    with pytest.raises(training.TrainingBlocked, match="MIXED_DOMAIN_TRAINING"):
        _run(paths, execute=True)
    assert not paths[-1].exists()


def _mock_training_stack(monkeypatch, *, steps=1, save_adapter=True, boundary=None):
    """Observe execution fences without optional packages, a GPU or model calls."""
    observed = {"train_calls": 0, "optimizer_steps": 0, "save_calls": 0, "boundaries": []}

    def reach(name):
        observed["boundaries"].append(name)
        if boundary is not None:
            boundary(name)

    class Tokenizer:
        def apply_chat_template(self, messages, **kwargs):
            return json.dumps(messages)

        def __call__(self, text, **kwargs):
            return {"input_ids": [1, 2]}

        def save_pretrained(self, path):
            (Path(path) / "tokenizer_config.json").write_text("{}")
            reach("tokenizer_saved")

    def load_tokenizer(path, **kwargs):
        assert kwargs["local_files_only"] is True
        assert kwargs["trust_remote_code"] is False
        assert training.os.environ["HF_HUB_OFFLINE"] == "1"
        return Tokenizer()

    def load_model(path, **kwargs):
        assert kwargs["local_files_only"] is True
        assert kwargs["trust_remote_code"] is False
        assert kwargs["use_safetensors"] is True
        return object()

    class Trainer:
        def __init__(self, **kwargs):
            observed["dataset"] = kwargs["train_dataset"]
            observed["args"] = kwargs["args"]
            self.callbacks = kwargs["callbacks"]

        def train(self):
            observed["train_calls"] += 1
            for index in range(steps):
                state = SimpleNamespace(global_step=index)
                for event in ("on_step_begin", "on_substep_end", "on_pre_optimizer_step"):
                    reach(f"{index}:{event}")
                    for callback in self.callbacks:
                        getattr(callback, event)(observed["args"], state, None)
                observed["optimizer_steps"] += 1
            reach("training_returned")
            return SimpleNamespace(global_step=steps)

        def save_model(self, path):
            observed["save_calls"] += 1
            if save_adapter:
                (Path(path) / "adapter_config.json").write_text("{}")
                (Path(path) / "adapter_model.safetensors").write_bytes(b"synthetic-unit-artifact")
            reach("adapter_saved")

    monkeypatch.setattr(training, "_require_cuda", lambda: (
        SimpleNamespace(bfloat16="synthetic-bfloat16"), "synthetic-test-device", 80 * 1024**3,
    ))
    monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(
        Dataset=SimpleNamespace(from_list=lambda rows: rows),
    ))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=load_tokenizer),
        AutoModelForCausalLM=SimpleNamespace(from_pretrained=load_model),
        Mxfp4Config=lambda **kwargs: kwargs,
        TrainerCallback=object,
    ))
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(
        LoraConfig=lambda **kwargs: kwargs, get_peft_model=lambda model, config: model,
    ))
    monkeypatch.setitem(sys.modules, "trl", SimpleNamespace(
        SFTConfig=lambda **kwargs: SimpleNamespace(**kwargs), SFTTrainer=Trainer,
    ))
    return observed


@pytest.mark.parametrize("revoke_at,completed_steps,saved", [
    ("1:on_step_begin", 1, False),
    ("0:on_substep_end", 0, False),
    ("0:on_pre_optimizer_step", 0, False),
    ("training_returned", 2, False),
    ("adapter_saved", 2, True),
    ("tokenizer_saved", 2, True),
])
def test_revocation_at_training_or_save_boundary_never_issues_usable_candidate(
        tmp_path, monkeypatch, revoke_at, completed_steps, saved):
    """Simulated compute only: drive the real caller's registered callback and save fences."""
    paths = _inputs(tmp_path, monkeypatch)
    approved = True

    def boundary(name):
        nonlocal approved
        if name == revoke_at:
            approved = False

    observed = _mock_training_stack(monkeypatch, steps=2, boundary=boundary)
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        _run(paths, execute=True, approval_verifier=lambda request: approved)
    status = json.loads((paths[-1] / "training_status.json").read_text())
    assert status["execution_state"] == "TRAINING_APPROVAL_REQUIRED"
    assert status["candidate_status"] == "NOT_EVALUATED"
    assert observed["optimizer_steps"] == completed_steps
    assert observed["save_calls"] == int(saved)
    # Already-written weights remain diagnostic artifacts; their denied status
    # prevents the existing evaluation/loader from accepting them as trained.
    assert (paths[-1] / "adapter_model.safetensors").exists() is saved


def test_approval_transport_failure_during_training_is_recorded_without_save(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    transport_available = True

    def boundary(name):
        nonlocal transport_available
        if name == "0:on_substep_end":
            transport_available = False

    def verify(request):
        if not transport_available:
            raise ConnectionError("isolated approval transport unavailable")
        return True

    observed = _mock_training_stack(monkeypatch, boundary=boundary)
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_VERIFIER_FAILED"):
        _run(paths, execute=True, approval_verifier=verify)
    assert observed["optimizer_steps"] == observed["save_calls"] == 0
    assert json.loads((paths[-1] / "training_status.json").read_text())["execution_state"] == "TRAINING_APPROVAL_VERIFIER_FAILED"


def test_execution_rechecks_revocation_before_first_write(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    observed = _mock_training_stack(monkeypatch)
    decisions = iter([True, False])
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        _run(paths, execute=True, approval_verifier=lambda request: next(decisions))
    assert not paths[-1].exists()
    assert observed["train_calls"] == 0


@pytest.mark.parametrize("steps,save_adapter,reason", [
    (0, True, "WITHOUT_OPTIMIZER_STEPS"),
    (1, False, "ARTIFACT_MISSING_OR_EMPTY"),
])
def test_failed_training_never_claims_trained(tmp_path, monkeypatch, steps, save_adapter, reason):
    paths = _inputs(tmp_path, monkeypatch)
    observed = _mock_training_stack(monkeypatch, steps=steps, save_adapter=save_adapter)
    with pytest.raises(training.TrainingBlocked, match=reason):
        _run(paths, execute=True, approval_verifier=lambda request: True)
    status = json.loads((paths[-1] / "training_status.json").read_text())
    assert status["execution_state"] != "TRAINED_NOT_EVALUATED"
    assert status["candidate_status"] == "NOT_EVALUATED"
    assert len(observed["dataset"]) == 1
    assert "Question A" in observed["dataset"][0]["text"]
    assert "Question B" not in observed["dataset"][0]["text"]
    assert observed["args"].push_to_hub is False
    assert observed["args"].report_to == "none"


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
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        _run(paths, recipe=training.T4_RECIPE, execute=True, approval_verifier=deny)
    assert seen[0].recipe == training.T4_RECIPE
    assert seen[0].model_id == training.T4_MODEL_ID
    assert seen[0].manifest_sha256 == hashlib.sha256(paths[1].read_bytes()).hexdigest()
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


@pytest.mark.parametrize("loss,accepted", [(1.0, True), (float("nan"), False), (float("inf"), False)])
def test_t4_execution_checks_loss_and_preserves_dataset_and_output_fences(tmp_path, monkeypatch, loss, accepted):
    from importlib import metadata
    paths = _t4_inputs(tmp_path, monkeypatch)
    observed = _mock_training_stack(monkeypatch)
    monkeypatch.setattr(training, "_require_cuda", lambda recipe: (object(), "synthetic-t4", 15637086208))
    versions = {"unsloth": "2026.9.12", "unsloth_zoo": "2026.9.8", "transformers": "4.56.2", "trl": "0.22.2",
                "torch": "2.11.0+cu128", "bitsandbytes": "0.50.2", "tokenizers": "0.22.2", "triton": "3.6.0"}
    monkeypatch.setattr(metadata, "version", versions.__getitem__)
    def load(**kwargs):
        assert kwargs["local_files_only"] is True and kwargs["trust_remote_code"] is False
        assert kwargs["token"] is False
        assert training.os.environ["UNSLOTH_FORCE_FLOAT32"] == "1"
        model = SimpleNamespace(config=SimpleNamespace(_name_or_path=str(paths[0]), quantization_config={"bnb_4bit_quant_type": "nf4"}))
        tokenizer = sys.modules["transformers"].AutoTokenizer.from_pretrained(str(paths[0]), local_files_only=True, trust_remote_code=False)
        return model, tokenizer
    monkeypatch.setitem(sys.modules, "unsloth", SimpleNamespace(FastLanguageModel=SimpleNamespace(
        from_pretrained=load, get_peft_model=lambda model, **kwargs: model)))
    trainer_class = sys.modules["trl"].SFTTrainer
    def train(self):
        observed["train_calls"] += 1
        return SimpleNamespace(global_step=1, metrics={"train_loss": loss})
    monkeypatch.setattr(trainer_class, "train", train)
    if accepted:
        result = _run(paths, execute=True, approval_verifier=lambda _: True, recipe=training.T4_RECIPE)
        assert result["execution_state"] == "TRAINED_NOT_EVALUATED"
        assert result["candidate_status"] == "NOT_EVALUATED"
        assert result["training_packages"] == versions
    else:
        with pytest.raises(training.TrainingBlocked, match="LOSS_UNAVAILABLE_OR_NONFINITE"):
            _run(paths, execute=True, approval_verifier=lambda _: True, recipe=training.T4_RECIPE)
        assert not (paths[-1] / "adapter_model.safetensors").exists()
    assert observed["args"].bf16 is False and observed["args"].fp16 is False
    assert observed["args"].max_length == 1024
    assert observed["args"].per_device_train_batch_size == 1
    assert "Question B" not in observed["dataset"][0]["text"]
