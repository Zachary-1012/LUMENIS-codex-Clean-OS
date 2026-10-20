"""Exact approval workflow and fake-adapter receipt tests: no real external action."""
import pytest
from tests.test_saved_document_workflow import workspace


def _registered(workspace):
    import subject_registry
    with workspace["repo"].transaction() as con:
        subject_registry.ensure_schema(con)
        con.execute("""INSERT INTO lumenis_subject_registry
            (subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh,
             name_en_norm, name_zh_norm, created_at, updated_at, status)
            VALUES ('HCG-SUBJECT','HCG-BRAND','BMP','brand','HCG','测试','hcg','测试','now','now','active')""")
    return {"domain_id": "zbmp", "subject_id": None, "brand_focus_id": "HCG-BRAND", "global_scope": False}


def _approve_call(ws, call):
    from kos_ops import ScopedOperationApprovalRequired
    with pytest.raises(ScopedOperationApprovalRequired) as needed:
        call()
    ws["gate"].grant_approval("db_write", resource=needed.value.resource, granted_by="isolated-test-user")
    return call()


def test_scoped_hcg_requires_real_approval_and_receipt(workspace, monkeypatch):
    import kos_execution as owner
    from lumenis.shared.reporting.saved_work import _digest
    ws = workspace
    scope = _registered(ws)
    args = dict(actor=ws["actor"], scope=scope, action_type="paid_media", target_author_id="synthetic-author",
                payload={"budget": 10, "destination": "synthetic-no-network"}, request_id="hcg-test-0001")
    first = _approve_call(ws, lambda: owner.create_scoped_execution(**args))
    eid = first["execution"]["execution_id"]
    assert first["execution"]["status"] == "AI_GENERATED"
    with pytest.raises(PermissionError, match="HUMAN_APPROVAL_REQUIRED"):
        owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)
    _approve_call(ws, lambda: owner.transition_scoped_execution(eid, "PENDING_HUMAN_REVIEW", actor=ws["actor"], scope=scope))
    approved = _approve_call(ws, lambda: owner.transition_scoped_execution(eid, "HUMAN_APPROVED", actor=ws["actor"], scope=scope))
    assert approved["execution"]["approved_at"]
    blocked = owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)
    assert blocked["code"] == "KOS_CHANNEL_NOT_CONFIGURED"
    assert blocked["execution"]["status"] == "HUMAN_APPROVED"
    with pytest.raises(ValueError, match="PROVIDER_RECEIPT"):
        owner.transition_scoped_execution(eid, "SUCCESS", actor=ws["actor"], scope=scope)
    class FakeAdapter:
        calls = 0
        receipt = None
        def authorize(self, **kwargs):
            assert kwargs["scope"] == scope
            return True
        def execute(self, *, execution_id, request):
            self.calls += 1
            self.receipt = {"status": "SUCCESS", "reference": "synthetic-receipt-001",
                            "execution_id": execution_id, "request_sha256": _digest(request)}
            return self.receipt
        def lookup_receipt(self, **kwargs):
            return self.receipt
        def verify_receipt(self, receipt, *, execution_id, request):
            return receipt == self.receipt and receipt["execution_id"] == execution_id and receipt["request_sha256"] == _digest(request)
    adapter = FakeAdapter()
    monkeypatch.setitem(owner._SCOPED_EXECUTION_ADAPTERS, "paid_media", adapter)
    complete = _approve_call(ws, lambda: owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope))
    assert complete["ok"] and complete["receipt"]["reference"] == "synthetic-receipt-001"
    assert adapter.calls == 1
    replay = owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)
    assert replay["replayed"] and adapter.calls == 1
    with ws["repo"].transaction() as con:
        con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE brand_focus_id='HCG-BRAND'")
    with pytest.raises(ValueError, match="PERMISSION_DENIED"):
        owner.list_scoped_executions(actor=ws["actor"], scope=scope)
    with ws["repo"].transaction() as con:
        con.execute("UPDATE lumenis_subject_registry SET status='active' WHERE brand_focus_id='HCG-BRAND'")
    recovered = owner.list_scoped_executions(actor=ws["actor"], scope=scope)
    assert recovered[0]["execution_id"] == eid
    assert recovered[0]["status"] == "SUCCESS"


def _scoped_list_record(workspace, *, request_id="kos-list-0001"):
    import kos_execution as owner
    scope = _registered(workspace)
    args = dict(actor=workspace["actor"], scope=scope, action_type="paid_media",
                target_author_id="synthetic-author", payload={"budget": 10}, request_id=request_id)
    result = _approve_call(workspace, lambda: owner.create_scoped_execution(**args))
    return owner, scope, result["execution"]


def test_scoped_execution_list_ignores_unrelated_malformed_rows(workspace):
    owner, scope, created = _scoped_list_record(workspace)
    context = owner._scoped_context(workspace["actor"], scope)
    caller = context.get("principal_ref") or "actor:" + str(context["actor_id"])
    with workspace["repo"].transaction() as con:
        con.execute("""INSERT INTO kos_executions
            (execution_id, action_type, target_author_id, target_brand, payload, status, actor,
             created_at, version)
            VALUES ('foreign-actor-bad', 'paid_media', 'private', ?, '{', 'AI_GENERATED', ?, 'now', 'scoped-v1')""",
            (scope["brand_focus_id"], "another-actor"))
        con.execute("""INSERT INTO kos_executions
            (execution_id, action_type, target_author_id, target_brand, payload, status, actor,
             created_at, version)
            VALUES ('foreign-brand-bad', 'paid_media', 'private', 'OTHER-BRAND', '{', 'AI_GENERATED', ?, 'now', 'scoped-v1')""",
            (caller,))
        con.execute("""INSERT INTO kos_executions
            (execution_id, action_type, target_author_id, target_brand, payload, status, actor,
             created_at, version)
            VALUES ('legacy-bad', 'paid_media', 'private', ?, '{', 'AI_GENERATED', ?, 'now', 'v1')""",
            (scope["brand_focus_id"], caller))

    rows = owner.list_scoped_executions(actor=workspace["actor"], scope=scope)
    assert [row["execution_id"] for row in rows] == [created["execution_id"]]
    assert owner.list_scoped_executions(actor=workspace["actor"], scope=scope,
                                        action_type="outreach_send") == []


@pytest.mark.parametrize("corruption", ["invalid_json"])
def test_scoped_execution_list_surfaces_corruption_inside_exact_scope(workspace, corruption):
    import json
    import kos_execution as owner
    owner, scope, created = _scoped_list_record(workspace)
    with workspace["repo"].transaction() as con:
        if corruption == "invalid_json":
            con.execute("UPDATE kos_executions SET payload='{' WHERE execution_id=?",
                        (created["execution_id"],))
        else:
            payload = json.loads(created["payload"])
            payload["context"]["brand_focus_id"] = "OTHER-BRAND"
            con.execute("UPDATE kos_executions SET payload=? WHERE execution_id=?",
                        (json.dumps(payload), created["execution_id"]))
    with pytest.raises(ValueError, match="KOS_EXECUTION_BINDING_INVALID"):
        owner.list_scoped_executions(actor=workspace["actor"], scope=scope)
    with pytest.raises(ValueError, match="KOS_EXECUTION_BINDING_INVALID"):
        owner.list_scoped_executions(actor=workspace["actor"], scope=scope, status="SUCCESS")


@pytest.mark.parametrize("column, corrupted", [
    ("actor", "another-actor"),
    ("target_brand", "OTHER-BRAND"),
    ("version", "v1"),
])
def test_scoped_execution_list_detects_corrupt_denormalized_binding(workspace, column, corrupted):
    import kos_execution as owner
    owner, scope, created = _scoped_list_record(workspace)
    # Keep the authoritative payload bound to this caller and alter only the
    # query/index columns. The row must remain visible as an integrity failure.
    with workspace["repo"].transaction() as con:
        con.execute(f"UPDATE kos_executions SET {column}=? WHERE execution_id=?",
                    (corrupted, created["execution_id"]))
    with pytest.raises(ValueError, match="KOS_EXECUTION_BINDING_INVALID"):
        owner.list_scoped_executions(actor=workspace["actor"], scope=scope)


def test_scoped_execution_list_preserves_rejection_state(workspace):
    import kos_execution as owner
    owner, scope, created = _scoped_list_record(workspace, request_id="kos-list-0002")
    pending = _approve_call(workspace, lambda: owner.transition_scoped_execution(
        created["execution_id"], "PENDING_HUMAN_REVIEW", actor=workspace["actor"], scope=scope))
    rejected = _approve_call(workspace, lambda: owner.transition_scoped_execution(
        created["execution_id"], "REJECTED", actor=workspace["actor"], scope=scope))
    assert pending["execution"]["status"] == "PENDING_HUMAN_REVIEW"
    assert rejected["execution"]["status"] == "REJECTED"
    rows = owner.list_scoped_executions(actor=workspace["actor"], scope=scope, status="REJECTED")
    assert [row["execution_id"] for row in rows] == [created["execution_id"]]


def test_scoped_execution_list_reports_verified_provider_failure(workspace, monkeypatch):
    import kos_execution as owner
    from lumenis.shared.reporting.saved_work import _digest
    owner, scope, created = _scoped_list_record(workspace, request_id="kos-list-0003")
    _approve_call(workspace, lambda: owner.transition_scoped_execution(
        created["execution_id"], "PENDING_HUMAN_REVIEW", actor=workspace["actor"], scope=scope))
    _approve_call(workspace, lambda: owner.transition_scoped_execution(
        created["execution_id"], "HUMAN_APPROVED", actor=workspace["actor"], scope=scope))

    class FailedAdapter:
        def authorize(self, **kwargs):
            return True
        def execute(self, *, execution_id, request):
            return {"status": "FAILED", "reference": "synthetic-failure-receipt",
                    "execution_id": execution_id, "request_sha256": _digest(request)}
        def lookup_receipt(self, **kwargs):
            return None
        def verify_receipt(self, receipt, *, execution_id, request):
            return (receipt.get("status") == "FAILED" and receipt.get("execution_id") == execution_id
                    and receipt.get("request_sha256") == _digest(request))

    monkeypatch.setitem(owner._SCOPED_EXECUTION_ADAPTERS, "paid_media", FailedAdapter())
    result = _approve_call(workspace, lambda: owner.execute_scoped_execution(
        created["execution_id"], actor=workspace["actor"], scope=scope))
    assert result["ok"] is False
    assert result["receipt"]["status"] == "FAILED"
    rows = owner.list_scoped_executions(actor=workspace["actor"], scope=scope, status="FAILED")
    assert [row["execution_id"] for row in rows] == [created["execution_id"]]
    assert rows[0]["evidence_ref"] == "synthetic-failure-receipt"


def test_scoped_execution_list_skips_row_whose_intact_payload_belongs_to_another_brand(workspace):
    import json
    owner, scope, created = _scoped_list_record(workspace)
    with workspace["repo"].transaction() as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(lumenis_subject_registry)")]
        row = con.execute("SELECT * FROM lumenis_subject_registry WHERE brand_focus_id=?",
                          (scope["brand_focus_id"],)).fetchone()
        values = dict(zip(cols, row))
        values.pop("id", None)
        values["brand_focus_id"] = "OTHER-VALID-BRAND"
        for key in ("subject_id", "subject_key", "slug", "name_en_norm", "name_zh_norm", "name_en", "name_zh"):
            if key in values and isinstance(values[key], str):
                values[key] = values[key] + "-other"
        con.execute(
            f"INSERT INTO lumenis_subject_registry ({','.join(values)}) VALUES ({','.join('?' * len(values))})",
            tuple(values.values()),
        )
        payload = json.loads(created["payload"])
        payload["context"]["brand_focus_id"] = "OTHER-VALID-BRAND"
        con.execute("UPDATE kos_executions SET payload=? WHERE execution_id=?",
                    (json.dumps(payload), created["execution_id"]))
    # The other brand's intact row must not block this caller's history.
    assert owner.list_scoped_executions(actor=workspace["actor"], scope=scope) == []


def _corrupt_payload_context(workspace, created, **changes):
    import json
    with workspace["repo"].transaction() as con:
        payload = json.loads(created["payload"])
        payload["context"].update(changes)
        con.execute("UPDATE kos_executions SET payload=? WHERE execution_id=?",
                    (json.dumps(payload), created["execution_id"]))


def test_intact_payload_for_unregistered_foreign_brand_stays_visible_corruption(workspace):
    owner, scope, created = _scoped_list_record(workspace)
    _corrupt_payload_context(workspace, created, brand_focus_id="OTHER-BRAND")
    with pytest.raises(ValueError, match="KOS_EXECUTION_BINDING_INVALID"):
        owner.list_scoped_executions(actor=workspace["actor"], scope=scope)


def test_nonexistent_foreign_actor_in_payload_stays_visible_corruption(workspace):
    owner, scope, created = _scoped_list_record(workspace)
    _corrupt_payload_context(workspace, created, actor_id=987654321)
    with pytest.raises(ValueError, match="KOS_EXECUTION_BINDING_INVALID"):
        owner.list_scoped_executions(actor=workspace["actor"], scope=scope)


def test_corrupted_principal_kind_in_payload_stays_visible_corruption(workspace):
    owner, scope, created = _scoped_list_record(workspace)
    _corrupt_payload_context(workspace, created, principal_kind="forged", principal_ref="workspace:local")
    with pytest.raises(ValueError, match="KOS_EXECUTION_BINDING_INVALID"):
        owner.list_scoped_executions(actor=workspace["actor"], scope=scope)
