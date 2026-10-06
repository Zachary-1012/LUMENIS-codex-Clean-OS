"""Hermetic resume wiring and cursor guards; no GPU, admission or model proof."""
import copy
import importlib.metadata
import json
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest

from lumenis.system.ai_gateway import owned_training as training
from lumenis.system.ai_gateway import owned_training_checkpoints as checkpoints
from lumenis.system.ai_gateway import owned_inference as inference
from tests.test_owned_ada_recipe import _ada_inputs
from tests.test_owned_ai_training import _record, _write_jsonl, _mock_training_stack
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


def _synthetic_adapter_stack(paths, policy, monkeypatch, *, resumed_step=1, total_step=4, receipt=True):
    # This stack checks the public caller's ordering only. It has no sealed
    # owner, physical checkpoint state, GPU, optimizer, or trained adapter.
    observed = _mock_training_stack(monkeypatch)
    events = []
    cuda = SimpleNamespace(synchronize=lambda _: events.append("cuda_sync"),
        reset_peak_memory_stats=lambda _: events.append("cuda_reset"),
        max_memory_allocated=lambda _: 10 * 1024**3, max_memory_reserved=lambda _: 12 * 1024**3)
    monkeypatch.setattr(training, "_require_cuda", lambda recipe: (
        SimpleNamespace(bfloat16="synthetic-bfloat16", cuda=cuda), "synthetic RTX 4090", 24 * 1024**3))
    monkeypatch.setattr(importlib.metadata, "version", inference._T4_PACKAGES.__getitem__)
    def load(**kwargs):
        model = SimpleNamespace(config=SimpleNamespace(_name_or_path=str(paths[0]),
            quantization_config={"bnb_4bit_quant_type": "nf4"}))
        return model, sys.modules["transformers"].AutoTokenizer.from_pretrained(
            str(paths[0]), local_files_only=True, trust_remote_code=False)
    monkeypatch.setitem(sys.modules, "unsloth", SimpleNamespace(FastLanguageModel=SimpleNamespace(
        from_pretrained=load, get_peft_model=lambda model, **kwargs: model)))
    adapter = object.__new__(checkpoints.TrainingCheckpointAdapter)
    adapter.policy = policy
    adapter._last_committed_checkpoint = None
    adapter._resume_reservation = {"completed_step": resumed_step}
    adapter._failed = False
    monkeypatch.setattr(checkpoints.TrainingCheckpointAdapter, "bind_request",
        lambda self, request, verifier: events.append("bind_request"))
    def prepare(self, **kwargs):
        events.append("prepare_load")
        observed["resume_arguments"] = kwargs
        return paths[4].parent / "owner-checkpoint" / "checkpoint-1"
    monkeypatch.setattr(checkpoints.TrainingCheckpointAdapter, "prepare_load", prepare)
    fresh_phase = object()
    def recovered(self, **kwargs):
        events.extend(["verified_recovery_handoff", "before_train"])
        return fresh_phase
    monkeypatch.setattr(checkpoints.TrainingCheckpointAdapter, "recovered_phase_client", recovered)
    def boundary(verifier, phase, request, name):
        # The actual cryptographic phase and permission fences remain exercised
        # independently by the existing callback/HTTP/recovery guard suites.
        training._verify_approval(verifier, request)
        events.append(name)
        if name in {"step_begin", "substep_end", "pre_optimizer_step", "before_adapter_save"} and "prepare_load" in events:
            assert phase is fresh_phase
    monkeypatch.setattr(training, "_verify_training_boundary", boundary)
    def update(self, trainer, control):
        events.append("observed_synthetic_update")
        return control
    monkeypatch.setattr(checkpoints.TrainingCheckpointAdapter, "complete_optimizer_step", update)
    parent = sys.modules["trl"].SFTTrainer
    class SyntheticTrainer(parent):
        def train(self, resume_from_checkpoint=None):
            observed["train_calls"] += 1
            if resume_from_checkpoint is not None:
                assert resume_from_checkpoint.endswith("owner-checkpoint\\checkpoint-1") or resume_from_checkpoint.endswith("owner-checkpoint/checkpoint-1")
                events.extend(["load_model", "load_optimizer_scheduler", "load_callbacks", "load_rng", "load_committed"])
                start = resumed_step
            else:
                start = 0
            control = SimpleNamespace(should_training_stop=False)
            self.state = SimpleNamespace(global_step=start, log_history=[])
            for index in range(start, total_step):
                for event in ("on_step_begin", "on_pre_optimizer_step"):
                    getattr(self.callbacks[0], event)(self.args if hasattr(self, "args") else observed["args"], self.state, control)
                self.state.global_step = index + 1
                self.state.log_history.append({"step": index + 1, "loss": 1.25})
                self.callbacks[0].on_step_end(observed["args"], self.state, control)
                if receipt:
                    adapter._last_committed_checkpoint = {"completed_step": index + 1, "checkpoint_ref": "ART-0123456789abcdef"}
                self.callbacks[0].on_save(observed["args"], self.state, control)
                if control.should_training_stop:
                    break
            return SimpleNamespace(global_step=self.state.global_step, metrics={"train_loss": 1.25})
    monkeypatch.setattr(checkpoints.TrainingCheckpointAdapter, "trainer_type", lambda self, trainer: SyntheticTrainer)
    return adapter, observed, events


def _resume_request():
    return training.TrainingResumeRequest("00000000-0000-4000-8000-000000000000",
        "ART-0123456789abcdef", "7" * 64, 1)


def test_public_resume_binds_after_rng_and_requires_remaining_updates(tmp_path, monkeypatch, policy_material):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    adapter, observed, events = _synthetic_adapter_stack(paths, policy, monkeypatch)
    result = _call(paths, policy, execute=True, approval_verifier=lambda _: True,
        checkpoint_adapter=adapter, resume_request=_resume_request(), recovery_phase_transport=lambda *args: None)
    assert "initial" not in events and "before_output_dir" not in events
    assert events.index("load_rng") < events.index("load_committed") < events.index("before_train") < events.index("step_begin")
    assert events.count("before_train") == 1
    assert observed["resume_arguments"]["operation_id"] == _resume_request().operation_id
    assert result["optimizer_steps_this_attempt"] == 3 and result["optimizer_steps"] == 4
    assert result["resume_completed_step"] == 1
    assert result["training_peak_allocated_bytes"] == 10 * 1024**3
    assert result["training_peak_reserved_bytes"] == 12 * 1024**3
    assert result["training_wall_seconds"] >= 0
    assert result["training_loss_history"][-1] == {"optimizer_step": 4, "loss": 1.25}
    assert result["execution_state"] == "TRAINED_NOT_EVALUATED"
    assert result["candidate_status"] == "NOT_EVALUATED"


def test_final_checkpoint_with_no_further_update_is_not_resumed_training(tmp_path, monkeypatch, policy_material):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    adapter, observed, events = _synthetic_adapter_stack(paths, policy, monkeypatch, resumed_step=4, total_step=4)
    with pytest.raises(training.TrainingBlocked, match="WITHOUT_OPTIMIZER_STEPS"):
        _call(paths, policy, execute=True, approval_verifier=lambda _: True,
            checkpoint_adapter=adapter, resume_request=_resume_request(), recovery_phase_transport=lambda *args: None)
    assert observed["save_calls"] == 0 and "before_train" not in events
    assert not (paths[4] / "adapter_model.safetensors").exists()


@pytest.mark.parametrize("committed", [True, False])
def test_controlled_interrupt_requires_committed_checkpoint_and_not_worker_reap(tmp_path, monkeypatch, policy_material, committed):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    adapter, observed, events = _synthetic_adapter_stack(paths, policy, monkeypatch, receipt=committed)
    kwargs = dict(execute=True, approval_verifier=lambda _: True, checkpoint_adapter=adapter,
        stop_after_checkpoint_step=1, phase_client=object())
    if not committed:
        with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_NOT_COMMITTED"):
            _call(paths, policy, **kwargs)
    else:
        result = _call(paths, policy, **kwargs)
        assert result["execution_state"] == "CHECKPOINT_SAVED_TRAINING_INTERRUPTED"
        assert result["worker_stop_state"] == "OWNER_STOP_AND_REAP_REQUIRED"
        assert result["optimizer_steps_this_attempt"] == 1
        assert result["candidate_status"] == "NOT_EVALUATED"
    assert observed["save_calls"] == 0
    assert not (paths[4] / "adapter_model.safetensors").exists()


@pytest.mark.parametrize("change", [{"replay_through_step": True}, {"operation_id": "latest"},
    {"expected_checkpoint_sha256": "unknown"}, {"checkpoint_ref": "checkpoint-1"}])
def test_resume_references_do_not_authorize_automatic_selection(tmp_path, monkeypatch, policy_material, change):
    paths, policy = _registered_ada_inputs(tmp_path, monkeypatch, policy_material)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        _call(paths, policy, resume_request=replace(_resume_request(), **change),
            recovery_phase_transport=lambda *args: None)
    assert not paths[4].exists()
