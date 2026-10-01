"""Request-authorized report execution using the existing SYSTEM TaskEngine.

Only operational intent/status lives in ai_task. Reporting still owns the
immutable daily_reports artifact. A crashed run requires a new authorized
request; persisted task JSON is never a credential or an approval.
"""
from __future__ import annotations

import logging
import os
import threading
import uuid
from functools import lru_cache

import psutil

from ai_task_engine import TaskEngine
from lumenis.shared.database import get_repository
from .source_brief_job import _scope_material, create_source_brief_job, get_source_brief_job

_log = logging.getLogger(__name__)
_workers: dict[str, threading.Thread] = {}
_lock = threading.RLock()


@lru_cache(maxsize=1)
def engine():
    # Startup/schema migrations retain ownership of table creation.
    return TaskEngine(auto_init_db=False)


def create_task(*, actor_ref, scope, permission_audit_ref, limit=30,
                image_source_ref=None, business_question=None, source_ids=None, revision=None):
    context = {
        "actor_ref": actor_ref, "scope": scope,
        "job_id": "brief-" + uuid.uuid4().hex,
        "permission_audit_ref": permission_audit_ref,
        "limit": limit, "image_source_ref": image_source_ref,
        "business_question": business_question,
        "source_ids": source_ids,
        "revision": revision,
    }
    return engine().create_report_task(context)


def scoped_task(task_id, *, actor_ref, scope):
    task = engine().get_report_task(task_id)
    if task is None:
        raise LookupError("SOURCE_BRIEF_TASK_NOT_FOUND")
    context = task["context"]
    if context.get("actor_ref") != actor_ref or context.get("scope") != scope:
        raise PermissionError("SOURCE_BRIEF_TASK_SCOPE_DENIED")
    return task


def _worker_alive(task):
    """False only when the exact claimed OS process is proven gone."""
    identity = task.get("parameters") or {}
    pid, started = identity.get("worker_pid"), identity.get("worker_started_at")
    if type(pid) is not int or pid <= 0 or type(started) not in {int, float}:
        raise RuntimeError("SOURCE_BRIEF_WORKER_IDENTITY_UNAVAILABLE")
    try:
        process = psutil.Process(pid)
        alive = process.is_running() and process.create_time() == started
        if alive and pid == os.getpid():
            with _lock:
                worker = _workers.get(task["task_id"])
                return worker is not None and worker.is_alive()
        return alive
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied as exc:
        raise RuntimeError("SOURCE_BRIEF_WORKER_IDENTITY_UNAVAILABLE") from exc


def status(task):
    context = task["context"]
    state = task["status"]
    if state == "running" and not _worker_alive(task):
        state = "interrupted"
    result = {
        "task_id": task["task_id"], "job_id": context["job_id"], "state": state,
        "can_resume": state in {"pending", "interrupted", "failed"},
        "error": task.get("error"), "result": None,
        "review_status": "HUMAN_PENDING", "publish_status": "not_performed",
    }
    if state == "succeeded":
        result["result"] = get_source_brief_job(
            context["job_id"], actor_id=context["actor_ref"],
            expected_scope=_scope_material(**context["scope"]),
        )
    return result


def dispatch(task, *, authorize, request_wrapper):
    """Execute only a live request's closure; never deserialize executable work.

    request_wrapper is Flask's copy_current_request_context, captured from the
    real start/resume request. It is not reconstructed from task JSON on boot.
    """
    task_id = task["task_id"]
    with _lock:
        active = _workers.get(task_id)
        if active is not None and active.is_alive():
            return
        current = engine().get_report_task(task_id)
        if current["status"] == "succeeded":
            return
        if current["status"] == "running":
            if _worker_alive(current):
                return
            engine().mark_interrupted_report_task(
                task_id, expected_parameters_json=current["parameters_json"],
            )
        authorize()
        if not engine().claim_report_task(task_id):
            return

        @request_wrapper
        def run():
            try:
                actor, audit_ref = authorize()
                context = scoped_task(
                    task_id, actor_ref=task["context"]["actor_ref"], scope=task["context"]["scope"],
                )["context"]
                con = get_repository().connect(read_only=True, wal=False)
                try:
                    result = create_source_brief_job(
                        con, **context["scope"], actor_id=context["actor_ref"],
                        permission_audit_ref=audit_ref, job_id=context["job_id"],
                        trace_id="source-brief:" + context["job_id"],
                        limit=context["limit"], image_source_ref=context["image_source_ref"],
                        image_actor=actor, business_question=context["business_question"],
                        source_ids=context.get("source_ids"),
                        revision_reference=context.get("revision"),
                        before_persist=authorize,
                    )
                finally:
                    con.close()
                authorize()
                finished = engine().finish_report_task(task_id, result={
                    "job_id": result["job_id"],
                    "artifact_hash": result["artifact_outcome"]["artifact_hash"],
                })
                if not finished:
                    raise RuntimeError("SOURCE_BRIEF_TASK_STATE_CONFLICT")
            except Exception as exc:
                # No raw exception, prompt, Cookie or path in the task response.
                code = "SOURCE_BRIEF_TASK_DENIED" if isinstance(exc, PermissionError) else "SOURCE_BRIEF_TASK_FAILED"
                try:
                    engine().finish_report_task(task_id, error=code)
                except Exception:
                    _log.error("Report task status could not be persisted: %s", task_id)
                _log.warning("Report task %s failed (%s)", task_id, type(exc).__name__)
            finally:
                with _lock:
                    _workers.pop(task_id, None)

        thread = threading.Thread(target=run, name="source-brief-" + task_id, daemon=True)
        _workers[task_id] = thread
        try:
            thread.start()
        except Exception:
            _workers.pop(task_id, None)
            engine().finish_report_task(task_id, error="SOURCE_BRIEF_WORKER_START_FAILED")
            raise RuntimeError("SOURCE_BRIEF_WORKER_START_FAILED") from None
