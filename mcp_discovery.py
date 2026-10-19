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
import hashlib
import select
import math
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Any, Dict, Iterable, List, Optional, Sequence

_MAX_LINE_BYTES = 1024 * 1024
_MAX_ITEMS = 128
_MAX_STRING = 4096
_MAX_DEPTH = 8
_SAFE_ENV_KEYS = {
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "SystemRoot",
    "WINDIR",
    "LOCALAPPDATA",
    "PROGRAMDATA",
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
        if not isinstance(key, str):
            raise ValueError("MCP discovery environment is invalid")
        if any(
            marker in key.upper()
            for marker in ("TOKEN", "API_KEY", "SECRET", "PASSWORD", "COOKIE", "SESSION")
        ):
            raise ValueError("MCP discovery does not accept secret environment variables")
        if (
            not isinstance(key, str)
            or not isinstance(value, str)
            or len(key) > 128
            or len(value) > 2048
        ):
            raise ValueError("MCP discovery environment is invalid")
        env[key] = value
    return env


def _send(proc: subprocess.Popen, message: Dict[str, Any], deadline=None) -> None:
    raw = json.dumps(message, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(raw.encode("utf-8")) > _MAX_LINE_BYTES:
        raise ValueError("MCP request exceeds size limit")
    if proc.stdin is None:
        raise RuntimeError("MCP process stdin is unavailable")
    deadline = deadline if deadline is not None else time.monotonic() + 10
    data = (raw + "\n").encode("utf-8")
    fd = proc.stdin.fileno()
    os.set_blocking(fd, False)
    while data:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], max(0, remaining))[1]:
            raise TimeoutError("MCP request write timed out")
        try:
            sent = os.write(fd, data)
        except BlockingIOError:
            continue
        data = data[sent:]


def _reader(proc: subprocess.Popen, queue: Queue) -> None:
    def emit(kind, value):
        try:
            queue.put_nowait((kind, value))
            return True
        except Full:
            return False

    if proc.stdout is None:
        emit("error", "MCP process stdout is unavailable")
        return
    while True:
        try:
            line = proc.stdout.readline(_MAX_LINE_BYTES + 1)
            if not line:
                emit("eof", None)
                return
            if len(line.encode("utf-8")) > _MAX_LINE_BYTES:
                emit("error", "MCP response exceeds size limit")
                return
            value = json.loads(
                line,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")),
                object_pairs_hook=_unique_object,
            )
        except (TypeError, ValueError, RecursionError, UnicodeError, OSError):
            emit("error", "MCP response is not valid bounded UTF-8 JSON")
            return
        if not isinstance(value, dict):
            emit("error", "MCP response must be a JSON object")
            return
        if not emit("message", _RpcMessage(value)):
            return


def _next_response(queue: Queue, request_id: int, deadline: float, proc=None) -> Dict[str, Any]:
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
        if message.get("jsonrpc") != "2.0":
            raise RuntimeError("MCP response has an unsupported jsonrpc version")
        if "id" not in message and isinstance(message.get("method"), str):
            if "result" in message or "error" in message:
                raise RuntimeError("invalid MCP notification")
            continue
        if "method" in message and "id" in message and proc is not None:
            if (
                type(message["id"]) not in (int, str)
                or not isinstance(message["method"], str)
                or "result" in message
                or "error" in message
            ):
                raise RuntimeError("invalid MCP server request")
            reply = {"jsonrpc": "2.0", "id": message["id"]}
            if message["method"] == "ping":
                reply["result"] = {}
            else:
                reply["error"] = {"code": -32601, "message": "Client capability not supported"}
            _send(proc, reply, deadline)
            continue
        if type(message.get("id")) is not int or message["id"] != request_id:
            raise RuntimeError("MCP response id does not match request")
        if "method" in message or (("result" in message) == ("error" in message)):
            raise RuntimeError("invalid MCP JSON-RPC response")
        if "error" in message:
            error = message["error"]
            if (
                not isinstance(error, dict)
                or type(error.get("code")) is not int
                or not isinstance(error.get("message"), str)
            ):
                raise RuntimeError("invalid MCP JSON-RPC error")
            raise RuntimeError("MCP server returned an RPC error")
        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("MCP response result must be an object")
        return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _initialize(result):
    if result.get("protocolVersion") != "2025-11-25":
        raise ValueError("unsupported MCP protocol version; supported: 2025-11-25")
    caps = result.get("capabilities")
    info = result.get("serverInfo")
    if (
        not isinstance(caps, dict)
        or not isinstance(info, dict)
        or not all(isinstance(info.get(k), str) and info[k] for k in ("name", "version"))
    ):
        raise ValueError("invalid MCP initialize result")
    if any(k in caps and not isinstance(caps[k], dict) for k in ("tools", "resources", "prompts")):
        raise ValueError("invalid MCP capability declaration")
    return caps


def _schema_validator(schema):
    from jsonschema import Draft202012Validator
    from referencing import Registry
    from referencing.exceptions import NoSuchResource

    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("MCP schema must describe an object")
    if (
        schema.get("$schema", "https://json-schema.org/draft/2020-12/schema")
        != "https://json-schema.org/draft/2020-12/schema"
    ):
        raise ValueError("unsupported MCP JSON Schema dialect")

    def inspect(value, depth=0):
        if depth > 48:
            raise ValueError("MCP schema exceeds depth limit")
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("$ref", "$dynamicRef") and (
                    not isinstance(item, str) or not item.startswith("#")
                ):
                    raise ValueError("external MCP schema references are forbidden")
                inspect(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                inspect(item, depth + 1)

    inspect(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise ValueError("invalid MCP JSON Schema") from exc

    def deny(uri):
        raise NoSuchResource(ref=uri)

    return Draft202012Validator(schema, registry=Registry(retrieve=deny))


def _validate_instance(schema, instance, label):
    try:
        _schema_validator(schema).validate(instance)
    except Exception as exc:
        raise ValueError("MCP " + label + " failed schema validation") from exc


def tool_contract_hash(tool):
    """Hash reviewed behavioral contract; discovery alone never grants approval."""
    execution = tool.get("execution")
    if execution is not None and (
        not isinstance(execution, dict)
        or not isinstance(execution.get("taskSupport", "forbidden"), str)
        or execution.get("taskSupport", "forbidden") not in {"required", "optional", "forbidden"}
    ):
        raise ValueError("invalid MCP tool execution capability")
    for key in ("inputSchema", "outputSchema"):
        if key == "inputSchema" or key in tool:
            _schema_validator(tool.get(key))
    contract = {
        key: tool.get(key)
        for key in ("name", "inputSchema", "outputSchema", "annotations", "execution")
    }
    return hashlib.sha256(
        json.dumps(
            contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def _list_all(request, field):
    items, cursors, names = [], set(), set()
    params = None
    for _ in range(32):
        result = request(field + "/list", params)
        page = result.get(field)
        if not isinstance(page, list):
            raise ValueError("invalid MCP list result")
        for item in page:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("name"), str)
                or not item["name"]
                or len(item["name"]) > 256
            ):
                raise ValueError("invalid MCP list item")
            if field == "resources" and (not isinstance(item.get("uri"), str) or not item["uri"]):
                raise ValueError("invalid MCP resource URI")
            identity = item.get("uri") if field == "resources" else item["name"]
            if identity in names:
                raise ValueError("duplicate MCP list item")
            names.add(identity)
            if field == "tools":
                tool_contract_hash(item)
            items.append(item)
        if len(json.dumps(items, ensure_ascii=False).encode("utf-8")) > _MAX_LINE_BYTES:
            raise ValueError("MCP catalog exceeds total size limit")
        if len(items) > _MAX_ITEMS:
            raise ValueError("MCP list exceeds item limit")
        cursor = result.get("nextCursor")
        if cursor is None:
            return items
        if (
            not isinstance(cursor, str)
            or not cursor
            or len(cursor) > _MAX_STRING
            or cursor in cursors
        ):
            raise ValueError("invalid or repeated MCP pagination cursor")
        cursors.add(cursor)
        params = {"cursor": cursor}
    raise ValueError("MCP pagination exceeds page limit")


def _close_process(proc):
    if proc is None:
        return
    try:
        if proc.stdin:
            proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)
    for stream in (proc.stdout, proc.stderr):
        if stream:
            stream.close()


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
    if (
        not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
        or timeout > 60
    ):
        base["errors"].append("MCP discovery timeout must be between 0 and 60 seconds")
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
        return base

    proc = None
    queue: Queue = Queue(maxsize=256)
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="strict",
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
            _send(proc, message, deadline)
            base["trace"]["request_count"] = request_id
            return _next_response(queue, request_id, deadline, proc)

        initialized = request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "lumenis-discovery", "version": "1.0.0"},
            },
        )
        capabilities = _initialize(initialized)
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        discovered = {
            field: _list_all(request, field) if field in capabilities else []
            for field in ("tools", "resources", "prompts")
        }
        base.update(
            {
                "ok": True,
                "state": "DISCOVERED",
                "server_info": _bounded(initialized.get("serverInfo", {})),
                "protocol_version": initialized.get("protocolVersion"),
                "capabilities": _bounded(initialized.get("capabilities", {})),
                "tools": discovered["tools"],
                "tool_contracts": {
                    item["name"]: tool_contract_hash(item) for item in discovered["tools"]
                },
                "resources": discovered["resources"],
                "prompts": discovered["prompts"],
            }
        )
    except TimeoutError as exc:
        base["state"] = "TIMEOUT"
        base["errors"].append(str(exc))
    except (OSError, RuntimeError, ValueError, RecursionError) as exc:
        base["state"] = "PROTOCOL_ERROR"
        base["errors"].append(str(exc))
    finally:
        _close_process(proc)
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
    return base


def _contains_sensitive_field(value: Any) -> bool:
    """Reject secret-shaped MCP arguments before a tool process is started."""
    sensitive = {
        "password",
        "token",
        "api_key",
        "secret",
        "cookie",
        "session",
        "private_key",
        "credential",
        "authorization",
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
        "password",
        "token",
        "api_key",
        "secret",
        "cookie",
        "session",
        "private_key",
        "credential",
        "authorization",
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
    reviewed_tool_contracts: Optional[Dict[str, str]] = None,
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
        if isinstance(permissions_granted, (list, tuple, set))
        else []
    )
    allowlist_values = (
        [str(item) for item in list(allowed_tools)[:128]]
        if isinstance(allowed_tools, (list, tuple, set))
        else []
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
    if (
        not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
        or timeout > 60
    ):
        return blocked("MCP call timeout must be between 0 and 60 seconds")

    proc = None
    queue: Queue = Queue(maxsize=256)
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="strict",
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
            _send(proc, message, deadline)
            base["trace"]["request_count"] = request_id
            return _next_response(queue, request_id, deadline, proc)

        initialized = request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "lumenis-client", "version": "1.0.0"},
            },
        )
        capabilities = _initialize(initialized)
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        if "tools" not in capabilities:
            return blocked("MCP tools capability not advertised", "CAPABILITY_UNAVAILABLE")
        tools = _list_all(request, "tools")
        selected = next((item for item in tools if item.get("name") == tool_name), None)
        if selected is None:
            return blocked("requested MCP tool was not advertised", "TOOL_NOT_FOUND")
        if (selected.get("execution") or {}).get("taskSupport") == "required":
            return blocked(
                "Task-augmented MCP tools are not supported by this client",
                "CAPABILITY_UNAVAILABLE",
            )
        annotations = selected.get("annotations")
        if not isinstance(annotations, dict) or annotations.get("readOnlyHint") is not True:
            return blocked("MCP tool lacks an explicit readOnlyHint", "READ_ONLY_GATE_BLOCKED")
        if annotations.get("destructiveHint") is True:
            return blocked("MCP tool is marked destructive", "READ_ONLY_GATE_BLOCKED")

        if "read_only" not in permission_values:
            return blocked("permission read_only is required", "READ_ONLY_GATE_BLOCKED")
        expected = (reviewed_tool_contracts or {}).get(tool_name)
        if not expected:
            return blocked("MCP tool contract requires approval", "CONTRACT_APPROVAL_REQUIRED")
        if expected != tool_contract_hash(selected):
            return blocked(
                "MCP tool contract changed; renewed approval required", "CONTRACT_CHANGED"
            )
        _validate_instance(selected["inputSchema"], arguments, "arguments")
        base["server_info"] = _redacted(initialized.get("serverInfo", {}))
        base["protocol_version"] = initialized.get("protocolVersion")
        base["tool_definition"] = _redacted(selected)
        base["security"]["tool_calls"] = 1
        call_result = request("tools/call", {"name": tool_name, "arguments": arguments})
        if "isError" in call_result and type(call_result["isError"]) is not bool:
            raise ValueError("invalid MCP tool isError flag")
        content = call_result.get("content")
        if not isinstance(content, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("type"), str) for item in content
        ):
            raise ValueError("invalid MCP tool content")
        for item in content:
            kind = item["type"]
            required = {
                "text": ("text",),
                "image": ("data", "mimeType"),
                "audio": ("data", "mimeType"),
                "resource_link": ("name", "uri"),
            }
            if kind in required:
                if any(not isinstance(item.get(key), str) for key in required[kind]):
                    raise ValueError("invalid MCP content block")
            elif kind == "resource":
                resource = item.get("resource")
                if (
                    not isinstance(resource, dict)
                    or not isinstance(resource.get("uri"), str)
                    or not any(isinstance(resource.get(key), str) for key in ("text", "blob"))
                ):
                    raise ValueError("invalid MCP embedded resource")
            else:
                raise ValueError("unsupported MCP content block")
        if "structuredContent" in call_result and not isinstance(
            call_result["structuredContent"], dict
        ):
            raise ValueError("invalid MCP structuredContent")
        if "outputSchema" in selected and call_result.get("isError") is not True:
            _validate_instance(
                selected["outputSchema"], call_result.get("structuredContent"), "structured output"
            )
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
    except (OSError, RuntimeError, ValueError, RecursionError) as exc:
        base["state"] = "PROTOCOL_ERROR"
        base["errors"].append(str(exc))
    finally:
        _close_process(proc)
        base["trace"]["duration_ms"] = int((time.monotonic() - started) * 1000)
    return base
