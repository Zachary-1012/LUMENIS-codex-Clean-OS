"""Regression coverage for account and open-workspace event review identities."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as app_module
from lumenis.system.security import permission


@pytest.mark.parametrize(
    ("action", "state", "response_key"),
    [("confirm", 1, "confirmed"), ("reject", 2, "rejected")],
)
def test_event_review_routes_accept_server_local_workspace_principal(
        monkeypatch, action, state, response_key):
    monkeypatch.setattr(
        permission, "_local_workspace_transport_allowed", lambda **_kwargs: True
    )
    with app_module.app.test_request_context(
            f"/api/event-review/event-1/{action}", method="POST"):
        principal = permission.resolve_local_workspace_principal(
            module="reports", action="write"
        )
    assert permission._is_server_local_workspace_principal(principal)

    scope = {
        "domain_id": "cth", "product_id": "CTH", "subject_id": "SUBJECT-A",
        "brand_focus_id": None, "global_scope": False,
    }
    monkeypatch.setattr(
        app_module, "_resolve_web_scope",
        lambda received_action, *, module: (principal, scope, [], None),
    )
    calls = []
    monkeypatch.setattr(
        app_module, "_event_set_review",
        lambda event_id, received_state, received_scope, by: (
            calls.append((event_id, received_state, received_scope, by))
            or {"events": 1, "notes": 1}
        ),
    )

    handler = (app_module.api_event_review_confirm if action == "confirm"
               else app_module.api_event_review_reject)
    with app_module.app.test_request_context(
            f"/api/event-review/event-1/{action}", method="POST"):
        response = handler("event-1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True and payload[response_key] is True
    assert calls == [("event-1", state, scope, "workspace:local")]


def test_event_review_actor_ref_keeps_account_audit_identity():
    assert app_module._event_review_actor_ref({"id": 57, "role": "owner"}) == "57"


def test_event_review_actor_ref_rejects_untrusted_identity_shape():
    with pytest.raises(PermissionError, match="AUTH_REQUIRED"):
        app_module._event_review_actor_ref({"id": "57"})
