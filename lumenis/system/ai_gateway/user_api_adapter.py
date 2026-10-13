"""Optional user-supplied model API (OpenAI-compatible) for the AI Gateway.

PO rule: the owned 序境 model is the default. This single generic adapter is
used only when the user explicitly sets AI_PROVIDER=user_api and supplies their
own purchased API (USER_MODEL_API_BASE_URL / USER_MODEL_API_KEY /
USER_MODEL_API_MODEL). There is no automatic fallback in either direction and
the product never calls a third-party model by default.
"""
import json
import os
import urllib.request

PROVIDER = "user_api"


def is_selected() -> bool:
    return os.environ.get("AI_PROVIDER", "").strip().lower() == PROVIDER


def config():
    return {
        "base_url": os.environ.get("USER_MODEL_API_BASE_URL", "").strip().rstrip("/"),
        "api_key": os.environ.get("USER_MODEL_API_KEY", "").strip(),
        "model": os.environ.get("USER_MODEL_API_MODEL", "").strip(),
    }


def is_configured() -> bool:
    cfg = config()
    return is_selected() and cfg["base_url"].startswith("https://") and bool(cfg["api_key"]) and bool(cfg["model"])


def chat(system, user, *, temperature=0.2, max_tokens=1200, timeout=60):
    """Return (content, provider, usage). Fails closed; never falls back."""
    if not is_configured():
        return None, "provider_disabled", None
    cfg = config()
    body = json.dumps({
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system or ""},
                     {"role": "user", "content": user or ""}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            return None, "user_api_invalid_response", data.get("usage")
        return content, PROVIDER, data.get("usage")
    except Exception:
        return None, "user_api_unavailable", None
