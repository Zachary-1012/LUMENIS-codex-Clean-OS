"""Scoped learning admission and local exchange, using the existing Evidence owner.

No receiver, scheduler, provider, account or database is created here. EXPORTED
is a durable local staged envelope, never proof of delivery. Admission changes
only this derivative learning reference; it does not activate a rule or train.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store
from lumenis.shared.reporting import operator_review, saved_work, source_brief_job
from lumenis.shared.reporting.media_brief import _actor_ref
from lumenis.system.security import permission

VERSION = "scoped-learning-exchange:v1"
FEATURE = "SCOPED_LEARNING_EXCHANGE"
RECEIPT_FEATURE = "SCOPED_LEARNING_TRANSPORT_RECEIPT"
LOCAL_REPO = "Zachary-1012/LUMENIS-codex-Clean-OS"
CONTRACT_PATH = Path(__file__).resolve().parents[3] / "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json"
STATES = {"PENDING", "EXPORTED", "ACKNOWLEDGED", "REJECTED", "FAILED", "DEAD_LETTER"}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _submission(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError("LEARNING_SUBMISSION_ID_INVALID")
    return value


def current_contract():
    """Read actual current metadata and verify its self-digest and safety shape."""
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    unsigned = {k: v for k, v in data.items() if k != "protocol_fingerprint_sha256"}
    if (data.get("protocol_fingerprint_sha256") != _hash(unsigned)
            or data.get("contract_id") != "lumenis-ggi-cross-product"
            or data.get("status") != "ACTIVE"
            or data.get("contract_version") != "1.1.0"
            or set(data["ggi_shared_intelligence_contribution"]["states"]) != STATES
            or data["ggi_shared_intelligence_contribution"]["max_retries"] != 3
            or data["truth_and_runtime_boundary"]["ai_or_research_may_overwrite_lumenis_production_truth"] is not False
            or data["truth_and_runtime_boundary"]["unrestricted_cross_product_writer"] is not False):
        raise RuntimeError("LEARNING_EXCHANGE_CONTRACT_UNSUPPORTED")
    return data


def _shared(scope):
    return scope == {"scope_kind": "shared_workspace", "version": 1}


def _service_scope(scope):
    return scope if _shared(scope) else source_brief_job._media_scope(scope)


def _scope_marker(scope):
    return None if _shared(scope) else operator_review._expected_scope_marker(scope)


def _access(actor, actor_id, scope, *, action, connection):
    if _actor_ref(actor) != actor_id:
        raise PermissionError("LEARNING_ACTOR_MISMATCH")
    if not _shared(scope) and (not isinstance(scope, dict) or scope.get("product_id") not in {"CTH", "ZBMP"}):
        raise ValueError("LEARNING_SCOPE_NOT_SUPPORTED")
    return saved_work.authorize_saved_work(actor, _service_scope(scope), action=action, connection=connection)


def _hypothesis_binding(report):
    """Pin the current SourceBrief owner's immutable review version, when present."""
    reference = report.get("hypothesis_review")
    return {"hypothesis_review": dict(reference)} if reference is not None else {}


def _material(job_id, review_id, actor, actor_id, scope, connection):
    context = _access(actor, actor_id, scope, action="read", connection=connection)
    row = source_brief_job._read_report(job_id, connection=connection)
    if row is None:
        raise LookupError("LEARNING_REPORT_UNAVAILABLE")
    report = source_brief_job._verify_report(row, job_id=job_id, actor_id=actor_id,
                                            expected_scope=scope, actor=actor)
    sources = report["source_brief"]["records"]
    if not sources:
        raise ValueError("LEARNING_REAL_SOURCES_REQUIRED")
    if _shared(scope):
        return _shared_material(report, review_id, actor, actor_id, scope, connection)
    resolved = source_brief_job.resolve_report_sources(job_id, actor=actor, actor_id=actor_id,
                                                       expected_scope=scope, connection=connection)
    bindings = [{"source_id": source["source_id"], "evidence_ref": source["content_evidence_ref"],
                 "content_hash": source["content_hash"], "rights": source["rights"],
                 "version": source["source_version"], "source_scope": source["source_scope"]}
                for source in resolved["records"]]
    if review_id.startswith('business:'):
        return {**_business_material(report, review_id, actor, actor_id, scope, bindings),
                **_hypothesis_binding(resolved['report'])}
    rows = connection.execute("SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? AND test_name=?",
                              (operator_review._FEATURE, job_id, review_id)).fetchall()
    if len(rows) != 1:
        raise PermissionError("LEARNING_REVIEW_REQUIRED")
    review = operator_review._verify_record(dict(rows[0]), job_id=job_id,
        artifact_hash=row["artifact_hash"], actor_id=actor_id, scope=scope)
    if review is None or operator_review._evaluation_state(review) != "recorded":
        raise PermissionError("LEARNING_INDEPENDENT_EVALUATION_REQUIRED")
    return {"job_id": job_id, "artifact_hash": row["artifact_hash"], "review_id": review_id,
            "review_evidence_ref": review["evidence_ref"], "evaluation_id": review["evaluation_id"],
            "feedback_decision": review["decision"], "feedback_text": review["notes"], "source_bindings": bindings,
            "business_outcome": "NOT_OBSERVED", **_hypothesis_binding(resolved["report"])}


def _read(connection, object_id, actor_id, scope, *, kind):
    if not isinstance(object_id, str) or not re.fullmatch(r"[0-9a-f]{64}", object_id):
        raise ValueError("LEARNING_ID_INVALID")
    rows = connection.execute("SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? ORDER BY id",
                              (FEATURE, object_id)).fetchall()
    events, previous = [], None
    for raw in rows:
        row = dict(raw)
        if not store.verify_evidence_record_integrity(row):
            raise RuntimeError("LEARNING_SIGNATURE_INVALID")
        inputs, state = json.loads(row["inputs_json"]), json.loads(row["outputs_json"])
        if (inputs.get("actor_id") != actor_id or inputs.get("scope") != scope or inputs.get("kind") != kind):
            raise PermissionError("LEARNING_OBJECT_UNAVAILABLE")
        if (row["source"] != "shared_learning" or row["version"] != VERSION or row["status"] != "derived"
                or row.get("result") != "RECORDED" or row.get("test_name") != inputs.get("submission_id")
                or row.get("product") != ("SHARED" if _shared(scope) else scope["product_id"])
                or (row.get("product_id") is not None if _shared(scope) else row.get("product_id") != scope["product_id"])
                or (row.get("domain_id") not in (None, "") if _shared(scope) else row.get("domain_id") != scope["domain_id"])
                or inputs.get("version") != VERSION
                or inputs.get("object_id") != object_id or state.get("revision") != len(events) + 1
                or inputs.get("previous_digest") != previous
                or inputs.get("_lumenis_scope") != _scope_marker(scope)):
            raise RuntimeError("LEARNING_EVENT_CHAIN_INVALID")
        previous = row["integrity_digest"]
        events.append({"inputs": inputs, "state": state, "evidence_ref": "app_evidence_records:" + str(row["id"]),
                       "digest": previous})
    if not events:
        raise LookupError("LEARNING_OBJECT_UNAVAILABLE")
    return events


def _append(connection, *, object_id, kind, actor_id, scope, submission_id, request, state, previous, audit):
    inputs = {"version": VERSION, "object_id": object_id, "kind": kind, "actor_id": actor_id,
              "scope": scope, "submission_id": submission_id, "request": request,
              "previous_digest": previous, **audit}
    record_id = store.record_evidence(connection=connection, source="shared_learning", project="LUMENIS",
        product="SHARED" if _shared(scope) else scope["product_id"], feature_id=FEATURE, asset_id=object_id, test_name=submission_id,
        version=VERSION, result="RECORDED", status="derived", inputs=inputs, outputs=state,
        capture_mode="local_learning_exchange", domain_id=scope.get("domain_id"),
        subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"), global_scope=scope.get("global", False))
    if type(record_id) is not int or record_id <= 0:
        raise RuntimeError("LEARNING_WRITE_FAILED")
    return _read(connection, object_id, actor_id, scope, kind=kind)[-1]


def _view(event):
    return {"id": event["inputs"]["object_id"], "kind": event["inputs"]["kind"],
            "actor_id": event["inputs"]["actor_id"], "scope": event["inputs"]["scope"],
            **event["state"], "evidence_ref": event["evidence_ref"],
            "production_truth_write": False, "training_eligible": False}


def _fresh(event, actor, actor_id, scope, connection):
    origin = event["state"]["origin"]
    current = _material(origin["job_id"], origin["review_id"], actor, actor_id, scope, connection)
    if current != origin:
        raise PermissionError("LEARNING_SOURCE_OR_REVIEW_CHANGED")


def _replay(events, submission_id, request):
    found = [event for event in events if event["inputs"]["submission_id"] == submission_id]
    if found:
        if len(found) != 1 or found[0]["inputs"]["request"] != request:
            raise ValueError("LEARNING_SUBMISSION_CONFLICT")
        return _view(found[0])
    return None


def _effect(actor, scope, operation, resource, *, connection):
    if _shared(scope):
        result = permission.check_shared_workspace_effect(actor, scope, operation, resource,
                    module="learning", action="write", connection=connection)
        if result.allowed is not True:
            raise PermissionError("LEARNING_EFFECT_PERMISSION_DENIED")
        return result
    context = saved_work.authorize_saved_work(actor, _service_scope(scope), action="write", connection=connection)
    if permission.is_testing_bypass_enabled():
        raise PermissionError("LEARNING_EFFECT_PERMISSION_UNVERIFIED")
    result = permission.get_permission_gate().check(operation, resource=resource, caller=_actor_ref(actor),
        domain_id="bmp" if context["domain_id"] == "zbmp" else "cth")
    if not result.allowed:
        raise saved_work.SavedWorkError("WORK_EFFECT_PERMISSION_DENIED")
    return result


def _approval(actor, scope, object_id, action, revision, *, connection):
    resource = approval_resource(object_id, action, revision)
    return _effect(actor, scope, permission.OperationType.CONFIG_MODIFY, resource, connection=connection)


def _commit_effect(connection, actor, scope, object_id, action, revision, operation):
    resource = approval_resource(object_id, action, revision)
    result = _effect(actor, scope, operation, resource, connection=connection)
    if not result.approval_token:
        raise PermissionError("LEARNING_EXACT_APPROVAL_REQUIRED")
    with permission.get_permission_gate().learning_exchange_commit_lease(
            result.approval_token, operation=operation, resource=resource, caller=_actor_ref(actor)) as current:
        current()
        connection.commit()


def approval_resource(object_id, action, revision):
    return "learning-exchange:" + _hash({"object_id": object_id, "action": action, "revision": revision})


def create_candidate(*, job_id, actor, actor_id, expected_scope, review_id, submission_id, authorize):
    _submission(submission_id)
    if (not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 128
            or not isinstance(review_id, str) or not review_id.strip() or len(review_id) > 512):
        raise ValueError("LEARNING_REPORT_REVIEW_REFERENCE_INVALID")
    request = {"job_id": job_id, "review_id": review_id}
    object_id = _hash({"version": VERSION, "actor_id": actor_id, "scope": expected_scope, **request})
    with get_repository().transaction(timeout=10) as con:
        con.execute("BEGIN IMMEDIATE")
        _access(actor, actor_id, expected_scope, action="write", connection=con)
        audit = operator_review._authorize(authorize, actor_id, expected_scope)
        origin = _material(job_id, review_id, actor, actor_id, expected_scope, con)
        try:
            events = _read(con, object_id, actor_id, expected_scope, kind="candidate")
        except LookupError:
            events = []
        if events:
            _fresh(events[-1], actor, actor_id, expected_scope, con)
            return _replay(events, submission_id, request) or _view(events[-1])
        state = {"origin": origin, "admission": "RAW", "revision": 1, "created_at": _now(),
                 "adoption_scope": "local_reference_only", "licensing": "UNKNOWN",
                 "commercial_use_eligible": False, "external_delivery_authorized": False}
        event = _append(con, object_id=object_id, kind="candidate", actor_id=actor_id, scope=expected_scope,
                        submission_id=submission_id, request=request, state=state, previous=None, audit=audit)
        _access(actor, actor_id, expected_scope, action="write", connection=con)
        operator_review._authorize(authorize, actor_id, expected_scope)
        return _view(event)


def get_candidate(candidate_id, *, actor, actor_id, expected_scope):
    with get_repository().connection(read_only=True, wal=False) as con:
        _access(actor, actor_id, expected_scope, action="read", connection=con)
        event = _read(con, candidate_id, actor_id, expected_scope, kind="candidate")[-1]
        _fresh(event, actor, actor_id, expected_scope, con)
        return _view(event)


def transition_candidate(candidate_id, *, actor, actor_id, expected_scope, action, expected_revision,
                         submission_id, authorize, notes):
    _submission(submission_id)
    if not isinstance(notes, str) or not notes.strip() or len(notes) > 2000:
        raise ValueError("LEARNING_REVIEW_NOTES_REQUIRED")
    request = {"action": action, "expected_revision": expected_revision, "notes": notes}
    transitions = {"review": ({"RAW"}, "REVIEWED"), "validate": ({"REVIEWED"}, "VALIDATED"),
                   "adopt": ({"VALIDATED"}, "ADOPTED"), "withdraw": ({"RAW", "REVIEWED", "VALIDATED", "ADOPTED"}, "WITHDRAWN"),
                   "restore": ({"WITHDRAWN"}, "REVIEWED"), "reject": ({"RAW", "REVIEWED", "VALIDATED"}, "REJECTED")}
    if action not in transitions or type(expected_revision) is not int:
        raise ValueError("LEARNING_TRANSITION_INVALID")
    with get_repository().transaction(timeout=10) as con:
        con.execute("BEGIN IMMEDIATE")
        _access(actor, actor_id, expected_scope, action="write", connection=con)
        audit = operator_review._authorize(authorize, actor_id, expected_scope)
        events = _read(con, candidate_id, actor_id, expected_scope, kind="candidate")
        _fresh(events[-1], actor, actor_id, expected_scope, con)
        replay = _replay(events, submission_id, request)
        if replay:
            return replay
        state = events[-1]["state"]
        allowed, target = transitions[action]
        if state["revision"] != expected_revision:
            raise RuntimeError("LEARNING_REVISION_CONFLICT")
        if state["admission"] not in allowed:
            raise ValueError("LEARNING_TRANSITION_INVALID")
        admission = _approval(actor, expected_scope, candidate_id, action, expected_revision, connection=con)
        audit.update(operation_audit_ref=admission.audit_id, effect_resource=admission.resource)
        state = {**state, "revision": expected_revision + 1, "admission": target,
                 "review_notes": notes, "updated_at": _now()}
        event = _append(con, object_id=candidate_id, kind="candidate", actor_id=actor_id, scope=expected_scope,
                        submission_id=submission_id, request=request, state=state, previous=events[-1]["digest"], audit=audit)
        _fresh(event, actor, actor_id, expected_scope, con)
        _approval(actor, expected_scope, candidate_id, action, expected_revision, connection=con)
        operator_review._authorize(authorize, actor_id, expected_scope)
        _commit_effect(con, actor, expected_scope, candidate_id, action, expected_revision, permission.OperationType.CONFIG_MODIFY)
        return _view(event)


def enqueue_candidate(candidate_id, *, actor, actor_id, expected_scope, expected_revision,
                      submission_id, authorize, receiver="Zachary-1012/Zachary-OS-AI"):
    _submission(submission_id)
    if _shared(expected_scope) and receiver != LOCAL_REPO:
        raise PermissionError("LEARNING_SHARED_EXTERNAL_DELIVERY_DENIED")
    contract = current_contract()
    if receiver not in contract["canonical_registry"]:
        raise ValueError("LEARNING_RECEIVER_INVALID")
    request = {"candidate_id": candidate_id, "candidate_revision": expected_revision, "receiver": receiver}
    object_id = _hash({"version": VERSION, **request})
    with get_repository().transaction(timeout=10) as con:
        con.execute("BEGIN IMMEDIATE")
        _access(actor, actor_id, expected_scope, action="write", connection=con)
        audit = operator_review._authorize(authorize, actor_id, expected_scope)
        candidate = _read(con, candidate_id, actor_id, expected_scope, kind="candidate")[-1]
        _fresh(candidate, actor, actor_id, expected_scope, con)
        state = candidate["state"]
        if state["revision"] != expected_revision:
            raise RuntimeError("LEARNING_REVISION_CONFLICT")
        if state["admission"] not in {"VALIDATED", "ADOPTED"}:
            raise ValueError("LEARNING_VALIDATED_CANDIDATE_REQUIRED")
        try:
            events = _read(con, object_id, actor_id, expected_scope, kind="outbox")
        except LookupError:
            events = []
        if events:
            return _replay(events, submission_id, request) or _view(events[-1])
        # No user prose, source body, source URL, credentials or free-form error
        # is copied into this minimized locally staged reference envelope.
        payload = {"contract_version": contract["contract_version"],
                   "cross_product_contract_fingerprint": contract["protocol_fingerprint_sha256"],
                   "source_product": LOCAL_REPO, "source_truth_owner": "Derived Learning Reference",
                   "receiver": receiver, "contribution_id": object_id,
                   "lineage": {"candidate_id": candidate_id, "candidate_revision": expected_revision,
                               "candidate_evidence_ref": candidate["evidence_ref"], "origin_digest": _hash(state["origin"])},
                   "created_at": _now(), "sensitivity": "internal", "license": "UNKNOWN",
                   "training_eligible": False, "commercial_use_eligible": False,
                   "external_delivery_authorized": False, "automatic_production_truth_write": False}
        out = {"origin": state["origin"], "candidate_id": candidate_id, "candidate_revision": expected_revision,
               "revision": 1, "transport": "PENDING", "attempts": 0, "retry_cycle": 0,
               "payload": payload, "payload_sha256": _hash(payload), "created_at": payload["created_at"],
               "delivery_proven": False}
        event = _append(con, object_id=object_id, kind="outbox", actor_id=actor_id, scope=expected_scope,
                        submission_id=submission_id, request=request, state=out, previous=None, audit=audit)
        _fresh(event, actor, actor_id, expected_scope, con)
        operator_review._authorize(authorize, actor_id, expected_scope)
        return _view(event)


def _outbox_current(event, actor, actor_id, scope, con):
    _fresh(event, actor, actor_id, scope, con)
    state = event["state"]
    candidate = _read(con, state["candidate_id"], actor_id, scope, kind="candidate")[-1]["state"]
    if candidate["revision"] != state["candidate_revision"] or candidate["admission"] not in {"VALIDATED", "ADOPTED"}:
        raise PermissionError("LEARNING_CANDIDATE_REVIEW_CHANGED")
    contract = current_contract()
    if (state["payload_sha256"] != _hash(state["payload"])
            or state["payload"]["contract_version"] != contract["contract_version"]
            or state["payload"]["cross_product_contract_fingerprint"] != contract["protocol_fingerprint_sha256"]):
        raise RuntimeError("LEARNING_EXCHANGE_CONTRACT_CHANGED")


def get_outbox(outbox_id, *, actor, actor_id, expected_scope):
    with get_repository().connection(read_only=True, wal=False) as con:
        _access(actor, actor_id, expected_scope, action="read", connection=con)
        event = _read(con, outbox_id, actor_id, expected_scope, kind="outbox")[-1]
        _outbox_current(event, actor, actor_id, expected_scope, con)
        return _view(event)


def list_outbox(*, actor, actor_id, expected_scope, limit=30, offset=0):
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("LEARNING_PAGINATION_INVALID")
    with get_repository().connection(read_only=True, wal=False) as con:
        _access(actor, actor_id, expected_scope, action="read", connection=con)
        rows = con.execute("""SELECT DISTINCT asset_id FROM app_evidence_records WHERE feature_id=?
            AND json_extract(inputs_json,'$.actor_id')=? AND json_extract(inputs_json,'$.kind')='outbox'
            AND COALESCE(json_extract(inputs_json,'$.scope.scope_key'),json_extract(inputs_json,'$.scope.scope_kind'))=? ORDER BY asset_id LIMIT ? OFFSET ?""",
            (FEATURE, actor_id, expected_scope.get("scope_key", expected_scope.get("scope_kind")), limit + 1, offset)).fetchall()
        records = []
        for row in rows[:limit]:
            event = _read(con, row[0], actor_id, expected_scope, kind="outbox")[-1]
            _outbox_current(event, actor, actor_id, expected_scope, con)
            records.append(_view(event))
        return {"records": records, "truncated": len(rows) > limit, "offset": offset}


def transition_outbox(outbox_id, *, actor, actor_id, expected_scope, action, expected_revision,
                      submission_id, authorize, receipt_evidence_ref=None):
    _submission(submission_id)
    if action not in {"stage", "fail", "requeue", "receipt"} or type(expected_revision) is not int:
        raise ValueError("LEARNING_TRANSPORT_ACTION_INVALID")
    request = {"action": action, "expected_revision": expected_revision, "receipt_evidence_ref": receipt_evidence_ref}
    with get_repository().transaction(timeout=10) as con:
        con.execute("BEGIN IMMEDIATE")
        _access(actor, actor_id, expected_scope, action="write", connection=con)
        audit = operator_review._authorize(authorize, actor_id, expected_scope)
        events = _read(con, outbox_id, actor_id, expected_scope, kind="outbox")
        event = events[-1]
        _outbox_current(event, actor, actor_id, expected_scope, con)
        replay = _replay(events, submission_id, request)
        if replay:
            return replay
        state = dict(event["state"])
        if state["revision"] != expected_revision:
            raise RuntimeError("LEARNING_REVISION_CONFLICT")
        status = state["transport"]
        if action in {"stage", "fail"}:
            if status not in {"PENDING", "FAILED"} or state["attempts"] >= 3:
                raise ValueError("LEARNING_TRANSPORT_TRANSITION_INVALID")
            state["attempts"] += 1
            state["transport"] = ("EXPORTED" if action == "stage" else
                                  "DEAD_LETTER" if state["attempts"] == 3 else "FAILED")
            if action == "stage":
                admission = _approval(actor, expected_scope, outbox_id, action, expected_revision, connection=con)
                audit.update(operation_audit_ref=admission.audit_id, effect_resource=admission.resource)
                state["staged_revision"] = expected_revision + 1
                state["staged_at"] = _now()
                state["staged_artifact"] = {"storage": "signed_evidence_envelope", "sha256": state["payload_sha256"]}
            else:
                state["last_error"] = "LOCAL_TRANSPORT_FAILED"  # No raw error/secret retention.
        elif action == "requeue":
            if status not in {"DEAD_LETTER", "REJECTED"}:
                raise ValueError("LEARNING_TRANSPORT_TRANSITION_INVALID")
            admission = _approval(actor, expected_scope, outbox_id, action, expected_revision, connection=con)
            audit.update(operation_audit_ref=admission.audit_id, effect_resource=admission.resource)
            state.update(transport="PENDING", attempts=0, retry_cycle=state["retry_cycle"] + 1)
            for key in ("receipt_evidence_ref", "staged_at", "staged_revision", "staged_artifact"):
                state.pop(key, None)
            state["delivery_proven"] = False
        else:
            if status != "EXPORTED":
                raise ValueError("LEARNING_RECEIPT_REQUIRES_STAGED")
            # External receipt strings or generic signed Evidence are not an
            # authenticated receiver. External delivery adapters are not bound.
            raise PermissionError("LEARNING_RECEIVER_NOT_BOUND")
        state.update(revision=expected_revision + 1, updated_at=_now())
        written = _append(con, object_id=outbox_id, kind="outbox", actor_id=actor_id, scope=expected_scope,
                          submission_id=submission_id, request=request, state=state, previous=event["digest"], audit=audit)
        _outbox_current(written, actor, actor_id, expected_scope, con)
        operator_review._authorize(authorize, actor_id, expected_scope)
        if action in {"requeue", "stage"}:
            _commit_effect(con, actor, expected_scope, outbox_id, action, expected_revision, permission.OperationType.CONFIG_MODIFY)
        return _view(written)


def build_reviewed_context(candidate_ids, *, actor, actor_id, expected_scope):
    """Optional untrusted reference context for the one existing AI Gateway.

    This makes no model call and grants no external-data sharing permission.
    Exact inference consent/source-use validation still belongs to the Gateway.
    """
    if (not isinstance(candidate_ids, list) or not 1 <= len(candidate_ids) <= 10
            or any(not isinstance(value, str) for value in candidate_ids)
            or len(set(candidate_ids)) != len(candidate_ids)):
        raise ValueError("LEARNING_CONTEXT_SELECTION_INVALID")
    references = []
    for candidate_id in candidate_ids:
        candidate = get_candidate(candidate_id, actor=actor, actor_id=actor_id, expected_scope=expected_scope)
        if candidate['admission'] != 'ADOPTED':
            raise PermissionError("LEARNING_CONTEXT_ADOPTION_REQUIRED")
        origin = candidate['origin']
        references.append({'candidate_id': candidate_id, 'revision': candidate['revision'],
                           'evidence_ref': candidate['evidence_ref'], 'feedback': origin['feedback_text'],
                           'source_refs': [x['evidence_ref'] for x in origin['source_bindings']],
                           'claim_type': 'OPERATOR_FEEDBACK', 'business_outcome': origin['business_outcome']})
    return {'schema': VERSION, 'references': references, 'trust': 'untrusted_reference_data',
            'instructions_authority': False, 'external_transmission_authorized': False,
            'production_truth_write': False, 'training_eligible': False}


def receive_local_contribution(outbox_id, *, actor, actor_id, expected_scope, expected_revision,
                               submission_id, authorize, accepted=True):
    """Actual same-owner local receive; this never proves a remote repo received.

    The receiver reopens the staged bytes, verifies the entire current source
    and candidate chain, and persists its own receipt in the same transaction.
    No arbitrary receipt dictionaries, receiver IDs or evidence refs are inputs.
    """
    _submission(submission_id)
    if type(accepted) is not bool or type(expected_revision) is not int:
        raise ValueError("LEARNING_RECEIVE_INPUT_INVALID")
    request = {'action': 'receive_local', 'expected_revision': expected_revision, 'accepted': accepted}
    with get_repository().transaction(timeout=10) as con:
        con.execute('BEGIN IMMEDIATE')
        _access(actor, actor_id, expected_scope, action='write', connection=con)
        audit = operator_review._authorize(authorize, actor_id, expected_scope)
        events = _read(con, outbox_id, actor_id, expected_scope, kind='outbox')
        event = events[-1]
        _outbox_current(event, actor, actor_id, expected_scope, con)
        replay = _replay(events, submission_id, request)
        if replay:
            return replay
        state = dict(event['state'])
        if state['revision'] != expected_revision:
            raise RuntimeError('LEARNING_REVISION_CONFLICT')
        if state['payload']['receiver'] != LOCAL_REPO:
            raise PermissionError('LEARNING_RECEIVER_NOT_BOUND')
        if state['transport'] != 'EXPORTED' or state.get('staged_artifact', {}).get('sha256') != state['payload_sha256']:
            raise ValueError('LEARNING_RECEIPT_REQUIRES_STAGED')
        resource = approval_resource(outbox_id, 'receive_local', expected_revision)
        admission = _effect(actor, expected_scope, permission.OperationType.DATA_IMPORT, resource, connection=con)
        audit.update(operation_audit_ref=admission.audit_id, effect_resource=admission.resource)
        receipt = {'receiver': LOCAL_REPO, 'receiver_owner': 'lumenis.shared.learning.contribution',
                   'outbox_id': outbox_id, 'staged_evidence_ref': event['evidence_ref'],
                   'staged_revision': state['staged_revision'], 'payload_sha256': state['payload_sha256'],
                   'contract_version': state['payload']['contract_version'],
                   'protocol_fingerprint_sha256': state['payload']['cross_product_contract_fingerprint'],
                   'received_at': _now(), 'decision': 'ACKNOWLEDGED' if accepted else 'REJECTED',
                   'scope': expected_scope, 'actor_id': actor_id, 'production_truth_write': False,
                   'admission_changed': False, 'remote_delivery_proven': False}
        state.update(transport=receipt['decision'], receipt=receipt, delivery_proven=True,
                     remote_delivery_proven=False, revision=expected_revision + 1, updated_at=_now())
        written = _append(con, object_id=outbox_id, kind='outbox', actor_id=actor_id, scope=expected_scope,
            submission_id=submission_id, request=request, state=state, previous=event['digest'], audit=audit)
        _outbox_current(written, actor, actor_id, expected_scope, con)
        _effect(actor, expected_scope, permission.OperationType.DATA_IMPORT, resource, connection=con)
        operator_review._authorize(authorize, actor_id, expected_scope)
        _commit_effect(con, actor, expected_scope, outbox_id, 'receive_local', expected_revision, permission.OperationType.DATA_IMPORT)
        return _view(written)


def _business_material(report, review_id, actor, actor_id, scope, bindings):
    from api_dual_domain import BusinessDecisionWorkflow
    reference = review_id[len('business:'):].split('|')
    if len(reference) != 2 or not re.fullmatch(r'app_evidence_records:[1-9][0-9]*', reference[1]):
        raise ValueError('LEARNING_BUSINESS_REVISION_REQUIRED')
    work_id, expected_business_revision = reference
    material = BusinessDecisionWorkflow.read_learning_material(work_id, actor=actor, actor_ref=actor_id,
        scope=scope, expected_revision=expected_business_revision)
    if (material['job_id'] != report['snapshot']['job_id']
            or material['artifact_hash'] != report['row']['artifact_hash']):
        raise PermissionError('LEARNING_BUSINESS_REPORT_BINDING_INVALID')
    return {'job_id': material['job_id'], 'artifact_hash': material['artifact_hash'],
            'review_id': review_id, 'business_work_id': work_id, 'business_revision': material['revision'],
            'review_evidence_ref': material['review_evidence_ref'], 'evaluation_id': material['evaluation_id'],
            'outcome_evidence_ref': material['outcome_evidence_ref'],
            'feedback_decision': material['feedback_decision'], 'feedback_text': material['feedback_text'],
            'limitations': material['limitations'], 'source_bindings': bindings,
            'business_outcome': material['business_outcome'], 'outcome_state': material['outcome_state']}


def _shared_material(report, review_id, actor, actor_id, scope, connection):
    observed = source_brief_job.read_shared_report_review(report['snapshot']['job_id'], review_id, actor=actor, actor_id=actor_id)
    if observed['state'] != 'recorded':
        raise RuntimeError('LEARNING_SHARED_EVALUATION_PENDING_RECOVERY')
    review = saved_work.read_committed_work(review_id, actor=actor, scope=scope, connection=connection)
    binding = review['document']['payload'].get('shared_report_review', {})
    if (binding.get('schema') != 'shared-report-review/v1' or binding.get('job_id') != report['snapshot']['job_id']
            or binding.get('artifact_hash') != report['row']['artifact_hash'] or binding.get('actor_id') != actor_id
            or binding.get('decision') not in {'use_for_next_step', 'request_changes', 'reject'}):
        raise PermissionError('LEARNING_SHARED_REVIEW_BINDING_INVALID')
    from lumenis.shared.evaluation.recorder import get_evaluation_record
    review_hash = review['artifact']['sha256']
    evaluation_id = hashlib.sha256(('shared-report-review:' + review_id + ':' + review_hash).encode()).hexdigest()
    evaluation = get_evaluation_record(evaluation_id)
    expected_metadata = {**binding, 'scope': scope, 'review_id': review_id, 'review_artifact_hash': review_hash,
        'evaluation_basis': 'Operator feedback only; business effect and fact verification unknown.'}
    if (evaluation is None or evaluation.get('source') != 'shared_report_review'
            or evaluation.get('metric_name') != 'operator_disposition' or evaluation.get('metric_value') is not None
            or evaluation.get('status') != 'unknown' or evaluation.get('dimension') != 'report'
            or evaluation.get('evidence_ref') != 'saved_work:' + review_id + ':' + review_hash
            or json.loads(evaluation.get('metadata') or '{}') != expected_metadata):
        raise RuntimeError('LEARNING_SHARED_EVALUATION_PENDING_RECOVERY')
    # The SourceBrief owner has already reopened each original private document
    # and its current access/rights. Bind these exact immutable source versions.
    resolved = source_brief_job.resolve_report_sources(report['snapshot']['job_id'], actor=actor, actor_id=actor_id,
                                                       expected_scope=scope, connection=connection)
    sources = resolved['records']
    bindings = [{'source_id': s['source_id'], 'evidence_ref': s['evidence_id'],
                 'content_hash': s['content_hash'], 'rights': s['rights'], 'version': s['source_version']}
                for s in sources]
    return {'job_id': report['snapshot']['job_id'], 'artifact_hash': report['row']['artifact_hash'],
            'review_id': review_id, 'review_evidence_ref': review_id,
            'review_artifact_hash': review['artifact']['sha256'],
            'evaluation_id': evaluation_id,
            'feedback_decision': binding['decision'], 'feedback_text': binding['notes'],
            'source_bindings': bindings, 'business_outcome': 'NOT_OBSERVED',
            **_hypothesis_binding(resolved['report'])}


def create_business_candidate(*, work_id, expected_business_revision, job_id, actor, actor_id,
                              expected_scope, submission_id, authorize):
    if (not isinstance(work_id, str) or '|' in work_id or not work_id
            or not isinstance(expected_business_revision, str)
            or not re.fullmatch(r'app_evidence_records:[1-9][0-9]*', expected_business_revision)):
        raise ValueError('LEARNING_BUSINESS_REFERENCE_INVALID')
    return create_candidate(job_id=job_id, review_id='business:' + work_id + '|' + expected_business_revision,
                            actor=actor, actor_id=actor_id, expected_scope=expected_scope,
                            submission_id=submission_id, authorize=authorize)


def validate_learning_exchange_resource(resource, *, actor, scope, operation, connection=None):
    """Permission-owner validator for exact current Shared learning effects.

    The hash binds an immutable signed object revision, hence its source/review,
    candidate and minimized payload/receiver. Arbitrary hashes or foreign rows
    cannot make a valid resource. This performs no writes or inference.
    """
    from contextlib import nullcontext
    if (not _shared(scope) or type(operation) is not permission.OperationType
            or operation not in {permission.OperationType.CONFIG_MODIFY, permission.OperationType.DATA_IMPORT}
            or not isinstance(resource, str) or not re.fullmatch(r'learning-exchange:[0-9a-f]{64}', resource)):
        return False
    actor_id = _actor_ref(actor)
    try:
        context = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
        with context as con:
            _access(actor, actor_id, scope, action='write', connection=con)
            rows = con.execute("""SELECT DISTINCT asset_id FROM app_evidence_records WHERE feature_id=?
                AND json_valid(inputs_json) AND json_extract(inputs_json,'$.actor_id')=?
                AND json_extract(inputs_json,'$.scope.scope_kind')='shared_workspace'""", (FEATURE, actor_id)).fetchall()
            for row in rows:
                for kind in ('candidate', 'outbox'):
                    try:
                        events = _read(con, row[0], actor_id, scope, kind=kind)
                    except PermissionError:
                        continue
                    latest = events[-1]
                    actions = (('receive_local',) if operation is permission.OperationType.DATA_IMPORT else
                               ('review', 'validate', 'adopt', 'withdraw', 'restore', 'reject') if kind == 'candidate'
                               else ('stage', 'requeue'))
                    for action in actions:
                        # The current revision is eligible before the write. The
                        # immediately preceding revision is eligible solely for
                        # the exact just-written transition's commit recheck.
                        revision = latest['state']['revision']
                        candidates = [revision]
                        req = latest['inputs']['request']
                        if req.get('action') == action and req.get('expected_revision') == revision - 1:
                            candidates.append(revision - 1)
                        for selected in candidates:
                            if approval_resource(row[0], action, selected) != resource:
                                continue
                            prior = events[selected - 1]
                            if kind == 'candidate':
                                allowed = {'review': {'RAW'}, 'validate': {'REVIEWED'}, 'adopt': {'VALIDATED'},
                                           'withdraw': {'RAW', 'REVIEWED', 'VALIDATED', 'ADOPTED'},
                                           'restore': {'WITHDRAWN'}, 'reject': {'RAW', 'REVIEWED', 'VALIDATED'}}
                                if action not in allowed or prior['state']['admission'] not in allowed[action]:
                                    return False
                                _fresh(latest, actor, actor_id, scope, con)
                            else:
                                _outbox_current(latest, actor, actor_id, scope, con)
                                allowed = {'stage': {'PENDING', 'FAILED'}, 'requeue': {'DEAD_LETTER', 'REJECTED'},
                                           'receive_local': {'EXPORTED'}}
                                if prior['state']['transport'] not in allowed[action]:
                                    return False
                                if (action == 'receive_local'
                                        and (prior['state']['payload']['receiver'] != LOCAL_REPO
                                             or prior['state'].get('staged_artifact', {}).get('sha256') != prior['state']['payload_sha256'])):
                                    return False
                            return True
        return False
    except (ValueError, TypeError, KeyError, LookupError, PermissionError, RuntimeError):
        return False


def list_candidates(*, actor, actor_id, expected_scope, limit=30, offset=0):
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError('LEARNING_PAGINATION_INVALID')
    with get_repository().connection(read_only=True, wal=False) as con:
        _access(actor, actor_id, expected_scope, action='read', connection=con)
        rows = con.execute("""SELECT DISTINCT asset_id FROM app_evidence_records WHERE feature_id=?
            AND json_extract(inputs_json,'$.actor_id')=? AND json_extract(inputs_json,'$.kind')='candidate'
            AND COALESCE(json_extract(inputs_json,'$.scope.scope_key'),json_extract(inputs_json,'$.scope.scope_kind'))=?
            ORDER BY asset_id LIMIT ? OFFSET ?""",
            (FEATURE, actor_id, expected_scope.get('scope_key', expected_scope.get('scope_kind')), limit + 1, offset)).fetchall()
        records = []
        for row in rows[:limit]:
            event = _read(con, row[0], actor_id, expected_scope, kind='candidate')[-1]
            _fresh(event, actor, actor_id, expected_scope, con)
            records.append(_view(event))
        return {'records': records, 'truncated': len(rows) > limit, 'offset': offset}
