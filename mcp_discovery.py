# -*- coding: utf-8 -*-
"""LUMENIS read-only MCP capability discovery.

This module implements the small, product-owned part of the MCP stdio
transport needed before a Skill can be registered.  It intentionally stops at
``initialize`` plus ``tools/list`` / ``resources/list`` / ``prompts/list``:
there is no tool call, file import, dependency install, secret injection, or
production-side effect here.

The result is discovery evidence, not permission, installation, enablement,
or production truth.  Calls that need a process must opt in explicitly and
must provide an argv list; shell strings are never accepted.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Dict, Iterable, List, Optional, Sequence


_MAX_LINE_BYTES = 1024 * 1024
_MAX_ITEMS = 128
_MAX_STRING = 4096
_MAX_DEPTH = 8
_SAFE_ENV_KEYS = {
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
    "SystemRoot", "WINDIR", "LOCALAPPDATA", "PROGRAMDATA",
}


@dataclass(frozen=True)
class _RpcMessage:
    value: Dict[str, Any]


def _bounded(value: Any, *, depth: int = 0) -> Any:
    """Return a bounded JSON-compatible copy of untrusted server metadata."""
    if depth >= _MAX_DEPTH:
        return "[truncated]"
    if isinstance(value, str):
        return value[:_MAX_STRING]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, list):
        return [_bounded(item, depth=depth + 1) for item in value[:_MAX_ITEMS]]
    if isinstance(value, dict):
        return {
            str(key)[:128]: _bounded(item, depth=depth + 1)
            for key, item in list(value.items())[:_MAX_ITEMS]
            if isinstance(key, (str, int, float, bool))
        }
    return str(value)[:_MAX_STRING]


def _safe_argv(command: Sequence[str], args: Sequence[str]) -> List[str]:
    if isinstance(command, (str, bytes)) or isinstance(args, (str, bytes)):
        raise ValueError("MCP stdio command and args must be argv lists, never shell strings")
    argv = list(command) + list(args)
    if not argv or len(argv) > 32:
        raise ValueError("MCP stdio argv must contain 1-32 entries")
    if any(not isinstance(item, str) or not item.strip() or len(item) > 512 for item in argv):
        raise ValueError("MCP stdio argv contains an invalid entry")
    return argv


def _safe_env(extra_env: Optional[Dict[str, str]]) -> Dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key in _SAFE_ENV_KEYS}
    for key, value in (extra_env or {}).items():
        if key.upper() in {"TOKEN", "API_KEY", "SECRET", "PASSWORD", "COOKIE", "SESSION"}:
            raise ValueError("MCP discovery does not accept secret environment variables")
        if not isinstance(key, str) or not isinstance(value, str) or len(key) > 128 or len(value) > 2048:
            raise ValueError("MCP discovery environment is invalid")
        env[key] = value
    return env


def _send(proc: subprocess.Popen, message: Dict[str, Any]) -> None:
    raw = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > _MAX_LINE_BYTES:
        raise ValueError("MCP request exceeds size limit")
    if proc.stdin is None:
        raise RuntimeError("MCP process stdin is unavailable")
    proc.stdin.write(raw + "\n")
    proc.stdin.flush()


def _reader(proc: subprocess.Popen, queue: Queue) -> None:
    if proc.stdout is None:
        queue.put(("error", "MCP process stdout is unavailable"))
        return
    while True:
        line = proc.stdout.readline()
        if not line:
            queue.put(("eof", None))
            return
        if len(line.encode("utf-8", errors="replace")) > _MAX_LINE_BYTES:
            queue.put(("error", "MCP response exceeds size limit"))
            return
        try:
            value = json.loads(line)
        except (TypeError, ValueError):
            queue.put(("error", "MCP response is not valid JSON"))
            return
        if isinstance(value, dict):
            queue.put(("message", _RpcMessage(value)))
        else:
            queue.put(("error", "MCP response must be a JSON object"))


def _next_response(queue: Queue, request_id: int, deadline: float) -> Dict[str, Any]:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("MCP discovery timed out")
        try:
            kind, payload = queue.get(timeout=remaining)
        except Empty as exc:
            raise TimeoutError("MCP discovery timed out") from exc
        if kind == "error":
            raise RuntimeError(str(payload))
        if kind == "eof":
            raise RuntimeError("MCP process closed before discovery completed")
        message = payload.value
        if message.get("id") != request_id:
            # Notifications and unrelated responses are ignored but never
            # interpreted as a successful response for this request.
            continue
        if message.get("jsonrpc") not in (None, "2.0"):
            raise RuntimeError("MCP response has an unsupported jsonrpc version")
        if isinstance(message.get("error"), dict):
            raise RuntimeError("MCP server returned a discovery error")
        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("MCP response result must be an object")
        return result


def _items(result: Dict[str, Any], field: str) -> List[Dict[str, Any]]:
    value = result.get(field, [])
    if not isinstance(value, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in value[:_MAX_ITEMS]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 256:
            continue
        normalized.append(_bounded(item))
    return normalized


def discover_mcp_stdio(
    command: Sequence[str],
    args: Sequence[str] = (),
    *,
    allow_process: bool = False,
    timeout: float = 10.0,
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Discover a stdio MCP server without invoking any tool.

    ``allow_process`` is intentionally false by default.  A future product
    route must obtain its owner/permission decision before setting it true.
    """
    started = time.monotonic()
    base = {
        "ok": False,
        "state": "BLOCKED",
        "transport": "stdio",
        "server_info": {},
        "protocol_version": None,
        "capabilities": {},
        "tools": [],
        "resources": [],
        "prompts": [],
        "security": {
            "process_started": False,
            "permissions_granted": [],
            "secrets_injected": False,
            "execution": "DISCOVERY_ONLY",
            "tool_calls": 0,
        },
        "trace": {"request_count": 0, "duration_ms": 0},
        "warnings": [],
        "errors": [],
    }
    try:
        argv = _safe_argv(command, args)
        env = _safe_env(extra_env)
    except ValueError as exc:
        base["errors"].append(str(exc))
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
        return base
    if not allow_process:
        base["errors"].append("process discovery requires explicit permission")
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
        return base
    if timeout <= 0 or timeout > 60:
        base["errors"].append("MCP discovery timeout must be between 0 and 60 seconds")
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
        return base

    proc = None
    queue: Queue = Queue()
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            env=env,
        )
        base["security"]["process_started"] = True
        reader = threading.Thread(target=_reader, args=(proc, queue), daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        request_id = 0

        def request(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            nonlocal request_id
            request_id += 1
            message: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
            if params is not None:
                message["params"] = params
            _send(proc, message)
            base["trace"]["request_count"] = request_id
            return _next_response(queue, request_id, deadline)

        initialized = request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "lumenis-discovery", "version": "1.0.0"},
            },
        )
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools_result = request("tools/list")
        try:
            resources_result = request("resources/list")
        except (RuntimeError, TimeoutError):
            resources_result = {}
            base["warnings"].append("resources/list unavailable or not advertised")
        try:
            prompts_result = request("prompts/list")
        except (RuntimeError, TimeoutError):
            prompts_result = {}
            base["warnings"].append("prompts/list unavailable or not advertised")
        base.update({
            "ok": True,
            "state": "DISCOVERED",
            "server_info": _bounded(initialized.get("serverInfo", {})),
            "protocol_version": initialized.get("protocolVersion"),
            "capabilities": _bounded(initialized.get("capabilities", {})),
            "tools": _items(tools_result, "tools"),
            "resources": _items(resources_result, "resources"),
            "prompts": _items(prompts_result, "prompts"),
        })
    except TimeoutError as exc:
        base["state"] = "TIMEOUT"
        base["errors"].append(str(exc))
    except (OSError, RuntimeError, ValueError) as exc:
        base["state"] = "PROTOCOL_ERROR"
        base["errors"].append(str(exc))
    finally:
        if proc is not None:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except OSError:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    proc.kill()
                except OSError:
                    pass
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
    return base


def _contains_sensitive_field(value: Any) -> bool:
    """Reject secret-shaped MCP arguments before a tool process is started."""
    sensitive = {
        "password", "token", "api_key", "secret", "cookie", "session",
        "private_key", "credential", "authorization",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in sensitive or any(
                marker in normalized for marker in ("password", "token", "secret", "cookie")
            ):
                return True
            if _contains_sensitive_field(item):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_field(item) for item in value)
    return False


def _redacted(value: Any, *, key: str = "", depth: int = 0) -> Any:
    """Bound and redact server-returned fields before crossing the API boundary."""
    normalized = key.strip().lower().replace("-", "_")
    if normalized in {
        "password", "token", "api_key", "secret", "cookie", "session",
        "private_key", "credential", "authorization",
    } or any(marker in normalized for marker in ("password", "token", "secret", "cookie")):
        return "[redacted]"
    if depth >= _MAX_DEPTH:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(item_key)[:128]: _redacted(item, key=str(item_key), depth=depth + 1)
            for item_key, item in list(value.items())[:_MAX_ITEMS]
        }
    if isinstance(value, list):
        return [_redacted(item, depth=depth + 1) for item in value[:_MAX_ITEMS]]
    if isinstance(value, str):
        return value[:_MAX_STRING]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:_MAX_STRING]


def call_mcp_stdio(
    command: Sequence[str],
    args: Sequence[str] = (),
    *,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    allow_process: bool = False,
    allow_tool_call: bool = False,
    human_approved: bool = False,
    permissions_granted: Sequence[str] = (),
    allowed_tools: Sequence[str] = (),
    timeout: float = 10.0,
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Call one reviewed read-only MCP tool through a bounded stdio session.

    This is deliberately stricter than MCP's advisory annotations.  The
    caller must separately provide process permission, tool-call permission,
    human approval, a reviewed tool allowlist, and the ``read_only`` grant.
    The result is returned as redacted staging data; this function never
    writes the LUMENIS database, Evidence, Canonical Data, or publication
    systems.
    """
    started = time.monotonic()
    permission_values = (
        [str(item) for item in list(permissions_granted)[:16]]
        if isinstance(permissions_granted, (list, tuple, set)) else []
    )
    allowlist_values = (
        [str(item) for item in list(allowed_tools)[:128]]
        if isinstance(allowed_tools, (list, tuple, set)) else []
    )
    base: Dict[str, Any] = {
        "ok": False,
        "state": "BLOCKED",
        "transport": "stdio",
        "server_info": {},
        "protocol_version": None,
        "tool": tool_name if isinstance(tool_name, str) else "",
        "tool_definition": {},
        "result": None,
        "security": {
            "process_started": False,
            "permissions_granted": permission_values,
            "secrets_injected": False,
            "execution": "READ_ONLY_TOOL_CALL",
            "tool_calls": 0,
            "production_truth_write": False,
        },
        "trace": {"request_count": 0, "duration_ms": 0},
        "warnings": [],
        "errors": [],
    }

    def blocked(message: str, state: str = "BLOCKED") -> Dict[str, Any]:
        base["state"] = state
        base["errors"].append(message)
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
        return base

    try:
        argv = _safe_argv(command, args)
        env = _safe_env(extra_env)
    except ValueError as exc:
        return blocked(str(exc))
    if not allow_process:
        return blocked("process execution requires explicit permission")
    if not allow_tool_call:
        return blocked("MCP tool call requires explicit permission")
    if not human_approved:
        return blocked("MCP tool call requires human approval")
    if not isinstance(permissions_granted, (list, tuple, set)):
        return blocked("permissions_granted must be a list")
    if not isinstance(allowed_tools, (list, tuple, set)):
        return blocked("allowed_tools must be a list")
    if "mcp:tools/call" not in set(permission_values):
        return blocked("permission mcp:tools/call is required")
    if not isinstance(tool_name, str) or not tool_name.strip() or len(tool_name) > 256:
        return blocked("tool_name is invalid")
    reviewed_tools = set(allowlist_values)
    if tool_name not in reviewed_tools:
        return blocked("tool is not in the reviewed allowlist")
    if not isinstance(arguments, dict):
        return blocked("MCP tool arguments must be an object")
    if _contains_sensitive_field(arguments):
        return blocked("MCP tool arguments contain sensitive fields")
    if timeout <= 0 or timeout > 60:
        return blocked("MCP call timeout must be between 0 and 60 seconds")

    proc = None
    queue: Queue = Queue()
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            env=env,
        )
        base["security"]["process_started"] = True
        reader = threading.Thread(target=_reader, args=(proc, queue), daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        request_id = 0

        def request(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            nonlocal request_id
            request_id += 1
            message: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
            if params is not None:
                message["params"] = params
            _send(proc, message)
            base["trace"]["request_count"] = request_id
            return _next_response(queue, request_id, deadline)

        initialized = request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "lumenis-client", "version": "1.0.0"},
            },
        )
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools_result = request("tools/list")
        tools = _items(tools_result, "tools")
        selected = next((item for item in tools if item.get("name") == tool_name), None)
        if selected is None:
            return blocked("requested MCP tool was not advertised", "TOOL_NOT_FOUND")
        annotations = selected.get("annotations")
        if not isinstance(annotations, dict) or annotations.get("readOnlyHint") is not True:
            return blocked("MCP tool lacks an explicit readOnlyHint", "READ_ONLY_GATE_BLOCKED")
        if annotations.get("destructiveHint") is True:
            return blocked("MCP tool is marked destructive", "READ_ONLY_GATE_BLOCKED")

        base["server_info"] = _redacted(initialized.get("serverInfo", {}))
        base["protocol_version"] = initialized.get("protocolVersion")
        base["tool_definition"] = _redacted(selected)
        base["security"]["tool_calls"] = 1
        call_result = request("tools/call", {"name": tool_name, "arguments": arguments})
        redacted_result = _redacted(call_result)
        base["result"] = redacted_result
        if call_result.get("isError") is True:
            base["state"] = "TOOL_ERROR"
            base["errors"].append("MCP tool reported an error")
            return base
        base["ok"] = True
        base["state"] = "CALLED"
    except TimeoutError as exc:
        base["state"] = "TIMEOUT"
        base["errors"].append(str(exc))
    except (OSError, RuntimeError, ValueError) as exc:
        base["state"] = "PROTOCOL_ERROR"
        base["errors"].append(str(exc))
    finally:
        if proc is not None:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except OSError:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    proc.kill()
                except OSError:
                    pass
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
    return base
