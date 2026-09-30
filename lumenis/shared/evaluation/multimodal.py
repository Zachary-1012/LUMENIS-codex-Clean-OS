"""Evidence-aware acceptance helpers for image, video, audio and document work.

The model may describe or transform a media input, but a non-empty model reply is
not a product result.  This module keeps the acceptance boundary in Shared
Evaluation: the input must identify its source and Evidence, and the derived
result must state whether it is complete, unavailable or failed.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional


SUPPORTED_INPUT_KINDS: FrozenSet[str] = frozenset({"image", "video", "audio", "document"})
VALID_ANALYSIS_STATES: FrozenSet[str] = frozenset({"complete", "unavailable", "error"})


@dataclass(frozen=True)
class MultimodalInput:
    """A source-backed media/document input presented to an AI capability."""

    input_id: str
    kind: str
    source_ref: str
    evidence_ref: str
    captured_at: Optional[str] = None
    content_sha256: Optional[str] = None

    @classmethod
    def from_bytes(
        cls,
        *,
        input_id: str,
        kind: str,
        source_ref: str,
        evidence_ref: str,
        payload: bytes,
        captured_at: Optional[str] = None,
    ) -> "MultimodalInput":
        """Bind the input to bytes actually supplied to an analyzer.

        The payload is hashed and never retained by this contract. Callers that
        only have a reference must leave the digest absent and cannot claim a
        completed analysis.
        """
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("MULTIMODAL_INPUT_BYTES_REQUIRED")
        return cls(
            input_id=input_id,
            kind=kind,
            source_ref=source_ref,
            evidence_ref=evidence_ref,
            captured_at=captured_at,
            content_sha256=hashlib.sha256(payload).hexdigest(),
        )

    def validation_errors(self) -> tuple[str, ...]:
        errors = []
        if not isinstance(self.input_id, str) or not self.input_id.strip():
            errors.append("INPUT_ID_REQUIRED")
        if self.kind not in SUPPORTED_INPUT_KINDS:
            errors.append("INPUT_KIND_UNSUPPORTED")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip():
            errors.append("SOURCE_REF_REQUIRED")
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref.strip():
            errors.append("EVIDENCE_REF_REQUIRED")
        if not isinstance(self.content_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.content_sha256
        ):
            errors.append("INPUT_CONTENT_HASH_REQUIRED")
        return tuple(errors)


def assess_multimodal_result(
    media_input: MultimodalInput,
    *,
    analysis_state: str,
    result_ref: str = "",
    grounded_in_evidence: bool = False,
    human_reviewed: bool = False,
    analysis_execution_ref: str = "",
    analysis_input_sha256: str = "",
) -> Dict[str, Any]:
    """Return an honest acceptance assessment without writing Production Truth.

    ``accepted`` is reserved for a complete, source-backed result.  An explicit
    unavailable/error state is returned to the caller and never converted to a
    false success.
    """

    state = str(analysis_state or "").strip().lower()
    errors = list(media_input.validation_errors())
    if state not in VALID_ANALYSIS_STATES:
        errors.append("ANALYSIS_STATE_INVALID")
    if state == "complete" and (not isinstance(result_ref, str) or not result_ref.strip()):
        errors.append("RESULT_REF_REQUIRED")
    if state == "complete" and not grounded_in_evidence:
        errors.append("EVIDENCE_GROUNDING_REQUIRED")
    if state == "complete" and not str(analysis_execution_ref or "").strip():
        errors.append("ANALYSIS_EXECUTION_REF_REQUIRED")
    if state == "complete":
        if not re.fullmatch(r"[0-9a-f]{64}", str(analysis_input_sha256 or "")):
            errors.append("ANALYSIS_INPUT_HASH_REQUIRED")
        elif analysis_input_sha256 != media_input.content_sha256:
            errors.append("ANALYSIS_INPUT_HASH_MISMATCH")

    accepted = state == "complete" and not errors
    return {
        "accepted": accepted,
        "state": state if state in VALID_ANALYSIS_STATES else "error",
        "input_id": media_input.input_id,
        "input_kind": media_input.kind,
        "source_ref": media_input.source_ref,
        "evidence_ref": media_input.evidence_ref,
        "input_content_sha256": media_input.content_sha256,
        "analysis_execution_ref": str(analysis_execution_ref or "").strip(),
        "analysis_input_sha256": str(analysis_input_sha256 or "").strip(),
        "result_ref": result_ref,
        "grounded_in_evidence": bool(grounded_in_evidence),
        "human_reviewed": bool(human_reviewed),
        "errors": errors,
    }
