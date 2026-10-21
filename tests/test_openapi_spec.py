# -*- coding: utf-8 -*-
"""P1-2 OpenAPI 生成器测试：规则转换、全覆盖、认证标注与真实 before_request 对齐。"""
import os
import sys
import json
from pathlib import Path
import subprocess

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openapi_spec import build_spec, flask_rule_to_path, auth_for, build_matrix_md  # noqa: E402
from flask import Flask  # noqa: E402


def _mini_app():
    a = Flask(__name__)

    @a.route("/healthz")
    def hz():
        return "ok"

    @a.route("/api/note/<int:note_id>", methods=["GET", "DELETE"])
    def note_detail(note_id):
        return ""

    @a.route("/v4/console/<path:sub>")
    def v4_console(sub):
        return ""

    return a


def test_rule_to_openapi_path_converter():
    a = _mini_app()
    rule = next(r for r in a.url_map.iter_rules() if "note" in r.rule)
    assert flask_rule_to_path(rule) == "/api/note/{note_id}"


def test_auth_mapping_matches_basic_auth_exemptions():
    assert auth_for("/healthz") == {}
    assert set(auth_for("/v4/console/x")) == {"v4Auth"}
    assert set(auth_for("/api/notes")) == {"httpBasic", "v4Auth"}


def test_build_spec_covers_every_nonstatic_rule():
    a = _mini_app()
    spec = build_spec(a)
    rules = [r for r in a.url_map.iter_rules() if r.endpoint != "static"]
    covered = set()
    for r in rules:
        covered.add(flask_rule_to_path(r))
    assert set(spec["paths"]) == covered
    note = spec["paths"]["/api/note/{note_id}"]
    assert set(note) == {"get", "delete"}
    # One Flask endpoint serves GET and DELETE: IDs stay unique per OpenAPI.
    assert note["get"]["x-flask-endpoint"] == note["delete"]["x-flask-endpoint"] == "note_detail"
    assert note["get"]["operationId"] == "note_detail__get"
    assert note["delete"]["operationId"] == "note_detail__delete"
    assert note["get"]["security"] == [{"httpBasic": []}, {"v4Auth": []}]
    assert note["get"]["parameters"][0]["name"] == "note_id"
    # /v4 仅 v4Auth；/healthz 无 security
    assert spec["paths"]["/v4/console/{sub}"]["get"]["security"] == [{"v4Auth": []}]
    assert "security" not in spec["paths"]["/healthz"]["get"]


def test_duplicate_routes_keep_all_candidates_without_selecting_one():
    a = Flask(__name__)

    @a.get("/api/shared", endpoint="shared_first")
    def shared_first():
        return "first"

    @a.get("/api/shared", endpoint="shared_second")
    def shared_second():
        return "second"

    spec = build_spec(a)
    operation = spec["paths"]["/api/shared"]["get"]
    assert "operationId" not in operation
    assert operation["x-route-candidates"] == [
        {"endpoint": "shared_first", "rule": "/api/shared"},
        {"endpoint": "shared_second", "rule": "/api/shared"},
    ]
    assert spec["x-duplicate-operation-candidates"] == [{
        "path": "/api/shared",
        "method": "GET",
        "candidates": operation["x-route-candidates"],
    }]
    assert spec["x-route-count"] == 2
    assert spec["x-operation-count"] == 2
    assert spec["x-operation-group-count"] == 1
    assert spec["x-duplicate-operation-group-count"] == 1


def test_real_app_spec_full_coverage(app):
    spec = build_spec(app)
    rules = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
    expected_paths = {flask_rule_to_path(r) for r in rules}
    assert set(spec["paths"]) == expected_paths  # 一条路由都不能漏
    assert spec["x-route-count"] == len(rules)
    assert spec["x-url-map-rule-count"] == sum(1 for _ in app.url_map.iter_rules())
    assert spec["x-static-route-count"] == sum(
        1 for rule in app.url_map.iter_rules() if rule.endpoint == "static"
    )
    assert spec["x-operation-count"] == sum(
        len((rule.methods or set()) & {"GET", "POST", "PUT", "DELETE", "PATCH"})
        for rule in rules
    )
    assert spec["x-path-count"] == len(expected_paths)
    assert spec["info"]["title"] == "LUMENIS API"
    summaries = [
        operation.get("summary", "")
        for operations in spec["paths"].values()
        for operation in operations.values()
    ]
    assert not any("Z-Brand" in summary or "ZBrand" in summary for summary in summaries)
    # Unique operations have an operationId; collisions preserve every endpoint.
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            assert op["tags"]
            if "x-route-candidates" in op:
                assert "operationId" not in op
                assert len(op["x-route-candidates"]) > 1
            else:
                assert op["operationId"] and op["x-flask-rule"]
                assert op["x-flask-endpoint"]
    operation_ids = [
        op["operationId"]
        for ops in spec["paths"].values() for op in ops.values() if "operationId" in op
    ]
    assert len(operation_ids) == len(set(operation_ids)), "operationId must be unique (OpenAPI 3.0.3)"


def test_generated_spec_files_valid(app):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    j = os.path.join(root, "docs", "API-OPENAPI-SPEC.json")
    assert os.path.exists(j)
    spec = json.load(open(j, encoding="utf-8"))
    assert spec["openapi"].startswith("3.0")
    assert "httpBasic" in spec["components"]["securitySchemes"]
    assert "/healthz" in spec["paths"] and len(spec["paths"]) > 300
    current = build_spec(app)
    assert spec["info"]["title"] == "LUMENIS API"
    assert spec["paths"] == current["paths"]
    for key in (
        "x-url-map-rule-count",
        "x-static-route-count",
        "x-route-count",
        "x-path-count",
        "x-operation-count",
        "x-operation-group-count",
        "x-duplicate-operation-group-count",
        "x-duplicate-operation-candidate-count",
    ):
        assert spec[key] == current[key]
    assert spec["x-duplicate-operation-candidates"] == current[
        "x-duplicate-operation-candidates"
    ]
    md = build_matrix_md(spec)
    assert "API 路由矩阵" in md and "/healthz" in md
    matrix_path = os.path.join(root, "docs", "API-ROUTE-MATRIX.md")
    assert open(matrix_path, encoding="utf-8").read() == md


def test_generator_cli_uses_an_isolated_database_environment(tmp_path):
    root = Path(__file__).resolve().parents[1]
    protected = root / "data" / "monitor.db"
    json_path = tmp_path / "openapi.json"
    matrix_path = tmp_path / "matrix.md"
    access_marker = tmp_path / "protected-db-access.txt"
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "\n".join([
            "import os",
            "import sqlite3",
            "import urllib.parse",
            "protected = os.path.normcase(os.path.abspath(os.environ['LUMENIS_TEST_PROTECTED_DB']))",
            "marker = os.environ['LUMENIS_TEST_PROTECTED_DB_MARKER']",
            "real_connect = sqlite3.connect",
            "def normalize(database):",
            "    value = os.fspath(database)",
            "    if value.startswith('file:'):",
            "        value = urllib.parse.unquote(value[5:].split('?', 1)[0])",
            "        if value.startswith('/') and len(value) > 2 and value[2] == ':':",
            "            value = value[1:]",
            "    return os.path.normcase(os.path.abspath(value))",
            "def guarded_connect(database, *args, **kwargs):",
            "    if normalize(database) == protected:",
            "        with open(marker, 'w', encoding='utf-8') as stream:",
            "            stream.write('protected database connection attempted')",
            "        raise RuntimeError('protected repository database connection is forbidden')",
            "    return real_connect(database, *args, **kwargs)",
            "sqlite3.connect = guarded_connect",
            "sqlite3.dbapi2.connect = guarded_connect",
            "",
        ]),
        encoding="utf-8",
    )
    child_pythonpath = os.pathsep.join(filter(None, [str(tmp_path), os.environ.get("PYTHONPATH", "")]))

    result = subprocess.run(
        [
            sys.executable,
            str(root / "openapi_spec.py"),
            "--json-path",
            str(json_path),
            "--matrix-path",
            str(matrix_path),
        ],
        cwd=root,
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONPATH": child_pythonpath,
            "LUMENIS_TEST_PROTECTED_DB": str(protected),
            "LUMENIS_TEST_PROTECTED_DB_MARKER": str(access_marker),
        },
        capture_output=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, (result.stderr or b"").decode("utf-8", errors="replace")
    assert not access_marker.exists(), "OpenAPI generator tried to connect to the protected database"
    assert json.loads(json_path.read_text(encoding="utf-8"))["paths"]
    assert "API 路由矩阵" in matrix_path.read_text(encoding="utf-8")
