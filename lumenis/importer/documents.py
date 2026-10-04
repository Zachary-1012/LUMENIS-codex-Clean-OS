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
    return _prepare(file_path, actor=actor, scope=scope, provenance=provenance)["resource"]


def import_document(file_path: str, *, actor: Any, scope: Mapping,
                    provenance: Mapping) -> dict:
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
            return _result(con, source_id, evidence_id, parsed, scope, product, replayed=True)
        with staging_write(prepared["resource"]):
            return _write_document(con, prepared, context, provenance, product, metadata, scope, actor)


def _write_document(con, prepared, context, provenance, product, metadata, scope, actor):
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
        con.execute("UPDATE lumenis_shared_artifacts SET evidence_id=? WHERE artifact_id=?",
                    (str(evidence_id), record["artifact_id"]))
        evidence = _verified_evidence(con, evidence_id, context)
        _source_bytes(con, evidence)
        _check_effect(actor, scope, OperationType.DATA_IMPORT, prepared["resource"], connection=con)
        result = _result(con, source_id, evidence_id, parsed, scope, product, replayed=False)
        con.commit()
        committed = True
        return result
    finally:
        if not committed:
            path.unlink(missing_ok=True)


def _source_bytes(con, evidence):
    import shared_artifacts
    provenance = evidence["provenance"]
    artifact_id = provenance.get("source_artifact_ref")
    cur = con.execute("SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=? AND kind='imported_document_source'", (artifact_id,))
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
    return raw, record


def reopen_imported_source(evidence_id: int, *, actor: Any, scope: Mapping) -> dict:
    context = authorize(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        evidence = _verified_evidence(con, evidence_id, context, actor)
        raw, record = _source_bytes(con, evidence)
    _check_effect(actor, scope, OperationType.DATA_EXPORT, "document-source-read:v1:" + record["sha256"])
    original = evidence["provenance"]["context"]
    authorize(actor, {k: original[k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}, action="read")
    return {"content":raw, "artifact_ref":record["artifact_id"], "sha256":record["sha256"],
            "size_bytes":record["size_bytes"], "filename":record["filename"],
            "source_id":evidence["asset_id"], "evidence_id":evidence_id,
            "source_origin":evidence["provenance"]["provenance"].get("source_origin"),
            "scope":{k: original[k] for k in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}}

def _result(con, source_id, evidence_id, parsed, scope, product, *, replayed):
    row = con.execute("SELECT canonical_id FROM canonical_data WHERE source_id=? AND product_id=?",
                      (source_id, product)).fetchone()
    if row is None:
        raise SavedWorkError("DOCUMENT_CANONICAL_MISSING")
    stored = con.execute("SELECT collection_metadata FROM app_evidence_records WHERE id=?",(evidence_id,)).fetchone()
    signed = json.loads(stored[0])
    return {"source_id": source_id, "evidence_id": evidence_id, "canonical_id": row[0],
            "source_artifact_ref":signed["source_artifact_ref"],
            "scope": dict(scope), "replayed": replayed, "metadata": dict(signed["parser"]),
            "locators": list(signed["locators"]), "scope_status": "UNASSIGNED" if scope["global_scope"] else "VERIFIED",
            "global_projection": "NOT_VERIFIED" if scope["global_scope"] else "NOT_APPLICABLE",
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
