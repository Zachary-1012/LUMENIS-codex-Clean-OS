"""Offline evaluation callable for one hash-pinned SYSTEM AI Gateway candidate."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import owned_evaluation, owned_training

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_HARMONY_CONTROL = re.compile(r"<\|[a-zA-Z0-9_]+\|>")
_MAX_SEQUENCE_LENGTH = 1024
_GENERATION_MAX_TIME_SECONDS = 180.0
_T4_PACKAGES = {
    "unsloth": "2026.9.12", "unsloth_zoo": "2026.9.8", "transformers": "4.56.2",
    "trl": "0.22.2", "torch": "2.11.0+cu128", "bitsandbytes": "0.50.2",
    "tokenizers": "0.22.2", "triton": "3.6.0",
}
_TERMINATORS = ("<|return|>", "<|fim_suffix|>")


class OwnedInferenceBlocked(RuntimeError):
    """A local candidate or inference request failed its explicit contract."""


def owned_inference_status(candidate=None):
    """Read a supplied evaluation runtime without loading, probing, or generating.

    An offline evaluation candidate is never an accepted product service. The
    caller must retain its actual runtime handle; this function discovers none.
    """
    status = {
        "provider": "owned", "available": False, "service_binding": "NOT_BOUND",
        "candidate_loaded": False, "evaluation_callable": False,
        "business_acceptance": "HUMAN_REVIEW_REQUIRED", "promotion_status": "NOT_PROMOTED",
        "generation_probe_performed": False, "fallback_allowed": False,
        "state": "UNAVAILABLE", "reason": "OWNED_RUNTIME_NOT_BOUND",
    }
    if candidate is None:
        return status
    if not isinstance(candidate, _OfflineCandidate):
        return {**status, "state": "BLOCKED", "reason": "OWNED_RUNTIME_HANDLE_INVALID"}
    try:
        candidate._verify_small_artifacts()
    except (OwnedInferenceBlocked, OSError):
        return {**status, "state": "BLOCKED", "reason": "CANDIDATE_ARTIFACT_CHANGED_OR_UNREADABLE"}
    return {
        **status, "state": "LOADED_EVALUATION_CANDIDATE", "reason": "NOT_ACCEPTED_OR_SERVICE_BOUND",
        "candidate_loaded": True, "evaluation_callable": True,
        "candidate_identity_sha256": candidate.candidate_identity_sha256,
        "model_id": candidate._preflight["model_id"],
        "model_revision": candidate._preflight["model_revision"],
        "training_recipe": candidate._preflight["training_recipe"],
        "max_sequence_length": _MAX_SEQUENCE_LENGTH,
    }


def _paths(model_snapshot_dir, train_jsonl_path, heldout_jsonl_path,
           candidate_output_dir, manifest_path):
    values = (model_snapshot_dir, train_jsonl_path, heldout_jsonl_path,
              candidate_output_dir, manifest_path)
    if any(Path(value).is_symlink() for value in values):
        raise OwnedInferenceBlocked("LOCAL_CANDIDATE_PATH_SYMLINKED")
    return tuple(owned_training._local_path(value) for value in values)


def load_owned_inference(
    model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir, *,
    manifest_path, expected_adapter_sha256: str, expected_adapter_config_sha256: str,
    recipe: str = owned_training.T4_RECIPE,
):
    """Explicitly load only the approved T4/NF4 candidate; H100 is unsupported."""
    if recipe != owned_training.T4_RECIPE:
        raise OwnedInferenceBlocked("UNSUPPORTED_INFERENCE_RECIPE")
    if any(not isinstance(value, str) or not _DIGEST.fullmatch(value)
           for value in (expected_adapter_sha256, expected_adapter_config_sha256)):
        raise OwnedInferenceBlocked("EXACT_ADAPTER_HASHES_REQUIRED")

    model_dir, train_path, heldout_path, output, manifest = _paths(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path,
        candidate_output_dir, manifest_path,
    )
    if not output.is_dir():
        raise OwnedInferenceBlocked("TRAINED_CANDIDATE_DIRECTORY_REQUIRED")
    status_path = output / "training_status.json"
    adapter_path = output / "adapter_model.safetensors"
    config_path = output / "adapter_config.json"
    if any(path.is_symlink() or not path.is_file()
           for path in (status_path, adapter_path, config_path)):
        raise OwnedInferenceBlocked("TRAINED_CANDIDATE_ARTIFACTS_REQUIRED")

    unused = output.parent / f".{output.name}.inference-preflight-unused"
    if unused.exists() or unused.is_symlink():
        raise OwnedInferenceBlocked("PREFLIGHT_OUTPUT_PATH_ALREADY_EXISTS")
    preflight = owned_training.run_owned_lora_training(
        model_dir, train_path, heldout_path, unused, manifest_path=manifest,
        execute=False, recipe=recipe,
    )
    status_bytes = status_path.read_bytes()
    try:
        status = json.loads(status_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OwnedInferenceBlocked("TRAINING_STATUS_INVALID") from exc
    if not isinstance(status, dict) or any(
        status.get(key) != preflight.get(key) for key in owned_evaluation._STATUS_IDENTITY
    ) or status.get("execution_state") != "TRAINED_NOT_EVALUATED" \
            or status.get("candidate_status") != "NOT_EVALUATED":
        raise OwnedInferenceBlocked("CANDIDATE_NOT_TRAINED_OR_IDENTITY_MISMATCH")

    adapter_sha, config_sha = owned_training._sha256(adapter_path), owned_training._sha256(config_path)
    if (adapter_sha, config_sha) != (expected_adapter_sha256, expected_adapter_config_sha256):
        raise OwnedInferenceBlocked("ADAPTER_HASH_MISMATCH")
    identity = {key: preflight[key] for key in owned_evaluation._STATUS_IDENTITY}
    status_sha = hashlib.sha256(status_bytes).hexdigest()
    identity.update({
        "execution_state": status["execution_state"], "candidate_status": status["candidate_status"],
        "training_status_sha256": status_sha,
        "adapter_sha256": adapter_sha, "adapter_config_sha256": config_sha,
    })
    candidate_sha = hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()

    # The same immutable local manifest validation used by training checks the
    # complete materialized base snapshot and its pinned file hashes here.
    from importlib.metadata import PackageNotFoundError, version
    try:
        installed = {name: version(name) for name in _T4_PACKAGES}
    except PackageNotFoundError as exc:
        raise OwnedInferenceBlocked("T4_INFERENCE_DEPENDENCIES_UNAVAILABLE") from exc
    if installed != _T4_PACKAGES:
        raise OwnedInferenceBlocked("T4_INFERENCE_STACK_VERSION_MISMATCH")

    try:
        with owned_training._offline_hf(recipe):
            from unsloth import FastLanguageModel
            from peft import PeftModel
            import torch
            owned_training._require_cuda(recipe)
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=str(model_dir), max_seq_length=_MAX_SEQUENCE_LENGTH, dtype=None,
                load_in_4bit=True, full_finetuning=False, local_files_only=True,
                trust_remote_code=False, token=False,
            )
            loaded_path = Path(str(getattr(model.config, "_name_or_path", ""))).resolve()
            if loaded_path != model_dir:
                raise OwnedInferenceBlocked("LOADER_CHANGED_PINNED_MODEL_PATH")
            quantization = getattr(model.config, "quantization_config", {})
            if not isinstance(quantization, dict) or quantization.get("bnb_4bit_quant_type") != "nf4":
                raise OwnedInferenceBlocked("LOADER_QUANTIZATION_MISMATCH")
            model = PeftModel.from_pretrained(
                model, str(output), is_trainable=False,
                local_files_only=True, token=False,
            )
            model.eval()
    except OwnedInferenceBlocked:
        raise
    except owned_training.TrainingBlocked as exc:
        raise OwnedInferenceBlocked(str(exc)) from exc
    except Exception as exc:
        raise OwnedInferenceBlocked("T4_LOCAL_CANDIDATE_LOAD_FAILED") from exc

    candidate = _OfflineCandidate(
        model, tokenizer, torch, status_path, adapter_path,
        config_path, preflight, candidate_sha, status_sha, adapter_sha, config_sha,
    )
    candidate._verify_small_artifacts()
    return candidate


class _OfflineCandidate:
    def __init__(self, model, tokenizer, torch, status_path,
                 adapter_path, config_path, preflight, candidate_sha, status_sha,
                 adapter_sha, config_sha):
        self._model, self._tokenizer, self._torch = model, tokenizer, torch
        self._status_path, self._adapter_path, self._config_path = status_path, adapter_path, config_path
        self._preflight, self.candidate_identity_sha256 = preflight, candidate_sha
        self._status_sha, self._adapter_sha, self._config_sha = status_sha, adapter_sha, config_sha
        self._eos_ids = {}
        for token in _TERMINATORS:
            token_id = tokenizer.convert_tokens_to_ids(token)
            if type(token_id) is not int or token_id < 0 or token_id == getattr(tokenizer, "unk_token_id", None):
                raise OwnedInferenceBlocked("GPT_OSS_TERMINATOR_TOKEN_UNAVAILABLE")
            self._eos_ids[token_id] = token

    def _verify_small_artifacts(self):
        if any(path.is_symlink() or not path.is_file() for path in
               (self._status_path, self._adapter_path, self._config_path)):
            raise OwnedInferenceBlocked("CANDIDATE_ARTIFACT_CHANGED")
        if (owned_training._sha256(self._status_path) != self._status_sha
                or owned_training._sha256(self._adapter_path) != self._adapter_sha
                or owned_training._sha256(self._config_path) != self._config_sha):
            raise OwnedInferenceBlocked("CANDIDATE_ARTIFACT_CHANGED")

    def __call__(self, request):
        if not isinstance(request, owned_evaluation.CandidateInferenceRequest):
            raise OwnedInferenceBlocked("CANDIDATE_INFERENCE_REQUEST_REQUIRED")
        expected = self._preflight
        if any((
            request.candidate_identity_sha256 != self.candidate_identity_sha256,
            request.model_id != expected["model_id"], request.model_revision != expected["model_revision"],
            request.training_recipe != owned_training.T4_RECIPE,
            request.manifest_sha256 != expected["manifest_sha256"],
            request.train_sha256 != expected["train_sha256"],
            request.heldout_sha256 != expected["heldout_sha256"],
            request.adapter_sha256 != self._adapter_sha,
            request.adapter_config_sha256 != self._config_sha,
            request.domain_id != expected["domain_id"], request.scope not in expected["scopes"],
            request.local_only is not True, request.network_access is not False,
            request.fallback_allowed is not False,
            type(request.max_new_tokens) is not int or not 1 <= request.max_new_tokens <= 4096,
            not isinstance(request.user_messages, tuple) or not request.user_messages
            or any(not isinstance(item, str) or not item.strip()
                   or _HARMONY_CONTROL.search(item) for item in request.user_messages),
        )):
            raise OwnedInferenceBlocked("CANDIDATE_INFERENCE_REQUEST_MISMATCH")
        self._verify_small_artifacts()

        prompt = "".join(
            f"<|start|>user<|message|>{message}<|end|>" for message in request.user_messages
        ) + "<|start|>assistant<|channel|>final<|message|>"
        try:
            with owned_training._offline_hf(owned_training.T4_RECIPE), self._torch.inference_mode():
                encoded = self._tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
                input_ids = encoded["input_ids"]
                input_length = int(input_ids.shape[1])
                if input_length + request.max_new_tokens > _MAX_SEQUENCE_LENGTH:
                    raise OwnedInferenceBlocked("T4_CONTEXT_BUDGET_EXCEEDED")
                device = getattr(self._model, "device", None)
                if device is not None:
                    encoded = {key: value.to(device) for key, value in encoded.items()}
                generated = self._model.generate(
                    **encoded, max_new_tokens=request.max_new_tokens, do_sample=False,
                    eos_token_id=list(self._eos_ids), pad_token_id=next(iter(self._eos_ids)),
                    # Transformers checks max_time between decode steps; this cannot cancel a running kernel.
                    use_cache=True, max_time=_GENERATION_MAX_TIME_SECONDS,
                )
            sequences = getattr(generated, "sequences", generated)
            token_ids = sequences[0][input_length:]
            if hasattr(token_ids, "tolist"):
                token_ids = token_ids.tolist()
            termination = self._eos_ids.get(token_ids[-1]) if token_ids else None
            text = self._tokenizer.decode(token_ids, skip_special_tokens=False)
            if termination and not text.endswith(termination):
                text = text.replace(termination, "") + termination
            raw = "<|start|>assistant<|channel|>final<|message|>" + text
            finish_reason = "stop" if termination else (
                "timeout" if len(token_ids) < request.max_new_tokens else "length"
            )
            response = {
                "generated_text": raw, "finish_reason": finish_reason,
                "termination_token": termination or "",
            }
            self._verify_small_artifacts()
            return response
        except OwnedInferenceBlocked:
            raise
        except Exception as exc:
            # No prompt, raw generation, or exception text is logged or persisted here.
            raise OwnedInferenceBlocked("T4_LOCAL_GENERATION_FAILED") from exc
