# -*- coding: utf-8 -*-
"""Cross-Core adapter serialization and least-privilege contract.

Authenticated compatibility-route roundtrips now live in
 test_skill_api_authorization.py, using actual sessions, DB and Permission.
An unauthenticated FakeAdapter result is not an execution authorization proof.
"""
import json


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
