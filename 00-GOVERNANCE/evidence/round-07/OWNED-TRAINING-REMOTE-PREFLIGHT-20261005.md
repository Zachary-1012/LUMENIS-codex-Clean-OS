# Owned-training remote preflight binding — 2026-10-05

## Purpose

The earlier rented-GPU attempt reached zero optimizer steps because the serving
Core did not establish its private endpoint binding before paid execution. A
local configuration file being present could not prove what the running Core or
remote machine would use.

This batch adds the missing no-model, no-GPU product preflight step to the
existing SYSTEM AI Gateway. It does not create another trainer, endpoint store,
Permission owner, queue, model route or GPU recipe.

## Bound path

```text
exact MODEL_TRAIN approval
→ current scope/identity recheck
→ current private endpoint resolver
→ authenticated one-shot SSH source-pin inspection
→ current scope/approval recheck
→ explicit REMOTE_TRAINING_PREFLIGHT_BOUND result
→ only then may the existing phase-task execution path be considered
```

The one-shot SSH command verifies only the configured remote source root and
the five pinned worker source hashes. It never calls `start_stdio`, creates a
remote worker process, loads a model, invokes CUDA, downloads weights, creates
an output directory, writes a checkpoint or increments optimizer steps.

## Contract

- New route: `POST /api/experience/owned-training/execution-preflight`.
- It reuses the existing exact training request, scope descriptors, Permission
  owner and private endpoint resolver; client-supplied endpoint, actor, pin or
  SSH option fields are never accepted.
- It returns no endpoint host, user, port, private-key path, known-hosts path,
  session, credential, remote directory or model content.
- Missing approval fails before constructing a transport. Changed or malformed
  remote observations fail closed as `REMOTE_TRAINING_PREFLIGHT_INVALID`.
- A positive result reports `training_started=false`, `model_loaded=false` and
  `optimizer_steps=0`; it is readiness evidence only.

## Local verification

`tests/test_owned_training_remote_preflight.py` covers:

1. the SSH adapter validates only its fixed source-pin request and does not
   create a channel or peer;
2. malformed remote observation fails closed;
3. the product endpoint returns the explicit no-training state;
4. missing exact approval reaches no transport; and
5. the global app Permission mapping delegates this exact route to the sealed
   owned-training owner rather than a generic path grant.

`python -m pytest tests/test_function_map_contract.py
tests/test_openapi_spec.py tests/test_owned_training_remote_preflight.py -q`
completed with **13 passing cases** after the final app-guard mapping. A prior
local attempt was correctly refused while the protected `data/monitor.db` had
WAL/SHM sidecars after an earlier default app import; the guard was not weakened
and the DB was not checkpointed, copied, deleted or repaired. The later isolated
test run passed with no background thread leak. Full clean-checkout execution
remains required after publication.

## Published-source verification

GitHub `main` commit `f3877f80b793e08807f3652b6c8cf550768fc2dc` contains this
source/API/documentation batch.

- [App Gate 37283524406](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37283524406)
  passed the Experience gates, complete Flutter analysis and canonical Flutter
  test suite.
- [Product Gate 37283529275](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37283529275)
  passed the governance/contract/Experience gates, clean-checkout Python
  compilation, isolated database acceptance and hermetic pytest suite.

These gate results prove the published source contracts. They do not establish
a reachable remote host, an allocated GPU, model files, model loading, training,
checkpoint bytes, inference quality or user acceptance.

## Current limits

- The current private runtime profile remains local and untracked by design.
- Its declared state is `NOT_LIVE_BINDING`; no current Core listens on 8201 and
  no remote preflight has been invoked in this batch.
- No GPU, paid resource, remote worker, model, source material, checkpoint,
  held-out evaluation, inference, promotion or rollback was started.
- A successful future preflight still does not allow billing automatically. The
  existing sequence remains: remote model-file inventory → model load → actual
  step/loss → checkpoint retrieval/reload → held-out evaluation → useful owned
  business result → controlled promotion/rollback.
