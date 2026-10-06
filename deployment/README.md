# LUMENIS compatibility deployment wrappers

> **SUPPORTING COMPATIBILITY / NOT CURRENT RUNTIME AUTHORITY.**
> Current Windows runtime authority is `scripts/start_production.ps1`; Product Core is `127.0.0.1:8201`.
> These files only preserve older operator entry names and must converge to that one launcher.

- `start_local.bat` and `启动系统.bat`: forward to the canonical 8201 production launcher.
- `start_remote.bat` and `启动远程访问.bat`: require explicit compatibility Basic Auth, ensure the canonical 8201 runtime, then start a Cloudflare Quick Tunnel to that same Core.
- No compatibility wrapper owns another Core port, database, collector, browser runtime or product identity.
- `.env.example` is documentation only. Runtime secrets/configuration come only from protected local configuration.
