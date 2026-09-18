# -*- coding: utf-8 -*-
"""Registered local MCP Skill runtime.

This is the one production adapter for Skills whose runtime is MCP.  It does
not create a second registry, does not write Canonical Data, and never treats
an MCP response as production truth.  Installation is restricted to the
canonical local Skill package root; invocation is read-only, permissioned,
human-approved, bounded, and delegated to the existing ``mcp_discovery``
firewall.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from mcp_discovery import call_mcp_stdio, discover_mcp_stdio


PACKAGE_ROOT = (Path(__file__).resolve().parent / "runtime" / "skill_packages").resolve()
READ_ONLY_PERMISSIONS = (
    "mcp:tools/call",
    "read_only",
    "network.public_sources",
    "evidence.staging",
)


def _json_list(value: Any) -> List[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:128]


def _package_path(install_path: Any) -> Path:
    raw = str(install_path or "").strip()
    if not raw:
        raise ValueError("MCP Skill install_path is required")
    path = Path(raw).resolve()
    try:
        path.relative_to(PACKAGE_ROOT)
    except ValueError as exc:
        raise ValueError("MCP Skill must be installed below the canonical Skill package root") from exc
    if not path.is_dir():
        raise ValueError("MCP Skill install_path does not exist")
    return path


def validate_installation(install_path: Any, *, expected_skill_id: str = "",
                          expected_version: str = "") -> Dict[str, Any]:
    """Validate a built local package without starting it."""
    try:
        path = _package_path(install_path)
    except ValueError as exc:
        return {"ok": False, "state": "BLOCKED", "errors": [str(exc)]}

    manifest_path = path / "manifest.json"
    package_path = path / "package.json"
    launcher = path / "scripts" / "launcher.mjs"
    entry = path / "dist" / "src" / "index.js"
    node_modules = path / "node_modules"
    errors: List[str] = []
    manifest: Dict[str, Any] = {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"manifest unreadable: {type(exc).__name__}")
    skill_id = str(manifest.get("name") or manifest.get("skill_id") or "").strip()
    version = str(manifest.get("version") or "").strip()
    if expected_skill_id and skill_id != expected_skill_id:
        errors.append("installed manifest skill_id does not match the registered Skill")
    if expected_version and version != expected_version:
        errors.append("installed manifest version does not match the registered Skill")
    for required, label in (
        (package_path, "package.json"),
        (launcher, "scripts/launcher.mjs"),
        (entry, "dist/src/index.js"),
        (node_modules, "node_modules"),
    ):
        if not required.exists():
            errors.append(f"missing built runtime: {label}")
    if errors:
        return {
            "ok": False, "state": "NOT_READY", "install_path": str(path),
            "skill_id": skill_id, "version": version, "errors": errors,
        }
    return {
        "ok": True, "state": "READY", "install_path": str(path),
        "skill_id": skill_id, "version": version,
        "manifest_path": str(manifest_path),
        "entrypoint": str(launcher),
        "errors": [],
    }


def _entrypoint(info: Dict[str, Any]) -> Tuple[str, List[str], Path]:
    package = _package_path(info.get("install_path"))
    raw = info.get("entrypoint") or ""
    if isinstance(raw, dict):
        descriptor = raw
    else:
        try:
            descriptor = json.loads(str(raw))
        except (TypeError, ValueError) as exc:
            raise ValueError("registered MCP entrypoint is not valid JSON") from exc
    if not isinstance(descriptor, dict):
        raise ValueError("registered MCP entrypoint must be an object")
    command = str(descriptor.get("command") or "").strip()
    args = descriptor.get("args", [])
    if not command or not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise ValueError("registered MCP entrypoint is incomplete")
    resolved_command = Path(command)
    if not resolved_command.is_absolute():
        resolved = shutil.which(command)
        if not resolved:
            raise ValueError(f"MCP runtime command is unavailable: {command}")
        command = resolved
    elif not resolved_command.is_file():
        raise ValueError("registered MCP runtime command does not exist")
    safe_args: List[str] = []
    for arg in args[:16]:
        # Registered args may be flags, but package files must stay inside the
        # package root.  The installer stores the launcher as an absolute path.
        if not arg.startswith("-"):
            candidate = Path(arg)
            if not candidate.is_absolute():
                candidate = package / arg
            candidate = candidate.resolve()
            try:
                candidate.relative_to(package)
            except ValueError as exc:
                raise ValueError("MCP entrypoint argument escapes its install root") from exc
            if not candidate.is_file():
                raise ValueError("MCP entrypoint file does not exist")
            safe_args.append(str(candidate))
        else:
            safe_args.append(arg)
    return command, safe_args, package


def build_entrypoint(install_path: Any) -> Dict[str, Any]:
    """Build an absolute stdio entrypoint for a validated local package."""
    path = _package_path(install_path)
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise ValueError("Node.js >=22 is required for the MCP Skill runtime")
    launcher = (path / "scripts" / "launcher.mjs").resolve()
    try:
        launcher.relative_to(path)
    except ValueError as exc:
        raise ValueError("MCP launcher is outside the install root") from exc
    if not launcher.is_file():
        raise ValueError("MCP launcher is missing")
    return {"command": str(Path(node).resolve()), "args": [str(launcher)]}


def discover_registered_mcp(info: Dict[str, Any], *, timeout: float = 30.0) -> Dict[str, Any]:
    """Start only the bounded discovery process; no MCP tool is called."""
    try:
        command, args, _ = _entrypoint(info)
    except ValueError as exc:
        return {"ok": False, "state": "NOT_READY", "errors": [str(exc)]}
    return discover_mcp_stdio([command], args, allow_process=True, timeout=timeout,
                              extra_env={"TRENTHUB_AUTOUPDATE": "0"})


def invoke_registered_mcp(info: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke one allowlisted read-only MCP tool through the product chain."""
    payload = payload if isinstance(payload, dict) else {}
    package_check = validate_installation(
        info.get("install_path"),
        expected_skill_id=str(info.get("skill_id") or ""),
        expected_version=str(info.get("active_version") or info.get("version") or ""),
    )
    if not package_check.get("ok"):
        return {"ok": False, "state": package_check.get("state", "NOT_READY"),
                "errors": package_check.get("errors", [])}
    try:
        command, args, _ = _entrypoint(info)
    except ValueError as exc:
        return {"ok": False, "state": "BLOCKED", "errors": [str(exc)]}

    tool_name = str(payload.get("tool_name") or "").strip()
    arguments = payload.get("arguments", {})
    allowed_tools = _json_list(info.get("tools_json"))
    granted = _json_list(info.get("permissions_granted_json"))
    if not tool_name:
        return {"ok": False, "state": "BLOCKED", "errors": ["tool_name is required"]}
    if tool_name not in allowed_tools:
        return {"ok": False, "state": "BLOCKED", "errors": ["tool is not in the registered allowlist"]}
    if payload.get("human_approved") is not True:
        return {"ok": False, "state": "BLOCKED", "errors": ["MCP tool call requires human approval"]}
    if not isinstance(arguments, dict):
        return {"ok": False, "state": "BLOCKED", "errors": ["MCP tool arguments must be an object"]}
    result = call_mcp_stdio(
        [command], args,
        tool_name=tool_name,
        arguments=arguments,
        allow_process=True,
        allow_tool_call=True,
        human_approved=True,
        permissions_granted=granted,
        allowed_tools=allowed_tools,
        timeout=min(float(payload.get("timeout", 30.0) or 30.0), 60.0),
        extra_env={"TRENTHUB_AUTOUPDATE": "0"},
    )
    result["skill_id"] = info.get("skill_id")
    result["production_truth_write"] = False
    return result
