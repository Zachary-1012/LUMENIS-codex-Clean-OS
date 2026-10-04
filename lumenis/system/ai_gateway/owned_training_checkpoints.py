"""Trainer-side checkpoint policy and inventory validation.

Task, Permission, Artifact and the supervised process owner admit effects and
commit immutable checkpoints. These local observations confer no authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict
import copy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import struct
import sys
import uuid

from .owned_training import (TrainingApprovalRequest, TrainingBlocked, T4_RECIPE,
    ADA_RECIPE, NF4_RECIPES, NATIVE_BF16_NF4_RECIPES, recipe_gradient_accumulation_steps, _verify_approval)


_HASH = re.compile(r"[0-9a-f]{64}")
_RECIPE = re.compile(r"(" + "|".join(re.escape(x) for x in sorted(NF4_RECIPES)) + r")\+checkpoint-v1:([0-9a-f]{64})")
_MAX_METADATA_BYTES = 1024 * 1024
_MAX_FILES = 4096
_POLICY_FIELDS = frozenset({
    "schema_version", "base_recipe", "checkpoint_interval_steps",
    "max_replay_optimizer_steps", "retain_committed",
    "save_only_at_completed_optimizer_step", "save_only_model",
    "automatic_rotation", "restore_dataset_position", "restore_callback_state",
    "rng_devices", "required_roles", "framework_lock_sha256",
    "trainer_config_sha256", "data_order_sha256", "numerical_tolerance",
})
_REQUIRED_ROLES = frozenset({
    "adapter_or_model", "model_config", "tokenizer", "optimizer", "scheduler",
    "rng_cpu", "rng_cuda", "trainer_state", "data_position", "callback_state",
})
_FRAMEWORK_PACKAGES = frozenset({
    "unsloth", "unsloth_zoo", "transformers", "trl", "torch", "bitsandbytes",
    "tokenizers", "triton", "peft", "accelerate", "datasets", "numpy",
    "safetensors", "huggingface_hub",
})
_SAVE_RESERVATION_FIELDS = frozenset({
    "schema_version", "operation_id", "task_digest", "origin_run_digest", "attempt_id",
    "worker_epoch", "completed_step", "parent_ref", "policy_sha256", "fingerprints",
    "staging_root", "checkpoint_relative_path", "write_deadline_utc", "admission_receipt",
})
_SAVE_RECEIPT_FIELDS = frozenset({
    "schema_version", "operation_id", "task_digest", "origin_run_digest", "attempt_id",
    "worker_epoch", "fingerprints", "policy_sha256", "completed_step", "artifact_ref",
    "artifact_version", "parent_ref", "inventory_sha256", "artifact_sha256",
    "storage_identity", "committed_at_utc", "task_step_ref", "receipt",
})
_RESUME_RESERVATION_FIELDS = frozenset({
    "schema_version", "operation_id", "task_digest", "checkpoint_ref", "checkpoint_sha256",
    "source_run_digest", "run_digest", "attempt_id", "worker_epoch", "completed_step",
    "replay_through_step", "policy_sha256", "fingerprints", "load_root",
    "checkpoint_relative_path", "worker_stop_receipt_ref", "admission_receipt",
})
_RESUME_RECEIPT_FIELDS = frozenset({
    "schema_version", "operation_id", "task_digest", "run_digest", "checkpoint_ref",
    "checkpoint_sha256", "restored_state", "task_step_ref", "committed_at_utc",
    "receipt", "phase_handoff",
})
_RECOVERY_HANDOFF_FIELDS = frozenset({
    "schema_version", "task_id", "task_digest", "run_digest", "attempt_id",
    "worker_epoch", "fingerprints", "checkpoint_ref", "checkpoint_sha256",
    "load_operation_id", "resume_receipt_sha256", "next_sequence", "next_phase",
    "admission_version", "worker_binding_sha256",
})
_ROW_MARKER = "__lumenis_checkpoint_row__"
_T4_REQUIRED_ROLE_PATHS = {
    "adapter_or_model": ["adapter_model.safetensors"], "model_config": ["adapter_config.json"],
    "tokenizer": ["tokenizer.json", "tokenizer_config.json"],
    "optimizer": ["optimizer.pt"], "scheduler": ["scheduler.pt"],
    "rng_cpu": ["rng_state.pth"], "rng_cuda": ["lumenis_cuda_rng.safetensors"],
    "trainer_state": ["trainer_state.json"], "data_position": ["lumenis_data_position.json"],
    "callback_state": ["lumenis_callback_state.json"],
}


def canonical_bytes(value: object) -> bytes:
    from lumenis.system.security import training_receipts

    try:
        raw = training_receipts._canonical_json_bytes(value)
    except training_receipts.TrainingReceiptError:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID") from None
    if len(raw) > _MAX_METADATA_BYTES:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    return raw


def strict_json(raw: bytes) -> object:
    from lumenis.system.security import training_receipts

    if type(raw) is not bytes or len(raw) > _MAX_METADATA_BYTES:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=training_receipts._reject_duplicate_json_keys,
            parse_constant=training_receipts._reject_json_constant,
        )
    except (ValueError, UnicodeError):
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID") from None


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_hash(value: object) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def training_state_sha256(value: object) -> str:
    """Hash observed state values without pickle, device names or ZIP metadata.

    This versioned representation distinguishes types, shapes and exact tensor
    bytes. It compares saved/loaded state, not numerical training quality. Torch
    is used only if the admitted training runtime has already imported it.
    """
    import numpy as np

    digest = hashlib.sha256(b"lumenis-training-state-v1\0")
    torch = sys.modules.get("torch")
    count = 0

    def emit(tag: bytes, raw: bytes) -> None:
        digest.update(tag)
        digest.update(struct.pack(">Q", len(raw)))
        digest.update(raw)

    def visit(item, depth=0):
        nonlocal count
        count += 1
        if depth > 64 or count > 1_000_000:
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        if item is None:
            emit(b"n", b"")
        elif type(item) is bool:
            emit(b"b", b"1" if item else b"0")
        elif type(item) is int:
            emit(b"i", str(item).encode("ascii"))
        elif type(item) is float:
            if not math.isfinite(item):
                raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
            emit(b"f", struct.pack(">d", item))
        elif type(item) is str:
            emit(b"s", item.encode("utf-8"))
        elif type(item) in {list, tuple}:
            emit(b"l" if type(item) is list else b"t", str(len(item)).encode("ascii"))
            for child in item:
                visit(child, depth + 1)
        elif type(item) in {dict, OrderedDict}:
            if any(type(key) not in {str, int} for key in item):
                raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
            emit(b"d", str(len(item)).encode("ascii"))
            for key in sorted(item, key=lambda key: (type(key).__name__, str(key))):
                visit(key, depth + 1)
                visit(item[key], depth + 1)
        elif torch is not None and type(item) in {torch.Tensor, torch.nn.Parameter}:
            if (item.layout != torch.strided or item.device.type == "meta"
                    or item.is_quantized or sys.byteorder != "little"
                    or not bool(torch.isfinite(item).all())):
                raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
            observed = item.detach().cpu().contiguous()
            emit(b"T", str(item.dtype).encode("ascii"))
            visit(tuple(item.shape), depth + 1)
            emit(b"v", observed.reshape(-1).view(torch.uint8).numpy().tobytes())
        elif type(item) is np.ndarray or isinstance(item, np.generic):
            observed = np.asarray(item)
            if observed.dtype.kind not in "biufc" or not bool(np.isfinite(observed).all()):
                raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
            dtype = observed.dtype.newbyteorder("<")
            emit(b"N", dtype.str.encode("ascii"))
            visit(tuple(observed.shape), depth + 1)
            emit(b"v", np.ascontiguousarray(observed, dtype=dtype).tobytes())
        else:
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")

    try:
        visit(value)
    except (RecursionError, UnicodeError, ValueError, TypeError, OverflowError):
        raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE") from None
    return digest.hexdigest()


def _relative_path(value: object) -> str:
    if (type(value) is not str or not value or len(value) > 512
            or "\\" in value or any(c in value for c in ':<>"|?*')
            or any(ord(c) < 32 for c in value)):
        raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
    path = PurePosixPath(value)
    parts = value.split("/")
    if (path.is_absolute() or path.as_posix() != value
            or any(p in {"", ".", ".."} or p.endswith((" ", "."))
                   or PureWindowsPath(p).is_reserved() for p in parts)):
        raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
    return value


@dataclass(frozen=True)
class CheckpointPolicy:
    """Immutable validated material; registration and permission remain separate."""

    canonical_document: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_document).hexdigest()

    @property
    def recipe(self) -> str:
        return f"{self.document['base_recipe']}+checkpoint-v1:{self.sha256}"

    @property
    def document(self) -> dict:
        return json.loads(self.canonical_document)

    @classmethod
    def validate(cls, value: object) -> CheckpointPolicy:
        if type(value) is not dict or set(value) != _POLICY_FIELDS:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        if (type(value["schema_version"]) is not int or value["schema_version"] != 1
                or type(value["base_recipe"]) is not str or value["base_recipe"] not in NF4_RECIPES):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        for key, minimum in [("checkpoint_interval_steps", 1), ("max_replay_optimizer_steps", 0)]:
            if type(value[key]) is not int or not minimum <= value[key] <= 1_000_000:
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        expected_flags = {
            "retain_committed": True, "save_only_at_completed_optimizer_step": True,
            "save_only_model": False, "automatic_rotation": False,
            "restore_dataset_position": True, "restore_callback_state": True,
        }
        if any(value[key] is not expected for key, expected in expected_flags.items()):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        if value["rng_devices"] != ["cpu", "cuda:0"]:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        for key in ["framework_lock_sha256", "trainer_config_sha256", "data_order_sha256"]:
            if not _is_hash(value[key]):
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        tolerance = value["numerical_tolerance"]
        if (type(tolerance) is not dict or set(tolerance) != {"rtol", "atol"}
                or any(type(v) not in {int, float} or not math.isfinite(v) or v < 0
                       for v in tolerance.values())):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        roles = value["required_roles"]
        if (type(roles) is not dict or not _REQUIRED_ROLES.issubset(roles)
                or set(roles) - _REQUIRED_ROLES - {"scaler"}):
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        names = set()
        for files in roles.values():
            if (type(files) is not list or not files
                    or any(type(name) is not str for name in files) or files != sorted(files)):
                raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
            for name in files:
                _relative_path(name)
                # Role paths are relative to the explicitly selected checkpoint.
                if name.casefold() in names:
                    raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
                names.add(name.casefold())
        if len(names) > _MAX_FILES:
            raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
        return cls(canonical_bytes(value))

    def validate_runtime(self, *, framework_versions: dict, trainer_config: dict,
                         data_order: object, scaler_present: bool) -> None:
        if (type(framework_versions) is not dict or set(framework_versions) != _FRAMEWORK_PACKAGES
                or any(type(v) is not str or not v.strip() or len(v) > 128
                       for v in framework_versions.values())):
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        document = self.document
        for key, actual in [("framework_lock_sha256", framework_versions),
                            ("trainer_config_sha256", trainer_config),
                            ("data_order_sha256", data_order)]:
            if _digest(actual) != document[key]:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        if type(scaler_present) is not bool or scaler_present != ("scaler" in document["required_roles"]):
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")


def load_recovery_policy(recipe: str, manifest_path: Path) -> CheckpointPolicy:
    """Resolve only a registered immutable policy; never extend an old recipe."""
    match = _RECIPE.fullmatch(recipe) if type(recipe) is str else None
    if match is None:
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    from .owned_training import APPROVED_MANIFEST_PATH

    path = Path(manifest_path)
    if path.is_symlink() or path.resolve(strict=True) != APPROVED_MANIFEST_PATH.resolve(strict=True):
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    document = strict_json(path.read_bytes())
    if type(document) is not dict:
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    registry = document.get("checkpoint_recovery_policies")
    if (type(registry) is not dict or set(registry) != {"schema_version", "policies"}
            or type(registry["schema_version"]) is not int or registry["schema_version"] != 1
            or type(registry["policies"]) is not dict):
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    if match[2] not in registry["policies"]:
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    policy = CheckpointPolicy.validate(registry["policies"][match[2]])
    if policy.document["base_recipe"] != match[1]:
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    if policy.sha256 != match[2]:
        raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
    return policy


class TrainingDataCursor:
    """Observe consumed rows for the single-epoch, recipe-pinned sampler.

    A batch is counted only after its training_step returns. A checkpoint can
    capture this cursor only after a completed optimizer update. Framework
    prefetching and a global_step number do not advance the observed position.
    Restoring these values requires separately verified checkpoint authority.
    """

    def __init__(self, *, dataset_sha256: str, row_sha256: list[str],
                 gradient_accumulation_steps: int, base_recipe: str = T4_RECIPE):
        if (not _is_hash(dataset_sha256) or type(row_sha256) is not list
                or not row_sha256 or any(not _is_hash(item) for item in row_sha256)
                or type(gradient_accumulation_steps) is not int
                or type(base_recipe) is not str or base_recipe not in NF4_RECIPES
                or gradient_accumulation_steps != recipe_gradient_accumulation_steps(base_recipe)):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        self._order = canonical_bytes({
            "schema_version": 1, "sampler": "sequential-v1", "epochs": 1,
            "batch_size": 1, "gradient_accumulation_steps": gradient_accumulation_steps,
            "dataset_sha256": dataset_sha256, "row_sha256": row_sha256,
        })
        self._row_hashes = tuple(row_sha256)
        self._accumulation_steps = gradient_accumulation_steps
        self._dataset_sha256 = dataset_sha256
        self._consumed: list[str] = []
        self._pending_row = None
        self._accumulation = 0
        self._completed_step = 0
        self._failed = False

    @property
    def data_order(self) -> dict:
        return json.loads(self._order)

    def begin_batch(self, row_index: int, row_sha256: str) -> None:
        """Check the actual collated row before the forward/backward call."""
        if (self._failed or self._pending_row is not None or self._accumulation >= self._accumulation_steps
                or type(row_index) is not int or row_index != len(self._consumed)
                or row_index >= len(self._row_hashes)
                or row_sha256 != self._row_hashes[row_index]):
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        self._pending_row = row_sha256

    def complete_batch(self) -> None:
        if self._failed or self._pending_row is None or self._accumulation >= self._accumulation_steps:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        self._consumed.append(self._pending_row)
        self._pending_row = None
        self._accumulation += 1

    def fail_batch(self) -> None:
        # No exception handler can turn partially accumulated gradients into
        # a committed position. A new owner-admitted attempt must restore it.
        self._failed = True

    def complete_optimizer_step(self, completed_step: int, *,
                                sync_gradients: bool, optimizer_step_was_skipped: bool) -> None:
        last_partial = len(self._consumed) == len(self._row_hashes) and 0 < self._accumulation < self._accumulation_steps
        if (self._failed or self._pending_row is not None
                or type(completed_step) is not int or completed_step != self._completed_step + 1
                or sync_gradients is not True or optimizer_step_was_skipped is not False
                or (self._accumulation != self._accumulation_steps and not last_partial)):
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        self._completed_step = completed_step
        self._accumulation = 0

    def snapshot(self) -> dict:
        if (self._failed or self._pending_row is not None or self._accumulation
                or self._completed_step == 0):
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        sampler = {
            "schema_version": 1, "sampler": "sequential-v1",
            "data_order_sha256": hashlib.sha256(self._order).hexdigest(),
            "consumed_row_sha256": list(self._consumed),
        }
        result = {
            "schema_version": 1, "sampler_state": sampler,
            "data_position": {
                "dataset_sha256": self._dataset_sha256,
                "sampler_state_sha256": _digest(sampler), "epoch_index": 0,
                "next_batch_index": len(self._consumed),
                "completed_step": self._completed_step, "gradient_accumulation_offset": 0,
            },
        }
        canonical_bytes(result)
        return result

    def restore(self, snapshot: object) -> None:
        """Validate a committed observation against this exact prepared dataset.

        The caller must verify the signed Artifact before supplying its state.
        This method validates data consistency and does not authorize a load.
        """
        if self._consumed or self._pending_row is not None or self._failed or self._completed_step:
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        if (type(snapshot) is not dict
                or set(snapshot) != {"schema_version", "sampler_state", "data_position"}
                or type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        sampler, position = snapshot["sampler_state"], snapshot["data_position"]
        if (type(sampler) is not dict
                or set(sampler) != {"schema_version", "sampler", "data_order_sha256", "consumed_row_sha256"}
                or type(sampler["schema_version"]) is not int or sampler["schema_version"] != 1
                or sampler["sampler"] != "sequential-v1"
                or sampler["data_order_sha256"] != hashlib.sha256(self._order).hexdigest()
                or type(sampler["consumed_row_sha256"]) is not list
                or type(position) is not dict
                or set(position) != {"dataset_sha256", "sampler_state_sha256", "epoch_index",
                                     "next_batch_index", "completed_step", "gradient_accumulation_offset"}):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        count = len(sampler["consumed_row_sha256"])
        expected = {
            "dataset_sha256": self._dataset_sha256, "sampler_state_sha256": _digest(sampler),
            "epoch_index": 0, "next_batch_index": count,
            "completed_step": (count + self._accumulation_steps - 1) // self._accumulation_steps,
            "gradient_accumulation_offset": 0,
        }
        if (not 0 < count <= len(self._row_hashes)
                or (count % self._accumulation_steps and count != len(self._row_hashes))
                or sampler["consumed_row_sha256"] != list(self._row_hashes[:count])
                or any(type(position[k]) is not type(v) or position[k] != v
                       for k, v in expected.items())):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        canonical_bytes(snapshot)
        self._consumed = list(sampler["consumed_row_sha256"])
        self._completed_step = position["completed_step"]


def _regular_stat(path: Path, *, directory: bool = False):
    value = path.lstat()
    reparse = getattr(value, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    expected = stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode)
    if reparse or not expected or (not directory and value.st_nlink != 1):
        raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
    return value


def _file_snapshot(path: Path) -> tuple[int, str]:
    before = _regular_stat(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    current = _regular_stat(path)
    def signature(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
                value.st_nlink, getattr(value, "st_birthtime_ns", None))

    # On Windows, path stat can report creation time as ctime while fstat
    # reports change time (CPython #157671). Preserve both mutation checks,
    # comparing each timestamp only against the same observation method.
    if (signature(before) != signature(opened) or signature(opened) != signature(after)
            or signature(before) != signature(current)
            or before.st_ctime_ns != current.st_ctime_ns
            or opened.st_ctime_ns != after.st_ctime_ns):
        raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
    return before.st_size, digest.hexdigest()


def inspect_checkpoint_files(staging_root: Path, checkpoint_relative_path: str,
                             policy: CheckpointPolicy) -> list[dict]:
    """Inventory the entire reserved root, including TRL auxiliary writes.

    This is a worker observation. The Artifact owner must independently verify
    and durably commit the closed files before they become a recovery point.
    """
    if type(staging_root) is not type(Path()) or not staging_root.is_absolute():
        raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
    _relative_path(checkpoint_relative_path)
    try:
        for parent in [*reversed(staging_root.parents), staging_root]:
            _regular_stat(parent, directory=True)
        checkpoint_root = staging_root / checkpoint_relative_path
        relative_parent = checkpoint_root
        while relative_parent != staging_root:
            _regular_stat(relative_parent, directory=True)
            relative_parent = relative_parent.parent
        roles = {}
        for role, names in policy.document["required_roles"].items():
            for name in names:
                roles[f"{checkpoint_relative_path}/{name}"] = role
        result, seen = [], set()
        pending = [staging_root]
        while pending:
            directory = pending.pop()
            for path in directory.iterdir():
                relative = _relative_path(path.relative_to(staging_root).as_posix())
                entry = path.lstat()
                if stat.S_ISDIR(entry.st_mode):
                    _regular_stat(path, directory=True)
                    pending.append(path)
                    continue
                if relative.casefold() in seen or len(result) >= _MAX_FILES:
                    raise TrainingBlocked("CHECKPOINT_INVENTORY_INVALID")
                seen.add(relative.casefold())
                size, digest = _file_snapshot(path)
                role = roles.get(relative, "auxiliary")
                if role != "auxiliary" and size <= 0:
                    raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
                result.append({"path": relative, "role": role, "size_bytes": size, "sha256": digest})
        if set(roles) - {item["path"] for item in result}:
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        result.sort(key=lambda item: item["path"])
        canonical_bytes(result)
        return result
    except OSError:
        raise TrainingBlocked("CHECKPOINT_STORAGE_UNAVAILABLE") from None


def _utc_time(value: object) -> datetime:
    if type(value) is not str:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID") from None
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    return result


def _uuid4(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return False
    return parsed.version == 4 and str(parsed) == value


def trainer_checkpoint_config(trainer, *, base_recipe: str = T4_RECIPE) -> dict:
    """Bind the full effective config, with owner-selected paths normalized."""
    if type(base_recipe) is not str or base_recipe not in NF4_RECIPES:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    material = trainer.args.to_dict()
    if type(material) is not dict:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    # Transformers redacts even a None hub_token in to_dict(). Check the actual
    # field first, then represent the verified absence without a fake token.
    if getattr(trainer.args, "hub_token", None) is not None:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    material = copy.deepcopy(material)
    material["hub_token"] = None
    required = {
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": recipe_gradient_accumulation_steps(base_recipe),
        "num_train_epochs": 1, "dataloader_num_workers": 0,
        "dataloader_drop_last": False, "remove_unused_columns": False,
        "save_only_model": False, "save_total_limit": None,
        "restore_callback_states_from_checkpoint": True, "ignore_data_skip": False,
        "push_to_hub": False, "hub_model_id": None, "hub_token": None,
        "packing": False, "fp16": False, "bf16": base_recipe in NATIVE_BF16_NF4_RECIPES,
    }
    # Trainer stores epochs as a float. Equality is intentional only for that
    # framework field; the strict policy's own integers never accept bools.
    if not set(required).issubset(material):
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    for key, expected in required.items():
        actual = material.get(key)
        correct_type = type(actual) is type(expected)
        if key == "num_train_epochs":
            correct_type = type(actual) in {int, float}
        if actual != expected or not correct_type:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    if (material.get("save_strategy") != "steps" or material.get("eval_strategy") != "no"
            or material.get("report_to") not in ([], "none")
            or trainer.args.world_size != 1 or trainer.args.n_gpu != 1
            or trainer.is_deepspeed_enabled or trainer.is_fsdp_enabled
            or trainer.hp_search_backend is not None):
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    material["output_dir"] = "<owner-reserved-output>"
    material["logging_dir"] = "<owner-reserved-logs>"
    material["lumenis_state_representation"] = "lumenis-training-state-v1"
    material["lumenis_sampler"] = "sequential-v1"
    canonical_bytes(material)
    return material


class TrainingCheckpointAdapter:
    """Trainer consumer of W6's bound checkpoint owner, never an effect owner.

    The save path is single-use. An unknown commit stops this worker and exposes
    its operation id for the Task owner's exact readback/reconciliation. It
    never repeats a physical save based on a historical receipt.
    """

    def __init__(self, request: TrainingApprovalRequest, context: dict, *,
                 manifest_path: Path, client, pinned_public_key: dict,
                 actor_id: int | None = None, principal=None, public_context=None):
        from lumenis.system.security import training_receipts
        from lumenis.system.security.permission import owned_training_phase_fingerprints

        if type(request) is not TrainingApprovalRequest:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        self.policy = load_recovery_policy(request.recipe, manifest_path)
        roles = self.policy.document["required_roles"]
        if (any(roles.get(role) != names for role, names in _T4_REQUIRED_ROLE_PATHS.items())
                or ("scaler" in roles and roles["scaler"] != ["scaler.pt"])):
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        symbols = ("VerifiedTrainingCheckpointAdmission", "VerifiedTrainingCheckpointReceipt",
                   "VerifiedTrainingResumeReceipt", "VerifiedTrainingRecoveryHandoff",
                   "verify_training_checkpoint_admission", "verify_training_checkpoint_receipt",
                   "verify_training_resume_receipt", "verify_training_recovery_handoff")
        if any(not hasattr(training_receipts, name) for name in symbols):
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        if any(not callable(getattr(client, name, None)) for name in (
                "reserve_save", "commit_save", "read_save", "prepare_resume",
                "complete_load", "read_resume", "require_current_admission")):
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        training_receipts._validate_pinned_public_key(pinned_public_key)
        from .owned_training_phases import TrainingPublicContext
        if public_context is None:
            self._fingerprints = owned_training_phase_fingerprints(
                request, context=context, domain_id=request.domain_id,
                actor_id=actor_id, principal=principal)
        elif type(public_context) is TrainingPublicContext and actor_id is None and principal is None:
            self._fingerprints = public_context.fingerprints_for(request, context)
        else:
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        self._public_context = public_context
        self._request, self._client = request, client
        self._context = copy.deepcopy(context)
        self._actor_id, self._principal = actor_id, principal
        self._pin = copy.deepcopy(pinned_public_key)
        self._approval_verifier = None
        self._cursor = None
        self._trainer = None
        self._parent_ref = None
        self._operation_id = None
        self._last_saved_step = 0
        self._last_committed_checkpoint = None
        self._resume_reservation = None
        self._load_components = set()
        self._load_started = False
        self._load_committed = False
        self._loaded_handoff = None
        self._recovery_phase_client = None
        self._recovery_phase_admitted = False
        self._expected_restored_state = None
        self._failed = False

    @property
    def last_operation_id(self) -> str | None:
        return self._operation_id

    @property
    def last_committed_checkpoint(self) -> dict | None:
        """Detached historical save record, never a current execution permit."""
        return copy.deepcopy(self._last_committed_checkpoint)

    @property
    def resume_completed_step(self) -> int:
        if self._resume_reservation is None or self._failed:
            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
        return self._resume_reservation["completed_step"]

    def bind_request(self, request, approval_verifier) -> None:
        if (type(request) is not TrainingApprovalRequest or request != self._request
                or self._approval_verifier is not None):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        _verify_approval(approval_verifier, request)
        self._approval_verifier = approval_verifier

    def trainer_type(self, base):
        """Wrap the pinned SFTTrainer at its actual batch/save boundaries."""
        adapter = self

        class CheckpointTrainer(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                adapter._bind_trainer(self)

            def _get_train_sampler(self, train_dataset=None):
                from torch.utils.data import SequentialSampler

                return SequentialSampler(self.train_dataset if train_dataset is None else train_dataset)

            def training_step(self, model, inputs, num_items_in_batch=None):
                if (getattr(adapter, "_resume_reservation", None) is not None
                        and (adapter._failed or not adapter._load_committed
                             or not getattr(adapter, "_recovery_phase_admitted", False))):
                    raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
                if type(inputs) is not dict or _ROW_MARKER not in inputs:
                    raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
                material = dict(inputs)
                marker = material.pop(_ROW_MARKER)
                if type(marker) is not tuple or len(marker) != 2:
                    raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
                adapter._cursor.begin_batch(*marker)
                try:
                    result = super().training_step(model, material, num_items_in_batch)
                except BaseException:
                    adapter._cursor.fail_batch()
                    raise
                adapter._cursor.complete_batch()
                return result

            def _save_checkpoint(self, model, trial):
                if trial is not None:
                    raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
                parent_save = super()._save_checkpoint
                adapter._save_checkpoint(self, lambda: parent_save(model, trial))

            def train(self, resume_from_checkpoint=None, *args, **kwargs):
                if resume_from_checkpoint is not None:
                    adapter._require_load_path(resume_from_checkpoint)
                elif adapter._resume_reservation is not None:
                    raise TrainingBlocked("CHECKPOINT_LOAD_FAILED")
                return super().train(resume_from_checkpoint, *args, **kwargs)

            def _load_from_checkpoint(self, checkpoint, model=None):
                parent_load = super()._load_from_checkpoint
                return adapter._load_component("model", checkpoint,
                    lambda: parent_load(checkpoint, model))

            def _load_optimizer_and_scheduler(self, checkpoint):
                if checkpoint is None and adapter._resume_reservation is None:
                    return super()._load_optimizer_and_scheduler(checkpoint)
                parent_load = super()._load_optimizer_and_scheduler
                return adapter._load_component("optimizer_scheduler", checkpoint,
                    lambda: parent_load(checkpoint))

            def _load_scaler(self, checkpoint):
                if checkpoint is None and adapter._resume_reservation is None:
                    return super()._load_scaler(checkpoint)
                parent_load = super()._load_scaler
                return adapter._load_component("scaler", checkpoint, lambda: parent_load(checkpoint))

            def _load_callback_state(self):
                if adapter._resume_reservation is None:
                    return super()._load_callback_state()
                parent_load = super()._load_callback_state
                result = adapter._load_component("callback", adapter._selected_checkpoint(), parent_load)
                adapter._validate_loaded_callbacks(self)
                return result

            def _load_rng_state(self, checkpoint):
                if checkpoint is None and adapter._resume_reservation is None:
                    return super()._load_rng_state(checkpoint)
                parent_load = super()._load_rng_state
                result = adapter._load_component("rng", checkpoint, lambda: parent_load(checkpoint))
                adapter._finish_load(self)
                return result

        return CheckpointTrainer

    def _selected_checkpoint(self) -> Path:
        if self._resume_reservation is None:
            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
        reservation = self._resume_reservation
        return reservation["load_root"] / reservation["checkpoint_relative_path"]

    def _require_load_path(self, checkpoint) -> Path:
        if self._failed:
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        selected = self._selected_checkpoint()
        if (type(checkpoint) not in {str, type(Path())}
                or not Path(checkpoint).is_absolute() or Path(checkpoint) != selected):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        return selected

    def _load_component(self, component: str, checkpoint, load):
        selected = self._require_load_path(checkpoint)
        if component in self._load_components:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        reservation = self._resume_reservation
        try:
            _verify_approval(self._approval_verifier, self._request)
            if not self._load_started:
                # v1.3 consumes the one-use start before the first checkpoint
                # read. Later components belong to this same managed load;
                # they cannot renew or consume a second start admission.
                self._client.require_current_admission(reservation["admission_receipt"],
                    request=self._request, operation="load")
                self._load_started = True
                self._prepare_load_metadata()
            _regular_stat(selected, directory=True)
            result = load()
            self._load_components.add(component)
            return result
        except TrainingBlocked:
            self._failed = True
            raise
        except Exception:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_LOAD_FAILED") from None
        except BaseException:
            self._failed = True
            raise

    def prepare_load(self, *, operation_id: str, checkpoint_ref: str,
                     expected_checkpoint_sha256: str, replay_through_step: int) -> Path:
        """Prepare one exact owner-selected load after Trainer preparation.

        This consumer is not the public run resume entry. The canonical runtime
        must bind the old-worker stop, new attempt and preparation permission;
        renewing a start admission is the owner producer's separate decision.
        """
        from lumenis.system.security import training_receipts

        if (self._trainer is None or self._resume_reservation is not None or self._failed
                or not _uuid4(operation_id) or type(checkpoint_ref) is not str
                or re.fullmatch(r"ART-[0-9a-f]{16}", checkpoint_ref) is None
                or not _is_hash(expected_checkpoint_sha256)
                or type(replay_through_step) is not int or replay_through_step < 0):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        required = ("VerifiedTrainingResumeReceipt", "VerifiedTrainingRecoveryHandoff",
                    "verify_training_resume_receipt", "verify_training_recovery_handoff")
        if any(not hasattr(training_receipts, name) for name in required):
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        self._validate_runtime(self._trainer)
        _verify_approval(self._approval_verifier, self._request)
        self._operation_id = operation_id
        reservation = self._client.prepare_resume(operation_id=operation_id,
            checkpoint_ref=checkpoint_ref, expected_checkpoint_sha256=expected_checkpoint_sha256,
            replay_through_step=replay_through_step)
        if type(reservation) is not dict or set(reservation) != _RESUME_RESERVATION_FIELDS:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        expected = {"schema_version": 1, "operation_id": operation_id,
                    "checkpoint_ref": checkpoint_ref, "checkpoint_sha256": expected_checkpoint_sha256,
                    "replay_through_step": replay_through_step, "policy_sha256": self.policy.sha256,
                    "fingerprints": self._fingerprints}
        if any(type(reservation[k]) is not type(v) or reservation[k] != v for k, v in expected.items()):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        if (any(not _is_hash(reservation[k]) for k in ("task_digest", "source_run_digest", "run_digest"))
                or reservation["run_digest"] == reservation["source_run_digest"]
                or not _uuid4(reservation["attempt_id"])
                or type(reservation["worker_epoch"]) is not int or reservation["worker_epoch"] < 0
                or type(reservation["completed_step"]) is not int or reservation["completed_step"] < 1
                or not reservation["completed_step"] <= replay_through_step
                          <= reservation["completed_step"] + self.policy.document["max_replay_optimizer_steps"]
                or type(reservation["load_root"]) is not type(Path())
                or not reservation["load_root"].is_absolute()
                or reservation["checkpoint_relative_path"] != f"checkpoint-{reservation['completed_step']}"
                or type(reservation["worker_stop_receipt_ref"]) is not str
                or not reservation["worker_stop_receipt_ref"].strip()):
            raise TrainingBlocked("CHECKPOINT_REPLAY_NOT_AUTHORIZED")
        admission = reservation["admission_receipt"]
        if type(admission) is not training_receipts.VerifiedTrainingCheckpointAdmission:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        envelope = admission.envelope
        if type(envelope) is not dict or type(envelope.get("payload")) is not dict:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        payload = {
            "operation_id": operation_id, "task_digest": reservation["task_digest"],
            "run_digest": reservation["run_digest"], "attempt_id": reservation["attempt_id"],
            "worker_epoch": reservation["worker_epoch"], "operation": "load",
            "completed_step": reservation["completed_step"], "checkpoint_ref": checkpoint_ref,
            "checkpoint_sha256": expected_checkpoint_sha256, "policy_sha256": self.policy.sha256,
            "fingerprints": self._fingerprints,
            "reservation_digest": envelope["payload"].get("reservation_digest"),
        }
        if not _is_hash(payload["reservation_digest"]):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        try:
            verified = training_receipts.verify_training_checkpoint_admission(
                envelope, expected_payload=payload, pinned_public_key=self._pin)
        except training_receipts.TrainingReceiptError:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID") from None
        if type(verified) is not training_receipts.VerifiedTrainingCheckpointAdmission:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        self._resume_reservation = {**reservation, "admission_receipt": verified}
        self._parent_ref = checkpoint_ref
        return reservation["load_root"] / reservation["checkpoint_relative_path"]

    def _prepare_load_metadata(self) -> None:
        """Inspect state only inside the owner's consumed managed load."""
        reservation = self._resume_reservation
        root = reservation["load_root"]
        for parent in [*reversed(root.parents), root]:
            _regular_stat(parent, directory=True)
        checkpoint = root / reservation["checkpoint_relative_path"]
        inspect_checkpoint_files(root, reservation["checkpoint_relative_path"], self.policy)
        position = strict_json((checkpoint / "lumenis_data_position.json").read_bytes())
        observed = strict_json((checkpoint / "lumenis_observed_state.json").read_bytes())
        self._cursor.restore(position)
        if (type(observed) is not dict
                or set(observed) != {"completed_step", "data_position", "optimizer_state_sha256",
                    "scheduler_state_sha256", "rng_state_sha256", "adapter_or_model_state_sha256",
                    "framework_lock_sha256"}
                or type(observed["completed_step"]) is not int
                or observed["completed_step"] != reservation["completed_step"]
                or observed["data_position"] != self._cursor.snapshot()["data_position"]
                or observed["framework_lock_sha256"] != self.policy.document["framework_lock_sha256"]
                or any(not _is_hash(observed[k]) for k in observed if k.endswith("sha256"))):
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        self._expected_restored_state = observed

    def _finish_load(self, trainer) -> None:
        """Measure the actual loaded objects after the framework restores RNG.

        This commits no local truth. The canonical owner validates the managed
        invocation and commits its load record. Lost acknowledgement stops this
        attempt; exact readback belongs to that owner, never a second load.
        """
        if (trainer is not self._trainer or self._failed or self._load_committed
                or not self._load_started or self._resume_reservation is None
                or self._load_components != {"model", "optimizer_scheduler", "scaler", "callback", "rng"}):
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
        try:
            _verify_approval(self._approval_verifier, self._request)
            packages, _ = self._validate_runtime(trainer)
            position = self._cursor.snapshot()
            if (type(trainer.state.global_step) is not int
                    or trainer.state.global_step != self._resume_reservation["completed_step"]
                    or trainer.state.global_step != position["data_position"]["completed_step"]):
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            checkpoint = self._selected_checkpoint()
            callbacks = strict_json((checkpoint / "lumenis_callback_state.json").read_bytes())
            if canonical_bytes(callbacks) != canonical_bytes(trainer.state.stateful_callbacks):
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            observed = self._observe_state(trainer, position, packages)
            if canonical_bytes(observed) != canonical_bytes(self._expected_restored_state):
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            _verify_approval(self._approval_verifier, self._request)
            try:
                receipt = self._client.complete_load(
                    operation_id=self._operation_id, restored_state=copy.deepcopy(observed))
            except TrainingBlocked:
                raise
            except Exception:
                raise TrainingBlocked("CHECKPOINT_COMMIT_UNKNOWN") from None
            self._loaded_handoff = self._accept_resume_receipt(receipt, observed)
            self._load_committed = True
        except TrainingBlocked:
            self._failed = True
            raise

        except OSError:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_STORAGE_UNAVAILABLE") from None
        except Exception:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_LOAD_FAILED") from None
        except BaseException:
            self._failed = True
            raise

    def _validate_loaded_callbacks(self, trainer) -> None:
        """Reject the framework's warning-only missing callback restoration."""
        try:
            callbacks = strict_json((self._selected_checkpoint() / "lumenis_callback_state.json").read_bytes())
            if (type(callbacks) is not dict
                    or canonical_bytes(callbacks) != canonical_bytes(trainer.state.stateful_callbacks)):
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            actual = trainer.callback_handler.callbacks + [trainer.control]
            for name, states in callbacks.items():
                expected = states if type(states) is list else [states]
                instances = [callback for callback in actual if type(callback).__name__ == name]
                if len(instances) != len(expected) or any(not callable(getattr(callback, "state", None)) for callback in instances):
                    raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
                if canonical_bytes([callback.state() for callback in instances]) != canonical_bytes(expected):
                    raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        except BaseException:
            self._failed = True
            raise

    def recovered_phase_client(self, *, transport):
        """Admit the first resumed phase with the owner's actual transport.

        The runtime caller must bind the returned exact TrainingPhaseClient to
        its existing phase callbacks. This is not a public run resume entry or
        permission for loading a worker, creating output, or preparing weights.
        """
        from .owned_training import _verify_training_boundary
        from .owned_training_phases import TrainingPhaseClient

        if (self._failed or not self._load_committed or self._loaded_handoff is None
                or self._recovery_phase_client is not None or not callable(transport)):
            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
        try:
            _verify_approval(self._approval_verifier, self._request)
            client = TrainingPhaseClient.from_recovery_handoff(
                self._request, self._context, handoff=self._loaded_handoff,
                pinned_public_key=self._pin, transport=transport,
                actor_id=self._actor_id, principal=self._principal, public_context=self._public_context)
            _verify_training_boundary(self._approval_verifier, client, self._request, "before_train")
            self._recovery_phase_client = client
            self._recovery_phase_admitted = True
            return client
        except BaseException:
            self._failed = True
            raise

    def _accept_resume_receipt(self, receipt, observed):
        from lumenis.system.security import training_receipts

        if type(receipt) is not dict or set(receipt) != _RESUME_RECEIPT_FIELDS:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        canonical_bytes(receipt)
        reservation = self._resume_reservation
        for key in ("schema_version", "operation_id", "task_digest", "run_digest", "checkpoint_ref", "checkpoint_sha256"):
            if type(receipt[key]) is not type(reservation[key]) or receipt[key] != reservation[key]:
                raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        if (type(receipt["task_step_ref"]) is not str or not receipt["task_step_ref"].strip()
                or type(receipt["restored_state"]) is not dict
                or canonical_bytes(receipt["restored_state"]) != canonical_bytes(observed)):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        _utc_time(receipt["committed_at_utc"])
        envelope = receipt["phase_handoff"]
        payload = envelope.get("payload") if type(envelope) is dict else None
        if type(payload) is not dict or set(payload) != _RECOVERY_HANDOFF_FIELDS:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        record_hash = _digest({key: value for key, value in receipt.items()
                               if key not in {"receipt", "phase_handoff"}})
        expected = {"schema_version": 1, "task_digest": reservation["task_digest"],
            "run_digest": reservation["run_digest"], "attempt_id": reservation["attempt_id"],
            "worker_epoch": reservation["worker_epoch"], "fingerprints": self._fingerprints,
            "checkpoint_ref": reservation["checkpoint_ref"],
            "checkpoint_sha256": reservation["checkpoint_sha256"],
            "load_operation_id": reservation["operation_id"], "resume_receipt_sha256": record_hash,
            "next_phase": "before_train", "admission_version": 3}
        if any(type(payload[key]) is not type(value) or payload[key] != value
               for key, value in expected.items()):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        if (type(payload["task_id"]) is not str
                or re.fullmatch(r"trainrelay_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", payload["task_id"]) is None
                or hashlib.sha256(payload["task_id"].encode()).hexdigest() != reservation["task_digest"]
                or type(payload["next_sequence"]) is not int or payload["next_sequence"] < 1
                or not _is_hash(payload["worker_binding_sha256"])):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        try:
            verified_receipt = training_receipts.verify_training_resume_receipt(
                copy.deepcopy(receipt["receipt"]),
                expected_payload={key: value for key, value in receipt.items() if key != "receipt"},
                pinned_public_key=self._pin)
            if type(verified_receipt) is not training_receipts.VerifiedTrainingResumeReceipt:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
            handoff = training_receipts.verify_training_recovery_handoff(
                copy.deepcopy(envelope), expected_payload=copy.deepcopy(payload), pinned_public_key=self._pin)
        except training_receipts.TrainingReceiptError:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH") from None
        if type(handoff) is not training_receipts.VerifiedTrainingRecoveryHandoff:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        return handoff

    def _bind_trainer(self, trainer) -> None:
        if self._trainer is not None or self._approval_verifier is None:
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        dataset = trainer.train_dataset
        if _ROW_MARKER in dataset.column_names:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        row_hashes = [_digest(dict(row)) for row in dataset]
        cursor = TrainingDataCursor(dataset_sha256=self._request.train_sha256,
            row_sha256=row_hashes,
            gradient_accumulation_steps=recipe_gradient_accumulation_steps(self.policy.document["base_recipe"]),
            base_recipe=self.policy.document["base_recipe"])
        original_collator = trainer.data_collator

        def collate(rows):
            if type(rows) is not list or len(rows) != 1:
                raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
            row = dict(rows[0])
            index = row.pop(_ROW_MARKER, None)
            if type(index) is not int or not 0 <= index < len(row_hashes):
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            observed = _digest(row)
            if observed != row_hashes[index]:
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            batch = original_collator([row])
            if type(batch) is not dict or _ROW_MARKER in batch:
                raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE")
            batch[_ROW_MARKER] = (index, observed)
            return batch

        self._trainer, self._cursor = trainer, cursor
        self._validate_runtime(trainer)
        trainer.train_dataset = dataset.add_column(_ROW_MARKER, list(range(len(dataset))))
        trainer.data_collator = collate

    def _validate_runtime(self, trainer) -> tuple[dict, dict]:
        from importlib.metadata import PackageNotFoundError

        try:
            packages = {name: version(name) for name in sorted(_FRAMEWORK_PACKAGES)}
        except PackageNotFoundError:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH") from None
        config = trainer_checkpoint_config(trainer, base_recipe=self.policy.document["base_recipe"])
        self.policy.validate_runtime(
            framework_versions=packages, trainer_config=config,
            data_order=self._cursor.data_order,
            scaler_present=getattr(trainer.accelerator, "scaler", None) is not None,
        )
        if trainer.args.save_steps != self.policy.document["checkpoint_interval_steps"]:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        return packages, config

    def complete_optimizer_step(self, trainer, control):
        if trainer is not self._trainer or self._failed:
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        self._cursor.complete_optimizer_step(
            trainer.state.global_step, sync_gradients=trainer.accelerator.sync_gradients,
            optimizer_step_was_skipped=trainer.accelerator.optimizer_step_was_skipped,
        )
        state = self._cursor.snapshot()
        if state["data_position"]["next_batch_index"] == len(trainer.train_dataset):
            control.should_save = True
        return control

    def _admit_save(self, step: int) -> dict:
        from lumenis.system.security import training_receipts

        _verify_approval(self._approval_verifier, self._request)
        reservation = self._client.reserve_save(
            operation_id=self._operation_id, completed_step=step, parent_ref=self._parent_ref,
        )
        if type(reservation) is not dict or set(reservation) != _SAVE_RESERVATION_FIELDS:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        expected = {"schema_version": 1, "operation_id": self._operation_id,
                    "completed_step": step, "parent_ref": self._parent_ref,
                    "policy_sha256": self.policy.sha256, "fingerprints": self._fingerprints}
        if any(type(reservation[k]) is not type(v) or reservation[k] != v for k, v in expected.items()):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        if (not _is_hash(reservation["task_digest"]) or not _is_hash(reservation["origin_run_digest"])
                or not _uuid4(reservation["attempt_id"])
                or type(reservation["worker_epoch"]) is not int or reservation["worker_epoch"] < 0
                or reservation["checkpoint_relative_path"] != f"checkpoint-{step}"
                or type(reservation["staging_root"]) is not type(Path())
                or not reservation["staging_root"].is_absolute()):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        admission = reservation["admission_receipt"]
        if type(admission) is not training_receipts.VerifiedTrainingCheckpointAdmission:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        envelope = admission.envelope
        if type(envelope) is not dict or type(envelope.get("payload")) is not dict:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        payload = {"operation_id": self._operation_id, "task_digest": reservation["task_digest"],
                   "run_digest": reservation["origin_run_digest"], "attempt_id": reservation["attempt_id"],
                   "worker_epoch": reservation["worker_epoch"], "operation": "save", "completed_step": step,
                   "checkpoint_ref": None, "checkpoint_sha256": None, "policy_sha256": self.policy.sha256,
                   "fingerprints": self._fingerprints,
                   "reservation_digest": envelope["payload"].get("reservation_digest")}
        if not _is_hash(payload["reservation_digest"]):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        try:
            verified = training_receipts.verify_training_checkpoint_admission(
                envelope, expected_payload=payload, pinned_public_key=self._pin,
            )
        except training_receipts.TrainingReceiptError:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID") from None
        if type(verified) is not training_receipts.VerifiedTrainingCheckpointAdmission:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        root = reservation["staging_root"]
        for parent in [*reversed(root.parents), root]:
            _regular_stat(parent, directory=True)
        if any(root.iterdir()):
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        if _utc_time(reservation["write_deadline_utc"]) <= datetime.now(timezone.utc):
            raise TrainingBlocked("CHECKPOINT_WRITE_EXPIRED")
        _verify_approval(self._approval_verifier, self._request)
        # This owner check binds the signed reservation_digest to the actual
        # storage root, live worker, Task and Permission immediately before IO.
        self._client.require_current_admission(verified, request=self._request, operation="save")
        return reservation

    def _save_checkpoint(self, trainer, save) -> None:
        if trainer is not self._trainer or self._failed:
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        position = self._cursor.snapshot()
        step = position["data_position"]["completed_step"]
        if step != trainer.state.global_step or step <= self._last_saved_step:
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        packages, config = self._validate_runtime(trainer)
        self._operation_id = str(uuid.uuid4())
        original_output = trainer.args.output_dir
        try:
            reservation = self._admit_save(step)
            # TRL creates README.md before delegating to Transformers. Redirect
            # its entire output root before entering either framework method.
            trainer.args.output_dir = str(reservation["staging_root"])
            save()
            checkpoint = reservation["staging_root"] / reservation["checkpoint_relative_path"]
            self._write_observations(trainer, checkpoint, position, packages)
            if _utc_time(reservation["write_deadline_utc"]) <= datetime.now(timezone.utc):
                raise TrainingBlocked("CHECKPOINT_WRITE_EXPIRED")
            inventory = {
                "schema_version": 1, "operation_id": self._operation_id, "completed_step": step,
                "checkpoint_relative_path": reservation["checkpoint_relative_path"],
                "policy_sha256": self.policy.sha256, "fingerprints": self._fingerprints,
                "framework_versions": packages, "trainer_config_sha256": _digest(config),
                "data_order_sha256": _digest(self._cursor.data_order),
                "data_position": position["data_position"],
                "files": inspect_checkpoint_files(reservation["staging_root"],
                                                   reservation["checkpoint_relative_path"], self.policy),
            }
            canonical_bytes(inventory)
            _verify_approval(self._approval_verifier, self._request)
            try:
                receipt = self._client.commit_save(operation_id=self._operation_id, inventory=inventory)
            except TrainingBlocked:
                raise
            except Exception:
                raise TrainingBlocked("CHECKPOINT_COMMIT_UNKNOWN") from None
            self._accept_save_receipt(receipt, reservation, inventory)
            self._last_committed_checkpoint = copy.deepcopy(receipt)
            self._parent_ref = receipt["artifact_ref"]
            self._last_saved_step = step
        except TrainingBlocked:
            self._failed = True
            raise
        except OSError:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_STORAGE_UNAVAILABLE") from None
        except Exception:
            self._failed = True
            raise TrainingBlocked("CHECKPOINT_STATE_INCOMPLETE") from None
        except BaseException:
            self._failed = True
            raise
        finally:
            trainer.args.output_dir = original_output

    def _observe_state(self, trainer, position: dict, packages: dict) -> dict:
        import random
        import numpy as np
        import torch
        from peft import get_peft_model_state_dict

        cuda_rng = torch.cuda.get_rng_state(0)
        scaler = getattr(trainer.accelerator, "scaler", None)
        return {
            "completed_step": trainer.state.global_step, "data_position": position["data_position"],
            "optimizer_state_sha256": training_state_sha256({
                "optimizer": trainer.optimizer.state_dict(),
                "scaler": None if scaler is None else scaler.state_dict(),
            }),
            "scheduler_state_sha256": training_state_sha256(trainer.lr_scheduler.state_dict()),
            "rng_state_sha256": training_state_sha256({"python": random.getstate(),
                "numpy": np.random.get_state(), "cpu": torch.get_rng_state(), "cuda:0": cuda_rng}),
            "adapter_or_model_state_sha256": training_state_sha256(get_peft_model_state_dict(trainer.model)),
            "framework_lock_sha256": _digest(packages),
        }

    def _write_observations(self, trainer, checkpoint: Path, position: dict, packages: dict) -> None:
        import torch
        from safetensors.torch import save_file

        observed = self._observe_state(trainer, position, packages)
        cuda_rng = torch.cuda.get_rng_state(0)
        _regular_stat(checkpoint, directory=True)
        for name, material in (("lumenis_data_position.json", position),
                               ("lumenis_callback_state.json", trainer.state.stateful_callbacks),
                               ("lumenis_observed_state.json", observed)):
            with (checkpoint / name).open("xb") as stream:
                stream.write(canonical_bytes(material))
        target = checkpoint / "lumenis_cuda_rng.safetensors"
        if target.exists() or target.is_symlink():
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        save_file({"cuda:0": cuda_rng}, str(target))

    def _accept_save_receipt(self, receipt, reservation, inventory) -> None:
        from lumenis.system.security import training_receipts

        if type(receipt) is not dict or set(receipt) != _SAVE_RECEIPT_FIELDS:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        for key in ("schema_version", "operation_id", "task_digest", "origin_run_digest", "attempt_id",
                    "worker_epoch", "fingerprints", "policy_sha256", "completed_step", "parent_ref"):
            if type(receipt[key]) is not type(reservation[key]) or receipt[key] != reservation[key]:
                raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        if (receipt["inventory_sha256"] != _digest(inventory) or not _is_hash(receipt["artifact_sha256"])
                or type(receipt["artifact_ref"]) is not str
                or re.fullmatch(r"ART-[0-9a-f]{16}", receipt["artifact_ref"]) is None
                or type(receipt["artifact_version"]) is not int or receipt["artifact_version"] < 1):
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        try:
            verified = training_receipts.verify_training_checkpoint_receipt(
                receipt["receipt"], expected_payload={k: v for k, v in receipt.items() if k != "receipt"},
                pinned_public_key=self._pin,
            )
        except training_receipts.TrainingReceiptError:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH") from None
        if type(verified) is not training_receipts.VerifiedTrainingCheckpointReceipt:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
