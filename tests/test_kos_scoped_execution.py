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
