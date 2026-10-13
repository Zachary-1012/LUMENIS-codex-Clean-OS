# LUMENIS compatibility deployment wrappers

> **SUPPORTING COMPATIBILITY / NOT CURRENT RUNTIME AUTHORITY.**
> Current Windows runtime authority is `scripts/start_production.ps1`; Product Core is `127.0.0.1:8201`.
> These files only preserve older operator entry names and must converge to that one launcher.

- `start_local.bat` and `启动系统.bat`: forward to the canonical 8201 production launcher.
- The product has no temporary public-tunnel launcher. `/remote` returns an explicit unavailable result without reading or redirecting to a saved external address. Any future public deployment needs its own approval.
- No compatibility wrapper owns another Core port, database, collector, browser runtime or product identity.
- `.env.example` is documentation only. Runtime secrets/configuration come only from protected local configuration.
