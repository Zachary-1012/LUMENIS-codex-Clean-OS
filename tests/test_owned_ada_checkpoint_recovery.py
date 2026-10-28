"""Hermetic resume wiring and cursor guards; no GPU, admission or model proof."""
import copy
import json
from dataclasses import replace

import pytest

from lumenis.system.ai_gateway import owned_training as training
from lumenis.system.ai_gateway import owned_training_checkpoints as checkpoints
from tests.test_owned_ada_recipe import _ada_inputs
from tests.test_owned_ai_training import _record, _write_jsonl
from tests.test_owned_training_checkpoint_recovery import policy_material, config_fixture, digest, consume_update


def test_ada_cursor_restores_remaining_three_updates_in_one_epoch():
    rows = [digest({"synthetic_row": i}) for i in range(4)]
    def cursor():
        return checkpoints.TrainingDataCursor(dataset_sha256="d" * 64, row_sha256=rows,
            gradient_accumulation_steps=1, base_recipe=training.ADA_RECIPE)
    reference, interrupted = cursor(), cursor()
    for value in (reference, interrupted):
        consume_update(value, rows, 0, 1, 1)
    restored = cursor()
    restored.restore(json.loads(json.dumps(interrupted.snapshot())))
    for value in (reference, restored):
        for index in range(1, 4):
            consume_update(value, rows, index, index + 1, index + 1)
    assert restored.snapshot() == reference.snapshot()
    assert restored.snapshot()["data_position"]["completed_step"] == 4
    assert restored.snapshot()["sampler_state"]["consumed_row_sha256"] == rows


@pytest.mark.parametrize("base,accumulation", [(training.T4_RECIPE, 1), (training.ADA_RECIPE, 4),
    (training.H100_RECIPE, 4), ("auto", 1), (training.ADA_RECIPE, True)])
def test_data_cursor_cannot_relabel_another_recipe(base, accumulation):
    with pytest.raises(training.TrainingBlocked):
        checkpoints.TrainingDataCursor(dataset_sha256="d" * 64, row_sha256=["e" * 64],
            gradient_accumulation_steps=accumulation, base_recipe=base)


def test_ada_resume_state_is_not_a_t4_committed_position():
    rows = [digest({"synthetic_row": i}) for i in range(4)]
    ada = checkpoints.TrainingDataCursor(dataset_sha256="d" * 64, row_sha256=rows,
        gradient_accumulation_steps=1, base_recipe=training.ADA_RECIPE)
    consume_update(ada, rows, 0, 1, 1)
    t4 = checkpoints.TrainingDataCursor(dataset_sha256="d" * 64, row_sha256=rows,
        gradient_accumulation_steps=4)
    with pytest.raises(training.TrainingBlocked, match="RESTORED_STATE_MISMATCH"):
        t4.restore(ada.snapshot())


def test_effective_ada_checkpoint_config_binds_native_precision_and_update_schedule():
    trainer, config = config_fixture()
    config.update({"bf16": True, "gradient_accumulation_steps": 1})
    observed = checkpoints.trainer_checkpoint_config(trainer, base_recipe=training.ADA_RECIPE)
    assert observed["bf16"] is True and observed["gradient_accumulation_steps"] == 1
    with pytest.raises(training.TrainingBlocked):
        checkpoints.trainer_checkpoint_config(trainer)
    config["fp16"] = True
    with pytest.raises(training.TrainingBlocked):
        checkpoints.trainer_checkpoint_config(trainer, base_recipe=training.ADA_RECIPE)


def _registered_ada_inputs(tmp_path, monkeypatch, policy_material):
    paths = _ada_inputs(tmp_path, monkeypatch)
    _write_jsonl(paths[2], [_record(f"TRAIN-{i}", f"Synthetic question {i}") for i in range(4)])
    policy = checkpoints.CheckpointPolicy.validate({**policy_material[0],
        "base_recipe": training.ADA_RECIPE, "checkpoint_interval_steps": 1})
    material = json.loads(paths[1].read_text())
    material["checkpoint_recovery_policies"] = {"schema_version": 1, "policies": {policy.sha256: policy.document}}
    paths[1].write_text(json.dumps(material), encoding="utf-8")
    return paths, policy


def _call(paths, policy, **kwargs):
    return training.run_owned_lora_training(paths[0], paths[2], paths[3], paths[4],
        manifest_path=paths[1], recipe=policy.recipe, **kwargs)


@pytest.mark.parametrize("stop", [True, 0, -1, 4, 5])
def test_invalid_stop_cannot_load_model_or_create_output(tmp_path, monkeypatch, policy_material, stop):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    calls = []
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        _call(paths, policy, stop_after_checkpoint_step=stop,
            execute=True, approval_verifier=lambda request: calls.append(request))
    assert not calls and not paths[4].exists()


def test_registered_ada_checkpoint_cannot_be_called_as_t4(tmp_path, monkeypatch, policy_material):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_RECIPE_NOT_AUTHORIZED"):
        training.run_owned_lora_training(paths[0], paths[2], paths[3], paths[4],
            manifest_path=paths[1], recipe=policy.recipe.replace(training.ADA_RECIPE, training.T4_RECIPE))


def _resume_request():
    return training.TrainingResumeRequest("00000000-0000-4000-8000-000000000000",
        "ART-0123456789abcdef", "7" * 64, 1)


def test_public_resume_binds_after_rng_and_requires_remaining_updates(tmp_path, monkeypatch, policy_material):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _call(paths, policy, execute=True, approval_verifier=lambda _request: pytest.fail("approval called"),
            checkpoint_adapter=object(), resume_request=_resume_request(), recovery_phase_transport=lambda *args: None)
    assert not (paths[4] / "adapter_model.safetensors").exists()


def test_final_checkpoint_with_no_further_update_is_not_resumed_training(tmp_path, monkeypatch, policy_material):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _call(paths, policy, execute=True, approval_verifier=lambda _request: pytest.fail("approval called"),
            checkpoint_adapter=object(), resume_request=_resume_request(), recovery_phase_transport=lambda *args: None)
    assert not (paths[4] / "adapter_model.safetensors").exists()


@pytest.mark.parametrize("committed", [True, False])
def test_controlled_interrupt_requires_committed_checkpoint_and_not_worker_reap(tmp_path, monkeypatch, policy_material, committed):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    kwargs = dict(execute=True, approval_verifier=lambda _request: pytest.fail("approval called"), checkpoint_adapter=object(),
        stop_after_checkpoint_step=1, phase_client=object())
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        _call(paths, policy, **kwargs)
    assert not (paths[4] / "adapter_model.safetensors").exists()


@pytest.mark.parametrize("change", [{"replay_through_step": True}, {"operation_id": "latest"},
    {"expected_checkpoint_sha256": "unknown"}, {"checkpoint_ref": "checkpoint-1"}])
def test_resume_references_do_not_authorize_automatic_selection(tmp_path, monkeypatch, policy_material, change):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        _call(paths, policy, resume_request=replace(_resume_request(), **change),
            recovery_phase_transport=lambda *args: None)
    assert not paths[4].exists()
