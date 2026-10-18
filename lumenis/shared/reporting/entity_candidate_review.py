"""Human review of source-backed matching candidates in original SavedWork.

Scores are statistical suggestions. A review is a user judgment, not identity
truth. Registry registration remains an independently confirmed CONFIG_MODIFY.
"""
from copy import deepcopy
import json

from . import saved_work

SCHEMA = "lumenis.entity-candidate-review/v1"
DECISIONS = {"KEEP_SEPARATE", "NEEDS_MORE_EVIDENCE", "PROPOSE_REGISTRATION"}


def _latest(artifact_id, *, actor, scope):
    work = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope)
    context = saved_work.authorize_saved_work(actor, scope, action="read")
    with saved_work.get_repository().connection(read_only=True, wal=False) as con:
        versions = saved_work._versions(con, work["document"]["work_id"], context, actor)
    if not versions or versions[-1]["artifact"]["artifact_id"] != artifact_id:
        raise ValueError("ENTITY_REVIEW_VERSION_CHANGED")
    return work


def read_candidates(artifact_id, *, actor, scope):
    """Recompute the original source recipe; editable report JSON is not authority."""
    from .business_brief import analyze_statistics_source

    work = _latest(artifact_id, actor=actor, scope=scope)
    statistics = work["document"]["payload"].get("statistics")
    if not isinstance(statistics, dict) or statistics.get("analysis") != "entity_matching":
        raise ValueError("ENTITY_CANDIDATE_REPORT_REQUIRED")
    fresh = analyze_statistics_source(
        statistics.get("source_evidence_id"), actor=actor, scope=scope,
        options=statistics.get("options"), business_purpose=statistics.get("business_purpose"),
    )
    if fresh["saved_work_draft"]["payload"]["statistics"] != statistics:
        raise ValueError("ENTITY_CANDIDATE_SOURCE_OR_RECIPE_CHANGED")
    return {
        "report_artifact_id": artifact_id, "report_sha256": work["artifact"]["sha256"],
        "report_work_id": work["document"]["work_id"],
        "report_version": work["document"]["version"],
        "method": statistics["result"]["method"],
        "state": statistics["result"]["state"],
        "candidates": deepcopy(statistics["result"].get("candidates", [])),
        "judgment": "NOT_REVIEWED", "registry_change": "NOT_PERFORMED",
        "citations": deepcopy(work["document"]["citations"]),
    }


def _material(report, candidate_id, decision, proposed_identity, rationale, proposed_side=None):
    if not isinstance(decision, str) or decision not in DECISIONS or not isinstance(rationale, str) or not 1 <= len(rationale.strip()) <= 4000:
        raise ValueError("ENTITY_REVIEW_JUDGMENT_INVALID")
    candidates = [row for row in report["candidates"] if row["id"] == candidate_id]
    if len(candidates) != 1:
        raise ValueError("ENTITY_REVIEW_CANDIDATE_UNKNOWN")
    candidate = candidates[0]
    identity = None
    if decision == "PROPOSE_REGISTRATION":
        if (not candidate.get("identity_pair") or
                candidate.get("source_binding_state") != "SOURCE_QUOTES_VERIFIED_NOT_IDENTITY_CONFIRMED"):
            raise ValueError("ENTITY_REVIEW_IDENTITY_SOURCES_REQUIRED")
        if proposed_side not in {"left", "right"}:
            raise ValueError("ENTITY_REVIEW_SELECTED_SIDE_REQUIRED")
        selected = candidate["identity_pair"][proposed_side]
        from subject_registry import prepare_subject_batch, get_subject_by_id
        prepared = prepare_subject_batch([{"baseline_id": candidate_id, "identity": proposed_identity}])
        identity = prepared["entries"][0]["identity"]
        label = selected["label"].strip().casefold()
        if label not in {identity["name_en"].casefold(), identity["name_zh"].casefold()}:
            raise ValueError("ENTITY_REVIEW_IDENTITY_NOT_SELECTED_CANDIDATE")
        if selected.get("registry_subject_id") is not None:
            registered = get_subject_by_id(identity["domain_id"], selected["registry_subject_id"])
            if not registered or any(registered[key] != identity[key] for key in ("name_en", "name_zh")):
                raise ValueError("ENTITY_REVIEW_DECLARED_REGISTRY_ID_MISMATCH")
    elif proposed_identity is not None or proposed_side is not None:
        raise ValueError("ENTITY_REVIEW_UNEXPECTED_IDENTITY")
    return {
        "schema": SCHEMA,
        **{key: report[key] for key in (
            "report_artifact_id", "report_sha256", "report_work_id", "report_version", "method")},
        "candidate_id": candidate_id, "candidate": deepcopy(candidate),
        "decision": decision, "rationale": rationale.strip(), "proposed_identity": identity,
        "proposed_side": proposed_side, "name_relation": "selected-source-label-plus-explicit-user-names" if identity else None,
        "judgment_origin": "explicit_user_review", "identity_truth": "NOT_ESTABLISHED",
        "registry_change": "NOT_PERFORMED", "merge_supported": False,
    }


def save_review(artifact_id, *, actor, scope, candidate_id, decision, rationale,
                request_id, proposed_identity=None, proposed_side=None, work_id=None, previous_artifact_id=None):
    report = read_candidates(artifact_id, actor=actor, scope=scope)
    material = _material(report, candidate_id, decision, proposed_identity, rationale, proposed_side)
    if previous_artifact_id:
        previous = _latest(previous_artifact_id, actor=actor, scope=scope)
        old = previous["document"]["payload"].get("entity_candidate_review", {})
        if old.get("schema") != SCHEMA or old.get("candidate_id") != candidate_id:
            raise ValueError("ENTITY_REVIEW_PARENT_MISMATCH")
        if work_id != previous["document"]["work_id"]:
            raise ValueError("ENTITY_REVIEW_PARENT_MISMATCH")

    def recheck(con, record, document):
        current = read_candidates(artifact_id, actor=actor, scope=scope)
        if current != report:
            raise ValueError("ENTITY_REVIEW_SOURCE_CHANGED")
        from lumenis.shared.evidence import store
        context = saved_work.authorize_saved_work(actor, scope, action="write", connection=con)
        binding = _receipt_binding(record, document, context)
        receipt_id = store.record_evidence(
            source="entity_candidate_review", feature_id=record["artifact_id"],
            asset_id=record["artifact_id"], product="ZBMP" if context["domain_id"] == "zbmp" else "CTH",
            domain_id=context["domain_id"], subject_id=context["subject_id"],
            brand_focus_id=context["brand_focus_id"], global_scope=context["global_scope"],
            inputs={"review_binding": binding}, outputs={"review_recorded": True, "identity_truth": "NOT_ESTABLISHED"},
            account=context.get("principal_ref") or "actor:" + str(context["actor_id"]),
            provider=__name__, status="pending", capture_mode="explicit-actor-review",
            connection=con,
        )
        row = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (receipt_id,)).fetchone()
        if not row or not store.verify_evidence_record_integrity(row):
            raise ValueError("ENTITY_REVIEW_RECEIPT_SIGNING_FAILED")

    return saved_work.save_work(
        title="Entity candidate review: " + candidate_id[:100], kind="report",
        markdown=("# Entity candidate review\n\n" + decision + "\n\n" + rationale.strip() +
                  "\n\nUser judgment only. No identity merge or registration was performed."),
        payload={"entity_candidate_review": material}, citations=report["citations"],
        request_id=request_id, actor=actor, scope=scope, work_id=work_id,
        previous_artifact_id=previous_artifact_id, before_commit=recheck,
    )


def registration_proposal(review_artifact_id, *, actor, scope):
    """Fresh exact proposal for the existing Registry approval workflow."""
    review = _latest(review_artifact_id, actor=actor, scope=scope)
    material = review["document"]["payload"].get("entity_candidate_review")
    if not isinstance(material, dict) or material.get("schema") != SCHEMA:
        raise ValueError("ENTITY_REVIEW_REQUIRED")
    context = saved_work.authorize_saved_work(actor, scope, action="read")
    _verify_receipt(review, context)
    report = read_candidates(material.get("report_artifact_id"), actor=actor, scope=scope)
    expected = _material(report, material.get("candidate_id"), material.get("decision"),
                         material.get("proposed_identity"), material.get("rationale"), material.get("proposed_side"))
    if expected != material:
        raise ValueError("ENTITY_REVIEW_SOURCE_CHANGED")
    if material["decision"] != "PROPOSE_REGISTRATION":
        raise ValueError("ENTITY_REVIEW_REGISTRATION_NOT_PROPOSED")
    return {
        "entries": [{"baseline_id": material["candidate_id"], "identity": material["proposed_identity"]}],
        "review_artifact_id": review_artifact_id, "review_sha256": review["artifact"]["sha256"],
        "report_artifact_id": report["report_artifact_id"], "report_sha256": report["report_sha256"],
        "registry_change": "NOT_PERFORMED", "merge_supported": False,
    }


def _receipt_binding(artifact, document, context):
    return {"contract": "entity-candidate-review-receipt/v1", "context": context,
            "artifact_id": artifact["artifact_id"], "artifact_sha256": artifact["sha256"],
            "work_id": document["work_id"], "version": document["version"],
            "parent_artifact_id": document.get("parent_artifact_id"),
            "review_sha256": saved_work._digest(document["payload"]["entity_candidate_review"])}


def _verify_receipt(review, context):
    from lumenis.shared.evidence import store
    expected = _receipt_binding(review["artifact"], review["document"], context)
    with saved_work.get_repository().connection(read_only=True, wal=False) as con:
        rows = con.execute("SELECT * FROM app_evidence_records WHERE source=? AND asset_id=?",
                           ("entity_candidate_review", review["artifact"]["artifact_id"])).fetchall()
    if len(rows) != 1 or not store.verify_evidence_record_integrity(rows[0]):
        raise ValueError("ENTITY_REVIEW_OWNER_RECEIPT_REQUIRED")
    row = dict(rows[0])
    if (row.get("provider") != __name__ or row.get("feature_id") != expected["artifact_id"]
            or json.loads(row["inputs_json"]).get("review_binding") != expected):
        raise ValueError("ENTITY_REVIEW_OWNER_RECEIPT_MISMATCH")
