"""Universal Skill source boundary tests; no remote code is executed."""

import json
import sqlite3
from pathlib import Path


def test_local_skill_manifest_is_previewed_with_deny_by_default(tmp_path):
    package = tmp_path / "sample-skill"
    package.mkdir()
    (package / "skill.json").write_text(json.dumps({
        "skill_id": "sample.research",
        "name": "Sample Research",
        "version": "1.2.3",
        "runtime": "python",
        "entrypoint": "main:run",
        "capabilities": ["research"],
        "permissions": ["network", "filesystem.read"],
        "secrets_required": ["provider_token"],
    }), encoding="utf-8")

    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    result = preview_skill_source(str(package))
    assert result["ok"] is True
    assert result["state"] == "VALIDATED"
    assert result["source"]["source_type"] == "local"
    assert result["validation"]["valid"] is True
    assert result["security"]["permissions_requested"] == ["network", "filesystem.read"]
    assert result["security"]["permissions_granted"] == []
    assert result["security"]["secrets_injected"] is False
    assert result["ownership"]["registry"] == "account.models.skills_registry"


def test_github_source_requires_explicit_revision_resolution():
    from lumenis.shared.agents.skills.package_runtime import detect_source, preview_skill_source

    source = "https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS"
    detected = detect_source(source)
    assert detected.supported is True
    assert detected.source_type == "github"
    preview = preview_skill_source(source)
    assert preview["state"] == "DETECTED"
    assert preview["manifest_state"] == "NOT_FETCHED"
    assert preview["revision"] is None
    assert preview["security"]["permissions_granted"] == []


def test_github_revision_resolution_accepts_advertised_head(monkeypatch):
    from lumenis.shared.agents.skills import package_runtime as runtime

    calls = []

    class Completed:
        returncode = 0
        stdout = "0123456789abcdef0123456789abcdef01234567\tHEAD\n"

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    revision = runtime.resolve_github_revision(
        "https://github.com/example/skill",
        git_executable="git",
    )

    assert revision == "0123456789abcdef0123456789abcdef01234567"
    assert calls == [["git", "ls-remote", "https://github.com/example/skill", "HEAD"]]


def test_standard_agentskills_skill_md_is_validated_without_json_manifest(tmp_path):
    package = tmp_path / "research-skill"
    package.mkdir()
    skill_md = package / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: research-skill\n"
        "description: Collects research notes and returns cited findings.\n"
        "---\n\n"
        "# Research Skill\n\n"
        "Use the evidence chain and do not invent sources.\n",
        encoding="utf-8",
    )

    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    result = preview_skill_source(str(package))
    assert result["state"] == "VALIDATED"
    assert result["manifest"]["format"] == "agentskills"
    assert result["validation"]["normalized"]["skill_id"] == "research-skill"
    assert result["validation"]["normalized"]["version"] == "0.0.0"
    assert result["registration"]["allowed"] is True
    assert result["security"]["execution"].startswith("BLOCKED_")


def test_standalone_skill_md_file_is_supported(tmp_path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: tiny-skill\ndescription: A minimal skill.\n---\n",
        encoding="utf-8",
    )

    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    result = preview_skill_source(str(skill_md))
    assert result["source"]["source_type"] == "skill_md"
    assert result["state"] == "VALIDATED"


def test_zip_path_traversal_manifest_is_not_accepted(tmp_path):
    import zipfile

    package = tmp_path / "unsafe-skill.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../SKILL.md", "---\nname: unsafe-skill\ndescription: unsafe\n---\n")

    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    result = preview_skill_source(str(package))
    assert result["state"] == "BLOCKED"
    assert result["manifest_state"] == "MISSING"


def test_github_skill_directory_is_pinned_before_manifest_fetch(monkeypatch):
    from lumenis.shared.agents.skills import package_runtime as runtime

    source = "https://github.com/example/skill/tree/main/skills/research-skill"
    detected = runtime.detect_source(source)
    assert detected.source_type == "github"
    assert detected.ref == "main"
    assert detected.subpath == "skills/research-skill"

    calls = []

    class Completed:
        returncode = 0
        stdout = "fedcba9876543210fedcba9876543210fedcba98\trefs/heads/main\n"

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    result = runtime.preview_skill_source(source, resolve_remote=True)
    assert result["state"] == "REMOTE_RESOLVED"
    assert result["revision"] == "fedcba9876543210fedcba9876543210fedcba98"
    assert result["manifest_state"] == "NOT_FETCHED"
    assert calls == [["git", "ls-remote", "https://github.com/example/skill", "main"]]


def test_github_skill_directory_preserves_exact_commit_pin_without_ls_remote(monkeypatch):
    from lumenis.shared.agents.skills import package_runtime as runtime

    revision = "0123456789abcdef0123456789abcdef01234567"
    source = f"https://github.com/example/skill/tree/{revision}/trendhub-mcp"
    calls = []

    def unexpected_run(command, **kwargs):
        calls.append(command)
        raise AssertionError("exact commit URL must not be resolved as a remote ref")

    monkeypatch.setattr(runtime.subprocess, "run", unexpected_run)
    assert runtime.resolve_github_revision(source) == revision
    assert calls == []


def test_github_skill_manifest_is_discovered_at_pinned_revision_without_checkout(monkeypatch):
    from lumenis.shared.agents.skills import package_runtime as runtime

    source = "https://github.com/Zachary-1012/Zachary-Skill/tree/main/trendhub-mcp"
    revision = "0123456789abcdef0123456789abcdef01234567"
    calls = []

    class Completed:
        returncode = 0
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Completed()
        if command[1:3] == ["ls-tree", "-r"]:
            result.stdout = "trendhub-mcp/manifest.json\ntrendhub-mcp/SKILL.md\n"
        elif command[1] == "show":
            result.stdout = '{"name":"trendhub-mcp","version":"1.4.4","runtime":"mcp","entrypoint":"scripts/launcher.mjs","permissions":[]}'
        return result

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    detected = runtime.detect_source(source)
    result = runtime.fetch_github_manifest(detected, revision=revision)

    assert result["state"] == "VALIDATED"
    assert result["path"] == "trendhub-mcp/manifest.json"
    assert result["validation"]["normalized"]["runtime"] == "mcp"
    assert calls[0][1:3] == ["init", "--quiet"]
    assert not any("checkout" in command for command in calls)


def test_github_skill_root_manifest_does_not_guess_between_nested_skills(monkeypatch):
    from lumenis.shared.agents.skills import package_runtime as runtime

    revision = "fedcba9876543210fedcba9876543210fedcba98"

    class Completed:
        returncode = 0
        stdout = ""

    def fake_run(command, **kwargs):
        result = Completed()
        if command[1:3] == ["ls-tree", "-r"]:
            result.stdout = "skills/trendhub/SKILL.md\ntrendhub-mcp/manifest.json\n"
        return result

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(runtime, "resolve_github_revision", lambda *args, **kwargs: revision)
    result = runtime.preview_skill_source(
        "https://github.com/Zachary-1012/Zachary-Skill",
        resolve_remote=True,
        fetch_remote_manifest=True,
    )

    assert result["state"] == "BLOCKED"
    assert result["manifest_state"] == "MISSING"
    assert result["remote_manifest"]["candidates"] == []
    assert "manifest not found" in result["errors"][0]


def test_github_remote_registration_requires_validated_manifest_evidence(tmp_path, monkeypatch):
    from lumenis.shared.agents.skills import package_runtime as runtime
    from account.models import init_account_db
    from account.skills import list_skills, register_validated_skill, set_skill_status

    revision = "abcdef0123456789abcdef0123456789abcdef01"

    class Completed:
        returncode = 0
        stdout = ""

    def fake_run(command, **kwargs):
        result = Completed()
        if command[1:3] == ["ls-tree", "-r"]:
            result.stdout = "trendhub-mcp/manifest.json\ntrendhub-mcp/SKILL.md\n"
        elif command[1] == "show":
            result.stdout = '{"name":"trendhub-mcp","version":"1.4.4","runtime":"mcp","entrypoint":"scripts/launcher.mjs","permissions":[]}'
        return result

    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "skills.db"))
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(runtime, "resolve_github_revision", lambda *args, **kwargs: revision)
    preview = runtime.preview_skill_source(
        "https://github.com/Zachary-1012/Zachary-Skill/tree/main/trendhub-mcp",
        resolve_remote=True,
        fetch_remote_manifest=True,
    )
    init_account_db()
    result = register_validated_skill(preview)

    assert preview["state"] == "REMOTE_VALIDATED"
    assert result["success"] is True
    registered = next(item for item in list_skills() if item["skill_id"] == "trendhub-mcp")
    assert registered["source_type"] == "github"
    assert registered["revision"] == revision
    assert registered["install_state"] == "not_installed"
    assert registered["status"] == "disabled"
    not_ready = set_skill_status("trendhub-mcp", "enabled")
    assert not_ready["success"] is False
    assert not_ready["code"] == "RUNTIME_NOT_READY"


def test_unknown_source_is_blocked_and_never_installed(tmp_path):
    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    result = preview_skill_source(str(tmp_path / "does-not-exist"))
    assert result["ok"] is False
    assert result["state"] == "BLOCKED"
    assert result["security"]["execution"].startswith("BLOCKED_")


def test_existing_skill_registry_is_extended_in_place(tmp_path, monkeypatch):
    db_path = tmp_path / "skills.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    from account.models import init_account_db

    init_account_db()
    con = sqlite3.connect(str(db_path))
    try:
        columns = {row[1] for row in con.execute("PRAGMA table_info(skills_registry)")}
    finally:
        con.close()
    assert {"source", "source_type", "revision", "digest", "runtime",
            "permissions_requested_json", "permissions_granted_json",
            "health_state", "install_state", "lifecycle_state"}.issubset(columns)


def test_skill_source_preview_route_requires_owner(client):
    response = client.post(
        "/api/system/account/skills/source/preview",
        json={"source": "https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS"},
    )
    assert response.status_code == 401


def test_skill_source_register_route_requires_owner(client):
    response = client.post(
        "/api/system/account/skills/source/register",
        json={"source": "C:/untrusted/skill"},
    )
    assert response.status_code == 401


def test_mcp_discovery_route_requires_owner(client):
    response = client.post(
        "/api/system/account/skills/source/mcp/discover",
        json={"source": "mcp+stdio://trendhub", "command": ["node"], "args": []},
    )
    assert response.status_code == 401


def test_mcp_call_route_requires_owner(client):
    response = client.post(
        "/api/system/account/skills/source/mcp/call",
        json={
            "source": "mcp+stdio://trendhub",
            "command": ["node"],
            "args": [],
            "tool_name": "read_signal",
            "arguments": {},
            "allowed_tools": ["read_signal"],
            "permissions_granted": ["mcp:tools/call"],
            "confirm_process": True,
            "confirm_tool_call": True,
            "human_approved": True,
        },
    )
    assert response.status_code == 401


def test_validated_skill_metadata_is_registered_disabled_and_uninstalled(tmp_path, monkeypatch):
    package = tmp_path / "registered-skill"
    package.mkdir()
    (package / "skill.json").write_text(json.dumps({
        "skill_id": "registered.research",
        "name": "Registered Research",
        "version": "1.0.0",
        "runtime": "python",
        "entrypoint": "main:run",
        "capabilities": ["research"],
        "permissions": ["filesystem.read"],
    }), encoding="utf-8")
    db_path = tmp_path / "skills.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    from account.models import init_account_db
    from account.skills import list_skills, register_validated_skill
    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    init_account_db()
    preview = preview_skill_source(str(package))
    result = register_validated_skill(preview)

    assert result["success"] is True
    assert result["status"] == "disabled"
    skill = next(item for item in list_skills() if item["skill_id"] == "registered.research")
    assert skill["install_state"] == "not_installed"
    assert skill["lifecycle_state"] == "validated"
    assert skill["trust_level"] == "unverified"
    assert skill["permissions_granted_json"] == "[]"


def test_mcp_registration_is_fail_closed(tmp_path):
    from account.skills import register_validated_skill
    from lumenis.shared.agents.skills.package_runtime import preview_skill_source

    preview = preview_skill_source("mcp+http://localhost:9000/tools")
    assert preview["state"] == "MCP_DISCOVERY_REQUIRED"
    assert preview["registration"]["allowed"] is False
    result = register_validated_skill(preview)
    assert result["success"] is False
    assert result["code"] == "MCP_DISCOVERY_AND_APPROVAL_REQUIRED"


def test_mcp_discovery_is_blocked_without_explicit_process_permission():
    from mcp_discovery import discover_mcp_stdio

    result = discover_mcp_stdio(["node"], ["server.mjs"])

    assert result["state"] == "BLOCKED"
    assert result["security"]["process_started"] is False
    assert result["security"]["tool_calls"] == 0


def test_mcp_stdio_discovery_lists_capabilities_but_never_calls_tools(tmp_path):
    import sys
    from mcp_discovery import discover_mcp_stdio

    script = tmp_path / "mcp_fixture.py"
    script.write_text(
        "import sys,json\n"
        "for line in sys.stdin:\n"
        " m=json.loads(line); i=m.get('id'); method=m.get('method')\n"
        " r={'jsonrpc':'2.0','id':i,'result':{}}\n"
        " if method=='initialize': r['result']={'protocolVersion':'2025-11-25','capabilities':{},'serverInfo':{'name':'fixture','version':'1'}}\n"
        " elif method=='tools/list': r['result']={'tools':[{'name':'read_signal','description':'read only','inputSchema':{'type':'object'}}]}\n"
        " elif method=='resources/list': r['result']={'resources':[{'name':'evidence://fixture'}]}\n"
        " elif method=='prompts/list': r['result']={'prompts':[{'name':'brief'}]}\n"
        " if 'id' in m: print(json.dumps(r),flush=True)\n",
        encoding="utf-8",
    )
    result = discover_mcp_stdio(
        [sys.executable], [str(script)], allow_process=True, timeout=10,
    )

    assert result["ok"] is True
    assert result["state"] == "DISCOVERED"
    assert result["server_info"]["name"] == "fixture"
    assert [tool["name"] for tool in result["tools"]] == ["read_signal"]
    assert result["resources"][0]["name"] == "evidence://fixture"
    assert result["prompts"][0]["name"] == "brief"
    assert result["security"]["tool_calls"] == 0


def test_mcp_tool_call_requires_human_permission_before_starting_process(tmp_path):
    import sys
    from mcp_discovery import call_mcp_stdio

    result = call_mcp_stdio(
        [sys.executable], [str(tmp_path / "not-started.py")],
        tool_name="read_signal", allowed_tools=("read_signal",),
    )

    assert result["state"] == "BLOCKED"
    assert result["security"]["process_started"] is False
    assert result["security"]["tool_calls"] == 0


def test_mcp_tool_call_requires_reviewed_read_only_annotation(tmp_path):
    import json
    import sys
    from mcp_discovery import call_mcp_stdio

    script = tmp_path / "mcp_write_hint_fixture.py"
    script.write_text(
        "import json,sys\n"
        "for line in sys.stdin:\n"
        " m=json.loads(line); i=m.get('id'); method=m.get('method')\n"
        " r={'jsonrpc':'2.0','id':i,'result':{}}\n"
        " if method=='initialize': r['result']={'protocolVersion':'2025-11-25','serverInfo':{'name':'fixture','version':'1'}}\n"
        " elif method=='tools/list': r['result']={'tools':[{'name':'write_signal','inputSchema':{'type':'object'}}]}\n"
        " elif method=='tools/call': r['result']={'content':[{'type':'text','text':'should not run'}]}\n"
        " if 'id' in m: print(json.dumps(r),flush=True)\n",
        encoding="utf-8",
    )
    result = call_mcp_stdio(
        [sys.executable], [str(script)],
        tool_name="write_signal", arguments={},
        allow_process=True, allow_tool_call=True, human_approved=True,
        permissions_granted=("mcp:tools/call",), allowed_tools=("write_signal",),
    )

    assert result["ok"] is False
    assert result["state"] == "READ_ONLY_GATE_BLOCKED"
    assert result["security"]["tool_calls"] == 0


def test_mcp_tool_call_returns_redacted_staging_result_without_production_write(tmp_path):
    import json
    import sys
    from mcp_discovery import call_mcp_stdio

    script = tmp_path / "mcp_read_fixture.py"
    script.write_text(
        "import json,sys\n"
        "for line in sys.stdin:\n"
        " m=json.loads(line); i=m.get('id'); method=m.get('method')\n"
        " r={'jsonrpc':'2.0','id':i,'result':{}}\n"
        " if method=='initialize': r['result']={'protocolVersion':'2025-11-25','serverInfo':{'name':'fixture','version':'1'}}\n"
        " elif method=='tools/list': r['result']={'tools':[{'name':'read_signal','description':'read only','annotations':{'readOnlyHint':True,'destructiveHint':False},'inputSchema':{'type':'object'}}]}\n"
        " elif method=='tools/call': r['result']={'content':[{'type':'text','text':'signal ok'}],'structuredContent':{'value':42,'token':'do-not-leak'}}\n"
        " if 'id' in m: print(json.dumps(r),flush=True)\n",
        encoding="utf-8",
    )
    result = call_mcp_stdio(
        [sys.executable], [str(script)],
        tool_name="read_signal", arguments={"query":"lumenis"},
        allow_process=True, allow_tool_call=True, human_approved=True,
        permissions_granted=("mcp:tools/call",), allowed_tools=("read_signal",),
    )

    assert result["ok"] is True
    assert result["state"] == "CALLED"
    assert result["security"]["tool_calls"] == 1
    assert result["security"]["production_truth_write"] is False
    assert result["result"]["structuredContent"]["value"] == 42
    assert result["result"]["structuredContent"]["token"] == "[redacted]"


def test_github_connector_is_allowlisted_read_only_and_never_exposes_token():
    import json as json_module
    from github_connector import GitHubConnector, GitHubConnectorConfig

    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _limit):
            return json_module.dumps({
                "id": 123,
                "full_name": "owner/repo",
                "name": "repo",
                "description": "truth",
                "owner": {"login": "owner"},
                "html_url": "https://github.com/owner/repo",
            }).encode("utf-8")

    def opener(request, timeout):
        requests.append((request, timeout))
        return Response()

    connector = GitHubConnector(
        config=GitHubConnectorConfig(
            client_id="app-id",
            redirect_uri="https://lumenis.example/callback",
            repositories=("owner/repo",),
        ),
        token_provider=lambda: "secret-token-for-test",
        opener=opener,
    )
    snapshot = connector.status()
    assert snapshot["state"] == "CONNECTED"
    assert snapshot["write_enabled"] is False
    assert snapshot["secret_material_exposed"] is False
    assert "secret-token-for-test" not in str(snapshot)

    payload = connector.repository("owner/repo")
    assert payload["full_name"] == "owner/repo"
    request = requests[0][0]
    assert request.get_method() == "GET"
    assert request.full_url == "https://api.github.com/repos/owner/repo"
    assert request.headers["Authorization"] == "Bearer secret-token-for-test"

    try:
        connector.repository("other/repo")
    except Exception as exc:
        assert getattr(exc, "code", None) == "REPOSITORY_NOT_ALLOWLISTED"
    else:
        raise AssertionError("non-allowlisted repository must be blocked")


def test_github_authorization_request_contains_state_but_no_secret():
    from github_connector import GitHubConnector, GitHubConnectorConfig

    connector = GitHubConnector(config=GitHubConnectorConfig(
        client_id="app-id",
        redirect_uri="https://lumenis.example/callback",
    ))
    url = connector.authorization_url("0123456789abcdef0123456789abcdef")
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=app-id" in url
    assert "state=0123456789abcdef0123456789abcdef" in url
    assert "secret" not in url.lower()


def test_github_connector_status_route_requires_owner(client):
    response = client.get("/api/system/account/connectors/github/status")
    assert response.status_code == 401


def test_skill_settings_surface_uses_real_source_preview_and_no_fake_mcp_ready_state():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates/system/skill_store.html").read_text(encoding="utf-8")
    script = (root / "static/js/skill-store.js").read_text(encoding="utf-8")

    assert "Universal Skill Runtime" in template
    assert "ssSourceModal" in template
    assert "/api/system/account/skills/source/preview" in script
    assert "MCP 服务器管理将在后续版本开放" not in script
    assert "不下载、不安装、不执行、不授予权限" in template
    assert "/api/system/account/connectors/github/status" in script
    assert "GitHub Connector" in template
