"""Report-only held-out evaluation for an exact locally trained AI Gateway candidate.

Inference is supplied by an already loaded local runtime. This module owns no
provider, model loader, persistence, business verdict, or promotion path.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from . import owned_training

_TERMINATORS = frozenset({"<|return|>", "<|fim_suffix|>"})
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_CITATION = re.compile(r"\[\[([^\[\]\r\n]+)\]\]")
_FINAL_HEADER = re.compile(
    r"(?:<\|start\|>|<\|im_start\|>)assistant<\|channel\|>final<\|message\|>"
    r"|<\|channel\|>final<\|message\|>"
    r"|<\|assistant\|>(?:<\|channel\|>)?final(?:[ \t\r\n]|$)"
)
_CHANNEL_MARKER = re.compile(r"<\|(?:start|im_start|assistant|channel|message|meta_sep)\|>")
_STATUS_IDENTITY = (
    "status", "model_id", "model_revision", "training_recipe", "base_revision_state",
    "manifest_sha256", "train_sha256", "heldout_sha256", "train_case_count",
    "heldout_case_count", "scopes", "domain_id",
)

BUSINESS_REVIEW_RUBRIC = (
    ("TASK_AND_SCOPE", "Does the result answer the actual held-out job for this exact CTH/BMP scope?"),
    ("EVIDENCE_GROUNDING", "Does each material claim follow from the cited source Evidence, with unsupported claims marked unknown?"),
    ("DELIVERABLE_COMPLETENESS", "Does it provide the requested decision or artifact, required entities, period, and next step?"),
    ("UNKNOWN_VS_ZERO", "Does it preserve 0, NULL, UNKNOWN, NOT_COLLECTED, STALE, OFFLINE, ERROR, and BLOCKED as distinct states?"),
    ("BUSINESS_ACTIONABILITY", "Are rationale, constraints, alternatives, risks, and an executable next action clear?"),
    ("PERMISSION_AND_RIGHTS", "Does it stay within the approved scope and avoid unsupported rights or external effects?"),
    ("LIMITS_AND_RECOVERY", "Are material uncertainty, stop conditions, and failure or recovery needs explicit?"),
)


class CandidateEvaluationBlocked(RuntimeError):
    """The candidate or held-out request does not match its pinned identity."""


@dataclass(frozen=True)
class CandidateInferenceRequest:
    candidate_identity_sha256: str
    model_id: str
    model_revision: str
    training_recipe: str
    manifest_sha256: str
    train_sha256: str
    heldout_sha256: str
    adapter_sha256: str
    adapter_config_sha256: str
    case_id: str
    domain_id: str
    scope: str
    source_evidence_refs: tuple[str, ...]
    user_messages: tuple[str, ...]
    max_new_tokens: int
    local_only: bool = True
    network_access: bool = False
    fallback_allowed: bool = False


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _parse_final(
    raw: object, finish_reason: object = None, termination_token: object = None,
    final_channel_prefill: object = False,
) -> tuple[str, str]:
    if not isinstance(raw, str) or not raw.strip():
        return "", "OUTPUT_MISSING"
    if termination_token not in _TERMINATORS:
        return "", "TERMINATION_TOKEN_UNSPECIFIED_OR_UNSUPPORTED"
    if type(final_channel_prefill) is not bool:
        return "", "FINAL_CHANNEL_PREFILL_METADATA_INVALID"
    if finish_reason is not None and str(finish_reason).lower() not in {"return", "eos", "stop"}:
        return "", "GENERATION_NOT_COMPLETE"
    source = raw.rstrip()
    if not source.endswith(termination_token) or source.count(termination_token) != 1:
        return "", "CONFIGURED_TERMINATION_MISSING_OR_TRUNCATED"
    body = source[:-len(termination_token)].rstrip()
    headers = list(_FINAL_HEADER.finditer(body))
    if headers:
        final = body[headers[-1].end():].strip()
    elif _CHANNEL_MARKER.search(body):
        return "", "FINAL_CHANNEL_MISSING"
    elif final_channel_prefill:
        final = body.strip()
    else:
        return "", "FINAL_CHANNEL_OR_PREFILL_MISSING"
    if not final or _CHANNEL_MARKER.search(final) or any(
        token in final for token in ("<|end|>", "<|ghissue|>", "<|call|>")
    ):
        return "", "FINAL_CHANNEL_EMPTY_OR_INVALID"
    return final, "COMPLETED_FINAL"


def _read_heldout(path: Path, expected_sha256: str) -> list[tuple[dict, str, str]]:
    data = path.read_bytes()
    if _hash_bytes(data) != expected_sha256:
        raise CandidateEvaluationBlocked("HELDOUT_DATASET_CHANGED_DURING_PREFLIGHT")
    rows = []
    for line in data.splitlines(keepends=True):
        if not line.strip():
            continue
        try:
            record = json.loads(line.decode("utf-8"))
            _, prompt = owned_training._validate_record(record)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise CandidateEvaluationBlocked("HELDOUT_RECORD_INVALID") from exc
        messages = tuple(
            message["content"].strip() for message in record["messages"]
            if message["role"] == "user"
        )
        rows.append((record, prompt, _hash_bytes(line)))
        record["_evaluation_user_messages"] = messages
    return rows


def evaluate_owned_candidate(
    model_snapshot_dir: str | Path,
    train_jsonl_path: str | Path,
    heldout_jsonl_path: str | Path,
    candidate_output_dir: str | Path,
    *,
    manifest_path: str | Path,
    expected_adapter_sha256: str,
    expected_adapter_config_sha256: str,
    local_infer: Callable[[CandidateInferenceRequest], object],
    recipe: str = owned_training.H100_RECIPE,
    max_new_tokens: int = 1024,
) -> dict[str, object]:
    """Evaluate held-out prompts through a caller-supplied local runtime.

    This returns structural observations and a human review packet only. A
    callable's presence or output does not prove runtime locality or business
    quality; promotion and acceptance are never performed here.
    """
    if not callable(local_infer):
        raise CandidateEvaluationBlocked("LOCAL_INFERENCE_CALLABLE_REQUIRED")
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 4096:
        raise ValueError("max_new_tokens must be an integer from 1 through 4096")
    for digest in (expected_adapter_sha256, expected_adapter_config_sha256):
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise CandidateEvaluationBlocked("EXPECTED_ADAPTER_HASH_REQUIRED")

    output = owned_training._local_path(candidate_output_dir)
    if Path(candidate_output_dir).is_symlink() or not output.is_dir():
        raise CandidateEvaluationBlocked("TRAINED_CANDIDATE_OUTPUT_DIRECTORY_REQUIRED")
    status_path = output / "training_status.json"
    adapter_path = output / "adapter_model.safetensors"
    config_path = output / "adapter_config.json"
    if any(path.is_symlink() or not path.is_file() for path in (status_path, adapter_path, config_path)):
        raise CandidateEvaluationBlocked("TRAINED_CANDIDATE_ARTIFACT_MISSING_OR_SYMLINKED")

    preflight_path = output.parent / f".{output.name}.owned-evaluation-preflight-unused"
    if preflight_path.exists() or preflight_path.is_symlink():
        raise CandidateEvaluationBlocked("PREFLIGHT_OUTPUT_PATH_ALREADY_EXISTS")
    preflight = owned_training.run_owned_lora_training(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, preflight_path,
        manifest_path=manifest_path, execute=False, recipe=recipe,
    )
    status_bytes = status_path.read_bytes()
    try:
        training_status = json.loads(status_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateEvaluationBlocked("TRAINING_STATUS_INVALID") from exc
    if not isinstance(training_status, dict) or any(
        training_status.get(key) != preflight.get(key) for key in _STATUS_IDENTITY
    ) or training_status.get("execution_state") != "TRAINED_NOT_EVALUATED" \
            or training_status.get("candidate_status") != "NOT_EVALUATED":
        raise CandidateEvaluationBlocked("TRAINING_STATUS_IDENTITY_MISMATCH_OR_NOT_TRAINED")

    adapter_sha, config_sha = _hash_file(adapter_path), _hash_file(config_path)
    if adapter_sha != expected_adapter_sha256 or config_sha != expected_adapter_config_sha256:
        raise CandidateEvaluationBlocked("ADAPTER_HASH_MISMATCH")
    rows = _read_heldout(Path(heldout_jsonl_path), str(preflight["heldout_sha256"]))
    if len(rows) != preflight["heldout_case_count"]:
        raise CandidateEvaluationBlocked("HELDOUT_CASE_COUNT_MISMATCH")

    identity = {key: preflight[key] for key in _STATUS_IDENTITY}
    identity.update({
        "execution_state": training_status["execution_state"],
        "candidate_status": training_status["candidate_status"],
        "training_status_sha256": _hash_bytes(status_bytes),
        "adapter_sha256": adapter_sha,
        "adapter_config_sha256": config_sha,
    })
    candidate_id = _hash_bytes(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())
    results = []
    for record, prompt, record_sha in rows:
        request = CandidateInferenceRequest(
            candidate_id, str(preflight["model_id"]), str(preflight["model_revision"]),
            str(preflight["training_recipe"]), str(preflight["manifest_sha256"]),
            str(preflight["train_sha256"]), str(preflight["heldout_sha256"]),
            adapter_sha, config_sha, record["case_id"],
            str(record["domain"]).strip().lower().replace("zbmp", "bmp"), record["scope"],
            tuple(record["source_evidence_refs"]), tuple(record["_evaluation_user_messages"]),
            max_new_tokens,
        )
        terminator = ""
        try:
            response = local_infer(request)
            if isinstance(response, Mapping):
                raw = response.get("generated_text", response.get("text"))
                finish = response.get("finish_reason")
                terminator = response.get("termination_token")
                final_prefill = response.get("final_channel_prefill", False)
                if response.get("error"):
                    raise RuntimeError("LOCAL_INFERENCE_REPORTED_ERROR")
            else:
                raw, finish, terminator, final_prefill = response, None, None, False
            final, completion = _parse_final(raw, finish, terminator, final_prefill)
        except Exception as exc:
            raw, final, completion = None, "", "INFERENCE_ERROR:" + type(exc).__name__
        raw_hash = _hash_bytes(raw.encode("utf-8")) if isinstance(raw, str) else ""
        citations = _CITATION.findall(final)
        source_refs = tuple(record["source_evidence_refs"])
        known = sorted({ref for ref in citations if ref in source_refs})
        unknown = sorted({ref for ref in citations if ref not in source_refs})
        results.append({
            "case_id": record["case_id"], "domain_id": request.domain_id, "scope": record["scope"],
            "source_evidence_refs": list(source_refs),
            "heldout_origin": {"dataset_role": "heldout", "dataset_sha256": preflight["heldout_sha256"],
                               "record_sha256": record_sha},
            "prompt_sha256": _hash_bytes(prompt.encode("utf-8")),
            "completion_state": completion, "final_text": final, "raw_output_sha256": raw_hash,
            "citation_state": "PRESENT" if known else "UNRESOLVED" if citations else "MISSING",
            "termination_token": terminator if isinstance(terminator, str) else "",
            "cited_source_refs": known, "unresolved_citation_refs": unknown,
            "business_review": {"state": "HUMAN_REVIEW_REQUIRED",
                                "criteria": {key: "PENDING" for key, _ in BUSINESS_REVIEW_RUBRIC}},
        })

    if _hash_file(status_path) != identity["training_status_sha256"] \
            or _hash_file(adapter_path) != adapter_sha or _hash_file(config_path) != config_sha:
        raise CandidateEvaluationBlocked("CANDIDATE_ARTIFACT_CHANGED_DURING_EVALUATION")
    if _hash_file(Path(train_jsonl_path)) != preflight["train_sha256"] \
            or _hash_file(Path(heldout_jsonl_path)) != preflight["heldout_sha256"]:
        raise CandidateEvaluationBlocked("DATASET_CHANGED_DURING_EVALUATION")

    all_complete = all(item["completion_state"] == "COMPLETED_FINAL" for item in results)
    return {
        "evaluation_status": "STRUCTURAL_OUTPUTS_CAPTURED" if all_complete else "INCOMPLETE_OUTPUTS_RECORDED",
        "candidate_status": "NOT_ACCEPTED", "business_acceptance": "HUMAN_REVIEW_REQUIRED",
        "runtime_verification": "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED",
        "generation_config": {"max_new_tokens": max_new_tokens,
                              "accepted_termination_tokens": sorted(_TERMINATORS)},
        "promotion_status": "NOT_PROMOTED", "candidate_identity": identity,
        "candidate_identity_sha256": candidate_id,
        "heldout_case_count": len(results), "completed_final_count": sum(
            item["completion_state"] == "COMPLETED_FINAL" for item in results
        ),
        "business_review_rubric": [{"criterion": key, "question": question}
                                   for key, question in BUSINESS_REVIEW_RUBRIC],
        "cases": results,
    }
