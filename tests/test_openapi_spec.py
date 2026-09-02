# -*- coding: utf-8 -*-
"""P1-2 OpenAPI 生成器测试：规则转换、全覆盖、认证标注与真实 before_request 对齐。"""
import os
import sys
import json

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
    assert note["get"]["operationId"] == "note_detail"
    assert note["get"]["parameters"][0]["name"] == "note_id"
    # /v4 仅 v4Auth；/healthz 无 security
    assert spec["paths"]["/v4/console/{sub}"]["get"]["security"] == [{"v4Auth": []}]
    assert "security" not in spec["paths"]["/healthz"]["get"]


def test_real_app_spec_full_coverage(app):
    spec = build_spec(app)
    rules = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
    expected_paths = {flask_rule_to_path(r) for r in rules}
    assert set(spec["paths"]) == expected_paths  # 一条路由都不能漏
    assert spec["x-route-count"] == len(rules)
    # 每个 operation 都有 operationId/tags
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            assert op["operationId"] and op["tags"]


def test_generated_spec_files_valid():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    j = os.path.join(root, "docs", "API-OPENAPI-SPEC.json")
    assert os.path.exists(j)
    spec = json.load(open(j, encoding="utf-8"))
    assert spec["openapi"].startswith("3.0")
    assert "httpBasic" in spec["components"]["securitySchemes"]
    assert "/healthz" in spec["paths"] and len(spec["paths"]) > 300
    md = build_matrix_md(spec)
    assert "API 路由矩阵" in md and "/healthz" in md
