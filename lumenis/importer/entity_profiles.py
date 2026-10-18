"""Typed, versioned entity research assertions in the existing document owners.

Registry supplies identity; signed Evidence supplies integrity, not fact truth.
Unknown publisher rights never become redistribution or training permission.
"""

from __future__ import annotations
import contextlib
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from lumenis.shared.database import get_repository
from lumenis.shared.reporting.saved_work import (
    authorize,
    _json,
    _digest,
    _verified_evidence,
)
from . import documents

SCHEMA = "lumenis.entity-profile-assertions/v1"
FIELDS = {
    "official_site",
    "object_kind",
    "industry",
    "region",
    "observed_name",
    "name_en",
    "name_zh",
    "description",
    "operating_status",
    "city",
    "address",
    "property_use",
    "founded_year",
}


def _context(actor, scope, action="read", connection=None):
    context = authorize(actor, scope, action=action, connection=connection)
    if context["global_scope"] or not (
        context["subject_id"] or context["brand_focus_id"]
    ):
        raise ValueError("ENTITY_PROFILE_EXACT_REGISTERED_SCOPE_REQUIRED")
    return context


def validate_manifest(manifest, *, actor, scope):
    context = _context(actor, scope, "write")
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {
            "schema",
            "entity",
            "request_id",
            "version",
            "parent_sha256",
            "imported_at",
            "sources",
            "assertions",
            "review",
        }
        or manifest["schema"] != SCHEMA
        or manifest["entity"]
        != {
            k: context[k]
            for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")
        }
        or not isinstance(manifest["request_id"], str)
        or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", manifest["request_id"]) is None
        or type(manifest["version"]) is not int
        or manifest["version"] < 1
        or (
            manifest["parent_sha256"] is not None
            and re.fullmatch(r"[0-9a-f]{64}", str(manifest["parent_sha256"])) is None
        )
    ):
        raise ValueError("ENTITY_PROFILE_MANIFEST_INVALID")
    if (
        not isinstance(manifest["sources"], list)
        or not 1 <= len(manifest["sources"]) <= 100
    ):
        raise ValueError("ENTITY_PROFILE_SOURCES_REQUIRED")
    source_ids = set()
    for source in manifest["sources"]:
        required = {
            "id",
            "source_url",
            "capture_method",
            "reviewed_on",
            "origin_captured_at",
            "extract_sha256",
            "excerpt",
            "excerpt_sha256",
            "source_range",
            "rights",
        }
        if (
            not isinstance(source, dict)
            or not required.issubset(source)
            or set(source) - required - {"source_as_of", "temporal_scope_note"}
            or source["id"] in source_ids
        ):
            raise ValueError("ENTITY_PROFILE_SOURCE_INVALID")
        source_ids.add(source["id"])
        if (
            not isinstance(source["id"], str)
            or not source["id"]
            or source["capture_method"] != "ASSISTED_WEB_TOOL_TEXT_EXTRACT"
            or source["rights"] != "UNKNOWN"
            or source["origin_captured_at"] is not None
            or not isinstance(source["excerpt"], str)
            or not 1 <= len(source["excerpt"]) <= 4000
            or hashlib.sha256(source["excerpt"].encode()).hexdigest()
            != source["excerpt_sha256"]
            or re.fullmatch(r"[0-9a-f]{64}", str(source["extract_sha256"])) is None
            or re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(source["reviewed_on"])) is None
        ):
            raise ValueError("ENTITY_PROFILE_CAPTURE_INVALID")
        if (
            source.get("source_as_of") is not None
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(source["source_as_of"])) is None
        ):
            raise ValueError("ENTITY_PROFILE_SOURCE_DATE_INVALID")
        from datetime import date

        for field in ("reviewed_on", "source_as_of"):
            if source.get(field) is not None:
                try:
                    date.fromisoformat(source[field])
                except (ValueError, TypeError) as exc:
                    raise ValueError("ENTITY_PROFILE_SOURCE_DATE_INVALID") from exc
        if "temporal_scope_note" in source and (
            not isinstance(source["temporal_scope_note"], str)
            or len(source["temporal_scope_note"]) > 1000
        ):
            raise ValueError("ENTITY_PROFILE_SOURCE_TIME_NOTE_INVALID")
        parsed = urlsplit(source["source_url"])
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("ENTITY_PROFILE_URL_INVALID")
        span = source["source_range"]
        if (
            not isinstance(span, dict)
            or set(span) != {"unit", "start", "end"}
            or span["unit"] != "extracted-page-text"
            or type(span["start"]) is not int
            or type(span["end"]) is not int
            or span["start"] < 0
            or span["end"] - span["start"] != len(source["excerpt"])
        ):
            raise ValueError("ENTITY_PROFILE_SOURCE_RANGE_INVALID")
    if (
        not isinstance(manifest["assertions"], list)
        or not 1 <= len(manifest["assertions"]) <= 200
    ):
        raise ValueError("ENTITY_PROFILE_ASSERTIONS_REQUIRED")
    assertion_ids = set()
    for assertion in manifest["assertions"]:
        if (
            not isinstance(assertion, dict)
            or set(assertion) != {"id", "field", "value", "source_id", "claim_type"}
            or not isinstance(assertion["id"], str)
            or not assertion["id"]
            or assertion["id"] in assertion_ids
            or assertion["field"] not in FIELDS
            or assertion["source_id"] not in source_ids
            or assertion["claim_type"] != "source_statement"
            or not (
                (
                    isinstance(assertion["value"], str)
                    and 0 < len(assertion["value"]) <= 1000
                )
                or (
                    assertion["field"] == "founded_year"
                    and type(assertion["value"]) is int
                    and 1 <= assertion["value"] <= 9999
                )
            )
        ):
            raise ValueError("ENTITY_PROFILE_ASSERTION_INVALID")
        assertion_ids.add(assertion["id"])
    if not isinstance(manifest["review"], dict) or set(manifest["review"]) - FIELDS:
        raise ValueError("ENTITY_PROFILE_REVIEW_INVALID")
    for field, selected in manifest["review"].items():
        if selected is not None and not any(
            a["id"] == selected and a["field"] == field for a in manifest["assertions"]
        ):
            raise ValueError("ENTITY_PROFILE_REVIEW_ASSERTION_MISMATCH")
    return json.loads(_json(manifest)), context


def read_profiles(*, actor, scope, connection=None):
    context = _context(actor, scope, connection=connection)
    manager = (
        contextlib.nullcontext(connection)
        if connection is not None
        else get_repository().connection(read_only=True, wal=False)
    )
    versions = []
    with manager as con:
        if (
            con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='canonical_data'"
            ).fetchone()
            is None
        ):
            return {
                "versions": [],
                "current": None,
                "adopted_fields": {},
                "conflicts": [],
            }
        # Type marker lives in signed owner metadata, not user document JSON.
        rows = con.execute(
            "SELECT c.* FROM canonical_data c JOIN app_evidence_records e ON CAST(e.id AS TEXT)=c.scope_evidence_ref WHERE c.source_type='document' AND c.domain_id=? AND COALESCE(c.subject_id,'')=? AND COALESCE(c.brand_focus_id,'')=? AND e.collection_metadata LIKE '%\"entity_profile\"%' ORDER BY e.id",
            (
                context["domain_id"],
                context["subject_id"] or "",
                context["brand_focus_id"] or "",
            ),
        ).fetchall()
        import canonical_data

        for raw in rows:
            row = dict(raw)
            proof = canonical_data.list_scoped_canonical(
                con,
                product_id="CTH" if context["domain_id"] == "cth" else "ZBMP",
                subject_id=context["subject_id"],
                brand_focus_id=context["brand_focus_id"],
                source_ids=[row["source_id"]],
                limit=100,
            )
            if not any(
                r["canonical_id"] == row["canonical_id"] for r in proof["records"]
            ):
                raise ValueError("ENTITY_PROFILE_CANONICAL_INTEGRITY_FAILED")
            try:
                evidence = _verified_evidence(
                    con, int(row["scope_evidence_ref"]), context, actor
                )
            except ValueError as exc:
                if str(exc) in {
                    "WORK_EVIDENCE_OWNER_MISMATCH",
                    "WORK_EVIDENCE_CONTEXT_MISMATCH",
                }:
                    continue
                raise
            marker = evidence["provenance"].get("entity_profile")
            if not isinstance(marker, dict) or marker.get("schema") != SCHEMA:
                continue
            manifest = json.loads(evidence["raw_content"])
            digest = _digest(manifest)
            if (
                marker.get("sha256") != digest
                or row["content"] != evidence["raw_content"]
            ):
                raise ValueError("ENTITY_PROFILE_MANIFEST_INTEGRITY_FAILED")
            documents._source_bytes(con, evidence)
            versions.append(
                {
                    "manifest": manifest,
                    "sha256": digest,
                    "evidence_id": evidence["id"],
                    "canonical_id": row["canonical_id"],
                    "source_id": row["source_id"],
                }
            )
        _context(actor, scope, connection=con)
    versions.sort(key=lambda row: row["manifest"]["version"])
    parent = None
    for i, row in enumerate(versions, 1):
        if (
            row["manifest"]["version"] != i
            or row["manifest"]["parent_sha256"] != parent
        ):
            raise ValueError("ENTITY_PROFILE_VERSION_CHAIN_INVALID")
        parent = row["sha256"]
    current = versions[-1] if versions else None
    adopted, conflicts = {}, []
    if current:
        manifest = current["manifest"]
        for field in FIELDS:
            candidates = [a for a in manifest["assertions"] if a["field"] == field]
            selected = manifest["review"].get(field)
            chosen = next((a for a in candidates if a["id"] == selected), None)
            adopted[field] = (
                {
                    "value": chosen["value"],
                    "assertion_id": chosen["id"],
                    "source_id": chosen["source_id"],
                    "state": "REVIEW_ADOPTED_SOURCE_STATEMENT",
                    "factual_truth": "NOT_INDEPENDENTLY_ESTABLISHED",
                    "current_validity": "NOT_ESTABLISHED",
                    "source_time": {
                        k: next(
                            s
                            for s in manifest["sources"]
                            if s["id"] == chosen["source_id"]
                        ).get(k)
                        for k in (
                            "reviewed_on",
                            "origin_captured_at",
                            "source_as_of",
                            "temporal_scope_note",
                        )
                    },
                }
                if chosen
                else None
            )
            if len({a["value"] for a in candidates}) > 1:
                conflicts.append(
                    {
                        "field": field,
                        "assertions": candidates,
                        "selected_assertion_id": selected,
                    }
                )
    return {
        "versions": versions,
        "current": current,
        "adopted_fields": adopted,
        "conflicts": conflicts,
        "source_rights": "UNKNOWN",
        "redistribution_allowed": False,
        "training_eligible": False,
        "hash_scope": "WEB_TOOL_TEXT_EXTRACT_NOT_ORIGIN_BYTES",
        "signature_is_not_fact_verification": True,
        "full_extract_hash_verification": "DECLARED_NOT_RECOMPUTED_FROM_EXCERPT",
        "retained_excerpt_hash_verification": "VERIFIED",
    }


def prepare_profile(manifest, *, actor, scope):
    manifest, context = validate_manifest(manifest, actor=actor, scope=scope)
    digest = _digest(manifest)
    provenance = {
        "source_url": None,
        "published_at": None,
        "captured_at": manifest["imported_at"],
        "rights": "owner-approved",
        "title": "Entity profile research assertions",
        "source_origin": {"kind": "approved-file", "ref": manifest["request_id"]},
        "content_origin": {
            "kind": "researcher-note",
            "claim_type": "research_inference",
        },
        "rights_statement": "Approval covers this private research compilation only. Underlying publisher rights remain UNKNOWN; no redistribution or training.",
        "intended_use": "research_reference",
    }
    with tempfile.TemporaryDirectory(prefix="lumenis-entity-profile-") as tmp:
        path = Path(tmp) / "entity-profile.txt"
        path.write_bytes(_json(manifest))
        resource = documents.document_import_resource(
            str(path), actor=actor, scope=scope, provenance=provenance
        )
    return {
        "manifest": manifest,
        "sha256": digest,
        "resource": resource,
        "provenance": provenance,
    }


def import_profile(manifest, *, actor, scope):
    prepared = prepare_profile(manifest, actor=actor, scope=scope)
    manifest = prepared["manifest"]
    from lumenis.system.security.permission import get_permission_gate

    def exact_approval():
        if (
            get_permission_gate().get_valid_approval_token(
                "data_import", prepared["resource"], exact=True
            )
            is None
        ):
            raise ValueError("WORK_EFFECT_PERMISSION_DENIED")

    exact_approval()

    def validate_in_transaction(con):
        exact_approval()
        existing = read_profiles(actor=actor, scope=scope, connection=con)
        replay = next(
            (
                r
                for r in existing["versions"]
                if r["manifest"]["request_id"] == manifest["request_id"]
            ),
            None,
        )
        if replay:
            if replay["sha256"] != prepared["sha256"]:
                raise ValueError("ENTITY_PROFILE_REQUEST_CONFLICT")
            return
        head = existing["current"]
        if manifest["version"] != (
            head["manifest"]["version"] + 1 if head else 1
        ) or manifest["parent_sha256"] != (head["sha256"] if head else None):
            raise ValueError("ENTITY_PROFILE_VERSION_CONFLICT")

    with tempfile.TemporaryDirectory(prefix="lumenis-entity-profile-") as tmp:
        path = Path(tmp) / "entity-profile.txt"
        path.write_bytes(_json(manifest))
        return documents.import_document(
            str(path),
            actor=actor,
            scope=scope,
            provenance=prepared["provenance"],
            _transaction_validator=validate_in_transaction,
            _owner_metadata={
                "entity_profile": {"schema": SCHEMA, "sha256": prepared["sha256"]}
            },
        )
