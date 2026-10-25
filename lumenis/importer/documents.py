"""Exact-scope, retryable document ingestion into the existing Evidence/Canonical owners.

The caller supplies one approved local file and provenance. No network, AI,
schema creation or production database selection occurs in this service.
"""
from __future__ import annotations

import hashlib
import json
import re
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
    prepared = _prepare(file_path, actor=actor, scope=scope, provenance=provenance)
    _require_document_evidence_signer()
    return prepared["resource"]


def _require_document_evidence_signer():
    """Read the existing signer configuration without creating or exposing a key."""
    try:
        evidence_store._integrity_key_ring()
    except evidence_store.EvidenceIntegrityError as exc:
        raise SavedWorkError("DOCUMENT_EVIDENCE_SIGNING_UNAVAILABLE") from exc


def _record_document_evidence(**kwargs):
    try:
        return evidence_store.record_evidence(**kwargs)
    except evidence_store.EvidenceIntegrityError as exc:
        # A configuration change during the transaction must still be a stable
        # failure, and a material/signature defect must never be bypassed.
        _require_document_evidence_signer()
        raise SavedWorkError("DOCUMENT_EVIDENCE_INTEGRITY_FAILED") from exc


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
                    expected_preview_rows_sha256: str | None = None,
                    _transaction_validator=None, _owner_metadata=None) -> dict:
    """Atomically retain parsed source, signed provenance and canonical content.

    A retry uses exactly the same provenance including capture time. A modified
    file, scope, source or time is a different import and needs its own admission.
    """
    prepared = _prepare(file_path, actor=actor, scope=scope, provenance=provenance)
    scope = {k: prepared["context"][k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}
    provenance = prepared["descriptor"]["provenance"]
    context = _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"])
    _require_document_evidence_signer()
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
    if _owner_metadata is not None:
        if not callable(_transaction_validator) or not isinstance(_owner_metadata, dict) or set(_owner_metadata) not in ({"entity_profile"}, {"research_origin"}):
            raise SavedWorkError("DOCUMENT_OWNER_METADATA_INVALID")
        metadata.update(json.loads(_json(_owner_metadata)))
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"], connection=con)
        if _transaction_validator is not None:
            if not callable(_transaction_validator):
                raise SavedWorkError("DOCUMENT_TRANSACTION_VALIDATOR_INVALID")
            _transaction_validator(con)
        cur = con.execute("SELECT * FROM app_evidence_records WHERE feature_id='DOCUMENT_IMPORT' AND asset_id=?",
                          (source_id,))
        row = cur.fetchone()
        if row is not None:
            evidence_id = dict(zip((column[0] for column in cur.description), row))["id"]
            evidence = _verified_evidence(con, evidence_id, context, actor)
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
        evidence_id = _record_document_evidence(
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
        evidence = _verified_evidence(con, evidence_id, context, actor)
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
        if (not row_sha256 or not re.fullmatch(r"[0-9a-f]{64}", row_sha256)
                or hashlib.sha256(row_payload.encode("utf-8")).hexdigest() != row_sha256):
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
        structured = getattr(note, "source_record", None)
        if structured is not None:
            if (_json(structured).decode("utf-8") != row_payload
                    or structured.get("source_sha256") != parsed.metadata["source_fingerprint"]):
                raise SavedWorkError("DOCUMENT_ROW_STRUCTURE_INVALID")
            row_provenance["source_record"] = structured
            row_provenance["source_fields"] = getattr(note, "source_fields", [])
            row_provenance["parser_version"] = parsed.metadata.get("parser_version", "")
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


def _verify_imported_document_producer(evidence):
    provenance = evidence.get('provenance')
    if (not isinstance(provenance, dict)
            or evidence.get('source') != 'document_import'
            or evidence.get('feature_id') != 'DOCUMENT_IMPORT'
            or evidence.get('provider') != 'importer'
            or evidence.get('version') not in {'document-import/1', 'document-import/2'}):
        raise SavedWorkError('DOCUMENT_SOURCE_PRODUCER_INVALID')


def _source_bytes(con, evidence):
    import shared_artifacts
    provenance = evidence["provenance"]
    artifact_id = provenance.get("source_artifact_ref")
    cur = con.execute("SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=? AND kind IN ('imported_document_source','collected_source')", (artifact_id,))
    row = cur.fetchone()
    if row is None:
        raise SavedWorkError("DOCUMENT_SOURCE_ARTIFACT_MISSING")
    record = dict(zip((c[0] for c in cur.description), row))
    if record['kind'] == 'imported_document_source':
        _verify_imported_document_producer(evidence)
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
    if evidence.get('version') == 'collected-browser-snapshot:v1':
        return _verify_browser_snapshot_source(con, evidence, raw, record)
    public_mode = evidence.get('version') == 'collected-public-source:live-v1'
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
        from lumenis.system.collector.adapters.secondary_collection import (
            NativePublicCapture, _native_capture_record, validate_public_source_original)
        original = (validate_public_source_original(raw, record['sha256']) if public_mode else
                    _native_capture_record(NativePublicCapture(binding['platform'], raw, record['sha256'])))
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
    expected_locator = {'unit':'public-document-body' if public_mode else 'native-post-body', 'json_path':'$.body',
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
            or (pending_version and not pending_mode)
            or public_mode != (capture_mode == 'live_public_response_intake')
            or (public_mode and binding['platform'] != 'public_http')):
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

    if live_mode or pending_mode or public_mode:
        lineage = original.get('source_lineage')
        if (signed.get('source_lineage') != lineage or not isinstance(lineage, list)
                or len(lineage) != (2 if public_mode else 1)):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        observed_lineage = lineage[1] if public_mode else lineage[0]
        if (not isinstance(observed_lineage, dict)
                or set(observed_lineage) != {'sha256', 'locator', 'kind', 'transport_original'}
                or observed_lineage.get('kind') != ('SIGNED_SOURCE_OBSERVATION_JSON' if public_mode else 'SIGNED_NATIVE_OBSERVATION_JSON')
                or observed_lineage.get('transport_original') is not False):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        observations = parent_inputs.get('source_observation_records')
        locator = observed_lineage.get('locator')
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
        if (observed_lineage.get('locator') !=
                ref + ':inputs.source_observation_records[' + str(observation_index) + ']'
                or observed_lineage.get('sha256') != hashlib.sha256(observation_bytes).hexdigest()
                or original.get('native_record') != observation
                or original.get('body') != observation.get('content')
                or original.get('source_url') != observation.get('url')):
            raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        if public_mode:
            # The pure PublicHttp producer above reparses its own preserved HTTP
            # bytes. A signed parent observation must still be that exact item;
            # neither URL discovery nor a parent grant supplies SourceUse rights.
            if (original.get('native_id') != observation.get('content_id')
                    or original.get('native_id') != str(evidence.get('asset_id'))
                    or original.get('body_state') != (observation.get('source_raw') or {}).get('content_observation', {}).get('completeness')):
                raise SavedWorkError('COLLECTED_SOURCE_PARENT_INVALID')
        elif pending_mode:
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


def reopen_imported_source(evidence_id: int, *, actor: Any, scope: Mapping) -> dict:
    context = authorize(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        evidence = _verified_evidence(con, evidence_id, context, actor)
        raw, record = _source_bytes(con, evidence)
    _check_effect(actor, scope, OperationType.DATA_EXPORT, "document-source-read:v1:" + record["sha256"])
    source_context = evidence["provenance"]["context"]
    authorize(actor, {k: source_context[k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}, action="read")
    result = {"content":raw, "artifact_ref":record["artifact_id"], "sha256":record["sha256"],
              "size_bytes":record["size_bytes"], "filename":record["filename"],
              "source_id":evidence["asset_id"], "evidence_id":evidence_id,
              "source_origin":evidence["provenance"]["provenance"].get("source_origin"),
              "scope":{k: source_context[k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}}
    if (evidence["provenance"].get("capture_mode") == "live_pending_observation_intake"
            and evidence.get("version") == "collected-native-source:pending-v1"):
        result.update(entity_assignment=evidence["provenance"].get("entity_assignment"),
                      scope_status="UNASSIGNED", canonical_ref=None)
    return result

def read_document_source_rows(source_ref, *, actor, scope, offset, limit,
                              source_version, source_sha256):
    """Bounded SH02 inspection of current authorized immutable original rows.

    The route reference plus ART identity and original-byte hash pin a page set.
    Re-parsing uses the existing bounded parser; no Canonical admission or write.
    """
    from .analyzer import extract_document_reading_rows
    if (type(offset) is not int or not 0 <= offset <= 100000
            or type(limit) is not int or not 1 <= limit <= 100
            or not isinstance(source_version, str) or not source_version
            or not isinstance(source_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None):
        raise ValueError("DOCUMENT_ROW_PAGE_INVALID")
    if type(source_ref) is int:
        material = reopen_imported_source(source_ref, actor=actor, scope=scope)
        version, fingerprint = material["artifact_ref"], material["sha256"]
        if version != source_version or fingerprint != source_sha256:
            raise ValueError("DOCUMENT_SOURCE_VERSION_CHANGED")
        # Collected sources have another producer/format contract, never guess.
        context = authorize(actor, scope, action="read")
        with get_repository().connection(read_only=True, wal=False) as con:
            evidence = _verified_evidence(con, source_ref, context, actor)
            _verify_imported_document_producer(evidence)
            revision = evidence["version"]
        with tempfile.TemporaryDirectory(prefix="lumenis-document-row-read-") as temporary:
            path = Path(temporary) / ("source" + Path(material["filename"]).suffix)
            path.write_bytes(material["content"])
            parsed = parse_file(str(path))
    else:
        record, parsed = _read_private_document_material(source_ref, actor=actor, scope=scope,
                                                        require_current=True)
        version, fingerprint = record["source_artifact_ref"], record["source_fingerprint"]
        revision = record["source_version"]
        if version != source_version or fingerprint != source_sha256:
            raise ValueError("DOCUMENT_SOURCE_VERSION_CHANGED")
    if parsed.metadata.get("format") not in {"excel", "word", "pdf", "csv"}:
        raise ValueError("DOCUMENT_TYPED_ROWS_UNAVAILABLE")
    notes = extract_document_reading_rows(parsed)
    rows = []
    for index, note in enumerate(notes[offset:offset + limit], start=offset):
        raw = str(note.raw_chunk)
        if hashlib.sha256(raw.encode()).hexdigest() != note.source_row_sha256:
            raise ValueError("DOCUMENT_TYPED_ROW_HASH_MISMATCH")
        rows.append({"index": index, "raw_chunk": raw, "source_locator": note.source_locator,
                     "source_row_sha256": note.source_row_sha256,
                     "source_record": note.source_record or {}, "source_fields": note.source_fields,
                     "analysis_status": "NOT_RUN"})
    # Revalidate current owner, rights and original bytes after parsing, before release.
    if type(source_ref) is int:
        current = reopen_imported_source(source_ref, actor=actor, scope=scope)
        if current["artifact_ref"] != version or current["sha256"] != fingerprint:
            raise ValueError("DOCUMENT_SOURCE_VERSION_CHANGED")
    else:
        current = read_private_document_source(source_ref, actor=actor, scope=scope)
        if current["source_artifact_ref"] != version or current["source_fingerprint"] != fingerprint:
            raise ValueError("DOCUMENT_SOURCE_VERSION_CHANGED")
    return {"source_version": version, "source_version_kind": "immutable_artifact_ref",
            "source_revision": revision, "source_sha256": fingerprint,
            "format": parsed.metadata["format"], "parser_version": parsed.metadata.get("parser_version"),
            "offset": offset, "limit": limit, "returned_count": len(rows),
            "source_row_count": len(notes), "has_more": offset + len(rows) < len(notes),
            "source_rows": rows, "analysis_status": "NOT_RUN", "fact_verified": False}


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
        evidence = _verified_evidence(con, evidence_id, context, actor)
    text = evidence["raw_content"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise SavedWorkError("DOCUMENT_QUOTE_RANGE_INVALID")
    source = evidence["provenance"]
    locators = [loc for loc in source.get("locators", []) if loc["start"] < end and loc["end"] > start]
    authorize(actor, scope, action="read")
    authorize(actor, {k: source["context"][k] for k in
                     ("domain_id", "subject_id", "brand_focus_id", "global_scope")}, action="read")
    return {"citation": {"evidence_id": evidence_id, "start": start, "end": end, "quote": text[start:end]},
            "original_scope": {k: source["context"][k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")},
            "source_id": evidence["asset_id"], "evidence_version": evidence["version"],
            "source_artifact_ref":source["source_artifact_ref"],
            "source_url": source["source_url"], "source_fingerprint": source["source_fingerprint"],
            "published_at": source["provenance"]["published_at"],
            "captured_at": source["provenance"]["captured_at"], "locators": locators,
            **source_boundaries(source["provenance"]), "rights": source["provenance"]["rights"],
            "intended_use": source["provenance"].get("intended_use", "research_reference")}


def save_private_document(file_path, *, actor, scope, request_id, title=None,
                          context_keywords=None):
    """Retain an uploaded original and deterministic analysis in private Shared.

    This is custody, not Canonical admission or an external-use rights grant.
    Reopening, revision, recovery and export stay with the existing SavedWork owner.
    """
    from pathlib import Path
    from lumenis.importer.parser import parse_file
    from lumenis.importer.analyzer import analyze_source_basics
    from lumenis.shared.reporting import saved_work

    if scope != {"scope_kind": "shared_workspace", "version": 1}:
        raise ValueError("DOCUMENT_PRIVATE_SCOPE_REQUIRED")
    saved_work.authorize_saved_work(actor, scope, action="write")
    path = Path(file_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("DOCUMENT_SOURCE_INVALID")
    with path.open("rb") as source:
        raw = source.read(8 * 1024 * 1024 + 1)
    if not 0 < len(raw) <= 8 * 1024 * 1024:
        raise ValueError("DOCUMENT_SOURCE_SIZE_INVALID")
    digest = hashlib.sha256(raw).hexdigest()
    extension = path.suffix.lower().lstrip(".")
    spec = {**saved_work._OFFICE_FORMATS, **saved_work._CUSTODY_FORMATS}.get(extension)
    if spec is None:
        raise ValueError("DOCUMENT_FORMAT_UNSUPPORTED")
    # Validate before parsing any untrusted office package.
    attachment = {"name": "original-" + digest[:20] + "." + extension,
                  "content": raw, "media_type": spec["media_type"]}
    checked = saved_work._attachment_spec(attachment["name"], attachment["media_type"])
    if not saved_work._valid_ooxml_attachment(raw, checked):
        raise ValueError("DOCUMENT_SOURCE_INVALID")
    parsed = parse_file(str(path))
    if parsed.metadata.get("source_fingerprint") != digest:
        raise ValueError("DOCUMENT_SOURCE_CHANGED")
    analysis = analyze_source_basics(parsed, context_keywords)
    payload = {
        "source_material": {"original_filename": path.name, "sha256": digest,
            "size_bytes": len(raw), "attachment_name": attachment["name"],
            "rights": "UNKNOWN", "author": None, "origin": "user-upload",
            "allowed_use": "private_custody_and_analysis", "external_redistribution": False,
            "canonical_admitted": False, "training_eligible": False},
        "parsed_source": {"text": parsed.text, "tables": parsed.tables,
                          "source_tables": getattr(parsed, "source_tables", []),
                          "source_blocks": getattr(parsed, "source_blocks", []),
                          "locators": parsed.locators, "metadata": parsed.metadata},
        "basic_analysis": analysis,
    }
    heading = title or path.name
    markdown = ("# " + heading + "\n\nPrivate uploaded source analysis\n\n"
                + f"Characters: {analysis['character_count']}\n\n"
                + f"Tables: {analysis['table_count']}\n\n"
                + "## Source excerpts (not verified facts)\n\n"
                + "\n\n".join(item["text"] for item in analysis["source_excerpts"])
                + "\n\n## Limitations\n\n" + "\n".join(analysis["limitations"]))
    return saved_work.save_work(
        title=heading, markdown=markdown, kind="research", payload=payload,
        citations=[], request_id=request_id, actor=actor, scope=scope,
        attachments=[attachment],
    )


def _office_snapshot(artifact_id, *, actor, scope):
    from lumenis.importer.office_package import OfficePackage
    from lumenis.shared.reporting import saved_work
    if scope != {"scope_kind": "shared_workspace", "version": 1}:
        raise ValueError('DOCUMENT_PRIVATE_SCOPE_REQUIRED')
    item = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope)
    material = item['document']['payload'].get('source_material')
    if type(material) is not dict or material.get('allowed_use') != 'private_custody_and_analysis':
        raise ValueError('DOCUMENT_ORIGINAL_REQUIRED')
    attachment = saved_work.download_attachment(artifact_id, name=material.get('attachment_name'), actor=actor, scope=scope)
    if material.get('sha256') != attachment['sha256'] or material.get('size_bytes') != len(attachment['content']):
        raise ValueError('DOCUMENT_ORIGINAL_CHANGED')
    extension = Path(attachment['filename']).suffix.lstrip('.')
    if extension not in saved_work._OFFICE_FORMATS:
        raise ValueError('OFFICE_PACKAGE_INVALID')
    attachment['media_type'] = saved_work._OFFICE_FORMATS[extension]['media_type']
    package = OfficePackage(attachment['content'], filename=attachment['filename'], media_type=attachment['media_type'])
    return item, attachment, package


def read_office_document(artifact_id, *, actor, scope, offset=0, limit=100):
    """Project exact authorized original objects; offsets never imply complete coverage."""
    from lumenis.shared.reporting import saved_work
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('OFFICE_OBJECT_PAGE_INVALID')
    item, attachment, package = _office_snapshot(artifact_id, actor=actor, scope=scope)
    projection = package.projection()
    objects = projection['objects']
    projection['objects'] = objects[offset:offset + limit]
    projection['has_more'] = offset + limit < len(objects)
    projection['next_offset'] = offset + limit if projection['has_more'] else None
    context = saved_work.authorize_saved_work(actor, scope, action='read')
    with saved_work.get_repository().connection(read_only=True, wal=False) as con:
        versions = saved_work._versions(con, item['document']['work_id'], context, actor)
        current = versions[-1]['artifact']['artifact_id'] == artifact_id
        saved_work.authorize_saved_work(actor, scope, action='read', connection=con)
    # A source changed/replaced while parsing cannot supply a successful object view.
    if saved_work.download_attachment(artifact_id, name=attachment['filename'], actor=actor, scope=scope)['sha256'] != package.sha256:
        raise ValueError('DOCUMENT_ORIGINAL_CHANGED')
    return {'source_artifact_id': artifact_id, 'source_artifact_sha256': item['artifact']['sha256'],
            'work_id': item['document']['work_id'], 'version': item['document']['version'],
            'current_version': current, 'attachment_name': attachment['filename'], **projection}


def edit_office_document(artifact_id, *, actor, scope, request_id, expected_sha256,
                         expected_package_sha256, reason, commands,
                         acknowledge_signature_invalidation=False):
    """Commit a local object edit as the same SavedWork's next immutable version."""
    from lumenis.importer.analyzer import analyze_source_basics
    from lumenis.shared.reporting import saved_work
    if type(reason) is not str or not reason.strip() or len(reason) > 2000:
        raise ValueError('OFFICE_EDIT_REASON_REQUIRED')
    if type(acknowledge_signature_invalidation) is not bool:
        raise ValueError('OFFICE_SIGNATURE_CONFIRMATION_INVALID')
    saved_work.authorize_saved_work(actor, scope, action='write')
    item, attachment, package = _office_snapshot(artifact_id, actor=actor, scope=scope)
    if item['artifact']['sha256'] != expected_sha256:
        raise ValueError('OFFICE_WORK_REVISION_CONFLICT')
    edited = package.edit(commands, expected_package_sha256=expected_package_sha256,
                          acknowledge_signature_invalidation=acknowledge_signature_invalidation)
    name = 'edited-' + edited['receipt']['package_sha256'][:20] + package.spec['extension']
    with tempfile.TemporaryDirectory(prefix='lumenis-office-edit-') as temporary:
        path = Path(temporary) / name
        path.write_bytes(edited['content'])
        parsed = parse_file(str(path))
    if parsed.metadata.get('source_fingerprint') != edited['receipt']['package_sha256']:
        raise ValueError('OFFICE_EDIT_REPARSE_MISMATCH')
    payload = json.loads(json.dumps(item['document']['payload'], ensure_ascii=False))
    payload['source_material'] = {**payload['source_material'],
        'sha256': edited['receipt']['package_sha256'], 'size_bytes': len(edited['content']),
        'attachment_name': name, 'origin': 'user-edited-original-version'}
    payload['parsed_source'] = {'text': parsed.text, 'tables': parsed.tables,
        'source_tables': getattr(parsed, 'source_tables', []), 'source_blocks': getattr(parsed, 'source_blocks', []),
        'locators': parsed.locators, 'metadata': parsed.metadata}
    analysis = analyze_source_basics(parsed)
    payload['basic_analysis'] = analysis
    payload['office_edit'] = {**edited['receipt'], 'reason': reason,
        'source_artifact_id': artifact_id, 'source_artifact_sha256': expected_sha256,
        'parent_attachment_name': attachment['filename'], 'result_attachment_name': name,
        'original_retained_in_parent_version': True}
    markdown = '# ' + item['document']['title'] + '\n\n' + reason + '\n\n' + '\n\n'.join(
        excerpt['text'] for excerpt in analysis['source_excerpts'])
    def recheck_source(con, _record, _document):
        parent = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope, connection=con)
        if parent['artifact']['sha256'] != expected_sha256:
            raise ValueError('OFFICE_WORK_REVISION_CONFLICT')
        binding = next(entry for entry in parent['document']['attachments'] if entry['name'] == attachment['filename'])
        context = saved_work.authorize_saved_work(actor, scope, action='read', connection=con)
        source = saved_work._read_attachment(con, binding, context, parent['document']['work_id'], actor=actor)
        if hashlib.sha256(source).hexdigest() != package.sha256:
            raise ValueError('DOCUMENT_ORIGINAL_CHANGED')
    result = saved_work.save_work(
        title=item['document']['title'], markdown=markdown, kind=item['document']['kind'], payload=payload,
        citations=item['document']['citations'], request_id=request_id, actor=actor, scope=scope,
        work_id=item['document']['work_id'], previous_artifact_id=artifact_id,
        expected_draft_digest=item['document']['draft_digest'], contract=item['document']['contract'],
        before_commit=recheck_source,
        attachments=[{'name': name, 'content': edited['content'], 'media_type': attachment['media_type']}])
    # Storage readback and caller-bound attachment identity are the actual export;
    # it never runs the report serializer to reconstruct the customer's package.
    downloaded = saved_work.download_attachment(result['artifact']['artifact_id'], name=name, actor=actor, scope=scope)
    if downloaded['content'] != edited['content']:
        raise ValueError('OFFICE_EDIT_READBACK_MISMATCH')
    result['office_attachment'] = {'artifact_id': result['artifact']['artifact_id'], 'name': name,
        'sha256': downloaded['sha256'], 'media_type': package.media_type,
        'size_bytes': len(downloaded['content'])}
    return result


_CAPTURE_RECEIPT_VERSION = 'admitted-document-receipt/1'


def _admitted_document_receipt_binding(record, document, spec, phase):
    return {'phase': phase, 'capture_schema': spec['capture_schema'],
            'artifact_id': record['artifact_id'], 'artifact_sha256': record['sha256'],
            'context': document['context'], 'request_id': document['request_id'],
            'payload_sha256': _digest(document['payload']),
            'attachments_sha256': _digest(document.get('attachments', []))}


def _write_admitted_document_receipt(con, record, document, *, spec, phase):
    """Internal capture owner only; same transaction as immutable SavedWork bytes."""
    binding = _admitted_document_receipt_binding(record, document, spec, phase)
    context = document['context']
    evidence_store.record_evidence(
        source='admitted_document_collector', product='CTH' if context['domain_id']=='cth' else 'ZBMP',
        feature_id='ADMITTED_DOCUMENT_' + phase.upper(), asset_id=record['artifact_id'],
        version=_CAPTURE_RECEIPT_VERSION, env='staging', capture_mode='owner_network_capture_receipt',
        provider='admitted_document_collector', inputs=binding, outputs={'saved_work_sha256': record['sha256']},
        raw_content=_json(binding).decode('utf-8'),
        collection_metadata={'context': context, 'binding': binding},
        domain_id=context['domain_id'], subject_id=context['subject_id'],
        brand_focus_id=context['brand_focus_id'], global_scope=context['global_scope'], connection=con)


def _verify_admitted_document_receipt(work, *, spec, phase):
    """A public SavedWork schema/string is never an acquisition credential."""
    binding = _admitted_document_receipt_binding(work['artifact'], work['document'], spec, phase)
    with get_repository().connection(read_only=True, wal=False) as con:
        cur = con.execute('SELECT * FROM app_evidence_records WHERE asset_id=? AND feature_id=?',
                          (work['artifact']['artifact_id'], 'ADMITTED_DOCUMENT_' + phase.upper()))
        rows = [dict(zip((c[0] for c in cur.description), row)) for row in cur.fetchall()]
    if len(rows) != 1:
        raise SavedWorkError(spec['error_prefix']+'_CAPTURE_OWNER_RECEIPT_REQUIRED')
    row = rows[0]
    expected_scope = evidence_store._normalize_record_evidence_scope(
        product='CTH' if binding['context']['domain_id']=='cth' else 'ZBMP',
        **{k: binding['context'][k] for k in ('domain_id','subject_id','brand_focus_id','global_scope')})
    try:
        valid = (evidence_store.classify_evidence_integrity(row)['verified'] is True
            and row.get('source') == 'admitted_document_collector'
            and row.get('provider') == 'admitted_document_collector'
            and row.get('version') == _CAPTURE_RECEIPT_VERSION
            and row.get('capture_mode') == 'owner_network_capture_receipt'
            and json.loads(row['inputs_json']) == {**binding, '_lumenis_scope': expected_scope}
            and json.loads(row['collection_metadata']) == {'context': binding['context'], 'binding': binding}
            and row.get('content_hash') == hashlib.sha256(_json(binding)).hexdigest()
            and json.loads(row['outputs_json']) == {'saved_work_sha256': work['artifact']['sha256']})
    except (ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise SavedWorkError(spec['error_prefix']+'_CAPTURE_OWNER_RECEIPT_INVALID')
    return row['id']


def _collect_admitted_document(target_artifact_id, *, actor, scope, request_id, spec,
        prepare_collection, read_target, existing_request, validate_response, prepare_capture):
    """Shared original document capture, parameterized only by internal owners.

    A revoked approval blocks even replay. Failure creates no successful capture;
    retry uses the same existing owner and never substitutes an unofficial host.
    """
    from lumenis.shared.reporting import saved_work
    from datetime import datetime, timezone
    from lumenis.system.security.permission import OperationType, get_permission_gate
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import public_source_provenance, PublicSourceError
    prepared=prepare_collection(target_artifact_id,actor=actor,scope=scope)
    gate=get_permission_gate()
    def admitted():
        saved_work.authorize(actor,scope,action='write')
        read_target(target_artifact_id,actor=actor,scope=scope)
        if gate.get_valid_approval_token(OperationType.COLLECTOR_START.value,prepared['resource'],exact=True) is None:
            raise PermissionError(spec['error_prefix']+'_COLLECTION_EXACT_APPROVAL_REQUIRED')
        saved_work._check_effect(actor,scope,OperationType.EXTERNAL_NETWORK,prepared['resource'])
    admitted()
    existing=existing_request(request_id,actor=actor,scope=scope)
    if existing:
        _verify_admitted_document_receipt(existing,spec=spec,phase='run')
        run=existing['document']['payload'].get(spec['run_key'],{})
        if run.get('target_artifact_id') != target_artifact_id:
            raise ValueError(spec['error_prefix']+'_REQUEST_REUSE_CONFLICT')
        capture=saved_work.reopen_work(run['capture_artifact_id'],actor=actor,scope=scope)
        return {'state':'CAPTURED','capture':capture,'replayed':True,
                'import_preview':prepare_capture(capture['artifact']['artifact_id'],actor=actor,scope=scope)}
    target_work,target=read_target(target_artifact_id,actor=actor,scope=scope)
    try:
        response=PublicHttpAdapter().fetch_document(target['url'],allowed_content_types=(spec['media_type'](target),),before_fetch=admitted)
    except PublicSourceError as exc:
        return {'state':'UNAVAILABLE','reason':'SAFE_PUBLIC_TRANSPORT_FAILED','error':str(exc)[:300],
                'url':target['url'],'source_saved':False,'analysis_status':'NOT_RUN',
                'next_step':spec['unavailable_hint']}
    admitted()  # cancellation, revoked scope/identity and approval during I/O
    if response.url != target['url']:
        raise ValueError(spec['error_prefix']+'_SOURCE_REDIRECT_TARGET_CHANGED')
    validate_response(response.content, target)
    filename=spec['filename'](target)
    media_type=spec['media_type'](target)
    sha=hashlib.sha256(response.content).hexdigest()
    stable_request=spec['capture_request_prefix']+saved_work._digest({'target':target_artifact_id,'sha256':sha})[:40]
    capture=existing_request(stable_request,actor=actor,scope=scope)
    def receipt_commit(phase):
        def commit(con, record, document):
            admitted()
            _write_admitted_document_receipt(con,record,document,spec=spec,phase=phase)
        return commit
    if capture is None:
        captured_at=datetime.now(timezone.utc).isoformat()
        provenance={'source_url':target['url'],'published_at':None,'captured_at':captured_at,
            'rights':'public-reference-only','title':spec['source_title'](target),
            'content_origin':{'kind':'publisher-material','claim_type':'source_statement'},
            'rights_statement':'Public disclosure response retained for internal reference; no redistribution or training grant.'}
        material={'schema':spec['capture_schema'],'target_artifact_id':target_artifact_id,
            'target_sha256':target_work['artifact']['sha256'],'sha256':sha,'size_bytes':len(response.content),
            'filename':filename,'source_provenance':provenance,
            'transport':public_source_provenance(response,target['url']),
            'capture_kind':'RAW_HTTP_RESPONSE_BODY','filing_document_original':spec['original_filing'](target),
            'source_admission':'PENDING_EXACT_IMPORT_APPROVAL','format':target['format']}
        capture=saved_work.save_work(title=spec['capture_title'],markdown=target['url']+'\nSHA256 '+sha+
            '\nRetained raw HTTP response; original-file status is recorded in the capture metadata. Canonical source admission is pending.',
            kind='research',payload={spec['capture_key']:material},citations=target_work['document']['citations'],
            request_id=stable_request,actor=actor,scope=scope,
            contract={'id':spec['capture_schema'],'version':'1','required_payload_paths':[spec['capture_key']]},
            attachments=[{'name':filename,'content':response.content,'media_type':spec.get('attachment_media_type',lambda _target:media_type)(target)}],
            before_commit=receipt_commit('capture'))
    _verify_admitted_document_receipt(capture,spec=spec,phase='capture')
    admitted()
    run=saved_work.save_work(title=spec['run_title'],markdown=target['url']+'\nCaptured '+sha,
        kind='research',payload={spec['run_key']:{'target_artifact_id':target_artifact_id,
            'capture_artifact_id':capture['artifact']['artifact_id'],'sha256':sha}},
        citations=target_work['document']['citations'],request_id=request_id,actor=actor,scope=scope,
        before_commit=receipt_commit('run'))
    _verify_admitted_document_receipt(run,spec=spec,phase='run')
    return {'state':'CAPTURED','capture':capture,'run':run,'replayed':False,
            'import_preview':prepare_capture(capture['artifact']['artifact_id'],actor=actor,scope=scope)}



def _read_admitted_document_capture(capture_artifact_id, *, actor, scope, spec, read_target, validate_response):
    """Reuse immutable SavedWork originals; callback owners bind source identity."""
    from lumenis.shared.reporting import saved_work
    work=saved_work.reopen_work(capture_artifact_id,actor=actor,scope=scope)
    _verify_admitted_document_receipt(work,spec=spec,phase='capture')
    def fail(suffix):
        raise ValueError(spec['error_prefix']+suffix)
    if work['document']['contract']['id']!=spec['capture_schema']:
        fail('_CAPTURE_CONTRACT_INVALID')
    material=work['document']['payload'].get(spec['capture_key'],{})
    target_work,target=read_target(material.get('target_artifact_id'),actor=actor,scope=scope)
    if target_work['artifact']['sha256']!=material.get('target_sha256'):
        fail('_TARGET_CHANGED')
    expected_filename=spec['filename'](target)
    if material.get('filename') != expected_filename:
        fail('_CAPTURE_FILENAME_INVALID')
    raw=saved_work.download_attachment(capture_artifact_id,name=expected_filename,actor=actor,scope=scope)['content']
    if hashlib.sha256(raw).hexdigest()!=material.get('sha256') or material['source_provenance']['source_url']!=target['url']:
        fail('_CAPTURE_CHANGED')
    validate_response(raw,target)
    return material,raw


def _prepare_admitted_document_capture(capture_artifact_id, *, actor, scope, read_capture):
    material,raw=read_capture(capture_artifact_id,actor=actor,scope=scope)
    with tempfile.TemporaryDirectory(prefix='lumenis-source-import-') as temporary:
        path=Path(temporary)/material['filename'];path.write_bytes(raw)
        resource=document_import_resource(str(path),actor=actor,scope=scope,provenance=material['source_provenance'])
    return {'state':'PREPARED','resource':resource,'sha256':material['sha256'],'source_url':material['source_provenance']['source_url'],
            'capture_artifact_id':capture_artifact_id,'effect':'CANONICAL_SOURCE_IMPORT','scope':scope}


def _import_admitted_document_capture(capture_artifact_id, *, actor, scope, read_capture, error_prefix):
    from lumenis.system.security.permission import get_permission_gate
    material,raw=read_capture(capture_artifact_id,actor=actor,scope=scope)
    with tempfile.TemporaryDirectory(prefix='lumenis-source-import-') as temporary:
        path=Path(temporary)/material['filename'];path.write_bytes(raw)
        resource=document_import_resource(str(path),actor=actor,scope=scope,provenance=material['source_provenance'])
        if get_permission_gate().get_valid_approval_token('data_import',resource,exact=True) is None:
            raise PermissionError(error_prefix+'_IMPORT_EXACT_APPROVAL_REQUIRED')
        def recheck(_con):
            current,current_raw=read_capture(capture_artifact_id,actor=actor,scope=scope)
            if current != material or current_raw != raw:
                raise ValueError(error_prefix+'_CAPTURE_CHANGED')
            if get_permission_gate().get_valid_approval_token('data_import',resource,exact=True) is None:
                raise PermissionError(error_prefix+'_IMPORT_EXACT_APPROVAL_REQUIRED')
        source=import_document(str(path),actor=actor,scope=scope,provenance=material['source_provenance'],
            _transaction_validator=recheck)
    return material,source


def _existing_source_request(request_id, *, actor, scope, error_prefix):
    from lumenis.shared.reporting import saved_work
    if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',request_id):
        raise ValueError(error_prefix+'_REQUEST_ID_INVALID')
    context=saved_work.authorize(actor,scope,action='read')
    work_id='WORK-'+saved_work._digest({'context':context,'request_id':request_id})[:24]
    with get_repository().connection(read_only=True,wal=False) as con:
        versions=saved_work._versions(con,work_id,context,actor)
    return saved_work.reopen_work(versions[-1]['artifact']['artifact_id'],actor=actor,scope=scope) if versions else None


def _verify_browser_snapshot_source(con, evidence, raw, record):
    """Pure integrity reader for Collector's sanitized snapshot producer."""
    from lumenis.system.collector.runtime.browser_extract import validate_source_snapshot, snapshot_bytes
    try:
        snapshot = validate_source_snapshot(json.loads(raw))
        if snapshot_bytes(snapshot) != raw:
            raise ValueError('noncanonical snapshot')
        metadata = evidence['provenance']
        binding = {**snapshot['binding'], 'snapshot_sha256': hashlib.sha256(raw).hexdigest()}
        integrity = evidence_store.classify_evidence_integrity(evidence)
        request = metadata['browser_admission_request']
        source = metadata['provenance']
        inputs = json.loads(evidence['inputs_json'])
        context = metadata['context']
        owner = {k:v for k,v in context.items() if k not in ('domain_id','subject_id','brand_focus_id','global_scope')}
        if (evidence.get('source') != 'collector' or evidence.get('feature_id') != 'COLLECTED_SOURCE'
                or evidence.get('provider') != 'collector-browser-snapshot'
                or evidence.get('version') != 'collected-browser-snapshot:v1'
                or evidence.get('status') != 'verified' or evidence.get('result') != 'PASS'
                or integrity.get('verified') is not True or integrity.get('assurance') != 'writer-authenticated'
                or metadata.get('browser_snapshot_binding') != binding
                or 'native_source_binding' in metadata
                or metadata.get('capture_mode') != 'sanitized_browser_snapshot'
                or metadata.get('source_kind') != 'collected_source'
                or metadata.get('original_resource_sha256', 'missing') is not None
                or metadata.get('parsed_text') != snapshot['body']
                or metadata.get('locators') != snapshot['block_map']
                or evidence.get('content_hash') != binding['body_sha256']
                or record.get('note_id') != evidence.get('asset_id')
                or request.get('context') != context or metadata.get('owner') != owner
                or source.get('source_url') != snapshot['metadata']['url']
                or metadata.get('source_url') != source.get('source_url')
                or source.get('captured_at') != snapshot['metadata']['captured_at']
                or source.get('title') != snapshot['metadata']['title']
                or source.get('published_at', 'missing') is not None
                or any(source.get(k) != request.get(k) for k in ('rights','rights_statement','intended_use'))
                or source.get('rights') not in ('public-reference-only','owner-approved')):
            raise ValueError('snapshot binding')
        source_boundaries(source)
        expected_id = 'browser_' + _digest({'context':context,'request_id':request['request_id']})
        expected_resource = 'browser-snapshot-import:v1:' + _digest({**request,'snapshot_sha256':binding['snapshot_sha256']})
        if (evidence['asset_id'] != expected_id or metadata['source_intake_resource'] != expected_resource
                or inputs.get('source_intake_resource') != expected_resource):
            raise ValueError('request binding')
        ref = metadata.get('collection_evidence_ref')
        if (not isinstance(ref, str) or re.fullmatch(r'app_evidence_records:[1-9][0-9]*',ref) is None
                or inputs.get('collection_evidence_ref') != ref):
            raise ValueError('parent reference')
        parent = con.execute('SELECT * FROM app_evidence_records WHERE id=?',(int(ref.split(':')[1]),)).fetchone()
        if parent is None:
            raise ValueError('missing parent')
        parent = dict(parent)
        parent_meta = json.loads(parent['collection_metadata'])
        parent_inputs = json.loads(parent['inputs_json'])
        integrity = evidence_store.classify_evidence_integrity(parent)
        if (parent.get('source') != 'collector' or parent.get('feature_id') != 'BROWSER_SNAPSHOT_ADMISSION'
                or parent.get('provider') != 'collector-browser-snapshot'
                or parent.get('version') != 'browser-snapshot-admission:v1'
                or parent.get('asset_id') != expected_id or parent.get('content_hash') != binding['body_sha256']
                or parent.get('status') != 'verified' or parent.get('result') != 'PASS'
                or integrity.get('verified') is not True or integrity.get('assurance') != 'writer-authenticated'
                or any(parent_meta.get(k) != metadata.get(k) for k in
                    ('context','owner','browser_admission_request','source_intake_resource','browser_snapshot_binding'))
                or parent_inputs.get('source_intake_resource') != expected_resource
                or parent_inputs.get('_lumenis_scope') != inputs.get('_lumenis_scope')):
            raise ValueError('parent binding')
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise SavedWorkError('BROWSER_SOURCE_INTEGRITY_FAILED') from exc


def _read_private_document_material(artifact_id, *, actor, scope, connection=None, require_current=True):
    """Read verified private custody bytes, never promote user text to fact.

    A user can edit SavedWork payloads. Reparse the checked original attachment
    rather than trusting a caller-supplied parsed_source or license assertion.
    """
    import tempfile
    from pathlib import Path
    from lumenis.importer.parser import parse_file
    from lumenis.shared.reporting import saved_work
    if scope != {"scope_kind": "shared_workspace", "version": 1}:
        raise ValueError("DOCUMENT_PRIVATE_SCOPE_REQUIRED")
    item = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope,
                                         connection=connection)
    from contextlib import nullcontext
    reader = saved_work.get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    with reader as con:
        context = saved_work.authorize_saved_work(actor, scope, action='read', connection=con)
        versions = saved_work._versions(con, item['document']['work_id'], context, actor)
        if require_current and (not versions or versions[-1]['artifact']['artifact_id'] != artifact_id):
            raise PermissionError('DOCUMENT_SOURCE_VERSION_CHANGED')
    material = item["document"]["payload"].get("source_material")
    if not isinstance(material, dict):
        raise ValueError("DOCUMENT_ORIGINAL_REQUIRED")
    name = material.get("attachment_name")
    attachment = saved_work.download_attachment(artifact_id, name=name, actor=actor, scope=scope)
    if (material.get("sha256") != attachment["sha256"]
            or material.get("size_bytes") != len(attachment["content"])):
        raise ValueError("DOCUMENT_ORIGINAL_CHANGED")
    suffix = Path(name).suffix
    with tempfile.TemporaryDirectory(prefix="lumenis-private-reparse-") as temporary:
        path = Path(temporary) / ("source" + suffix)
        path.write_bytes(attachment["content"])
        parsed = parse_file(str(path))
    saved_work.authorize_saved_work(actor, scope, action="read", connection=connection)
    ref = "saved_work:" + artifact_id + ":" + item["artifact"]["sha256"]
    record = {"source_id": artifact_id, "source_artifact_ref": artifact_id,
            "source_artifact_sha256": item["artifact"]["sha256"],
            "source_version": item["document"]["version"], "evidence_id": ref,
            "scope_evidence_ref": ref, "canonical_id": None,
            "source_type": "private_document", "title": item["document"]["title"],
            "source_url": None, "published_at": None,
            "captured_at": item["document"].get("created_at"),
            "content_hash": hashlib.sha256(parsed.text.encode()).hexdigest(),
            "source_fingerprint": attachment["sha256"],
            "content_excerpt": parsed.text[:1200], "character_count": len(parsed.text),
            "table_count": len(parsed.tables), "truncated": len(parsed.text) > 1200,
            "rights": "UNKNOWN", "allowed_use": "private_custody_and_analysis",
            "external_redistribution": False, "training_eligible": False,
            "claim_type": "SOURCE_STATEMENT", "fact_verified": False,
            "scope": dict(scope)}

    return record, parsed


def adopt_shared_research_source(*, job_id, source_id, actor, target_scope, provenance,
                                 mode='prepare'):
    """Explicit same-actor custody-to-domain import using the existing importer.

    The caller must declare lawful intended use and obtain the normal exact
    DATA_IMPORT approval. Private custody does not assert a redistribution right.
    The signed origin remains a live dependency on the private report and bytes.
    """
    from lumenis.shared.reporting import saved_work, source_brief_job as reports
    if mode not in {'prepare', 'import'}:
        raise ValueError('RESEARCH_ADOPTION_MODE_INVALID')
    context = authorize(actor, target_scope, action='write')
    if context.get('global_scope') or not (context.get('subject_id') or context.get('brand_focus_id')):
        raise ValueError('RESEARCH_ADOPTION_FOCUSED_SCOPE_REQUIRED')
    if (not isinstance(provenance, Mapping) or provenance.get('rights') != 'owner-approved'
            or not isinstance(provenance.get('rights_statement'), str)
            or not provenance['rights_statement'].strip()):
        raise ValueError('RESEARCH_ADOPTION_EXPLICIT_RIGHTS_REQUIRED')
    identity = saved_work.authorize_saved_work(actor, reports.SHARED_SCOPE, action='read')
    actor_id = identity.get('principal_ref') or f"actor:{identity.get('actor_id')}"
    report = reports.get_source_brief_job(job_id, actor=actor, actor_id=actor_id,
                                         expected_scope=reports.SHARED_SCOPE)
    if report.get('hypothesis_review_state') == 'requires_reassessment':
        raise PermissionError('SOURCE_BRIEF_RESEARCH_REASSESSMENT_REQUIRED')
    matches = [row for row in report['source_brief']['records'] if row['source_id'] == source_id]
    if len(matches) != 1:
        raise ValueError('RESEARCH_ADOPTION_SOURCE_NOT_BOUND')
    source = matches[0]
    item = saved_work.read_committed_work(source_id, actor=actor, scope=reports.SHARED_SCOPE)
    name = item['document']['payload']['source_material']['attachment_name']
    attachment = saved_work.download_attachment(source_id, name=name, actor=actor, scope=reports.SHARED_SCOPE)
    origin = {'schema': 'shared-research-adoption/v1', 'job_id': job_id, 'actor_id': actor_id,
              'report_hash': report['artifact_outcome']['artifact_hash'], 'source_id': source_id,
              'source_artifact_sha256': source['source_artifact_sha256'],
              'source_fingerprint': attachment['sha256'], 'scope': reports.SHARED_SCOPE}
    if report.get('hypothesis_review') is not None:
        origin['hypothesis_review'] = report['hypothesis_review']
    declaration = json.loads(_json(dict(provenance)))
    # Origin is determined from verified owner bytes, never a client-provided URL.
    if declaration.get('source_url') is not None or 'source_origin' in declaration:
        raise ValueError('RESEARCH_ADOPTION_ORIGIN_IS_SERVER_BOUND')
    declaration['source_origin'] = {'kind': 'approved-file', 'ref': 'research_' + _digest(origin)}
    def current(con):
        validate_shared_research_origin(origin, actor=actor, connection=con)
    with tempfile.TemporaryDirectory(prefix='lumenis-research-adoption-') as temporary:
        file_path = Path(temporary) / ('source' + Path(name).suffix)
        file_path.write_bytes(attachment['content'])
        resource = document_import_resource(str(file_path), actor=actor, scope=target_scope,
                                            provenance=declaration)
        if mode == 'prepare':
            return {'state': 'awaiting_exact_import_approval', 'resource': resource,
                    'operation': 'data_import', 'research_origin': origin,
                    'rights': 'USER_DECLARED_OWNER_APPROVED', 'fact_verified': False}
        result = import_document(str(file_path), actor=actor, scope=target_scope,
            provenance=declaration, _transaction_validator=current, _owner_metadata={'research_origin': origin})
        return {**result, 'research_origin': origin, 'fact_verified': False}


def validate_shared_research_origin(origin, *, actor, connection=None):
    from lumenis.shared.reporting import source_brief_job as reports
    if (not isinstance(origin, dict) or origin.get('schema') != 'shared-research-adoption/v1'
            or origin.get('scope') != reports.SHARED_SCOPE):
        raise PermissionError('RESEARCH_ADOPTION_ORIGIN_INVALID')
    report = reports.get_source_brief_job(origin['job_id'], actor=actor, actor_id=origin['actor_id'],
        expected_scope=reports.SHARED_SCOPE, connection=connection)
    if (report.get('hypothesis_review_state') == 'requires_reassessment'
            or report.get('hypothesis_review') != origin.get('hypothesis_review')):
        raise PermissionError('RESEARCH_ADOPTION_REVIEW_CHANGED')
    matches = [row for row in report['source_brief']['records'] if row['source_id'] == origin['source_id']]
    if (report['artifact_outcome']['artifact_hash'] != origin['report_hash'] or len(matches) != 1
            or matches[0]['source_artifact_sha256'] != origin['source_artifact_sha256']
            or matches[0]['source_fingerprint'] != origin['source_fingerprint']):
        raise PermissionError('RESEARCH_ADOPTION_ORIGIN_CHANGED')
    return origin


def read_private_document_source(artifact_id, *, actor, scope, connection=None, require_current=True):
    record, _parsed = _read_private_document_material(artifact_id, actor=actor, scope=scope,
        connection=connection, require_current=require_current)
    return record


def read_private_document_typed_source(artifact_id, *, actor, scope, connection=None):
    """Derive complete typed rows only from current authorized original bytes."""
    from .analyzer import extract_document_reading_rows
    record, parsed = _read_private_document_material(artifact_id, actor=actor, scope=scope,
                                                    connection=connection, require_current=True)
    rows = []
    typed_rows = extract_document_reading_rows(parsed) if parsed.metadata.get("format") in {"excel", "word", "pdf", "csv"} else []
    for index, note in enumerate(typed_rows):
        raw = str(note.raw_chunk)
        if hashlib.sha256(raw.encode()).hexdigest() != note.source_row_sha256:
            raise ValueError("DOCUMENT_TYPED_ROW_HASH_MISMATCH")
        rows.append({"index": index, "title": note.title, "content": note.content,
                     "author": note.author, "publish_date": note.publish_date,
                     "raw_chunk": raw, "source_locator": note.source_locator,
                     "source_row_sha256": note.source_row_sha256,
                     "source_record": note.source_record or {},
                     "source_fields": note.source_fields, "analysis_status": "NOT_RUN"})
    return {"source_record": record, "evidence_ref": record["evidence_id"],
            "title": record["title"], "source_name": parsed.metadata.get("source_name", ""),
            "format": parsed.metadata.get("format", "UNKNOWN"),
            "published_at": record["published_at"], "captured_at": record["captured_at"],
            "source_fingerprint": record["source_fingerprint"],
            "content_sha256": record["content_hash"], "source_rows_sha256": _digest(rows),
            "source_row_count": len(rows), "source_rows": rows,
            "rights": record["rights"], "intended_use": record["allowed_use"],
            "analysis_status": "NOT_RUN"}
