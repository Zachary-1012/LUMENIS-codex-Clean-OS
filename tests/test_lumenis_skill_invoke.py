# -*- coding: utf-8 -*-
"""LUMENIS Cross-Core Skill 真实执行链测试。

覆盖（不调用云端、不起子进程，全部 monkeypatch）：
- ZBC invoke 路由 → CrossCoreSkillAdapter → OSAI SkillInvoker 的状态映射
- SUCCESS=COMPLETED / BLOCKED=权限拒绝 / FAILED=留证 / OSAI 不可用=诚实 ACCEPTED 兜底
- Evidence/Evaluation 状态来自 OSAI 真实返回，绝不伪造 COMPLETED
- 调用记录持久化到独立 JSONL（不写生产 DB），历史端点可回读
- CrossCoreSkillAdapter.invoke_skill 的参数与最小权限
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lumenis_app_api as lf  # noqa: E402


class _FakeAdapter:
    def __init__(self, invoke_result, skill_status="IMPLEMENTED", found=True):
        self._invoke_result = invoke_result
        self._skill_status = skill_status
        self._found = found
        self.calls = []

    def get_skill(self, skill_id):
        if not self._found:
            return {"found": False, "status": "UNKNOWN", "skill": None}
        return {"found": True, "status": "OK", "skill": {
            "id": skill_id, "name": skill_id + " Name", "version": "1.0.0",
            "status": self._skill_status,
            "permissions": ["READ", "AUDIT", "ANALYZE"],
        }}

    def invoke_skill(self, **kwargs):
        self.calls.append(kwargs)
        return self._invoke_result


def _osai_success():
    return {"connected": True, "status": "CONNECTED", "error": None, "osai": {
        "status": "SUCCESS", "trace_id": "TRACE-real", "evidence_id": "EV-real",
        "evaluation_id": "EVAL-real", "engine_id": "eng-1", "model_id": "glm-4.5-air",
        "permission_check": {"allowed": True, "reason": "ok"},
        "result": {"content": "ok out", "latency_ms": 1234.5,
                   "tokens_in": 10, "tokens_out": 20},
    }}


@pytest.fixture
def runtime_dir(tmp_path, monkeypatch):
    d = tmp_path / "lumenis_rt"
    d.mkdir()
    monkeypatch.setenv("LUMENIS_RUNTIME_DIR", str(d))
    return d


def _patch_adapter(monkeypatch, res, **kw):
    fake = _FakeAdapter(res, **kw)
    monkeypatch.setattr(lf, "get_skill_adapter", lambda: fake)
    return fake


def test_invoke_success_completed_and_persisted(client, auth_headers, runtime_dir, monkeypatch):
    _patch_adapter(monkeypatch, _osai_success())
    r = client.post("/lumenis/api/skills/invoke",
                    json={"skill_id": "S01", "task": "t", "workspace": "intelligence"},
                    headers=auth_headers)
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "COMPLETED"
    assert d["execution_status"] == "CONNECTED"
    assert d["evidence_status"] == "EVIDENCE_CREATED"
    assert d["evaluation_status"] == "EVALUATION_CREATED"
    assert d["trace_id"] == "TRACE-real"          # 使用 OSAI 统一 trace，不自造
    assert d["model_id"] == "glm-4.5-air"
    assert d["result"]["tokens_out"] == 20

    # JSONL 持久化落盘
    f = runtime_dir / "skill_invocations.jsonl"
    assert f.exists()
    lines = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1 and lines[0]["skill_id"] == "S01"

    # 历史端点回读
    h = client.get("/lumenis/api/skills/invocations?skill_id=S01", headers=auth_headers)
    assert h.status_code == 200
    hd = h.get_json()
    assert hd["count"] == 1 and hd["records"][0]["status"] == "COMPLETED"


def test_invoke_osai_unavailable_is_honest_accepted(client, auth_headers, runtime_dir, monkeypatch):
    # OSAI 不可用：禁止伪造 COMPLETED，回到已受理/部分连接/无证据
    _patch_adapter(monkeypatch,
                   {"connected": False, "status": "UNAVAILABLE", "error": "OSAI_TIMEOUT", "osai": None})
    d = client.post("/lumenis/api/skills/invoke",
                    json={"skill_id": "S01", "task": "t"}, headers=auth_headers).get_json()
    assert d["status"] == "ACCEPTED"
    assert d["execution_status"] == "PARTIALLY_CONNECTED"
    assert d["evidence_status"] == "NO_EVIDENCE"
    assert d["evaluation_status"] == "NO_DATA"


def test_invoke_permission_blocked_fail_close(client, auth_headers, runtime_dir, monkeypatch):
    res = {"connected": True, "status": "CONNECTED", "error": None, "osai": {
        "status": "BLOCKED", "trace_id": "TRACE-b", "evidence_id": None,
        "evaluation_id": None, "permission_check": {"allowed": False, "reason": "missing READ"},
    }}
    _patch_adapter(monkeypatch, res)
    d = client.post("/lumenis/api/skills/invoke",
                    json={"skill_id": "S02", "task": "t"}, headers=auth_headers).get_json()
    assert d["status"] == "BLOCKED"
    assert d["evidence_status"] == "NO_EVIDENCE"   # 权限在建证据前拒绝
    assert d["permission_check"]["allowed"] is False


def test_invoke_failed_keeps_evidence(client, auth_headers, runtime_dir, monkeypatch):
    res = {"connected": True, "status": "CONNECTED", "error": None, "osai": {
        "status": "FAILED", "trace_id": "TRACE-f", "evidence_id": "EV-f",
        "evaluation_id": None, "engine_id": "eng", "model_id": "glm-4.5-air",
        "permission_check": {"allowed": True}, "error": "provider error",
    }}
    _patch_adapter(monkeypatch, res)
    d = client.post("/lumenis/api/skills/invoke",
                    json={"skill_id": "S03", "task": "t"}, headers=auth_headers).get_json()
    assert d["status"] == "FAILED"
    assert d["evidence_status"] == "EVIDENCE_CREATED"  # 失败也留证
    assert d["evaluation_status"] == "NO_DATA"


def test_unknown_skill_404(client, auth_headers, runtime_dir, monkeypatch):
    _patch_adapter(monkeypatch, None, found=False)
    r = client.post("/lumenis/api/skills/invoke",
                    json={"skill_id": "SXX", "task": "t"}, headers=auth_headers)
    assert r.status_code == 404


def test_planned_skill_not_executable(client, auth_headers, runtime_dir, monkeypatch):
    _patch_adapter(monkeypatch, None, skill_status="PLANNED")
    r = client.post("/lumenis/api/skills/invoke",
                    json={"skill_id": "S40", "task": "t"}, headers=auth_headers)
    assert r.status_code == 400
    assert r.get_json()["status"] == "BLOCKED"


def test_adapter_invoke_maps_osai_and_least_privilege(monkeypatch):
    from lumenis_skill_adapter import CrossCoreSkillAdapter
    ad = CrossCoreSkillAdapter(osai_root="/tmp/osai", timeout=5)
    captured = {}

    def fake_run(script, timeout=None, argv=None):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(argv[0])
        return {"status": "SUCCESS", "trace_id": "T1"}

    monkeypatch.setattr(ad, "_run_osai", fake_run)
    out = ad.invoke_skill("task", "S01", workspace="engineering")
    assert out["connected"] is True and out["osai"]["trace_id"] == "T1"
    assert captured["timeout"] == 90.0                 # 云模型放宽超时
    perms = captured["payload"]["user_permissions"]
    assert "COMMIT" not in perms and "PUSH" not in perms  # 最小权限，不含写权限
    assert "READ" in perms


def test_adapter_invoke_unavailable(monkeypatch):
    from lumenis_skill_adapter import CrossCoreSkillAdapter
    ad = CrossCoreSkillAdapter(osai_root="/tmp/osai", timeout=5)
    monkeypatch.setattr(ad, "_run_osai", lambda *a, **k: None)
    ad._last_error = "OSAI_TIMEOUT"
    out = ad.invoke_skill("t", "S01")
    assert out["connected"] is False and out["status"] == "UNAVAILABLE"
