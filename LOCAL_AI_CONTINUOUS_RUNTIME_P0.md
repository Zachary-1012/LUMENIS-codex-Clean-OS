# Local AI Continuous Runtime — P0

Status: Frozen execution requirement

## Goal
Local AI must be treated as a supervised runtime service, not a manually started best-effort process.

## Required lifecycle
START → LOAD MODEL → HEALTH CHECK → READY → HEARTBEAT → INFERENCE CHECK → RECOVER ON FAILURE → HEALTH CHECK → READY

## Required observability
Track:
- process/service status;
- endpoint reachability;
- model-loaded/ready state;
- last successful health check;
- last successful inference;
- consecutive failures;
- restart count;
- cooldown state;
- current provider/model;
- degraded/fallback state.

Do not treat an alive process as healthy if inference is unavailable.

## Recovery
Use a supervisor appropriate to the host OS/runtime. On failure, restart within configured limits and cooldown. After restart, require model readiness and a real inference health check before returning READY.

Prevent restart storms with bounded retries, exponential/backoff or configured cooldown and circuit-breaker behavior. If recovery fails, emit an explicit alert/state and invoke the documented fallback provider if available.

## Availability contract
“Continuous” means: while the host machine and required runtime resources are available, the service is continuously supervised and automatically recovered where possible. Power loss, OS shutdown, hardware failure or resource exhaustion cannot be promised away; these must produce a detectable failure state and recovery path.

## No silent degradation
No empty/mock result may be presented as successful AI output. Every degraded/fallback response must carry runtime state/evidence sufficient for diagnosis.

## Security
No credentials, cookies, tokens or secrets may be written to logs or Git. Local endpoints must follow the repository's access-control/network policy.

## Integration boundary
Local AI is a provider/runtime capability. It must not modify ZBC Subject Truth, business rules, risk thresholds, permissions or Evidence. Cross-repository use remains governed by the Zachary↔ZBC Twin-Repository Contract.

## Definition of Done
- supervisor configured;
- boot/start recovery tested;
- model-load failure tested;
- endpoint failure tested;
- inference failure tested;
- restart/cooldown tested;
- fallback tested where configured;
- heartbeat and last_success_at visible;
- no secret leakage;
- regression tests pass;
- Evidence recorded;
- committed and pushed.
