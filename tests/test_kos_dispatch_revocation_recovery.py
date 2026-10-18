"""Synthetic reproduction only. No network or production writes."""

import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_kos_scoped_execution import _registered, _approve_call


def test_dispatch_exact_token_revoked_after_status_transition(workspace, monkeypatch):
    import kos_execution as owner
    from lumenis.shared.reporting.saved_work import _digest

    ws = workspace
    scope = _registered(ws)
    eid = _approve_call(
        ws,
        lambda: owner.create_scoped_execution(
            actor=ws["actor"],
            scope=scope,
            action_type="paid_media",
            target_author_id="synthetic-author",
            payload={"budget": 10},
            request_id="revocation-probe-0001",
        ),
    )["execution"]["execution_id"]
    for status in ["PENDING_HUMAN_REVIEW", "HUMAN_APPROVED"]:
        _approve_call(
            ws,
            lambda: owner.transition_scoped_execution(
                eid, status, actor=ws["actor"], scope=scope
            ),
        )

    class Adapter:
        auth_count = 0
        calls = 0
        receipt = None
        resource = None

        def authorize(self, **kwargs):
            self.auth_count += 1
            if self.resource and self.auth_count == 2:
                token = ws["gate"].get_valid_approval_token(
                    "db_write", self.resource, exact=True
                )
                assert token is not None
                assert ws["gate"].revoke_approval(token)
            return True

        def execute(self, *, execution_id, request):
            assert (
                ws["gate"].get_valid_approval_token(
                    "db_write", self.resource, exact=True
                )
                is not None
            )
            self.calls += 1
            self.receipt = {"status": "SUCCESS", "reference": "synthetic-no-network"}
            return self.receipt

        def lookup_receipt(self, **kwargs):
            return self.receipt

        def verify_receipt(self, receipt, **kwargs):
            return receipt == self.receipt

    adapter = Adapter()
    monkeypatch.setitem(owner._SCOPED_EXECUTION_ADAPTERS, "paid_media", adapter)
    from kos_ops import ScopedOperationApprovalRequired

    try:
        owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)
    except ScopedOperationApprovalRequired as exc:
        adapter.resource = exc.resource
    assert adapter.resource
    ws["gate"].grant_approval(
        "db_write", resource=adapter.resource, granted_by="synthetic"
    )
    adapter.auth_count = 0
    with pytest.raises(ScopedOperationApprovalRequired):
        owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)
    assert adapter.calls == 0
    assert (
        owner.list_scoped_executions(actor=ws["actor"], scope=scope)[0]["status"]
        == "HUMAN_APPROVED"
    )
    print(
        "PASS: exact dispatch token revoked before execute; synthetic effect was NOT called; no SUCCESS stored"
    )

    ws["gate"].grant_approval(
        "db_write", resource=adapter.resource, granted_by="synthetic-reauthorize"
    )
    retry = owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)
    assert retry["ok"] and adapter.calls == 1
    assert owner.execute_scoped_execution(eid, actor=ws["actor"], scope=scope)[
        "replayed"
    ]
    assert adapter.calls == 1
