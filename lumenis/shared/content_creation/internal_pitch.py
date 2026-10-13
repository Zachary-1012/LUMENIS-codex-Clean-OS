"""Bind existing Word/ShotPlan, TaskEngine and SavedWork owners for internal work.

No schema creation, alternate store, external publishing or model route.
Permission is always resolved by the existing owner from the live request.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from urllib.parse import urlsplit
import re
import unicodedata
import tempfile
from functools import lru_cache
from pathlib import Path

from ai_task_engine import TaskEngine
from lumenis.shared.content_creation.contracts import Shot, ShotPlan, resolve_creation_upstream
from lumenis.shared.database import get_repository
from lumenis.shared.reporting import saved_work as work
from lumenis.system.security.permission import OperationType

CONTRACT = {"id": "lumenis.internal-pitch", "version": "1",
            "required_payload_paths": ["manuscript", "shot_plan", "truth_state"]}
MANUSCRIPT_PROFILE = "manuscript-only/v2"
MANUSCRIPT_CONTRACT = {"id": "lumenis.internal-pitch", "version": "2",
                       "required_payload_paths": ["manuscript", "input_manifest", "truth_state"]}
SOURCE_PROFILE = "source-bound/v3"
SOURCE_CONTRACT = {"id": "lumenis.internal-pitch", "version": "3",
                   "required_payload_paths": ["manuscript", "upstream_binding", "truth_state"]}
INPUT_MANIFEST_SCHEMA = "lumenis.internal-pitch-input-manifest/v1"
_SCOPE = ("domain_id", "subject_id", "brand_focus_id", "global_scope")


def _document_basename(value):
    # Equivalent bounded display-name handling to Importer path.name, without
    # opening a file or importing an admission owner. Preserve Unicode exactly.
    if not isinstance(value, str) or not 5 < len(value) <= 185:
        return False
    if (value != value.strip() or any(char in '<>:"/\\|?*' for char in value)
            or any(unicodedata.category(char).startswith("C") for char in value)
            or not value.lower().endswith(".docx")):
        return False
    stem = value[:-5]
    if not stem or stem.endswith((" ", ".")) or stem.split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *{f"COM{number}" for number in range(1, 10)},
        *{f"LPT{number}" for number in range(1, 10)},
    }:
        return False
    return True


def _input_manifest(manifest):
    """Retain operator declarations/full text, never ingest or authorize sources.

    Original binary size/hash declarations are not verified file receipts.
    W5's existing Importer retains/admit originals; all formal refs stay NULL.
    """
    if (not isinstance(manifest, dict) or set(manifest) != {"schema", "state", "materials"}
            or manifest["schema"] != INPUT_MANIFEST_SCHEMA or manifest["state"] != "NOT_INGESTED"
            or not isinstance(manifest["materials"], list) or not 1 <= len(manifest["materials"]) <= 16):
        raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
    fields = {"material_id", "role", "filename", "size_bytes", "sha256", "text", "text_sha256",
              "source_url", "published_at", "captured_at", "source_ref", "evidence_ref", "source_use_ref"}
    seen = set()
    for material in manifest["materials"]:
        has_origin = isinstance(material, dict) and "source_origin" in material
        if (not isinstance(material, dict) or set(material) != fields | ({"source_origin"} if has_origin else set())
                or not isinstance(material["material_id"], str)
                or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", material["material_id"]) is None
                or material["material_id"] in seen
                or not isinstance(material["role"], str) or material["role"] not in {"brief", "application_form", "reference"}
                or not _document_basename(material["filename"])
                or type(material["size_bytes"]) is not int or not 0 < material["size_bytes"] <= 8 * 1024 * 1024
                or not isinstance(material["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", material["sha256"]) is None
                or not isinstance(material["text"], str) or not material["text"].strip()
                or len(material["text"].encode("utf-8")) > 512 * 1024
                or material["text_sha256"] != hashlib.sha256(material["text"].encode("utf-8")).hexdigest()):
            raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
        if any(material[key] is not None for key in ("source_ref", "evidence_ref", "source_use_ref")):
            raise ValueError("INTERNAL_PITCH_SOURCE_BINDING_REQUIRED")
        url = material["source_url"]
        if url is None:
            # This is an unverified declaration of the existing Importer's
            # approved-file origin shape, not a new upload or approval receipt.
            origin = material.get("source_origin")
            valid_url = (isinstance(origin, dict) and set(origin) == {"kind", "ref"}
                         and origin["kind"] == "approved-file" and isinstance(origin["ref"], str)
                         and re.fullmatch(r"[A-Za-z0-9_-]{8,128}", origin["ref"]) is not None)
        else:
            try:
                parts = urlsplit(url) if isinstance(url, str) else None
                valid_url = (not has_origin and parts is not None and parts.scheme == "https"
                             and parts.hostname and not parts.username and not parts.password)
            except ValueError:
                valid_url = False
        if not valid_url:
            raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
        for key in ("published_at", "captured_at"):
            stamp = material[key]
            if stamp is None:
                continue
            try:
                parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")) if isinstance(stamp, str) else None
                valid_stamp = parsed is not None and parsed.utcoffset() is not None
            except (ValueError, OverflowError):
                valid_stamp = False
            if not valid_stamp:
                raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
        seen.add(material["material_id"])
    return manifest


def _contract(value):
    # Absence of profile identifies exact historical v1 input. Never add new
    # keys to old task hashes or reinterpret a committed ShotPlan work.
    if "profile" not in value:
        return CONTRACT
    if value["profile"] == SOURCE_PROFILE:
        if "shot_plan" in value or "input_manifest" in value or not isinstance(value.get("upstream_binding"), dict):
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        return SOURCE_CONTRACT
    if value["profile"] != MANUSCRIPT_PROFILE or "shot_plan" in value:
        raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
    _input_manifest(value["input_manifest"])
    return MANUSCRIPT_CONTRACT


@lru_cache(maxsize=1)
def engine():
    return TaskEngine(auto_init_db=False)


def _context(actor, scope, action, *, connection=None):
    # Explicit GLOBAL/ALL is valid for internal work. The existing Permission
    # owner rejects inconsistent focus fields; NULL focus never implies a grant.
    options = {"connection": connection} if connection is not None else {}
    return work.authorize(actor, scope, action=action, **options)


def _permission(actor, scope, resource, *, connection=None):
    _context(actor, scope, "write", connection=connection)
    options = {"connection": connection} if connection is not None else {}
    return work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource, **options)


def _check_upstream(value, *, actor, scope, connection=None):
    if _contract(value) != SOURCE_CONTRACT:
        return None
    sealed = value["upstream_binding"]
    current = resolve_creation_upstream(sealed["reference"], actor=actor, scope=scope, connection=connection)
    if work._digest(current) != work._digest(sealed):
        raise ValueError("INTERNAL_PITCH_UPSTREAM_CHANGED")
    return current


def prepare_internal_pitch(*, manuscript, request_id, actor, scope, shot_plan=None,
                           citations=None, work_id=None, previous_artifact_id=None,
                           expected_draft_digest=None, profile=None, input_manifest=None, upstream_ref=None):
    """Seal the existing ShotPlan v1 or explicit manuscript-only v2 input."""
    context = _context(actor, scope, "write")
    value = {"manuscript": manuscript, "citations": citations if citations is not None else [], "work_id": work_id,
             "previous_artifact_id": previous_artifact_id, "expected_draft_digest": expected_draft_digest}
    if profile == SOURCE_PROFILE and shot_plan is None and input_manifest is None:
        binding = resolve_creation_upstream(upstream_ref, actor=actor, scope=scope)
        inherited = binding["document"].get("citations", [])
        merged = inherited + value["citations"]
        value["citations"] = list({work._digest(item): item for item in merged}.values())
        value.update(profile=profile, upstream_binding=binding)
    elif profile is None:
        if input_manifest is not None or upstream_ref is not None:
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        value["shot_plan"] = shot_plan
    elif profile == MANUSCRIPT_PROFILE and shot_plan is None and upstream_ref is None:
        value.update(profile=profile, input_manifest=input_manifest)
    else:
        raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
    value = json.loads(work._json(value))
    work._safe_payload(value)
    manuscript = value["manuscript"]
    if (not isinstance(manuscript, dict) or set(manuscript) != {"title", "summary", "sections", "language", "authorship"}
            or not isinstance(manuscript["title"], str) or not 0 < len(manuscript["title"].strip()) <= 300
            or not isinstance(manuscript["summary"], str) or not manuscript["summary"].strip()
            or not isinstance(manuscript["language"], str) or manuscript["language"] not in {"zh", "en", "ko"}
            or not isinstance(manuscript["authorship"], str) or manuscript["authorship"] not in {"assisted", "user_supplied"}
            or not isinstance(manuscript["sections"], list) or not 1 <= len(manuscript["sections"]) <= 64):
        raise ValueError("INTERNAL_PITCH_MANUSCRIPT_INVALID")
    for section in manuscript["sections"]:
        if (not isinstance(section, dict) or set(section) != {"heading", "body"}
                or any(not isinstance(section[k], str) or not section[k].strip() for k in ("heading", "body"))):
            raise ValueError("INTERNAL_PITCH_MANUSCRIPT_INVALID")
    if not isinstance(value["citations"], list):
        raise ValueError("INTERNAL_PITCH_CITATIONS_INVALID")
    if _contract(value) == SOURCE_CONTRACT:
        _check_upstream(value, actor=actor, scope=scope)
    elif _contract(value) == MANUSCRIPT_CONTRACT:
        _input_manifest(value["input_manifest"])
    else:
        shot = value["shot_plan"]
        if (not isinstance(shot, dict) or set(shot) != {"shots", "brief_ref", "evidence_refs"}
                or not isinstance(shot["shots"], list) or not 1 <= len(shot["shots"]) <= 128
                or any(not isinstance(s, dict) for s in shot["shots"])
                or not isinstance(value["citations"], list)):
            raise ValueError("INTERNAL_PITCH_SHOT_PLAN_INVALID")
        # Current W4 input refs are empty. The actual canonical source-use reader
        # must bind nonempty refs; a local work locator never substitutes for one.
        if shot["brief_ref"] != "" or shot["evidence_refs"] or any(s.get("evidence_refs") for s in shot["shots"]):
            raise ValueError("INTERNAL_PITCH_SOURCE_BINDING_REQUIRED")
        try:
            plan = ShotPlan(tuple(Shot(**s) for s in shot["shots"]))
            plan.validate()
        except (TypeError, ValueError) as exc:
            raise ValueError("INTERNAL_PITCH_SHOT_PLAN_INVALID") from exc
        if plan.to_dict() != shot:
            raise ValueError("INTERNAL_PITCH_SHOT_PLAN_INVALID")
    value["title"] = manuscript["title"]
    task_context = {"schema": "lumenis.internal-pitch-task/v1", "owner_context": context,
                    "request_id": request_id, "input_hash": work._digest(value), "input": value}
    resource = "internal-pitch-prepare:v1:" + work._digest(task_context)
    _permission(actor, scope, resource)
    with work.staging_write(resource):
        def before_prepare_commit():
            _permission(actor, scope, resource)
            _check_upstream(value, actor=actor, scope=scope)
        task = engine().create_pitch_task(task_context, before_commit=before_prepare_commit)
    return read_internal_pitch(task["task_id"], actor=actor, scope=scope)


def run_internal_pitch(task_id, *, actor, scope):
    """Actually produce Word, then atomically commit the work and Task result."""
    context = _context(actor, scope, "write")
    task = engine().get_pitch_task(task_id, owner_context=context)
    if task["status"] == "succeeded":
        return read_internal_pitch(task_id, actor=actor, scope=scope)
    resource = "internal-pitch-run:v1:" + work._digest({"task_id": task_id, "input_hash": task["context"]["input_hash"]})
    _permission(actor, scope, resource)
    _check_upstream(task["context"]["input"], actor=actor, scope=scope)
    with work.staging_write(resource):
        if task["status"] in {"running", "cancel_requested"}:
            engine().reconcile_pitch_worker(task_id, owner_context=context,
                                            before_commit=lambda: _permission(actor, scope, resource))
        task = engine().claim_pitch_task(task_id, owner_context=context,
                                         before_commit=lambda: _permission(actor, scope, resource))
    worker, value = task["parameters"], task["context"]["input"]

    def check_continue():
        if _context(actor, scope, "write") != context:
            raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
        _permission(actor, scope, resource)
        engine().require_pitch_worker(task_id, owner_context=context, worker=worker)

    try:
        check_continue()
        from scripts.pitch_export import export_pitch_docx
        from lumenis.shared.reporting.artifact import verify_artifact_file
        with tempfile.TemporaryDirectory(prefix="lumenis-internal-pitch-") as temporary:
            output = Path(temporary) / "document.docx"
            result_path = Path(export_pitch_docx({}, str(output), manuscript=value["manuscript"], check_continue=check_continue))
            if result_path.resolve() != output.resolve() or not verify_artifact_file(str(output))["valid"]:
                raise ValueError("INTERNAL_PITCH_OUTPUT_INVALID")
            raw = output.read_bytes()
            check_continue()

        if _contract(value) == CONTRACT:
            payload = {"manuscript": value["manuscript"], "shot_plan": value["shot_plan"],
                       "truth_state": {"source_admission": "PENDING" if not value["citations"] else "SIGNED_CITATIONS_BOUND",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED", "shot_timing": "PLANNED"}}
        contract = _contract(value)
        if contract == SOURCE_CONTRACT:
            _check_upstream(value, actor=actor, scope=scope)
            payload = {"manuscript": value["manuscript"], "upstream_binding": value["upstream_binding"],
                       "truth_state": {"source_admission": "UPSTREAM_READER_BOUND",
                                       "citation_admission": "SIGNED_CITATIONS_BOUND" if value["citations"] else "NO_SIGNED_QUOTE",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED"}}
        if contract == MANUSCRIPT_CONTRACT:
            payload = {"manuscript": value["manuscript"], "input_manifest": value["input_manifest"],
                       "truth_state": {"source_admission": "PENDING", "input_materials": "OPERATOR_DECLARED_NOT_INGESTED",
                                       "citation_admission": "SIGNED_CITATIONS_BOUND" if value["citations"] else "PENDING",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED"}}
        markdown = value["manuscript"]["title"] + "\n\n" + value["manuscript"]["summary"] + "\n\n" + "\n\n".join(
            "## " + s["heading"] + "\n\n" + s["body"] for s in value["manuscript"]["sections"])

        def before_commit(con, artifact, document):
            check = _context(actor, scope, "write", connection=con)
            if check != context:
                raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
            _permission(actor, scope, resource, connection=con)
            _check_upstream(value, actor=actor, scope=scope, connection=con)
            engine().commit_pitch_task(task_id, owner_context=context, worker=worker,
                                       connection=con, artifact=artifact, document=document)

        work.save_work(title=value["title"], markdown=markdown, kind="report", payload=payload,
                       citations=value["citations"], request_id=task["context"]["request_id"], actor=actor, scope=scope,
                       work_id=value["work_id"], previous_artifact_id=value["previous_artifact_id"],
                       expected_draft_digest=value["expected_draft_digest"], contract=contract, task_id=task_id,
                       before_commit=before_commit, attachments=[{"name": "document.docx", "content": raw,
                           "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}])
    except BaseException as exc:
        code = str(exc)
        if re.fullmatch(r"[A-Z_0-9]{1,100}", code) is None:
            code = "INTERNAL_PITCH_EXECUTION_FAILED"
        engine().fail_pitch_task(task_id, owner_context=context, worker=worker, error=code)
        raise
    return read_internal_pitch(task_id, actor=actor, scope=scope)


def read_internal_pitch(task_id, *, actor, scope):
    """Reconcile lost acknowledgement through actual committed owner bytes."""
    context = _context(actor, scope, "read")
    task = engine().get_pitch_task(task_id, owner_context=context)
    result = {"task_id": task_id, "state": task["status"], "error": task["error"],
              "action_receipt": None, "work": None, "scope": {k: context[k] for k in _SCOPE}}
    if task["status"] == "succeeded":
        upstream = _check_upstream(task["context"]["input"], actor=actor, scope=scope)
        stored = task["result"]
        committed = work.reopen_work(stored["artifact_id"], actor=actor, scope=scope)
        if (committed["artifact"]["sha256"] != stored["sha256"] or committed["artifact"]["size_bytes"] != stored["size_bytes"]
                or committed["document"]["task_id"] != task_id or committed["document"]["version"] != stored["version"]
                or committed["document"]["work_id"] != stored["work_id"]
                or committed["document"]["parent_artifact_id"] != stored["parent_artifact_id"]
                or committed["document"]["parent_sha256"] != stored["parent_sha256"]
                or committed["document"]["contract"] != _contract(task["context"]["input"])
                or len(committed["document"].get("attachments", [])) != 1):
            raise ValueError("INTERNAL_PITCH_RECEIPT_INTEGRITY_FAILED")
        if upstream is not None:
            if committed["document"]["payload"].get("upstream_binding") != upstream:
                raise ValueError("INTERNAL_PITCH_UPSTREAM_INTEGRITY_FAILED")
            result["research_return_ref"] = upstream["return_ref"]
        result["work"] = committed
        result["action_receipt"] = {"owner": "Shared ContentCreation/TaskEngine/SavedWork",
                                    "task_id": task_id, **stored, "scope": result["scope"],
                                    "output": committed["document"]["attachments"][0]}
    if _context(actor, scope, "read") != context:
        raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
    return result


def cancel_internal_pitch(task_id, *, actor, scope):
    context = _context(actor, scope, "write")
    resource = "internal-pitch-cancel:v1:" + work._digest({"context": context, "task_id": task_id})
    _permission(actor, scope, resource)
    with work.staging_write(resource):
        task = engine().cancel_pitch_task(task_id, owner_context=context,
                                         before_commit=lambda: _permission(actor, scope, resource))
    result = read_internal_pitch(task_id, actor=actor, scope=scope)
    result["cancellation"] = "ALREADY_COMMITTED" if task["status"] == "succeeded" else task["status"].upper()
    return result


def download_internal_pitch(task_id, *, actor, scope):
    result = read_internal_pitch(task_id, actor=actor, scope=scope)
    if result["work"] is None:
        raise ValueError("INTERNAL_PITCH_OUTPUT_NOT_COMMITTED")
    binding = result["action_receipt"]["output"]
    resource = "internal-pitch-export:v1:" + work._digest(binding)
    work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource)
    context = _context(actor, scope, "read")
    with get_repository().connection(read_only=True, wal=False) as con:
        raw = work._read_attachment(con, binding, context, result["action_receipt"]["work_id"])
    read_internal_pitch(task_id, actor=actor, scope=scope)
    work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource)
    return {"content": raw, "filename": binding["name"], "media_type": binding["media_type"],
            "sha256": binding["sha256"], "action_receipt": result["action_receipt"]}
