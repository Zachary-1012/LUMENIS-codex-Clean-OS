"""Exact-scope, retryable document ingestion into the existing Evidence/Canonical owners.

The caller supplies one approved local file and provenance. No network, AI,
schema creation or production database selection occurs in this service.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

import canonical_data
from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store as evidence_store
from lumenis.shared.reporting.saved_work import (
    SavedWorkError, _check_effect, _digest, _json, _verified_evidence, authorize, staging_write, _stage_bytes,
)
from lumenis.shared.reporting.operational_brief import _source_url
from lumenis.system.security.permission import OperationType
from .parser import parse_file


_APPROVED_SOURCE_USE_RECEIPT_ID = "PO-20261011-APPROVED-INTERNAL-SOURCE-USE"
_APPROVED_SOURCE_REFERENCE_FEATURE = "APPROVED_INTERNAL_SOURCE_REFERENCE"


def _approved_source_use_receipt_entry(
    source_id: str, receipt_id: str = _APPROVED_SOURCE_USE_RECEIPT_ID,
) -> tuple[dict, dict]:
    from lumenis.system.security.permission import _load_source_use_receipt

    receipt = _load_source_use_receipt(receipt_id)
    matches = [source for source in receipt["sources"]
               if isinstance(source, dict) and source.get("source_id") == source_id]
    if len(matches) != 1:
        raise SavedWorkError("SOURCE_USE_SOURCE_NOT_APPROVED")
    entry = matches[0]
    if (entry.get("snapshot_kind") not in {
            "existing_canonical_content_snapshot_not_native_capture",
            "existing_source_evidence_snapshot"}
            or entry.get("commercial_state") != "UNKNOWN"
            or entry.get("publication_state") != "NOT_APPROVED"
            or entry.get("training_state") != "NOT_APPROVED"):
        raise SavedWorkError("SOURCE_USE_APPROVAL_RECEIPT_INVALID")
    return receipt, entry


def _approved_source_use_entry(source_id: str, receipt_id: str = _APPROVED_SOURCE_USE_RECEIPT_ID) -> dict:
    return _approved_source_use_receipt_entry(source_id, receipt_id)[1]


def _approved_source_parent_binding(entry: Mapping, derived_content_evidence_ref: str) -> dict:
    return {
        "receipt_id": _APPROVED_SOURCE_USE_RECEIPT_ID,
        "source_id": entry["source_id"],
        "source_url": entry["source_url"],
        "domain_id": entry["domain_id"],
        "subject_id": entry["subject_id"],
        "brand_focus_id": entry["brand_focus_id"],
        "scope_evidence_ref": entry["scope_evidence_ref"],
        "source_content_locator": entry["content_evidence_ref"],
        "derived_content_evidence_ref": derived_content_evidence_ref,
        "body_sha256": entry["body_sha256"],
        "snapshot_kind": entry["snapshot_kind"],
    }


def _approved_source_use_marker(entry: Mapping, derived_content_evidence_ref: str) -> dict:
    return {
        "receipt_id": _APPROVED_SOURCE_USE_RECEIPT_ID,
        "source_id": entry["source_id"],
        "source_url": entry["source_url"],
        "domain_id": entry["domain_id"],
        "subject_id": entry["subject_id"],
        "brand_focus_id": entry["brand_focus_id"],
        "scope_evidence_ref": entry["scope_evidence_ref"],
        "content_evidence_ref": derived_content_evidence_ref,
        "body_sha256": entry["body_sha256"],
        "allowed_purposes": list(entry["allowed_purposes"]),
        "allowed_operations": [operation for operation in entry["allowed_operations"]
                               if operation in {"read", "save", "revise", "reopen"}],
        "rights_state": entry["rights_state"],
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }


def _approved_source_canonical(con, entry: Mapping) -> tuple[dict, dict, str]:
    """Read the one current, scope-verified Canonical and its exact source body."""
    cursor = con.execute(
        "SELECT * FROM canonical_data WHERE canonical_id=? AND source_id=? AND domain_id=? "
        "AND product_id=? AND NULLIF(subject_id,'') IS ? AND NULLIF(brand_focus_id,'') IS ? "
        "AND scope_status='VERIFIED'",
        (entry["canonical_id"], entry["source_id"], entry["domain_id"],
         "CTH" if entry["domain_id"] == "cth" else "ZBMP",
         entry["subject_id"], entry["brand_focus_id"]),
    )
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise SavedWorkError("SOURCE_USE_CANONICAL_SOURCE_UNAVAILABLE")
    canonical = dict(zip((column[0] for column in cursor.description), rows[0]))
    body = canonical.get("content")
    if (canonical.get("url") != entry["source_url"] or type(body) is not str
            or hashlib.sha256(body.encode("utf-8")).hexdigest() != entry["body_sha256"]):
        raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")
    try:
        raw_ref = json.loads(canonical.get("raw_ref") or "{}")
    except (TypeError, ValueError) as exc:
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID") from exc
    if not isinstance(raw_ref, dict):
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")

    locator = entry["content_evidence_ref"]
    if locator.startswith("notes:"):
        match = re.fullmatch(r"notes:([1-9][0-9]*)", locator)
        if (entry["domain_id"] != "cth" or match is None
                or raw_ref.get("table") != "notes"
                or raw_ref.get("note_id") != entry["source_id"]
                or raw_ref.get("id") != int(match.group(1))):
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
        note_cursor = con.execute("SELECT * FROM notes WHERE id=?", (int(match.group(1)),))
        note_row = note_cursor.fetchone()
        if note_row is None:
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_MISSING")
        note = dict(zip((column[0] for column in note_cursor.description), note_row))
        note_body = note.get("content") or note.get("body")
        note_source_id = note.get("source_id") or note.get("note_id") or entry["source_id"]
        if (note_source_id != entry["source_id"]
                or note.get("url") not in {None, "", entry["source_url"]}
                or type(note_body) is not str
                or hashlib.sha256(note_body.encode("utf-8")).hexdigest() != entry["body_sha256"]):
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_INVALID")
        original_rights = note.get("rights", note.get("rights_state"))
    else:
        from lumenis.shared.evidence.store import classify_evidence_integrity

        match = re.fullmatch(r"app_evidence_records:([1-9][0-9]*)", locator)
        if match is None:
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
        evidence_cursor = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (int(match.group(1)),))
        evidence_row = evidence_cursor.fetchone()
        if evidence_row is None:
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_MISSING")
        evidence = dict(zip((column[0] for column in evidence_cursor.description), evidence_row))
        integrity = classify_evidence_integrity(evidence)
        try:
            metadata = json.loads(evidence.get("collection_metadata") or "{}")
            inputs = json.loads(evidence.get("inputs_json") or "{}")
        except (TypeError, ValueError) as exc:
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_INVALID") from exc
        product = "CTH" if entry["domain_id"] == "cth" else "ZBMP"
        expected_scope = evidence_store._normalize_record_evidence_scope(
            product=product, domain_id=entry["domain_id"], subject_id=entry["subject_id"],
            brand_focus_id=entry["brand_focus_id"], global_scope=False,
        )
        source_provenance = metadata.get("provenance") if isinstance(metadata, dict) else None
        if (integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated"
                or evidence.get("result") != "PASS" or evidence.get("status") != "verified"
                or evidence.get("asset_id") != entry["source_id"]
                or evidence.get("domain_id") != entry["domain_id"]
                or evidence.get("product_id") != product
                or not isinstance(inputs, dict)
                or inputs.get("_lumenis_scope") != expected_scope
                or not isinstance(source_provenance, dict)
                or metadata.get("parsed_text") != body):
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_INVALID")
        try:
            original_raw, _ = _source_bytes(con, {**evidence, "provenance": metadata})
        except (SavedWorkError, OSError, ValueError) as exc:
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_INVALID") from exc
        if original_raw.decode("utf-8", errors="strict") != body:
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_INVALID")
        original_rights = source_provenance.get("rights")
        scope_match = re.fullmatch(r"app_evidence_records:([1-9][0-9]*)", entry["scope_evidence_ref"])
        if scope_match is None:
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
        scope_cursor = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (int(scope_match.group(1)),))
        scope_row = scope_cursor.fetchone()
        if scope_row is None:
            raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_MISSING")
        scope_evidence = dict(zip((column[0] for column in scope_cursor.description), scope_row))
        scope_integrity = classify_evidence_integrity(scope_evidence)
        try:
            scope_inputs = json.loads(scope_evidence.get("inputs_json") or "{}")
        except (TypeError, ValueError) as exc:
            raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH") from exc
        if (scope_integrity.get("verified") is not True
                or scope_integrity.get("assurance") != "writer-authenticated"
                or scope_evidence.get("result") != "PASS" or scope_evidence.get("status") != "verified"
                or scope_evidence.get("domain_id") != entry["domain_id"]
                or scope_evidence.get("product_id") != product
                or not isinstance(scope_inputs, dict)
                or scope_inputs.get("_lumenis_scope") != expected_scope):
            raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH")
    from lumenis.system.security.permission import _source_use_rights_state

    if _source_use_rights_state(original_rights) != entry["rights_state"]:
        raise SavedWorkError("SOURCE_USE_RIGHTS_STATE_CHANGED")
    mapping = raw_ref.get("approved_internal_source_use")
    if mapping is not None:
        if (not isinstance(mapping, dict)
                or mapping.get("receipt_id") != _APPROVED_SOURCE_USE_RECEIPT_ID
                or mapping.get("source_id") != entry["source_id"]
                or mapping.get("source_url") != entry["source_url"]
                or mapping.get("domain_id") != entry["domain_id"]
                or mapping.get("subject_id") != entry["subject_id"]
                or mapping.get("brand_focus_id") != entry["brand_focus_id"]
                or mapping.get("scope_evidence_ref") != entry["scope_evidence_ref"]
                or mapping.get("source_content_locator") != entry["content_evidence_ref"]
                or mapping.get("body_sha256") != entry["body_sha256"]
                or mapping.get("snapshot_kind") != entry["snapshot_kind"]
                or not re.fullmatch(r"app_evidence_records:[1-9][0-9]*",
                                    mapping.get("derived_content_evidence_ref", ""))):
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_CHANGED")
    return canonical, raw_ref, body


def resolve_approved_source_reference(
    connection, *, source_id: str, canonical_id: str, domain_id: str,
    subject_id: str | None, brand_focus_id: str | None,
    source_content_locator: str, body_sha256: str,
) -> dict:
    """Resolve only the derivative reference attached by the approved importer."""
    from lumenis.system.security import permission
    from lumenis.shared.evidence.store import classify_evidence_integrity

    entry = _approved_source_use_entry(source_id)
    if (entry.get("canonical_id") != canonical_id or entry.get("domain_id") != domain_id
            or entry.get("subject_id") != subject_id or entry.get("brand_focus_id") != brand_focus_id
            or entry.get("content_evidence_ref") != source_content_locator
            or entry.get("body_sha256") != body_sha256):
        raise SavedWorkError("SOURCE_USE_SCOPE_OR_CONTENT_MISMATCH")
    try:
        con = permission._require_canonical_scope_connection(connection)
        checked = permission.validate_current_source_use(
            con, source_id=source_id, source_url=entry["source_url"], domain_id=domain_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id,
            scope_evidence_ref=entry["scope_evidence_ref"], content_evidence_ref=source_content_locator,
            body_sha256=body_sha256, purpose="internal_research", operation="read",
            receipt_id=_APPROVED_SOURCE_USE_RECEIPT_ID)
        canonical, raw_ref, body = _approved_source_canonical(con, entry)
    except permission.SourceUseApprovalError as exc:
        raise SavedWorkError(exc.code) from exc
    except (TypeError, ValueError, RuntimeError) as exc:
        if isinstance(exc, SavedWorkError):
            raise
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID") from exc
    binding = raw_ref.get("approved_internal_source_use")
    if not isinstance(binding, dict):
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_NOT_ADMITTED")
    match = re.fullmatch(r"app_evidence_records:([1-9][0-9]*)",
                         binding.get("derived_content_evidence_ref", ""))
    if match is None:
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
    evidence_id = int(match.group(1))
    cursor = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,))
    row = cursor.fetchone()
    if row is None:
        raise SavedWorkError("SOURCE_USE_SOURCE_EVIDENCE_MISSING")
    evidence = dict(zip((column[0] for column in cursor.description), row))
    integrity = classify_evidence_integrity(evidence)
    try:
        metadata = json.loads(evidence.get("collection_metadata") or "{}")
        inputs = json.loads(evidence.get("inputs_json") or "{}")
    except (TypeError, ValueError) as exc:
        raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_INVALID") from exc
    if not isinstance(metadata, dict) or not isinstance(inputs, dict):
        raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_INVALID")
    product = "CTH" if entry["domain_id"] == "cth" else "ZBMP"
    expected_scope = evidence_store._normalize_record_evidence_scope(
        product=product, domain_id=entry["domain_id"], subject_id=entry["subject_id"],
        brand_focus_id=entry["brand_focus_id"], global_scope=False,
    )
    expected_binding = _approved_source_parent_binding(entry, f"app_evidence_records:{evidence_id}")
    marker = (metadata.get("provenance", {}).get("approved_internal_source_use")
              if isinstance(metadata, dict) and isinstance(metadata.get("provenance"), dict) else None)
    expected_marker = _approved_source_use_marker(entry, f"app_evidence_records:{evidence_id}")
    if (integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated"
            or evidence.get("feature_id") != _APPROVED_SOURCE_REFERENCE_FEATURE
            or evidence.get("asset_id") != "approved-source-reference:" + hashlib.sha256(
                f"{entry['canonical_id']}\n{entry['body_sha256']}".encode()).hexdigest()[:32]
            or evidence.get("result") != "PASS" or evidence.get("status") != "verified"
            or evidence.get("domain_id") != entry["domain_id"]
            or evidence.get("product_id") != product
            or inputs.get("_lumenis_scope") != expected_scope
            or metadata.get("source_reference_parent") != expected_binding
            or metadata.get("provenance", {}).get("source_reference_parent") != expected_binding
            or metadata.get("provenance", {}).get("parsed_text") != body
            or hashlib.sha256(body.encode("utf-8")).hexdigest() != entry["body_sha256"]
            or not isinstance(marker, dict)
            or marker != expected_marker
            or checked.get("rights_state") != entry["rights_state"]):
        raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_INVALID")
    try:
        source_bytes, _ = _source_bytes(con, {**evidence, "provenance": metadata})
    except (SavedWorkError, OSError, ValueError) as exc:
        raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_INVALID") from exc
    if source_bytes != body.encode("utf-8"):
        raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_INVALID")
    return {"evidence_id": evidence_id,
            "content_evidence_ref": f"app_evidence_records:{evidence_id}",
            "derived_content_evidence_ref": f"app_evidence_records:{evidence_id}",
            "scope_evidence_ref": entry["scope_evidence_ref"],
            "source_content_locator": source_content_locator,
            "body_sha256": body_sha256, "canonical_id": canonical_id,
            "source_reference_parent": expected_binding}


def _prepare_approved_source_reference(
    con, *, source_id: str, canonical_id: str, expected_body_sha256: str,
    request_id: str, actor: Any, scope: Mapping, action: str, source_use_operation: str,
) -> tuple[dict, dict, dict, dict, str]:
    """Describe an exact current request; no effect admission or writes occur here."""
    if (type(source_id) is not str or not source_id or source_id != source_id.strip()
            or type(canonical_id) is not str or not canonical_id
            or type(request_id) is not str or re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", request_id) is None
            or type(expected_body_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_body_sha256) is None):
        raise SavedWorkError("SOURCE_USE_REQUEST_INVALID")
    context = authorize(actor, scope, action=action, connection=con)
    receipt, entry = _approved_source_use_receipt_entry(source_id)
    if (canonical_id != entry["canonical_id"] or expected_body_sha256 != entry["body_sha256"]
            or context["domain_id"] != entry["domain_id"]
            or context["subject_id"] != entry["subject_id"]
            or context["brand_focus_id"] != entry["brand_focus_id"]
            or context["global_scope"] is not False):
        raise SavedWorkError("SOURCE_USE_SCOPE_OR_CONTENT_MISMATCH")
    from lumenis.system.security import permission

    permission.validate_current_source_use(
        con, source_id=source_id, source_url=entry["source_url"], domain_id=entry["domain_id"],
        subject_id=entry["subject_id"], brand_focus_id=entry["brand_focus_id"],
        scope_evidence_ref=entry["scope_evidence_ref"],
        content_evidence_ref=entry["content_evidence_ref"],
        body_sha256=entry["body_sha256"], purpose="internal_research",
        operation=source_use_operation, receipt_id=_APPROVED_SOURCE_USE_RECEIPT_ID,
    )
    canonical, raw_ref, body = _approved_source_canonical(con, entry)
    # SourceUse is a separately maintained receipt. Fail if it changed while
    # the exact source was being checked, even when its source row still matches.
    current_receipt, current_entry = _approved_source_use_receipt_entry(source_id)
    if _digest(current_receipt) != _digest(receipt) or current_entry != entry:
        raise SavedWorkError("SOURCE_USE_APPROVAL_RECEIPT_CHANGED")
    descriptor = {
        "schema": "lumenis.approved-source-reference-request/v2",
        "source_id": source_id, "canonical_id": canonical_id,
        "expected_body_sha256": expected_body_sha256, "request_id": request_id,
        "context": context,
        "source_url": entry["source_url"],
        "scope_evidence_ref": entry["scope_evidence_ref"],
        "source_content_locator": entry["content_evidence_ref"],
        "body_sha256": entry["body_sha256"],
        "parsed_text": body, "body_length": len(body),
        "offset_unit": "unicode-codepoint",
        "title": canonical.get("title") or source_id,
        "source_platform": canonical.get("source_platform") or "UNKNOWN",
        "published_at": canonical.get("publish_datetime") or "UNKNOWN",
        "captured_at": canonical.get("captured_at") or "UNKNOWN",
        "rights_state": entry["rights_state"], "snapshot_kind": entry["snapshot_kind"],
        "receipt_id": _APPROVED_SOURCE_USE_RECEIPT_ID,
        "receipt_descriptor_sha256": _digest(receipt),
        "source_use": {"purpose": "internal_research", "operation": "derive_reference",
                       "commercial_state": "UNKNOWN", "publication_state": "NOT_APPROVED",
                       "training_state": "NOT_APPROVED"},
    }
    descriptor_sha256 = _digest(descriptor)
    resource = "approved-internal-source-reference:v2:" + descriptor_sha256
    return ({"ok": True, "prepared": True, **descriptor,
             "descriptor_sha256": descriptor_sha256, "resource": resource},
            entry, canonical, raw_ref, body)


def prepare_approved_source_reference(
    *, source_id: str, canonical_id: str, expected_body_sha256: str,
    request_id: str, actor: Any, scope: Mapping,
) -> dict:
    """Read a server-authorized source request for the existing confirmation owner.

    The returned v2 resource binds the actual principal, exact focus, request,
    body, original locators and current SourceUse receipt. It grants no
    DATA_IMPORT approval, token or Effect Fence reservation and writes nothing.
    """
    from lumenis.system.security import permission

    try:
        with get_repository().connection(read_only=True, wal=False) as con:
            con.execute("BEGIN")
            prepared, *_ = _prepare_approved_source_reference(
                con, source_id=source_id, canonical_id=canonical_id,
                expected_body_sha256=expected_body_sha256, request_id=request_id,
                actor=actor, scope=scope, action="read", source_use_operation="read",
            )
            return prepared
    except permission.SourceUseApprovalError as exc:
        raise SavedWorkError(exc.code) from exc
    except SavedWorkError:
        raise
    except Exception as exc:
        raise SavedWorkError("SOURCE_USE_REFERENCE_UNAVAILABLE") from exc


def create_approved_source_reference(
    *, source_id: str, canonical_id: str, expected_body_sha256: str,
    request_id: str, actor: Any, scope: Mapping,
) -> dict:
    """Create one immutable derivative Source reference under existing owners.

    This snapshots existing Canonical/source Evidence content only. It does not
    fetch the URL, alter source rights, create another Canonical fact, or grant
    export/publication/training permission. DATA_IMPORT and scope are rechecked.
    """
    from lumenis.system.security import permission

    try:
        prepared = prepare_approved_source_reference(
            source_id=source_id, canonical_id=canonical_id,
            expected_body_sha256=expected_body_sha256, request_id=request_id,
            actor=actor, scope=scope,
        )
        resource = prepared["resource"]
        def check_reference_effect(descriptor, *, connection=None):
            decision = permission.check_approved_source_reference_import(
                actor=actor, scope=scope, prepared=descriptor, connection=connection,
            )
            if not decision.allowed:
                raise SavedWorkError("WORK_EFFECT_PERMISSION_DENIED")

        check_reference_effect(prepared)
        with get_repository().transaction() as con:
            con.execute("BEGIN IMMEDIATE")
            current, entry, canonical, raw_ref, body = _prepare_approved_source_reference(
                con, source_id=source_id, canonical_id=canonical_id,
                expected_body_sha256=expected_body_sha256, request_id=request_id,
                actor=actor, scope=scope, action="write", source_use_operation="derive_reference",
            )
            if current["resource"] != resource:
                raise SavedWorkError("SOURCE_USE_PREPARED_REQUEST_CHANGED")
            context = current["context"]
            check_reference_effect(current, connection=con)
            existing_mapping = raw_ref.get("approved_internal_source_use")
            asset_id = "approved-source-reference:" + hashlib.sha256(
                f"{entry['canonical_id']}\n{entry['body_sha256']}".encode()).hexdigest()[:32]
            if existing_mapping is not None:
                resolved = resolve_approved_source_reference(
                    con, source_id=source_id, canonical_id=canonical_id,
                    domain_id=entry["domain_id"], subject_id=entry["subject_id"],
                    brand_focus_id=entry["brand_focus_id"],
                    source_content_locator=entry["content_evidence_ref"],
                    body_sha256=expected_body_sha256,
                )
                rechecked, *_ = _prepare_approved_source_reference(
                    con, source_id=source_id, canonical_id=canonical_id,
                    expected_body_sha256=expected_body_sha256, request_id=request_id,
                    actor=actor, scope=scope, action="write", source_use_operation="derive_reference",
                )
                if rechecked["resource"] != resource:
                    raise SavedWorkError("SOURCE_USE_PREPARED_REQUEST_CHANGED")
                check_reference_effect(rechecked, connection=con)
                con.commit()
                return {"ok": True, "replayed": True, "request_id": request_id,
                        "source_id": source_id, "source_url": entry["source_url"],
                        "rights_state": entry["rights_state"],
                        "snapshot_kind": entry["snapshot_kind"], **resolved}
            orphan = con.execute(
                "SELECT id FROM app_evidence_records WHERE feature_id=? AND asset_id=?",
                (_APPROVED_SOURCE_REFERENCE_FEATURE, asset_id),
            ).fetchall()
            if orphan:
                raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_ORPHANED")

            product = "CTH" if entry["domain_id"] == "cth" else "ZBMP"
            owner = {key: value for key, value in context.items()
                     if key in {"actor_id", "principal_kind", "principal_ref"}}
            raw = body.encode("utf-8")
            source_record = source_path = None
            committed = False
            try:
                with staging_write(resource):
                    source_record, source_path = _stage_bytes(
                        con, raw=raw, context=context, kind="imported_document_source",
                        source_execution_id=asset_id, extension=".txt", media_type="text/plain; charset=utf-8",
                    )
                    sequence = con.execute(
                        "SELECT COALESCE(MAX(id),0) FROM app_evidence_records"
                    ).fetchone()[0]
                    try:
                        sqlite_sequence = con.execute(
                            "SELECT seq FROM sqlite_sequence WHERE name='app_evidence_records'"
                        ).fetchone()
                    except sqlite3.OperationalError:
                        sqlite_sequence = None
                    next_evidence_id = max(int(sequence), int(sqlite_sequence[0]) if sqlite_sequence else 0) + 1
                    derived_ref = f"app_evidence_records:{next_evidence_id}"
                    parent_binding = _approved_source_parent_binding(entry, derived_ref)
                    marker = _approved_source_use_marker(entry, derived_ref)
                    metadata = {
                        "context": context,
                        "owner": owner,
                        "source_url": entry["source_url"],
                        "source_artifact_ref": source_record["artifact_id"],
                        "source_fingerprint": hashlib.sha256(raw).hexdigest(),
                        "parsed_text": body,
                        "locators": [{"unit": "reference_snapshot", "start": 0, "end": len(body),
                                      "offset_unit": "unicode-codepoint",
                                      "source_content_locator": entry["content_evidence_ref"]}],
                        "capture_mode": "approved_internal_reference_snapshot",
                        "autonomous_collection": False,
                        "source_reference_parent": parent_binding,
                        "provenance": {
                            "source_url": entry["source_url"],
                            "published_at": canonical.get("publish_datetime") or "UNKNOWN",
                            "captured_at": canonical.get("captured_at") or "UNKNOWN",
                            "title": canonical.get("title") or source_id,
                            "source_platform": canonical.get("source_platform") or "UNKNOWN",
                            "rights": entry["rights_state"],
                            "intended_use": "internal_research",
                            "content_origin": {"kind": "publisher-material", "claim_type": "source_statement"},
                            "approved_internal_source_use": marker,
                            "source_reference_parent": parent_binding,
                            "parsed_text": body,
                        },
                    }
                    evidence_id = evidence_store.record_evidence(
                        source="approved_internal_source_reference", product=product,
                        feature_id=_APPROVED_SOURCE_REFERENCE_FEATURE, asset_id=asset_id,
                        version="approved-internal-source-reference:v1", env="internal",
                        capture_mode="approved_internal_reference_snapshot",
                        inputs={"source_ids": [source_id], "canonical_id": canonical_id,
                                "scope_evidence_ref": entry["scope_evidence_ref"],
                                "source_content_locator": entry["content_evidence_ref"],
                                "body_sha256": expected_body_sha256,
                                "request_id": request_id},
                        outputs={"source_reference_parent": parent_binding},
                        raw_content=body, collection_metadata=metadata,
                        publish_datetime=canonical.get("publish_datetime") or "",
                        provider="internal_reference", subject_scope=entry["domain_id"].upper(),
                        domain_id=entry["domain_id"], subject_id=entry["subject_id"],
                        brand_focus_id=entry["brand_focus_id"], global_scope=False,
                        connection=con,
                    )
                    if evidence_id != next_evidence_id:
                        raise SavedWorkError("SOURCE_USE_EVIDENCE_IDENTITY_RACE")
                    con.execute("UPDATE lumenis_shared_artifacts SET evidence_id=? WHERE artifact_id=?",
                                (str(evidence_id), source_record["artifact_id"]))
                    old_raw_ref = canonical.get("raw_ref") or "{}"
                    updated_raw_ref = dict(raw_ref)
                    updated_raw_ref["approved_internal_source_use"] = parent_binding
                    updated_raw_ref_text = json.dumps(
                        updated_raw_ref, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    changed = con.execute(
                        "UPDATE canonical_data SET raw_ref=? WHERE canonical_id=? AND source_id=? "
                        "AND content_hash=? AND content=? AND raw_ref=?",
                        (updated_raw_ref_text, entry["canonical_id"], entry["source_id"],
                         canonical.get("content_hash"), body, old_raw_ref),
                    ).rowcount
                    if changed != 1:
                        raise SavedWorkError("SOURCE_USE_CANONICAL_SOURCE_CHANGED")
                    check = resolve_approved_source_reference(
                        con, source_id=source_id, canonical_id=canonical_id,
                        domain_id=entry["domain_id"], subject_id=entry["subject_id"],
                        brand_focus_id=entry["brand_focus_id"],
                        source_content_locator=entry["content_evidence_ref"],
                        body_sha256=expected_body_sha256,
                    )
                    rechecked, *_ = _prepare_approved_source_reference(
                        con, source_id=source_id, canonical_id=canonical_id,
                        expected_body_sha256=expected_body_sha256, request_id=request_id,
                        actor=actor, scope=scope, action="write", source_use_operation="derive_reference",
                    )
                    if rechecked["resource"] != resource:
                        raise SavedWorkError("SOURCE_USE_PREPARED_REQUEST_CHANGED")
                    check_reference_effect(rechecked, connection=con)
                    con.commit()
                    committed = True
                    return {"ok": True, "replayed": False, "request_id": request_id,
                            "source_id": source_id, "source_url": entry["source_url"],
                            "rights_state": entry["rights_state"],
                            "snapshot_kind": entry["snapshot_kind"], **check}
            finally:
                if source_path is not None and not committed:
                    source_path.unlink(missing_ok=True)
    except permission.SourceUseApprovalError as exc:
        raise SavedWorkError(exc.code) from exc
    except SavedWorkError:
        raise
    except Exception as exc:
        raise SavedWorkError("SOURCE_USE_REFERENCE_UNAVAILABLE") from exc


def _capture_observation(provenance: Mapping) -> dict | None:
    observation = provenance.get("capture_observation")
    if "capture_observation" not in provenance:
        return None
    required = {"literal", "precision", "utc_offset", "timezone", "absolute_utc", "invocation_bounds"}
    if (not isinstance(observation, dict) or set(observation) != required
            or observation["literal"] != provenance.get("captured_at")
            or observation["utc_offset"] is not None or observation["absolute_utc"] is not None
            or observation["timezone"] != "UNKNOWN"
            or not isinstance(observation["literal"], str)
            or not isinstance(observation["precision"], str)):
        raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID")
    patterns = {"minute": r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}",
                "second": r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
                "subsecond": r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{1,6}"}
    pattern = patterns.get(observation["precision"])
    if pattern is None or re.fullmatch(pattern, observation["literal"]) is None:
        raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID")
    try:
        timestamp = datetime.fromisoformat(observation["literal"])
    except ValueError as exc:
        raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID") from exc
    if timestamp.tzinfo is not None:
        raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID")
    bounds = observation["invocation_bounds"]
    if bounds is not None:
        if (not isinstance(bounds, dict) or set(bounds) != {"started_at", "finished_at", "meaning"}
                or bounds["meaning"] != "original-invocation-bounds-not-exact-capture"
                or any(not isinstance(bounds[k], str) or len(bounds[k]) > 64 for k in ("started_at", "finished_at"))):
            raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID")
        try:
            start, end = (datetime.fromisoformat(bounds[k].replace("Z", "+00:00"))
                          for k in ("started_at", "finished_at"))
        except ValueError as exc:
            raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID") from exc
        if (start.utcoffset() is None or end.utcoffset() is None
                or start.utcoffset().total_seconds() != 0 or end.utcoffset().total_seconds() != 0 or start > end):
            raise SavedWorkError("DOCUMENT_CAPTURE_OBSERVATION_INVALID")
    return json.loads(_json(observation))


def source_boundaries(provenance: Mapping) -> dict:
    """Describe source declarations, never factual or Learning admission.

    A research/package ID remains provenance. Only the existing Evidence
    writer issues Evidence IDs; Learning/Training admission has its own owner.
    """
    default_kind = "publisher-material" if provenance.get("source_url") else "self-authored"
    default_claim = "source_statement" if default_kind == "publisher-material" else "author_statement"
    declared = provenance.get("content_origin", {"kind": default_kind, "claim_type": default_claim})
    allowed = {"publisher-material": {"source_statement"},
               "researcher-note": {"research_inference", "method_proposal"},
               "self-authored": {"author_statement", "research_inference", "method_proposal", "synthetic_sample"}}
    if (not isinstance(declared, Mapping) or not {"kind", "claim_type"}.issubset(declared)
            or set(declared) - {"kind", "claim_type", "research_id"}
            or not isinstance(declared.get("kind"), str) or declared["kind"] not in allowed
            or not isinstance(declared.get("claim_type"), str)
            or declared["claim_type"] not in allowed[declared["kind"]]
            or "research_id" in declared and (not isinstance(declared["research_id"], str)
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", declared["research_id"]))):
        raise SavedWorkError("DOCUMENT_CONTENT_ORIGIN_INVALID")
    observation = _capture_observation(provenance)
    return {"content_origin": dict(declared), "claim_type": declared["claim_type"],
            "fact_verification": "NOT_VERIFIED", "learning_admission": "NOT_ADMITTED",
            "training_eligible": False, "held_out": False,
            "rights_statement": provenance.get("rights_statement"),
            "research_transport": provenance.get("research_transport"),
            **({"capture_observation": observation, "capture_absolute_time_status": "UNKNOWN"}
               if observation is not None else {})}


def _prepare(file_path: str, *, actor: Any, scope: Mapping, provenance: Mapping) -> dict:
    context = authorize(actor, scope, action="write")
    required = {"source_url", "published_at", "captured_at", "rights", "title"}
    if not isinstance(provenance, Mapping) or not required.issubset(provenance) or set(provenance) - required - {"intended_use", "capture", "source_origin", "content_origin", "rights_statement", "research_transport", "capture_observation"}:
        raise SavedWorkError("DOCUMENT_PROVENANCE_REQUIRED")
    # Seal nested declarations as well as bytes: decoder duration must not let
    # a caller replace approved rights/origin/capture metadata after admission.
    provenance = json.loads(_json(dict(provenance)))
    source_boundaries(provenance)
    if "rights_statement" in provenance and (not isinstance(provenance["rights_statement"], str)
                                             or not 0 < len(provenance["rights_statement"]) <= 2000):
        raise SavedWorkError("DOCUMENT_RIGHTS_STATEMENT_INVALID")
    if "research_transport" in provenance:
        transport = provenance["research_transport"]
        if (not isinstance(transport, dict) or set(transport) != {"sha256", "parent_manifest_sha256", "record_id"}
                or any(not isinstance(transport[k], str) or not re.fullmatch(r"[0-9a-f]{64}", transport[k])
                       for k in ("sha256", "parent_manifest_sha256"))
                or transport["record_id"] != source_boundaries(provenance)["content_origin"].get("research_id")):
            raise SavedWorkError("DOCUMENT_RESEARCH_TRANSPORT_INVALID")
    if (provenance["source_url"] is None and isinstance(provenance["rights"], str)
            and provenance["rights"] in {"owner-approved", "public-reference-only"}):
        origin = provenance.get("source_origin")
        if (not isinstance(origin, dict) or set(origin) != {"kind", "ref"} or origin["kind"] != "approved-file"
                or not isinstance(origin["ref"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", origin["ref"])):
            raise SavedWorkError("DOCUMENT_APPROVED_FILE_ORIGIN_REQUIRED")
        source_url = None
    else:
        source_url, state = _source_url(provenance["source_url"])
        if state != "AVAILABLE" or "source_origin" in provenance:
            raise SavedWorkError("DOCUMENT_PUBLIC_SOURCE_URL_REQUIRED")
        host = urlsplit(source_url).hostname or ""
        if host == "openstax.org" or host.endswith(".openstax.org"):
            # This card admits only OpenStax metadata/links. The text importer
            # cannot establish that an arbitrary file contains no prohibited
            # textbook body, so it must not ingest it into searchable Evidence.
            raise SavedWorkError("DOCUMENT_SOURCE_LINK_ONLY_REQUIRED")
    if (not isinstance(provenance["rights"], str)
            or provenance["rights"] not in {"public-reference-only", "owner-approved"}
            or not isinstance(provenance["title"], str) or not provenance["title"].strip()
            or len(provenance["title"]) > 300):
        raise SavedWorkError("DOCUMENT_PROVENANCE_INVALID")
    if (not isinstance(provenance.get("intended_use", "research_reference"), str)
            or provenance.get("intended_use", "research_reference") not in {"research_reference", "report_quote", "internal_draft"}):
        raise SavedWorkError("DOCUMENT_USE_INVALID")
    if provenance["rights"] == "public-reference-only" and provenance.get("intended_use") == "internal_draft":
        raise SavedWorkError("DOCUMENT_USE_NOT_AUTHORIZED")
    if "capture" in provenance:
        capture = provenance["capture"]
        if (not isinstance(capture, dict) or set(capture) != {"original_sha256", "method", "source_range"}
                or not isinstance(capture["original_sha256"], str) or len(capture["original_sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in capture["original_sha256"])
                or not isinstance(capture["method"], str) or not 0 < len(capture["method"]) <= 500
                or not isinstance(capture["source_range"], dict)
                or set(capture["source_range"]) != {"unit", "start", "end"}
                or capture["source_range"]["unit"] != "extracted-page-text"
                or any(type(capture["source_range"][k]) is not int for k in ("start", "end"))
                or not 0 <= capture["source_range"]["start"] < capture["source_range"]["end"]):
            raise SavedWorkError("DOCUMENT_CAPTURE_INVALID")
    for key in ("published_at", "captured_at"):
        value = provenance[key]
        if key == "published_at" and value is None:
            continue
        if not isinstance(value, str):
            raise SavedWorkError("DOCUMENT_TIME_INVALID")
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SavedWorkError("DOCUMENT_TIME_INVALID") from exc
        if timestamp.tzinfo is None and not (key == "captured_at" and "capture_observation" in provenance):
            raise SavedWorkError("DOCUMENT_TIME_OFFSET_REQUIRED")
    # Bound the service input separately from the legacy 500MB parser envelope.
    path = Path(file_path)
    if not path.is_file() or not 0 < path.stat().st_size <= 8 * 1024 * 1024:
        raise SavedWorkError("DOCUMENT_SIZE_INVALID")
    # Parse a sealed copy so a source-file change cannot combine one document's
    # text with another document's fingerprint during the conversion.
    with path.open("rb") as source:
        raw = source.read(8 * 1024 * 1024 + 1)
    if not 0 < len(raw) <= 8 * 1024 * 1024:
        raise SavedWorkError("DOCUMENT_SIZE_INVALID")
    descriptor = {"context": context, "source_url": source_url,
                  "source_fingerprint": hashlib.sha256(raw).hexdigest(),
                  "source_name": path.name, "extension": path.suffix.lower(),
                  "size_bytes": len(raw), "provenance": dict(provenance),
                  "importer_contract": "document-import/2" if "capture_observation" in provenance else "document-import/1"}
    return {"context": context, "descriptor": descriptor,
            "resource": "document-import:v1:" + _digest(descriptor),
            "source_bytes": raw, "extension": path.suffix.lower()}


def _parse_approved(prepared: dict) -> dict:
    raw, descriptor = prepared["source_bytes"], prepared["descriptor"]
    with tempfile.TemporaryDirectory(prefix="lumenis-document-parse-") as work:
        sealed = Path(work) / ("input" + prepared["extension"])
        sealed.write_bytes(raw)
        parsed = parse_file(str(sealed))
    parsed.metadata["source_name"] = descriptor["source_name"]
    if parsed.metadata["source_fingerprint"] != descriptor["source_fingerprint"]:
        raise SavedWorkError("DOCUMENT_SOURCE_CHANGED")
    if not parsed.text.strip() or len(parsed.text.encode("utf-8")) > 8 * 1024 * 1024:
        raise SavedWorkError("DOCUMENT_TEXT_UNAVAILABLE")
    material = {"context": prepared["context"], "source_url": descriptor["source_url"],
                "source_fingerprint": descriptor["source_fingerprint"],
                "parsed_text_sha256": parsed.metadata["parsed_text_sha256"],
                "provenance": descriptor["provenance"], "locators": parsed.locators,
                "source_name": descriptor["source_name"]}
    return {**prepared, "material": material, "source_id": "DOC-" + _digest(material)[:32],
            "parsed": parsed}


def document_import_resource(file_path: str, *, actor: Any, scope: Mapping,
                             provenance: Mapping) -> str:
    """The W6 confirmation adapter may request approval for these exact bytes/scope."""
    return _prepare(file_path, actor=actor, scope=scope, provenance=provenance)["resource"]


def _selected_source_rows(parsed, *, selected_row_indices, preview_row_count,
                          expected_preview_rows_sha256):
    if selected_row_indices is None:
        if preview_row_count is not None or expected_preview_rows_sha256 is not None:
            raise SavedWorkError("DOCUMENT_PREVIEW_SELECTION_INVALID")
        return [], []
    if (not isinstance(selected_row_indices, list) or not selected_row_indices
            or any(type(index) is not int or index < 0 for index in selected_row_indices)
            or len(set(selected_row_indices)) != len(selected_row_indices)
            or type(preview_row_count) is not int or preview_row_count <= 0
            or not isinstance(expected_preview_rows_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_preview_rows_sha256) is None):
        raise SavedWorkError("DOCUMENT_PREVIEW_SELECTION_INVALID")
    indices = sorted(selected_row_indices)
    if any(index >= preview_row_count for index in indices):
        raise SavedWorkError("DOCUMENT_PREVIEW_SELECTION_INVALID")
    from .analyzer import extract_source_rows, source_rows_fingerprint
    rows = extract_source_rows(parsed)
    if len(rows) < preview_row_count:
        raise SavedWorkError("DOCUMENT_PREVIEW_SELECTION_CHANGED")
    actual_fingerprint = source_rows_fingerprint(parsed, rows, count=preview_row_count)
    if actual_fingerprint != expected_preview_rows_sha256:
        raise SavedWorkError("DOCUMENT_PREVIEW_SELECTION_CHANGED")
    return indices, [(index, rows[index]) for index in indices]


def import_document(file_path: str, *, actor: Any, scope: Mapping,
                    provenance: Mapping, selected_row_indices=None,
                    preview_row_count=None,
                    expected_preview_rows_sha256: str | None = None) -> dict:
    """Atomically retain parsed source, signed provenance and canonical content.

    A retry uses exactly the same provenance including capture time. A modified
    file, scope, source or time is a different import and needs its own admission.
    """
    prepared = _prepare(file_path, actor=actor, scope=scope, provenance=provenance)
    scope = {k: prepared["context"][k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}
    provenance = prepared["descriptor"]["provenance"]
    context = _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"])
    prepared = _parse_approved(prepared)
    parsed, source_id = prepared["parsed"], prepared["source_id"]
    selected_indices, selected_rows = _selected_source_rows(
        parsed, selected_row_indices=selected_row_indices,
        preview_row_count=preview_row_count,
        expected_preview_rows_sha256=expected_preview_rows_sha256,
    )
    product = "CTH" if context["domain_id"] == "cth" else "ZBMP"
    owner = {k: v for k, v in context.items() if k in {"actor_id", "principal_kind", "principal_ref"}}
    metadata = {**prepared["material"], "owner": owner, "parser": parsed.metadata,
                "parsed_text": parsed.text,
                "capture_mode": "assisted_file_import", **source_boundaries(provenance),
                "autonomous_collection": False}
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"], connection=con)
        cur = con.execute("SELECT * FROM app_evidence_records WHERE feature_id='DOCUMENT_IMPORT' AND asset_id=?",
                          (source_id,))
        row = cur.fetchone()
        if row is not None:
            evidence_id = dict(zip((column[0] for column in cur.description), row))["id"]
            evidence = _verified_evidence(con, evidence_id, context)
            if evidence["raw_content"] != parsed.text or evidence["provenance"].get("source_fingerprint") != parsed.metadata["source_fingerprint"]:
                raise SavedWorkError("DOCUMENT_REPLAY_CONFLICT")
            _source_bytes(con, evidence)
            _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"], connection=con)
            row_records, rows_inserted = _persist_selected_rows(
                con, source_id=source_id, evidence_id=evidence_id, parsed=parsed,
                selected_rows=selected_rows, context=context, product=product,
                metadata=metadata, provenance=provenance,
            )
            return _result(
                con, source_id, evidence_id, parsed, scope, product,
                replayed=rows_inserted == 0, source_replayed=True,
                selected_indices=selected_indices,
                row_records=row_records, rows_inserted=rows_inserted,
                preview_rows_sha256=expected_preview_rows_sha256,
            )
        with staging_write(prepared["resource"]):
            return _write_document(
                con, prepared, context, provenance, product, metadata, scope, actor,
                selected_indices=selected_indices, selected_rows=selected_rows,
                preview_rows_sha256=expected_preview_rows_sha256,
            )


def _write_document(con, prepared, context, provenance, product, metadata, scope, actor,
                    *, selected_indices, selected_rows, preview_rows_sha256):
    parsed, source_id = prepared["parsed"], prepared["source_id"]
    record, path = _stage_bytes(con, raw=prepared["source_bytes"], context=context,
                               kind="imported_document_source", source_execution_id=source_id,
                               extension=prepared["extension"], media_type="application/octet-stream")
    committed = False
    try:
        metadata = {**metadata, "source_artifact_ref": record["artifact_id"]}
        evidence_id = evidence_store.record_evidence(
            source="document_import", product=product, feature_id="DOCUMENT_IMPORT",
            asset_id=source_id, version=prepared["descriptor"]["importer_contract"], env="staging",
            capture_mode="file_import", captured_at=provenance["captured_at"],
            inputs={"source_ids": [source_id], "import_resource": prepared["resource"]},
            outputs={"parsed_text_sha256": parsed.metadata["parsed_text_sha256"]},
            raw_content=parsed.text, collection_metadata=metadata,
            publish_datetime=provenance["published_at"] or "", provider="importer",
            domain_id=context["domain_id"], subject_id=context["subject_id"],
            brand_focus_id=context["brand_focus_id"], global_scope=context["global_scope"],
            connection=con,
        )
        canonical_record = canonical_data.CanonicalRecord(
            product_id=product, domain_id=context["domain_id"],
            subject_id=context["subject_id"] or "", brand_focus_id=context["brand_focus_id"] or "",
            scope_status="UNASSIGNED" if context["global_scope"] else "VERIFIED",
            scope_evidence_ref=str(evidence_id), source_id=source_id, external_id=source_id,
            provenance=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            source_type="document", source_table="app_evidence_records",
            source_platform="public_document" if metadata["content_origin"]["kind"] == "publisher-material" else "approved_research_document",
            title=provenance["title"], content=parsed.text, url=provenance["source_url"] or "",
            publish_datetime=provenance["published_at"] or "", captured_at=provenance["captured_at"],
            content_hash=hashlib.sha256(parsed.text.encode()).hexdigest(),
        )
        canonical_data.persist_canonical(con, canonical_record)
        row_records, rows_inserted = _persist_selected_rows(
            con, source_id=source_id, evidence_id=evidence_id, parsed=parsed,
            selected_rows=selected_rows, context=context, product=product,
            metadata=metadata, provenance=provenance,
        )
        con.execute("UPDATE lumenis_shared_artifacts SET evidence_id=? WHERE artifact_id=?",
                    (str(evidence_id), record["artifact_id"]))
        evidence = _verified_evidence(con, evidence_id, context)
        _source_bytes(con, evidence)
        _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"], connection=con)
        result = _result(
            con, source_id, evidence_id, parsed, scope, product, replayed=False,
            selected_indices=selected_indices, row_records=row_records,
            rows_inserted=rows_inserted,
            preview_rows_sha256=preview_rows_sha256,
        )
        con.commit()
        committed = True
        return result
    finally:
        if not committed:
            path.unlink(missing_ok=True)


def _persist_selected_rows(con, *, source_id, evidence_id, parsed, selected_rows,
                           context, product, metadata, provenance):
    records = []
    inserted_count = 0
    source_platform = ("public_document"
                       if metadata["content_origin"]["kind"] == "publisher-material"
                       else "approved_research_document")
    for row_index, note in selected_rows:
        locator = json.loads(_json(note.source_locator))
        row_payload = str(note.raw_chunk or note.content or "")
        row_sha256 = str(note.source_row_sha256 or "")
        if not row_sha256 or not re.fullmatch(r"[0-9a-f]{64}", row_sha256):
            raise SavedWorkError("DOCUMENT_ROW_PROJECTION_INVALID")
        identity = json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        canonical_id = "CAN-DOCROW-" + hashlib.sha256(
            f"{source_id}\n{identity}".encode("utf-8")
        ).hexdigest()[:32]
        row_provenance = {
            "schema": "document-row-projection/v1",
            "document_source_id": source_id,
            "evidence_id": int(evidence_id),
            "source_fingerprint": parsed.metadata["source_fingerprint"],
            "parsed_text_sha256": parsed.metadata["parsed_text_sha256"],
            "source_locator": locator,
            "source_row_sha256": row_sha256,
            "source_row_payload": row_payload,
            "claim_type": metadata["claim_type"],
            "rights": provenance["rights"],
            "intended_use": provenance.get("intended_use", "research_reference"),
            "fact_verification": "NOT_VERIFIED",
            "learning_admission": "NOT_ADMITTED",
            "training_eligible": False,
            "analysis_status": "NOT_RUN",
            "analysis_code": "SOURCE_ROW_PROJECTION_NOT_ANALYZED",
        }
        record = canonical_data.CanonicalRecord(
            canonical_id=canonical_id,
            product_id=product, domain_id=context["domain_id"],
            subject_id=context["subject_id"] or "",
            brand_focus_id=context["brand_focus_id"] or "",
            scope_status="UNASSIGNED" if context["global_scope"] else "VERIFIED",
            scope_evidence_ref=str(evidence_id), source_id=source_id,
            external_id=f"{source_id}:row:{canonical_id}",
            provenance=json.dumps(row_provenance, ensure_ascii=False, sort_keys=True),
            source_type="document_row", source_table="app_evidence_records",
            source_platform=source_platform,
            title=str(note.title or ""), content=str(note.content or note.raw_chunk or ""),
            author_name=str(note.author or ""), url=provenance["source_url"] or "",
            publish_datetime=str(note.publish_date or provenance["published_at"] or ""),
            captured_at=provenance["captured_at"],
            sentiment="unknown", sentiment_score=None,
            risk_level="unknown", risk_score=None,
            quality_status="unknown", relevance_status="unknown",
            verification_status="review", ai_provider="unknown", ai_model="", ai_analysis="",
            raw_ref=json.dumps({
                "table": "app_evidence_records", "evidence_id": int(evidence_id),
                "source_id": source_id, "source_locator": locator,
                "source_row_sha256": row_sha256,
            }, ensure_ascii=False, sort_keys=True),
        )
        existing = con.execute(
            "SELECT source_id, source_type, scope_evidence_ref FROM canonical_data WHERE canonical_id=?",
            (canonical_id,),
        ).fetchone()
        if existing is not None and (
                existing[0] != source_id or existing[1] != "document_row"
                or str(existing[2] or "") != str(evidence_id)):
            raise SavedWorkError("DOCUMENT_ROW_CANONICAL_CONFLICT")
        status = canonical_data.persist_canonical(con, record)
        inserted_count += int(status == "inserted")
        records.append({
            "canonical_id": canonical_id, "row_index": row_index,
            "source_locator": locator, "source_row_sha256": row_sha256,
        })
    return records, inserted_count


def _source_bytes(con, evidence):
    import shared_artifacts
    provenance = evidence["provenance"]
    artifact_id = provenance.get("source_artifact_ref")
    cur = con.execute("SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=? AND kind IN ('imported_document_source','collected_source')", (artifact_id,))
    row = cur.fetchone()
    if row is None:
        raise SavedWorkError("DOCUMENT_SOURCE_ARTIFACT_MISSING")
    record = dict(zip((c[0] for c in cur.description), row))
    root = shared_artifacts.artifact_root()
    path = (root / record["relative_path"]).resolve()
    if (record["source_execution_id"] != evidence["asset_id"] or record["evidence_id"] != str(evidence["id"])
            or record["domain_id"] != provenance["context"]["domain_id"]
            or record["sha256"] != provenance["source_fingerprint"]
            or not path.is_relative_to(root) or not path.is_file() or not 0 < record["size_bytes"] <= 8*1024*1024):
        raise SavedWorkError("DOCUMENT_SOURCE_ARTIFACT_INVALID")
    with path.open("rb") as source:
        raw = source.read(8*1024*1024+1)
    if len(raw) != record["size_bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise SavedWorkError("DOCUMENT_SOURCE_ARTIFACT_INVALID")
    if record['kind'] == 'collected_source':
        _verify_collected_source(con, evidence, raw, record)
    return raw, record


def _verify_collected_source(con, evidence, raw, record):
    """Consume a source-specific Collector original through the existing owner.

    The Collector stages and commits these bytes with its Source/Canonical
    transaction. This reader does not import, relabel, grant rights, or create
    an alternate Canonical record. Native body offsets are Unicode code points
    in the unchanged body, never byte offsets into its JSON transport envelope.
    """
    signed = evidence['provenance']
    binding = signed.get('native_source_binding')
    try:
        child_inputs = json.loads(evidence.get('inputs_json') or "")
    except (TypeError, ValueError) as exc:
        raise SavedWorkError('COLLECTED_SOURCE_BINDING_INVALID') from exc
    if (evidence.get('feature_id') != 'COLLECTED_SOURCE'
            or evidence.get('source') != 'collector'
            or signed.get('source_kind') != 'collected_source'
            or not isinstance(child_inputs, dict)
            or not isinstance(binding, dict)
            or set(binding) != {'platform','native_id','stable_source_key','source_id',
                               'body_sha256','collection_evidence_ref'}
            or binding.get('source_id') != evidence.get('asset_id')
            or record.get('note_id') != evidence.get('asset_id')):
        raise SavedWorkError('COLLECTED_SOURCE_BINDING_INVALID')
    try:
        # Native identity/lineage/public URL validation remains Collector-owned.
        # This pure reader makes no collection, session or network invocation.
        from lumenis.system.collector.adapters.secondary_collection import NativePublicCapture, _native_capture_record
        original = _native_capture_record(NativePublicCapture(binding['platform'], raw, record['sha256']))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SavedWorkError('COLLECTED_SOURCE_ORIGINAL_INVALID') from exc
    if not isinstance(original, dict) or not isinstance(original.get('publication') or {}, dict):
        raise SavedWorkError('COLLECTED_SOURCE_ORIGINAL_INVALID')
    source = signed.get('provenance')
    body = original.get('body')
    if (not isinstance(source, dict) or not isinstance(body, str) or not body.strip()
            or signed.get('parsed_text') != body
            or not isinstance(binding['platform'], str)
            or not isinstance(binding['native_id'], str) or not binding['native_id']
            or binding['stable_source_key'] != binding['platform'] + ':' + binding['native_id']
            or any(original.get(k) != binding[k] for k in ('platform','native_id','stable_source_key','body_sha256'))
            or hashlib.sha256(body.encode('utf-8')).hexdigest() != binding['body_sha256']
            or signed.get('source_url') != original.get('source_url')
            or source.get('source_url') != original.get('source_url')
            or source.get('captured_at') != original.get('capture_observation_native')
            or source.get('published_at') != (original.get('publication') or {}).get('published_at_utc')
            or original.get('body_state') in {'OG_PREVIEW_ONLY_NOT_NATIVE_FULL_POST','NATIVE_BODY_UNAVAILABLE'}):
        raise SavedWorkError('COLLECTED_SOURCE_ORIGINAL_INVALID')
    expected_locator = {'unit':'native-post-body', 'json_path':'$.body',
                        'start':0, 'end':len(body), 'offset_unit':'unicode-codepoint'}
    if signed.get('locators') != [expected_locator]:
        raise SavedWorkError('COLLECTED_SOURCE_LOCATOR_INVALID')
    ref = binding['collection_evidence_ref']
    if not isinstance(ref, str) or not re.fullmatch(r'app_evidence_records:[1-9]\d*', ref):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    if child_inputs.get('collection_evidence_ref') != ref:
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    source_context = signed.get('context')
    if not isinstance(source_context, dict):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    capture_mode = signed.get('capture_mode')
    evidence_version = evidence.get('version')
    live_mode = capture_mode == 'live_native_observation_intake'
    pending_mode = capture_mode == 'live_pending_observation_intake'
    live_version = evidence_version == 'collected-native-source:live-v1'
    pending_version = evidence_version == 'collected-native-source:pending-v1'
    if (live_mode != live_version or pending_mode != pending_version
            or (pending_version and not pending_mode)):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    if pending_mode:
        assignment = signed.get('entity_assignment')
        assignment_keys = {'state', 'subject_id', 'brand_focus_id', 'canonical_ref',
                           'context_role', 'reason'}
        if (not isinstance(assignment, dict) or set(assignment) != assignment_keys
                or assignment.get('state') != 'PENDING'
                or assignment.get('subject_id') is not None
                or assignment.get('brand_focus_id') is not None
                or assignment.get('canonical_ref') is not None
                or assignment.get('context_role') != 'ACQUISITION_PERMISSION_CONTEXT_ONLY'
                or not isinstance(assignment.get('reason'), str)
                or re.fullmatch(r'[A-Z][A-Z0-9_]{0,100}', assignment.get('reason')) is None
                or child_inputs.get('entity_assignment') != assignment
                or original.get('entity_assignment') != assignment):
            raise SavedWorkError('COLLECTED_SOURCE_BINDING_INVALID')
    domain_id = source_context.get('domain_id')
    if not isinstance(domain_id, str):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    product = {'cth': 'CTH', 'bmp': 'ZBMP', 'zbmp': 'ZBMP'}.get(domain_id)
    if product is None:
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    try:
        expected_scope = evidence_store._normalize_record_evidence_scope(
            product=product,
            domain_id=domain_id,
            subject_id=source_context.get('subject_id'),
            brand_focus_id=source_context.get('brand_focus_id'),
            global_scope=source_context.get('global_scope'),
        )
    except (TypeError, ValueError) as exc:
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID') from exc
    if expected_scope is None or child_inputs.get('_lumenis_scope') != expected_scope:
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    if pending_mode and (not isinstance(source_context.get('collector_plan_id'), str)
                         or not source_context.get('collector_plan_id')):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    parent = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(ref.split(':')[1]),)).fetchone()
    if parent is None:
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    parent = dict(parent)
    try:
        parent_inputs = json.loads(parent['inputs_json'])
    except (TypeError, ValueError) as exc:
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID') from exc
    integrity = evidence_store.classify_evidence_integrity(parent)
    if (integrity.get('verified') is not True or integrity.get('assurance') != 'writer-authenticated'
            or parent.get('status') != 'verified'
            or parent_inputs.get('_lumenis_scope') != child_inputs.get('_lumenis_scope')):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    if pending_mode:
        try:
            parent_collection_metadata = json.loads(parent.get('collection_metadata') or '')
        except (TypeError, ValueError) as exc:
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID') from exc
        expected_parent_feature = 'PRELAUNCH_' + binding['platform'].upper() + '_COLLECT'
        if (parent.get('source') != 'collector'
                or parent.get('feature_id') != expected_parent_feature
                or parent.get('version') != 'collector-native-observation:v2'
                or parent.get('result') not in {'PASS', 'FAIL'}
                or not isinstance(parent_collection_metadata, dict)
                or parent_collection_metadata.get('maintenance_plan_id')
                    != source_context.get('collector_plan_id')):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
    elif (parent.get('result') != 'PASS'
          or binding['source_id'] not in [str(value) for value in parent_inputs.get('source_ids', [])]):
        raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')

    if live_mode or pending_mode:
        lineage = original.get('source_lineage')
        if (signed.get('source_lineage') != lineage or not isinstance(lineage, list)
                or len(lineage) != 1 or not isinstance(lineage[0], dict)
                or set(lineage[0]) != {'sha256', 'locator', 'kind', 'transport_original'}
                or lineage[0].get('kind') != 'SIGNED_NATIVE_OBSERVATION_JSON'
                or lineage[0].get('transport_original') is not False):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        observations = parent_inputs.get('source_observation_records')
        locator = lineage[0].get('locator')
        locator_match = (re.fullmatch(
            re.escape(ref) + r':inputs\.source_observation_records\[(0|[1-9]\d*)\]',
            locator) if isinstance(locator, str) else None)
        if not isinstance(observations, list) or locator_match is None:
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        index_text = locator_match.group(1)
        if len(index_text) > len(str(len(observations))):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        observation_index = int(index_text)
        if observation_index >= len(observations):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        observation = observations[observation_index]
        if not isinstance(observation, dict):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        observation_bytes = json.dumps(
            observation, ensure_ascii=False, sort_keys=True, separators=(',', ':')
        ).encode('utf-8')
        if (lineage[0].get('locator') !=
                ref + ':inputs.source_observation_records[' + str(observation_index) + ']'
                or lineage[0].get('sha256') != hashlib.sha256(observation_bytes).hexdigest()
                or original.get('native_record') != observation
                or original.get('body') != observation.get('content')
                or original.get('source_url') != observation.get('url')):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        if pending_mode:
            try:
                from lumenis.system.collector.adapters.secondary_collection import (
                    _verified_live_native_observation,
                )
                observed_native_id, observed_body = _verified_live_native_observation(
                    original.get('platform'), observation)
            except (ImportError, TypeError, ValueError, KeyError) as exc:
                raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID') from exc
            if (not isinstance(observed_native_id, str) or not observed_native_id
                    or not isinstance(observed_body, str)
                    or observed_native_id != original.get('native_id')
                    or observed_native_id != str(evidence.get('asset_id'))
                    or observed_body != original.get('body')
                    or observed_body != body):
                raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        else:
            from lumenis.system.collector.adapters.platform_naming import get_platform_fields, normalize_content_id
            platform_fields = get_platform_fields(original.get('platform'))
            observed_native_id = normalize_content_id(
                original.get('platform'),
                observation.get(platform_fields.content_id) if platform_fields else None,
            )
            if not observed_native_id:
                observed_native_id = normalize_content_id(original.get('platform'), observation.get('content_id'))
            if (not observed_native_id or observed_native_id != original.get('native_id')
                    or str(evidence.get('asset_id')) != observed_native_id):
                raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')


def reopen_imported_source(evidence_id: int, *, actor: Any, scope: Mapping,
                           _source_use_operation: str = "reopen") -> dict:
    if _source_use_operation not in {"reopen", "export"}:
        raise SavedWorkError("DOCUMENT_SOURCE_OPERATION_INVALID")
    context = authorize(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        evidence = _verified_evidence(
            con, evidence_id, context, actor,
            source_use_purposes=("internal_research",), source_use_operation=_source_use_operation,
        )
        raw, record = _source_bytes(con, evidence)
    _check_effect(actor, scope, OperationType.DATA_EXPORT, "document-source-read:v1:" + record["sha256"])
    source_context = evidence["provenance"]["context"]
    authorize(actor, {k: source_context[k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}, action="read")
    result = {"content":raw, "artifact_ref":record["artifact_id"], "sha256":record["sha256"],
              "size_bytes":record["size_bytes"], "filename":record["filename"],
              "source_id":evidence["source_id"], "evidence_id":evidence_id,
              "parsed_text":evidence["raw_content"],
              "text_length":len(evidence["raw_content"]),
              "locators":evidence["provenance"].get("locators", []),
              "source_url":evidence["provenance"]["source_url"],
              "source_boundaries":source_boundaries(evidence["provenance"]["provenance"]),
              "source_origin":evidence["provenance"]["provenance"].get("source_origin"),
              "scope":{k: source_context[k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}}
    if (evidence["provenance"].get("capture_mode") == "live_pending_observation_intake"
            and evidence.get("version") == "collected-native-source:pending-v1"):
        result.update(entity_assignment=evidence["provenance"].get("entity_assignment"),
                      scope_status="UNASSIGNED", canonical_ref=None)
    return result

def _result(con, source_id, evidence_id, parsed, scope, product, *, replayed,
            source_replayed=False,
            selected_indices=None, row_records=None, rows_inserted=0,
            preview_rows_sha256=None):
    rows = con.execute(
        "SELECT canonical_id FROM canonical_data WHERE source_id=? AND product_id=? "
        "AND source_type='document' AND scope_evidence_ref=?",
        (source_id, product, str(evidence_id)),
    ).fetchall()
    if not rows:
        raise SavedWorkError("DOCUMENT_CANONICAL_MISSING")
    if len(rows) != 1:
        raise SavedWorkError("DOCUMENT_CANONICAL_CONFLICT")
    row = rows[0]
    stored = con.execute("SELECT collection_metadata FROM app_evidence_records WHERE id=?",(evidence_id,)).fetchone()
    signed = json.loads(stored[0])
    return {"source_id": source_id, "evidence_id": evidence_id, "canonical_id": row[0],
            "source_artifact_ref":signed["source_artifact_ref"],
            "scope": dict(scope), "replayed": replayed,
            "source_replayed": source_replayed, "metadata": dict(signed["parser"]),
            "locators": list(signed["locators"]), "scope_status": "UNASSIGNED" if scope["global_scope"] else "VERIFIED",
            "global_projection": "NOT_VERIFIED" if scope["global_scope"] else "NOT_APPLICABLE",
            "selected_row_indices": list(selected_indices or []),
            "canonical_rows_inserted": int(rows_inserted),
            "canonical_row_records": list(row_records or []),
            "preview_rows_sha256": preview_rows_sha256,
            "source_boundaries": source_boundaries(signed["provenance"])}


def locate_quote(evidence_id: int, *, actor: Any, scope: Mapping, start: int, end: int) -> dict:
    """Resolve an exact quote and its parser position from retained source truth."""
    context = authorize(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        evidence = _verified_evidence(
            con, evidence_id, context, actor,
            source_use_purposes=("internal_research", "short_quote"), source_use_operation="read",
        )
    text = evidence["raw_content"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise SavedWorkError("DOCUMENT_QUOTE_RANGE_INVALID")
    source = evidence["provenance"]
    if (source["provenance"].get("approved_internal_source_use") is not None
            and end - start > 160):
        raise SavedWorkError("SOURCE_USE_QUOTE_LIMIT_EXCEEDED")
    locators = [loc for loc in source.get("locators", []) if loc["start"] < end and loc["end"] > start]
    authorize(actor, scope, action="read")
    authorize(actor, {k: source["context"][k] for k in
                     ("domain_id", "subject_id", "brand_focus_id", "global_scope")}, action="read")
    return {"citation": {"evidence_id": evidence_id, "start": start, "end": end, "quote": text[start:end]},
            "original_scope": {k: source["context"][k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")},
            "source_id": evidence["source_id"], "evidence_version": evidence["version"],
            "source_artifact_ref":source["source_artifact_ref"],
            "source_url": source["source_url"], "source_fingerprint": source["source_fingerprint"],
            "published_at": source["provenance"]["published_at"],
            "captured_at": source["provenance"]["captured_at"], "locators": locators,
            **source_boundaries(source["provenance"]), "rights": source["provenance"]["rights"],
            "intended_use": source["provenance"].get("intended_use", "research_reference")}
