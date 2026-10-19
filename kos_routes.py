# -*- coding: utf-8 -*-


"""LUMENIS BMP KOS API compatibility blueprint











复用 kos_engine.py 与 Shared Reporting KOS owner，不重复建设。





API 统一前缀 /api/kos/。





"""


from flask import Blueprint, jsonify, request

# KOS采集专用香港账号（rednote_hk）
try:
    from dual_account_rotation import select_account_for_collection

    KOS_DUAL_ACCOUNT = True
except ImportError:
    KOS_DUAL_ACCOUNT = False

import os
import sys
from pathlib import Path

kos_bp = Blueprint("kos", __name__, url_prefix="/api/kos")


# 延迟导入，避免循环依赖


def _engine():

    if "kos_engine" not in sys.modules:

        __import__("kos_engine")

    return sys.modules["kos_engine"]


def _intel():
    """Resolve the existing KOS intelligence owner lazily."""
    if "kos_intel" not in sys.modules:
        __import__("kos_intel")

    return sys.modules["kos_intel"]


def _resolve_kos_brand_scope(action):
    """Resolve one registered BMP BrandFocus and its current Permission receipt."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (
        LocalWorkspacePrincipal,
        check_actor_scope_permission,
        check_local_workspace_scope_permission,
        resolve_local_workspace_principal,
    )
    from subject_registry import get_subject_by_id, list_subjects, normalize_domain

    try:
        domain_name = normalize_domain(request.headers.get("X-Domain-Id", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("DOMAIN_REQUIRED") from exc
    if domain_name != "BMP":
        raise ValueError("BMP_DOMAIN_REQUIRED")
    product = request.headers.get("X-Product-Id")
    if product is not None and product.strip().upper() not in {"BMP", "ZBMP"}:
        raise ValueError("CONTEXT_SCOPE_MISMATCH")
    if request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL") != "FOCUS":
        raise ValueError("BRAND_FOCUS_REQUIRED")

    subject_id = request.headers.get("X-Subject-ID")
    brand_focus_id = request.headers.get("X-Brand-Focus-ID")
    if any(
        value is not None and (not value.strip() or value != value.strip())
        for value in (subject_id, brand_focus_id)
    ):
        raise ValueError("CONTEXT_SCOPE_MISMATCH")
    if subject_id:
        selected = get_subject_by_id(domain_name, subject_id)
        if (
            not isinstance(selected, dict)
            or selected.get("subject_type") != "brand"
            or not selected.get("brand_focus_id")
            or (brand_focus_id and selected.get("brand_focus_id") != brand_focus_id)
        ):
            raise ValueError("BRAND_FOCUS_NOT_REGISTERED")
    elif brand_focus_id:
        matches = [
            entry
            for entry in list_subjects(domain_name)
            if entry.get("brand_focus_id") == brand_focus_id
            and entry.get("status") in {"active", "configured"}
        ]
        if len(matches) != 1 or matches[0].get("subject_type") != "brand":
            raise ValueError("BRAND_FOCUS_NOT_UNIQUELY_REGISTERED")
        selected = matches[0]
    else:
        raise ValueError("BRAND_FOCUS_REQUIRED")
    if selected.get("status") not in {"active", "configured"}:
        raise ValueError("BRAND_FOCUS_NOT_ACTIVE")

    scope = {
        "domain_id": "zbmp",
        "subject_id": None,
        "brand_focus_id": selected["brand_focus_id"],
        "global_scope": False,
    }
    principal = resolve_local_workspace_principal(module="reports", action=action)
    actor = (
        principal
        if principal is not None
        else get_current_user(read_only=action == "read")
    )
    if principal is None and (
        not isinstance(actor, dict)
        or type(actor.get("id")) is not int
        or actor["id"] <= 0
    ):
        raise PermissionError("AUTH_REQUIRED")
    checker = (
        check_local_workspace_scope_permission
        if principal is not None
        else check_actor_scope_permission
    )
    decision = checker(actor, module="reports", action=action, **scope)
    if (
        decision.allowed is not True
        or decision.verification_state != "verified"
        or not decision.scope_audit_id
        or decision.scope_action != action
        or decision.subject_id is not None
        or decision.brand_focus_id != scope["brand_focus_id"]
        or decision.global_scope is not False
    ):
        raise PermissionError("SCOPE_PERMISSION_DENIED")
    if principal is not None:
        if (
            type(principal) is not LocalWorkspacePrincipal
            or actor is not principal
            or principal.actor_id is not None
            or principal.principal_ref != "workspace:local"
            or decision.actor_id is not None
            or decision.caller != "workspace:local"
            or decision.principal_kind != principal.principal_kind
            or decision.principal_ref != principal.principal_ref
        ):
            raise PermissionError("SCOPE_IDENTITY_MISMATCH")
    else:
        actor_id = actor.get("id") if isinstance(actor, dict) else None
        if (
            type(actor_id) is not int
            or actor_id <= 0
            or decision.actor_id != actor_id
            or decision.caller != f"actor:{actor_id}"
            or decision.principal_kind is not None
            or decision.principal_ref is not None
        ):
            raise PermissionError("SCOPE_IDENTITY_MISMATCH")
    if not isinstance(decision.caller, str) or not decision.caller.strip():
        raise PermissionError("SCOPE_IDENTITY_UNAVAILABLE")
    return actor, decision.caller, scope, selected, decision


def _kos_scope_error(exc):
    code = str(exc) or type(exc).__name__
    status = (
        403
        if isinstance(exc, PermissionError)
        else (503 if "UNAVAILABLE" in code else 400)
    )
    return (
        jsonify(
            {
                "ok": False,
                "status": (
                    "denied"
                    if status == 403
                    else "blocked" if status == 503 else "invalid_request"
                ),
                "code": code,
            }
        ),
        status,
    )


def _kos_scoped_author_profile(author_id, scope):
    import database as db
    import reprocess

    if not isinstance(author_id, str) or not author_id.strip():
        return None
    author_id = author_id.strip()
    ids = reprocess._canonical_source_ids(scope, limit=5000)
    if not ids:
        return None
    rows = db.get_notes_for_canonical_source_ids(
        ids, filters={"author_id": author_id}, limit=min(len(ids), 1000)
    )
    matched = []
    for row in rows:
        note = reprocess._scoped_note(row, scope)
        if note.get("author_id") == author_id:
            matched.append(note)
    if not matched:
        return None
    return {
        "author_id": author_id,
        "author_nickname": matched[0].get("author_nickname"),
        "kos_tier": None,
        "notes": matched,
    }


def _kos_selected_brand_name(selected):
    value = selected.get("name_zh") or selected.get("name_en")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("BRAND_DISPLAY_NAME_UNAVAILABLE")
    return value.strip()


def _scoped_profile_view(kind):
    """Preserve useful author workflows while keeping their source scope exact."""
    from experience_runtime import _bmp01_read_scope

    try:
        binding, error = _bmp01_read_scope()
        if error is not None:
            return error
        from lumenis.auth.service import get_current_user
        actor_identity = None
        if binding.get("actor_scope") == "authenticated":
            actor = get_current_user(read_only=True)
            if not isinstance(actor, dict) or type(actor.get("id")) is not int:
                raise PermissionError("AUTH_REQUIRED")
            actor_identity = actor["id"]
        if request.args.get("brand") is not None:
            _actor, _caller, _scope, selected, _decision = _resolve_kos_brand_scope(
                "read"
            )
            aliases = {
                selected.get(key)
                for key in ("name_zh", "name_en", "subject_id", "brand_focus_id", "key")
            }
            if request.args["brand"] not in aliases:
                raise ValueError("BRAND_FOCUS_MISMATCH")
        data = _engine().read_scoped_profiles(binding)
        profiles = data.pop("profiles")
        author_id = request.args.get("author_id", "").strip()
        platform = request.args.get("platform", "").strip()
        if author_id:
            profiles = [
                row
                for row in profiles
                if row["author_id"] == author_id
                and (not platform or row["source_platform"] == platform)
            ]
        elif kind in {"detail", "account", "content_dna", "identity"}:
            raise ValueError("AUTHOR_ID_REQUIRED")
        if platform:
            profiles = [row for row in profiles if row["source_platform"] == platform]
        if kind in {"detail", "account", "content_dna", "identity"}:
            if not profiles:
                if data.get("truncated") or data.get("rejected_count"):
                    return jsonify({"ok": False, "code": "AUTHOR_SEARCH_INCOMPLETE"}), 503
                return jsonify({"ok": False, "code": "AUTHOR_NOT_FOUND_IN_SCOPE"}), 404
            if len(profiles) != 1:
                raise ValueError("AUTHOR_PLATFORM_REQUIRED")
        limit, offset = int(request.args.get("limit", "50")), int(
            request.args.get("offset", "0")
        )
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("KOS_PAGE_INVALID")
        search = request.args.get("search", "").casefold()
        if search:
            profiles = [
                row
                for row in profiles
                if search
                in ((row["author_nickname"] or "") + row["author_id"]).casefold()
            ]
        if request.args.get("risk") == "1":
            profiles = [row for row in profiles if row["risk_count"] > 0]
        classification_unknown = {
            field: sum(row.get(field) is None for row in profiles)
            for field in ("kos_tier", "lifecycle_stage", "is_potential")
        }
        for argument, field in (("tier", "kos_tier"), ("lifecycle", "lifecycle_stage")):
            selected_value = request.args.get(argument)
            if selected_value:
                profiles = [row for row in profiles if
                    (str(row.get(field)).casefold() == selected_value.casefold()
                     if row.get(field) is not None else selected_value.casefold() == "unknown")]
        potential = request.args.get("potential")
        if potential not in (None, "", "0", "1", "unknown", "UNKNOWN"):
            raise ValueError("KOS_POTENTIAL_FILTER_INVALID")
        if potential == "1":
            profiles = [row for row in profiles if row.get("is_potential") is True]
        elif potential and potential.casefold() == "unknown":
            profiles = [row for row in profiles if row.get("is_potential") is None]
        sort_by = request.args.get("sort_by", "kos_score")
        if sort_by not in {"kos_score", "total_engagement", "note_count", "total_likes", "avg_engagement"}:
            raise ValueError("KOS_SORT_INVALID")
        profiles.sort(key=lambda row: (row.get(sort_by) is None,
                      -(row.get(sort_by) or 0), row["source_platform"], row["author_id"]))
        data["classification_unknown_count"] = classification_unknown
        data["classification_coverage"] = ("PARTIAL" if any(classification_unknown.values())
                                           or not data.get("source_read_complete", True)
                                           else "OBSERVED_HEURISTICS")
        data["sort_by"] = sort_by
        result = {
            **data,
            "profiles": profiles[offset : offset + limit],
            "returned": len(profiles[offset : offset + limit]),
            "total": len(profiles),
            "limit": limit,
            "offset": offset,
            "legacy_unscoped_profiles": "NOT_INCLUDED_SCOPE_UNKNOWN",
        }
        if kind == "overview":
            result = {
                **data,
                "total": len(profiles),
                "potential": (None if not data.get("source_read_complete", True)
                              or any(row.get("is_potential") is None for row in profiles)
                              else sum(row["is_potential"] is True for row in profiles)),
                "observed_potential": sum(row.get("is_potential") is True for row in profiles),
                "potential_unknown_count": sum(row.get("is_potential") is None for row in profiles),
                "risk": sum(row["risk_count"] > 0 for row in profiles),
                "by_tier": {value: sum((row.get("kos_tier") or "UNKNOWN") == value for row in profiles)
                            for value in sorted({row.get("kos_tier") or "UNKNOWN" for row in profiles})},
                "by_lifecycle": {value: sum((row.get("lifecycle_stage") or "UNKNOWN") == value for row in profiles)
                                 for value in sorted({row.get("lifecycle_stage") or "UNKNOWN" for row in profiles})},
            }
        elif kind in {"detail", "account"}:
            result = profiles[0]
        elif kind in {"identity", "ownership"}:
            result = {
                "profiles": [
                    {
                        "author_id": row["author_id"],
                        "source_platform": row["source_platform"],
                        "identity_label": "UNKNOWN",
                        "ownership_type": "UNKNOWN",
                        "needs_manual_review": True,
                        "source_refs": row["source_refs"],
                    }
                    for row in profiles
                ],
                "count": len(profiles),
                "reason": "Observed content is not evidence of employment or cooperation.",
            }
        elif kind in {"tier", "candidates"}:
            ranked = sorted(
                profiles,
                key=lambda row: (
                    row["total_engagement"] is None,
                    -(row["total_engagement"] or 0),
                    row["source_platform"],
                    row["author_id"],
                ),
            )
            result = {
                "profiles": ranked[:limit],
                "count": len(profiles),
                "ranking_basis": "scoped observed engagement; not influence or suitability",
                "unknown_engagement": sum(
                    row["total_engagement"] is None for row in profiles
                ),
                "classification": "NOT_ESTABLISHED",
                "external_effect": "not_performed",
                "method": "source-observation-order:v1",
            }
        elif kind == "content_dna":
            from lumenis.importer.analyzer import extract_source_keyword_candidates

            observations = profiles[0]["observations"][:limit]
            result = {
                "author_id": author_id,
                "notes_analyzed": len(observations),
                "method": "source-literal-structure:v1",
                "sources": [
                    {
                        **row,
                        "keyword_candidates": extract_source_keyword_candidates(
                            row["title"] + "\n" + row["content"]
                        ),
                    }
                    for row in observations
                ],
                "ai_state": "NOT_RUN",
                "identity_label": "UNKNOWN",
            }
        current, denied = _bmp01_read_scope()
        if denied is not None or current != binding:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        if actor_identity is not None:
            current_actor = get_current_user(read_only=True)
            if not isinstance(current_actor, dict) or current_actor.get("id") != actor_identity:
                raise PermissionError("SCOPE_IDENTITY_CHANGED")
        if kind in {"list", "refresh"}:
            if kind == "refresh":
                from datetime import datetime, timezone
                result.update(recomputed=True, persisted=False,
                              recomputed_at=datetime.now(timezone.utc).isoformat(),
                              refresh_method="signed-canonical-dynamic-aggregation:v1")
            return jsonify({"ok": True, **result, "binding": binding})
        return jsonify({"ok": True, "data": result, "binding": binding})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "KOS_SCOPED_READ_UNAVAILABLE"}), 503


def _scoped_comment_view():
    from experience_runtime import _bmp01_read_scope

    try:
        binding, error = _bmp01_read_scope()
        if error is not None:
            return error
        result = _engine().read_scoped_comments(
            binding,
            author_id=request.args.get("author_id", ""),
            note_id=request.args.get("note_id", ""),
            limit=int(request.args.get("limit", "50")),
        )
        current, denied = _bmp01_read_scope()
        if denied is not None or current != binding:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        return jsonify({"ok": True, **result, "data": result, "binding": binding})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "KOS_SCOPED_COMMENTS_UNAVAILABLE"}), 503


# Process-local signing only authenticates a pending owner-issued request. It
# grants no effect; the authenticated user must confirm the exact challenge.
import secrets as _kos_secrets

_KOS_APPROVAL_CHALLENGE_KEY = _kos_secrets.token_bytes(32)


def _kos_approval_challenge(resource, request_id):
    import base64, hashlib, hmac, json, time
    import kos_ops

    actor, caller, scope, _selected, _decision = _resolve_kos_brand_scope("write")
    context = kos_ops._scoped_operation_identity(actor, scope, "write")
    raw = json.dumps(
        {
            "context": context,
            "resource": resource,
            "request_id": request_id,
            "expires": int(time.time()) + 300,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return (
        base64.urlsafe_b64encode(raw).decode()
        + "."
        + hmac.new(_KOS_APPROVAL_CHALLENGE_KEY, raw, hashlib.sha256).hexdigest()
    )


@kos_bp.route("/approvals/confirm", methods=["POST"])
def api_kos_approval_confirm():
    return _kos_approval_decision(False)


@kos_bp.route("/approvals/revoke", methods=["POST"])
def api_kos_approval_revoke():
    return _kos_approval_decision(True)


def _kos_approval_decision(revoke):
    import base64, hashlib, hmac, json, time
    import kos_ops
    from experience_runtime import _content_source_same_origin
    from lumenis.system.security.permission import get_permission_gate, PermissionLevel

    try:
        if not _content_source_same_origin():
            raise PermissionError("KOS_APPROVAL_ORIGIN_DENIED")
        actor, caller, scope, _selected, _decision = _resolve_kos_brand_scope("write")
        body = request.get_json(silent=True)
        if (
            not isinstance(body, dict)
            or set(body) != {"challenge", "confirm"}
            or body.get("confirm") is not True
            or not isinstance(body.get("challenge"), str)
            or len(body["challenge"]) > 6000
        ):
            raise ValueError("KOS_EXACT_CONFIRMATION_REQUIRED")
        encoded, signature = body["challenge"].split(".", 1)
        raw = base64.urlsafe_b64decode(encoded)
        if not hmac.compare_digest(
            signature,
            hmac.new(_KOS_APPROVAL_CHALLENGE_KEY, raw, hashlib.sha256).hexdigest(),
        ):
            raise PermissionError("KOS_APPROVAL_CHALLENGE_INVALID")
        value = json.loads(raw)
        context = kos_ops._scoped_operation_identity(actor, scope, "write")
        if value["context"] != context or value["expires"] < time.time():
            raise PermissionError("KOS_APPROVAL_CHALLENGE_EXPIRED_OR_SCOPE_CHANGED")
        gate = get_permission_gate()
        if not gate.has_permission(
            PermissionLevel.HUMAN_APPROVAL
        ) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError("KOS_MANUAL_APPROVAL_AUTHORITY_REQUIRED")
        resource = value["resource"]
        token = gate.get_valid_approval_token("db_write", resource, exact=True)
        if revoke:
            changed = bool(token and gate.revoke_approval(token))
            return jsonify({"ok": True, "revoked": changed, "resource": resource})
        if token is None:
            gate.grant_approval(
                "db_write", resource=resource, duration_minutes=5, granted_by=caller
            )
        return jsonify(
            {
                "ok": True,
                "approved": True,
                "operation_type": "db_write",
                "resource": resource,
                "request_id": value["request_id"],
                "expires_in_minutes": 5,
                "external_effect": "not_performed",
            }
        )
    except (ValueError, PermissionError, KeyError, TypeError) as exc:
        return _kos_scope_error(exc)


def _private_kos_operation(operation, *, list_all=False):
    """Account/BrandFocus-bound drafts; caller-provided actor is never authority."""
    import math
    import uuid
    import kos_ops

    fields = {
        "lead": {
            "contact_name",
            "phone",
            "wechat",
            "email",
            "mcn",
            "company",
            "region",
        },
        "cooperation": {"cooperation_status", "quote", "budget", "note"},
        "manual_metrics": {
            "wecom_add",
            "sales_amount",
            "boosting_budget",
            "inquiry",
            "clicks",
            "impressions",
            "revenue",
        },
        "paid_plan": {"note_id", "budget", "channel", "expected_reach"},
        "reward_plan": {"points", "amount", "reason"},
        "ownership_claim": {"ownership_class", "note"},
        "operation_note": {"action", "note"},
        "paid_result": {
            "plan_id",
            "spend",
            "impressions",
            "clicks",
            "conversions",
            "note",
        },
    }
    try:
        action = "write" if request.method == "POST" else "read"
        actor, actor_ref, scope, selected, _decision = _resolve_kos_brand_scope(action)
        body = (
            request.get_json(silent=True)
            if request.method == "POST"
            else dict(request.args)
        )
        if not isinstance(body, dict):
            raise ValueError("KOS_OPERATION_INPUT_INVALID")
        author_id = kos_ops.resolve_author_aliases(body, required=not (
            list_all or operation == "paid_result" or (
                request.method == "GET" and operation in {"paid_plan", "reward_plan", "ownership_claim"}
            )
        ))
        if request.method == "POST":
            if (
                set(body)
                - fields[operation]
                - {"author_id", "kos_id", "request_id", "expected_version"}
            ):
                raise ValueError("KOS_OPERATION_FIELDS_INVALID")
            payload = {key: body[key] for key in fields[operation] if key in body}
            if not payload:
                raise ValueError("KOS_OPERATION_PAYLOAD_REQUIRED")
            numeric = {
                "quote",
                "budget",
                "wecom_add",
                "sales_amount",
                "boosting_budget",
                "inquiry",
                "clicks",
                "impressions",
                "revenue",
                "expected_reach",
                "points",
                "amount",
                "spend",
                "conversions",
            }
            for key, value in payload.items():
                if key in numeric:
                    if value is not None and (
                        type(value) not in (int, float)
                        or not math.isfinite(value)
                        or value < 0
                    ):
                        raise ValueError("KOS_OPERATION_NUMBER_INVALID")
                elif not isinstance(value, str) or len(value) > 4000:
                    raise ValueError("KOS_OPERATION_TEXT_INVALID")
            if operation == "cooperation" and payload.get(
                "cooperation_status", "NONE"
            ) not in {"NONE", "LEAD", "DISCUSSING", "NEGOTIATING", "REJECTED"}:
                raise ValueError("KOS_COOPERATION_CONFIRMATION_REQUIRED")
            if operation == "paid_result":
                from kos_paid import resolve_scoped_paid_plan
                binding = resolve_scoped_paid_plan(actor=actor, scope=scope,
                    plan_id=payload.get("plan_id"), author_id=author_id)
                author_id = binding["author_id"]
            result = kos_ops.write_scoped_operation(
                actor=actor,
                scope=scope,
                author_id=author_id.strip(),
                operation=operation,
                payload=payload,
                request_id=body.get("request_id") or "kos-" + uuid.uuid4().hex,
                expected_version=body.get("expected_version", 0),
            )
            if operation == "paid_plan":
                result["plan_id"] = result["operation"]["plan_id"]
        else:
            data = kos_ops.read_scoped_operations(
                actor=actor,
                scope=scope,
                author_id=author_id.strip(),
                operation=None if list_all else operation,
                limit=int(body.get("limit", "100")),
            )
            result = {
                "ok": True,
                **data,
                "current": data["items"][0] if data["items"] else None,
            }
        current = _resolve_kos_brand_scope(action)
        if current[1] != actor_ref or current[2] != scope or current[3] != selected:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        return jsonify(result)
    except kos_ops.ScopedOperationApprovalRequired as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "code": str(exc),
                    "requires_approval": True,
                    "operation_type": "db_write",
                    "resource": exc.resource,
                    "request_id": exc.request_id,
                    "challenge": _kos_approval_challenge(exc.resource, exc.request_id),
                    "external_effect": "not_performed",
                }
            ),
            403,
        )
    except kos_ops.ScopedOperationHistoryLimitError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 503
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "KOS_PRIVATE_OPERATION_UNAVAILABLE"}), 503


def _private_kos_metrics(kind):
    import kos_metrics

    try:
        actor, caller, scope, selected, _decision = _resolve_kos_brand_scope("read")
        data = kos_metrics.read_scoped_manual_metrics(
            actor=actor, scope=scope, period=request.args.get("period", "all")
        )
        if kind == "funnel":
            data["funnel"] = {
                "viewership": data["impressions"],
                "wecom_add": data["wecom_add"],
                "sales_amount": data["sales_amount"],
            }
        if kind == "channel_roi":
            data["channels"] = []
            data["channel_coverage"] = "NOT_ESTABLISHED_BY_UNSCOPED_LEGACY_CHANNELS"
        current = _resolve_kos_brand_scope("read")
        if current[1] != caller or current[2] != scope or current[3] != selected:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        return jsonify({"ok": True, "data": data})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "KOS_PRIVATE_METRICS_UNAVAILABLE"}), 503


def _scoped_execution_route(mode, execution_id=None, action_type=None):
    import uuid
    import kos_execution
    import kos_ops

    try:
        actor, caller, scope, selected, _decision = _resolve_kos_brand_scope(
            "read" if mode == "list" else "write"
        )
        if mode == "list":
            rows = kos_execution.list_scoped_executions(
                actor=actor,
                scope=scope,
                status=request.args.get("status", ""),
                action_type=request.args.get("action_type", ""),
                target_author_id=request.args.get("author_id", ""),
                limit=int(request.args.get("limit", "50")),
            )
            return jsonify(
                {
                    "ok": True,
                    "executions": rows,
                    "count": len(rows),
                    "legacy_scope": "UNKNOWN",
                }
            )
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or any(
            key in body
            for key in (
                "actor",
                "confirmed_by",
                "result",
                "evidence_ref",
                "failure_reason",
            )
        ):
            raise ValueError("KOS_EXECUTION_SERVER_AUTHORITY_REQUIRED")
        if mode == "create":
            if set(body) - {
                "action_type",
                "target_author_id",
                "author_id",
                "kos_id",
                "payload",
                "quote",
                "budget",
                "request_id",
                "operation_record_id",
            }:
                raise ValueError("KOS_EXECUTION_FIELDS_INVALID")
            chosen_action = action_type or body.get("action_type")
            if action_type and body.get("action_type", action_type) != action_type:
                raise ValueError("KOS_PLAN_ACTION_MISMATCH")
            author_id = kos_ops.resolve_author_aliases(body, execution=True,
                required=body.get("operation_record_id") is None)
            payload = kos_ops.normalize_execution_payload(body, chosen_action)
            source_options = {}
            if body.get("operation_record_id") is not None:
                source = kos_ops.resolve_scoped_operation_record(actor=actor, scope=scope,
                    record_id=body["operation_record_id"], author_id=author_id)
                author_id = source["author_id"]
                source_options["expected_source_version"] = source["version"]
                mapping = {
                    "paid_plan": "paid_media",
                    "reward_plan": "reward_issue",
                    "cooperation": "cooperation_confirm",
                }
                if mapping.get(source["operation"]) != chosen_action:
                    raise ValueError("KOS_PLAN_ACTION_MISMATCH")
                bound_payload = {
                    "private_plan": source["payload"],
                    "source_record_id": source["record_id"],
                    "source_sha256": source["sha256"],
                }
                if payload and payload != bound_payload and any(
                    key not in source["payload"] or source["payload"][key] != value
                    for key, value in payload.items()
                ):
                    raise ValueError("KOS_EXECUTION_PAYLOAD_CONFLICT")
                payload = bound_payload
            result = kos_execution.create_scoped_execution(
                actor=actor,
                scope=scope,
                action_type=chosen_action,
                target_author_id=author_id,
                payload=payload,
                request_id=body.get("request_id") or "kx-" + uuid.uuid4().hex,
                **source_options,
            )
        elif mode == "transition":
            if set(body) - {"status", "to_status"}:
                raise ValueError("KOS_EXECUTION_FIELDS_INVALID")
            result = kos_execution.transition_scoped_execution(
                execution_id,
                body.get("status") or body.get("to_status"),
                actor=actor,
                scope=scope,
            )
        else:
            if set(body) != {"execution_id"}:
                raise ValueError("KOS_EXECUTION_FIELDS_INVALID")
            result = kos_execution.execute_scoped_execution(
                body["execution_id"], actor=actor, scope=scope
            )
        return jsonify(result), (200 if result.get("ok") else 409)
    except kos_ops.ScopedOperationApprovalRequired as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "code": str(exc),
                    "requires_approval": True,
                    "operation_type": "db_write",
                    "resource": exc.resource,
                    "request_id": exc.request_id,
                    "challenge": _kos_approval_challenge(exc.resource, exc.request_id),
                    "external_effect": "not_performed",
                }
            ),
            403,
        )
    except kos_ops.ScopedOperationHistoryLimitError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 503
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except LookupError:
        return jsonify({"ok": False, "code": "KOS_EXECUTION_NOT_FOUND"}), 404
    except Exception:
        return jsonify({"ok": False, "code": "KOS_SCOPED_EXECUTION_UNAVAILABLE"}), 503


@kos_bp.route("/overview", methods=["GET"])
def api_overview():
    return _scoped_profile_view("overview")


@kos_bp.route("/list", methods=["GET"])
def api_list():
    return _scoped_profile_view("list")


@kos_bp.route("/detail", methods=["GET"])
def api_detail():
    return _scoped_profile_view("detail")


@kos_bp.route("/refresh", methods=["POST"])
def api_refresh():
    # Canonical is already persisted; rebuilding its projection is a read.
    # Never revive the unscoped kos_profiles cache, which is no longer consumed.
    body = request.get_json(silent=True)
    if request.data and body != {}:
        return _kos_scope_error(ValueError("KOS_REFRESH_REQUEST_INVALID"))
    return _scoped_profile_view("refresh")


@kos_bp.route("/comments", methods=["GET"])
def api_comments():
    return _scoped_comment_view()


@kos_bp.route("/outreach", methods=["POST"])
def api_outreach():
    """Create a scoped, deterministic outreach draft for human review."""
    try:
        _actor, actor_ref, scope, selected, decision = _resolve_kos_brand_scope("write")
        data = request.get_json(silent=True) or {}
        author_id = data.get("author_id")
        campaign_name = data.get("campaign_name", "")
        if not isinstance(author_id, str) or not author_id.strip():
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "AUTHOR_ID_REQUIRED",
                    }
                ),
                400,
            )
        if not isinstance(campaign_name, str) or len(campaign_name) > 200:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "CAMPAIGN_NAME_INVALID",
                    }
                ),
                400,
            )
        profile = _kos_scoped_author_profile(author_id, scope)
        if profile is None:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "not_found",
                        "code": "AUTHOR_NOT_IN_BRAND_SCOPE",
                    }
                ),
                404,
            )
        brand_name = _kos_selected_brand_name(selected)
        result = _engine().generate_outreach(
            author_id,
            brand_name=brand_name,
            campaign_name=campaign_name,
            profile=profile,
            ai_enhance=False,
        )
        if result.get("ok") is not True:
            return jsonify(result), 409
        try:
            import kos_execution as execution

            receipt = execution.create_scoped_execution(
                actor=_actor,
                scope=scope,
                action_type="outreach_send",
                target_author_id=author_id or "unassigned-user-comment",
                request_id=data.get("request_id")
                or "draft-" + __import__("uuid").uuid4().hex,
                payload={
                    "campaign_name": campaign_name,
                    "generated_draft": result.get("content", ""),
                    "content_source": "deterministic_rule",
                },
            )["execution"]
        except __import__("kos_ops").ScopedOperationApprovalRequired as exc:
            return (
                jsonify(
                    {
                        "ok": False,
                        "code": str(exc),
                        "requires_approval": True,
                        "resource": exc.resource,
                        "request_id": exc.request_id,
                        "challenge": _kos_approval_challenge(
                            exc.resource, exc.request_id
                        ),
                        "draft": result,
                    }
                ),
                403,
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 - convert unknown persistence failures to an explicit partial result.
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "partial",
                        "code": "DRAFT_REVIEW_RECORD_FAILED",
                        "draft": result,
                        "error_type": type(exc).__name__,
                    }
                ),
                503,
            )
        result["hcg"] = {
            "status": receipt.get("status"),
            "execution_id": receipt.get("execution_id"),
            "note": "规则生成草稿已登记；未发送，需人工审核。",
        }
        result["scope"] = {
            "domain_id": scope["domain_id"],
            "brand_focus_id": scope["brand_focus_id"],
            "scope_audit_id": decision.scope_audit_id,
        }
        return jsonify(result)
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except (
        Exception
    ) as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "error",
                    "code": "OUTREACH_FAILED",
                    "error_type": type(exc).__name__,
                }
            ),
            503,
        )


@kos_bp.route("/ad-candidates", methods=["GET"])
def api_ad_candidates():

    return _scoped_profile_view("candidates")


@kos_bp.route("/reward", methods=["GET"])
def api_reward():

    return _private_kos_operation("reward_plan")


@kos_bp.route("/report/generate", methods=["POST"])
def api_report_generate():
    """Generate a fresh BrandFocus snapshot through the existing report owner."""
    try:
        _resolve_kos_brand_scope("write")
        from experience_runtime import (
            _content_source_same_origin,
            generate_source_brief_job,
        )

        if not _content_source_same_origin():
            raise PermissionError("KOS_REPORT_ORIGIN_DENIED")
        return generate_source_brief_job()
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)


@kos_bp.route("/report/view", methods=["GET"])
def api_report_view():
    """Reopen the selected immutable report, with fresh actor/source checks."""
    try:
        _resolve_kos_brand_scope("read")
        if set(request.args) != {"job_id"} or len(request.args.getlist("job_id")) != 1:
            raise ValueError("KOS_REPORT_JOB_ID_REQUIRED")
        from experience_runtime import reopen_source_brief_job

        return reopen_source_brief_job(request.args["job_id"])
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)


@kos_bp.route("/reply/generate", methods=["POST"])
def api_reply_generate():
    """Create a scoped reply suggestion; never sends it or changes brand identity."""
    try:
        _actor, actor_ref, scope, selected, decision = _resolve_kos_brand_scope("write")
        data = request.get_json(silent=True) or {}
        comment_text = data.get("comment_text")
        if (
            not isinstance(comment_text, str)
            or not comment_text.strip()
            or len(comment_text) > 8000
        ):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "COMMENT_TEXT_REQUIRED",
                    }
                ),
                400,
            )
        author_id = data.get("author_id", "")
        if author_id and (
            not isinstance(author_id, str)
            or _kos_scoped_author_profile(author_id, scope) is None
        ):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "denied",
                        "code": "AUTHOR_NOT_IN_BRAND_SCOPE",
                    }
                ),
                403,
            )
        risk_level = data.get("risk_level", "low")
        if risk_level not in {"low", "medium", "high", "critical"}:
            risk_level = "unknown"
        reply_style = data.get("reply_style", "professional")
        if not isinstance(reply_style, str) or len(reply_style) > 40:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "REPLY_STYLE_INVALID",
                    }
                ),
                400,
            )
        brand_name = _kos_selected_brand_name(selected)
        result = _engine().generate_reply(
            comment_text=comment_text.strip(),
            brand_name=brand_name,
            reply_style=reply_style,
            risk_level=risk_level,
            ai_enhance=False,
        )
        result["content_source"] = "deterministic_rule"
        result["input_provenance"] = "USER_PROVIDED_UNVERIFIED"
        result["scope"] = {
            "domain_id": scope["domain_id"],
            "brand_focus_id": scope["brand_focus_id"],
            "scope_audit_id": decision.scope_audit_id,
        }
        if result.get("ok") is True and result.get("action") == "SUGGEST_REPLY":
            suggested_reply = result.get("suggested_reply")
            if not isinstance(suggested_reply, str) or not suggested_reply.strip():
                return (
                    jsonify(
                        {
                            "ok": False,
                            "status": "unavailable",
                            "code": "SUGGESTED_REPLY_UNAVAILABLE",
                        }
                    ),
                    503,
                )
            try:
                import kos_execution as execution

                receipt = execution.create_scoped_execution(
                    actor=_actor,
                    scope=scope,
                    action_type="reply_send",
                    target_author_id=author_id or "unassigned-user-comment",
                    request_id=data.get("request_id")
                    or "draft-" + __import__("uuid").uuid4().hex,
                    payload={
                        "comment_text": comment_text.strip(),
                        "comment_source": "USER_PROVIDED_UNVERIFIED",
                        "reply_style": reply_style,
                        "generated_reply": suggested_reply,
                        "target_binding": (
                            "SCOPED_AUTHOR" if author_id else "UNASSIGNED_RECIPIENT"
                        ),
                    },
                )["execution"]
            except __import__("kos_ops").ScopedOperationApprovalRequired as exc:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "code": str(exc),
                            "requires_approval": True,
                            "resource": exc.resource,
                            "request_id": exc.request_id,
                            "challenge": _kos_approval_challenge(
                                exc.resource, exc.request_id
                            ),
                            "suggestion": result,
                        }
                    ),
                    403,
                )
            except (
                Exception
            ) as exc:  # noqa: BLE001 - preserve the suggestion but report failed review registration.
                return (
                    jsonify(
                        {
                            "ok": False,
                            "status": "partial",
                            "code": "REPLY_REVIEW_RECORD_FAILED",
                            "suggestion": result,
                            "error_type": type(exc).__name__,
                        }
                    ),
                    503,
                )
            result["hcg"] = {
                "status": receipt.get("status"),
                "execution_id": receipt.get("execution_id"),
                "note": "规则生成建议已登记；未发送，需人工审核。",
            }
        elif result.get("ok") is True and result.get("action") != "NO_REPLY":
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "unavailable",
                        "code": "REPLY_ACTION_UNAVAILABLE",
                    }
                ),
                503,
            )
        return jsonify(result)
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except (
        Exception
    ) as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "error",
                    "code": "REPLY_GENERATION_FAILED",
                    "error_type": type(exc).__name__,
                }
            ),
            503,
        )


@kos_bp.route("/content-dna", methods=["GET"])
def api_content_dna():
    return _scoped_profile_view("content_dna")


@kos_bp.route("/attribution", methods=["GET"])
def api_attribution():
    """Return attribution from notes verified within the selected BrandFocus."""
    try:
        _actor, _actor_id, scope, selected, decision = _resolve_kos_brand_scope("read")
        author_id = request.args.get("author_id", "")
        note_ids = request.args.get("note_ids", "")
        brand_name = _kos_selected_brand_name(selected)
        if author_id:
            import kos_attribution

            outcome = kos_attribution.calculate_attribution(
                author_id,
                brand_name=brand_name,
                scope=scope,
                actor=_actor,
            )
        elif note_ids:
            normalized = [part.strip() for part in note_ids.split(",") if part.strip()]
            import kos_attribution

            outcome = kos_attribution.calculate_multi_touch_attribution(
                normalized,
                brand_name=brand_name,
                scope=scope,
            )
        else:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "AUTHOR_ID_OR_NOTE_IDS_REQUIRED",
                    }
                ),
                400,
            )
        if outcome.get("ok") is not True:
            status = 403 if outcome.get("status") == "denied" else 409
            return (
                jsonify({**outcome, "scope_audit_id": decision.scope_audit_id}),
                status,
            )
        current = _resolve_kos_brand_scope("read")
        if current[1] != _actor_id or current[2] != scope or current[3] != selected:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        return jsonify({**outcome, "scope_audit_id": decision.scope_audit_id})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except (
        Exception
    ) as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "error",
                    "code": "ATTRIBUTION_FAILED",
                    "error_type": type(exc).__name__,
                }
            ),
            503,
        )


@kos_bp.route("/intent-analysis", methods=["GET"])
def api_intent_analysis():
    return _scoped_comment_view()


@kos_bp.route("/kos-identity", methods=["GET", "POST"])
def api_kos_identity():

    return _scoped_profile_view("identity" if request.method == "GET" else "list")


@kos_bp.route("/competitor-benchmark", methods=["GET"])
def api_competitor_benchmark():
    """Read explicit registered BrandFocus observations in current authorized scope."""
    from experience_runtime import _bmp01_read_scope

    try:
        if request.args:
            raise ValueError("BMP_BENCHMARK_REQUEST_INVALID")
        binding, error = _bmp01_read_scope()
        if error is not None:
            return error
        result = _intel().read_scoped_benchmark(binding)
        current, denied = _bmp01_read_scope()
        if denied is not None or current != binding:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        return jsonify({"ok": True, "data": result, "binding": binding})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "BMP_BENCHMARK_UNAVAILABLE"}), 503


@kos_bp.route("/funnel", methods=["GET"])
def api_kos_funnel():
    return _private_kos_metrics("funnel")


@kos_bp.route("/cost", methods=["GET"])
def api_kos_cost():
    return _private_kos_metrics("cost")


@kos_bp.route("/tier", methods=["GET"])
def api_kos_tier():

    return _scoped_profile_view("tier")


@kos_bp.route("/koc-tier", methods=["GET"])
def api_kos_koc_tier():
    """Preserve declared-input arithmetic and the scoped roster compatibility read."""
    if not request.args:
        return _scoped_profile_view("tier")
    try:
        original = _resolve_kos_brand_scope("read")
        expected = {"interactions_24h", "interactions_7d"}
        if set(request.args) != expected or any(len(request.args.getlist(key)) != 1 for key in expected):
            raise ValueError("KOC_INTERACTIONS_REQUIRED")
        values = []
        for key in ("interactions_24h", "interactions_7d"):
            raw = request.args[key]
            if not raw.isascii() or not raw.isdigit() or len(raw) > 16:
                raise ValueError("KOC_INTERACTIONS_INVALID")
            value = int(raw)
            if value > 9007199254740991:
                raise ValueError("KOC_INTERACTIONS_INVALID")
            values.append(value)
        from kos_metrics import koc_reward_tier
        result = koc_reward_tier(*values)
        current = _resolve_kos_brand_scope("read")
        if current[1:4] != original[1:4]:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        result.update(input_basis="user_declared", method="configured-koc-thresholds:v1",
                      observation_verified=False, external_effect="not_performed")
        return jsonify({"ok": True, "data": result, "scope": original[2], "persisted": False})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "KOC_CALCULATION_UNAVAILABLE"}), 503


@kos_bp.route("/manual", methods=["POST"])
def api_kos_manual():
    return _private_kos_operation("manual_metrics")


@kos_bp.route("/campaign", methods=["POST"])
def api_kos_campaign():
    """Scoped stateless arithmetic, never a claim of verified campaign results."""
    try:
        _actor, _caller, scope, _selected, _decision = _resolve_kos_brand_scope("read")
        from experience_runtime import _content_source_same_origin

        if not _content_source_same_origin():
            raise PermissionError("KOS_CAMPAIGN_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - {"campaign", "kocs"}:
            raise ValueError("KOS_CAMPAIGN_REQUEST_INVALID")
        from kos_metrics import koc_campaign_review

        result = koc_campaign_review(
            body.get("campaign", "Untitled private calculation"), body.get("kocs", [])
        )
        _resolve_kos_brand_scope("read")
        return jsonify({"ok": True, "data": result, "scope": scope, "persisted": False})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)


@kos_bp.route("/channel-roi", methods=["GET"])
def api_kos_channel_roi():
    return _private_kos_metrics("channel_roi")


@kos_bp.route("/profile", methods=["GET"])
def api_kos_profile():
    try:
        _actor, _caller, scope, selected, _decision = _resolve_kos_brand_scope("read")
        return jsonify(
            {
                "ok": True,
                "data": {
                    "brand_focus_id": scope["brand_focus_id"],
                    "subject_id": selected["subject_id"],
                    "display_name": _kos_selected_brand_name(selected),
                    "scope": scope,
                    "configured_subject": selected,
                    "collection_state": "NOT_STARTED_BY_PROFILE_READ",
                },
            }
        )
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)


@kos_bp.route("/collect", methods=["POST"])
def api_kos_collect():
    """Compatibility entry into the canonical scoped secondary-collection flow."""
    try:
        body = request.get_json(silent=True)
        allowed = {"brand", "operator", "confirm_read_only", "max_results"}
        if not isinstance(body, dict) or set(body) - allowed:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "INVALID_COLLECTION_REQUEST",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                400,
            )
        operator = str(body.get("operator") or "").strip().lower()
        if operator not in {"human", "human_ui"}:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "denied",
                        "code": "HUMAN_OPERATOR_REQUIRED",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                403,
            )
        if body.get("confirm_read_only") is not True:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "input_required",
                        "code": "READ_ONLY_CONFIRMATION_REQUIRED",
                    }
                ),
                400,
            )
        brand_key = body.get("brand")
        if not isinstance(brand_key, str) or not brand_key.strip():
            return (
                jsonify(
                    {"ok": False, "status": "input_required", "code": "BRAND_REQUIRED"}
                ),
                400,
            )
        brand_key = brand_key.strip()
        raw_limit = body.get("max_results", 20)
        if type(raw_limit) is not int or not 1 <= raw_limit <= 20:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "MAX_RESULTS_OUT_OF_RANGE",
                    }
                ),
                400,
            )

        from subject_rules import BRAND_PROFILES

        profile = BRAND_PROFILES.get(brand_key)
        if not isinstance(profile, dict):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "invalid_request",
                        "code": "BRAND_PROFILE_UNKNOWN",
                    }
                ),
                400,
            )

        from experience_runtime import _content_project_error, _content_project_scope
        from shared_artifacts import LocalArtifactError

        try:
            actor, scope = _content_project_scope("write", module="collector")
        except LocalArtifactError as exc:
            return _content_project_error(exc)
        if (
            scope.get("domain_id") not in {"bmp", "zbmp"}
            or not isinstance(scope.get("brand_focus_id"), str)
            or not scope["brand_focus_id"]
            or scope.get("global_scope") is True
        ):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "denied",
                        "code": "EXACT_BRAND_FOCUS_REQUIRED",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                403,
            )

        from subject_registry import list_subjects

        entries = [
            entry
            for entry in list_subjects("BMP")
            if entry.get("brand_focus_id") == scope["brand_focus_id"]
        ]
        if len(entries) != 1:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "blocked",
                        "code": "BRAND_FOCUS_NOT_UNIQUELY_REGISTERED",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                503,
            )
        entry = entries[0]
        registered_terms = entry.get("keywords")
        if not isinstance(registered_terms, list):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "blocked",
                        "code": "BRAND_TOPIC_TERMS_UNAVAILABLE",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                503,
            )
        registered_names = {
            str(value).strip().casefold()
            for value in (
                entry.get("name_zh"),
                entry.get("name_en"),
                *registered_terms,
                entry.get("subject_id"),
                entry.get("brand_focus_id"),
            )
            if isinstance(value, str) and value.strip()
        }
        profile_names = {
            part.strip().casefold()
            for part in str(profile.get("display_name") or "").split("/")
            if part.strip()
        }
        if not profile_names.intersection(registered_names):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "denied",
                        "code": "BRAND_PROFILE_SCOPE_MISMATCH",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                403,
            )

        terms = []
        seen_terms = set()
        for value in (entry.get("name_zh"), entry.get("name_en"), *registered_terms):
            if (
                isinstance(value, str)
                and value.strip()
                and value.strip().casefold() not in seen_terms
            ):
                term = value.strip()
                seen_terms.add(term.casefold())
                terms.append(term)
        if not terms:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "blocked",
                        "code": "BRAND_TOPIC_TERMS_UNAVAILABLE",
                        "read_only": True,
                        "external_write": False,
                    }
                ),
                503,
            )

        from xhs_cookie_bridge import is_user_paused

        paused = is_user_paused()
        if paused and not os.environ.get("ZBC_TEST_MODE"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "USER_PAUSED",
                        "reason": paused.get("reason", "采集已暂停"),
                        "brand_focus_id": scope["brand_focus_id"],
                    }
                ),
                409,
            )

        from lumenis.system.collector.adapters.secondary_collection import (
            collect_search,
        )

        results = []
        stop_statuses = {
            "RISK_WARNING",
            "NEED_VERIFY",
            "SESSION_EXPIRED",
            "BLOCKED",
            "PROVIDER_UNAVAILABLE",
            "NOT_CONFIGURED",
            "RATE_LIMITED",
            "COOLING_DOWN",
            "SCOPE_UNAUTHORIZED",
            "APPROVAL_REQUIRED",
            "PERMISSION_UNAVAILABLE",
        }
        result_fields = {
            "ok",
            "status",
            "platform",
            "raw_count",
            "returned_count",
            "imported",
            "updated",
            "failed",
            "subject_matches",
            "canonical_synced",
            "native_fields_synced",
            "evidence_recorded",
            "evidence_ref",
            "scope_status",
            "refresh_verified",
            "error_type",
            "read_only",
            "external_write",
            "publish_authority",
        }
        for keyword in terms:
            try:
                result = collect_search(
                    "xiaohongshu",
                    keyword,
                    max_results=raw_limit,
                    operator=operator,
                    actor=actor,
                    scope=scope,
                )
            except Exception as exc:
                result = {
                    "ok": False,
                    "status": "ERROR",
                    "error_type": type(exc).__name__,
                }
            results.append(
                {
                    "keyword": keyword,
                    **{
                        field: result[field]
                        for field in result_fields
                        if field in result
                    },
                }
            )
            if str(result.get("status") or "").upper() in stop_statuses:
                break

        accepted_total = sum(
            int(result.get("imported", 0) or 0) + int(result.get("updated", 0) or 0)
            for result in results
            if result.get("ok") is True
        )
        all_terms_completed = len(results) == len(terms)
        all_succeeded = (
            all(result.get("ok") is True for result in results) and all_terms_completed
        )
        any_succeeded = any(result.get("ok") is True for result in results)
        status = (
            "SUCCESS"
            if all_succeeded
            else (
                "PARTIAL"
                if any_succeeded
                else (
                    str(results[-1].get("status") or "ERROR").upper()
                    if results
                    else "ERROR"
                )
            )
        )
        try:
            collection_stats = _engine().brand_collection_stats(brand_key)
            collection_stats_status = "AVAILABLE"
        except Exception:
            collection_stats = None
            collection_stats_status = "UNAVAILABLE"
        return jsonify(
            {
                "ok": all_succeeded,
                "status": status,
                "brand": entry.get("name_zh"),
                "brand_focus_id": scope["brand_focus_id"],
                "accepted_total": accepted_total,
                "collection": collection_stats,
                "collection_stats_status": collection_stats_status,
                "query_count": len(results),
                "query_total": len(terms),
                "results": results,
            }
        ), (200 if all_succeeded or any_succeeded else 503)
    except Exception as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "unavailable",
                    "code": "KOS_COLLECTION_UNAVAILABLE",
                    "error_type": type(exc).__name__,
                }
            ),
            503,
        )


@kos_bp.route("/brand", methods=["GET"])
def api_kos_brand():
    """Read observed authors for the registered BrandFocus, never keyword-derived scope."""
    try:
        if set(request.args) - {"brand", "limit"}:
            raise ValueError("BMP_PROFILE_REQUEST_INVALID")
        actor, actor_ref, scope, selected, decision = _resolve_kos_brand_scope("read")
        supplied = request.args.get("brand")
        aliases = {
            selected.get(key)
            for key in ("name_zh", "name_en", "subject_id", "brand_focus_id", "key")
        }
        if supplied is not None and supplied not in aliases:
            raise ValueError("BRAND_FOCUS_MISMATCH")
        limit = int(request.args.get("limit", "20"))
        if not 1 <= limit <= 100:
            raise ValueError("BMP_PROFILE_LIMIT_INVALID")
        binding = {
            "contract": "lumenis.scope-read-binding.v1",
            "domain_id": "BMP",
            "product_id": "ZBMP",
            "read_allowed": True,
            "scope_verified": True,
            "canonical_scope": "FOCUS",
            "subject_id": selected["subject_id"],
            "brand_focus_id": scope["brand_focus_id"],
        }
        result = _engine().read_scoped_profiles(binding)
        current = _resolve_kos_brand_scope("read")
        if current[1] != actor_ref or current[2] != scope or current[3] != selected:
            raise PermissionError("SCOPE_PERMISSION_CHANGED")
        rows = result.pop("profiles")
        return jsonify(
            {
                "ok": True,
                "brand": _kos_selected_brand_name(selected),
                "binding": binding,
                "stats": result,
                "profiles": rows[:limit],
                "has_more": len(rows) > limit,
            }
        )
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "BMP_PROFILE_UNAVAILABLE"}), 503


@kos_bp.route("/ownership", methods=["GET"])
def api_kos_ownership():
    return _scoped_profile_view("ownership")


@kos_bp.route("/execution", methods=["POST"])
def api_kos_execution_create():
    return _scoped_execution_route("create", execution_id=None, action_type=None)


@kos_bp.route("/execution/<execution_id>/transition", methods=["POST"])
def api_kos_execution_transition(execution_id):
    return _scoped_execution_route(
        "transition", execution_id=execution_id, action_type=None
    )


@kos_bp.route("/executions", methods=["GET"])
def api_kos_executions():
    return _scoped_execution_route("list", execution_id=None, action_type=None)


@kos_bp.route("/account", methods=["GET"])
def api_kos_account():
    return _scoped_profile_view("account")


@kos_bp.route("/ownership/confirm", methods=["POST"])
def api_kos_ownership_confirm():
    return _private_kos_operation("ownership_claim")


@kos_bp.route("/ownership/overrides", methods=["GET"])
def api_kos_ownership_overrides():
    return _private_kos_operation("ownership_claim", list_all=False)


# ===== KOS 运营模块端点（kos_ops.py：留资/合作/邮件邀约/运营闭环） =====
@kos_bp.route("/lead", methods=["GET", "POST"])
def api_kos_lead():
    return _private_kos_operation("lead", list_all=False)


@kos_bp.route("/cooperation", methods=["GET", "POST"])
def api_kos_cooperation():
    return _private_kos_operation("cooperation", list_all=False)


@kos_bp.route("/cooperation/confirm", methods=["POST"])
def api_kos_cooperation_confirm():
    return _scoped_execution_route(
        "create", execution_id=None, action_type="cooperation_confirm"
    )


@kos_bp.route("/cooperation/execute", methods=["POST"])
def api_kos_cooperation_execute():
    return _scoped_execution_route("execute", execution_id=None, action_type=None)


@kos_bp.route("/email/invitation", methods=["POST"])
def api_kos_email_invitation():
    return _scoped_execution_route(
        "create", execution_id=None, action_type="email_send"
    )


@kos_bp.route("/email/send", methods=["POST"])
def api_kos_email_send():
    return _scoped_execution_route("execute", execution_id=None, action_type=None)


@kos_bp.route("/operations", methods=["GET"])
def api_kos_operations():
    return _private_kos_operation(None, list_all=True)


@kos_bp.route("/operation", methods=["POST"])
def api_kos_record_operation():
    return _private_kos_operation("operation_note")


# ===== KOS P2 投流与奖励端点（kos_paid.py） =====
@kos_bp.route("/paid/plan", methods=["POST"])
def api_kos_paid_plan():
    return _private_kos_operation("paid_plan", list_all=False)


@kos_bp.route("/paid/execute", methods=["POST"])
def api_kos_paid_execute():
    return _scoped_execution_route("execute", execution_id=None, action_type=None)


@kos_bp.route("/paid/result", methods=["POST"])
def api_kos_paid_result():
    return _private_kos_operation("paid_result")


@kos_bp.route("/paid/plans", methods=["GET"])
def api_kos_paid_plans():
    return _private_kos_operation("paid_plan", list_all=False)


@kos_bp.route("/reward/issue", methods=["POST"])
def api_kos_reward_issue():
    return _private_kos_operation("reward_plan", list_all=False)


@kos_bp.route("/reward/execute", methods=["POST"])
def api_kos_reward_execute():
    return _scoped_execution_route("execute", execution_id=None, action_type=None)


@kos_bp.route("/rewards", methods=["GET"])
def api_kos_rewards():
    return _private_kos_operation("reward_plan", list_all=False)


def _kos_profile_field(author_id: str, field: str):
    """辅助：读取 kos_profiles 单字段。"""
    from lumenis.shared.database import get_repository

    conn = get_repository().connect()
    try:
        r = conn.execute(
            f"SELECT {field} FROM kos_profiles WHERE author_id = ?", (author_id,)
        ).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def _DB():
    from lumenis.shared.database import main_db_path

    return main_db_path()


# ============ 专业号接入口（每品牌可选，默认关闭，熔断保护） ============


def _professional():
    try:
        import kos_professional as kp

        return kp
    except Exception as e:
        print(f"[KOS] professional module unavailable: {e}")
        return None


def _professional_scoped_response(mode):
    import uuid
    import kos_professional
    import kos_ops

    try:
        writing = request.method == "POST"
        actor, _actor_ref, scope, selected, _decision = _resolve_kos_brand_scope(
            "write" if writing else "read"
        )
        body = request.get_json(silent=True) if writing else dict(request.args)
        if not isinstance(body, dict):
            raise ValueError("PROFESSIONAL_REQUEST_INVALID")
        allowed = {
            "brand_id",
            "platform",
            "account_id",
            "account_name",
            "request_id",
            "expected_version",
            "metrics",
            "start_date",
            "end_date",
        }
        if set(body) - allowed:
            raise ValueError("PROFESSIONAL_REQUEST_FIELDS_INVALID")
        if body.get("brand_id") not in (
            None,
            scope["brand_focus_id"],
            selected["subject_id"],
        ):
            raise ValueError("PROFESSIONAL_BRAND_SCOPE_MISMATCH")
        if writing:
            from experience_runtime import _content_source_same_origin

            if not _content_source_same_origin():
                raise PermissionError("PROFESSIONAL_ORIGIN_DENIED")
        platform = body.get("platform", "xiaohongshu")
        account_id = body.get("account_id", "")
        common = {"actor": actor, "scope": scope}
        if mode == "status":
            result = kos_professional.read_scoped_accounts(**common, platform=platform)
            result.update(
                enabled=any(a["enabled"] for a in result["accounts"]),
                account_count=len(result["accounts"]),
            )
        elif mode == "metrics":
            result = kos_professional.read_scoped_metrics(
                **common,
                platform=platform,
                account_id=account_id,
                start_date=body.get("start_date", ""),
                end_date=body.get("end_date", ""),
            )
        else:
            common.update(
                platform=platform,
                account_id=account_id,
                request_id=body.get("request_id") or "professional-" + uuid.uuid4().hex,
                expected_version=body.get("expected_version", 0),
            )
            if mode in {"enable", "disable"}:
                result = kos_professional.configure_scoped_account(
                    **common,
                    enabled=mode == "enable",
                    account_name=body.get("account_name", ""),
                )
            else:
                result = kos_professional.import_scoped_metrics(
                    **common, metrics=body.get("metrics")
                )
        return jsonify({"ok": True, **result})
    except kos_ops.ScopedOperationApprovalRequired as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "code": str(exc),
                    "resource": exc.resource,
                    "request_id": exc.request_id,
                    "challenge": _kos_approval_challenge(exc.resource, exc.request_id),
                }
            ),
            403,
        )
    except kos_ops.ScopedOperationHistoryLimitError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 503
    except PermissionError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 403
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "code": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "code": "PROFESSIONAL_OWNER_UNAVAILABLE"}), 503


@kos_bp.route("/professional/status", methods=["GET"])
def api_professional_status():
    return _professional_scoped_response("status")


@kos_bp.route("/professional/enable", methods=["POST"])
def api_professional_enable():
    return _professional_scoped_response("enable")


@kos_bp.route("/professional/disable", methods=["POST"])
def api_professional_disable():
    return _professional_scoped_response("disable")


@kos_bp.route("/professional/import", methods=["POST"])
def api_professional_import():
    return _professional_scoped_response("import")


@kos_bp.route("/professional/metrics", methods=["GET"])
def api_professional_metrics():
    return _professional_scoped_response("metrics")


def register_kos_api(app):
    """注册 KOS Blueprint 到 Flask app。"""

    app.register_blueprint(kos_bp)


# Exact routing map for the HTTP perimeter; each owner still checks live scope
# and its payload-bound effect immediately before committing.
_KOS_STATELESS_READ_POSTS = {"api_refresh", "api_kos_identity", "api_kos_campaign"}

_KOS_PRIVATE_WRITE_ROUTES = {
    "api_report_generate": "/api/kos/report/generate",
    "api_refresh": "/api/kos/refresh",
    "api_kos_identity": "/api/kos/kos-identity",
    "api_kos_campaign": "/api/kos/campaign",
    "api_professional_enable": "/api/kos/professional/enable",
    "api_professional_disable": "/api/kos/professional/disable",
    "api_professional_import": "/api/kos/professional/import",
    "api_outreach": "/api/kos/outreach",
    "api_reply_generate": "/api/kos/reply/generate",
    "api_kos_lead": "/api/kos/lead",
    "api_kos_cooperation": "/api/kos/cooperation",
    "api_kos_manual": "/api/kos/manual",
    "api_kos_paid_plan": "/api/kos/paid/plan",
    "api_kos_reward_issue": "/api/kos/reward/issue",
    "api_kos_execution_create": "/api/kos/execution",
    "api_kos_execution_transition": "/api/kos/execution/<execution_id>/transition",
    "api_kos_cooperation_confirm": "/api/kos/cooperation/confirm",
    "api_kos_cooperation_execute": "/api/kos/cooperation/execute",
    "api_kos_email_invitation": "/api/kos/email/invitation",
    "api_kos_email_send": "/api/kos/email/send",
    "api_kos_paid_execute": "/api/kos/paid/execute",
    "api_kos_reward_execute": "/api/kos/reward/execute",
    "api_kos_ownership_confirm": "/api/kos/ownership/confirm",
    "api_kos_record_operation": "/api/kos/operation",
    "api_kos_paid_result": "/api/kos/paid/result",
    "api_kos_approval_confirm": "/api/kos/approvals/confirm",
    "api_kos_approval_revoke": "/api/kos/approvals/revoke",
}
_KOS_PRIVATE_READ_ROUTES = {
    "api_report_view": "/api/kos/report/view",
    "api_overview": "/api/kos/overview",
    "api_list": "/api/kos/list",
    "api_detail": "/api/kos/detail",
    "api_comments": "/api/kos/comments",
    "api_ad_candidates": "/api/kos/ad-candidates",
    "api_reward": "/api/kos/reward",
    "api_content_dna": "/api/kos/content-dna",
    "api_attribution": "/api/kos/attribution",
    "api_intent_analysis": "/api/kos/intent-analysis",
    "api_kos_identity": "/api/kos/kos-identity",
    "api_competitor_benchmark": "/api/kos/competitor-benchmark",
    "api_kos_funnel": "/api/kos/funnel",
    "api_kos_cost": "/api/kos/cost",
    "api_kos_tier": "/api/kos/tier",
    "api_kos_koc_tier": "/api/kos/koc-tier",
    "api_kos_channel_roi": "/api/kos/channel-roi",
    "api_kos_profile": "/api/kos/profile",
    "api_kos_brand": "/api/kos/brand",
    "api_kos_ownership": "/api/kos/ownership",
    "api_kos_account": "/api/kos/account",
    "api_professional_status": "/api/kos/professional/status",
    "api_professional_metrics": "/api/kos/professional/metrics",
    "api_kos_lead": "/api/kos/lead",
    "api_kos_cooperation": "/api/kos/cooperation",
    "api_kos_ownership_overrides": "/api/kos/ownership/overrides",
    "api_kos_operations": "/api/kos/operations",
    "api_kos_executions": "/api/kos/executions",
    "api_kos_paid_plans": "/api/kos/paid/plans",
    "api_kos_rewards": "/api/kos/rewards",
}


def private_kos_route_matches(*, write_only=False):
    aggregate_routes = {
        "lumenis_agg.kos_professional_status": ("/api/kos/professional/status", "GET"),
        "lumenis_agg.kos_professional_enable": ("/api/kos/professional/enable", "POST"),
        "lumenis_agg.kos_professional_disable": (
            "/api/kos/professional/disable",
            "POST",
        ),
        "lumenis_agg.kos_professional_import": ("/api/kos/professional/import", "POST"),
    }
    expected = aggregate_routes.get(request.endpoint)
    if expected is not None:
        return bool(
            request.url_rule is not None
            and request.url_rule.rule == expected[0]
            and request.method == expected[1]
            and (not write_only or request.method == "POST")
        )
    routes = (
        _KOS_PRIVATE_WRITE_ROUTES
        if request.method == "POST"
        else (
            _KOS_PRIVATE_READ_ROUTES
            if request.method == "GET" and not write_only
            else {}
        )
    )
    name = (request.endpoint or "").removeprefix(kos_bp.name + ".")
    return bool(
        request.endpoint == kos_bp.name + "." + name
        and request.url_rule is not None
        and routes.get(name) == request.url_rule.rule
    )


def private_kos_route_action():
    name = (request.endpoint or "").removeprefix(kos_bp.name + ".")
    return (
        "read"
        if request.method == "GET" or name in _KOS_STATELESS_READ_POSTS
        else "write"
    )


def private_kos_local_access_allowed():
    from lumenis.system.security.permission import LocalWorkspacePrincipal

    if not private_kos_route_matches():
        return False
    try:
        actor, *_rest = _resolve_kos_brand_scope(private_kos_route_action())
        return type(actor) is LocalWorkspacePrincipal
    except (ValueError, PermissionError):
        return False
