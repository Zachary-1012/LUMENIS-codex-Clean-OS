"""SYS-01 must not present partial RuntimeGuardian observations as healthy."""

from __future__ import annotations

import copy

import pytest

import experience_screens
import runtime_guardian


_HEALTHY = {
    "overall": "healthy",
    "workers": {"total": 0, "failed": 0},
    "dlq": {"total": 0},
    "circuit_breakers": {},
    "reaper_running": True,
    "guardian_name": "test-guardian",
    "timestamp": "2026-09-23T12:00:00Z",
}


def _screen(monkeypatch: pytest.MonkeyPatch, health: dict) -> dict:
    monkeypatch.setattr(runtime_guardian, "legacy_health_check", lambda: health)
    return experience_screens._build_sys01()


def _overall(screen: dict) -> tuple[str | None, str, str]:
    runtime = next(section for section in screen["sections"] if section["type"] == "runtime")
    item = next(item for item in runtime["items"] if item["name"] == "总体状态")
    return screen["truth"]["overall"], item["state"], item["detail"]


def test_healthy_requires_running_reaper_and_complete_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    screen = _screen(monkeypatch, copy.deepcopy(_HEALTHY))

    assert _overall(screen) == ("healthy", "ok", "healthy")
    assert screen["runtime_observation"]["state"] == "ready"


def test_stopped_reaper_degrades_system_overall(monkeypatch: pytest.MonkeyPatch) -> None:
    health = copy.deepcopy(_HEALTHY)
    health["reaper_running"] = False

    screen = _screen(monkeypatch, health)

    assert _overall(screen) == ("degraded", "warn", "degraded")
    assert screen["runtime_observation"]["state"] == "ready"


@pytest.mark.parametrize("missing", ["reaper_running", "workers", "dlq", "circuit_breakers"])
def test_missing_guardrail_or_counts_cannot_look_healthy(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    health = copy.deepcopy(_HEALTHY)
    health.pop(missing)

    screen = _screen(monkeypatch, health)

    assert _overall(screen) == (None, "offline", "unknown")
    assert screen["runtime_observation"]["state"] == "unavailable"
    assert screen["runtime_observation"]["trace_id"] is None


def test_trace_changes_with_real_guardrail_state(monkeypatch: pytest.MonkeyPatch) -> None:
    healthy = _screen(monkeypatch, copy.deepcopy(_HEALTHY))
    stopped = copy.deepcopy(_HEALTHY)
    stopped["reaper_running"] = False
    degraded = _screen(monkeypatch, stopped)

    assert healthy["runtime_observation"]["trace_id"] != degraded["runtime_observation"]["trace_id"]
