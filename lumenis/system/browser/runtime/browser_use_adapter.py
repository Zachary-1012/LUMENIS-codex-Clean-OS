"""Optional Browser Use boundary for the existing LUMENIS Browser session.

The upstream agent is deliberately not imported or instantiated until the
existing Product task, owned Gateway and enforced network boundary are all
available. Browser Use's own BrowserSession/tools would otherwise create a
second browser/action path around the LUMENIS Action Firewall.
"""
from __future__ import annotations

import importlib.util
import os
from typing import Any, Dict, Optional


BROWSER_USE_VERSION = "0.13.10"
EGRESS_ENFORCEMENT = "NOT_ENFORCED"
_ENABLED = os.getenv("LUMENIS_BROWSER_USE_ENABLED", "false").strip().lower() == "true"


def _owned_gateway_status() -> Dict[str, Any]:
    """Read the existing gateway status only; never invoke inference here."""
    try:
        from lumenis.system.ai_gateway.core import owned_inference_status

        status = owned_inference_status()
        if not isinstance(status, dict):
            return {"available": False, "service_binding": "UNKNOWN"}
        return {
            "available": status.get("available") is True,
            "service_binding": status.get("service_binding"),
            "reason": status.get("reason") or status.get("code"),
        }
    except Exception:
        return {"available": False, "service_binding": "STATUS_UNAVAILABLE"}


def browser_use_readiness(session: Any) -> Dict[str, Any]:
    """Return a truthful gate report without loading the optional package."""
    blockers = []
    if not _ENABLED:
        blockers.append("BROWSER_USE_DISABLED")
    if getattr(getattr(session, "status", None), "value", None) != "running":
        blockers.append("BROWSER_SESSION_NOT_RUNNING")
    task_binding = getattr(session, "task_binding_status", "UNBOUND")
    if task_binding != "BOUND":
        blockers.append(
            "BROWSER_TASK_BINDING_UNVERIFIED"
            if task_binding == "UNVERIFIED"
            else "BROWSER_TASK_BINDING_UNBOUND"
        )
    if getattr(session, "source_binding", None) is None:
        blockers.append("BROWSER_SOURCE_USE_BINDING_UNAVAILABLE")
    gateway = _owned_gateway_status()
    if gateway.get("available") is not True or gateway.get("service_binding") != "BOUND":
        blockers.append("OWNED_GATEWAY_NOT_BOUND")
    # The current browser_surface/Playwright path does not enforce DNS pinning,
    # private-address rejection, redirects and WebSocket egress as one boundary.
    if EGRESS_ENFORCEMENT != "ENFORCED":
        blockers.append("BROWSER_EGRESS_ENFORCEMENT_UNAVAILABLE")
    # The existing Session has an Action Firewall, but no Browser Use tool bridge
    # that routes every proposed action through it yet.
    blockers.append("BROWSER_USE_ACTION_FIREWALL_BRIDGE_UNBOUND")
    installed = importlib.util.find_spec("browser_use") is not None
    if _ENABLED and not installed:
        blockers.append("BROWSER_USE_DEPENDENCY_UNAVAILABLE")
    return {
        "status": "AVAILABLE" if not blockers else "UNAVAILABLE",
        "provider": "owned_gateway",
        "browser_use_version": BROWSER_USE_VERSION,
        "feature_enabled": _ENABLED,
        "dependency_installed": installed,
        "egress_enforcement": EGRESS_ENFORCEMENT,
        "task_binding_status": getattr(session, "task_binding_status", "UNBOUND"),
        "task_binding_verified": False,
        "gateway": gateway,
        "fallback_allowed": False,
        "blockers": blockers,
    }


def run_browser_use_step(
    session: Any,
    *,
    instruction: Optional[str] = None,
    source_binding: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fail closed until a typed task, gateway and enforced action bridge exist."""
    readiness = browser_use_readiness(session)
    if readiness["status"] != "AVAILABLE":
        return {
            "ok": False,
            "status": "UNAVAILABLE",
            "code": readiness["blockers"][0] if readiness["blockers"] else "BROWSER_USE_UNAVAILABLE",
            "readiness": readiness,
            "output": None,
        }
    # Keep this explicit: no third-party model/provider client is created here.
    # An available call requires an owner-supplied, permission-checked
    # BaseChatModel bridge and an action bridge that cannot bypass the runtime.
    return {
        "ok": False,
        "status": "UNAVAILABLE",
        "code": "BROWSER_USE_GATEWAY_ACTION_BRIDGE_UNBOUND",
        "readiness": readiness,
        "output": None,
    }
