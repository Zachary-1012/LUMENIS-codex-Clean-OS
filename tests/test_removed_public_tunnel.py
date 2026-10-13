"""Isolated regression for removed public exposure; no app/service startup."""
import ast
from pathlib import Path

import pytest
from flask import Flask, jsonify

ROOT = Path(__file__).resolve().parents[1]


def test_old_remote_bookmark_never_reads_or_redirects_external_state():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "remote_access")
    node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {"jsonify": jsonify, "APP_PORT": 8201}
    # Execute only the committed route AST; importing app would start unrelated services.
    exec(compile(module, "remote_access", "exec"), namespace)  # noqa: S102
    app = Flask(__name__)
    with app.test_request_context("/remote"):
        response, status = namespace["remote_access"]()
    assert status == 410
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"] == "PUBLIC_REMOTE_ACCESS_UNAVAILABLE"
    assert payload["local_url"] == "http://127.0.0.1:8201"
    assert set(payload["messages"]) == {"zh", "en", "ko"}
    assert all(payload["messages"].values())
    assert "Location" not in response.headers


@pytest.mark.parametrize("name", ["tunnel_guardian.py", "deployment/start_remote.bat",
                                  "cloudflared_guardian.ps1", "start_tunnel.bat"])
def test_removed_launchers_cannot_be_called(name):
    assert not (ROOT / name).exists()
