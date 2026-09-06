# Local AI Continuous Runtime — P0

Status: Frozen execution requirement

Local AI is a supervised runtime capability, not a manually started best-effort process.

Required lifecycle:
START → LOAD MODEL → HEALTH CHECK → READY → HEARTBEAT → INFERENCE CHECK → RECOVER ON FAILURE → HEALTH CHECK → READY

Required state: process status, endpoint reachability, model readiness, last successful health check, last successful inference, consecutive failures, restart count, cooldown state, provider/model and degraded/fallback state.

An alive process is not considered healthy if inference is unavailable.

Use a host-appropriate supervisor. Restart failed services within bounded retry/cooldown limits, then require model readiness and a real inference check before READY. Prevent restart storms. If recovery fails, expose an explicit failure state and use the documented fallback where configured.

Continuous means continuously supervised while the host and required resources are available; power loss, OS shutdown, hardware failure and resource exhaustion must be detectable rather than silently ignored.

Never emit mock/empty output as successful AI output. Never write credentials, cookies, tokens or secrets to logs or Git.

Local AI remains a general runtime capability and must not modify ZBC Subject Truth, business rules, risk thresholds, permissions or Evidence. Cross-repository use follows the Zachary↔ZBC Twin-Repository Contract.

## Development takeover rule

When an AI agent performs code development, the target system must be started in a controlled development/runtime environment whenever technically possible. The agent must observe the live application state, run relevant health checks and tests, and continuously compare expected behavior against actual behavior while changes are being made.

A development task is not complete merely because source code compiles. The running system, API path, UI path and relevant data/AI path must be checked. Runtime errors, console errors, failed requests, broken interactions and regressions must be captured as Evidence and corrected before completion.

If the system cannot be started, the agent must explicitly mark runtime verification BLOCKED rather than claiming PASS.

## Definition of Done

Supervisor configured; boot recovery tested; model/endpoint/inference failures tested; restart/cooldown tested; fallback tested where configured; heartbeat and last_success_at visible; development runtime started and observed during applicable coding work; relevant live UI/API/data/AI paths verified; no secret leakage; regression tests pass; Evidence recorded; committed and pushed.
