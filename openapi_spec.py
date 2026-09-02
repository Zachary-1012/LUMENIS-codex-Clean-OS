# -*- coding: utf-8 -*-
"""OpenAPI 3.0 路由清单生成器（对账 P1-2）——从 Flask url_map 自动反射，零运行时改动。

- 不手写、不猜路由：直接遍历 app.url_map，Flask `<converter:name>` 转 OpenAPI `{name}`；
- 认证标注与 app.py before_request 真实规则一致：
  * /healthz：公开（无 security）
  * /v4/*：独立 v4 token/会话（不走 HTTP Basic）
  * 其余：HTTP Basic 或有效 v4 会话（二选一）
- 输出标准 OpenAPI 3.0.3 JSON + 人类可读路由矩阵 Markdown；只生成文档，不改任何端点行为。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

_PARAM_RE = re.compile(r"<(?:[a-zA-Z]+:)?([^>]+)>")
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


def flask_rule_to_path(rule: str) -> str:
    """'/api/note/<int:note_id>' -> '/api/note/{note_id}'。"""
    return _PARAM_RE.sub(lambda m: "{" + m.group(1) + "}", rule.rule)


def auth_for(path: str) -> Dict[str, List[str]]:
    """返回该路径需要的 security（与 app._basic_auth 豁免逻辑对齐）。[] 表示公开。"""
    if path == "/healthz":
        return {}  # 公开
    if path.startswith("/v4/"):
        return {"v4Auth": []}
    return {"httpBasic": [], "v4Auth": []}  # Basic 或有效 v4 会话，二选一


def _tag_of(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    if not parts:
        return "root"
    if parts[0] == "api" and len(parts) > 1:
        return "api/" + parts[1]
    return parts[0]


def _doc_summary(view_func: Any) -> str:
    doc = (getattr(view_func, "__doc__", "") or "").strip().splitlines()
    return doc[0].strip() if doc else ""


def build_spec(app: Any, title: str = "Z-Brand-Core API", version: str = "1.0.0") -> dict:
    paths: Dict[str, dict] = {}
    covered_rules = 0
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        covered_rules += 1
        path = flask_rule_to_path(rule)
        view = app.view_functions.get(rule.endpoint)
        summary = _doc_summary(view) if view else ""
        ops = {}
        for method in sorted(rule.methods or []):
            if method not in HTTP_METHODS:
                continue
            sec = auth_for(path)
            op: Dict[str, Any] = {
                "operationId": rule.endpoint,
                "tags": [_tag_of(path)],
                "parameters": [
                    {"name": p, "in": "path", "required": True,
                     "schema": {"type": "string"}}
                    for p in _PARAM_RE.findall(rule.rule)
                ],
            }
            if summary:
                op["summary"] = summary
            if sec:
                op["security"] = [sec] if len(sec) == 1 else [[{k: []}] for k in sec]
            ops[method.lower()] = op
        if ops:
            paths.setdefault(path, {}).update(ops)
    return {
        "openapi": "3.0.3",
        "info": {"title": title, "version": version,
                 "description": "Auto-generated from Flask url_map (P1-2). Do not edit by hand."},
        "components": {"securitySchemes": {
            "httpBasic": {"type": "http", "scheme": "basic"},
            "v4Auth": {"type": "apiKey", "in": "header", "name": "Authorization",
                       "description": "v4 独立 token/会话（Bearer 或同名 session cookie）"},
        }},
        "x-route-count": covered_rules,
        "paths": paths,
    }


def build_matrix_md(spec: dict) -> str:
    paths = spec["paths"]
    lines = ["# API 路由矩阵（P1-2，由 openapi_spec 从 url_map 自动生成，勿手改）\n",
             f"- 非 static 路由（path 去重后）：**{len(paths)}**；url_map 规则数：{spec.get('x-route-count')}",
             "- 认证：public=/healthz；v4Auth=/v4/* 独立 token；其余 httpBasic 或 v4 会话。\n",
             "| 路径 | 方法 | Endpoint | 认证 | 分组 |",
             "|------|------|----------|------|------|"]
    for path in sorted(paths):
        for method, op in sorted(paths[path].items()):
            sec = op.get("security")
            if not sec:
                auth = "public"
            elif len(sec) == 1 and "v4Auth" in sec[0]:
                auth = "v4Auth"
            else:
                auth = "basic/v4"
            lines.append(f"| `{path}` | {method.upper()} | {op['operationId']} | {auth} | {op['tags'][0]} |")
    return "\n".join(lines) + "\n"


def generate(app: Any, json_path: str, matrix_path: Optional[str] = None,
             title: str = "Z-Brand-Core API", version: str = "1.0.0") -> dict:
    spec = build_spec(app, title=title, version=version)
    with open(json_path, "w", encoding="utf-8", newline="") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    if matrix_path:
        with open(matrix_path, "w", encoding="utf-8", newline="") as f:
            f.write(build_matrix_md(spec))
    return spec
