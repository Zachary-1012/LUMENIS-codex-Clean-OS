# Retired provider compatibility repair — 2026-10-05

## Current behavior

The product keeps historical local-AI and quota URLs for compatibility, but the
SYSTEM AI Gateway retirement policy now controls every executable entry:

- App startup no longer imports the local AI client solely for side effects.
- `GET /api/local-ai/status` and the historical analysis/chat POST routes return
  `provider_disabled` without importing, probing or calling a local model.
- The historical per-call resource-pack entry rejects a retired provider before
  checking quota, recording usage, or dispatching to the Gateway.
- Retired-provider governance status reports `provider_disabled`, not Zhipu as
  a current primary provider.
- `config/ai-quota.json` remains a provenance-preserving 2026-09-03 resource
  snapshot and now states explicitly that it is not a current product execution
  route.

The original adapter code and historical observation remain in source/history.
The repair removes only their ability to become an active product execution path
through startup, a compatibility URL, quota mutation, or a false status label.

## Verification

`74` targeted tests passed across retired-local-AI compatibility, resource-pack
model forwarding under an explicit test-only provider override, Gateway degrade
and provider failover checks. The test-only override never changes the product
registry or enables a provider in normal runtime.

## Limits

This repair does not prove owned inference, model training, semantic quality,
actual business analysis, promotion, release or operating status. The approved
open-weight AI route remains the only future product inference path and still
requires its own runtime, evaluation and user-task evidence.
