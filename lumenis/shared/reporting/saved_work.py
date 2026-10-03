"""Versioned document outcomes using the existing Shared Artifact registry.

No schema, API composition, media rendering, AI or new storage owner lives here.
Each revision is an immutable JSON artifact. Writes serialize in the canonical
DB; retries identify the same request; a stale parent cannot overwrite work.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from typing import Any, Mapping

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store as evidence_store
from lumenis.system.security import permission
from lumenis.system.security.action_firewall import AgentAction
from lumenis.system.security.effect_fence import get_effect_fence

SCHEMA = "lumenis.saved-work/v1"
_KIND = "saved_document"
_TABLE = "lumenis_shared_artifacts"
_ID = re.compile(r"ART-[0-9a-f]{16}\Z")
_WORK = re.compile(r"WORK-[0-9a-f]{24}\Z")
_LIMIT = 8 * 1024 * 1024
_KINDS = {"research", "report", "podcast_episode", "delivery_preferences"}
_SCOPE_KEYS = ("domain_id", "subject_id", "brand_focus_id", "global_scope")


class SavedWorkError(ValueError):
    """Stable error codes for the Product Core adapter."""


def _json(value: Any) -> bytes:
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise SavedWorkError("WORK_JSON_INVALID") from exc
    if len(raw) > _LIMIT:
        raise SavedWorkError("WORK_TOO_LARGE")
    return raw


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def authorize(actor: Any, scope: Mapping[str, Any], *, action: str) -> dict:
    """Revalidate the existing server-issued principal and exact report scope."""
    keys = {"domain_id", "subject_id", "brand_focus_id", "global_scope"}
    if not isinstance(scope, Mapping) or set(scope) != keys:
        raise SavedWorkError("WORK_SCOPE_INVALID")
    domain = scope["domain_id"]
    if not isinstance(domain, str) or domain not in {"cth", "bmp", "zbmp"}:
        raise SavedWorkError("WORK_SCOPE_INVALID")
    normalized = {**scope, "domain_id": "zbmp" if domain in {"bmp", "zbmp"} else "cth"}
    checker = (permission.check_local_workspace_scope_permission
               if type(actor) is permission.LocalWorkspacePrincipal
               else permission.check_actor_scope_permission)
    decision = checker(actor, module="reports", action=action, **normalized)
    if decision.allowed is not True or decision.verification_state != "verified":
        raise SavedWorkError("WORK_PERMISSION_DENIED")
    identity = ({"principal_kind": actor.principal_kind, "principal_ref": actor.principal_ref}
                if type(actor) is permission.LocalWorkspacePrincipal
                else {"actor_id": actor.get("id")})
    return {**normalized, **identity}


def _check_effect(actor: Any, scope: Mapping, operation: Any, resource: str) -> dict:
    context = authorize(actor, scope, action="write" if operation != permission.OperationType.DATA_EXPORT else "read")
    if permission.is_testing_bypass_enabled():
        raise SavedWorkError("WORK_PERMISSION_UNVERIFIED")
    caller = context.get("principal_ref") or f"actor:{context['actor_id']}"
    result = permission.get_permission_gate().check(
        operation, resource=resource, caller=caller,
        domain_id="bmp" if context["domain_id"] == "zbmp" else "cth")
    if not result.allowed:
        raise SavedWorkError("WORK_EFFECT_PERMISSION_DENIED")
    return context


@contextmanager
def staging_write(resource: str):
    """Fence one admitted staging attempt; durable replay is checked in SQLite.

    The attempt ID is server-generated once, never retried after fence denial.
    It is distinct from the durable document operation/request ID: failed
    attempts may be explicitly retried, while committed operations cannot apply
    twice. No admission to Production Truth is granted by this fence.
    """
    fence = get_effect_fence()
    decision = fence.check(action=AgentAction.WRITE, target="shared-deliverable-staging",
                           payload={"effect_mode": "staging", "resource": resource},
                           operation_id="saved-work-attempt:" + uuid.uuid4().hex)
    if not decision.allowed:
        raise SavedWorkError("WORK_EFFECT_FENCE_DENIED")
    try:
        yield decision
    except BaseException:
        fence.complete(decision.idempotency_key, success=False)
        raise
    else:
        fence.complete(decision.idempotency_key, success=True)


def _stage_bytes(con, *, raw: bytes, context: dict, kind: str,
                 source_execution_id: str, evidence_id: str = "",
                 extension: str = ".json", media_type: str = "application/json"):
    """Stage bytes in the existing Artifact owner; caller owns commit/rollback.

    Atomic exclusive linking prevents a collision from replacing an existing
    immutable artifact. Unsupported storage semantics fail without fallback.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _LIMIT:
        raise SavedWorkError("WORK_TOO_LARGE")
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", extension):
        raise SavedWorkError("WORK_INPUT_INVALID")
    import shared_artifacts
    root = shared_artifacts.artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    artifact_id = "ART-" + uuid.uuid4().hex[:16]
    path = root / (artifact_id + extension)
    installed = False
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix=".saved-work-", delete=False) as handle:
            temp = handle.name
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        except FileExistsError as exc:
            raise SavedWorkError("WORK_ARTIFACT_COLLISION") from exc
        installed = True
        os.unlink(temp)
        temp = None
        if os.name != "nt":
            directory_fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        now = datetime.now(timezone.utc).isoformat()
        record = dict(artifact_id=artifact_id, kind=kind,
                      product_id="CTH" if context["domain_id"] == "cth" else "ZBMP",
                      domain_id=context["domain_id"], source_execution_id=source_execution_id,
                      evidence_id=str(evidence_id), note_id="", filename=path.name,
                      media_type=media_type, relative_path=path.name,
                      size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                      status="staged", approval_required=1, approval_status="pending",
                      created_at=now, updated_at=now)
        columns = tuple(record)
        con.execute(f"INSERT INTO {_TABLE} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                    tuple(record.values()))
        return record, path
    except BaseException:
        if installed:
            path.unlink(missing_ok=True)
        raise
    finally:
        if temp is not None:
            os.unlink(temp)


def _safe_payload(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = {"path", "local_path", "source_path", "absolute_path", "asset_path",
                     "file_path", "cookie", "cookies", "token", "api_key", "authorization"}
        if any(not isinstance(k, str) or k.casefold() in forbidden for k in value):
            raise SavedWorkError("WORK_PRIVATE_FIELD_FORBIDDEN")
        for item in value.values():
            _safe_payload(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _safe_payload(item)


def _validate_contract(contract: Any, payload: dict) -> dict:
    if contract is None:
        contract = {"id": "lumenis.saved-work", "version": "1", "required_payload_paths": []}
    if (not isinstance(contract, dict) or set(contract) != {"id", "version", "required_payload_paths"}
            or not all(isinstance(contract[k], str) and 0 < len(contract[k]) <= 200 for k in ("id", "version"))
            or not isinstance(contract["required_payload_paths"], list)
            or len(contract["required_payload_paths"]) > 100):
        raise SavedWorkError("WORK_CONTRACT_INVALID")
    for path in contract["required_payload_paths"]:
        if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,199}", path):
            raise SavedWorkError("WORK_CONTRACT_INVALID")
        value = payload
        for key in path.split("."):
            if not isinstance(value, dict) or key not in value:
                raise SavedWorkError("WORK_PAYLOAD_INCOMPLETE")
            value = value[key]
    return contract


def _verified_evidence(con, evidence_id: int, context: dict, actor: Any = None,
                       *, purpose: str = "quote_reference") -> dict:
    if type(evidence_id) is not int or evidence_id <= 0:
        raise SavedWorkError("WORK_EVIDENCE_INVALID")
    cur = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,))
    row = cur.fetchone()
    if row is None:
        raise SavedWorkError("WORK_EVIDENCE_MISSING")
    item = dict(zip((c[0] for c in cur.description), row))
    integrity = evidence_store.classify_evidence_integrity(item)
    try:
        inputs = json.loads(item["inputs_json"])
        provenance = json.loads(item["collection_metadata"])
    except (ValueError, TypeError) as exc:
        raise SavedWorkError("WORK_EVIDENCE_INVALID") from exc
    if not isinstance(inputs, dict) or not isinstance(provenance, dict):
        raise SavedWorkError("WORK_EVIDENCE_INVALID")
    source_context = provenance.get("context")
    if not isinstance(source_context, dict) or not all(k in source_context for k in _SCOPE_KEYS):
        raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    source_scope = {k: source_context[k] for k in _SCOPE_KEYS}
    source_provenance = provenance.get("provenance")
    # A scoped work may cite a general proposed method, preserving its original
    # GLOBAL scope and explicit purpose. This never transfers another entity's
    # facts or authorizes publication/training. Both scopes are still checked by
    # the existing Permission owner; the exact use is bound into write approval.
    method_reference = False
    if purpose == "method_reference":
        from lumenis.importer.documents import source_boundaries
        if isinstance(source_provenance, dict):
            origin = source_boundaries(source_provenance)["content_origin"]
            method_reference = (origin["kind"] == "researcher-note" and origin["claim_type"] == "method_proposal"
                                and source_provenance.get("rights") == "owner-approved"
                                and source_provenance.get("intended_use", "research_reference") == "research_reference")
        if not method_reference:
            raise SavedWorkError("WORK_METHOD_REFERENCE_INVALID")
    elif purpose != "quote_reference":
        raise SavedWorkError("WORK_CITATION_PURPOSE_INVALID")
    owner = {k: v for k, v in context.items() if k not in _SCOPE_KEYS}
    if (source_context.get("domain_id") != context["domain_id"]
            or {k: v for k, v in source_context.items() if k not in _SCOPE_KEYS} != owner
            or (not context["global_scope"] and source_context != context
                and not (method_reference and source_context["global_scope"] is True))):
        raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    # GLOBAL never authorizes a focused source. Resolve its own scope afresh
    # through the canonical Permission owner for every use/read/export.
    if actor is not None:
        if authorize(actor, source_scope, action="read") != source_context:
            raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    elif source_context != context:
        raise SavedWorkError("WORK_SOURCE_AUTHORIZATION_REQUIRED")
    product = "CTH" if source_context["domain_id"] == "cth" else "ZBMP"
    expected = {"product_id": product, "domain_id": source_context["domain_id"],
                "global": source_context["global_scope"]}
    if not source_context["global_scope"]:
        key = "subject_id" if product == "CTH" else "brand_focus_id"
        expected[key] = source_context[key]
    if (integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated"
            or item.get("result") != "PASS" or item.get("status") != "verified"
            or inputs.get("_lumenis_scope") != expected
            or provenance.get("owner") != owner):
        raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    # Shared Evidence signs collection_metadata and hashes raw_content; its
    # established schema does not contain a raw_content column. Retain the
    # parsed text inside that signed metadata instead of adding a schema owner.
    text = provenance.get("parsed_text")
    if not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != item.get("content_hash"):
        raise SavedWorkError("WORK_EVIDENCE_INTEGRITY_FAILED")
    rights = source_provenance.get("rights") if isinstance(source_provenance, dict) else None
    if not isinstance(rights, str) or rights not in {"public-reference-only", "owner-approved"}:
        raise SavedWorkError("WORK_SOURCE_RIGHTS_UNVERIFIED")
    # The original approved input is retained by the same Artifact registry,
    # not just a claimed hash. Every citation/read/export verifies its bytes.
    from lumenis.importer.documents import _source_bytes, source_boundaries
    source_boundaries(source_provenance)
    _source_bytes(con, {**item, "provenance": provenance})
    return {**item, "raw_content": text, "provenance": provenance}


def _validate_citations(con, citations: list, context: dict, actor: Any = None) -> list:
    if not isinstance(citations, list) or len(citations) > 100:
        raise SavedWorkError("WORK_CITATIONS_INVALID")
    checked = []
    for citation in citations:
        required = {"evidence_id", "start", "end", "quote"}
        if not isinstance(citation, dict) or not required.issubset(citation) or set(citation) - required - {"source_scope", "purpose"}:
            raise SavedWorkError("WORK_CITATION_INVALID")
        purpose = citation.get("purpose", "quote_reference")
        if not isinstance(purpose, str) or purpose not in {"quote_reference", "method_reference"}:
            raise SavedWorkError("WORK_CITATION_PURPOSE_INVALID")
        evidence = _verified_evidence(con, citation["evidence_id"], context, actor, purpose=purpose)
        source_scope = {k: evidence["provenance"]["context"][k] for k in _SCOPE_KEYS}
        if "source_scope" in citation and citation["source_scope"] != source_scope:
            raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
        start, end = citation["start"], citation["end"]
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(evidence["raw_content"])
                or evidence["raw_content"][start:end] != citation["quote"]):
            raise SavedWorkError("WORK_CITATION_UNGROUNDED")
        checked.append({**citation, "source_scope": source_scope})
    return checked


def _read(con, artifact_id: str, context: dict, actor: Any = None, *, verify_sources: bool = True) -> dict:
    if not isinstance(artifact_id, str) or not _ID.fullmatch(artifact_id):
        raise SavedWorkError("WORK_NOT_FOUND")
    cur = con.execute(f"SELECT * FROM {_TABLE} WHERE artifact_id=? AND kind=?", (artifact_id, _KIND))
    row = cur.fetchone()
    if row is None:
        raise SavedWorkError("WORK_NOT_FOUND")
    record = dict(zip((c[0] for c in cur.description), row))
    import shared_artifacts
    root = shared_artifacts.artifact_root()
    path = (root / record["relative_path"]).resolve()
    if (not path.is_relative_to(root) or not path.is_file()
            or path.stat().st_size != record["size_bytes"] or not 0 < path.stat().st_size <= _LIMIT):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    with path.open("rb") as source:
        raw = source.read(_LIMIT + 1)
    if len(raw) != record["size_bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise SavedWorkError("WORK_INTEGRITY_FAILED") from exc
    if (not isinstance(document, dict) or document.get("schema") != SCHEMA
            or document.get("context") != context or document.get("work_id") != record["source_execution_id"]
            or document.get("kind") not in _KINDS or type(document.get("version")) is not int
            or document["version"] < 1 or record["domain_id"] != context["domain_id"]
            or record["product_id"] != ("CTH" if context["domain_id"] == "cth" else "ZBMP")):
        raise SavedWorkError("WORK_CONTEXT_MISMATCH")
    if (not all(isinstance(document.get(k), str) for k in ("title", "markdown", "request_id", "input_hash"))
            or not isinstance(document.get("contract"), dict) or _json(document) != raw):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    if (not isinstance(document.get("payload"), dict)
            or document.get("draft_digest") != _digest(document["payload"])):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    _validate_contract(document.get("contract"), document["payload"])
    if not isinstance(document.get("citations"), list):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    attachments = document.get("attachments", [])
    if not isinstance(attachments, list) or len(attachments) > 8:
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
    for binding in attachments:
        _read_attachment(con, binding, context, document["work_id"])
    if verify_sources:
        document["citations"] = _validate_citations(con, document["citations"], context, actor)
    return {"artifact": record, "document": document, "_content_bytes": raw,
            "return_ref": {"artifact_id": artifact_id, "work_id": document["work_id"],
                           "version": document["version"], "scope": {k: context[k] for k in
                           ("domain_id", "subject_id", "brand_focus_id", "global_scope")}}}


def _read_attachment(con, binding, context, work_id):
    import shared_artifacts
    if (not isinstance(binding, dict) or set(binding) != {"name", "artifact_id", "sha256", "size_bytes", "media_type"}
            or not isinstance(binding["artifact_id"], str) or not _ID.fullmatch(binding["artifact_id"])):
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
    row = con.execute(f"SELECT * FROM {_TABLE} WHERE artifact_id=?", (binding["artifact_id"],)).fetchone()
    if row is None:
        raise SavedWorkError("WORK_ATTACHMENT_MISSING")
    record = dict(row)
    if (record["kind"] != "saved_document_attachment" or record["domain_id"] != context["domain_id"]
            or record["product_id"] != ("CTH" if context["domain_id"] == "cth" else "ZBMP")
            or record["source_execution_id"] != work_id
            or record["relative_path"] != binding["artifact_id"] + ".docx"
            or any(record[k] != binding[k] for k in ("sha256", "size_bytes", "media_type"))):
        raise SavedWorkError("WORK_ATTACHMENT_INTEGRITY_FAILED")
    path = shared_artifacts.artifact_root() / record["relative_path"]
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _LIMIT:
        raise SavedWorkError("WORK_ATTACHMENT_INTEGRITY_FAILED")
    raw = path.read_bytes()
    if len(raw) != binding["size_bytes"] or hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        raise SavedWorkError("WORK_ATTACHMENT_INTEGRITY_FAILED")
    return raw


def _versions(con, work_id: str, context: dict, actor: Any = None) -> list:
    count = con.execute(f"SELECT COUNT(*) FROM {_TABLE} WHERE kind=? AND source_execution_id=?",
                        (_KIND, work_id)).fetchone()[0]
    if count > 1000:
        raise SavedWorkError("WORK_VERSION_SCAN_LIMIT")
    ids = con.execute(f"SELECT artifact_id FROM {_TABLE} WHERE kind=? AND source_execution_id=?",
                      (_KIND, work_id)).fetchall()
    # Historical parents prove immutable provenance, not a grant to display
    # their withdrawn source content. Only a requested/current revision's
    # sources are authorized. This permits repairing a work by removing a
    # withdrawn citation without returning or re-exporting its old bytes.
    versions = sorted((_read(con, row[0], context, actor, verify_sources=False) for row in ids), key=lambda r: r["document"]["version"])
    for index, version in enumerate(versions, 1):
        parent = versions[index - 2]["artifact"]["artifact_id"] if index > 1 else None
        parent_hash = versions[index - 2]["artifact"]["sha256"] if index > 1 else None
        if (version["document"]["version"] != index or version["document"].get("parent_artifact_id") != parent
                or version["document"].get("parent_sha256") != parent_hash):
            raise SavedWorkError("WORK_VERSION_CHAIN_INVALID")
    return versions


def work_write_resource(*, title: str, markdown: str, kind: str, payload: dict,
                        citations: list, request_id: str, work_id: str | None,
                        previous_artifact_id: str | None, actor: Any, scope: Mapping,
                        expected_draft_digest: str | None = None, contract: dict | None = None,
                        task_id: str | None = None, assertion_id: str | None = None) -> str:
    context = authorize(actor, scope, action="write")
    return "saved-work:v1:" + _digest({"context": context, "title": title, "markdown": markdown,
                                     "kind": kind, "payload": payload, "citations": citations,
                                     "request_id": request_id, "work_id": work_id,
                                     "parent_artifact_id": previous_artifact_id,
                                     "expected_draft_digest": expected_draft_digest,
                                     "contract": _validate_contract(contract, payload),
                                     "task_id": task_id, "assertion_id": assertion_id})


def save_work(*, title: str, markdown: str, kind: str, payload: dict,
              citations: list, request_id: str, actor: Any, scope: Mapping,
              work_id: str | None = None, previous_artifact_id: str | None = None,
              expected_draft_digest: str | None = None, contract: dict | None = None,
              task_id: str | None = None, assertion_id: str | None = None,
              before_commit=None, attachments: list | None = None) -> dict:
    """Save or revise an exact document; optional payload retains the W4 snapshot.

    PodcastPlan/script/original transcript/corrections/chapters/source refs/version/
    Timeline belong to W4 and pass through unchanged as JSON. This service does
    not validate editorial quality, render media, approve or publish anything.
    """
    if (not isinstance(title, str) or not title.strip() or len(title) > 300
            or not isinstance(markdown, str) or not markdown.strip() or not isinstance(kind, str) or kind not in _KINDS
            or not isinstance(payload, dict) or not isinstance(request_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id)):
        raise SavedWorkError("WORK_INPUT_INVALID")
    if work_id is not None and (not isinstance(work_id, str) or not _WORK.fullmatch(work_id)):
        raise SavedWorkError("WORK_ID_INVALID")
    if expected_draft_digest is not None and (not isinstance(expected_draft_digest, str)
                                             or not re.fullmatch(r"[0-9a-f]{64}", expected_draft_digest)):
        raise SavedWorkError("WORK_DRAFT_DIGEST_INVALID")
    if any(value is not None and (not isinstance(value, str) or not 0 < len(value) <= 128)
           for value in (task_id, assertion_id)):
        raise SavedWorkError("WORK_ASSERTION_INVALID")
    _safe_payload(payload)
    # These are server-owned execution outputs, never client file paths or
    # credentials. A binding may commit its existing Task row on this same
    # connection, serializing cancellation against the Artifact commit.
    if before_commit is not None and not callable(before_commit):
        raise SavedWorkError("WORK_COMMIT_CALLBACK_INVALID")
    attachment_bytes = []
    for item in attachments or []:
        if (not isinstance(item, dict) or set(item) != {"name", "content", "media_type"}
                or not isinstance(item["name"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}\.docx", item["name"])
                or item["media_type"] != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                or not isinstance(item["content"], bytes) or not 0 < len(item["content"]) <= _LIMIT):
            raise SavedWorkError("WORK_ATTACHMENT_INVALID")
        attachment_bytes.append(dict(item))
    if (len(attachment_bytes) > 8 or len({a["name"] for a in attachment_bytes}) != len(attachment_bytes)
            or sum(len(a["content"]) for a in attachment_bytes) > _LIMIT):
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
    # Detach mutable caller data before hashing, validation and persistence.
    payload, citations = json.loads(_json(payload)), json.loads(_json(citations))
    contract = json.loads(_json(_validate_contract(contract, payload)))
    if kind == "podcast_episode" and not contract["required_payload_paths"]:
        raise SavedWorkError("WORK_EPISODE_CONTRACT_REQUIRED")
    args = dict(title=title, markdown=markdown, kind=kind, payload=payload, citations=citations,
                request_id=request_id, work_id=work_id, previous_artifact_id=previous_artifact_id,
                expected_draft_digest=expected_draft_digest, contract=contract,
                task_id=task_id, assertion_id=assertion_id, actor=actor, scope=scope)
    resource = work_write_resource(**args)
    context = _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
    # Export admission does not replace the write scope check.
    authorize(actor, scope, action="write")
    assigned_work = work_id or "WORK-" + _digest({"context": context, "request_id": request_id})[:24]
    input_hash = _digest({k: v for k, v in args.items() if k not in {"actor", "scope"}})
    if attachment_bytes:
        input_hash = _digest({"request": input_hash, "attachments": [
            {"name": a["name"], "media_type": a["media_type"],
             "sha256": hashlib.sha256(a["content"]).hexdigest(), "size_bytes": len(a["content"])}
            for a in attachment_bytes]})
    # Schema is initialized by W6/the application, never implicitly migrated here.
    path = None
    committed = False
    attachment_paths = []
    with get_repository().connection() as con, ExitStack() as effects:
        con.execute("BEGIN IMMEDIATE")
        try:
            checked_citations = _validate_citations(con, citations, context, actor)
            versions = _versions(con, assigned_work, context, actor)
            for existing in versions:
                if existing["document"]["request_id"] == request_id:
                    if existing["document"]["input_hash"] != input_hash:
                        raise SavedWorkError("WORK_REQUEST_REUSE_CONFLICT")
                    con.rollback()
                    return {**reopen_work(existing["artifact"]["artifact_id"], actor=actor, scope=scope), "replayed": True}
            parent = versions[-1]["artifact"]["artifact_id"] if versions else None
            if previous_artifact_id != parent:
                raise SavedWorkError("WORK_REVISION_CONFLICT")
            prior_digest = versions[-1]["document"]["draft_digest"] if versions else None
            if (expected_draft_digest is not None and expected_draft_digest != prior_digest
                    or kind == "podcast_episode" and versions and expected_draft_digest is None):
                raise SavedWorkError("WORK_DRAFT_REVISION_CONFLICT")
            if versions and versions[-1]["document"]["kind"] != kind:
                raise SavedWorkError("WORK_KIND_CHANGE_FORBIDDEN")
            if versions and versions[-1]["document"]["contract"] != contract:
                raise SavedWorkError("WORK_CONTRACT_CHANGE_FORBIDDEN")
            effects.enter_context(staging_write(resource))
            document = {"schema": SCHEMA, "context": context, "work_id": assigned_work,
                        "version": len(versions) + 1, "parent_artifact_id": parent,
                        "parent_sha256": versions[-1]["artifact"]["sha256"] if versions else None,
                        "request_id": request_id, "input_hash": input_hash,
                        "draft_digest": _digest(payload), "contract": contract,
                        "task_id": task_id, "assertion_id": assertion_id,
                        "kind": kind, "title": title, "markdown": markdown,
                        "payload": payload, "citations": checked_citations,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "authorship": "user-supplied; source facts require citations"}
            if attachment_bytes:
                document["attachments"] = []
                for item in attachment_bytes:
                    attached, attached_path = _stage_bytes(
                        con, raw=item["content"], context=context, kind="saved_document_attachment",
                        source_execution_id=assigned_work, extension=".docx", media_type=item["media_type"])
                    attachment_paths.append(attached_path)
                    document["attachments"].append({"name": item["name"], "artifact_id": attached["artifact_id"],
                                                    "sha256": attached["sha256"], "size_bytes": attached["size_bytes"],
                                                    "media_type": attached["media_type"]})
            raw = _json(document)
            _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
            authorize(actor, scope, action="write")
            record, path = _stage_bytes(con, raw=raw, context=context, kind=_KIND,
                                        source_execution_id=assigned_work,
                                        evidence_id=str(citations[0]["evidence_id"]) if citations else "")
            artifact_id = record["artifact_id"]
            _read(con, artifact_id, context, actor)
            _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
            authorize(actor, scope, action="write")
            _validate_citations(con, checked_citations, context, actor)
            if before_commit is not None:
                before_commit(con, record, document)
            _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
            authorize(actor, scope, action="write")
            con.commit()
            committed = True
            # A receipt is issued only after an independent connection has
            # reopened the committed registry row and actual immutable bytes.
            return {**reopen_work(artifact_id, actor=actor, scope=scope), "replayed": False}
        except BaseException:
            con.rollback()
            raise
        finally:
            if path is not None and not committed:
                path.unlink(missing_ok=True)
            if not committed:
                for attached_path in attachment_paths:
                    attached_path.unlink(missing_ok=True)


def read_committed_work(artifact_id: str, *, actor: Any, scope: Mapping) -> dict:
    """Canonical server reader; never accepts a tool/model receipt as evidence."""
    context = authorize(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        result = _read(con, artifact_id, context, actor)
        child = result
        for _ in range(1000):
            doc = child["document"]
            parent = doc.get("parent_artifact_id")
            if doc["version"] == 1:
                if parent is not None or doc.get("parent_sha256") is not None:
                    raise SavedWorkError("WORK_VERSION_CHAIN_INVALID")
                break
            previous = _read(con, parent, context, actor, verify_sources=False)
            if (previous["document"]["version"] != doc["version"] - 1
                    or previous["document"]["work_id"] != doc["work_id"]
                    or previous["document"]["kind"] != doc["kind"]
                    or previous["document"]["contract"] != doc["contract"]
                    or previous["artifact"]["sha256"] != doc.get("parent_sha256")):
                raise SavedWorkError("WORK_VERSION_CHAIN_INVALID")
            child = previous
        else:
            raise SavedWorkError("WORK_VERSION_SCAN_LIMIT")
        from lumenis.importer.documents import source_boundaries
        sources = []
        for evidence_id in sorted({c["evidence_id"] for c in result["document"]["citations"]}):
            purposes = sorted({c.get("purpose", "quote_reference") for c in result["document"]["citations"]
                               if c["evidence_id"] == evidence_id})
            evidence = _verified_evidence(con, evidence_id, context, actor, purpose=purposes[0])
            provenance = evidence["provenance"]
            sources.append({"evidence_id": evidence_id,
                            "source_id": evidence["asset_id"], "evidence_version": evidence["version"],
                            "source_artifact_ref": provenance["source_artifact_ref"],
                            "scope": {k: provenance["context"][k] for k in _SCOPE_KEYS},
                            "source_url": provenance["source_url"],
                            "source_fingerprint": provenance["source_fingerprint"],
                            "parsed_text_sha256": evidence["content_hash"],
                            "rights": provenance["provenance"]["rights"],
                            "intended_use": provenance["provenance"].get("intended_use", "research_reference"),
                            "capture": provenance["provenance"].get("capture"),
                            "published_at": provenance["provenance"]["published_at"],
                            "captured_at": provenance["provenance"]["captured_at"],
                            "purposes": purposes,
                            **source_boundaries(provenance["provenance"])})
    authorize(actor, scope, action="read")
    for source in sources:
        authorize(actor, source["scope"], action="read")
    doc, record = result["document"], result["artifact"]
    receipt = {"schema": "lumenis.committed-saved-work/v1", "task_id": doc.get("task_id"),
               "assertion_id": doc.get("assertion_id"), "contract": doc["contract"],
               "scope": result["return_ref"]["scope"], "ref": artifact_id,
               "work_id": doc["work_id"], "version": doc["version"],
               "parent": {"ref": doc.get("parent_artifact_id"), "sha256": doc.get("parent_sha256")},
               "sha256": record["sha256"], "size_bytes": record["size_bytes"],
               "draft_digest": doc["draft_digest"], "sources": sources,
               "constraint_observations": {"committed_bytes_match": True, "parent_chain_verified": True,
                   "required_payload_paths_present": list(doc["contract"]["required_payload_paths"]),
                   "source_authorization": "fresh-per-source", "source_count": len(sources),
                   "factual_verification": "NOT_ESTABLISHED_BY_STORAGE",
                   "learning_admission": "NOT_ESTABLISHED_BY_STORAGE",
                   "training_eligible": False, "held_out": False,
                   "assertion_binding": "present" if doc.get("task_id") and doc.get("assertion_id") else "absent",
                   "media_lineage": "W4_W6_NOT_VERIFIED" if doc["kind"] == "podcast_episode" else "not_applicable"},
               "commit_state": "registry_committed_artifact_staged"}
    raw = result.pop("_content_bytes")
    # The final response boundary retains the exact target actor/scope.
    authorize(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        _validate_citations(con, result["document"]["citations"], context, actor)
    authorize(actor, scope, action="read")
    return {**result, "content": raw, "receipt": receipt}


def reopen_work(artifact_id: str, *, actor: Any, scope: Mapping) -> dict:
    result = read_committed_work(artifact_id, actor=actor, scope=scope)
    result.pop("content")
    return result


def search_work(*, actor: Any, scope: Mapping, query: str = "", limit: int = 30,
                cursor: str | None = None, kind: str | None = None) -> dict:
    """Bounded, newest-first search; return a continuation even across hidden rows."""
    context = authorize(actor, scope, action="read")
    if not isinstance(query, str) or len(query) > 200 or type(limit) is not int or not 1 <= limit <= 100:
        raise SavedWorkError("WORK_SEARCH_INVALID")
    if kind is not None and (not isinstance(kind, str) or kind not in _KINDS):
        raise SavedWorkError("WORK_SEARCH_INVALID")
    import shared_artifacts
    identity = _digest({"owner": "saved_work", "context": context, "query": query, "kind": kind})
    try:
        boundary_value = shared_artifacts._content_project_list_boundary(cursor, identity)
    except shared_artifacts.LocalArtifactError as exc:
        raise SavedWorkError("WORK_CURSOR_INVALID") from exc
    with get_repository().connection(read_only=True, wal=False) as con:
        params = [_KIND, context["domain_id"]]
        boundary = ""
        if boundary_value is not None:
            boundary = " AND (created_at<? OR (created_at=? AND artifact_id<?))"
            params.extend([boundary_value[0], boundary_value[0], boundary_value[1]])
        rows = con.execute(f"SELECT artifact_id,created_at FROM {_TABLE} WHERE kind=? AND domain_id=?" + boundary +
                           " ORDER BY created_at DESC,artifact_id DESC LIMIT 201", params).fetchall()
        results, unavailable_count = [], 0
        last_scanned = None
        consumed = 0
        for row in rows[:200]:
            consumed += 1
            last_scanned = {"artifact_id": row[0], "created_at": row[1]}
            try:
                item = _read(con, row[0], context, actor)
            except SavedWorkError as exc:
                if str(exc) == "WORK_CONTEXT_MISMATCH":
                    continue
                # A corrupt blob cannot prove its owner. Reveal neither its ID
                # nor its contents; report incomplete verification explicitly.
                unavailable_count += 1
                continue
            doc = item["document"]
            item.pop("_content_bytes")
            if (kind is None or doc["kind"] == kind) and query.casefold() in (doc["title"] + "\n" + doc["markdown"]).casefold():
                results.append(item)
            if len(results) == limit:
                break
    authorize(actor, scope, action="read")
    has_more = len(rows) > consumed
    return {"items": results, "unverified_candidates": unavailable_count, "has_more": has_more,
            "next_cursor": shared_artifacts._content_project_list_cursor(identity, last_scanned)
            if has_more else None, "verification_complete": unavailable_count == 0}


def export_work(artifact_id: str, *, actor: Any, scope: Mapping, format: str = "json") -> dict:
    if not isinstance(format, str) or format not in {"json", "md", "txt", "docx", "pdf", "xlsx"}:
        raise SavedWorkError("WORK_EXPORT_FORMAT_INVALID")
    item = read_committed_work(artifact_id, actor=actor, scope=scope)
    resource = "saved-work-export:v1:" + _digest({"id": artifact_id,
                                               "sha256": item["artifact"]["sha256"], "format": format})
    _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
    if format == "json":
        raw = item["content"]
    elif format in {"md", "txt"}:
        appendix = "\n\nSources (original scopes and rights):\n" + json.dumps(item["receipt"]["sources"], ensure_ascii=False, indent=2)
        raw = (item["document"]["markdown"] + appendix).encode("utf-8")
    else:
        try:
            from .word_pdf_export import ReportExporter
            raw = ReportExporter.export_saved_document(item["document"], sources=item["receipt"]["sources"], format=format)
        except ImportError as exc:
            raise SavedWorkError("WORK_EXPORT_DEPENDENCY_UNAVAILABLE") from exc
    # Recheck after conversion, including each original source scope. A changed
    # or revoked source cannot produce a successful export response.
    read_committed_work(artifact_id, actor=actor, scope=scope)
    _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
    types = {"json": "application/json", "md": "text/markdown; charset=utf-8", "txt": "text/plain; charset=utf-8",
             "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "pdf": "application/pdf", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    return {"content": raw, "filename": artifact_id + "." + format,
            "media_type": types[format],
            "sha256": hashlib.sha256(raw).hexdigest(), "return_ref": item["return_ref"]}
