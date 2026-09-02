# -*- coding: utf-8 -*-
"""采集运维控制面 RuntimeSwitch 测试（研究自 baldur System-Control 落地）。"""
import os

import pytest

from collector_guard.runtime_switch import RuntimeSwitch


@pytest.fixture
def sw(tmp_path):
    return RuntimeSwitch(state_path=str(tmp_path / "switch.json"),
                         audit_path=str(tmp_path / "audit.jsonl"))


def test_default_enabled_live(sw):
    st = sw.status()
    assert st["enabled"] is True and st["dry_run"] is False
    assert st["state"] == "ENABLED"
    assert sw.is_enabled() is True and sw.is_dry_run() is False


def test_disable_requires_reason(sw):
    r = sw.set_enabled(False, reason=None)
    assert r["ok"] is False
    assert "reason" in r["error"]
    assert sw.is_enabled() is True  # 未生效


def test_disable_with_reason(sw):
    r = sw.set_enabled(False, reason="incident response", actor="ops")
    assert r["ok"] is True
    assert r["state"] == "DISABLED"
    assert sw.is_enabled() is False


def test_enable_requires_confirm(sw):
    sw.set_enabled(False, reason="test")
    r = sw.set_enabled(True)  # 无 confirm
    assert r["ok"] is False
    assert sw.is_enabled() is False
    r2 = sw.set_enabled(True, confirm=True)
    assert r2["ok"] is True and sw.is_enabled() is True


def test_dry_run_on_off(sw):
    r = sw.set_dry_run(True)
    assert r["ok"] is True and r["state"] == "DRY_RUN"
    assert sw.is_dry_run() is True
    # 退出需 confirm
    r2 = sw.set_dry_run(False)
    assert r2["ok"] is False and sw.is_dry_run() is True
    r3 = sw.set_dry_run(False, confirm=True)
    assert r3["ok"] is True and r3["state"] == "ENABLED"


def test_disable_sticks_across_restart(tmp_path):
    p = str(tmp_path / "switch.json")
    a = str(tmp_path / "audit.jsonl")
    s1 = RuntimeSwitch(state_path=p, audit_path=a)
    s1.set_enabled(False, reason="maintenance")
    s2 = RuntimeSwitch(state_path=p, audit_path=a)  # 模拟重启
    assert s2.is_enabled() is False  # 重启保持 disabled，不静默重新启用


def test_fail_safe_on_unreadable(tmp_path):
    p = str(tmp_path / "missing.json")
    sw = RuntimeSwitch(state_path=p, audit_path=str(tmp_path / "a.jsonl"))
    # 读不到状态 -> fail-safe enabled + live
    assert sw.is_enabled() is True and sw.is_dry_run() is False


def test_audit_trail_records_flips(sw):
    sw.set_enabled(False, reason="incident", actor="admin")
    sw.set_enabled(True, confirm=True, reason="resolved", actor="admin")
    trail = sw.audit_trail()
    assert len(trail) == 2
    assert trail[0]["action"] == "disable" and trail[0]["reason"] == "incident"
    assert trail[1]["action"] == "enable" and trail[1]["actor"] == "admin"
