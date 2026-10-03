"""Bind existing Word/ShotPlan, TaskEngine and SavedWork owners for internal work.

No schema creation, alternate store, external publishing or model route.
Permission is always resolved by the existing owner from the live request.
"""
from __future__ import annotations

import json
import re
import tempfile
from functools import lru_cache
from pathlib import Path

from ai_task_engine import TaskEngine
from lumenis.shared.content_creation.contracts import Shot, ShotPlan
from lumenis.shared.database import get_repository
from lumenis.shared.reporting import saved_work as work
from lumenis.system.security.permission import OperationType

CONTRACT = {"id": "lumenis.internal-pitch", "version": "1",
            "required_payload_paths": ["manuscript", "shot_plan", "truth_state"]}
_SCOPE = ("domain_id", "subject_id", "brand_focus_id", "global_scope")


@lru_cache(maxsize=1)
def engine():
    return TaskEngine(auto_init_db=False)


def _context(actor, scope, action):
    # Explicit GLOBAL/ALL is valid for internal work. The existing Permission
    # owner rejects inconsistent focus fields; NULL focus never implies a grant.
    return work.authorize(actor, scope, action=action)


def _permission(actor, scope, resource):
    _context(actor, scope, "write")
    return work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource)


def prepare_internal_pitch(*, manuscript, shot_plan, request_id, actor, scope,
                           citations=None, work_id=None, previous_artifact_id=None,
                           expected_draft_digest=None):
    """Seal one actual W4 manuscript/ShotPlan and its revision intent."""
    context = _context(actor, scope, "write")
    value = json.loads(work._json({"manuscript": manuscript, "shot_plan": shot_plan,
                                  "citations": citations or [], "work_id": work_id,
                                  "previous_artifact_id": previous_artifact_id,
                                  "expected_draft_digest": expected_draft_digest}))
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
        task = engine().create_pitch_task(task_context, before_commit=lambda: _permission(actor, scope, resource))
    return read_internal_pitch(task["task_id"], actor=actor, scope=scope)


def run_internal_pitch(task_id, *, actor, scope):
    """Actually produce Word, then atomically commit the work and Task result."""
    context = _context(actor, scope, "write")
    task = engine().get_pitch_task(task_id, owner_context=context)
    if task["status"] == "succeeded":
        return read_internal_pitch(task_id, actor=actor, scope=scope)
    resource = "internal-pitch-run:v1:" + work._digest({"task_id": task_id, "input_hash": task["context"]["input_hash"]})
    _permission(actor, scope, resource)
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

        payload = {"manuscript": value["manuscript"], "shot_plan": value["shot_plan"],
                   "truth_state": {"source_admission": "PENDING" if not value["citations"] else "SIGNED_CITATIONS_BOUND",
                                   "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                   "business_outcome": "NOT_OBSERVED", "shot_timing": "PLANNED"}}
        markdown = value["manuscript"]["title"] + "\n\n" + value["manuscript"]["summary"] + "\n\n" + "\n\n".join(
            "## " + s["heading"] + "\n\n" + s["body"] for s in value["manuscript"]["sections"])

        def before_commit(con, artifact, document):
            check = _context(actor, scope, "write")
            if check != context:
                raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
            _permission(actor, scope, resource)
            engine().commit_pitch_task(task_id, owner_context=context, worker=worker,
                                       connection=con, artifact=artifact, document=document)

        work.save_work(title=value["title"], markdown=markdown, kind="report", payload=payload,
                       citations=value["citations"], request_id=task["context"]["request_id"], actor=actor, scope=scope,
                       work_id=value["work_id"], previous_artifact_id=value["previous_artifact_id"],
                       expected_draft_digest=value["expected_draft_digest"], contract=CONTRACT, task_id=task_id,
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
        stored = task["result"]
        committed = work.reopen_work(stored["artifact_id"], actor=actor, scope=scope)
        if (committed["artifact"]["sha256"] != stored["sha256"] or committed["artifact"]["size_bytes"] != stored["size_bytes"]
                or committed["document"]["task_id"] != task_id or committed["document"]["version"] != stored["version"]
                or committed["document"]["work_id"] != stored["work_id"]
                or committed["document"]["parent_artifact_id"] != stored["parent_artifact_id"]
                or committed["document"]["parent_sha256"] != stored["parent_sha256"]
                or committed["document"]["contract"] != CONTRACT or len(committed["document"].get("attachments", [])) != 1):
            raise ValueError("INTERNAL_PITCH_RECEIPT_INTEGRITY_FAILED")
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
