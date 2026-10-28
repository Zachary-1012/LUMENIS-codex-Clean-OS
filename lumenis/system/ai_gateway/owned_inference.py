"""Hash-pinned local kernels and separately admitted SYSTEM inference runtimes."""
from __future__ import annotations

import gc
import hashlib
import json
import os
import re
import threading
import time
import uuid
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
_PRETRAINED_PACKAGE_NAMES = ("safetensors", "tokenizers", "torch", "transformers")
_PRETRAINED_MEMORY_RESERVE_BYTES = 512 * 1024**2
_TORCH_CPU_THREADS_LOCK = threading.RLock()


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
        "max_sequence_length": candidate._max_sequence_length,
    }


def _paths(model_snapshot_dir, train_jsonl_path, heldout_jsonl_path,
           candidate_output_dir, manifest_path):
    values = (model_snapshot_dir, train_jsonl_path, heldout_jsonl_path,
              candidate_output_dir, manifest_path)
    if any(Path(value).is_symlink() for value in values):
        raise OwnedInferenceBlocked("LOCAL_CANDIDATE_PATH_SYMLINKED")
    return tuple(owned_training._local_path(value) for value in values)


def _prepare_candidate_files(
    model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir, *,
    manifest_path, expected_adapter_sha256: str, expected_adapter_config_sha256: str,
    recipe: str = owned_training.T4_RECIPE,
):
    """Verify immutable local files without importing or loading model weights."""
    checkpoint_recipe = (type(recipe) is str and any(
        recipe.startswith(base + "+checkpoint-v1:") for base in owned_training.NF4_RECIPES))
    if recipe not in owned_training.NF4_RECIPES and not checkpoint_recipe:
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

    return (model_dir, output, status_path, adapter_path, config_path, preflight,
            candidate_sha, status_sha, adapter_sha, config_sha,
            {"manifest_sha256": manifest, "train_sha256": train_path,
             "heldout_sha256": heldout_path})


def _installed_inference_packages():

    # The same immutable local manifest validation used by training checks the
    # complete materialized base snapshot and its pinned file hashes here.
    from importlib.metadata import PackageNotFoundError, version
    try:
        installed = {name: version(name) for name in _T4_PACKAGES}
    except PackageNotFoundError as exc:
        raise OwnedInferenceBlocked("T4_INFERENCE_DEPENDENCIES_UNAVAILABLE") from exc
    if installed != _T4_PACKAGES:
        raise OwnedInferenceBlocked("T4_INFERENCE_STACK_VERSION_MISMATCH")
    return installed


def _load_local_kernel(parts, *, evaluation_only=False):
    (model_dir, output, status_path, adapter_path, config_path, preflight,
     candidate_sha, status_sha, adapter_sha, config_sha) = parts[:10]
    base_recipe = preflight["base_training_recipe"]
    _installed_inference_packages()

    try:
        with owned_training._offline_hf(base_recipe):
            from unsloth import FastLanguageModel
            from peft import PeftModel
            import torch
            owned_training._require_cuda(base_recipe)
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=str(model_dir), max_seq_length=owned_training.recipe_sequence_length(base_recipe),
                dtype=torch.bfloat16 if base_recipe in owned_training.NATIVE_BF16_NF4_RECIPES else None,
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

    kernel_type = _OfflineCandidate if evaluation_only else _LocalTextKernel
    candidate = kernel_type(
        model, tokenizer, torch, status_path, adapter_path,
        config_path, preflight, candidate_sha, status_sha, adapter_sha, config_sha,
    )
    candidate._verify_small_artifacts()
    return candidate


def load_owned_inference(
    model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir, *,
    manifest_path, expected_adapter_sha256: str, expected_adapter_config_sha256: str,
    recipe: str = owned_training.T4_RECIPE,
):
    """Load an evaluation candidate; this entry never grants production use."""
    parts = _prepare_candidate_files(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir,
        manifest_path=manifest_path, expected_adapter_sha256=expected_adapter_sha256,
        expected_adapter_config_sha256=expected_adapter_config_sha256, recipe=recipe,
    )
    return _load_local_kernel(parts, evaluation_only=True)


class _LocalTextKernel:
    def __init__(self, model, tokenizer, torch, status_path,
                 adapter_path, config_path, preflight, candidate_sha, status_sha,
                 adapter_sha, config_sha):
        self._model, self._tokenizer, self._torch = model, tokenizer, torch
        self._status_path, self._adapter_path, self._config_path = status_path, adapter_path, config_path
        self._preflight, self.candidate_identity_sha256 = preflight, candidate_sha
        self._base_recipe = preflight.get("base_training_recipe", preflight["training_recipe"])
        self._max_sequence_length = owned_training.recipe_sequence_length(self._base_recipe)
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

    def _generate(self, prompt, max_new_tokens, *, is_cancelled=None, context_window_tokens=None):
        self._verify_small_artifacts()
        if is_cancelled is not None and is_cancelled():
            raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCELLED")
        try:
            with owned_training._offline_hf(self._base_recipe), self._torch.inference_mode():
                encoded = self._tokenizer(prompt, return_tensors="pt", add_special_tokens=False, truncation=False)
                input_length = int(encoded["input_ids"].shape[1])
                limit = self._max_sequence_length if context_window_tokens is None else context_window_tokens
                if input_length + max_new_tokens > limit:
                    raise OwnedInferenceBlocked("T4_CONTEXT_BUDGET_EXCEEDED")
                device = getattr(self._model, "device", None)
                if device is not None:
                    encoded = {key: value.to(device) for key, value in encoded.items()}
                options = {}
                if is_cancelled is not None:
                    from transformers import StoppingCriteria, StoppingCriteriaList

                    class _Cancelled(StoppingCriteria):
                        def __call__(self, input_ids, scores, **kwargs):
                            return bool(is_cancelled())

                    options["stopping_criteria"] = StoppingCriteriaList([_Cancelled()])
                if is_cancelled is not None and is_cancelled():
                    raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCELLED")
                generated = self._model.generate(
                    **encoded, max_new_tokens=max_new_tokens, do_sample=False,
                    eos_token_id=list(self._eos_ids), pad_token_id=next(iter(self._eos_ids)),
                    # Cancellation/time limits are checked between decode steps, not inside a CUDA kernel.
                    use_cache=True, max_time=_GENERATION_MAX_TIME_SECONDS, **options,
                )
            if is_cancelled is not None and is_cancelled():
                raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCELLED")
            sequences = getattr(generated, "sequences", generated)
            token_ids = sequences[0][input_length:]
            if hasattr(token_ids, "tolist"):
                token_ids = token_ids.tolist()
            termination = self._eos_ids.get(token_ids[-1]) if token_ids else None
            text = self._tokenizer.decode(token_ids, skip_special_tokens=False)
            if termination and not text.endswith(termination):
                text = text.replace(termination, "") + termination
            response = {
                "generated_text": "<|start|>assistant<|channel|>final<|message|>" + text,
                "finish_reason": "stop" if termination else (
                    "timeout" if len(token_ids) < max_new_tokens else "length"
                ),
                "termination_token": termination or "",
                "prompt_tokens": input_length, "completion_tokens": len(token_ids),
                "final_channel_prefill": True,
            }
            self._verify_small_artifacts()
            return response
        except OwnedInferenceBlocked:
            raise
        except Exception as exc:
            raise OwnedInferenceBlocked("T4_LOCAL_GENERATION_FAILED") from exc


class _OfflineCandidate(_LocalTextKernel):
    def __call__(self, request):
        if not isinstance(request, owned_evaluation.CandidateInferenceRequest):
            raise OwnedInferenceBlocked("CANDIDATE_INFERENCE_REQUEST_REQUIRED")
        expected = self._preflight
        if any((
            request.candidate_identity_sha256 != self.candidate_identity_sha256,
            request.model_id != expected["model_id"], request.model_revision != expected["model_revision"],
            request.training_recipe != expected["training_recipe"],
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
        response = self._generate(prompt, request.max_new_tokens)
        return {key: response[key] for key in
                ("generated_text", "finish_reason", "termination_token")}


_PRODUCTION_RUNTIME_ISSUER = object()


def _production_executor_identity(handler=None):
    from agent_capability.formation import implementation_identity
    from . import owned_service
    from lumenis.system.security import owned_model_admission

    return implementation_identity(handler or OwnedProductionRuntime.generate, (
        __file__, owned_training.__file__, owned_evaluation.__file__,
        owned_service.__file__, owned_model_admission.__file__,
    ))


def _production_runtime_identity(parts, context_window_tokens, output_token_limit):
    preflight, candidate_sha = parts[5], parts[6]
    base_recipe = preflight["base_training_recipe"]
    maximum = owned_training.recipe_sequence_length(base_recipe)
    if (type(context_window_tokens) is not int
            or not 2 <= context_window_tokens <= maximum
            or type(output_token_limit) is not int
            or not 1 <= output_token_limit < context_window_tokens):
        raise OwnedInferenceBlocked("OWNED_RUNTIME_TOKEN_LIMITS_INVALID")
    installed = _installed_inference_packages()
    if any(path.is_symlink() or not path.is_file()
           or owned_training._sha256(path) != preflight[key]
           for key, path in parts[10].items()):
        raise OwnedInferenceBlocked("OWNED_RUNTIME_MATERIAL_CHANGED")
    try:
        with owned_training._offline_hf(base_recipe):
            torch, gpu_name, gpu_memory = owned_training._require_cuda(base_recipe)
            capability = tuple(torch.cuda.get_device_capability(0))
            device_count = torch.cuda.device_count()
            cuda_version = torch.version.cuda
        if (type(gpu_name) is not str or not gpu_name
                or type(gpu_memory) is not int or gpu_memory <= 0
                or len(capability) != 2 or any(type(n) is not int for n in capability)
                or type(device_count) is not int or device_count < 1
                or type(cuda_version) is not str or not cuda_version):
            raise OwnedInferenceBlocked("OWNED_RUNTIME_ENVIRONMENT_UNVERIFIED")
    except OwnedInferenceBlocked:
        raise
    except owned_training.TrainingBlocked as exc:
        raise OwnedInferenceBlocked(str(exc)) from exc
    except Exception as exc:
        raise OwnedInferenceBlocked("OWNED_RUNTIME_ENVIRONMENT_UNVERIFIED") from exc
    identity = {
        "executor_sha256": _production_executor_identity(),
        "candidate_identity_sha256": candidate_sha,
        "model_id": preflight["model_id"], "model_revision": preflight["model_revision"],
        "recipe": preflight["training_recipe"],
        "manifest_sha256": preflight["manifest_sha256"],
        "train_sha256": preflight["train_sha256"], "heldout_sha256": preflight["heldout_sha256"],
        "adapter_sha256": parts[8], "adapter_config_sha256": parts[9],
        "context_window_tokens": context_window_tokens, "output_token_limit": output_token_limit,
    }
    runtime_payload = {
        "schema": "owned-production-runtime-v1", "identity": identity,
        "training_status_sha256": parts[7], "packages": installed,
        "gpu_name": gpu_name, "gpu_memory_bytes": gpu_memory,
        "compute_capability": capability, "visible_device_count": device_count,
        "cuda_version": cuda_version,
    }
    identity["runtime_sha256"] = hashlib.sha256(json.dumps(
        runtime_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return identity


def inspect_owned_production_runtime(
    model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir, *,
    manifest_path, expected_adapter_sha256: str, expected_adapter_config_sha256: str,
    context_window_tokens: int, output_token_limit: int,
    recipe: str = owned_training.T4_RECIPE,
):
    """Form actual file/environment pins for review, without model loading or admission."""
    parts = _prepare_candidate_files(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir,
        manifest_path=manifest_path, expected_adapter_sha256=expected_adapter_sha256,
        expected_adapter_config_sha256=expected_adapter_config_sha256, recipe=recipe,
    )
    return _production_runtime_identity(parts, context_window_tokens, output_token_limit)


def _require_model_admission(admission):
    from lumenis.system.security.owned_model_admission import OwnedModelAdmissionVerifier
    from .owned_service import _verify_admission

    if type(admission) is not OwnedModelAdmissionVerifier:
        raise OwnedInferenceBlocked("OWNED_MODEL_ADMISSION_VERIFIER_REQUIRED")
    if getattr(admission.recheck, "__func__", None) is not OwnedModelAdmissionVerifier.recheck:
        raise OwnedInferenceBlocked("OWNED_MODEL_ADMISSION_VERIFIER_IMPLEMENTATION_CHANGED")
    _verify_admission(admission)
    if admission.request.action not in {"admit", "rollback"}:
        raise OwnedInferenceBlocked("OWNED_MODEL_EXECUTION_NOT_ADMITTED")


def load_owned_production_runtime(
    model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir, *,
    manifest_path, expected_adapter_sha256: str, expected_adapter_config_sha256: str,
    admission, source_validator, source_dependency_paths=(),
    recipe: str = owned_training.T4_RECIPE,
):
    """Retired CUDA-trained serving path; keep its old signature fail-closed."""
    raise OwnedInferenceBlocked("TRAINED_CUDA_RUNTIME_WITHDRAWN_BY_PO")


def _require_source_validator(admission, validator, dependency_paths):
    from agent_capability.formation import implementation_identity

    if not callable(validator):
        raise OwnedInferenceBlocked("OWNED_SOURCE_VALIDATOR_REQUIRED")
    try:
        actual = implementation_identity(validator, dependency_paths)
    except Exception as exc:
        raise OwnedInferenceBlocked("OWNED_SOURCE_VALIDATOR_IDENTITY_UNAVAILABLE") from exc
    if actual != admission.request.source_validator_sha256:
        raise OwnedInferenceBlocked("OWNED_SOURCE_VALIDATOR_IDENTITY_MISMATCH")


class OwnedProductionRuntime:
    """Server-retained runtime; offline candidates and arbitrary callables cannot substitute."""

    def __init__(self, kernel, parts, identity, admission, source_validator,
                 source_dependency_paths=(), *, _issuer=None):
        if (_issuer is not _PRODUCTION_RUNTIME_ISSUER
                or type(kernel) is not _LocalTextKernel):
            raise OwnedInferenceBlocked("OWNED_PRODUCTION_FACTORY_REQUIRED")
        self._kernel, self._parts, self._identity, self._admission = (
            kernel, parts, dict(identity), admission,
        )
        self._lock = threading.RLock()
        self._source_validator = source_validator
        self._source_dependency_paths = tuple(source_dependency_paths)
        self._model_handle, self._tokenizer_handle, self._torch_handle = (
            kernel._model, kernel._tokenizer, kernel._torch,
        )
        self._kernel_handler = kernel._generate.__func__
        self._formatter_handle = type(self)._request_prompt

    def identity(self):
        with self._lock:
            if (self._kernel._model is not self._model_handle
                    or self._kernel._tokenizer is not self._tokenizer_handle
                    or self._kernel._torch is not self._torch_handle
                    or getattr(self._kernel._generate, "__func__", None) is not self._kernel_handler
                    or type(self)._request_prompt is not self._formatter_handle
                    or _production_executor_identity(self.generate) != self._identity["executor_sha256"]):
                raise OwnedInferenceBlocked("OWNED_RUNTIME_HANDLE_CHANGED")
            _require_model_admission(self._admission)
            _require_source_validator(
                self._admission, self._source_validator, self._source_dependency_paths,
            )
            self._kernel._verify_small_artifacts()
            current = _production_runtime_identity(
                self._parts, self._identity["context_window_tokens"],
                self._identity["output_token_limit"],
            )
            if current != self._identity:
                raise OwnedInferenceBlocked("OWNED_RUNTIME_IDENTITY_CHANGED")
            return dict(current)

    def _verify_source(self, request):
        from .owned_service import OwnedServiceBlocked, _validate_source_decision

        _require_source_validator(
            self._admission, self._source_validator, self._source_dependency_paths,
        )
        try:
            decision = self._source_validator(request)
        except Exception as exc:
            raise OwnedInferenceBlocked("OWNED_SOURCE_VALIDATION_UNAVAILABLE") from exc
        try:
            _validate_source_decision(decision, request)
        except OwnedServiceBlocked as exc:
            raise OwnedInferenceBlocked("OWNED_SOURCE_USE_NOT_AUTHORIZED") from exc
        _require_source_validator(
            self._admission, self._source_validator, self._source_dependency_paths,
        )

    @staticmethod
    def _request_prompt(request):
        return (
            f"<|start|>system<|message|>{request.system_prompt}<|end|>"
            f"<|start|>user<|message|>{request.user_payload}<|end|>"
            "<|start|>assistant<|channel|>final<|message|>"
        )

    def measure_request(self, request):
        """Exact loaded-tokenizer count, with no generation or model loading."""
        from .owned_service import (OwnedServiceRequest, validate_owned_service_request,
            _request_matches_admission, owned_service_request_digest)
        if type(request) is not OwnedServiceRequest:
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_REQUIRED")
        validate_owned_service_request(request)
        _request_matches_admission(request, self._admission.request, self._admission.public_identity)
        if any(_HARMONY_CONTROL.search(value) for value in (request.system_prompt, request.user_payload)):
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_MISMATCH")
        with self._lock:
            identity = self.identity()
            self._verify_source(request)
            prompt = self._request_prompt(request)
            with owned_training._offline_hf(self._kernel._base_recipe):
                encoded = self._tokenizer_handle(prompt, return_tensors="pt", add_special_tokens=False, truncation=False)
                count = int(encoded["input_ids"].shape[1])
            if count < 0 or self.identity() != identity:
                raise OwnedInferenceBlocked("OWNED_RUNTIME_IDENTITY_CHANGED")
            self._verify_source(request)
            return {"prompt_tokens": count, "output_tokens_reserved": request.max_output_tokens,
                "context_window_tokens": identity["context_window_tokens"],
                "output_token_limit": identity["output_token_limit"],
                "fits": count + request.max_output_tokens <= identity["context_window_tokens"],
                "request_sha256": owned_service_request_digest(request),
                "runtime_sha256": identity["runtime_sha256"],
                "tokenizer_identity": identity["runtime_sha256"],
                "formatter_sha256": identity["executor_sha256"],
                "count_method": "loaded_runtime_tokenizer", "generation_performed": False}

    def generate(self, request, *, is_cancelled=None):
        from dataclasses import asdict
        from .owned_service import OwnedServiceRequest, validate_owned_service_request

        if type(request) is not OwnedServiceRequest:
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_REQUIRED")
        validate_owned_service_request(request)
        policy = self._admission.request
        if (request.actor_ref != self._admission.public_identity.get("caller")
                or request.domain_id != policy.domain_id or request.scope not in policy.scopes
                or request.operation not in policy.allowed_operations
                or request.source_use_policy_version != policy.source_use_version
                or request.source_use_policy_sha256 != policy.source_use_sha256
                or type(request.max_output_tokens) is not int
                or not 1 <= request.max_output_tokens <= policy.output_token_limit
                or any(type(value) is not str or not value.strip()
                       or _HARMONY_CONTROL.search(value)
                       for value in (request.system_prompt, request.user_payload))
                or (is_cancelled is not None and not callable(is_cancelled))):
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_MISMATCH")
        request_sha = hashlib.sha256(json.dumps(
            asdict(request), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")).hexdigest()
        prompt = self._request_prompt(request)

        def must_stop():
            if is_cancelled is not None:
                cancelled = is_cancelled()
                if type(cancelled) is not bool:
                    raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCEL_CHECK_INVALID")
                if cancelled:
                    return True
            return self._admission.recheck().allowed is not True

        with self._lock:
            identity = self.identity()
            self._verify_source(request)
            response = self._kernel._generate(
                prompt, request.max_output_tokens, is_cancelled=must_stop,
                context_window_tokens=policy.context_window_tokens,
            )
            self.identity()
            self._verify_source(request)
            return {
                **response, "text": response["generated_text"], **identity,
                "request_sha256": request_sha, "request_digest": request_sha,
                "total_tokens": response["prompt_tokens"] + response["completion_tokens"],
                "run_id": "owned-" + uuid.uuid4().hex,
            }
    __slots__ = (
        "_kernel", "_parts", "_identity", "_admission", "_lock",
        "_source_validator", "_source_dependency_paths", "_model_handle",
        "_tokenizer_handle", "_torch_handle", "_kernel_handler", "_formatter_handle",
    )


def _pretrained_request_type():
    from .owned_service import OwnedPretrainedInferenceAdmissionRequest

    return OwnedPretrainedInferenceAdmissionRequest


def _pretrained_cpu_packages():
    from importlib.metadata import PackageNotFoundError, version

    try:
        packages = tuple((name, version(name)) for name in _PRETRAINED_PACKAGE_NAMES)
    except PackageNotFoundError as exc:
        raise OwnedInferenceBlocked("PRETRAINED_CPU_DEPENDENCIES_UNAVAILABLE") from exc
    if any("cuda" in value.lower() or "+cu" in value.lower() for _name, value in packages):
        raise OwnedInferenceBlocked("PRETRAINED_CPU_BUILD_REQUIRED")
    return packages


def _pretrained_package_lock_sha256(packages):
    return hashlib.sha256(json.dumps(
        [list(item) for item in packages], sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _pretrained_code_identities():
    from agent_capability.formation import implementation_identity
    from . import owned_service
    from lumenis.system.security import owned_model_admission

    dependencies = (__file__, owned_service.__file__, owned_model_admission.__file__)
    return {
        "runtime_build_sha256": implementation_identity(_load_pretrained_cpu_kernel, dependencies),
        "executor_sha256": implementation_identity(OwnedPretrainedProductionRuntime.generate, dependencies),
    }


def _pretrained_artifact_root(request, artifact_root):
    from .owned_service import validate_pretrained_inference_admission_request

    validate_pretrained_inference_admission_request(request)
    try:
        raw = os.fspath(artifact_root)
        path = Path(raw)
        if (type(raw) is not str or not path.is_absolute() or path.is_symlink()
                or raw.startswith(("\\\\", "//")) or "://" in raw):
            raise ValueError("absolute non-network artifact path required")
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("symlinked artifact path")
        root = path.resolve(strict=True)
        if not root.is_dir() or str(root).startswith(("\\\\", "//")):
            raise ValueError("local artifact directory required")
    except (OSError, TypeError, ValueError) as exc:
        raise OwnedInferenceBlocked("PRETRAINED_LOCAL_ARTIFACT_PATH_INVALID") from exc

    expected = {name: (size, digest) for name, size, digest in request.artifact_files}
    found = {}
    try:
        for current, directories, filenames in os.walk(root, followlinks=False):
            current_path = Path(current)
            if any((current_path / name).is_symlink() for name in directories):
                raise OwnedInferenceBlocked("PRETRAINED_LOCAL_ARTIFACT_SYMLINKED")
            for filename in filenames:
                item = current_path / filename
                if item.is_symlink() or not item.is_file():
                    raise OwnedInferenceBlocked("PRETRAINED_LOCAL_ARTIFACT_FILE_INVALID")
                relative = item.relative_to(root).as_posix()
                found[relative] = item
        if set(found) != set(expected):
            raise OwnedInferenceBlocked("PRETRAINED_LOCAL_ARTIFACT_FILE_SET_MISMATCH")
        total_bytes = 0
        for relative, item in found.items():
            size, expected_sha = expected[relative]
            if item.stat().st_size != size or owned_training._sha256(item) != expected_sha:
                raise OwnedInferenceBlocked("PRETRAINED_LOCAL_ARTIFACT_HASH_MISMATCH")
            total_bytes += size
    except OwnedInferenceBlocked:
        raise
    except (OSError, ValueError) as exc:
        raise OwnedInferenceBlocked("PRETRAINED_LOCAL_ARTIFACT_READ_FAILED") from exc
    return root, found, total_bytes


def _pretrained_runtime_payload(request, packages):
    from .owned_service import pretrained_artifact_identity_sha256

    return {
        "schema": "owned-pretrained-cpu-runtime-v1",
        "manifest_sha256": request.manifest_sha256,
        "artifact_identity_sha256": pretrained_artifact_identity_sha256(request),
        "runtime_build_sha256": request.runtime_build_sha256,
        "executor_sha256": request.executor_sha256,
        "runtime_package_lock_sha256": request.runtime_package_lock_sha256,
        "packages": [list(item) for item in packages],
        "device_kind": "cpu",
        "limits": {
            "context_window_tokens": request.context_window_tokens,
            "output_token_limit": request.output_token_limit,
            "cpu_threads": request.cpu_threads,
            "memory_limit_bytes": request.memory_limit_bytes,
            "generation_timeout_seconds": request.generation_timeout_seconds,
            "max_concurrent_requests": request.max_concurrent_requests,
        },
    }


def derive_pretrained_inference_runtime_pins(request, artifact_root):
    """Derive exact local CPU/code pins; this performs no model load or generation."""
    from dataclasses import replace
    from .owned_service import (
        OwnedServiceBlocked, pretrained_inference_manifest_sha256,
        validate_pretrained_inference_admission_request,
    )

    if type(request) is not _pretrained_request_type():
        raise OwnedInferenceBlocked("PRETRAINED_ADMISSION_TYPE_INVALID")
    _root, _files, total_bytes = _pretrained_artifact_root(request, artifact_root)
    packages = _pretrained_cpu_packages()
    identities = _pretrained_code_identities()
    package_lock = _pretrained_package_lock_sha256(packages)
    updated = replace(
        request, runtime_packages=packages,
        runtime_version=dict(packages)["transformers"],
        runtime_build_sha256=identities["runtime_build_sha256"],
        executor_sha256=identities["executor_sha256"],
        runtime_package_lock_sha256=package_lock,
        runtime_sha256="0" * 64, manifest_sha256="0" * 64,
    )
    manifest_sha = pretrained_inference_manifest_sha256(updated)
    updated = replace(updated, manifest_sha256=manifest_sha)
    try:
        validate_pretrained_inference_admission_request(updated)
    except OwnedServiceBlocked as exc:
        raise OwnedInferenceBlocked(exc.code) from exc
    runtime_sha = hashlib.sha256(json.dumps(
        _pretrained_runtime_payload(updated, packages), sort_keys=True,
        separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return replace(updated, runtime_sha256=runtime_sha)


def _current_process_rss_bytes():
    """Read resident memory using only platform standard libraries."""
    import sys

    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class _Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _Counters()
            counters.cb = ctypes.sizeof(counters)
            psapi = ctypes.WinDLL("psapi")
            kernel32 = ctypes.WinDLL("kernel32")
            if not psapi.GetProcessMemoryInfo(
                    kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                raise OSError("process memory read failed")
            return int(counters.WorkingSetSize)
        try:
            with open("/proc/self/statm", "r", encoding="ascii") as stream:
                fields = stream.read(128).split()
            if len(fields) < 2:
                raise OSError("process memory read failed")
            return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE"))
        except OSError:
            import resource

            maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            # macOS reports bytes; the BSD/Linux interfaces report KiB.
            return maximum if sys.platform == "darwin" else maximum * 1024
    except Exception as exc:
        raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_OBSERVATION_UNAVAILABLE") from exc


def _pretrained_runtime_identity(request, packages):
    from .owned_service import (
        OwnedServiceBlocked, pretrained_artifact_identity_sha256,
        validate_pretrained_inference_admission_request,
    )

    try:
        validate_pretrained_inference_admission_request(request)
        identities = _pretrained_code_identities()
        lock_sha = _pretrained_package_lock_sha256(packages)
        if (request.runtime_packages != packages
                or request.runtime_version != dict(packages).get("transformers")
                or request.runtime_package_lock_sha256 != lock_sha
                or request.runtime_build_sha256 != identities["runtime_build_sha256"]
                or request.executor_sha256 != identities["executor_sha256"]):
            raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_PIN_MISMATCH")
        runtime_sha = hashlib.sha256(json.dumps(
            _pretrained_runtime_payload(request, packages), sort_keys=True,
            separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")).hexdigest()
        if request.runtime_sha256 != runtime_sha:
            raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_PIN_MISMATCH")
        return {
            "schema_version": 2, "artifact_kind": "PRETRAINED_INFERENCE",
            "runtime_sha256": runtime_sha, "executor_sha256": identities["executor_sha256"],
            "artifact_identity_sha256": pretrained_artifact_identity_sha256(request),
            "model_id": request.model_id, "model_revision": request.model_revision,
            "recipe": f"{request.runtime_engine}:{request.quantization_format}",
            "manifest_sha256": request.manifest_sha256,
            "runtime_build_sha256": identities["runtime_build_sha256"],
            "runtime_package_lock_sha256": lock_sha,
            "tokenizer_sha256": request.tokenizer_sha256,
            "chat_template_sha256": request.chat_template_sha256,
            "context_window_tokens": request.context_window_tokens,
            "output_token_limit": request.output_token_limit,
            "cpu_threads": request.cpu_threads,
            "memory_limit_bytes": request.memory_limit_bytes,
            "generation_timeout_seconds": request.generation_timeout_seconds,
            "max_concurrent_requests": request.max_concurrent_requests,
        }
    except OwnedServiceBlocked as exc:
        raise OwnedInferenceBlocked(exc.code) from exc


def inspect_pretrained_inference_runtime(request, artifact_root):
    """Verify existing local files and exact CPU/runtime pins without loading weights."""
    if type(request) is not _pretrained_request_type():
        raise OwnedInferenceBlocked("PRETRAINED_ADMISSION_TYPE_INVALID")
    _root, _files, total_bytes = _pretrained_artifact_root(request, artifact_root)
    packages = _pretrained_cpu_packages()
    # Reserve room for a state dict and tokenizer/runtime overhead before an
    # approved process can load any weight shard.
    if (total_bytes * 2 + _PRETRAINED_MEMORY_RESERVE_BYTES
            > request.memory_limit_bytes):
        raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_INSUFFICIENT")
    identity = _pretrained_runtime_identity(request, packages)
    return {
        **identity, "device_kind": "cpu", "weights_loaded": False,
        "generation_performed": False, "artifact_bytes": total_bytes,
        "runtime_packages": [list(item) for item in packages],
    }


def _load_pretrained_cpu_kernel(request, artifact_root, expected_identity):
    root, files, total_bytes = _pretrained_artifact_root(request, artifact_root)
    memory_limit = request.memory_limit_bytes
    if total_bytes * 2 + _PRETRAINED_MEMORY_RESERVE_BYTES > memory_limit:
        raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_INSUFFICIENT")
    if _current_process_rss_bytes() + total_bytes * 2 + _PRETRAINED_MEMORY_RESERVE_BYTES > memory_limit:
        raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_INSUFFICIENT")
    model = None
    tokenizer = None
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if getattr(torch.version, "cuda", None) is not None:
            raise OwnedInferenceBlocked("PRETRAINED_CPU_BUILD_REQUIRED")
        if getattr(getattr(torch.backends, "cuda", None), "is_built", lambda: False)():
            raise OwnedInferenceBlocked("PRETRAINED_CPU_BUILD_REQUIRED")
        tokenizer = AutoTokenizer.from_pretrained(
            str(root), local_files_only=True, trust_remote_code=False,
            token=False, use_fast=True,
        )
        template_bytes = files[request.chat_template_file].read_bytes()
        try:
            chat_template = template_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OwnedInferenceBlocked("PRETRAINED_CHAT_TEMPLATE_INVALID") from exc
        if not chat_template.strip():
            raise OwnedInferenceBlocked("PRETRAINED_CHAT_TEMPLATE_INVALID")
        tokenizer.chat_template = chat_template
        model = AutoModelForCausalLM.from_pretrained(
            str(root), local_files_only=True, trust_remote_code=False,
            token=False, use_safetensors=True, low_cpu_mem_usage=False,
            torch_dtype=torch.float32,
        )
        config_path = Path(str(getattr(model.config, "_name_or_path", "")))
        if config_path.resolve(strict=True) != root:
            raise OwnedInferenceBlocked("PRETRAINED_LOADER_CHANGED_PINNED_MODEL_PATH")
        if any(parameter.device.type != "cpu" for parameter in model.parameters()):
            raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_DEVICE_MISMATCH")
        model.eval()
        loaded_rss = _current_process_rss_bytes()
        if loaded_rss > memory_limit:
            raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_EXCEEDED")
    except OwnedInferenceBlocked:
        model = None
        tokenizer = None
        gc.collect()
        raise
    except Exception as exc:
        model = None
        tokenizer = None
        gc.collect()
        raise OwnedInferenceBlocked("PRETRAINED_CPU_LOCAL_LOAD_FAILED") from exc

    kernel = _PretrainedCPUTextKernel(model, tokenizer, torch, request, root, expected_identity)
    model = None
    tokenizer = None
    try:
        root_after, _files_after, bytes_after = _pretrained_artifact_root(request, artifact_root)
        packages_after = _pretrained_cpu_packages()
        if (root_after != root or bytes_after != total_bytes
                or _pretrained_runtime_identity(request, packages_after) != expected_identity):
            raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_CHANGED_DURING_LOAD")
        return kernel
    except Exception:
        kernel.close()
        raise


class _PretrainedCPUTextKernel:
    __slots__ = ("artifact_root", "identity", "model", "request", "tokenizer", "torch")

    def __init__(self, model, tokenizer, torch, request, artifact_root, identity):
        self.model, self.tokenizer, self.torch = model, tokenizer, torch
        self.request, self.artifact_root, self.identity = request, artifact_root, dict(identity)

    def close(self):
        """Drop model, tokenizer and request handles after the owning slot stops."""
        if self.model is None and self.tokenizer is None and self.torch is None:
            return
        self.model = None
        self.tokenizer = None
        self.torch = None
        self.request = None
        self.artifact_root = None
        self.identity = {}
        gc.collect()

    def prompt(self, request):
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_payload},
        ]
        try:
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
        except Exception as exc:
            raise OwnedInferenceBlocked("PRETRAINED_CHAT_TEMPLATE_RENDER_FAILED") from exc
        if type(prompt) is not str or not prompt.strip():
            raise OwnedInferenceBlocked("PRETRAINED_CHAT_TEMPLATE_RENDER_FAILED")
        return prompt

    def count_tokens(self, prompt):
        try:
            encoded = self.tokenizer(
                prompt, return_tensors="pt", add_special_tokens=False, truncation=False,
            )
            return encoded, int(encoded["input_ids"].shape[1])
        except Exception as exc:
            raise OwnedInferenceBlocked("PRETRAINED_TOKENIZER_UNAVAILABLE") from exc

    def generate(self, prompt, max_new_tokens, *, is_cancelled, memory_limit_bytes):
        from transformers import StoppingCriteria, StoppingCriteriaList

        start = time.monotonic()
        deadline = start + self.request.generation_timeout_seconds
        stop_reason = {"value": None, "steps": 0}

        class _BoundedStop(StoppingCriteria):
            def __call__(_self, input_ids, scores, **kwargs):
                stop_reason["steps"] += 1
                if is_cancelled():
                    stop_reason["value"] = "cancelled"
                    return True
                if time.monotonic() >= deadline:
                    stop_reason["value"] = "timeout"
                    return True
                if stop_reason["steps"] % 8 == 0 and _current_process_rss_bytes() > memory_limit_bytes:
                    stop_reason["value"] = "memory"
                    return True
                return False

        encoded, input_tokens = self.count_tokens(prompt)
        if input_tokens + max_new_tokens > self.request.context_window_tokens:
            raise OwnedInferenceBlocked("PRETRAINED_CONTEXT_BUDGET_EXCEEDED")
        eos = self.tokenizer.eos_token_id
        if type(eos) is not int or eos < 0:
            raise OwnedInferenceBlocked("PRETRAINED_EOS_TOKEN_UNAVAILABLE")
        with _TORCH_CPU_THREADS_LOCK:
            previous_threads = self.torch.get_num_threads()
            try:
                self.torch.set_num_threads(self.request.cpu_threads)
                with self.torch.inference_mode():
                    generated = self.model.generate(
                        **encoded, max_new_tokens=max_new_tokens, do_sample=False,
                        eos_token_id=eos,
                        pad_token_id=(self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else eos),
                        use_cache=True, stopping_criteria=StoppingCriteriaList([_BoundedStop()]),
                    )
            except OwnedInferenceBlocked:
                raise
            except Exception as exc:
                raise OwnedInferenceBlocked("PRETRAINED_CPU_GENERATION_FAILED") from exc
            finally:
                try:
                    self.torch.set_num_threads(previous_threads)
                except (RuntimeError, TypeError, ValueError) as exc:
                    raise OwnedInferenceBlocked("PRETRAINED_CPU_THREAD_RESTORE_FAILED") from exc
        reason = stop_reason["value"]
        if reason == "cancelled":
            raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCELLED")
        if reason == "timeout":
            raise OwnedInferenceBlocked("PRETRAINED_CPU_GENERATION_TIMEOUT")
        if reason == "memory":
            raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_EXCEEDED")
        if time.monotonic() >= deadline:
            raise OwnedInferenceBlocked("PRETRAINED_CPU_GENERATION_TIMEOUT")
        if _current_process_rss_bytes() > memory_limit_bytes:
            raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_EXCEEDED")
        sequences = getattr(generated, "sequences", generated)
        token_ids = sequences[0][input_tokens:]
        if hasattr(token_ids, "tolist"):
            token_ids = token_ids.tolist()
        if not token_ids or token_ids[-1] != eos:
            raise OwnedInferenceBlocked("PRETRAINED_CPU_OUTPUT_INCOMPLETE")
        text = self.tokenizer.decode(token_ids[:-1], skip_special_tokens=True).strip()
        if not text:
            raise OwnedInferenceBlocked("PRETRAINED_CPU_OUTPUT_EMPTY")
        if _HARMONY_CONTROL.search(text):
            raise OwnedInferenceBlocked("PRETRAINED_CPU_OUTPUT_CONTROL_TOKEN_INVALID")
        return {
            "generated_text": "<|start|>assistant<|channel|>final<|message|>" + text + "<|return|>",
            "finish_reason": "return", "termination_token": "<|return|>",
            "final_channel_prefill": True,
            "prompt_tokens": input_tokens, "completion_tokens": len(token_ids),
            "total_tokens": input_tokens + len(token_ids),
        }


_PRETRAINED_RUNTIME_ISSUER = object()


def _require_pretrained_source_validator(admission, validator, dependency_paths):
    _require_source_validator(admission, validator, dependency_paths)


def load_owned_pretrained_production_runtime(
    request, artifact_root, *, admission, source_validator, source_dependency_paths=(),
):
    """Load one exact, approved local pretrained model on CPU; never downloads or discovers."""
    from .owned_service import OwnedServiceBlocked, validate_pretrained_inference_admission_request

    if (type(request) is not _pretrained_request_type()
            or type(getattr(admission, "request", None)) is not _pretrained_request_type()
            or admission.request != request):
        raise OwnedInferenceBlocked("PRETRAINED_ADMISSION_REQUEST_MISMATCH")
    _require_model_admission(admission)
    _require_pretrained_source_validator(admission, source_validator, source_dependency_paths)
    try:
        validate_pretrained_inference_admission_request(request)
    except OwnedServiceBlocked as exc:
        raise OwnedInferenceBlocked(exc.code) from exc
    _root, _files, total_bytes = _pretrained_artifact_root(request, artifact_root)
    packages = _pretrained_cpu_packages()
    if total_bytes * 2 + _PRETRAINED_MEMORY_RESERVE_BYTES > request.memory_limit_bytes:
        raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_INSUFFICIENT")
    if _current_process_rss_bytes() + total_bytes * 2 + _PRETRAINED_MEMORY_RESERVE_BYTES > request.memory_limit_bytes:
        raise OwnedInferenceBlocked("PRETRAINED_CPU_MEMORY_BUDGET_INSUFFICIENT")
    identity = _pretrained_runtime_identity(request, packages)
    _require_model_admission(admission)
    kernel = _load_pretrained_cpu_kernel(request, artifact_root, identity)
    try:
        _require_model_admission(admission)
        _require_pretrained_source_validator(admission, source_validator, source_dependency_paths)
        return OwnedPretrainedProductionRuntime(
            kernel, identity, admission, source_validator, source_dependency_paths,
            _issuer=_PRETRAINED_RUNTIME_ISSUER,
        )
    except Exception:
        kernel.close()
        raise


class OwnedPretrainedProductionRuntime:
    """Private CPU-only production executor for an exact v2 admission."""

    __slots__ = (
        "_admission", "_closed", "_format_handler", "_generate_handler",
        "_identity", "_kernel", "_lock", "_model_handle", "_semaphore",
        "_source_dependency_paths", "_source_validator", "_tokenizer_handle",
        "_torch_handle", "_unload_state",
    )

    def __init__(self, kernel, identity, admission, source_validator,
                 source_dependency_paths=(), *, _issuer=None):
        if (_issuer is not _PRETRAINED_RUNTIME_ISSUER
                or type(kernel) is not _PretrainedCPUTextKernel):
            raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_FACTORY_REQUIRED")
        self._kernel, self._identity, self._admission = kernel, dict(identity), admission
        self._lock = threading.RLock()
        self._source_validator = source_validator
        self._source_dependency_paths = tuple(source_dependency_paths)
        self._model_handle, self._tokenizer_handle, self._torch_handle = (
            kernel.model, kernel.tokenizer, kernel.torch,
        )
        self._generate_handler = type(kernel).generate
        self._format_handler = type(kernel).prompt
        self._semaphore = threading.BoundedSemaphore(admission.request.max_concurrent_requests)
        self._closed = False
        self._unload_state = None

    def close(self):
        """Unload the exact CPU model after its service slot has been removed."""
        with self._lock:
            if self._closed:
                state = self._unload_state or "UNLOAD_FAILED"
                return {"ok": state == "CLOSED", "state": state, "already_closed": True}
            self._closed = True
            kernel = self._kernel
            self._kernel = None
            self._identity = {}
            self._admission = None
            self._source_validator = None
            self._source_dependency_paths = ()
            self._model_handle = None
            self._tokenizer_handle = None
            self._torch_handle = None
            self._generate_handler = None
            self._format_handler = None
            try:
                if kernel is not None:
                    kernel.close()
                self._unload_state = "CLOSED"
            except (RuntimeError, TypeError, ValueError):
                self._unload_state = "UNLOAD_FAILED"
            finally:
                gc.collect()
        return {"ok": self._unload_state == "CLOSED", "state": self._unload_state,
                "already_closed": False}

    def identity(self):
        with self._lock:
            if (self._closed or self._kernel is None
                    or self._kernel.model is not self._model_handle
                    or self._kernel.tokenizer is not self._tokenizer_handle
                    or self._kernel.torch is not self._torch_handle
                    or type(self._kernel).generate is not self._generate_handler
                    or type(self._kernel).prompt is not self._format_handler
                    or _pretrained_runtime_identity(
                        self._admission.request, _pretrained_cpu_packages(),
                    ) != self._identity):
                raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_HANDLE_CHANGED")
            _require_model_admission(self._admission)
            _require_pretrained_source_validator(
                self._admission, self._source_validator, self._source_dependency_paths,
            )
            return dict(self._identity)

    def _verify_source(self, request):
        from .owned_service import OwnedServiceBlocked, _validate_source_decision

        _require_pretrained_source_validator(
            self._admission, self._source_validator, self._source_dependency_paths,
        )
        try:
            decision = self._source_validator(request)
            _validate_source_decision(decision, request)
        except Exception as exc:
            if isinstance(exc, OwnedServiceBlocked):
                raise OwnedInferenceBlocked("OWNED_SOURCE_USE_NOT_AUTHORIZED") from exc
            raise OwnedInferenceBlocked("OWNED_SOURCE_VALIDATION_UNAVAILABLE") from exc
        _require_pretrained_source_validator(
            self._admission, self._source_validator, self._source_dependency_paths,
        )

    def measure_request(self, request):
        from .owned_service import (
            OwnedServiceRequest, owned_service_request_digest,
            _request_matches_admission, validate_owned_service_request,
        )

        if type(request) is not OwnedServiceRequest:
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_REQUIRED")
        validate_owned_service_request(request)
        with self._lock:
            if self._closed or self._kernel is None or self._admission is None:
                raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_CLOSED")
            policy = self._admission.request
            _request_matches_admission(request, policy, self._admission.public_identity)
            if policy.action not in {"admit", "rollback"}:
                raise OwnedInferenceBlocked("OWNED_MODEL_EXECUTION_NOT_ADMITTED")
            identity = self.identity()
            self._verify_source(request)
            prompt = self._kernel.prompt(request)
            _encoded, count = self._kernel.count_tokens(prompt)
            if self.identity() != identity:
                raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_IDENTITY_CHANGED")
            self._verify_source(request)
            return {
                "prompt_tokens": count, "output_tokens_reserved": request.max_output_tokens,
                "context_window_tokens": identity["context_window_tokens"],
                "output_token_limit": identity["output_token_limit"],
                "fits": count + request.max_output_tokens <= identity["context_window_tokens"],
                "request_sha256": owned_service_request_digest(request),
                "runtime_sha256": identity["runtime_sha256"],
                "tokenizer_identity": identity["runtime_sha256"],
                "formatter_sha256": identity["executor_sha256"],
                "count_method": "loaded_runtime_tokenizer", "generation_performed": False,
            }

    def generate(self, request, *, is_cancelled=None):
        from dataclasses import asdict
        from .owned_service import (
            OwnedServiceRequest, _request_matches_admission,
            validate_owned_service_request,
        )

        if type(request) is not OwnedServiceRequest:
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_REQUIRED")
        validate_owned_service_request(request)
        if is_cancelled is not None and not callable(is_cancelled):
            raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_MISMATCH")
        if not self._semaphore.acquire(blocking=False):
            raise OwnedInferenceBlocked("PRETRAINED_CPU_RUNTIME_BUSY")
        try:
            request_sha = hashlib.sha256(json.dumps(
                asdict(request), sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")).hexdigest()
            with self._lock:
                if self._closed or self._kernel is None or self._admission is None:
                    raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_CLOSED")
                policy = self._admission.request
                _request_matches_admission(request, policy, self._admission.public_identity)
                if (policy.action not in {"admit", "rollback"}
                        or request.max_output_tokens > policy.output_token_limit
                        or _HARMONY_CONTROL.search(request.system_prompt)
                        or _HARMONY_CONTROL.search(request.user_payload)):
                    raise OwnedInferenceBlocked("OWNED_SERVICE_REQUEST_MISMATCH")
                identity = self.identity()
                self._verify_source(request)
                prompt = self._kernel.prompt(request)
                encoded, prompt_tokens = self._kernel.count_tokens(prompt)
                if prompt_tokens + request.max_output_tokens > policy.context_window_tokens:
                    raise OwnedInferenceBlocked("PRETRAINED_CONTEXT_BUDGET_EXCEEDED")

                stop_cause = {"code": None}

                def must_stop():
                    if is_cancelled is not None:
                        value = is_cancelled()
                        if type(value) is not bool:
                            raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCEL_CHECK_INVALID")
                        if value:
                            stop_cause["code"] = "OWNED_INFERENCE_CANCELLED"
                            return True
                    try:
                        decision = self._admission.recheck()
                        if decision.allowed is not True:
                            stop_cause["code"] = "OWNED_MODEL_ADMISSION_REVOKED"
                            return True
                        return False
                    except Exception:
                        stop_cause["code"] = "OWNED_MODEL_ADMISSION_RECHECK_FAILED"
                        return True

                try:
                    raw = self._kernel.generate(
                        prompt, request.max_output_tokens, is_cancelled=must_stop,
                        memory_limit_bytes=policy.memory_limit_bytes,
                    )
                except OwnedInferenceBlocked:
                    if stop_cause["code"] is not None:
                        raise OwnedInferenceBlocked(stop_cause["code"])
                    raise
                if is_cancelled is not None and is_cancelled():
                    raise OwnedInferenceBlocked("OWNED_INFERENCE_CANCELLED")
                if self._admission.recheck().allowed is not True:
                    raise OwnedInferenceBlocked("OWNED_MODEL_ADMISSION_REVOKED")
                if self.identity() != identity:
                    raise OwnedInferenceBlocked("PRETRAINED_RUNTIME_IDENTITY_CHANGED")
                self._verify_source(request)
                return {
                    **raw, **identity,
                    "text": raw["generated_text"], "request_sha256": request_sha,
                    "request_digest": request_sha,
                    "total_tokens": raw["prompt_tokens"] + raw["completion_tokens"],
                    "device_kind": "cpu", "run_id": "owned-" + uuid.uuid4().hex,
                }
        finally:
            self._semaphore.release()
