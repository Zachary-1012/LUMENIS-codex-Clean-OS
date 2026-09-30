"""Evidence-aware acceptance helpers for image, video, audio and document work.

The model may describe or transform a media input, but a non-empty model reply is
not a product result.  This module keeps the acceptance boundary in Shared
Evaluation: the input must identify its source and Evidence, and the derived
result must state whether it is complete, unavailable or failed.
"""
from __future__ import annotations

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

    def validation_errors(self) -> tuple[str, ...]:
        errors = []
        if not self.input_id.strip():
            errors.append("INPUT_ID_REQUIRED")
        if self.kind not in SUPPORTED_INPUT_KINDS:
            errors.append("INPUT_KIND_UNSUPPORTED")
        if not self.source_ref.strip():
            errors.append("SOURCE_REF_REQUIRED")
        if not self.evidence_ref.strip():
            errors.append("EVIDENCE_REF_REQUIRED")
        return tuple(errors)


def assess_multimodal_result(
    media_input: MultimodalInput,
    *,
    analysis_state: str,
    result_ref: str = "",
    grounded_in_evidence: bool = False,
    human_reviewed: bool = False,
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
    if state == "complete" and not result_ref.strip():
        errors.append("RESULT_REF_REQUIRED")
    if state == "complete" and not grounded_in_evidence:
        errors.append("EVIDENCE_GROUNDING_REQUIRED")

    accepted = state == "complete" and not errors
    return {
        "accepted": accepted,
        "state": state if state in VALID_ANALYSIS_STATES else "error",
        "input_id": media_input.input_id,
        "input_kind": media_input.kind,
        "source_ref": media_input.source_ref,
        "evidence_ref": media_input.evidence_ref,
        "result_ref": result_ref,
        "grounded_in_evidence": bool(grounded_in_evidence),
        "human_reviewed": bool(human_reviewed),
        "errors": errors,
    }
