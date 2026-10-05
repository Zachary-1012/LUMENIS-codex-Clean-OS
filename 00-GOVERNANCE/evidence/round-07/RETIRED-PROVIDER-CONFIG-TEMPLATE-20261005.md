# Retired-provider configuration template alignment — 2026-10-05

The tracked `.env.example` previously described local Ollama and multiple
external providers as automatic product routes, while the current product rule
retired those routes. This could cause a later workstation setup to reintroduce
an unavailable or forbidden fallback even though the SYSTEM AI Gateway rejected
it at runtime.

The template now preserves every compatibility key for local configuration
coverage but keeps the values blank and marks the routes retired. It sets
`ALLOW_CLOUD_AI=false` and `LOCAL_AI_PREFERRED=false`; `AI_PROVIDER=auto`
therefore remains an honest unavailable state until the owned foundation route
has real binding evidence. The historical provider-failover document is marked
`SUPERSEDED / HISTORICAL ONLY` and points back to the current AGENTS/SYSTEM AI
Gateway authority.

No product provider code, credential, quota, local model server, external API,
model execution or user data changed. `tests/test_ai_off_shardB.py` asserts the
template cannot restore the retired routes.

GitHub `main` commit `373d846a0afb55f76e26753d6f5a953994a1f074` passed
[Product Gate 37289571504](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37289571504),
including the clean-checkout hermetic pytest suite and configuration test. This
confirms the source/template rule; it does not make an owned model available.
