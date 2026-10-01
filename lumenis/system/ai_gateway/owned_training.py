"""Local-only, approval-gated LoRA training owned by the SYSTEM AI Gateway."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVED_MANIFEST_PATH = REPO_ROOT / "config" / "ai-owned-foundation.json"
MODEL_ID = "openai/gpt-oss-20b"
MODEL_REVISION = "6cee5e81ee83917806bbde320786a8fb61efebee"
_MIN_CUDA_MEMORY = 75 * 1024**3
_MODEL_FILES = frozenset({
    "LICENSE", "USAGE_POLICY", "chat_template.jinja", "config.json",
    "model-00000-of-00002.safetensors", "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors", "model.safetensors.index.json",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
})
_RECORD_FIELDS = frozenset({
    "case_id", "source_evidence_refs", "scope", "domain", "context",
    "permission_ref", "rights_ref", "review_status", "reviewer_approval_ref",
    "reviewer_approved_target", "training_eligible", "messages",
})
_SECRET_KEY = re.compile(r"(?:api[_-]?key|authorization|cookie|session|password|secret|private[_-]?key|access[_-]?token|refresh[_-]?token)", re.I)
_SECRET_VALUE = re.compile(
    r"(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|[-]{5}BEGIN [A-Z ]*PRIVATE KEY[-]{5}|\bBearer\s+\S+)", re.I)
_UNKNOWN = frozenset({"", "UNKNOWN", "UNVERIFIED", "NOT_AVAILABLE", "NOT_COLLECTED", "N/A", "NA", "NONE", "PENDING", "DENIED", "REJECTED", "REVOKED"})
_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1", "WANDB_DISABLED": "true", "DO_NOT_TRACK": "1",
}


class TrainingBlocked(RuntimeError):
    """Training cannot proceed without the local safety gates."""


@dataclass(frozen=True)
class TrainingApprovalRequest:
    model_id: str
    model_revision: str
    train_sha256: str
    heldout_sha256: str
    scopes: tuple[str, ...]


def _local_path(value: str | os.PathLike[str], *, exists: bool = True) -> Path:
    raw = os.fspath(value)
    if not raw or "://" in raw or raw.startswith(("\\\\", "//")):
        raise ValueError("Only absolute local filesystem paths are accepted")
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError("Only absolute local filesystem paths are accepted")
    resolved = path.resolve(strict=exists)
    if str(resolved).startswith(("\\\\", "//")):
        raise ValueError("Network paths are not accepted")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _manifest(model_dir: Path, manifest_path: str | os.PathLike[str]) -> tuple[str, str]:
    supplied = _local_path(manifest_path)
    canonical = APPROVED_MANIFEST_PATH.resolve(strict=True)
    if Path(manifest_path).is_symlink() or supplied != canonical:
        raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_REQUIRED")
    raw = supplied.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or any((
        data.get("schema_version") != 1, data.get("owner") != "SYSTEM AI Gateway",
        data.get("model_id") != MODEL_ID, data.get("revision") != MODEL_REVISION,
        data.get("license") != "Apache-2.0", data.get("capability") != "text",
        data.get("format") != "transformers_safetensors",
        data.get("status") != "APPROVED_FOUNDATION_NOT_TRAINED",
        data.get("source_url") != f"https://huggingface.co/{MODEL_ID}/tree/{MODEL_REVISION}",
        data.get("usage_policy_url") != f"https://huggingface.co/{MODEL_ID}/blob/{MODEL_REVISION}/USAGE_POLICY",
        data.get("fine_tune_reference") != "https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers",
        not isinstance(data.get("files"), dict) or set(data["files"]) != _MODEL_FILES,
    )):
        raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_INVALID")
    entries = list(model_dir.iterdir())
    if any(not item.is_file() for item in entries) or {item.name for item in entries} != _MODEL_FILES:
        raise TrainingBlocked("LOCAL_MODEL_SNAPSHOT_FILE_SET_MISMATCH")
    for name, expected in data["files"].items():
        if Path(name).name != name or not isinstance(expected, dict) or set(expected) != {"size_bytes", "sha256"}:
            raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_INVALID")
        file = model_dir / name
        resolved = file.resolve(strict=True)
        if str(resolved).startswith(("\\\\", "//")) or model_dir not in resolved.parents:
            raise TrainingBlocked("LOCAL_MODEL_SYMLINK_ESCAPES_SNAPSHOT")
        if not file.is_file():
            raise TrainingBlocked("LOCAL_MODEL_FILE_UNAVAILABLE")
        size = file.stat().st_size
        if type(expected.get("size_bytes")) is not int or expected["size_bytes"] != size:
            raise TrainingBlocked("LOCAL_MODEL_FILE_HASH_MISMATCH")
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected.get("sha256", ""))) or _sha256(file) != expected["sha256"]:
            raise TrainingBlocked("LOCAL_MODEL_FILE_HASH_MISMATCH")
    return hashlib.sha256(raw).hexdigest(), data["revision"]


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip().upper() in _UNKNOWN:
        raise ValueError(f"Invalid or unknown {field}")
    return value.strip()


def _has_secret(value: object) -> bool:
    if isinstance(value, dict):
        return any(_SECRET_KEY.search(str(key)) or _has_secret(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_secret(item) for item in value)
    return isinstance(value, str) and bool(_SECRET_VALUE.search(value))


def _validate_record(record: object) -> tuple[dict, str]:
    if not isinstance(record, dict) or set(record) != _RECORD_FIELDS or _has_secret(record):
        raise ValueError("Record schema or secret scan failed")
    _text(record["case_id"], "case_id")
    for field in ("scope", "domain", "context", "permission_ref", "rights_ref", "reviewer_approval_ref", "reviewer_approved_target"):
        _text(record[field], field)
    refs = record["source_evidence_refs"]
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() or ref.strip().upper() in _UNKNOWN for ref in refs):
        raise ValueError("Source Evidence references must be explicit")
    if record["training_eligible"] is not True or str(record["review_status"]).upper() not in {"APPROVED", "REVIEWER_APPROVED"}:
        raise ValueError("Only reviewer-approved eligible records can be trained")
    messages = record["messages"]
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError("At least one user message and one final answer are required")
    users, assistants = [], []
    canonical = []
    for message in messages:
        if not isinstance(message, dict) or set(message) - {"role", "content", "channel"}:
            raise ValueError("Messages may contain only user input and final answer text")
        role = message.get("role")
        content = _text(message.get("content"), "message content")
        if role == "user" and "channel" not in message:
            users.append(content)
            canonical.append({"role": "user", "content": content})
        elif role == "assistant" and message.get("channel", "final") == "final":
            assistants.append(content)
            canonical.append({"role": "assistant", "content": content, "channel": "final"})
        else:
            raise ValueError("Only user messages and one final assistant answer are allowed")
    if not users or len(assistants) != 1 or messages[-1].get("role") != "assistant" or assistants[0] != record["reviewer_approved_target"].strip():
        raise ValueError("The sole final answer must match its reviewer-approved target")
    prompt = " ".join(unicodedata.normalize("NFKC", " ".join(users)).casefold().split())
    return {"case_id": record["case_id"], "scope": record["scope"].strip(), "messages": canonical}, prompt


def _read_jsonl(path: Path) -> tuple[list[tuple[dict, str]], str]:
    if path.suffix.lower() != ".jsonl" or not path.is_file():
        raise ValueError("Training inputs must be local JSONL files")
    records = []
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line_number, line in enumerate(stream, 1):
            digest.update(line)
            if line.strip():
                try:
                    records.append(_validate_record(json.loads(line.decode("utf-8"))))
                except (json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"Invalid approved dataset record at line {line_number}") from exc
    if not records:
        raise ValueError("Training and held-out datasets must both be non-empty")
    return records, digest.hexdigest()


def _output_path(value: str | os.PathLike[str], protected: list[Path]) -> Path:
    raw = os.fspath(value)
    if not raw or "://" in raw or raw.startswith(("\\\\", "//")) or not Path(raw).is_absolute():
        raise ValueError("The output must be an absolute local path")
    requested = Path(raw)
    if os.path.lexists(raw) or not requested.name:
        raise ValueError("The output directory must be new and must not be a symlink")
    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("The output parent must already exist")
    candidate = parent / requested.name
    if any(_overlaps(candidate, path.resolve(strict=False)) for path in protected):
        raise ValueError("The output overlaps protected model, input, manifest, repository, or database paths")
    return candidate


@contextmanager
def _offline_hf():
    previous = {key: os.environ.get(key) for key in _OFFLINE_ENV}
    os.environ.update(_OFFLINE_ENV)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _require_cuda() -> tuple[object, str, int]:
    try:
        import torch
    except ImportError as exc:
        raise TrainingBlocked("CUDA_TRAINING_DEPENDENCIES_UNAVAILABLE") from exc
    if not torch.cuda.is_available() or not torch.cuda.device_count():
        raise TrainingBlocked("CUDA_REQUIRED_NO_CPU_FALLBACK")
    device = torch.cuda.get_device_properties(0)
    if int(device.total_memory) < _MIN_CUDA_MEMORY or not torch.cuda.is_bf16_supported():
        raise TrainingBlocked("CUDA_MEMORY_OR_BFLOAT16_BELOW_H100_RECIPE_GATE")
    return torch, str(device.name), int(device.total_memory)


def _verify_approval(verifier: Callable[[TrainingApprovalRequest], bool] | None, request: TrainingApprovalRequest) -> None:
    if not callable(verifier):
        raise TrainingBlocked("TRAINING_APPROVAL_REQUIRED")
    try:
        approved = verifier(request)
    except Exception as exc:
        raise TrainingBlocked("TRAINING_APPROVAL_VERIFIER_FAILED") from exc
    if approved is not True:
        raise TrainingBlocked("TRAINING_APPROVAL_REQUIRED")


def run_owned_lora_training(
    model_snapshot_dir: str | os.PathLike[str], train_jsonl_path: str | os.PathLike[str],
    heldout_jsonl_path: str | os.PathLike[str], output_dir: str | os.PathLike[str], *,
    manifest_path: str | os.PathLike[str], execute: bool = False,
    approval_verifier: Callable[[TrainingApprovalRequest], bool] | None = None,
) -> dict[str, object]:
    """Validate explicit local inputs; train only after Learning approval and CUDA gates."""
    if type(execute) is not bool:
        raise ValueError("execute must be an explicit boolean")
    if Path(model_snapshot_dir).is_symlink():
        raise TrainingBlocked("LOCAL_MODEL_SYMLINK_ESCAPES_SNAPSHOT")
    model_dir = _local_path(model_snapshot_dir)
    if not model_dir.is_dir():
        raise ValueError("A local model snapshot directory is required")
    if Path(train_jsonl_path).is_symlink() or Path(heldout_jsonl_path).is_symlink():
        raise TrainingBlocked("LOCAL_DATASET_SYMLINK_NOT_ALLOWED")
    train_path, heldout_path = _local_path(train_jsonl_path), _local_path(heldout_jsonl_path)
    manifest_file = _local_path(manifest_path)
    manifest_hash, revision = _manifest(model_dir, manifest_file)
    train, train_hash = _read_jsonl(train_path)
    heldout, heldout_hash = _read_jsonl(heldout_path)
    case_ids, prompts = set(), set()
    for record, prompt in train + heldout:
        if record["case_id"] in case_ids or prompt in prompts:
            raise ValueError("Training and held-out inputs overlap by case_id or normalized prompt")
        case_ids.add(record["case_id"])
        prompts.add(prompt)
    db_value = os.environ.get("ZBC_DB_PATH", str(REPO_ROOT / "data" / "monitor.db"))
    db_path = Path(db_value) if Path(db_value).is_absolute() else Path.cwd() / db_value
    output = _output_path(output_dir, [model_dir, train_path, heldout_path, manifest_file, REPO_ROOT, db_path])
    scopes = tuple(sorted({record["scope"] for record, _ in train + heldout}))
    result: dict[str, object] = {
        "status": "VALIDATED_LOCAL_INPUTS_NOT_PRODUCTION_ACCEPTANCE",
        "execution_state": "PREFLIGHT_ONLY", "candidate_status": "NOT_EVALUATED",
        "permission_evidence_state": "LOCAL_ATTESTATIONS_ONLY_NOT_VERIFIED",
        "model_id": MODEL_ID, "model_revision": revision,
        "manifest_sha256": manifest_hash, "train_sha256": train_hash,
        "heldout_sha256": heldout_hash, "train_case_count": len(train),
        "heldout_case_count": len(heldout), "scopes": list(scopes),
    }
    if not execute:
        return result
    request = TrainingApprovalRequest(MODEL_ID, revision, train_hash, heldout_hash, scopes)
    _verify_approval(approval_verifier, request)
    torch, device_name, memory_bytes = _require_cuda()
    with _offline_hf():
        try:
            from datasets import Dataset
            from peft import LoraConfig, get_peft_model
            from transformers import AutoModelForCausalLM, AutoTokenizer, Mxfp4Config
            from trl import SFTConfig, SFTTrainer
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir), revision=revision, local_files_only=True, trust_remote_code=False)
            rows = []
            for record, _ in train:
                text = tokenizer.apply_chat_template(record["messages"], tokenize=False)
                if len(tokenizer(text, add_special_tokens=False, truncation=False)["input_ids"]) > 2048:
                    raise TrainingBlocked("TRAINING_EXAMPLE_EXCEEDS_MAX_LENGTH")
                rows.append({"text": text})
            dataset = Dataset.from_list(rows)
            model = AutoModelForCausalLM.from_pretrained(
                str(model_dir), revision=revision, local_files_only=True, trust_remote_code=False,
                attn_implementation="eager", torch_dtype=torch.bfloat16,
                quantization_config=Mxfp4Config(dequantize=True), use_cache=False, device_map="auto", use_safetensors=True,
            )
            config = LoraConfig(
                r=8, lora_alpha=16, target_modules="all-linear",
                target_parameters=[f"{layer}.mlp.experts.{projection}" for layer in (7, 15, 23) for projection in ("gate_up_proj", "down_proj")],
            )
            model = get_peft_model(model, config)
            args = SFTConfig(
                learning_rate=2e-4, gradient_checkpointing=True, num_train_epochs=1,
                logging_steps=1, per_device_train_batch_size=4, gradient_accumulation_steps=4,
                max_length=2048, warmup_ratio=0.03, lr_scheduler_type="cosine_with_min_lr",
                lr_scheduler_kwargs={"min_lr_rate": 0.1}, output_dir=str(output),
                report_to="none", push_to_hub=False, save_strategy="no", bf16=True,
            )
            _verify_approval(approval_verifier, request)
            output.mkdir(exist_ok=False)
            result.update({"execution_state": "TRAINING_IN_PROGRESS", "cuda_device": device_name, "cuda_memory_bytes": memory_bytes})
            _write_status(output, result)
            try:
                trainer = SFTTrainer(model=model, args=args, train_dataset=dataset, processing_class=tokenizer)
                _verify_approval(approval_verifier, request)
                train_result = trainer.train()
                if int(getattr(train_result, "global_step", 0)) <= 0:
                    raise TrainingBlocked("TRAINING_COMPLETED_WITHOUT_OPTIMIZER_STEPS")
                trainer.save_model(str(output))
                tokenizer.save_pretrained(str(output))
                for artifact in ("adapter_config.json", "adapter_model.safetensors"):
                    path = output / artifact
                    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
                        raise TrainingBlocked("TRAINED_ADAPTER_ARTIFACT_MISSING_OR_EMPTY")
            except TrainingBlocked as exc:
                result["execution_state"] = str(exc)
                _write_status(output, result)
                raise
            except Exception:
                result["execution_state"] = "TRAINING_FAILED"
                _write_status(output, result)
                raise
            result["execution_state"] = "TRAINED_NOT_EVALUATED"
            _write_status(output, result)
            return result
        except ImportError as exc:
            raise TrainingBlocked("LOCAL_TRAINING_DEPENDENCIES_UNAVAILABLE") from exc


def _write_status(output: Path, result: dict[str, object]) -> None:
    (output / "training_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
