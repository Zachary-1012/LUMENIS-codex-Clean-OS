"""Optional user-supplied model API (OpenAI-compatible) for the AI Gateway.

PO rule: the owned 序境 model is the default. This single generic adapter is
used only when the user explicitly sets AI_PROVIDER=user_api and supplies their
own authorized API (USER_MODEL_API_BASE_URL / USER_MODEL_API_KEY /
USER_MODEL_API_MODEL). There is no automatic fallback in either direction and
the product never calls a third-party model by default.
"""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit

PROVIDER = "user_api"


def is_selected() -> bool:
    return os.environ.get("AI_PROVIDER", "").strip().lower() == PROVIDER


def config():
    return {
        "base_url": os.environ.get("USER_MODEL_API_BASE_URL", "").strip().rstrip("/"),
        "api_key": os.environ.get("USER_MODEL_API_KEY", "").strip(),
        "model": os.environ.get("USER_MODEL_API_MODEL", "").strip(),
    }


def configuration_is_complete(cfg) -> bool:
    try:
        url = urlsplit(cfg["base_url"])
        valid_url = (url.scheme == "https" and bool(url.hostname)
                     and not url.username and not url.password
                     and not url.query and not url.fragment and url.port in (None, 443))
    except ValueError:
        valid_url = False
    return valid_url and bool(cfg["api_key"]) and bool(cfg["model"])


def is_configured() -> bool:
    return is_selected() and configuration_is_complete(config())


def status():
    """Read configuration only; no discovery, secret output or inference claim."""
    cfg = config()
    configured = is_configured()
    return {
        "provider": PROVIDER, "configured": configured, "available": False,
        "state": "CONFIGURED_NOT_VERIFIED" if configured else "UNAVAILABLE",
        "reason": "INFERENCE_NOT_VERIFIED" if configured else "USER_API_CONFIGURATION_REQUIRED",
        "service_binding": "CONFIGURED" if configured else "NOT_BOUND",
        "service_provider": "groq" if cfg["base_url"] == "https://api.groq.com/openai/v1" else "user_api",
        "model_id": cfg["model"] if configured else None, "fallback_allowed": False,
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A configured destination is not permission to forward its bearer token.
        return None


def _open(req, timeout):
    return urllib.request.build_opener(_NoRedirect()).open(req, timeout=timeout)


def chat(system, user, *, temperature=0.2, max_tokens=1200, timeout=60):
    """Return (content, provider, usage). Fails closed; never falls back."""
    if not is_configured():
        return None, "provider_disabled", None
    cfg = config()
    from .core import redact_for_cloud

    # Final transport boundary applies to every admitted caller. Configuration
    # is not a grant to export business sources or credential material.
    system = redact_for_cloud(system).replace(cfg["api_key"], "[REDACTED]") if system else ""
    user = redact_for_cloud(user).replace(cfg["api_key"], "[REDACTED]") if user else ""
    body = json.dumps({
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system or ""},
                     {"role": "user", "content": user or ""}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "LUMENIS-Gateway/1.0",
                 "Authorization": "Bearer " + cfg["api_key"]})
    try:
        with _open(req, timeout=timeout) as resp:
            raw = resp.read(2_000_001)
            if len(raw) > 2_000_000:
                return None, "user_api_invalid_response", None
            data = json.loads(raw.decode("utf-8"))
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            return None, "user_api_invalid_response", data.get("usage")
        return content, PROVIDER, data.get("usage")
    except urllib.error.HTTPError as exc:
        # Do not leak raw provider bodies, prompts, credentials or URLs.
        code = ("authentication_failed" if exc.code == 401 else
                "access_denied" if exc.code == 403 else
                "rate_limited" if exc.code == 429 else "unavailable")
        return None, "user_api_" + code, None
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError):
        return None, "user_api_unavailable", None
