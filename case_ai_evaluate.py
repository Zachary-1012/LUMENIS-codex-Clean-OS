"""Case score estimates through the existing source-authorized Owned Gateway.

The caller supplies a server-held request over the complete current Case and
permitted materials. Scores are derivative estimates, never observed outcomes.
Local template suggestions remain usable without inference.
"""
from __future__ import annotations

import hashlib
import json
import math
import re


OPERATION = "case_evaluate"
VERSION = "cth-case-evaluation/1"
_DIMENSIONS = ("impact", "innovation", "replicability", "risk")
# Historical import compatibility only. These functions never inspect a secret
# or call the retired provider, even when an old caller invokes them directly.
_ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


def _get_zhipu_key():
    return ""


def _chat(prompt, max_tokens=1000):
    return ""


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _num(value):
    """Return only a finite score in the declared range; unknown stays unknown."""
    if type(value) not in (int, float) or not 0 <= value <= 10:
        return None
    return float(value) if math.isfinite(value) else None


def _clamp(value):
    # Retain the old callable without silently repairing an invalid estimate.
    return _num(value)


def case_evaluation_schema():
    number = {"type": "number", "minimum": 0, "maximum": 10}
    return {"type": "object", "properties": {
        **{key: dict(number) for key in _DIMENSIONS},
        "advice": {"type": "string", "minLength": 1, "maxLength": 800},
    }, "required": [*_DIMENSIONS, "advice"], "additionalProperties": False}


def _unavailable(status="UNAVAILABLE", code="CASE_OWNED_REQUEST_REQUIRED"):
    return {"enabled": False, "status": status, "code": code,
            "score": {key: None for key in (*_DIMENSIONS, "overall")},
            "advice": "", "error": code, "provider": "owned", "version": VERSION,
            "claim_type": "INFERRED", "evaluation_state": "NOT_RUN",
            "quality_state": "NOT_EVALUATED", "product_acceptance": False,
            "provenance": None}


def _case_request(case, request):
    """Validate the domain input, without manufacturing source-use permission."""
    from cth_cases import _scope, get_cth_case
    from lumenis.system.ai_gateway.owned_service import (
        _strict_json, validate_owned_service_request,
    )

    schema = validate_owned_service_request(request)
    if not isinstance(case, dict):
        raise ValueError("CASE_SNAPSHOT_REQUIRED")
    scope = case.get("scope")
    _scope(scope)
    if (request.operation != OPERATION or request.domain_id != "cth"
            or request.scope != scope["subject_id"]
            or schema != case_evaluation_schema()):
        raise ValueError("CASE_REQUEST_BINDING_INVALID")
    # Freeze nested data before invoking any reader or executor. Neither a
    # mutable caller object nor an edited Case can change an in-flight input.
    snapshot = json.loads(_json(case))
    current = get_cth_case(snapshot.get("case_id"), actor_ref=request.actor_ref,
                           expected_scope=scope)
    if _json(current) != _json(snapshot):
        raise PermissionError("CASE_SNAPSHOT_CHANGED")
    payload = _strict_json(request.user_payload)
    if (type(payload) is not dict or set(payload) != {"case", "materials"}
            or _json(payload["case"]) != _json(snapshot)
            or hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
            != request.input_revision_sha256):
        raise ValueError("CASE_INPUT_REVISION_INVALID")
    refs = snapshot.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("CASE_SOURCE_REFS_REQUIRED")
    source_ids = [ref["source_id"] for ref in refs]
    materials = payload["materials"]
    if not isinstance(materials, list) or len(materials) != len(source_ids):
        raise ValueError("CASE_MATERIALS_REQUIRED")
    material_ids = []
    for material in materials:
        if (not isinstance(material, dict)
                or not isinstance(material.get("source_id"), str)
                or not isinstance(material.get("text"), str) or not material["text"].strip()
                or not isinstance(material.get("content_evidence_ref"), str)
                or material["content_evidence_ref"] not in request.source_evidence_refs
                or not isinstance(material.get("body_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", material["body_sha256"])):
            raise ValueError("CASE_MATERIALS_INVALID")
        material_ids.append(material["source_id"])
    if len(set(source_ids)) != len(source_ids) or sorted(material_ids) != sorted(source_ids):
        raise ValueError("CASE_SOURCE_BINDING_INVALID")
    # Text, ranges, original hash, rights and current source withdrawal are
    # verified by the existing Gateway's server-held SourceUse validator.
    return snapshot


def _provenance(result, request):
    # Reuse Reporting's existing consumer validation of Gateway receipts and
    # budget/version pins. This helper performs no source or permission grant.
    from lumenis.shared.reporting.business_brief import _owned_result_provenance

    return _owned_result_provenance(result, request)


def evaluate_case(case, *, request=None, is_cancelled=None):
    """Evaluate one current Case; ordinary legacy calls return explicit state.

    Only the server's existing source-use/admission path may issue ``request``.
    The evaluator neither builds permissions nor binds an executor. The current
    Case is re-read on both sides of inference; a changed/withdrawn source cannot
    leave a usable score behind.
    """
    from case_templates import match_templates

    case_fields = case if isinstance(case, dict) else {}
    keywords = " ".join(str(case_fields.get(key) or "")
                        for key in ("title", "question", "case_title", "case_type", "industry"))
    output = {"ai": _unavailable(), "templates": match_templates(keywords, limit=2),
              "templates_state": "LOCAL_ADVISORY", "templates_are_evidence": False}
    if request is None:
        return output
    try:
        snapshot = _case_request(case, request)
        from cth_cases import get_cth_case
        from lumenis.system.ai_gateway import core

        result = core.run_owned_request(request, is_cancelled=is_cancelled)
        current = get_cth_case(snapshot["case_id"], actor_ref=request.actor_ref,
                               expected_scope=snapshot["scope"])
        if _json(current) != _json(snapshot):
            raise PermissionError("CASE_SNAPSHOT_CHANGED")
        if not isinstance(result, dict) or result.get("ok") is not True:
            status = result.get("status") if isinstance(result, dict) else None
            code = result.get("code") if isinstance(result, dict) else None
            if status not in {"UNAVAILABLE", "BLOCKED", "ERROR", "INVALID_INPUT", "CANCELLED"}:
                status = "ERROR"
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", code):
                code = "CASE_OWNED_EXECUTION_FAILED"
            output["ai"] = _unavailable(status, code)
            return output
        provenance = _provenance(result, request)
        analysis = result.get("analysis")
        if not isinstance(analysis, dict) or set(analysis) != {*_DIMENSIONS, "advice"}:
            raise ValueError("CASE_ESTIMATE_INVALID")
        scores = {key: _num(analysis[key]) for key in _DIMENSIONS}
        advice = analysis["advice"]
        if (any(value is None for value in scores.values())
                or not isinstance(advice, str) or not advice.strip() or len(advice) > 800):
            raise ValueError("CASE_ESTIMATE_INVALID")
        scores["overall"] = round((scores["impact"] + scores["innovation"]
            + scores["replicability"] + (10 - scores["risk"])) / 4, 1)
        output["ai"] = {**_unavailable(), "enabled": True, "status": "COMPLETED",
            "code": "CASE_ESTIMATE_COMPLETED", "score": scores,
            "advice": advice, "error": "", "provenance": provenance}
    except PermissionError:
        output["ai"] = _unavailable("BLOCKED", "CASE_CURRENT_SOURCE_OR_SCOPE_DENIED")
    except (ValueError, TypeError, KeyError, LookupError):
        output["ai"] = _unavailable("INVALID_INPUT", "CASE_INPUT_OR_RESULT_INVALID")
    except Exception:
        # Never return a raw provider, source, session or private-material error.
        output["ai"] = _unavailable("ERROR", "CASE_OWNED_EXECUTION_FAILED")
    return output
