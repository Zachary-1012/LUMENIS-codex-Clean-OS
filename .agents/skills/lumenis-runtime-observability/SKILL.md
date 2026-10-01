---
name: lumenis-runtime-observability
description: Use for LUMENIS startup, health, supervisor, process, scheduler, runtime topology, logs, recovery, port, API-health, resident browser, or live-environment investigation.
---
# Runtime / Observability
Use scripts/start_production.ps1 and http://127.0.0.1:8201/healthz as canonical Windows entry points unless current source changes them. Separate core health from external browser/login/source health. Trace dependencies -> config -> launcher -> boot -> supervisor -> port -> health -> initialization -> critical API/Experience. Never upgrade partial health into overall success.
