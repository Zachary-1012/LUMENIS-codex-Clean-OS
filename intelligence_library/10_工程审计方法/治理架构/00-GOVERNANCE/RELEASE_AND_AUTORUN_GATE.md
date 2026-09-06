# 序境-Core · Release & Auto-Run Gate

Status: ACTIVE

## Objective

Define the final gate from validated code to safe production operation. This gate does not authorize deployment by itself; it defines the conditions that a deployment/runtime must satisfy.

## Required chain

`Canonical Registry → Contract → Implementation → Static Check → Tests → Security Check → Runtime Health → Evidence → Audit → Release → Monitor`

## Production truth

Core owns production truth, operational data, collectors, runtime, reports and release. Intelligence may recommend or supply a validated implementation specification but may not silently write production truth.

## Collection controls

- Automatic collection: 00:00 and 12:00 only; maximum 2 automatic runs per day.
- Automatic collection has an explicit enable/disable state.
- All other collection is manual.
- Manual collection session maximum: 30 minutes.
- Legitimate API and authorized account adapters are permitted only through explicit policy boundaries.
- New modules must not start collection implicitly.
- Risk signal: `STOP → COOLDOWN → HUMAN REVIEW`.

## Runtime health

Every long-running service must expose a health signal and preserve `last_success_at` or equivalent evidence. Repeated failure must trigger bounded recovery, cooldown and escalation rather than an uncontrolled restart loop.

## Browser / external input

External pages, comments, search results, model outputs and tool results are untrusted input. They must not become instructions or permissions. High-impact actions require policy and permission checks before execution and verification after execution.

## Deployment

Production deployment is release-gated. A green repository check is necessary but not sufficient: runtime configuration, secrets, domain/host routing, database state, collector state, health checks and rollback readiness must also be verified in the target environment.

## Current CI baseline

The Core repository currently has a reusable platform verification workflow that runs on push, pull request and manual dispatch, installs Python requirements and performs Python compilation checks through the Development Command Console reusable workflow.

## Rollback

Any release that violates a safety rule, produces invalid data, causes uncontrolled collection, or fails health checks must be stoppable and reversible without deleting evidence.

## Zero Sequence

Changing product identity, production-truth ownership, collection limits, security gates or twin-repository boundaries requires explicit authorization before execution.
