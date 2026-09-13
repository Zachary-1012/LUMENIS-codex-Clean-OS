# -*- coding: utf-8 -*-
"""LUMENIS Experience V2 -> backend Binding Adapter (EXAMPLE / stub for Codex).
The experience layer is backend-agnostic. Replace DESIGN_ONLY fixtures by returning
the SAME view-model shape from real services. Never create a second truth store.
Contract: 12_contracts/VIEWMODEL_REGISTRY.json + binding_contract.schema.json.
"""
from __future__ import annotations
from typing import Any, Dict

# screen id -> callable that loads the production view-model (Codex implements)
_PROVIDERS: Dict[str, Any] = {}

def register_provider(screen_id: str, fn) -> None:
    """fn(subject_context) -> view-model dict matching <screen>.viewmodel.json"""
    _PROVIDERS[screen_id] = fn

def get_viewmodel(screen_id: str, subject_context: dict) -> dict:
    """Server-side: re-verify permission for subject_context BEFORE reading data.
    Missing values must be explicit null/'unknown' — never 0 or '未知' silent fill."""
    fn = _PROVIDERS.get(screen_id)
    if fn is None:
        return {"screen": screen_id, "state_source": "DESIGN_ONLY fixture",
                "note": "no production provider bound yet (CODEX_BINDING_REQUIRED)"}
    vm = fn(subject_context)
    vm["state_source"] = "backend"
    return vm

# Jinja-friendly: render the static shell, then hydrate sections from this VM.
# Static templates live in 10_prototype (HTML+Vanilla/ESM); no React/Vue required.
