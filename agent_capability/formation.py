"""Server-owned call identity for the existing Router and AgentLoop.

Bindings are integrity records, never Permission or approval grants. Owners
must supply current safety configuration, environment and non-secret origin
scope, and declare implementation dependencies. They must serialize changes
with the same dispatch lock. Python introspection cannot prove arbitrary
undeclared global state or make an in-process plugin a security sandbox.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import struct
import threading
from types import CodeType


class FormationError(RuntimeError):
    """A pending call requires owner reconciliation; never choose a successor."""

    def __init__(self, reason, *, changed_fields=()):
        super().__init__(reason)
        self.changed_fields = tuple(changed_fields)


def canonical_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise FormationError("TOOL_IDENTITY_NOT_SERIALIZABLE") from exc


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path):
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        raise FormationError("TOOL_DEPENDENCY_UNAVAILABLE")
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _code_value(value):
    # Use documented code attributes and typed constants. marshal is an
    # interpreter serialization format, not a canonical semantic fingerprint.
    if isinstance(value, CodeType):
        names = ("co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals",
                 "co_stacksize", "co_flags", "co_names", "co_varnames", "co_freevars", "co_cellvars")
        return {"code": value.co_code.hex(), "constants": [_code_value(v) for v in value.co_consts],
                "exception_table": getattr(value, "co_exceptiontable", b"").hex(),
                "attributes": {name: getattr(value, name) for name in names}}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, tuple):
        return {"tuple": [_code_value(v) for v in value]}
    if isinstance(value, slice):
        # Python 3.14 stores literal slices in co_consts. Bind all three typed
        # components; repr/hash or ignoring the constant would lose semantics.
        return {"slice": [_code_value(value.start), _code_value(value.stop), _code_value(value.step)]}
    if isinstance(value, frozenset):
        return {"frozenset": sorted((_code_value(v) for v in value), key=canonical_bytes)}
    if isinstance(value, float):
        return {"float64": struct.pack("!d", value).hex()}
    if isinstance(value, complex):
        return {"complex": [_code_value(value.real), _code_value(value.imag)]}
    if value is Ellipsis:
        return {"ellipsis": True}
    if value is None or type(value) in {bool, int, str}:
        return value
    raise FormationError("TOOL_IMPLEMENTATION_IDENTITY_UNAVAILABLE")


def implementation_identity(handler, dependency_paths=()):
    # Capture the actual callable, not its registry name/version. Mutable
    # closures and owner flags belong in the mandatory runtime provider below.
    function = handler.__func__ if inspect.ismethod(handler) else handler
    code = getattr(function, "__code__", None)
    if code is None:
        raise FormationError("TOOL_IMPLEMENTATION_IDENTITY_UNAVAILABLE")
    source = inspect.getsourcefile(function)
    files = {str(Path(p).resolve()): file_digest(p) for p in dependency_paths}
    if source and Path(source).is_file():
        files[str(Path(source).resolve())] = file_digest(str(Path(source).resolve()))
    return digest({"module": function.__module__, "qualname": function.__qualname__,
                   "code": _code_value(code),
                   "defaults": function.__defaults__, "keyword_defaults": function.__kwdefaults__,
                   "files": files})


def runtime_identity(provider):
    if not callable(provider):
        raise FormationError("TOOL_RUNTIME_IDENTITY_NOT_BOUND")
    try:
        state = provider()
    except Exception as exc:
        raise FormationError("TOOL_RUNTIME_IDENTITY_UNAVAILABLE") from exc
    required = {"configuration", "environment", "origin_scope_id", "implementation_revision", "available"}
    if not isinstance(state, dict) or not required.issubset(state):
        raise FormationError("TOOL_RUNTIME_IDENTITY_INCOMPLETE")
    if (state["available"] is not True or not isinstance(state["configuration"], dict)
            or not isinstance(state["environment"], dict)
            or not isinstance(state["origin_scope_id"], str) or not state["origin_scope_id"]
            or not isinstance(state["implementation_revision"], str) or not state["implementation_revision"]):
        raise FormationError("TOOL_RUNTIME_UNAVAILABLE")
    # Persist only its digest: configuration and origin-session material stay
    # with the existing owner. A later approval cannot refill an old binding.
    return digest({"state": state, "provider_implementation": implementation_identity(provider)})


def request_identity(step):
    return digest({"step_id": step.step_id, "tool": step.tool, "action": step.action,
                   "params": step.params, "expected_output": step.expected_output,
                   "risk_level": step.risk_level})


def context_identity(context):
    # Never serialize a server seal or let a wire dictionary impersonate it.
    from lumenis.system.security.permission import (_is_server_local_workspace_principal,
        resolve_local_workspace_principal, LocalWorkspacePrincipal)
    actor = context.get("actor")
    manifest = context.get("agent_runtime") or {}
    local = _is_server_local_workspace_principal(actor)
    if local or manifest.get("principal_kind") == "local_workspace" or type(actor) is LocalWorkspacePrincipal:
        from agent_runtime.task_binding import _workspace_binding
        if (not local or resolve_local_workspace_principal(module="skills", action="read") is None
                or context.get("actor_id") is not None
                or manifest.get("workspace_binding") != _workspace_binding()
                or manifest.get("principal_ref") != "workspace:local"):
            raise FormationError("LOCAL_PRINCIPAL_BINDING_INVALID")
        actor = {"principal_kind": "local_workspace", "principal_ref": "workspace:local", "actor_id": None}
    identity = {key: context.get(key) for key in
                ("actor_id", "domain_id", "scope", "module", "role", "product", "permission_role")}
    identity["actor"] = actor
    if local:
        identity["workspace_binding"] = manifest["workspace_binding"]
    return digest(identity)


class FormedCall:
    """One captured handler and immutable input, held across admission."""

    def __init__(self, *, step, context, identity, invoke, lock, expected=None):
        self._identity = identity
        self._invoke = invoke
        self._lock = lock
        self._step = deepcopy(step)
        self._context = deepcopy(context)
        self._binding = identity()
        if expected is not None and (not isinstance(expected, dict) or expected != self._binding):
            raise FormationError("TOOL_FORMATION_CHANGED", changed_fields=(
                sorted(key for key in self._binding if expected.get(key) != self._binding[key])
                if isinstance(expected, dict) else ("binding",)))

    @property
    def binding(self):
        return deepcopy(self._binding)

    def assert_current(self, step, context):
        current = self._identity()
        changed = {key for key in self._binding if current.get(key) != self._binding[key]}
        if request_identity(step) != self._binding["request_sha256"]:
            changed.add("request_sha256")
        if context_identity(context) != self._binding["context_sha256"]:
            changed.add("context_sha256")
        if changed:
            raise FormationError("TOOL_FORMATION_CHANGED", changed_fields=sorted(changed))

    @contextmanager
    def guard(self, step, context):
        with self._lock:
            self.assert_current(step, context)
            yield self

    def invoke(self, step, context):
        # No second registry lookup: the exact checked implementation and
        # copied parameters are held until the actual call completes.
        self.assert_current(step, context)
        invocation_context = deepcopy(self._context)
        from lumenis.system.security.permission import _is_server_local_workspace_principal
        if _is_server_local_workspace_principal(context.get("actor")):
            # assert_current above verified the live immutable principal and
            # full actor/scope/workspace identity against formation.
            invocation_context["actor"] = context["actor"]
        control = context.get("execution_control")
        if control is not None:
            from agent_runtime.loop import StepExecutionControl
            if type(control) is not StepExecutionControl:
                raise FormationError("TOOL_EXECUTION_CONTROL_INVALID")
            # Server-only dispatch control is deliberately not model data or a
            # replacement for the captured actor/scope/parameter binding.
            invocation_context["execution_control"] = control
        return self._invoke(deepcopy(self._step), invocation_context)


class BoundToolExecutor:
    """Bind a direct server callback; this adds no registry or runtime owner.

    Registry-dispatch callbacks must instead use CapabilityRouter.form_step,
    which captures the resolved handler. Do not wrap a name-only dispatcher.
    """

    def __init__(self, handler, *, origin, resource_uri, identity_provider,
                 dependency_paths=(), action_type="ANALYZE", lock=None):
        self.handler = handler
        self.origin = origin
        self.resource_uri = resource_uri
        self.identity_provider = identity_provider
        self.dependency_paths = tuple(dependency_paths)
        self.action_type = action_type
        self.lock = lock or threading.RLock()

    def form_step(self, step, context, *, expected=None):
        with self.lock:
            if not self.origin or not self.resource_uri or not callable(self.handler):
                raise FormationError("TOOL_IMPLEMENTATION_NOT_BOUND")
            handler = self.handler
            provider = self.identity_provider

            def identity():
                if self.handler is not handler:
                    raise FormationError("TOOL_IMPLEMENTATION_CHANGED")
                if self.identity_provider is not provider:
                    raise FormationError("TOOL_RUNTIME_IDENTITY_CHANGED")
                return {"schema": "lumenis-formed-call:v1", "origin": self.origin,
                        "resource_uri": self.resource_uri, "effect": self.action_type,
                        "descriptor_sha256": digest({"tool": step.tool, "effect": self.action_type}),
                        "implementation_sha256": implementation_identity(handler, self.dependency_paths),
                        "runtime_sha256": runtime_identity(self.identity_provider),
                        "content_sha256": digest([]), "request_sha256": request_identity(step),
                        "context_sha256": context_identity(context)}

            return FormedCall(step=step, context=context, identity=identity, invoke=handler,
                              lock=self.lock, expected=expected)
