from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse


MODEL_NAME = re.compile(r"^[A-Za-z0-9._/-]+(?::[A-Za-z0-9._-]+)?$")
SECRET = re.compile(
    r"(?i)(api[_-]?key|authorization|bearer|token|secret|password|cookie)"
    r"([=: ]+)([^\s,;\"']+)"
)
SENSITIVE_KEY = re.compile(r"(?i)(^|_)(api[_-]?key|authorization|access[_-]?token|refresh[_-]?token|secret|password|cookie)($|_)")


def validate_local_endpoint(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("local AI endpoint must be loopback HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("unsafe local AI endpoint")
    return url.rstrip("/")


def validate_model_name(name: str) -> str:
    if not MODEL_NAME.fullmatch(name or "") or ".." in name:
        raise ValueError("unsafe model name")
    return name


def sanitize_trace(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else sanitize_trace(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_trace(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_trace(item) for item in value]
    if isinstance(value, str):
        return SECRET.sub(r"\1\2[REDACTED]", value)
    return value
