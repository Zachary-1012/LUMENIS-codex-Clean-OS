import json


def _package(tmp_path, monkeypatch):
    import mcp_skill_runtime as runtime

    root = tmp_path / "skill_packages"
    package = root / "trendhub-mcp"
    (package / "scripts").mkdir(parents=True)
    (package / "dist" / "src").mkdir(parents=True)
    (package / "node_modules").mkdir()
    (package / "manifest.json").write_text(
        json.dumps({"name": "trendhub-mcp", "version": "1.5.2"}), encoding="utf-8"
    )
    (package / "package.json").write_text("{}", encoding="utf-8")
    (package / "scripts" / "launcher.mjs").write_text("", encoding="utf-8")
    (package / "dist" / "src" / "index.js").write_text("", encoding="utf-8")
    monkeypatch.setattr(runtime, "PACKAGE_ROOT", root.resolve())
    return runtime, package


def test_mcp_skill_installation_is_rooted_and_built(tmp_path, monkeypatch):
    runtime, package = _package(tmp_path, monkeypatch)

    result = runtime.validate_installation(
        str(package), expected_skill_id="trendhub-mcp", expected_version="1.5.2"
    )
    assert result["ok"] is True
    entrypoint = runtime.build_entrypoint(str(package))
    assert entrypoint["args"] == [str(package / "scripts" / "launcher.mjs")]
    assert entrypoint["command"].lower().endswith(("node.exe", "node"))


def test_mcp_skill_invocation_requires_human_approval_before_process(tmp_path, monkeypatch):
    runtime, package = _package(tmp_path, monkeypatch)
    info = {
        "skill_id": "trendhub-mcp",
        "version": "1.5.2",
        "active_version": "1.5.2",
        "install_path": str(package),
        "entrypoint": json.dumps(runtime.build_entrypoint(str(package))),
        "tools_json": json.dumps(["list_platforms"]),
        "permissions_granted_json": json.dumps(list(runtime.READ_ONLY_PERMISSIONS)),
    }
    result = runtime.invoke_registered_mcp(
        info, {"tool_name": "list_platforms", "arguments": {}, "human_approved": False}
    )
    assert result["ok"] is False
    assert result["state"] == "BLOCKED"
    assert "human approval" in result["errors"][0]


def test_mcp_skill_rejects_unregistered_tool(tmp_path, monkeypatch):
    runtime, package = _package(tmp_path, monkeypatch)
    info = {
        "skill_id": "trendhub-mcp",
        "version": "1.5.2",
        "active_version": "1.5.2",
        "install_path": str(package),
        "entrypoint": json.dumps(runtime.build_entrypoint(str(package))),
        "tools_json": json.dumps(["list_platforms"]),
        "permissions_granted_json": json.dumps(list(runtime.READ_ONLY_PERMISSIONS)),
    }
    result = runtime.invoke_registered_mcp(
        info, {"tool_name": "workspace_manage", "arguments": {}, "human_approved": True}
    )
    assert result["ok"] is False
    assert result["state"] == "BLOCKED"
    assert "allowlist" in result["errors"][0]
