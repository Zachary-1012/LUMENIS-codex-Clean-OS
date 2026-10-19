"""Paper computations as versioned outcomes of the existing Task/SavedWork owners.

Explicit mathematical scenarios are not observed commercial facts. This binding
does not create a queue, database, inference provider or an approval authority.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy

from .core import MathInputError, digest, strict_keys
from .dispatch import OPERATIONS

CONTRACT = {
    "id": "lumenis.openai-math",
    "version": "2",
    "required_payload_paths": [
        "problem_sha256",
        "operation",
        "result",
        "source_brief_artifact_hash",
        "input_declaration",
    ],
}


def freeze_problem(problem, declaration):
    strict_keys(problem, {"operation", "parameters"})
    operation = problem["operation"]
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise MathInputError("UNSUPPORTED_PAPER_OPERATION")
    _, required, optional = OPERATIONS[operation]
    strict_keys(problem["parameters"], required, optional)
    strict_keys(declaration, {"origin", "purpose", "variable_map"})
    if declaration["origin"] != "DECLARED_MATHEMATICAL_SCENARIO":
        raise MathInputError("EXPLICIT_MATHEMATICAL_SCENARIO_REQUIRED")
    if (
        not isinstance(declaration["purpose"], str)
        or not 1 <= len(declaration["purpose"].strip()) <= 500
        or not isinstance(declaration["variable_map"], dict)
        or not 1 <= len(declaration["variable_map"]) <= 256
        or any(
            not isinstance(k, str)
            or not isinstance(v, str)
            or not 1 <= len(k) <= 80
            or not 1 <= len(v.strip()) <= 300
            for k, v in declaration["variable_map"].items()
        )
    ):
        raise MathInputError("MATHEMATICAL_VARIABLE_MAPPING_REQUIRED")
    raw = json.dumps(
        {"problem": problem, "declaration": declaration},
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(raw.encode()) > 50_000:
        raise MathInputError("MATHEMATICAL_INPUT_SIZE_LIMIT")
    return deepcopy(problem), deepcopy(declaration), digest(problem)


def saved_scope(source_brief):
    """Project the verified SourceBrief contract into the existing SavedWork scope."""
    scope = source_brief["source_brief"]["scope"]
    return {
        "domain_id": scope["domain_id"],
        "subject_id": scope["subject_id"],
        "brand_focus_id": scope["brand_focus_id"],
        "global_scope": scope["global"],
    }


def authorize_compute(*, actor, task, problem_sha256, source_brief, phase):
    from lumenis.shared.reporting.saved_work import authorize
    from lumenis.system.security import OperationType, get_permission_gate

    scope = saved_scope(source_brief)
    authorize(actor, scope, action="read")
    resource = "paper-computation:" + task["task_id"] + ":" + problem_sha256
    decision = get_permission_gate().check(
        OperationType.REPORT_GENERATE,
        resource=resource,
        caller=task["created_by"],
        domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
    )
    allowed = getattr(decision, "allowed", False) is True
    return {
        "allowed": allowed,
        "decision_ref": digest(
            {
                "task": task["task_id"],
                "phase": phase,
                "operation": "REPORT_GENERATE",
                "resource": resource,
                "permission": decision.to_dict(),
                "scope": scope,
            }
        ),
        "permission": decision.to_dict(),
    }


def _storage_result(result):
    value = deepcopy(result)
    # SavedWork deliberately rejects private 'path' fields. A public manuscript
    # locator is projected without weakening that existing storage boundary.
    paper = value.get("paper", {})
    if "path" in paper:
        paper["manuscript_file"] = paper.pop("path")
    return value


def execute_product_task(engine, task):
    from agent_runtime.openai_math_paper_handler import handle_openai_math_task
    from lumenis.shared.reporting.saved_work import (
        authorize,
        read_committed_work,
        save_work,
    )

    context = task["context"]
    actor, actor_id = engine._analysis_actor(task)
    source = engine._read_analysis_source(task)
    scope = saved_scope(source)
    problem, declaration, problem_hash = freeze_problem(
        context["openai_math_problem"], context["openai_math_declaration"]
    )
    if problem_hash != context.get("openai_math_problem_sha256"):
        raise MathInputError("FROZEN_PROBLEM_IDENTITY_REQUIRED")

    def cancelled():
        return (engine._db_get_task(task["task_id"]) or {}).get("status") != "running"

    computed = handle_openai_math_task(
        task,
        actor=actor,
        actor_id=actor_id,
        expected_scope=context["openai_math_source_scope"],
        authorize_compute=authorize_compute,
        cancelled=cancelled,
    )
    payload = _storage_result(computed)
    payload.update(
        problem=problem,
        problem_sha256=problem_hash,
        input_declaration=declaration,
        input_declaration_sha256=digest(declaration),
        analysis_operation="openai_math",
        ai_required=False,
        normal_outcome="versioned mathematical scenario, not a Canonical fact",
    )
    parent_ref = context.get("openai_math_parent_artifact_id")
    work_id = "WORK-" + digest({"task_id": task["task_id"], "actor": actor_id})[:24]
    parent_digest = None
    if parent_ref:
        parent = read_committed_work(parent_ref, actor=actor, scope=scope)
        if (
            parent["document"]["contract"] != CONTRACT
            or parent["document"]["payload"].get("source_brief_job_id")
            != source["job_id"]
        ):
            raise MathInputError("MATHEMATICAL_PARENT_CONTEXT_MISMATCH")
        parent_task = engine._db_get_task(parent["document"]["task_id"])
        if not parent_task or parent_task.get("created_by") != actor_id:
            raise PermissionError("MATHEMATICAL_PARENT_ACTOR_MISMATCH")
        work_id = parent["document"]["work_id"]
        parent_digest = parent["document"]["draft_digest"]

    def before_commit(con, record, document):
        from .provenance import assert_review
        # The same SQLite writer transaction serializes reviews and publication.
        assert_review(payload["paper"]["family"], payload["paper"]["review"], connection=con)
        current = con.execute(
            "SELECT status,context_json,created_by FROM ai_task WHERE task_id=?",
            (task["task_id"],),
        ).fetchone()
        if (
            current is None
            or current[0] != "running"
            or current[2] != actor_id
            or json.loads(current[1]) != context
        ):
            raise PermissionError("MATHEMATICAL_TASK_CHANGED_BEFORE_COMMIT")
        authorize(actor, scope, action="write", connection=con)
        fresh = engine._read_analysis_source(task)
        if fresh["artifact_outcome"] != source["artifact_outcome"]:
            raise PermissionError("MATHEMATICAL_SOURCE_CHANGED_BEFORE_COMMIT")
        gate = authorize_compute(
            actor=actor,
            task=task,
            problem_sha256=problem_hash,
            source_brief=fresh,
            phase="commit",
        )
        if not gate["allowed"]:
            raise PermissionError("MATHEMATICAL_COMMIT_PERMISSION_DENIED")
        # Same canonical transaction records the staged Artifact and task output.
        # Cancellation serializes against this CAS; the normal engine subsequently
        # obtains the independent Owner readback before marking the task verified.
        pending = {
            "task_id": task["task_id"],
            "output": {
                **payload,
                "artifact_id": record["artifact_id"],
                "artifact_work_id": document["work_id"],
                "artifact_version": document["version"],
            },
            "task_outcome": "ARTIFACT_COMMITTED_OWNER_VERIFICATION_PENDING",
        }
        con.execute(
            "UPDATE ai_task SET result_json=?,updated_at=? WHERE task_id=? AND status='running'",
            (json.dumps(pending, ensure_ascii=False), engine._now(), task["task_id"]),
        )

    saved = save_work(
        title="数学分析 · " + problem["operation"],
        markdown="论文计算与声明情景\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2),
        kind="research",
        payload=payload,
        citations=[],
        request_id="math-" + task["task_id"],
        actor=actor,
        scope=scope,
        work_id=work_id,
        previous_artifact_id=parent_ref,
        expected_draft_digest=parent_digest,
        contract=CONTRACT,
        task_id=task["task_id"],
        assertion_id="mathematical-scenario-v2",
        before_commit=before_commit,
    )
    return {
        **payload,
        "artifact_id": saved["artifact"]["artifact_id"],
        "artifact_work_id": saved["document"]["work_id"],
        "artifact_version": saved["document"]["version"],
        "artifact_outcome": saved["receipt"],
        "base_analysis_status": "completed",
    }


def verify_product_outcome(engine, task, result, *, connection=None):
    from lumenis.shared.reporting.saved_work import read_committed_work

    actor, _ = engine._analysis_actor(task)
    source = engine._read_analysis_source(task)
    context = task["context"]
    problem, declaration, problem_hash = freeze_problem(
        context["openai_math_problem"], context["openai_math_declaration"]
    )
    artifact_id = result.get("artifact_id", "")
    if not isinstance(artifact_id, str) or not re.fullmatch(
        r"ART-[0-9a-f]{16}", artifact_id
    ):
        return False
    saved = read_committed_work(
        artifact_id, actor=actor, scope=saved_scope(source), connection=connection
    )
    payload = saved["document"]["payload"]
    return (
        saved["document"]["task_id"] == task["task_id"]
        and saved["document"]["contract"] == CONTRACT
        and payload.get("problem") == problem
        and payload.get("input_declaration") == declaration
        and payload.get("problem_sha256") == problem_hash
        and payload.get("source_brief_artifact_hash")
        == context["source_brief_artifact_hash"]
        and all(result.get(k) == v for k, v in payload.items())
        and result.get("artifact_outcome") == saved["receipt"]
    )
