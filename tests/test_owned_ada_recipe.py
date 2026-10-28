"""Hermetic Ada compatibility contracts; no real GPU or training acceptance."""
import contextlib
import importlib.metadata
import json
import os
import sys
from types import SimpleNamespace

import pytest

from lumenis.system.ai_gateway import owned_training as training
from lumenis.system.ai_gateway import owned_inference as inference
from tests.test_owned_ai_training import _t4_inputs, _run
from tests.test_owned_inference import candidate, _Tokenizer, _Tensor, _request
from tests.test_owned_training_checkpoint_recovery import policy_material


@pytest.fixture(autouse=True)
def unit_receipt_signer(monkeypatch):
    from tests.test_owned_training_callback_v3 import _unit_signer
    _unit_signer(monkeypatch)


def _ada_inputs(tmp_path, monkeypatch):
    paths = _t4_inputs(tmp_path, monkeypatch)
    data = json.loads(paths[1].read_text())
    data["training_recipes"] = {training.ADA_RECIPE: training.ADA_RECIPE_POLICY}
    paths[1].write_text(json.dumps(data))
    return paths


def test_ada_reuses_exact_nf4_snapshot_and_requires_its_own_approval(tmp_path, monkeypatch):
    paths = _ada_inputs(tmp_path, monkeypatch)
    result = _run(paths, recipe=training.ADA_RECIPE)
    assert result["model_id"] == "unsloth/gpt-oss-20b-unsloth-bnb-4bit"
    assert result["model_revision"] == "093fba6992ef5a7152481afec0bdfca1ac486998"
    assert result["base_revision_state"] == "UPSTREAM_UNSPECIFIED"
    assert result["execution_state"] == "PREFLIGHT_ONLY"
    requests = []
    def deny(request):
        requests.append(request)
        return False
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, recipe=training.ADA_RECIPE, execute=True, approval_verifier=deny)
    assert requests == []
    assert not paths[-1].exists()


@pytest.mark.parametrize("policies", [None, [], "Ada", {}, {"unsloth-rtx4090-nf4": {"max_sequence_length": 8192}}])
def test_ada_requires_exact_manifest_policy(tmp_path, monkeypatch, policies):
    paths = _ada_inputs(tmp_path, monkeypatch)
    data = json.loads(paths[1].read_text())
    data["training_recipes"] = policies
    paths[1].write_text(json.dumps(data))
    with pytest.raises(training.TrainingBlocked, match="APPROVED_ADA_RECIPE_POLICY_REQUIRED"):
        _run(paths, recipe=training.ADA_RECIPE)
    assert not paths[-1].exists()


def test_ada_does_not_accept_unpinned_snapshot(tmp_path, monkeypatch):
    paths = _ada_inputs(tmp_path, monkeypatch)
    (paths[0] / "config.json").write_text("tampered")
    with pytest.raises(training.TrainingBlocked, match="LOCAL_MODEL_FILE_HASH_MISMATCH"):
        _run(paths, recipe=training.ADA_RECIPE)


@pytest.mark.parametrize("major,minor,name,memory,count,bf16,allowed", [
    (8, 9, "NVIDIA GeForce RTX 4090", 24 * 1024**3, 1, True, True),
    (8, 9, "NVIDIA GeForce RTX 4090", 22 * 1024**3, 1, True, True),
    (7, 5, "Tesla T4", 24 * 1024**3, 1, True, False),
    (9, 0, "NVIDIA H100", 80 * 1024**3, 1, True, False),
    (8, 9, "NVIDIA RTX 4000 Ada", 24 * 1024**3, 1, True, False),
    (8, 9, "NVIDIA GeForce RTX 4090 D", 24 * 1024**3, 1, True, False),
    (8, 9, "NVIDIA GeForce RTX 4090", 22 * 1024**3 - 1, 1, True, False),
    (8, 9, "NVIDIA GeForce RTX 4090", 24 * 1024**3, 2, True, False),
    (8, 9, "NVIDIA GeForce RTX 4090", 24 * 1024**3, 1, False, False),
])
def test_ada_hardware_gate_is_explicit(monkeypatch, major, minor, name, memory, count, bf16, allowed):
    device = SimpleNamespace(name=name, major=major, minor=minor, total_memory=memory)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
        is_available=lambda: True, device_count=lambda: count,
        get_device_properties=lambda _: device, is_bf16_supported=lambda: bf16)))
    if allowed:
        assert training._require_cuda(training.ADA_RECIPE)[1:] == (name, memory)
        for other_recipe in (training.T4_RECIPE, training.H100_RECIPE):
            with pytest.raises(training.TrainingBlocked):
                training._require_cuda(other_recipe)
    else:
        with pytest.raises(training.TrainingBlocked, match="ADA_NF4_RECIPE_REQUIRES_VERIFIED"):
            training._require_cuda(training.ADA_RECIPE)


def test_ada_precision_scope_restores_existing_environment(monkeypatch):
    monkeypatch.setenv("UNSLOTH_FORCE_FLOAT32", "previous")
    with training._offline_hf(training.ADA_RECIPE):
        assert os.environ["UNSLOTH_FORCE_FLOAT32"] == "0"
        assert os.environ["HF_HUB_OFFLINE"] == "1"
        with training._offline_hf(training.T4_RECIPE):
            assert os.environ["UNSLOTH_FORCE_FLOAT32"] == "1"
        assert os.environ["UNSLOTH_FORCE_FLOAT32"] == "0"
    assert os.environ["UNSLOTH_FORCE_FLOAT32"] == "previous"


def test_ada_training_execution_is_withdrawn_after_read_only_preflight(tmp_path, monkeypatch):
    paths = _ada_inputs(tmp_path, monkeypatch)
    preflight = _run(paths, recipe=training.ADA_RECIPE)
    assert preflight["execution_state"] == "PREFLIGHT_ONLY"
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, recipe=training.ADA_RECIPE, execute=True,
            approval_verifier=lambda _request: pytest.fail("approval must not be requested"))
    assert not paths[-1].exists()


def _ada_candidate(candidate, checkpoint_document=None):
    data = json.loads(candidate["manifest"].read_text())
    data["training_recipes"] = {training.ADA_RECIPE: training.ADA_RECIPE_POLICY}
    recipe = training.ADA_RECIPE
    if checkpoint_document is not None:
        from lumenis.system.ai_gateway.owned_training_checkpoints import CheckpointPolicy
        policy = CheckpointPolicy.validate({**checkpoint_document, "base_recipe": training.ADA_RECIPE})
        data["checkpoint_recovery_policies"] = {"schema_version": 1, "policies": {policy.sha256: policy.document}}
        recipe = policy.recipe
    candidate["manifest"].write_text(json.dumps(data))
    preflight = training.run_owned_lora_training(
        candidate["model"], candidate["train"], candidate["heldout"],
        candidate["output"].parent / "ada-preflight-unused", manifest_path=candidate["manifest"],
        recipe=recipe)
    candidate["preflight"] = preflight
    candidate["status"].write_text(json.dumps({**preflight,
        "execution_state": "TRAINED_NOT_EVALUATED", "candidate_status": "NOT_EVALUATED"}))
    return recipe


@pytest.mark.parametrize("checkpoint_recipe", [False, True])
def test_ada_offline_load_budget_and_identity_do_not_promote_service(candidate, monkeypatch, policy_material, checkpoint_recipe):
    recipe = _ada_candidate(candidate, policy_material[0] if checkpoint_recipe else None)
    tokenizer = _Tokenizer()
    tokenizer.decoded = {90: "Synthetic answer [[EVIDENCE-TEST-1]].", 900: "<|return|>"}
    calls = []
    torch = SimpleNamespace(bfloat16="synthetic-bfloat16", inference_mode=contextlib.nullcontext)
    class Model:
        config = SimpleNamespace(_name_or_path=str(candidate["model"]),
            quantization_config={"bnb_4bit_quant_type": "nf4"})
        device = "cuda:0"
        def eval(self):
            return self
        def generate(self, **kwargs):
            assert os.environ["UNSLOTH_FORCE_FLOAT32"] == "0"
            calls.append(kwargs)
            return _Tensor([[1, 2, 3, 90, 900]])
    def load(**kwargs):
        assert kwargs["max_seq_length"] == 4096 and kwargs["dtype"] == "synthetic-bfloat16"
        assert kwargs["local_files_only"] is True and kwargs["token"] is False
        return Model(), tokenizer
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "unsloth", SimpleNamespace(FastLanguageModel=SimpleNamespace(from_pretrained=load)))
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(PeftModel=SimpleNamespace(from_pretrained=lambda model, *a, **k: model)))
    monkeypatch.setattr(importlib.metadata, "version", inference._T4_PACKAGES.__getitem__)
    monkeypatch.setattr(training, "_require_cuda", lambda recipe: (torch, "synthetic RTX 4090", 24 * 1024**3))
    local = inference.load_owned_inference(
        candidate["model"], candidate["train"], candidate["heldout"], candidate["output"],
        manifest_path=candidate["manifest"], expected_adapter_sha256=candidate["adapter_sha"],
        expected_adapter_config_sha256=candidate["config_sha"], recipe=recipe)
    request = _request(candidate, local, training_recipe=recipe, max_new_tokens=1200)
    assert local(request)["finish_reason"] == "stop"
    assert "PRIVATE EXPECTED TARGET" not in tokenizer.prompt
    assert len(calls) == 1
    with pytest.raises(inference.OwnedInferenceBlocked, match="REQUEST_MISMATCH"):
        local(_request(candidate, local))
    with pytest.raises(inference.OwnedInferenceBlocked, match="CONTEXT_BUDGET_EXCEEDED"):
        local(_request(candidate, local, training_recipe=recipe, max_new_tokens=4096))
    assert len(calls) == 1
    status = inference.owned_inference_status(local)
    assert status["max_sequence_length"] == 4096
    assert status["available"] is False and status["service_binding"] == "NOT_BOUND"
    assert status["promotion_status"] == "NOT_PROMOTED"
    assert status["training_recipe"] == recipe
    if checkpoint_recipe:
        with pytest.raises(inference.OwnedInferenceBlocked, match="REQUEST_MISMATCH"):
            local(_request(candidate, local, training_recipe=training.ADA_RECIPE))


def test_unknown_recipe_never_falls_back():
    with pytest.raises(training.TrainingBlocked, match="NO_AUTOMATIC_FALLBACK"):
        training.recipe_sequence_length("auto")
    assert training.recipe_sequence_length(training.T4_RECIPE) == 1024
    assert training.recipe_sequence_length(training.H100_RECIPE) == 2048
