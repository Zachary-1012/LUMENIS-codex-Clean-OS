from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .security import validate_local_endpoint, validate_model_name


class OllamaRuntimeError(RuntimeError):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


class OllamaAdapter:
    def __init__(self, base_url: str, model: str, timeout: float = 120, context_window: int = 2048, max_retry: int = 1, cooldown_seconds: float = 2):
        self.base_url = validate_local_endpoint(base_url)
        self.model = validate_model_name(model)
        self.timeout = max(1.0, min(float(timeout), 300.0))
        self.context_window = max(512, min(int(context_window), 32768))
        self.max_retry = max(0, min(int(max_retry), 2))
        self.cooldown_seconds = max(0.0, min(float(cooldown_seconds), 5.0))
        self.last_success: str | None = None
        self.last_failure: str | None = None

    def _request(self, path: str, payload: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "LUMENIS-LocalAI/3.0"},
            method="POST" if payload is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                return json.loads(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:500]
            if "requires more system memory" in body.lower():
                kind = "RESOURCE_LIMIT"
            else:
                kind = "UNSUPPORTED_CAPABILITY" if exc.code in {400, 404} else "DOWN"
            raise OllamaRuntimeError(kind, f"ollama_http_{exc.code}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise OllamaRuntimeError("TIMEOUT", "ollama_timeout") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise OllamaRuntimeError("DOWN", f"ollama_unreachable:{type(exc).__name__}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaRuntimeError("INVALID_OUTPUT", "ollama_invalid_json_response") from exc

    def installed_models(self) -> list[dict[str, Any]]:
        return list(self._request("/api/tags", timeout=5).get("models") or [])

    def health(self, real_call: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            models = self.installed_models()
            names = {str(item.get("name") or item.get("model")) for item in models}
            installed = self.model in names
            result = {
                "installed": installed,
                "configured": True,
                "reachable": True,
                "loadable": False,
                "real_call_verified": False,
                "status": "DEGRADED" if not installed else "UP",
                "model": self.model,
                "last_success": self.last_success,
                "last_failure": self.last_failure,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            if real_call and installed:
                for attempt in range(1 + self.max_retry):
                    try:
                        call = self.chat(
                            "只输出JSON。", "返回 {\"health\":\"ok\"}",
                            {"type": "object", "properties": {"health": {"type": "string"}}, "required": ["health"]},
                            max_tokens=16,
                        )
                        result["loadable"] = True
                        result["real_call_verified"] = call["content"].get("health") == "ok"
                        result["status"] = "UP" if result["real_call_verified"] else "DEGRADED"
                        if result["real_call_verified"]:
                            self.last_success = datetime.now(timezone.utc).isoformat()
                            result["last_success"] = self.last_success
                        break
                    except OllamaRuntimeError as exc:
                        result["status"] = "DEGRADED"
                        result["error_type"] = exc.error_type
                        self.last_failure = datetime.now(timezone.utc).isoformat()
                        result["last_failure"] = self.last_failure
                        if attempt >= self.max_retry or exc.error_type not in {"RESOURCE_LIMIT", "TIMEOUT"}:
                            break
                        time.sleep(self.cooldown_seconds)
            result["latency_ms"] = int((time.perf_counter() - started) * 1000)
            return result
        except OllamaRuntimeError as exc:
            self.last_failure = datetime.now(timezone.utc).isoformat()
            return {"installed": False, "configured": True, "reachable": False, "loadable": False, "real_call_verified": False, "status": "DOWN", "error_type": exc.error_type, "last_success": self.last_success, "last_failure": self.last_failure, "checked_at": datetime.now(timezone.utc).isoformat(), "latency_ms": int((time.perf_counter() - started) * 1000)}

    def chat(self, system: str, user: str, schema: dict[str, Any], max_tokens: int = 512) -> dict[str, Any]:
        started = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0, "num_predict": min(max(16, int(max_tokens)), 2048), "num_ctx": self.context_window},
            "keep_alive": 0,
        }
        response = self._request("/api/chat", payload)
        raw = str((response.get("message") or {}).get("content") or "")
        try:
            content = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaRuntimeError("INVALID_OUTPUT", "model_output_not_json") from exc
        return {
            "content": content,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "prompt_tokens": int(response.get("prompt_eval_count") or 0),
            "completion_tokens": int(response.get("eval_count") or 0),
            "done_reason": response.get("done_reason", ""),
        }

    def chat_stream(self, system: str, user: str, max_tokens: int = 128):
        """Yield Ollama NDJSON text chunks; structured business paths still use chat()."""
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": True,
            "options": {"temperature": 0, "num_predict": min(max(16, int(max_tokens)), 512), "num_ctx": self.context_window},
            "keep_alive": 0,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + "/api/chat", data=data, headers={"Content-Type": "application/json", "User-Agent": "LUMENIS-LocalAI/3.0"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                for line in response:
                    item = json.loads(line.decode("utf-8"))
                    chunk = str((item.get("message") or {}).get("content") or "")
                    if chunk:
                        yield chunk
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise OllamaRuntimeError("DOWN", f"ollama_stream_failed:{type(exc).__name__}") from exc

    def unload(self) -> bool:
        self._request("/api/generate", {"model": self.model, "keep_alive": 0})
        return True
