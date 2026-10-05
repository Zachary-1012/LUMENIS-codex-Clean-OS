"""Explicit RTX5090 compatibility checks; all hardware/model stacks are synthetic."""
import importlib.metadata
import json
import os
import sys
from types import SimpleNamespace

import pytest

from lumenis.system.ai_gateway import owned_training as training, owned_inference as inference
from lumenis.system.ai_gateway import owned_training_checkpoints as checkpoints
from tests.test_owned_ai_training import _t4_inputs, _run, _mock_training_stack
from tests.test_owned_training_checkpoint_recovery import config_fixture, policy_material


@pytest.fixture(autouse=True)
def unit_receipt_signer(monkeypatch):
    from tests.test_owned_training_callback_v3 import _unit_signer
    _unit_signer(monkeypatch)


def blackwell_inputs(tmp_path, monkeypatch):
    paths = _t4_inputs(tmp_path, monkeypatch)
    data = json.loads(paths[1].read_bytes())
    data["training_recipes"] = {training.BLACKWELL_RECIPE: training.BLACKWELL_RECIPE_POLICY}
    paths[1].write_text(json.dumps(data), encoding="utf-8")
    return paths


def test_blackwell_reuses_approved_variant_and_has_distinct_recipe_permission(tmp_path, monkeypatch):
    paths = blackwell_inputs(tmp_path, monkeypatch)
    result = _run(paths, recipe=training.BLACKWELL_RECIPE)
    assert result["model_id"] == training.T4_MODEL_ID and result["model_revision"] == training.T4_MODEL_REVISION
    assert result["execution_state"] == "PREFLIGHT_ONLY"
    seen = []
    def deny(request):
        seen.append(request)
        return False
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        _run(paths, recipe=training.BLACKWELL_RECIPE, execute=True, approval_verifier=deny)
    assert seen[0].recipe == training.BLACKWELL_RECIPE
    assert not paths[-1].exists()


def test_blackwell_manifest_cannot_be_replaced_with_ada_policy(tmp_path, monkeypatch):
    paths = blackwell_inputs(tmp_path, monkeypatch)
    data = json.loads(paths[1].read_bytes())
    data["training_recipes"][training.BLACKWELL_RECIPE] = training.ADA_RECIPE_POLICY
    paths[1].write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(training.TrainingBlocked, match="APPROVED_BLACKWELL_RECIPE_POLICY_REQUIRED"):
        _run(paths, recipe=training.BLACKWELL_RECIPE)
    assert not paths[-1].exists()


@pytest.mark.parametrize("major,minor,name,memory,count,bf16,cuda,arch,allowed", [
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 1, True, "12.8", ["sm_120"], True),
    (12, 0, "NVIDIA GeForce RTX 5090", 30 * 1024**3, 1, True, "12.8", ["sm_90", "sm_120"], True),
    (8, 9, "NVIDIA GeForce RTX 4090", 32 * 1024**3, 1, True, "12.8", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090 D", 32 * 1024**3, 1, True, "12.8", ["sm_120"], False),
    (10, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 1, True, "12.8", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 30 * 1024**3 - 1, 1, True, "12.8", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 5, True, "12.8", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, True, True, "12.8", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 1, False, "12.8", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 1, True, "12.6", ["sm_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 1, True, "12.8", ["compute_120"], False),
    (12, 0, "NVIDIA GeForce RTX 5090", 32 * 1024**3, 1, True, "12.8", [], False),
])
def test_blackwell_requires_native_single_card_sm120_and_compiled_stack(monkeypatch, major, minor, name, memory, count, bf16, cuda, arch, allowed):
    seen = []
    def native(*, including_emulation):
        seen.append(including_emulation)
        return bf16
    device = SimpleNamespace(name=name, major=major, minor=minor, total_memory=memory)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda=cuda), cuda=SimpleNamespace(
        is_available=lambda: True, device_count=lambda: count, get_device_properties=lambda _: device,
        is_bf16_supported=native, get_arch_list=lambda: arch)))
    if allowed:
        assert training._require_cuda(training.BLACKWELL_RECIPE)[1:] == (name, memory)
        assert seen == [False]
    else:
        with pytest.raises(training.TrainingBlocked, match="BLACKWELL_NF4_RECIPE_REQUIRES"):
            training._require_cuda(training.BLACKWELL_RECIPE)


def test_blackwell_checkpoint_policy_and_native_configuration_bind_its_own_recipe(policy_material):
    policy = checkpoints.CheckpointPolicy.validate({**policy_material[0], "base_recipe": training.BLACKWELL_RECIPE})
    assert policy.recipe.startswith(training.BLACKWELL_RECIPE + "+checkpoint-v1:")
    trainer, config = config_fixture()
    config.update(bf16=True, gradient_accumulation_steps=1)
    measured = checkpoints.trainer_checkpoint_config(trainer, base_recipe=training.BLACKWELL_RECIPE)
    assert measured["bf16"] is True and measured["gradient_accumulation_steps"] == 1
    assert training.recipe_sequence_length(training.BLACKWELL_RECIPE) == 16384
    with pytest.raises(training.TrainingBlocked):
        checkpoints.trainer_checkpoint_config(trainer, base_recipe=training.T4_RECIPE)
    config["bf16"] = False
    with pytest.raises(training.TrainingBlocked):
        checkpoints.trainer_checkpoint_config(trainer, base_recipe=training.BLACKWELL_RECIPE)


def test_blackwell_training_loader_retains_exact_nf4_and_bf16_isolation(tmp_path, monkeypatch):
    paths = blackwell_inputs(tmp_path, monkeypatch)
    observed = _mock_training_stack(monkeypatch)
    monkeypatch.setattr(training, "_require_cuda", lambda recipe: (
        SimpleNamespace(bfloat16="synthetic-native-bf16", cuda=SimpleNamespace(synchronize=lambda _: None,
            reset_peak_memory_stats=lambda _: None, max_memory_allocated=lambda _: 10 * 1024**3,
            max_memory_reserved=lambda _: 12 * 1024**3)), "synthetic RTX5090", 32 * 1024**3))
    monkeypatch.setattr(importlib.metadata, "version", inference._T4_PACKAGES.__getitem__)
    def load(**kwargs):
        assert kwargs["dtype"] == "synthetic-native-bf16" and kwargs["max_seq_length"] == 16384
        assert kwargs["load_in_4bit"] is True and kwargs["local_files_only"] is True and kwargs["token"] is False
        assert os.environ["UNSLOTH_FORCE_FLOAT32"] == "0"
        model = SimpleNamespace(config=SimpleNamespace(_name_or_path=str(paths[0]),
            quantization_config={"bnb_4bit_quant_type": "nf4"}))
        return model, sys.modules["transformers"].AutoTokenizer.from_pretrained(str(paths[0]), local_files_only=True, trust_remote_code=False)
    monkeypatch.setitem(sys.modules, "unsloth", SimpleNamespace(FastLanguageModel=SimpleNamespace(
        from_pretrained=load, get_peft_model=lambda model, **kwargs: model)))
    trainer = sys.modules["trl"].SFTTrainer
    parent = trainer.train
    def train(self):
        value = parent(self)
        value.metrics = {"train_loss": 1.25}
        return value
    monkeypatch.setattr(trainer, "train", train)
    result = _run(paths, recipe=training.BLACKWELL_RECIPE, execute=True, approval_verifier=lambda _: True)
    assert result["training_recipe"] == training.BLACKWELL_RECIPE
    assert result["training_packages"] == inference._T4_PACKAGES
    assert observed["args"].bf16 is True and observed["args"].gradient_accumulation_steps == 1
    assert result["training_peak_reserved_bytes"] == 12 * 1024**3
