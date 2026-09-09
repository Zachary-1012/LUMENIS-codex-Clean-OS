from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REQUIRED_MODEL_FIELDS = {
    "id", "name", "provider", "runtime", "source", "upstream_repo",
    "upstream_version", "weight_source", "version", "license",
    "license_verified", "weight_license", "weight_license_verified",
    "commercial_use", "checksum", "capabilities", "languages",
    "context_window", "quantization", "hardware_requirement", "adapter",
    "health", "fallback", "resource_budget", "status", "replacement_target",
}
ALLOWED_PROMOTION = {"PRODUCTION_CANDIDATE", "PRODUCTION_APPROVED"}


class RegistryError(ValueError):
    pass


class AIRuntimeRegistry:
    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path(__file__).resolve().parents[1] / "config" / "ai_runtime"
        self.providers = self._load("providers.json")["providers"]
        self.models = self._load("models.json")["models"]
        self.runtime = self._load("runtime.json")
        self._validate()

    def _load(self, name: str) -> dict[str, Any]:
        path = (self.config_dir / name).resolve()
        if self.config_dir.resolve() not in path.parents:
            raise RegistryError("registry path traversal blocked")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"invalid registry: {name}: {type(exc).__name__}") from exc

    def _validate(self) -> None:
        provider_ids = {item.get("id") for item in self.providers}
        if len(provider_ids) != len(self.providers) or None in provider_ids:
            raise RegistryError("provider ids must be unique and non-empty")
        for model in self.models:
            missing = REQUIRED_MODEL_FIELDS - set(model)
            if missing:
                raise RegistryError(f"model {model.get('id')} missing fields: {sorted(missing)}")
            if model["provider"] not in provider_ids:
                raise RegistryError(f"unknown provider for model {model['id']}")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(model["checksum"])):
                raise RegistryError(f"model {model['id']} has invalid checksum manifest")
            if model["status"] in ALLOWED_PROMOTION:
                if not model["license_verified"] or not model["weight_license_verified"]:
                    raise RegistryError(f"model {model['id']} cannot be promoted with unknown license")
                if not model["source"] or not model["weight_source"]:
                    raise RegistryError(f"model {model['id']} cannot be promoted with unknown source")
            maximum = int(self.runtime.get("resource_guard", {}).get("max_model_memory_mb", 0))
            declared = int(model.get("resource_budget", {}).get("max_ram_mb", 0))
            if model["id"] == self.runtime.get("default_model") and maximum and declared > maximum:
                raise RegistryError(f"default model {model['id']} exceeds max_model_memory")

    def provider(self, provider_id: str) -> dict[str, Any]:
        for item in self.providers:
            if item["id"] == provider_id:
                return dict(item)
        raise RegistryError(f"unknown provider: {provider_id}")

    def model(self, model_id: str) -> dict[str, Any]:
        for item in self.models:
            if item["id"] == model_id:
                return dict(item)
        raise RegistryError(f"unknown model: {model_id}")
