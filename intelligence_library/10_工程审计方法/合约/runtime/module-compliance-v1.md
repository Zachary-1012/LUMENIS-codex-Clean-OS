# Global Module Runtime Compliance v1

This contract applies to existing and newly added modules. No module is exempt.

## Mandatory execution chain

Trigger -> Run ID -> Execute -> Heartbeat -> Result -> Evidence -> Return -> Persistence -> Health Check -> Recovery/Breaker -> Final Status.

## Forbidden states

- Silent execution
- Silent failure
- Silent completion
- Untracked background jobs
- Results that cannot be correlated to a Run ID
- AI output presented as verified fact without evidence

## Required observable state

Every runtime operation must expose: `run_id`, `module`, `started_at`, `status`, `return_status`, `heartbeat.last_at`, `heartbeat.interval_ms`, `last_success_at`, `evidence_ids`, and counters where applicable.

## Status semantics

`queued` -> `running` -> `success | partial | failed | no_return | recovering | cancelled`.

`no_return` is a first-class failure state and must trigger diagnosis/retry policy according to the owning module's recovery policy.

## Cross-repository rule

Zachary OS AI owns generic AI/runtime/orchestration capabilities. Z-Brand-Core owns product-domain business logic. Cross-repository communication must use versioned contracts/adapters and evidence identifiers. Business modules must not depend on private implementation details of the AI/runtime layer.
