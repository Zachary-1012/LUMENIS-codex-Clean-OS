"""Real local stdio discovery plus existing signed metadata approval boundary."""

import json
import sqlite3
import sys
import uuid

import pytest

from tests.test_skill_metadata_lifecycle import (
    registry,
    canonical_gate,
    _row,
    _workspace_app,
    _workspace_admission,
)
from tests.test_mcp_protocol_contract import server, TOOL
from lumenis.shared.agents.skills import lifecycle as lc


def prepare_fixture(registry, tmp_path, monkeypatch):
    path, package = registry
    import mcp_skill_runtime

    monkeypatch.setattr(mcp_skill_runtime, "PACKAGE_ROOT", tmp_path)
    command, args = server(package)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE skills_registry SET runtime='mcp',entrypoint=?,tools_json=?,permissions_granted_json=? WHERE skill_id='owned.read'",
            (
                json.dumps({"command": command[0], "args": args}),
                json.dumps(["read_signal"]),
                json.dumps(["mcp:tools/call", "read_only"]),
            ),
        )
    return lc.prepare_skill_metadata_change(
        "owned.read", "review_mcp_contract", operation_id=str(uuid.uuid4()), confirm_process=True
    )


def test_review_prepare_requires_process_consent(registry):
    before = _row(registry[0])
    with pytest.raises(PermissionError, match="PROCESS_CONFIRMATION"):
        lc.prepare_skill_metadata_change(
            "owned.read", "review_mcp_contract", operation_id=str(uuid.uuid4())
        )
    assert _row(registry[0]) == before


def test_review_discovery_exact_approval_and_signed_history(
    registry, canonical_gate, tmp_path, monkeypatch
):
    candidate = prepare_fixture(registry, tmp_path, monkeypatch)
    before = _row(registry[0])
    preview = candidate.to_dict()
    metadata = json.loads(preview["after_metadata"]["compatibility_json"])
    assert metadata["mcp_reviewed_tools"] == [TOOL]
    assert preview["state"] == "PREPARED_NOT_APPROVED"
    assert preview["after_metadata"]["status"] == "disabled"
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, resource, token = _workspace_admission(candidate, canonical_gate, grant=False)
        with pytest.raises(PermissionError):
            lc.apply_skill_metadata_change(candidate, **args)
        assert _row(registry[0]) == before
        args, resource, token = _workspace_admission(candidate, canonical_gate)
        result = lc.apply_skill_metadata_change(candidate, **args)
    assert result["state"] == "applied"
    after = _row(registry[0])
    assert after["status"] == "disabled"
    assert after["install_path"] == before["install_path"]
    assert after["permissions_granted_json"] == before["permissions_granted_json"]
    assert lc.read_skill_version_history("owned.read")[0]["signature_verified"] is True


def test_registry_change_invalidates_review(registry, canonical_gate, tmp_path, monkeypatch):
    candidate = prepare_fixture(registry, tmp_path, monkeypatch)
    with sqlite3.connect(registry[0]) as conn:
        conn.execute("UPDATE skills_registry SET version='changed' WHERE skill_id='owned.read'")
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, resource, token = _workspace_admission(candidate, canonical_gate)
        with pytest.raises((PermissionError, ValueError, RuntimeError)):
            lc.apply_skill_metadata_change(candidate, **args)
    assert not json.loads(_row(registry[0])["compatibility_json"] or "{}").get("mcp_tool_contracts")


@pytest.mark.parametrize(
    "field,value",
    [
        ("permissions_granted_json", '["write"]'),
        ("entrypoint", "evil"),
        ("install_path", "/evil"),
        ("version", "new"),
        ("status", "enabled"),
        ("tools_json", '["evil"]'),
        ("input_schema_json", "{}"),
    ],
)
def test_review_fence_rejects_any_unrelated_metadata_change(
    registry, tmp_path, monkeypatch, field, value
):
    from dataclasses import replace
    from lumenis.system.security.effect_fence import EffectFence

    candidate = prepare_fixture(registry, tmp_path, monkeypatch)
    after = json.loads(candidate._after_json)
    if after[field] == value:
        value = "changed"
    after[field] = value
    forged = replace(candidate, _after_json=lc._json(after), after_sha256=lc._hash(after))
    forged = replace(forged, candidate_sha256=lc._hash(lc._candidate_material(forged)))
    with pytest.raises(ValueError, match="SCOPE_INVALID"):
        EffectFence._skill_metadata_candidate(forged)


def test_rediscovery_requires_new_exact_approval(registry, canonical_gate, tmp_path, monkeypatch):
    old = prepare_fixture(registry, tmp_path, monkeypatch)
    package = registry[1]
    server(package, tool={**TOOL, "inputSchema": {"type": "object"}})
    new = lc.prepare_skill_metadata_change(
        "owned.read", "review_mcp_contract", operation_id=str(uuid.uuid4()), confirm_process=True
    )
    assert old.candidate_sha256 != new.candidate_sha256
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, resource, token = _workspace_admission(old, canonical_gate)
        with pytest.raises(PermissionError):
            lc.apply_skill_metadata_change(new, **args)
        with pytest.raises(PermissionError):
            lc.apply_skill_metadata_change(old, **{**args, "domain_id": "bmp"})


from tests.test_skill_metadata_permission import registry as account_registry


@pytest.fixture
def api_client(account_registry, canonical_gate, tmp_path, monkeypatch):
    from flask import Flask
    from account import service
    from account.api import account_bp, _MCP_REVIEW_CANDIDATES
    import mcp_skill_runtime

    monkeypatch.setattr(service, "_initialized", True)
    monkeypatch.setattr(mcp_skill_runtime, "PACKAGE_ROOT", tmp_path)
    package = tmp_path / "api-package"
    package.mkdir()
    command, args = server(package)
    with sqlite3.connect(account_registry) as conn:
        for sql in [
            "ALTER TABLE v4_users ADD COLUMN email TEXT",
            "ALTER TABLE v4_users ADD COLUMN must_change_password INTEGER DEFAULT 0",
            "ALTER TABLE v4_sessions ADD COLUMN ip TEXT",
            "ALTER TABLE v4_sessions ADD COLUMN user_agent TEXT",
        ]:
            conn.execute(sql)
        conn.execute(
            "UPDATE skills_registry SET runtime='mcp',entrypoint=?,tools_json=?,permissions_granted_json=?, install_path=? WHERE skill_id='owned.read'",
            (
                json.dumps({"command": command[0], "args": args}),
                json.dumps(["read_signal"]),
                json.dumps(["mcp:tools/call", "read_only"]),
                str(package),
            ),
        )
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table

    ensure_skill_executions_table()
    _MCP_REVIEW_CANDIDATES.clear()
    app = Flask(__name__)
    app.register_blueprint(account_bp)
    return app.test_client(), account_registry


def test_owner_http_contract_review_is_exact_and_one_shot(api_client):
    client, path = api_client
    headers = {"Authorization": "Bearer valid-owner-session"}
    base = "/api/system/account/skills/owned.read/mcp/contract"
    assert client.post(base + "/prepare", json={"confirm_process": True}).status_code == 401
    assert (
        client.post(
            base + "/prepare",
            headers={"Authorization": "Bearer valid-member-session"},
            json={"confirm_process": True},
        ).status_code
        == 403
    )
    result = client.post(base + "/prepare", headers=headers, json={"confirm_process": True})
    assert result.status_code == 200, result.json
    fingerprint = result.json["candidate"]["candidate_sha256"]
    assert (
        client.post(
            base + "/approve", headers=headers, json={"confirm": True, "candidate_sha256": "wrong"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            base + "/approve", headers=headers, json={"candidate_sha256": fingerprint}
        ).status_code
        == 400
    )
    approved = client.post(
        base + "/approve", headers=headers, json={"confirm": True, "candidate_sha256": fingerprint}
    )
    assert approved.status_code == 200, approved.json
    assert approved.json["result"]["metadata"]["status"] == "disabled"
    assert (
        client.post(
            base + "/approve",
            headers=headers,
            json={"confirm": True, "candidate_sha256": fingerprint},
        ).status_code
        == 409
    )


def test_old_argv_route_cannot_self_authorize(api_client):
    client, path = api_client
    headers = {"Authorization": "Bearer valid-owner-session"}
    for route in ("call", "discover"):
        result = client.post(
            "/api/system/account/skills/source/mcp/" + route,
            headers=headers,
            json={
                "command": [sys.executable],
                "confirm_process": True,
                "permissions_granted": ["read_only"],
                "human_approved": True,
            },
        )
        assert result.status_code == 400
        assert result.json["state"] == "REGISTERED_SKILL_REQUIRED"


def test_owner_mcp_review_activate_enable_execute_full_loop(api_client, tmp_path, monkeypatch):
    client, path = api_client
    import mcp_skill_runtime as runtime
    import shutil

    package = tmp_path / "api-package"
    (package / "scripts").mkdir()
    (package / "dist" / "src").mkdir(parents=True)
    (package / "node_modules").mkdir()
    (package / "manifest.json").write_text(json.dumps({"name": "owned.read", "version": "1.0.0"}))
    (package / "package.json").write_text("{}")
    (package / "dist" / "src" / "index.js").write_text("// local fixture\n")
    launcher = package / "scripts" / "launcher.mjs"
    launcher.write_text("""import readline from 'node:readline';
const tool=TOOL;
for await (const line of readline.createInterface({input:process.stdin})) {
 const m=JSON.parse(line); if(m.id===undefined) continue;
 let result;
 if(m.method==='initialize') result={protocolVersion:'2025-11-25',capabilities:{tools:{}},serverInfo:{name:'self-authored-fixture',version:'1'}};
 else if(m.method==='tools/list') result={tools:[tool]};
 else if(m.method==='tools/call') result={content:[{type:'text',text:'local approved signal'}],structuredContent:{value:42}};
 else throw new Error('unsupported method');
 console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result}));
}
""".replace("TOOL", json.dumps(TOOL)))
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE skills_registry SET entrypoint=?, permissions_granted_json=? WHERE skill_id='owned.read'",
            (
                json.dumps(runtime.build_entrypoint(str(package))),
                json.dumps(list(runtime.READ_ONLY_PERMISSIONS)),
            ),
        )
    headers = {"Authorization": "Bearer valid-owner-session"}
    base = "/api/system/account/skills"
    review = client.post(
        base + "/owned.read/mcp/contract/prepare", headers=headers, json={"confirm_process": True}
    )
    assert review.status_code == 200, review.json
    approved = client.post(
        base + "/owned.read/mcp/contract/approve",
        headers=headers,
        json={"confirm": True, "candidate_sha256": review.json["candidate"]["candidate_sha256"]},
    )
    assert approved.status_code == 200, approved.json
    activated = client.post(
        base + "/source/activate",
        headers=headers,
        json={"skill_id": "owned.read", "install_path": str(package)},
    )
    assert activated.status_code == 200, activated.json
    enabled = client.post(base + "/owned.read/enable", headers=headers, json={})
    assert enabled.status_code == 200, enabled.json
    executed = client.post(
        base + "/owned.read/execute",
        headers=headers,
        json={
            "input": {
                "tool_name": "read_signal",
                "arguments": {"query": "local"},
                "human_approved": True,
            },
            "product": "SYSTEM",
        },
    )
    assert executed.status_code == 200, executed.json
    assert executed.json["success"] is True, executed.json
    assert (
        executed.json["result"]["result"]["result"]["structuredContent"]["value"] == 42
    ), executed.json
    assert executed.json["result"]["source"] == "registered_mcp"
    with sqlite3.connect(path) as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM skill_executions WHERE skill_id='owned.read' AND status='completed'"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize(
    "headers",
    [{"Origin": "https://attacker.invalid"}, {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}],
)
def test_mcp_confirmation_and_process_routes_reject_cross_origin(api_client, headers):
    client, path = api_client
    headers = {"Authorization": "Bearer valid-owner-session", **headers}
    for endpoint in (
        "/skills/owned.read/mcp/contract/prepare",
        "/skills/owned.read/mcp/contract/approve",
        "/skills/source/mcp/discover",
        "/skills/source/mcp/call",
    ):
        response = client.post(
            "/api/system/account" + endpoint,
            headers=headers,
            json={"confirm": True, "confirm_process": True},
        )
        assert response.status_code == 403
        assert response.json["error"] == "MCP_SAME_ORIGIN_JSON_REQUIRED"


def test_invalid_scope_is_rejected_before_registered_process(api_client, monkeypatch):
    client, path = api_client
    import mcp_skill_runtime

    monkeypatch.setattr(
        mcp_skill_runtime,
        "discover_registered_mcp",
        lambda *a, **k: pytest.fail("scope denied: process must not start"),
    )
    response = client.post(
        "/api/system/account/skills/owned.read/mcp/contract/prepare",
        headers={"Authorization": "Bearer valid-owner-session"},
        json={"confirm_process": True, "global_scope": False, "subject_id": "missing-scope"},
    )
    assert response.status_code == 400
    assert response.json["error"] == "MCP_SKILL_SCOPE_DENIED"
