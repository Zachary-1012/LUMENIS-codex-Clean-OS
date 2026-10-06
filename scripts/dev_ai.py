# -*- coding: utf-8 -*-
"""RETIRED engineering helper — not a current LUMENIS execution route.

Historical versions of this script selected Zhipu GLM models and performed an
automatic model fallback. That conflicts with the current Product Owner rule:
Codex/Codex CLI engineering uses exactly the model, reasoning effort, and speed
selected manually in the active Codex window, while product AI belongs only to
the LUMENIS-owned SYSTEM AI Gateway / C2 route.

This path is retained as a fail-closed compatibility marker so old commands do
not silently reactivate a retired engineering provider.
"""
from __future__ import annotations

MESSAGE = (
    "[dev_ai] RETIRED: no default engineering model, provider, or automatic "
    "fallback is allowed. Use the current manually selected Codex window for "
    "engineering; use the owned SYSTEM AI Gateway/C2 contracts for LUMENIS "
    "product AI."
)

def main() -> int:
    print(MESSAGE)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
