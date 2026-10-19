"""Hash-pinned local kernels and separately admitted SYSTEM inference runtimes."""
from __future__ import annotations

import hashlib
import json
import re
import threading
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
    base_recipe = preflight["base_training_recipe"]
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
    """Load the common local kernel only after exact, fresh production admission."""
    _require_model_admission(admission)
    _require_source_validator(admission, source_validator, source_dependency_paths)
    parts = _prepare_candidate_files(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir,
        manifest_path=manifest_path, expected_adapter_sha256=expected_adapter_sha256,
        expected_adapter_config_sha256=expected_adapter_config_sha256, recipe=recipe,
    )
    identity = _production_runtime_identity(
        parts, admission.request.context_window_tokens, admission.request.output_token_limit,
    )
    if any(getattr(admission.request, key, None) != value for key, value in identity.items()):
        raise OwnedInferenceBlocked("OWNED_RUNTIME_ADMISSION_IDENTITY_MISMATCH")
    preflight = parts[5]
    if (admission.request.domain_id != preflight["domain_id"]
            or not set(admission.request.scopes).issubset(set(preflight["scopes"]))):
        raise OwnedInferenceBlocked("OWNED_RUNTIME_ADMISSION_SCOPE_MISMATCH")
    _require_model_admission(admission)
    kernel = _load_local_kernel(parts)
    _require_model_admission(admission)
    # Revalidate the complete manifested base after the loader has read it.
    # Small adapter/data checks alone cannot detect a base changed during load.
    parts_after = _prepare_candidate_files(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, candidate_output_dir,
        manifest_path=manifest_path, expected_adapter_sha256=expected_adapter_sha256,
        expected_adapter_config_sha256=expected_adapter_config_sha256, recipe=recipe,
    )
    if parts_after[6:10] != parts[6:10]:
        raise OwnedInferenceBlocked("OWNED_RUNTIME_CHANGED_DURING_LOAD")
    if identity != _production_runtime_identity(
        parts, admission.request.context_window_tokens, admission.request.output_token_limit,
    ):
        raise OwnedInferenceBlocked("OWNED_RUNTIME_CHANGED_DURING_LOAD")
    kernel._verify_small_artifacts()
    return OwnedProductionRuntime(
        kernel, parts, identity, admission, source_validator, source_dependency_paths,
        _issuer=_PRODUCTION_RUNTIME_ISSUER,
    )


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
