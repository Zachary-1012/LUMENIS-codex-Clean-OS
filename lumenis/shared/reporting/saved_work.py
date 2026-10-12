"""Versioned document outcomes using the existing Shared Artifact registry.

No schema, API composition, media rendering, AI or new storage owner lives here.
Each revision is an immutable JSON artifact. Writes serialize in the canonical
DB; retries identify the same request; a stale parent cannot overwrite work.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import tempfile
import uuid
import zipfile
import xml.etree.ElementTree as ET
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
_MAX_OOXML_ENTRIES = 4096
_MAX_OOXML_MEMBER_BYTES = 8 * 1024 * 1024
_MAX_OOXML_TOTAL_BYTES = 64 * 1024 * 1024
_MAX_OOXML_METADATA_BYTES = 2 * 1024 * 1024
_ATTACHMENT_NAME = re.compile(r"[A-Za-z0-9_-]{1,80}\.(docx|xlsx|pptx)\Z")
_OFFICE_FORMATS = {
    "docx": {
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "main_part": "word/document.xml",
        "main_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        "main_root": "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document",
    },
    "xlsx": {
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "main_part": "xl/workbook.xml",
        "main_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        "main_root": "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbook",
    },
    "pptx": {
        "media_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "main_part": "ppt/presentation.xml",
        "main_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
        "main_root": "{http://schemas.openxmlformats.org/presentationml/2006/main}presentation",
    },
}
_KINDS = {"research", "report", "podcast_episode", "delivery_preferences"}
_SCOPE_KEYS = ("domain_id", "subject_id", "brand_focus_id", "global_scope")
_SHARED_SCOPE_KEYS = ("scope_kind", "version")
_SHARED_SCOPE_KIND = "shared_workspace"
_SHARED_SCOPE_VERSION = 1


class SavedWorkError(ValueError):
    """Stable error codes for the Product Core adapter."""


class SavedWorkCommittedReadbackError(SavedWorkError):
    """The write committed, but its content cannot currently be returned."""

    def __init__(self, commit_status: dict):
        super().__init__("WORK_COMMITTED_REOPEN_UNAVAILABLE")
        self.commit_status = commit_status


def _attachment_spec(name: Any, media_type: Any) -> dict | None:
    """Return the exact supported OOXML format for a safe basename/MIME pair."""
    if not isinstance(name, str):
        return None
    match = _ATTACHMENT_NAME.fullmatch(name)
    if match is None:
        return None
    extension = match.group(1)
    spec = _OFFICE_FORMATS[extension]
    if media_type != spec["media_type"]:
        return None
    return {"extension": "." + extension, **spec}


def _validated_attachment_inputs(attachments: Any) -> tuple[list[dict], list[dict]]:
    """Detach and validate attachments before they bind permissions or request identity."""
    if attachments is None:
        items = []
    elif isinstance(attachments, (list, tuple)):
        items = list(attachments)
    else:
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
    if len(items) > 8:
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")

    normalized, manifest = [], []
    names = set()
    total_bytes = 0
    for item in items:
        if not isinstance(item, dict) or set(item) != {"name", "content", "media_type"}:
            raise SavedWorkError("WORK_ATTACHMENT_INVALID")
        spec = _attachment_spec(item["name"], item["media_type"])
        content = item["content"]
        if (spec is None or not isinstance(content, bytes)
                or not 0 < len(content) <= _LIMIT or item["name"] in names):
            raise SavedWorkError("WORK_ATTACHMENT_INVALID")
        total_bytes += len(content)
        if total_bytes > _LIMIT or not _valid_ooxml_attachment(content, spec):
            raise SavedWorkError("WORK_ATTACHMENT_INVALID")
        names.add(item["name"])
        normalized.append({"name": item["name"], "content": content, "media_type": item["media_type"]})
        manifest.append({"name": item["name"], "media_type": item["media_type"],
                         "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
    return normalized, manifest


def _read_ooxml_xml(archive: zipfile.ZipFile, name: str, maximum: int):
    """Read a bounded UTF-8 XML member without permitting DTD/entity expansion."""
    info = archive.getinfo(name)
    if info.is_dir() or not 0 < info.file_size <= maximum:
        raise ValueError("invalid OOXML XML part size")
    raw = archive.read(info)
    if len(raw) != info.file_size:
        raise ValueError("truncated OOXML XML part")
    # OOXML package XML is UTF-8; rejecting alternate encodings prevents DTD
    # declarations from evading the explicit entity prohibition below.
    text = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in text:
        raise ValueError("NUL bytes and non-UTF-8 XML encodings are not accepted")
    upper = text.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise ValueError("DTD and entity declarations are not accepted")
    return ET.fromstring(text)


def _has_zip_envelope(raw: bytes) -> bool:
    """Require an OOXML ZIP stream without a prepended stub or trailing payload."""
    if not raw.startswith(b"PK\x03\x04"):
        return False
    signature = b"PK\x05\x06"
    lower = max(0, len(raw) - (22 + 0xFFFF))
    cursor = len(raw)
    while True:
        offset = raw.rfind(signature, lower, cursor)
        if offset < 0:
            return False
        if offset + 22 <= len(raw):
            comment_size = int.from_bytes(raw[offset + 20:offset + 22], "little")
            if offset + 22 + comment_size == len(raw):
                return True
        cursor = offset


def _valid_ooxml_attachment(raw: bytes, spec: Mapping[str, Any]) -> bool:
    """Validate a bounded, exact-format OOXML ZIP package without extracting it."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _LIMIT or not _has_zip_envelope(raw):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            if not 3 <= len(infos) <= _MAX_OOXML_ENTRIES:
                return False
            members = {}
            total_uncompressed = 0
            for info in infos:
                name = info.filename
                path_name = name[:-1] if name.endswith("/") else name
                if (not path_name or name.startswith("/") or "\\" in name or ":" in name
                        or "\x00" in name
                        or any(part in {"", ".", ".."} for part in path_name.split("/"))
                        or name in members or info.flag_bits & (0x1 | 0x40)
                        or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or info.file_size < 0 or info.compress_size < 0
                        or info.file_size > _MAX_OOXML_MEMBER_BYTES
                        or stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)):
                    return False
                if info.is_dir() and info.file_size != 0:
                    return False
                total_uncompressed += info.file_size
                if total_uncompressed > _MAX_OOXML_TOTAL_BYTES:
                    return False
                members[name] = info

            main_part = spec["main_part"]
            required = ("[Content_Types].xml", "_rels/.rels", main_part)
            if any(name not in members for name in required):
                return False
            # Check every member's CRC and actual size, within the declared caps.
            if archive.testzip() is not None:
                return False

            package_ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
            types = _read_ooxml_xml(archive, "[Content_Types].xml", _MAX_OOXML_METADATA_BYTES)
            if types.tag != package_ns + "Types":
                return False
            overrides = [node for node in types.findall(package_ns + "Override")
                         if node.attrib.get("PartName") == "/" + main_part]
            if len(overrides) != 1 or overrides[0].attrib.get("ContentType") != spec["main_type"]:
                return False

            rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
            relationships = _read_ooxml_xml(archive, "_rels/.rels", _MAX_OOXML_METADATA_BYTES)
            if relationships.tag != rel_ns + "Relationships":
                return False
            office_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
            office_rels = [node for node in relationships.findall(rel_ns + "Relationship")
                           if node.attrib.get("Type") == office_type]
            if (len(office_rels) != 1
                    or office_rels[0].attrib.get("Target") not in {main_part, "/" + main_part}
                    or office_rels[0].attrib.get("TargetMode") == "External"):
                return False

            main = _read_ooxml_xml(archive, main_part, _MAX_OOXML_MEMBER_BYTES)
            if main.tag != spec["main_root"]:
                return False
            # Inspect every XML and relationship member for unsafe declarations
            # and malformed XML, not only the package manifest and main part.
            for name in members:
                if name.casefold().endswith((".xml", ".rels")) and name not in required:
                    _read_ooxml_xml(archive, name, _MAX_OOXML_MEMBER_BYTES)
            return True
    except Exception:
        # Parser failures on untrusted bytes become a stable invalid-input result.
        return False


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


def authorize(actor: Any, scope: Mapping[str, Any], *, action: str, connection=None) -> dict:
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
    connection_options = {} if connection is None else {"connection": connection}
    decision = checker(actor, module="reports", action=action, **normalized, **connection_options)
    if decision.allowed is not True or decision.verification_state != "verified":
        raise SavedWorkError("WORK_PERMISSION_DENIED")
    identity = ({"principal_kind": actor.principal_kind, "principal_ref": actor.principal_ref}
                if type(actor) is permission.LocalWorkspacePrincipal
                else {"actor_id": actor.get("id")})
    return {**normalized, **identity}


def _shared_scope_requested(scope: Any) -> bool:
    """Recognize only the typed client arm; legacy Scope4 stays unchanged."""
    return type(scope) is dict and any(key in scope for key in _SHARED_SCOPE_KEYS)


def authorize_saved_work(actor: Any, scope: Mapping[str, Any], *, action: str, connection=None) -> dict:
    """Authorize this SavedWork container through its existing Permission owner."""
    if not _shared_scope_requested(scope):
        return authorize(actor, scope, action=action, connection=connection)
    try:
        return permission.authorize_shared_workspace(
            actor, scope, module="reports", action=action, connection=connection,
        )
    except ValueError as exc:
        raise SavedWorkError("WORK_SCOPE_INVALID") from exc
    except PermissionError as exc:
        raise SavedWorkError("WORK_PERMISSION_DENIED") from exc


def _shared_context(context: Any) -> bool:
    """Validate the exact server result shape without accepting client identity."""
    if not isinstance(context, dict) or not any(key in context for key in _SHARED_SCOPE_KEYS):
        return False
    if (context.get("scope_kind") != _SHARED_SCOPE_KIND
            or type(context.get("version")) is not int
            or context["version"] != _SHARED_SCOPE_VERSION):
        raise SavedWorkError("WORK_CONTEXT_MISMATCH")
    keys = set(context)
    if (keys == set(_SHARED_SCOPE_KEYS) | {"actor_id"}
            and type(context["actor_id"]) is int and context["actor_id"] > 0):
        return True
    if (keys == set(_SHARED_SCOPE_KEYS) | {"principal_kind", "principal_ref"}
            and isinstance(context["principal_kind"], str) and context["principal_kind"]
            and isinstance(context["principal_ref"], str) and context["principal_ref"]):
        return True
    raise SavedWorkError("WORK_CONTEXT_MISMATCH")


def _client_scope(context: dict) -> dict:
    if _shared_context(context):
        return {"scope_kind": _SHARED_SCOPE_KIND, "version": _SHARED_SCOPE_VERSION}
    if not all(key in context for key in _SCOPE_KEYS):
        raise SavedWorkError("WORK_CONTEXT_MISMATCH")
    return {key: context[key] for key in _SCOPE_KEYS}


def _context_owner(context: dict) -> dict:
    if _shared_context(context):
        return {key: value for key, value in context.items() if key not in _SHARED_SCOPE_KEYS}
    return {key: value for key, value in context.items() if key not in _SCOPE_KEYS}


def _shared_context_matches_actor(context: dict, actor: Any) -> bool:
    if not _shared_context(context) or actor is None:
        return False
    if "actor_id" in context:
        actor_id = actor.get("id") if isinstance(actor, Mapping) else None
        return type(actor_id) is int and actor_id == context["actor_id"]
    return (type(actor) is permission.LocalWorkspacePrincipal
            and actor.principal_kind == context["principal_kind"]
            and actor.principal_ref == context["principal_ref"])


def _artifact_product_domain(context: dict, *, kind: str) -> tuple[str, str]:
    if _shared_context(context):
        if kind not in {_KIND, "saved_document_attachment"}:
            raise SavedWorkError("WORK_SCOPE_INVALID")
        return "SHARED", "content"
    domain = context.get("domain_id")
    if domain not in {"cth", "zbmp"}:
        raise SavedWorkError("WORK_CONTEXT_MISMATCH")
    return ("CTH" if domain == "cth" else "ZBMP"), domain


def _validate_contract_scope(context: dict, contract: dict) -> None:
    if (_shared_context(context)
            and contract.get("id") == "lumenis.cth-bmp-business-result"):
        raise SavedWorkError("WORK_SCOPE_INVALID")


def _check_effect(actor: Any, scope: Mapping, operation: Any, resource: str, *, connection=None) -> dict:
    action = "write" if operation != permission.OperationType.DATA_EXPORT else "read"
    context = authorize_saved_work(actor, scope, action=action, connection=connection)
    if permission.is_testing_bypass_enabled():
        raise SavedWorkError("WORK_PERMISSION_UNVERIFIED")
    if _shared_context(context):
        result = permission.check_shared_workspace_effect(
            actor, scope, operation, resource, module="reports", action=action,
            connection=connection,
        )
        if getattr(result, "allowed", False) is not True:
            raise SavedWorkError("WORK_EFFECT_PERMISSION_DENIED")
        return context
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
    product_id, domain_id = _artifact_product_domain(context, kind=kind)
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
                      product_id=product_id, domain_id=domain_id,
                      source_execution_id=source_execution_id,
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


_APPROVED_SOURCE_USE_MARKER_FIELDS = {
    "receipt_id", "source_id", "source_url", "domain_id", "subject_id", "brand_focus_id",
    "scope_evidence_ref", "content_evidence_ref", "body_sha256", "allowed_purposes",
    "allowed_operations", "rights_state", "commercial_state", "publication_state", "training_state",
}
_APPROVED_SOURCE_PARENT_FIELDS = {
    "receipt_id", "source_id", "source_url", "domain_id", "subject_id", "brand_focus_id",
    "scope_evidence_ref", "source_content_locator", "derived_content_evidence_ref",
    "body_sha256", "snapshot_kind",
}
_APPROVED_SOURCE_USE_PURPOSES = {"internal_research", "short_quote", "cth_brief", "bmp_brief"}
_APPROVED_SOURCE_USE_OPERATIONS = {"read", "save", "revise", "reopen"}


def _validate_current_approved_source_use(con, item: dict, provenance: dict, source_provenance: dict,
                                         context: dict, *, purpose: str, operation: str,
                                         source_binding: Mapping | None = None) -> bool:
    """Revalidate an exact PO use receipt without changing the source rights state."""
    marker = source_provenance.get("approved_internal_source_use")
    if marker is None:
        return False
    if not isinstance(marker, dict) or set(marker) != _APPROVED_SOURCE_USE_MARKER_FIELDS:
        raise SavedWorkError("SOURCE_USE_APPROVAL_RECEIPT_INVALID")
    if context.get("domain_id") == "cth":
        expected_purposes = {"internal_research", "short_quote", "cth_brief"}
    elif context.get("domain_id") == "zbmp":
        expected_purposes = {"internal_research", "short_quote", "bmp_brief"}
    else:
        raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH")
    allowed_purposes = marker.get("allowed_purposes")
    allowed_operations = marker.get("allowed_operations")
    if (not isinstance(allowed_purposes, list)
            or not all(isinstance(value, str) for value in allowed_purposes)
            or len(allowed_purposes) != len(set(allowed_purposes))
            or set(allowed_purposes) != expected_purposes
            or not isinstance(allowed_operations, list)
            or not all(isinstance(value, str) for value in allowed_operations)
            or len(allowed_operations) != len(set(allowed_operations))
            or set(allowed_operations) != _APPROVED_SOURCE_USE_OPERATIONS):
        raise SavedWorkError("SOURCE_USE_APPROVAL_RECEIPT_INVALID")
    if purpose not in _APPROVED_SOURCE_USE_PURPOSES or purpose not in marker["allowed_purposes"]:
        raise SavedWorkError("SOURCE_USE_PURPOSE_NOT_ALLOWED")
    if operation not in _APPROVED_SOURCE_USE_OPERATIONS or operation not in marker["allowed_operations"]:
        raise SavedWorkError("SOURCE_USE_PURPOSE_NOT_ALLOWED")

    rights = source_provenance.get("rights")
    if (rights not in {"UNKNOWN", "UNREVIEWED"} or marker.get("rights_state") != rights
            or marker.get("commercial_state") != "UNKNOWN"
            or marker.get("publication_state") != "NOT_APPROVED"
            or marker.get("training_state") != "NOT_APPROVED"):
        raise SavedWorkError("SOURCE_USE_APPROVAL_RECEIPT_INVALID")

    from lumenis.importer.documents import _APPROVED_SOURCE_REFERENCE_FEATURE

    derived_reference = item.get("feature_id") == _APPROVED_SOURCE_REFERENCE_FEATURE
    source_id = marker.get("source_id") if derived_reference else item.get("asset_id")
    source_url = source_provenance.get("source_url")
    source_context = provenance.get("context")
    if (not isinstance(source_id, str) or not source_id
            or not isinstance(source_url, str) or not source_url
            or not isinstance(source_context, dict)
            or marker.get("source_id") != source_id
            or marker.get("source_url") != source_url
            or marker.get("domain_id") != source_context.get("domain_id")
            or marker.get("domain_id") != context.get("domain_id")
            or marker.get("subject_id") != source_context.get("subject_id")
            or marker.get("brand_focus_id") != source_context.get("brand_focus_id")):
        raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH")

    try:
        import canonical_data
        from lumenis.shared.reporting.operational_brief import _source_level_record
        product_id = "CTH" if context["domain_id"] == "cth" else "ZBMP"
        current = canonical_data.list_scoped_canonical(
            con, product_id=product_id,
            subject_id=context["subject_id"] if context["domain_id"] == "cth" else None,
            brand_focus_id=context["brand_focus_id"] if context["domain_id"] == "zbmp" else None,
            source_ids=[source_id], source_level=True, limit=100,
        )
        row = _source_level_record(current.get("records", []))
    except (TypeError, ValueError, KeyError) as exc:
        raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH") from exc
    if (not isinstance(row, dict) or row.get("source_id") != source_id
            or row.get("domain_id") != context.get("domain_id")
            or (row.get("subject_id") or None) != context.get("subject_id")
            or (row.get("brand_focus_id") or None) != context.get("brand_focus_id")):
        raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH")

    scope_evidence_ref = str(row.get("scope_evidence_ref") or "")
    canonical_scope_locator = (f"app_evidence_records:{scope_evidence_ref}"
                               if re.fullmatch(r"[1-9][0-9]*", scope_evidence_ref) else None)
    raw_ref = row.get("raw_ref")
    if isinstance(raw_ref, str):
        try:
            raw_ref = json.loads(raw_ref)
        except (TypeError, ValueError):
            raw_ref = None
    if not isinstance(raw_ref, dict):
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")

    source_scope_locator = None
    if isinstance(raw_ref, dict) and raw_ref.get("table") == "notes":
        note_id, row_id = raw_ref.get("note_id"), raw_ref.get("id")
        if (note_id != source_id or type(row_id) is not int or row_id <= 0):
            raise SavedWorkError("SOURCE_USE_SCOPE_MISMATCH")
        source_scope_locator = f"notes:{row_id}"

    parent_binding = raw_ref.get("approved_internal_source_use")
    if (not isinstance(parent_binding, dict)
            or set(parent_binding) != _APPROVED_SOURCE_PARENT_FIELDS):
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
    raw_content_locator = raw_ref.get("content_evidence_ref")
    if source_scope_locator is not None:
        source_content_locator = source_scope_locator
        expected_snapshot_kind = "existing_canonical_content_snapshot_not_native_capture"
        if (context.get("domain_id") != "cth"
                or parent_binding.get("scope_evidence_ref") != source_scope_locator
                or parent_binding.get("source_content_locator") != source_content_locator):
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
    else:
        if (canonical_scope_locator is None
                or not isinstance(raw_content_locator, str)
                or not re.fullmatch(r"app_evidence_records:[1-9][0-9]*", raw_content_locator)):
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")
        source_content_locator = raw_content_locator
        expected_snapshot_kind = "existing_source_evidence_snapshot"
        if (parent_binding.get("scope_evidence_ref") != canonical_scope_locator
                or parent_binding.get("source_content_locator") != source_content_locator):
            raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_INVALID")

    body = row.get("content")
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest() if isinstance(body, str) else None
    current_url = row.get("url") or row.get("canonical_url")
    content_evidence_id = item.get("id")
    if type(content_evidence_id) is not int or content_evidence_id <= 0:
        raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")
    content_evidence_ref = f"app_evidence_records:{content_evidence_id}"
    expected_parent_binding = {
        "receipt_id": marker.get("receipt_id"),
        "source_id": source_id,
        "source_url": current_url,
        "domain_id": row.get("domain_id"),
        "subject_id": row.get("subject_id") or None,
        "brand_focus_id": row.get("brand_focus_id") or None,
        "scope_evidence_ref": parent_binding.get("scope_evidence_ref"),
        "source_content_locator": source_content_locator,
        "derived_content_evidence_ref": content_evidence_ref,
        "body_sha256": body_sha256,
        "snapshot_kind": expected_snapshot_kind,
    }
    if parent_binding != expected_parent_binding:
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_CHANGED")

    provenance_parent = provenance.get("source_reference_parent")
    nested_parent = source_provenance.get("source_reference_parent")
    if provenance_parent != parent_binding or nested_parent != parent_binding:
        raise SavedWorkError("SOURCE_USE_SOURCE_REFERENCE_CHANGED")

    native_binding = source_provenance.get("native_source_binding")
    if (canonical_scope_locator is not None
            and isinstance(native_binding, dict)
            and native_binding.get("collection_evidence_ref") != canonical_scope_locator):
        raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")
    if (canonical_scope_locator is not None
            and source_provenance.get("source_kind") == "collected_source"
            and not isinstance(native_binding, dict)):
        raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")
    if (marker.get("scope_evidence_ref") != parent_binding.get("scope_evidence_ref")
            or marker.get("content_evidence_ref") != content_evidence_ref
            or parent_binding.get("derived_content_evidence_ref") != content_evidence_ref
            or not isinstance(body, str) or not body
            or body != provenance.get("parsed_text")
            or hashlib.sha256(body.encode("utf-8")).hexdigest() != item.get("content_hash")
            or marker.get("body_sha256") != body_sha256
            or marker.get("source_url") != current_url
            or provenance.get("source_url") != current_url
            or (not derived_reference and item.get("asset_id") != source_id)
            or parent_binding.get("receipt_id") != marker.get("receipt_id")
            or parent_binding.get("source_id") != source_id
            or parent_binding.get("source_url") != current_url
            or parent_binding.get("domain_id") != row.get("domain_id")
            or parent_binding.get("subject_id") != (row.get("subject_id") or None)
            or parent_binding.get("brand_focus_id") != (row.get("brand_focus_id") or None)):
        raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")

    if source_binding is not None:
        expected_binding = {
            "source_id": source_id,
            "canonical_id": row.get("canonical_id"),
            "scope_evidence_ref": scope_evidence_ref,
            "content_evidence_ref": content_evidence_ref,
            "source_scope_locator": parent_binding["scope_evidence_ref"],
            "source_content_locator": source_content_locator,
            "evidence_id": content_evidence_id,
            "body_sha256": body_sha256,
        }
        if any(source_binding.get(key) != value for key, value in expected_binding.items()):
            raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")
    elif marker.get("domain_id") in {"cth", "zbmp"} and purpose in {"cth_brief", "bmp_brief"}:
        raise SavedWorkError("SOURCE_USE_CONTENT_MISMATCH")

    if derived_reference:
        from lumenis.importer.documents import resolve_approved_source_reference

        # The immutable child has its own asset identity. Resolve its original
        # Source through the existing importer, retaining both the parent bytes
        # and the exact Canonical-to-child binding on this transaction.
        resolved = resolve_approved_source_reference(
            con, source_id=source_id, canonical_id=row.get("canonical_id"),
            domain_id=row["domain_id"], subject_id=row.get("subject_id") or None,
            brand_focus_id=row.get("brand_focus_id") or None,
            source_content_locator=source_content_locator, body_sha256=body_sha256,
        )
        if (resolved.get("evidence_id") != content_evidence_id
                or resolved.get("source_reference_parent") != parent_binding):
            raise SavedWorkError("SOURCE_USE_DERIVED_EVIDENCE_INVALID")

    validator = getattr(permission, "validate_current_source_use", None)
    if not callable(validator):
        raise SavedWorkError("SOURCE_USE_APPROVAL_UNAVAILABLE")
    try:
        checked = validator(
            con, source_id=source_id, source_url=current_url, domain_id=row["domain_id"],
            subject_id=row.get("subject_id") or None, brand_focus_id=row.get("brand_focus_id") or None,
            scope_evidence_ref=parent_binding["scope_evidence_ref"],
            content_evidence_ref=source_content_locator,
            body_sha256=body_sha256, purpose=purpose, operation=operation, receipt_id=marker["receipt_id"],
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        if isinstance(code, str) and code.startswith("SOURCE_USE_"):
            raise SavedWorkError(code) from exc
        raise
    if not isinstance(checked, dict) or checked.get("rights_state") != rights:
        raise SavedWorkError("SOURCE_USE_APPROVAL_RECEIPT_INVALID")
    return True


def _verified_evidence(con, evidence_id: int, context: dict, actor: Any = None,
                       *, purpose: str = "quote_reference", source_use_purposes: tuple[str, ...] = (),
                       source_use_operation: str = "read", source_binding: Mapping | None = None) -> dict:
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
    shared_context = _shared_context(context)
    owner = _context_owner(context)
    if shared_context:
        if {k: v for k, v in source_context.items() if k not in _SCOPE_KEYS} != owner:
            raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    elif (source_context.get("domain_id") != context["domain_id"]
          or {k: v for k, v in source_context.items() if k not in _SCOPE_KEYS} != owner
          or (not context["global_scope"] and source_context != context
              and not (method_reference and source_context["global_scope"] is True))):
        raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    # Legacy GLOBAL never authorizes a focused source. Shared has no business
    # scope of its own, so each source uses its signed Scope4 below.
    # Resolve every source scope afresh for each use/read/export.
    if actor is not None:
        if authorize(actor, source_scope, action="read", connection=con) != source_context:
            raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
    elif shared_context or source_context != context:
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
    from lumenis.importer.documents import _source_bytes, source_boundaries
    source_boundaries(source_provenance)
    _source_bytes(con, {**item, "provenance": provenance})
    rights = source_provenance.get("rights") if isinstance(source_provenance, dict) else None
    approved_source_use = (isinstance(source_provenance, dict)
                           and source_provenance.get("approved_internal_source_use") is not None)
    if approved_source_use:
        if not source_use_purposes:
            raise SavedWorkError("SOURCE_USE_PURPOSE_NOT_ALLOWED")
        for use_purpose in source_use_purposes:
            _validate_current_approved_source_use(
                con, item, provenance, source_provenance if isinstance(source_provenance, dict) else {},
                source_context,
                purpose=use_purpose, operation=source_use_operation, source_binding=source_binding,
            )
    elif not isinstance(rights, str) or rights not in {"public-reference-only", "owner-approved"}:
        raise SavedWorkError("WORK_SOURCE_RIGHTS_UNVERIFIED")
    # The original approved input is retained by the same Artifact registry,
    # not just a claimed hash. Every citation/read/export verifies its bytes.
    source_id = item["asset_id"]
    if approved_source_use:
        from lumenis.importer.documents import _APPROVED_SOURCE_REFERENCE_FEATURE

        if item.get("feature_id") == _APPROVED_SOURCE_REFERENCE_FEATURE:
            source_id = source_provenance["approved_internal_source_use"]["source_id"]
    return {**item, "source_id": source_id, "raw_content": text, "provenance": provenance}


def _source_use_request(citation: dict, context: dict, contract: Mapping | None,
                        payload: dict | None) -> tuple[tuple[str, ...], Mapping | None]:
    contract_id = contract.get("id") if isinstance(contract, Mapping) else None
    source_binding = None
    if contract_id == "lumenis.cth-bmp-business-result":
        if _shared_context(context):
            raise SavedWorkError("WORK_SCOPE_INVALID")
        use_purpose = "cth_brief" if context.get("domain_id") == "cth" else "bmp_brief"
        business = payload.get("business_work") if isinstance(payload, dict) else None
        bindings = business.get("source_bindings") if isinstance(business, dict) else None
        if isinstance(bindings, list):
            matches = [binding for binding in bindings
                       if isinstance(binding, dict) and binding.get("evidence_id") == citation.get("evidence_id")]
            if len(matches) == 1:
                source_binding = matches[0]
    else:
        use_purpose = "internal_research"
    # A citation is a user-selected verbatim span. The Evidence offset check
    # below proves it is an exact substring of the approved source body.
    return (use_purpose, "short_quote"), source_binding


def _validate_citations(con, citations: list, context: dict, actor: Any = None, *,
                        source_use_operation: str = "read", contract: Mapping | None = None,
                        payload: dict | None = None) -> list:
    if not isinstance(citations, list) or len(citations) > 100:
        raise SavedWorkError("WORK_CITATIONS_INVALID")
    checked = []
    quote_text_by_source = {}
    for citation in citations:
        required = {"evidence_id", "start", "end", "quote"}
        if not isinstance(citation, dict) or not required.issubset(citation) or set(citation) - required - {"source_scope", "purpose"}:
            raise SavedWorkError("WORK_CITATION_INVALID")
        purpose = citation.get("purpose", "quote_reference")
        if not isinstance(purpose, str) or purpose not in {"quote_reference", "method_reference"}:
            raise SavedWorkError("WORK_CITATION_PURPOSE_INVALID")
        source_use_purposes, source_binding = _source_use_request(citation, context, contract, payload)
        evidence = _verified_evidence(
            con, citation["evidence_id"], context, actor, purpose=purpose,
            source_use_purposes=source_use_purposes, source_use_operation=source_use_operation,
            source_binding=source_binding,
        )
        source_scope = {k: evidence["provenance"]["context"][k] for k in _SCOPE_KEYS}
        if "source_scope" in citation and citation["source_scope"] != source_scope:
            raise SavedWorkError("WORK_EVIDENCE_CONTEXT_MISMATCH")
        start, end = citation["start"], citation["end"]
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(evidence["raw_content"])
                or evidence["raw_content"][start:end] != citation["quote"]):
            raise SavedWorkError("WORK_CITATION_UNGROUNDED")
        source_provenance = evidence["provenance"].get("provenance")
        marker = (source_provenance.get("approved_internal_source_use")
                  if isinstance(source_provenance, dict) else None)
        if marker is not None:
            if len(citation["quote"]) > 160:
                raise SavedWorkError("SOURCE_USE_QUOTE_LIMIT_EXCEEDED")
            key = (marker.get("source_id"), marker.get("content_evidence_ref"), marker.get("body_sha256"))
            quote_text_by_source.setdefault(key, set()).add(citation["quote"])
            if sum(map(len, quote_text_by_source[key])) > 160:
                raise SavedWorkError("SOURCE_USE_QUOTE_LIMIT_EXCEEDED")
        checked.append({**citation, "source_scope": source_scope})
    return checked


def _read(con, artifact_id: str, context: dict, actor: Any = None, *, verify_sources: bool = True,
          source_use_operation: str = "read") -> dict:
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
    product_id, domain_id = _artifact_product_domain(context, kind=_KIND)
    if (not isinstance(document, dict) or document.get("schema") != SCHEMA
            or document.get("context") != context or document.get("work_id") != record["source_execution_id"]
            or document.get("kind") not in _KINDS or type(document.get("version")) is not int
            or document["version"] < 1 or record["domain_id"] != domain_id
            or record["product_id"] != product_id):
        raise SavedWorkError("WORK_CONTEXT_MISMATCH")
    if (not all(isinstance(document.get(k), str) for k in ("title", "markdown", "request_id", "input_hash"))
            or not isinstance(document.get("contract"), dict) or _json(document) != raw):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    if (not isinstance(document.get("payload"), dict)
            or document.get("draft_digest") != _digest(document["payload"])):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    _validate_contract_scope(context, _validate_contract(document.get("contract"), document["payload"]))
    if not isinstance(document.get("citations"), list):
        raise SavedWorkError("WORK_INTEGRITY_FAILED")
    attachments = document.get("attachments", [])
    if not isinstance(attachments, list) or len(attachments) > 8:
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
    for binding in attachments:
        _read_attachment(con, binding, context, document["work_id"], actor=actor)
    if verify_sources:
        document["citations"] = _validate_citations(
            con, document["citations"], context, actor, source_use_operation=source_use_operation,
            contract=document["contract"], payload=document["payload"],
        )
    return {"artifact": record, "document": document, "_content_bytes": raw,
            "return_ref": {"artifact_id": artifact_id, "work_id": document["work_id"],
                           "version": document["version"], "scope": _client_scope(context)}}


def _read_attachment(con, binding, context, work_id, *, actor=None):
    import shared_artifacts
    if _shared_context(context) and not _shared_context_matches_actor(context, actor):
        raise SavedWorkError("WORK_CONTEXT_MISMATCH")
    if (not isinstance(binding, dict) or set(binding) != {"name", "artifact_id", "sha256", "size_bytes", "media_type"}
            or not isinstance(binding["artifact_id"], str) or not _ID.fullmatch(binding["artifact_id"])):
        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
    spec = _attachment_spec(binding["name"], binding["media_type"])
    if spec is None:
        raise SavedWorkError("WORK_ATTACHMENT_INTEGRITY_FAILED")
    row = con.execute(f"SELECT * FROM {_TABLE} WHERE artifact_id=?", (binding["artifact_id"],)).fetchone()
    if row is None:
        raise SavedWorkError("WORK_ATTACHMENT_MISSING")
    record = dict(row)
    product_id, domain_id = _artifact_product_domain(context, kind="saved_document_attachment")
    if (record["kind"] != "saved_document_attachment" or record["domain_id"] != domain_id
            or record["product_id"] != product_id
            or record["source_execution_id"] != work_id
            or record["relative_path"] != binding["artifact_id"] + spec["extension"]
            or any(record[k] != binding[k] for k in ("sha256", "size_bytes", "media_type"))):
        raise SavedWorkError("WORK_ATTACHMENT_INTEGRITY_FAILED")
    path = shared_artifacts.artifact_root() / record["relative_path"]
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _LIMIT:
        raise SavedWorkError("WORK_ATTACHMENT_INTEGRITY_FAILED")
    raw = path.read_bytes()
    if (len(raw) != binding["size_bytes"] or hashlib.sha256(raw).hexdigest() != binding["sha256"]
            or not _valid_ooxml_attachment(raw, spec)):
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
                        task_id: str | None = None, assertion_id: str | None = None,
                        attachments: list | None = None) -> str:
    context = authorize_saved_work(actor, scope, action="write")
    _, attachment_manifest = _validated_attachment_inputs(attachments)
    contract_value = _validate_contract(contract, payload)
    _validate_contract_scope(context, contract_value)
    resource = {"context": context, "title": title, "markdown": markdown,
                "kind": kind, "payload": payload, "citations": citations,
                "request_id": request_id, "work_id": work_id,
                "parent_artifact_id": previous_artifact_id,
                "expected_draft_digest": expected_draft_digest,
                "contract": contract_value,
                "task_id": task_id, "assertion_id": assertion_id}
    # Keep the historical no-attachment resource byte-for-byte stable.
    if attachment_manifest:
        resource["attachments"] = attachment_manifest
    return "saved-work:v1:" + _digest(resource)


def _reopen_saved_result(artifact_id: str, *, request_id: str, actor: Any,
                         scope: Mapping, context: dict, replayed: bool,
                         replay_resource: str | None = None) -> dict:
    """Keep commit knowledge separate from permission to return saved content."""
    try:
        if replayed:
            # An exact retry recognizes committed state before read/export
            # admission, but never returns content without the current fence.
            if not isinstance(replay_resource, str):
                raise SavedWorkError("WORK_READBACK_UNAVAILABLE")
            current_context = _check_effect(
                actor, scope, permission.OperationType.DATA_EXPORT, replay_resource,
            )
            if current_context != context:
                raise SavedWorkError("WORK_CONTEXT_MISMATCH")
        return {**reopen_work(artifact_id, actor=actor, scope=scope), "replayed": replayed}
    except Exception as exc:
        code = str(exc)
        if not re.fullmatch(r"(?:WORK|SOURCE_USE|SOURCE_REFERENCE)_[A-Z0-9_]+", code):
            code = "WORK_READBACK_UNAVAILABLE"
        status = {
            "schema": "lumenis.saved-work-commit-status/v1",
            "state": "committed_readback_unavailable",
            "request_id": request_id,
            "replayed": replayed,
            "readback_error_code": code,
            "result": None,
        }
        # This metadata is not a content receipt. Recheck the current container
        # owner and immutable bytes without exposing withdrawn source content.
        try:
            with get_repository().connection(read_only=True, wal=False) as con:
                current_context = authorize_saved_work(actor, scope, action="read", connection=con)
                if current_context != context:
                    raise SavedWorkError("WORK_CONTEXT_MISMATCH")
                item = _read(con, artifact_id, context, actor, verify_sources=False)
                doc, record = item["document"], item["artifact"]
                if doc["request_id"] != request_id:
                    raise SavedWorkError("WORK_REQUEST_REUSE_CONFLICT")
                if authorize_saved_work(actor, scope, action="read", connection=con) != context:
                    raise SavedWorkError("WORK_CONTEXT_MISMATCH")
                status["result"] = {
                    "artifact_id": record["artifact_id"],
                    "sha256": record["sha256"],
                    "work_id": doc["work_id"],
                    "version": doc["version"],
                    "draft_digest": doc["draft_digest"],
                    "scope": _client_scope(context),
                }
            # Do not release a pointer after a subsequent container revocation.
            if authorize_saved_work(actor, scope, action="read") != context:
                status["result"] = None
        except Exception:
            status["result"] = None
        raise SavedWorkCommittedReadbackError(status) from exc


def save_work(*, title: str, markdown: str, kind: str, payload: dict,
              citations: list, request_id: str, actor: Any, scope: Mapping,
              work_id: str | None = None, previous_artifact_id: str | None = None,
              expected_draft_digest: str | None = None, contract: dict | None = None,
              task_id: str | None = None, assertion_id: str | None = None,
              before_commit=None, attachments: list | None = None) -> dict:
    """Save or revise an exact document; optional payload retains the W4 snapshot.

    PodcastPlan/script/original transcript/corrections/chapters/source refs/version/
    Timeline belong to W4. A supplied ``podcast_plan`` is parsed through the
    existing podcast runtime before storage; legacy episode payloads remain
    readable. This service does not validate editorial quality, render media,
    approve or publish anything.
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
    attachment_bytes, attachment_manifest = _validated_attachment_inputs(attachments)
    # Detach mutable caller data before hashing, validation and persistence.
    payload, citations = json.loads(_json(payload)), json.loads(_json(citations))
    contract = json.loads(_json(_validate_contract(contract, payload)))
    if kind == "podcast_episode" and not contract["required_payload_paths"]:
        raise SavedWorkError("WORK_EPISODE_CONTRACT_REQUIRED")
    if kind == "podcast_episode" and "podcast_plan" in payload:
        try:
            from podcast.intelligence.episode_runtime import PodcastPlan

            PodcastPlan.from_dict(payload["podcast_plan"])
        except (TypeError, ValueError) as exc:
            raise SavedWorkError("WORK_PODCAST_PLAN_INVALID") from exc
    args = dict(title=title, markdown=markdown, kind=kind, payload=payload, citations=citations,
                request_id=request_id, work_id=work_id, previous_artifact_id=previous_artifact_id,
                expected_draft_digest=expected_draft_digest, contract=contract,
                task_id=task_id, assertion_id=assertion_id, actor=actor, scope=scope)
    resource = work_write_resource(**args, attachments=attachment_bytes)
    # Write admission permits immutable request matching; it grants no content
    # read or export. Exact retries still pass the current export fence below.
    context = authorize_saved_work(actor, scope, action="write")
    assigned_work = work_id or "WORK-" + _digest({"context": context, "request_id": request_id})[:24]
    input_hash = _digest({k: v for k, v in args.items() if k not in {"actor", "scope"}})
    if attachment_manifest:
        input_hash = _digest({"request": input_hash, "attachments": attachment_manifest})
    # Schema is initialized by W6/the application, never implicitly migrated here.
    path = None
    committed = False
    attachment_paths = []
    with get_repository().connection() as con, ExitStack() as effects:
        con.execute("BEGIN IMMEDIATE")
        try:
            source_use_operation = "revise" if previous_artifact_id is not None else "save"
            versions = _versions(con, assigned_work, context, actor)
            for existing in versions:
                if existing["document"]["request_id"] == request_id:
                    if existing["document"]["input_hash"] != input_hash:
                        raise SavedWorkError("WORK_REQUEST_REUSE_CONFLICT")
                    con.rollback()
                    return _reopen_saved_result(
                        existing["artifact"]["artifact_id"], request_id=request_id,
                        actor=actor, scope=scope, context=context, replayed=True,
                        replay_resource=resource,
                    )
            if _check_effect(
                actor, scope, permission.OperationType.DATA_EXPORT, resource, connection=con,
            ) != context:
                raise SavedWorkError("WORK_CONTEXT_MISMATCH")
            checked_citations = _validate_citations(
                con, citations, context, actor, source_use_operation=source_use_operation,
                contract=contract, payload=payload,
            )
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
                    spec = _attachment_spec(item["name"], item["media_type"])
                    if spec is None:
                        raise SavedWorkError("WORK_ATTACHMENT_INVALID")
                    attached, attached_path = _stage_bytes(
                        con, raw=item["content"], context=context, kind="saved_document_attachment",
                        source_execution_id=assigned_work, extension=spec["extension"], media_type=item["media_type"])
                    attachment_paths.append(attached_path)
                    document["attachments"].append({"name": item["name"], "artifact_id": attached["artifact_id"],
                                                    "sha256": attached["sha256"], "size_bytes": attached["size_bytes"],
                                                    "media_type": attached["media_type"]})
            raw = _json(document)
            _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
            authorize_saved_work(actor, scope, action="write")
            record, path = _stage_bytes(con, raw=raw, context=context, kind=_KIND,
                                        source_execution_id=assigned_work,
                                        evidence_id=str(citations[0]["evidence_id"]) if citations else "")
            artifact_id = record["artifact_id"]
            _read(con, artifact_id, context, actor, source_use_operation=source_use_operation)
            _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
            authorize_saved_work(actor, scope, action="write")
            _validate_citations(
                con, checked_citations, context, actor, source_use_operation=source_use_operation,
                contract=contract, payload=payload,
            )
            if before_commit is not None:
                before_commit(con, record, document)
            _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource, connection=con)
            authorize_saved_work(actor, scope, action="write", connection=con)
            _validate_citations(
                con, checked_citations, context, actor, source_use_operation=source_use_operation,
                contract=contract, payload=payload,
            )
            con.commit()
            committed = True
            # A receipt is issued only after an independent connection has
            # reopened the committed registry row and actual immutable bytes.
            return _reopen_saved_result(
                artifact_id, request_id=request_id, actor=actor, scope=scope,
                context=context, replayed=False,
            )
        except BaseException:
            con.rollback()
            raise
        finally:
            if path is not None and not committed:
                path.unlink(missing_ok=True)
            if not committed:
                for attached_path in attachment_paths:
                    attached_path.unlink(missing_ok=True)


def read_committed_work(artifact_id: str, *, actor: Any, scope: Mapping, connection=None,
                        _source_use_operation: str = "read") -> dict:
    """Canonical server reader; never accepts a tool/model receipt as evidence."""
    from contextlib import nullcontext
    if connection is not None:
        permission._require_canonical_scope_connection(connection)
    context = authorize_saved_work(actor, scope, action="read", connection=connection)
    committed_refs = []
    reader = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    with reader as con:
        result = _read(con, artifact_id, context, actor, source_use_operation=_source_use_operation)
        child = result
        for _ in range(1000):
            doc = child["document"]
            committed_refs.append(child["artifact"])
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
            citation = next(c for c in result["document"]["citations"] if c["evidence_id"] == evidence_id)
            source_use_purposes, source_binding = _source_use_request(
                citation, context, result["document"]["contract"], result["document"]["payload"])
            evidence = _verified_evidence(
                con, evidence_id, context, actor, purpose=purposes[0],
                source_use_purposes=source_use_purposes,
                source_use_operation=_source_use_operation, source_binding=source_binding,
            )
            provenance = evidence["provenance"]
            sources.append({"evidence_id": evidence_id,
                            "source_id": evidence["source_id"], "evidence_version": evidence["version"],
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
    if connection is not None:
        # Scope/rights checks use the caller's transaction. This separate view
        # proves only that immutable upstream rows were committed beforehand;
        # it can never authorize an otherwise denied or newly staged source.
        with get_repository().connection(read_only=True, wal=False) as committed:
            for artifact in committed_refs:
                row = committed.execute(f"SELECT sha256,size_bytes,source_execution_id,kind FROM {_TABLE} WHERE artifact_id=?",
                                        (artifact["artifact_id"],)).fetchone()
                if (row is None or row[0] != artifact["sha256"] or row[1] != artifact["size_bytes"]
                        or row[2] != artifact["source_execution_id"] or row[3] != _KIND):
                    raise SavedWorkError("WORK_NOT_COMMITTED")
    authorize_saved_work(actor, scope, action="read", connection=connection)
    for source in sources:
        authorize(actor, source["scope"], action="read", connection=connection)
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
    authorize_saved_work(actor, scope, action="read", connection=connection)
    reader = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    with reader as con:
        _validate_citations(
            con, result["document"]["citations"], context, actor,
            source_use_operation=_source_use_operation, contract=result["document"]["contract"],
            payload=result["document"]["payload"],
        )
    authorize_saved_work(actor, scope, action="read", connection=connection)
    return {**result, "content": raw, "receipt": receipt}


def reopen_work(artifact_id: str, *, actor: Any, scope: Mapping, connection=None) -> dict:
    options = {} if connection is None else {"connection": connection}
    result = read_committed_work(artifact_id, actor=actor, scope=scope,
                                 _source_use_operation="reopen", **options)
    result.pop("content")
    return result


def _revision_target(document: dict, pointer: str):
    if (not isinstance(pointer, str) or len(pointer) > 1000 or not pointer.startswith("/")
            or re.search(r"~(?![01])", pointer)):
        raise SavedWorkError("WORK_EDIT_POINTER_INVALID")
    tokens = tuple(token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/"))
    if tokens not in {("title",), ("markdown",)} and not (len(tokens) > 1 and tokens[0] == "payload"):
        raise SavedWorkError("WORK_EDIT_FIELD_FORBIDDEN")
    if tokens[:2] == ("payload", "revision_note"):
        raise SavedWorkError("WORK_EDIT_FIELD_FORBIDDEN")
    current = document
    for token in tokens[:-1]:
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(current):
            current = current[int(token)]
        else:
            raise SavedWorkError("WORK_EDIT_TARGET_NOT_FOUND")
    key = tokens[-1]
    if isinstance(current, list):
        if not re.fullmatch(r"0|[1-9][0-9]*", key) or int(key) >= len(current):
            raise SavedWorkError("WORK_EDIT_TARGET_NOT_FOUND")
        key = int(key)
    elif not isinstance(current, dict) or key not in current:
        raise SavedWorkError("WORK_EDIT_TARGET_NOT_FOUND")
    if isinstance(current[key], (dict, list)):
        raise SavedWorkError("WORK_EDIT_CONTAINER_REPLACEMENT_FORBIDDEN")
    return tokens, current, key


def _apply_work_edits(document: dict, edits: list) -> list:
    if not isinstance(edits, list) or not 1 <= len(edits) <= 100:
        raise SavedWorkError("WORK_EDITS_REQUIRED")
    grouped = {}
    for edit in edits:
        if not isinstance(edit, dict):
            raise SavedWorkError("WORK_EDIT_INVALID")
        fields = set(edit)
        if fields not in ({"pointer", "expected", "value"}, {"pointer", "start", "end", "expected", "replacement"}):
            raise SavedWorkError("WORK_EDIT_INVALID")
        tokens, target, key = _revision_target(document, edit["pointer"])
        value = target[key]
        if fields == {"pointer", "expected", "value"}:
            if tokens in grouped or isinstance(edit["value"], (dict, list)):
                raise SavedWorkError("WORK_EDIT_OVERLAP_OR_CONTAINER")
            if _json(value) != _json(edit["expected"]):
                raise SavedWorkError("WORK_EDIT_VALUE_CHANGED")
        else:
            if (not isinstance(value, str) or type(edit["start"]) is not int or type(edit["end"]) is not int
                    or not 0 <= edit["start"] <= edit["end"] <= len(value)
                    or not isinstance(edit["expected"], str) or not isinstance(edit["replacement"], str)):
                raise SavedWorkError("WORK_EDIT_RANGE_INVALID")
            if value[edit["start"]:edit["end"]] != edit["expected"]:
                raise SavedWorkError("WORK_EDIT_VALUE_CHANGED")
            if tokens in grouped and any("start" not in other for other in grouped[tokens]):
                raise SavedWorkError("WORK_EDIT_OVERLAP_OR_CONTAINER")
        grouped.setdefault(tokens, []).append(edit)
    for tokens, changes in grouped.items():
        _, target, key = _revision_target(document, changes[0]["pointer"])
        if "value" in changes[0]:
            target[key] = changes[0]["value"]
            continue
        ordered = sorted(changes, key=lambda item: (item["start"], item["end"]))
        for previous, current in zip(ordered, ordered[1:]):
            if previous["end"] > current["start"] or previous["start"] == current["start"]:
                raise SavedWorkError("WORK_EDIT_RANGES_OVERLAP")
        text = target[key]
        for edit in reversed(ordered):
            text = text[:edit["start"]] + edit["replacement"] + text[edit["end"]:]
        target[key] = text
    return edits


def revise_work(artifact_id: str, *, actor: Any, scope: Mapping, request_id: str,
                expected_sha256: str, reason: str, edits: list, citations: list | None = None,
                source_adoptions: list | None = None) -> dict:
    """Apply explicit local user edits to a current generic research/report owner.

    Creation and Task-owned contracts retain their dedicated revision service.
    Offsets are Unicode code points in the selected immutable parent string.
    """
    if (not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
            or not isinstance(reason, str) or not reason.strip() or len(reason) > 4000):
        raise SavedWorkError("WORK_REVISION_INPUT_INVALID")
    item = read_committed_work(artifact_id, actor=actor, scope=scope,
                               _source_use_operation="revise")
    if item["artifact"]["sha256"] != expected_sha256:
        raise SavedWorkError("WORK_REVISION_SOURCE_CHANGED")
    document = json.loads(_json(item["document"]))
    preserved_attachments = []
    attachment_bindings = document.get("attachments", [])
    if attachment_bindings:
        with get_repository().connection(read_only=True, wal=False) as con:
            for binding in attachment_bindings:
                preserved_attachments.append({
                    "name": binding["name"],
                    "media_type": binding["media_type"],
                    "content": _read_attachment(
                        con, binding, document["context"], document["work_id"], actor=actor,
                    ),
                })
    if (document["kind"] not in {"research", "report"} or document.get("task_id") is not None
            or document.get("assertion_id") is not None
            or document["contract"] != {"id": "lumenis.saved-work", "version": "1", "required_payload_paths": []}):
        raise SavedWorkError("WORK_REVISION_OWNER_REQUIRED")
    edits = json.loads(_json(edits))
    chosen_citations = document["citations"] if citations is None else json.loads(_json(citations))
    adoptions = json.loads(_json([] if source_adoptions is None else source_adoptions))
    if not isinstance(chosen_citations, list) or not isinstance(adoptions, list) or len(adoptions) > 100:
        raise SavedWorkError("WORK_SOURCE_ADOPTION_INVALID")
    old_ids = {citation["evidence_id"] for citation in document["citations"]}
    if any(not isinstance(citation, dict) or type(citation.get("evidence_id")) is not int
           or citation["evidence_id"] <= 0 for citation in chosen_citations):
        raise SavedWorkError("WORK_CITATIONS_INVALID")
    new_ids = {citation["evidence_id"] for citation in chosen_citations}
    for adoption in adoptions:
        if (not isinstance(adoption, dict) or set(adoption) != {"from_evidence_id", "to_evidence_id"}
                or any(adoption[key] is not None and (type(adoption[key]) is not int or adoption[key] <= 0) for key in adoption)
                or adoption["from_evidence_id"] is not None and adoption["from_evidence_id"] not in old_ids
                or adoption["to_evidence_id"] is not None and adoption["to_evidence_id"] not in new_ids
                or adoption["from_evidence_id"] == adoption["to_evidence_id"]):
            raise SavedWorkError("WORK_SOURCE_ADOPTION_INVALID")
    if ((new_ids - old_ids) - {adoption["to_evidence_id"] for adoption in adoptions}
            or (old_ids - new_ids) - {adoption["from_evidence_id"] for adoption in adoptions}):
        raise SavedWorkError("WORK_SOURCE_ADOPTION_REQUIRED")
    applied = _apply_work_edits(document, edits)
    document["payload"]["revision_note"] = {
        "schema": "lumenis.user-work-local-revision/v1", "reason": reason,
        "parent": {"artifact_id": artifact_id, "sha256": expected_sha256, "version": item["document"]["version"]},
        "edits": applied, "source_adoptions": adoptions, "offset_unit": "unicode_codepoint",
        "source_relation": "explicit user selection; not an independent correction of source Evidence"}
    _safe_payload(document["payload"])
    return save_work(title=document["title"], markdown=document["markdown"], kind=document["kind"],
                     payload=document["payload"], citations=chosen_citations, request_id=request_id,
                     actor=actor, scope=scope, work_id=document["work_id"], previous_artifact_id=artifact_id,
                     expected_draft_digest=item["document"]["draft_digest"], contract=document["contract"],
                     attachments=preserved_attachments)


def search_work(*, actor: Any, scope: Mapping, query: str = "", limit: int = 30,
                cursor: str | None = None, kind: str | None = None,
                evidence_id: int | None = None) -> dict:
    """Bounded, newest-first search; return a continuation even across hidden rows."""
    context = authorize_saved_work(actor, scope, action="read")
    if not isinstance(query, str) or len(query) > 200 or type(limit) is not int or not 1 <= limit <= 100:
        raise SavedWorkError("WORK_SEARCH_INVALID")
    if kind is not None and (not isinstance(kind, str) or kind not in _KINDS):
        raise SavedWorkError("WORK_SEARCH_INVALID")
    if evidence_id is not None and (type(evidence_id) is not int or evidence_id <= 0):
        raise SavedWorkError("WORK_SEARCH_INVALID")
    import shared_artifacts
    selectors = {"owner": "saved_work", "context": context, "query": query, "kind": kind}
    if evidence_id is not None:
        selectors["evidence_id"] = evidence_id
    identity = _digest(selectors)
    try:
        boundary_value = shared_artifacts._content_project_list_boundary(cursor, identity)
    except shared_artifacts.LocalArtifactError as exc:
        raise SavedWorkError("WORK_CURSOR_INVALID") from exc
    with get_repository().connection(read_only=True, wal=False) as con:
        shared = _shared_context(context)
        if shared:
            product_id, domain_id = _artifact_product_domain(context, kind=_KIND)
            params = [_KIND, product_id, domain_id]
            scope_filter = " AND product_id=? AND domain_id=?"
        else:
            params = [_KIND, context["domain_id"]]
            scope_filter = " AND domain_id=?"
        boundary = ""
        if boundary_value is not None:
            boundary = " AND (created_at<? OR (created_at=? AND artifact_id<?))"
            params.extend([boundary_value[0], boundary_value[0], boundary_value[1]])
        rows = con.execute(f"SELECT artifact_id,created_at FROM {_TABLE} WHERE kind=?" + scope_filter + boundary +
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
            if evidence_id is not None:
                matches = [citation for citation in doc["citations"] if citation["evidence_id"] == evidence_id]
                if not matches:
                    continue
                # These are source-character uses in immutable work versions.
                # Storage cannot infer an uncited claim or a scene/audio link.
                item["source_matches"] = {"evidence_id": evidence_id, "citations": matches,
                    "impact": "source-cited-work-version", "uncited_dependencies": "NOT_VERIFIED"}
            if (kind is None or doc["kind"] == kind) and query.casefold() in (doc["title"] + "\n" + doc["markdown"]).casefold():
                results.append(item)
            if len(results) == limit:
                break
    authorize_saved_work(actor, scope, action="read")
    with get_repository().connection(read_only=True, wal=False) as con:
        for item in results:
            _validate_citations(
                con, item["document"]["citations"], context, actor,
                source_use_operation="read", contract=item["document"]["contract"],
                payload=item["document"]["payload"],
            )
        authorize_saved_work(actor, scope, action="read", connection=con)
    has_more = len(rows) > consumed
    return {"items": results, "unverified_candidates": unavailable_count, "has_more": has_more,
            "next_cursor": shared_artifacts._content_project_list_cursor(identity, last_scanned)
            if has_more else None, "verification_complete": unavailable_count == 0}


def export_work(artifact_id: str, *, actor: Any, scope: Mapping, format: str = "json") -> dict:
    if not isinstance(format, str) or format not in {"json", "md", "txt", "docx", "pdf", "xlsx", "pptx"}:
        raise SavedWorkError("WORK_EXPORT_FORMAT_INVALID")
    item = read_committed_work(artifact_id, actor=actor, scope=scope,
                               _source_use_operation="export")
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
    read_committed_work(artifact_id, actor=actor, scope=scope,
                        _source_use_operation="export")
    _check_effect(actor, scope, permission.OperationType.DATA_EXPORT, resource)
    types = {"json": "application/json", "md": "text/markdown; charset=utf-8", "txt": "text/plain; charset=utf-8",
             "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "pdf": "application/pdf", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
    return {"content": raw, "filename": artifact_id + "." + format,
            "media_type": types[format],
            "sha256": hashlib.sha256(raw).hexdigest(), "return_ref": item["return_ref"]}
