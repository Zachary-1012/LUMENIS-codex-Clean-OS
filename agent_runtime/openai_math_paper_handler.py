"""Opt-in source-owner adapter. No registration, persistence or inference on import.

Insert only under current Task Engine's authenticated actor/scope branch.
Authorize compute through a server-held callback, not a client allow=True field.
"""

from copy import deepcopy

from lumenis.shared.evaluation.openai_math_papers.core import (
    Budget,
    MathInputError,
    digest,
)
from lumenis.shared.evaluation.openai_math_papers.dispatch import execute
from lumenis.shared.evaluation.openai_math_papers.provenance import assert_review


def handle_openai_math_task(
    task, *, actor, actor_id, expected_scope, authorize_compute, cancelled=None
):
    from lumenis.shared.reporting.source_brief_job import get_source_brief_job

    if actor is None or not callable(authorize_compute):
        raise PermissionError("SERVER_ACTOR_AND_AUTHORIZER_REQUIRED")
    context = task.get("context") or {}
    spec = deepcopy(context.get("openai_math_problem"))
    expected_problem = context.get("openai_math_problem_sha256")
    if not isinstance(spec, dict) or digest(spec) != expected_problem:
        raise MathInputError("FROZEN_PROBLEM_IDENTITY_REQUIRED")
    job = context.get("source_brief_job_id")
    version = context.get("source_brief_artifact_hash")
    before = get_source_brief_job(
        job, actor_id=actor_id, actor=actor, expected_scope=expected_scope
    )
    if before["artifact_outcome"]["artifact_hash"] != version:
        raise MathInputError("SOURCE_VERSION_CHANGED")
    decision = authorize_compute(
        actor=actor,
        task=task,
        problem_sha256=expected_problem,
        source_brief=before,
        phase="before",
    )
    if (
        not isinstance(decision, dict)
        or decision.get("allowed") is not True
        or not decision.get("decision_ref")
    ):
        raise PermissionError("MATHEMATICAL_DERIVATION_NOT_ADMITTED")
    # Spec graphs/margins/weights are mathematical inputs. Their business mapping
    # must come from an approved importer or explicit user declaration, not LLM invention.
    result = execute(spec, budget=Budget(cancelled=cancelled))
    after = get_source_brief_job(
        job, actor_id=actor_id, actor=actor, expected_scope=expected_scope
    )
    final = authorize_compute(
        actor=actor,
        task=task,
        problem_sha256=expected_problem,
        source_brief=after,
        phase="before_return",
    )
    if (
        after["artifact_outcome"]["artifact_hash"] != version
        or not isinstance(final, dict)
        or final.get("allowed") is not True
        or not final.get("decision_ref")
    ):
        raise PermissionError("SOURCE_OR_PERMISSION_CHANGED_DURING_COMPUTATION")
    assert_review(result["paper"]["family"], result["paper"]["review"])
    result.update(
        source_brief_job_id=job,
        source_brief_artifact_hash=version,
        compute_decision_ref=decision["decision_ref"],
        return_decision_ref=final["decision_ref"],
        persistence="CALLER_MUST_USE_EXISTING_TASK_AND_ARTIFACT_OWNER",
        source_to_model_mapping="REQUIRES_APPROVED_MAPPING_OR_EXPLICIT_USER_PARAMETERS",
        AI_training_authorized=False,
    )
    return result
