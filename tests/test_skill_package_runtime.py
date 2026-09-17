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

    from skill_package_runtime import preview_skill_source

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
    from skill_package_runtime import detect_source, preview_skill_source

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
    import skill_package_runtime as runtime

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

    from skill_package_runtime import preview_skill_source

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

    from skill_package_runtime import preview_skill_source

    result = preview_skill_source(str(skill_md))
    assert result["source"]["source_type"] == "skill_md"
    assert result["state"] == "VALIDATED"


def test_zip_path_traversal_manifest_is_not_accepted(tmp_path):
    import zipfile

    package = tmp_path / "unsafe-skill.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../SKILL.md", "---\nname: unsafe-skill\ndescription: unsafe\n---\n")

    from skill_package_runtime import preview_skill_source

    result = preview_skill_source(str(package))
    assert result["state"] == "BLOCKED"
    assert result["manifest_state"] == "MISSING"


def test_github_skill_directory_is_pinned_before_manifest_fetch(monkeypatch):
    import skill_package_runtime as runtime

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


def test_unknown_source_is_blocked_and_never_installed(tmp_path):
    from skill_package_runtime import preview_skill_source

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
    from skill_package_runtime import preview_skill_source

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
    from skill_package_runtime import preview_skill_source

    preview = preview_skill_source("mcp+http://localhost:9000/tools")
    assert preview["state"] == "MCP_DISCOVERY_REQUIRED"
    assert preview["registration"]["allowed"] is False
    result = register_validated_skill(preview)
    assert result["success"] is False
    assert result["code"] == "MCP_DISCOVERY_AND_APPROVAL_REQUIRED"


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
