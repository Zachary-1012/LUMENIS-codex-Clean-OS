# AI Provider Runtime Policy V1

Status: Frozen execution policy

## Objective
Keep only AI providers/models that have an evidenced runtime path; remove dead implementations and stale configuration while preserving a clean provider interface.

## Provider states
- ACTIVE: implementation + configuration path + real health/integration evidence.
- INTERFACE_ONLY: reusable adapter/interface intentionally retained, but no active credential/configuration.
- DISABLED: known unusable and excluded from runtime selection; remove implementation when dependency tracing proves it is dead.
- REMOVE: dead/duplicate/obsolete implementation with no required contract, test, CI, compliance or evidence dependency.

## Credential rule
Never commit API keys, tokens, cookies or secrets. Runtime secrets are environment/secret-manager values only. Empty/missing credentials must fail explicitly and use a documented fallback; never silently report success.

## Current confirmed signal
ZBC has a real ARK/Volcengine adapter history. Commit `35213832a1b74977cc3ddee023c75dc157b72afd` removed a hard-coded ARK API key and requires the key from `.env`, with explicit empty-key failure/degradation. Therefore ARK implementation remains subject to runtime health verification; the credential itself is never stored in Git.

## Execution
For every provider: locate adapter → locate config/env → locate callers → locate model/endpoint → inspect tests/CI → runtime health check → classify → clean unused implementation → regression test → evidence → commit.

Do not classify a provider as ACTIVE merely because code or an environment variable exists.

## Boundary
Provider cleanup must not alter ZBC business Truth, Subject filtering, risk thresholds, reporting semantics, permissions, or the Zachary↔ZBC repository contract.

## Required evidence
ACTIVE requires timestamped health/integration evidence with provider/model identifier, endpoint class, result, failure reason if any, and no secret values.
