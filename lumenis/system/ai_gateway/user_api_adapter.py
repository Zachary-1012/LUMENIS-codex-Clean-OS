"""User-selected external AI within the single Gateway, with exact consent.

User-supplied external APIs remain a multi-provider product capability. Reviewed
connections resolve through the existing origin-scoped registry. Custom HTTPS
connections use the same protocol and IP-pinned TLS safety boundary; unsupported
protocols remain explicitly not adapted.
Process environment variables never select a provider for a product user.
Credentials are held only in this process for their authenticated actor (or the
explicit local workspace), never persisted, returned, logged or auto-restored.
"""
from contextlib import contextmanager
import hashlib
import http.client
import ipaddress
import json
import math
import secrets
import socket
import ssl
import threading
import urllib.error
import urllib.request
import weakref
from urllib.parse import urlsplit
from .providers import user_api_connection

PROVIDER = "user_api"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_URL = GROQ_BASE_URL + "/chat/completions"
_configuration_lock = threading.RLock()
# Runtime-only values are tied to the canonical Gate lifetime and actor. A new
# process/Gate always starts with owned routing, even if old env flags remain.
_configurations = weakref.WeakKeyDictionary()


def _current_actor():
    from flask import has_request_context
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    if not has_request_context():
        raise PermissionError("USER_API_PERMISSION_CONTEXT_REQUIRED")
    actor = get_current_user(read_only=True)
    if actor is None:
        actor = resolve_local_workspace_principal(module="conversation", action="write")
    if actor is None:
        raise PermissionError("USER_API_PERMISSION_DENIED")
    return actor


def _identity():
    from lumenis.system.security.permission import get_permission_gate, _shared_workspace_actor_identity
    actor = _current_actor()
    gate = get_permission_gate()
    caller = _shared_workspace_actor_identity(actor)[2]
    if caller == "anonymous":
        raise PermissionError("USER_API_PERMISSION_DENIED")
    return actor, gate, caller


def config():
    """Internal snapshot for the current actor; never read server-wide keys."""
    try:
        _actor, gate, caller = _identity()
        with _configuration_lock:
            return dict(_configurations.get(gate, {}).get(caller, {}))
    except Exception:
        return {}


def is_selected() -> bool:
    return config().get("provider") == PROVIDER


def safe_error_code(code, default="USER_API_SETTINGS_UNAVAILABLE"):
    """Only fixed public protocol errors may leave the external-AI boundary."""
    allowed = {
        "PROVIDER_DISABLED", "USER_API_PERMISSION_DENIED", "USER_API_PERMISSION_CONTEXT_REQUIRED",
        "USER_API_PERMISSION_UNAVAILABLE", "USER_API_AUDIT_UNAVAILABLE",
        "USER_API_SETTINGS_ORIGIN_DENIED", "USER_API_SECURE_SETTINGS_REQUIRED",
        "USER_API_SETTINGS_INVALID", "USER_API_SETTINGS_UNAVAILABLE",
        "USER_API_CONFIGURATION_REQUIRED", "USER_API_CONFIGURATION_CHANGED",
        "USER_API_BASE_URL_REQUIRED", "USER_API_DESTINATION_NOT_ALLOWED",
        "USER_API_PROTOCOL_NOT_ADAPTED",
        "USER_API_KEY_REQUIRED", "USER_API_KEY_INVALID", "USER_API_MODEL_REQUIRED",
        "USER_API_MODEL_INVALID", "USER_API_INVALID_REQUEST", "USER_API_NOT_SELECTED",
        "USER_API_REQUEST_BINDING_INVALID", "USER_API_CONFIRMATION_INVALID", "USER_API_APPROVAL_REVOKED",
    }
    return code if type(code) is str and code in allowed else default


def audit_denial(code, error=None):
    """Log only fixed denial metadata; never include exception/request details."""
    if error is not None and getattr(error, "audit_id", None):
        return error.audit_id
    from lumenis.system.security.permission import get_permission_gate
    return get_permission_gate().audit_user_api_denial(code)


def _denied(code, *, audit_code=None, error=None):
    code = safe_error_code(code.upper(), "USER_API_PERMISSION_UNAVAILABLE").lower()
    try:
        audit_id = audit_denial(audit_code or code.upper(), error)
    except Exception:
        return None, "user_api_audit_unavailable", None
    return None, code, {"audit_id": audit_id}


def configure(data):
    """Audit refusal without recording settings values or credential hashes."""
    try:
        return _configure_current_user(data)
    except (PermissionError, ValueError) as exc:
        # Identity/storage failures may carry private exception text. Only the
        # fixed settings protocol codes below may cross this public boundary.
        code = str(exc)
        if safe_error_code(code) != code:
            code = "USER_API_SETTINGS_UNAVAILABLE"
            error = PermissionError(code)
        else:
            error = type(exc)(code)
        error.audit_id = audit_denial(code, exc)
        raise error from None
    except Exception:
        exc = PermissionError("USER_API_SETTINGS_UNAVAILABLE")
        exc.audit_id = audit_denial("USER_API_SETTINGS_UNAVAILABLE")
        raise exc from None


def _configure_current_user(data):
    """Explicit user settings, no probe or persistent credential grant."""
    from flask import request
    # JSON plus a same-origin browser request. Credential-bearing requests must
    # not be accepted from a cross-site form or another site's JavaScript.
    origin = request.headers.get("Origin")
    if (not request.is_json or (origin is not None and origin != request.host_url.rstrip("/"))):
        raise PermissionError("USER_API_SETTINGS_ORIGIN_DENIED")
    if not request.is_secure:
        from lumenis.system.security.permission import _local_workspace_authority_allowed
        try:
            loopback = ipaddress.ip_address(request.remote_addr).is_loopback
        except (TypeError, ValueError):
            loopback = False
        if not loopback or not _local_workspace_authority_allowed(request.host):
            raise PermissionError("USER_API_SECURE_SETTINGS_REQUIRED")
    if (type(data) is not dict or type(data.get("provider")) is not str
            or data.get("provider") not in {"owned", PROVIDER}):
        raise ValueError("USER_API_SETTINGS_INVALID")
    if set(data) - {"provider", "base_url", "api_key", "model", "protocol"}:
        raise ValueError("USER_API_SETTINGS_INVALID")
    actor, gate, caller = _identity()
    provider = data["provider"]
    if provider == "owned":
        if set(data) != {"provider"}:
            raise ValueError("USER_API_SETTINGS_INVALID")
        with _configuration_lock:
            _configurations.get(gate, {}).pop(caller, None)
            gate.revoke_user_api_requests(actor)
        return {"provider": "owned", "external_selected": False,
                "credential_persistence": "NONE", "fallback_allowed": False}
    gate.authorize_user_api_action(actor)
    cfg = {key: data.get(key) for key in ("base_url", "api_key", "model")}
    cfg["protocol"] = data.get("protocol", "openai_chat_completions")
    error = configuration_error(cfg)
    if error:
        raise ValueError(error)
    cfg.update(provider=PROVIDER, revision=secrets.token_hex(32))
    with _configuration_lock:
        gate.revoke_user_api_requests(actor)
        _configurations.setdefault(gate, {})[caller] = cfg
    return status()


def configuration_error(cfg):
    """Return a secret-free configuration error, without discovery or probing."""
    if not isinstance(cfg, dict):
        return "USER_API_CONFIGURATION_REQUIRED"
    base = cfg.get("base_url")
    if not isinstance(base, str) or not base:
        return "USER_API_BASE_URL_REQUIRED"
    connection = user_api_connection(base, cfg.get("protocol", "openai_chat_completions"))
    if connection is None:
        return "USER_API_DESTINATION_NOT_ALLOWED"
    if (connection["protocol"] != "openai_chat_completions"
            or connection["token_field"] not in {"max_tokens", "max_completion_tokens"}):
        return "USER_API_PROTOCOL_NOT_ADAPTED"
    for field, code in (("api_key", "KEY"), ("model", "MODEL")):
        value = cfg.get(field)
        if not isinstance(value, str) or not value.strip():
            return "USER_API_" + code + "_REQUIRED"
        if len(value) > (8192 if field == "api_key" else 200) or any(ord(c) < 32 or ord(c) == 127 for c in value):
            return "USER_API_" + code + "_INVALID"
    return None


def configuration_is_complete(cfg) -> bool:
    return configuration_error(cfg) is None


def is_configured() -> bool:
    cfg = config()
    return cfg.get("provider") == PROVIDER and configuration_is_complete(cfg)


def status():
    """Current actor's sanitized selection; configuration never proves inference."""
    cfg = config()
    selected = cfg.get("provider") == PROVIDER
    error = configuration_error(cfg)
    configured = selected and error is None
    connection = user_api_connection(cfg.get("base_url"), cfg.get("protocol", "openai_chat_completions")) if selected else None
    return {
        "provider": PROVIDER, "selected": selected,
        "configured": configured, "available": False,
        "state": "CONFIGURED_NOT_VERIFIED" if configured else "UNAVAILABLE",
        "reason": ("INFERENCE_NOT_VERIFIED" if configured else
                   "USER_API_NOT_SELECTED" if not selected else error),
        "service_binding": "CONFIGURED" if configured else "NOT_BOUND",
        "service_provider": connection["service_provider"] if connection else None,
        "connection_origin": "user_api", "protocol": connection["protocol"] if connection else None,
        "destination": connection["destination"] if configured else None,
        "admission_state": ("NOT_ADAPTED" if error == "USER_API_PROTOCOL_NOT_ADAPTED" else
                            "REQUIRES_DNS_VALIDATION" if configured else "NOT_ADMITTED"),
        "model_id": cfg.get("model") if configured else None,
        "fallback_allowed": False, "credential_persistence": "NONE",
        "confirmation_required": True,
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _public_address(value):
    """Deny special/local ranges, including mapped IPv4 and IPv6 tunnels."""
    try:
        address = ipaddress.ip_address(value)
        if (not address.is_global or address.is_multicast or address.is_reserved
                or address.is_loopback or address.is_link_local or address.is_unspecified):
            return False
        if address.version == 6:
            # Do not admit IPv4-mapped, NAT64, 6to4 or Teredo routes whose embedded
            # target can differ from the apparently public IPv6 destination.
            return (address in ipaddress.ip_network("2000::/3")
                    and address not in ipaddress.ip_network("2001::/23")
                    and address not in ipaddress.ip_network("2002::/16"))
        # Python versions differ on newer special-use classifications.
        return not any(address in ipaddress.ip_network(network) for network in
                       ("192.0.0.0/24", "192.88.99.0/24", "198.18.0.0/15"))
    except (TypeError, ValueError):
        return False


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """One validated numeric address; TLS authenticates the original hostname."""
    def __init__(self, host, address, timeout):
        context = ssl.create_default_context()
        context.set_alpn_protocols(["http/1.1"])
        super().__init__(host, 443, timeout=timeout, context=context)
        self._validated_address = address

    def connect(self):
        family, socktype, proto, _canonname, sockaddr = self._validated_address
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(self.timeout)
            sock.connect(sockaddr)  # Numeric address: no second DNS lookup.
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


@contextmanager
def _open(req, timeout):
    """Public-only pinned HTTPS; no env proxy, redirect, DNS rebinding or retry."""
    url = urlsplit(req.full_url)
    # The request URL is reconstructed from the same connection as the consent.
    # This final defensive check precedes DNS, TLS and transmission of any key.
    if (url.scheme != "https" or url.port not in (None, 443) or not url.hostname
            or url.username is not None or url.password is not None
            or url.query or url.fragment or req.get_method() != "POST"):
        raise PermissionError("USER_API_DESTINATION_NOT_ALLOWED")
    addresses = socket.getaddrinfo(url.hostname, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    if (not addresses or any(item[0] not in (socket.AF_INET, socket.AF_INET6)
            or item[1] != socket.SOCK_STREAM or item[2] != socket.IPPROTO_TCP
            or not _public_address(item[4][0]) or item[4][1] != 443
            or (item[0] == socket.AF_INET6 and item[4][3] != 0)
            for item in addresses)):
        raise PermissionError("USER_API_DESTINATION_NOT_ALLOWED")
    connection = _PinnedHTTPSConnection(url.hostname, addresses[0], timeout)
    try:
        connection.request("POST", url.path or "/", body=req.data, headers=dict(req.header_items()))
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            # No redirect handling, including same-origin redirects. Do not read
            # or expose an error body that could echo credentials or prompts.
            raise urllib.error.HTTPError(req.full_url, response.status, "Provider request failed", {}, None)
        yield response
    finally:
        connection.close()


def chat(system, user, *, temperature=0.2, max_tokens=1200, timeout=60,
         external_user_input=False, external_approval=None):
    """Return content/provider/usage-or-preview; fail closed without exact consent."""
    if external_user_input is not True:
        return _denied("provider_disabled", audit_code="USER_API_EXTERNAL_INPUT_REQUIRED")
    try:
        actor, gate, caller = _identity()
        gate.authorize_user_api_action(actor)
    except PermissionError as exc:
        code = str(exc)
        return _denied(safe_error_code(code, "USER_API_PERMISSION_UNAVAILABLE").lower(), error=exc)
    except Exception:
        return _denied("user_api_permission_unavailable")
    cfg = config()
    if cfg.get("provider") != PROVIDER:
        return _denied("provider_disabled", audit_code="USER_API_NOT_SELECTED")
    error = configuration_error(cfg)
    if error:
        return _denied(error.lower())
    if (not isinstance(system, str) or not isinstance(user, str)
            or len(system) + len(user) > 32000
            or type(max_tokens) is not int or not 0 < max_tokens <= 8192
            or type(temperature) not in (int, float)
            or not math.isfinite(temperature) or not 0 <= temperature <= 2
            or type(timeout) not in (int, float)
            or not math.isfinite(timeout) or not 0 < timeout <= 60):
        return _denied("user_api_invalid_request")
    from .core import redact_for_cloud
    system = redact_for_cloud(system).replace(cfg["api_key"], "[REDACTED]") if system else ""
    user = redact_for_cloud(user).replace(cfg["api_key"], "[REDACTED]") if user else ""
    connection = user_api_connection(cfg["base_url"], cfg.get("protocol", "openai_chat_completions"))
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature, connection["token_field"]: max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    binding = {"caller": caller, "destination": connection["destination"], "model": cfg["model"],
               "body_sha256": hashlib.sha256(body).hexdigest(), "configuration_revision": cfg["revision"]}
    token = None
    try:
        if external_approval is None:
            preview = gate.prepare_user_api_request(actor, binding)
            return None, "user_api_approval_required", {
                "approval_request": {**preview, "destination": connection["destination"],
                    "provider": connection["service_provider"], "connection_origin": "user_api",
                    "protocol": connection["protocol"], "model": cfg["model"], "request": payload,
                    "body_sha256": binding["body_sha256"], "single_use": True,
                    "data_scope": "This exact redacted conversation only; no stored business sources."},
            }
        token = gate.confirm_user_api_request(actor, binding, external_approval)
        # Serialize withdrawal with the final check and transport initiation.
        # No retry occurs after consumption, even when the remote result is unknown.
        with _configuration_lock:
            if config() != cfg or user_api_connection(cfg["base_url"], cfg.get("protocol", "openai_chat_completions")) != connection:
                raise PermissionError("USER_API_CONFIGURATION_CHANGED")
            decision = gate.consume_user_api_approval(actor, binding, token)
            result = _send(cfg, body, timeout, connection=connection)
            try:
                gate._write_audit(
                    operation_type=decision.operation_type, resource=decision.resource,
                    risk_level="high", permission_required="exact_user_confirmation",
                    caller=decision.caller, result="completed" if result[1] == PROVIDER else "failed",
                    reason="USER_API_TRANSPORT_COMPLETED" if result[1] == PROVIDER else result[1].upper(),
                    operation_id=None, approval_token=None, require_persistence=True,
                )
            except Exception:
                # The request may already have left the process. Never retry or
                # return its unrecorded answer as a verified complete operation.
                return None, "user_api_audit_unavailable_after_send", None
            return result
    except PermissionError as exc:
        code = str(exc)
        return _denied(safe_error_code(code, "USER_API_PERMISSION_UNAVAILABLE").lower(), error=exc)
    except Exception:
        return _denied("user_api_permission_unavailable")
    finally:
        if token:
            gate.revoke_approval(token)


def _send(cfg, body, timeout, *, connection=None):
    """Only chat's exact single-use permission boundary may initiate transport."""
    current = user_api_connection(cfg.get("base_url"), cfg.get("protocol", "openai_chat_completions"))
    error = configuration_error(cfg)
    if error:
        return None, error.lower(), None
    if connection is not None and current != connection:
        return None, "user_api_configuration_changed", None
    req = urllib.request.Request(
        current["destination"], data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "LUMENIS-Gateway/1.0",
                 "Authorization": "Bearer " + cfg["api_key"]})
    try:
        with _open(req, timeout=timeout) as resp:
            raw = resp.read(2_000_001)
            if len(raw) > 2_000_000:
                return None, "user_api_invalid_response", None
            data = json.loads(raw.decode("utf-8"))
        if (not isinstance(data, dict) or data.get("error")
                or data.get("status") not in (None, "completed")):
            return None, "user_api_invalid_response", None
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content")
        if (not isinstance(content, str) or not content.strip()
                or choice.get("finish_reason") not in (None, "stop")):
            return None, "user_api_invalid_response", None
        raw_usage = data.get("usage")
        usage = ({key: value for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                  if type(value := raw_usage.get(key)) is int and value >= 0}
                 if isinstance(raw_usage, dict) else None)
        return content, PROVIDER, usage or None
    except PermissionError:
        return None, "user_api_destination_not_allowed", None
    except urllib.error.HTTPError as exc:
        # Do not leak raw provider bodies, prompts, credentials or URLs.
        code = ("authentication_failed" if exc.code == 401 else
                "access_denied" if exc.code == 403 else
                "rate_limited" if exc.code == 429 else "unavailable")
        return None, "user_api_" + code, None
    except ssl.SSLError:
        # Certificate verification errors also inherit ValueError. They are
        # transport failures, never a malformed model response or retry grant.
        return None, "user_api_unavailable", None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return None, "user_api_invalid_response", None
    except (OSError, http.client.HTTPException):
        return None, "user_api_unavailable", None
