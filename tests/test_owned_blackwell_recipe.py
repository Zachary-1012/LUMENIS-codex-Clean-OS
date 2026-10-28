"""Explicit RTX5090 compatibility checks; all hardware/model stacks are synthetic."""
import importlib.metadata
import json
import os
import sys
from types import SimpleNamespace

import pytest

from lumenis.system.ai_gateway import owned_training as training, owned_inference as inference
from lumenis.system.ai_gateway import owned_training_checkpoints as checkpoints
from tests.test_owned_ai_training import _t4_inputs, _run
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
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, recipe=training.BLACKWELL_RECIPE, execute=True, approval_verifier=deny)
    assert seen == []
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


def test_blackwell_training_execution_is_withdrawn_after_preflight(tmp_path, monkeypatch):
    paths = blackwell_inputs(tmp_path, monkeypatch)
    result = _run(paths, recipe=training.BLACKWELL_RECIPE)
    assert result["execution_state"] == "PREFLIGHT_ONLY"
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _run(paths, recipe=training.BLACKWELL_RECIPE, execute=True,
            approval_verifier=lambda _request: pytest.fail("approval must not be requested"))
    assert not paths[-1].exists()
