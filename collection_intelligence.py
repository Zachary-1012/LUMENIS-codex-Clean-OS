"""Collection Intelligence helpers for Phase 2.

Pure functions only: no network access and no writes to the production DB.
They distinguish unavailable/failed/not-applicable fields and bridge collected
notes/comments into the shadow Context Intelligence layer.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable

from context_intelligence import analyze_context

FIELDS = (
    "note_id", "title", "content", "publish_date", "url", "author_id",
    "author_nickname", "likes", "comments", "collects", "shares",
    "comment_list", "cover",
)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def field_state(note: Dict[str, Any], field: str) -> str:
    """Return PRESENT / EMPTY / NOT_APPLICABLE / UNKNOWN.

    A separate collector failure state can be supplied through `collection_state`
    and is intentionally not converted to EMPTY.
    """
    if field not in note:
        return "UNKNOWN"
    if note.get("collection_state") in {"BLOCKED", "AUTH_REQUIRED", "CAPTCHA", "NETWORK_ERROR"}:
        return note["collection_state"]
    if note.get(f"{field}_not_applicable"):
        return "NOT_APPLICABLE"
    return "PRESENT" if _present(note.get(field)) else "EMPTY"


def completeness(note: Dict[str, Any], fields: Iterable[str] = FIELDS) -> Dict[str, Any]:
    fields = list(fields)
    states = {field: field_state(note, field) for field in fields}
    applicable = [x for x in states.values() if x != "NOT_APPLICABLE"]
    present = sum(x == "PRESENT" for x in applicable)
    score = round(present / len(applicable), 4) if applicable else 1.0
    return {
        "schema_version": "collection-quality.v1",
        "score": score,
        "present": present,
        "applicable": len(applicable),
        "states": states,
        "collection_state": note.get("collection_state", "SUCCESS"),
    }


def context_shadow(note: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze already-collected public note/comment context without side effects."""
    return analyze_context(note, note.get("comment_list") or [])


def quality_envelope(note: Dict[str, Any]) -> Dict[str, Any]:
    quality = completeness(note)
    return {
        "collection_quality": quality,
        "context_shadow": context_shadow(note),
        "provenance": {
            "source_channel": note.get("source_channel", "unknown"),
            "authoritative_source": True,
            "derived_context_authoritative": False,
        },
    }
